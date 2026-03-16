"""Fetcher: People's Bank of China, Legal Affairs Dept (pbc.gov.cn/tiaofasi/)."""

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
log = logging.getLogger("fetch_pbc")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

BASE_URL = "https://www.pbc.gov.cn"
# Multiple sections: regulations, rules, normative documents
SECTIONS = [
    ("regulations", f"{BASE_URL}/tiaofasi/144941/144951/index.html"),      # Law/regulations
    ("rules", f"{BASE_URL}/tiaofasi/144941/144953/index.html"),            # Rules/guizhang
    ("normative_docs", f"{BASE_URL}/tiaofasi/144941/144957/index.html"),   # Normative documents
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


def _parse_listing(html: str, section_base_url: str) -> list[dict]:
    """Extract regulation links from PBC listing page."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    # PBC uses table or <li> based listings depending on section
    for row in soup.select("table.newslist_style tr, ul.list li, div.MediaBlock_list ul li"):
        a_tag = row.find("a")
        if not a_tag or not a_tag.get("href"):
            continue
        title = a_tag.get_text(strip=True)
        href = a_tag["href"]
        if href.startswith("./"):
            href = section_base_url + href[1:]
        elif not href.startswith("http"):
            href = BASE_URL + href if href.startswith("/") else section_base_url + "/" + href

        # Date extraction
        date_str = ""
        td_or_span = row.find("td", class_="hb_time") or row.find("span")
        if td_or_span:
            date_match = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", td_or_span.get_text())
            date_str = date_match.group(1) if date_match else ""

        if title and len(title) > 5:
            items.append({"title": title, "url": href, "date": date_str})

    # Regex fallback: PBC links follow /tiaofasi/144941/144957/XXX/index.html pattern
    if len(items) < 3:
        seen_urls = {i["url"] for i in items}
        for m in re.finditer(
            r'<a[^>]*href=["\']'
            r'(/tiaofasi/\d+/\d+/[^"\']+)'
            r'["\'][^>]*>([^<]{5,})</a>',
            html,
        ):
            href, title = m.group(1), m.group(2).strip()
            full_url = BASE_URL + href
            if full_url not in seen_urls and title and len(title) > 5:
                items.append({"title": title, "url": full_url, "date": ""})
                seen_urls.add(full_url)
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
        content_div = soup.select_one("div#zoom, div.TRS_Editor, div.content")
        text = content_div.get_text(separator="\n", strip=True) if content_div else ""
        return text[:3000]
    except Exception as e:
        log.warning("Detail fetch failed for %s: %s", url, e)
        return ""


def fetch(output_dir: str, max_pages: int = 5, fetch_detail: bool = True) -> list[dict]:
    results = []
    now = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for section_name, section_index_url in SECTIONS:
            section_base_url = section_index_url.rsplit("/", 1)[0]
            for page_idx in range(max_pages):
                if page_idx == 0:
                    url = section_index_url
                else:
                    url = section_index_url.replace("index.html", f"index_{page_idx}.html")
                try:
                    if page_idx > 0 or section_name != SECTIONS[0][0]:
                        time.sleep(5)
                    log.info("Fetching section '%s' page %d/%d: %s", section_name, page_idx + 1, max_pages, url)
                    resp = client.get(url, headers=_headers())
                    if resp.status_code == 404:
                        log.info("Section '%s' page %d returned 404, stopping", section_name, page_idx + 1)
                        break
                    resp.encoding = "utf-8"
                    entries = _parse_listing(resp.text, section_base_url)
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
                            "source": "pbc_tiaofasi",
                            "type": section_name,
                            "date": entry["date"],
                            "crawled_at": now,
                        })
                except Exception as e:
                    log.error("Section '%s' page %d failed: %s", section_name, page_idx + 1, e)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "pbc.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch PBC regulations")
    parser.add_argument("--output", default="./out", help="Output directory")
    parser.add_argument("--pages", type=int, default=5, help="Max pages per section")
    parser.add_argument("--no-detail", action="store_true", help="Skip fetching article body")
    args = parser.parse_args()
    fetch(args.output, max_pages=args.pages, fetch_detail=not args.no_detail)
