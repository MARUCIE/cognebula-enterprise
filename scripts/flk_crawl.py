"""Crawl flk.npc.gov.cn law full text via Playwright browser navigation.

Strategy: Navigate to category pages, extract law list, click into each law,
extract full text from rendered page.

Output: /home/kg/cognebula-enterprise/data/recrawl/flk_npc_laws.json
"""
import json
import re
import time
import os
import hashlib
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

OUTPUT_PATH = "/home/kg/cognebula-enterprise/data/recrawl/flk_npc_laws.json"
CHECKPOINT_PATH = "/home/kg/cognebula-enterprise/data/recrawl/flk_npc_checkpoint.json"

# Categories to crawl (skip dfxfg = 15K+ local regulations)
CATEGORIES = [
    ("fl.html", "法律", "flfg"),
    ("xzfg.html", "行政法规", "xzfg"),
    ("sfjs.html", "司法解释", "sfjs"),
]

results = []


def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH) as f:
            return json.load(f)
    return {"crawled_ids": [], "results": []}


def save_checkpoint(state):
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump(state, f, ensure_ascii=False)


def extract_law_links(page):
    """Extract law title + link from current listing page."""
    links = page.query_selector_all("a[href*='detail']")
    items = []
    for link in links:
        href = link.get_attribute("href") or ""
        title = link.inner_text().strip()
        if title and len(title) >= 3 and ("detail" in href or href.startswith("/")):
            items.append({"title": title, "href": href})
    return items


def extract_fulltext(page):
    """Extract full text from a law detail page."""
    # Wait for content to render
    time.sleep(2)

    # Try multiple content selectors
    for selector in [".law-content", ".article-content", ".content-box",
                     ".detail-content", "#law-content", ".body",
                     "article", ".main-content", "[class*=content]"]:
        el = page.query_selector(selector)
        if el:
            text = el.inner_text().strip()
            if len(text) > 100:
                return text

    # Fallback: get all body text
    body_text = page.inner_text("body")
    # Remove common noise
    for noise in ["返回顶部", "版权所有", "请使用IE", "相关链接", "小程序"]:
        idx = body_text.find(noise)
        if idx > 0:
            body_text = body_text[:idx]

    return body_text.strip()


def crawl_category(page, cat_url, cat_name, cat_code, checkpoint):
    """Crawl all laws in a category."""
    base_url = "https://flk.npc.gov.cn"
    crawled_ids = set(checkpoint.get("crawled_ids", []))
    cat_results = []

    print(f"\n=== {cat_name} ({cat_url}) ===")
    page.goto(f"{base_url}/{cat_url}", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    # Get page text to find law entries
    body = page.inner_text("body")
    print(f"Page loaded, body length: {len(body)}")

    # Extract all links to law details
    all_links = page.query_selector_all("a")
    detail_links = []
    for link in all_links:
        href = link.get_attribute("href") or ""
        title = link.inner_text().strip()
        if len(title) >= 4 and len(title) <= 100:
            # Check if it looks like a law title
            if href and ("detail" in href or href.startswith("/") or "npc.gov.cn" in href):
                detail_links.append({"title": title, "href": href})

    # Deduplicate
    seen = set()
    unique_links = []
    for dl in detail_links:
        key = dl["title"]
        if key not in seen:
            seen.add(key)
            unique_links.append(dl)

    print(f"Found {len(unique_links)} unique law links")
    for dl in unique_links[:5]:
        print(f"  [{dl['title'][:40]}] -> {dl['href'][:60]}")

    # Click into each law and extract text
    for i, dl in enumerate(unique_links):
        title = dl["title"]
        law_id = hashlib.sha256(f"flk:{cat_code}:{title}".encode()).hexdigest()[:16]

        if law_id in crawled_ids:
            continue

        try:
            # Navigate to detail page
            href = dl["href"]
            if href.startswith("/"):
                href = base_url + href
            elif not href.startswith("http"):
                href = base_url + "/" + href

            page.goto(href, wait_until="networkidle", timeout=20000)
            time.sleep(2)

            fulltext = extract_fulltext(page)

            item = {
                "id": law_id,
                "title": title,
                "content": fulltext[:50000],
                "source": f"flk_{cat_code}",
                "type": cat_name,
                "url": href,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
            cat_results.append(item)
            crawled_ids.add(law_id)

            content_len = len(fulltext)
            status = "OK" if content_len >= 100 else "SHORT"
            print(f"  [{i+1}/{len(unique_links)}] {status} {title[:40]} ({content_len}c)")

            # Checkpoint every 20 items
            if (i + 1) % 20 == 0:
                checkpoint["crawled_ids"] = list(crawled_ids)
                checkpoint["results"] = checkpoint.get("results", []) + cat_results
                save_checkpoint(checkpoint)
                cat_results = []

            # Go back to listing
            page.go_back(wait_until="networkidle", timeout=15000)
            time.sleep(1 + (i % 3))  # Variable delay

        except Exception as e:
            print(f"  [{i+1}] ERROR: {title[:30]} - {str(e)[:80]}")
            # Try to recover by going back to category
            try:
                page.goto(f"{base_url}/{cat_url}", wait_until="networkidle", timeout=20000)
                time.sleep(2)
            except:
                pass

    return cat_results


def main():
    checkpoint = load_checkpoint()
    all_results = checkpoint.get("results", [])

    p = sync_playwright().start()
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
    ctx = b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="zh-CN",
    )
    pg = ctx.new_page()

    for cat_url, cat_name, cat_code in CATEGORIES:
        try:
            cat_results = crawl_category(pg, cat_url, cat_name, cat_code, checkpoint)
            all_results.extend(cat_results)
        except Exception as e:
            print(f"Category {cat_name} failed: {e}")

    # Save final results
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    with_content = sum(1 for r in all_results if len(r.get("content", "")) >= 100)
    print(f"\n=== DONE ===")
    print(f"Total: {len(all_results)} laws")
    print(f"With content >= 100c: {with_content}")
    print(f"Saved to: {OUTPUT_PATH}")

    b.close()
    p.stop()


if __name__ == "__main__":
    main()
