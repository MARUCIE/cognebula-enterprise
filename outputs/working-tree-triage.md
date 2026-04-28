# Working Tree Triage Manifest

- **Run (UTC)**: `2026-04-28T00:59:53Z`
- **Branch**: `main`
- **HEAD**: `f581e2c`
- **Schema version**: 1

## Summary

- Total dirty entries: **766**
- Status breakdown: `{' M': 222, ' D': 315, '??': 229}`

| Bucket | Count |
|---|---:|
| `critical_code` | 162 |
| `tests` | 47 |
| `docs` | 367 |
| `configs` | 3 |
| `data_or_cache` | 26 |
| `other` | 161 |

## Top-5 by churn per bucket

### `critical_code` — 162 files, +9998 / -3774

| Status | Path | + | - | Churn |
|---|---|---:|---:|---:|
| ` M` | `scripts/seed_v42_phase6_expand_cr_pen.py` | 886 | 349 | 1235 |
| ` M` | `src/api/kg_api.py` | 765 | 126 | 891 |
| ` M` | `scripts/migrate_v4.1.py` | 539 | 344 | 883 |
| ` M` | `scripts/seed_v42_phase3.py` | 599 | 186 | 785 |
| ` M` | `scripts/seed_v42_phase5_expand_rs_pc.py` | 505 | 238 | 743 |

### `tests` — 47 files, +0 / -0

| Status | Path | + | - | Churn |
|---|---|---:|---:|---:|
| `??` | `tests/e2e/` | 0 | 0 | 0 |
| `??` | `tests/fixtures/` | 0 | 0 | 0 |
| `??` | `tests/golden/` | 0 | 0 | 0 |
| `??` | `tests/integration/` | 0 | 0 | 0 |
| `??` | `tests/performance/` | 0 | 0 | 0 |

### `docs` — 367 files, +1420 / -20561

| Status | Path | + | - | Churn |
|---|---|---:|---:|---:|
| ` M` | `HANDOFF.md` | 1221 | 1374 | 2595 |
| ` D` | `doc/00_project/initiative_finance_tax_kb/FINANCE_TAX_SKILL_TEAM_ARCHITECTURE-zh.html` | 0 | 717 | 717 |
| ` D` | `doc/00_project/initiative_finance_tax_kb/COGNEBULA_ONTOLOGY_V4-zh.html` | 0 | 705 | 705 |
| ` D` | `skills/team-finance-tax/SKILL.md` | 0 | 162 | 162 |
| ` D` | `skills/ft-tax-incentive/SKILL.md` | 0 | 134 | 134 |

### `configs` — 3 files, +40 / -11

| Status | Path | + | - | Churn |
|---|---|---:|---:|---:|
| ` M` | `docker-compose.yml` | 25 | 2 | 27 |
| ` M` | `Dockerfile` | 12 | 9 | 21 |
| ` M` | `worker/wrangler.toml` | 3 | 0 | 3 |

### `data_or_cache` — 26 files, +0 / -0

| Status | Path | + | - | Churn |
|---|---|---:|---:|---:|
| `??` | `outputs/reports/ontology-audit-swarm/2026-04-20-kg-sota-gap.html` | 0 | 0 | 0 |
| `??` | `outputs/reports/ontology-audit-swarm/2026-04-20-v4.2-sota-gap-analysis.html` | 0 | 0 | 0 |
| `??` | `outputs/reports/ontology-audit-swarm/2026-04-21-enterprise-readiness-status.html` | 0 | 0 | 0 |
| `??` | `outputs/reports/ontology-audit-swarm/2026-04-21-session-quality-audit.html` | 0 | 0 | 0 |
| `??` | `outputs/reports/ontology-audit-swarm/2026-04-22-session-delta-audit.html` | 0 | 0 | 0 |

### `other` — 161 files, +14299 / -4703

| Status | Path | + | - | Churn |
|---|---|---:|---:|---:|
| ` M` | `src/inject_tax_incentives.py` | 1661 | 675 | 2336 |
| ` M` | `src/inject_tax_rates.py` | 1558 | 409 | 1967 |
| ` M` | `src/cognebula.py` | 1478 | 397 | 1875 |
| ` M` | `web/src/app/expert/data-quality/page.tsx` | 655 | 203 | 858 |
| ` M` | `src/seed_data.py` | 763 | 94 | 857 |

---

> Re-generate with: `python3 scripts/working_tree_triage.py`.
> JSON form at `outputs/working-tree-triage.json` for re-ingestion.
