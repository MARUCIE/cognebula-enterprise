#!/usr/bin/env python3
"""Probe flk detail page — find content loading mechanism."""
import json
import time
from playwright.sync_api import sync_playwright

BBBS = "127e971ed95b44dd8ae375ab1aa8e531"

p = sync_playwright().start()
b = p.chromium.launch(headless=True, args=["--no-sandbox"])
pg = b.new_page()

# Capture ALL network requests
all_requests = []
def on_request(req):
    all_requests.append({"method": req.method, "url": req.url, "type": req.resource_type})
pg.on("request", on_request)

# Load detail page
url = f"https://flk.npc.gov.cn/detail2.html?ZmY={BBBS}"
print(f"Loading: {url}")
pg.goto(url, wait_until="domcontentloaded", timeout=60000)
time.sleep(10)

print(f"\nAll requests ({len(all_requests)}):")
for r in all_requests:
    print(f"  {r['method']} {r['type']:10s} {r['url'][:120]}")

# Check page HTML source for API clues
html = pg.content()
print(f"\nPage HTML: {len(html)} chars")

# Search for API patterns in the JS bundles
import re
# Find loaded JS files
js_urls = [r["url"] for r in all_requests if r["url"].endswith(".js")]
print(f"\nJS bundles: {len(js_urls)}")
for js_url in js_urls[:5]:
    print(f"  {js_url}")

# Try to find the content loading code in page scripts
# Look for fetch/axios patterns in inline scripts
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"\nInline scripts: {len(scripts)}")
for i, s in enumerate(scripts):
    if len(s) > 20:
        print(f"  Script {i}: {len(s)} chars, preview: {s[:150]}")

# Try older URL format
print("\n=== Trying detail.html (v1) ===")
pg.goto(f"https://flk.npc.gov.cn/detail.html?ZmY={BBBS}", wait_until="domcontentloaded", timeout=60000)
time.sleep(8)
body2 = pg.inner_text("body")
print(f"Body: {len(body2)} chars")
if len(body2) > 600:
    print(f"Content: {body2[400:700]}")

# Try the search list API to get content field
print("\n=== Trying search/list with bbbs filter ===")
JS_FETCH = """(params) => {
    return fetch('/law-search/search/list', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(params)
    }).then(r => r.text()).catch(e => 'ERR:' + e.message);
}"""

params = {
    "searchRange": 1, "searchType": 0,
    "searchContent": "民族团结进步促进法",
    "page": 1, "size": 1,
}
raw = pg.evaluate(JS_FETCH, params)
if raw and not raw.startswith("ERR:"):
    d = json.loads(raw)
    if d.get("code") == 200:
        rows = d.get("rows", [])
        if rows:
            print(f"Found via search, fields:")
            for k, v in rows[0].items():
                print(f"  {k}: {str(v)[:100]}")

b.close()
p.stop()
