#!/usr/bin/env python3
"""Extract content from high-value PDF files in doc-tax/.

Uses PyMuPDF (fitz) to extract text, then structures into injection-ready JSON.
Focus: regulatory guides, compliance handbooks, industry inspection guides.

Usage:
    python3 src/extract_pdf_docs.py [--output data/extracted/pdf_docs.json] [--dry-run]
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install PyMuPDF")
    sys.exit(1)

DOC_TAX = Path("doc-tax")

# High-value PDF files to extract (skip DeepSeek/Python cheatsheets)
PRIORITY_PDFS = [
    # Compliance & Regulation
    "福建省民营企业涉税合规自查手册.pdf",
    # Industry guides (行业账务风险筹划)
    "3.财税实战工具大全/5.行业账务风险筹划/*.pdf",
    # Financial management templates
    "3.财税实战工具大全/4.行业财务制度范本/*.pdf",
    # Key reference docs
    "3.财税实战工具大全/9.财税实战资料下载/*.pdf",
    # IPO guides
    "1.财税脑图分类合集/财税优化/IPO*.pdf",
    # CPA exam materials
    "09CPA学习/2021版高顿CPA内部资料*/CPA税法加油包/*.pdf",
    "09CPA学习/2021版高顿CPA内部资料*/CPA会计加油包/*.pdf",
    # Enterprise report examples
    "企业报告示例/*.pdf",
]

# Skip patterns (non-finance content)
SKIP_PATTERNS = [
    "DeepSeek", "Python数据科学", "Keras", "Scikit", "Spark",
    "Matplotlib", "Seaborn", "Numpy", "Pandas",
]


def should_skip(filepath: str) -> bool:
    return any(p in filepath for p in SKIP_PATTERNS)


def extract_pdf(pdf_path: Path) -> dict:
    """Extract text content from a PDF file."""
    try:
        doc = fitz.open(str(pdf_path))
        pages = []
        total_text = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                pages.append({"page": page_num + 1, "text": text.strip()})
                total_text += text + "\n"
        doc.close()

        # Determine category from path
        rel_path = str(pdf_path.relative_to(DOC_TAX))
        category = "general"
        if "行业账务风险筹划" in rel_path:
            category = "industry_guide"
        elif "行业财务制度范本" in rel_path:
            category = "financial_template"
        elif "财税实战资料下载" in rel_path:
            category = "reference_material"
        elif "IPO" in rel_path or "财税优化" in rel_path:
            category = "ipo_guide"
        elif "CPA" in rel_path or "09CPA" in rel_path:
            category = "cpa_study"
        elif "企业报告" in rel_path:
            category = "enterprise_report"
        elif "合规" in rel_path or "自查" in rel_path:
            category = "compliance_guide"

        # Detect industry from filename/content
        industry = ""
        industry_kw = {
            "房地产": "房地产业", "建筑": "建筑业", "医美": "医疗美容",
            "医疗美容": "医疗美容", "物业": "物业管理", "网络直播": "网络直播",
            "劳务派遣": "劳务派遣", "合伙企业": "合伙企业",
            "民间非营利": "民间非营利组织", "高新技术": "高新技术企业",
            "律师事务所": "律师事务所", "汽车经销": "汽车经销",
            "幼儿园": "学前教育", "再生资源": "再生资源",
            "出口退税": "出口退税企业",
        }
        for kw, ind in industry_kw.items():
            if kw in pdf_path.name or kw in total_text[:2000]:
                industry = ind
                break

        return {
            "filename": pdf_path.name,
            "rel_path": rel_path,
            "category": category,
            "industry": industry,
            "page_count": len(pages),
            "total_chars": len(total_text),
            "content_hash": hashlib.sha256(total_text.encode()).hexdigest()[:16],
            "pages": pages,
            "full_text": total_text[:10000],  # Cap at 10K for injection
        }
    except Exception as e:
        return {
            "filename": pdf_path.name,
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/extracted/pdf_docs.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Find all PDFs
    pdf_files = list(DOC_TAX.rglob("*.pdf"))
    pdf_files = [p for p in pdf_files if not should_skip(str(p))]
    pdf_files.sort(key=lambda p: p.stat().st_size, reverse=True)

    print(f"Found {len(pdf_files)} PDF files (after skip filter)")

    results = []
    total_chars = 0
    total_pages = 0

    for i, pdf_path in enumerate(pdf_files):
        if args.dry_run:
            size_kb = pdf_path.stat().st_size / 1024
            print(f"  [{i+1}] {pdf_path.name} ({size_kb:.0f} KB)")
            continue

        result = extract_pdf(pdf_path)
        if "error" in result:
            print(f"  [{i+1}] ERROR: {pdf_path.name}: {result['error']}")
            continue

        results.append(result)
        total_chars += result["total_chars"]
        total_pages += result["page_count"]

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{len(pdf_files)} | {total_pages} pages | {total_chars:,} chars")

    if args.dry_run:
        print(f"\nDry run: {len(pdf_files)} PDFs to process")
        return

    # Save extracted data
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Summary
    by_cat = {}
    for r in results:
        cat = r["category"]
        by_cat[cat] = by_cat.get(cat, 0) + 1

    print(f"\n{'='*50}")
    print(f"Extracted: {len(results)} PDFs")
    print(f"Total pages: {total_pages}")
    print(f"Total chars: {total_chars:,}")
    print(f"By category:")
    for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
