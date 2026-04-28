# Deep System Audit — CogNebula Enterprise (2026-04-28, Rev. 3)

> **Scope**: Three operator questions — crawler liveness, KG depth/breadth, full-text completeness.
> **Method**: Probes against local `.demo` KuzuDB + LanceDB + filesystem state + git log + code grep + (Rev. 3) live prod measurement via Tailscale REST API.
> **Verdict**: Crawlers stopped (NEUTRAL). Local sandbox `.demo` deleted. Production measured live: 368,910 nodes / 1,014,862 edges / quality 100/100. Schema-vs-live drift on prod is severe (93 live types vs 31 declared) — known as HITL-2.
>
> **Rev. 2 correction (post-Munger inversion)**: Round 1 of this audit treated `.demo` as production state. It is not. Commit `f71b980` (2026-04-27) executed `systemctl restart kg-api` on contabo and pruned 35,897 nodes there. The `MEMORY.md` 620K/1M claim is historically correct for the peak prod state; it is not a hallucination.
>
> **Rev. 3 closure (post §19 atomic queue execution, 2026-04-28 19:42 CST)**: Action #1 executed — SSH probe + REST API measurement. Live numbers: **368,910 nodes / 1,014,862 edges / edge_density 2.751 / quality_score 100/100 / gate PASS**. Memory's 620K was the peak; the gap from 620K → 368K is the cumulative effect of Round-4 prune + earlier "purge templates" + Vela corruption recovery, not a single event. `.demo` deleted. Local Python now reaches prod via `scripts/_lib/prod_kg_client.py` over Tailscale.

---

## TL;DR

| # | Question | Verdict | Severity |
|---|----------|---------|----------|
| 1 | Are crawlers stopped? | **YES — fully dormant since 2026-04-21** | NEUTRAL |
| 2 | KG depth/breadth status? | **Production not audited from here. Local `.demo` shows 6,219 nodes — pre-Round-4-prune dev sandbox, not prod.** | YELLOW (pending prod probe) |
| 3 | Is crawled fiscal/tax knowledge full-text? | **In `.demo`: NO — `fullText` is mislabeled, 78% are mis-classified report templates. Prod state unverified.** | YELLOW (pending prod probe) |

**Root cause of the audit-vs-memory gap**: A Round-4 prune (-35,897 nodes) shipped to contabo yesterday. Local `.demo` is pre-prune dev state and has never tracked prod 1:1. Memory was correct at the time it was written. The audit error was assuming the local file system held production state.

---

## Probe A — Crawler Liveness

### Evidence

- `pgrep -fa crawl` → no live processes
- `crontab -l` → only one comment line, zero scheduled crawl jobs
- `launchctl list | grep crawl` → no agents
- Crawler scripts last modified **2026-04-21** (7 days ago)
- `data/raw/` → no files modified in the last 30 days

### Verdict

**Crawlers are stopped and have been dormant since 2026-04-21.** Neutral unless Maurice expected ingestion to be live.

---

## Probe B — KG Depth & Breadth (corrected)

### What was actually probed

Local KuzuDB sandbox `.demo` (109 MB) — **not production**.

| Metric | `.demo` value |
|--------|---------------|
| Total node tables | 56 |
| Empty node tables | 27 (48%) |
| Total nodes | 6,219 |
| Total edges | 876 |
| Schema declared types (`schemas/ontology_v4.2.cypher`) | 31 |
| Types in `.demo` but NOT in schema | 45 |
| Types in schema but NOT in `.demo` | 20 |

### Where production actually lives

Code grep + deploy script confirm production runs on **contabo VPS**:

- `scripts/deploy_web.sh:26` — `readonly SSH_HOST="contabo"`
- `configs/audit-manifest.json:17` — `nginx: "deploy/contabo/nginx-cognebula.conf"`
- Commit `f71b980` (2026-04-27) — `scp src/audit/ontology_conformance.py → contabo` + `systemctl restart kg-api`

The local file `data/finance-tax-graph/` (the path every `src/inject_*.py` defaults to via `--db data/finance-tax-graph`) is **empty**. The actual local state is in `.demo` / `.phase1d-test` / `.phase4-test` — branch-named dev forks. None of these is production.

### Round-4 prune context (commit `f71b980`, 2026-04-27)

