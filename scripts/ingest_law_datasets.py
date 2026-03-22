#!/usr/bin/env python3
"""Ingest twang2218/law-datasets into KuzuDB — tax-filtered + edge-first.

Source: https://github.com/twang2218/law-datasets (Apache 2.0)
       https://huggingface.co/datasets/twang2218/chinese-law-and-regulations
Format: JSON array, each entry has: id, title, office, publish, expiry, type, status, url, content

Strategy:
  1. Download laws.json.zip from GitHub releases or HuggingFace
  2. Filter for tax/finance/accounting related laws (~2-3K of 22K)
  3. Ingest as LawOrRegulation with fullText
  4. Create edges: ISSUED_BY, CLASSIFIED_UNDER_TAX, SUPERSEDES (if expiry/publish date chains)

Run on kg-node:
    # Step 1: Download (no DB needed)
    /home/kg/kg-env/bin/python3 -u scripts/ingest_law_datasets.py --download-only

    # Step 2: Ingest (needs DB lock)
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/ingest_law_datasets.py --ingest
    sudo systemctl start kg-api
"""
import argparse
import hashlib
import json
import logging
import os
import re
import time
import zipfile
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("law_ds")

DATA_DIR = "/home/kg/cognebula-enterprise/data/law-datasets"
LAWS_ZIP = os.path.join(DATA_DIR, "laws.json.zip")
LAWS_JSON = os.path.join(DATA_DIR, "laws.json")
FILTERED_JSON = os.path.join(DATA_DIR, "laws_tax_filtered.json")
DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"

# HuggingFace dataset URL (more reliable than GitHub releases)
DOWNLOAD_URL = "https://huggingface.co/datasets/twang2218/chinese-law-and-regulations/resolve/main/laws.json.zip"

# Tax filter keywords
TAX_FILTER = [
    "税", "发票", "财政", "会计", "审计", "预算", "关税", "海关",
    "纳税", "征收", "退税", "免税", "减税", "税率", "税额", "税务",
    "税收", "缴税", "欠税", "偷税", "逃税", "骗税",
    "注册会计师", "资产评估", "财务报表", "金融", "银行", "证券",
    "保险", "社保", "公积金", "出口退税", "进出口",
]

# Tax keyword → TaxType matching (same as other scripts)
TAX_KW_MAP = {
    "企业所得税": ["企业所得"],
    "增值税": ["增值税"],
    "个人所得税": ["个人所得"],
    "消费税": ["消费税"],
    "关税": ["关税"],
    "城市维护建设税": ["城市维护", "城建税"],
    "土地增值税": ["土地增值"],
    "房产税": ["房产税"],
    "印花税": ["印花税"],
    "契税": ["契税"],
    "车辆购置税": ["车辆购置"],
    "车船税": ["车船税"],
    "资源税": ["资源税"],
    "环境保护税": ["环境保护", "环保税"],
    "烟叶税": ["烟叶税"],
    "耕地占用税": ["耕地占用"],
    "城镇土地使用税": ["城镇土地", "土地使用税"],
    "教育费附加": ["教育费附加", "教育附加"],
    "税收征收管理": ["税收征管", "征收管理"],
    "财政": ["财政部", "财政"],
    "会计": ["会计法", "会计准则", "会计制度"],
    "审计": ["审计法", "审计"],
}


def download():
    """Download laws.json.zip from HuggingFace."""
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(LAWS_JSON):
        log.info("laws.json already exists, skipping download")
        return

    if not os.path.exists(LAWS_ZIP):
        log.info("Downloading from %s ...", DOWNLOAD_URL)
        urllib.request.urlretrieve(DOWNLOAD_URL, LAWS_ZIP)
        size_mb = os.path.getsize(LAWS_ZIP) / 1024 / 1024
        log.info("Downloaded: %.1f MB", size_mb)

    log.info("Extracting...")
    with zipfile.ZipFile(LAWS_ZIP, 'r') as zf:
        zf.extractall(DATA_DIR)
    log.info("Extracted to %s", DATA_DIR)


def filter_tax():
    """Filter laws for tax/finance/accounting related entries."""
    log.info("Loading laws.json...")
    with open(LAWS_JSON, encoding="utf-8") as f:
        laws = json.load(f)
    log.info("Total laws: %d", len(laws))

    filtered = []
    for law in laws:
        title = law.get("title", "")
        content = law.get("content", "")[:2000]  # Check first 2000 chars for speed
        office = law.get("office", "")
        text = title + content + office
        if any(kw in text for kw in TAX_FILTER):
            filtered.append(law)

    log.info("Tax-filtered: %d (%.1f%%)", len(filtered), 100 * len(filtered) / max(len(laws), 1))

    # Save filtered
    with open(FILTERED_JSON, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False)
    log.info("Saved to %s", FILTERED_JSON)

    # Stats
    offices = {}
    types = {}
    for law in filtered:
        o = law.get("office", "unknown")
        t = law.get("type", "unknown")
        offices[o] = offices.get(o, 0) + 1
        types[t] = types.get(t, 0) + 1

    log.info("Top offices:")
    for k, v in sorted(offices.items(), key=lambda x: -x[1])[:10]:
        log.info("  %5d  %s", v, k)
    log.info("Types:")
    for k, v in sorted(types.items(), key=lambda x: -x[1]):
        log.info("  %5d  %s", v, k)

    return filtered


