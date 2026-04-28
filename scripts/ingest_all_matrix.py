import kuzu
import json
import glob
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "finance-tax-graph")
MATRIX_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "compliance-matrix")


def main():
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    files = glob.glob(os.path.join(MATRIX_DIR, "*.json"))
    print(f"Found {len(files)} JSON files")

    total_nodes = 0
    total_edges = 0

    for fname in sorted(files):
        if "all" in fname:
            continue

        with open(fname, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except:
                continue

            if not isinstance(data, list):
                continue

            for item in data:
                if "id" not in item:
                    continue

                r = conn.execute(
                    "MATCH (k:KnowledgeUnit {id: $id}) RETURN count(k)",
                    {"id": item["id"]},
                )
                if r.get_next()[0] > 0:
                    continue

                try:
                    conn.execute(
                        "CREATE (k:KnowledgeUnit {id: $id, title: $title, content: $content, source: $source, type: $tp, extracted_by: $eb})",
                        {
                            "id": item["id"],
                            "title": item["title"],
                            "content": item["content"],
                            "source": "compliance_matrix",
                            "tp": f"{item.get("industry", "N/A")}/{item.get("taxType", "N/A")}",
                            "eb": "ingest_all_matrix-v1",
                        },
                    )
                    total_nodes += 1

                    tax_type = item.get("taxType", "")
                    if tax_type:
                        r = conn.execute(
                            "MATCH (t:TaxType) WHERE t.name CONTAINS $tax RETURN t.id LIMIT 1",
                            {"tax": tax_type[:4]},
                        )
                        if r.has_next():
                            tt_id = str(r.get_next()[0])
                            conn.execute(
                                "MATCH (k:KnowledgeUnit {id: $kid}), (t:TaxType {id: $tid}) CREATE (k)-[:KU_ABOUT_TAX]->(t)",
                                {"kid": item["id"], "tid": tt_id},
                            )
                            total_edges += 1
                except Exception as e:
                    print(f"Error ingesting {item["id"]}: {e}")

        print(f"File {os.path.basename(fname)} processed. Total: {total_nodes} nodes.")

    print(f"Final total: +{total_nodes} nodes, +{total_edges} edges")


if __name__ == "__main__":
    main()
