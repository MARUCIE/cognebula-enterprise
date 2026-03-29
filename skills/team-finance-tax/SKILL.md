---
name: team-finance-tax
description: "Router for finance/tax expert team. Use when: user asks about 财税/会计/税务/记账/申报/合规/社保/工商/发票/报表/征期/法规/税会差异/检查清单/注销/关联交易/转让定价/出口退税/税收优惠/坏账/更正申报/筹划/国际税/法务/成本/风险/补贴/印花税/房产税/关税/数字资产/审计. Trigger: 29 specialist skills (13 core + 7 advanced + 4 audit-team + 5 specialty). Routes to team-audit for internal audit/consolidation/FX/transfer pricing. NOT for: investment advice, status inquiries (query workflow system instead)."
version: 1.0.0
---

# 财税专家团路由器

意图分类 -> 专家分发 -> 协作编排 -> 结果综合。所有财税类问题的入口，根据用户意图路由到最合适的单一专家或编排多专家协作。简单事实类问题（如"增值税税率是多少"）路由器直接回答，不调用专家。

## Core Knowledge

### 意图-专家映射表

| 用户意图关键词 | 目标专家 | 说明 |
|---|---|---|
| 记账/凭证/科目/分录/结账/会计准则/账务处理/坏账/应收核销 | ft-accountant | 会计核算类 |
| 税种/税率/申报/纳税/增值税/企业所得税/个税/附加税/更正申报/补报/修正申报 | ft-tax-advisor | 税务申报类 |
| 社保/公积金/五险一金/社保基数/工伤/生育/残保金/灵活用工 | ft-social-insurance | 社保公积金类 |
| 工商/注册/营业执照/变更/年报/经营范围/股东变更 | ft-business-registration | 工商行政类(注销见跨领域) |
| 合规/风险/稽查/预警/金税四期/内控/质检/查账 | ft-compliance-auditor | 合规审计类 |
| 业务分析/经营场景/涉税事项/新客户接入/业务拆解/关联交易识别 | ft-business-analyst | 业务分析类(关联交易识别后触发 ft-compliance-auditor; 转让定价文档则路由 team-audit) |
| 发票/开票/认证/勾选/进项/销项/红冲/数电票/留抵退税 | ft-invoice-manager | 发票管理类 |
| 资产负债表/利润表/现金流量表/财务报表/财务分析/财务比率 | ft-financial-statement | 报表编制与分析类 |
| 征期/申报截止/纳税日历/延期/节假日顺延 | ft-period-calendar | 征期日历类 |
| 法规查询/条款/政策依据/法律条文/税率查询/税收优惠/减免政策/优惠政策 | ft-regulation-lookup | 法规检索类(优惠类同时触发 ft-tax-advisor 解读) |
| 合规清单/检查清单/月度检查/季度检查/年度检查 | ft-compliance-checklist | 合规清单生成类 |
| 税会差异/纳税调整/永久性差异/暂时性差异/汇算清缴调整/递延所得税 | ft-tax-accounting-gap | 税会差异分析类 |
| 出口退税/出口/外贸/退税申请 | ft-export-tax-rebate | 出口退税专项(免退/免抵退/退税率/单证) |
| 税务筹划/节税/组织架构优化/业务拆分/反避税 | ft-tax-planner | 事前税务筹划方案设计 |
| 跨境/非居民/税收协定/境外抵免/常设机构/BEPS | ft-international-tax | 国际税务专项 |
| 税务争议/行政复议/稽查应对/处罚/听证/涉税犯罪 | ft-legal-counsel | 涉税法律风险与争议解决 |
| 成本核算/制造费用/标准成本/存货计价/在产品/约当产量 | ft-cost-accounting | 产品成本核算与差异分析 |
| 高新认定/小微/研发加计/即征即退/加速折旧/优惠叠加 | ft-tax-incentive | 税收优惠政策适用与申报 |
| 风险评估/税负率/行业对标/异常检测/预警/稽查风险 | ft-risk-assessment | 税务合规风险量化评估 |
| 政府补贴/研发补助/专精特新/项目验收/财政资金 | ft-subsidy-application | 政府补贴申报与合规管理 |
| 印花税/房产税/土地使用税/契税/土地增值税/车船税/环保税 | ft-stamp-property-tax | 小税种计算与申报 |
| 关税/进口增值税/进口消费税/HS编码/保税区/加工贸易 | ft-customs-duty | 进出口环节关税消费税 |
| 数据资产入表/AI模型成本/碳交易/碳排放/ESG税务 | ft-digital-asset-tax | 数字资产与ESG税务新兴领域 |
| 内部审计/内控/舞弊/COSO/审计底稿 | team-audit → ft-internal-audit | 路由至审计团队 |
| 合并报表/抵消分录/少数股东/合并范围 | team-audit → ft-consolidation | 路由至审计团队 |
| 外币/汇率/汇兑损益/报表折算/功能货币 | team-audit → ft-fx-accounting | 路由至审计团队 |
| 转让定价/同期资料/APA/独立交易原则/特别纳税调整 | team-audit → ft-transfer-pricing | 路由至审计团队 |

