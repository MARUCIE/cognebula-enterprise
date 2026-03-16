#!/usr/bin/env python3
"""Crawl HS customs codes from hsbianma.com.

Strategy:
1. Search by 2-digit chapter code (01-97), paginate to collect all 10-digit codes
2. Optionally fetch detail pages for VAT rate + consumption tax rate
3. Derive 4-digit and 6-digit hierarchy from 10-digit codes
4. Save as JSON per chapter + merged full dataset

Output: data/raw/20260315-hs-codes/

Usage:
    python src/fetchers/fetch_hs_codes.py
    python src/fetchers/fetch_hs_codes.py --chapters 1-30
    python src/fetchers/fetch_hs_codes.py --skip-details
"""

import argparse
import json
import os
import re
import sys
import time
import random
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Install deps: pip install requests beautifulsoup4 lxml")
    sys.exit(1)


BASE_URL = "http://www.hsbianma.com"
SEARCH_URL = f"{BASE_URL}/Search"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "20260315-hs-codes"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

SEARCH_DELAY = 3.0
DETAIL_DELAY = 3.5
MAX_RETRIES = 3
CONNECT_TIMEOUT = 20
READ_TIMEOUT = 30
BACKOFF_DELAY = 30  # wait this long after repeated failures

SECTION_MAP = {}
for sec, chapters in {
    "I": range(1, 6), "II": range(6, 15), "III": [15],
    "IV": range(16, 25), "V": range(25, 28), "VI": range(28, 39),
    "VII": range(39, 41), "VIII": range(41, 44), "IX": range(44, 47),
    "X": range(47, 50), "XI": range(50, 64), "XII": range(64, 68),
    "XIII": range(68, 71), "XIV": [71], "XV": range(72, 84),
    "XVI": range(84, 86), "XVII": range(86, 90), "XVIII": range(90, 93),
    "XIX": [93], "XX": range(94, 97), "XXI": [97],
}.items():
    for ch in chapters:
        SECTION_MAP[f"{ch:02d}"] = sec


consecutive_failures = 0


def get_session():
    """Create a fresh session."""
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


session = get_session()


def fetch_with_retry(url, params=None, delay=SEARCH_DELAY):
    """Fetch URL with retries, backoff, and rate limiting."""
    global consecutive_failures, session

    jitter = random.uniform(0, delay * 0.3)
    time.sleep(delay + jitter)

    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, params=params, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                consecutive_failures = 0
                return resp.text
            elif resp.status_code == 429 or resp.status_code == 503:
                print(f"  WARN: Rate limited (HTTP {resp.status_code}), backing off {BACKOFF_DELAY}s...")
                time.sleep(BACKOFF_DELAY)
                session = get_session()  # fresh session
            else:
                print(f"  WARN: HTTP {resp.status_code} for {url}, retry {attempt+1}")
        except requests.exceptions.Timeout:
            consecutive_failures += 1
            print(f"  WARN: Timeout for {url}, retry {attempt+1} (consecutive: {consecutive_failures})")
            if consecutive_failures >= 3:
                print(f"  BACKOFF: {consecutive_failures} consecutive failures, waiting {BACKOFF_DELAY}s...")
                time.sleep(BACKOFF_DELAY)
                session = get_session()
                consecutive_failures = 0
        except requests.exceptions.ConnectionError:
            consecutive_failures += 1
            print(f"  WARN: Connection error, retry {attempt+1} (consecutive: {consecutive_failures})")
            if consecutive_failures >= 3:
                print(f"  BACKOFF: Waiting {BACKOFF_DELAY}s and creating fresh session...")
                time.sleep(BACKOFF_DELAY)
                session = get_session()
                consecutive_failures = 0
        except Exception as e:
            print(f"  WARN: {e}, retry {attempt+1}")

        time.sleep(delay * (attempt + 1))

    print(f"  ERROR: Failed after {MAX_RETRIES} retries: {url}")
    return None


