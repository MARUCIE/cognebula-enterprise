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

### 8. 维基百科评估
- 中文维基财税词条 ~2000-5000 条
- 信息密度 5-10% (vs 税务总局 80%+)
- 结论: P3 低优先, 不推荐 M3 阶段引入
