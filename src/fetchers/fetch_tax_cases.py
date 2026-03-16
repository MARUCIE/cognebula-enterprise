#!/usr/bin/env python3
"""Fetcher: Tax enforcement cases from multiple public sources.

Combines three data sources for tax judicial/enforcement data:
  1. ChinaTax 税案通报 (Tax Case Reports) - SAT official case disclosures
  2. ChinaTax FGK keyword search - Policy documents mentioning penalties
  3. Provincial tax bureau penalty disclosures (Jiangsu, Shanghai, Zhejiang, Tianjin)

Each case record includes structured fields extracted from article text:
  - title, url, date, content (full text)
  - case_parties, violation_types, tax_types, penalty_amounts
  - legal_basis, issuing_authority, province

This is the HIGHEST competitive moat data source -- scattered across thousands
of sites, nobody has done systematic structuring.

Usage:
    python src/fetchers/fetch_tax_cases.py --output data/raw/tax-cases
    python src/fetchers/fetch_tax_cases.py --sources sat_cases --max-pages 1
    python src/fetchers/fetch_tax_cases.py --sources sat_cases,provincial --provinces jiangsu shanghai
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
log = logging.getLogger("fetch_tax_cases")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

BASE_URL = "https://www.chinatax.gov.cn"

# Known violation type keywords for structured extraction
VIOLATION_KEYWORDS = [
    "虚开增值税专用发票", "虚开发票", "虚开", "骗取出口退税", "骗税",
    "偷税", "逃税", "逃避缴纳税款", "逃避追缴欠税", "欠税",
    "隐匿收入", "虚假申报", "拒不缴纳税款", "走逃失联",
    "私印发票", "伪造发票", "变造发票", "非法代开发票",
]

# Known tax type keywords
TAX_TYPE_KEYWORDS = [
    "增值税", "企业所得税", "个人所得税", "消费税", "关税",
    "出口退税", "城建税", "城市维护建设税", "房产税", "印花税",
    "土地增值税", "资源税", "环保税", "车辆购置税", "契税",
]


def _headers(referer: str = BASE_URL + "/") -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html, application/xml, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": referer,
    }


def _make_id(source: str, url: str) -> str:
    return hashlib.sha256(f"{source}:{url}".encode()).hexdigest()[:16]


def _get_chinatax_cookies(client: httpx.Client) -> dict:
    """Get C3VK anti-bot cookie from chinatax.gov.cn."""
    try:
        resp = client.get(BASE_URL + "/", headers=_headers(), timeout=10)
        cookies = dict(resp.cookies)
        m = re.search(r"C3VK=([^;]+)", resp.text)
        if m:
            cookies["C3VK"] = m.group(1)
        return cookies
    except Exception as e:
        log.warning("Cookie fetch failed: %s", e)
        return {}


def _extract_structured_fields(content: str) -> dict:
    """Extract structured enforcement data from article text.

    Returns dict with:
      violation_types, tax_types, penalty_amounts, legal_basis, case_parties
    """
    if not content:
        return {}

    # Violation types (longest match first to avoid partial matches)
    sorted_violations = sorted(VIOLATION_KEYWORDS, key=len, reverse=True)
    violations = []
    for kw in sorted_violations:
        if kw in content and kw not in violations:
            # Avoid duplicates from substring matches
            is_substring = any(kw != v and kw in v for v in violations)
            if not is_substring:
                violations.append(kw)

    # Tax types
    tax_types = [kw for kw in TAX_TYPE_KEYWORDS if kw in content]

    # Penalty amounts: look for monetary amounts near penalty keywords
    amounts = re.findall(
        r'(?:罚款|处罚|追缴|补缴|退税款?|涉案金额|税款)[^。，]{0,30}?'
        r'(\d[\d,.]+(?:万元|亿元|元))',
        content,
    )
    # Also capture standalone large amounts
    all_amounts = re.findall(r'(\d[\d,.]+(?:亿元|万元))', content)
    # Merge, deduplicate, keep order
    seen = set()
    merged_amounts = []
    for a in amounts + all_amounts:
        if a not in seen:
            seen.add(a)
            merged_amounts.append(a)

    # Legal basis: text within 《》 brackets
    laws = re.findall(r'《([^》]+)》', content)
    unique_laws = list(dict.fromkeys(laws))

    # Case parties: company names (XX有限公司, XX股份有限公司, etc.)
    companies = re.findall(
        r'([\u4e00-\u9fff]{2,}(?:有限公司|股份有限公司|合伙企业|个体工商户|集团公司))',
        content,
    )
    unique_companies = list(dict.fromkeys(companies))[:10]

    # Person names: Chinese names are typically 2-3 chars after "以XX为实际控制人"
    # or "法定代表人XX" patterns
    persons = []
    # Pattern 1: 以XX为实际控制人
    for m in re.finditer(r'以([\u4e00-\u9fff]{2,3})为实际控制人', content):
        persons.append(m.group(1))
    # Pattern 2: 法定代表人（或负责人）XX，
    for m in re.finditer(
        r'(?:法定代表人|实际控制人|犯罪嫌疑人|被告人)\s*(?:为|是|：|:)\s*'
        r'([\u4e00-\u9fff]{2,3})(?:等|，|,|\s|。)',
        content,
    ):
        persons.append(m.group(1))
    # Filter out verbs and non-name words
    verb_blacklist = {"表示", "供述", "交代", "承认", "辩称", "认为", "指出", "强调"}
    persons = [p for p in persons if p not in verb_blacklist]
    unique_persons = list(dict.fromkeys(persons))[:5]

    return {
        "violation_types": violations,
        "tax_types": tax_types,
        "penalty_amounts": merged_amounts[:10],
        "legal_basis": unique_laws[:10],
        "case_parties_companies": unique_companies,
        "case_parties_persons": unique_persons,
    }


def _fetch_article_detail(
    client: httpx.Client,
    url: str,
    cookies: dict | None = None,
) -> tuple[str, str, str]:
    """Fetch article body text, date, and source info.

    Returns (content, date_str, source_info).
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        log.warning("bs4 not installed, skipping detail fetch")
        return "", "", ""

    try:
        time.sleep(3)
        kwargs = {"headers": _headers(url), "timeout": 15}
        if cookies:
            kwargs["cookies"] = cookies
        resp = client.get(url, **kwargs)
        resp.encoding = "utf-8"

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Extract date
        date_str = ""
        date_el = soup.select_one(".date, .tts_time, .pages_info")
        if date_el:
            date_text = date_el.get_text(strip=True)
            dm = re.search(r'(\d{4}[-/]\d{2}[-/]\d{2})', date_text)
            if dm:
                date_str = dm.group(1).replace("/", "-")

        # Extract source authority
        source_info = ""
        for sel in [".source", ".tts_source", ".ly"]:
            el = soup.select_one(sel)
            if el:
                source_info = el.get_text(strip=True)[:100]
                break

        # Extract content
        content = ""
        for sel in [
            "#fontzoom", "div.tts_editor_view", "div.TRS_Editor",
            "div.pages_content", "div.content", "#zoom",
            "div.article_con", "div.wz_con", "div.nr_content",
        ]:
            content_div = soup.select_one(sel)
            if content_div:
                content = content_div.get_text(separator="\n", strip=True)
                if len(content) > 50:
                    break

        if not content:
            body = soup.find("body")
            if body:
                content = body.get_text(separator="\n", strip=True)

        return content[:5000], date_str, source_info

    except Exception as e:
        log.warning("Detail fetch failed for %s: %s", url, e)
        return "", "", ""


