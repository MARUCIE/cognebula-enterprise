#!/usr/bin/env python3
"""Phase 1: Fast API scan — get flfgDetails metadata for all 2901 items.

No page navigation, just fetch() calls. ~1s per item = ~50min total.
Saves: bbbs, title, ossFile paths, related docs, all API fields.

Phase 2 (separate script): only navigate to preview pages for items with ossFile.

Run: .venv/bin/python3 scripts/flk_fast_scan.py
"""
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("flk_scan")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_LEGACY = os.path.join(BASE, "data", "recrawl", "flk_npc_laws.jsonl")
INPUT = os.path.join(BASE, "data", "recrawl", "flk_all_ids.jsonl")
OUTPUT = os.path.join(BASE, "data", "recrawl", "flk_details.jsonl")
RESTART_EVERY = 200

JS_DETAIL = """(bbbs) => {
    return fetch('/law-search/search/flfgDetails?bbbs=' + encodeURIComponent(bbbs))
        .then(r => r.text()).catch(e => 'ERR:' + e.message);
}"""


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
    seen = set()
    items = []
    for path in [INPUT, INPUT_LEGACY]:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                try:
                    it = json.loads(line)
                    bbbs = it.get("bbbs", "")
                    if bbbs and bbbs not in seen:
                        items.append(it)
                        seen.add(bbbs)
                except Exception:
                    pass
    return items


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
    has_oss = 0
    errors = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        log.info("Loading main page...")
        for attempt in range(3):
            try:
                page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=20000)
                time.sleep(3)
                break
            except Exception:
                log.warning("  Init attempt %d failed", attempt + 1)
                time.sleep(5)

        calls = 0

        for i, item in enumerate(pending):
            bbbs = item.get("bbbs", "")
            if not bbbs:
                continue

            # Browser restart periodically
            if calls >= RESTART_EVERY:
                log.info("  Browser restart at %d/%d", i, len(pending))
                try:
                    browser.close()
                except:
                    pass
                time.sleep(random.uniform(2, 4))
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                for attempt in range(3):
                    try:
                        page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=20000)
                        time.sleep(3)
                        break
                    except Exception:
                        log.warning("  Init page attempt %d failed, retrying...", attempt + 1)
                        time.sleep(5)
                calls = 0

            try:
                page.set_default_timeout(15000)
                raw = page.evaluate(JS_DETAIL, bbbs)
                calls += 1

                if not raw or raw.startswith("ERR:"):
                    errors += 1
                    if errors <= 5:
                        log.warning("  ERR %s: %s", bbbs[:12], (raw or "null")[:60])
                    continue

                d = json.loads(raw)
                if d.get("code") != 200:
                    errors += 1
                    continue

                data = d.get("data", {})
                oss = data.get("ossFile") or {}
                oss_path = oss.get("ossWordOfdPath") or oss.get("ossWordPath") or ""

                record = {
                    "bbbs": bbbs,
                    "title": strip_html(data.get("title", item.get("title", ""))),
                    "flxz": data.get("flxz", item.get("flxz", "")),
                    "gbrq": data.get("gbrq", item.get("gbrq", "")),
                    "sxrq": data.get("sxrq", item.get("sxrq", "")),
                    "zdjgName": data.get("zdjgName", item.get("zdjgName", "")),
                    "sxx": data.get("sxx", item.get("sxx", 0)),
                    "xfFlag": data.get("xfFlag", ""),
                    "oss_word": oss.get("ossWordPath", ""),
                    "oss_ofd": oss.get("ossWordOfdPath", ""),
                    "oss_size": oss.get("ossWordOfdSize", 0),
                    "has_content": bool(data.get("content")),
                    "xgzl_count": len(data.get("xgzl") or []),
                    "xgwj_count": len(data.get("xgwj") or []),
                    "source": "flk_npc",
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }

                outf.write(json.dumps(record, ensure_ascii=False) + "\n")
                fetched += 1
                if oss_path:
                    has_oss += 1

            except Exception as e:
                errors += 1
                if errors <= 10:
                    log.warning("  Exception %s: %s", bbbs[:12], str(e)[:80])
                # Recovery
                try:
                    browser.close()
                except:
                    pass
                time.sleep(5)
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                for attempt in range(3):
                    try:
                        page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=20000)
                        time.sleep(3)
                        break
                    except Exception:
                        log.warning("  Recovery init attempt %d failed", attempt + 1)
                        time.sleep(5)
                calls = 0

            # Fast pace: 0.5-1.5s between API calls (no page navigation)
            time.sleep(random.uniform(0.5, 1.5))

            if (i + 1) % 100 == 0:
                outf.flush()
                log.info("  %d/%d: fetched=%d has_oss=%d errors=%d",
                         i + 1, len(pending), fetched, has_oss, errors)

        browser.close()

    outf.close()
    log.info("=" * 50)
    log.info("DONE: fetched=%d has_oss=%d errors=%d", fetched, has_oss, errors)
    log.info("Output: %s", OUTPUT)
    log.info("Next: run flk_preview_extract.py for items with oss_ofd")
    log.info("=" * 50)


if __name__ == "__main__":
    main()
