#!/usr/bin/env python3
"""
split_regulation_clauses.py -- Clause-level regulation splitting pipeline.

Splits LawOrRegulation nodes with substantial fullText into individual
RegulationClause nodes linked via CLAUSE_OF edges. Cross-references
between clauses are captured via CLAUSE_REFERENCES edges.

M1 target: top 500 regulations -> ~15,000 clause nodes.

Usage:
    python3 src/split_regulation_clauses.py --dry-run --limit 10
    python3 src/split_regulation_clauses.py --limit 100
    python3 src/split_regulation_clauses.py --limit 500
"""

import argparse
import hashlib
import logging
import re
import sys
import time
from dataclasses import dataclass, field

import kuzu

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_PATH = "data/finance-tax-graph"
MIN_FULLTEXT_LEN = 200

# Regex: match "第X条" at the start of a line or after whitespace.
# Captures the article number (Chinese or Arabic) and optional inline title.
RE_ARTICLE_SPLIT = re.compile(
    r"(?:^|\n)\s*第([一二三四五六七八九十百千零\d]+)条\s*",
)

# Regex: capture paragraph markers "第X款" within an article body.
RE_PARAGRAPH = re.compile(
    r"第([一二三四五六七八九十百千零\d]+)款",
)

# Regex: capture item markers "(X)" or "（X）" -- numbered items.
RE_ITEM = re.compile(
    r"[（\(]\s*([一二三四五六七八九十百千零\d]+)\s*[）\)]",
)

# Regex: detect cross-references to other clauses.
RE_CROSS_REF = re.compile(
    r"(?:依照|按照|参照|依据|根据|适用|违反)(?:本法|本条例|本规定|本办法)?"
    r"第([一二三四五六七八九十百千零\d]+)条"
    r"(?:第([一二三四五六七八九十百千零\d]+)款)?"
    r"(?:第([一二三四五六七八九十百千零\d]+)项)?",
)

# Chinese numeral -> int mapping
CN_NUM_MAP = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "百": 100, "千": 1000,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cn_to_int(s: str) -> int:
    """Convert a Chinese numeral string (or Arabic digit string) to int.

    Handles common patterns: 一..九, 十, 十一..十九, 二十, 二十一, 百+.
    Falls back to int() for Arabic digit strings.
    """
    if not s:
        return 0
    # Pure Arabic digits
    if s.isdigit():
        return int(s)

    result = 0
    current = 0
    for ch in s:
        v = CN_NUM_MAP.get(ch, None)
        if v is None:
            return 0  # Unknown char, bail
        if v >= 10:
            # Multiplier
            if current == 0:
                current = 1  # implicit leading 1 (e.g. "十" = 10)
            result += current * v
            current = 0
        else:
            current = v
    result += current
    return result


def make_clause_id(regulation_id: str, article: int, paragraph: int = 0, item: int = 0) -> str:
    """Generate a deterministic clause ID using full regulation ID."""
    parts = [f"CL_{regulation_id}_art{article}"]
    if paragraph > 0:
        parts.append(f"para{paragraph}")
    if item > 0:
        parts.append(f"item{item}")
    return "_".join(parts)


@dataclass
class ClauseNode:
    """Represents a single regulation clause."""
    id: str
    regulation_id: str
    article_number: int
    paragraph_number: int = 0
    item_number: int = 0
    title: str = ""
    full_text: str = ""
    keywords: str = ""
    referenced_clauses: str = ""
    notes: str = ""


@dataclass
class CrossRef:
    """A cross-reference between two clauses."""
    from_clause_id: str
    to_article: int
    to_paragraph: int = 0
    to_item: int = 0


def extract_title_from_article(text: str) -> tuple[str, str]:
    """Try to extract an inline title from the beginning of an article body.

    Some articles have a title-like phrase before the actual text body,
    often ending with a newline or period. E.g.:
        "【行政处罚】纳税人有下列行为之一的..."

    Returns (title, remaining_text). If no title found, title is empty.
    """
    # Pattern: 【...】 at start
    m = re.match(r"^[【\[]([^】\]]+)[】\]]\s*", text)
    if m:
        return m.group(1).strip(), text[m.end():]
    return "", text


def parse_articles(full_text: str, regulation_id: str) -> list[ClauseNode]:
    """Parse a regulation's fullText into individual article clauses."""
    clauses: list[ClauseNode] = []

    # Find all article boundaries
    matches = list(RE_ARTICLE_SPLIT.finditer(full_text))
    if not matches:
        return clauses

    # Track article number occurrences for dedup (some docs repeat "第三条" in different chapters)
    art_seen: dict[int, int] = {}

    for i, m in enumerate(matches):
        article_num = cn_to_int(m.group(1))
        if article_num <= 0:
            continue

        # Article text: from end of this match to start of next match (or end of string)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        article_text = full_text[start:end].strip()

        if not article_text:
            continue

        # Extract optional title
        title, body = extract_title_from_article(article_text)

        # Detect cross-references
        refs = []
        for ref_match in RE_CROSS_REF.finditer(article_text):
            ref_art = cn_to_int(ref_match.group(1))
            ref_para = cn_to_int(ref_match.group(2)) if ref_match.group(2) else 0
            ref_item = cn_to_int(ref_match.group(3)) if ref_match.group(3) else 0
            refs.append(f"art{ref_art}" + (f"_para{ref_para}" if ref_para else "") + (f"_item{ref_item}" if ref_item else ""))

        # Dedup: if same article number appears again, append occurrence suffix
        occurrence = art_seen.get(article_num, 0)
        art_seen[article_num] = occurrence + 1
        if occurrence > 0:
            clause_id = make_clause_id(regulation_id, article_num) + f"_dup{occurrence}"
        else:
            clause_id = make_clause_id(regulation_id, article_num)

        clause = ClauseNode(
            id=clause_id,
            regulation_id=regulation_id,
            article_number=article_num,
            title=title,
            full_text=article_text,
            referenced_clauses=";".join(refs) if refs else "",
        )
        clauses.append(clause)

    return clauses


