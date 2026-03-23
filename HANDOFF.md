# HANDOFF.md — CogNebula M3 Session 4→5 状态交接

> Updated: 2026-03-23 16:15 CST

## Session 4 完成: KU Content 恢复

### 问题诊断
v1 restore_ku_content.py 有致命 bug: `set_content()` 无条件写入，导致好内容被空/短内容覆盖。
覆盖率从 10.3% 降到 2.2%。

### 修复动作
1. **restore_ku_content_v2.py** — 安全恢复，仅在新内容 ≥100c 且比现有更长时才写入
   - lr_cleanup JSONL: +18,449 | baike: +2,767 | NDRC: +593 | CICPA: +91 | compliance_matrix: +17,638
   - 结果: 2.2% → 5.3%
2. **restore_ku_from_csv.py** — 从原始 CSV 源文件补充 JSONL 未覆盖的记录
   - lr_cleanup CSV: +19,927 (CSV 有 32K 条，JSONL 仅 18K)
   - 结果: 5.3% → 10.9% (15,717/143,893)

### 关键教训
- KuzuDB SET 操作必须先查现有值再决定是否写入（防覆盖）
- CSV 源文件比 LLM 回填 JSONL 覆盖面更广（32K vs 18K）

## PREVIOUS: WAL 删除导致数据回退

Session 3 末尾发生了 KuzuDB WAL OOM 事件：
1. lr_cleanup 回填 18,713 条 SET 操作导致 WAL 过大 → DB 无法打开
2. 删除 WAL 恢复 DB → **发现之前 Session 1-3 的所有写入都未 CHECKPOINT**
3. 删除 WAL = 回退到最后一个 checkpoint 状态 → **大量 KU content 丢失**

**影响**: gemini-qa-v3(23K), mindmap(28K), flk_npc(22K) 等信源的 content 字段被清空。
**恢复方案**: `scripts/restore_ku_content.py` 已在运行（`/tmp/restore_ku_content.log`）。
- lr_cleanup: 18,713 条 DONE (14,999 updated)
- compliance_matrix: 20K+ 条 IN PROGRESS
- baike/ndrc/mindmap: 待续
- SafeDB 模式: CHECKPOINT/50 + RECONNECT/10K 防 OOM

**教训**: KuzuDB 8GB RAM VPS 上的关键规则：
- 每 50 条写入后必须 CHECKPOINT
- 单条 content 截断到 2000c（减少 buffer pressure）
- 长时间写入进程每 14,000 条需要重启 DB 连接释放 buffer pool

## 图谱当前状态 (Session 4 完成)

| 指标 | 值 | 目标 | Session 4 变化 |
|------|-----|------|---------------|
| Nodes | 505,674 | 1,000,000 | +4,859 (12366 FAQ) |
| Edges | 1,076,926 | 6,000,000 | +5,976 (引用+关联+税种) |
| Density | 2.130 | 6.0 | - |
| KU content ≥100c | **11.9%** (17,671/148,752) | 50%+ | 从 2.2% 恢复 (稳定基线) |
| Title Coverage | **99.5%** | 99%+ | 从 96.3% 修复 |
| Quality Score | 100 | 100 | PASS |
| API | healthy | - | uvicorn :8400 |

### KuzuDB 8GB VPS 已知问题
- **reconnect 导致数据丢失**: SafeDB._reconnect() (del db → new Database) 会使之前 CHECKPOINT 的部分数据丢失
- 实测: CSV CHECKPOINT=13.6% → JSONL reconnect 后降到 8.4%
- **根因**: 8GB 内存压力下 buffer pool 释放与 WAL 持久化竞争
- **规避**: 避免在同一脚本中多次 reconnect，改用独立脚本分批处理
- **长期方案**: 升级到 16GB+ 实例或迁移到 PostgreSQL

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

### P0: KU Content 覆盖率继续提升 (11.9% → 20%+)

已恢复的稳定基线: 17,671/148,752 KU (11.9%)。按源分析剩余缺口：

| 来源 | 缺口 | 可恢复性 | 策略 |
|------|------|---------|------|
| mindmap (28.5K) | 28,522 | 低 | 思维导图节点本身就是短标签，接受 |
| lr_cleanup (23.9K) | ~14K | 受限 | CSV/JSONL 已最大化利用，reconnect 丢数据 |
| gemini-qa-v3 (23.5K) | 23,546 | 中 | 有 Q 无 A，需 LLM 生成答案或从 clause_qa 匹配 |
| flk_npc (22.4K) | 22,447 | 高 | 法规全文可从 flk.npc.gov.cn 爬取 |
| compliance_matrix (13.8K) | ~7K | 低 | 分析文本 <100c，需 LLM 扩写 |
| stard_statute (5.9K) | 5,885 | 中 | 需从 STARD 源恢复全文 |
| lecture/CPA (~6K) | ~6K | 低 | 讲义切片，内容本身就是要点 |

**高性价比方向**: flk_npc 浏览器爬取 (22K法规全文) > LLM 为 QA 生成答案 (23K)

### P1: 结构质量修复

4. **RegulationClause 标题覆盖率 47%** — 15,786 条缺标题，需要从 fullText 提取
5. **边密度攻坚** — 2.14 → 3.0+ (需 ~400K 新边)
6. **boost_edge_density 第二轮** — KU 有 content 后关键词匹配能建更多边

### P2: 扩容

7. Matrix 扩容重试 (之前 DB lock 失败)
8. SUPERSEDES 批量发现 (法规时间链)
9. APPLIES_TO_ENTITY 扩展

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
