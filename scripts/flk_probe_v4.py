#!/usr/bin/env python3
"""Probe flk: check Vue state, try all JS chunks, try Jina Reader fallback."""
import json
import re
import time
from playwright.sync_api import sync_playwright

BBBS = "127e971ed95b44dd8ae375ab1aa8e531"

p = sync_playwright().start()
b = p.chromium.launch(headless=True, args=["--no-sandbox"])
pg = b.new_page()

# Load and wait long
url = f"https://flk.npc.gov.cn/detail2.html?ZmY={BBBS}"
pg.goto(url, wait_until="domcontentloaded", timeout=60000)
time.sleep(8)

# 1. Check Vue devtools / app state
print("=== Vue State ===")
for expr in [
    "document.querySelector('#app').__vue_app__?.config?.globalProperties",
    "window.__INITIAL_STATE__",
    "window.__NUXT__",
    "window.__pinia__",
    "JSON.stringify(Object.keys(window).filter(k => k.startsWith('__')))",
]:
    try:
        val = pg.evaluate(f"() => {{ try {{ return {expr} }} catch(e) {{ return 'ERR:' + e.message }} }}")
        if val and val != "ERR:undefined" and str(val) != "null":
            print(f"  {expr[:50]}: {str(val)[:200]}")
    except:
        pass

# 2. Get all JS chunk URLs from HTML
html = pg.content()
js_chunks = re.findall(r'src="(/assets/[^"]+\.js)"', html)
print(f"\n=== JS Chunks ({len(js_chunks)}) ===")
for chunk in js_chunks:
    print(f"  {chunk}")

# 3. Search ALL JS chunks for API patterns
print("\n=== API patterns in JS ===")
for chunk in js_chunks:
    try:
        code = pg.evaluate(f"""() => fetch('{chunk}').then(r => r.text())""")
        # Find API patterns
        apis = re.findall(r'["\'](/law-search/[^"\']+)["\']', code)
        if apis:
            print(f"  {chunk}:")
            for a in sorted(set(apis)):
                print(f"    {a}")
        # Also look for fetch/axios with dynamic paths
        fetches = re.findall(r'(?:fetch|post|get|axios)\s*\(\s*[`"\']([^`"\']+)', code, re.I)
        if fetches:
            for f in sorted(set(fetches)):
                if "law" in f.lower() or "detail" in f.lower() or "content" in f.lower():
                    print(f"    DYNAMIC: {f}")
    except:
        pass

# 4. DOM structure
print("\n=== DOM structure ===")
dom_info = pg.evaluate("""() => {
    const app = document.querySelector('#app');
    if (!app) return 'no #app';
    const children = Array.from(app.children).map(c => `${c.tagName}.${c.className.slice(0,50)} (${c.innerHTML.length})`);
    return children.join('\\n');
}""")
print(dom_info)

# 5. Try Jina Reader as fallback
print("\n=== Jina Reader fallback ===")
jina_url = f"https://r.jina.ai/https://flk.npc.gov.cn/detail2.html?ZmY={BBBS}"
try:
    resp = pg.evaluate(f"""() => fetch('{jina_url}', {{headers: {{'Accept': 'text/plain'}}}}).then(r => r.text()).catch(e => 'ERR:'+e.message)""")
    if resp and not resp.startswith("ERR:"):
        print(f"Jina response: {len(resp)} chars")
        print(resp[:500])
    else:
        print(f"Jina failed: {resp[:100] if resp else 'null'}")
except Exception as e:
    print(f"Jina error: {e}")

b.close()
p.stop()