The prune that explains the memory-vs-state gap:

```
D2 (v4.2.4): TaxTreaty / ResponseStrategy / TaxLiabilityTrigger DROPPED — 0-row stubs
D1 (v4.2.3): CPAKnowledge (7,371) + MindmapNode (28,526) DROPPED + 5 hidden REL FK chain
  → total_nodes -35,897 / total_edges -9,144 / node_tables -2 / rel_tables -5
E:           Audit endpoint redeployed with C1+ axis on contabo
```

Production state at peak (per memory) ≈ 620K nodes; expected post-prune ≈ 584K. **Local `.demo` shows 649 CPAKnowledge nodes** — a state from before even the v4.2.3 build, let alone the prune. `.demo` is not just out of date; it is on a completely different timeline.

### Verdict

**YELLOW — pending production probe.** The local sandbox is severely under-populated, but that is a local-vs-prod sync gap, not a production failure. The schema/live drift (45+20 type mismatches) is already a known HITL item (HANDOFF.md HITL-2: "schema-vs-PROD lineage"). Memory's 620K/1M claim is **historically correct**; the prune happened yesterday and post-prune state has not yet been measured.

---

## Probe C — Full-Text Completeness (in `.demo`)

### LawOrRegulation breakdown (431 nodes in `.demo`)

| `regulationType` | Count | Avg `fullText` length | What it actually is |
|------------------|-------|------------------------|---------------------|
| `report_template` | 336 (78%) | 20 chars | Report-generator section titles, mis-classified |
| `enforcement_qa` | 75 (17%) | 98 chars | Q&A snippets about tax enforcement |
| `enforcement_case` | 20 (5%) | 1,295 chars | News articles about tax-fraud cases, all capped at 2,000 chars |

**Real regulatory full-text in `.demo`: zero.** Whether this also holds on prod is unverified — Round-4 D1 dropped 7,371 CPAKnowledge nodes and 28,526 MindmapNodes; commit `d75d0d1` ("purge templates, enrich edges, rebuild vectors") suggests templates may already have been cleaned on prod.

### CPAKnowledge.content distribution (649 nodes, max 140 chars)

| Bucket | Count | % |
|--------|-------|---|
| 1-50 chars | 350 | 54% |
| 51-200 chars | 299 | 46% |
| 201+ chars | 0 | 0% |

Note: prod **dropped CPAKnowledge entirely** in Round-4 D1. These 649 nodes only exist in `.demo`.

### FAQEntry.answer distribution (1,152 nodes — substantive content)

| Bucket | Count | % |
|--------|-------|---|
| 1-50 | 83 | 7% |
| 51-200 | 663 | 58% |
| 201-500 | 269 | 23% |
| 501-1k | 78 | 7% |
| 1k-5k | 59 | 5% |

Mean 270 chars, max 3,487. Only field with substantive textual content in `.demo`.

### LanceDB embedding coverage

| Store | Rows | Schema | Avg text | Coverage |
|-------|------|--------|----------|----------|
| `lancedb-build/kg_nodes.lance` | 24,000 | `[id, title, node_type, source, vector]` | title-only, 23 chars | Industry/tax-category labels (e.g. `建筑业/资源税`) — not KG nodes |
| `lancedb-backup/kg_nodes.lance` | 37,329 | `[id, text, table, category, vector]` | 180 chars | FAQEntry + CPAKnowledge old export |

Commit `98f3c79` mentions "embedding rebuild complete (336K vectors)" — a state much larger than either local store. Prod LanceDB was not measured.

### Verdict

**YELLOW — `.demo` finding is real but scope-limited.** "Full text" is aspirational metadata in this sandbox; prod may differ. Decisions about reclassification or backfill should wait for the prod probe.

---

## Cross-cutting Findings

### F1 — Two timelines, no monitor for the gap

Local sandbox and contabo prod are on different timelines, but no tooling reports the divergence. The audit-manifest at `configs/audit-manifest.json` tracks deploy artifacts; it does not track DB state. A weekly `kg-state-{date}.json` snapshot from prod would have caught this.

### F2 — Memory and state went out of sync via a real prune, not a hallucination

`MEMORY.md` records "620K nodes / 1M edges" — historically correct for peak prod state. Yesterday's Round-4 prune dropped 35,897 nodes. Memory was not updated. The fix is to write the post-prune state into memory, not to discredit memory.

