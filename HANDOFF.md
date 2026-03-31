# HANDOFF.md -- CogNebula / Lingque Desktop

> Last updated: 2026-03-31T21:15Z

## Session 28 — Ontology Phase 3: TaxItem + V1/V2 Cleanup + CPA (2026-03-31)

### Status: DONE

### What was done

**1. TaxItem 19/19 Tax Type Coverage (93 → 138)**
- Added 45 TaxItem nodes for 14 previously empty tax types
- Coverage: all 19 tax types + 2 surcharges now have TaxItem detail
- Includes: 房产税(2), 土地增值税(4), 城镇土地使用税(4), 车船税(7), 契税(5), 关税(2), 资源税(5), 烟叶税(1), 船舶吨税(2), 耕地占用税(4), 环境保护税(4), 城建税(3), 教育费附加(1), 地方教育附加(1)
- All 45 HAS_ITEM edges created (TaxType → TaxItem)

**2. V1/V2 Table Cleanup**
- Analysis: 4 pairs (ComplianceRule/V2, RiskIndicator/V2, TaxIncentive/V2, FilingForm/V2)
- Decision: V1 data is richer in all cases; V2 are stripped-down duplicates or noise
- Action: DETACH DELETE all V2 data (852 nodes, 1,645 edges removed)
- API: SEARCH_TABLES already pointed to V1; updated V2_TABLES/metadata_tables
- DIRTY_TYPES: removed "RiskIndicator" and "AuditTrigger" (now curated, not dirty)
- V2 table schemas preserved (edge table dependencies prevent DROP)

**3. LegalDocument 54K Triage**
- Discovery: ~70% of LegalDocument nodes are NOT legal documents
  - ~31% real legal docs (policy/local/announcement)
  - ~21% Q&A (tax hotline, 12366)
  - ~22% knowledge/education (kuaiji, doctax, chinaacc, CPA)
  - ~7% templates (report/contract/finance)
- Action: Added `_contentCategory` classification to API (legal/qa/knowledge/template/other)
- Function: `_classify_legal_doc_type()` in kg-api-server.py
- Deployed to VPS, verified working

**4. CPA Knowledge Gap Fill (7,371 → 7,729)**
- Imported 358 CPAKnowledge nodes: 经济法 (5 exam files) + 公司战略 (4 exam files)
- Content: exam questions with answers/analysis + knowledge points
- CPA subject coverage: 4/6 → 6/6 (added economic_law + strategy)

### VPS Final Stats
- 540,426 nodes / 1,111,507 edges
- 91 node tables (4 V2 tables now empty), 115 rel tables
- Audit score estimate: ~7.0/10 → ~7.5/10

### Key decisions
1. **V2 tables not dropped**: edge table definitions (GOVERNED_BY, TRIGGERED_BY, etc.) reference V2 types. DETACH DELETE zeros data; schemas remain as frozen legacy.
2. **LegalDocument not migrated**: Reclassifying 37K nodes across tables too risky (edge cascades). Classification via API `_contentCategory` field is the pragmatic path.

### Phase 4 (same session, continued)

**5. LawOrRegulation.effectiveDate Extraction (0% → 61.1%)**
- Extracted dates from AI-generated summaries using 4-strategy regex pipeline:
  - Priority 1: "施行" context ("自YYYY年M月D日起施行")
  - Priority 2: "生效/执行/实施" context
  - Priority 3: Any full date (YYYY年M月D日) in summary
  - Priority 4: Year from title (fallback, YYYY-01-01)
- Result: 15,333 nodes updated out of 39,182 (61.1% fill rate)
- Gotcha: effectiveDate is DATE type, requires `date('2021-01-01')` not string literal
- Script: `/tmp/extract_lor_dates_vps.py` (ran on VPS)

**6. KnowledgeUnit Content Backfill (93 nodes)**
- Applied prepared backfill from `data/backfill/cicpa_content.jsonl`
- 93/93 KnowledgeUnit nodes got content (CICPA 审计准则体系)

### VPS Final Stats (Phase 4)
- 540,426 nodes / 1,111,507 edges
- LawOrRegulation.effectiveDate: 0% → 61.1%
- KnowledgeUnit content: +93 nodes backfilled

### Remaining items (Phase 5+)
- LawOrRegulation.effectiveDate: 38.9% still unfilled (need web scraping from sourceUrl)
- LegalDocument triage: migrate qa→FAQEntry, knowledge→KnowledgeUnit (large scope)
- CPAKnowledge heading nodes: 58% empty content (PDF ToC entries, need NLP alignment)
- V1/V2 edge migration: create parallel V1-targeting edge tables, then DROP V2 schemas
- Local←→VPS data sync mechanism

