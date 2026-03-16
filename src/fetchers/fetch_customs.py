"""Fetcher: General Administration of Customs tariff listings (customs.gov.cn)."""

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
log = logging.getLogger("fetch_customs")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

BASE_URL = "http://www.customs.gov.cn"
LIST_URL = f"{BASE_URL}/customs/302427/302442/jckszcx/index.html"


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
    """Extract tariff / policy links from Customs listing page."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.select("ul.list_02 li, ul.conList li, div.conList_ld ul li, ul.list li"):
        a_tag = li.find("a")
        if not a_tag or not a_tag.get("href"):
            continue
        title = a_tag.get_text(strip=True)
        href = a_tag["href"]
        if not href.startswith("http"):
            href = BASE_URL + href if href.startswith("/") else LIST_URL.rsplit("/", 1)[0] + "/" + href

        date_span = li.find("span")
        date_text = date_span.get_text(strip=True) if date_span else ""
        date_match = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", date_text)
        date_str = date_match.group(1) if date_match else date_text

        if title:
            items.append({"title": title, "url": href, "date": date_str})
    return items


def _fetch_detail(client: httpx.Client, url: str) -> str:
    """Fetch article body text."""
    try:
        time.sleep(5)
        resp = client.get(url, headers=_headers(), timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        content_div = soup.select_one("div.easysite-news-text, div.TRS_Editor, div.content")
        text = content_div.get_text(separator="\n", strip=True) if content_div else ""
        return text[:3000]
    except Exception as e:
        log.warning("Detail fetch failed for %s: %s", url, e)
        return ""


def fetch(output_dir: str, max_pages: int = 2, fetch_detail: bool = True) -> list[dict]:
    results = []
    now = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for page_idx in range(max_pages):
            url = LIST_URL if page_idx == 0 else LIST_URL.replace("index.html", f"index_{page_idx}.html")
            try:
                if page_idx > 0:
                    time.sleep(5)
                log.info("Fetching listing page %d: %s", page_idx + 1, url)
                resp = client.get(url, headers=_headers())
                resp.encoding = "utf-8"
                entries = _parse_listing(resp.text)
                log.info("Found %d entries on page %d", len(entries), page_idx + 1)

                for entry in entries:
                    content = ""
                    if fetch_detail:
                        content = _fetch_detail(client, entry["url"])
                    results.append({
                        "id": _make_id(entry["url"]),
                        "title": entry["title"],
                        "url": entry["url"],
                        "content": content,
                        "source": "customs_tariff",
                        "type": "tariff",
                        "date": entry["date"],
                        "crawled_at": now,
                    })
            except Exception as e:
                log.error("Listing page %d failed: %s", page_idx + 1, e)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "customs.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Customs tariff listings")
    parser.add_argument("--output", default="./out", help="Output directory")
    parser.add_argument("--pages", type=int, default=2, help="Number of listing pages")
    parser.add_argument("--no-detail", action="store_true", help="Skip fetching article body")
    args = parser.parse_args()
    fetch(args.output, max_pages=args.pages, fetch_detail=not args.no_detail)
