"""Fetcher: National People's Congress Law Database (flk.npc.gov.cn) — Playwright version.

The old API endpoint no longer returns JSON (site converted to Vue SPA).
This fetcher reads from the Playwright-based crawler output at scripts/flk_crawl.py.
"""
import argparse
import json
import logging
import os
import hashlib

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fetch_flk_npc")

JSONL_PATH = "/home/kg/cognebula-enterprise/data/recrawl/flk_npc_laws.jsonl"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    outfile = os.path.join(args.output, "flk_npc.json")

    if not os.path.exists(JSONL_PATH):
        log.warning("No Playwright crawler output found at %s", JSONL_PATH)
        json.dump([], open(outfile, "w"))
        return

    items = []
    with open(JSONL_PATH) as f:
        for line in f:
            try:
                d = json.loads(line.strip())
                title = d.get("title", "")
                if not title or len(title) < 3:
                    continue
                code_id = str(d.get("flfgCodeId", ""))
                detail_url = "https://flk.npc.gov.cn/detail2.html?NpcId=" + code_id
                items.append({
                    "id": hashlib.sha256(title.encode()).hexdigest()[:16],
                    "title": title,
                    "date": d.get("sxrq", "") or d.get("gbrq", ""),
                    "doc_num": d.get("bbbs", ""),
                    "type": d.get("flxz", "law"),
                    "source": "flk.npc.gov.cn",
                    "url": detail_url,
                    "content": d.get("content", "") or "",
                })
            except Exception:
                continue

    with open(outfile, "w") as f:
        json.dump(items, f, ensure_ascii=False)
    log.info("Saved %d items to %s", len(items), outfile)
    has_content = sum(1 for i in items if len(i.get("content", "")) >= 100)
    log.info("Quality: %d/%d have content >= 100 chars (%.1f%%)",
             has_content, len(items),
             has_content / max(len(items), 1) * 100)


if __name__ == "__main__":
    main()
