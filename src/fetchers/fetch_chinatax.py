"""Fetcher: State Taxation Administration policy database (fgk.chinatax.gov.cn).

The policy database is JS-rendered (Vue SPA). Simple HTTP returns an empty shell.
This fetcher attempts a plain HTTP request first; if it gets no useful content,
it falls back to non-SPA chinatax.gov.cn pages with deep pagination.
"""

import argparse
import hashlib
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fetch_chinatax")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# Known API endpoints discovered via browser DevTools
SEARCH_API = "https://fgk.chinatax.gov.cn/api/tax/search"
LIST_URL = "https://fgk.chinatax.gov.cn/"

# Non-SPA sections on www.chinatax.gov.cn with pagination support
CHINATAX_BASE = "https://www.chinatax.gov.cn/chinatax"
FALLBACK_SECTIONS = [
    ("tax_policy_announce", f"{CHINATAX_BASE}/n810341/n810755/index.html"),    # Original: policy announcements
    ("tax_guidance", f"{CHINATAX_BASE}/n810351/n810838/index.html"),            # Original: tax guidance
    ("tax_news", f"{CHINATAX_BASE}/n810219/n810724/index.html"),               # Original: tax news
    ("tax_policy_gonggao", f"{CHINATAX_BASE}/n810341/n810760/index.html"),     # Tax policy/gonggao
    ("tax_publicity", f"{CHINATAX_BASE}/n810219/n810744/index.html"),          # Tax publicity
    ("policy_interpret", f"{CHINATAX_BASE}/n810341/n810765/index.html"),       # Policy interpretation
    ("tax_service_guide", f"{CHINATAX_BASE}/n810351/n810896/index.html"),      # Tax service guide
]

LINK_PATTERN = r'<a[^>]*href=["\']([^"\']*content[^"\']*)["\'][^>]*>([^<]{8,})</a>'


def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": LIST_URL,
    }


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _fetch_detail(client: httpx.Client, url: str) -> str:
    """Fetch article body text, truncated to 3000 chars."""
    try:
        time.sleep(5)
        resp = client.get(url, headers=_headers(), timeout=15)
        resp.encoding = "utf-8"
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        content_div = soup.select_one("div.TRS_Editor, div.pages_content, div.content, #zoom")
        text = content_div.get_text(separator="\n", strip=True) if content_div else ""
        if not text:
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else ""
        return text[:3000]
    except Exception as e:
        log.warning("Detail fetch failed for %s: %s", url, e)
        return ""


def fetch(output_dir: str, max_pages_per_section: int = 5, fetch_detail: bool = True) -> list[dict]:
    """Try HTTP-based fetching. Returns items or empty list."""
    results = []
    now = datetime.now(timezone.utc).isoformat()
    seen_urls = set()

    # Attempt 1: hit the search API directly (observed in browser network tab)
    try:
        log.info("Attempting search API at %s", SEARCH_API)
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.post(
                SEARCH_API,
                headers=_headers(),
                json={"keyword": "税收", "page": 1, "size": 20},
            )
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/json"):
                data = resp.json()
                items = data.get("data", {}).get("list", []) if isinstance(data.get("data"), dict) else []
                for item in items:
                    item_url = item.get("url", LIST_URL)
                    results.append({
                        "id": _make_id(item_url),
                        "title": item.get("title", ""),
                        "url": item_url,
                        "content": item.get("content", ""),
                        "source": "chinatax_fgk",
                        "type": "policy",
                        "date": item.get("publishDate", ""),
                        "crawled_at": now,
                    })
                    seen_urls.add(item_url)
                log.info("Search API returned %d items", len(results))
            else:
                log.warning("Search API returned status %d (content-type: %s)", resp.status_code, resp.headers.get("content-type", ""))
    except Exception as e:
        log.warning("Search API failed: %s", e)

    # Attempt 2: crawl non-SPA chinatax.gov.cn sections with deep pagination
    log.info("Crawling non-SPA chinatax.gov.cn sections (up to %d pages each)", max_pages_per_section)
    with httpx.Client(timeout=15, follow_redirects=True) as client:
        # Get C3VK anti-bot cookie first
        r_init = client.get("https://www.chinatax.gov.cn/", headers=_headers(), timeout=10)
        cookies = {}
        m_cookie = re.search(r"C3VK=([^;]+)", r_init.text)
        if m_cookie:
            cookies["C3VK"] = m_cookie.group(1)
            log.info("Got C3VK cookie: %s", m_cookie.group(1)[:10])
            time.sleep(1)
            # Verify cookie works
            client.get("https://www.chinatax.gov.cn/", headers=_headers(), cookies=cookies, timeout=10)
            time.sleep(1)
        for s_idx, (section_name, section_index_url) in enumerate(FALLBACK_SECTIONS):
            # Refresh cookie every 3 sections
            if s_idx > 0 and s_idx % 3 == 0:
                r_refresh = client.get("https://www.chinatax.gov.cn/", headers=_headers(), timeout=10)
                m_refresh = re.search(r"C3VK=([^;]+)", r_refresh.text)
                if m_refresh:
                    cookies["C3VK"] = m_refresh.group(1)
                    log.info("Refreshed C3VK cookie")
                    time.sleep(1)
            for page_idx in range(max_pages_per_section):
                if page_idx == 0:
                    url = section_index_url
                else:
                    url = section_index_url.replace("index.html", f"index_{page_idx}.html")
                try:
                    time.sleep(5)
                    log.info("Fetching section '%s' page %d/%d: %s", section_name, page_idx + 1, max_pages_per_section, url)
                    resp = client.get(url, headers=_headers(), cookies=cookies)
                    if resp.status_code == 404:
                        log.info("Section '%s' page %d returned 404, stopping", section_name, page_idx + 1)
                        break
                    resp.encoding = "utf-8"

                    page_count = 0
                    for m in re.finditer(LINK_PATTERN, resp.text):
                        href, title = m.group(1), m.group(2).strip()
                        if not href.startswith("http"):
                            href = "https://www.chinatax.gov.cn" + href
                        if len(title) > 8 and "content" in href and href not in seen_urls:
                            content = ""
                            if fetch_detail:
                                content = _fetch_detail(client, href)
                            results.append({
                                "id": _make_id(href),
                                "title": title,
                                "url": href,
                                "content": content,
                                "source": "chinatax",
                                "type": section_name,
                                "date": "",
                                "crawled_at": now,
                            })
                            seen_urls.add(href)
                            page_count += 1

                    log.info("Found %d new entries in section '%s' page %d (total: %d)", page_count, section_name, page_idx + 1, len(results))

                    if page_count == 0:
                        log.info("Section '%s' page %d returned 0 new items, stopping", section_name, page_idx + 1)
                        break

                except Exception as e:
                    log.error("Section '%s' page %d failed: %s", section_name, page_idx + 1, e)

    # Save output
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "chinatax.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch ChinaTax policy database")
    parser.add_argument("--output", default="./out", help="Output directory")
    parser.add_argument("--pages-per-section", type=int, default=5, help="Max pages per section")
    parser.add_argument("--no-detail", action="store_true", help="Skip fetching article body")
    args = parser.parse_args()
    fetch(args.output, max_pages_per_section=args.pages_per_section, fetch_detail=not args.no_detail)
