#!/usr/bin/env python3
"""Fetcher: Provincial tax bureau websites (省级税务局).

Supports 4 CMS patterns found across Chinese provincial tax bureau sites:
  1. Hanweb CMS (江苏/浙江 etc.) - jpage/dataproxy.jsp XML API
  2. TRS WAS5 (上海) - was5/web/search POST XML API
  3. Tianjin shtml - direct HTML scrape from shtml-based pages
  4. Generic HTML scrape - fallback for other provinces

NOTE: Many provincial sites block VPS/datacenter IPs (guangdong, henan, sichuan,
hubei, hunan, anhui, fujian, beijing, chongqing, shandong). Verified working from
VPS: jiangsu, zhejiang, shanghai, tianjin.

Provincial sites follow the pattern: https://{province}.chinatax.gov.cn/

Usage:
    python src/fetchers/fetch_provincial.py --provinces jiangsu shanghai zhejiang
    python src/fetchers/fetch_provincial.py --provinces all --max-pages 5
    python src/fetchers/fetch_provincial.py --provinces guangdong jiangsu --no-detail
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
log = logging.getLogger("fetch_provincial")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# Province configuration: code -> (Chinese name, CMS type, policy column configs)
# CMS types: "hanweb" (jpage proxy), "was5" (TRS WAS5 XML POST), "shtml" (Tianjin), "generic"
#
# Verified working from VPS (2026-03-15):
#   jiangsu (Hanweb), zhejiang (Hanweb), shanghai (WAS5), tianjin (shtml)
# Blocked from VPS (datacenter IP restrictions):
#   guangdong, shandong(412), henan, sichuan, hubei, hunan(503), anhui(403),
#   fujian, beijing, chongqing(504)
PROVINCE_CONFIG = {
    # === VERIFIED WORKING ===
    "jiangsu": {
        "name": "江苏省",
        "authority": "国家税务总局江苏省税务局",
        "cms": "hanweb",
        "columns": [
            {"name": "latest_policy", "columnid": "8349", "unitid": "31591", "webid": "18"},
            {"name": "policy_interpret", "columnid": "8350", "unitid": "31591", "webid": "18"},
            {"name": "notice", "columnid": "8274", "unitid": "31591", "webid": "18"},
            {"name": "hot_qa", "columnid": "8353", "unitid": "31591", "webid": "18"},
        ],
    },
    "zhejiang": {
        "name": "浙江省",
        "authority": "国家税务总局浙江省税务局",
        "cms": "hanweb",
        "columns": [
            # unitids verified via jpage init JS blocks on column pages
            {"name": "latest_policy", "columnid": "13226", "unitid": "57907", "webid": "15"},
            {"name": "policy_interpret", "columnid": "13229", "unitid": "57907", "webid": "15"},
            {"name": "notice", "columnid": "13230", "unitid": "63222", "webid": "15"},
        ],
    },
    "shanghai": {
        "name": "上海市",
        "authority": "国家税务总局上海市税务局",
        "cms": "was5",
        # WAS5 POST XML API: channelid=123952 for zcfgk, 5598 total records
        "was5_channels": [
            {"name": "policy_law", "channelid": "123952"},
        ],
    },
    "tianjin": {
        "name": "天津市",
        "authority": "国家税务总局天津市税务局",
        "cms": "shtml",
        # Each section maps to a JSP page that lists shtml articles
        "sections": [
            {"name": "policy_files", "lmdm": "03", "fjdm": "11200000000"},
            {"name": "info_disclosure", "lmdm": "01", "fjdm": "11200000000"},
        ],
    },
    # === BLOCKED FROM VPS (kept for future residential proxy use) ===
    "guangdong": {
        "name": "广东省",
        "authority": "国家税务总局广东省税务局",
        "cms": "hanweb",
        "columns": [],  # Need residential IP to probe column IDs
    },
    "shandong": {
        "name": "山东省",
        "authority": "国家税务总局山东省税务局",
        "cms": "hanweb",
        "columns": [],  # Returns 412; needs residential IP
    },
    "beijing": {
        "name": "北京市",
        "authority": "国家税务总局北京市税务局",
        "cms": "hanweb",
        "columns": [],  # Connection refused from VPS
    },
    "chongqing": {
        "name": "重庆市",
        "authority": "国家税务总局重庆市税务局",
        "cms": "hanweb",
        "columns": [],  # Returns 504
    },
}

# Link patterns for extracting articles from HTML
LINK_PATTERN_ART = re.compile(
    r'<a[^>]*title="([^"]{8,})"[^>]*href="([^"]*art[^"]*)"[^>]*>',
    re.IGNORECASE,
)
LINK_PATTERN_GENERIC = re.compile(
    r'<a[^>]*href=["\']([^"\']*(?:content|art|zcfg|zcfw)[^"\']*)["\'][^>]*>([^<]{8,})</a>',
    re.IGNORECASE,
)
# jpage XML record pattern
JPAGE_RECORD = re.compile(
    r'<record><!\[CDATA\[(.*?)\]\]></record>',
    re.DOTALL,
)
# Match <a> tags with title and href in either order
JPAGE_LINK_TITLE_FIRST = re.compile(
    r'<a[^>]*title="([^"]*)"[^>]*href="([^"]*)"[^>]*>',
)
JPAGE_LINK_HREF_FIRST = re.compile(
    r'<a[^>]*href="([^"]*)"[^>]*title="([^"]*)"[^>]*>',
)
JPAGE_DATE = re.compile(r'<span>(\d{4}-\d{2}-\d{2})</span>')
JPAGE_TOTAL = re.compile(r'<totalrecord>(\d+)</totalrecord>')


def _headers(referer: str = "https://www.chinatax.gov.cn/") -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html, application/xml, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": referer,
    }


def _make_id(province: str, url: str) -> str:
    return hashlib.sha256(f"{province}:{url}".encode()).hexdigest()[:16]


def _normalize_url(href: str, province: str) -> str:
    """Normalize a relative URL to absolute."""
    base = f"https://{province}.chinatax.gov.cn"
    href = href.strip()
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return base + href
    if href.startswith("./"):
        return base + href[1:]
    if href.startswith("http"):
        return href
    return base + "/" + href


def _fetch_detail(client: httpx.Client, url: str, province: str) -> str:
    """Fetch article body text, truncated to 3000 chars."""
    try:
        time.sleep(3)
        resp = client.get(url, headers=_headers(f"https://{province}.chinatax.gov.cn/"), timeout=15)
        resp.encoding = "utf-8"
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        # Try common content div selectors
        for selector in ["div.TRS_Editor", "div.pages_content", "div.content",
                         "#zoom", "div.article_con", "div.con_text",
                         "div.news_cont_d_wrap", "div.wz_con"]:
            content_div = soup.select_one(selector)
            if content_div:
                text = content_div.get_text(separator="\n", strip=True)
                if len(text) > 50:
                    return text[:3000]
        body = soup.find("body")
        text = body.get_text(separator="\n", strip=True) if body else ""
        return text[:3000]
    except Exception as e:
        log.warning("Detail fetch failed for %s: %s", url, e)
        return ""


def _fetch_hanweb_jpage(
    client: httpx.Client,
    province: str,
    column: dict,
    max_pages: int,
    fetch_detail: bool,
    per_page: int = 30,
) -> list[dict]:
    """Fetch from Hanweb CMS jpage proxy API."""
    items = []
    base_url = f"https://{province}.chinatax.gov.cn"
    proxy_url = f"{base_url}/module/web/jpage/dataproxy.jsp"
    seen_urls = set()
    now = datetime.now(timezone.utc).isoformat()

    columnid = column["columnid"]
    unitid = column["unitid"]
    webid = column["webid"]
    col_name = column["name"]

    for page in range(max_pages):
        start = page * per_page
        end = start + per_page

        params = {
            "startrecord": str(start),
            "endrecord": str(end),
            "perpage": str(per_page),
            "col": "1",
            "webid": webid,
            "path": "/",
            "columnid": columnid,
            "sourceContentType": "1",
            "unitid": unitid,
        }

        try:
            time.sleep(3)
            log.info("[%s] Fetching %s page %d (records %d-%d)", province, col_name, page + 1, start, end)
            resp = client.get(proxy_url, params=params, headers=_headers(base_url + "/"), timeout=15)
            resp.encoding = "utf-8"

            if resp.status_code != 200:
                log.warning("[%s] jpage returned %d for page %d", province, resp.status_code, page + 1)
                break

            xml_text = resp.text

            # Extract total record count from first page
            if page == 0:
                total_m = JPAGE_TOTAL.search(xml_text)
                if total_m:
                    total = int(total_m.group(1))
                    log.info("[%s] Column %s total records: %d", province, col_name, total)

            # Parse records from XML CDATA
            page_count = 0
            for record_m in JPAGE_RECORD.finditer(xml_text):
                html_frag = record_m.group(1)
                date_m = JPAGE_DATE.search(html_frag)

                # Try both attribute orderings: title-first (jiangsu) and href-first (zhejiang)
                link_m = JPAGE_LINK_TITLE_FIRST.search(html_frag)
                if link_m:
                    title = link_m.group(1).strip()
                    href = link_m.group(2).strip()
                else:
                    link_m = JPAGE_LINK_HREF_FIRST.search(html_frag)
                    if link_m:
                        href = link_m.group(1).strip()
                        title = link_m.group(2).strip()
                    else:
                        continue
                date_str = date_m.group(1) if date_m else ""
                url = _normalize_url(href, province)

                if url in seen_urls or len(title) < 5:
                    continue
                seen_urls.add(url)

                content = ""
                if fetch_detail:
                    content = _fetch_detail(client, url, province)

                items.append({
                    "id": _make_id(province, url),
                    "title": title,
                    "url": url,
                    "content": content,
                    "source": f"provincial_{province}",
                    "type": f"provincial/{col_name}",
                    "province": province,
                    "date": date_str,
                    "crawled_at": now,
                })
                page_count += 1

            log.info("[%s] Column %s page %d: %d items (total so far: %d)",
                     province, col_name, page + 1, page_count, len(items))

            if page_count == 0:
                log.info("[%s] Column %s page %d empty, stopping", province, col_name, page + 1)
                break

        except Exception as e:
            log.error("[%s] Column %s page %d failed: %s", province, col_name, page + 1, e)
            break

    return items


def _fetch_was5(
    client: httpx.Client,
    province: str,
    channel: dict,
    max_pages: int,
    fetch_detail: bool,
    per_page: int = 15,
) -> list[dict]:
    """Fetch from TRS WAS5 search engine via POST XML API (used by Shanghai).

    The API returns structured XML with <REC> elements containing:
    TITLE, URL, WH (document number), DOCRELTIME (date), FWDW (issuing authority).
    """
    items = []
    base_url = f"https://{province}.chinatax.gov.cn"
    search_url = f"{base_url}/was5/web/search"
    seen_urls = set()
    now = datetime.now(timezone.utc).isoformat()

    channelid = channel["channelid"]
    ch_name = channel["name"]

    # WAS5 XML record patterns
    rec_pattern = re.compile(r'<REC>(.*?)</REC>', re.DOTALL)
    field_pattern = re.compile(r'<(\w+)><!\[CDATA\[(.*?)\]\]></\1>', re.DOTALL)

    for page in range(1, max_pages + 1):
        try:
            time.sleep(3)
            log.info("[%s] WAS5 fetching %s page %d", province, ch_name, page)

            post_data = {
                "channelid": channelid,
                "searchword": "",
                "extrasql": "",
                "page": str(page),
                "prepage": str(per_page),
            }

            resp = client.post(
                search_url,
                data=post_data,
                headers=_headers(base_url + "/"),
                timeout=15,
            )
            resp.encoding = "utf-8"

            if resp.status_code != 200:
                log.warning("[%s] WAS5 returned %d for page %d", province, resp.status_code, page)
                break

            xml_text = resp.text

            # Extract total from first page
            if page == 1:
                total_m = re.search(r'<RECORDCOUNT><!\[CDATA\[(\d+)\]\]></RECORDCOUNT>', xml_text)
                if total_m:
                    log.info("[%s] WAS5 channel %s total records: %s", province, ch_name, total_m.group(1))

            page_count = 0
            for rec_m in rec_pattern.finditer(xml_text):
                rec_text = rec_m.group(1)
                fields = {}
                for fm in field_pattern.finditer(rec_text):
                    fields[fm.group(1)] = fm.group(2).strip()

                title = fields.get("TITLE", "")
                href = fields.get("URL", "")
                if not title or not href or len(title) < 5:
                    continue

                url = _normalize_url(href, province)
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                date_str = fields.get("DOCRELTIME", fields.get("PRINTTIME", ""))
                doc_num = fields.get("WH", "")
                issuing_auth = fields.get("FWDW", "")

                content = ""
                if fetch_detail:
                    content = _fetch_detail(client, url, province)

                items.append({
                    "id": _make_id(province, url),
                    "title": title,
                    "url": url,
                    "content": content,
                    "source": f"provincial_{province}",
                    "type": f"provincial/{ch_name}",
                    "province": province,
                    "date": date_str,
                    "doc_num": doc_num,
                    "issuing_authority": issuing_auth,
                    "crawled_at": now,
                })
                page_count += 1

            log.info("[%s] WAS5 %s page %d: %d items (total: %d)",
                     province, ch_name, page, page_count, len(items))

            if page_count == 0:
                break

        except Exception as e:
            log.error("[%s] WAS5 %s page %d failed: %s", province, ch_name, page, e)
            break

    return items


def _fetch_shtml(
    client: httpx.Client,
    province: str,
    section: dict,
    max_pages: int,
    fetch_detail: bool,
) -> list[dict]:
    """Fetch from Tianjin-style shtml CMS (direct HTML scrape)."""
    items = []
    base_url = f"https://{province}.chinatax.gov.cn"
    seen_urls = set()
    now = datetime.now(timezone.utc).isoformat()

    lmdm = section["lmdm"]
    fjdm = section["fjdm"]
    sec_name = section["name"]

    # Tianjin stores articles in paths like /11200000000/0300/030004/03000418/YYYYMMDD.shtml
    # The JSP pages (sjsy_zcwj.jsp, sjsy_xxgk.jsp) list articles with shtml links.
    shtml_link = re.compile(
        r'<a[^>]*title="([^"]{8,})"[^>]*href="(/[^"]*\.shtml)"[^>]*>',
    )

    # Determine which JSP page to scrape based on section
    # lmdm starting with "03" = policy files page, "01" = info disclosure, "02" = news
    lm_prefix = lmdm[:2]
    jsp_map = {"03": "sjsy_zcwj.jsp", "01": "sjsy_xxgk.jsp", "02": "sjsy_xwdt.jsp"}
    jsp_page = jsp_map.get(lm_prefix, "sjsy_zcwj.jsp")

    # Tianjin lmdm doesn't map 1:1 to URL paths; e.g. lmdm "030001" -> /0300/030004/
    # So we just collect all shtml article links from the JSP page (already section-specific)

    try:
        time.sleep(3)
        log.info("[%s] shtml fetching section %s from %s", province, sec_name, jsp_page)

        resp = client.get(f"{base_url}/{jsp_page}", headers=_headers(base_url + "/"), timeout=15)
        resp.encoding = "utf-8"

        page_count = 0
        for m in shtml_link.finditer(resp.text):
            title, href = m.group(1).strip(), m.group(2).strip()

            url = _normalize_url(href, province)
            if url in seen_urls or len(title) < 8:
                continue
            seen_urls.add(url)

            # Extract date from path like /20260305143157405.shtml
            date_str = ""
            dm = re.search(r'/(\d{4})(\d{2})(\d{2})', href)
            if dm:
                date_str = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"

            content = ""
            if fetch_detail:
                content = _fetch_detail(client, url, province)

            items.append({
                "id": _make_id(province, url),
                "title": title,
                "url": url,
                "content": content,
                "source": f"provincial_{province}",
                "type": f"provincial/{sec_name}",
                "province": province,
                "date": date_str,
                "crawled_at": now,
            })
            page_count += 1

        log.info("[%s] shtml section %s: found %d items", province, sec_name, page_count)

    except Exception as e:
        log.error("[%s] shtml section %s failed: %s", province, sec_name, e)

    return items


def _fetch_generic(
    client: httpx.Client,
    province: str,
    max_pages: int,
    fetch_detail: bool,
) -> list[dict]:
    """Generic HTML scrape fallback for provinces with unknown CMS."""
    items = []
    base_url = f"https://{province}.chinatax.gov.cn"
    seen_urls = set()
    now = datetime.now(timezone.utc).isoformat()

    try:
        time.sleep(3)
        log.info("[%s] Generic scrape: fetching homepage", province)
        resp = client.get(base_url + "/", headers=_headers(), timeout=15)
        resp.encoding = "utf-8"

        for m in LINK_PATTERN_ART.finditer(resp.text):
            title, href = m.group(1).strip(), m.group(2).strip()
            url = _normalize_url(href, province)

            if url in seen_urls or len(title) < 8:
                continue
            seen_urls.add(url)

            content = ""
            if fetch_detail:
                content = _fetch_detail(client, url, province)

            items.append({
                "id": _make_id(province, url),
                "title": title,
                "url": url,
                "content": content,
                "source": f"provincial_{province}",
                "type": "provincial/homepage",
                "province": province,
                "date": "",
                "crawled_at": now,
            })

        log.info("[%s] Generic scrape: found %d items from homepage", province, len(items))

    except Exception as e:
        log.error("[%s] Generic scrape failed: %s", province, e)

    return items


def _probe_hanweb_columns(client: httpx.Client, province: str) -> list[dict]:
    """Auto-detect Hanweb CMS column IDs by scraping homepage JS.

    This is used when we don't have pre-configured column IDs for a province.
    It looks for jpage initialization JS blocks that contain columnid/unitid/webid.
    """
    base_url = f"https://{province}.chinatax.gov.cn"
    columns = []

    try:
        time.sleep(2)
        resp = client.get(base_url + "/", headers=_headers(base_url + "/"), timeout=15)
        resp.encoding = "utf-8"

        # Look for jpage init blocks like:
        # var param_31591 = {col:1,webid:18,...,columnid:8349,...,unitid:'31591',...}
        for m in re.finditer(
            r"var\s+param_(\d+)\s*=\s*\{([^}]+)\}",
            resp.text,
        ):
            block = m.group(2)
            col_m = re.search(r"columnid\s*:\s*['\"]?(\d+)", block)
            web_m = re.search(r"webid\s*:\s*['\"]?(\d+)", block)
            unit_m = re.search(r"unitid\s*:\s*['\"]?(\d+)", block)

            if col_m and web_m and unit_m:
                columns.append({
                    "name": f"auto_{col_m.group(1)}",
                    "columnid": col_m.group(1),
                    "webid": web_m.group(1),
                    "unitid": unit_m.group(1),
                })

        log.info("[%s] Auto-detected %d Hanweb columns", province, len(columns))
    except Exception as e:
        log.warning("[%s] Column probe failed: %s", province, e)

    return columns


def fetch_province(
    province: str,
    output_dir: str,
    max_pages: int = 5,
    fetch_detail: bool = True,
) -> list[dict]:
    """Fetch policy documents from a single province."""
    config = PROVINCE_CONFIG.get(province)
    if not config:
        log.warning("No config for province '%s', attempting generic scrape", province)
        config = {
            "name": province,
            "authority": f"国家税务总局{province}税务局",
            "cms": "generic",
        }

    log.info("=== Fetching %s (%s) [cms=%s] ===", province, config["name"], config["cms"])
    results = []

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        cms = config["cms"]

        if cms == "hanweb":
            columns = config.get("columns", [])
            # Auto-detect if no pre-configured columns
            if not columns:
                columns = _probe_hanweb_columns(client, province)

            for col in columns:
                col_items = _fetch_hanweb_jpage(
                    client, province, col, max_pages, fetch_detail,
                )
                results.extend(col_items)
                time.sleep(10)  # Pause between columns

        elif cms == "was5":
            channels = config.get("was5_channels", [])
            for ch in channels:
                ch_items = _fetch_was5(
                    client, province, ch, max_pages, fetch_detail,
                )
                results.extend(ch_items)
                time.sleep(10)

        elif cms == "shtml":
            sections = config.get("sections", [])
            for sec in sections:
                sec_items = _fetch_shtml(
                    client, province, sec, max_pages, fetch_detail,
                )
                results.extend(sec_items)
                time.sleep(10)

        else:
            results = _fetch_generic(client, province, max_pages, fetch_detail)

    # Save per-province output
    if output_dir and results:
        prov_dir = os.path.join(output_dir, province)
        os.makedirs(prov_dir, exist_ok=True)
        out_path = os.path.join(prov_dir, f"{province}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info("[%s] Saved %d items to %s", province, len(results), out_path)

    return results


def fetch(
    provinces: list[str],
    output_dir: str,
    max_pages: int = 5,
    fetch_detail: bool = True,
) -> list[dict]:
    """Fetch policy documents from multiple provinces."""
    if "all" in provinces:
        provinces = list(PROVINCE_CONFIG.keys())

    all_results = []
    for i, province in enumerate(provinces):
        log.info("--- Province %d/%d: %s ---", i + 1, len(provinces), province)
        try:
            items = fetch_province(province, output_dir, max_pages, fetch_detail)
            all_results.extend(items)
            log.info("[%s] Complete: %d items", province, len(items))
        except Exception as e:
            log.error("[%s] Failed: %s", province, e)

        # Pause between provinces
        if i < len(provinces) - 1:
            log.info("Pausing 10s before next province...")
            time.sleep(10)

    # Save combined summary
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        summary_path = os.path.join(output_dir, "provincial_summary.json")
        summary = {
            "total_items": len(all_results),
            "provinces_fetched": list(set(r["province"] for r in all_results)),
            "by_province": {},
            "crawled_at": datetime.now(timezone.utc).isoformat(),
        }
        for r in all_results:
            p = r["province"]
            if p not in summary["by_province"]:
                summary["by_province"][p] = 0
            summary["by_province"][p] += 1

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        log.info("Summary saved to %s", summary_path)

    log.info("=== TOTAL: %d items from %d provinces ===", len(all_results), len(set(r["province"] for r in all_results)) if all_results else 0)
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch provincial tax bureau policies")
    parser.add_argument(
        "--provinces",
        nargs="+",
        default=["jiangsu", "shanghai", "zhejiang"],
        help="Province codes to fetch (or 'all' for all configured provinces)",
    )
    parser.add_argument("--output", default="data/raw/20260315-provincial", help="Output directory")
    parser.add_argument("--max-pages", type=int, default=5, help="Max pages per column/channel")
    parser.add_argument("--no-detail", action="store_true", help="Skip fetching article body text")
    args = parser.parse_args()
    fetch(args.provinces, args.output, max_pages=args.max_pages, fetch_detail=not args.no_detail)
