#!/usr/bin/env python3
"""Finance/Tax Knowledge Base Processor -- China Tax Ontology v2.0

Processes crawled content (JSON files from AI-Fleet skills) into KuzuDB nodes/edges.
Pipeline: Raw JSON -> NER (rule-based) -> Change Detection -> KuzuDB Ingestion

Usage:
    python finance_tax_processor.py --input data/raw/2026-03-14 --db data/finance-tax-graph
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Any

# Add parent src to path for cognebula imports
sys.path.insert(0, str(Path(__file__).parent))
from cognebula import init_kuzu_db, FINANCE_TAX_NODE_TABLES, FINANCE_TAX_REL_SPECS


# ── Rule-based NER Patterns (China Tax Domain) ─────────────────────────
PATTERNS = {
    # Regulation numbering (5 authority levels)
    "reg_state_council": re.compile(r"国发[〔\[（(]\d{4}[〕\]）)]\d+号"),
    "reg_mof_sat_joint": re.compile(r"财税[〔\[（(]\d{4}[〕\]）)]\d+号"),
    "reg_sat_issuance": re.compile(r"税总[办]?发[〔\[（(]\d{4}[〕\]）)]\d+号"),
    "reg_sat_announcement": re.compile(r"国家税务总局公告\d{4}年第\d+号"),
    "reg_customs": re.compile(r"海关总署公告\d{4}年第\d+号"),
    "reg_pbc": re.compile(r"中国人民银行令?[〔\[（(]\d{4}[〕\]）)]第?\d+号"),
    "reg_ndrc": re.compile(r"发改[委]?[〔\[（(]\d{4}[〕\]）)]\d+号"),
    # Effective dates
    "effective_date": re.compile(r"自(\d{4})年(\d{1,2})月(\d{1,2})日起施行"),
    "effective_date_alt": re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日起执行"),
    # Tax rates
    "tax_rate_pct": re.compile(r"税率[为是]?百?分?之?(\d+\.?\d*)%?"),
    "vat_rate": re.compile(r"增值税[税率征收率为]*(\d+)%"),
    # Industry codes
    "gb_industry": re.compile(r"GB/T\s*4754"),
    # Clause references
    "clause_ref": re.compile(r"第[一二三四五六七八九十百千]+条"),
    "article_num": re.compile(r"第(\d+)条"),
    # Amendment signals
    "amendment": re.compile(r"修订|废止|修改|补充|替代|失效"),
    # Tax type mentions
    "tax_type_vat": re.compile(r"增值税"),
    "tax_type_cit": re.compile(r"企业所得税"),
    "tax_type_pit": re.compile(r"个人所得税"),
    "tax_type_consumption": re.compile(r"消费税"),
    "tax_type_tariff": re.compile(r"关税"),
    "tax_type_stamp": re.compile(r"印花税"),
    "tax_type_property": re.compile(r"房产税"),
    "tax_type_land_vat": re.compile(r"土地增值税"),
    "tax_type_resource": re.compile(r"资源税"),
    "tax_type_env": re.compile(r"环境保护税"),
    "tax_type_vehicle": re.compile(r"车船税"),
    "tax_type_contract": re.compile(r"契税"),
    "tax_type_urban": re.compile(r"城市维护建设税|城建税"),
    "tax_type_education": re.compile(r"教育费附加"),
    "tax_type_cultivated": re.compile(r"耕地占用税"),
    "tax_type_tobacco": re.compile(r"烟叶税"),
    "tax_type_tonnage": re.compile(r"船舶吨税"),
    "tax_type_land_use": re.compile(r"城镇土地使用税"),
    # Taxpayer classification
    "general_taxpayer": re.compile(r"一般纳税人"),
    "small_scale": re.compile(r"小规模纳税人"),
    "small_micro": re.compile(r"小微企业|小型微利企业"),
    "high_tech": re.compile(r"高新技术企业"),
    "resident_enterprise": re.compile(r"居民企业"),
    "non_resident": re.compile(r"非居民企业"),
    # Incentive signals
    "incentive_exempt": re.compile(r"免征|免税|减免"),
    "incentive_reduce": re.compile(r"减按|减半|减征"),
    "incentive_deduct": re.compile(r"加计扣除|税前扣除"),
    "incentive_credit": re.compile(r"抵免|税额抵扣"),
    "incentive_refund": re.compile(r"即征即退|先征后退|先征后返"),
}

# Tax type ID mapping
TAX_TYPE_MAP = {
    "tax_type_vat": ("TT_VAT", "增值税"),
    "tax_type_cit": ("TT_CIT", "企业所得税"),
    "tax_type_pit": ("TT_PIT", "个人所得税"),
    "tax_type_consumption": ("TT_CONSUMPTION", "消费税"),
    "tax_type_tariff": ("TT_TARIFF", "关税"),
    "tax_type_stamp": ("TT_STAMP", "印花税"),
    "tax_type_property": ("TT_PROPERTY", "房产税"),
    "tax_type_land_vat": ("TT_LAND_VAT", "土地增值税"),
    "tax_type_resource": ("TT_RESOURCE", "资源税"),
    "tax_type_env": ("TT_ENV", "环境保护税"),
    "tax_type_vehicle": ("TT_VEHICLE", "车船税"),
    "tax_type_contract": ("TT_CONTRACT", "契税"),
    "tax_type_urban": ("TT_URBAN", "城市维护建设税"),
    "tax_type_education": ("TT_EDUCATION", "教育费附加"),
    "tax_type_cultivated": ("TT_CULTIVATED", "耕地占用税"),
    "tax_type_tobacco": ("TT_TOBACCO", "烟叶税"),
    "tax_type_tonnage": ("TT_TONNAGE", "船舶吨税"),
    "tax_type_land_use": ("TT_LAND_USE", "城镇土地使用税"),
}


def extract_entities(text: str) -> dict[str, list]:
    """Extract finance/tax entities from Chinese text using rule-based NER."""
    entities: dict[str, list] = {
        "regulation_numbers": [],
        "effective_dates": [],
        "tax_rates": [],
        "clause_refs": [],
        "tax_types": [],
        "taxpayer_types": [],
        "incentive_signals": [],
        "amendment_signals": [],
    }

    # Regulation numbers (5 types)
    for key in ["reg_state_council", "reg_mof_sat_joint", "reg_sat_issuance",
                "reg_sat_announcement", "reg_customs", "reg_pbc", "reg_ndrc"]:
        for m in PATTERNS[key].finditer(text):
            entities["regulation_numbers"].append({
                "number": m.group(),
                "authority": key.replace("reg_", ""),
                "hierarchy": {"state_council": 0, "mof_sat_joint": 1,
                              "sat_issuance": 2, "sat_announcement": 3,
                              "customs": 3, "pbc": 2, "ndrc": 2}.get(key.replace("reg_", ""), 4),
            })

    # Effective dates
    for pat_key in ["effective_date", "effective_date_alt"]:
        for m in PATTERNS[pat_key].finditer(text):
            try:
                entities["effective_dates"].append(
                    date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
                )
            except ValueError:
                pass

    # Tax rates
    for m in PATTERNS["tax_rate_pct"].finditer(text):
        entities["tax_rates"].append(float(m.group(1)))
    for m in PATTERNS["vat_rate"].finditer(text):
        entities["tax_rates"].append(float(m.group(1)))
    entities["tax_rates"] = sorted(set(entities["tax_rates"]))

    # Clause references
    for m in PATTERNS["clause_ref"].finditer(text):
        entities["clause_refs"].append(m.group())
    for m in PATTERNS["article_num"].finditer(text):
        entities["clause_refs"].append(f"第{m.group(1)}条")
    entities["clause_refs"] = sorted(set(entities["clause_refs"]))

    # Tax types mentioned
    for key, (tid, tname) in TAX_TYPE_MAP.items():
        if PATTERNS[key].search(text):
            entities["tax_types"].append({"id": tid, "name": tname})

    # Taxpayer types
    for key in ["general_taxpayer", "small_scale", "small_micro", "high_tech",
                "resident_enterprise", "non_resident"]:
        if PATTERNS[key].search(text):
            entities["taxpayer_types"].append(key)

    # Incentive signals
    for key in ["incentive_exempt", "incentive_reduce", "incentive_deduct",
                "incentive_credit", "incentive_refund"]:
        if PATTERNS[key].search(text):
            entities["incentive_signals"].append(key.replace("incentive_", ""))

    # Amendment signals
    if PATTERNS["amendment"].search(text):
        entities["amendment_signals"] = PATTERNS["amendment"].findall(text)

    return entities


def compute_content_hash(text: str) -> str:
    """SHA256 hash for change detection (Tier 1)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def detect_changes(new_hash: str, db_path: Path, doc_id: str) -> bool:
    """Check if content has changed since last ingestion."""
    # Store hashes in sibling dir to avoid conflict with KuzuDB data dir
    hash_file = db_path.parent / "ft-hashes" / f"{doc_id}.sha256"
    if hash_file.exists():
        old_hash = hash_file.read_text().strip()
        if old_hash == new_hash:
            return False
    hash_file.parent.mkdir(parents=True, exist_ok=True)
    hash_file.write_text(new_hash)
    return True


