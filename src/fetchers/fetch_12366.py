"""Fetcher: 12366 Tax Hotline Q&A Archives (12366.chinatax.gov.cn).

The 12366 platform is China SAT's official tax consultation hotline.
Their Q&A knowledge base is published at https://12366.chinatax.gov.cn/sscx/rdzs
and exposes a POST JSON API at /sscx/rdzs03.

API discovery (2026-03-15):
  List endpoint: POST /sscx/rdzs03
    Body: bqtype, code (sort field), time, lb, sortrule, title, page, pageSize
    Response: {totalRow: 5297, pageCount: 106, cupage: N, data: [{BH, RDWTBT, LBMC, FBSJ, ...}]}
    pageSize up to 50 supported.

  Detail endpoint: POST /sscx/toDetail
    Body: {code: BH, gjz: ""}
    Response: {bean: {ZLTITLE, ZLCLJNR (HTML answer), ZLBFRQ, ZLFLAG, ZLTYPE, ...}}

Total records: ~5,300 hotspot QA pairs (as of 2026-03-15)
Categories: 问题解答->增值税->征税范围, 问题解答->企业所得税, etc.
"""

import argparse
import hashlib
import html
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fetch_12366")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

BASE_URL = "https://12366.chinatax.gov.cn"
LIST_API = f"{BASE_URL}/sscx/rdzs03"
DETAIL_API = f"{BASE_URL}/sscx/toDetail"

# Rate limit: 1 request per 3 seconds
REQUEST_DELAY = 3.0
PAGE_SIZE = 50  # Server supports up to 50


def _headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": f"{BASE_URL}/sscx/rdzs?more=1&bqtype=",
        "Origin": BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
    }


def _make_id(code: str) -> str:
    """Generate a deterministic short ID from the QA code."""
    return hashlib.sha256(code.encode()).hexdigest()[:16]


