#!/usr/bin/env python3
"""P0-1: Extract enterprise report structures from 8 PDFs using PyMuPDF.

Extracts chapters, sections, indicators, risk dimensions from each report.
Output: data/extracted/enterprise_reports/ with one JSON per report + manifest.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF

BASE_DIR = Path("/Users/mauricewen/Projects/cognebula-enterprise")
INPUT_DIR = BASE_DIR / "doc-tax" / "企业报告示例"
OUTPUT_DIR = BASE_DIR / "data" / "extracted" / "enterprise_reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Heading detection heuristics
CHAPTER_RE = re.compile(r"^[一二三四五六七八九十]+[、.．]|^第[一二三四五六七八九十百]+[章节篇]|^\d{1,2}[、.．]\s*\S")
SECTION_RE = re.compile(r"^[（(]\s*[一二三四五六七八九十\d]+\s*[）)]|^\d{1,2}\.\d+|^[①②③④⑤⑥⑦⑧⑨⑩]")
INDICATOR_RE = re.compile(r"[\u6307\u6807]|rate|ratio|score|index|指数|比率|占比|增长率|合计|总计", re.IGNORECASE)
RISK_RE = re.compile(r"风险|预警|异常|违规|稽查|risk|warning|alert", re.IGNORECASE)


def classify_line(text: str) -> str:
    """Classify a text line as chapter/section/indicator/risk/content."""
    stripped = text.strip()
    if not stripped:
        return "empty"
    if CHAPTER_RE.match(stripped):
        return "chapter"
    if SECTION_RE.match(stripped):
        return "section"
    if RISK_RE.search(stripped):
        return "risk_dimension"
    if INDICATOR_RE.search(stripped):
        return "indicator"
    return "content"


def extract_report(pdf_path: Path) -> dict:
    """Extract structured content from a single PDF report."""
    doc = fitz.open(str(pdf_path))
    result = {
        "file": pdf_path.name,
        "file_size_bytes": pdf_path.stat().st_size,
        "page_count": len(doc),
        "chapters": [],
        "indicators": [],
        "risk_dimensions": [],
        "tables": [],
        "metadata": {},
    }

    current_chapter = None
    current_section = None
    all_text_lines = []
    seen_indicators = set()
    seen_risks = set()

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Extract text blocks with font size info for heading detection
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if block["type"] != 0:  # skip image blocks
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans).strip()
                if not text:
                    continue
                max_font_size = max(s["size"] for s in spans)
                is_bold = any("bold" in s.get("font", "").lower() for s in spans)

                line_type = classify_line(text)

                # Large font or bold + chapter pattern = chapter heading
                if max_font_size >= 14 or (is_bold and max_font_size >= 12):
                    if line_type in ("chapter", "content") and len(text) < 60:
                        line_type = "chapter"

                if line_type == "chapter":
                    current_chapter = {
                        "title": text,
                        "page": page_num + 1,
                        "sections": [],
                        "content_lines": 0,
                    }
                    result["chapters"].append(current_chapter)
                    current_section = None
                elif line_type == "section":
                    current_section = {
                        "title": text,
                        "page": page_num + 1,
                    }
                    if current_chapter:
                        current_chapter["sections"].append(current_section)
                elif line_type == "indicator":
                    indicator_text = text[:100]
                    if indicator_text not in seen_indicators:
                        seen_indicators.add(indicator_text)
                        result["indicators"].append({
                            "text": text,
                            "page": page_num + 1,
                            "chapter": current_chapter["title"] if current_chapter else None,
                        })
                elif line_type == "risk_dimension":
                    risk_text = text[:100]
                    if risk_text not in seen_risks:
                        seen_risks.add(risk_text)
                        result["risk_dimensions"].append({
                            "text": text,
                            "page": page_num + 1,
                            "chapter": current_chapter["title"] if current_chapter else None,
                        })

                if current_chapter and line_type == "content":
                    current_chapter["content_lines"] += 1

                all_text_lines.append(text)

        # Extract tables
        tables = page.find_tables()
        for table in tables:
            extracted = table.extract()
            if extracted and len(extracted) > 1:
                headers = [str(c).strip() if c else "" for c in extracted[0]]
                result["tables"].append({
                    "page": page_num + 1,
                    "headers": headers,
                    "row_count": len(extracted) - 1,
                    "chapter": current_chapter["title"] if current_chapter else None,
                })

    doc.close()

    result["metadata"] = {
        "total_text_lines": len(all_text_lines),
        "total_chapters": len(result["chapters"]),
        "total_sections": sum(len(c.get("sections", [])) for c in result["chapters"]),
        "total_indicators": len(result["indicators"]),
        "total_risk_dimensions": len(result["risk_dimensions"]),
        "total_tables": len(result["tables"]),
    }

    return result


def main():
    pdfs = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdfs:
        print("ERROR: No PDFs found in", INPUT_DIR)
        sys.exit(1)

    manifest = {
        "extracted_at": datetime.now().isoformat(),
        "source_dir": str(INPUT_DIR),
        "output_dir": str(OUTPUT_DIR),
        "reports": [],
    }

    for pdf_path in pdfs:
        print(f"  Extracting: {pdf_path.name} ...", end=" ", flush=True)
        try:
            report = extract_report(pdf_path)
            slug = pdf_path.stem
            out_path = OUTPUT_DIR / f"{slug}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            meta = report["metadata"]
            print(f"OK ({meta['total_chapters']} chapters, {meta['total_indicators']} indicators, "
                  f"{meta['total_risk_dimensions']} risks, {meta['total_tables']} tables)")

            manifest["reports"].append({
                "file": pdf_path.name,
                "output": out_path.name,
                "pages": report["page_count"],
                **meta,
            })
        except Exception as e:
            print(f"ERROR: {e}")
            manifest["reports"].append({
                "file": pdf_path.name,
                "error": str(e),
            })

    # Write manifest
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    total_chapters = sum(r.get("total_chapters", 0) for r in manifest["reports"])
    total_indicators = sum(r.get("total_indicators", 0) for r in manifest["reports"])
    total_risks = sum(r.get("total_risk_dimensions", 0) for r in manifest["reports"])
    total_tables = sum(r.get("total_tables", 0) for r in manifest["reports"])
    print(f"\nP0-1 DONE: {len(pdfs)} reports -> {total_chapters} chapters, "
          f"{total_indicators} indicators, {total_risks} risk dimensions, {total_tables} tables")
    print(f"  Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
