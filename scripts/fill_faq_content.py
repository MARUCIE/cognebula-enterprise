#!/usr/bin/env python3
"""Batch-fill empty FAQ-type KnowledgeUnit content using Gemini.

These KUs have questions as titles but empty content. Gemini generates
concise answers based on Chinese tax/accounting domain knowledge.

Run when API is stopped (needs KuzuDB lock).
"""
import kuzu
import json
import logging
import os
import time
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fill_faq")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
MODEL = "gemini-2.5-flash"
GEN_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SYSTEM = """你是中国财税领域专家。请用2-4句话简洁回答以下问题。
要求：直接回答，不要重复问题，不要加"根据..."等引导语。如果问题太模糊无法回答，回复"该问题需要更多上下文信息"。"""


def get_api_key():
    for p in ["/home/kg/cognebula-enterprise/.env", "/home/kg/.env.kg-api"]:
        if os.path.exists(p):
            for line in open(p):
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get("GEMINI_API_KEY", "")


def generate_answer(question: str, category: str, api_key: str) -> str:
    prompt = f"领域：{category}\n问题：{question}"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300},
    }).encode()

    for attempt in range(3):
        try:
            req = urllib.request.Request(
                f"{GEN_URL}?key={api_key}",
                data=body, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
    return ""


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=5000, help="Max items to process")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api_key = get_api_key()
    if not api_key:
        log.error("No GEMINI_API_KEY")
        return

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    r = conn.execute(
        'MATCH (k:KnowledgeUnit) '
        'WHERE k.type = "FAQ" AND (k.content IS NULL OR size(k.content) < 20) '
        'AND size(k.title) >= 8 '
        'RETURN count(k)'
    )
    total_empty = r.get_next()[0]
    log.info("Empty FAQ KUs with title >= 8 chars: %d", total_empty)

    if args.dry_run:
        log.info("[DRY RUN] Would process %d items", min(total_empty, args.max))
        del conn; del db
        return

    r = conn.execute(
        'MATCH (k:KnowledgeUnit) '
        'WHERE k.type = "FAQ" AND (k.content IS NULL OR size(k.content) < 20) '
        'AND size(k.title) >= 8 '
        f'RETURN k.id, k.title, k.source LIMIT {args.max}'
    )
    records = []
    while r.has_next():
        records.append(r.get_next())
    log.info("Fetched %d FAQ KUs to process", len(records))

    updated = 0
    errors = 0
    start = time.time()

    for i, (ku_id, title, source) in enumerate(records):
        answer = generate_answer(title, source or "财税", api_key)
        if answer and len(answer) > 10 and not answer.startswith("该问题需要"):
            escaped = answer.replace("'", "\\'").replace("\n", " ")[:1000]
            try:
                conn.execute(
                    f"MATCH (k:KnowledgeUnit) WHERE k.id = '{ku_id}' "
                    f"SET k.content = '{escaped}'"
                )
                updated += 1
            except:
                errors += 1
        else:
            errors += 1

        if (i + 1) % 100 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            eta = (len(records) - i - 1) / rate / 60
            log.info("  %d/%d (%.1f/sec, updated: %d, errors: %d, ETA: %.0fmin)",
                     i + 1, len(records), rate, updated, errors, eta)

        time.sleep(1)  # Rate limit

    elapsed = time.time() - start
    log.info("DONE: %d/%d updated in %.1f min (%.1f%% success)",
             updated, len(records), elapsed / 60, updated / max(len(records), 1) * 100)

    del conn; del db


if __name__ == "__main__":
    main()