#### 固有跨领域意图(单一关键词触发多专家)

| 关键词 | 主专家 | 辅助专家 | 原因 |
|---|---|---|---|
| 注销 | ft-business-registration | ft-tax-advisor(清税) + ft-social-insurance(社保注销) | 注销流程必须先税务清算后工商注销 |
| 关联交易/转让定价 | ft-business-analyst | ft-compliance-auditor(定价合规+同期资料) | 识别归业务分析，合规归审计 |
| 坏账/应收核销 | ft-accountant | ft-tax-accounting-gap(税前扣除条件) | 会计处理和税务处理规则不同 |
| 更正申报/补报 | ft-tax-advisor | ft-compliance-auditor(风险评估) | 更正程序归税务师，风险评估归审计 |
| 税收优惠/减免 | ft-regulation-lookup | ft-tax-advisor(资格判定+适用解读) | 先检索再解读 |
| 出口退税 | ft-export-tax-rebate | ft-invoice-manager(凭证归集) + ft-tax-advisor(申报) | 退税专家主导，发票+税务配合 |
| 税务筹划+跨境 | ft-tax-planner | ft-international-tax(跨境结构) | 境内筹划+境外合规 |
| 政府补贴+研发 | ft-subsidy-application | ft-tax-incentive(加计扣除) | 补贴申报+税收优惠叠加 |
| 风险预警+成本 | ft-risk-assessment | ft-cost-accounting(成本分析) | 异常检测+成本核实 |
| 进口+成本 | ft-customs-duty | ft-cost-accounting(进口成本入账) | 关税计算+成本核算 |

### 路由决策树

```
用户问题进入
  |
  +-- 意图不明确？（单个词如"增值税"、过于宽泛如"帮我做所有的事"）
  |     YES --> 追问澄清：请用户说明具体需求（是查税率？做申报？开发票？查法规？）
  |             不要猜测意图后直接执行，错误路由的返工成本远高于追问一次
  |
  +-- 状态查询？（"做完了吗"/"进度怎样"/"完成没有"）
  |     YES --> 查询任务管理/工作流系统状态，不调专家
  |             路由器返回当前任务进度，不是发起新任务
  |
  +-- 工具类查询（征期/清单/法规/报表模板）？
  |     YES --> 判断工具类型：
  |              征期/截止日 --> ft-period-calendar
  |              合规清单 --> ft-compliance-checklist --> 生成后交 ft-compliance-auditor 执行
  |              法规/条款/政策依据/税收优惠检索 --> ft-regulation-lookup
  |              报表编制/财务分析 --> ft-financial-statement
  |              税会差异/纳税调整 --> ft-tax-accounting-gap
  |
  +-- 事实查询（税率/比例/简单规则）？
  |     YES --> 路由器直接回答，不调专家
  |
  +-- 固有跨领域意图？（注销/关联交易/坏账/更正申报/税收优惠/出口退税）
  |     YES --> 按"固有跨领域意图"映射表，主专家 + 辅专家协作
  |
  +-- 单一领域问题？
  |     YES --> 匹配意图表，分发到单专家
  |
  +-- 跨领域问题（涉及2个专家）？
  |     YES --> 主专家处理 + 辅专家校验
  |
  +-- 复杂综合问题（3+专家）？
        YES --> 圆桌模式：业务分析师先拆解，各专家并行处理，路由器综合
```

### 协作协议

- 串行模式：业务分析师拆解 -> 会计师做账 -> 税务师核税 -> 合规审计师检查
- 并行模式：同一业务事件同时触发多个专家（如新员工入职同时触发社保+个税+会计）
- 圆桌模式：汇算清缴季(CIT 1-5月 + PIT 3-6月)专用，3+专家参与，路由器负责冲突仲裁
- 工具辅助：征期日历(ft-period-calendar)、法规查询(ft-regulation-lookup)、合规清单(ft-compliance-checklist)、报表编制(ft-financial-statement)、税会差异(ft-tax-accounting-gap)可被任何专家调用作为辅助工具

## Decision Framework

