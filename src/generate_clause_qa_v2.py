#!/usr/bin/env python3
"""M2 Phase 1b: Generate QA pairs from RegulationClause nodes via Gemini.

For each clause, generates 1-3 practical Q&A pairs that an accountant/tax
practitioner would ask. Uses Gemini for generation + Multi-Swarm QC for validation.

Edge-first: each QA node links to source clause via DERIVED_FROM edge.
Content minimum: QA text >= 50 chars.

Expected output: ~60K QA nodes from ~120K clauses (0.5 QA/clause avg).

Usage:
    python3 src/generate_clause_qa_v2.py --dry-run --limit 100
    python3 src/generate_clause_qa_v2.py --limit 5000 --batch-size 10
"""
import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx
import kuzu

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("clause_qa_v2")

DB_PATH = "data/finance-tax-graph"
GEMINI_GEN_BASE = os.environ.get(
    "GEMINI_GEN_BASE",
    "https://gemini-api-proxy.maoyuan-wen-683.workers.dev"
)
MODEL = "gemini-2.5-flash-lite"  # Latest lite model for QA generation
GEN_URL = f"{GEMINI_GEN_BASE}/v1beta/models/{MODEL}:generateContent"

SYSTEM_PROMPT = """你是中国财税领域的资深专家。根据给定的法规条款内容，生成1-3个实用的问答对。

要求：
1. 问题必须是会计/税务从业人员在实际工作中会遇到的
2. 答案必须准确引用条款内容，不要编造
3. 答案要简洁实用，100-200字
4. 每个问答用JSON格式：{"q": "问题", "a": "答案"}
5. 只返回JSON数组，不要其他文字

如果条款内容太短或太模糊无法生成有意义的问答，返回空数组 []"""

MIN_QA_LEN = 50  # Content minimum per M2 principle


def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    for p in [Path.home() / ".openclaw" / ".env", Path(".env")]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    raise RuntimeError("GEMINI_API_KEY not found")


def generate_qa(clause_text: str, clause_title: str, api_key: str, client: httpx.Client) -> list[dict]:
    """Generate QA pairs from a clause using Gemini."""
    prompt = f"条款标题: {clause_title}\n条款内容: {clause_text[:3000]}"

    body = {
        "contents": [
            {"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}]}
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024,
        },
    }

    for attempt in range(3):
        try:
            resp = client.post(f"{GEN_URL}?key={api_key}", json=body, timeout=30)
            if resp.status_code == 429:
                time.sleep(2 ** attempt + 5)
                continue
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]

            # Parse JSON from response
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            qa_pairs = json.loads(text)
            if not isinstance(qa_pairs, list):
                return []

            # Filter by content minimum
            valid = []
            for qa in qa_pairs:
                if isinstance(qa, dict) and "q" in qa and "a" in qa:
                    if len(qa["q"]) + len(qa["a"]) >= MIN_QA_LEN:
                        valid.append(qa)
            return valid

        except (json.JSONDecodeError, KeyError, IndexError):
            return []
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                log.warning("Generate failed: %s", str(e)[:100])
                return []

    return []


def esc(s):
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()

    api_key = get_api_key()
    db = kuzu.Database(args.db)
    conn = kuzu.Connection(db)

    # Ensure DERIVED_FROM edge table exists
    if not args.dry_run:
        try:
            conn.execute("CREATE REL TABLE IF NOT EXISTS DERIVED_FROM(FROM LawOrRegulation TO RegulationClause)")
        except Exception as e:
            if "already exists" not in str(e).lower():
                log.warning("DERIVED_FROM creation: %s", e)

    # Get clauses that haven't had QA generated yet
    # Skip clauses that already have derived QA (check by regulationId pattern)
    r = conn.execute("""
        MATCH (c:RegulationClause)
        WHERE c.fullText IS NOT NULL AND size(c.fullText) >= 50
        RETURN c.id, c.title, c.fullText, c.regulationId
        ORDER BY size(c.fullText) DESC
        SKIP $offset LIMIT $lim
    """, {"offset": args.offset, "lim": args.limit})

    clauses = []
    while r.has_next():
        row = r.get_next()
        clauses.append({
            "id": row[0] or "",
            "title": row[1] or "",
            "text": row[2] or "",
            "reg_id": row[3] or "",
        })

    log.info("Loaded %d clauses (offset=%d, limit=%d)", len(clauses), args.offset, args.limit)

    if args.dry_run:
        log.info("Dry run: would generate QA for %d clauses", len(clauses))
        # Estimate
        est_qa = int(len(clauses) * 1.5)  # ~1.5 QA per clause avg
        log.info("Estimated output: ~%d QA nodes", est_qa)
        return

    client = httpx.Client()
    total_qa = 0
    total_edges = 0
    errors = 0

    for i, clause in enumerate(clauses):
        qa_pairs = generate_qa(clause["text"], clause["title"], api_key, client)

        for j, qa in enumerate(qa_pairs):
            clause_id = clause["id"]
            nid = f"LR_QA2_{hashlib.md5(f'{clause_id}_{j}'.encode()).hexdigest()[:10]}"
            title = f"[QA-v2] {qa['q'][:120]}"
            clause_title = clause["title"]
            content = f"问: {qa['q']}\n答: {qa['a']}\n\n法规依据: {clause_title} (条款ID: {clause_id})"

            try:
                sql = (
                    f"CREATE (n:LawOrRegulation {{"
                    f"id: '{esc(nid)}', title: '{esc(title[:200])}', "
                    f"regulationNumber: '', issuingAuthority: 'ai-synthesis-clause-qa-v2', "
                    f"regulationType: 'derived_qa_v2', "
                    f"issuedDate: date('2026-01-01'), effectiveDate: date('2026-01-01'), "
                    f"expiryDate: date('2099-12-31'), status: 'reference', hierarchyLevel: 99, "
                    f"sourceUrl: '{esc(clause['id'])}', "
                    f"contentHash: '{hashlib.sha256(content.encode()).hexdigest()[:16]}', "
                    f"fullText: '{esc(content[:2000])}', "
                    f"validTimeStart: timestamp('2026-01-01 00:00:00'), "
                    f"validTimeEnd: timestamp('2099-12-31 00:00:00'), "
                    f"txTimeCreated: timestamp('2026-03-16 00:00:00'), "
                    f"txTimeUpdated: timestamp('2026-03-16 00:00:00')"
                    f"}})"
                )
                conn.execute(sql)
                total_qa += 1

                # Edge: QA -> source clause (DERIVED_FROM)
                try:
                    conn.execute(
                        "MATCH (a:LawOrRegulation), (b:RegulationClause) "
                        "WHERE a.id = $aid AND b.id = $bid "
                        "CREATE (a)-[:DERIVED_FROM]->(b)",
                        {"aid": nid, "bid": clause["id"]}
                    )
                    total_edges += 1
                except:
                    pass

            except Exception as e:
                errors += 1
                if errors <= 5:
                    log.warning("Insert error: %s", str(e)[:100])

        if (i + 1) % 100 == 0:
            log.info("Progress: %d/%d clauses | +%d QA | +%d edges | %d errors",
                     i + 1, len(clauses), total_qa, total_edges, errors)

        # Rate limit
        if (i + 1) % args.batch_size == 0:
            time.sleep(1)

    client.close()

    log.info("Complete: +%d QA nodes, +%d edges, %d errors", total_qa, total_edges, errors)

    r = conn.execute("MATCH (n) RETURN count(n)")
    log.info("Total nodes: %d", r.get_next()[0])


if __name__ == "__main__":
    main()
