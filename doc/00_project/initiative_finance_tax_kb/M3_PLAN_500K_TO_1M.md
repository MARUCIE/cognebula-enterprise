# CogNebula M3: 500K → 1M Node Plan

> 中文财税领域首个百万节点知识图谱 | 2026-03-19 drafted

## 0. Executive Summary

M3 目标是在 M2 (500K) 基础上翻倍到 **1M 节点**。**数据增长优先，架构迁移延后**。
KuzuDB 虽已被 Apple 收购归档，但在 1M 规模内仍可用（单写锁通过 stop/start API 解决）。

预计耗时 **16 周**（4 个 Phase），预算 **~$350**（主要是 Gemini API）。

| Metric | M2 End | M3 Target | Delta |
|--------|--------|-----------|-------|
| Nodes | 500K | 1,000,000 | +500K |
| Edges | ~150K | 3,000,000+ | +2.85M |
| Orphan rate | <5% | <3% | -2pp |
| Edge density | ≥3.0 | ≥6.0 | 2x |
| P@5 precision | ≥85% | ≥90% | +5pp |
| Query latency p99 | ~200ms | <100ms | 2x faster |

---

## 1. KuzuDB → 新引擎迁移（Phase 0, W1-3）

### 1.1 为什么必须迁移

KuzuDB 于 2025-10 被 Apple 收购，开源项目已归档（GitHub read-only）。v0.11.3 是最终版本。
核心风险：
- 无安全更新
- 无 Python 版本兼容性修复
- 单写锁（single-writer）无法支撑多 Agent 并发写入

### 1.2 候选方案对比

| 维度 | Vela-kuzu Fork | FalkorDB | ArcadeDB |
|------|---------------|----------|----------|
| 迁移成本 | **1 天** (drop-in) | 5-7 天 | 10-14 天 |
| 并发写入 | YES (fork 特性) | 单写锁 | YES (MVCC) |
| 嵌入式 | YES | 需 Redis | YES |
| Cypher | 100% 兼容 | ~90% openCypher | 97.8% TCK |
| 向量搜索 | 需 LanceDB | **内置** | **内置** |
| Python SDK | pip install kuzu | falkordb-py | arcadedb-embedded |
| License | MIT (archived) | Source-available | Apache 2.0 |
| 1M 节点验证 | 100K (fork) | 生产级 | 2M+/sec ingest |
| 社区活跃度 | 低 (Vela 单家) | 高 | 中 |
| DBA 需求 | 无 | 无 (嵌入模式) | 无 |

### 1.3 推荐路径：双轨验证

| 周 | 主轨 | 备轨 |
|----|------|------|
| W1 | Vela-kuzu fork 安装 + M2 数据导入 + 并发写入压测 | FalkorDB POC: CSV 导出 + Rust Loader |
| W2 | 压测结果评估 → GO/NO-GO | FalkorDB 向量搜索验证 (替代 LanceDB) |
| W3 | 胜出方案部署到 VPS + 管线迁移 | — |

**决策门 (W3)**:
- Vela fork 通过: 并发写入 5 agent × 100 write/s ≥ 500 write/s → 选 Vela
- Vela fork 失败: FalkorDB query latency < 100ms + 向量 recall ≥ 0.85 → 选 FalkorDB
- 两者均失败 → ArcadeDB 长期方案（延迟 M3 2 周）

### 1.4 迁移步骤 (Vela fork 路径)

```bash
# 1. 安装 Vela fork
pip install kuzu-vela  # 或从源码编译

# 2. 数据迁移 (KuzuDB 0.11.3 → Vela fork, binary compatible)
cp -r data/finance-tax-graph data/finance-tax-graph-vela

# 3. 验证
python3 -c "
import kuzu  # Vela fork
db = kuzu.Database('data/finance-tax-graph-vela')
conn = kuzu.Connection(db)
r = conn.execute('MATCH (n) RETURN count(n)')
print(f'Nodes: {r.get_next()[0]}')
"

# 4. 并发压测
python3 tests/concurrent_write_benchmark.py --agents 5 --writes 1000

# 5. 切换 (VPS)
sudo systemctl stop kg-api
mv data/finance-tax-graph data/finance-tax-graph-old
mv data/finance-tax-graph-vela data/finance-tax-graph
sudo systemctl start kg-api
```