def determine_hierarchy_level(regulation_number: str) -> int:
    """Determine regulation hierarchy level from its number."""
    if "国发" in regulation_number:
        return 0
    if "财税" in regulation_number:
        return 1
    if "税总" in regulation_number:
        return 2
    if "公告" in regulation_number:
        return 3
    if "海关" in regulation_number:
        return 3
    return 4


def ingest_document(conn: Any, doc: dict, entities: dict) -> dict:
    """Ingest a single document into KuzuDB as LawOrRegulation + related nodes."""
    now = datetime.utcnow().isoformat()
    doc_id = doc.get("id") or compute_content_hash(doc.get("title", "") + doc.get("url", ""))[:16]
    reg_number = ""
    hierarchy = 4

    # Extract regulation number if found
    if entities["regulation_numbers"]:
        reg_info = entities["regulation_numbers"][0]
        reg_number = reg_info["number"]
        hierarchy = reg_info["hierarchy"]

    effective_date = entities["effective_dates"][0] if entities["effective_dates"] else None

    # Upsert LawOrRegulation node
    # KuzuDB DATE columns need date() cast; skip effectiveDate if None
    try:
        set_clause = (
            "SET n.regulationNumber = $rn, n.title = $title, "
            "n.issuingAuthority = $auth, n.regulationType = $rtype, "
            "n.status = $status, "
            "n.hierarchyLevel = $hlevel, n.sourceUrl = $url, "
            "n.contentHash = $hash, n.fullText = $text"
        )
        params: dict[str, Any] = {
            "id": doc_id, "rn": reg_number,
            "title": doc.get("title", ""),
            "auth": doc.get("source", "unknown"),
            "rtype": doc.get("type", "notice"),
            "status": "active",
            "hlevel": hierarchy,
            "url": doc.get("url", ""),
            "hash": doc.get("content_hash", ""),
            "text": doc.get("content", "")[:10000],
        }
        # Only set effectiveDate if we have a valid date string
        if effective_date:
            set_clause += f", n.effectiveDate = date('{effective_date}')"

        conn.execute(
            f"MERGE (n:LawOrRegulation {{id: $id}}) {set_clause}",
            params,
        )
    except Exception as e:
        return {"error": str(e), "doc_id": doc_id}

    # Create edges to mentioned tax types
    for tt in entities["tax_types"]:
        try:
            conn.execute(
                "MERGE (t:TaxType {id: $tid}) SET t.name = $tname",
                {"tid": tt["id"], "tname": tt["name"]},
            )
            conn.execute(
                "MATCH (law:LawOrRegulation {id: $lid}), (tax:TaxType {id: $tid}) "
                "MERGE (tax)-[:FT_GOVERNED_BY {governanceLevel: $gl, confidence: 0.8}]->(law)",
                {"lid": doc_id, "tid": tt["id"], "gl": hierarchy},
            )
        except Exception:
            pass

    return {"doc_id": doc_id, "reg_number": reg_number, "entities": len(entities["tax_types"])}


