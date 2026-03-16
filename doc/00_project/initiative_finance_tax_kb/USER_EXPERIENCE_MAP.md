# CogNebula Finance/Tax Knowledge Base -- User Experience Map

> v1.1 | 2026-03-15 | Initiative: finance_tax_kb
> v1.1 change: Updated metrics (7,295 nodes, 11 sources, 1,438 vectors, 5,781+ Obsidian files)

## 1. User Personas

### P1: AI Agent (OpenClaw)
- **Context**: Autonomous agent handling compliance reasoning tasks
- **Goal**: Get structured, accurate finance/tax context within token budget
- **Interaction**: MCP tools (programmatic, zero UI)
- **Pain**: Hallucination on tax rules without grounded context

### P2: Tax Compliance Officer (秦税安 Expert Persona)
- **Context**: Needs daily monitoring of regulatory changes
- **Goal**: Never miss a policy update, understand impact quickly
- **Interaction**: Telegram digest (morning) + CF Pages dashboard
- **Pain**: Manual scanning of 10+ government websites daily

### P3: Product Manager (Maurice)
- **Context**: Building compliance products, needs knowledge base as infrastructure
- **Goal**: Reliable, queryable, up-to-date finance/tax knowledge graph
- **Interaction**: CLI + API + Dashboard
- **Pain**: No structured data source for Chinese tax domain

## 2. Journey Maps

### Journey A: AI Agent Tax Query

```
Trigger: User asks OpenClaw "软件企业增值税优惠政策有哪些？"
    |
    v
1. OpenClaw routes to CogNebula MCP tool: tax_query
    |
    v
2. CogNebula Hybrid RAG:
   a. LanceDB semantic search -> top-5 relevant docs
   b. KuzuDB graph traversal -> Policy -> TaxType -> Industry chain
   c. Tiered context assembly (4K token budget)
    |
    v
3. Return structured markdown:
   - Applicable policies (with effective dates)
   - Tax rates + exemption conditions
   - Relevant clauses (full text)
   - Case precedents (if any)
    |
    v
4. OpenClaw synthesizes answer for user
    |
    v
5. User receives: grounded, citation-backed tax guidance
```

**Quality Gates:**
- Precision@5 >= 85% (relevant results in top 5)
- Response time < 3s (MCP round-trip)
- Token budget adherence: context <= 4K tokens

### Journey B: Daily Regulatory Monitoring

```
Dual-batch cron (10:00 + 15:00 UTC) triggers finance-tax-crawl.sh (7-stage pipeline)
    |
    v
1. AI-Fleet skill fetchers crawl 11 active sources (sequential, 5s polite delay)
   - chinatax.gov.cn: 132 items (non-SPA fallback)
   - chinatax FGK API: 57,073 records (JSON API, paginated)
   - mof.gov.cn: 50 items (regex parser)
   - pbc.gov.cn: 10 items (条法司)
   - safe.gov.cn: 60 items (外汇管理局, 3 sections)
   - csrc.gov.cn: 177 items (证监会, 3 sections)
   - ndrc.gov.cn: 592 items (发改委)
   - casc.ac.cn: 53 items (中科院)
   - stats.gov.cn: 30 items (统计局)
   - baike.kuaiji.com: 17K entries (accounting wiki, running)
    |
    v
2. Change detection (per source):
   - Hash comparison: any binary change?
   - If changed: unified_diff -> identify sections
   - If significant: embedding similarity < 0.95
    |
    v
3. New/changed content processed:
   - Trafilatura text extraction
   - Rule-based NER (regulation codes, dates, rates)
   - KuzuDB node upsert + edge creation
   - LanceDB embedding generation
    |
    v
4. Alert dispatch:
   - Telegram: "NOTE: 3 new policies detected"
     - Policy A: [title] (effective: YYYY-MM-DD)
     - Policy B: [title] (amends: [old policy])
     - Policy C: [title] (industry: software)
    |
    v
5. CF Pages dashboard updated:
   - Timeline view: all changes this week
   - Impact analysis: affected industries/tax types
   - Full text with diff highlighting
```

**Quality Gates:**
- Crawl completion: all 11 active sources checked (target 15+)
- Change detection latency: < 24h from publication
- Alert delivery: within 30 min of detection
- Zero false negatives on Tier-1 source changes

