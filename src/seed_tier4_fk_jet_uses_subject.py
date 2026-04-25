"""
Seed JournalEntryTemplate → AccountingSubject FK edges.

JET schema carries debit/credit as composite STRING fields:
  - prefix `as_` (subject marker)
  - inner separators `/` (alternatives) and `+` (additive multiples)
  - parentheticals like `(销项)` (drop)
  - sub-account suffix `应交税费-城建税` (fallback to first segment before `-`)

Strategy:
  1. parse the composite string into normalized tokens
  2. match each token: exact name first → fallback to segment-before-hyphen
  3. record (jet, subject, role={debit,credit}, combinator={atomic,alternative,additive})
  4. log unmatched tokens (truly absent in AccountingSubject)

Reversibility: `DROP TABLE JET_USES_SUBJECT;` removes all edges in one statement.
"""

from __future__ import annotations

import argparse
import re
import sys
import time

import kuzu

PARENS_RE = re.compile(r"\(.*?\)")
SEP_ALT_RE = re.compile(r"\s*/\s*")
SEP_ADD_RE = re.compile(r"\s*\+\s*")

# Chinese compound-noun suffixes commonly elided in alternative chains.
# e.g. "销售/管理/制造费用" expands to ["销售费用", "管理费用", "制造费用"]
SHARED_SUFFIXES = ("费用", "成本", "收入", "资产", "负债", "公积金")

# Token aliases: jet-side colloquial → canonical AccountingSubject.name.
# These resolve cases where the canonical layer DOES carry the concept
# but under a different (typically more formal) name. Adding them here
# preserves single-source-of-truth on AccountingSubject while letting
# JET seed prose stay accountant-natural.
TOKEN_ALIASES: dict[str, str] = {
    "税金及附加": "营业税金及附加",       # 6403 — formal canonical name
    "教育费附加": "应交税费",             # 2221 — sub-account collapse
    "地方教育附加": "应交税费",           # 2221 — sub-account collapse
    "未交增值税": "应交税费",             # 2221 — sub-account collapse
    "公积金": "应付职工薪酬",             # 2211 — sub-account (housing fund 通常 lives under 应付职工薪酬-福利费 or 其他应付款; mapping to 2211 keeps the payroll-cycle scope clean)
}


def expand_shared_suffix(parts: list[str]) -> list[str]:
    """If the last token ends in a known shared suffix and earlier tokens lack it,
    append the suffix to earlier tokens. Only applies when the chain is plausibly
    abbreviation-style (2+ alternatives, last token longer than first)."""
    if len(parts) < 2:
        return parts
    last = parts[-1]
    for suf in SHARED_SUFFIXES:
        if last.endswith(suf) and len(last) > len(suf):
            stem_len = len(suf)
            expanded = []
            for p in parts[:-1]:
                if not p.endswith(suf):
                    expanded.append(p + suf)
                else:
                    expanded.append(p)
            expanded.append(last)
            return expanded
    return parts


def parse_composite(raw: str | None) -> list[tuple[str, str]]:
    """Return [(token, combinator), ...] from a composite subject cell.

    combinator ∈ {'atomic', 'alternative', 'additive'}
    Strips `as_` prefix, parentheticals, inner whitespace.
    """
    if not raw:
        return []
    cleaned = raw.replace("as_", "").strip()
    cleaned = PARENS_RE.sub("", cleaned)

    # First split by `+` (additive), then each segment by `/` (alternative).
    additive_parts = SEP_ADD_RE.split(cleaned)
    has_add = len(additive_parts) > 1
    out: list[tuple[str, str]] = []

    for ap in additive_parts:
        ap_clean = ap.strip()
        if not ap_clean:
            continue
        alt_parts = SEP_ALT_RE.split(ap_clean)
        has_alt = len(alt_parts) > 1
        if has_alt:
            alt_parts = expand_shared_suffix(alt_parts)
        for tok in alt_parts:
            tok_clean = re.sub(r"\s+", "", tok).strip()
            if not tok_clean:
                continue
            if has_add and has_alt:
                comb = "additive+alternative"
            elif has_add:
                comb = "additive"
            elif has_alt:
                comb = "alternative"
            else:
                comb = "atomic"
            out.append((tok_clean, comb))
    return out


