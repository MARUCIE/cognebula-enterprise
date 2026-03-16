#!/usr/bin/env python3
"""Cloudflare Browser Rendering API fetcher for finance/tax knowledge base.

Leverages CF Browser Rendering REST API for:
1. /crawl - Async multi-page crawling with JS rendering (for SPA sites)
2. /json  - AI-powered structured data extraction
3. /scrape - CSS selector-based element extraction

Key use cases:
- NPC (全人大): Vue SPA, needs JS rendering
- SAMR (市场监管总局): Hanweb CMS, JS-rendered listings
- MIIT (工信部): Hanweb CMS, JS-rendered
- Any site with dynamic content our httpx fetchers can't handle

Setup:
    export CF_ACCOUNT_ID=<your-account-id>
    export CF_API_TOKEN=<your-api-token-with-browser-rendering-edit>

Usage:
    # Crawl a site (async, returns job ID)
    python fetch_cf_browser.py crawl --url https://www.npc.gov.cn/flcaw/ --limit 50 --depth 2

    # Extract structured data from a page
    python fetch_cf_browser.py json --url https://www.samr.gov.cn/fldys/ --prompt "提取所有法规标题、发布日期、文号"

    # Scrape specific elements
    python fetch_cf_browser.py scrape --url https://www.miit.gov.cn/ --selector ".policy-list li a"

    # Check crawl job status
    python fetch_cf_browser.py status --job-id <id>
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    import urllib.request
    httpx = None


CF_API_BASE = "https://api.cloudflare.com/client/v4/accounts"


def _get_config():
    """Load CF account ID and API token from env."""
    account_id = os.environ.get("CF_ACCOUNT_ID", "")
    api_token = os.environ.get("CF_API_TOKEN", "")

    if not account_id or not api_token:
        # Try loading from .env files
        for env_path in [Path.home() / ".cloudflare" / ".env", Path(".env")]:
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    if line.startswith("CF_ACCOUNT_ID="):
                        account_id = line.split("=", 1)[1].strip()
                    elif line.startswith("CF_API_TOKEN="):
                        api_token = line.split("=", 1)[1].strip()

    if not account_id or not api_token:
        print("ERROR: CF_ACCOUNT_ID and CF_API_TOKEN required")
        print("  export CF_ACCOUNT_ID=<account-id>")
        print("  export CF_API_TOKEN=<api-token-with-browser-rendering-edit>")
        sys.exit(1)

    return account_id, api_token


def _api_url(account_id: str, endpoint: str) -> str:
    return f"{CF_API_BASE}/{account_id}/browser-rendering/{endpoint}"


def _headers(api_token: str) -> dict:
    return {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }


def _post(url: str, headers: dict, payload: dict) -> dict:
    """HTTP POST with httpx or urllib fallback."""
    if httpx:
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, headers=headers, json=payload)
            return {"status": resp.status_code, "data": resp.json() if resp.status_code < 500 else {"error": resp.text}}
    else:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return {"status": resp.status, "data": json.loads(resp.read())}
        except urllib.error.HTTPError as e:
            return {"status": e.code, "data": {"error": e.read().decode()}}


def _get(url: str, headers: dict) -> dict:
    """HTTP GET."""
    if httpx:
        with httpx.Client(timeout=60) as client:
            resp = client.get(url, headers=headers)
            return {"status": resp.status_code, "data": resp.json() if resp.status_code < 500 else {"error": resp.text}}
    else:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return {"status": resp.status, "data": json.loads(resp.read())}


# ============================================================
# CRAWL - Async multi-page crawling
# ============================================================

def crawl_start(url: str, limit: int = 50, depth: int = 2,
                formats: list = None, render: bool = True,
                include_patterns: list = None, exclude_patterns: list = None) -> dict:
    """Start an async crawl job."""
    account_id, api_token = _get_config()

    payload = {
        "url": url,
        "limit": limit,
        "depth": depth,
        "formats": formats or ["markdown"],
        "render": render,
        "options": {},
    }
    if include_patterns:
        payload["options"]["includePatterns"] = include_patterns
    if exclude_patterns:
        payload["options"]["excludePatterns"] = exclude_patterns

    # Optimize: block images/fonts for speed
    payload["rejectResourceTypes"] = ["image", "font", "media"]

    result = _post(_api_url(account_id, "crawl"), _headers(api_token), payload)
    return result


def crawl_status(job_id: str) -> dict:
    """Check crawl job status."""
    account_id, api_token = _get_config()
    url = f"{_api_url(account_id, 'crawl')}/{job_id}?limit=1"
    return _get(url, _headers(api_token))


def crawl_results(job_id: str, limit: int = 100, cursor: str = None) -> dict:
    """Get crawl results with pagination."""
    account_id, api_token = _get_config()
    url = f"{_api_url(account_id, 'crawl')}/{job_id}?limit={limit}"
    if cursor:
        url += f"&cursor={cursor}"
    return _get(url, _headers(api_token))


def crawl_and_wait(url: str, limit: int = 50, depth: int = 2,
                   poll_interval: int = 10, max_wait: int = 600, **kwargs) -> list:
    """Start crawl and wait for completion, return all results."""
    resp = crawl_start(url, limit, depth, **kwargs)
    if resp["status"] != 200:
        print(f"ERROR: Crawl start failed: {resp}")
        return []

    job_id = resp["data"].get("result", resp["data"].get("id", ""))
    if not job_id:
        # Try extracting from nested structure
        job_id = resp["data"].get("result", {}).get("id", "")
    print(f"Crawl job started: {job_id}")

    # Poll for completion
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval
        status = crawl_status(job_id)
        job_status = status.get("data", {}).get("result", {}).get("status", "unknown")
        finished = status.get("data", {}).get("result", {}).get("finished", 0)
        total = status.get("data", {}).get("result", {}).get("total", 0)
        print(f"  [{elapsed}s] Status: {job_status}, {finished}/{total} pages")

        if job_status in ("completed", "errored", "cancelled_due_to_timeout"):
            break

    # Fetch all results
    all_records = []
    cursor = None
    while True:
        results = crawl_results(job_id, limit=100, cursor=cursor)
        records = results.get("data", {}).get("result", {}).get("records", [])
        all_records.extend(records)
        cursor = results.get("data", {}).get("result_info", {}).get("cursor")
        if not cursor or not records:
            break

    return all_records


# ============================================================
# JSON - AI-powered structured extraction
# ============================================================

def extract_json(url: str, prompt: str, schema: dict = None) -> dict:
    """Extract structured data from a page using AI."""
    account_id, api_token = _get_config()

    payload = {"url": url, "prompt": prompt}
    if schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "extraction",
                "schema": schema,
            }
        }

    return _post(_api_url(account_id, "json"), _headers(api_token), payload)


# ============================================================
# SCRAPE - CSS selector extraction
# ============================================================

def scrape_elements(url: str, selectors: list, wait_until: str = "networkidle0") -> dict:
    """Scrape specific elements from a page."""
    account_id, api_token = _get_config()

    payload = {
        "url": url,
        "elements": [{"selector": s} for s in selectors],
        "gotoOptions": {"waitUntil": wait_until},
    }

    return _post(_api_url(account_id, "scrape"), _headers(api_token), payload)


# ============================================================
# FINANCE-TAX SPECIFIC WRAPPERS
# ============================================================

def crawl_gov_site(site_name: str, url: str, output_dir: str, limit: int = 100) -> list:
    """Crawl a government site and save results as JSON.

    Optimized for Chinese government tax/finance sites:
    - JS rendering enabled (for SPA/CMS sites)
    - Markdown format for clean text extraction
    - Include only policy/regulation pages
    """
    print(f"Crawling {site_name}: {url} (limit={limit})")

    records = crawl_and_wait(
        url=url,
        limit=limit,
        depth=2,
        formats=["markdown"],
        render=True,
        include_patterns=[f"{url}*"],
    )

    # Save results
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    items = []
    for rec in records:
        if rec.get("status") != "completed":
            continue
        item = {
            "title": rec.get("metadata", {}).get("title", ""),
            "url": rec.get("url", ""),
            "content": rec.get("markdown", ""),
            "source": site_name,
            "http_status": rec.get("metadata", {}).get("statusCode", 0),
        }
        if item["content"]:
            items.append(item)

    out_file = out_dir / f"{site_name}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(items)} pages saved to {out_file}")
    return items


def extract_policy_list(url: str) -> list:
    """Extract structured policy list from a Chinese gov page using AI."""
    schema = {
        "type": "object",
        "properties": {
            "policies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Policy title in Chinese"},
                        "doc_number": {"type": "string", "description": "Document number like 财税〔2024〕1号"},
                        "publish_date": {"type": "string", "description": "YYYY-MM-DD format"},
                        "issuing_authority": {"type": "string", "description": "Issuing body"},
                        "url": {"type": "string", "description": "Full URL to the policy"},
                        "category": {"type": "string", "description": "Policy category"},
                    },
                    "required": ["title"],
                }
            }
        },
        "required": ["policies"],
    }

    result = extract_json(
        url=url,
        prompt="从该页面提取所有法规政策文件列表，包括标题、文号、发布日期、发布机构、链接地址。只提取实际的法规文件，忽略导航菜单和广告。",
        schema=schema,
    )

    if result["status"] == 200:
        return result["data"].get("result", {}).get("policies", [])
    return []


# ============================================================
# PRIORITY TARGET SITES (previously blocked)
# ============================================================

GOV_TARGETS = {
    "npc": {
        "name": "全国人大-法律草案/法律",
        "url": "https://www.npc.gov.cn/flcaw/",
        "note": "Vue SPA, returned 405 with direct HTTP",
    },
    "samr": {
        "name": "市场监管总局-法规",
        "url": "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/",
        "note": "Hanweb CMS, JS-rendered listings",
    },
    "miit": {
        "name": "工信部-政策法规",
        "url": "https://www.miit.gov.cn/zwgk/zcwj/",
        "note": "Hanweb CMS, JS-rendered listings",
    },
    "customs": {
        "name": "海关总署-法规",
        "url": "https://www.customs.gov.cn/customs/302249/302266/",
        "note": "瑞数WAF JS challenge",
    },
    "guangdong_tax": {
        "name": "广东省税务局",
        "url": "https://guangdong.chinatax.gov.cn/gdsw/zcfg_index/",
        "note": "Blocked from VPS datacenter IP, CF might bypass",
    },
}


def crawl_all_blocked_targets(output_dir: str, limit: int = 50):
    """Crawl all previously-blocked government sites via CF Browser Rendering."""
    for key, target in GOV_TARGETS.items():
        print(f"\n=== {target['name']} ({key}) ===")
        print(f"URL: {target['url']}")
        print(f"Note: {target['note']}")
        try:
            crawl_gov_site(key, target["url"], output_dir, limit=limit)
        except Exception as e:
            print(f"ERROR: {key} failed: {e}")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Cloudflare Browser Rendering fetcher")
    sub = parser.add_subparsers(dest="command")

    # crawl
    p_crawl = sub.add_parser("crawl", help="Crawl a site")
    p_crawl.add_argument("--url", required=True)
    p_crawl.add_argument("--limit", type=int, default=50)
    p_crawl.add_argument("--depth", type=int, default=2)
    p_crawl.add_argument("--output", default="data/raw/cf-crawl")
    p_crawl.add_argument("--name", default="cf_site")

    # json
    p_json = sub.add_parser("json", help="AI-powered extraction")
    p_json.add_argument("--url", required=True)
    p_json.add_argument("--prompt", required=True)

    # scrape
    p_scrape = sub.add_parser("scrape", help="CSS selector scrape")
    p_scrape.add_argument("--url", required=True)
    p_scrape.add_argument("--selector", required=True, nargs="+")

    # status
    p_status = sub.add_parser("status", help="Check crawl job")
    p_status.add_argument("--job-id", required=True)

    # blocked targets
    p_blocked = sub.add_parser("blocked", help="Crawl all blocked gov sites")
    p_blocked.add_argument("--output", default="data/raw/cf-blocked")
    p_blocked.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()

    if args.command == "crawl":
        items = crawl_gov_site(args.name, args.url, args.output, args.limit)
        print(json.dumps({"count": len(items)}, indent=2))

    elif args.command == "json":
        result = extract_json(args.url, args.prompt)
        print(json.dumps(result["data"], ensure_ascii=False, indent=2))

    elif args.command == "scrape":
        result = scrape_elements(args.url, args.selector)
        print(json.dumps(result["data"], ensure_ascii=False, indent=2))

    elif args.command == "status":
        result = crawl_status(args.job_id)
        print(json.dumps(result["data"], ensure_ascii=False, indent=2))

    elif args.command == "blocked":
        crawl_all_blocked_targets(args.output, args.limit)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
