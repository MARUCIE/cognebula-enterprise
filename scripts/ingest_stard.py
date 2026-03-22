#!/usr/bin/env python3
"""Ingest STARD statute dataset into KuzuDB — tax-filtered + edge-first.

Source: https://github.com/oneal2000/STARD
Format: JSONL, each line: {"id": N, "name": "法律名第X条", "content": "条文内容"}

Strategy (Meadows Edge-First):
  1. Filter: only ingest tax/finance/accounting related articles (~5.6K of 55K)
  2. Create KU node for each article
  3. Create edges: KU_ABOUT_TAX (keyword match), REFERENCES (law name match to LR)
  4. Target: ~5.6K nodes + ~8K edges (ratio ≥ 1.4 edges/node)

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 -u scripts/ingest_stard.py
    sudo systemctl start kg-api
"""
import hashlib
import json
import logging
import re
import time
import kuzu

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("stard")

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
STARD_PATH = "/tmp/STARD/data/corpus.jsonl"

# --- Tax filter keywords (must appear in article name or content) ---
TAX_FILTER = [
    "税", "发票", "财政", "财务", "会计", "审计", "预算", "关税", "海关",
    "企业所得", "个人所得", "增值税", "消费税", "印花税", "房产税", "土地",
    "资源税", "车船", "契税", "城建", "烟叶", "耕地", "纳税", "征收",
    "退税", "抵扣", "免税", "减税", "税率", "税额", "税基", "税务",
    "税收", "缴税", "欠税", "偷税", "逃税", "骗税", "避税",
    "注册会计师", "审计报告", "财务报表", "资产评估",
]

# Tax keyword → TaxType name fragments for edge creation
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
}

# Regex to extract law name from article name (e.g., "企业所得税法实施条例" from "企业所得税法实施条例第三条")
LAW_NAME_RE = re.compile(r'^(.+?)第[一二三四五六七八九十百千\d]+条')
# Regex to find 《法规名》 in content
REF_RE = re.compile(r'《([^》]{3,40}(?:法|条例|办法|规定|通知|决定|意见|准则|制度|规则|细则))》')


def is_tax_related(name: str, content: str) -> bool:
    """Check if article is tax/finance/accounting related."""
    text = name + content
    return any(kw in text for kw in TAX_FILTER)


def extract_law_name(article_name: str) -> str:
    """Extract parent law name from article name like '企业所得税法第三条'."""
    m = LAW_NAME_RE.match(article_name)
    return m.group(1).strip() if m else ""