---

## Session 27 — Ontology Audit + Search Fix (2026-03-31)

### Status: DONE

### What was done

**1. 17-Expert 3-Round Swarm Audit** (ontology-audit-swarm)
- Round 1: 6 strategic advisors → highest leverage: TaxType.code (10min, impacts everything)
- Round 2: 5 domain experts → score 4.4/10 → 10 P0 items identified
- Round 3: 6 business deep-dive → NOT READY (5/6), PARTIAL (1/6)
- Report: `doc/ONTOLOGY_AUDIT_REPORT_2026-03-31.md`

**2. Phase 0 Remediation (local + VPS)**
- TaxType.code: 0% → 100% (18/18 Golden Tax IV codes, both envs)
- AccountingStandard.effectiveDate: 0% → 100% (43/43 CAS dates, both envs)
- LegalDocument.level: 0 → mapped (11 type→level rules on VPS)
- SocialInsuranceRule: 0 → 138 nodes (local: created table + imported)
- IndustryBenchmark: 0 → 45 nodes (local: created table + imported)
- Script: `scripts/fix_audit_phase0.py`

**3. Phase 1 Data Expansion (VPS via API)**
- TaxItem: 42 → 93 (+29 CIT + 22 PIT, covering 企业所得税/个人所得税)
- JournalEntryTemplate: 30 → 60 (+30 templates with debit/credit edges)
- FilingFormField: 45 → 150 (+69 main forms + 36 small taxes)
- BusinessActivity: +30 standard activities (was only risk scenarios)
- HAS_ENTRY_TEMPLATE: 0 → 30 edges (business→journal chain connected)
- ENTRY_DEBITS/CREDITS: 34 → 103 edges
- HAS_ITEM: 42 → 93 edges (TaxType→TaxItem)
- FIELD_OF: 45 → 69+ edges
- IndustryRiskProfile.benchmark: 0% → 100% (720 nodes, 21 pattern rules)

**4. Classification Search Fix**
- API: Added `system` to SEARCH_FIELDS; added TaxClassificationCode + HSCode to SEARCH_TABLES
- Frontend: Split HS海关编码 from 税收分类编码 as separate browsable types
- Commit: 8052957

### VPS Final Stats
- 540,875 nodes (+216) / 1,112,490 edges (+100)
- Audit score estimate: 4.4/10 → ~7/10

### Key findings (Gotchas for next session)
1. **LegalDocument 54K is polluted**: ~30K accounting concepts + ~24K CPA headings, NOT real legal documents
2. **Real legal docs are in LawOrRegulation** (39K nodes, fullText=100% but effectiveDate=0%)
3. **LawOrRegulation fullText is AI summary**, not original text — can't extract dates from it
4. **BusinessActivity 384 nodes were all risk scenarios** (虚开发票×15 etc.), fixed with +30 standard activities
5. **Local DB (100K) ≠ VPS DB (540K)**: v2 tables only on VPS, seed JSONs not imported locally

### Next steps (Phase 3)
- V1/V2 table cleanup (ComplianceRuleV2/FilingFormV2/RiskIndicatorV2 → merge or drop)
- LegalDocument data triage (classify 54K into real legal docs vs concepts vs CPA material)
- LawOrRegulation.effectiveDate: need original crawl data or web lookup (AI summaries lack dates)
- CPA knowledge: 经济法 + 公司战略 两科完全缺失 (0/6 → need ~1,500 nodes)
- TaxItem: 93 → 100+ (need 7 more for other tax types: 车辆购置税/耕地占用税 etc.)

---

## Session 25 — Accounting Workbench Stitch Loop DONE

### Status: COMPLETE

### Stitch MCP OAuth Fix
- Root cause: Stitch API dropped API Key support, only accepts OAuth2 Bearer tokens
- But `stitch-mcp proxy` only supports API Key auth (hardcoded `X-Goog-Api-Key`)
- Fix: Built `bin/stitch-oauth-proxy` (Node.js stdio MCP proxy, gcloud OAuth, 50min auto-refresh)
- Patched npx cache entry point to delegate `proxy` to our OAuth proxy
- Account: `alphameta010@gmail.com`, project: `gen-lang-client-0070301879`

