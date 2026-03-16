#!/usr/bin/env python3
"""Generate derived Q&A nodes from RegulationClause nodes using Gemini AI.

Each clause generates 2 FAQ-style questions that a practitioner would ask.
Results are injected as LawOrRegulation nodes with regulationType='derived_qa'.

Usage:
    python src/generate_clause_qa.py --limit 500
    python src/generate_clause_qa.py --limit 10 --dry-run
    python src/generate_clause_qa.py --limit 500 --offset 500  # second batch

Dependencies: requests, kuzu
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

try:
    import kuzu
except ImportError:
    kuzu = None  # type: ignore[assignment]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("clause_qa")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# On VPS, direct Google API is geo-blocked; use CF Worker proxy
GEMINI_PROXY_URL = "https://gemini-api-proxy.maoyuan-wen-683.workers.dev/v1beta/models"
GEMINI_DIRECT_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """你是一位中国财税实务专家。基于法规条款生成实务问答对。

要求:
1. 问题必须是实务中的具体问题，自然口语化
2. 答案必须简短(100字以内)，给出明确结论并引用条款
3. 不要展开解释，不要列举多种情况，只给核心结论
4. 严格输出JSON数组，不要输出其他内容"""

USER_PROMPT_TEMPLATE = """基于以下法规条款生成2个实务问答对。每个答案不超过100字。

法规: {regulation_title} 第{article_number}条
原文: {clause_text}

输出JSON: [{{"q":"问题","a":"答案(100字以内)"}}]"""


def _resolve_api_key() -> str:
    """Resolve Gemini API key from env or ~/.openclaw/.env."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key
    env_path = Path.home() / ".openclaw" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip("\"'")
    raise EnvironmentError("GEMINI_API_KEY not found in env or ~/.openclaw/.env")


def _resolve_base_url() -> str:
    """Resolve Gemini API base URL. Prefer proxy on VPS."""
    env_url = os.environ.get("GEMINI_BASE_URL", "")
    if env_url:
        return env_url.rstrip("/")
    # Auto-detect VPS by hostname or explicit flag
    if os.environ.get("USE_GEMINI_PROXY", "") or Path("/root").exists():
        return GEMINI_PROXY_URL
    return GEMINI_DIRECT_URL


