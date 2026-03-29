# 场景：意图分类示例库——50个真实问题到路由结果

**政策依据**：基于CogNebula Enterprise财税知识图谱的意图路由引擎设计

## 第一步：理解意图分类框架

team-finance-tax作为财税路由器，将用户问题分类到正确的专家技能。分类维度：
- **税种维度**：增值税/企业所得税/个税/印花税/房产税/关税/消费税/土增税等
- **业务维度**：记账/报表/合并/审计/转让定价/补贴/外汇等
- **紧急程度**：日常咨询/月度申报/年度汇算/突发合规问题

## 第二步：增值税与所得税类（路由到ft-vat-specialist/ft-corporate-tax）

1. "进项发票认证期限是多久" → ft-vat-specialist
2. "简易计征和一般计税怎么选" → ft-vat-specialist
3. "出口退税率查询" → ft-export-tax-rebate
4. "研发费用加计扣除比例是多少" → ft-corporate-tax
5. "固定资产一次性扣除500万限额还有吗" → ft-corporate-tax
6. "小规模纳税人季度30万免征增值税" → ft-vat-specialist
7. "高新技术企业优惠税率15%的条件" → ft-corporate-tax
8. "留抵退税怎么申请" → ft-vat-specialist
9. "企业所得税季度预缴怎么算" → ft-corporate-tax
10. "技术转让所得免征企业所得税500万怎么理解" → ft-corporate-tax

## 第三步：个税/社保/薪酬类（路由到ft-individual-tax/ft-social-insurance）

11. "年终奖单独计税还是并入综合所得" → ft-individual-tax
12. "股权激励怎么缴个税" → ft-individual-tax
13. "外籍员工个税优惠政策" → ft-individual-tax
14. "社保缴费基数怎么确定" → ft-social-insurance
15. "公积金缴存比例上下限" → ft-social-insurance
16. "劳务报酬预扣税率表" → ft-individual-tax
17. "个税专项附加扣除标准2024" → ft-individual-tax
18. "员工离职经济补偿金免税额度" → ft-individual-tax
19. "实习生要不要交社保" → ft-social-insurance
20. "残疾人就业保障金怎么计算" → ft-social-insurance

## 第四步：专业领域类（路由到对应专家skill）

21. "合并报表内部交易怎么抵消" → ft-consolidation
22. "境外子公司报表怎么折算" → ft-fx-accounting
23. "关联方借款利息能不能扣除" → ft-transfer-pricing
24. "高新技术企业补贴怎么申请" → ft-subsidy-application
25. "印花税新法哪些合同要交" → ft-stamp-property-tax
26. "进口关税完税价格怎么算" → ft-customs-duty
27. "内部审计发现了职责分离问题" → ft-internal-audit
28. "审计报告什么时候出保留意见" → team-audit
29. "房产税从价还是从租" → ft-stamp-property-tax
30. "转让定价同期资料什么时候准备" → ft-transfer-pricing
31. "政府补助总额法和净额法怎么选" → ft-subsidy-application
32. "HS编码归类有争议怎么办" → ft-customs-duty
33. "外币交易初始确认用什么汇率" → ft-fx-accounting
34. "商誉减值测试怎么做" → ft-consolidation
35. "来料加工和进料加工税务区别" → ft-customs-duty
36. "环保税怎么计算" → ft-stamp-property-tax
37. "土增税清算条件" → ft-stamp-property-tax
38. "预约定价安排值不值得申请" → ft-transfer-pricing
39. "专精特新认定条件" → ft-subsidy-application
40. "管理层凌驾内控怎么审" → ft-internal-audit
41. "成本会计差异分析" → ft-cost-accounting
42. "新开公司注册流程" → ft-business-registration
43. "财务报表怎么编制" → ft-financial-statement
44. "经营风险评估矩阵" → ft-risk-assessment
45. "合规检查清单" → ft-compliance-checklist
46. "数字资产怎么入账" → ft-digital-asset-tax
47. "出口退税申报操作" → ft-export-tax-rebate
48. "征期日历这个月有什么要报的" → ft-period-calendar
49. "法律合规意见" → ft-legal-counsel
50. "发票管理规范" → ft-invoice-manager
