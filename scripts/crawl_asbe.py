#!/usr/bin/env python3
"""Crawl Chinese Accounting Standards (ASBE/CAS) from MOF website.

Source: https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/
42 enterprise accounting standards (基本准则 + CAS 1-42)

Output: JSON file with full text for each standard.
No DB write — safe to run anytime.

Run:
    python3 scripts/crawl_asbe.py
"""
import json
import logging
import os
import re
import time

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("asbe")

BASE_URL = "https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "asbe")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "asbe_standards.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def crawl_listing(client: httpx.Client) -> list[dict]:
    """Crawl all standard listings across paginated pages."""
    standards = []
    seen_urls = set()

    # Page 1 has no suffix, pages 2-5 have index_N.htm
    pages = [BASE_URL] + [f"{BASE_URL}index_{i}.htm" for i in range(1, 10)]

    for page_url in pages:
        try:
            time.sleep(1)
            resp = client.get(page_url, headers=HEADERS, timeout=15)
            if resp.status_code == 404:
                break
            resp.encoding = "utf-8"

            soup = BeautifulSoup(resp.text, "html.parser")
            links = soup.select("a[href]")

            page_count = 0
            for link in links:
                href = link.get("href", "")
                title = link.get_text(strip=True)

                # Filter for standard links (contain 准则 or t2008/t2019 etc.)
                if not title or len(title) < 5:
                    continue
                if "准则" not in title and "基本准则" not in title:
                    continue

                # Resolve URL
                if href.startswith("./"):
                    full_url = BASE_URL + href[2:]
                elif href.startswith("http"):
                    full_url = href
                elif href.startswith("/"):
                    full_url = "https://kjs.mof.gov.cn" + href
                else:
                    full_url = BASE_URL + href

                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # Extract CAS number
                cas_match = re.search(r'第(\d+)号', title)
                cas_num = int(cas_match.group(1)) if cas_match else 0

                standards.append({
                    "title": title,
                    "url": full_url,
                    "cas_number": cas_num,
                })
                page_count += 1

            log.info("Page %s: %d standards found", page_url.split("/")[-1] or "index", page_count)
            if page_count == 0:
                break

        except Exception as e:
            log.error("Page %s failed: %s", page_url, e)
            break

    # Sort by CAS number
    standards.sort(key=lambda x: x["cas_number"])
    log.info("Total standards found: %d", len(standards))
    return standards


def crawl_fulltext(client: httpx.Client, standards: list[dict]) -> list[dict]:
    """Fetch full text for each standard."""
    results = []

    for i, std in enumerate(standards):
        try:
            time.sleep(2)
            resp = client.get(std["url"], headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"

            soup = BeautifulSoup(resp.text, "html.parser")

            # Try multiple content selectors
            content_el = None
            for sel in ["div.TRS_Editor", "div.content", "div.article-content",
                        "div.text", "div#zoom", "div.Custom_UnionStyle"]:
                content_el = soup.select_one(sel)
                if content_el and len(content_el.get_text(strip=True)) > 100:
                    break

            if not content_el:
                # Fallback: largest text block
                divs = soup.find_all("div")
                best = max(divs, key=lambda d: len(d.get_text(strip=True)), default=None)
                if best and len(best.get_text(strip=True)) > 200:
                    content_el = best

            content = ""
            if content_el:
                # Clean up: remove scripts, styles
                for tag in content_el.find_all(["script", "style", "nav"]):
                    tag.decompose()
                content = content_el.get_text("\n", strip=True)

            results.append({
                **std,
                "content": content[:50000],
                "content_length": len(content),
            })

            status = "OK" if len(content) > 100 else "SHORT"
            log.info("  [%d/%d] %s %s (%d chars)", i + 1, len(standards), status, std["title"][:40], len(content))

        except Exception as e:
            log.error("  [%d/%d] FAIL %s: %s", i + 1, len(standards), std["title"][:30], e)
            results.append({**std, "content": "", "content_length": 0})

    good = sum(1 for r in results if r["content_length"] > 100)
    log.info("Full text: %d/%d OK (%.0f%%)", good, len(results), 100 * good / max(len(results), 1))
    return results


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        standards = crawl_listing(client)
        if not standards:
            log.error("No standards found. Site may have changed.")
            return

        results = crawl_fulltext(client, standards)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log.info("Saved to %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
