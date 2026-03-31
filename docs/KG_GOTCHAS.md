# KG 开发坑点清单 (Gotchas)

> 来自 v4.1→v4.2 本体扩展的实战教训。每条都对应一次真实踩坑。

---

## 1. API 白名单陷阱 — 数据入库了但用户看不到

**现象**: DDL 建表 + seed 脚本灌数据都成功了，`/api/v1/stats` 显示节点数正确，但前端图谱完全看不到新类型。

**根因**: `kg-api-server.py` 的 constellation、search、edge 扫描全部使用**硬编码白名单** (`TYPES`, `SEARCH_TABLES`, `ALL_EDGE_TABLES`)，不是动态发现。新类型入库后如果不手动加到这三个列表，API 永远不会返回它们。

**检查点（每次加新类型必做）**:
1. `TYPES` — constellation 端点的 `(table, sample_limit, node_size, label_field)` 元组列表
2. `SEARCH_TABLES` — search 端点的搜索范围
3. `ALL_EDGE_TABLES` — constellation 扫描的边类型列表
4. `INTERNAL_EDGES` — constellation_by_type 的自引用边列表
5. **前端 `kg-api.ts`** — `LAYER_GROUPS`, `NODE_COLORS`, `EDGE_LABELS_ZH`, `FIELD_ZH`

**教训**: 前端可以提前注册（不影响功能），但 API server 漏注册 = 数据对用户完全不可见。这是最容易遗漏的一环。

---

## 2. Seed 脚本注释与实际数据不一致

**现象**: `seed_v42_phase3.py` 文件头注释写"ResponseStrategy: 40 条, PolicyChange: 30 条"，但实际 Python 列表只定义了 17 条和 11 条。

**根因**: 注释写的是设计目标数量，实际编码时只写了核心数据就提交了，注释未同步更新。

**规则**: seed 脚本的文件头注释必须反映实际数据量，不能写设计目标。目标数量放到 ontology design doc 里。

---

## 3. KuzuDB ALTER 列不能在 CREATE 中使用

**现象**: ALTER TABLE 新增的列（如 `fullText`, `description`）不能在 `CREATE (n:Type {fullText: '...'})` 中直接赋值，会报语法错误。

**解法**: 分两步：先 `CREATE` 只写初始列，再 `MATCH + SET` 补充 ALTER 列的值。

**代码模式**:
```python
# Step 1: CREATE with original columns only
create_stmts.append(f"CREATE (n:Type {{id: '{id}', name: '{name}'}})")
# Step 2: SET alter-added columns
set_stmts.append(f"MATCH (n:Type) WHERE n.id = '{id}' SET n.fullText = '{text}'")
```

---

## 4. VPS 部署必须清 __pycache__

**现象**: 更新 `kg-api-server.py` 后 scp 到 VPS 重启 uvicorn，但行为没变。

**根因**: Python 缓存了旧的 `.pyc` 文件。

**规则**: 每次 scp 后、restart 前必须 `rm -rf __pycache__`。

**完整重启命令**:
```bash
ssh root@VPS "fuser -k 8400/tcp; sleep 2; rm -rf /home/kg/cognebula-enterprise/__pycache__; cd /home/kg/cognebula-enterprise && nohup sudo -u kg /home/kg/kg-env/bin/python3 -m uvicorn kg-api-server:app --host 0.0.0.0 --port 8400 --workers 1 > /home/kg/kg-api.log 2>&1 &"
```

---

## 5. Constellation 返回中混入邻居节点

**现象**: 查 `constellation/type?type=ResponseStrategy` 返回 32 个节点，但实际 RS_* 只有 17 个，其余 15 个是 RI_* (RiskIndicator)。

**根因**: constellation_by_type 端点会沿边探索邻居节点。RESPONDS_TO 边连接 ResponseStrategy→RiskIndicator，所以 RiskIndicator 节点也被返回了。

**注意**: 不能直接用 constellation 端点的节点数量等同于该类型的实际数据量。要用 `/api/v1/stats` 的 `nodes_by_type` 字段。

---

## 6. FilingFormField 设计了但从未 seed

**现象**: 本体设计文档列了 FilingFormField 300-500 条，DDL 建表成功，前端注册了颜色和图层，但数据量为 0。

**根因**: Phase 1 seed 脚本 (`seed_v42_phase1.py`) 专注于 JournalEntryTemplate / FinancialStatementItem 等高优先级类型，FilingFormField 需要爬取实际申报表栏次数据，复杂度高，被跳过了。HANDOFF 中 `HAS_ENTRY_TEMPLATE: 0 (deferred)` 已有说明但容易遗漏。

**状态**: 待补。需要从增值税一般纳税人主表/附表、企业所得税年度申报表等结构化来源提取。

---

## 7. 前端超前注册不会报错但会造成空图层

**现象**: 前端 `kg-api.ts` 的 LAYER_GROUPS 包含了全部 35 类型，但其中部分类型（如 FilingFormField）在 DB 中无数据。图层面板显示该类型但点击后无节点。