### Journey C: Compliance Check Workflow

```
Trigger: User asks "我们公司是杭州的软件企业，今年要缴哪些税？"
    |
    v
1. OpenClaw parses intent:
   - Jurisdiction: 杭州市 (浙江省)
   - Industry: 软件 (GB 65)
   - TaxpayerType: 企业 (一般纳税人 assumed)
   - Time: 2026 current
    |
    v
2. MCP tool: compliance_check
   Input: {industry: "软件", jurisdiction: "杭州", taxpayer: "一般纳税人", year: 2026}
    |
    v
3. Graph traversal:
   a. Jurisdiction(杭州) -> parent -> Jurisdiction(浙江) -> parent -> Jurisdiction(国家)
   b. At each level: GOVERNS -> Regulations
   c. Filter: status=active, effective_date <= 2026-03-14
   d. Industry(软件): APPLIES_TO <- TaxType(*)
   e. TaxpayerType(一般纳税人): SCOPED_TO <- Policy(*)
    |
    v
4. Assemble compliance checklist:
   - 增值税: 6% (软件服务) / 13% (软件产品)
     - 优惠: 即征即退 (超3%部分)
   - 企业所得税: 25% (标准) / 15% (高新技术)
   - 附加税: 城建税 + 教育费附加
   - 印花税: 合同类
   - Jurisdiction-specific: 浙江省地方优惠
    |
    v
5. Return with citations: [法规编号] + [条款号] + [有效期]
```

### Journey D: Expert Digest Production

```
Schedule: Daily 09:30 CST (via existing expert team pipeline)
    |
    v
1. Expert 秦税安 (UC-81~90) activated:
   - web_search: latest tax policy changes
   - CogNebula MCP: change_monitor(last_24h)
   - Combine: web freshness + graph depth
    |
    v
2. Generate analysis:
   - 3-5 key updates with impact assessment
   - Risk signals (upcoming deadlines, expiring policies)
   - Action items for compliance team
    |
    v
3. Delivery pipeline (reuse existing):
   - HTML poster (800x1120, Bloomberg style)
   - Playwright screenshot
   - Telegram push (screenshot + 3-line TLDR)
   - CF Pages: ai-fleet-dashboard.pages.dev/finance-tax-digest-YYYY-MM-DD.html
```

## 3. Touchpoint Matrix

| Touchpoint | User | Channel | Frequency | Content |
|-----------|------|---------|-----------|---------|
| MCP tax_query | AI Agent | stdio | On-demand | Structured context |
| MCP compliance_check | AI Agent | stdio | On-demand | Compliance checklist |
| MCP change_monitor | AI Agent / Expert | stdio | Daily | Change summary |
| Telegram alert | Compliance Officer | Telegram | On change | New policy notification |
| Expert digest | All users | Telegram + CF Pages | Daily 09:30 | Analysis + TLDR |
| Dashboard | Product Manager | Browser | On-demand | Timeline + impact view |
| CLI query | Developer | Terminal | On-demand | Raw Cypher / search |

## 4. Error States & Recovery

| Error | User Impact | Recovery |
|-------|-----------|----------|
| Crawler blocked by gov site | Stale data (no update) | Retry with different UA; alert after 3 failures |
| KuzuDB query timeout | Slow MCP response | Cache frequent queries; timeout at 10s with partial result |
| Embedding API unavailable | No semantic search | Fallback to KuzuDB text search (query_symbols) |
| PDF OCR failure | Missing document content | Queue for manual review; flag in graph as `ocr_failed` |
| Change detection false positive | Unnecessary alert | Include confidence score in alert; threshold at 0.95 |

## 5. Information Architecture

```
Dashboard (CF Pages)
  ├── /finance-tax/                    # Landing page
  │   ├── /timeline                    # Chronological policy updates
  │   ├── /by-tax-type                 # Browse by 增值税/所得税/...
  │   ├── /by-jurisdiction             # Browse by 国家/省/市
  │   └── /search                      # Full-text + graph search
  ├── /finance-tax-digest-{date}.html  # Daily expert digest
  └── /finance-tax-report-{date}.html  # Weekly summary report
```

---

Maurice | maurice_wen@proton.me
