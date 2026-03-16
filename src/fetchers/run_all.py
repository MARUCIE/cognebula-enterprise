"""Run all finance-tax fetchers sequentially.

Usage:
    python run_all.py --output ./out
    python run_all.py --output ./out --skip chinatax customs
    python run_all.py --output ./out --only mof npc
"""

import argparse
import logging
import sys
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("run_all")

# Registry: name -> (module_path, fetch function import)
FETCHERS = {
    "chinatax": "fetch_chinatax",
    "mof": "fetch_mof",
    "pbc": "fetch_pbc",
    "safe": "fetch_safe",
    "csrc": "fetch_csrc",
    "ndrc": "fetch_ndrc",
    "casc": "fetch_casc",
    "stats": "fetch_stats",
    # CF Browser Rendering API fetchers (JS-rendered sites, require CF_ACCOUNT_ID + CF_API_TOKEN):
    # "cf_npc": "fetch_cf_browser",      # 全人大 (Vue SPA) -- crawl mode
    # "cf_samr": "fetch_cf_browser",     # 市场监管总局 (Hanweb CMS) -- crawl mode
    # "cf_miit": "fetch_cf_browser",     # 工信部 (Hanweb CMS) -- crawl mode
    # "cf_customs": "fetch_cf_browser",  # 海关总署 (瑞数WAF) -- crawl mode
    # Enable by: export CF_ACCOUNT_ID=xxx CF_API_TOKEN=xxx
    # Run standalone: python fetch_cf_browser.py blocked --output data/raw/cf-blocked
    # Disabled: ctax (domain dead, DNS unresolvable)
    "baike_kuaiji": "fetch_baike_kuaiji",
    "12366": "fetch_12366",
    "chinaacc": "fetch_chinaacc",
}


def run(output_dir: str, include: list[str] | None = None, exclude: list[str] | None = None):
    """Run selected fetchers sequentially."""
    import importlib

    exclude_set = set(exclude or [])
    names = include if include else list(FETCHERS.keys())
    names = [n for n in names if n not in exclude_set]

    log.info("Running %d fetchers: %s", len(names), ", ".join(names))
    log.info("Output directory: %s", output_dir)

    results_summary = {}
    start_all = time.time()

    for i, name in enumerate(names):
        if name not in FETCHERS:
            log.warning("Unknown fetcher '%s', skipping", name)
            continue

        log.info("--- [%d/%d] %s ---", i + 1, len(names), name)
        start = time.time()
        try:
            mod = importlib.import_module(FETCHERS[name])
            items = mod.fetch(output_dir)
            elapsed = time.time() - start
            results_summary[name] = {"count": len(items), "time": f"{elapsed:.1f}s", "status": "ok"}
            log.info("[%s] OK: %d items in %.1fs", name, len(items), elapsed)
        except Exception as e:
            elapsed = time.time() - start
            results_summary[name] = {"count": 0, "time": f"{elapsed:.1f}s", "status": f"error: {e}"}
            log.error("[%s] FAILED: %s (%.1fs)", name, e, elapsed)

        # Delay between fetchers to be respectful
        if i < len(names) - 1:
            time.sleep(5)

    total_time = time.time() - start_all
    total_items = sum(r["count"] for r in results_summary.values())
    log.info("=== Summary ===")
    log.info("Total: %d items from %d fetchers in %.1fs", total_items, len(results_summary), total_time)
    for name, info in results_summary.items():
        status_prefix = "OK" if info["status"] == "ok" else "ERROR"
        log.info("  %s %s: %d items (%s)", status_prefix, name, info["count"], info["time"])

    return results_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all finance-tax fetchers")
    parser.add_argument("--output", default="./out", help="Output directory for all JSON files")
    parser.add_argument("--only", nargs="+", help="Run only these fetchers")
    parser.add_argument("--skip", nargs="+", help="Skip these fetchers")
    args = parser.parse_args()
    run(args.output, include=args.only, exclude=args.skip)