### 1.5 向量搜索一体化 (如选 FalkorDB)

FalkorDB 内置 cosine/Euclidean 向量搜索 → 可淘汰 LanceDB：
- 省去 2 套数据库同步
- Graph + Vector 统一查询 (Graph-RAG 原生支持)
- 内存占用从 ~600MB (KuzuDB + LanceDB) 降到 ~400MB

---

## 2. 数据增长路径：500K → 1M

### 2.1 增量来源分层

| 层 | 来源 | 预计增量 | 成本 | 优先级 |
|----|------|---------|------|--------|
| **L1 深化 (内生)** | 现有数据二次加工 | +150K | ~$80 | P0 |
| **L2 扩源 (外部)** | 新政府/法律数据源 | +200K | ~$50 | P1 |
| **L3 合成 (AI)** | Gemini 生成 + 交叉推理 | +100K | ~$150 | P1 |
| **L4 众包 (人工)** | 专家贡献 + 社区 | +50K | ~$70 | P2 |
| **Total** | | **+500K** | **~$350** | |

### 2.2 L1 深化：现有数据二次加工 (+150K)

| 数据源 | 操作 | 预计节点 | 脚本状态 |
|--------|------|---------|---------|
| LR Article QA (40K articles) | Gemini QA v3 (文章级, 非条款级) | +120K | `generate_lr_qa.py` ready |
| RegulationClause 二级拆分 | 条 → 款 → 项 三级 | +15K | `split_clauses_v2.py` 扩展 |
| Edge 富化 (orphan → connected) | 基于关键词/实体的边创建 | +0 nodes, +50K edges | `enrich_orphan_edges.py` ready |
| Temporal Version Chain | 法规修订链 (replace/amend/revoke) | +15K | 新建 |

### 2.3 L2 扩源：新数据源 (+200K)

| 数据源 | 预计节点 | 方法 | 难度 | 阻塞 |
|--------|---------|------|------|------|
| **司法裁判文书** (四级法院) | 100K | 裁判文书网 + browser-automation | HIGH | JS 渲染 + 验证码 |
| **企业研报** (CNINFO/巨潮) | 30K | PDF 解析 + NER | MED | PDF 表格提取 |
| **跨境税务** (DTA/BEPS) | 15K | PDF OCR + 结构化 | MED | 多语言 |
| **社保五险一金** (31 省) | 10K | 政府网站爬虫 | LOW | 已有框架 |
| **个税专项扣除** (7 类) | 5K | 结构化文档 | LOW | 无 |
| **海关监管** (HS 码深度) | 20K | 海关总署 API | MED | WAF 反爬 |
| **行业协会** (注协/税协/财协) | 20K | 网站爬虫 | LOW | 无 |

### 2.4 L3 合成：AI 生成 (+100K)

| 操作 | 预计节点 | 模型 | 成本 |
|------|---------|------|------|
| Industry × Tax × Lifecycle 三维矩阵 | 40K | Gemini 2.5 Flash | ~$60 |
| 合规检查清单生成 (per 法规) | 25K | Gemini 2.5 Flash | ~$40 |
| 假设性问答 (what-if scenarios) | 20K | Gemini 2.5 Pro | ~$30 |
| 跨法规关联推理 | 15K | Gemini 2.5 Pro | ~$20 |

### 2.5 L4 众包：人工贡献 (+50K)

| 渠道 | 预计节点 | 方法 |
|------|---------|------|
| 秦税安专家专栏 | 10K | 邀稿 + 结构化录入 |
| 微信公众号精选 | 15K | wechat-article-search + NER |
| Bilibili 财税课程字幕 | 10K | yt-search-download + 转录 |
| 社区 FAQ (知乎/小红书) | 15K | agent-reach 爬取 + 去重 |

---

## 3. 架构升级

### 3.1 当前架构 (M2)

```
Mac (dev) ──rsync──→ VPS kg-node (100.75.77.112)
                       ├── kg-api (uvicorn:8400)
                       │    ├── KuzuDB (单写锁, 归档)
                       │    └── LanceDB (768d vectors)
                       ├── daily_pipeline.sh (cron)
                       └── m2_pipeline.sh (cron)
```

### 3.2 M3 目标架构