def process_directory(input_dir: Path, db_path: Path) -> dict:
    """Process all JSON files in input directory into KuzuDB."""
    db, conn = init_kuzu_db(db_path)

    stats = {"processed": 0, "changed": 0, "skipped": 0, "errors": 0, "nodes_created": 0}

    json_files = sorted(input_dir.glob("**/*.json"))
    if not json_files:
        print(f"WARN: No JSON files found in {input_dir}")
        return stats

    for jf in json_files:
        try:
            docs = json.loads(jf.read_text(encoding="utf-8"))
            if isinstance(docs, dict):
                docs = [docs]

            for doc in docs:
                content = doc.get("content", "") or doc.get("text", "") or doc.get("title", "")
                if not content:
                    stats["skipped"] += 1
                    continue

                content_hash = compute_content_hash(content)
                doc["content_hash"] = content_hash
                doc_id = doc.get("id") or content_hash[:16]

                if not detect_changes(content_hash, db_path, doc_id):
                    stats["skipped"] += 1
                    continue

                entities = extract_entities(content)
                result = ingest_document(conn, doc, entities)

                if "error" in result:
                    stats["errors"] += 1
                    print(f"ERROR: {result['error']} for {doc.get('title', 'unknown')[:50]}")
                else:
                    stats["changed"] += 1
                    stats["nodes_created"] += 1

                stats["processed"] += 1

        except Exception as e:
            stats["errors"] += 1
            print(f"ERROR: Failed to process {jf.name}: {e}")

    print(f"OK: Processed {stats['processed']} docs, "
          f"{stats['changed']} changed, {stats['skipped']} skipped, "
          f"{stats['errors']} errors")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Finance/Tax Knowledge Base Processor")
    parser.add_argument("--input", required=True, help="Input directory with JSON files")
    parser.add_argument("--db", required=True, help="KuzuDB database path")
    parser.add_argument("--stats-output", help="Write stats JSON to file")
    args = parser.parse_args()

    input_dir = Path(args.input)
    db_path = Path(args.db)

    if not input_dir.exists():
        print(f"ERROR: Input directory does not exist: {input_dir}")
        sys.exit(1)

    stats = process_directory(input_dir, db_path)

    if args.stats_output:
        Path(args.stats_output).write_text(json.dumps(stats, indent=2))

    sys.exit(0 if stats["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
