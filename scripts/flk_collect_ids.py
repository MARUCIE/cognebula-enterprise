#!/usr/bin/env python3
"""Collect all law bbbs IDs from flk.npc.gov.cn via search list API.

Strategy: Query each flfgCodeId separately (avoids 500-page/10K item API limit).
Uses Playwright browser context for WAF cookies.

API params (Ruoyi/PageHelper): pageNum, pageSize, flfgCodeId
API endpoint: POST /law-search/search/list

Output: data/recrawl/flk_all_ids.jsonl (appends, idempotent)
Run: .venv/bin/python3 scripts/flk_collect_ids.py [--limit 100]
"""
import json, logging, os, random, sys, time
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("flk_ids")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(BASE, "data", "recrawl", "flk_all_ids.jsonl")
PAGE_SIZE = 20
RESTART_EVERY = 250  # restart browser every N API calls

LIMIT = None
for i, a in enumerate(sys.argv):
    if a == "--limit" and i + 1 < len(sys.argv):
        LIMIT = int(sys.argv[i + 1])

JS_SEARCH_LIST = """(params) => {
    return fetch('/law-search/search/list', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(params)
    }).then(r => r.text()).catch(e => 'ERR:' + e.message);
}"""


def load_done():
    done = set()
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            for line in f:
                try:
                    done.add(json.loads(line).get("bbbs", ""))
                except Exception:
                    pass
    done.discard("")
    return done


def search_page(page, page_num, code_id=None, retries=3):
    params = {
        "searchRange": 1,
        "searchType": 0,
        "searchContent": "",
        "pageNum": page_num,
        "pageSize": PAGE_SIZE,
    }
    if code_id is not None:
        params["flfgCodeId"] = [code_id]

    for attempt in range(retries):
        try:
            raw = page.evaluate(JS_SEARCH_LIST, params)
            if not raw or raw.startswith("ERR:"):
                time.sleep(2)
                continue
            d = json.loads(raw)
            if d.get("code") == 200:
                return d
        except Exception:
            if attempt < retries - 1:
                time.sleep(2)
    return None


def restart_browser(pw, browser):
    """Close and relaunch browser with fresh WAF cookies."""
    try:
        browser.close()
    except Exception:
        pass
    time.sleep(random.uniform(2, 4))
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=60000)
    time.sleep(5)
    return browser, page


def discover_codes(page):
    """Probe flfgCodeId values 100-400 to find all valid codes."""
    codes = {}
    for code_id in range(100, 401, 5):
        d = search_page(page, 1, code_id)
        if d:
            total = d.get("total", 0)
            if total > 0:
                rows = d.get("rows", [])
                flxz = rows[0].get("flxz", "?") if rows else "?"
                codes[code_id] = {"total": total, "flxz": flxz}
        time.sleep(0.3)

    # Also try intermediate values around known codes
    known_codes = [110, 115, 120, 125, 130, 135, 140, 145, 150, 155, 160, 165,
                   170, 175, 180, 185, 190, 195, 200, 205, 210, 215, 220, 225,
                   230, 235, 240, 245, 250, 255, 260, 265, 270, 275, 280, 285,
                   290, 295, 300, 305, 310, 315, 320, 325, 330, 335, 340, 345, 350]
    for code_id in known_codes:
        if code_id not in codes:
            d = search_page(page, 1, code_id)
            if d:
                total = d.get("total", 0)
                if total > 0:
                    rows = d.get("rows", [])
                    flxz = rows[0].get("flxz", "?") if rows else "?"
                    codes[code_id] = {"total": total, "flxz": flxz}
            time.sleep(0.3)

    return codes


def collect_code(page, code_id, code_info, done, outf):
    """Paginate one flfgCodeId and collect all items."""
    total = code_info["total"]
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    collected = 0
    consecutive_fail = 0

    for page_num in range(1, total_pages + 2):  # +2 for safety
        d = search_page(page, page_num, code_id)

        if not d:
            consecutive_fail += 1
            if consecutive_fail >= 3:
                break
            continue

        rows = d.get("rows", [])
        if not rows:
            break

        consecutive_fail = 0
        for row in rows:
            bbbs = row.get("bbbs", "")
            if bbbs and bbbs not in done:
                record = {
                    "bbbs": bbbs,
                    "title": row.get("title", ""),
                    "flxz": row.get("flxz", ""),
                    "gbrq": row.get("gbrq", ""),
                    "sxrq": row.get("sxrq", ""),
                    "zdjgName": row.get("zdjgName", ""),
                    "flfgCodeId": row.get("flfgCodeId", ""),
                    "sxx": row.get("sxx", ""),
                    "source": "flk_npc",
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                }
                outf.write(json.dumps(record, ensure_ascii=False) + "\n")
                done.add(bbbs)
                collected += 1

        if len(rows) < PAGE_SIZE:
            break

        time.sleep(random.uniform(0.5, 1.0))

    return collected


def main():
    from playwright.sync_api import sync_playwright

    done = load_done()
    log.info("Already collected: %d IDs", len(done))

    outf = open(OUTPUT, "a", buffering=1)
    total_new = 0
    api_calls = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        bpage = browser.new_page()

        log.info("Loading main page (WAF cookies)...")
        bpage.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)
        log.info("Page loaded")

        # Phase 1: Discover all valid flfgCodeId values
        log.info("=== Phase 1: Discovering flfgCodeId values ===")
        codes = discover_codes(bpage)
        total_expected = sum(c["total"] for c in codes.values())
        log.info("Found %d valid codes, total expected: %d items", len(codes), total_expected)
        for cid in sorted(codes):
            log.info("  code=%d: %d items (%s)", cid, codes[cid]["total"], codes[cid]["flxz"])

        # Restart browser before collection phase
        browser, bpage = restart_browser(pw, browser)

        # Phase 2: Collect each code
        log.info("=== Phase 2: Collecting per flfgCodeId ===")
        for cid in sorted(codes, key=lambda x: codes[x]["total"], reverse=True):
            info = codes[cid]

            if LIMIT and total_new >= LIMIT:
                log.info("Global limit %d reached", LIMIT)
                break

            log.info("  code=%d (%s): %d expected...", cid, info["flxz"], info["total"])
            n = collect_code(bpage, cid, info, done, outf)
            total_new += n
            api_calls += info["total"] // PAGE_SIZE + 1
            log.info("  code=%d done: +%d new (total: %d)", cid, n, total_new)

            # Browser restart every RESTART_EVERY calls
            if api_calls >= RESTART_EVERY:
                log.info("  Restarting browser at %d API calls...", api_calls)
                browser, bpage = restart_browser(pw, browser)
                api_calls = 0

            outf.flush()

        browser.close()
    outf.close()

    log.info("=" * 60)
    log.info("DONE: +%d new IDs (cumulative %d)", total_new, len(done))
    log.info("Output: %s", OUTPUT)


if __name__ == "__main__":
    main()
