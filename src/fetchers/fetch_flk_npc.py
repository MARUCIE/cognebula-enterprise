"""Fetcher: National Database of Laws and Regulations (国家法律法规数据库).

Source: https://flk.npc.gov.cn
Content: Constitutional laws, administrative regulations, department rules, local regulations
Volume: 17,000+ documents
Priority: P0 CRITICAL (蜂群审计 Tier 1)

NOTE: flk.npc.gov.cn was rebuilt as a Vue SPA in 2025. All /api/* paths now return
the SPA HTML shell. The real API calls are made internally by the JS app via XHR.
To crawl, use one of:
  1. Playwright: render the SPA, intercept network requests to find the real API
  2. fleet-page-fetch: VPS browser rendering proxy
  3. Alternative: use existing datasets (twang2218/law-datasets on GitHub)

The old GET/POST endpoints no longer work directly (405 or HTML returned).
Download base: https://wb.flk.npc.gov.cn (for PDF/WORD files, may still work)
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
LIST_API = f"{BASE_URL}/api/"
DETAIL_API = f"{BASE_URL}/api/detail"

# Law categories (type param for filtered queries)
CATEGORIES = [
    {"name": "law", "type": "flfg"},           # 法律法规
    {"name": "admin_reg", "type": "xzfg"},      # 行政法规
    {"name": "supervisory", "type": "jcfg"},    # 监察法规
    {"name": "judicial", "type": "sfjs"},        # 司法解释
    {"name": "local_reg", "type": "dfxfg"},      # 地方性法规
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
    "Referer": f"{BASE_URL}/",
}


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _list_page(client: httpx.Client, page: int = 1, size: int = 10) -> dict:
    """List all laws via GET API with pagination."""
    try:
        resp = client.get(
            LIST_API,
            params={"page": page, "size": size},
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") or data.get("code") == 200:
                return data
            log.warning("API returned code=%s", data.get("code"))
    except Exception as e:
        log.warning("List page %d failed: %s", page, e)
    return {}


def _fetch_detail(client: httpx.Client, doc_id: str) -> str:
    """Fetch full text via detail API."""
    try:
        resp = client.get(
            DETAIL_API,
            params={"id": doc_id},
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            body = data.get("result", {}).get("body", [])
            if body and isinstance(body, list):
                for item in body:
                    text = item.get("body", "") or item.get("content", "")
                    if text:
                        text = re.sub(r'<[^>]+>', '', text).strip()
                        if len(text) >= 50:
                            return text[:10000]
    except Exception:
        pass
    return ""


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
    """Fetch from NPC National Law Database via GET pagination API."""
    results = []
    now = datetime.now(timezone.utc).isoformat()
    seen_ids = set()
    page_size = 10

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for page in range(1, max_total // page_size + 2):
            if len(results) >= max_total:
                break

            time.sleep(3)  # polite delay
            data = _list_page(client, page, page_size)

            result = data.get("result", {})
            items = result.get("data", [])
            if not items:
                log.info("No more items at page %d", page)
                break

            for item in items:
                title = item.get("title", "")
                title = re.sub(r'<[^>]+>', '', title).strip()

                detail_id = item.get("id", "")
                url = item.get("url", "")
                if not url and detail_id:
                    url = f"{BASE_URL}/detail2.html?id={detail_id}"

                doc_id = _make_id(detail_id or url or title)
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)

                content = ""
                if fetch_content and detail_id:
                    time.sleep(2)
                    content = _fetch_detail(client, detail_id)

                law_type = item.get("type", "")
                cat_name = next(
                    (c["name"] for c in CATEGORIES if c["type"] == law_type),
                    "other"
                )

                results.append({
                    "id": doc_id,
                    "title": title,
                    "url": url,
                    "content": content,
                    "source": f"flk_npc/{cat_name}",
                    "type": f"law/{law_type}",
                    "date": item.get("publish", ""),
                    "status": item.get("status", ""),
                    "issuing_body": item.get("office", ""),
                    "crawled_at": now,
                })

            total_count = result.get("totalSizes", 0)
            log.info("Page %d: +%d items (total %d/%d)", page, len(items), len(results), total_count)
            if page * page_size >= total_count:
                break

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