def lookup_subject(conn: kuzu.Connection, token: str) -> str | None:
    """Match token to AccountingSubject.id; tier 1 exact → tier 2 alias → tier 3 first-segment."""
    # Tier 1: exact name match
    res = conn.execute(
        "MATCH (a:AccountingSubject) WHERE a.name = $nm RETURN a.id LIMIT 1",
        {"nm": token},
    )
    if res.has_next():
        return res.get_next()[0]

    # Tier 2: alias table (jet-side colloquial → canonical name)
    aliased = TOKEN_ALIASES.get(token)
    if aliased:
        res = conn.execute(
            "MATCH (a:AccountingSubject) WHERE a.name = $nm RETURN a.id LIMIT 1",
            {"nm": aliased},
        )
        if res.has_next():
            return res.get_next()[0]

    # Tier 3: split on `-` and try the first segment
    if "-" in token:
        head = token.split("-", 1)[0].strip()
        if head:
            res2 = conn.execute(
                "MATCH (a:AccountingSubject) WHERE a.name = $nm RETURN a.id LIMIT 1",
                {"nm": head},
            )
            if res2.has_next():
                return res2.get_next()[0]
    return None


def ensure_rel_table(conn: kuzu.Connection) -> None:
    ddl = """
    CREATE REL TABLE IF NOT EXISTS JET_USES_SUBJECT(
      FROM JournalEntryTemplate TO AccountingSubject,
      role STRING,
      combinator STRING,
      sourceToken STRING
    )
    """
    conn.execute(ddl)


def fetch_jets(conn: kuzu.Connection) -> list[tuple[str, str | None, str | None]]:
    res = conn.execute(
        "MATCH (n:JournalEntryTemplate) "
        "RETURN n.id, n.debitSubjectId, n.creditSubjectId ORDER BY n.id"
    )
    rows: list[tuple[str, str | None, str | None]] = []
    while res.has_next():
        row = res.get_next()
        rows.append((row[0], row[1], row[2]))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = kuzu.Database(args.db)
    conn = kuzu.Connection(db)

    if not args.dry_run:
        print("[create] REL TABLE JET_USES_SUBJECT (idempotent)")
        ensure_rel_table(conn)

    jets = fetch_jets(conn)
    edges_added = 0
    edges_unmatched: list[tuple[str, str, str]] = []  # (jet_id, role, token)

    t0 = time.perf_counter()
    for jid, deb, cred in jets:
        for role, raw in (("debit", deb), ("credit", cred)):
            for token, combinator in parse_composite(raw):
                subject_id = lookup_subject(conn, token)
                if subject_id is None:
                    edges_unmatched.append((jid, role, token))
                    continue
                if args.dry_run:
                    edges_added += 1
                    continue
                cypher = (
                    "MATCH (j:JournalEntryTemplate {id: $jid}), "
                    "(s:AccountingSubject {id: $sid}) "
                    "MERGE (j)-[e:JET_USES_SUBJECT {role: $role, sourceToken: $tok}]->(s) "
                    "ON CREATE SET e.combinator = $comb"
                )
                conn.execute(
                    cypher,
                    {"jid": jid, "sid": subject_id, "role": role, "tok": token, "comb": combinator},
                )
                edges_added += 1
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    verb = "[DRY-RUN]" if args.dry_run else "[APPLY]"
    print(f"  {verb} JET_USES_SUBJECT: edges_added={edges_added} elapsed={elapsed_ms}ms")
    print(f"  unmatched_count={len(edges_unmatched)}")
    if edges_unmatched:
        print("  unmatched samples:")
        for jid, role, tok in edges_unmatched[:10]:
            print(f"    {jid} {role}: {tok!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
