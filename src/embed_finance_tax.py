#!/usr/bin/env python3
"""Generate embeddings for all Finance/Tax knowledge graph nodes and store in LanceDB.

Uses Gemini Embedding 2 Preview via AI-Fleet bin/embed.
Stores in LanceDB table 'finance_tax_embeddings' for Hybrid RAG.

Usage: python embed_finance_tax.py --db data/finance-tax-graph
"""
import argparse, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cognebula import init_kuzu_db

AI_FLEET = Path.home() / "00-AI-Fleet"
EMBED_BIN = AI_FLEET / "bin" / "embed"

# Node types to embed with their text-forming fields
EMBED_CONFIGS = {
    "TaxType": "n.name + ' ' + COALESCE(n.rateRange, '') + ' ' + COALESCE(n.governingLaw, '')",
    "TaxpayerStatus": "n.name + ' ' + COALESCE(n.domain, '') + ' ' + COALESCE(n.qualificationCriteria, '')",
    "EnterpriseType": "n.name + ' ' + COALESCE(n.taxJurisdiction, '')",
    "AccountingStandard": "n.name + ' ' + COALESCE(n.ifrsEquivalent, '') + ' ' + COALESCE(n.scope, '')",
    "LawOrRegulation": "COALESCE(n.title, '') + ' ' + COALESCE(n.regulationNumber, '') + ' ' + COALESCE(n.fullText, '')",
    "TaxIncentive": "n.name + ' ' + COALESCE(n.incentiveType, '') + ' ' + COALESCE(n.eligibilityCriteria, '')",
    "ChartOfAccount": "n.code + ' ' + n.name + ' ' + COALESCE(n.englishName, '') + ' ' + COALESCE(n.category, '')",
    "TaxRateMapping": "COALESCE(n.productCategory, '') + ' ' + COALESCE(n.rateLabel, '') + ' ' + COALESCE(n.specialPolicyDetail, '')",
    "ComplianceRule": "n.name + ' ' + COALESCE(n.conditionDescription, '') + ' ' + COALESCE(n.requiredAction, '')",
    "AccountEntry": "n.name + ' ' + COALESCE(n.scenarioDescription, '') + ' ' + COALESCE(n.debitAccountName, '') + ' ' + COALESCE(n.creditAccountName, '')",
    "IndustryBookkeeping": "COALESCE(n.industryName, '') + ' ' + COALESCE(n.costMethod, '') + ' ' + COALESCE(n.revenueRecognition, '')",
    "EntityTypeProfile": "n.name + ' ' + COALESCE(n.entityType, '') + ' ' + COALESCE(n.applicableTaxTypes, '')",
    "TaxCalendar": "n.name + ' ' + COALESCE(n.adjustmentReason, '')",
}


def get_embedding(text: str) -> list[float] | None:
    """Call bin/embed to get embedding vector."""
    if not text.strip():
        return None
    # Truncate to 8000 chars (model limit)
    text = text[:8000]
    try:
        result = subprocess.run(
            [str(EMBED_BIN), "text", "--json", text],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("embedding") or data.get("values")
    except Exception:
        pass
    return None


def extract_texts(conn, node_type: str, text_expr: str) -> list[tuple[str, str]]:
    """Extract (id, text) pairs from graph for embedding."""
    results = []
    try:
        r = conn.execute(f"MATCH (n:{node_type}) RETURN n.id, {text_expr}")
        while r.has_next():
            row = r.get_next()
            nid = str(row[0])
            text = str(row[1]) if row[1] else ""
            if text.strip():
                results.append((nid, text[:2000]))  # truncate for batch
    except Exception as e:
        print(f"WARN: Failed to extract {node_type}: {e}")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Only show texts, don't embed")
    args = parser.parse_args()

    db, conn = init_kuzu_db(Path(args.db))

    all_items = []
    for node_type, text_expr in EMBED_CONFIGS.items():
        items = extract_texts(conn, node_type, text_expr)
        for nid, text in items:
            all_items.append({"id": nid, "type": node_type, "text": text})

    print(f"Total items to embed: {len(all_items)}")

    if args.dry_run:
        for item in all_items[:10]:
            print(f"  [{item['type']}] {item['id']}: {item['text'][:80]}...")
        return

    # Check bin/embed availability
    if not EMBED_BIN.exists():
        print(f"ERROR: {EMBED_BIN} not found")
        sys.exit(1)

    # Batch embed via bin/embed batch
    batch_file = Path(args.db).parent / "embed_batch_input.jsonl"
    with open(batch_file, "w") as f:
        for item in all_items:
            f.write(json.dumps({"id": item["id"], "text": item["text"], "metadata": {"type": item["type"]}}, ensure_ascii=False) + "\n")

    print(f"Batch file written: {batch_file} ({len(all_items)} items)")

    # Run batch embedding
    result = subprocess.run(
        [str(EMBED_BIN), "batch", "--file", str(batch_file)],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode == 0:
        print(f"OK: Batch embedding complete")
        print(result.stdout[-500:] if result.stdout else "")
    else:
        print(f"WARN: Batch embedding returned code {result.returncode}")
        print(result.stderr[-500:] if result.stderr else "")

    # Verify
    result2 = subprocess.run(
        [str(EMBED_BIN), "search", "--collection", "finance-tax", "--query", "增值税", "--limit", "3"],
        capture_output=True, text=True, timeout=30
    )
    if result2.returncode == 0:
        print(f"\n=== Verification: search '增值税' ===")
        print(result2.stdout[:500])
    print("OK: Embedding pipeline complete")


if __name__ == "__main__":
    main()
