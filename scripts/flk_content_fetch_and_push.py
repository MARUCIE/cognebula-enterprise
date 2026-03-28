#!/usr/bin/env python3
"""Phase A2: Fetch actual content text for items with has_content=true,
then push to KG via DDL API.

Reads: data/recrawl/flk_details.jsonl (items with has_content=true)
Uses: Playwright to call flfgDetails API (browser context needed for cookies)
Pushes: content to VPS KG via DDL MATCH...SET

Run from Mac:
    .venv/bin/python3 scripts/flk_content_fetch_and_push.py [--kg-host 100.88.170.57]
"""
import json
import logging
import os
import random
import re
import sys
import time
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("flk_content")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETAILS_FILE = os.path.join(BASE, "data", "recrawl", "flk_details.jsonl")
OUTPUT = os.path.join(BASE, "data", "recrawl", "flk_with_content.jsonl")

KG_HOST = "100.88.170.57"
for i, a in enumerate(sys.argv):
    if a == "--kg-host" and i + 1 < len(sys.argv):
        KG_HOST = sys.argv[i + 1]

JS_DETAIL = """(bbbs) => {
    return fetch('/law-search/search/flfgDetails?bbbs=' + encodeURIComponent(bbbs))
        .then(r => r.text()).catch(e => 'ERR:' + e.message);
}"""


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s).strip() if s else ""


def escape_cypher(s):
    if not s:
        return ""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")


def ddl(stmts):
    url = f"http://{KG_HOST}:8400/api/v1/admin/execute-ddl"
    body = json.dumps({"statements": stmts}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)[:200]}


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


def main():
    from playwright.sync_api import sync_playwright

    # Load items that have content
    items = []
    with open(DETAILS_FILE) as f:
        for line in f:
            try:
                d = json.loads(line)
                if d.get("has_content"):
                    items.append(d)
            except:
                pass

    done = load_done()
    pending = [d for d in items if d.get("bbbs", "") not in done]
    log.info("Items with content: %d | Done: %d | Pending: %d", len(items), len(done), len(pending))

    if not pending:
        log.info("Nothing to do!")
        return

    outf = open(OUTPUT, "a", buffering=1)
    fetched = 0
    pushed = 0
    errors = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(15000)

        for attempt in range(3):
            try:
                page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=20000)
                time.sleep(3)
                break
            except:
                time.sleep(5)

        calls = 0

        for i, item in enumerate(pending):
            bbbs = item.get("bbbs", "")
            if not bbbs:
                continue

            # Browser restart every 200 calls
            if calls >= 200:
                try:
                    browser.close()
                except:
                    pass
                time.sleep(random.uniform(2, 4))
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(15000)
                for attempt in range(3):
                    try:
                        page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=20000)
                        time.sleep(3)
                        break
                    except:
                        time.sleep(5)
                calls = 0

            try:
                raw = page.evaluate(JS_DETAIL, bbbs)
                calls += 1

                if not raw or raw.startswith("ERR:"):
                    errors += 1
                    continue

                d = json.loads(raw)
                if d.get("code") != 200:
                    errors += 1
                    continue

                data = d.get("data", {})
                content = strip_html(str(data.get("content", "") or ""))

                if len(content) < 50:
                    errors += 1
                    continue

                # Save locally
                record = {
                    "bbbs": bbbs,
                    "title": strip_html(data.get("title", "")),
                    "content": content[:50000],
                }
                outf.write(json.dumps(record, ensure_ascii=False) + "\n")
                fetched += 1

                # Push to KG: update the LawOrRegulation node's fullText
                node_id = f"FLK_{bbbs[:16]}"
                ec = escape_cypher(content[:5000])
                eid = escape_cypher(node_id)
                stmt = f"MATCH (n:LawOrRegulation {{id: '{eid}'}}) SET n.fullText = '{ec}'"
                result = ddl([stmt])
                if "error" not in result:
                    pushed += 1

            except Exception as e:
                errors += 1
                if errors <= 5:
                    log.warning("  %s: %s", bbbs[:12], str(e)[:60])
                try:
                    browser.close()
                except:
                    pass
                time.sleep(5)
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(15000)
                for attempt in range(3):
                    try:
                        page.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=20000)
                        time.sleep(3)
                        break
                    except:
                        time.sleep(5)
                calls = 0

            time.sleep(random.uniform(0.5, 1.5))

            if (i + 1) % 100 == 0:
                outf.flush()
                log.info("  %d/%d: fetched=%d pushed=%d errors=%d",
                         i + 1, len(pending), fetched, pushed, errors)

        browser.close()

    outf.close()
    log.info("=" * 50)
    log.info("DONE: fetched=%d pushed_to_kg=%d errors=%d", fetched, pushed, errors)
    log.info("=" * 50)


if __name__ == "__main__":
    main()
