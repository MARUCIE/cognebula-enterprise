#!/usr/bin/env python3
"""Inject CPA exam questions into KuzuDB as OP_StandardCase nodes.

Reads from data/extracted/cpa_exams/ (produced by extract_cpa_exams.py) and:
- Each question -> OP_StandardCase node (caseType='cpa_exam_question')
- Links to related AccountingStandard/TaxType nodes where identifiable

Usage:
    .venv/bin/python3 src/inject_cpa_exams.py --dry-run
    .venv/bin/python3 src/inject_cpa_exams.py [--db data/finance-tax-graph]
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# -- Constants ----------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CPA_EXAMS_DIR = PROJECT_ROOT / "data" / "extracted" / "cpa_exams"

# Subject to Chinese label
SUBJECT_CN = {
    "accounting": "会计",
    "audit": "审计",
    "tax_law": "税法",
    "economic_law": "经济法",
    "financial_management": "财管",
    "strategy": "战略",
}

# Question type to Chinese label
QTYPE_CN = {
    "single_choice": "单项选择题",
    "multiple_choice": "多项选择题",
    "true_false": "判断题",
    "comprehensive": "综合题",
    "calculation_analysis": "计算分析题",
    "calculation": "计算题",
    "short_answer": "简答题",
    "case_analysis": "案例分析题",
    "definition": "名词解释",
    "essay": "论述题",
    "unknown": "其他",
}

# Tax type keywords -> TaxType node IDs (match existing KuzuDB schema)
TAX_TYPE_KEYWORDS = {
    "增值税": "TT_VAT",
    "消费税": "TT_CONSUMPTION",
    "企业所得税": "TT_CIT",
    "个人所得税": "TT_IIT",
    "印花税": "TT_STAMP",
    "房产税": "TT_PROPERTY",
    "车船税": "TT_VEHICLE",
    "土地增值税": "TT_LAND_VAT",
    "城建税": "TT_URBAN_MAINT",
    "城市维护建设税": "TT_URBAN_MAINT",
    "资源税": "TT_RESOURCE",
    "关税": "TT_CUSTOMS",
    "城镇土地使用税": "TT_LAND_USE",
    "契税": "TT_DEED",
    "耕地占用税": "TT_FARMLAND",
    "烟叶税": "TT_TOBACCO",
    "船舶吨税": "TT_TONNAGE",
    "环保税": "TT_ENVIRON",
}

# Accounting standard keywords -> approximate AccountingStandard references
ACCOUNTING_STD_KEYWORDS = {
    "收入确认": "CAS14",
    "长期股权投资": "CAS2",
    "金融工具": "CAS22",
    "租赁": "CAS21",
    "所得税会计": "CAS18",
    "外币折算": "CAS19",
    "合并报表": "CAS33",
    "资产减值": "CAS8",
    "存货": "CAS1",
    "固定资产": "CAS4",
    "无形资产": "CAS6",
    "投资性房地产": "CAS3",
    "职工薪酬": "CAS9",
    "借款费用": "CAS17",
    "或有事项": "CAS13",
    "资产负债表日后事项": "CAS29",
    "会计政策变更": "CAS28",
    "会计估计变更": "CAS28",
    "持续经营": "CAS30",
    "关联方": "CAS36",
    "政府补助": "CAS16",
    "非货币性资产交换": "CAS7",
    "债务重组": "CAS12",
    "股份支付": "CAS11",
    "每股收益": "CAS34",
}


def esc(s: str) -> str:
    """Escape string for Cypher literal."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def make_id(prefix: str, *parts) -> str:
    """Generate a deterministic short ID."""
    raw = "_".join(str(p) for p in parts)
    h = hashlib.md5(raw.encode()).hexdigest()[:10]
    return f"{prefix}_{h}"


def detect_related_tax_types(text: str) -> list[str]:
    """Detect TaxType node IDs referenced in question text."""
    found = []
    for keyword, node_id in TAX_TYPE_KEYWORDS.items():
        if keyword in text:
            found.append(node_id)
    return list(set(found))


def detect_related_standards(text: str) -> list[str]:
    """Detect AccountingStandard references in question text."""
    found = []
    for keyword, std_id in ACCOUNTING_STD_KEYWORDS.items():
        if keyword in text:
            found.append(std_id)
    return list(set(found))


