#!/usr/bin/env python3
"""Final probe: check HTML content + search API full response."""
import json
import re
import time
from playwright.sync_api import sync_playwright

BBBS = "127e971ed95b44dd8ae375ab1aa8e531"

p = sync_playwright().start()
b = p.chromium.launch(headless=True, args=["--no-sandbox"])
pg = b.new_page()

# Go to detail page
url = f"https://flk.npc.gov.cn/detail2.html?ZmY={BBBS}"
pg.goto(url, wait_until="domcontentloaded", timeout=60000)
time.sleep(5)

# Check raw HTML for content
html = pg.content()

# Look for content patterns in HTML
print("=== HTML Analysis ===")
print(f"Total HTML: {len(html)} chars")

# Search for law-related text in HTML
for pattern in ["第一条", "第一章", "总则", "民族团结"]:
    idx = html.find(pattern)
    if idx >= 0:
        print(f"FOUND '{pattern}' at pos {idx}: ...{html[max(0,idx-50):idx+100]}...")

# Check if there's embedded JSON data (common in SSR/SSG)
json_matches = re.findall(r'window\.__\w+__\s*=\s*(\{[^;]{100,})', html)
if json_matches:
    for i, m in enumerate(json_matches):
        print(f"\nEmbedded JSON {i}: {len(m)} chars, preview: {m[:200]}")

# Look for API URL patterns in JS
api_patterns = re.findall(r'["\'](/[a-z-]+/[a-z-]+/[a-z-]+)["\']', html)
unique_apis = sorted(set(api_patterns))
if unique_apis:
    print(f"\nAPI paths found in HTML: {unique_apis}")

# Now try: search API with full response examination
print("\n=== Search API Full Response ===")
JS_FETCH = """(params) => {
    return fetch('/law-search/search/list', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(params)
    }).then(r => r.text()).catch(e => 'ERR:' + e.message);
}"""

# Search for the specific law by title
params = {
    "searchRange": 1, "searchType": 0,
    "searchContent": "",
    "flfgCodeId": [110],
    "page": 1, "size": 1,
}
raw = pg.evaluate(JS_FETCH, params)
if raw and not raw.startswith("ERR:"):
    d = json.loads(raw)
    if d.get("code") == 200:
        rows = d.get("rows", [])
        if rows:
            print(f"Row has {len(rows[0])} fields:")
            for k, v in sorted(rows[0].items()):
                vs = str(v)
                print(f"  {k}: ({type(v).__name__}) {vs[:120]}")

# Try getting the detail by ZmY directly via page.evaluate with custom fetch
print("\n=== Try direct content fetch patterns ===")
for path in [
    f"/law-search/search/detail2?bbbs={BBBS}",
    f"/law-search/flfg/{BBBS}",
    f"/law-search/flfg/detail/{BBBS}",
    f"/law-search/flfg/content?bbbs={BBBS}",
]:
    js = f"""() => fetch('{path}').then(r => r.text()).catch(e => 'ERR:' + e.message)"""
    try:
        raw = pg.evaluate(js)
        if raw and not raw.startswith("ERR:") and "404" not in raw[:50]:
            print(f"HIT  {path}: {len(raw)} chars -> {raw[:150]}")
        else:
            print(f"miss {path}")
    except:
        print(f"err  {path}")

# Check if main JS bundle has API endpoints
print("\n=== Checking main JS bundle for API patterns ===")
js_url = "https://flk.npc.gov.cn/assets/index-B65rCxEa.js"
try:
    js_code = pg.evaluate(f"""() => fetch('{js_url}').then(r => r.text())""")
    # Find fetch/axios calls
    api_calls = re.findall(r'["\'](/law-search/[^"\']+)["\']', js_code)
    api_calls = sorted(set(api_calls))
    print(f"API endpoints in JS: {api_calls}")
except Exception as e:
    print(f"Could not fetch JS: {e}")

b.close()
p.stop()
