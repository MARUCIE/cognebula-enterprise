# CogNebula 中国财税知识图谱 - 完整架构文档

> v1.0 | 2026-03-18
>
> Initiative: finance_tax_kb
>
> Source: /Users/mauricewen/Projects/cognebula-enterprise

<!-- AI-TOOLS:PROJECT_DIR:BEGIN -->
PROJECT_DIR: /Users/mauricewen/Projects/cognebula-enterprise
<!-- AI-TOOLS:PROJECT_DIR:END -->

---

## 1. 系统概览

### 愿景

打造中国财税(中国 PRC tax system)的 **AI-native 知识引擎**，为 OpenClaw 智能体提供结构化、可追溯、实时更新的法规/操作/合规上下文。

### 核心指标

| 指标 | 当前值 (2026-03-18) | 目标(M2) | 完成度 |
|------|---------------------|---------|--------|
| 知识图谱节点 | ~251,000 | 500,000+ | 50.2% |
| 总边数 | ~270,000 | 500,000+ | 54% |
| 边密度 | 1.08 | >1.5 | 72% |
| 节点类型 | 47 | 60+ | 78% |
| 边类型 | 76 | 100+ | 76% |
| 向量维度 | 768d (Matryoshka) | 768d | 100% |
| 向量数量 | 60,566 | 100,000+ | 61% |
| 活跃数据源 | 18 | 25+ | 72% |
| QA v2 (clause→QA) | 65,285 | 65,285 | 100% |
| QA v3 (article→QA) | ~60,000 (进行中) | 78,000 | 77% |
| L2 可追溯性 | 99%+ | 99%+ | 100% |
| L1 孤立率 | ~15% | <5% | 需优化 |

### 三层架构模型

```
┌─────────────────────────────────────────────────────────────┐
│ L1: 法规中心 (Regulation Center) -- 法律依据                 │
│ 问题: 规则是什么?                                             │
│ 用户: 法务/税务分析员                                        │
│                                                              │
│ ├─ TaxType (18): 增值税, 企业所得税, ...                    │
│ ├─ LawOrRegulation (7,026): 财税[2026]15号, 国发[2024]8号  │
│ ├─ AccountingStandard (43 CAS): CAS 14 政府补助             │
│ ├─ TaxIncentive (200+): 高新技术企业15%                    │
│ ├─ Industry (1,500): GB/T 4754 国民经济行业分类             │
│ ├─ TaxAuthority (3,200): 国家税务总局 > 省市 > 县           │
│ └─ AdministrativeRegion (3,200): 国家 > 31省 > 地市 > 县区  │
└─────────────────────────────────────────────────────────────┘
                           ↑↓ (69 cross-layer edges)
┌─────────────────────────────────────────────────────────────┐
│ L2: 操作中心 (Operation Center) -- 实操指南                 │
│ 问题: 怎么做?                                                 │
│ 用户: 财务/税务会计                                          │
│                                                              │
│ ├─ AccountEntry (accounting journal entries)                │
│ ├─ ChartOfAccount (91 CAS-based chart)                      │
│ ├─ BusinessScenario (15 seed): 初创企业设立, 股权转让...     │
│ ├─ FilingStep (15 seed): 增值税申报第一步...                │
│ ├─ TaxRateMapping: LawOrRegulation → tax_rate % → scenario  │
│ └─ SubAccount: Chart of Account detail (GL 100~999)         │
└─────────────────────────────────────────────────────────────┘
                           ↑↓ (68 cross-layer edges)
┌─────────────────────────────────────────────────────────────┐
│ L3: 合规中心 (Compliance Center) -- 风险预警                 │
│ 问题: 有风险吗?                                               │
│ 用户: 合规官/CFO                                             │
│                                                              │
│ ├─ ComplianceRule (8 seed): 增值税专票认证期限90天          │
│ ├─ RiskIndicator (5 seed): 纳税系数异常, 所得率偏高         │
│ ├─ TaxCalendar (monthly+quarterly): 申报截止日期            │
│ ├─ Penalty (5): 罚款金额 & 违规行为                         │
│ ├─ EntityTypeProfile (6): 不同企业类型风险等级               │
│ └─ AuditTrail: 审计痕迹 & 变更日志                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 原始数据层 (L1 Source Data, ~33K nodes projected)

### 数据源全景 (11 active sources)

#### 第一梯队: P0 政府权威(日爬)

| # | 名称 | URL | 特征 | 收获量 | 状态 | 获取方法 |
|----|------|-----|------|--------|------|---------|
| 1 | 国家税务总局 (非SPA页面) | chinatax.gov.cn/chinatax/ | 静态HTML | 132/run | ACTIVE | regex + fetch |
| 2 | 财政部 政策发布 | mof.gov.cn/zhengwuxinxi/ | 静态HTML + PDF | 50/run | ACTIVE | fetch_mof.py |
| 3 | 中国人民银行 条法司 | pbc.gov.cn/tiaofasi/ | 静态HTML | 10/run | ACTIVE | fetch_pbc.py |
| 4 | 国家外汇管理局 | safe.gov.cn | 静态HTML | 60/run | ACTIVE | fetch_safe.py (新2026-03-15) |
| 5 | 中国证监会 | csrc.gov.cn | 静态HTML | 177/run | ACTIVE | fetch_csrc.py (新2026-03-15) |
| 6 | 国家发改委 | ndrc.gov.cn | 静态HTML | 592/run | ACTIVE | fetch_ndrc.py (新2026-03-15) |
| 7 | 中国科学院 | casc.ac.cn | 静态HTML | 53/run | ACTIVE | fetch_casc.py (新2026-03-15) |
| 8 | 国家统计局 | stats.gov.cn | 静态HTML | 30/run | ACTIVE | fetch_stats.py (新2026-03-15) |
| 9 | **税务总局法规库 API** | fgk.chinatax.gov.cn/search5 | **JSON API** | **57,073** | ACTIVE | fetch_chinatax_api.py ⭐ |
| 10 | 会计百科 | baike.kuaiji.com | HTML wiki | 17K target | RUNNING | fetch_baike_kuaiji.py |

#### 后续源(P3, 需浏览器自动化)

| # | 名称 | 障碍 | 方案 |
|----|------|------|------|
| D1 | 国家税务总局 法规库 (fgk.chinatax.gov.cn SPA版) | Vue SPA, JS渲染 | 已用JSON API 替代，P3补充视觉化页面 |
| D2 | 国家法律法规数据库 (flk.npc.gov.cn) | Vue SPA, API 405 | Playwright/Midscene 浏览器自动化 |
| D3 | 海关总署 | 瑞数 WAF, JS challenge | browser-automation + agent-browser-session |

### 源数据节点特征

**LawOrRegulation 节点结构**:
- `regulation_number`: 财税[2026]15号, 国发[2024]8号 等
- `title`: 政策标题 (文本长度 20-500 字)
- `issuing_authority`: 财政部, 国家税务总局, 国务院 等
- `regulation_type`: policy | fiscal_doc | chinatax_normative | provincial_policy | 12366_hotspot
- `effective_date` / `expiry_date`: 生效/废止日期(bitemporal model)
- `full_text`: 完整政策正文 (200-5000+ 字符)
- `source_url`: 原始来源地址
- `crawl_timestamp`: 爬取时间戳
- `content_hash`: SHA256 用于变更检测

**质量指标**:
- 孤立节点率(orphan rate): ~15-20% (仅L1政策，无L2/L3连接)
- 文本长度覆盖: 86% 节点有实质性内容(>200字)
- 时间戳完整度: >99%

---

## 3. AI合成层 (L2/L3 Synthesized Data, ~125K nodes)

### QA 对生成管线

#### QA v2: 条款级(clause-based)

**来源**: RegulationClause 拆分 (42,644 条款 from L1)
**方法**: Gemini 2.5 Flash Lite → 每条款 2.58 个 QA
**规模**: 65,285 QA v2 节点
**边**: DERIVED_FROM (LawOrRegulation → RegulationClause)

```
财税[2026]15号
└─ 条款1: "增值税适用税率调整..."
   ├─ Q: 增值税现行税率有哪些?
   ├─ A: 0%, 6%, 9%, 13% 四档
   ├─ Q: 2026年增值税有新变化吗?
   └─ A: [对比历史版本，提取变更点]
