"""Fetcher: State Administration of Foreign Exchange (safe.gov.cn) policy/regulation releases."""

import argparse
import hashlib
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fetch_safe")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

BASE_URL = "https://www.safe.gov.cn"
# Multiple sections: policy interpretation, forex news, regulations
SECTIONS = [
    ("policy_interpret", f"{BASE_URL}/safe/zcfgjd/index.html"),
    ("forex_news", f"{BASE_URL}/safe/whxw/index.html"),
    ("regulations", f"{BASE_URL}/safe/zcfg/index.html"),
]


def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": BASE_URL,
    }


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _parse_listing(html: str) -> list[dict]:
    """Extract links from SAFE listing pages.

    SAFE uses /safe/YYYY/MMDD/NNNNN.html pattern for article URLs.
    """
    items = []
    seen_urls = set()

    # Strategy 1: BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        title = a_tag.get_text(strip=True)
        if not title or len(title) < 8:
            continue
        if href.startswith("/safe/") and re.match(r"/safe/\d{4}/\d{4}/\d+\.html", href):
            full_url = BASE_URL + href
            if full_url not in seen_urls:
                # Extract date from URL: /safe/YYYY/MMDD/
                date_m = re.search(r"/safe/(\d{4})/(\d{2})(\d{2})/", href)
                date_str = f"{date_m.group(1)}-{date_m.group(2)}-{date_m.group(3)}" if date_m else ""
                items.append({"title": title, "url": full_url, "date": date_str})
                seen_urls.add(full_url)

    # Strategy 2: Regex fallback
    if len(items) < 3:
        for m in re.finditer(
            r'<a[^>]*href="(/safe/\d{4}/\d{4}/\d+\.html)"[^>]*>([^<]{8,})</a>',
            html,
        ):
            href, title = m.group(1), m.group(2).strip()
            full_url = BASE_URL + href
            if full_url not in seen_urls:
                date_m = re.search(r"/safe/(\d{4})/(\d{2})(\d{2})/", href)
                date_str = f"{date_m.group(1)}-{date_m.group(2)}-{date_m.group(3)}" if date_m else ""
                items.append({"title": title, "url": full_url, "date": date_str})
                seen_urls.add(full_url)

    return items


def _fetch_detail(client: httpx.Client, url: str) -> str:
    """Fetch article body text, truncated to 3000 chars."""
    try:
        time.sleep(5)
        resp = client.get(url, headers=_headers(), timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        content_div = soup.select_one("div.TRS_Editor, div.detail-content, div.content, #zoom")
        text = content_div.get_text(separator="\n", strip=True) if content_div else ""
        if not text:
            # Fallback: get main body text
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else ""
        return text[:3000]
    except Exception as e:
        log.warning("Detail fetch failed for %s: %s", url, e)
        return ""


def fetch(output_dir: str, max_pages_per_section: int = 5, fetch_detail: bool = True) -> list[dict]:
    results = []
    now = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for section_name, section_index_url in SECTIONS:
            for page_idx in range(max_pages_per_section):
                if page_idx == 0:
                    url = section_index_url
                else:
                    url = section_index_url.replace("index.html", f"index_{page_idx}.html")
                try:
                    if page_idx > 0 or section_name != SECTIONS[0][0]:
                        time.sleep(5)
                    log.info("Fetching section '%s' page %d/%d: %s", section_name, page_idx + 1, max_pages_per_section, url)
                    resp = client.get(url, headers=_headers())
                    if resp.status_code == 404:
                        log.info("Section '%s' page %d returned 404, stopping", section_name, page_idx + 1)
                        break
                    resp.encoding = "utf-8"
                    entries = _parse_listing(resp.text)
                    log.info("Found %d entries in section '%s' page %d", len(entries), section_name, page_idx + 1)

                    if not entries:
                        log.info("Section '%s' page %d returned 0 items, stopping", section_name, page_idx + 1)
                        break

                    for entry in entries:
                        content = ""
                        if fetch_detail:
                            content = _fetch_detail(client, entry["url"])
                        results.append({
                            "id": _make_id(entry["url"]),
                            "title": entry["title"],
                            "url": entry["url"],
                            "content": content,
                            "source": "safe_forex",
                            "type": section_name,
                            "date": entry["date"],
                            "crawled_at": now,
                        })
                except Exception as e:
                    log.error("Section '%s' page %d failed: %s", section_name, page_idx + 1, e)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "safe.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch SAFE forex regulations")
    parser.add_argument("--output", default="./out", help="Output directory")
    parser.add_argument("--pages-per-section", type=int, default=5, help="Max pages per section")
    parser.add_argument("--no-detail", action="store_true", help="Skip fetching article body")
    args = parser.parse_args()
    fetch(args.output, max_pages_per_section=args.pages_per_section, fetch_detail=not args.no_detail)