def load_exam_data() -> tuple[dict, list[dict]]:
    """Load manifest and all exam paper JSON files."""
    manifest_path = CPA_EXAMS_DIR / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"ERROR: manifest not found at {manifest_path}. Run extract_cpa_exams.py first.")

    with open(manifest_path) as f:
        manifest = json.load(f)

    papers = []
    for json_file in sorted(CPA_EXAMS_DIR.glob("*.json")):
        if json_file.name == "manifest.json":
            continue
        try:
            with open(json_file) as f:
                data = json.load(f)
            papers.append(data)
        except Exception as e:
            print(f"  WARN: failed to load {json_file.name}: {e}")

    return manifest, papers


def build_cypher_statements(papers: list[dict]) -> tuple[list[str], list[str], dict]:
    """Build Cypher CREATE statements for questions and relationship edges.

    Returns:
        - node_stmts: CREATE statements for OP_StandardCase nodes
        - edge_stmts: CREATE statements for edges to TaxType/AccountingStandard
        - stats: summary statistics
    """
    node_stmts = []
    edge_stmts = []
    stats = {
        "total_questions": 0,
        "nodes_created": 0,
        "edges_tax_type": 0,
        "edges_accounting_std": 0,
        "by_year": {},
        "by_subject": {},
        "by_type": {},
        "skipped_short": 0,
    }

    seen_ids = set()

    for paper in papers:
        year = paper.get("year") or "unknown"
        subject = paper.get("subject", "unknown")
        source_file = paper.get("source_file", "")

        for qi, q in enumerate(paper.get("questions", [])):
            stats["total_questions"] += 1

            q_text = q.get("question", "")
            q_answer = q.get("answer") or ""
            q_type = q.get("type", "unknown")
            full_text = q.get("full_text", q_text)

            # Skip very short questions (likely parsing artifacts)
            if len(q_text.strip()) < 15:
                stats["skipped_short"] += 1
                continue

            # Build deterministic ID
            case_id = make_id("SC_CPAQ", str(year), subject, str(qi), q_text[:100])
            if case_id in seen_ids:
                continue
            seen_ids.add(case_id)

            # Build scenario description
            q_num = q.get("number", qi + 1)
            type_cn = QTYPE_CN.get(q_type, q_type)
            subject_cn = SUBJECT_CN.get(subject, subject)
            scenario = f"{year}年CPA《{subject_cn}》{type_cn} 第{q_num}题"

            # Truncate for DB fields
            correct_treatment = q_answer[:1500] if q_answer else ""
            question_text = q_text[:2000]

            node_sql = (
                f"CREATE (n:OP_StandardCase {{"
                f"id: '{esc(case_id)}', "
                f"name: '{esc(scenario[:120])}', "
                f"standardId: '', clauseRef: '', "
                f"caseType: 'cpa_exam_question', "
                f"scenario: '{esc(question_text)}', "
                f"correctTreatment: '{esc(correct_treatment)}', "
                f"commonMistake: '', "
                f"industryRelevance: 'all', "
                f"diffFromSme: false, diffFromIfrs: false, "
                f"diffDescription: '', "
                f"notes: 'year:{year} subject:{subject} type:{q_type} source:{esc(source_file[:80])}'"
                f"}})"
            )
            node_stmts.append(node_sql)
            stats["nodes_created"] += 1

            # Track distributions
            y_key = str(year)
            stats["by_year"][y_key] = stats["by_year"].get(y_key, 0) + 1
            stats["by_subject"][subject] = stats["by_subject"].get(subject, 0) + 1
            stats["by_type"][q_type] = stats["by_type"].get(q_type, 0) + 1

            # Detect and create relationship edges
            combined_text = q_text + " " + q_answer

            if subject == "tax_law":
                tax_types = detect_related_tax_types(combined_text)
                for tt_id in tax_types:
                    edge_sql = (
                        f"MATCH (c:OP_StandardCase), (t:TaxType) "
                        f"WHERE c.id = '{esc(case_id)}' AND t.id = '{esc(tt_id)}' "
                        f"CREATE (c)-[:RELATED_TO {{relType: 'cpa_exam_tax', weight: 0.8}}]->(t)"
                    )
                    edge_stmts.append(edge_sql)
                    stats["edges_tax_type"] += 1

            if subject in ("accounting", "audit"):
                std_refs = detect_related_standards(combined_text)
                for std_id in std_refs:
                    edge_sql = (
                        f"MATCH (c:OP_StandardCase), (s:AccountingStandard) "
                        f"WHERE c.id = '{esc(case_id)}' AND s.id = '{esc(std_id)}' "
                        f"CREATE (c)-[:RELATED_TO {{relType: 'cpa_exam_standard', weight: 0.8}}]->(s)"
                    )
                    edge_stmts.append(edge_sql)
                    stats["edges_accounting_std"] += 1

    return node_stmts, edge_stmts, stats