# ---------------------------------------------------------------------------
# Source 1: SAT Tax Case Reports (税案通报)
# ---------------------------------------------------------------------------

def fetch_sat_case_reports(
    client: httpx.Client,
    cookies: dict,
    fetch_detail: bool = True,
) -> list[dict]:
    """Fetch from SAT official 税案通报 (Tax Case Reports) column.

    URL: https://www.chinatax.gov.cn/chinatax/n810219/c102025/common_listwyc.html
    Contains detailed enforcement case narratives published by SAT.
    """
    log.info("=== Source: SAT Tax Case Reports (税案通报) ===")
    results = []
    now = datetime.now(timezone.utc).isoformat()

    url = BASE_URL + "/chinatax/n810219/c102025/common_listwyc.html"
    try:
        resp = client.get(url, headers=_headers(), cookies=cookies, timeout=15)
        resp.encoding = "utf-8"

        if resp.status_code != 200:
            log.warning("Tax case reports page returned %d", resp.status_code)
            return results

        # Extract article links -- try both attribute orderings
        links_a = re.findall(
            r'href="(/chinatax/n810219/c102025/c\d+/content\.html)"[^>]*title="([^"]*)"',
            resp.text,
        )
        links_b = re.findall(
            r'title="([^"]*)"[^>]*href="(/chinatax/n810219/c102025/c\d+/content\.html)"',
            resp.text,
        )
        # Normalize to (path, title)
        all_links = [(u, t) for u, t in links_a] + [(u, t) for t, u in links_b]

        # Deduplicate by path
        seen = set()
        unique_links = []
        for path, title in all_links:
            if path not in seen:
                seen.add(path)
                unique_links.append((path, title))

        log.info("Found %d unique article links on tax case reports page", len(unique_links))

        for i, (path, title) in enumerate(unique_links):
            title = re.sub(r"<[^>]+>", "", title).strip()
            article_url = BASE_URL + path

            content = ""
            date_str = ""
            source_info = ""
            structured = {}

            if fetch_detail:
                # Refresh cookies before every 3rd article to avoid JS challenge
                if i > 0 and i % 3 == 0:
                    cookies = _get_chinatax_cookies(client)
                    time.sleep(1)

                content, date_str, source_info = _fetch_article_detail(
                    client, article_url, cookies,
                )

                # Retry once if content is empty (JS challenge likely expired cookie)
                if not content or len(content) < 50:
                    log.info("  Retrying %s (empty content, refreshing cookie)", title[:40])
                    cookies = _get_chinatax_cookies(client)
                    time.sleep(2)
                    content, date_str, source_info = _fetch_article_detail(
                        client, article_url, cookies,
                    )

                structured = _extract_structured_fields(content)

            full_text = title
            if content:
                full_text = f"{title}\n\n{content}"

            results.append({
                "id": _make_id("sat_case_report", article_url),
                "title": title,
                "url": article_url,
                "content": content[:3000],
                "full_text": full_text[:5000],
                "source": "sat_case_report",
                "source_column": "税案通报",
                "type": "enforcement/case_report",
                "date": date_str,
                "source_authority": source_info or "国家税务总局",
                "crawled_at": now,
                **structured,
            })

            log.info("[%d/%d] %s (%s)", i + 1, len(unique_links), title[:50], date_str)

    except Exception as e:
        log.error("Failed to fetch SAT case reports: %s", e)

    log.info("SAT case reports: %d items", len(results))
    return results