def _esc(s: str) -> str:
    """Escape string for Cypher literal."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def fetch_clauses(conn, limit: int, offset: int) -> list[dict]:
    """Fetch RegulationClause nodes with their parent regulation."""
    query = (
        "MATCH (c:RegulationClause)-[:CLAUSE_OF]->(r:LawOrRegulation) "
        "RETURN c.id, c.fullText, c.articleNumber, r.title "
        f"SKIP {offset} LIMIT {limit}"
    )
    result = conn.execute(query)
    clauses = []
    while result.has_next():
        row = result.get_next()
        clauses.append({
            "id": row[0],
            "fullText": row[1] or "",
            "articleNumber": str(row[2] or ""),
            "regulationTitle": row[3] or "",
        })
    return clauses


def generate_qa_pairs(
    api_key: str,
    base_url: str,
    clause: dict,
    model: str = DEFAULT_MODEL,
) -> list[dict]:
    """Call Gemini to generate QA pairs for a single clause."""
    url = f"{base_url}/{model}:generateContent?key={api_key}"
    user_prompt = USER_PROMPT_TEMPLATE.format(
        regulation_title=clause["regulationTitle"],
        article_number=clause["articleNumber"],
        clause_text=clause["fullText"][:2000],  # cap at 2000 chars
    )
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": user_prompt}]},
        ],
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}],
        },
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        logger.warning("Unexpected response for clause %s: %s", clause["id"], str(data)[:200])
        return []

    # Parse JSON response -- handle potential edge cases
    try:
        # Strip BOM and whitespace
        text = text.strip().lstrip("\ufeff")
        qa_list = json.loads(text)
        if isinstance(qa_list, dict):
            # Sometimes model wraps in a dict
            for key in ("qa", "questions", "data", "result", "results"):
                if key in qa_list:
                    qa_list = qa_list[key]
                    break
            else:
                # Single QA dict, not wrapped
                if "q" in qa_list and "a" in qa_list:
                    qa_list = [qa_list]
                else:
                    qa_list = list(qa_list.values()) if qa_list else []
        if not isinstance(qa_list, list):
            qa_list = [qa_list]
        # Validate structure
        valid = []
        for item in qa_list:
            if isinstance(item, dict) and "q" in item and "a" in item:
                valid.append({"q": str(item["q"]), "a": str(item["a"])})
        return valid[:3]  # cap at 3 QA pairs
    except json.JSONDecodeError as exc:
        logger.warning(
            "JSON parse failed for clause %s: error=%s text_repr=%s",
            clause["id"], exc, repr(text[:300]),
        )
        return []


def inject_qa_nodes(conn, clause: dict, qa_pairs: list[dict], dry_run: bool = False) -> int:
    """Inject QA pairs as LawOrRegulation nodes."""
    injected = 0
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    for i, qa in enumerate(qa_pairs):
        # Generate deterministic ID from clause + question
        qa_hash = hashlib.md5(f"{clause['id']}_{qa['q']}".encode()).hexdigest()[:12]
        node_id = f"QA_{qa_hash}"

        reg_title = clause["regulationTitle"]
        article = clause["articleNumber"]

        title = f"[FAQ-{reg_title}] {qa['q'][:150]}"
        full_text = (
            f"问: {qa['q']}\n"
            f"答: {qa['a']}\n\n"
            f"法规依据: {reg_title} 第{article}条"
        )

        if dry_run:
            logger.info("  [DRY] Would create: %s", title[:80])
            injected += 1
            continue

        cypher = (
            f"CREATE (n:LawOrRegulation {{"
            f"id: '{_esc(node_id)}', "
            f"regulationNumber: 'CLAUSE_QA_{_esc(qa_hash)}', "
            f"title: '{_esc(title[:200])}', "
            f"issuingAuthority: 'ai-synthesis-clause-qa', "
            f"regulationType: 'derived_qa', "
            f"issuedDate: date('2026-03-15'), "
            f"effectiveDate: date('2026-03-15'), "
            f"expiryDate: date('2099-12-31'), "
            f"status: 'active', "
            f"hierarchyLevel: 99, "
            f"sourceUrl: 'clause:{_esc(clause['id'])}', "
            f"contentHash: '{_esc(qa_hash)}', "
            f"fullText: '{_esc(full_text)}', "
            f"validTimeStart: timestamp('{now_ts}'), "
            f"validTimeEnd: timestamp('2099-12-31T00:00:00'), "
            f"txTimeCreated: timestamp('{now_ts}'), "
            f"txTimeUpdated: timestamp('{now_ts}')"
            f"}})"
        )
        try:
            conn.execute(cypher)
            injected += 1
        except Exception as exc:
            logger.warning("Failed to inject %s: %s", node_id, str(exc)[:200])

    return injected


def inject_from_json(args):
    """Phase 2: Inject QA nodes from a previously saved JSON batch file."""
    import kuzu as _kuzu
    with open(args.inject_from) as f:
        data = json.load(f)

    results = data.get("results", [])
    if not results:
        logger.info("No results in %s", args.inject_from)
        return

    db = _kuzu.Database(args.db)
    conn = _kuzu.Connection(db)

    total_injected = 0
    for item in results:
        clause = {
            "id": item["clause_id"],
            "regulationTitle": item["regulation"],
            "articleNumber": item["article"],
        }
        injected = inject_qa_nodes(conn, clause, item["qa_pairs"], dry_run=args.dry_run)
        total_injected += injected

    logger.info("Injected %d QA nodes from %s", total_injected, args.inject_from)


def main():
    parser = argparse.ArgumentParser(description="Generate Q&A nodes from RegulationClause")
    parser.add_argument("--db", default="data/finance-tax-graph", help="KuzuDB path")
    parser.add_argument("--limit", type=int, default=500, help="Number of clauses to process")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N clauses")
    parser.add_argument("--dry-run", action="store_true", help="Parse clauses, call API, but don't inject")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model name")
    parser.add_argument("--no-inject", action="store_true", help="Call API but skip DB injection (save JSON only)")
    parser.add_argument("--inject-from", type=str, help="Inject from a previously saved JSON file (skip API calls)")
    args = parser.parse_args()

    if requests is None and not args.inject_from:
        print("ERROR: requests package required. pip install requests")
        sys.exit(1)
    if kuzu is None:
        print("ERROR: kuzu package required. pip install kuzu")
        sys.exit(1)

    # Phase 2: inject from saved JSON
    if args.inject_from:
        return inject_from_json(args)

    api_key = _resolve_api_key()
    base_url = _resolve_base_url()
    logger.info("Gemini base URL: %s", base_url)
    logger.info("Model: %s", args.model)

    # Open DB read-only for fetching clauses (allows concurrent access)
    read_only = args.no_inject or args.dry_run
    db = kuzu.Database(args.db, read_only=read_only)
    conn = kuzu.Connection(db)

    # Fetch clauses
    clauses = fetch_clauses(conn, args.limit, args.offset)
    logger.info("Fetched %d clauses (offset=%d, limit=%d)", len(clauses), args.offset, args.limit)

    if not clauses:
        logger.info("No clauses to process")
        return

    # Process
    total_qa = 0
    total_injected = 0
    errors = 0
    all_results = []
    start_time = time.time()

    for idx, clause in enumerate(clauses):
        try:
            qa_pairs = generate_qa_pairs(api_key, base_url, clause, model=args.model)
            if not qa_pairs:
                logger.warning("[%d/%d] No QA generated for %s", idx + 1, len(clauses), clause["id"])
                errors += 1
                continue

            total_qa += len(qa_pairs)

            # Save result for JSON export
            all_results.append({
                "clause_id": clause["id"],
                "regulation": clause["regulationTitle"],
                "article": clause["articleNumber"],
                "qa_pairs": qa_pairs,
            })

            if not args.no_inject:
                injected = inject_qa_nodes(conn, clause, qa_pairs, dry_run=args.dry_run)
                total_injected += injected

            if (idx + 1) % 50 == 0:
                elapsed = time.time() - start_time
                rate = (idx + 1) / elapsed * 60
                logger.info(
                    "[%d/%d] QA: %d, Injected: %d, Rate: %.0f clauses/min",
                    idx + 1, len(clauses), total_qa, total_injected, rate,
                )

        except requests.exceptions.HTTPError as exc:
            logger.error("[%d/%d] HTTP error for %s: %s", idx + 1, len(clauses), clause["id"], exc)
            errors += 1
            if "429" in str(exc):
                logger.info("Rate limited, sleeping 10s...")
                time.sleep(10)
        except Exception as exc:
            logger.error("[%d/%d] Error for %s: %s", idx + 1, len(clauses), clause["id"], exc)
            errors += 1

    elapsed = time.time() - start_time

    # Save results to JSON
    output_dir = Path("data/synthesized/clause_qa")
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"batch_{ts}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": ts,
            "clauses_processed": len(clauses),
            "qa_generated": total_qa,
            "qa_injected": total_injected,
            "errors": errors,
            "elapsed_seconds": round(elapsed, 1),
            "results": all_results,
        }, f, ensure_ascii=False, indent=2)

    logger.info("=" * 60)
    logger.info("DONE")
    logger.info("  Clauses processed: %d", len(clauses))
    logger.info("  QA pairs generated: %d", total_qa)
    logger.info("  QA nodes injected: %d", total_injected)
    logger.info("  Errors: %d", errors)
    logger.info("  Elapsed: %.1fs (%.1f clauses/min)", elapsed, len(clauses) / elapsed * 60 if elapsed > 0 else 0)
    logger.info("  Results saved: %s", output_file)


if __name__ == "__main__":
    main()
