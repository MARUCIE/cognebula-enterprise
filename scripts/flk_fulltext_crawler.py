#!/usr/bin/env python3
"""Crawl flk.npc.gov.cn law preview text via OFD reader.

Pipeline per item:
  1. flfgDetails?bbbs=X → ossFile.ossWordOfdPath
  2. previewLink?filePath=Y → public reader URL
  3. Navigate to reader → extract first-page text from DOM

Run from Mac (good .gov.cn connectivity):
    .venv/bin/python3 scripts/flk_fulltext_crawler.py
"""
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("flk_ft")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE, "data", "recrawl", "flk_npc_laws.jsonl")
OUTPUT = os.path.join(BASE, "data", "recrawl", "flk_fulltext.jsonl")
RESTART_EVERY = 60


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s).strip() if s else ""


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


def load_items():
    items = []
    with open(INPUT) as f:
        for line in f:
            try:
                items.append(json.loads(line))
            except:
                pass
    return items


JS_DETAIL = """(bbbs) => {
    return fetch('/law-search/search/flfgDetails?bbbs=' + encodeURIComponent(bbbs))
        .then(r => r.text()).catch(e => 'ERR:' + e.message);
}"""

JS_PREVIEW = """(filePath) => {
    return fetch('/law-search/amazonFile/previewLink?filePath=' + encodeURIComponent(filePath))
        .then(r => r.text()).catch(e => 'ERR:' + e.message);
}"""


def main():
    from playwright.sync_api import sync_playwright

    items = load_items()
    done = load_done()
    pending = [it for it in items if it.get("bbbs", "") not in done]
    log.info("Total: %d | Done: %d | Pending: %d", len(items), len(done), len(pending))

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
        time.sleep(5)

        calls_since_restart = 0

        for i, item in enumerate(pending):
            bbbs = item.get("bbbs", "")
            if not bbbs:
                continue

            # Browser restart
            if calls_since_restart >= RESTART_EVERY:
                log.info("  Restarting browser at %d/%d", i, len(pending))
                browser.close()
                time.sleep(random.uniform(3, 6))
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=60000)
                time.sleep(5)
                calls_since_restart = 0

            try:
                # Step 1: Get ossFile path
                raw = page.evaluate(JS_DETAIL, bbbs)
                calls_since_restart += 1
                if not raw or raw.startswith("ERR:"):
                    errors += 1
                    continue

                d = json.loads(raw)
                if d.get("code") != 200:
                    errors += 1
                    continue

                data = d.get("data", {})
                oss_file = data.get("ossFile") or {}
                # Prefer OFD, fallback to docx
                file_path = oss_file.get("ossWordOfdPath") or oss_file.get("ossWordPath") or ""

                content = ""
                if file_path:
                    # Step 2: Get preview URL
                    raw2 = page.evaluate(JS_PREVIEW, file_path)
                    calls_since_restart += 1
                    if raw2 and not raw2.startswith("ERR:"):
                        d2 = json.loads(raw2)
                        if d2.get("code") == 200:
                            preview_url = d2.get("data", {}).get("url", "")
                            if preview_url:
                                # Step 3: Load preview, extract text
                                page.goto(preview_url, wait_until="domcontentloaded", timeout=30000)
                                time.sleep(4)
                                # Scroll down once to trigger more text rendering
                                page.evaluate("window.scrollTo(0, 800)")
                                time.sleep(1)
                                content = page.inner_text("body").strip()
                                # Clean: remove reader UI noise
                                for noise in ["100%", "查找", "下载"]:
                                    content = content.replace(noise, "")
                                # Remove page numbers like "1/20"
                                content = re.sub(r'\d+/\d+\s*', '', content).strip()

                                # Return to main page for next API call
                                page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=30000)
                                time.sleep(2)
                                calls_since_restart += 1

                record = {
                    "bbbs": bbbs,
                    "title": strip_html(data.get("title", item.get("title", ""))),
                    "content": content[:50000],
                    "source": "flk_npc",
                    "url": f"https://flk.npc.gov.cn/detail2.html?ZmY={bbbs}",
                    "type": data.get("flxz", item.get("flxz", "")),
                    "gbrq": data.get("gbrq", item.get("gbrq", "")),
                    "sxrq": data.get("sxrq", item.get("sxrq", "")),
                    "zdjgName": data.get("zdjgName", item.get("zdjgName", "")),
                    "oss_path": file_path,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }

                outf.write(json.dumps(record, ensure_ascii=False) + "\n")
                fetched += 1
                if len(content) >= 100:
                    good += 1

                if fetched % 50 == 0:
                    outf.flush()
                    log.info("  %d/%d: fetched=%d good=%d errors=%d",
                             i + 1, len(pending), fetched, good, errors)

            except Exception as e:
                errors += 1
                if errors <= 10:
                    log.warning("  Exception %s: %s", bbbs[:12], str(e)[:80])
                # Try to recover
                try:
                    page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=30000)
                    time.sleep(3)
                    calls_since_restart += 1
                except:
                    browser.close()
                    time.sleep(5)
                    browser = pw.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=60000)
                    time.sleep(5)
                    calls_since_restart = 0

            time.sleep(random.uniform(2, 5))

        browser.close()

    outf.close()
    log.info("=" * 50)
    log.info("DONE: fetched=%d good_content=%d errors=%d", fetched, good, errors)
    log.info("Output: %s", OUTPUT)
    log.info("=" * 50)


if __name__ == "__main__":
    main()
