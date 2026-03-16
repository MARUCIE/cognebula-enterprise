#!/usr/bin/env python3
"""P0-4: Fix low-quality mindmap extractions.

Problem files:
- 行业相关.doc -> 7MB, only 1 node extracted (151 pages, 32K words!)
- 公司相关/公司相关.docx -> 1.7MB, only 3 nodes extracted
- 财税优化/ directory -> 5MB+, only 49 nodes from multiple files

Strategy:
1. .docx files: try python-docx, extract paragraph hierarchy
2. .doc files (Composite Document): use textutil -convert txt, parse structure
3. Parse indentation/heading levels to reconstruct mindmap tree
4. Output fixed extractions to data/extracted/mindmap_fixes/
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import docx

BASE_DIR = Path("/Users/mauricewen/Projects/cognebula-enterprise")
OUTPUT_DIR = BASE_DIR / "data" / "extracted" / "mindmap_fixes"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MINDMAP_BASE = BASE_DIR / "doc-tax" / "财税脑图3.0" / "1.财税脑图分类合集"


def convert_doc_to_text(doc_path: Path) -> str:
    """Convert .doc to plain text using macOS textutil."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["textutil", "-convert", "txt", "-output", tmp_path, str(doc_path)],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"textutil failed: {result.stderr}")
        with open(tmp_path, "r", encoding="utf-8") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def extract_docx_hierarchy(docx_path: Path) -> list[dict]:
    """Extract paragraph hierarchy from .docx using python-docx."""
    try:
        doc = docx.Document(str(docx_path))
    except Exception as e:
        print(f"    python-docx failed: {e}")
        return []

    nodes = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Determine level from style
        style_name = para.style.name if para.style else ""
        level = 0
        if "Heading" in style_name:
            try:
                level = int(re.search(r"\d+", style_name).group())
            except (AttributeError, ValueError):
                level = 1
        elif para.paragraph_format and para.paragraph_format.left_indent:
            # Indentation-based level
            indent_pt = para.paragraph_format.left_indent
            if indent_pt:
                level = min(int(indent_pt / 360000) + 1, 10)  # EMU to level

        # Check for outline numbering in text
        outline_match = re.match(r"^([一二三四五六七八九十]+)[、.．]\s*", text)
        if outline_match:
            level = max(level, 1)

        is_bold = any(run.bold for run in para.runs if run.bold is not None)

        nodes.append({
            "text": text,
            "level": level,
            "style": style_name,
            "is_bold": is_bold,
        })

    return nodes


def parse_text_to_nodes(text: str, source_name: str) -> list[dict]:
    """Parse plain text (from textutil) into hierarchical nodes.

    Mindmap docs often use tabs or spaces for indentation,
    or numbered/bulleted outlines.
    """
    lines = text.split("\n")
    nodes = []
    current_l1 = ""
    current_l2 = ""

    for line in lines:
        if not line.strip():
            continue

        # Detect indentation
        raw_indent = len(line) - len(line.lstrip())
        tab_count = line.count("\t")
        level = tab_count if tab_count > 0 else raw_indent // 2
        stripped = line.strip()

        # Detect heading patterns
        if re.match(r"^[一二三四五六七八九十]+[、.．]", stripped):
            level = max(level, 1)
            current_l1 = stripped
        elif re.match(r"^[（(][一二三四五六七八九十\d]+[）)]", stripped):
            level = max(level, 2)
            current_l2 = stripped
        elif re.match(r"^\d+[、.．]", stripped):
            level = max(level, 2)

        nodes.append({
            "text": stripped,
            "level": level,
            "parent_l1": current_l1 if level > 1 else "",
            "parent_l2": current_l2 if level > 2 else "",
        })

    return nodes


def build_tree(nodes: list[dict]) -> dict:
    """Build a tree structure from flat nodes with levels."""
    root = {"text": "root", "children": [], "level": -1}
    stack = [root]

    for node in nodes:
        level = node.get("level", 0)
        tree_node = {
            "text": node["text"],
            "level": level,
            "children": [],
        }

        # Pop stack until we find a parent with lower level
        while len(stack) > 1 and stack[-1]["level"] >= level:
            stack.pop()

        stack[-1]["children"].append(tree_node)
        stack.append(tree_node)

    return root


