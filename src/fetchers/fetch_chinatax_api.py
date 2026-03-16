"""Fetcher: ChinaTax FGK Policy Database via search5 JSON API.

Discovered by R2 swarm agent: the FGK policy database exposes a search API at
https://www.chinatax.gov.cn/search5/search/s that returns structured JSON.

Total records: 57,073+ (as of 2026-03-15)
Key columns: 政策法规 (4,960), 税务规范性文件 (1,911), 财税文件 (1,512)

The API requires a cookie (C3VK) from a prior page visit due to JS challenge.
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

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fetch_chinatax_api")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

BASE_URL = "https://www.chinatax.gov.cn"
SEARCH_API = f"{BASE_URL}/search5/search/s"

# Columns worth crawling (filter by label for precision)
SEARCH_CONFIGS = [
    {"name": "policy_law", "label": "税务规范性文件", "max_pages": 200},
    {"name": "fiscal_doc", "label": "财税文件", "max_pages": 200},
    {"name": "admin_regulation", "label": "行政法规", "max_pages": 50},
    {"name": "dept_rule", "label": "部门规章", "max_pages": 50},
    {"name": "policy_interpret", "label": "政策解读", "max_pages": 100},
    {"name": "law", "label": "法律", "max_pages": 10},
    {"name": "all_policy", "label": "", "max_pages": 200},  # No label = all content
]


def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": f"{BASE_URL}/",
    }


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _get_cookie(client: httpx.Client) -> dict:
    """Get the C3VK anti-bot cookie by visiting any page first."""
    try:
        resp = client.get(f"{BASE_URL}/", headers=_headers(), timeout=10)
        # The JS challenge sets a cookie; extract it from the response
        cookies = dict(resp.cookies)
        if cookies:
            log.info("Got cookies: %s", list(cookies.keys()))
            return cookies
        # Try to extract C3VK from JS in response body
        m = re.search(r"C3VK=([^;]+)", resp.text)
        if m:
            cookies["C3VK"] = m.group(1)
            log.info("Extracted C3VK cookie from JS")
            return cookies
    except Exception as e:
        log.warning("Cookie fetch failed: %s", e)
    return {}


def _search_page(client: httpx.Client, label: str, page: int, cookies: dict) -> list[dict]:
    """Fetch one page of search results from FGK API."""
    params = {
        "siteCode": "bm29000002",
        "searchSiteName": "GSFFK",
        "pageNum": str(page),
        "indexCode": "1",
    }
    if label:
        params["label"] = label

    try:
        resp = client.get(
            SEARCH_API,
            params=params,
            headers=_headers(),
            cookies=cookies,
            timeout=15,
        )
        if resp.status_code != 200:
            log.warning("API returned %d for page %d", resp.status_code, page)
            return []

        # Detect JS challenge (non-JSON response)
        if not resp.text.strip().startswith("{"):
            log.warning("API returned non-JSON for page %d (cookie expired?)", page)
            return []

        data = resp.json()
        total_info = data.get("searchResultAll", {})
        items_raw = total_info.get("searchTotal", [])

        if not items_raw:
            return []

        items = []
        for item in items_raw:
            url = item.get("url", "")
            if not url:
                continue
            if not url.startswith("http"):
                url = BASE_URL + url

            title = item.get("title", "")
            # Clean HTML tags from title
            title = re.sub(r"<[^>]+>", "", title).strip()

            content = item.get("content", "")
            content = re.sub(r"<[^>]+>", "", content).strip()

            date_str = item.get("cwrq", item.get("publishDate", ""))
            doc_num = ""
            gov_doc = item.get("govDoc", {})
            if isinstance(gov_doc, dict):
                doc_num = gov_doc.get("docNum", "")

            items.append({
                "title": title,
                "url": url,
                "content": content[:3000],
                "date": date_str,
                "doc_num": doc_num,
                "label": item.get("label", ""),
                "column": item.get("column", ""),
            })
        return items

    except Exception as e:
        log.warning("API call failed for page %d: %s", page, e)
        return []


def fetch(output_dir: str, max_total: int = 2000) -> list[dict]:
    """Fetch from ChinaTax FGK search API."""
    results = []
    now = datetime.now(timezone.utc).isoformat()
    seen_urls = set()

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        # Get anti-bot cookie first
        cookies = _get_cookie(client)
        time.sleep(2)

        for config in SEARCH_CONFIGS:
            label = config["label"]
            max_pages = config["max_pages"]
            section_count = 0

            # Refresh cookie at start of each label
            cookies = _get_cookie(client)
            time.sleep(1)

            log.info("Searching label='%s' (max %d pages)", label, max_pages)

            for page in range(max_pages):
                if len(results) >= max_total:
                    log.info("Reached max_total=%d, stopping", max_total)
                    break

                # Refresh cookie every 3 pages to avoid anti-bot expiry
                if page > 0 and page % 3 == 0:
                    time.sleep(2)
                    cookies = _get_cookie(client)
                    time.sleep(1)

                time.sleep(2)  # Polite delay
                items = _search_page(client, label, page, cookies)

                # If failed (cookie expired), refresh and retry once
                if not items:
                    cookies = _get_cookie(client)
                    time.sleep(1)
                    items = _search_page(client, label, page, cookies)

                if not items:
                    log.info("Label '%s' page %d returned 0 items, stopping", label, page)
                    break

                new_count = 0
                for item in items:
                    if item["url"] in seen_urls:
                        continue
                    seen_urls.add(item["url"])
                    new_count += 1

                    results.append({
                        "id": _make_id(item["url"]),
                        "title": item["title"],
                        "url": item["url"],
                        "content": item["content"],
                        "source": "chinatax_fgk_api",
                        "type": f"policy/{config['name']}",
                        "date": item["date"],
                        "doc_num": item.get("doc_num", ""),
                        "crawled_at": now,
                    })
                    section_count += 1

                log.info("Label '%s' page %d: %d items (%d new), total %d",
                         label, page, len(items), new_count, len(results))

            log.info("Label '%s' complete: %d items", label, section_count)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "chinatax_api.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch ChinaTax FGK via search API")
    parser.add_argument("--output", default="./out", help="Output directory")
    parser.add_argument("--max-total", type=int, default=2000, help="Max total items to fetch")
    args = parser.parse_args()
    fetch(args.output, max_total=args.max_total)