def main():
    parser = argparse.ArgumentParser(description="Inject CPA exam questions into KuzuDB")
    parser.add_argument("--db", default="data/finance-tax-graph",
                        help="Path to KuzuDB database directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate statements without executing")
    args = parser.parse_args()

    print(f"Loading CPA exam data from {CPA_EXAMS_DIR}")
    manifest, papers = load_exam_data()
    print(f"Loaded {len(papers)} exam papers")

    print("\nBuilding Cypher statements...")
    node_stmts, edge_stmts, stats = build_cypher_statements(papers)

    print(f"\n{'='*60}")
    print(f"Injection Plan")
    print(f"{'='*60}")
    print(f"Total questions parsed:  {stats['total_questions']}")
    print(f"Nodes to create:        {stats['nodes_created']}")
    print(f"Skipped (too short):    {stats['skipped_short']}")
    print(f"Tax type edges:         {stats['edges_tax_type']}")
    print(f"Accounting std edges:   {stats['edges_accounting_std']}")
    print(f"\nBy year:   {json.dumps(stats['by_year'], indent=2)}")
    print(f"\nBy subject: {json.dumps(stats['by_subject'], indent=2)}")
    print(f"\nBy type:   {json.dumps(stats['by_type'], indent=2)}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would execute {len(node_stmts)} node + {len(edge_stmts)} edge statements.")
        # Show a few sample statements
        print("\n--- Sample node statements ---")
        for stmt in node_stmts[:3]:
            print(f"  {stmt[:200]}...")
        if edge_stmts:
            print("\n--- Sample edge statements ---")
            for stmt in edge_stmts[:3]:
                print(f"  {stmt[:200]}...")
        return

    # Actual injection
    try:
        import kuzu
    except ImportError:
        sys.exit("ERROR: kuzu not installed. Run: pip install kuzu")

    db_path = PROJECT_ROOT / args.db
    if not db_path.exists():
        sys.exit(f"ERROR: database not found at {db_path}")

    print(f"\nConnecting to KuzuDB at {db_path}...")
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    # Execute node creation
    print(f"\nCreating {len(node_stmts)} OP_StandardCase nodes...")
    node_ok, node_fail = 0, 0
    for i, stmt in enumerate(node_stmts):
        try:
            conn.execute(stmt)
            node_ok += 1
        except Exception as e:
            node_fail += 1
            if node_fail <= 5:
                print(f"  WARN: node creation failed: {str(e)[:120]}")

        if (i + 1) % 100 == 0:
            print(f"  Progress: {i+1}/{len(node_stmts)} ({node_ok} ok, {node_fail} fail)")

    print(f"  Nodes: {node_ok} created, {node_fail} failed")

    # Execute edge creation
    if edge_stmts:
        print(f"\nCreating {len(edge_stmts)} relationship edges...")
        edge_ok, edge_fail = 0, 0
        for i, stmt in enumerate(edge_stmts):
            try:
                conn.execute(stmt)
                edge_ok += 1
            except Exception as e:
                edge_fail += 1
                if edge_fail <= 5:
                    print(f"  WARN: edge creation failed: {str(e)[:120]}")

        print(f"  Edges: {edge_ok} created, {edge_fail} failed")
    else:
        edge_ok = 0

    print(f"\n{'='*60}")
    print(f"Injection Complete: +{node_ok} nodes, +{edge_ok} edges")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
