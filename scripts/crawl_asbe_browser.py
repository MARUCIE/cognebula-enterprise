#!/usr/bin/env python3
"""Crawl ASBE (Chinese Accounting Standards) via Playwright browser automation.

MOF CDN blocks VPS IPs — must run on local Mac with real browser.
Uses Playwright headless Chrome to bypass CDN/WAF restrictions.

Source: https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/
Target: 42 enterprise accounting standards (基本准则 + CAS 1-42) full text

Run on Mac:
    python3 scripts/crawl_asbe_browser.py
Then SCP result to VPS:
    scp data/asbe/asbe_browser.json kg-node:/home/kg/cognebula-enterprise/data/asbe/
"""
import json
import logging
import os
import re
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("asbe_browser")

BASE_URL = "https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "asbe")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "asbe_browser.json")


def main():
    from playwright.sync_api import sync_playwright

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    standards = []
    seen_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = context.new_page()

        # --- Phase 1: Collect all standard links from paginated listing ---
        log.info("Phase 1: Collecting standard links...")
        listing_pages = [BASE_URL] + [f"{BASE_URL}index_{i}.htm" for i in range(1, 10)]

        for lp_url in listing_pages:
            try:
                page.goto(lp_url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(1)

                links = page.query_selector_all("a")
                page_count = 0
                for link in links:
                    try:
                        title = (link.inner_text() or "").strip()
                        href = link.get_attribute("href") or ""
                        if not title or len(title) < 5 or "准则" not in title:
                            continue

                        # Resolve URL
                        if href.startswith("./"):
                            full_url = BASE_URL + href[2:]
                        elif href.startswith("http"):
                            full_url = href
                        elif href.startswith("/"):
                            full_url = "https://kjs.mof.gov.cn" + href
                        else:
                            full_url = BASE_URL + href

                        if full_url in seen_urls:
                            continue
                        seen_urls.add(full_url)

                        cas_match = re.search(r'第(\d+)号', title)
                        cas_num = int(cas_match.group(1)) if cas_match else 0

                        standards.append({
                            "title": title,
                            "url": full_url,
                            "cas_number": cas_num,
                            "content": "",
                        })
                        page_count += 1
                    except Exception:
                        continue

                log.info("  %s: +%d standards", lp_url.split("/")[-1] or "index", page_count)
                if page_count == 0:
                    break

            except Exception as e:
                log.warning("  Listing page failed: %s — %s", lp_url, e)
                break

        # Deduplicate and sort
        standards.sort(key=lambda x: x["cas_number"])
        log.info("Total standard links: %d", len(standards))

        # --- Phase 2: Fetch full text for each standard ---
        log.info("\nPhase 2: Fetching full text...")
        for i, std in enumerate(standards):
            try:
                page.goto(std["url"], wait_until="domcontentloaded", timeout=20000)
                time.sleep(2)
                # Wait for potential iframe/AJAX content
                page.wait_for_timeout(1000)

                # Try multiple content extraction strategies
                content = ""

                # Strategy 1: TRS_Editor (MOF standard layout)
                el = page.query_selector("div.TRS_Editor")
                if el:
                    content = el.inner_text() or ""

                # Strategy 2: Common content divs
                if len(content) < 200:
                    for sel in ["div#zoom", "div.article-content", "div.content", "div.text",
                                "div.Custom_UnionStyle", "div.TRS_PreAppend"]:
                        el = page.query_selector(sel)
                        if el:
                            txt = el.inner_text() or ""
                            if len(txt) > len(content):
                                content = txt

                # Strategy 3: Check iframes
                if len(content) < 200:
                    iframes = page.query_selector_all("iframe")
                    for iframe in iframes:
                        try:
                            frame = iframe.content_frame()
                            if frame:
                                txt = frame.query_selector("body").inner_text() or ""
                                if len(txt) > len(content):
                                    content = txt
                        except Exception:
                            continue

                # Strategy 4: Largest text block as fallback
                if len(content) < 200:
                    all_divs = page.query_selector_all("div")
                    for div in all_divs:
                        try:
                            txt = div.inner_text() or ""
                            if len(txt) > len(content) and len(txt) < 100000:
                                content = txt
                        except Exception:
                            continue

                # Clean up
                content = content.strip()
                # Remove navigation/footer noise
                for noise in ["上一篇", "下一篇", "打印本页", "关闭窗口", "【字体：", "来源：", "发布日期："]:
                    idx = content.rfind(noise)
                    if idx > 0 and idx > len(content) * 0.8:
                        content = content[:idx].strip()

                std["content"] = content[:50000]
                std["content_length"] = len(content)

                status = "OK" if len(content) > 500 else ("SHORT" if len(content) > 100 else "FAIL")
                log.info("  [%d/%d] %s %s (%d chars)", i + 1, len(standards), status, std["title"][:40], len(content))

            except Exception as e:
                log.error("  [%d/%d] ERR %s: %s", i + 1, len(standards), std["title"][:30], e)
                std["content"] = ""
                std["content_length"] = 0

        # --- Phase 3: Retry SHORT results with longer wait ---
        short_stds = [s for s in standards if 0 < s.get("content_length", 0) < 500]
        if short_stds:
            log.info("\nPhase 3: Retrying %d SHORT standards with longer wait...", len(short_stds))
            for i, std in enumerate(short_stds):
                try:
                    page.goto(std["url"], wait_until="domcontentloaded", timeout=20000)
                    time.sleep(5)  # Longer wait for AJAX
                    page.wait_for_timeout(3000)

                    content = ""
                    for sel in ["div.TRS_Editor", "div#zoom", "div.article-content", "div.content",
                                "div.text", "div.Custom_UnionStyle", "div.TRS_PreAppend"]:
                        el = page.query_selector(sel)
                        if el:
                            txt = el.inner_text() or ""
                            if len(txt) > len(content):
                                content = txt

                    # Check iframes
                    if len(content) < 200:
                        for iframe in page.query_selector_all("iframe"):
                            try:
                                frame = iframe.content_frame()
                                if frame:
                                    txt = frame.query_selector("body").inner_text() or ""
                                    if len(txt) > len(content):
                                        content = txt
                            except Exception:
                                continue

                    if len(content) > std.get("content_length", 0):
                        std["content"] = content[:50000]
                        std["content_length"] = len(content)
                        log.info("  [retry %d/%d] UPGRADED %s (%d chars)", i+1, len(short_stds), std["title"][:40], len(content))
                    else:
                        log.info("  [retry %d/%d] NO CHANGE %s", i+1, len(short_stds), std["title"][:40])
                except Exception as e:
                    log.warning("  [retry %d/%d] ERR: %s", i+1, len(short_stds), e)

        browser.close()

    # Save results
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(standards, f, ensure_ascii=False, indent=2)

    good = sum(1 for s in standards if s.get("content_length", 0) > 500)
    short = sum(1 for s in standards if 100 < s.get("content_length", 0) <= 500)
    fail = sum(1 for s in standards if s.get("content_length", 0) <= 100)
    log.info("\n=== Results ===")
    log.info("Total: %d standards", len(standards))
    log.info("Good (>500c): %d", good)
    log.info("Short (100-500c): %d", short)
    log.info("Fail (<100c): %d", fail)
    log.info("Saved to %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
