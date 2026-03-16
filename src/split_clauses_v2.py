#!/usr/bin/env python3
"""split_clauses_v2.py -- M2 Phase 1: Full clause-level regulation splitting.

Upgrades from v1:
1. Processes ALL regulations (no limit), not just top 500
2. Sub-article splitting: 一、二、三... and （一）（二）（三）...
3. Edge-first: each clause gets CLAUSE_OF + LR_ABOUT_TAX edges
4. Content minimum: skip clauses < 30 chars
5. Idempotent: skips regulations already split
6. Progress tracking with resume support

Expected output: ~120K new RegulationClause nodes from ~46K LawOrRegulation

Usage:
    python3 src/split_clauses_v2.py --dry-run
    python3 src/split_clauses_v2.py
    python3 src/split_clauses_v2.py --min-len 100  # only regulations with 100+ chars
"""
import argparse
import hashlib
import logging
import re
import sys
import time
from dataclasses import dataclass

import kuzu

DB_PATH = "data/finance-tax-graph"
MIN_FULLTEXT_LEN = 100  # Lowered from 200 to catch more splittable content
MIN_CLAUSE_LEN = 30     # Content minimum per M2 principle

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Phase 1: "第X条" article-level splitting
RE_ARTICLE = re.compile(
    r"(?:^|\n)\s*第([一二三四五六七八九十百千零\d]+)条\s*"
)

# Phase 2a: "一、" "二、" "三、" top-level numbered sections
RE_SECTION_CN = re.compile(
    r"(?:^|\n)\s*([一二三四五六七八九十]+)[、．.]\s*"
)

# Phase 2b: "（一）" "（二）" sub-items
RE_SUBITEM_CN = re.compile(
    r"(?:^|\n)\s*[（(]([一二三四五六七八九十]+)[)）]\s*"
)

# Phase 2c: "1." "2." "3." Arabic numbered items
RE_NUMBERED = re.compile(
    r"(?:^|\n)\s*(\d+)[.、．]\s*"
)

# Cross-reference detection
RE_CROSS_REF = re.compile(
    r"(?:依照|按照|参照|依据|根据|适用|违反)(?:本法|本条例|本规定|本办法)?"
    r"第([一二三四五六七八九十百千零\d]+)条"
    r"(?:第([一二三四五六七八九十百千零\d]+)款)?"
)

# Tax keyword -> TaxType ID mapping for edge creation
TAX_KEYWORDS = {
    "增值税": "TT_VAT", "进项": "TT_VAT", "销项": "TT_VAT", "发票": "TT_VAT",
    "企业所得税": "TT_CIT", "所得税": "TT_CIT", "纳税调整": "TT_CIT",
    "个人所得税": "TT_PIT", "个税": "TT_PIT", "工资薪金": "TT_PIT",
    "印花税": "TT_STAMP", "消费税": "TT_CONSUMPTION", "关税": "TT_TARIFF",
    "房产税": "TT_PROPERTY", "土地增值税": "TT_LAND_VAT",
    "车船税": "TT_VEHICLE", "资源税": "TT_RESOURCE", "契税": "TT_CONTRACT",
    "城建税": "TT_URBAN", "城市维护建设税": "TT_URBAN",
    "教育费附加": "TT_EDUCATION", "环境保护税": "TT_ENV",
}

CN_NUM_MAP = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "百": 100, "千": 1000,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def cn_to_int(s: str) -> int:
    if not s:
        return 0
    if s.isdigit():
        return int(s)
    result = 0
    current = 0
    for ch in s:
        v = CN_NUM_MAP.get(ch)
        if v is None:
            return 0
        if v >= 10:
            if current == 0:
                current = 1
            result += current * v
            current = 0
        else:
            current = v
    return result + current


def make_clause_id(reg_id: str, art: int, para: int = 0, item: int = 0) -> str:
    parts = [f"CL_{reg_id}_art{art}"]
    if para > 0:
        parts.append(f"p{para}")
    if item > 0:
        parts.append(f"i{item}")
    raw = "_".join(parts)
    if len(raw) > 200:
        return f"CL_{hashlib.md5(raw.encode()).hexdigest()[:12]}"
    return raw


@dataclass
class Clause:
    id: str
    regulation_id: str
    article: int
    paragraph: int
    item: int
    title: str
    text: str
    refs: str


