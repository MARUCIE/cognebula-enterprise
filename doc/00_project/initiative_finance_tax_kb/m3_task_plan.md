# M3 执行计划: 500K → 1M 节点 (Edge-First)

## Goal
中文财税领域首个百万节点知识图谱。基于蜂群审计的 Edge-First 策略重设计。

**核心约束 (Meadows)**:
- 密度 6.0 = 每个节点平均 6 条边 = 1M 节点需要 6M 边
- 当前 860K 边，缺口 5.14M
- 每个新节点必须携带 ≥ 8.7 条边，否则密度下降
- **L3 = 边引擎 (edge engine)，不是节点引擎**

## Current Phase
Phase 2 A+B 并行 — 爬取扩源 + 合规矩阵生成 (2026-03-22 session 2)

### Session 2 进展 (2026-03-22)
1. **Swarm fulltext backfill 修复+运行** — LegalClause schema bug 修复 (regulationId→documentId, articleNumber→clauseNumber), +298 KU content recovered
2. **Fetcher 研究完成** — mof/ndrc/baike 三个 fetcher 都有 fetch_detail 能力，但生产用 --no-detail 跑（title-only），且内容截断到 3000 chars
3. **Fetcher 升级** — 去掉 3000 char 截断 (→50K)，添加 fleet-page-fetch 浏览器兜底，添加 error page 检测
4. **MOF 子域名 502** — gss/jrs/nys 等子域名全部 502（CDN/WAF 层面），即使 VPS 浏览器也无法访问。MOF 只能获取 listing 信息
5. **NDRC 全文爬取成功** — httpx 直接成功，2000-4000 chars 级别全文，正在入库
6. **Baike 全文爬取启动** — 5 分类 5000 条目标，3-5s polite delay，后台运行中
7. **Phase B 合规矩阵框架完成** — generate_compliance_matrix.py, 24×19×20×5=45,600 组合, Gemini 2.5 Flash Lite
8. **合规矩阵质量验证 PASS** — 3/3 测试节点质量极好 (1500-2200 chars, 引用具体法规条款), 500 条试跑启动

### 下个 Session 继续点
1. **Baike 完成后处理** — Baike 进程 PID 122095 还在跑(4h+)，完成后用 `ingest_from_json.py` 从 JSON 入库 (~5K nodes)
2. **REFERENCES 边创建** — `edge_references.py` 已就绪，等 DB 解锁后运行（KU《法规名》→ LR 匹配）
3. **合规矩阵继续** — 已完成 2,493/10,000，需要重新启动补完剩余 7,500 条
4. **合规矩阵扩容** — 10K 验证后扩到 45K (全24×19×20×5组合)，然后扩 Scenario 维度到 20+
5. **边密度大幅提升** — 当前 2.16，目标 5.0+。已有 KU_ABOUT_TAX Cypher 匹配(+8,348)，还需 SUPERSEDES/CONFLICTS
6. **API 重启** — Baike 完成后 `sudo systemctl start kg-api`
7. **质量审核** — 法律数据集 22K 条质量待验证

## Phases

### Phase 1: L1 深化 — 现有数据深挖 (W1-7, +150K nodes, +450K edges)
- [x] QA 生成管线 (generate_lr_qa.py) — 42K 文章 → ~120K QA 对
- [x] QA 管线测试: 5 篇 → 14 QA (2.8/篇), gemini-2.5-flash-lite
- [x] M3 orchestrator + cron (02:00 UTC daily)
- [x] Edge Engine (generate_edges_ai.py) — AI 发现 SUPERSEDES/cross-ref
- [x] Daily pipeline depth fix (--fetch-content for chinaacc等)
- [x] chinatax_api detail fetch — 反爬失败, 改 LLM 生成 +1,958 LR content
- [x] LegalClause 二级拆分 (条→款→项) — +12,925 sub-clause nodes + 10,460 PART_OF edges
- [x] Temporal version chain — +317 SUPERSEDES edges (5-year PIT chain)
- [x] Edge enrichment — +7,716 cross-ref edges (CLASSIFIED_UNDER_TAX + KU_ABOUT_TAX)
- [x] KU content backfill — 44% → 66% (3 rounds: +9,838 + 998 + running)
- [x] QA generation — +11,894 QA nodes + 6,415 edges (50 batches)
- [ ] Mini Gate @ 500K: orphan < 5% (tracked PASS), density ≥ 3.0 (tracked 3.53 PASS)