def main():
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    # Pre-flight
    r = conn.execute("MATCH (n) RETURN count(n)")
    before_nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    before_edges = r.get_next()[0]
    log.info("Before: %s nodes / %s edges / density %.3f",
             f"{before_nodes:,}", f"{before_edges:,}", before_edges / before_nodes if before_nodes else 0)

    # Load TaxType lookup for edge creation
    r = conn.execute("MATCH (t:TaxType) RETURN t.id, t.name")
    tax_types = {}
    while r.has_next():
        row = r.get_next()
        tax_types[str(row[0])] = str(row[1])
    log.info("TaxType nodes: %d", len(tax_types))

    # Build keyword → taxtype_id mapping
    kw_to_tt = {}
    for tt_id, tt_name in tax_types.items():
        for tax_name, keywords in TAX_KW_MAP.items():
            for kw in keywords:
                if kw in tt_name:
                    kw_to_tt[tax_name] = tt_id
                    break
    log.info("Tax keyword → TaxType mapping: %d entries", len(kw_to_tt))

    # Load LR title index for REFERENCES edge creation
    r = conn.execute("MATCH (l:LawOrRegulation) RETURN l.id, l.title LIMIT 100000")
    lr_index = {}  # title_fragment → lr_id
    while r.has_next():
        row = r.get_next()
        lr_id, lr_title = str(row[0]), str(row[1] or "")
        if len(lr_title) >= 4:
            lr_index[lr_title] = lr_id
            # Also index short form (without 中华人民共和国 prefix)
            short = lr_title.replace("中华人民共和国", "")
            if len(short) >= 4:
                lr_index[short] = lr_id
    log.info("LR title index: %d entries", len(lr_index))

    # --- Pass 1: Filter + Group by parent law ---
    t0 = time.time()
    articles = []  # (id, name, content, law_name)
    law_groups = {}  # law_name → [article_ids]

    with open(STARD_PATH) as f:
        for line in f:
            d = json.loads(line)
            name = d.get("name", "")
            content = d.get("content", "").strip()
            if len(content) < 10:
                continue
            if not is_tax_related(name, content):
                continue

            doc_id = hashlib.sha256(f"stard:{d['id']}:{name}".encode()).hexdigest()[:16]
            law_name = extract_law_name(name)
            articles.append((doc_id, name, content, law_name))

            if law_name:
                law_groups.setdefault(law_name, []).append(doc_id)

    log.info("Tax-filtered: %d articles from %d parent laws", len(articles), len(law_groups))

    # --- Pass 2: Ingest nodes + create edges ---
    inserted = 0
    skipped = 0
    edges_tax = 0
    edges_ref = 0
    edges_clause = 0
    errors = 0

    for idx, (doc_id, name, content, law_name) in enumerate(articles):
        # Check duplicate
        try:
            r = conn.execute("MATCH (k:KnowledgeUnit {id: $id}) RETURN k.id", {"id": doc_id})
            if r.has_next():
                skipped += 1
                continue
        except Exception:
            pass

        # Create KU node
        try:
            conn.execute(
                "CREATE (k:KnowledgeUnit {id: $id, title: $title, content: $content, "
                "source: $source, type: $tp})",
                {"id": doc_id, "title": name[:500], "content": content[:50000],
                 "source": "stard_statute", "tp": "statute_article"}
            )
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                log.warning("Node ERR: %s", str(e)[:100])
            continue

        # Edge 1: KU_ABOUT_TAX (keyword match)
        text = name + " " + content
        for tax_name, tt_id in kw_to_tt.items():
            if tax_name in text or any(kw in text for kw in TAX_KW_MAP.get(tax_name, [])):
                try:
                    conn.execute(
                        "MATCH (k:KnowledgeUnit {id: $kid}), (t:TaxType {id: $tid}) "
                        "CREATE (k)-[:KU_ABOUT_TAX]->(t)",
                        {"kid": doc_id, "tid": tt_id}
                    )
                    edges_tax += 1
                except Exception:
                    pass

        # Edge 2: REFERENCES (link to matching LR by parent law name)
        if law_name:
            for lr_title, lr_id in lr_index.items():
                if law_name == lr_title or lr_title.startswith(law_name):
                    try:
                        conn.execute(
                            "MATCH (k:KnowledgeUnit {id: $kid}), (l:LawOrRegulation {id: $lid}) "
                            "CREATE (k)-[:REFERENCES]->(l)",
                            {"kid": doc_id, "lid": lr_id}
                        )
                        edges_ref += 1
                        break  # One REFERENCES edge per article
                    except Exception:
                        pass

        # Edge 3: Extract 《法规名》 from content → REFERENCES
        refs_in_content = REF_RE.findall(content)
        seen_refs = set()
        for ref_name in refs_in_content[:5]:  # Cap at 5 refs per article
            if ref_name in seen_refs:
                continue
            seen_refs.add(ref_name)
            for lr_title, lr_id in lr_index.items():
                if ref_name in lr_title or lr_title.endswith(ref_name):
                    try:
                        conn.execute(
                            "MATCH (k:KnowledgeUnit {id: $kid}), (l:LawOrRegulation {id: $lid}) "
                            "CREATE (k)-[:REFERENCES]->(l)",
                            {"kid": doc_id, "lid": lr_id}
                        )
                        edges_ref += 1
                        break
                    except Exception:
                        pass

        if (idx + 1) % 500 == 0:
            elapsed = time.time() - t0
            rate = (idx + 1) / elapsed * 3600
            log.info("  [%d/%d] +%d nodes, +%d tax edges, +%d ref edges (%.0f/hr)",
                     idx + 1, len(articles), inserted, edges_tax, edges_ref, rate)

    elapsed = time.time() - t0
    total_edges = edges_tax + edges_ref + edges_clause

    # Final stats
    r = conn.execute("MATCH (n) RETURN count(n)")
    after_nodes = r.get_next()[0]
    r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
    after_edges = r.get_next()[0]

    log.info("=" * 60)
    log.info("STARD ingest complete (%.0fs)", elapsed)
    log.info("  Nodes: +%d new, %d skipped, %d errors", inserted, skipped, errors)
    log.info("  Edges: +%d total (+%d KU_ABOUT_TAX, +%d REFERENCES)", total_edges, edges_tax, edges_ref)
    log.info("  Edge ratio: %.2f edges/node", total_edges / inserted if inserted else 0)
    log.info("  Graph: %s nodes / %s edges / density %.3f",
             f"{after_nodes:,}", f"{after_edges:,}", after_edges / after_nodes)
    log.info("  Delta: +%s nodes / +%s edges",
             f"{after_nodes - before_nodes:,}", f"{after_edges - before_edges:,}")

    del conn
    del db


if __name__ == "__main__":
    main()