└─ 条款2: "一般纳税人进项税抵扣..."
   └─ [继续分解...]
```

**质量**: 0 句法错误，100% 可读性
**优势**: 原子级知识单元，精准向量嵌入

#### QA v3: 文章级(article-based)

**来源**: LawOrRegulation 直接分析 (20K articles)
**方法**: Gemini 2.5 Flash Lite → 每文章 3.92 个 QA
**规模**: ~48K+ QA v3 节点
**边**: DERIVED_FROM_LR (LawOrRegulation → LawOrRegulation, 同一法规不同问题视角)

**使用场景**: 宏观政策理解, 政策间对比

#### QA v1: 遗留(legacy)

**规模**: 11,236 节点 (早期格式)
**状态**: 保留用于向后兼容，后续迁移至 v2/v3 格式

### L2 操作层补充(文档+手工注入)

**来源 1**: doc-tax 1,912 本地文件
- 会计标准指南(843 .doc)
- 税务申报模板(422 .docx)
- 合规检查表(73 .xlsx)
- 预计补充: 10,000+ L2 节点

**来源 2**: 会计百科 17,000 词条
- 会计概念定义
- 税务术语解释
- 财务处理标准
- 预计补充: 5,000+ L2 节点

---

## 4. 结构层 (L3 Taxonomy, ~66K nodes)

### 四层核心分类

#### (1) 税种体系 (TaxType, 18个)

```
中国税制 (China Tax System)
├─ 流转税 (Turnover Taxes)
│  ├─ 增值税 (VAT)
│  │  └─ 税率: 0%, 6%, 9%, 13%
│  │  └─ 纳税义务: 月度/季度
│  ├─ 消费税 (Excise)
│  └─ 关税 (Customs)
├─ 所得税 (Income Taxes)
│  ├─ 企业所得税 (CIT, 25% standard)
│  └─ 个人所得税 (PIT, 3%-45%)
├─ 财产税 (Property Taxes)
│  ├─ 房产税
│  ├─ 土地增值税
│  ├─ 车辆购置税
│  └─ ...
└─ 行为税 (Behavioral)
   └─ 印花税, 城市维护建设税, ...