def _strip_html(raw: str) -> str:
    """Remove HTML tags, decode entities, normalize whitespace."""
    text = re.sub(r"<[^>]+>", "", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_list_page(client: httpx.Client, page: int,
                    bqtype: str = "", sort_field: str = "fbsj",
                    sort_order: str = "0") -> tuple[list[dict], int]:
    """Fetch one page of QA list from the rdzs03 API.

    Returns (items, total_count).
    sort_field: 'fbsj' (publish date) or 'djl' (click count)
    sort_order: '0' (desc) or '1' (asc)
    """
    form_data = {
        "bqtype": bqtype,
        "code": sort_field,
        "time": "",
        "lb": "",
        "sortrule": sort_order,
        "title": "",
        "page": str(page),
        "pageSize": str(PAGE_SIZE),
    }

    try:
        resp = client.post(
            LIST_API,
            data=form_data,
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code != 200:
            log.warning("List API returned %d for page %d", resp.status_code, page)
            return [], 0

        result = resp.json()
        total = int(result.get("totalRow", 0))
        items = result.get("data", [])
        return items, total

    except Exception as e:
        log.warning("List API failed for page %d: %s", page, e)
        return [], 0


def fetch_detail(client: httpx.Client, code: str) -> dict | None:
    """Fetch full QA detail from the toDetail API.

    Returns the bean dict with ZLTITLE, ZLCLJNR, etc.
    """
    try:
        resp = client.post(
            DETAIL_API,
            data={"code": code, "gjz": ""},
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code != 200:
            log.warning("Detail API returned %d for code %s", resp.status_code, code)
            return None

        result = resp.json()
        return result.get("bean")

    except Exception as e:
        log.warning("Detail API failed for code %s: %s", code, e)
        return None


def fetch(output_dir: str, max_pages: int = 0,
          fetch_details: bool = True) -> list[dict]:
    """Fetch 12366 hotspot QA archives.

    Args:
        output_dir: Directory to save JSON output.
        max_pages: Max pages to fetch (0 = all).
        fetch_details: Whether to fetch full answer content per item.
    """
    results = []
    now = datetime.now(timezone.utc).isoformat()
    seen_codes = set()

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        # First request to discover total count
        items, total = fetch_list_page(client, page=1)
        if not items:
            log.error("First page returned no items -- API may be down or blocked")
            return []

        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        if max_pages > 0:
            total_pages = min(total_pages, max_pages)

        log.info("Total records: %d, pages to fetch: %d (pageSize=%d)",
                 total, total_pages, PAGE_SIZE)

        # Process first page
        page_num = 1
        while True:
            if page_num > 1:
                time.sleep(REQUEST_DELAY)
                items, _ = fetch_list_page(client, page=page_num)

            if not items:
                log.info("Page %d returned no items, stopping", page_num)
                break

            new_on_page = 0
            for item in items:
                code = item.get("BH", "")
                if not code or code in seen_codes:
                    continue
                seen_codes.add(code)
                new_on_page += 1

                title = item.get("RDWTBT", "").strip()
                category = item.get("LBMC", "").strip()
                pub_date = item.get("FBSJ", "").strip()
                bqtype = item.get("BQTYPE", "").strip()

                # Build source URL
                source_url = f"{BASE_URL}/sscx/rddetail?bh={code}"

                record = {
                    "id": _make_id(code),
                    "code": code,
                    "title": title,
                    "question": title,  # Title IS the question for hotspot QA
                    "answer": "",
                    "answer_html": "",
                    "category": category,
                    "bqtype": bqtype,
                    "date": pub_date,
                    "source": "12366_hotspot",
                    "source_url": source_url,
                    "type": "qa/tax_hotline",
                    "crawled_at": now,
                }

                # Fetch full answer content if requested
                if fetch_details:
                    time.sleep(REQUEST_DELAY)
                    detail = fetch_detail(client, code)
                    if detail:
                        answer_html = detail.get("ZLCLJNR", "")
                        record["answer_html"] = answer_html
                        record["answer"] = _strip_html(answer_html)
                        # Prefer detail's title if available
                        if detail.get("ZLTITLE"):
                            record["title"] = detail["ZLTITLE"].strip()
                            record["question"] = record["title"]
                        if detail.get("ZLBFRQ") and detail["ZLBFRQ"] != "--":
                            record["date"] = detail["ZLBFRQ"].strip()

                results.append(record)

            log.info("Page %d/%d: %d items (%d new), %d total collected",
                     page_num, total_pages, len(items), new_on_page, len(results))

            if page_num >= total_pages:
                break
            page_num += 1

    # Conform to standard output schema (id, title, url, content, source, type, date, crawled_at)
    # while keeping extra fields for QA-specific data
    output_records = []
    for r in results:
        output_records.append({
            "id": r["id"],
            "title": r["title"],
            "url": r["source_url"],
            "content": f"Q: {r['question']}\nA: {r['answer']}" if r["answer"] else r["question"],
            "source": r["source"],
            "type": r["type"],
            "date": r["date"],
            "crawled_at": r["crawled_at"],
            # Extra QA-specific fields
            "question": r["question"],
            "answer": r["answer"],
            "answer_html": r["answer_html"],
            "category": r["category"],
            "bqtype": r["bqtype"],
            "code": r["code"],
        })

    if output_dir:
        date_str = datetime.now().strftime("%Y%m%d")
        subdir = os.path.join(output_dir, f"{date_str}-12366")
        os.makedirs(subdir, exist_ok=True)
        out_path = os.path.join(subdir, "12366_hotspot.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_records, f, ensure_ascii=False, indent=2)
        log.info("Saved %d QA items to %s", len(output_records), out_path)

    return output_records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch 12366 Tax Hotline QA Archives")
    parser.add_argument("--output", default="./out", help="Output directory")
    parser.add_argument("--max-pages", type=int, default=0,
                        help="Max pages to fetch (0 = all, ~106 pages at 50/page)")
    parser.add_argument("--no-details", action="store_true",
                        help="Skip fetching full answer content (faster, titles only)")
    parser.add_argument("--list-only", action="store_true",
                        help="Alias for --no-details")
    args = parser.parse_args()

    fetch_details = not (args.no_details or args.list_only)
    fetch(args.output, max_pages=args.max_pages, fetch_details=fetch_details)
