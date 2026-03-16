#!/usr/bin/env python3
"""Inject extracted PDF documents into KuzuDB as LawOrRegulation nodes.

Splits each PDF into chapter/section-level nodes (not one node per PDF).
Edge-first: creates LR_ABOUT_TAX and LR_ABOUT_INDUSTRY edges.

Usage:
    python3 src/inject_pdf_docs.py [--db data/finance-tax-graph] [--dry-run]
"""
import argparse
import hashlib
import json
import re
import sys


def esc(s):
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


TAX_KW = {
    "增值税": "TT_VAT", "进项税": "TT_VAT", "销项税": "TT_VAT", "发票": "TT_VAT",
    "企业所得税": "TT_CIT", "所得税": "TT_CIT", "汇算清缴": "TT_CIT",
    "个人所得税": "TT_PIT", "个税": "TT_PIT",
    "印花税": "TT_STAMP", "消费税": "TT_CONSUMPTION", "关税": "TT_TARIFF",
    "房产税": "TT_PROPERTY", "土地增值税": "TT_LAND_VAT",
    "车船税": "TT_VEHICLE", "资源税": "TT_RESOURCE", "契税": "TT_CONTRACT",
    "城建税": "TT_URBAN", "教育费附加": "TT_EDUCATION",
}

IND_KW = {
    "房地产": "IND_REALESTATE", "建筑": "IND_CONSTRUCTION",
    "医美": "IND_MEDICAL_AESTHETICS", "医疗美容": "IND_MEDICAL_AESTHETICS",
    "物业": "IND_PROPERTY_MGMT", "网络直播": "IND_SERVICE",
    "劳务派遣": "IND_LABOR_DISPATCH", "合伙企业": "IND_PARTNERSHIP",
    "高新技术": "IND_HIGH_TECH", "律师": "IND_LAW_FIRM",
    "汽车经销": "IND_COMMERCE", "幼儿园": "IND_KINDERGARTEN",
    "再生资源": "IND_RECYCLING", "出口退税": "IND_EXPORT_REFUND",
    "民间非营利": "IND_NONPROFIT", "制造": "IND_MANUFACTURING",
    "软件": "IND_SOFTWARE", "餐饮": "IND_CATERING",
    "煤炭": "IND_COAL_MINING", "采矿": "IND_MINING",
    "金融": "IND_FINANCE", "农业": "IND_AGRICULTURE",
}

# Category -> regulationType mapping
CAT_TYPE = {
    "industry_guide": "pdf_industry_guide",
    "compliance_guide": "pdf_compliance_guide",
    "reference_material": "pdf_reference",
    "ipo_guide": "pdf_ipo_guide",
    "cpa_study": "pdf_cpa_study",
    "enterprise_report": "pdf_enterprise_report",
    "financial_template": "pdf_financial_template",
    "general": "pdf_general",
}