# ---------------------------------------------------------------------------
# DDL: Create schema on KuzuDB
# ---------------------------------------------------------------------------

DDL_STATEMENTS = [
    """CREATE NODE TABLE IF NOT EXISTS RegulationClause(
        id STRING,
        regulationId STRING,
        articleNumber INT64,
        paragraphNumber INT64,
        itemNumber INT64,
        title STRING,
        fullText STRING,
        keywords STRING,
        referencedClauses STRING,
        notes STRING,
        PRIMARY KEY (id)
    )""",
    """CREATE REL TABLE IF NOT EXISTS CLAUSE_OF(
        FROM RegulationClause TO LawOrRegulation
    )""",
    """CREATE REL TABLE IF NOT EXISTS CLAUSE_REFERENCES(
        FROM RegulationClause TO RegulationClause
    )""",
]


def ensure_schema(conn: kuzu.Connection) -> None:
    """Create node/rel tables if they don't exist."""
    for ddl in DDL_STATEMENTS:
        try:
            conn.execute(ddl)
            log.info("DDL OK: %s", ddl[:60])
        except Exception as e:
            # "already exists" is fine
            if "already exists" in str(e).lower():
                log.info("DDL skipped (exists): %s", ddl[:60])
            else:
                raise


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def fetch_regulations(conn: kuzu.Connection, limit: int) -> list[tuple[str, str, str]]:
    """Fetch LawOrRegulation nodes with substantial fullText.

    Returns list of (id, title, fullText), ordered by fullText length desc
    so the richest regulations are processed first.
    """
    query = """
        MATCH (n:LawOrRegulation)
        WHERE n.fullText IS NOT NULL AND size(n.fullText) >= $min_len
        RETURN n.id, n.title, n.fullText
        ORDER BY size(n.fullText) DESC
        LIMIT $lim
    """
    result = conn.execute(query, {"min_len": MIN_FULLTEXT_LEN, "lim": limit})
    rows = []
    while result.has_next():
        row = result.get_next()
        rows.append((row[0], row[1], row[2]))
    return rows


def check_existing_clauses(conn: kuzu.Connection, regulation_id: str) -> int:
    """Check if clauses already exist for a regulation (idempotency)."""
    result = conn.execute(
        "MATCH (c:RegulationClause) WHERE c.regulationId = $rid RETURN count(c)",
        {"rid": regulation_id},
    )
    return result.get_next()[0]


def insert_clauses(conn: kuzu.Connection, clauses: list[ClauseNode], regulation_id: str) -> int:
    """Insert clause nodes and CLAUSE_OF edges. Returns count inserted."""
    inserted = 0
    for c in clauses:
        try:
            # Insert node
            conn.execute(
                """CREATE (n:RegulationClause {
                    id: $id,
                    regulationId: $reg_id,
                    articleNumber: $art,
                    paragraphNumber: $para,
                    itemNumber: $item,
                    title: $title,
                    fullText: $text,
                    keywords: $kw,
                    referencedClauses: $refs,
                    notes: $notes
                })""",
                {
                    "id": c.id,
                    "reg_id": c.regulation_id,
                    "art": c.article_number,
                    "para": c.paragraph_number,
                    "item": c.item_number,
                    "title": c.title,
                    "text": c.full_text,
                    "kw": c.keywords,
                    "refs": c.referenced_clauses,
                    "notes": c.notes,
                },
            )

            # Create CLAUSE_OF edge
            conn.execute(
                """MATCH (c:RegulationClause), (r:LawOrRegulation)
                   WHERE c.id = $cid AND r.id = $rid
                   CREATE (c)-[:CLAUSE_OF]->(r)""",
                {"cid": c.id, "rid": regulation_id},
            )
            inserted += 1
        except Exception as e:
            if "duplicated primary key" in str(e).lower():
                log.debug("Skipping duplicate clause %s", c.id)
            else:
                log.warning("Failed to insert clause %s: %s", c.id, e)

    return inserted


