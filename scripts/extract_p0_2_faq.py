#!/usr/bin/env python3
"""P0-2: Extract 1,163 QA pairs from the finance/tax FAQ mindmap doc.

The file is a .doc (Composite Document, not .docx), so python-docx won't work.
Strategy: use macOS textutil to convert to txt, then parse QA structure.

Actual format discovered:
  0001 question text？
  问
  question detail lines...
  答
  answer detail lines...
  0002 next question？
  ...

Output: data/extracted/faq/ with structured JSON.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/Users/mauricewen/Projects/cognebula-enterprise")
INPUT_FILE = BASE_DIR / "doc-tax" / "财税脑图3.0" / "3.财税实战工具大全" / "1.财税实战答疑脑图" / "财税实战答疑脑图（1163问）.doc"
OUTPUT_DIR = BASE_DIR / "data" / "extracted" / "faq"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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


def parse_qa_pairs(text: str) -> list[dict]:
    """Parse QA pairs from the extracted text.

    Format: 4-digit number + space + question, followed by 问/答 delimited blocks.
    """
    lines = text.split("\n")

    # Pattern: 4-digit number (0001-9999) followed by question text
    q_start_re = re.compile(r"^(\d{4})\s+(.+)")

    qa_pairs = []
    current_num = None
    current_question_title = None
    current_section = None  # 'question_detail', 'answer'
    question_detail_lines = []
    answer_lines = []

    def flush_current():
        """Save the current QA pair."""
        if current_num is not None and current_question_title:
            q_detail = "\n".join(question_detail_lines).strip()
            answer = "\n".join(answer_lines).strip()
            qa_pairs.append({
                "id": int(current_num),
                "question": current_question_title,
                "question_detail": q_detail if q_detail else None,
                "answer": answer if answer else None,
            })

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Check for new question start (4-digit number)
        m = q_start_re.match(stripped)
        if m:
            # Save previous QA pair
            flush_current()

            current_num = m.group(1)
            current_question_title = m.group(2).strip()
            current_section = "question_detail"
            question_detail_lines = []
            answer_lines = []
            continue

        # Check for 问 / 答 delimiters (standalone on a line)
        if stripped == "问" or stripped == "问：" or stripped == "问:":
            current_section = "question_detail"
            continue
        if stripped == "答" or stripped == "答：" or stripped == "答:":
            current_section = "answer"
            continue

        # Accumulate content
        if current_num is not None:
            if current_section == "answer":
                answer_lines.append(stripped)
            else:
                question_detail_lines.append(stripped)

    # Save last QA pair
    flush_current()

    return qa_pairs


def categorize_qa(qa: dict) -> str:
    """Auto-categorize a QA pair based on keywords in question text."""
    text = qa["question"] + " " + (qa.get("question_detail") or "")

    categories = [
        ("增值税", ["增值税", "进项", "销项", "留抵", "退税", "差额征税", "简易计税"]),
        ("企业所得税", ["企业所得税", "汇算清缴", "弥补亏损", "税前扣除"]),
        ("个人所得税", ["个税", "个人所得税", "工资薪金", "劳务报酬", "年终奖"]),
        ("发票管理", ["发票", "开票", "红字", "电子发票", "专票", "普票"]),
        ("印花税", ["印花税"]),
        ("房产税", ["房产税", "房屋", "不动产"]),
        ("土地税", ["土地增值税", "土地使用税", "城镇土地"]),
        ("社保公积金", ["社保", "公积金", "五险一金"]),
        ("公司注册变更", ["注册", "注销", "变更", "营业执照", "工商"]),
        ("资产管理", ["固定资产", "折旧", "摊销", "无形资产"]),
        ("成本费用", ["成本", "费用", "报销", "差旅"]),
        ("账务处理", ["账务", "会计", "分录", "科目", "凭证", "记账"]),
        ("税务稽查", ["稽查", "税务检查", "税务风险", "处罚"]),
        ("税收优惠", ["优惠", "减免", "免税", "小微", "高新"]),
        ("财政补贴", ["补贴", "补助", "奖励"]),
        ("IPO上市", ["IPO", "上市", "ipo"]),
        ("视同销售", ["视同销售"]),
        ("房产交易", ["买房", "卖房", "房产交易", "二手房"]),
    ]

    for cat_name, keywords in categories:
        for kw in keywords:
            if kw in text:
                return cat_name
    return "其他"


def main():
    if not INPUT_FILE.exists():
        print(f"ERROR: File not found: {INPUT_FILE}")
        sys.exit(1)

    print(f"  Converting .doc to text: {INPUT_FILE.name} ...", flush=True)
    text = convert_doc_to_text(INPUT_FILE)
    print(f"  Extracted {len(text)} chars, {len(text.splitlines())} lines")

    # Save raw text for debugging
    raw_path = OUTPUT_DIR / "raw_text.txt"
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(text)

    print("  Parsing QA pairs ...", flush=True)
    qa_pairs = parse_qa_pairs(text)

    # Auto-categorize
    for qa in qa_pairs:
        qa["category"] = categorize_qa(qa)

    # Stats
    with_answers = sum(1 for qa in qa_pairs if qa["answer"])
    with_details = sum(1 for qa in qa_pairs if qa["question_detail"])

    cat_dist = {}
    for qa in qa_pairs:
        cat = qa["category"]
        cat_dist[cat] = cat_dist.get(cat, 0) + 1

    result = {
        "extracted_at": datetime.now().isoformat(),
        "source_file": str(INPUT_FILE),
        "total_qa_pairs": len(qa_pairs),
        "qa_with_answers": with_answers,
        "qa_with_question_detail": with_details,
        "category_distribution": dict(sorted(cat_dist.items(), key=lambda x: -x[1])),
        "qa_pairs": qa_pairs,
    }

    out_path = OUTPUT_DIR / "finance_tax_faq_1163.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nP0-2 DONE: {len(qa_pairs)} QA pairs extracted ({with_answers} with answers)")
    print(f"  Categories ({len(cat_dist)}):")
    for cat, count in sorted(cat_dist.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
