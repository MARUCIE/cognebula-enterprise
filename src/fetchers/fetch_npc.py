"""Fetcher: National Laws and Regulations Database (flk.npc.gov.cn).

The NPC database exposes a search API at /api/ that accepts POST requests.
We hit it with tax-related keywords to pull relevant laws and regulations.
"""

import argparse
import hashlib
import json
import logging
import os
import random
import time
from datetime import datetime, timezone

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fetch_npc")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

BASE_URL = "https://flk.npc.gov.cn"
# Discovered API endpoint: search interface used by the frontend
SEARCH_API = f"{BASE_URL}/api/law/search"

# Tax-related search queries
SEARCH_QUERIES = ["税收", "增值税", "企业所得税", "个人所得税", "税收征收管理"]


def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/index.html",
    }


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _search(client: httpx.Client, keyword: str) -> list[dict]:
    """Hit the NPC search API with a keyword."""
    items = []
    # The API payload structure (reverse-engineered from browser)
    payload = {
        "searchType": "title;vague",
        "sortType": "publish_date;desc",
        "params": keyword,
        "page": 1,
        "size": 10,
    }
    try:
        resp = client.post(SEARCH_API, headers=_headers(), json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # Response structure varies; common patterns:
            records = data.get("result", {}).get("data", []) if isinstance(data.get("result"), dict) else []
            if not records and isinstance(data.get("data"), list):
                records = data["data"]
            for rec in records:
                items.append({
                    "title": rec.get("title", ""),
                    "url": rec.get("url", f"{BASE_URL}/detail.html?id={rec.get('id', '')}"),
                    "date": rec.get("publish_date", rec.get("publishDate", "")),
                    "content": rec.get("body", rec.get("content", ""))[:3000],
                    "law_type": rec.get("type", ""),
                })
            log.info("Query '%s' returned %d results", keyword, len(items))
        else:
            log.warning("Query '%s' returned status %d", keyword, resp.status_code)
    except Exception as e:
        log.warning("Query '%s' failed: %s", keyword, e)
    return items


def fetch(output_dir: str, queries: list[str] | None = None) -> list[dict]:
    results = []
    now = datetime.now(timezone.utc).isoformat()
    seen_urls = set()

    if queries is None:
        queries = SEARCH_QUERIES

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for i, query in enumerate(queries):
            if i > 0:
                time.sleep(5)
            items = _search(client, query)
            for item in items:
                url = item["url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append({
                    "id": _make_id(url),
                    "title": item["title"],
                    "url": url,
                    "content": item.get("content", ""),
                    "source": "npc_flk",
                    "type": f"law/{item.get('law_type', 'unknown')}",
                    "date": item["date"],
                    "crawled_at": now,
                })

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "npc.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch NPC laws database")
    parser.add_argument("--output", default="./out", help="Output directory")
    parser.add_argument("--query", nargs="+", help="Custom search queries (default: tax-related)")
    args = parser.parse_args()
    fetch(args.output, queries=args.query)