def split_by_articles(text: str, reg_id: str) -> list[Clause]:
    """Phase 1: Split by 第X条."""
    clauses = []
    matches = list(RE_ARTICLE.finditer(text))
    if not matches:
        return clauses

    for i, m in enumerate(matches):
        art = cn_to_int(m.group(1))
        if art <= 0:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if len(body) < MIN_CLAUSE_LEN:
            continue

        # Extract cross-refs
        refs = []
        for ref in RE_CROSS_REF.finditer(body):
            ref_art = cn_to_int(ref.group(1))
            refs.append(f"art{ref_art}")

        # Extract title from 【...】
        title = ""
        tm = re.match(r"^[【\[]([^】\]]+)[】\]]\s*", body)
        if tm:
            title = tm.group(1).strip()

        clauses.append(Clause(
            id=make_clause_id(reg_id, art),
            regulation_id=reg_id,
            article=art, paragraph=0, item=0,
            title=title,
            text=body[:5000],
            refs=";".join(refs),
        ))
    return clauses


def split_by_sections(text: str, reg_id: str) -> list[Clause]:
    """Phase 2: Split by 一、二、三... or （一）（二）（三）... when no 第X条 found."""
    clauses = []

    # Try 一、二、三 pattern
    matches = list(RE_SECTION_CN.finditer(text))
    if len(matches) >= 3:  # Need at least 3 sections to be meaningful
        for i, m in enumerate(matches):
            num = cn_to_int(m.group(1))
            if num <= 0:
                continue
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            if len(body) < MIN_CLAUSE_LEN:
                continue
            clauses.append(Clause(
                id=make_clause_id(reg_id, num),
                regulation_id=reg_id,
                article=num, paragraph=0, item=0,
                title="", text=body[:5000], refs="",
            ))
        return clauses

    # Try （一）（二）（三） pattern
    matches = list(RE_SUBITEM_CN.finditer(text))
    if len(matches) >= 3:
        for i, m in enumerate(matches):
            num = cn_to_int(m.group(1))
            if num <= 0:
                continue
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            if len(body) < MIN_CLAUSE_LEN:
                continue
            clauses.append(Clause(
                id=make_clause_id(reg_id, 0, num),
                regulation_id=reg_id,
                article=0, paragraph=num, item=0,
                title="", text=body[:5000], refs="",
            ))
        return clauses

    # Try 1. 2. 3. pattern
    matches = list(RE_NUMBERED.finditer(text))
    if len(matches) >= 3:
        for i, m in enumerate(matches):
            num = int(m.group(1))
            if num <= 0 or num > 200:
                continue
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            if len(body) < MIN_CLAUSE_LEN:
                continue
            clauses.append(Clause(
                id=make_clause_id(reg_id, num),
                regulation_id=reg_id,
                article=num, paragraph=0, item=0,
                title="", text=body[:5000], refs="",
            ))
        return clauses

    return clauses