def insert_cross_references(conn: kuzu.Connection, clauses: list[ClauseNode], regulation_id: str) -> int:
    """Create CLAUSE_REFERENCES edges for detected cross-references within the same regulation."""
    created = 0
    # Build lookup: article_number -> clause_id
    art_to_id = {c.article_number: c.id for c in clauses}

    for c in clauses:
        if not c.referenced_clauses:
            continue
        for ref_str in c.referenced_clauses.split(";"):
            # Parse "art5" or "art5_para2" etc.
            m = re.match(r"art(\d+)", ref_str)
            if not m:
                continue
            target_art = int(m.group(1))
            target_id = art_to_id.get(target_art)
            if target_id and target_id != c.id:
                try:
                    conn.execute(
                        """MATCH (a:RegulationClause), (b:RegulationClause)
                           WHERE a.id = $from_id AND b.id = $to_id
                           CREATE (a)-[:CLAUSE_REFERENCES]->(b)""",
                        {"from_id": c.id, "to_id": target_id},
                    )
                    created += 1
                except Exception:
                    pass  # Duplicate or missing target
    return created


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Split regulations into clause-level nodes")
    parser.add_argument("--dry-run", action="store_true", help="Parse and report without writing to DB")
    parser.add_argument("--limit", type=int, default=100, help="Number of regulations to process (default: 100)")
    parser.add_argument("--db-path", type=str, default=DB_PATH, help="Path to KuzuDB directory")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="Skip regulations with existing clauses")
    args = parser.parse_args()

    log.info("Opening KuzuDB at %s", args.db_path)
    db = kuzu.Database(args.db_path)
    conn = kuzu.Connection(db)

    if not args.dry_run:
        log.info("Ensuring schema (RegulationClause + edges)...")
        ensure_schema(conn)

    log.info("Fetching top %d regulations with fullText >= %d chars...", args.limit, MIN_FULLTEXT_LEN)
    regulations = fetch_regulations(conn, args.limit)
    log.info("Fetched %d regulations", len(regulations))

    total_clauses = 0
    total_refs = 0
    total_skipped = 0
    total_empty = 0
    stats = []  # (title, clause_count)

    for i, (reg_id, title, full_text) in enumerate(regulations):
        # Idempotency: skip if already split
        if args.skip_existing and not args.dry_run:
            existing = check_existing_clauses(conn, reg_id)
            if existing > 0:
                log.info("[%d/%d] SKIP %s (%d clauses exist)", i + 1, len(regulations), title[:40], existing)
                total_skipped += 1
                continue

        clauses = parse_articles(full_text, reg_id)
        if not clauses:
            total_empty += 1
            if i < 20:  # Only log first 20 empties
                log.info("[%d/%d] EMPTY %s (no articles found)", i + 1, len(regulations), title[:40])
            continue

        total_clauses += len(clauses)
        stats.append((title, len(clauses)))

        if args.dry_run:
            log.info("[%d/%d] %s -> %d clauses (dry-run)",
                     i + 1, len(regulations), title[:40], len(clauses))
            # Show first 2 clauses as sample
            if i < 5:
                for c in clauses[:2]:
                    log.info("    art%d: %s... (refs: %s)",
                             c.article_number, c.full_text[:80], c.referenced_clauses or "none")
        else:
            # Insert with retry for lock contention
            for attempt in range(3):
                try:
                    inserted = insert_clauses(conn, clauses, reg_id)
                    refs = insert_cross_references(conn, clauses, reg_id)
                    total_refs += refs
                    log.info("[%d/%d] %s -> %d clauses, %d cross-refs",
                             i + 1, len(regulations), title[:40], inserted, refs)
                    break
                except Exception as e:
                    if "lock" in str(e).lower() and attempt < 2:
                        log.warning("DB locked, retrying in 5s...")
                        time.sleep(5)
                    else:
                        log.error("Failed to insert clauses for %s: %s", title[:40], e)
                        break

    # Summary
    log.info("=" * 60)
    log.info("SUMMARY")
    log.info("  Regulations processed: %d", len(regulations))
    log.info("  Skipped (existing):    %d", total_skipped)
    log.info("  Empty (no articles):   %d", total_empty)
    log.info("  Total clauses:         %d", total_clauses)
    log.info("  Total cross-refs:      %d", total_refs)
    if stats:
        avg = total_clauses / len(stats) if stats else 0
        log.info("  Avg clauses/regulation: %.1f", avg)
        # Top 5 by clause count
        stats.sort(key=lambda x: x[1], reverse=True)
        log.info("  Top 5 by clause count:")
        for title, count in stats[:5]:
            log.info("    %d clauses: %s", count, title[:50])

    if args.dry_run:
        log.info("DRY-RUN complete. No data written.")
    else:
        # Verify
        result = conn.execute("MATCH (c:RegulationClause) RETURN count(c)")
        log.info("Total RegulationClause nodes in DB: %d", result.get_next()[0])
        result = conn.execute("MATCH ()-[e:CLAUSE_OF]->() RETURN count(e)")
        log.info("Total CLAUSE_OF edges in DB: %d", result.get_next()[0])
        result = conn.execute("MATCH ()-[e:CLAUSE_REFERENCES]->() RETURN count(e)")
        log.info("Total CLAUSE_REFERENCES edges in DB: %d", result.get_next()[0])


if __name__ == "__main__":
    main()