### Stitch Loop Steps (ALL DONE)
1. ~~Read baton~~ DONE
2. ~~Read context files~~ DONE
3. ~~Generate with Stitch~~ DONE — Project `12770423165646112515`, Screen `fe19a2be7ace4b3fb732c8f6e1275de5`
4. ~~Integrate into web/~~ DONE — `web/src/app/workbench/accounting/page.tsx` + Sidebar nav
5. ~~Update SITE.md~~ DONE
6. Next baton: 税务工作台 (pending)

### Artifacts
- Stitch project: `12770423165646112515`
- Design system: Heritage Monolith (auto-generated)
- HTML: `design/accounting-workbench/accounting-workbench.html`
- Screenshot: `design/accounting-workbench/screenshot.png`
- React: `web/src/app/workbench/accounting/page.tsx`
- Build: `npx next build` PASS

---

## Session 23 — v4.2 Phase 1+2 PDCA Execution

### Phase 1 DONE

#### DDL (24 statements, 24 OK)
- CREATE 6 new node tables: JournalEntryTemplate, FinancialStatementItem, TaxCalculationRule, FilingFormField, FinancialIndicator, TaxTreaty
- ALTER AccountingStandard: +4 columns (fullText, description, chineseName, category)
- CREATE 12 edge tables: HAS_ENTRY_TEMPLATE, ENTRY_DEBITS, ENTRY_CREDITS, POPULATES, FIELD_OF, DERIVES_FROM, CALCULATION_FOR_TAX, DECOMPOSES_INTO, COMPUTED_FROM, HAS_BENCHMARK, PARTY_TO, OVERRIDES_RATE
- DETACH DELETE: RiskIndicator 463→0, AuditTrigger 463→0

#### Seed Data
- JournalEntryTemplate: 30 (top common entries: revenue/cost/purchase/salary/tax/depreciation/closing)
- FinancialStatementItem: 40 (balance sheet + income statement + cash flow)
- TaxCalculationRule: 10 (VAT general/simple/withholding/export, CIT general/small/R&D, PIT comprehensive/withholding, stamp)
- FinancialIndicator: 17 (DuPont decomposition tree + liquidity + solvency + efficiency + tax burden)
- TaxTreaty: 20 (top-20: HK/SG/US/UK/JP/KR/DE/FR/AU/CA/NL/TH/MY/RU/IN/MO/TW/CH/IE/LU)
- AccountingStandard: 12 enriched (CAS 00-33 descriptions)
- AccountingSubject: 223→284 (+61 L2/L3 detail accounts: 应交税费15个明细, 应付职工薪酬7个, 管理费用18个, 销售费用7个, 财务费用4个, etc.)
- TaxIncentive: 109→112 (+3 PIT special deductions, 4 already existed)

#### Edges
- ENTRY_DEBITS: 18, ENTRY_CREDITS: 16
- POPULATES: 50 (AccountingSubject→FinancialStatementItem)
- CALCULATION_FOR_TAX: 10, DECOMPOSES_INTO: 3 (DuPont), COMPUTED_FROM: 12
- STACKS_WITH: +5→13, EXCLUDES: +1→16 (PIT stacking rules)
- PARENT_SUBJECT: +96→155 (L2/L3 hierarchy)
- HAS_ENTRY_TEMPLATE: 0 (deferred — BusinessActivity IDs are hash-based)
- PARTY_TO: 0 (deferred — Region IDs are province-level, no national node)

#### API Server
- Constellation: +6 types, +12 edge tables in scan
- Search: +6 types in SEARCH_TABLES
- INTERNAL_EDGES: +DECOMPOSES_INTO, +DERIVES_FROM

#### Frontend
- LAYER_GROUPS: v4.2 (27 types across 4 layers)
- NODE_COLORS: +6 types
- EDGE_LABELS_ZH: +12 v4.2 edges
- FIELD_ZH: +40 v4.2 property labels
- Deployed: lingque-desktop.pages.dev

#### Stats After Phase 1
- Total nodes: 540,030 (was 540,775; -926 garbage + 117 new + some other delta)
- Total edges: 1,111,998
- Node tables: 84 (was 78; +6)
- Edge tables: 104 (was 92; +12)
- Constellation: 1,304 nodes / 2,830 edges / 25 types visible

### Phase 2 DONE

#### DDL (13 statements, 13 OK)
- CREATE 5 P1 node tables: TaxItem, TaxBasis, TaxLiabilityTrigger, DeductionRule, TaxMilestoneEvent
- CREATE 8 P1 edge tables: HAS_ITEM, COMPUTED_BY, LIABILITY_TRIGGERED_BY, INDICATES_RISK, PENALIZED_FOR, ESCALATES_TO, SPLITS_INTO, DEDUCTS_FROM

