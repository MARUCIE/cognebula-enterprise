"""Fetcher: National Database of Laws and Regulations (国家法律法规数据库).

Source: https://flk.npc.gov.cn
Content: Constitutional laws, administrative regulations, department rules, local regulations
Volume: 17,000+ documents
Priority: P0 CRITICAL (蜂群审计 Tier 1)

API: POST https://flk.npc.gov.cn/api/ with search parameters
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

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fetch_flk_npc")

BASE_URL = "https://flk.npc.gov.cn"
SEARCH_API = f"{BASE_URL}/api/"

# Law categories to crawl
CATEGORIES = [
    {"name": "tax_law", "type": "flfg", "keywords": ["税", "税收", "增值税", "所得税", "消费税"]},
    {"name": "admin_regulation", "type": "xzfg", "keywords": ["税", "财政", "会计"]},
    {"name": "dept_rule", "type": "bmgz", "keywords": ["税务", "财政部", "会计"]},
    {"name": "judicial_interp", "type": "sfjs", "keywords": ["税", "逃税", "偷税"]},
]


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _search(client: httpx.Client, law_type: str, keyword: str, page: int = 1, size: int = 10) -> dict:
    """Search the NPC law database API."""
    payload = {
        "type": law_type,
        "searchType": "title;vague",
        "sortTr": "f_bbrq_s;desc",
        "gbrqStart": "",
        "gbrqEnd": "",
        "sxrqStart": "",
        "sxrqEnd": "",
        "sort": "true",
        "page": str(page),
        "size": str(size),
        "q": keyword,
    }
    try:
        resp = client.post(
            SEARCH_API,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
                "Referer": f"{BASE_URL}/",
                "Origin": BASE_URL,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        log.warning("Search failed for '%s' page %d: %s", keyword, page, e)
    return {}


def _fetch_detail(client: httpx.Client, detail_url: str) -> str:
    """Fetch full text of a law document."""
    try:
        resp = client.get(
            detail_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
                "Referer": f"{BASE_URL}/",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            html = resp.text
            # Extract main content
            for pattern in [
                r'<div[^>]*class="law-content"[^>]*>(.*?)</div>',
                r'<div[^>]*id="law_content"[^>]*>(.*?)</div>',
                r'<div[^>]*class="content"[^>]*>(.*?)</div>',
            ]:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    content = re.sub(r'<[^>]+>', '', match.group(1))
                    content = re.sub(r'\s+', ' ', content).strip()
                    if len(content) >= 50:
                        return content[:10000]
    except Exception:
        pass
    return ""


def fetch(output_dir: str, max_total: int = 5000, fetch_content: bool = False) -> list[dict]:
    """Fetch from NPC National Law Database."""
    results = []
    now = datetime.now(timezone.utc).isoformat()
    seen_ids = set()

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for cat in CATEGORIES:
            for keyword in cat["keywords"]:
                if len(results) >= max_total:
                    break

                log.info("Searching type='%s' keyword='%s'", cat["type"], keyword)

                for page in range(1, 51):  # up to 50 pages
                    if len(results) >= max_total:
                        break

                    time.sleep(3)  # polite delay
                    data = _search(client, cat["type"], keyword, page)

                    items = data.get("result", {}).get("data", [])
                    if not items:
                        break

                    for item in items:
                        title = item.get("title", "")
                        # Clean HTML from title
                        title = re.sub(r'<[^>]+>', '', title).strip()

                        url = item.get("url", "")
                        if not url:
                            detail_id = item.get("id", "")
                            if detail_id:
                                url = f"{BASE_URL}/detail2.html?ZmY4MDgwODE2ZjEz#{detail_id}"

                        doc_id = _make_id(url or title)
                        if doc_id in seen_ids:
                            continue
                        seen_ids.add(doc_id)

                        content = item.get("body", "")
                        if content:
                            content = re.sub(r'<[^>]+>', '', content).strip()[:5000]

                        # Optionally fetch full text
                        if fetch_content and url and len(content) < 200:
                            time.sleep(2)
                            full = _fetch_detail(client, url)
                            if full:
                                content = full

                        results.append({
                            "id": doc_id,
                            "title": title,
                            "url": url,
                            "content": content,
                            "source": f"flk_npc/{cat['name']}",
                            "type": f"law/{cat['type']}",
                            "date": item.get("publish", ""),
                            "status": item.get("status", ""),
                            "issuing_body": item.get("office", ""),
                            "crawled_at": now,
                        })

                    total_count = data.get("result", {}).get("totalSizes", 0)
                    if page * 10 >= total_count:
                        break

                log.info("Keyword '%s' done: %d total results", keyword, len(results))

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "flk_npc.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch NPC National Law Database")
    parser.add_argument("--output", default="./out")
    parser.add_argument("--max-total", type=int, default=5000)
    parser.add_argument("--fetch-content", action="store_true")
    args = parser.parse_args()
    fetch(args.output, max_total=args.max_total, fetch_content=args.fetch_content)
