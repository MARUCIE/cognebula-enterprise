"""Fetcher: Chinese Institute of Certified Public Accountants (中国注册会计师协会).

Source: https://www.cicpa.org.cn
Content: Audit standards, professional guidelines, interpretation documents
Volume: 200+ standards and guidelines
Priority: P0 (蜂群审计 Tier 2)
"""
import argparse
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fetch_cicpa")

BASE_URL = "https://www.cicpa.org.cn"

# Sections with tax/audit-relevant content
SECTIONS = [
    {"name": "professional_standards", "url": "/ztzl1/Professional_standards/", "max_pages": 10},
    {"name": "industry_regulation", "url": "/ztzl1/Industry_regulation/", "max_pages": 10},
    {"name": "public_services", "url": "/ggfw/", "max_pages": 5},
    {"name": "news", "url": "/xxfb/news/", "max_pages": 5},
    {"name": "notices", "url": "/xxfb/tzgg/", "max_pages": 5},
    {"name": "registration", "url": "/ztzl1/Registration/", "max_pages": 3},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _fetch_list_page(client: httpx.Client, url: str) -> list[dict]:
    """Fetch a listing page and extract article links."""
    items = []
    try:
        resp = client.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return items
        soup = BeautifulSoup(resp.text, "html.parser")

        # Common CICPA list patterns
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            if not href.startswith("http"):
                href = BASE_URL + href
            if "cicpa.org.cn" in href and title:
                items.append({"title": title, "url": href})
    except Exception as e:
        log.warning("List page failed %s: %s", url, e)
    return items


def _fetch_article(client: httpx.Client, url: str) -> str:
    """Fetch full article text."""
    try:
        resp = client.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try common content selectors
        for selector in [".article-content", ".content-detail", ".TRS_Editor", "#content", ".main-content"]:
            div = soup.select_one(selector)
            if div:
                text = div.get_text(separator=" ", strip=True)
                if len(text) >= 50:
                    return text[:10000]

        # Fallback: largest text block
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20)
        if len(text) >= 100:
            return text[:10000]
    except Exception:
        pass
    return ""


def fetch(output_dir: str, max_total: int = 1000, fetch_content: bool = False) -> list[dict]:
    """Fetch from CICPA website."""
    results = []
    now = datetime.now(timezone.utc).isoformat()
    seen_urls = set()

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for section in SECTIONS:
            if len(results) >= max_total:
                break

            log.info("Section: %s", section["name"])

            for page in range(1, section["max_pages"] + 1):
                if len(results) >= max_total:
                    break

                url = f"{BASE_URL}{section['url']}"
                if page > 1:
                    url = f"{url}index_{page}.html"

                time.sleep(3)
                items = _fetch_list_page(client, url)

                if not items:
                    break

                for item in items:
                    if item["url"] in seen_urls:
                        continue
                    seen_urls.add(item["url"])

                    content = ""
                    if fetch_content:
                        time.sleep(3)
                        content = _fetch_article(client, item["url"])

                    results.append({
                        "id": _make_id(item["url"]),
                        "title": item["title"],
                        "url": item["url"],
                        "content": content,
                        "source": f"cicpa/{section['name']}",
                        "type": "standard/audit",
                        "crawled_at": now,
                    })

                log.info("Section '%s' page %d: %d items, total %d",
                         section["name"], page, len(items), len(results))

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "cicpa.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch CICPA standards and guidelines")
    parser.add_argument("--output", default="./out")
    parser.add_argument("--max-total", type=int, default=1000)
    parser.add_argument("--fetch-content", action="store_true")
    args = parser.parse_args()
    fetch(args.output, max_total=args.max_total, fetch_content=args.fetch_content)
