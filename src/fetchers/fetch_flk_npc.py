"""Fetcher: flk.npc.gov.cn (国家法律法规数据库) — JSON API.

Categories: flfg (法律), xzfg (行政法规), sfjs (司法解释), dfxfg (地方性法规), jcfg (监察法规)
API: GET https://flk.npc.gov.cn/api/?type=flfg&page=1&size=10
Detail: POST https://flk.npc.gov.cn/api/detail (form data: id=xxx)

Priority: P0 CRITICAL (蜂群审计 Tier 1, 17K+ docs)
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
log = logging.getLogger("fetch_flk")

BASE_URL = "https://flk.npc.gov.cn"
LIST_API = f"{BASE_URL}/api/"
DETAIL_API = f"{BASE_URL}/api/detail"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

CATEGORIES = {
    "flfg": "法律",
    "xzfg": "行政法规",
    "sfjs": "司法解释",
    "jcfg": "监察法规",
    "dfxfg": "地方性法规",
}

# Default: skip dfxfg (16K+) for initial crawl
DEFAULT_CATS = ["flfg", "xzfg", "sfjs"]


def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/index.html",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }


def _make_id(npc_id: str) -> str:
    return hashlib.sha256(f"flk:{npc_id}".encode()).hexdigest()[:16]


def _list_page(client: httpx.Client, category: str, page: int, size: int = 10) -> dict:
    """Fetch listing page from API."""
    try:
        time.sleep(3 + random.uniform(0, 2))
        import math
        resp = client.get(
            LIST_API,
            params={"type": category, "searchType": "title;vague",
                    "sortTr": "f_bbrq_s;desc",
                    "page": page, "size": size,
                    "_": int(time.time() * 1000)},
            headers=_headers(), timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") or data.get("code") == 200:
                return data.get("result", {})
            log.warning("API response: code=%s success=%s", data.get("code"), data.get("success"))
    except Exception as e:
        log.warning("List page %d failed: %s", page, e)
    return {}


def _fetch_detail(client: httpx.Client, doc_id: str) -> str:
    """Fetch full text via POST detail API."""
    try:
        time.sleep(3 + random.uniform(0, 2))
        resp = client.post(
            DETAIL_API,
            data={"id": doc_id},
            headers=_headers(),
            timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") or data.get("code") == 200:
                result = data.get("result", {})
                # Try multiple content fields
                body = result.get("body", "")
                if isinstance(body, list):
                    # body is array of sections
                    texts = []
                    for item in body:
                        t = item.get("body", "") or item.get("content", "") or item.get("text", "")
                        if t:
                            texts.append(re.sub(r'<[^>]+>', '', str(t)).strip())
                    full = "\n".join(texts)
                elif isinstance(body, str):
                    full = re.sub(r'<[^>]+>', '', body).strip()
                else:
                    full = ""

                if not full:
                    # Fallback to content/detail fields
                    for field in ["content", "detail", "fullText"]:
                        v = result.get(field, "")
                        if v and len(str(v)) > len(full):
                            full = re.sub(r'<[^>]+>', '', str(v)).strip()

                return re.sub(r'\s+', '\n', full).strip()[:50000]
    except Exception as e:
        log.warning("Detail fetch failed for %s: %s", doc_id[:20], e)
    return ""


def fetch(
    output_dir: str,
    categories: list[str] | None = None,
    max_per_category: int = 1000,
    fetch_detail_flag: bool = True,
) -> list[dict]:
    """Crawl flk.npc.gov.cn by category."""
    cats = categories or DEFAULT_CATS
    results = []
    now = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for cat in cats:
            cat_name = CATEGORIES.get(cat, cat)
            log.info("=== Category: %s (%s) ===", cat_name, cat)

            # First page
            first = _list_page(client, cat, page=1, size=10)
            total = first.get("totalSizes", first.get("totalCount", 0))
            items = first.get("data", [])
            log.info("  Total: %d docs, first page: %d items", total, len(items))

            if not items:
                continue

            all_items = list(items)
            max_items = min(total, max_per_category)
            page_size = 10
            total_pages = (max_items + page_size - 1) // page_size

            for page in range(2, total_pages + 1):
                if len(all_items) >= max_items:
                    break
                page_data = _list_page(client, cat, page=page, size=page_size)
                page_items = page_data.get("data", [])
                if not page_items:
                    break
                all_items.extend(page_items)
                if page % 20 == 0:
                    log.info("  [%s] page %d/%d, %d items", cat, page, total_pages, len(all_items))

            log.info("  [%s] listed %d items", cat, len(all_items))

            # Fetch details
            cat_results = []
            for i, item in enumerate(all_items[:max_items]):
                doc_id = item.get("id", "")
                title = re.sub(r'<[^>]+>', '', item.get("title", "")).strip()
                if not doc_id or not title:
                    continue

                content = ""
                if fetch_detail_flag:
                    content = _fetch_detail(client, doc_id)

                cat_results.append({
                    "id": _make_id(doc_id),
                    "npc_id": doc_id,
                    "title": title,
                    "content": content,
                    "source": f"flk_{cat}",
                    "type": cat_name,
                    "office": item.get("office", ""),
                    "publish_date": item.get("publish", ""),
                    "status": item.get("status", ""),
                    "crawled_at": now,
                })

                if (i + 1) % 50 == 0:
                    with_content = sum(1 for r in cat_results if len(r.get("content", "")) >= 100)
                    log.info("  [%s] %d/%d fetched, %d with content",
                             cat, i + 1, min(len(all_items), max_items), with_content)

            results.extend(cat_results)
            with_content = sum(1 for r in cat_results if len(r.get("content", "")) >= 100)
            log.info("  [%s] done: %d items, %d with content (%.1f%%)",
                     cat, len(cat_results), with_content,
                     100 * with_content / max(len(cat_results), 1))

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "flk_npc.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    with_content = sum(1 for r in results if len(r.get("content", "")) >= 100)
    log.info("Quality: %d/%d have content >= 100 chars (%.1f%%)",
             with_content, len(results), 100 * with_content / max(len(results), 1))

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch 国家法律法规数据库 (flk.npc.gov.cn)")
    parser.add_argument("--output", default="./out")
    parser.add_argument("--categories", nargs="+", default=None, choices=list(CATEGORIES.keys()))
    parser.add_argument("--max-per-category", type=int, default=1000)
    parser.add_argument("--no-detail", action="store_true")
    args = parser.parse_args()
    fetch(args.output, categories=args.categories,
          max_per_category=args.max_per_category,
          fetch_detail_flag=not args.no_detail)