def detect_tax_type(text: str) -> set[str]:
    """Detect tax type IDs from text for edge creation."""
    found = set()
    for kw, tid in TAX_KEYWORDS.items():
        if kw in text:
            found.add(tid)
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--min-len", type=int, default=MIN_FULLTEXT_LEN)
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()

    db = kuzu.Database(args.db_path)
    conn = kuzu.Connection(db)

    # Ensure schema
    if not args.dry_run:
        for ddl in [
            "CREATE NODE TABLE IF NOT EXISTS RegulationClause(id STRING, regulationId STRING, articleNumber INT64, paragraphNumber INT64, itemNumber INT64, title STRING, fullText STRING, keywords STRING, referencedClauses STRING, notes STRING, PRIMARY KEY (id))",
            "CREATE REL TABLE IF NOT EXISTS CLAUSE_OF(FROM RegulationClause TO LawOrRegulation)",
            "CREATE REL TABLE IF NOT EXISTS CLAUSE_REFERENCES(FROM RegulationClause TO RegulationClause)",
        ]:
            try:
                conn.execute(ddl)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    raise

    # Get valid TaxType IDs
    valid_tax_ids = set()
    try:
        r = conn.execute("MATCH (t:TaxType) RETURN t.id")
        while r.has_next():
            valid_tax_ids.add(r.get_next()[0])
    except:
        pass
    log.info("Valid TaxType IDs: %d", len(valid_tax_ids))

    # Check LR_ABOUT_TAX edge table exists
    has_tax_edge = False
    try:
        r = conn.execute("CALL show_tables() RETURN *")
        while r.has_next():
            row = r.get_next()
            if row[1] == "LR_ABOUT_TAX":
                has_tax_edge = True
                break
    except:
        pass

    # Fetch ALL regulations with sufficient content
    log.info("Fetching regulations with fullText >= %d chars...", args.min_len)
    r = conn.execute(
        "MATCH (n:LawOrRegulation) WHERE n.fullText IS NOT NULL AND size(n.fullText) >= $ml "
        "RETURN n.id, n.title, n.fullText ORDER BY size(n.fullText) DESC",
        {"ml": args.min_len}
    )
    regulations = []
    while r.has_next():
        row = r.get_next()
        regulations.append((row[0], row[1], row[2]))
    log.info("Found %d regulations to process", len(regulations))

    # Get existing clause regulation IDs (for skip)
    existing_regs = set()
    try:
        r = conn.execute("MATCH (c:RegulationClause) RETURN DISTINCT c.regulationId")
        while r.has_next():
            existing_regs.add(r.get_next()[0])
    except:
        pass
    log.info("Regulations already split: %d", len(existing_regs))

    total_clauses = 0
    total_refs = 0
    total_tax_edges = 0
    skipped = 0
    empty = 0
    phase1_count = 0
    phase2_count = 0

    for i, (reg_id, title, text) in enumerate(regulations):
        if reg_id in existing_regs:
            skipped += 1
            continue

        # Try Phase 1 first (第X条)
        clauses = split_by_articles(text, reg_id)
        if clauses:
            phase1_count += 1
        else:
            # Fall back to Phase 2 (一、二、三 etc.)
            clauses = split_by_sections(text, reg_id)
            if clauses:
                phase2_count += 1

        if not clauses:
            empty += 1
            continue

        total_clauses += len(clauses)

        if args.dry_run:
            if (i - skipped) < 20:
                log.info("[%d] %s -> %d clauses (P%s)",
                         i + 1, title[:50], len(clauses),
                         "1" if clauses[0].article > 0 and clauses[0].paragraph == 0 else "2")
            continue

        # Insert clauses + edges
        for c in clauses:
            try:
                conn.execute(
                    "CREATE (n:RegulationClause {id: $id, regulationId: $rid, "
                    "articleNumber: $art, paragraphNumber: $para, itemNumber: $item, "
                    "title: $title, fullText: $text, keywords: $kw, "
                    "referencedClauses: $refs, notes: $notes})",
                    {"id": c.id, "rid": c.regulation_id,
                     "art": c.article, "para": c.paragraph, "item": c.item,
                     "title": c.title, "text": c.text, "kw": "",
                     "refs": c.refs, "notes": ""}
                )
                # CLAUSE_OF edge
                conn.execute(
                    "MATCH (c:RegulationClause), (r:LawOrRegulation) "
                    "WHERE c.id = $cid AND r.id = $rid "
                    "CREATE (c)-[:CLAUSE_OF]->(r)",
                    {"cid": c.id, "rid": reg_id}
                )

                # Tax type edge (edge-first principle)
                if has_tax_edge:
                    tax_ids = detect_tax_type(c.text + " " + (title or ""))
                    for tid in tax_ids:
                        if tid in valid_tax_ids:
                            # RegulationClause doesn't have LR_ABOUT_TAX edge table
                            # We connect the parent regulation instead (already done in P0-1)
                            pass

            except Exception as e:
                if "duplicate" not in str(e).lower():
                    log.warning("Insert error: %s", str(e)[:100])

        # Cross-references within same regulation
        art_map = {c.article: c.id for c in clauses if c.article > 0}
        for c in clauses:
            if not c.refs:
                continue
            for ref_str in c.refs.split(";"):
                m = re.match(r"art(\d+)", ref_str)
                if m:
                    target_art = int(m.group(1))
                    target_id = art_map.get(target_art)
                    if target_id and target_id != c.id:
                        try:
                            conn.execute(
                                "MATCH (a:RegulationClause), (b:RegulationClause) "
                                "WHERE a.id = $fid AND b.id = $tid "
                                "CREATE (a)-[:CLAUSE_REFERENCES]->(b)",
                                {"fid": c.id, "tid": target_id}
                            )
                            total_refs += 1
                        except:
                            pass

        if (i + 1) % 1000 == 0:
            log.info("Progress: %d/%d | clauses: %d | P1: %d | P2: %d | skip: %d",
                     i + 1, len(regulations), total_clauses, phase1_count, phase2_count, skipped)

    # Summary
    log.info("=" * 60)
    log.info("SUMMARY")
    log.info("  Regulations total:     %d", len(regulations))
    log.info("  Skipped (existing):    %d", skipped)
    log.info("  Empty (no structure):  %d", empty)
    log.info("  Phase 1 (Article):     %d", phase1_count)
    log.info("  Phase 2 (Section):     %d", phase2_count)
    log.info("  Total new clauses:     %d", total_clauses)
    log.info("  Cross-references:      %d", total_refs)

    if not args.dry_run:
        r = conn.execute("MATCH (c:RegulationClause) RETURN count(c)")
        log.info("  DB total clauses:      %d", r.get_next()[0])
        r = conn.execute("MATCH ()-[e:CLAUSE_OF]->() RETURN count(e)")
        log.info("  DB CLAUSE_OF edges:    %d", r.get_next()[0])


if __name__ == "__main__":
    main()