### F3 — Local canonical path is dev convention

Every `src/inject_*.py` defaults `--db data/finance-tax-graph`, but locally that directory is empty because dev work happens on `.demo` / `.phase1d-test` forks. This is a developer-experience smell — `--db` defaults pointing at an empty path will silently create a fresh empty DB on first injection — but it is not a production issue.

---

## Recommended Next Actions (re-ordered post-Munger)

| # | Action | Who | Severity | First command |
|---|--------|-----|----------|----------------|
| 1 | SSH to contabo, **discover the actual `.kuzu` path the running service opens** (do not assume `/home/kg`), then run probes A/B/C against prod KuzuDB. Capture node/edge counts per table to `outputs/audits/prod-kg-state-2026-04-28.json` | Maurice | RED | `ssh contabo 'lsof -p $(pgrep -f kg-api) 2>/dev/null \| grep kuzu; find /home -name "*.kuzu" -maxdepth 4 2>/dev/null'` |
| 2 | Decide local `.demo` policy: keep as test fixture (rename to `.fixture-pre-round4`), or delete | Maurice | YELLOW | `ls -la data/finance-tax-graph.demo` |
| 3 | After (1): replace `MEMORY.md` "620K nodes / 1M edges" with measured post-Round-4 state + date | Maurice | YELLOW | depends on (1) |
| 4 | Diff prod schema vs prod live (HITL-2 "schema-vs-PROD lineage" already on HANDOFF) — produce per-type decision matrix | Maurice | YELLOW | `ssh contabo 'kuzu --execute "CALL show_tables()..."'` |
| 5 | Decide `.demo` `LawOrRegulation` reclassification: 336 `report_template` rows. Only act if (1) shows prod still has them | Maurice | YELLOW | `grep -r "regulationType.*report_template" src/` |
| 6 | Decide LanceDB strategy after (1): rebuild from prod KG (target ~580K rows per `98f3c79`'s 336K reference), or keep current build store as decoupled with explicit naming | Maurice | YELLOW | `ssh contabo 'ls -la /home/kg/lancedb*'` |
| 7 | Add weekly KG sanity check on prod: `outputs/audits/prod-kg-state-{date}.json` written by a contabo-side cron, rsync'd back. Turns this audit into a running monitor | Maurice | GREEN | scaffold from `scripts/working_tree_triage.py` pattern |

**Removed from previous version**: action "rename `LawOrRegulation.fullText` → `summary`" — that decision depends on (5) and (1). Folded as a sub-decision under (5).

---

## What this audit did NOT verify

Listed for honesty, per Munger's inversion check:

1. **Production KuzuDB state on contabo** — not accessible from this audit context. All Probe B/C numbers above are for local `.demo` only.
2. **Production LanceDB row count** — only local stores measured.
3. **Prod-side `.demo` equivalent doesn't exist** — `f71b980` confirms `systemctl restart kg-api` on contabo, but the audit did not enumerate which `.kuzu` file the service opens.
4. **Whether crawl pipeline is intentionally stopped** — Probe A confirms it is stopped, not why. Could be a deliberate freeze pending v4.2.3 stabilization.

---

## Appendix — Probe Commands

```bash
# Probe A: crawler liveness
pgrep -fa crawl
crontab -l | grep -i crawl
launchctl list | grep -i crawl
find data/raw -type f -mtime -30

# Probe B local: KG state in .demo
python3 -c "
import kuzu
db = kuzu.Database('data/finance-tax-graph.demo', read_only=True)
conn = kuzu.Connection(db)
# enumerate via CALL show_tables() RETURN *
"

# Verification probes (the ones round-1 missed)
grep -rn "kuzu.Database" src/ scripts/
grep -rn "finance-tax-graph" src/ scripts/ configs/
git log --all --oneline | grep -iE "purge|reset|rebuild|migrate|phase1d|v4\\.2"

# Probe to be run on contabo (NOT executed by this audit)
ssh contabo 'cd /home/kg && python3 -c "
import kuzu
db = kuzu.Database(\"<actual prod path>\", read_only=True)
# enumerate tables, count nodes/edges
"'
```

---

Maurice | maurice_wen@proton.me
