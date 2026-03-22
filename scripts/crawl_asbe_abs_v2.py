#!/usr/bin/env python3
"""Crawl ASBE standards using agent-browser-session eval.

Uses system Chrome (Patchright anti-detection) + JS eval for content extraction.
Closes each tab after extraction per user requirement.

Run on Mac:
    python3 scripts/crawl_asbe_abs_v2.py
"""
import json
import logging
import os
import re
import subprocess
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("asbe")

ABS = "agent-browser-session"
BASE = "https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "asbe")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "asbe_official.json")


def abs_cmd(*args, timeout=15) -> str:
    """Run agent-browser-session command and return stdout."""
    try:
        r = subprocess.run([ABS] + list(args), capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f"ERR: {e}"


def extract_content() -> str:
    """Extract main article content via JS eval, excluding nav/footer."""
    # Try specific selectors first, then full body
    for js in [
        "document.querySelector('.TRS_Editor')?.innerText || ''",
        "document.querySelector('#zoom')?.innerText || ''",
        "document.querySelector('.Custom_UnionStyle')?.innerText || ''",
    ]:
        txt = abs_cmd("eval", js)
        if txt and len(txt) > 200 and "第一" in txt:
            return txt.strip('"').replace("\\n", "\n")

    # Fallback: full body, strip nav/footer
    txt = abs_cmd("eval", "document.body.innerText", timeout=10)
    txt = txt.strip('"').replace("\\n", "\n")

    # Remove common header/footer patterns
    lines = txt.split("\n")
    start = 0
    end = len(lines)
    for i, line in enumerate(lines):
        if "第一章" in line or "第一条" in line:
            start = i
            break
    for i in range(len(lines) - 1, -1, -1):
        if "打印本页" in lines[i] or "关闭窗口" in lines[i] or "版权所有" in lines[i]:
            end = i
            break

    content = "\n".join(lines[start:end]).strip()
    return content if len(content) > 100 else txt


def collect_links() -> list[dict]:
    """Collect all standard links from paginated listing."""
    standards = []
    seen = set()

    for page_suffix in ["", "index_1.htm", "index_2.htm", "index_3.htm", "index_4.htm"]:
        url = BASE + page_suffix
        abs_cmd("open", url)
        time.sleep(2)

        # Get snapshot and parse links
        snap = abs_cmd("snapshot")
        for match in re.finditer(r'link "企业会计准则([^"]*)" \[ref=(e\d+)\]', snap):
            title = "企业会计准则" + match.group(1)
            ref = match.group(2)

            if title in seen or len(title) < 10:
                continue
            seen.add(title)

            # Skip category links (not actual standards)
            if title in ("企业会计准则", "企业会计准则解释"):
                continue

            cas_match = re.search(r'第(\d+)号', title)
            cas_num = int(cas_match.group(1)) if cas_match else 0

            standards.append({"title": title, "cas_number": cas_num, "ref": ref, "page_url": url})

        log.info("  Page %s: %d total standards so far", page_suffix or "index", len(standards))

        if not any(r'link "企业会计准则' in line for line in snap.split("\n")):
            break

    standards.sort(key=lambda x: x["cas_number"])
    return standards


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = []

    log.info("Phase 1: Collecting standard links...")
    standards = collect_links()
    log.info("Found %d standards\n", len(standards))

    log.info("Phase 2: Fetching full text...")
    current_page = ""

    for i, std in enumerate(standards):
        # Navigate to the listing page if needed
        if std["page_url"] != current_page:
            abs_cmd("open", std["page_url"])
            time.sleep(2)
            current_page = std["page_url"]

        # Click the standard link
        abs_cmd("click", std["ref"])
        time.sleep(3)

        # Extract content
        content = extract_content()
        content_len = len(content)

        results.append({
            "title": std["title"],
            "cas_number": std["cas_number"],
            "content": content[:50000],
            "content_length": content_len,
        })

        status = "OK" if content_len > 500 else ("SHORT" if content_len > 100 else "FAIL")
        log.info("  [%d/%d] %s %s (%d chars)", i + 1, len(standards), status, std["title"][:40], content_len)

        # Go back to listing and close the detail tab/page
        abs_cmd("open", std["page_url"])
        time.sleep(1)

    # Kill browser session to free resources
    abs_cmd("kill")

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    good = sum(1 for r in results if r["content_length"] > 500)
    short = sum(1 for r in results if 100 < r["content_length"] <= 500)
    fail = sum(1 for r in results if r["content_length"] <= 100)
    log.info("\n=== Results ===")
    log.info("Total: %d standards", len(results))
    log.info("Good (>500c): %d", good)
    log.info("Short (100-500c): %d", short)
    log.info("Fail (<100c): %d", fail)
    log.info("Saved to %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
