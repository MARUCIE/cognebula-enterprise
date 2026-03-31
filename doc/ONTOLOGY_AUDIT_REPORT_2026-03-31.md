# CogNebula 本体审计报告 (Ontology Audit Report)

> 17-Expert 3-Round Swarm Audit | 2026-03-31
> Target: 540K nodes / 1,112,390 edges (VPS production)
> Method: ontology-audit-swarm (Round 1: Strategic × 6 + Round 2: Domain × 5 + Round 3: Business × 6)

---

## Executive Summary

**综合评分: 4.4/10**（5 路领域专家平均）

| 维度 | 评分 | 一句话 |
|------|------|--------|
| 税法结构 | 5/10 | 企业所得税/个人所得税 TaxItem 零覆盖 |
| 会计准则 | 4/10 | 分录模板 30 个远不够 60+；effectiveDate 0% |
| 实务代账 | 4/10 | 银行对账完全缺失；FilingFormField 仅覆盖 30% |
| KG 设计 | 5/10 | V1/V2 共存混乱；33 空表未分类处理 |
| 税务风险 | 4/10 | benchmark 0% = 风险引擎瘫痪 |
| 业务就绪 | NOT READY | 6 路业务专家 5/6 判定 NOT READY |

**根因**: 不是缺设计，而是**执行断裂** — Schema 完备但数据空洞；种子数据存在 JSON 文件中但从未导入图谱。

---

## 1. 双库差异 (Critical Finding)

| 环境 | 节点数 | 边数 | v4.2 表 | 种子数据 |
|------|--------|------|---------|---------|
| **VPS 生产** | 540,659 | 1,112,390 | 已建+已填 | 已导入 |
| **本地开发** | 100,768 | 7,255 | 33 空表 + 6 表不存在 | JSON 未导入 |

本地数据库严重落后于生产。开发调试在残缺数据上跑，无法验证真实业务链路。

---

## 2. 法律文件缺失字段 (Primary Audit Target)

### 2.1 LegalDocument (~2,000 nodes on VPS)

| 字段 | 填充率 | 问题 | 影响 |
|------|--------|------|------|
| effectiveDate | ~0% (全是 "--") | 法规时效判断失效 | 无法筛选现行有效法规 |
| description | ~0% (空) | RAG 检索只有标题 | LLM 只能猜测内容 |
| level | ~0% (全是 0) | 效力层级不可用 | 无法判断法律>法规>规章优先级 |
| type | 混杂 | shuiwu/kuaiji/tax_policy_announce/policy_law 混用 | 无法按类型分类筛选 |
| status | 未审计 | 可能同样缺失 | 无法判断"已失效/已修订" |

### 2.2 LegalClause (~50,000 nodes on VPS)

| 字段 | 填充率 | 问题 |
|------|--------|------|
| content | ~46% (抽样 DocumentSection) | 超半数条款只有标题没有正文 |
| clauseLevel | 未审计 | 章/节/条/款/项层级可能缺失 |
| keywords | 未审计 | 关键词提取可能未执行 |

### 2.3 修复方案

```
P0-FIX-1: effectiveDate 批量提取
  方法: LLM (Gemini Flash) 从 fullText 正则 + NLP 提取 "自XXXX年X月X日起施行"
  成本: ~$2-5 (2K docs × ~500 tokens)
  工时: 4-8h (含脚本开发+验证)

P0-FIX-2: level 从 type 字段映射
  规则: policy_law → 1, admin_regulation → 2, shuiwu/kuaiji → 3, tax_policy_announce → 4
  工时: 1h

P0-FIX-3: type 字段标准化
  目标枚举: law | admin_regulation | department_rule | normative_document | judicial_interpretation | accounting_standard
  方法: CASE WHEN 映射
  工时: 1h

P1-FIX-4: content 回填
  方法: 从原始爬取数据/PDF 重新提取正文
  工时: 取决于原始数据可用性
```

---

## 3. 节点数据完整度矩阵

### 3.1 已有数据表 — 字段缺失

| 表 | 节点数 | 字段 | 填充率 | 修复方法 | 优先级 |
|----|--------|------|--------|---------|--------|
| DocumentSection | 42,115 | content | 46.2% | 从源 PDF 重提取 | P1 |
| CPAKnowledge | 7,371 | content | 44.0% | heading 节点从讲义 JSON 回填 | P1 |
| MindmapNode | 28,526 | parent_text | 0% | 从原始思维导图重建层级 | P2 |
| IndustryRiskProfile | 720 | benchmark | 0% | 从 extracted JSON 映射数值 | P0 |
| AccountingStandard | 43 | effectiveDate | 0% | 手工填充 CAS 1-42 日期 | P0 |
| AccountingStandard | 43 | differenceFromIfrs | 0% | AI 生成 + 人工校验 | P1 |
| TaxType | 19 | code | 0% | 手工填充金税代码 | P0 |
| TaxClassificationCode | 4,205 | description | 71.3% | AI 补充缺失 29% | P2 |

### 3.2 种子数据未导入 (本地环境)

| 种子文件 | 条数 | 目标表 | 状态 |
|----------|------|--------|------|
| seed_social_insurance.json | 138 | SocialInsuranceRule | JSON 就绪，表不存在 |
| seed_industry_benchmarks.json | 45 | IndustryBenchmark | JSON 就绪，表不存在 |
| seed_tax_accounting_gap.json | 50 | TaxAccountingGap | JSON 就绪，未验证 |
| seed_invoice_rules.json | 40 | InvoiceRule | JSON 就绪，未验证 |
| CPA 真题 JSON (28 份) | ~2,000+ | CPAKnowledge | extracted/ 目录 |

