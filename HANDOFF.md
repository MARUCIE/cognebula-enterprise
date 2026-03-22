# HANDOFF.md — CogNebula M3 Session 3 状态交接

> Updated: 2026-03-22 23:00 CST

## 图谱当前状态

| 指标 | 值 | 目标 |
|------|-----|------|
| Nodes | 505,433 | 1,000,000 |
| Edges | 1,103,590 | 6,000,000 |
| Density | 2.183 | 6.0 |
| Quality Score | 100 | 100 |
| KU content ≥100c | 80% | 95%+ |
| LR fullText ≥100c | 100% | 100% |

## 后台长跑任务 (kg-node VPS)

| 任务 | 日志 | 进度 | 预计完成 |
|------|------|------|---------|
| lr_cleanup LLM 回填 | `/tmp/backfill_lr_cleanup.log` | ~2K/18,893 (10%) | +5h |
| Baike 全文爬取 | `/tmp/baike_recrawl.log` | page ~60 | +1.5h |
| Matrix 扩容 114K | `/tmp/matrix_fast_expansion.log` | 200/114,000 | +63h |
| CICPA 回填 | `data/backfill/cicpa_content.jsonl` | 93/102 DONE | 待入库 |

**NOTE**: Matrix 扩容占 DB lock，API inactive。回填完成后需要等 Matrix 暂停或完成才能入库。

## 待入库数据 (已生成，需等 DB lock 释放)

| 数据 | 文件 | 条数 |
|------|------|------|
| lr_cleanup 内容 | `data/backfill/lr_cleanup_content.jsonl` | ~18K (生成中) |
| CICPA 审计准则 | `data/backfill/cicpa_content.jsonl` | 93 条 |
| ASBE 会计准则 (LLM) | `data/asbe/asbe_llm_generated.json` | 43 条 (临时，需官方替换) |
| Baike 全文 | `data/recrawl/baike_fulltext.json` | ~3K (爬取中) |

入库脚本:
- `backfill_lr_cleanup.py --ingest` (回填内容写入 KU)
- `recrawl_fulltext.py --source baike` (Baike 入库)
- ASBE/CICPA 需要新的入库脚本

## 下个 Session 优先事项

### P0: 官方信源浏览器爬取 (用户明确要求)

1. **kjs.mof.gov.cn (ASBE 42 条)** — 被 rate limit，等 1-2h 解除后用 agent-browser-session 重爬
   - `eval "document.body.innerText"` 确认可抓全文
   - 第一次 Playwright 拿到 14/33 全文 (但结果被覆盖丢失)
   - 策略: `domcontentloaded` + eval 提取 + 每页爬完 close tab

2. **chinatax.gov.cn (57K 政策全文)** — 3 层反爬 (JS Cookie + onMouseMove + browser detect)
   - 需要 agent-browser-session (Patchright 反检测) + Browser Proxy 模式
   - 已有 title-only 数据在 KuzuDB，需补全文

3. **flk.npc.gov.cn (17K 法规全文)** — Vue SPA，需要 Playwright CDP 拦截
   - law-datasets 已覆盖 509 条核心税法，剩余 ~16K 非税法规优先级低

### P1: 入库 + 二次质量审计

4. 等 Matrix 扩容暂停时插入: lr_cleanup 回填 + CICPA + Baike + ASBE
5. 第二轮 boost_edge_density (回填后 KU 有内容了，关键词匹配能建更多边)
6. 质量审计: KU 覆盖率 80%→?%, 孤儿率, 密度变化

### P2: 边密度攻坚 (Meadows Edge-First)

7. 密度 2.18 → 3.0+: 需要 ~400K 新边
8. SUPERSEDES 批量发现 (法规时间链)
9. APPLIES_TO_ENTITY 扩展 (17 纳税主体 × 法规适用性)

## 关键决策记录

- STARD 55K → 税过滤 5,885: 防止密度稀释
- law-datasets 标题精确匹配 → 509 条核心税法
- lr_cleanup 回填而非删除: 98.8% 已有边，标题有价值
- QA-v3 短答案是正常模式，不修复
- MOF 系网站 VPS 全线 502，必须用本地浏览器
- 用户要求: 官方信源优先，LLM 生成只作 fallback

## Git 状态

- Branch: master
- Latest: 92ef293 (pushed to MARUCIE/cognebula-enterprise)
- 本地未提交: crawl_asbe_browser.py, crawl_asbe_abs_v2.py, crawl_asbe_abs.sh, crawl_asbe.py (爬虫脚本)