**影响**: 用户可能认为功能异常。

**建议**: 对空数据类型在 UI 上标注"待填充"或灰显处理，而不是直接隐藏（隐藏会让人以为没实现）。

---

## 8. seed 脚本非幂等 — 重跑会报重复 ID

**现象**: `seed_v42_phase3.py` 使用 `CREATE` 语句，重跑会因为 ID 重复报错。

**根因**: KuzuDB 的 `CREATE` 不支持 `ON CONFLICT` / `MERGE` 语义。

**解法**: seed 脚本应先查询已有 ID，过滤掉已存在的再 CREATE。或者在脚本头部加 `MATCH (n:Type) WHERE n.id IN [...] DELETE n` 清理后重建。

---

## 9. V1/V2 表与边表绑定冲突

**现象**: `RULE_FOR_TAX` 边表绑定的 FROM 类型是 `ComplianceRuleV2`，不是 `ComplianceRule`。新数据写入 `ComplianceRule` 后，尝试创建边到 `TaxType` 报 "Expected labels are ComplianceRuleV2"。

**根因**: 数据库中同时存在 V1 和 V2 版本的表（列完全不同: CR 25列 vs CRV2 15列）。边表 DDL 用的是 `FROM ComplianceRuleV2`，所以只有 V2 表的节点能参与这些边。

**短期解法（已采用）**: 将 75 条新 ComplianceRule 也镜像写入 ComplianceRuleV2（只填共有列），然后从 CRV2 出发建边。两张表保持 ID 同步。

**长期解法**: 合并 V1/V2 为统一表。但列差异大（10 列仅在 CR 有、5 列仅在 CRV2 有），需要 ALTER 补列 + 数据迁移 + 边重建，停机风险高。

**规则**: 新建边表时检查 FROM/TO 绑定的是哪个版本的表。写入新数据后如需建边，先确认边表的 FROM 约束。

---

## 10. Penalty 表没有 fullText 列

**现象**: 对 Penalty 节点 SET fullText 报 "Cannot find property fullText"，但 ALTER TABLE ADD fullText 返回 SKIP。

**根因**: ALTER SKIP 可能是因为 DDL endpoint 误判，实际上该列从未添加成功。Penalty 表的列集合与 ComplianceRule 不同。

**解法**: Penalty 的 `description` 列已经存放了足够内容，不需要 fullText。如确需添加，用 VPS Python 直连 KuzuDB 执行 ALTER（绕过 API DDL endpoint 的限制）。

---

## 11. DDL 建表 SKIP 不等于列完整

**现象**: `CREATE NODE TABLE FilingFormField (id, name, ..., formCode, ...)` 被 API 返回 `SKIP (exists)`，但后续 CREATE 节点时报 `Cannot find property formCode`。

**根因**: 表之前已被另一个 DDL 以较少列创建过。KuzuDB DDL 端点对已存在的表返回 SKIP 而非合并列。新 CREATE 语句中的额外列被静默忽略。

**解法**: 用 `ALTER TABLE xxx ADD column STRING DEFAULT ''` 逐列补齐。已存在的列会报错，可忽略。然后用 MATCH+SET 写入 ALTER 列的值。

**防御**: 建表前先查 `table_info` 确认列集合。如果 table_info 不可用（如 API DDL 端点限制），用 CREATE 一条测试节点来探测可用列。

---

## 12. SEARCH_FIELDS 必须与 KuzuDB 实际列名精确匹配

**现象**: LegalDocument 搜索"增值税"返回 0 结果，但数据库里有 3,580 条匹配。

**根因**: `SEARCH_FIELDS` 定义了 `["name", "title", "fullText"]`，但 LegalDocument 表没有 `title` 列。KuzuDB 在 Binder 阶段（不是运行时）检查列是否存在，`IS NOT NULL` 保护无效——整个 WHERE 子句因为引用了不存在的列而编译失败。

**解法**: 每个表的搜索字段必须来自实际 `table_info` 或 API `/nodes?limit=1` 返回的列集合。不能假设所有表都有 `name`/`title`/`fullText`。

**验证方法**: `curl API/nodes?type=X&limit=1&q=关键词` 检查 `total` 字段是否 >0。

---

## Checklist: 新增节点类型发布前检查

```
[ ] DDL: CREATE TABLE 成功
[ ] Seed: 数据灌入，/api/v1/stats 确认 count > 0
[ ] API TYPES: constellation 白名单已加
[ ] API SEARCH_TABLES: 搜索范围已加
[ ] API ALL_EDGE_TABLES: 相关边已加
[ ] API INTERNAL_EDGES: 如有自引用边则加入
[ ] Frontend LAYER_GROUPS: 已注册到正确图层
[ ] Frontend NODE_COLORS: 已分配颜色
[ ] Frontend EDGE_LABELS_ZH: 新边中文标签已加
[ ] Frontend FIELD_ZH: 属性中文标签已加
[ ] VPS: scp + rm __pycache__ + restart
[ ] 验证: constellation 能看到 + search 能搜到
```
