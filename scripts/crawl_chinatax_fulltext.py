#!/usr/bin/env python3
"""Crawl chinatax.gov.cn full text via fleet-page-fetch (Patchright engine).

Strategy:
1. Load existing chinatax URLs from raw data files
2. Fetch each URL via fleet-page-fetch (VPS Patchright, bypasses anti-bot)
3. Save results to JSONL for later DB ingest
4. Rate limit: 5-8s between requests to be respectful

Run on mac (requires Tailscale for fleet-page-fetch access):
    python3 scripts/crawl_chinatax_fulltext.py 2>&1 | tee /tmp/chinatax_crawl.log
"""
import hashlib
import json
import logging
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("chinatax_crawl")

DATA_DIR = os.path.expanduser("~/Projects/27-cognebula-enterprise/data")
OUTPUT_JSONL = os.path.join(DATA_DIR, "recrawl", "chinatax_fulltext.jsonl")
CHECKPOINT_FILE = os.path.join(DATA_DIR, "recrawl", "chinatax_crawl_checkpoint.json")
FLEET_FETCH = os.path.expanduser("~/00-AI-Fleet/scripts/fleet-page-fetch.sh")
DELAY_MIN = 5
DELAY_MAX = 8


def load_urls():
    """Load all chinatax URLs from raw data files."""
    urls = {}  # url -> {title, id}

    for fpath in [
        os.path.join(DATA_DIR, "raw/chinatax-full/chinatax_api.json"),
        os.path.join(DATA_DIR, "raw/20260315-fgk-deep/chinatax_api.json"),
        os.path.join(DATA_DIR, "raw/2026-03-15-fgk-extra/chinatax_api.json"),
        os.path.join(DATA_DIR, "raw/2026-03-15-fgk-10k/chinatax_api.json"),
    ]:
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            data = json.load(f)
        for item in data:
            url = item.get("url", "")
            title = item.get("title", "")
            content = item.get("content", "")
            if url and title and len(content) < 100:
                # Only fetch URLs where we don't have good content
                urls[url] = {"title": title, "id": item.get("id", "")}

    return urls


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"crawled_urls": []}


def save_checkpoint(state):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(state, f)


def fetch_url(url):
    """Fetch URL via fleet-page-fetch and return markdown content."""
    try:
        result = subprocess.run(
            [FLEET_FETCH, url],
            capture_output=True, text=True, timeout=45
        )
        if result.returncode == 0:
            text = result.stdout.strip()
            # Remove markdown noise
            text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # images
            text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # links (keep text)
            text = re.sub(r'#{1,6}\s*', '', text)  # headers
            text = re.sub(r'\*{1,3}', '', text)  # bold/italic
            text = re.sub(r'\n{3,}', '\n\n', text)  # excess newlines
            return text.strip()
    except subprocess.TimeoutExpired:
        log.warning("  Timeout for %s", url[:60])
    except Exception as e:
        log.warning("  Error: %s", str(e)[:80])
    return ""


def main():
    urls = load_urls()
    log.info("URLs without full text: %d", len(urls))

    checkpoint = load_checkpoint()
    crawled = set(checkpoint.get("crawled_urls", []))
    log.info("Already crawled: %d", len(crawled))

    todo = {u: v for u, v in urls.items() if u not in crawled}
    log.info("Remaining: %d", len(todo))

    if not todo:
        log.info("Nothing to do")
        return

    # Open output file for append
    out_f = open(OUTPUT_JSONL, "a")
    fetched = 0
    good = 0

    for i, (url, meta) in enumerate(todo.items()):
        title = meta["title"]
        log.info("[%d/%d] %s", i + 1, len(todo), title[:50])

        content = fetch_url(url)

        if len(content) >= 100:
            item = {
                "id": meta["id"] or hashlib.sha256(url.encode()).hexdigest()[:16],
                "title": title,
                "content": content[:5000],
                "url": url,
                "source": "chinatax_fgk_fulltext",
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
            out_f.write(json.dumps(item, ensure_ascii=False) + "\n")
            good += 1
            log.info("  OK (%d chars)", len(content))
        else:
            log.info("  SHORT/EMPTY (%d chars)", len(content))

        fetched += 1
        crawled.add(url)

        # Checkpoint every 20
        if fetched % 20 == 0:
            checkpoint["crawled_urls"] = list(crawled)
            save_checkpoint(checkpoint)
            out_f.flush()
            log.info("  [CHECKPOINT] fetched=%d, good=%d", fetched, good)

        # Rate limit
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        time.sleep(delay)

        # Safety: stop after 500 per run to avoid abuse
        if fetched >= 500:
            log.info("Reached 500 limit, stopping")
            break

    out_f.close()
    checkpoint["crawled_urls"] = list(crawled)
    save_checkpoint(checkpoint)

    log.info("\n=== DONE ===")
    log.info("Fetched: %d | Good (>=100c): %d | Rate: %.0f%%",
             fetched, good, 100 * good / max(fetched, 1))


if __name__ == "__main__":
    main()
