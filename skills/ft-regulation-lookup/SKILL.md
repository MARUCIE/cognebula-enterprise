---
name: ft-regulation-lookup
description: "Use when: looking up specific tax regulations, legal clauses, compliance rules, tax rates from the knowledge graph. Trigger: 法规查询, 条款, 税率查询, 政策依据, 法律条文. NOT for: interpretation or planning, just lookup."
version: 1.0.0
---

# 法规查询工具

KG MCP tool 的消费者。教模型何时查询知识图谱、如何构造查询、怎样解读返回结果。不做法规解读或税务筹划，只负责精准检索并返回结构化法规数据。

## Core Knowledge

### KG API Endpoints

| 端点 | 方法 | 用途 | 适用场景 |
|---|---|---|---|
| `/search?q=关键词` | GET | 语义搜索 | 模糊查询，不确定法规名称时 |
| `/graph?table=节点类型&id_value=ID` | GET | 节点展开 | 已知具体节点，查看关联 |
| `/nodes?type=节点类型` | GET | 按类型浏览 | 浏览某类所有节点(如所有税率) |
| `/chat` | POST | RAG 问答 | 复杂问题，需要上下文理解 |

### 18种本体节点类型

| 类型 | 说明 | 示例 |
|---|---|---|
| LegalDocument | 法律文件(法/条例/规章/公告) | 企业所得税法、财税[2019]13号 |
| LegalClause | 法规条款(具体条/款/项) | 企业所得税法第二十八条 |
| TaxRate | 税率(含适用条件) | 增值税13%/9%/6%/3% |
| ComplianceRule | 合规规则(操作要求) | 进项发票无认证期限限制(2020年起取消) |
| TaxType | 税种 | 增值税/企业所得税/个人所得税 |
| TaxIncentive | 税收优惠(减免/抵扣/退税) | 小微企业所得税优惠 |
| FilingRequirement | 申报要求(表单/期限/条件) | 月度增值税申报 |
| PenaltyRule | 罚则(滞纳金/罚款/刑责) | 偷税罚款50%-500% |
| AccountingStandard | 会计准则 | 企业会计准则第14号-收入 |
| IndustryRegulation | 行业特殊规定 | 建筑业预缴增值税 |
| ThresholdValue | 门槛值/限额 | 小规模纳税人年销售额500万 |
| TimePeriod | 时间周期(征期/有效期) | 征期每月1-15日 |
| GovernmentAgency | 政府机构 | 国家税务总局/财政部 |
| TaxpayerCategory | 纳税人分类 | 一般纳税人/小规模纳税人 |
| GeographicScope | 地域范围 | 全国/特定区域(海南自贸港) |
| FormTemplate | 申报表模板 | A100000企业所得税年度申报表 |
| RiskIndicator | 风险指标 | 税负率异常/进销比异常 |
| BusinessScenario | 业务场景 | 固定资产处置/股权转让 |

### 查询模板

**按税种查询：**
```
/search?q=增值税&table_filter=TaxRate
/search?q=企业所得税优惠&table_filter=TaxIncentive
```

**按法规名查询：**
```
/search?q=财税[2019]13号
/graph?table=LegalDocument&id_value=<doc_id>  (展开条款)
```

**按关键词查询：**
```
/search?q=研发费用加计扣除
/search?q=小微企业标准
```

**按时间范围查询：**
```
/search?q=2024年新政策&table_filter=LegalDocument
```

**查看关联关系：**
```
/graph?table=LegalClause&id_value=<clause_id>
# 返回: BELONGS_TO(法规) + REFERENCES(引用的其他条款) + SUPERSEDED_BY(被替代)
```

### 返回值关键字段

| 字段 | 含义 | 注意事项 |
|---|---|---|
| `status` | 生效状态(active/superseded/repealed) | 必须检查，废止法规不可引用 |
| `effectiveDate` | 生效日期 | 部分法规有延迟生效 |
| `expiryDate` | 失效日期(如有) | null 表示长期有效 |
| `supersededBy` | 被哪个新法规替代 | 通过 SUPERSEDES 边查找最新版 |
| `confidence` | 语义搜索置信度(0-1) | < 0.7 建议换关键词重新搜索 |
| `sourceDocument` | 原始法规文号 | 用于最终引用标注 |

## Decision Framework

| 需求 | 用哪个端点 | 为什么 |
|---|---|---|
| "增值税税率是多少" | `/nodes?type=TaxRate` + 过滤增值税 | 已知节点类型，直接浏览 |
| "研发费用怎么扣除" | `/search?q=研发费用加计扣除` | 不确定具体法规，语义搜索 |
| "这个法规条款引用了哪些其他条款" | `/graph?table=LegalClause&id_value=...` | 已知具体节点，查关联 |
| "小微企业最新优惠政策有哪些" | `/chat` POST | 需要跨多个节点综合回答 |
| "财税[2019]13号说了什么" | `/search?q=财税[2019]13号` | 按文号精确查找 |
| "建筑业有哪些特殊税务规定" | `/search?q=建筑业&table_filter=IndustryRegulation` | 按行业+类型过滤 |

## Gotchas

1. **KG 搜索是向量语义搜索，不是关键词精确匹配** -- `/search` 端点使用 embedding 向量做相似度搜索。"增值税优惠"和"VAT incentive"能匹配到同一结果。但这也意味着搜索结果可能包含语义相近但实际不相关的内容。置信度 < 0.7 的结果要人工复核。

2. **法规可能已废止，查到后必须检查 status 和 effectiveDate** -- KG 中保留了已废止的法规(status=repealed/superseded)用于历史追溯。如果直接引用一个已废止的法规给客户，后果严重。每次查询结果返回后，第一步检查 status 字段。

3. **同一法规可能有多个版本** -- 企业所得税法从2008年到现在经过多次修订。通过 SUPERSEDES 边可以找到版本链。始终引用最新生效版本。如果查到的法规有 supersededBy 字段非空，必须沿链查到最终版本。

4. **KG 中有 514K 节点，不加过滤的查询很慢** -- 使用 `table_filter` 参数缩小搜索范围。不要直接 `/search?q=税` 这种过于宽泛的查询。好的查询：具体税种+具体事项+节点类型过滤。

5. **法规查询和法规解读是两个不同的技能** -- ft-regulation-lookup 只负责"找到正确的法规条文并返回"。如果用户需要"这个法规对我的企业意味着什么"，那是 ft-tax-advisor 或 ft-compliance-auditor 的工作。不要在查询结果上叠加解读。

6. **地方性法规和全国性法规混在一起** -- KG 中包含地方税务局的公告和规范性文件。查询结果需要检查 GeographicScope 字段，确认该法规是否适用于客户所在地区。上海的地方政策不适用于北京的企业。

7. **文号格式不统一导致搜索失败** -- "财税〔2019〕13号"和"财税[2019]13号"是同一个文件，但方括号/六角括号不同。搜索时用语义搜索(不依赖精确匹配)或同时尝试两种格式。

## When to Escalate

- 查询结果为空且换了3种以上关键词仍无结果：可能 KG 中未收录该法规，需要人工补充
- 查到的法规之间存在矛盾(同一事项不同规定)：需要 ft-tax-advisor 判断适用优先级
- 客户要求出具正式的政策依据文件：需要人工复核法规引用的准确性和完整性
- 涉及尚未入库的最新政策(刚发布的公告)：KG 更新有延迟，需要直接查税务总局官网
