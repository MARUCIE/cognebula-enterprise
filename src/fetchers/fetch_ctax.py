"""Fetcher: China Taxation News (ctax.org.cn) -- news and article listings."""

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
log = logging.getLogger("fetch_ctax")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

BASE_URL = "https://www.ctax.org.cn"
# Multiple sections worth crawling
SECTIONS = [
    ("tax_news", f"{BASE_URL}/csyw/"),          # Tax news
    ("policy_interpret", f"{BASE_URL}/zcjd/"),   # Policy interpretation
    ("tax_practice", f"{BASE_URL}/swsw/"),       # Tax practice
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


def _parse_listing(html: str, section_url: str) -> list[dict]:
    """Extract article links from a ctax.org.cn listing page."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.select("ul.list li, div.list ul li, ul.news_list li, div.listBox ul li"):
        a_tag = li.find("a")
        if not a_tag or not a_tag.get("href"):
            continue
        title = a_tag.get_text(strip=True)
        href = a_tag["href"]
        if not href.startswith("http"):
            href = BASE_URL + href if href.startswith("/") else section_url + href

        date_str = ""
        date_el = li.find("span") or li.find("em")
        if date_el:
            date_match = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", date_el.get_text())
            date_str = date_match.group(1) if date_match else ""

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
        content_div = soup.select_one("div.TRS_Editor, div.content, div.article-content, #zoom")
        text = content_div.get_text(separator="\n", strip=True) if content_div else ""
        return text[:3000]
    except Exception as e:
        log.warning("Detail fetch failed for %s: %s", url, e)
        return ""


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
                entries = _parse_listing(resp.text, section_url)
                log.info("Found %d entries in section '%s'", len(entries), section_name)

                for entry in entries:
                    content = ""
                    if fetch_detail:
                        content = _fetch_detail(client, entry["url"])
                    results.append({
                        "id": _make_id(entry["url"]),
                        "title": entry["title"],
                        "url": entry["url"],
                        "content": content,
                        "source": "ctax",
                        "type": section_name,
                        "date": entry["date"],
                        "crawled_at": now,
                    })
            except Exception as e:
                log.error("Section '%s' failed: %s", section_name, e)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "ctax.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch ctax.org.cn articles")
    parser.add_argument("--output", default="./out", help="Output directory")
    parser.add_argument("--no-detail", action="store_true", help="Skip fetching article body")
    args = parser.parse_args()
    fetch(args.output, fetch_detail=not args.no_detail)
