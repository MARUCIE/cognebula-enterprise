#!/usr/bin/env python3
"""Probe flk.npc.gov.cn for content API endpoints."""
import json
import time
from playwright.sync_api import sync_playwright

BBBS = "127e971ed95b44dd8ae375ab1aa8e531"

JS_FETCH = """(args) => {
    return fetch(args.path, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(args.params)
    }).then(r => r.text()).catch(e => 'ERR:' + e.message);
}"""

JS_GET = """(url) => {
    return fetch(url).then(r => r.text()).catch(e => 'ERR:' + e.message);
}"""

p = sync_playwright().start()
b = p.chromium.launch(headless=True, args=["--no-sandbox"])
pg = b.new_page()

# Set cookies by visiting main page (use domcontentloaded to avoid WAF networkidle hang)
print("Loading main page...")
pg.goto("https://flk.npc.gov.cn/fl.html", wait_until="domcontentloaded", timeout=60000)
time.sleep(8)  # Let WAF JS challenge complete
print(f"Main page body: {len(pg.inner_text('body'))} chars")

# POST endpoints to try
post_endpoints = [
    "/law-search/detail",
    "/law-search/search/detail",
    "/law-search/detail/content",
    "/law-search/search/content",
    "/law-search/index/detail",
    "/law-search/law/detail",
    "/law-search/search/getFlfg",
    "/law-search/search/info",
]

# GET endpoints to try
get_endpoints = [
    f"/law-search/detail?bbbs={BBBS}",
    f"/law-search/detail/{BBBS}",
    f"/law-search/content/{BBBS}",
    f"/api/detail?bbbs={BBBS}",
    f"/api/flfg/detail?bbbs={BBBS}",
]

print("=== POST endpoints ===")
for path in post_endpoints:
    try:
        raw = pg.evaluate(JS_FETCH, {"path": path, "params": {"bbbs": BBBS}})
        if raw and not raw.startswith("ERR:") and len(raw) > 20:
            print(f"HIT  {path}: {len(raw)} chars")
            print(f"     {raw[:200]}")
        else:
            short = (raw or "null")[:60]
            print(f"MISS {path}: {short}")
    except Exception as e:
        print(f"ERR  {path}: {str(e)[:80]}")
    time.sleep(0.5)

print("\n=== GET endpoints ===")
for url in get_endpoints:
    try:
        raw = pg.evaluate(JS_GET, url)
        if raw and not raw.startswith("ERR:") and len(raw) > 20 and "404" not in raw[:30]:
            print(f"HIT  {url}: {len(raw)} chars")
            print(f"     {raw[:200]}")
        else:
            short = (raw or "null")[:60]
            print(f"MISS {url}: {short}")
    except Exception as e:
        print(f"ERR  {url}: {str(e)[:80]}")
    time.sleep(0.5)

# Also try: load the detail page and capture XHR after waiting longer
print("\n=== Detail page with long wait ===")
api_calls = []
def on_response(resp):
    if resp.request.resource_type in ("xhr", "fetch"):
        api_calls.append({"url": resp.url, "status": resp.status})

pg.on("response", on_response)
pg.goto(f"https://flk.npc.gov.cn/detail2.html?ZmY={BBBS}", wait_until="domcontentloaded", timeout=60000)
time.sleep(10)

# Try scrolling to trigger lazy load
pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
time.sleep(3)

print(f"XHR/fetch calls captured: {len(api_calls)}")
for call in api_calls:
    print(f"  {call['status']} {call['url'][:120]}")

# Check page content after long wait
body = pg.inner_text("body")
print(f"\nBody after 11s: {len(body)} chars")
if len(body) > 600:
    print(f"Content found! Preview: {body[400:600]}")

b.close()
p.stop()
