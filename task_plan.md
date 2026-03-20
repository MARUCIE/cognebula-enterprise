# Task Plan: CogNebula KG 数据质量修复 + 门禁标准

## Goal
修复图谱 5 大质量问题（空标题/编码标签/稀疏连通性/无语义边/可视化重叠），并建立入库门禁确保未来数据质量。

## Current Phase
Day 3 执行中 — APPLIES_TO_CLASS 边创建进行中 (5/次, 1.5s间隔, ~9K目标)

## Phases

### Phase 1: API 层修复 — 标签显示 + 序列化
- [x] 1.1 修复 `_serialize()` 处理 KuzuDB 内部类型（offset tuple → 人类可读）
- [x] 1.2 修复 `/api/sample` 标签回退逻辑：7 字段优先级链
- [x] 1.3 为 TaxRateMapping 添加中文标签映射表 (TRM_LABELS)
- [x] 1.4 添加 `/api/v1/quality` 审计端点
- [x] 1.5 `_get_node_label()` 支持 node_text/topic/item_name/productCategory 等非标准字段
- [x] 1.6 `/api/v1/nodes` 注入 `_display_label` 动态标签

### Phase 2: Ingest 门禁（Quality Gate）
- [x] 2.1 强化 `/api/v1/ingest` 验证：5 项门禁 (id/title/content/raw_id_leak)
- [x] 2.2 创建 `scripts/kg_quality_gate.py` — CLI 批量校验
- [x] 2.3 门禁标准文档：`docs/KG_QUALITY_GATE.md`

### Phase 3: 数据修复
- [x] 3.1 `/api/v1/admin/fix-titles` — 服务端动态修复（受 WAL 限制改为查询层映射）
- [x] 3.2 `/api/v1/admin/enrich-edges` — 1,754 条 MENTIONS 边连接 16 个税种到内容节点
- [x] 3.3 创建离线修复脚本（fix_empty_titles.py/fix_trm_labels.py/enrich_tax_edges.py）

### Phase 4: 前端可视化优化
- [x] 4.1 `getNodeLabel()` JS 函数 — 7 字段回退 + TRM 解码 + hash 缩短
- [x] 4.2 所有节点渲染路径集成 getNodeLabel（loadNodes/expandNode/neighbors）

### Phase 5: 验证 + 部署
- [x] 5.1 本地语法检查全部通过
- [x] 5.2 推送到 kg-node + systemctl restart
- [x] 5.3 API 验证：Quality Score 46→78, Gate FAIL→PASS
- [ ] 5.4 前端截图验证（待用户打开浏览器）

## Key Questions
- KG API 当前 Connection Refused，需要先恢复服务才能执行 Phase 3/5

## Decisions Made
- 修复策略：先修显示层（API+前端），再修数据层，最后建门禁
- 所有修复脚本放在 scripts/ 下，可重复执行（幂等）
- 门禁标准：title 必填(≥5字) + content 必填(≥20字) + 边密度目标 ≥0.5 edges/node

## Errors Encountered
- (none yet)

## Notes
- 当前数据：155,783 nodes / 37,024 edges / 0.24 edges/node
- 主要节点：DocumentSection(42K), MindmapNode(28K), RegulationClause(28K), LawOrRegulation(26K)
- 主要边：CLAUSE_OF(28K) 占 76%，其余边类型都很少