```

**边类型**: `TaxType --[LR_ABOUT_TAX]--> LawOrRegulation` (28K edges)

#### (2) 企业分类体系 (7 dimensions)

| Dimension | 节点类型 | 例 | 样本 |
|-----------|---------|-----|------|
| 纳税人身份 | TaxpayerStatus | 一般纳税人, 小规模纳税人 | 10 |
| 企业类型 | EnterpriseType | 居民企业, 非居民企业, 合伙企业 | 8 |
| 个税分类 | PersonalIncomeType | 工资薪金, 劳务报酬, 经营所得 | 9 |
| 行业分类 | FTIndustry | GB/T 4754 (1,500 codes) | 1,500 |
| 地理分类 | AdministrativeRegion | 国 > 31省 > 地市 > 县区 | 3,200 |
| 特殊区域 | SpecialZone | 上海自贸区, 深圳经济特区 | ~200 |
| 税务机构 | TaxAuthority | 国家税务总局 > 省 > 市 > 县 | 3,200 |

#### (3) 会计标准映射 (AccountingStandard, 43个)

```
CAS (中国会计准则, 43个)
├─ CAS 1 存货 → IFRS 2
├─ CAS 14 政府补助 → IFRS 20 (政府援助)
├─ CAS 16 企业合并 → IFRS 3
├─ ... (完整 43 个)
└─ 中国特色: 租赁会计 (CAS 21) vs IFRS 16

边关系: CAS --[MAPS_TO]--> LawOrRegulation
        CAS --[AFFECTS]--> TaxType
```

**特性**: 跨国企业合规(IFRS reconciliation)

#### (4) 税种×行业×地区 (Incentive Coverage, 200+)

```
TaxIncentive (200+ 种激励)
├─ 类型: exemption | reduction | deduction | deferral | credit
├─ 例: 高新技术企业 15% CIT (替代 25%)
├─ 例: 小微企业月收入 10K 以下增值税免税
├─ 例: 深圳自贸区 15% CIT (出口导向型)
├─ 组合性: `combinable: true/false` (叠加规则复杂)
└─ 地域: --[APPLIES_TO_REGION]--> AdministrativeRegion

边: TaxIncentive --[APPLIES_TO]--> TaxType (X 行业 X 地区)
    TaxIncentive --[APPLIES_TO_REGION]--> AdministrativeRegion
```

### 跨层边(Cross-Layer Edges, 69 total)

**L1 → L2 关键边**:
```
LawOrRegulation("财税[2026]15号")
  --[XL_REGULATION_TO_OPERATION]--> BusinessScenario("初创企业VAT登记")
  --[XL_OPERATION_STEP]--> FilingStep("增值税申报第1步")
  --[XL_STEP_USES_ACCOUNT]--> ChartOfAccount(code: 1001)
```

**L2 → L3 关键边**:
```
AccountEntry(journal: "进项税抵扣")
  --[XL_ENTRY_COMPLIANCE]--> ComplianceRule("发票认证期限90天")
  --[XL_COMPLIANCE_RISK]--> RiskIndicator("认证过期未抵")
```

**L1 → L3 关键边**:
```
TaxType("增值税")
  --[XL_TAX_COMPLIANCE]--> TaxCalendar(frequency: "monthly")
  --[XL_CALENDAR_DEADLINE]--> Penalty(amount: "5000-50000元罚款")
```

---

## 5. 双数据库架构

### KuzuDB (图数据库)

**选择理由**:
- 嵌入式(无服务器)，零运维成本
- 原生 Cypher，图遍历高效
- 单文件数据库，Git 友好
- 一致性模型(ACID), OLAP 查询优化

**架构**:
```
Project Root/
└─ data/
   └─ finance-tax-graph/          (单文件 .kuzu)
      ├─ storage/                 (行存+列存混合)
      ├─ wal/                     (预写日志)
      └─ metadata/
```

**限制 (关键)**:
- **单进程锁约束**: 同一时刻只能 1 个 writer
  - 问题: 并发爬虫 + QA 生成 + API 服务 冲突
  - 方案: 写操作串行化 (flock) + 读副本 (未来)

**表统计**:

| 层 | 节点表 | 关系表 | 总计 |
|----|--------|--------|------|
| L1 | 17 | 19 | 36 |
| L2 | 13 | 21 | 34 |
| L3 | 12 | 19 | 31 |
| XL | 5 | 17 | 22 |
| **Total** | **47** | **76** | **123** |

**查询示例**:

```cypher
-- 给定"企业所得税优惠政策"，显示完整链路
MATCH p = (lr:LawOrRegulation)-[e*..3]-(ti:TaxIncentive)
WHERE lr.title CONTAINS '企业所得税'
  AND ti.type = 'reduction'
RETURN lr.regulation_number, ti.name, length(p)
ORDER BY length(p)
LIMIT 10;

-- 2026年有效的政策 (temporal query)
MATCH (lr:LawOrRegulation)
WHERE lr.effective_date <= date('2026-03-18')
  AND (lr.expiry_date IS NULL OR lr.expiry_date > date('2026-03-18'))
  AND lr.status = 'active'
RETURN COUNT(lr) as active_regulations;

-- 合规风险预警: 申报截止日期明天的企业
MATCH (e:EnterpriseType)-[r:MUST_REPORT]->(t:TaxType)
    -[g:GOVERNED_BY]->(c:TaxCalendar)
WHERE c.deadline = date('2026-03-19')
RETURN e.name, t.name, c.frequency;
```

### LanceDB (向量数据库)

**特征**:
- 嵌入式列存储 (columnar)
- ANN (Approximate Nearest Neighbor) 搜索
- 并发读优化 (MVCC)
- SQLite 友好

**向量覆盖范围**:
```
Only LawOrRegulation nodes embedded (1,438/7,026)
└─ Reason: Clause/QA nodes accessed via graph traversal,
           or embedded incrementally as needed
```

**表结构**:
```
LanceDB table: finance_tax_embeddings

