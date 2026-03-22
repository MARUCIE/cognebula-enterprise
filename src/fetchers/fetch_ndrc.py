"""Fetcher: National Development and Reform Commission (ndrc.gov.cn) notices, announcements, and orders."""

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
log = logging.getLogger("fetch_ndrc")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

BASE_URL = "https://www.ndrc.gov.cn"
# Sections: notices, announcements, commission orders
SECTION_PATHS = [
    ("notice", "/xxgk/zcfb/tz/"),
    ("announcement", "/xxgk/zcfb/gg/"),
    ("commission_order", "/xxgk/zcfb/fzggwl/"),
]

# Build paginated URLs: index.html, index_1.html ... index_4.html (5 pages per section)
SECTIONS = []
for sec_name, sec_path in SECTION_PATHS:
    for page in range(5):
        suffix = "index.html" if page == 0 else f"index_{page}.html"
        SECTIONS.append((sec_name, f"{BASE_URL}{sec_path}{suffix}"))


def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": BASE_URL,
    }


def _make_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _resolve_url(href: str, section_url: str) -> str:
    """Resolve relative URLs against the section listing URL."""
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    # Relative path like ./YYYYMM/tXXX.html or ../../jd/jd/YYYYMM/tXXX.html
    from urllib.parse import urljoin
    return urljoin(section_url, href)


def _parse_listing(html: str, section_url: str = "") -> list[dict]:
    """Extract links from NDRC listing pages.

    NDRC uses relative paths: ./YYYYMM/tYYYYMMDD_ID.html or ../../jd/.../YYYYMM/tYYYYMMDD_ID.html
    """
    items = []
    seen_urls = set()

    # Strategy 1: BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        title = a_tag.get_text(strip=True)
        if not title or len(title) < 8:
            continue
        # Match NDRC content URLs: any path containing /YYYYMM/tYYYYMMDD_ID.html
        if re.search(r"\d{6}/t\d{8}_\d+\.html", href):
            full_url = _resolve_url(href, section_url)
            if full_url not in seen_urls:
                date_m = re.search(r"/t(\d{4})(\d{2})(\d{2})_", href)
                date_str = f"{date_m.group(1)}-{date_m.group(2)}-{date_m.group(3)}" if date_m else ""
                items.append({"title": title, "url": full_url, "date": date_str})
                seen_urls.add(full_url)

    # Strategy 2: Regex fallback
    if len(items) < 3:
        for m in re.finditer(
            r'<a[^>]*href="([^"]*?\d{6}/t\d{8}_\d+\.html)"[^>]*>([^<]{8,})</a>',
            html,
        ):
            href, title = m.group(1), m.group(2).strip()
            full_url = _resolve_url(href, section_url)
            if full_url not in seen_urls:
                date_m = re.search(r"/t(\d{4})(\d{2})(\d{2})_", href)
                date_str = f"{date_m.group(1)}-{date_m.group(2)}-{date_m.group(3)}" if date_m else ""
                items.append({"title": title, "url": full_url, "date": date_str})
                seen_urls.add(full_url)

    return items


def _fetch_via_fleet(url: str) -> str:
    """Fallback: fetch via fleet-page-fetch VPS browser proxy."""
    try:
        import subprocess
        result = subprocess.run(
            ["ssh", "kg-node", f"curl -sf 'http://100.106.223.39:19801/fetch' -X POST -H 'Content-Type: application/json' -d '{{\"url\": \"{url}\"}}'"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and result.stdout:
            import json as _json
            data = _json.loads(result.stdout)
            return data.get("markdown", data.get("text", ""))[:50000]
    except Exception as e:
        log.warning("Fleet fetch failed for %s: %s", url, e)
    return ""


def _fetch_detail(client: httpx.Client, url: str) -> tuple[str, str]:
    """Fetch full article body text. Falls back to fleet-page-fetch if httpx returns empty."""
    try:
        time.sleep(5)
        resp = client.get(url, headers=_headers(), timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract date from detail page
        date_str = ""
        date_el = soup.select_one("span.time, span.info-time, div.article-info, div.pub_border")
        if date_el:
            date_m = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", date_el.get_text())
            if date_m:
                date_str = date_m.group(1)

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        content_div = soup.select_one("div.TRS_Editor, div.article-content, div.detail-content, div.content, #zoom")
        text = content_div.get_text(separator="\n", strip=True) if content_div else ""
        if not text:
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else ""
        if len(text) >= 100:
            return text[:50000], date_str
    except Exception as e:
        log.warning("Detail fetch failed for %s: %s", url, e)

    # Fallback: browser rendering via VPS
    log.info("Trying fleet-page-fetch fallback for %s", url)
    fleet_text = _fetch_via_fleet(url)
    return fleet_text, ""


def fetch(output_dir: str, fetch_detail: bool = True) -> list[dict]:
    results = []
    now = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for section_name, section_url in SECTIONS:
            try:
                time.sleep(5)
                log.info("Fetching section '%s': %s", section_name, section_url)
                resp = client.get(section_url, headers=_headers())
                resp.encoding = "utf-8"
                entries = _parse_listing(resp.text, section_url)
                log.info("Found %d entries in section '%s'", len(entries), section_name)

                for entry in entries:
                    content = ""
                    date = entry["date"]
                    if fetch_detail:
                        content, detail_date = _fetch_detail(client, entry["url"])
                        if detail_date:
                            date = detail_date
                    results.append({
                        "id": _make_id(entry["url"]),
                        "title": entry["title"],
                        "url": entry["url"],
                        "content": content,
                        "source": "ndrc",
                        "type": section_name,
                        "date": date,
                        "crawled_at": now,
                    })
            except Exception as e:
                log.error("Section '%s' failed: %s", section_name, e)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "ndrc.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(results), out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch NDRC notices, announcements, and orders")
    parser.add_argument("--output", default="./out", help="Output directory")
    parser.add_argument("--no-detail", action="store_true", help="Skip fetching article body")
    args = parser.parse_args()
    fetch(args.output, fetch_detail=not args.no_detail)