def split_into_sections(pages: list[dict], filename: str) -> list[dict]:
    """Split PDF pages into meaningful sections (chapters/sections)."""
    sections = []
    current_title = ""
    current_text = ""
    current_start_page = 1

    for page in pages:
        text = page["text"]
        page_num = page["page"]

        # Detect section headers
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            # Match chapter/section patterns
            is_header = False
            if re.match(r"^第[一二三四五六七八九十]+[章节篇]", line):
                is_header = True
            elif re.match(r"^[一二三四五六七八九十]+[、．.]", line) and len(line) < 50:
                is_header = True
            elif re.match(r"^\d+[.、]\s*\S", line) and len(line) < 50:
                is_header = True

            if is_header and current_text and len(current_text) >= 100:
                sections.append({
                    "title": current_title or f"{filename} P{current_start_page}",
                    "text": current_text[:5000],
                    "start_page": current_start_page,
                })
                current_title = line[:100]
                current_text = ""
                current_start_page = page_num
            else:
                current_text += line + "\n"
                if not current_title and line and len(line) > 5 and len(line) < 80:
                    current_title = line

    # Last section
    if current_text and len(current_text) >= 50:
        sections.append({
            "title": current_title or f"{filename} P{current_start_page}",
            "text": current_text[:5000],
            "start_page": current_start_page,
        })

    # If no sections found, create one per ~3 pages
    if not sections and pages:
        chunk_size = 3
        for i in range(0, len(pages), chunk_size):
            chunk_pages = pages[i:i+chunk_size]
            chunk_text = "\n".join(p["text"] for p in chunk_pages)
            if len(chunk_text) >= 50:
                sections.append({
                    "title": f"{filename} P{chunk_pages[0]['page']}-{chunk_pages[-1]['page']}",
                    "text": chunk_text[:5000],
                    "start_page": chunk_pages[0]["page"],
                })

    return sections


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/extracted/pdf_docs.json")
    parser.add_argument("--db", default="data/finance-tax-graph")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        docs = json.load(f)

    print(f"Loaded {len(docs)} PDF extractions")

    if not args.dry_run:
        import kuzu
        db = kuzu.Database(args.db)
        conn = kuzu.Connection(db)
        # Get valid IDs
        valid_tax = set()
        r = conn.execute("MATCH (t:TaxType) RETURN t.id")
        while r.has_next():
            valid_tax.add(r.get_next()[0])
        valid_ind = set()
        r = conn.execute("MATCH (i:FTIndustry) RETURN i.id")
        while r.has_next():
            valid_ind.add(r.get_next()[0])
    else:
        conn = None
        valid_tax = set(TAX_KW.values())
        valid_ind = set(IND_KW.values())

    total_nodes = 0
    total_edges = 0

    for doc in docs:
        if "error" in doc:
            continue

        filename = doc["filename"]
        category = doc["category"]
        industry = doc.get("industry", "")
        reg_type = CAT_TYPE.get(category, "pdf_general")
        pages = doc.get("pages", [])

        # Split into sections
        sections = split_into_sections(pages, filename)
        if not sections:
            continue

        for j, section in enumerate(sections):
            nid = f"LR_PDF_{hashlib.md5(f'{filename}_{j}'.encode()).hexdigest()[:10]}"
            title = f"[PDF-{category}] {section['title'][:120]}"
            content = section["text"]

            if len(content) < 50:
                continue

            total_nodes += 1

            if args.dry_run:
                continue

            # Create node
            try:
                sql = (
                    f"CREATE (n:LawOrRegulation {{"
                    f"id: '{esc(nid)}', title: '{esc(title[:200])}', "
                    f"regulationNumber: '', issuingAuthority: 'doc-tax-pdf', "
                    f"regulationType: '{reg_type}', "
                    f"issuedDate: date('2026-01-01'), effectiveDate: date('2026-01-01'), "
                    f"expiryDate: date('2099-12-31'), status: 'reference', hierarchyLevel: 99, "
                    f"sourceUrl: '{esc(filename)}', "
                    f"contentHash: '{hashlib.sha256(content.encode()).hexdigest()[:16]}', "
                    f"fullText: '{esc(content[:5000])}', "
                    f"validTimeStart: timestamp('2026-01-01 00:00:00'), "
                    f"validTimeEnd: timestamp('2099-12-31 00:00:00'), "
                    f"txTimeCreated: timestamp('2026-03-16 00:00:00'), "
                    f"txTimeUpdated: timestamp('2026-03-16 00:00:00')"
                    f"}})"
                )
                conn.execute(sql)
            except Exception:
                continue

            # Edge-first: tax type edges
            search_text = title + " " + content[:500]
            for kw, tid in TAX_KW.items():
                if kw in search_text and tid in valid_tax:
                    try:
                        conn.execute(
                            "MATCH (a:LawOrRegulation), (b:TaxType) "
                            "WHERE a.id = $aid AND b.id = $bid "
                            "CREATE (a)-[:LR_ABOUT_TAX]->(b)",
                            {"aid": nid, "bid": tid}
                        )
                        total_edges += 1
                    except:
                        pass

            # Industry edges
            for kw, iid in IND_KW.items():
                if kw in search_text and iid in valid_ind:
                    try:
                        conn.execute(
                            "MATCH (a:LawOrRegulation), (b:FTIndustry) "
                            "WHERE a.id = $aid AND b.id = $bid "
                            "CREATE (a)-[:LR_ABOUT_INDUSTRY]->(b)",
                            {"aid": nid, "bid": iid}
                        )
                        total_edges += 1
                    except:
                        pass

    print(f"\nResults:")
    print(f"  Nodes: +{total_nodes}")
    print(f"  Edges: +{total_edges}")

    if conn:
        r = conn.execute("MATCH (n) RETURN count(n)")
        print(f"  Total nodes: {r.get_next()[0]}")


if __name__ == "__main__":
    main()