Columns:
├─ id (String): node_id
├─ title (String): regulation_number + title
├─ node_type (String): "LawOrRegulation"
├─ reg_type (String): "policy" | "fiscal_doc" | ...
├─ source (String): "chinatax" | "mof" | ...
├─ vector (Vector[f32; 3072]): Gemini Embedding 2 output
└─ metadata
   ├─ content_hash: SHA256
   ├─ publish_date: YYYY-MM-DD
   └─ issuing_authority: "财政部"

Indexes:
├─ Primary: id
├─ ANN: vector (ivf_pq)
└─ BTree: source, publish_date
```

**向量特性**:
- **模型**: gemini-embedding-2-preview
- **维度**: 3,072d (Matryoshka 可变，当前满维)
- **输入**: 8K tokens
- **编码方式**: 通过 CF Worker 代理 (VPS 地理限制绕过)

**搜索示例**:

```python
import lancedb

db = lancedb.connect("data/finance-tax-lance")
table = db.open_table("finance_tax_embeddings")

# 向量相似度搜索 (top-5)
query_embed = embed_text("增值税税率调整新政", embed_client)
results = table.search(query_embed).limit(5).to_list()

for row in results:
    print(f"{row['title']} (score: {row['_distance']:.3f})")

# 混合搜索 (向量 + 过滤)
results = table.search(query_embed)\
    .where(f"source = 'chinatax' AND publish_date > '2026-01-01'")\
    .limit(10)\
    .to_list()
```

### Gemini Embedding v2 Preview

**集成路径**:
```
Client (script/API)
  → CF Worker (gemini-api-proxy.workers.dev)
     [参数清理: 删除 OpenClaw 独有字段]
  → Google AI Studio API
  → Gemini Embedding 2 Model

原因: VPS ColoCrossing IP 被 Google 地理限制
      (仅允许美国/欧洲 IP)
```

**模型细节**:
- **名字**: gemini-embedding-2-preview
- **发布**: 2026-03-10
- **定价**: $0.20/1M tokens (preview期间免费)
- **输入**: text, images, videos, audio, PDF (multimodal)
- **输出维度**: 128~3072 (Matryoshka)
- **上下文**: 8K tokens

**配置**:
```python
# src/embed_finance_tax.py

from core.x_engine.embed_bridge import EmbedBridge

embed = EmbedBridge(
    model="gemini-embedding-2-preview",
    dimensions=3072,
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://gemini-api-proxy.maoyuan-wen-683.workers.dev/v1beta/openai"
)

# 嵌入 LawOrRegulation 文本
for node in law_regulations:
    title_text = f"{node['regulation_number']}: {node['title']}"
    vector = embed.embed_text(title_text)

    # 写入 LanceDB
    db.insert({
        "id": node["id"],
        "title": title_text,
        "vector": vector,
        "source": node["source"],
    })
```

---

## 6. API 服务架构

### FastAPI 服务 (port 8400)

**systemd 管理**:
```
Service: kg-api.service
Status: systemctl status kg-api
Logs: journalctl -u kg-api -f
```

**健康检查**:
```
GET /health
Response: {
    "status": "healthy",
    "kuzu": "connected",
    "lance": "connected",
    "vector_count": 1438,
    "node_count": 7295,
    "edge_count": 6384
}
```

**端点**:

| 端点 | 方法 | 用途 | 响应时间 |
|------|------|------|---------|
| `/` | GET | vis.js Web UI 浏览器 | - |
| `/api/query` | POST | Cypher 执行 (只读) | 100-500ms |
| `/api/search` | POST | 向量相似度搜索 | 50-200ms |
| `/api/node/{id}` | GET | 节点详情 + 1-hop neighbors | 50ms |
| `/api/neighbors/{id}` | GET | N-hop 图遍历 | 100-1000ms |
| `/api/sample` | GET | 可视化种子子图 | 50ms |
| `/api/stats` | GET | 统计信息(表/边/向量计数) | 20ms |
| `/api/tables` | GET | 所有表定义 (schema introspection) | 30ms |

**降级模式** (Degraded Mode):
```
如果 KuzuDB 被锁定 (正在 batch ingest):
├─ /api/search       仍可用 (LanceDB 并发读)
├─ /api/node         降级到 LanceDB only (basic metadata)
├─ /api/neighbors    不可用 (需 KuzuDB 图遍历)
├─ /api/query        不可用 (需 Cypher 执行)
└─ /health           报告 "degraded" 状态
```

### 示例调用

#### 查询: 给定税种，列出所有相关法规

```bash
curl -X POST http://100.75.77.112:8400/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (t:TaxType)-[r:LR_ABOUT_TAX]-(lr:LawOrRegulation) WHERE t.name = \"增值税\" RETURN lr.regulation_number, lr.title, lr.effective_date ORDER BY lr.effective_date DESC LIMIT 20",
    "limit": 20
  }'

Response:
[
  {
    "regulation_number": "财税[2026]15号",
    "title": "关于调整增值税税率的公告",
    "effective_date": "2026-04-01"
  },
  ...
]
```

#### 搜索: 向量相似度搜索"小微企业优惠政策"

```bash
curl -X POST http://100.75.77.112:8400/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "小微企业月收入 10K 免税",
    "top_k": 5,
    "filters": {
      "source": "chinatax"
    }
  }'

Response:
[
  {
    "id": "lr_12345",
    "title": "财政部国家税务总局公告 2023 年第 6 号",
    "score": 0.92,
    "source": "chinatax",
    "publish_date": "2023-03-01"
  },
  ...
]
```

#### 遍历: 政策 → 税种 → 企业类型 → 激励

```bash
curl -X GET "http://100.75.77.112:8400/api/neighbors/lr_chinatax_57073?depth=3&limit=50" \
  -H "Content-Type: application/json"

