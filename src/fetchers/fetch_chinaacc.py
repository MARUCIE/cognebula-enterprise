"""Fetcher: chinaacc.com (正保会计网校) accounting/tax practice articles.

Site structure (discovered 2026-03-15):
- Main categories:
  - /kuaijishiwu/  (会计实务, 18 sub-sections)
  - /zhucekuaijishi/ (注册会计师, 7 sub-sections)
  - /chujizhicheng/ (初级会计, 7 sub-sections)
  - /gaojikuaijishi/ (高级会计师, 7 sub-sections)
  - /guanlikuaijishi/ (管理会计师)
- Each sub-section has at most 5 list pages (index + page2..page5)
- ~24-36 articles per page
- Article URLs: /<category>/<subsection>/<2-char-prefix><timestamp>.shtml
- Server-side rendered HTML, no AJAX needed

Pagination: pageN.shtml (N=2..5), page 1 = index (no suffix)
Total capacity: ~50 sub-sections x 5 pages x ~30 articles = ~7,500 articles
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
log = logging.getLogger("fetch_chinaacc")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

BASE_URL = "https://www.chinaacc.com"

# All discoverable sections with sub-sections.
# max_pages: site caps at 5 per sub-section (page 1 = index, pages 2-5 = paginated).
SECTIONS = [
    # === 会计实务 (Accounting Practice) - 18 sub-sections ===
    {"name": "accounting_skills", "path": "/kuaijishiwu/zzjn/", "label": "会计实务-职称技能"},
    {"name": "accounting_tax_affairs", "path": "/kuaijishiwu/sssw/", "label": "会计实务-涉税实务"},
    {"name": "accounting_tax_policy", "path": "/kuaijishiwu/sszc/", "label": "会计实务-税收政策"},
    {"name": "accounting_tax_theory", "path": "/kuaijishiwu/swll/", "label": "会计实务-税务理论"},
    {"name": "accounting_standards", "path": "/kuaijishiwu/kjzz/", "label": "会计实务-会计准则"},
    {"name": "accounting_cert", "path": "/kuaijishiwu/kjgwzz/", "label": "会计实务-会计官网资讯"},
    {"name": "accounting_bookkeeping", "path": "/kuaijishiwu/jz/", "label": "会计实务-记账"},
    {"name": "accounting_voucher", "path": "/kuaijishiwu/pzzb/", "label": "会计实务-凭证账簿"},
    {"name": "accounting_report", "path": "/kuaijishiwu/bb/", "label": "会计实务-报表"},
    {"name": "accounting_cost", "path": "/kuaijishiwu/cbkj/", "label": "会计实务-成本会计"},
    {"name": "accounting_tax_planning", "path": "/kuaijishiwu/szgg/", "label": "会计实务-税制改革"},
    {"name": "accounting_gst", "path": "/kuaijishiwu/gssw/", "label": "会计实务-个税实务"},
    {"name": "accounting_audit", "path": "/kuaijishiwu/ghy/", "label": "会计实务-工会"},
    {"name": "accounting_company", "path": "/kuaijishiwu/gszl/", "label": "会计实务-公司资料"},
    {"name": "accounting_settlement", "path": "/kuaijishiwu/jiz/", "label": "会计实务-汇算清缴"},
    {"name": "accounting_hr", "path": "/kuaijishiwu/rlzy/", "label": "会计实务-人力资源"},
    {"name": "accounting_market", "path": "/kuaijishiwu/scyx/", "label": "会计实务-市场营销"},
    {"name": "accounting_digital_tax", "path": "/kuaijishiwu/dzsw/", "label": "会计实务-电子税务"},

    # === 注册会计师 (CPA) - 7 sub-sections ===
    {"name": "cpa_study_exp", "path": "/zhucekuaijishi/bkjy/", "label": "注册会计师-备考经验"},
    {"name": "cpa_registration", "path": "/zhucekuaijishi/bm/", "label": "注册会计师-报名"},
    {"name": "cpa_results", "path": "/zhucekuaijishi/cf/", "label": "注册会计师-成绩"},
    {"name": "cpa_review", "path": "/zhucekuaijishi/fxzd/", "label": "注册会计师-复习指导"},
    {"name": "cpa_faq", "path": "/zhucekuaijishi/jhwd/", "label": "注册会计师-精华问答"},
    {"name": "cpa_exam_news", "path": "/zhucekuaijishi/ksdt/", "label": "注册会计师-考试动态"},
    {"name": "cpa_other", "path": "/zhucekuaijishi/qita/", "label": "注册会计师-其他"},

    # === 初级会计 (Junior Accounting) - 7 sub-sections ===
    {"name": "junior_study_exp", "path": "/chujizhicheng/bkjy/", "label": "初级会计-备考经验"},
    {"name": "junior_registration", "path": "/chujizhicheng/bm/", "label": "初级会计-报名"},
    {"name": "junior_results", "path": "/chujizhicheng/cf/", "label": "初级会计-成绩"},
    {"name": "junior_faq", "path": "/chujizhicheng/jhwd/", "label": "初级会计-精华问答"},
    {"name": "junior_exam_news", "path": "/chujizhicheng/ksdt/", "label": "初级会计-考试动态"},
    {"name": "junior_other", "path": "/chujizhicheng/qita/", "label": "初级会计-其他"},
    {"name": "junior_textbook", "path": "/chujizhicheng/js/", "label": "初级会计-教材"},

    # === 高级会计师 (Senior Accounting) - 7 sub-sections ===
    {"name": "senior_study_exp", "path": "/gaojikuaijishi/bkjy/", "label": "高级会计师-备考经验"},
    {"name": "senior_registration", "path": "/gaojikuaijishi/bm/", "label": "高级会计师-报名"},
    {"name": "senior_results", "path": "/gaojikuaijishi/cf/", "label": "高级会计师-成绩"},
    {"name": "senior_review", "path": "/gaojikuaijishi/fxzd/", "label": "高级会计师-复习指导"},
    {"name": "senior_exam_news", "path": "/gaojikuaijishi/ksdt/", "label": "高级会计师-考试动态"},
    {"name": "senior_other", "path": "/gaojikuaijishi/qita/", "label": "高级会计师-其他"},
    {"name": "senior_review_eval", "path": "/gaojikuaijishi/sbps/", "label": "高级会计师-申报评审"},
]

# Max pages per sub-section. Site returns 404 for page >= 6.
MAX_PAGES_PER_SECTION = 5

# Article link pattern: /<category>/<subsection>/<2-letter-prefix><digits>.shtml
# Covers patterns like zh20260313102513, gu20250725094912, de20260312155207, etc.
ARTICLE_LINK_RE = re.compile(
    r'href="(/(?:kuaijishiwu|zhucekuaijishi|chujizhicheng|gaojikuaijishi|guanlikuaijishi)'
    r'/[a-z]+/[a-z]{2}\d{14,}\.shtml)"',
    re.IGNORECASE,
)

# Broader link pattern to also catch titles from anchor text
ARTICLE_WITH_TITLE_RE = re.compile(
    r'<a[^>]*href="(/(?:kuaijishiwu|zhucekuaijishi|chujizhicheng|gaojikuaijishi)'
    r'/[a-z]+/[a-z]{2}\d{14,}\.shtml)"[^>]*>'
    r'\s*(?:<[^>]*>)*\s*([^<]{4,})',
    re.IGNORECASE,
)

# Date extraction from article URL: zh20260313102513 -> 20260313
URL_DATE_RE = re.compile(r"/([a-z]{2})(\d{8})\d{6,}\.shtml")

# Content extraction: <h1> for title, <p>/<section> for body text
TITLE_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL)

REQUEST_DELAY_MIN = 1.5
REQUEST_DELAY_MAX = 3.0


def _headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": BASE_URL + "/",
    }


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _delay():
    time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))


def _page_url(section_path: str, page: int) -> str:
    """Build paginated URL.

    Page 1: /kuaijishiwu/zzjn/
    Page N: /kuaijishiwu/zzjn/pageN.shtml
    """
    if page <= 1:
        return BASE_URL + section_path
    return BASE_URL + section_path.rstrip("/") + f"/page{page}.shtml"


def _extract_date(url: str) -> str:
    """Extract date from article URL pattern."""
    m = URL_DATE_RE.search(url)
    if m:
        d = m.group(2)
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    return ""


def _extract_title_from_html(html: str) -> str:
    """Extract article title from page HTML."""
    m = TITLE_RE.search(html)
    if m:
        title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        # chinaacc h1 often contains just the section name; look for more specific title
        if len(title) > 5:
            return title
    # Fallback: <title> tag
    m = re.search(r"<title>([^<]+)</title>", html)
    if m:
        t = m.group(1).strip()
        # Remove site suffix
        t = re.sub(r"\s*[-_|]\s*正保会计网校.*$", "", t)
        t = re.sub(r"\s*[-_|]\s*中华会计网校.*$", "", t)
        return t
    return ""


def _extract_content(html: str) -> str:
    """Extract article body text from HTML."""
    # Strategy: collect all <p> and <section> text blocks
    # Filter out navigation, sidebar, and ad content
    blocks = re.findall(r"<(?:p|section)[^>]*>(.*?)</(?:p|section)>", html, re.DOTALL)
    texts = []
    for b in blocks:
        text = re.sub(r"<[^>]+>", " ", b)
        text = re.sub(r"&nbsp;|&amp;|&lt;|&gt;", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        # Skip short or navigation-like blocks
        if len(text) < 15:
            continue
        # Skip blocks that look like navigation/ads
        if re.match(r"^(初级|中级|高级|注册|报名|考试|查分|备考|题库|复习|课程|选课)", text):
            if len(text) < 50:
                continue
        texts.append(text)

    content = "\n".join(texts)
    return content[:5000]  # Cap at 5000 chars


def fetch_list_page(client: httpx.Client, url: str, section_path: str) -> list[dict]:
    """Fetch a list page and extract article links."""
    try:
        resp = client.get(url, headers=_headers(), timeout=20)
        if resp.status_code != 200:
            log.warning("Got %d for %s", resp.status_code, url)
            return []

        articles = []
        seen = set()

        # Try with-title pattern first for better title extraction
        for match in ARTICLE_WITH_TITLE_RE.finditer(resp.text):
            path = match.group(1)
            title = match.group(2).strip()
            if path in seen:
                continue
            # Only include articles from this section
            if not path.startswith(section_path.rstrip("/")):
                continue
            seen.add(path)
            full_url = BASE_URL + path
            articles.append({
                "url": full_url,
                "title": re.sub(r"<[^>]+>", "", title).strip()[:200],
                "date": _extract_date(path),
            })

        # Also catch any links missed by the title pattern
        for match in ARTICLE_LINK_RE.finditer(resp.text):
            path = match.group(1)
            if path in seen:
                continue
            if not path.startswith(section_path.rstrip("/")):
                continue
            seen.add(path)
            full_url = BASE_URL + path
            articles.append({
                "url": full_url,
                "title": "",  # Will be fetched from article page if needed
                "date": _extract_date(path),
            })

        return articles

    except Exception as e:
        log.warning("Failed to fetch %s: %s", url, e)
        return []


def fetch_article(client: httpx.Client, url: str) -> dict:
    """Fetch full article page, return title + content."""
    try:
        resp = client.get(url, headers=_headers(), timeout=20)
        if resp.status_code != 200:
            return {"title": "", "content": ""}

        title = _extract_title_from_html(resp.text)
        content = _extract_content(resp.text)
        return {"title": title, "content": content}

    except Exception as e:
        log.warning("Failed to fetch article %s: %s", url, e)
        return {"title": "", "content": ""}


def fetch(output_dir: str, max_pages: int = 0,
          fetch_content: bool = False,
          sections_filter: str = "",
          save_interval: int = 200) -> list[dict]:
    """Fetch chinaacc practice articles.

    Args:
        output_dir: Directory to save JSON output.
        max_pages: Override max pages per section (0 = use MAX_PAGES_PER_SECTION).
        fetch_content: Whether to fetch full article content (slow, ~2s/article).
        sections_filter: Comma-separated section name prefixes to include (empty = all).
        save_interval: Save intermediate results every N articles.
    """
    results = []
    now = datetime.now(timezone.utc).isoformat()
    seen_urls = set()
    pages_limit = max_pages if max_pages > 0 else MAX_PAGES_PER_SECTION

    # Filter sections if requested
    active_sections = SECTIONS
    if sections_filter:
        prefixes = [s.strip() for s in sections_filter.split(",")]
        active_sections = [
            s for s in SECTIONS
            if any(s["name"].startswith(p) for p in prefixes)
        ]
        log.info("Filtered to %d sections matching: %s", len(active_sections), sections_filter)

    # Prepare output directory
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    total_sections = len(active_sections)

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for si, section in enumerate(active_sections, 1):
            name = section["name"]
            path = section["path"]

            log.info("[%d/%d] Section '%s' (%s), max %d pages",
                     si, total_sections, name, section["label"], pages_limit)

            consecutive_empty = 0
            for page in range(1, pages_limit + 1):
                url = _page_url(path, page)
                _delay()

                articles = fetch_list_page(client, url, path)
                if not articles:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        log.info("Section '%s' page %d: 2 consecutive empty, stopping", name, page)
                        break
                    continue
                consecutive_empty = 0

                new_count = 0
                for art in articles:
                    if art["url"] in seen_urls:
                        continue
                    seen_urls.add(art["url"])
                    new_count += 1

                    content = ""
                    title = art["title"]

                    if fetch_content:
                        _delay()
                        fetched = fetch_article(client, art["url"])
                        content = fetched["content"]
                        if not title and fetched["title"]:
                            title = fetched["title"]

                    results.append({
                        "id": _make_id(art["url"]),
                        "title": title,
                        "url": art["url"],
                        "content": content,
                        "source": "chinaacc",
                        "section": name,
                        "label": section["label"],
                        "date": art["date"],
                        "crawled_at": now,
                    })

                log.info("Section '%s' page %d: %d articles (%d new), total %d",
                         name, page, len(articles), new_count, len(results))

                # Intermediate save
                if output_dir and save_interval > 0 and len(results) % save_interval < new_count:
                    _save_results(results, output_dir, intermediate=True)

    if output_dir:
        _save_results(results, output_dir, intermediate=False)

    return results


def _save_results(results: list, output_dir: str, intermediate: bool = False):
    """Save results to JSON file."""
    suffix = "_partial" if intermediate else ""
    out_path = os.path.join(output_dir, f"chinaacc{suffix}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log.info("Saved %d articles to %s", len(results), out_path)

    # Also save a summary/stats file
    stats = {
        "total_articles": len(results),
        "sections": {},
        "date_range": {"min": "", "max": ""},
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    dates = [r["date"] for r in results if r["date"]]
    if dates:
        stats["date_range"]["min"] = min(dates)
        stats["date_range"]["max"] = max(dates)
    for r in results:
        sec = r["section"]
        if sec not in stats["sections"]:
            stats["sections"][sec] = {"count": 0, "label": r["label"]}
        stats["sections"][sec]["count"] += 1

    stats_path = os.path.join(output_dir, f"stats{suffix}.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch chinaacc.com accounting/tax articles")
    parser.add_argument("--output", default="./out",
                        help="Output directory (default: ./out)")
    parser.add_argument("--max-pages", type=int, default=0,
                        help="Max pages per section (0 = 5, the site max)")
    parser.add_argument("--fetch-content", action="store_true",
                        help="Also fetch full article content (slow, ~2s/article)")
    parser.add_argument("--sections", default="",
                        help="Comma-separated section name prefixes to crawl (empty = all)")
    parser.add_argument("--save-interval", type=int, default=200,
                        help="Save intermediate results every N articles")
    args = parser.parse_args()
    results = fetch(args.output, max_pages=args.max_pages,
                    fetch_content=args.fetch_content,
                    sections_filter=args.sections,
                    save_interval=args.save_interval)
    print(f"\nDone. Total: {len(results)} articles.")