def ingest(filtered=None):
    """Ingest filtered laws into KuzuDB as LawOrRegulation nodes + edges."""
    import kuzu

    if filtered is None:
        if os.path.exists(FILTERED_JSON):
            with open(FILTERED_JSON, encoding="utf-8") as f:
                filtered = json.load(f)
        else:
            log.error("No filtered data. Run --download-only first.")
            return

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Pre-flight
    r = conn.execute("MATCH (n) RETURN count(n)")
    before_nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    before_edges = r.get_next()[0]
    log.info("Before: %s nodes / %s edges", f"{before_nodes:,}", f"{before_edges:,}")

    # Load TaxType for edge creation
    r = conn.execute("MATCH (t:TaxType) RETURN t.id, t.name")
    tax_types = {}
    while r.has_next():
        row = r.get_next()
        tax_types[str(row[0])] = str(row[1])

    kw_to_tt = {}
    for tt_id, tt_name in tax_types.items():
        for tax_name, keywords in TAX_KW_MAP.items():
            for kw in keywords:
                if kw in tt_name:
                    kw_to_tt[tax_name] = tt_id
                    break

    # Load IssuingBody for ISSUED_BY edges
    r = conn.execute("MATCH (b:IssuingBody) RETURN b.id, b.name")
    issuers = {}
    while r.has_next():
        row = r.get_next()
        issuers[str(row[1])] = str(row[0])

    log.info("TaxType: %d, IssuingBody: %d", len(tax_types), len(issuers))

    t0 = time.time()
    inserted = 0
    skipped = 0
    updated = 0
    edges_tax = 0
    edges_issued = 0

    for idx, law in enumerate(filtered):
        title = law.get("title", "").strip()
        content = law.get("content", "").strip()
        if not title or len(title) < 3:
            continue

        doc_id = hashlib.sha256(f"lawds:{law.get('id', idx)}:{title}".encode()).hexdigest()[:16]

        # Check if LR with same title exists (update fullText)
        try:
            r = conn.execute(
                "MATCH (l:LawOrRegulation) WHERE l.title = $t RETURN l.id LIMIT 1",
                {"t": title}
            )
            if r.has_next():
                existing_id = str(r.get_next()[0])
                # Update content if empty
                if content and len(content) > 100:
                    try:
                        conn.execute(
                            "MATCH (l:LawOrRegulation {id: $id}) "
                            "WHERE l.fullText IS NULL OR size(l.fullText) < 100 "
                            "SET l.fullText = $ft",
                            {"id": existing_id, "ft": content[:50000]}
                        )
                        updated += 1
                    except Exception:
                        pass
                skipped += 1
                continue
        except Exception:
            pass

        # Create new LR node
        try:
            conn.execute(
                "CREATE (l:LawOrRegulation {id: $id, title: $title, fullText: $ft, "
                "status: $st})",
                {
                    "id": doc_id, "title": title[:500],
                    "ft": content[:50000] if content else "",
                    "st": law.get("status", ""),
                }
            )
            inserted += 1
        except Exception as e:
            if inserted < 3:
                log.warning("Node ERR: %s", str(e)[:100])
            continue

        # Edge: CLASSIFIED_UNDER_TAX
        text = title + " " + content[:1000]
        for tax_name, tt_id in kw_to_tt.items():
            if tax_name in text or any(kw in text for kw in TAX_KW_MAP.get(tax_name, [])):
                try:
                    conn.execute(
                        "MATCH (l:LawOrRegulation {id: $lid}), (t:TaxType {id: $tid}) "
                        "CREATE (l)-[:CLASSIFIED_UNDER_TAX]->(t)",
                        {"lid": doc_id, "tid": tt_id}
                    )
                    edges_tax += 1
                except Exception:
                    pass

        # Edge: ISSUED_BY
        office = law.get("office", "")
        if office:
            for issuer_name, issuer_id in issuers.items():
                if issuer_name in office or office in issuer_name:
                    try:
                        conn.execute(
                            "MATCH (l:LawOrRegulation {id: $lid}), (b:IssuingBody {id: $bid}) "
                            "CREATE (l)-[:ISSUED_BY]->(b)",
                            {"lid": doc_id, "bid": issuer_id}
                        )
                        edges_issued += 1
                        break
                    except Exception:
                        pass

        if (idx + 1) % 200 == 0:
            log.info("  [%d/%d] +%d new, %d updated, +%d tax edges, +%d issued edges",
                     idx + 1, len(filtered), inserted, updated, edges_tax, edges_issued)

    elapsed = time.time() - t0
    total_edges = edges_tax + edges_issued

    r = conn.execute("MATCH (n) RETURN count(n)")
    after_nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    after_edges = r.get_next()[0]

    log.info("=" * 60)
    log.info("law-datasets ingest complete (%.0fs)", elapsed)
    log.info("  New LR: +%d, Updated fullText: %d, Skipped: %d", inserted, updated, skipped)
    log.info("  Edges: +%d total (+%d CLASSIFIED_UNDER_TAX, +%d ISSUED_BY)", total_edges, edges_tax, edges_issued)
    log.info("  Graph: %s nodes / %s edges / density %.3f",
             f"{after_nodes:,}", f"{after_edges:,}", after_edges / after_nodes)

    del conn
    del db


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-only", action="store_true", help="Download + filter only, no DB write")
    parser.add_argument("--ingest", action="store_true", help="Ingest filtered data to KuzuDB")
    args = parser.parse_args()

    if args.download_only or not args.ingest:
        download()
        filter_tax()

    if args.ingest:
        ingest()


if __name__ == "__main__":
    main()
