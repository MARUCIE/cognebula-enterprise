#!/usr/bin/env python3
"""Convert crawled JSON files to Obsidian-flavored Markdown with wikilinks, tags, and frontmatter.

Reads JSON from data/raw/{date}/ and outputs .md files to Obsidian vault.
Each document gets:
- YAML frontmatter (source, date, tax_type, regulation_number, status)
- Wikilinks: [[增值税]] [[CAS 14]] [[一般纳税人]]
- Tags: #法规 #增值税 #2026
- Callouts for key points

Usage:
    python json_to_obsidian.py --input data/raw/2026-03-15 --vault ~/Obsidian/财税知识库
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from finance_tax_processor import extract_entities, TAX_TYPE_MAP


# Map source IDs to vault subdirectories
SOURCE_TO_DIR = {
    "chinatax": "法规/国家税务总局",
    "chinatax_fgk": "法规/国家税务总局",
    "mof": "法规/财政部",
    "npc": "法规/人大法律库",
    "customs": "法规/海关总署",
    "pbc": "法规/中国人民银行",
    "pbc_tiaofasi": "法规/中国人民银行",
    "mof_zhengcefabu": "法规/财政部",
    "ctax": "媒体/中国税务网",
    "safe_forex": "法规/外汇管理局",
    "csrc": "法规/证监会",
    "ndrc": "法规/发改委",
    "casc_accounting": "法规/会计准则委",
    "stats_gov": "数据/国家统计局",
    "samr": "法规/市场监管总局",
    "miit": "法规/工信部",
    "wallstreetcn": "媒体/华尔街见闻",
    "shui5": "媒体/税屋网",
    "thepaper": "媒体/澎湃新闻",
    "esnai": "媒体/中国会计视野",
    "baike_kuaiji": "百科/会计百科",
    "local_doctax": "本地资料/财税脑图",
    "default": "日报",
}

# Tax type name to vault directory
TAX_DIR_MAP = {
    "增值税": "税种/增值税",
    "企业所得税": "税种/企业所得税",
    "个人所得税": "税种/个人所得税",
    "消费税": "税种/消费税",
    "关税": "税种/关税",
    "印花税": "税种/印花税",
    "房产税": "税种/房产税",
    "土地增值税": "税种/土地增值税",
    "资源税": "税种/资源税",
    "环境保护税": "税种/环境保护税",
    "车船税": "税种/车船税",
    "契税": "税种/契税",
    "城市维护建设税": "税种/城市维护建设税",
}


def sanitize_filename(title: str) -> str:
    """Create a safe filename from title."""
    # Remove characters invalid in filenames
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = re.sub(r'\s+', ' ', safe).strip()
    # Truncate by bytes (ext4 max 255 bytes; leave room for .md suffix)
    max_bytes = 240
    encoded = safe.encode("utf-8")
    if len(encoded) > max_bytes:
        while len(safe.encode("utf-8")) > max_bytes:
            safe = safe[:-1]
    return safe


def generate_wikilinks(entities: dict) -> list[str]:
    """Generate Obsidian wikilinks from extracted entities."""
    links = []
    for tt in entities.get("tax_types", []):
        links.append(f"[[{tt['name']}]]")
    for tp in entities.get("taxpayer_types", []):
        name_map = {
            "general_taxpayer": "一般纳税人",
            "small_scale": "小规模纳税人",
            "small_micro": "小微企业",
            "high_tech": "高新技术企业",
            "resident_enterprise": "居民企业",
            "non_resident": "非居民企业",
        }
        if tp in name_map:
            links.append(f"[[{name_map[tp]}]]")
    return list(set(links))


def generate_tags(entities: dict, source: str) -> list[str]:
    """Generate Obsidian tags."""
    tags = ["#财税"]
    if source in ("chinatax", "mof", "npc", "customs", "pbc"):
        tags.append("#法规")
    else:
        tags.append("#资讯")
    for tt in entities.get("tax_types", []):
        tag = tt["name"].replace(" ", "")
        tags.append(f"#{tag}")
    for sig in entities.get("incentive_signals", []):
        tags.append(f"#优惠_{sig}")
    if entities.get("amendment_signals"):
        tags.append("#修订")
    return list(set(tags))


def doc_to_obsidian_md(doc: dict) -> str:
    """Convert a single document to Obsidian-flavored markdown."""
    title = doc.get("title", "Untitled")
    content = doc.get("content", "") or doc.get("text", "")
    source = doc.get("source", "default")
    url = doc.get("url", "")
    doc_date = doc.get("date", datetime.now().strftime("%Y-%m-%d"))
    doc_type = doc.get("type", "notice")

    # Extract entities for wikilinks and tags
    entities = extract_entities(content) if content else {}
    wikilinks = generate_wikilinks(entities)
    tags = generate_tags(entities, source)

    # Get regulation number if available
    reg_number = ""
    if entities.get("regulation_numbers"):
        reg_number = entities["regulation_numbers"][0]["number"]

    # Get primary tax type
    primary_tax = ""
    if entities.get("tax_types"):
        primary_tax = entities["tax_types"][0]["name"]

    # Build frontmatter
    frontmatter_lines = [
        "---",
        f"title: \"{title}\"",
        f"source: {source}",
        f"date: {doc_date}",
        f"type: {doc_type}",
        f"url: \"{url}\"",
    ]
    if reg_number:
        frontmatter_lines.append(f"regulation_number: \"{reg_number}\"")
    if primary_tax:
        frontmatter_lines.append(f"tax_type: {primary_tax}")
    if entities.get("effective_dates"):
        frontmatter_lines.append(f"effective_date: {entities['effective_dates'][0]}")
    frontmatter_lines.append(f"tags: {json.dumps(tags, ensure_ascii=False)}")
    frontmatter_lines.append(f"created: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
    frontmatter_lines.append("---")

    # Build body
    body_lines = [
        f"# {title}",
        "",
    ]

    # Metadata callout
    if reg_number or url:
        body_lines.append("> [!info] 文档信息")
        if reg_number:
            body_lines.append(f"> **文号**: {reg_number}")
        if url:
            body_lines.append(f"> **来源**: [{source}]({url})")
        if entities.get("effective_dates"):
            body_lines.append(f"> **生效日期**: {entities['effective_dates'][0]}")
        body_lines.append("")

    # Wikilinks section
    if wikilinks:
        body_lines.append(f"**相关**: {' '.join(wikilinks)}")
        body_lines.append("")

    # Main content
    if content:
        body_lines.append("## 内容")
        body_lines.append("")
        body_lines.append(content)
        body_lines.append("")

    # Key entities callout
    if entities.get("tax_rates") or entities.get("incentive_signals"):
        body_lines.append("> [!tip] 关键信息")
        if entities.get("tax_rates"):
            body_lines.append(f"> **税率**: {', '.join(str(r) + '%' for r in entities['tax_rates'])}")
        if entities.get("incentive_signals"):
            body_lines.append(f"> **优惠类型**: {', '.join(entities['incentive_signals'])}")
        body_lines.append("")

    # Tags at bottom
    body_lines.append("")
    body_lines.append(" ".join(tags))

    return "\n".join(frontmatter_lines) + "\n\n" + "\n".join(body_lines)


def determine_vault_dir(doc: dict, entities: dict) -> str:
    """Determine which vault subdirectory this document belongs in."""
    source = doc.get("source", "default")

    # Primary: by source
    vault_dir = SOURCE_TO_DIR.get(source, SOURCE_TO_DIR["default"])

    # If it's about a specific tax type, also create a symlink/copy in tax dir
    # For now, just use source-based dir
    return vault_dir


def process_directory(input_dir: Path, vault_dir: Path) -> dict:
    """Process all JSON files and output Obsidian markdown."""
    stats = {"processed": 0, "written": 0, "skipped": 0, "errors": 0}

    json_files = sorted(input_dir.glob("**/*.json"))
    if not json_files:
        print(f"WARN: No JSON files in {input_dir}")
        return stats

    for jf in json_files:
        try:
            docs = json.loads(jf.read_text(encoding="utf-8"))
            if isinstance(docs, dict):
                docs = [docs]

            for doc in docs:
                stats["processed"] += 1
                title = doc.get("title", "")
                if not title:
                    stats["skipped"] += 1
                    continue

                content = doc.get("content", "") or doc.get("text", "")
                entities = extract_entities(content) if content else {}

                # Determine output path
                sub_dir = determine_vault_dir(doc, entities)
                out_dir = vault_dir / sub_dir
                out_dir.mkdir(parents=True, exist_ok=True)

                filename = sanitize_filename(title) + ".md"
                out_path = out_dir / filename

                # Generate and write markdown
                md_content = doc_to_obsidian_md(doc)
                out_path.write_text(md_content, encoding="utf-8")
                stats["written"] += 1

        except Exception as e:
            stats["errors"] += 1
            print(f"ERROR: {jf.name}: {e}")

    print(f"OK: {stats['written']} files written, {stats['skipped']} skipped, {stats['errors']} errors")
    return stats


def main():
    parser = argparse.ArgumentParser(description="JSON to Obsidian Markdown converter")
    parser.add_argument("--input", required=True, help="Input directory with JSON files")
    parser.add_argument("--vault", required=True, help="Obsidian vault root directory")
    args = parser.parse_args()

    input_dir = Path(args.input)
    vault_dir = Path(args.vault).expanduser()

    if not input_dir.exists():
        print(f"ERROR: {input_dir} not found")
        sys.exit(1)

    vault_dir.mkdir(parents=True, exist_ok=True)
    stats = process_directory(input_dir, vault_dir)
    sys.exit(0 if stats["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