# ---------------------------------------------------------------------------
# Source 2: ChinaTax FGK API keyword search for enforcement content
# ---------------------------------------------------------------------------

FGK_ENFORCEMENT_KEYWORDS = [
    "行政处罚决定",
    "税务行政处罚",
    "重大税收违法失信",
    "税务稽查",
    "偷税案件",
    "虚开发票",
    "骗取出口退税",
]


def fetch_fgk_enforcement_search(
    client: httpx.Client,
    cookies: dict,
    max_pages: int = 3,
    fetch_detail: bool = False,
) -> list[dict]:
    """Search FGK policy database for enforcement-related documents.

    Uses the search5 API with enforcement keywords. The FGK API is the same
    one used by fetch_chinatax_api.py but with penalty/enforcement search terms.

    NOTE: The FGK search API sometimes ignores the q parameter and returns
    generic results. Results should be filtered by title keywords.
    """
    log.info("=== Source: FGK API Enforcement Keyword Search ===")
    results = []
    seen_urls = set()
    now = datetime.now(timezone.utc).isoformat()

    search_url = BASE_URL + "/search5/search/s"

    for keyword in FGK_ENFORCEMENT_KEYWORDS:
        log.info("Searching FGK for keyword: %s", keyword)

        for page in range(max_pages):
            time.sleep(3)

            # Refresh cookies periodically
            if page > 0 and page % 3 == 0:
                cookies = _get_chinatax_cookies(client)
                time.sleep(1)

            params = {
                "siteCode": "bm29000002",
                "searchSiteName": "GSFFK",
                "pageNum": str(page),
                "pageSize": "10",
                "q": keyword,
            }

            try:
                resp = client.get(
                    search_url,
                    params=params,
                    headers=_headers(),
                    cookies=cookies,
                    timeout=15,
                )

                if not resp.text.strip().startswith("{"):
                    log.warning("FGK returned non-JSON for '%s' page %d", keyword, page)
                    cookies = _get_chinatax_cookies(client)
                    time.sleep(1)
                    continue

                data = resp.json()
                search_all = data.get("searchResultAll", {})
                items = search_all.get("searchTotal", [])

                if not items:
                    break

                page_new = 0
                for item in items:
                    raw_title = item.get("title", "")
                    title = re.sub(r"<[^>]+>", "", raw_title).strip()
                    item_url = item.get("url", "")
                    if not item_url:
                        continue
                    if not item_url.startswith("http"):
                        item_url = BASE_URL + item_url

                    if item_url in seen_urls:
                        continue

                    # Filter: only keep items with enforcement-related titles
                    enforcement_signals = [
                        "处罚", "稽查", "违法", "失信", "偷税", "骗税",
                        "虚开", "案件", "查处", "追缴", "罚款",
                    ]
                    if not any(sig in title for sig in enforcement_signals):
                        continue

                    seen_urls.add(item_url)
                    page_new += 1

                    raw_content = item.get("content", "")
                    content = re.sub(r"<[^>]+>", "", raw_content).strip()
                    date_str = item.get("cwrq", item.get("publishDate", ""))
                    label = item.get("label", "")

                    results.append({
                        "id": _make_id("fgk_enforcement", item_url),
                        "title": title,
                        "url": item_url,
                        "content": content[:3000],
                        "full_text": f"{title}\n\n{content[:3000]}",
                        "source": "fgk_enforcement",
                        "source_column": label or "政策法规库",
                        "type": "enforcement/policy_doc",
                        "date": date_str,
                        "search_keyword": keyword,
                        "crawled_at": now,
                    })

                log.info("FGK '%s' page %d: %d items (%d enforcement-related)",
                         keyword, page, len(items), page_new)

                if page_new == 0:
                    break  # No more relevant results

            except Exception as e:
                log.warning("FGK search failed for '%s' page %d: %s", keyword, page, e)
                break

    log.info("FGK enforcement search: %d items", len(results))
    return results