### Phase 2: L2 扩源 — 新信源 + 入图协议 (W8-12, +200K nodes, +600K edges)
- [ ] 入图协议 (Admission Protocol): staging → NER → min 3 edges → main graph
- [ ] Batch density gate: 边/节点比 < 3.0 的批次退回 staging
- [ ] 新爬虫 P0: flk.npc.gov.cn (国家法律法规数据库, 17K docs)
- [x] 新爬虫 P0: cicpa.org.cn — 71 records crawled, 69 ingested as KU
- [x] 新爬虫 P0: cctaa.cn — 749 records crawled, 691 ingested as KU
- [ ] 新爬虫 P1: aifa.org.cn (会计准则ASBE, 60 准则)
- [ ] 新爬虫 P1: pbc.gov.cn/data (央行金融数据)
- [ ] 新爬虫 P1: epub.cnipa.gov.cn (专利/高新R&D优惠)
- [ ] 裁判文书评估: splcgk.court.gov.cn ROI 分析 (100K cases, DES3加密)
- [ ] Mini Gate @ 700K: orphan < 3.5%, density ≥ 4.5, P@5 ≥ 87%

### Phase 3: L3 合成 — Gemini 边引擎 (W13-15, +50K nodes, +2M edges)
- [ ] L3 职能切换: 从"造节点"→"造边" (Meadows insight)
- [ ] SUPERSEDES 批量发现 (法规时间链, 14 税种 × 100 文档对)
- [ ] CONFLICTS_WITH 推理 (相互矛盾的条款对)
- [ ] APPLIES_TO_ENTITY 扩展 (17 纳税主体 × 法规适用性)
- [ ] APPLIES_IN_REGION 扩展 (31 地区 × 法规地域适用性)
- [ ] Industry×Tax×Lifecycle 三维矩阵 (+40K 交叉节点)
- [ ] 合规检查清单生成 (+25K 清单节点)
- [ ] Mini Gate @ 850K: orphan < 3%, density ≥ 5.0, P@5 ≥ 88%

### Phase 4: L4 收尾 — 专家贡献 + Final Gate (W16)
- [ ] Know-Arc 审核通过三元组注入主图 (inject_know_arc.py)
- [ ] 专家手工校验 Top 100 高流量节点
- [ ] Final Gate @ 1M: orphan < 3%, density ≥ 6.0, P@5 ≥ 90%
- [ ] 架构文档更新 (PDCA 4-doc sync)
- [ ] 竞争定位声明: "中文财税领域首个百万节点、600万边知识图谱"

### Phase 5: 交付
- [ ] M3 完成报告 (Economist Editorial HTML)
- [ ] GitHub release tag (v3.1-m3)
- [ ] 更新 memory + SKILL-MANIFEST
- [ ] Telegram 通知 + 截图

## Key Questions
1. chinatax_api detail fetch 是否会触发反爬？(57K 全文请求)
2. 裁判文书网 DES3 加密是否有社区解决方案？(GitHub Leon406/wenshukt)
3. KuzuDB 在 1M 节点时性能如何？(单写锁, 归档软件)
4. Edge Engine 的 Gemini 成本控制 (每天 ~$2, 16 周 ~$224)
5. flk.npc.gov.cn SPA 重构后如何获取数据？(需要 Playwright CDP 拦截实际 XHR)

## Decisions Made
0. **flk.npc.gov.cn SPA 阻塞** (2026-03-22): 2025年重构为 Vue SPA，旧 REST API 不再工作。需要 Playwright CDP 拦截方案或用 twang2218/law-datasets GitHub 数据集替代
1. **Edge-First 战略** (Meadows): L3 = 边引擎，不是节点引擎
2. **深度优先于广度**: L1 派生节点自带 3-5 边，L2 新源需要额外建边管线
3. **入图协议**: staging → NER → min 3 edges → main graph (锁死 R2 死亡螺旋)
4. **批次密度监控**: 每日 cron 输出边/节点比，< 3.0 触发告警
5. **gemini-2.5-flash-lite**: QA 生成最佳模型 (无 thinking tokens 开销)
6. **M3 cron 02:00 UTC**: 不影响白天 API 可用性
7. **python3 -u**: orchestrator 必须 unbuffered 输出 (管道 buffer 导致无日志)
8. **pgrep 等待**: systemctl stop 后 pgrep 轮询确认进程退出 (sleep 2 不够)

## Errors Encountered
1. gemini-2.5-flash-preview-05-20 404 — 模型 ID 过时，改用 gemini-2.5-flash-lite
2. max_output_tokens=1000 截断 JSON — 2.5 Flash thinking 消耗 token，改用 lite
3. KuzuDB lock file 残留 — pkill python3 清理后恢复
4. SCP 到错误路径 — uvicorn 从 /home/kg/ 加载，不是 /home/kg/cognebula-enterprise/
5. 9.9GB doc-tax PDF 在 git 中 — soft reset + .gitignore 清理

## Notes
- M3 orchestrator: 5 步 (QA gen → Edge Engine → API restart → density check → daily crawl)
- 蜂群审计: 3 agent 并行 (Research Analyst + Explorer + Meadows)
- 22 爬虫中 4 个 SOTA, 10 个标题级, 3 个失效
- 18 个遗漏信源, 8 个 P0/P1
- Know-Arc 已整合到 /api/v1/ka/* (23 endpoints, same-origin)
