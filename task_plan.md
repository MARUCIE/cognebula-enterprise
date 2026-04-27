# Task Plan: CogNebula KG 数据质量修复 + 门禁标准

## Goal
修复图谱 5 大质量问题（空标题/编码标签/稀疏连通性/无语义边/可视化重叠），并建立入库门禁确保未来数据质量。

## Current Phase
Day 3 已完成 — APPLIES_TO_CLASS 边创建完成 (+9000)

## Phases

### Phase 1: API 层修复 — 标签显示 + 序列化
- [x] 1.1 修复 `_serialize()` 处理 KuzuDB 内部类型（offset tuple → 人类可读）
- [x] 1.2 修复 `/api/sample` 标签回退逻辑：7 字段优先级链
- [x] 1.3 为 TaxRateMapping 添加中文标签映射表 (TRM_LABELS)
- [x] 1.4 添加 `/api/v1/quality` 审计端点
- [x] 1.5 `_get_node_label()` 支持 node_text/topic/item_name/productCategory 等非标准字段
- [x] 1.6 `/api/v1/nodes` 注入 `_display_label` 动态标签

### Phase 2: Ingest 门禁（Quality Gate）
- [x] 2.1 强化 `/api/v1/ingest` 验证：5 项门禁 (id/title/content/raw_id_leak)
- [x] 2.2 创建 `scripts/kg_quality_gate.py` — CLI 批量校验
- [x] 2.3 门禁标准文档：`docs/KG_QUALITY_GATE.md`

### Phase 3: 数据修复
- [x] 3.1 `/api/v1/admin/fix-titles` — 服务端动态修复（受 WAL 限制改为查询层映射）
- [x] 3.2 `/api/v1/admin/enrich-edges` — 1,754 条 MENTIONS 边连接 16 个税种到内容节点
- [x] 3.3 创建离线修复脚本（fix_empty_titles.py/fix_trm_labels.py/enrich_tax_edges.py）

### Phase 4: 前端可视化优化
- [x] 4.1 `getNodeLabel()` JS 函数 — 7 字段回退 + TRM 解码 + hash 缩短
- [x] 4.2 所有节点渲染路径集成 getNodeLabel（loadNodes/expandNode/neighbors）

### Phase 5: 验证 + 部署
- [x] 5.1 本地语法检查全部通过
- [x] 5.2 推送到 kg-node + systemctl restart
- [x] 5.3 API 验证：Quality Score 46→78, Gate FAIL→PASS
- [x] 5.4 前端截图验证（已通过 Ghost OS 验证）


## Decisions Made
- 修复策略：先修显示层（API+前端），再修数据层，最后建门禁
- 所有修复脚本放在 scripts/ 下，可重复执行（幂等）
- 门禁标准：title 必填(≥5字) + content 必填(≥20字) + 边密度目标 ≥0.5 edges/node

## Errors Encountered
- (none yet)

## Notes
- 当前数据：155,783 nodes / 37,024 edges / 0.24 edges/node
- 主要节点：DocumentSection(42K), MindmapNode(28K), RegulationClause(28K), LawOrRegulation(26K)
- 主要边：CLAUSE_OF(28K) 占 76%，其余边类型都很少


## §6. Atomic Execution Queue — Sprint D Mutation Expansion (2026-04-27)

### Phase milestone
Mutation testing currently covers 3 of 9 audit dimensions (placeholder / duplicate_id / null_coverage) + 1 compound. Six dimensions have ZERO single-axis path-independence verification: stale, integrity, jurisdiction, prohibited_role, invalid_chain, inconsistent_scope. Plus the cross-dimension orthogonality property (mutating dimension A leaves dimension B count untouched) has no test. Phase boundary = 3 highest-leverage single-axis machines + 1 orthogonality machine + nightly green run.

### Atomic queue
- [x] D.1 read existing mutation pattern — confirmed (`tests/test_data_quality_mutation.py:72-145`)
- [x] D.2 confirm 6 uncovered dimensions via inspection of `survey_type` (line 226-309 of `data_quality_survey.py`)
- [x] D.3 add `StaleMutationMachine` — toggle `effective_from` between fresh/stale dates, invariant `stale_count == #rows older than threshold`
- [x] D.4 add `IntegrityViolationMutationMachine` — toggle `reviewed_at` / `reviewed_by` independently, invariant `integrity_violations == count(XOR of pair)`
- [x] D.5 add `JurisdictionMismatchMutationMachine` — toggle `jurisdiction_code` / `jurisdiction_scope`, invariant `jurisdiction_mismatches == #rows with XOR or unknown scope`
- [x] D.6 add `OrthogonalityMachine` — non-overlapping field-routing per dim, invariant non-mutated dims stay at baseline 0
- [x] D.7 register the 4 new TestCase classes with `settings(max_examples=400, stateful_step_count=50)`
- [x] D.8 run `tests/test_data_quality_mutation.py` standalone — 8 machines passing in 33.96s
- [x] D.9 run nightly tier `./scripts/run_data_quality_tests.sh nightly` — 5,853 IDs, 5,842 pass + 11 designed-FAIL schema-completeness (HITL pending), 42.56s
- [x] D.10 PDCA updated — added `P0.8b Sprint D` section + refreshed `Final test suite status` to 12 files / 5,853 IDs / ~222K cases
- [x] D.11 Sprint D entry appended to `notes.md` with field-routing matrix + write-time bug RCA
- [x] D.12 commit landed: `7961a92` (5 files, +1185 / -19)


## §7. Atomic Execution Queue — 队列全部执行 (MVS-pattern, 2026-04-27)