```
Mac (dev) ──auto-sync──→ VPS kg-node
                           ├── kg-api v2 (FastAPI + WebSocket)
                           │    ├── [New] Graph Engine (Vela/FalkorDB)
                           │    │    ├── 并发读写 (5+ agents)
                           │    │    └── [可选] 内置向量搜索
                           │    ├── [保留/替代] LanceDB (if Graph DB 无内置向量)
                           │    └── [New] Event Bus (写入 → 触发 embedding + edge enrichment)
                           ├── [New] Agent Ingest Pool
                           │    ├── crawler-agent (14 gov sources)
                           │    ├── synthesis-agent (Gemini QA/matrix)
                           │    ├── enrichment-agent (edge creation)
                           │    └── embedding-agent (incremental index)
                           ├── [New] Quality Monitor
                           │    ├── orphan rate checker (cron)
                           │    ├── density tracker
                           │    └── Telegram alert on regression
                           └── m3_pipeline.sh (orchestrator)
```

### 3.3 关键架构变更

| 变更 | 原因 | 影响 |
|------|------|------|
| Graph Engine 迁移 | KuzuDB 归档, 单写锁 | 解锁并发写入 |
| Event Bus (写后触发) | Embedding 不再阻塞 ingest | 异步化, 吞吐量 10x |
| Agent Ingest Pool | 多 Agent 并行爬取+注入 | 数据增长速率 5x |
| Quality Monitor | M1/M2 质量回退教训 | 实时告警, 不等 gate |
| API v2 (WebSocket) | 长连接查询 + 流式结果 | RAG 延迟降低 |

---

## 4. 质量保证

### 4.1 Quality Gates

| 节点数 | Gate | 指标 |
|--------|------|------|
| 600K | Mini Gate 4 | orphan < 4%, density ≥ 4.0, P@5 ≥ 86% |
| 700K | Mini Gate 5 | orphan < 3.5%, density ≥ 4.5, P@5 ≥ 87% |
| 850K | Mini Gate 6 | orphan < 3%, density ≥ 5.0, P@5 ≥ 88% |
| 1M | **Final Gate** | **orphan < 3%, density ≥ 6.0, P@5 ≥ 90%** |

### 4.2 Anti-patterns (M1/M2 教训)

| 教训 | M3 对策 |
|------|--------|
| Ingest 端点静默失败 (M2) | 每次 ingest 返回 count + 校验 |
| 空壳节点 (baike 无 content) | Content minimum 200 chars (从 100 提升) |
| KuzuDB 锁阻塞管线 (M2) | 迁移到并发引擎 |
| QA 生成 hang (httpx) | 全局 timeout 1h + 批次 2000 |
| 日期类型不匹配 (M2) | Schema 统一用 STRING, 应用层解析 |
| Orphan 率反弹 (M1) | 实时监控 + 每 10K 节点检查 |

### 4.3 Edge-First 升级：Edge Density ≥ 6.0

M2 目标 density ≥ 3.0, M3 要求 ≥ 6.0 (即每个节点平均 6 条边)。

策略：
1. **注入时创建** (≥2 edges/node): CLASSIFIED_UNDER, ISSUED_BY, LR_ABOUT_TAX
2. **批量富化** (cron): keyword-based RELATES_TO, SIMILAR_TO
3. **AI 推理** (Gemini): semantic REFERENCES, SUPERSEDES, CONFLICTS_WITH
4. **temporal** (自动): VERSION_OF, AMENDED_BY, REVOKED_BY

---

## 5. 时间线

```
W1-4   Phase 1: L1 深化 (+150K, 内生加工) ← 数据优先
W5-10  Phase 2: L2 扩源 (+200K, 新数据源)
W11-14 Phase 3: L3 合成 + L4 众包 (+150K)
W15    Final Gate + 发布
W16    [可选] Phase 0: 图引擎迁移 (如需并发写入)
```

### 详细里程碑

