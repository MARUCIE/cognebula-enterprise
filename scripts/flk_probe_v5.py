#!/usr/bin/env python3
"""Test flfgDetails API endpoint for full text."""
import json
import time
from playwright.sync_api import sync_playwright

BBBS = "127e971ed95b44dd8ae375ab1aa8e531"

p = sync_playwright().start()
b = p.chromium.launch(headless=True, args=["--no-sandbox"])
pg = b.new_page()

pg.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=60000)
time.sleep(5)

# Try flfgDetails with bbbs
JS = """(params) => {
    return fetch('/law-search/search/flfgDetails', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(params)
    }).then(r => r.text()).catch(e => 'ERR:' + e.message);
}"""

# Try various param formats
for params in [
    {"bbbs": BBBS},
    {"ZmY": BBBS},
    {"id": BBBS},
    {"bbbs": BBBS, "searchContent": ""},
]:
    raw = pg.evaluate(JS, params)
    if raw and not raw.startswith("ERR:"):
        print(f"Params: {params}")
        d = json.loads(raw)
        if d.get("code") == 200:
            data = d.get("data", d.get("result", d))
            if isinstance(data, dict):
                print(f"  Fields: {list(data.keys())}")
                for k, v in data.items():
                    vs = str(v)
                    if len(vs) > 200:
                        print(f"  {k}: {len(vs)} chars -> {vs[:150]}...")
                    else:
                        print(f"  {k}: {vs}")
            else:
                print(f"  Data type: {type(data).__name__}, preview: {str(data)[:300]}")
        else:
            print(f"  Response: {raw[:200]}")
        break
    else:
        print(f"  {params}: {raw[:100] if raw else 'null'}")

# Also try xgzlDetails and xgwjDetails
for endpoint in ["/law-search/search/xgzlDetails", "/law-search/search/xgwjDetails"]:
    JS2 = f"""(params) => {{
        return fetch('{endpoint}', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(params)
        }}).then(r => r.text()).catch(e => 'ERR:' + e.message);
    }}"""
    raw = pg.evaluate(JS2, {"bbbs": BBBS})
    if raw and not raw.startswith("ERR:") and len(raw) > 50:
        print(f"\n{endpoint}: {raw[:200]}")

b.close()
p.stop()
