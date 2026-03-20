# M3 Findings

## 蜂群审计结果 (2026-03-20)

### 1. 爬虫深度危机 (Explorer Agent)
- 4/22 (18%) 全文抓取: 12366, tax_cases, baike_kuaiji, hs_codes
- 10/22 (45%) 仅标题: chinaacc, chinatax_api, provincial, npc, casc, ctax, customs, stats, csrc, chinatax
- 3/22 (14%) 失效: cf_browser, chinatax(SPA), mof
- 根因: daily_pipeline.sh 未传 --fetch-content
- 修复: 已部署 content depth flags + per-crawler timeouts

### 2. 遗漏信源 (Research Analyst)
18 个高价值源未覆盖:
- P0: flk.npc.gov.cn (17K laws), cicpa.org.cn, cctaa.cn
- P1: aifa.org.cn (ASBE), pbc.gov.cn/data, chinamoney.com.cn, epub.cnipa.gov.cn
- P2: splcgk.court.gov.cn (100K cases), qcc.com, pkulaw.com

### 3. 系统动力学 (Meadows)
4 反馈回路:
- R1 深度增强 (正向, 未激活): 深度爬取→更好QA→更多边→更高密度
- R2 孤儿死亡螺旋 (负向): 快速注入→边跟不上→孤儿增加
- B1 质量门平衡: 节点增加→维护困难→门控触发→减速
- B2 密度稀释: 节点增加无边→密度下降

核心数学:
- 6.0 density @ 1M nodes = 6M edges
- 当前 860K edges, 缺口 5.14M
- 每个新节点需携带 8.7 条边
- L3 必须从"造节点"切换为"造边"

### 4. chinatax_api 深度问题
- 57K 政策文档只取了 search snippet (3000 chars)
- 未跟进 URL 获取全文
- 修复方案: 增加 detail fetch 步骤 (每篇 3-5s, 总计 ~48h)

### 5. INTERPRETS 分析
- 82% INTERPRETS 率合理 (76% 是思维导图节点)
- 扩展关键词仅额外捕获 0.7%
- 结论: 不需要 LLM 精细化

### 7. 前端升级调研 (Research Analyst)
推荐: **Cytoscape.js + fcose** (Force-directed Clustered Spring Embedder)
- 原生 compound nodes 支持 L1/L2/L3 分组 (vis.js 不支持)
- fcose 专为层级聚类设计, 比 vis.js 布局质量高 20-30%
- 可增量迁移 (vis.js 和 Cytoscape.js 共存过渡)
- JSON Canvas 导出需 2-3 周 adapter
- 5K 节点 60fps (Canvas 渲染), 够用; >10K 再升 WebGL
- 5-6 周分阶段: POC(W1-2) → 数据适配(W3-4) → Canvas导出(W5-6)
- 社区验证: 生物信息学 KG (BioGRID, cBioPortal) 同等规模

### 9. 本体完整性审计 (Hickey, 2026-03-20)

**Verdict: COMPLECTED — 需要外科手术级修复**

#### 纠缠问题 (Complections)
- C1: Schema 自相矛盾 — edge 引用 7 个不存在的节点 (V2 后缀幽灵)
- C2: Classification 把 4 种分类体系揉成一张表 (HS码/行业/税收编码/企业类型)
- C3: KnowledgeUnit 是万能垃圾桶 (FAQ/案例/考点/指南/思维导图混一表)
- C4: TaxType 同时承担字典和业务枢纽 (19 节点 15 种边)

#### 数据平衡异常
- INTERPRETS 45% = RAG chunk 伪装成图关系, 删掉后密度从 2.07 降到 1.14
- ISSUED_BY 128K (文档 55K, 平均 2.3 个机构/文档, 可能重复)
- FILING_FOR_TAX=3, RULE_FOR_TAX=5, Penalty=8 — L3 几乎为空
- AuditTrigger=463 与 RiskIndicator=463 完全一致 — 疑似 1:1 copy

