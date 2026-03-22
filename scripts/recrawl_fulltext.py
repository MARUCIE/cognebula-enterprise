#!/usr/bin/env python3
"""Re-crawl MOF/NDRC/Baike with full text and ingest to KuzuDB.

Fixes the production issue where these sources ran with --no-detail (title-only).
Uses httpx with fleet-page-fetch fallback for anti-bot bypass.

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/recrawl_fulltext.py --source mof
    /home/kg/kg-env/bin/python3 -u scripts/recrawl_fulltext.py --source ndrc
    /home/kg/kg-env/bin/python3 -u scripts/recrawl_fulltext.py --source baike
    sudo systemctl start kg-api

Or all at once:
    /home/kg/kg-env/bin/python3 -u scripts/recrawl_fulltext.py --source all
"""
import argparse
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

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("recrawl")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
OUTPUT_DIR = "/home/kg/cognebula-enterprise/data/recrawl"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _fleet_fetch(url: str) -> str:
    """Fetch via fleet-page-fetch VPS browser proxy (localhost on kg-node)."""
    try:
        result = subprocess.run(
            ["curl", "-sf", "http://100.106.223.39:19801/fetch",
             "-X", "POST", "-H", "Content-Type: application/json",
             "-d", json.dumps({"url": url})],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            return data.get("markdown", data.get("text", ""))
    except Exception as e:
        log.warning("Fleet fetch failed for %s: %s", url, e)
    return ""


ERROR_PATTERNS = re.compile(
    r"(502 Bad Gateway|503 Service|404 Not Found|Error Times:|"
    r"The requested URL could not be retrieved|access denied|"
    r"请开启JavaScript|请完成安全验证)", re.IGNORECASE
)


def _is_error_page(text: str) -> bool:
    """Detect error/anti-bot pages masquerading as content."""
    if len(text) < 50:
        return True
    if ERROR_PATTERNS.search(text[:500]):
        return True
    # Chinese content should have Chinese chars
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text[:500]))
    if chinese_chars < 10 and len(text) < 300:
        return True
    return False


def _fetch_page(client: httpx.Client, url: str, selectors: list[str]) -> str:
    """Fetch page content via httpx, fallback to fleet-page-fetch."""
    try:
        time.sleep(3 + random.uniform(0, 2))
        resp = client.get(url, headers=_headers(), timeout=20)
        resp.encoding = "utf-8"

        if resp.status_code >= 400:
            raise ValueError(f"HTTP {resp.status_code}")

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "iframe"]):
            tag.decompose()
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) >= 100 and not _is_error_page(text):
                    return text[:50000]
        # Fallback to body
        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
            if len(text) >= 100 and not _is_error_page(text):
                return text[:50000]
    except Exception as e:
        log.warning("httpx failed for %s: %s", url, e)

    # Fleet fallback (browser rendering)
    log.info("  -> fleet-page-fetch fallback: %s", url)
    text = _fleet_fetch(url)
    if text and not _is_error_page(text):
        return text[:50000]
    return ""


# ─── MOF ──────────────────────────────────────────────────────────────
def crawl_mof(client: httpx.Client, max_pages: int = 20) -> list[dict]:
    """Crawl MOF policy releases with full text."""
    BASE = "https://www.mof.gov.cn"
    LIST_URL = f"{BASE}/zhengwuxinxi/zhengcefabu/"
    selectors = ["div.TRS_Editor", "div.pages_content", "div.content", "#zoom"]
    results = []
    now = datetime.now(timezone.utc).isoformat()

    for page_idx in range(max_pages):
        url = LIST_URL if page_idx == 0 else f"{LIST_URL}index_{page_idx}.htm"
        try:
            if page_idx > 0:
                time.sleep(3)
            log.info("[MOF] listing page %d/%d", page_idx + 1, max_pages)
            resp = client.get(url, headers=_headers(), timeout=15)
            if resp.status_code == 404:
                break
            resp.encoding = "utf-8"

            # Parse listing
            soup = BeautifulSoup(resp.text, "html.parser")
            entries = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                title = a_tag.get_text(strip=True)
                if not title or len(title) < 8:
                    continue
                if "mof.gov.cn" in href or (href.startswith("./") and href.endswith(".htm")):
                    from urllib.parse import urljoin
                    full_url = urljoin(url, href)
                    entries.append({"title": title, "url": full_url})

            # Regex fallback
            if len(entries) < 3:
                for m in re.finditer(r'<a[^>]*href=["\']([^"\']*mof\.gov\.cn[^"\']+)["\'][^>]*>([^<]{8,})</a>', resp.text):
                    entries.append({"title": m.group(2).strip(), "url": m.group(1)})

            log.info("[MOF] page %d: %d entries", page_idx + 1, len(entries))
            if not entries:
                break

            for entry in entries:
                content = _fetch_page(client, entry["url"], selectors)
                if len(content) < 100:
                    log.warning("  SKIP (short): %s (%d chars)", entry["title"][:30], len(content))
                    continue
                results.append({
                    "id": _make_id(entry["url"]),
                    "title": entry["title"],
                    "url": entry["url"],
                    "content": content,
                    "source": "mof",
                    "crawled_at": now,
                })
                log.info("  OK: %s (%d chars)", entry["title"][:40], len(content))

        except Exception as e:
            log.error("[MOF] page %d failed: %s", page_idx + 1, e)

    return results


