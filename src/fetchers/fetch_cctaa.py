"""Fetcher: China Certified Tax Agents Association (中国注册税务师协会).

Source: https://www.cctaa.cn
Content: Tax practice guidelines, professional standards, member publications
Volume: 300+ documents
Priority: P0 (蜂群审计 Tier 2)
Members: 9,392 tax firms, 55,078 individual tax practitioners
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
log = logging.getLogger("fetch_cctaa")

BASE_URL = "https://www.cctaa.cn"

SECTIONS = [
    {"name": "policy_law", "url": "/channels/287.html", "max_pages": 10},
    {"name": "industry_standard", "url": "/channels/288.html", "max_pages": 5},
    {"name": "practice_guide", "url": "/channels/289.html", "max_pages": 5},
    {"name": "tax_service", "url": "/channels/290.html", "max_pages": 5},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _fetch_list_page(client: httpx.Client, url: str) -> list[dict]:
    """Fetch listing page and extract links."""
    items = []
    try:
        resp = client.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return items
        soup = BeautifulSoup(resp.text, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            if not href.startswith("http"):
                href = BASE_URL + href
            if "cctaa.cn" in href and "/contents/" in href:
                items.append({"title": title, "url": href})
    except Exception as e:
        log.warning("List page failed: %s", e)
    return items


def _fetch_article(client: httpx.Client, url: str) -> str:
    """Fetch full article content."""
    try:
        resp = client.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")

        for selector in [".article-content", ".content", ".TRS_Editor", "#content", ".detail-content"]:
            div = soup.select_one(selector)
            if div:
                text = div.get_text(separator=" ", strip=True)
                if len(text) >= 50:
                    return text[:10000]

        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20)
        if len(text) >= 100:
            return text[:10000]
    except Exception:
        pass
    return ""


def fetch(output_dir: str, max_total: int = 1000, fetch_content: bool = False) -> list[dict]:
    """Fetch from CCTAA website."""
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

                url = section["url"]
                if page > 1:
                    url = url.replace(".html", f"_{page}.html")

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
                        "source": f"cctaa/{section['name']}",
                        "type": "standard/tax_practice",
                        "crawled_at": now,
                    })

                log.info("Section '%s' page %d: %d items, total %d",
                         section["name"], page, len(items), len(results))

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "cctaa.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch CCTAA tax practice standards")
    parser.add_argument("--output", default="./out")
    parser.add_argument("--max-total", type=int, default=1000)
    parser.add_argument("--fetch-content", action="store_true")
    args = parser.parse_args()
    fetch(args.output, max_total=args.max_total, fetch_content=args.fetch_content)