def parse_search_page(html):
    """Parse search result page, return list of code dicts + has_next_page."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for row in soup.select("tr.result-grid"):
        tds = row.find_all("td")
        if len(tds) < 7:
            continue

        code_text = tds[0].get_text(strip=True).replace(" ", "").replace(".", "")
        code_text = re.sub(r'\[过期\]', '', code_text).strip()
        code = re.sub(r'[^\d]', '', code_text)
        if not code or len(code) < 4:
            continue

        name = tds[1].get_text(strip=True)
        unit = tds[2].get_text(strip=True)
        export_refund = tds[3].get_text(strip=True)

        detail_link = tds[6].find("a")
        detail_href = detail_link["href"] if detail_link else ""

        results.append({
            "code": code,
            "name_cn": name,
            "unit": unit,
            "export_refund_rate": export_refund,
            "detail_url": detail_href,
        })

    pagination = soup.select_one("#pagination")
    has_next = False
    if pagination:
        next_link = pagination.find("a", string="下一页")
        if next_link:
            has_next = True

    return results, has_next


def parse_detail_page(html):
    """Parse detail page for VAT and consumption tax rates."""
    soup = BeautifulSoup(html, "html.parser")
    info = {}

    labels = soup.select("td.td-label")
    for label_td in labels:
        label = label_td.get_text(strip=True)
        value_td = label_td.find_next_sibling("td")
        if not value_td:
            continue
        value = value_td.get_text(strip=True)

        if label == "增值税率":
            info["vat_rate"] = value
        elif label == "消费税率":
            info["consumption_tax"] = value
        elif label == "最惠国税率":
            info["mfn_rate"] = value
        elif label == "进口普通税率":
            info["general_import_rate"] = value
        elif label == "出口税率":
            info["export_rate"] = value
        elif label == "出口退税税率":
            info["export_refund_rate"] = value
        elif label == "编码状态":
            info["status"] = value

    return info


def crawl_chapter(chapter_code, skip_details=False):
    """Crawl all codes for a 2-digit chapter."""
    all_codes = []
    page = 1

    while True:
        if page == 1:
            url = f"{BASE_URL}/search"
            params = {"keywords": chapter_code, "filterFailureCode": "true"}
        else:
            url = f"{SEARCH_URL}/{page}"
            params = {"keywords": chapter_code, "filterFailureCode": "true"}

        html = fetch_with_retry(url, params=params)
        if not html:
            # If we got nothing on page 1, this chapter failed
            if page == 1:
                return None  # signal failure
            break

        codes, has_next = parse_search_page(html)
        if not codes:
            break

        codes = [c for c in codes if c["code"].startswith(chapter_code)]
        all_codes.extend(codes)

        if not has_next:
            break
        page += 1

    # Fetch detail pages for VAT and consumption tax
    if not skip_details and all_codes:
        for i, code_info in enumerate(all_codes):
            detail_url = code_info.get("detail_url", "")
            if not detail_url:
                detail_url = f"/Code/{code_info['code']}.html"

            html = fetch_with_retry(f"{BASE_URL}{detail_url}", delay=DETAIL_DELAY)
            if html:
                detail = parse_detail_page(html)
                code_info.update(detail)

    return all_codes


def derive_hierarchy(codes_10digit):
    """Derive 2/4/6/8-digit hierarchy from 10-digit codes."""
    hierarchy = {}

    for item in codes_10digit:
        code = item["code"]
        if len(code) < 4:
            continue

        for lvl in [2, 4, 6, 8]:
            if lvl >= len(code):
                break
            prefix = code[:lvl]
            if prefix not in hierarchy:
                hierarchy[prefix] = {
                    "code": prefix,
                    "name_cn": "",
                    "level": lvl,
                    "parent_code": code[:lvl-2] if lvl > 2 else "",
                }

        hierarchy[code] = {
            "code": code,
            "name_cn": item.get("name_cn", ""),
            "level": len(code),
            "parent_code": code[:max(len(code)-2, 2)] if len(code) > 2 else "",
            "unit": item.get("unit", ""),
            "vat_rate": item.get("vat_rate", ""),
            "consumption_tax": item.get("consumption_tax", ""),
            "export_refund_rate": item.get("export_refund_rate", ""),
            "mfn_rate": item.get("mfn_rate", ""),
            "export_rate": item.get("export_rate", ""),
            "general_import_rate": item.get("general_import_rate", ""),
            "status": item.get("status", ""),
        }

    # Name intermediate nodes
    for code, info in sorted(hierarchy.items(), key=lambda x: (-len(x[0]), x[0])):
        if info["name_cn"]:
            continue
        children = [v for k, v in hierarchy.items()
                    if k.startswith(code) and len(k) == len(code) + 2 and v["name_cn"]]
        if children:
            info["name_cn"] = f"{code[:2]}章-{code}类"

    return hierarchy


def main():
    parser = argparse.ArgumentParser(description="Crawl HS codes from hsbianma.com")
    parser.add_argument("--chapters", default="1-97",
                       help="Chapter range, e.g., '1-30' or '1,5,10'")
    parser.add_argument("--skip-details", action="store_true",
                       help="Skip detail page fetching (search results only)")
    parser.add_argument("--output", default=str(OUTPUT_DIR),
                       help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    chapters = []
    for part in args.chapters.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            chapters.extend(range(int(start), int(end) + 1))
        else:
            chapters.append(int(part))

    chapters = [c for c in chapters if c != 77]

    print(f"Crawling {len(chapters)} chapters: {chapters[0]:02d}-{chapters[-1]:02d}")
    print(f"Output: {output_dir}")
    print(f"Skip details: {args.skip_details}")

    all_results = []
    total_codes = 0
    failed_chapters = []

    for idx, ch_num in enumerate(chapters):
        chapter_code = f"{ch_num:02d}"

        chapter_file = output_dir / f"chapter-{chapter_code}.json"
        if chapter_file.exists():
            with open(chapter_file) as f:
                cached = json.load(f)
            print(f"[{idx+1}/{len(chapters)}] Chapter {chapter_code}: CACHED ({len(cached)} codes)")
            all_results.extend(cached)
            total_codes += len(cached)
            continue

        codes = crawl_chapter(chapter_code, skip_details=args.skip_details)

        if codes is None:
            # Failed to get any results - rate limited
            print(f"[{idx+1}/{len(chapters)}] Chapter {chapter_code}: FAILED (rate limited?)")
            failed_chapters.append(chapter_code)
            print(f"  Backing off {BACKOFF_DELAY}s before next chapter...")
            time.sleep(BACKOFF_DELAY)
            continue

        total_codes += len(codes)

        with open(chapter_file, "w", encoding="utf-8") as f:
            json.dump(codes, f, ensure_ascii=False, indent=2)
        print(f"[{idx+1}/{len(chapters)}] Chapter {chapter_code}: {len(codes)} codes saved")

        all_results.extend(codes)

    # Retry failed chapters once
    if failed_chapters:
        print(f"\n=== Retrying {len(failed_chapters)} failed chapters after {BACKOFF_DELAY*2}s backoff ===")
        time.sleep(BACKOFF_DELAY * 2)
        global session
        session = get_session()

        for chapter_code in failed_chapters:
            chapter_file = output_dir / f"chapter-{chapter_code}.json"
            if chapter_file.exists():
                continue

            codes = crawl_chapter(chapter_code, skip_details=args.skip_details)
            if codes is None or not codes:
                print(f"  Chapter {chapter_code}: STILL FAILED")
                continue

            total_codes += len(codes)
            with open(chapter_file, "w", encoding="utf-8") as f:
                json.dump(codes, f, ensure_ascii=False, indent=2)
            print(f"  Chapter {chapter_code}: {len(codes)} codes saved (retry)")
            all_results.extend(codes)

    # Derive hierarchy
    print(f"\n=== Deriving hierarchy from {total_codes} leaf codes ===")
    hierarchy = derive_hierarchy(all_results)

    level_counts = defaultdict(int)
    for info in hierarchy.values():
        level_counts[info["level"]] += 1
    for lvl in sorted(level_counts):
        print(f"  Level {lvl}: {level_counts[lvl]} codes")
    print(f"  TOTAL: {sum(level_counts.values())} codes")

    # Save outputs
    merged_file = output_dir / "hs-codes-all.json"
    with open(merged_file, "w", encoding="utf-8") as f:
        json.dump(list(hierarchy.values()), f, ensure_ascii=False, indent=2)
    print(f"Saved merged: {merged_file}")

    inject_file = output_dir / "hs-codes-for-inject.json"
    inject_data = []
    for code, info in sorted(hierarchy.items()):
        section = SECTION_MAP.get(code[:2], "")
        inject_data.append({
            "code": info["code"],
            "name_cn": info["name_cn"],
            "level": info["level"],
            "parent_code": info["parent_code"],
            "section": section,
            "vat_rate": info.get("vat_rate", ""),
            "consumption_tax": info.get("consumption_tax", ""),
            "export_refund_rate": info.get("export_refund_rate", ""),
        })
    with open(inject_file, "w", encoding="utf-8") as f:
        json.dump(inject_data, f, ensure_ascii=False, indent=2)
    print(f"Saved injection-ready: {inject_file} ({len(inject_data)} entries)")

    # Report final status
    chapter_files = list(output_dir.glob("chapter-*.json"))
    total_chapters_done = len(chapter_files)
    print(f"\nStatus: {total_chapters_done}/96 chapters completed")
    if failed_chapters:
        still_missing = [c for c in failed_chapters if not (output_dir / f"chapter-{c}.json").exists()]
        if still_missing:
            print(f"Missing chapters: {', '.join(still_missing)}")
            print("Re-run the script to retry these chapters.")


if __name__ == "__main__":
    main()