# ---------------------------------------------------------------------------
# Source 3: Provincial tax bureau penalty/enforcement content
# ---------------------------------------------------------------------------

# Provincial enforcement column IDs (discovered via provincial fetcher)
# These are specific columns on provincial sites that contain penalty disclosures
PROVINCIAL_ENFORCEMENT_CONFIGS = {
    "jiangsu": {
        "name": "江苏省",
        "authority": "国家税务总局江苏省税务局",
        "cms": "hanweb",
        # Jiangsu has enforcement info in notice columns
        "columns": [
            {"name": "notice", "columnid": "8274", "unitid": "31591", "webid": "18"},
        ],
        "filter_keywords": ["处罚", "稽查", "违法", "失信", "案件", "查处"],
    },
    "zhejiang": {
        "name": "浙江省",
        "authority": "国家税务总局浙江省税务局",
        "cms": "hanweb",
        "columns": [
            {"name": "notice", "columnid": "13230", "unitid": "63222", "webid": "15"},
        ],
        "filter_keywords": ["处罚", "稽查", "违法", "失信", "案件", "查处"],
    },
    "shanghai": {
        "name": "上海市",
        "authority": "国家税务总局上海市税务局",
        "cms": "was5",
        # Shanghai uses WAS5 with channelid for policy law database
        "was5_channels": [
            {"name": "policy_law", "channelid": "123952"},
        ],
        "filter_keywords": ["处罚", "稽查", "违法", "失信", "案件", "查处"],
    },
}

# Hanweb jpage patterns (reused from fetch_provincial.py)
JPAGE_RECORD = re.compile(r'<record><!\[CDATA\[(.*?)\]\]></record>', re.DOTALL)
JPAGE_LINK_TITLE_FIRST = re.compile(r'<a[^>]*title="([^"]*)"[^>]*href="([^"]*)"[^>]*>')
JPAGE_LINK_HREF_FIRST = re.compile(r'<a[^>]*href="([^"]*)"[^>]*title="([^"]*)"[^>]*>')
JPAGE_DATE = re.compile(r'<span>(\d{4}-\d{2}-\d{2})</span>')
JPAGE_TOTAL = re.compile(r'<totalrecord>(\d+)</totalrecord>')

