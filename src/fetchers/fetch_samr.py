"""Fetcher: State Administration for Market Regulation (samr.gov.cn) news and notices.

NOTE: SAMR uses Hanweb CMS which renders listing content via client-side JavaScript.
httpx cannot execute JS, so this fetcher may return 0 items from listing pages.
It is kept for future browser-automation integration. For now, disabled in run_all.py.
"""

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
log = logging.getLogger("fetch_samr")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

BASE_URL = "https://www.samr.gov.cn"
# Sections: homepage links covering news categories (gdt = work dynamics, zj = special focus)
SECTIONS = [
    ("work_dynamics", f"{BASE_URL}/xw/gdt/"),
    ("special_focus", f"{BASE_URL}/xw/zj/"),
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
    """Extract links from SAMR listing pages.

    SAMR uses /xw/{section}/art/YYYY/art_UUID.html pattern.
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
        # Match SAMR content URLs: /xw/.../art/YYYY/art_UUID.html
        if re.search(r"/xw/\w+/art/\d{4}/art_[a-f0-9\-]+\.html", href, re.IGNORECASE):
            full_url = href if href.startswith("http") else BASE_URL + href
            if full_url not in seen_urls:
                date_m = re.search(r"/art/(\d{4})/", href)
                date_str = date_m.group(1) if date_m else ""
                items.append({"title": title, "url": full_url, "date": date_str})
                seen_urls.add(full_url)

    # Strategy 2: Regex fallback
    if len(items) < 3:
        for m in re.finditer(
            r'<a[^>]*href="([^"]*?/xw/\w+/art/\d{4}/art_[a-f0-9\-]+\.html)"[^>]*>([^<]{8,})</a>',
            html,
            re.IGNORECASE,
        ):
            href, title = m.group(1), m.group(2).strip()
            full_url = href if href.startswith("http") else BASE_URL + href
            if full_url not in seen_urls:
                date_m = re.search(r"/art/(\d{4})/", href)
                date_str = date_m.group(1) if date_m else ""
                items.append({"title": title, "url": full_url, "date": date_str})
                seen_urls.add(full_url)

    return items


def _fetch_detail(client: httpx.Client, url: str) -> tuple[str, str]:
    """Fetch article body text, truncated to 3000 chars. Returns (content, date_str)."""
    try:
        time.sleep(5)
        resp = client.get(url, headers=_headers(), timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract date from detail page
        date_str = ""
        date_el = soup.select_one("span.time, span.info-time, div.article-info, div.artinfo")
        if date_el:
            date_m = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", date_el.get_text())
            if date_m:
                date_str = date_m.group(1)

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        content_div = soup.select_one("div.TRS_Editor, div.detail-content, div.content, div.article-content, #zoom")
        text = content_div.get_text(separator="\n", strip=True) if content_div else ""
        if not text:
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else ""
        return text[:3000], date_str
    except Exception as e:
        log.warning("Detail fetch failed for %s: %s", url, e)
        return "", ""


def fetch(output_dir: str, fetch_detail: bool = True) -> list[dict]:
    results = []
    now = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for section_name, section_url in SECTIONS:
            try:
                time.sleep(5)
                log.info("Fetching section '%s': %s", section_name, section_url)
                resp = client.get(section_url, headers=_headers())
                resp.encoding = "utf-8"
                entries = _parse_listing(resp.text)
                log.info("Found %d entries in section '%s'", len(entries), section_name)

                for entry in entries:
                    content = ""
                    date = entry["date"]
                    if fetch_detail:
                        content, detail_date = _fetch_detail(client, entry["url"])
                        if detail_date:
                            date = detail_date
                    results.append({
                        "id": _make_id(entry["url"]),
                        "title": entry["title"],
                        "url": entry["url"],
                        "content": content,
                        "source": "samr",
                        "type": section_name,
                        "date": date,
                        "crawled_at": now,
                    })
            except Exception as e:
                log.error("Section '%s' failed: %s", section_name, e)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "samr.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch SAMR news and market regulation notices")
    parser.add_argument("--output", default="./out", help="Output directory")
    parser.add_argument("--no-detail", action="store_true", help="Skip fetching article body")
    args = parser.parse_args()
    fetch(args.output, fetch_detail=not args.no_detail)