def count_tree_nodes(tree: dict) -> int:
    """Count total nodes in tree."""
    count = 1  # self
    for child in tree.get("children", []):
        count += count_tree_nodes(child)
    return count


def fix_industry_doc():
    """Fix: 行业相关.doc (7MB, 151 pages, 32K words -> was only 1 node)."""
    doc_path = MINDMAP_BASE / "行业相关.doc"
    print(f"\n  [P0-4a] Fixing: {doc_path.name} ({doc_path.stat().st_size / 1024 / 1024:.1f} MB)")

    if not doc_path.exists():
        print("    ERROR: File not found")
        return {"file": doc_path.name, "error": "not found"}

    print("    Converting with textutil ...", flush=True)
    text = convert_doc_to_text(doc_path)
    line_count = len(text.splitlines())
    print(f"    Extracted {len(text)} chars, {line_count} lines")

    # Save raw text
    raw_path = OUTPUT_DIR / "行业相关_raw.txt"
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(text)

    nodes = parse_text_to_nodes(text, "行业相关")
    tree = build_tree(nodes)
    total = count_tree_nodes(tree) - 1  # exclude root

    result = {
        "file": doc_path.name,
        "category": "行业相关",
        "extraction_method": "textutil + text parsing",
        "total_nodes": total,
        "flat_nodes": nodes,
        "tree": tree,
        "raw_text_chars": len(text),
        "raw_text_lines": line_count,
        "extracted_at": datetime.now().isoformat(),
    }

    out_path = OUTPUT_DIR / "行业相关_fixed.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"    OK: {total} nodes (was: 1)")
    return {"file": doc_path.name, "nodes": total, "output": out_path.name}


def fix_company_docx():
    """Fix: 公司相关/公司相关.docx (1.7MB -> was only 3 nodes)."""
    docx_path = MINDMAP_BASE / "公司相关" / "公司相关.docx"
    print(f"\n  [P0-4b] Fixing: {docx_path.name} ({docx_path.stat().st_size / 1024 / 1024:.1f} MB)")

    if not docx_path.exists():
        print("    ERROR: File not found")
        return {"file": docx_path.name, "error": "not found"}

    # Try python-docx first
    print("    Trying python-docx ...", flush=True)
    nodes = extract_docx_hierarchy(docx_path)

    if len(nodes) < 10:
        # Fallback to textutil
        print(f"    python-docx got only {len(nodes)} nodes, trying textutil ...", flush=True)
        text = convert_doc_to_text(docx_path)
        line_count = len(text.splitlines())
        print(f"    textutil: {len(text)} chars, {line_count} lines")

        raw_path = OUTPUT_DIR / "公司相关_raw.txt"
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(text)

        nodes = parse_text_to_nodes(text, "公司相关")
        method = "textutil + text parsing"
    else:
        method = "python-docx paragraph extraction"

    tree = build_tree(nodes)
    total = count_tree_nodes(tree) - 1

    # Also process sub-files in the directory
    sub_nodes = []
    sub_dir = MINDMAP_BASE / "公司相关"
    sub_files = [f for f in sub_dir.iterdir() if f.name != "公司相关.docx" and f.suffix in (".doc", ".docx", ".xls")]
    for sf in sorted(sub_files):
        print(f"    Sub-file: {sf.name}", flush=True)
        if sf.suffix == ".docx":
            sn = extract_docx_hierarchy(sf)
            if not sn:
                try:
                    st = convert_doc_to_text(sf)
                    sn = parse_text_to_nodes(st, sf.stem)
                except Exception as e:
                    print(f"      WARN: {e}")
        elif sf.suffix == ".doc":
            try:
                st = convert_doc_to_text(sf)
                sn = parse_text_to_nodes(st, sf.stem)
            except Exception as e:
                print(f"      WARN: {e}")
                sn = []
        else:
            sn = []
        sub_nodes.append({"file": sf.name, "node_count": len(sn), "nodes": sn})

    result = {
        "file": docx_path.name,
        "category": "公司相关",
        "extraction_method": method,
        "total_nodes": total,
        "flat_nodes": nodes,
        "tree": tree,
        "sub_files": sub_nodes,
        "total_with_subs": total + sum(s["node_count"] for s in sub_nodes),
        "extracted_at": datetime.now().isoformat(),
    }

    out_path = OUTPUT_DIR / "公司相关_fixed.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"    OK: {result['total_with_subs']} nodes total (was: 3)")
    return {"file": docx_path.name, "nodes": result["total_with_subs"], "output": out_path.name}


