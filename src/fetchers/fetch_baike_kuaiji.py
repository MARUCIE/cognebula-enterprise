"""Fetcher: baike.kuaiji.com (会计百科) -- wiki-style accounting encyclopedia with 17,000+ entries.

Crawls category index pages to discover entries, then optionally fetches detail pages
for full definitions.

Site structure:
  Categories: /kuaiji/, /shuiwu/, /caiwu/, /shenji/, /jinrong/, /jingji/, /kaoshi/, /jigou/, /shangxueyuan/, /renwu/
  Entries: /vNNNNNNN.html (e.g. /v402717379.html)
  Pagination: /{category}/2.html, /{category}/3.html, ...  (page 1 = /{category}/)
  10 entries per page, pure HTML, no JS rendering.
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
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fetch_baike_kuaiji")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

BASE_URL = "https://baike.kuaiji.com"

# All known categories: (slug, display_name)
CATEGORIES = [
    ("kuaiji", "会计"),
    ("shuiwu", "税务"),
    ("caiwu", "财务"),
    ("shenji", "审计"),
    ("jinrong", "金融"),
    ("jingji", "经济"),
    ("kaoshi", "考试"),
    ("jigou", "机构"),
    ("shangxueyuan", "商学院"),
    ("renwu", "人物"),
]

# Default subset for finance/tax knowledge base
DEFAULT_CATEGORIES = ["kuaiji", "shuiwu", "caiwu", "shenji", "jinrong"]

# Max pages to probe per category before giving up (safety ceiling)
MAX_PAGES_PER_CATEGORY = 500


def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": BASE_URL,
    }


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _polite_delay(seconds: float = 3.0):
    """Polite delay with jitter."""
    time.sleep(seconds + random.uniform(0, 1.0))


def _parse_index_page(html: str) -> list[dict]:
    """Extract entry links from a category index page.

    Returns list of dicts with keys: title, url, entry_id.
    """
    items = []
    seen = set()
    soup = BeautifulSoup(html, "html.parser")

    # Entry links match /vNNNNNNN.html
    entry_re = re.compile(r"^/v(\d+)\.html$")

    for a_tag in soup.find_all("a", href=entry_re):
        href = a_tag["href"]
        title = a_tag.get_text(strip=True)
        if not title or len(title) < 2:
            continue
        m = entry_re.match(href)
        if not m:
            continue
        entry_id = m.group(1)
        full_url = BASE_URL + href
        if full_url not in seen:
            items.append({"title": title, "url": full_url, "entry_id": entry_id})
            seen.add(full_url)

    # Regex fallback if BS4 found too few
    if len(items) < 3:
        for m in re.finditer(r'<a[^>]*href="(/v(\d+)\.html)"[^>]*>([^<]{2,})</a>', html):
            href, entry_id, title = m.group(1), m.group(2), m.group(3).strip()
            full_url = BASE_URL + href
            if full_url not in seen:
                items.append({"title": title, "url": full_url, "entry_id": entry_id})
                seen.add(full_url)

    return items


def _detect_max_page(html: str, slug: str) -> int | None:
    """Try to detect the last page number from pagination links.

    Pagination shows a sliding window (e.g. pages 96-104 when on page 100),
    so we re-detect on each page and take the running max.
    """
    page_nums = []
    # Match only pagination links for the current category slug
    pattern = rf'/{re.escape(slug)}/(\d+)\.html'
    for m in re.finditer(pattern, html):
        try:
            page_nums.append(int(m.group(1)))
        except ValueError:
            pass
    return max(page_nums) if page_nums else None


def _fetch_detail(client: httpx.Client, url: str) -> dict:
    """Fetch entry detail page. Returns dict with content, related_terms, breadcrumb_category."""
    result = {"content": "", "related_terms": [], "breadcrumb_category": ""}
    try:
        _polite_delay()
        resp = client.get(url, headers=_headers(), timeout=20)
        if resp.status_code != 200:
            log.warning("Detail %s returned HTTP %d", url, resp.status_code)
            return result
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "iframe"]):
            tag.decompose()

        # Breadcrumb category (e.g. "会计百科 > 会计 > 补偿性资产")
        breadcrumb = soup.find("div", class_="breadcrumb") or soup.find("nav", class_="breadcrumb")
        if breadcrumb:
            crumbs = [a.get_text(strip=True) for a in breadcrumb.find_all("a")]
            if len(crumbs) >= 2:
                result["breadcrumb_category"] = crumbs[-1]  # last link before current

        # Main content: try multiple selectors
        content_el = None
        for selector in [
            "div.wiki-content",
            "div.entry-content",
            "div.content",
            "div.article-content",
            "article",
            "#doctitle ~ div",
            "div.main-content",
        ]:
            content_el = soup.select_one(selector)
            if content_el:
                break

        if not content_el:
            # Fallback: find the largest text block after h1
            h1 = soup.find("h1")
            if h1 and h1.parent:
                content_el = h1.parent

        if content_el:
            text = content_el.get_text(separator="\n", strip=True)
            result["content"] = text[:5000]
        else:
            body = soup.find("body")
            if body:
                result["content"] = body.get_text(separator="\n", strip=True)[:3000]

        # Related terms: internal links within content
        entry_re = re.compile(r"^/v\d+\.html$")
        related = set()
        search_area = content_el or soup
        for a_tag in search_area.find_all("a", href=entry_re):
            term = a_tag.get_text(strip=True)
            if term and len(term) >= 2:
                related.add(term)
        result["related_terms"] = sorted(related)[:30]

    except Exception as e:
        log.warning("Detail fetch failed for %s: %s", url, e)
    return result


def crawl_category(
    client: httpx.Client,
    slug: str,
    display_name: str,
    max_total: int | None,
    current_count: int,
    fetch_detail_flag: bool,
) -> list[dict]:
    """Crawl all pages of a single category. Returns list of entry dicts."""
    entries = []
    now = datetime.now(timezone.utc).isoformat()
    seen_urls = set()
    max_page_detected = None
    consecutive_empty = 0

    for page_idx in range(1, MAX_PAGES_PER_CATEGORY + 1):
        # Check global limit
        if max_total is not None and (current_count + len(entries)) >= max_total:
            log.info("Reached max_total %d, stopping category '%s'", max_total, slug)
            break

        # Build page URL
        if page_idx == 1:
            page_url = f"{BASE_URL}/{slug}/"
        else:
            page_url = f"{BASE_URL}/{slug}/{page_idx}.html"

        # Stop if we've gone past detected last page
        if max_page_detected is not None and page_idx > max_page_detected:
            log.info("Category '%s': reached last detected page %d", slug, max_page_detected)
            break

        if page_idx > 1:
            _polite_delay()

        try:
            log.info("[%s] page %d: %s", slug, page_idx, page_url)
            resp = client.get(page_url, headers=_headers(), timeout=15)

            if resp.status_code == 404:
                log.info("[%s] page %d returned 404, stopping", slug, page_idx)
                break
            if resp.status_code != 200:
                log.warning("[%s] page %d returned HTTP %d", slug, page_idx, resp.status_code)
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break
                continue

            resp.encoding = "utf-8"

            # Re-detect max page on every page (pagination is a sliding window)
            page_max = _detect_max_page(resp.text, slug)
            if page_max and (max_page_detected is None or page_max > max_page_detected):
                max_page_detected = page_max
                if page_idx == 1:
                    log.info("[%s] detected %d total pages (~%d entries)", slug, max_page_detected, max_page_detected * 10)

            page_items = _parse_index_page(resp.text)

            if not page_items:
                consecutive_empty += 1
                log.info("[%s] page %d returned 0 items (consecutive_empty=%d)", slug, page_idx, consecutive_empty)
                if consecutive_empty >= 3:
                    log.info("[%s] 3 consecutive empty pages, stopping", slug)
                    break
                continue

            consecutive_empty = 0

            for item in page_items:
                if item["url"] in seen_urls:
                    continue
                seen_urls.add(item["url"])

                # Check global limit
                if max_total is not None and (current_count + len(entries)) >= max_total:
                    break

                detail = {}
                if fetch_detail_flag:
                    detail = _fetch_detail(client, item["url"])

                entries.append({
                    "id": _make_id(item["url"]),
                    "title": item["title"],
                    "url": item["url"],
                    "content": detail.get("content", ""),
                    "related_terms": detail.get("related_terms", []),
                    "source": "baike_kuaiji",
                    "type": slug,
                    "type_display": display_name,
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "crawled_at": now,
                })

            log.info("[%s] page %d: +%d entries (total %d)", slug, page_idx, len(page_items), len(entries))

        except Exception as e:
            log.error("[%s] page %d failed: %s", slug, page_idx, e)
            consecutive_empty += 1
            if consecutive_empty >= 3:
                break

    return entries


def fetch(
    output_dir: str,
    max_total: int = 5000,
    categories: list[str] | None = None,
    fetch_detail: bool = True,
) -> list[dict]:
    """Main entry point. Crawl baike.kuaiji.com categories.

    Args:
        output_dir: Directory to write JSON output.
        max_total: Maximum total entries to fetch across all categories.
        categories: List of category slugs to crawl. None = default 5 categories.
        fetch_detail: Whether to fetch detail pages for full content.

    Returns:
        List of all fetched entry dicts.
    """
    # Resolve which categories to crawl
    cat_slugs = categories or DEFAULT_CATEGORIES
    cat_map = {slug: name for slug, name in CATEGORIES}
    cats_to_crawl = [(s, cat_map.get(s, s)) for s in cat_slugs if s in cat_map]

    if not cats_to_crawl:
        valid = [s for s, _ in CATEGORIES]
        log.error("No valid categories. Valid: %s", ", ".join(valid))
        return []

    log.info("Crawling %d categories: %s (max_total=%d, detail=%s)",
             len(cats_to_crawl), ", ".join(s for s, _ in cats_to_crawl), max_total, fetch_detail)

    all_results = []

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for slug, display_name in cats_to_crawl:
            if max_total is not None and len(all_results) >= max_total:
                log.info("Reached max_total %d, stopping", max_total)
                break

            log.info("=== Category: %s (%s) ===", display_name, slug)
            entries = crawl_category(
                client=client,
                slug=slug,
                display_name=display_name,
                max_total=max_total,
                current_count=len(all_results),
                fetch_detail_flag=fetch_detail,
            )
            all_results.extend(entries)
            log.info("Category '%s': %d entries (running total: %d)", slug, len(entries), len(all_results))

            # Delay between categories
            if slug != cats_to_crawl[-1][0]:
                _polite_delay(5.0)

    # Write output
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "baike_kuaiji.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(all_results), out_path)

    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch baike.kuaiji.com accounting encyclopedia")
    parser.add_argument("--output", default="./out", help="Output directory")
    parser.add_argument("--max-total", type=int, default=5000, help="Max entries to fetch (default 5000)")
    parser.add_argument("--no-detail", action="store_true", help="Only get titles from index, skip detail pages")
    parser.add_argument("--category", nargs="+", help="Crawl specific categories only (e.g. kuaiji shuiwu)")
    parser.add_argument("--all-categories", action="store_true", help="Crawl all 10 categories (default: 5 core)")
    args = parser.parse_args()

    cats = args.category
    if args.all_categories:
        cats = [s for s, _ in CATEGORIES]

    fetch(
        output_dir=args.output,
        max_total=args.max_total,
        categories=cats,
        fetch_detail=not args.no_detail,
    )