# ─── NDRC ─────────────────────────────────────────────────────────────
def crawl_ndrc(client: httpx.Client) -> list[dict]:
    """Crawl NDRC notices/announcements/orders with full text."""
    BASE = "https://www.ndrc.gov.cn"
    SECTION_PATHS = [
        ("notice", "/xxgk/zcfb/tz/"),
        ("announcement", "/xxgk/zcfb/gg/"),
        ("commission_order", "/xxgk/zcfb/fzggwl/"),
    ]
    selectors = ["div.TRS_Editor", "div.article-content", "div.detail-content", "div.content", "#zoom"]
    results = []
    now = datetime.now(timezone.utc).isoformat()

    for sec_name, sec_path in SECTION_PATHS:
        for page in range(5):
            suffix = "index.html" if page == 0 else f"index_{page}.html"
            section_url = f"{BASE}{sec_path}{suffix}"
            try:
                time.sleep(3)
                log.info("[NDRC] %s page %d: %s", sec_name, page + 1, section_url)
                resp = client.get(section_url, headers=_headers(), timeout=15)
                resp.encoding = "utf-8"

                # Parse entries
                entries = []
                for m in re.finditer(r'<a[^>]*href="([^"]*?\d{6}/t\d{8}_\d+\.html)"[^>]*>([^<]{8,})</a>', resp.text):
                    from urllib.parse import urljoin
                    full_url = urljoin(section_url, m.group(1))
                    entries.append({"title": m.group(2).strip(), "url": full_url})

                log.info("[NDRC] %s page %d: %d entries", sec_name, page + 1, len(entries))

                for entry in entries:
                    content = _fetch_page(client, entry["url"], selectors)
                    if len(content) < 100:
                        log.warning("  SKIP (short): %s (%d chars)", entry["title"][:30], len(content))
                        continue
                    results.append({
                        "id": _make_id(entry["url"]),
                        "title": entry["title"],
                        "url": entry["url"],
                        "content": content,
                        "source": "ndrc",
                        "type": sec_name,
                        "crawled_at": now,
                    })
                    log.info("  OK: %s (%d chars)", entry["title"][:40], len(content))

            except Exception as e:
                log.error("[NDRC] %s page %d failed: %s", sec_name, page + 1, e)

    return results