# WAS5 XML patterns
WAS5_REC = re.compile(r'<REC>(.*?)</REC>', re.DOTALL)
WAS5_FIELD = re.compile(r'<(\w+)><!\[CDATA\[(.*?)\]\]></\1>', re.DOTALL)


def _normalize_provincial_url(href: str, province: str) -> str:
    base = f"https://{province}.chinatax.gov.cn"
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return base + href
    return base + "/" + href


def _fetch_hanweb_enforcement(
    client: httpx.Client,
    province: str,
    config: dict,
    max_pages: int,
    fetch_detail: bool,
) -> list[dict]:
    """Fetch enforcement-related items from Hanweb CMS provincial site."""
    items = []
    base_url = f"https://{province}.chinatax.gov.cn"
    proxy_url = f"{base_url}/module/web/jpage/dataproxy.jsp"
    now = datetime.now(timezone.utc).isoformat()
    filter_keywords = config.get("filter_keywords", [])
    authority = config["authority"]

    for column in config.get("columns", []):
        columnid = column["columnid"]
        unitid = column["unitid"]
        webid = column["webid"]
        col_name = column["name"]
        per_page = 30

        for page in range(max_pages):
            start = page * per_page
            end = start + per_page
            time.sleep(3)

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
                resp = client.get(
                    proxy_url,
                    params=params,
                    headers=_headers(base_url + "/"),
                    timeout=15,
                )
                resp.encoding = "utf-8"

                if resp.status_code != 200:
                    break

                page_count = 0
                for rec_m in JPAGE_RECORD.finditer(resp.text):
                    html_frag = rec_m.group(1)
                    date_m = JPAGE_DATE.search(html_frag)

                    link_m = JPAGE_LINK_TITLE_FIRST.search(html_frag)
                    if link_m:
                        title, href = link_m.group(1).strip(), link_m.group(2).strip()
                    else:
                        link_m = JPAGE_LINK_HREF_FIRST.search(html_frag)
                        if link_m:
                            href, title = link_m.group(1).strip(), link_m.group(2).strip()
                        else:
                            continue

                    date_str = date_m.group(1) if date_m else ""
                    url = _normalize_provincial_url(href, province)

                    # Filter for enforcement content
                    if filter_keywords and not any(kw in title for kw in filter_keywords):
                        continue

                    content = ""
                    if fetch_detail:
                        content, _, _ = _fetch_article_detail(client, url)

                    structured = _extract_structured_fields(f"{title}\n{content}")

                    items.append({
                        "id": _make_id(f"provincial_{province}", url),
                        "title": title,
                        "url": url,
                        "content": content[:3000],
                        "full_text": f"{title}\n\n{content[:3000]}" if content else title,
                        "source": f"provincial_{province}",
                        "source_column": col_name,
                        "type": "enforcement/provincial_penalty",
                        "province": province,
                        "date": date_str,
                        "source_authority": authority,
                        "crawled_at": now,
                        **structured,
                    })
                    page_count += 1

                log.info("[%s] %s page %d: %d enforcement items",
                         province, col_name, page + 1, page_count)

                if page_count == 0 and page > 0:
                    break

            except Exception as e:
                log.warning("[%s] %s page %d failed: %s", province, col_name, page + 1, e)
                break

    return items