#### 缺失节点类型
- JournalEntry (会计分录) — 业务→分录→科目核心链路缺失
- TaxPeriod/Deadline (纳税期限) — 超越 deadlineDay 字段
- CaseDecision (案例裁决) — 混在 KnowledgeUnit 里
- Invoice/Voucher (发票凭证) — 中国税务核心场景完全缺失
- TaxBracket (税率档次) — 累进税率需要独立建模

#### 缺失边类型
- GENERATES_ENTRY: BusinessActivity → JournalEntry
- REQUIRES_INVOICE: BusinessActivity → Invoice
- KU_ABOUT_ACTIVITY: KnowledgeUnit → BusinessActivity (打破法规层隔离)
- INCENTIVE_FOR_ENTITY: TaxIncentive → TaxEntity
- APPLIES_TO_ACTIVITY: TaxRate → BusinessActivity
- CLAUSE_DEFINES_RATE: LegalClause → TaxRate (反向链接)

#### 结构空洞 (6 个)
- BusinessActivity ↔ AccountingSubject (无直连, 必须绕 TaxType)
- TaxIncentive ↔ TaxEntity (谁能享受什么优惠?)
- ComplianceRule ↔ LegalClause (合规规则的法律依据?)
- RiskIndicator ↔ BusinessActivity (什么业务触发什么风险?)
- FilingForm ↔ LegalClause (申报表的法律依据?)
- KnowledgeUnit ↔ BusinessActivity (知识和业务割裂)

#### 整改优先级
- P0: Schema 自洽修复 (幽灵节点 + V2 后缀对齐)
- P1: 拆 Classification → 4 独立分类表
- P1: 补 JournalEntry + Invoice + 对应边
- P2: KU 直连 BusinessActivity/TaxRate (不强制绕法规层)
- P2: L3 数据充实 (ComplianceRule 84→800+, Penalty 8→100+)
- P3: DROP 全部 26 条 legacy edge

### 10. 数据质量审计 (Explorer, 2026-03-20)
- 质量评分: 62/100
- 孤儿节点 80K: LawOrRegulation 86%孤儿, Classification 88%孤儿, AccountingSubject 92.5%孤儿
- KU 内容危机: 33,293/37,067 (89.8%) content < 20 chars
- 重复节点 10K: LR 5,739 + Classification 4,269 + TaxRate 3,000
- 元数据缺失: LR 55.1% 无 effectiveDate, TaxRate 100% 无 effectiveDate
- Tax Applicability 严重不足: 仅 24K 边 (应 > 50K)

### 11. 图结构系统分析 (Meadows, 2026-03-20)
- Classification 31K 是结构孤岛 (只有 CHILD_OF 自指, 无出边到其他类型)
- INTERPRETS 55% 是单一栽培风险 (类比爱尔兰大饥荒)
- L3 合规层 555 节点 = 结构性缺失, Penalty 仅 8 个 = B1 平衡回路断开
- R2 孤儿死亡螺旋当前主导, R1 知识飞轮未激活
- 下 1000 条边优先级: Classification→KU(300) > LegalClause→ComplianceRule(200) > CR→Penalty(150) > TaxType→CR(200) > AuditTrigger→RI(150)
- 预测: 维持现状 → 6 个月后密度 1.8, 合规价值趋零; 暂停造节点专注造边 → 3 个月后密度 4.0+

### 12. LR 孤儿根因 (2026-03-20)
- 49,541 个 LawOrRegulation 孤儿 (86%)
- IssuingBody top 5 不是政府机构而是数据源 (doc-tax-pdf, 12366, chinaacc)
- 孤儿 LR 标题不含"国家税务总局"等关键词 — 不是真正的法规文档
- 根因: LawOrRegulation 表被当作万能垃圾桶 (类似 Hickey C3 的 KnowledgeUnit 问题)
- 修复: 需要数据分类清洗 (将非法规数据迁移到正确的表 — KnowledgeUnit/CPAKnowledge 等)
- 预计影响: 清洗后 LR 从 57K 降到 ~8K (真正的法规)，孤儿率大幅下降

### 13. 维基百科评估
- 中文维基财税词条 ~2000-5000 条
- 信息密度 5-10% (vs 税务总局 80%+)
- 结论: P3 低优先, 不推荐 M3 阶段引入