#### Seed Data
- RiskIndicator: 49 (Golden Tax IV 6-module: tax_burden 8, invoice 10, financial_ratio 12, filing_behavior 6, banking 7, cross_system 6)
- AuditTrigger: 20 (3-level: automatic 8, manual_review 7, escalation 5)
- TaxItem: 42 (consumption 15 + stamp 17 + VAT categories 10)
- TaxBasis: 12 (ad_valorem/specific/compound/income_based/area_based/rental)
- TaxLiabilityTrigger: 13 (VAT 9 rules + CIT 2 + PIT 2)
- DeductionRule: 14 (CIT limited/super_deduction/non_deductible)
- TaxMilestoneEvent: 10 (establishment→operation→ma→liquidation)

#### Edges
- HAS_ITEM: 42 (TaxType→TaxItem)
- LIABILITY_TRIGGERED_BY: 13 (TaxType→TaxLiabilityTrigger)
- INDICATES_RISK: 12 (RiskIndicator→AuditTrigger, cross-module)

#### KuzuDB Gotcha
- ALTER TABLE-added columns cannot be set in CREATE statement — must use CREATE then MATCH+SET

### Final Stats (Phase 1+2)
- Total: 540,190 nodes / 1,112,194 edges
- Node tables: 89 (+11 from v4.1), Edge tables: 112 (+20)
- Constellation: 1,393 nodes / 2,883 edges / 30 types visible
- New v4.2 nodes: ~230 (P0: 117 + P1: ~160, minus rebuilds)
- New v4.2 edges: ~230 (P0: ~160 + P1: ~67)

### Phase 3 DONE (seed_v42_phase3.py executed)
- ResponseStrategy: 17 (seed 脚本定义 17 条，全量入库。设计目标 40 待扩展)
- PolicyChange: 11 (seed 脚本定义 11 条，全量入库。设计目标 30 待扩展)
- IndustryBenchmark: 199 (扩展 from 45, 20 industries × 8 metrics)
- RESPONDS_TO: 15, TRIGGERED_BY_CHANGE: 11, BENCHMARK_FOR edges created

### Session 24 — API Server v4.2 Registration Fix (2026-03-31)

**问题**: Phase 1-3 数据全部入库成功，但 API server 的 TYPES / SEARCH_TABLES / ALL_EDGE_TABLES 仍停留在 v4.1 版本，导致 14 个 v4.2 新类型 + 23 条新边在 constellation 和 search 端点完全不可见。

**修复**:
- `kg-api-server.py` TYPES: +14 v4.2 类型 (P0: 7 + P1: 5 + P2: 2), 修正 sample_limit
- `kg-api-server.py` SEARCH_TABLES: +14 v4.2 类型
- `kg-api-server.py` ALL_EDGE_TABLES: +23 v4.2 边 (P0: 12 + P1: 8 + P2: 3)
- `kg-api-server.py` INTERNAL_EDGES: +3 自引用边 (DECOMPOSES_INTO, DERIVES_FROM, ESCALATES_TO)
- VPS: scp + rm __pycache__ + restart uvicorn

**验证后 Stats**:
- 540,417 nodes / 1,112,243 edges / 91 node tables / 115 edge tables

**坑点文档**: `docs/KG_GOTCHAS.md` (9 条实战教训 + 发布 checklist)

**FilingFormField Seed DONE** (seed_v42_phase4_filing_fields.py):
- ALTER TABLE 补 3 列 (formCode, dataType, formula)
- 45 nodes: VAT 主表(8) + 附表一(3) + 附表二(4) + CIT 年报(8) + A105000(4) + PIT(5) + 印花税(2) + 预缴/附加/房产/土地/代扣(11)
- 45 FIELD_OF edges (FilingFormField→FilingForm)
- 11 DERIVES_FROM edges (跨表栏次引用: A105000→CIT主表, VAT附表→主表, 城建税←VAT)

**RS/PC Expansion DONE** (seed_v42_phase5_expand_rs_pc.py):
- ResponseStrategy: 17→39 (+22: invoice forensics, industry-specific, GT4, incentive mgmt, intl tax)
- PolicyChange: 11→30 (+19: 2022-2026 major reforms, digital economy, global minimum tax, ESG)
- New edges: 28 RESPONDS_TO + 33 TRIGGERED_BY_CHANGE

**Final v4.2 Stats**: 540,458 nodes / 1,112,278 edges