| Week | Phase | 目标节点 | 关键交付 |
|------|-------|---------|---------|
| W1 | 0.1 | 500K (M2 end) | Vela fork 安装 + 并发压测 |
| W2 | 0.2 | 500K | FalkorDB POC + 向量搜索验证 |
| W3 | 0.3 | 500K | 迁移完成, kg-api v2 上线 |
| W4 | 1.1 | 550K | LR Article QA v3 (+50K, 最长文章优先) |
| W5 | 1.2 | 600K | Article QA 继续 + Clause 二级拆分 |
| W6 | 1.3 | 620K | Temporal version chain (+15K) |
| W7 | 1.4 | 650K | Edge 富化 sprint (+50K edges) → Mini Gate 4 |
| W8 | 2.1 | 700K | 司法裁判文书 batch 1 (+50K) |
| W9 | 2.2 | 750K | 裁判文书 batch 2 + 企业研报 → Mini Gate 5 |
| W10 | 2.3 | 800K | 跨境税务 + 社保五险 (+25K) |
| W11 | 2.4 | 850K | 海关监管 + 行业协会 (+50K) → Mini Gate 6 |
| W12 | 2.5 | 880K | 补充爬取 + 去重清洗 |
| W13 | 3.1 | 920K | Industry×Tax×Lifecycle 矩阵 (+40K) |
| W14 | 3.2 | 960K | 合规清单 + what-if (+45K) |
| W15 | 3.3 | 1M | 众包 + 跨法规推理 (+40K) |
| W16 | Gate | 1M | **Final Gate: P@5 ≥ 90%, orphan < 3%, density ≥ 6.0** |

---

## 6. 成本估算

| 项目 | 数量 | 单价 | 总计 |
|------|------|------|------|
| Gemini 2.5 Flash (QA + matrix) | ~500K API calls | $0.20/1M tokens | ~$150 |
| Gemini 2.5 Pro (complex synthesis) | ~50K API calls | $2.50/1M tokens | ~$80 |
| Gemini Embedding 2 | ~1M embeddings | $0.20/1M tokens | ~$20 |
| VPS kg-node (existing) | 16 weeks | $0/month (已有) | $0 |
| Browser Proxy (CF Workers) | ~100K requests | Free tier | $0 |
| 裁判文书网会员 (如需) | 1 month | ~$50 | ~$50 |
| 备用: Residential Proxy | 1GB | ~$50 | ~$50 |
| **Total** | | | **~$350** |

---

## 7. 风险矩阵

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Vela fork 停更 | 中 | 高 | 内部 fork + 6 个月 deadline 切 FalkorDB |
| 裁判文书网反爬升级 | 高 | 中 | scrapling-crawler + 会员账号 + IP 轮换 |
| Gemini API 涨价 | 低 | 中 | Flash Lite 模型降级 + 本地 Qwen 2.5 备份 |
| VPS 磁盘不足 | 低 | 低 | 当前 135GB free, 1M 节点估计 ~2GB |
| 质量稀释 (节点多但边少) | 中 | 高 | 实时 density monitor + Edge-First 强制 |
| 数据合规 (裁判文书隐私) | 中 | 高 | 匿名化 pipeline + 仅保留法律观点不保留当事人信息 |

---

## 8. 竞争定位

| 竞对 | 节点/文档数 | 特点 | CogNebula M3 优势 |
|------|-----------|------|------------------|
| Wolters Kluwer | 126 万 (flat text) | 大而全但浅 | Graph-native, 6x edge density |
| 百度财税知识库 | ~50 万 (搜索索引) | 搜索导向 | MCP Agent 原生, multi-hop |
| 金蝶/用友 ERP 知识库 | ~20 万 (封闭) | ERP 绑定 | 开放架构, 跨系统 |
| Tax.cn 问答 | ~30 万 (Q&A) | 社区众包 | AI 合成 + 图推理 |

M3 完成后定位：**中文财税领域首个百万节点、600 万边的知识图谱，支持 Graph-RAG 多跳推理**。

---

## 9. M3 Principles (从 M1/M2 继承 + 新增)

### 继承
1. **Edge-First**: 每个注入脚本必须同时创建节点+边
2. **Content Minimum**: LR ≥ 200 chars (从 100 提升), QA ≥ 80 chars
3. **Dedup at Source**: Title hash + content hash 双重去重
4. **Quality Gate at Every 50K**: 不等到目标才检查

### 新增
5. **Concurrent-First**: 所有管线假设多 Agent 并行写入
6. **Schema Freeze at 800K**: 800K 后不再改表结构, 只加数据
7. **Privacy-by-Design**: 裁判文书/企业研报自动匿名化
8. **Cost Cap**: 单次管线运行 ≤ $5, 总预算 ≤ $350
9. **Observability**: 每次写入记录 trace (source, count, errors, duration)

---

Maurice | maurice_wen@proton.me