def _fetch_was5_enforcement(
    client: httpx.Client,
    province: str,
    config: dict,
    max_pages: int,
    fetch_detail: bool,
) -> list[dict]:
    """Fetch enforcement-related items from WAS5 provincial site."""
    items = []
    base_url = f"https://{province}.chinatax.gov.cn"
    search_url = f"{base_url}/was5/web/search"
    now = datetime.now(timezone.utc).isoformat()
    filter_keywords = config.get("filter_keywords", [])
    authority = config["authority"]

    for channel in config.get("was5_channels", []):
        channelid = channel["channelid"]
        ch_name = channel["name"]

        for page in range(1, max_pages + 1):
            time.sleep(3)

            try:
                post_data = {
                    "channelid": channelid,
                    "searchword": "",
                    "page": str(page),
                    "prepage": "15",
                }
                resp = client.post(
                    search_url,
                    data=post_data,
                    headers=_headers(base_url + "/"),
                    timeout=15,
                )
                resp.encoding = "utf-8"

                page_count = 0
                for rec_m in WAS5_REC.finditer(resp.text):
                    fields = {}
                    for fm in WAS5_FIELD.finditer(rec_m.group(1)):
                        fields[fm.group(1)] = fm.group(2).strip()

                    title = re.sub(r"<[^>]+>", "", fields.get("TITLE", ""))
                    href = fields.get("URL", "")
                    if not title or not href:
                        continue

                    # Filter for enforcement content
                    if filter_keywords and not any(kw in title for kw in filter_keywords):
                        continue

                    url = _normalize_provincial_url(href, province)
                    date_str = fields.get("DOCRELTIME", "")
                    doc_num = fields.get("WH", "")

                    content = ""
                    if fetch_detail:
                        content, _, _ = _fetch_article_detail(client, url)

                    structured = _extract_structured_fields(f"{title}\n{content}")

                    items.append({
                        "id": _make_id(f"provincial_{province}", url),
                        "title": title,
                        "url": url,
                        "content": content[:3000],
                        "full_text": f"{title}\n\n{content[:3000]}" if content else title,
                        "source": f"provincial_{province}",
                        "source_column": ch_name,
                        "type": "enforcement/provincial_penalty",
                        "province": province,
                        "date": date_str,
                        "doc_num": doc_num,
                        "source_authority": authority,
                        "crawled_at": now,
                        **structured,
                    })
                    page_count += 1

                log.info("[%s] WAS5 %s page %d: %d enforcement items",
                         province, ch_name, page, page_count)

                if page_count == 0:
                    break

            except Exception as e:
                log.warning("[%s] WAS5 %s page %d failed: %s", province, ch_name, page, e)
                break

    return items


def fetch_provincial_enforcement(
    provinces: list[str] | None = None,
    max_pages: int = 3,
    fetch_detail: bool = True,
) -> list[dict]:
    """Fetch enforcement data from provincial tax bureau sites.

    Creates its own httpx.Client per province to avoid cross-site cookie issues.
    """
    log.info("=== Source: Provincial Tax Bureau Enforcement ===")

    if provinces is None:
        provinces = list(PROVINCIAL_ENFORCEMENT_CONFIGS.keys())

    results = []
    for province in provinces:
        config = PROVINCIAL_ENFORCEMENT_CONFIGS.get(province)
        if not config:
            log.warning("No enforcement config for province '%s'", province)
            continue

        log.info("Fetching enforcement from %s (%s)", province, config["name"])
        cms = config.get("cms", "hanweb")

        try:
            with httpx.Client(timeout=15, follow_redirects=True) as prov_client:
                if cms == "hanweb":
                    items = _fetch_hanweb_enforcement(
                        prov_client, province, config, max_pages, fetch_detail,
                    )
                elif cms == "was5":
                    items = _fetch_was5_enforcement(
                        prov_client, province, config, max_pages, fetch_detail,
                    )
                else:
                    items = []

                results.extend(items)
                log.info("[%s] Total enforcement items: %d", province, len(items))

        except Exception as e:
            log.error("[%s] Provincial enforcement failed: %s", province, e)

        time.sleep(5)

    log.info("Provincial enforcement total: %d items", len(results))
    return results


# ---------------------------------------------------------------------------
# Source 4: Filter existing 12366 data for enforcement-related QA
# ---------------------------------------------------------------------------

def filter_12366_enforcement(input_dir: str = "data/raw") -> list[dict]:
    """Scan existing 12366 crawl data for enforcement/penalty QA items.

    Looks for 12366 JSON files in input_dir and filters items whose title
    or content mentions enforcement keywords.
    """
    log.info("=== Source: 12366 Enforcement Filter ===")
    results = []
    now = datetime.now(timezone.utc).isoformat()

    enforcement_signals = [
        "行政处罚", "税务稽查", "偷税", "骗税", "虚开", "欠税",
        "违法", "失信", "罚款", "追缴", "查处", "处罚决定",
    ]

    # Look for 12366 JSON files
    import glob
    patterns = [
        os.path.join(input_dir, "**", "12366*.json"),
        os.path.join(input_dir, "**", "*12366*.json"),
    ]

    json_files = []
    for pat in patterns:
        json_files.extend(glob.glob(pat, recursive=True))

    log.info("Found %d 12366 JSON files to scan", len(json_files))

    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                continue

            file_hits = 0
            for item in data:
                title = item.get("title", "") or item.get("question", "")
                content = item.get("content", "") or item.get("answer", "")
                combined = f"{title} {content}"

                if any(sig in combined for sig in enforcement_signals):
                    results.append({
                        "id": item.get("id", _make_id("12366_enforcement", title)),
                        "title": title[:300],
                        "url": item.get("url", ""),
                        "content": content[:3000],
                        "full_text": f"{title}\n\n{content[:3000]}",
                        "source": "12366_enforcement",
                        "source_column": "12366热线",
                        "type": "enforcement/qa",
                        "date": item.get("date", ""),
                        "crawled_at": now,
                    })
                    file_hits += 1

            if file_hits:
                log.info("  %s: %d enforcement-related items", os.path.basename(fpath), file_hits)

        except Exception as e:
            log.warning("Failed to process %s: %s", fpath, e)

    log.info("12366 enforcement filter: %d items", len(results))
    return results