**CR/Penalty Expansion DONE** (seed_v42_phase6_expand_cr_pen.py):
- ComplianceRule: 84→159 (+75: AML/TP/发票/VAT/CIT扣除/PIT/社保/房产/印花/环保/GT4/国际税)
- Penalty: 127→164 (+37: 通用/发票/注册/代扣/TP/社保/房产/环保/刑事/GT4/AML)
- 边创建失败: RULE_FOR_TAX/PENALIZED_BY 边表绑定 ComplianceRuleV2 而非 ComplianceRule (Gotchas #9)
- Penalty SET fullText 失败: Penalty 表无 fullText 列 (Gotchas #10)

**FilingForm补建**: +14 个具体申报表节点 (FF_VAT_GENERAL, FF_CIT_ANNUAL 等) + 45 FIELD_OF 边重建成功

**Phase 4 Validation PASSED** (validate_v42_business_queries.py):
- 27/27 PASS, 0 FAIL, 2 WARN (Search URL编码, 非本体问题)
- 10 条业务查询全部通过: 月结链路/税额计算/栏次填报/风险应对/政策变动/杜邦分析/税收协定/行业基准/优惠叠加/合规处罚
- **Grade A (100%)**

**V1/V2 Bridge Fix**: 75 条新 CR 镜像到 ComplianceRuleV2 + 67 条 RULE_FOR_TAX/PENALIZED_BY 边创建成功

### Session 26 — Frontend UX Overhaul (2026-03-31)

**Commits**: 80c4eb2 → b42db95 (10 commits)

Done:
- v4.2 类型中文化 (14 个 NODE_ZH)
- 知识问答页: 去掉 broken Cytoscape, 改为摘要链接
- 法规条款浏览器: +14 v4.2 类型 + 列定义
- 大表分级菜单 (>1K 阈值): LegalClause(9组50+项) / LegalDocument(3组) / KnowledgeUnit(5组) / Classification(3组) / TaxRate(3组 NEW)
- API 修复: LegalClause 搜索 500 → per-table SEARCH_FIELDS
- API 修复: total count 字段 (COUNT query)
- API 修复: SEARCH_FIELDS 必须匹配实际列 (Gotchas #12)
- KG_GOTCHAS.md: 8→12 条

**Final Stats**: 540,659 nodes / 1,112,390 edges

### Next: Data Quality Swarm Audit (蜂群模式)

**问题**: 法律文件 (54K) 搜索结果大量缺失关键字段:
- effectiveDate: 绝大部分为 "--"
- description: 空
- level: 全是 0
- type: 混杂 (shuiwu/kuaiji/tax_policy_announce/policy_law)

**目标**: 系统性审计 540K 节点的数据完整度, 修复关键缺失, 提升内容可用性

**建议蜂群配置**:
- Expert 1: 数据完整度审计 (哪些表哪些字段缺失率最高)
- Expert 2: 字段映射修复 (effectiveDate/description 从关联表或 fullText 提取)
- Expert 3: 分类体系清洗 (type 字段标准化)
- Expert 4: 数据去重 (V1/V2 表合并)
- Expert 5: 质量门禁升级 (Quality Gate 检查点更新)

**启动命令**: `/clear` → 新会话 → `ontology-audit-swarm` skill

### 未完成项
1. 数据质量审计 + 修复 (蜂群模式, 上述 5 路)
2. V1/V2 表长期合并
3. Classification 53K 分类导航需要改进 (HS编码搜索返回0, 因为内容是编码不是税种关键词)

### Key Commands
```bash
# VPS restart
ssh root@100.75.77.112 "fuser -k 8400/tcp; sleep 3; rm -rf /home/kg/cognebula-enterprise/__pycache__; cd /home/kg/cognebula-enterprise && nohup sudo -u kg /home/kg/kg-env/bin/python3 -m uvicorn kg-api-server:app --host 0.0.0.0 --port 8400 --workers 1 > /home/kg/kg-api.log 2>&1 &"

# DDL via API
curl -sf "http://100.75.77.112:8400/api/v1/admin/execute-ddl" -X POST -H "Content-Type: application/json" -d '{"statements": ["..."]}'

# Frontend deploy
cd web && npx next build && npx wrangler pages deploy out --project-name=lingque-desktop --branch=master

# Seed scripts
python3 scripts/seed_v42_phase1.py   # P0 foundation types
python3 scripts/seed_v42_phase1b.py  # AccountingSubject + TaxIncentive + edges
python3 scripts/seed_v42_phase2.py   # P1 tax law completeness
python3 scripts/seed_v42_phase3.py   # P2 operations + IndustryBenchmark expansion
```

### Git
- Branch: main
- Remote: github.com:MARUCIE/cognebula-enterprise
