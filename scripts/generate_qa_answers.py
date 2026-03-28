#!/usr/bin/env python3
"""Generate answers for 23K QA nodes using Gemini Flash.

Each QA node has a tax question as title but no answer (content is NULL).
We batch questions to Gemini and write answers back as content.

Strategy:
- Batch 10 questions per API call (reduce cost)
- Use gemini-2.0-flash (fast, cheap)
- Write answers back to KU content
- No DB reconnect (8GB VPS safety)
- Checkpoint every 50 writes

Run on kg-node:
    source /home/kg/.env.kg-api
    /home/kg/kg-env/bin/python3 -u scripts/generate_qa_answers.py 2>&1 | tee /tmp/qa_gen.log

Cost estimate: 23K questions / 10 per batch = 2,300 API calls
  ~500 tokens input + 500 output per batch = ~2.3M tokens total
  Gemini Flash: ~$0.10/M tokens = ~$0.23 total
"""
import json
import logging
import os
import time

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import llm_generate

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("qa_gen")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
OUTPUT_JSONL = "/home/kg/cognebula-enterprise/data/backfill/qa_answers.jsonl"
BATCH_SIZE = 10
MAX_CONTENT = 3000
CHECKPOINT_EVERY = 50

SYSTEM_PROMPT = """你是中国税务专家。对于以下税务问题，请逐一给出简明准确的回答。
每个回答 100-200 字，引用相关法规名称。格式：

Q1: [问题]
A1: [回答]

Q2: [问题]
A2: [回答]

...以此类推。"""


def generate_batch_answers(questions: list[tuple[str, str]]) -> dict[str, str]:
    """Generate answers for a batch of questions. Returns {node_id: answer}."""
    prompt_parts = [SYSTEM_PROMPT + "\n\n"]
    for i, (nid, q) in enumerate(questions, 1):
        prompt_parts.append(f"Q{i}: {q}\n")

    prompt = "\n".join(prompt_parts)

    try:
        text = llm_generate(prompt)
        if text.startswith("[ERROR]"):
            log.warning("  LLM error: %s", text[:100])
            return {}

        # Parse answers
        answers = {}
        lines = text.split("\n")
        current_q_idx = None
        current_answer = []

        for line in lines:
            line = line.strip()
            # Check for A{n}: pattern
            for i in range(1, len(questions) + 1):
                if line.startswith(f"A{i}:") or line.startswith(f"A{i}："):
                    if current_q_idx is not None and current_answer:
                        nid = questions[current_q_idx - 1][0]
                        answers[nid] = " ".join(current_answer).strip()
                    current_q_idx = i
                    answer_text = line.split(":", 1)[-1].split("：", 1)[-1].strip()
                    current_answer = [answer_text] if answer_text else []
                    break
            else:
                if current_q_idx is not None and line and not line.startswith("Q"):
                    current_answer.append(line)

        # Save last answer
        if current_q_idx is not None and current_answer:
            nid = questions[current_q_idx - 1][0]
            answers[nid] = " ".join(current_answer).strip()

        return answers

    except Exception as e:
        log.warning("  API error: %s", str(e)[:100])
        time.sleep(5)
        return {}


def main():
    import kuzu
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Get all QA nodes without content
    log.info("Loading QA nodes without content...")
    r = conn.execute("""
    MATCH (k:KnowledgeUnit)
    WHERE k.source = 'gemini-qa-v3'
      AND (k.content IS NULL OR size(k.content) < 100)
      AND k.title IS NOT NULL AND size(k.title) >= 10
    RETURN k.id, k.title
    """)
    qa_nodes = []
    while r.has_next():
        row = r.get_next()
        qa_nodes.append((str(row[0]), str(row[1])))
    log.info("Found %d QA nodes to process", len(qa_nodes))

    # Check for existing answers (resume capability)
    existing = set()
    if os.path.exists(OUTPUT_JSONL):
        with open(OUTPUT_JSONL) as f:
            for line in f:
                try:
                    item = json.loads(line)
                    existing.add(item["id"])
                except:
                    pass
    log.info("Existing answers: %d (will skip)", len(existing))

    # Filter out already-answered
    todo = [(nid, q) for nid, q in qa_nodes if nid not in existing]
    log.info("Remaining to process: %d", len(todo))

    # Process in batches
    writes = 0
    generated = 0
    failed = 0
    out_f = open(OUTPUT_JSONL, "a")

    for batch_start in range(0, len(todo), BATCH_SIZE):
        batch = todo[batch_start:batch_start + BATCH_SIZE]
        answers = generate_batch_answers(batch)

        for nid, q in batch:
            answer = answers.get(nid, "")
            if len(answer) >= 30:
                content = f"Q: {q}\nA: {answer}"
                if len(content) >= 100:
                    # Write to DB
                    try:
                        conn.execute(
                            "MATCH (k:KnowledgeUnit {id: $id}) SET k.content = $c",
                            {"id": nid, "c": content[:MAX_CONTENT]}
                        )
                        writes += 1
                        if writes % CHECKPOINT_EVERY == 0:
                            conn.execute("CHECKPOINT")
                    except:
                        pass
                    generated += 1
                    # Save to JSONL for resume
                    out_f.write(json.dumps({"id": nid, "question": q, "answer": answer}, ensure_ascii=False) + "\n")
                else:
                    failed += 1
            else:
                failed += 1

        if (batch_start // BATCH_SIZE + 1) % 50 == 0:
            out_f.flush()
            log.info("  Batch %d/%d: generated=%d, failed=%d, writes=%d",
                     batch_start // BATCH_SIZE + 1,
                     (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE,
                     generated, failed, writes)

        # Rate limit: 15 RPM for free tier
        time.sleep(4)

    out_f.close()
    conn.execute("CHECKPOINT")

    r = conn.execute("MATCH (k:KnowledgeUnit) WHERE k.content IS NOT NULL AND size(k.content)>=100 RETURN count(k)")
    good = r.get_next()[0]
    r = conn.execute("MATCH (k:KnowledgeUnit) RETURN count(k)")
    total = r.get_next()[0]

    log.info("\n" + "=" * 60)
    log.info("QA Generation complete")
    log.info("  Generated: %d | Failed: %d | Writes: %d", generated, failed, writes)
    log.info("  KU coverage: %d/%d (%.1f%%)", good, total, 100 * good / total)
    log.info("  Output: %s", OUTPUT_JSONL)

    del conn, db


if __name__ == "__main__":
    main()