def fix_tax_optimization():
    """Fix: 财税优化/ directory (5MB+ -> was only 49 nodes)."""
    opt_dir = MINDMAP_BASE / "财税优化"
    print(f"\n  [P0-4c] Fixing: 财税优化/ directory")

    if not opt_dir.exists():
        print("    ERROR: Directory not found")
        return {"dir": "财税优化", "error": "not found"}

    all_nodes = []
    file_results = []

    for f in sorted(opt_dir.iterdir()):
        if f.name.startswith("."):
            continue
        print(f"    Processing: {f.name} ({f.stat().st_size / 1024:.0f} KB)", flush=True)

        nodes = []
        method = ""

        if f.suffix == ".docx":
            nodes = extract_docx_hierarchy(f)
            method = "python-docx"
            if len(nodes) < 5:
                try:
                    text = convert_doc_to_text(f)
                    nodes = parse_text_to_nodes(text, f.stem)
                    method = "textutil fallback"
                except Exception as e:
                    print(f"      WARN textutil: {e}")

        elif f.suffix == ".doc":
            try:
                text = convert_doc_to_text(f)
                nodes = parse_text_to_nodes(text, f.stem)
                method = "textutil"
            except Exception as e:
                print(f"      WARN: {e}")

        elif f.suffix == ".pdf":
            try:
                import fitz
                doc = fitz.open(str(f))
                text_parts = []
                for page in doc:
                    text_parts.append(page.get_text("text"))
                doc.close()
                text = "\n".join(text_parts)
                nodes = parse_text_to_nodes(text, f.stem)
                method = "PyMuPDF"
            except Exception as e:
                print(f"      WARN: {e}")

        elif f.suffix in (".xls", ".xlsx"):
            # Skip spreadsheets for now, they're templates not mindmap content
            method = "skipped (spreadsheet)"

        print(f"      -> {len(nodes)} nodes ({method})")
        file_results.append({
            "file": f.name,
            "node_count": len(nodes),
            "method": method,
            "nodes": nodes,
        })
        all_nodes.extend(nodes)

    result = {
        "directory": "财税优化",
        "category": "财税优化",
        "total_nodes": len(all_nodes),
        "file_count": len(file_results),
        "files": file_results,
        "extracted_at": datetime.now().isoformat(),
    }

    out_path = OUTPUT_DIR / "财税优化_fixed.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"    OK: {len(all_nodes)} total nodes from {len(file_results)} files (was: 49)")
    return {"dir": "财税优化", "nodes": len(all_nodes), "files": len(file_results), "output": out_path.name}


def main():
    print("P0-4: Fixing low-quality mindmap extractions")

    results = {
        "extracted_at": datetime.now().isoformat(),
        "fixes": [],
    }

    results["fixes"].append(fix_industry_doc())
    results["fixes"].append(fix_company_docx())
    results["fixes"].append(fix_tax_optimization())

    # Write manifest
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in results.items() if k != "fixes" or True},
                  f, ensure_ascii=False, indent=2)

    print(f"\nP0-4 DONE: 3 fixes applied")
    for fix in results["fixes"]:
        name = fix.get("file") or fix.get("dir")
        nodes = fix.get("nodes", "ERROR")
        print(f"  {name}: {nodes} nodes")
    print(f"  Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
