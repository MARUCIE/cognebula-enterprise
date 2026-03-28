#!/usr/bin/env python3
"""Extract law text from DOCX/OFD via flk reader. Optimized: skip flfgDetails.

Input: data/recrawl/flk_details.jsonl (items without has_content, have oss_word)
Output: data/recrawl/flk_fulltext_poe.jsonl

Run from Mac (.venv has Playwright):
    .venv/bin/python3 scripts/flk_docx_extract.py [--limit 100]
"""
import json, logging, os, random, re, sys, time
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("flk_extract")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE, "data", "recrawl", "flk_details.jsonl")
OUTPUT = os.path.join(BASE, "data", "recrawl", "flk_fulltext_poe.jsonl")
RESTART_EVERY = 40

LIMIT = None
for i, a in enumerate(sys.argv):
    if a == "--limit" and i + 1 < len(sys.argv):
        LIMIT = int(sys.argv[i + 1])

JS_PREVIEW = """(filePath) => {
    return fetch('/law-search/amazonFile/previewLink?filePath=' + encodeURIComponent(filePath))
        .then(r => r.text()).catch(e => 'ERR:' + e.message);
}"""


def load_done():
    done = set()
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            for line in f:
                try:
                    done.add(json.loads(line).get("bbbs", ""))
                except:
                    pass
    done.discard("")
    return done


def clean_text(s):
    if not s:
        return ""
    for noise in ["100%", "查找", "下载", "页码", "跳转"]:
        s = s.replace(noise, "")
    s = re.sub(r'\d+/\d+\s*', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def main():
    from playwright.sync_api import sync_playwright

    # Load items without API content
    with open(INPUT) as f:
        all_items = [json.loads(l) for l in f if l.strip()]
    pending = [d for d in all_items if not d.get("has_content") and d.get("oss_word")]

    done = load_done()
    pending = [d for d in pending if d.get("bbbs") not in done]

    if LIMIT:
        pending = pending[:LIMIT]

    log.info("Total: %d | Done: %d | Pending: %d", len(all_items), len(done), len(pending))
    if not pending:
        log.info("Nothing to do!")
        return

    outf = open(OUTPUT, "a", buffering=1)
    fetched = 0
    good = 0
    errors = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        log.info("Loading main page for cookies...")
        page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        calls = 0

        for i, item in enumerate(pending):
            bbbs = item.get("bbbs", "")
            oss_word = item.get("oss_word", "")
            if not bbbs or not oss_word:
                continue

            # Browser restart periodically
            if calls >= RESTART_EVERY:
                log.info("  Restarting browser at %d/%d", i, len(pending))
                browser.close()
                time.sleep(random.uniform(2, 4))
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=60000)
                time.sleep(3)
                calls = 0

            try:
                # Step 1: Get preview URL (HTTP via browser fetch)
                raw = page.evaluate(JS_PREVIEW, oss_word)
                calls += 1

                if not raw or raw.startswith("ERR:"):
                    errors += 1
                    continue

                d = json.loads(raw)
                if d.get("code") != 200:
                    errors += 1
                    continue

                preview_url = d.get("data", {}).get("url", "")
                if not preview_url:
                    errors += 1
                    continue

                # Step 2: Navigate to reader, extract text
                page.goto(preview_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(4)

                # Scroll to load more content
                for scroll_y in [800, 1600, 2400]:
                    page.evaluate(f"window.scrollTo(0, {scroll_y})")
                    time.sleep(0.5)

                content = clean_text(page.inner_text("body"))

                # Return to main page
                page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=30000)
                time.sleep(1)
                calls += 1

                record = {
                    "bbbs": bbbs,
                    "title": item.get("title", ""),
                    "content": content[:50000],
                    "source": "flk_npc",
                    "type": item.get("flxz", ""),
                    "gbrq": item.get("gbrq", ""),
                    "sxrq": item.get("sxrq", ""),
                    "zdjgName": item.get("zdjgName", ""),
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }
                outf.write(json.dumps(record, ensure_ascii=False) + "\n")
                fetched += 1
                if len(content) >= 200:
                    good += 1

                if fetched % 20 == 0:
                    outf.flush()
                    log.info("  %d/%d: fetched=%d good=%d err=%d", i + 1, len(pending), fetched, good, errors)

            except Exception as e:
                errors += 1
                if errors <= 5:
                    log.warning("  Error %s: %s", bbbs[:12], str(e)[:80])
                try:
                    page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=30000)
                    time.sleep(2)
                    calls += 1
                except:
                    browser.close()
                    time.sleep(3)
                    browser = pw.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=60000)
                    time.sleep(3)
                    calls = 0

            time.sleep(random.uniform(1, 2))

        browser.close()
    outf.close()

    log.info("DONE: fetched=%d good=%d errors=%d", fetched, good, errors)


if __name__ == "__main__":
    main()
