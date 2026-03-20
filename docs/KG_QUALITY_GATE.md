# KG Quality Gate Standard

> CogNebula 知识图谱入库门禁标准 v1.0

## Gate Thresholds

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| `title` length | >= 5 chars | Nodes without titles display as raw IDs in visualization |
| `content/fullText` length | >= 20 chars | Content too short to be meaningful knowledge atom |
| Title coverage | >= 95% per table | Ensures visual readability |
| Edge density | >= 0.5 edges/node | Below this, graph is mostly disconnected islands |
| No raw ID leak | title must not start with `{'_id':`, `{'offset':`, `TRM_` | Internal IDs must never reach display layer |

## Enforcement Points

### 1. API Ingest Gate (`/api/v1/ingest`)
- Pre-validates all nodes before DB insertion
- Rejects nodes failing any gate check
- Returns `rejected` array with reasons for upstream correction
- Rejection does NOT count as error (upstream can fix and retry)

### 2. CLI Quality Gate (`scripts/kg_quality_gate.py`)
```bash
# Validate JSON file before ingest
python3 scripts/kg_quality_gate.py data/extracted/doctax_extracted.json

# Audit live KG via API
python3 scripts/kg_quality_gate.py --check-api
```

### 3. Quality Audit Endpoint (`/api/v1/quality`)
Returns:
- Per-table title coverage stats
- Edge density metrics
- Isolated node counts
- Overall quality score (0-100)
- Gate verdict: PASS/FAIL

## Data Repair Scripts

| Script | Purpose | Run on |
|--------|---------|--------|
| `scripts/fix_empty_titles.py` | Extract titles from content for empty-title nodes | kg-node |
| `scripts/fix_trm_labels.py` | Replace TRM_ codes with Chinese labels | kg-node |
| `scripts/enrich_tax_edges.py` | Add MENTIONS edges for isolated tax types | kg-node |

All scripts support `--dry-run` flag.

## Execution Order

```bash
# 1. Dry run all repairs
python3 scripts/fix_empty_titles.py --dry-run
python3 scripts/fix_trm_labels.py --dry-run
python3 scripts/enrich_tax_edges.py --dry-run

# 2. Apply repairs
python3 scripts/fix_empty_titles.py
python3 scripts/fix_trm_labels.py
python3 scripts/enrich_tax_edges.py

# 3. Verify via API
curl http://100.75.77.112:8400/api/v1/quality | python3 -m json.tool
```

## Quality Score Formula

```
score = 100
score -= max(0, (0.95 - title_coverage) * 100)   # Title coverage penalty
score -= max(0, (0.50 - edge_density) * 50)        # Edge density penalty
score -= min(20, (isolated_nodes / total_nodes) * 200)  # Isolation penalty
```

- **>= 80**: Healthy graph
- **60-79**: Acceptable, some repairs needed
- **< 60**: FAIL — block new ingestion until repaired

---

Maurice | maurice_wen@proton.me
