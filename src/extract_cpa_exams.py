#!/usr/bin/env python3
"""Extract CPA exam questions from archived exam papers (1997-2020).

Archives contain PDF/DOC/DOCX files with real CPA exam questions and answers.
Extracts individual questions, classifies by year/subject, and outputs JSON
to data/extracted/cpa_exams/ with a manifest.

Usage:
    .venv/bin/python3 src/extract_cpa_exams.py
    .venv/bin/python3 src/extract_cpa_exams.py --dry-run
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("ERROR: PyMuPDF not installed. Run: pip install PyMuPDF")

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

# -- Constants ----------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = PROJECT_ROOT / "doc-tax" / "09CPA学习" / "1997-2020年CPA真题答案与解析"
OUTPUT_DIR = PROJECT_ROOT / "data" / "extracted" / "cpa_exams"

# CPA subject name normalization
SUBJECT_MAP = {
    "会计": "accounting",
    "审计": "audit",
    "税法": "tax_law",
    "财管": "financial_management",
    "财务成本管理": "financial_management",
    "经济法": "economic_law",
    "战略": "strategy",
    "公司战略与风险管理": "strategy",
    "公司战略": "strategy",
}

# Regex for detecting year in filename
RE_YEAR = re.compile(r"((?:19|20)\d{2})")

# Regex for question numbering patterns in CPA exams
RE_QUESTION_NUM = re.compile(
    r"^(?:"
    r"(?:第?\s*)?(\d{1,3})\s*[、.．]\s*|"                        # 1. / 1、
    r"[（(]\s*(\d{1,3})\s*[）)]\s*|"                              # (1)
    r"(?:题目|第)\s*(\d{1,3})\s*(?:题|\.)|"                       # 题目1 / 第1题
    r"(\d{1,3})\s*[．.]\s*(?:[\u4e00-\u9fff])"                   # 1．中文
    r")",
    re.MULTILINE,
)

# Question type headers
RE_QUESTION_TYPE = re.compile(
    r"((?:一|二|三|四|五|六|七|八|九|十)[、．.]\s*"
    r"(?:单项选择题|多项选择题|综合题|计算分析题|计算题|"
    r"简答题|案例分析题|计算回答题|判断题|"
    r"单选题|多选题|名词解释|论述题|分析题))",
    re.MULTILINE,
)

# Answer pattern
RE_ANSWER = re.compile(
    r"(?:答案\s*[:：]\s*|【答案】\s*|参考答案\s*[:：]?\s*)([A-Da-d,，、\s]+|[√×对错是否])",
)

# Choice option pattern
RE_CHOICE = re.compile(r"[A-D][、.．)\s]")


# -- Archive extraction -------------------------------------------------------


def extract_zip(zip_path: Path, target_dir: Path) -> list[Path]:
    """Extract a .zip file, return list of extracted file paths."""
    extracted = []
    with zipfile.ZipFile(str(zip_path), "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            # Handle encoding issues with Chinese filenames
            try:
                name = info.filename
                # Try to fix garbled Chinese filenames
                try:
                    name = info.filename.encode("cp437").decode("gbk")
                except (UnicodeDecodeError, UnicodeEncodeError):
                    try:
                        name = info.filename.encode("cp437").decode("utf-8")
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        name = info.filename

                ext = Path(name).suffix.lower()
                if ext not in (".pdf", ".doc", ".docx", ".txt"):
                    continue

                out_path = target_dir / Path(name).name
                # Avoid collisions
                if out_path.exists():
                    stem = out_path.stem
                    out_path = target_dir / f"{stem}_{hashlib.md5(name.encode()).hexdigest()[:6]}{ext}"

                with zf.open(info) as src, open(out_path, "wb") as dst:
                    dst.write(src.read())
                extracted.append(out_path)
            except Exception as e:
                print(f"  WARN: failed to extract {info.filename}: {e}")
    return extracted


def extract_rar(rar_path: Path, target_dir: Path) -> list[Path]:
    """Extract a .rar file using unar CLI, return list of extracted file paths."""
    # Use unar (macOS universal archiver)
    try:
        result = subprocess.run(
            ["unar", "-o", str(target_dir), "-f", str(rar_path)],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            print(f"  WARN: unar failed for {rar_path.name}: {result.stderr[:200]}")
            return []
    except FileNotFoundError:
        print("  ERROR: unar not found. Install with: brew install unar")
        return []

    # Collect extracted files
    extracted = []
    for root, _dirs, files in os.walk(target_dir):
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext in (".pdf", ".doc", ".docx", ".txt"):
                extracted.append(Path(root) / fname)
    return extracted


# -- Text extraction -----------------------------------------------------------


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract all text from a PDF."""
    texts = []
    try:
        doc = fitz.open(str(pdf_path))
        for page in doc:
            text = page.get_text().strip()
            if text:
                texts.append(text)
        doc.close()
    except Exception as e:
        print(f"  WARN: PDF read failed {pdf_path.name}: {e}")
    return "\n\n".join(texts)