| 场景 | 路由策略 | 原因 |
|---|---|---|
| "增值税税率是多少" | 路由器直接答 | 事实查询，调专家浪费资源 |
| "这笔采购怎么做分录" | ft-accountant 单专家 | 纯会计问题 |
| "新注册的公司要交哪些税" | ft-business-registration + ft-tax-advisor | 工商完成后需要税种鉴定 |
| "帮我做这个月的税" | 拆分后多专家 | 至少涉及记账+申报+合规检查 |
| "年度汇算清缴" | 圆桌模式 | 会计+税务+合规+业务分析全参与 |
| "出一下这个月的财务报表" | ft-financial-statement | 报表编制单专家(数据来自 ft-accountant 结账结果) |
| "这个月什么时候申报截止" | ft-period-calendar | 征期查询，不需要其他专家 |
| "研发费用加计扣除的政策依据" | ft-regulation-lookup | 法规检索后可能需要 ft-tax-advisor 解读 |
| "新客户第一个月的检查清单" | ft-compliance-checklist -> ft-compliance-auditor | 先生成清单再执行检查 |
| "业务招待费的税会差异怎么处理" | ft-tax-accounting-gap | 汇算清缴调整专项 |
| "帮我做汇算清缴的纳税调整" | ft-tax-accounting-gap + ft-tax-advisor | 差异识别+申报填写协作 |
| "公司要注销了" | ft-business-registration + ft-tax-advisor + ft-social-insurance | 固有跨领域：工商注销+清税+社保注销 |
| "关联公司交易怎么定价" | ft-business-analyst + ft-compliance-auditor | 固有跨领域：交易识别+转让定价合规 |
| "出口退税怎么申请" | ft-tax-advisor + ft-invoice-manager | 固有跨领域：退税流程+凭证归集 |
| "有什么税收优惠" | ft-regulation-lookup + ft-tax-advisor | 先检索优惠政策再判定资格 |
| "客户欠款能不能做坏账" | ft-accountant + ft-tax-accounting-gap | 固有跨领域：会计核销+税前扣除条件 |
| "上个月申报有错，怎么更正" | ft-tax-advisor + ft-compliance-auditor | 固有跨领域：更正程序+风险评估 |
| "增值税"(单词无上下文) | 追问澄清 | 意图不明确，需要用户说明具体需求 |
| "这个月的账做完了吗" | 查询任务状态 | 状态查询，不调专家 |
| "帮我做转让定价同期资料" | team-audit → ft-transfer-pricing | 同期资料三层文档准备 |
| "公司要申请高新认定" | ft-tax-incentive | HNTE 8项条件判定+申报辅导 |
| "境外子公司分红要交多少税" | ft-international-tax | 非居民预提税+协定优惠+间接抵免 |
| "帮我算土地增值税" | ft-stamp-property-tax | 四级超率累进税率计算 |
| "研发补贴怎么入账" | ft-subsidy-application + ft-tax-accounting-gap | 补贴会计处理+税务影响 |
| "集团合并报表内部交易抵消" | team-audit → ft-consolidation | 五大类抵消分录 |
| "外币贷款汇兑损益" | team-audit → ft-fx-accounting | 货币性项目期末重估 |
| "进口原材料关税计算" | ft-customs-duty | 完税价格+关税+进口增值税 |
| "数据资产能不能入无形资产" | ft-digital-asset-tax | 数据资源入表条件判定 |
| "内审发现高管报销私人费用" | team-audit → ft-internal-audit + ft-legal-counsel | 舞弊识别+法律风险评估 |

## Gotchas

1. **不要把所有问题都转给税务师** -- 统计显示约50%的财税问题单专家可解决，过度协作反而降低效率和一致性。先判断复杂度再决定调几个专家。

2. **"帮我做这个月的税"需要拆分成5+个子任务** -- 用户说的"做税"实际包含：凭证检查、账务调整、税金计提、申报表填写、申报提交。不拆分直接扔给税务师会导致遗漏前置步骤。

3. **客户用自然语言不用税务术语** -- "这笔钱能不能报销"="费用扣除判定"，"老板从公司拿钱"="股东借款/分红"，"给员工发福利"="职工薪酬/福利费"。路由器必须做语义映射，不能只匹配关键词。

4. **简单问题路由器直接答，不调专家** -- 税率查询、申报截止日期、社保比例这类事实性问题，路由器自己回答。调专家增加延迟且不增加准确性。

5. **汇算清缴季(CIT 1-5月 + PIT 3-6月)是唯一需要3+专家协作的常规场景** -- 其他场景即使看起来复杂，通常1-2个专家足够。过度启动圆桌模式是资源浪费。

6. **注销/关联交易/坏账/更正申报/出口退税/税收优惠是固有跨领域意图** -- 这6类问题看起来像单领域，但天然需要2+专家协作。不要因为用户只说了一个关键词就路由到单专家。例如"公司要注销"不只是工商手续，还必须清税+注销社保。已在"固有跨领域意图"映射表中列出。

7. **单个关键词或过于宽泛的请求必须追问，不能猜测路由** -- "增值税"可能是问税率、做申报、查发票、看法规。猜错了路由的返工成本远高于追问一次。判断标准：如果同一个关键词能匹配意图表中2个以上专家，且没有额外上下文消歧，就追问。

8. **状态查询不是任务请求，不要调专家** -- "做完了吗""进度怎样"是在问工作流状态，不是在提出新的财税问题。路由器应查询任务管理系统返回进度，不是把"做完了吗"转给会计师。

## When to Escalate

- 涉及复杂跨境并购重组税务架构：ft-international-tax 初步评估后需要外部税务师事务所+律所联合
- 涉及刑事案件（虚开/骗税已移送司法）：ft-legal-counsel 评估后需要外部刑事辩护律师
- 涉及投资理财建议（资产配置、基金推荐）：不是财税范畴
- 客户提供的信息严重不足，无法判断业务实质：要求补充原始凭证/合同
- 涉及金额超过500万的单笔税务处理：高风险，需要人工复核