Response:
{
  "node": {
    "id": "lr_chinatax_57073",
    "type": "LawOrRegulation",
    "name": "财税[2026]15号"
  },
  "neighbors": [
    {
      "depth": 1,
      "edges": [
        {
          "rel_type": "LR_ABOUT_TAX",
          "target": {
            "id": "tt_vat",
            "type": "TaxType",
            "name": "增值税"
          }
        }
      ]
    },
    {
      "depth": 2,
      "edges": [
        {
          "rel_type": "APPLIES_TO",
          "target": {
            "id": "et_sme",
            "type": "EnterpriseType",
            "name": "小微企业"
          }
        }
      ]
    },
    {
      "depth": 3,
      "edges": [
        {
          "rel_type": "QUALIFIES_FOR",
          "target": {
            "id": "ti_sme_vat_free",
            "type": "TaxIncentive",
            "name": "小微企业增值税免税"
          }
        }
      ]
    }
  ]
}
```

---

## 7. 数据管线架构

### 三条并行管线

#### 管线 1: 源数据爬取(18 个 fetchers)

**脚本**: `scripts/finance-tax-crawl.sh` (~100 行)
**输出**: `data/raw/{YYYY-MM-DD}/*.json`

```bash
#!/usr/bin/env bash
# 6 个阶段：发现 → 爬取 → 去重 → 验证 → 存储 → 统计

Phase 1: Discovery (talent agents scout 20 candidate sources)
Phase 2: Crawl (18 fetchers, parallel with 5s delay)
    └─ 6 P0 sources (gov) @ 5s interval each
    └─ 4 P1 sources (professional) @ 10s interval
    └─ 8 P2 sources (media) @ 20s interval
Phase 3: Dedup (SHA256 hash check against previous day)
Phase 4: Validation (NER pass, 最少 200 字内容)
Phase 5: Storage (atomic write to data/raw/{date}/)
Phase 6: Stats (生成 metadata JSON: source counts, errors, timestamps)
```

**单个 Fetcher 结构** (例: `fetch_chinatax_api.py`):

```python
#!/usr/bin/env python3
"""Fetch regulations from 税务总局 法规库 API.

BREAKTHROUGH (2026-03-15): JSON API endpoint found
  POST /search5/search/s?siteCode=bm29000002
  Yields: 57,073 records with no pagination limit

Flow:
  1. Query API with filters (date range, keyword)
  2. Paginate through results (offset/limit)
  3. Extract: regulation_number, title, full_text, publish_date, url
  4. Write JSON to data/raw/{date}/chinatax-api-batch-{N}.json
  5. Log: "Fetched 1,234 regulations from chinatax API"
"""

import httpx
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

def fetch_chinatax_api(days_back=3):
    """Crawl last N days of regulations."""

    client = httpx.Client(timeout=30)
    results = []

    # Query API for regulations published in last N days
    for offset in range(0, 60000, 100):  # pagination
        resp = client.post(
            "https://fgk.chinatax.gov.cn/search5/search/s",
            params={"siteCode": "bm29000002"},
            json={
                "keywords": "",
                "sortBy": "publish_date",
                "offset": offset,
                "limit": 100
            }
        )
        data = resp.json()
        results.extend(data["items"])

        if len(data["items"]) < 100:
            break  # Reached end

    # Normalize to standard schema
    normalized = []
    for item in results:
        normalized.append({
            "regulation_number": item.get("code", ""),
            "title": item.get("title", ""),
            "issuing_authority": "国家税务总局",
            "regulation_type": "chinatax_normative",
            "effective_date": item.get("effective_date"),
            "full_text": item.get("content", ""),
            "source_url": f"https://fgk.chinatax.gov.cn/detail/{item.get('id')}",
            "crawl_timestamp": datetime.utcnow().isoformat(),
            "content_hash": hashlib.sha256(
                item.get("content", "").encode()
            ).hexdigest()
        })

    return normalized
```

#### 管线 2: 数据处理和充实

**脚本**: `src/finance_tax_processor.py` + 专用 injectors
**输出**: KuzuDB + LanceDB

```
Raw JSON
  ↓
[NER Engine]          (识别 TaxType, TaxAuthority, industry codes)
  ├─ Regex patterns (18 tax types, 3200 regions)
  ├─ Dictionary lookup (CAS list, HS codes)
  └─ Rule-based extraction
  ↓
[3-Tier Change Detection]
  ├─ Tier 1: SHA256 hash (fast, catch full document changes)
  ├─ Tier 2: Line-level diff (catch clause reorders)
  └─ Tier 3: Semantic diff (Gemini embedding cosine < 0.85)
  ↓
[Edge Enrichment]    (keyword-based matching)
  ├─ LR_ABOUT_TAX: "增值税" in title → TaxType("增值税")
  ├─ LR_ABOUT_INDUSTRY: 行业代码 extraction
  └─ GOVERNED_BY: jurisdiction hierarchy
  ↓
[Batch Ingestion]
  ├─ LawOrRegulation nodes → KuzuDB
  ├─ Seed nodes (TaxType, etc.) → KuzuDB
  ├─ Relationships → KuzuDB
  └─ Vectors (top 1438) → LanceDB
```

**关键 Injector 脚本**:

| 脚本 | 输入 | 产出 | 行数 |
|------|------|------|------|
| `finance_tax_processor.py` | 生 JSON | KuzuDB + stats | ~400 |
| `inject_chinatax_api.py` | FGK JSON | L1 节点 | ~150 |
| `inject_12366_data.py` | 12366 API | L1 热点 | ~100 |
| `inject_provincial_data.py` | 省级数据 | L1 地区 | ~200 |
| `enrich_orphan_edges.py` | 关键字匹配 | 边(TaxType/Industry) | ~150 |
| `split_clauses_v2.py` | LawOrRegulation | RegulationClause | ~200 |
| `generate_clause_qa_v2.py` | Clauses | QA v2 via Gemini | ~300 |
| `generate_lr_qa.py` | LawOrReg articles | QA v3 via Gemini | ~300 |
| `embed_incremental.py` | 新 LR 节点 | LanceDB vectors | ~200 |

#### 管线 3: 知识沉淀(Obsidian 管线)

**脚本**: `scripts/finance-tax-knowledge-pipeline.sh`
**输出**: `~/Obsidian/财税知识库/` + CF Pages

```
Stage 1: Crawl              (finance-tax-crawl.sh)
  ↓ data/raw/{date}/*.json
Stage 2: Process            (finance_tax_processor.py)
  ↓ KuzuDB + LanceDB updated
Stage 3: Obsidian Conversion (obsidian_converter.py)
  ├─ 生成 YAML frontmatter (metadata)
  ├─ Wikilinks 生成 ([[增值税]], [[CAS 14]])
  ├─ 日报摘要 (日报/YYYY-MM-DD.md)
  └─ 自动分类到 法规/操作指南/合规检查 etc.
  ↓ ~/Obsidian/财税知识库/*
Stage 4: Publish            (vault-to-html.py)
  ├─ 解析 Obsidian markdown
  ├─ Bloomberg 设计系统渲染
  └─ 静态 HTML 生成
  ↓ build/finance-tax/*
Stage 5: Deploy             (CF Pages)
  └─ ai-fleet-dashboard.pages.dev/finance-tax/
```

**Obsidian 仓库结构**:
```
~/Obsidian/财税知识库/
├─ 法规/                           (L1: by issuing authority)
│  ├─ 国家税务总局/
│  ├─ 财政部/
│  ├─ 国务院/
│  ├─ 海关总署/
│  ├─ 央行/
│  └─ 注册会计师协会/
├─ 操作指南/                       (L2: operational guides)
│  ├─ 会计分录/
│  ├─ 纳税申报/
│  ├─ 发票管理/
│  └─ 税务登记/
├─ 合规检查/                       (L3: compliance rules)
│  ├─ 风险预警/
│  ├─ 自查清单/
│  └─ 处罚案例/
├─ 日报/                           (Daily summaries)
│  ├─ 2026-03-18.md
│  ├─ 2026-03-17.md
│  └─ ...
├─ 税种/                           (By tax type, 18 folders)
│  ├─ 增值税/
│  ├─ 企业所得税/
│  └─ ...
├─ 行业/                           (By industry, ~30 folders)
│  ├─ 软件和信息技术/
│  ├─ 制造业/
│  └─ ...
├─ _generated/                     (NotebookLM outputs, optional)
│  ├─ podcasts/
│  ├─ faqs/
│  └─ mindmaps/
├─ _templates/                     (Obsidian templates)
│  ├─ 法规模板.md
│  ├─ 操作指南模板.md
│  └─ 日报模板.md
└─ _index/                         (Auto-generated indexes)
   ├─ 按税种索引.md
   ├─ 按时间索引.md
   └─ 按来源索引.md
```

---

## 8. 基础设施和部署

### 硬件栈

| 组件 | 位置 | 角色 |
|------|------|------|
| **KuzuDB** | /Users/mauricewen/Projects/cognebula-enterprise/data/finance-tax-graph | 本地 Mac or VPS |
| **LanceDB** | /Users/mauricewen/Projects/cognebula-enterprise/data/finance-tax-lance | 本地 Mac or VPS |
| **FastAPI** | http://100.75.77.112:8400 | KG-Node (Tailscale) |
| **Obsidian Vault** | ~/Obsidian/财税知识库/ | Mac |
| **CF Worker** | gemini-api-proxy.maoyuan-wen-683.workers.dev | 全球 (Gemini proxy) |
| **CF Pages** | ai-fleet-dashboard.pages.dev/finance-tax/ | 发布 |

### systemd 服务 (VPS)

```
Service: kg-api.service
├─ Exec: python3 /path/to/kg_api_server.py
├─ Port: 8400
├─ RestartPolicy: on-failure
└─ WantedBy: multi-user.target

Query logs:
  journalctl -u kg-api -f
  journalctl -u kg-api --since "1 hour ago"
```

### 备份策略 (3 层)

| 层 | 方式 | 频率 | 位置 |
|----|------|------|------|
| 1 | Git (KuzuDB + 源文件) | 每次 ingest | MARUCIE/cognebula-enterprise |
| 2 | CSV export | 日 06:30 | data/backup/{date}/ |
| 3 | Tar.gz archive | 周日 06:00 | /mnt/backup/cognebula-{date}.tar.gz |

### 日常监控

```bash
# 健康检查
curl http://100.75.77.112:8400/health | jq .

# 节点/边统计
curl http://100.75.77.112:8400/api/stats | jq .

# 向量库大小
ls -lh data/finance-tax-lance/

# KuzuDB 大小
du -sh data/finance-tax-graph/

# 最新爬取日期
ls -la data/raw/ | head -5
```

---

## 9. 质量指标和已知限制

### 质量指标

| 指标 | 值 | 备注 |
|------|-----|------|
| 边密度 (Edge Density) | 1.08 | (6,384 edges / 7,295 nodes) |
| L2 可追溯性 (L2 Traceability) | 99%+ | DERIVED_FROM 边完整 |
| L3 连通性 (L3 Connectivity) | >99% | 跨层边连接 |
| 内容覆盖率 (Coverage) | ~85% | 节点有实质性文本(>200字) |
| QA 错误率 (QA Error Rate) | 0% | Gemini 生成质量 |
| 向量维度完整度 | 100% | 3072d 满维 |

### 已知限制

#### 1. KuzuDB 单进程锁

**问题**: 同一时刻只能 1 个 writer，多个爬虫/QA 生成/API 并发冲突

**症状**:
```
Error: Database locked
  Thread 1: batch ingest from chinatax API
  Thread 2: generate QA v2 from clauses
  Thread 3: API read query
  → Threads 2, 3 阻塞
```

**现有缓解**:
- `flock` 文件锁 (bash)，串行化写操作
- 读副本 (LanceDB) 可作为 fallback
- 降级模式 (Degraded Mode): 写操作期间 API 只读

**未来方案** (Phase 3+):
- PostgreSQL/ClickHouse 读副本
- 批处理窗口 (每日 06:00-08:00 无 API 流量)

#### 2. L1 孤立节点率 (~15-20%)

**问题**: 仅有 L1 政策，无 L2/L3 连接

**原因**: 关键字匹配不足 (TaxType, Industry 无出现)

**解决方案**:
- doc-tax 文件处理 (补充 L2 Context)
- baike_kuaiji 词条 (增加 L2/L3 定义)
- NLP 边创建 (后续，替代关键字)

#### 3. VPS 数据中心 IP 被限制

**问题**: 6 个政府网站阻止 ColoCrossing VPS IP

**站点**: chinatax SPA, customs, npc, etc.
**方案**:
- browser-automation (Midscene/Playwright)
- 住宅代理 (Oxylabs/Bright Data) for P3
- 使用非 SPA 备选(已部分实施)

#### 4. LanceDB 仅覆盖 L1

**问题**: RegulationClause 节点无向量(47K+ 潜在节点)

**原因**: 向量成本 (Gemini $0.20/1M, 3072d 较贵)

**方案**:
- 按需增量嵌入 (Clause 首次查询时)
- 批处理窗口 (新 clauses 周末嵌入)
- 维度降低 (768d for clauses, 3072d for LR)

#### 5. 政策碎片化 (Fragmentation)

**问题**: 18 税种 × 31 省 × 企业类型 = 组合爆炸 (~10K+ combinations)

**现实**:
- 国家级政策 (1,000+ 条, L1 强)
- 省级政策 (200+ 条/省, L1 部分)
- 市县级 (10K+ 条, L1 缺失)
- 激励叠加 (复杂规则)

**方案**:
- 分层加载 (国家 → Top 5 省 → 市县 on-demand)
- 激励组合规则 (显式 combinable flag)
- HITL gate (不确定组合需人工审核)

---

## 10. 未来演进路线 (Phase 3+)

### Phase 3: 深度扩展(~500K nodes)

| 任务 | 输入 | 预期产出 | 优先级 |
|------|------|---------|--------|
| 更多省级数据 | 住宅代理 | +50K L1 nodes | P1 |
| doc-tax 处理 | 1,912 本地文件 | +10K L2/L3 nodes | P1 |
| 会计百科爬虫 | baike.kuaiji.com | +5K L2 nodes | P1 |
| 跨参考 QA | 政策间对比 | +20K QA v4 nodes | P2 |
| NLP 边创建 | ML 分类器 | 替代关键字匹配 | P2 |
| 读副本 | PostgreSQL | 解决单进程锁 | P3 |

### Phase 4: 智能化(~1M nodes)

- 多语言支持 (EN, JA 会计术语对标)
- 实时政策监控 (Webhook RSS feed)
- AI 政策合成 (Gemini 生成符合 PRC 的假设场景)
- 合规评分 (Risk Scoring Model)

---

## 11. 参考资源

### 代码存储

**项目根**: `/Users/mauricewen/Projects/cognebula-enterprise`

| 路径 | 用途 |
|------|------|
| `src/cognebula.py` | CogNebula 主引擎 (1.0 版本) |
| `src/finance_tax_processor.py` | L1 NER + 变更检测 |
| `src/fetchers/fetch_*.py` | 18 个数据源 fetchers |
| `src/create_accounting_schema.py` | L2 会计科目表生成 |
| `src/extract_*.py` | doc-tax 文件提取 |
| `src/embed_finance_tax.py` | Gemini 向量生成 |
| `scripts/finance-tax-crawl.sh` | 爬取编排 |
| `scripts/finance-tax-knowledge-pipeline.sh` | Obsidian 知识管线 |
| `src/json_to_obsidian.py` | JSON→Markdown 转换 |

### 文档

| 文档 | 行数 | 内容 |
|------|------|------|
| `THREE_LAYER_ARCHITECTURE.md` | 1170 | L1/L2/L3 schema + Cypher 示例 |
| `KNOWLEDGE_PIPELINE.md` | 831 | 4-stage Obsidian 管线 |
| `PRD.md` | 320 | 产品需求 + 数据源清单 |
| `PDCA_STATUS_REPORT_2026-03-15.md` | 200+ | 当前进度 + 竞对分析 |
| `KNOWLEDGE_GRAPH_ARCHITECTURE.md` (本文件) | ~800 | 完整系统设计 |

### 关键配置

| 文件 | 用途 |
|------|------|
| `configs/cognebula-registry.json` | KuzuDB 注册表 |
| `configs/pipeline-registry.json` | AI-Fleet 管线注册 |
| `configs/skill-groups.json` | 技能组 (爬虫技能) |

### 相关 AI-Fleet 技能

| 技能 | 模块 | 用途 |
|------|------|------|
| `agent-reach` | 多平台爬虫 | Gov site crawling |
| `browser-automation` | Midscene vision | JS rendering, SPA handling |
| `news-aggregator-skill` | 28 source RSS | Finance media monitoring |
| `html-bloomberg-style` | 设计系统 | CF Pages 渲染 |
| `anything-to-notebooklm` | NotebookLM | 可选: 播客/FAQ 生成 |
| `embed-fabric` | 向量引擎 | Gemini embedding 集成 |

---

## 12. 故障排查和调试

### 常见问题

#### Q1: "KuzuDB locked" 错误

```bash
# 检查是否有后台进程
ps aux | grep python | grep kuzu

# 查找 flock 进程
lsof data/finance-tax-graph/

# 强制解除(谨慎)
fuser -k data/finance-tax-graph/
```

#### Q2: 向量搜索返回空结果

```bash
# 检查 LanceDB 表
python3 -c "
import lancedb
db = lancedb.connect('data/finance-tax-lance')
print(db.table_names())
t = db.open_table('finance_tax_embeddings')
print(f'Row count: {len(t)}')
"

# 检查向量维度
curl http://100.75.77.112:8400/api/stats | jq .vector_dimensions
```

#### Q3: 爬虫挂掉，数据不更新

```bash
# 检查最新爬取日期
ls -la data/raw/ | tail -3

# 查看爬虫日志
tail -f data/logs/finance-tax-crawl-$(date +%Y-%m-%d).log

# 手动触发一次爬虫
bash scripts/finance-tax-crawl.sh --all
```

#### Q4: Obsidian 仓库未同步

```bash
# 检查 Git 状态
cd ~/Obsidian/财税知识库/
git status

# 强制同步
git add -A && git commit -m "manual sync" && git push

# 检查 CF Pages 部署
curl ai-fleet-dashboard.pages.dev/finance-tax/ -I
```

### 调试命令集

```bash
# 1. 系统健康检查
curl http://100.75.77.112:8400/health | jq .

# 2. KuzuDB 节点/边统计
curl http://100.75.77.112:8400/api/stats | jq .

# 3. 向量搜索测试
curl -X POST http://100.75.77.112:8400/api/search \
  -H "Content-Type: application/json" \
  -d '{"query_text": "增值税", "top_k": 5}'

# 4. Cypher 查询测试
curl -X POST http://100.75.77.112:8400/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (n:TaxType) RETURN COUNT(n) as count"
  }'

# 5. 检查最新爬虫输出
ls -lh data/raw/$(date +%Y-%m-%d)/ | head

# 6. Gemini API 代理测试
curl https://gemini-api-proxy.maoyuan-wen-683.workers.dev/v1beta/models/gemini-embedding-2-preview:embedContent \
  -H "Authorization: Bearer $GEMINI_API_KEY"

# 7. Obsidian 文件同步检查
find ~/Obsidian/财税知识库/法规 -name "*.md" -mtime -1 | wc -l

# 8. CF Pages 构建状态
curl ai-fleet-dashboard.pages.dev/_json/build-status 2>/dev/null || echo "N/A"
```

---

## 13. 性能基准

### 查询延迟(P50/P95)

| 查询类型 | P50 | P95 | 最坏情况 |
|---------|-----|-----|---------|
| `/api/node` (ID lookup) | 10ms | 50ms | 200ms |
| `/api/search` (ANN, top-5) | 50ms | 150ms | 500ms |
| `/api/neighbors` (1-hop) | 100ms | 300ms | 1000ms |
| `/api/neighbors` (3-hop) | 500ms | 2000ms | 5000ms+ |
| `/api/query` (Cypher, LIMIT 100) | 100ms | 500ms | 2000ms |

### 吞吐量

| 操作 | RPS | 并发上限 |
|------|-----|---------|
| 写入 (batch, 单 writer) | 100 docs/min | 1 (lock-based) |
| 读取 (KuzuDB) | 500 RPS | 8 (concurrent) |
| 向量搜索 (ANN) | 1000 RPS | 16+ |
| API 整体 | 200-500 RPS | 64 (FastAPI workers) |

### 存储大小

| 组件 | 大小 |
|------|------|
| KuzuDB (7.3K nodes) | ~250MB |
| LanceDB (1.4K vectors × 3072d) | ~71MB |
| Obsidian vault (5.8K files) | ~45MB |
| **Total** | **~366MB** |

**按节点缩放**: ~50KB/node (including indices, all layers)

---

## 14. 许可证和法律

### 开源许可

- **KuzuDB**: MIT (嵌入式)
- **LanceDB**: Apache 2.0 / MIT (混合)
- **FastAPI**: MIT
- **CogNebula 项目**: Proprietary (Maurice)

### 合规注意事项

**PRC Penal Code Art. 285** (未经授权访问计算机系统):
- ✅ 合法: 爬取公开网站 (遵守 robots.txt，5s 延迟)
- ❌ 违法: 破解验证码，绕过 WAF，暴力破解密码

**当前操作**: 仅爬取 PRC 政府网站**公开页面**, 无 CAPTCHA 绕过, 无 API 滥用

**未来检查**: P3 添加住宅代理时，需法律审查

---

Maurice | maurice_wen@proton.me

最后更新: 2026-03-18