# ─── Baike ────────────────────────────────────────────────────────────
def crawl_baike(client: httpx.Client, max_total: int = 5000) -> list[dict]:
    """Crawl baike.kuaiji.com wiki entries with full text."""
    BASE = "https://baike.kuaiji.com"
    CATEGORIES = ["kuaiji", "shuiwu", "caiwu", "shenji", "jinrong"]
    selectors = ["div.wiki-content", "div.entry-content", "div.content", "div.article-content", "article"]
    results = []
    now = datetime.now(timezone.utc).isoformat()
    seen_urls = set()

    for cat in CATEGORIES:
        if len(results) >= max_total:
            break
        log.info("[Baike] === Category: %s ===", cat)
        consecutive_empty = 0

        for page_idx in range(1, 200):
            if len(results) >= max_total:
                break
            page_url = f"{BASE}/{cat}/" if page_idx == 1 else f"{BASE}/{cat}/{page_idx}.html"

            try:
                time.sleep(3 + random.uniform(0, 2))
                resp = client.get(page_url, headers=_headers(), timeout=15)
                if resp.status_code == 404:
                    break
                resp.encoding = "utf-8"

                # Parse entries
                entries = []
                for m in re.finditer(r'<a[^>]*href="(/v(\d+)\.html)"[^>]*>([^<]{2,})</a>', resp.text):
                    entry_url = BASE + m.group(1)
                    if entry_url not in seen_urls:
                        entries.append({"title": m.group(3).strip(), "url": entry_url})
                        seen_urls.add(entry_url)

                if not entries:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                    continue
                consecutive_empty = 0

                log.info("[Baike] %s page %d: %d entries", cat, page_idx, len(entries))

                for entry in entries:
                    if len(results) >= max_total:
                        break
                    content = _fetch_page(client, entry["url"], selectors)
                    if len(content) < 50:
                        continue
                    results.append({
                        "id": _make_id(entry["url"]),
                        "title": entry["title"],
                        "url": entry["url"],
                        "content": content,
                        "source": "baike_kuaiji",
                        "type": cat,
                        "crawled_at": now,
                    })

            except Exception as e:
                log.error("[Baike] %s page %d failed: %s", cat, page_idx, e)
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break

        log.info("[Baike] %s: %d total so far", cat, len(results))

    return results


# ─── Ingest to KuzuDB ────────────────────────────────────────────────
def ingest_to_kuzu(items: list[dict], source_name: str):
    """Ingest crawled items as KnowledgeUnit nodes into KuzuDB."""
    import kuzu
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    inserted = 0
    skipped = 0
    for item in items:
        try:
            # Check if already exists
            r = conn.execute(
                "MATCH (k:KnowledgeUnit {id: $id}) RETURN k.id",
                {"id": item["id"]}
            )
            if r.has_next():
                # Update content if existing node has short content
                conn.execute(
                    "MATCH (k:KnowledgeUnit {id: $id}) "
                    "WHERE k.content IS NULL OR size(k.content) < 100 "
                    "SET k.content = $content",
                    {"id": item["id"], "content": item["content"][:50000]}
                )
                skipped += 1
                continue

            # Insert new
            conn.execute(
                "CREATE (k:KnowledgeUnit {"
                "id: $id, title: $title, content: $content, "
                "source: $source, type: $tp"
                "})",
                {
                    "id": item["id"],
                    "title": item["title"],
                    "content": item["content"][:50000],
                    "source": source_name,
                    "tp": item.get("type", source_name),
                }
            )
            inserted += 1
        except Exception as e:
            log.warning("Ingest failed for %s: %s", item.get("title", "?")[:30], e)

    log.info("Ingest %s: +%d new, %d updated/skipped", source_name, inserted, skipped)

    # Final stats
    r = conn.execute("MATCH (n) RETURN count(n)")
    nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    edges = r.get_next()[0]
    log.info("Graph: %s nodes / %s edges / density %.3f", f"{nodes:,}", f"{edges:,}", edges / nodes)

    del conn
    del db


def main():
    parser = argparse.ArgumentParser(description="Re-crawl MOF/NDRC/Baike with full text")
    parser.add_argument("--source", required=True, choices=["mof", "ndrc", "baike", "all"])
    parser.add_argument("--max-pages", type=int, default=20, help="Max listing pages for MOF")
    parser.add_argument("--max-total", type=int, default=5000, help="Max entries for Baike")
    parser.add_argument("--no-ingest", action="store_true", help="Crawl only, do not ingest to DB")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sources = [args.source] if args.source != "all" else ["mof", "ndrc", "baike"]

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for source in sources:
            log.info("=" * 60)
            log.info("Starting %s full-text crawl", source.upper())
            log.info("=" * 60)

            if source == "mof":
                items = crawl_mof(client, max_pages=args.max_pages)
            elif source == "ndrc":
                items = crawl_ndrc(client)
            elif source == "baike":
                items = crawl_baike(client, max_total=args.max_total)
            else:
                continue

            # Save JSON
            out_path = os.path.join(OUTPUT_DIR, f"{source}_fulltext.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            log.info("Saved %d items to %s", len(items), out_path)

            # Quality check
            good = [i for i in items if len(i.get("content", "")) >= 100]
            log.info("Quality: %d/%d have content >= 100 chars (%.1f%%)",
                     len(good), len(items), 100 * len(good) / max(len(items), 1))

            # Ingest
            if not args.no_ingest and good:
                ingest_to_kuzu(good, source)


if __name__ == "__main__":
    main()
