"""Fetcher: China Securities Regulatory Commission (csrc.gov.cn) news and regulations."""

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
log = logging.getLogger("fetch_csrc")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

BASE_URL = "http://www.csrc.gov.cn"
# Key sections: news, policy interpretation, dept rules, normative docs
SECTIONS = [
    ("csrc_news", f"{BASE_URL}/csrc/c100028/common_list.shtml"),          # CSRC news
    ("policy_interpret", f"{BASE_URL}/csrc/c100039/common_list.shtml"),    # Policy interpretation
    ("dept_rules", f"{BASE_URL}/csrc/c100033/common_list.shtml"),          # Dept rules/bumen guizhang
    ("normative_docs", f"{BASE_URL}/csrc/c100034/common_list.shtml"),      # Normative documents
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
    """Extract links from CSRC listing pages.

    CSRC uses /csrc/cNNNNNN/cNNNNNN/content.shtml pattern.
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
        # Match CSRC content URLs: /csrc/cNNNNNN/cNNNNNN/content.shtml
        if re.match(r"/csrc/c\d+/c\d+/content\.shtml", href):
            full_url = BASE_URL + href
            if full_url not in seen_urls:
                items.append({"title": title, "url": full_url, "date": ""})
                seen_urls.add(full_url)

    # Strategy 2: Regex fallback
    if len(items) < 3:
        for m in re.finditer(
            r'<a[^>]*href="(/csrc/c\d+/c\d+/content\.shtml)"[^>]*>([^<]{8,})</a>',
            html,
        ):
            href, title = m.group(1), m.group(2).strip()
            full_url = BASE_URL + href
            if full_url not in seen_urls:
                items.append({"title": title, "url": full_url, "date": ""})
                seen_urls.add(full_url)

    return items


def _fetch_detail(client: httpx.Client, url: str) -> str:
    """Fetch article body text, truncated to 3000 chars."""
    try:
        time.sleep(5)
        # Detail pages may redirect; follow them
        resp = client.get(url, headers=_headers(), timeout=15, follow_redirects=True)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract date from detail page
        date_str = ""
        date_el = soup.select_one("span.info-time, span.time, div.article-info")
        if date_el:
            date_m = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", date_el.get_text())
            if date_m:
                date_str = date_m.group(1)

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        content_div = soup.select_one("div.TRS_Editor, div.detail-content, div.content, #zoom")
        text = content_div.get_text(separator="\n", strip=True) if content_div else ""
        if not text:
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else ""
        return text[:3000], date_str
    except Exception as e:
        log.warning("Detail fetch failed for %s: %s", url, e)
        return "", ""


def fetch(output_dir: str, max_pages: int = 5, fetch_detail: bool = True) -> list[dict]:
    results = []
    seen_urls = set()
    now = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=15, follow_redirects=False) as client:
        for section_name, section_url in SECTIONS:
            for page_idx in range(max_pages):
                if page_idx == 0:
                    url = section_url
                else:
                    url = section_url.replace("common_list.shtml", f"common_list_{page_idx}.shtml")
                try:
                    if page_idx > 0 or section_name != SECTIONS[0][0]:
                        time.sleep(5)
                    log.info("Fetching section '%s' page %d/%d: %s", section_name, page_idx + 1, max_pages, url)
                    resp = client.get(url, headers=_headers())
                    if resp.status_code == 404:
                        log.info("Section '%s' page %d returned 404, stopping", section_name, page_idx + 1)
                        break
                    # Detect redirect to homepage (section unavailable)
                    if resp.status_code in (301, 302, 303, 307, 308):
                        location = resp.headers.get("location", "")
                        log.warning("Section '%s' page %d redirected to %s, skipping section", section_name, page_idx + 1, location)
                        break
                    resp.encoding = "utf-8"
                    entries = _parse_listing(resp.text)
                    log.info("Found %d entries in section '%s' page %d", len(entries), section_name, page_idx + 1)

                    if not entries:
                        log.info("Section '%s' page %d returned 0 items, stopping", section_name, page_idx + 1)
                        break

                    new_count = 0
                    for entry in entries:
                        if entry["url"] in seen_urls:
                            continue
                        seen_urls.add(entry["url"])
                        new_count += 1
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
                            "source": "csrc",
                            "type": section_name,
                            "date": date,
                            "crawled_at": now,
                        })
                    log.info("Added %d new (deduped) entries from section '%s' page %d", new_count, section_name, page_idx + 1)
                except Exception as e:
                    log.error("Section '%s' page %d failed: %s", section_name, page_idx + 1, e)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "csrc.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch CSRC news and regulations")
    parser.add_argument("--output", default="./out", help="Output directory")
    parser.add_argument("--pages", type=int, default=5, help="Max pages per section")
    parser.add_argument("--no-detail", action="store_true", help="Skip fetching article body")
    args = parser.parse_args()
    fetch(args.output, max_pages=args.pages, fetch_detail=not args.no_detail)