def extract_docx_text(docx_path: Path) -> str:
    """Extract all text from a DOCX file."""
    if DocxDocument is None:
        print("  WARN: python-docx not installed, skipping DOCX")
        return ""
    try:
        doc = DocxDocument(str(docx_path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        print(f"  WARN: DOCX read failed {docx_path.name}: {e}")
        return ""


def extract_doc_text(doc_path: Path) -> str:
    """Extract text from a .doc file using macOS textutil."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name
        result = subprocess.run(
            ["textutil", "-convert", "txt", "-output", tmp_path, str(doc_path)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            text = Path(tmp_path).read_text(encoding="utf-8", errors="replace")
            os.unlink(tmp_path)
            return text
        else:
            print(f"  WARN: textutil failed for {doc_path.name}: {result.stderr[:200]}")
            os.unlink(tmp_path)
            return ""
    except Exception as e:
        print(f"  WARN: doc conversion failed {doc_path.name}: {e}")
        return ""


def extract_file_text(file_path: Path) -> str:
    """Extract text from any supported file."""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf_text(file_path)
    elif ext == ".docx":
        return extract_docx_text(file_path)
    elif ext == ".doc":
        return extract_doc_text(file_path)
    elif ext == ".txt":
        try:
            return file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""
    return ""


# -- Question parsing ----------------------------------------------------------


def detect_subject(filename: str, text: str) -> str:
    """Detect the CPA subject from filename or content.

    Uses guillemet-quoted subject names (e.g. 《税法》) for higher precision,
    then falls back to keyword matching with disambiguation.
    """
    # Priority: look for guillemet-quoted subject names (most precise)
    for source in [filename, text[:500]]:
        for cn_name, en_name in SUBJECT_MAP.items():
            pattern = f"《{cn_name}》"
            if pattern in source:
                return en_name

    # Specific multi-char subjects first (avoid false positives from 会计 in 注册会计师)
    ORDERED_SUBJECTS = [
        ("公司战略与风险管理", "strategy"),
        ("公司战略", "strategy"),
        ("财务成本管理", "financial_management"),
        ("经济法", "economic_law"),
        ("税法", "tax_law"),
        ("审计", "audit"),
        ("战略", "strategy"),
        ("财管", "financial_management"),
        ("会计", "accounting"),  # Last -- avoid matching 注册会计师
    ]

    for source in [filename, text[:500]]:
        for cn_name, en_name in ORDERED_SUBJECTS:
            # For "会计", require it NOT to be part of "注册会计师"
            if cn_name == "会计":
                # Match 会计 only if not preceded by 注册 and not followed by 师
                import re as _re
                if _re.search(r"(?<!注册)会计(?!师)", source):
                    return en_name
            elif cn_name in source:
                return en_name

    return "unknown"


def detect_year(filename: str, text: str) -> int | None:
    """Detect the exam year from filename or content."""
    # Filename first
    m = RE_YEAR.search(filename)
    if m:
        year = int(m.group(1))
        if 1997 <= year <= 2025:
            return year

    # Content header
    m = RE_YEAR.search(text[:300])
    if m:
        year = int(m.group(1))
        if 1997 <= year <= 2025:
            return year

    return None


def split_by_question_type(text: str) -> list[dict]:
    """Split text into sections by question type headers."""
    matches = list(RE_QUESTION_TYPE.finditer(text))
    if not matches:
        return [{"type": "unknown", "text": text}]

    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        type_name = m.group(1).strip()
        # Normalize type
        q_type = "unknown"
        if "单" in type_name and "选择" in type_name:
            q_type = "single_choice"
        elif "多" in type_name and "选择" in type_name:
            q_type = "multiple_choice"
        elif "判断" in type_name:
            q_type = "true_false"
        elif "综合" in type_name:
            q_type = "comprehensive"
        elif "计算" in type_name and ("分析" in type_name or "回答" in type_name):
            q_type = "calculation_analysis"
        elif "计算" in type_name:
            q_type = "calculation"
        elif "简答" in type_name:
            q_type = "short_answer"
        elif "案例" in type_name:
            q_type = "case_analysis"
        elif "名词" in type_name:
            q_type = "definition"
        elif "论述" in type_name:
            q_type = "essay"

        sections.append({
            "type": q_type,
            "type_cn": type_name,
            "text": text[start:end].strip(),
        })

    return sections


def parse_choice_questions(text: str, q_type: str) -> list[dict]:
    """Parse individual choice questions from a section."""
    questions = []

    # Split by question number patterns
    parts = re.split(r"\n(?=\s*\d{1,3}\s*[、.．])", text)
    if len(parts) <= 1:
        # Try alternative split
        parts = re.split(r"\n(?=\s*(?:第?\s*)?\d{1,3}\s*(?:题|[、.．]))", text)

    for part in parts:
        part = part.strip()
        if len(part) < 15:
            continue

        # Extract question number
        num_match = RE_QUESTION_NUM.match(part)
        q_num = None
        if num_match:
            q_num = next((g for g in num_match.groups() if g), None)

        # Extract answer
        answer = None
        ans_match = RE_ANSWER.search(part)
        if ans_match:
            answer = ans_match.group(1).strip()

        # Detect if it has choice options
        has_choices = bool(RE_CHOICE.search(part))

        if has_choices or len(part) > 20:
            # Clean up the question text
            q_text = part
            # Remove answer line for cleaner question text
            if ans_match:
                q_text_clean = part[:ans_match.start()].strip()
            else:
                q_text_clean = q_text

            questions.append({
                "number": int(q_num) if q_num else None,
                "type": q_type,
                "question": q_text_clean[:2000],
                "answer": answer,
                "has_choices": has_choices,
                "full_text": part[:3000],
            })

    return questions


def parse_subjective_questions(text: str, q_type: str) -> list[dict]:
    """Parse subjective questions (comprehensive, calculation, short answer)."""
    questions = []

    # Split by question boundaries (numbered or keyword-based)
    parts = re.split(
        r"\n(?=\s*(?:第?\s*)?\d{1,3}\s*[、.．题]|资料[:：]|题目[:：])",
        text,
    )

    for part in parts:
        part = part.strip()
        if len(part) < 30:
            continue

        # Look for sub-questions
        sub_parts = re.split(r"\n(?=\s*[（(]\s*\d+\s*[）)])", part)

        # Extract answer/solution
        answer = None
        ans_idx = part.find("【答案】")
        if ans_idx == -1:
            ans_idx = part.find("参考答案")
        if ans_idx == -1:
            # Try "答：" pattern
            ans_match = re.search(r"\n\s*答[:：]", part)
            if ans_match:
                ans_idx = ans_match.start()

        if ans_idx >= 0:
            answer = part[ans_idx:].strip()[:3000]
            question_text = part[:ans_idx].strip()
        else:
            question_text = part

        questions.append({
            "number": None,
            "type": q_type,
            "question": question_text[:3000],
            "answer": answer,
            "has_sub_questions": len(sub_parts) > 1,
            "sub_question_count": len(sub_parts) - 1 if len(sub_parts) > 1 else 0,
            "full_text": part[:5000],
        })

    return questions


def parse_questions(text: str) -> list[dict]:
    """Parse all questions from exam text."""
    sections = split_by_question_type(text)
    all_questions = []

    for section in sections:
        q_type = section["type"]
        section_text = section["text"]

        if q_type in ("single_choice", "multiple_choice", "true_false"):
            qs = parse_choice_questions(section_text, q_type)
        else:
            qs = parse_subjective_questions(section_text, q_type)

        for q in qs:
            q["section_type_cn"] = section.get("type_cn", "")
        all_questions.extend(qs)

    return all_questions


def extract_knowledge_points(questions: list[dict]) -> list[str]:
    """Extract referenced knowledge points from questions."""
    kp_patterns = [
        r"(?:根据|依据|按照).*?(?:准则|规定|规则|法规|条例)",
        r"《.*?》",  # Law/regulation references in guillemets
        r"第[一二三四五六七八九十\d]+章",
        r"(?:增值税|消费税|企业所得税|个人所得税|印花税|房产税|车船税|土地增值税|城建税|资源税|关税|城镇土地使用税|契税|耕地占用税|烟叶税|船舶吨税|环保税)",
        r"(?:资产减值|收入确认|合并报表|长期股权投资|金融工具|租赁|所得税会计|外币折算|会计政策变更|会计估计变更|或有事项|资产负债表日后事项|持续经营|关联方)",
    ]

    points = set()
    for q in questions:
        text = q.get("question", "") + " " + (q.get("answer") or "")
        for pattern in kp_patterns:
            for m in re.finditer(pattern, text):
                point = m.group(0).strip()
                if 2 < len(point) < 60:
                    points.add(point)

    return sorted(points)


# -- Main pipeline -------------------------------------------------------------


def process_archive(archive_path: Path, tmp_base: Path) -> list[dict]:
    """Process one archive file, return list of exam paper results."""
    ext = archive_path.suffix.lower()
    archive_name = archive_path.stem

    # Create temp extraction dir
    tmp_dir = tmp_base / archive_name
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Extracting: {archive_path.name} ---")

    if ext == ".zip":
        files = extract_zip(archive_path, tmp_dir)
    elif ext == ".rar":
        files = extract_rar(archive_path, tmp_dir)
    else:
        print(f"  WARN: unsupported archive format: {ext}")
        return []

    print(f"  Extracted {len(files)} document files")

    results = []
    for fpath in sorted(files):
        print(f"  Processing: {fpath.name}")
        text = extract_file_text(fpath)
        if not text or len(text) < 50:
            print(f"    WARN: insufficient text ({len(text)} chars), skipping")
            continue

        year = detect_year(fpath.name, text)
        subject = detect_subject(fpath.name, text)
        questions = parse_questions(text)
        knowledge_points = extract_knowledge_points(questions)

        # Count questions with answers
        answered = sum(1 for q in questions if q.get("answer"))

        result = {
            "source_archive": archive_path.name,
            "source_file": fpath.name,
            "file_hash": hashlib.sha256(text[:4096].encode()).hexdigest()[:16],
            "year": year,
            "subject": subject,
            "subject_cn": next(
                (cn for cn, en in SUBJECT_MAP.items() if en == subject),
                subject,
            ),
            "total_chars": len(text),
            "question_count": len(questions),
            "answered_count": answered,
            "knowledge_points": knowledge_points,
            "questions": questions,
        }

        if questions:
            print(f"    OK: year={year}, subject={subject}, "
                  f"{len(questions)} questions ({answered} with answers), "
                  f"{len(knowledge_points)} knowledge points")
        else:
            print(f"    NOTE: no structured questions found (raw text: {len(text)} chars)")

        results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(description="Extract CPA exam questions from archives")
    parser.add_argument("--dry-run", action="store_true", help="List archives without extracting")
    args = parser.parse_args()

    # Validate paths
    if not ARCHIVE_DIR.exists():
        sys.exit(f"ERROR: archive dir not found: {ARCHIVE_DIR}")

    archives = sorted(
        p for p in ARCHIVE_DIR.iterdir()
        if p.suffix.lower() in (".zip", ".rar")
    )
    print(f"Found {len(archives)} archives in {ARCHIVE_DIR.name}")
    for a in archives:
        print(f"  {a.name} ({a.stat().st_size / 1024 / 1024:.1f} MB)")

    if args.dry_run:
        print("\n[DRY RUN] Would extract and process the above archives.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Use a temp dir for archive extraction
    with tempfile.TemporaryDirectory(prefix="cpa_exam_") as tmp_base:
        all_results = []
        for archive in archives:
            results = process_archive(archive, Path(tmp_base))
            all_results.extend(results)

    # Save individual JSON per exam paper
    saved_files = []
    for result in all_results:
        year = result["year"] or "unknown"
        subject = result["subject"]
        safe_name = re.sub(r"[^\w\-]", "_", result["source_file"])[:60]
        filename = f"{year}_{subject}_{safe_name}.json"
        out_path = OUTPUT_DIR / filename

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        saved_files.append(filename)

    # Build manifest
    year_dist = {}
    subject_dist = {}
    total_questions = 0
    total_answered = 0
    all_knowledge_points = set()
    sample_questions = []

    for r in all_results:
        y = str(r["year"] or "unknown")
        s = r["subject"]
        qc = r["question_count"]
        year_dist[y] = year_dist.get(y, 0) + qc
        subject_dist[s] = subject_dist.get(s, 0) + qc
        total_questions += qc
        total_answered += r["answered_count"]
        all_knowledge_points.update(r["knowledge_points"])

        # Collect sample questions (first 2 from each paper, up to 20 total)
        for q in r["questions"][:2]:
            if len(sample_questions) < 20:
                sample_questions.append({
                    "year": r["year"],
                    "subject": r["subject"],
                    "type": q["type"],
                    "question": q["question"][:300],
                    "answer": (q.get("answer") or "")[:200],
                })

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "src/extract_cpa_exams.py",
        "source_dir": str(ARCHIVE_DIR.relative_to(PROJECT_ROOT)),
        "output_dir": str(OUTPUT_DIR.relative_to(PROJECT_ROOT)),
        "stats": {
            "archives_processed": len(archives),
            "papers_extracted": len(all_results),
            "total_questions": total_questions,
            "total_answered": total_answered,
            "unique_knowledge_points": len(all_knowledge_points),
        },
        "by_year": dict(sorted(year_dist.items())),
        "by_subject": dict(sorted(subject_dist.items())),
        "knowledge_points": sorted(all_knowledge_points)[:200],
        "sample_questions": sample_questions,
        "files": [
            {
                "filename": r.get("source_file", ""),
                "archive": r.get("source_archive", ""),
                "year": r.get("year"),
                "subject": r.get("subject"),
                "question_count": r.get("question_count", 0),
                "answered_count": r.get("answered_count", 0),
                "output_file": f"data/extracted/cpa_exams/"
                    f"{r['year'] or 'unknown'}_{r['subject']}_"
                    f"{re.sub(r'[^\\w\\-]', '_', r['source_file'])[:60]}.json",
            }
            for r in all_results
        ],
    }

    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Summary
    print(f"\n{'='*60}")
    print(f"CPA Exam Extraction Complete")
    print(f"{'='*60}")
    print(f"Archives processed: {len(archives)}")
    print(f"Papers extracted:   {len(all_results)}")
    print(f"Total questions:    {total_questions}")
    print(f"With answers:       {total_answered}")
    print(f"Knowledge points:   {len(all_knowledge_points)}")
    print(f"\nBy year:")
    for y, c in sorted(year_dist.items()):
        print(f"  {y}: {c} questions")
    print(f"\nBy subject:")
    for s, c in sorted(subject_dist.items()):
        print(f"  {s}: {c} questions")
    print(f"\nOutput: {OUTPUT_DIR}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