# ---------------------------------------------------------------------------
# Main fetch orchestrator
# ---------------------------------------------------------------------------

ALL_SOURCES = ["sat_cases", "fgk_search", "provincial", "12366_filter"]


def fetch(
    output_dir: str,
    sources: list[str] | None = None,
    provinces: list[str] | None = None,
    max_pages: int = 3,
    fetch_detail: bool = True,
    raw_data_dir: str = "data/raw",
) -> list[dict]:
    """Fetch tax enforcement cases from all configured sources."""
    if sources is None:
        sources = ALL_SOURCES

    all_results = []

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        cookies = {}
        if any(s in sources for s in ["sat_cases", "fgk_search"]):
            cookies = _get_chinatax_cookies(client)
            time.sleep(1)

        # Source 1: SAT case reports
        if "sat_cases" in sources:
            items = fetch_sat_case_reports(client, cookies, fetch_detail)
            all_results.extend(items)
            time.sleep(3)

        # Source 2: FGK enforcement keyword search
        if "fgk_search" in sources:
            cookies = _get_chinatax_cookies(client)
            time.sleep(1)
            items = fetch_fgk_enforcement_search(
                client, cookies, max_pages, fetch_detail=False,
            )
            all_results.extend(items)
            time.sleep(3)

    # Source 3: Provincial enforcement (uses separate client per province)
    if "provincial" in sources:
        items = fetch_provincial_enforcement(
            provinces,
            max_pages,
            fetch_detail,
        )
        all_results.extend(items)

    # Source 4: 12366 filter
    if "12366_filter" in sources:
        items = filter_12366_enforcement(raw_data_dir)
        all_results.extend(items)

    # Save output
    if output_dir and all_results:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "tax_cases.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        log.info("Saved %d items to %s", len(all_results), out_path)

        # Save summary
        summary = {
            "total_items": len(all_results),
            "by_source": {},
            "by_type": {},
            "crawled_at": datetime.now(timezone.utc).isoformat(),
        }
        for r in all_results:
            src = r.get("source", "unknown")
            summary["by_source"][src] = summary["by_source"].get(src, 0) + 1
            typ = r.get("type", "unknown")
            summary["by_type"][typ] = summary["by_type"].get(typ, 0) + 1

        summary_path = os.path.join(output_dir, "tax_cases_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        log.info("Summary saved to %s", summary_path)

    log.info("=== TOTAL: %d tax enforcement items ===", len(all_results))
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch tax enforcement cases")
    parser.add_argument("--output", default="data/raw/tax-cases",
                        help="Output directory")
    parser.add_argument("--sources", default=None,
                        help="Comma-separated sources: sat_cases,fgk_search,provincial,12366_filter")
    parser.add_argument("--provinces", nargs="*", default=None,
                        help="Provinces for provincial source")
    parser.add_argument("--max-pages", type=int, default=3,
                        help="Max pages per source/keyword")
    parser.add_argument("--no-detail", action="store_true",
                        help="Skip fetching article body text")
    parser.add_argument("--raw-data-dir", default="data/raw",
                        help="Directory with existing raw data (for 12366 filter)")
    args = parser.parse_args()

    sources = args.sources.split(",") if args.sources else None

    fetch(
        output_dir=args.output,
        sources=sources,
        provinces=args.provinces,
        max_pages=args.max_pages,
        fetch_detail=not args.no_detail,
        raw_data_dir=args.raw_data_dir,
    )