### Honest skip log (out-of-scope per 能力圈 / commercial-legal exclusion)
- ⏭ **B' — P4 orphan_fk_count 第 10 维**: product-level call. Affects yiclaw + 灵阙 consumer contract. NOT autonomous test-only scope. Skipped honest, log here.
- ⏭ **HITL Plan A/B/C/D jurisdiction**: still pending Maurice decision. Schema sync remains BLOCKED.
- ⏭ **xfail policy decision**: design call (signal vs forcing function). Defer to Maurice.
- ⏭ **E' — cross-initiative switch**: out of scope for "test plan continuation". Other initiatives (accounting_agent / finance_tax_kb / lingque_fusion) untouched.

### Slice S7.1 — PDCA HTML 2份制 sync (DONE, 3 swarm rounds, 3/3 APPROVE)
- [x] S7.1.a HTML KPI band identified at line 209
- [x] S7.1.b KPI updated: `5 853 · pytest IDs · nightly 43s` (per Munger R1: dropped both `~102K` and `~222K` assertion counts as Goodhart-gameable; per Hara R1: kept only 1st-order verifiable measurements)
- [x] S7.1.c Sprint D inline insertion REVERTED (R1 swarm flagged Run 1→Run 2 chronology break + density mismatch); deferred to S7.F bundled commit
- [x] S7.1.d HTML still valid (Run 1 → code-change → test-delta → Run 2 chronology restored)
- [x] S7.1.e .md runtime drift fixed: `~45s estimate` → `~43s (empirical 42.56s)` per Hickey R2 + agent counter-investigation
- [x] S7.1.f Swarm trace at `outputs/reports/auto-swarm-trace/2026-04-27-pdca-html-slice1-kpi-sync.md`
- [ ] S7.1.g Commit `data-quality: PDCA HTML+md Slice 1 — KPI sync to Sprint D state (3-round swarm consensus)`
- ⏭ **deferred half** (logged): full Sprint D HTML narrative section; red KPI juxtaposition for `0/5 backfilled`; Sprint D §A · Act h3 mirror of P0.8b in .md

### Slice S7.2 — Property invariant +3 (DONE, 5 methods landed)
- [x] S7.2.a Read existing `test_data_quality_property.py` invariants (19 functions baseline)
- [x] S7.2.b Identify 3 high-leverage invariants: (i) idempotence of survey_type, (ii) defects_total upper bound, (iii) defects_total monotone-non-decreasing under add-only mutation
- [x] S7.2.c Implement 3 invariant CLASSES (`TestIdempotence` 2 methods + `TestDefectsUpperBound` 2 methods + `TestDefectsMonotoneAddOnly` 1 method = 5 test methods total, each `@settings(max_examples=300)`)
- [x] S7.2.d Run `pytest tests/test_data_quality_property.py -q` standalone — `24 passed in 6.12s` (was 19 → +5 methods, not +3 as initially planned: 3 conceptual invariants materialized as 2+2+1=5 methods)
- [x] S7.2.e Run nightly count: 5,853 → 5,858 (+5 IDs, not +3 — same root cause as S7.2.d)
- [x] S7.2.f Commit landed: `73ba8b3` (`data-quality: Sprint E1 — 3 new property invariants (5 test methods)`)
- ⏭ **deferred half**: 5+ more invariants (commutativity under restore, hash stability of placeholder-per-field, sample-size scaling); matrix expansion (more cells); doctests

### Slice S7.3 — Sprint E2: 1 clause-axis machine (DONE)
- [x] S7.3.a Read `src/kg/clause_inspector.py:71-161` — confirmed `inspect()` row contract: `argument_role` (str) → `is_prohibited_in_tax_law(role)` → `defect_flags.append("prohibited_role")` → `_clause_defect_counts` increments `prohibited_role_count`
- [x] S7.3.b Identified trigger field `argument_role`; `_clause_defect_counts` at `src/audit/data_quality_survey.py:215-218` consumes the flag
- [x] S7.3.c Located prohibited role value: `analogy` (类推适用) at `src/kg/argument_role_registry.py:107-117`, marked `prohibited_in_tax_law=True` per 税收法定. Clean roles selected: `yiju` (依据) + `shouquan` (授权) for two-distinct-clean transition coverage
- [x] S7.3.d Built `ProhibitedRoleMutationMachine` (400×50, 5 rules: `make_prohibited` / `make_clean` / `make_alt_clean` / `make_null_role` + initialize). Two-clean design avoids Sprint D's single-clean blind spot (same lesson as `make_alt_fresh`)
- [x] S7.3.e `pytest tests/test_data_quality_mutation.py -q` → `9 passed in 38.50s` (was 8 → +1 machine)
- [x] S7.3.f Nightly count: 5,858 → 5,859 (+1 ID, exactly as predicted)
- [ ] S7.3.g Commit `data-quality: Sprint E2 — prohibited_role mutation machine`
- ⏭ **deferred half**: `invalid_chain` machine (needs `validate_chain_id` fixture data) + `inconsistent_scope` machine (needs `_check_consistency` truth table) + Sprint E1 PDCA section update + Sprint E narrative in notes.md (single batched at end of queue)

### Final: end-of-queue housekeeping (target: 15 min)
- [ ] S7.F PDCA + notes.md narrative for Sprint E1+E2 (single bundled commit)
- [ ] S7.F commit `data-quality: Sprint E PDCA + notes sync`

### Out of scope (deferred, logged not asked)
- New audit dimensions (P4 orphan_fk_count) — product-level call
- Schema sync / xfail markers — HITL
- PDCA HTML side update — 2份制 housekeeping, separate task