### 3.3 空表清单 (33 tables, 0 nodes)

**建议 DROP (V1 遗产，已被 V2 替代):**
- Document, LawOrRegulation, Section (→ LegalDocument/LegalClause)
- ArrowFunction, Class, Community, External, File, Folder, Function, Interface, Method, Module, Topic (代码分析残留)

**建议保留 + 排期填数据:**
- LifecycleStage, LifecycleActivity (企业生命周期)
- FilingForm, FilingObligation (申报表)
- TaxIncentive, TaxPlanningStrategy (税收优惠/筹划)
- Penalty, RiskIndicator, AuditTrigger (风险/稽查)
- ComplianceChecklist, FinancialStatement (合规/报表)
- PersonalIncomeType, SpecialZone, TaxAuthority (分类)

**建议评估后决定:**
- AdministrativeRegion (与 Region 重复?)
- FTIndustry (与 Industry 重复?)
- IndustryGuide (与 IndustryKnowledge 重复?)
- JournalTemplate (与 v4.2 JournalEntryTemplate 重复?)
- TaxRateVersion (与 TaxRateDetail 重复?)

---

## 4. 蜂群共识行动计划

### Phase 0: 立即修复 (Day 1, ~4h)

| # | 动作 | 杠杆率 | 工时 |
|---|------|--------|------|
| 1 | `TaxType.code` 手工填充 19 条 | 极高 (辐射全库查询) | 10min |
| 2 | `AccountingStandard.effectiveDate` 填充 43 条 | 高 | 30min |
| 3 | 导入 `seed_social_insurance.json` 138 条 | 高 (代账月度刚需) | 2h |
| 4 | 导入 `seed_industry_benchmarks.json` 45 条 | 高 (行业对标) | 1h |

### Phase 1: 核心链路修复 (Day 2-5, ~20h)

| # | 动作 | 解锁场景 | 工时 |
|---|------|---------|------|
| 5 | `LegalDocument.effectiveDate` LLM 批量提取 | 法规时效判断 | 4-8h |
| 6 | `LegalDocument.level` 映射修复 | 效力层级排序 | 1h |
| 7 | `HAS_ENTRY_TEMPLATE` 边补建 30+ 条 | 业务→记账链路 | 1h |
| 8 | `IndustryRiskProfile.benchmark` 回填 | 风险预警 | 2h |
| 9 | 填充 `TaxIncentive` 50 条核心优惠 | 税收优惠匹配 | 4h |
| 10 | 补充企业所得税/个人所得税 `TaxItem` ~60 条 | 两大核心税种查询 | 3.5d |

### Phase 2: 业务就绪 (Week 2-3)

| # | 动作 | 工时 |
|---|------|------|
| 11 | `JournalEntryTemplate` 扩充至 60+ | 3d |
| 12 | `FilingFormField` 扩充至 150+ | 3d |
| 13 | `LifecycleStage` + `LifecycleActivity` 填充 | 1d |
| 14 | V1/V2 表清理 (合并 + DROP 废表) | 2d |
| 15 | API 白名单改动态发现 | 4-8h |

### Phase 3: 差异化能力 (Week 3-4)

| # | 动作 | 工时 |
|---|------|------|
| 16 | `TaxTreaty` 20 个主要协定国 | 1d |
| 17 | 发票异常 + 行为异常 `RiskIndicator` ~20 项 | 2d |
| 18 | `FinancialIndicator` 杜邦分析树 17 条 | 0.5d |
| 19 | CPA 真题导入 + 经济法/公司战略知识点 | 2d |
| 20 | 本地←→VPS 数据同步机制 | 1d |

---

## 5. 关键指标 (KPI)

审计后应持续监控:

| 指标 | 当前值 | 目标 (Phase 1 后) | 目标 (Phase 3 后) |
|------|--------|------------------|------------------|
| LegalDocument effectiveDate 填充率 | ~0% | >80% | >95% |
| LegalDocument level 填充率 | ~0% | >95% | >99% |
| TaxType.code 填充率 | 0% | 100% | 100% |
| IndustryRiskProfile.benchmark 填充率 | 0% | >80% | >95% |
| JournalEntryTemplate 数量 | 30 | 60+ | 100+ |
| FilingFormField 数量 | 45 | 150+ | 300+ |
| TaxItem 覆盖税种数 | 3/19 | 5/19 | 15/19 |
| 空 node 表数 | 33 | <20 | <10 |
| 业务就绪评估 | NOT READY | PARTIAL | READY |

---

## 6. Gotchas & Lessons

1. **本地≠生产**: 开发必须在与生产同构的数据上进行，否则所有测试都是自欺
2. **Schema ≠ 数据**: 91 张表 / 115 张边表的设计完备度不代表数据完备度
3. **种子数据必须自动化导入**: JSON 文件不等于图谱数据，需要 CI/CD 管线
4. **时效性是财税命脉**: effectiveDate/expiryDate/status 必须作为 Quality Gate 强制项
5. **V1/V2 共存是定时炸弹**: 每个查询都要决定查哪个表，等于给每个调用者加认知负担

---

Maurice | maurice_wen@proton.me
CogNebula v4.2 Ontology Audit | 2026-03-31
