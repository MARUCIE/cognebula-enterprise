#!/usr/bin/env python3
"""Inject enterprise report chapters and indicators into KuzuDB graph.

7 report templates (01融资 is scanned/empty, skipped):
- 企业全景报告, 02税务风险报告, 03企业尽调报告, 04供应商尽调,
  05投资尽调, 06财政补贴报告, 07经营参谋报告

Chapters -> LawOrRegulation nodes (regulationType: report_template)
Indicators -> RiskIndicator nodes

Usage:
    python src/inject_enterprise_reports.py [--db data/finance-tax-graph] [--dry-run]
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def esc(s: str) -> str:
    """Escape string for Cypher."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def make_id(prefix: str, text: str) -> str:
    """Generate deterministic ID."""
    h = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


def has_chinese(s: str) -> bool:
    """Check if string contains Chinese characters."""
    return bool(re.search(r"[\u4e00-\u9fff]", s))


# Report files to process (skip 01融资 - scanned/empty)
REPORT_FILES = {
    "全景": "企业全景报告报告.json",
    "税务风险": "02税务风险报告示例.json",
    "企业尽调": "03企业尽调报告示例.json",
    "供应商尽调": "04供应商尽调示例.json",
    "投资尽调": "05投资尽调示例.json",
    "财政补贴": "06财政补贴报告示例.json",
    "经营参谋": "07经营参谋报告示例.json",
}


def inject_chapters(conn, dry_run: bool) -> int:
    """Inject report chapters as LawOrRegulation nodes."""
    base = Path("data/extracted/enterprise_reports")
    total = 0

    for report_type, filename in REPORT_FILES.items():
        fpath = base / filename
        if not fpath.exists():
            print(f"WARN: {fpath} not found, skipping")
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        chapters = data.get("chapters", [])
        count = 0

        for ch in chapters:
            title = str(ch.get("title", "")).strip()

            # Filter: must have Chinese chars and title >= 5 chars
            if len(title) < 5 or not has_chinese(title):
                continue

            full_title = f"[ReportTemplate-{report_type}] {title}"
            nid = make_id("LR_RPT", f"{report_type}_{title}")
            page = ch.get("page", 0)
            content_lines = ch.get("content_lines", 0)

            # Build fullText from title + sections info
            full_text = title
            if ch.get("sections"):
                section_text = "; ".join(str(s) for s in ch["sections"][:20])
                full_text = f"{title} | sections: {section_text}"
            full_text = full_text[:2000]

            sql = (
                f"CREATE (n:LawOrRegulation {{"
                f"id: '{esc(nid)}', title: '{esc(full_title[:200])}', "
                f"regulationNumber: 'RPT-{report_type}-P{page}', "
                f"issuingAuthority: 'doc-tax-enterprise-reports', "
                f"regulationType: 'report_template', "
                f"issuedDate: date('2026-01-01'), effectiveDate: date('2026-01-01'), "
                f"expiryDate: date('2099-12-31'), "
                f"status: 'reference', hierarchyLevel: 0, "
                f"sourceUrl: 'local://doc-tax/enterprise-reports/{esc(filename)}', "
                f"contentHash: '{hashlib.sha256(full_text.encode()).hexdigest()[:16]}', "
                f"fullText: '{esc(full_text)}', "
                f"validTimeStart: timestamp('2026-01-01 00:00:00'), "
                f"validTimeEnd: timestamp('2099-12-31 00:00:00'), "
                f"txTimeCreated: timestamp('2026-03-15 00:00:00'), "
                f"txTimeUpdated: timestamp('2026-03-15 00:00:00')"
                f"}})"
            )

            if dry_run:
                count += 1
            else:
                try:
                    conn.execute(sql)
                    count += 1
                except Exception:
                    pass  # skip duplicates

        print(f"  {report_type}: +{count} chapters")
        total += count

    return total


def inject_indicators(conn, dry_run: bool) -> int:
    """Inject report indicators as RiskIndicator nodes."""
    base = Path("data/extracted/enterprise_reports")
    total = 0

    for report_type, filename in REPORT_FILES.items():
        fpath = base / filename
        if not fpath.exists():
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        indicators = data.get("indicators", [])
        count = 0

        for ind in indicators:
            text = str(ind.get("text", "")).strip()
            chapter = str(ind.get("chapter", ""))

            # Filter: must have Chinese and >= 10 chars
            if len(text) < 10 or not has_chinese(text):
                continue

            rid = make_id("RI_RPT", f"{report_type}_{text}")
            name = text[:60]

            sql = (
                f"CREATE (n:RiskIndicator {{"
                f"id: '{esc(rid)}', name: '{esc(name)}', "
                f"indicatorCode: 'RPT-{report_type}-{count+1:03d}', "
                f"metricName: '{esc(text[:80])}', "
                f"metricFormula: '', "
                f"thresholdLow: 0.0, thresholdHigh: 0.0, "
                f"industryBenchmark: 0.0, industryId: '', "
                f"triggerCondition: '{esc(chapter[:100])}', "
                f"severity: 'medium', detectionMethod: 'report_template', "
                f"dataSource: 'doc-tax/enterprise-reports/{esc(report_type)}', "
                f"monitoringFrequency: 'per_report', falsePositiveRate: 0.1, "
                f"recommendedAction: '', "
                f"notes: 'source: enterprise_reports/{esc(filename)}', "
                f"confidence: 0.8"
                f"}})"
            )

            if dry_run:
                count += 1
            else:
                try:
                    conn.execute(sql)
                    count += 1
                except Exception:
                    pass  # skip duplicates

        if count > 0:
            print(f"  {report_type}: +{count} indicators")
        total += count

    return total


def main():
    parser = argparse.ArgumentParser(description="Inject enterprise report data into KuzuDB")
    parser.add_argument("--db", default="data/finance-tax-graph", help="KuzuDB path")
    parser.add_argument("--dry-run", action="store_true", help="Print counts without writing")
    args = parser.parse_args()

    conn = None
    if not args.dry_run:
        try:
            import kuzu
        except ImportError:
            print("ERROR: kuzu not installed")
            sys.exit(1)
        db = kuzu.Database(args.db)
        conn = kuzu.Connection(db)

    print("=== Injecting Report Chapters as LawOrRegulation ===")
    ch_count = inject_chapters(conn, args.dry_run)
    print(f"OK: Total {ch_count} chapters injected\n")

    print("=== Injecting Report Indicators as RiskIndicator ===")
    ind_count = inject_indicators(conn, args.dry_run)
    print(f"OK: Total {ind_count} indicators injected\n")

    print(f"=== Grand Total: +{ch_count + ind_count} new nodes ===")


if __name__ == "__main__":
    main()
