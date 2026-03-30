# HANDOFF.md -- CogNebula / Lingque Desktop

> Last updated: 2026-03-30T17:30Z

## Session 22 — KG Sigma + v4.2 Ontology Design (15 commits)

### Completed
1. **Sigma.js fix**: `type` attr reserved in v3 → crash. Fixed + Error Boundary + ForceAtlas2 tuned for 1300+ nodes
2. **Dense constellation**: 153n/63e → 1346n/3286e (21 types, 36 edge tables scanned)
3. **View simplification**: Removed 3D/2D, kept sigma + cards only (-531 lines)
4. **Chinese labels**: 60+ FIELD_ZH property mappings, 10 missing edge labels added
5. **Quality fix**: 1398 descriptions added, 452 backbone edges built, RiskIndicator/AuditTrigger excluded (100% garbage)
6. **Type-focused subgraph**: /constellation/type API, sidebar click loads focused view
7. **v4.2 Design**: 3-round 17-expert swarm → +14 types, +20 edges, 35 total
8. **Skill group**: `ontology-audit-swarm` fixed in skill-groups.json
9. **HTML**: 1691-line McKinsey Blue complete ontology document

### Next: v4.2 PDCA Implementation

Design: `docs/plans/2026-03-30-ontology-v42-final-design.md`

#### Phase 1: P0 Foundation (Week 1-2)

CREATE 7 node tables:
```
JournalEntryTemplate (分录模板, 200-300)
FinancialStatementItem (报表项目, 150-200)
TaxCalculationRule (计算规则, 100-150)
FilingFormField (申报表栏次, 300-500)
FinancialIndicator (财务指标, 80-120)
AccountingStandard (会计准则, 60-80)
TaxTreaty (税收协定, 112)
```

CREATE 12 edge tables:
```
HAS_ENTRY_TEMPLATE: BusinessActivity → JournalEntryTemplate
ENTRY_DEBITS: JournalEntryTemplate → AccountingSubject
ENTRY_CREDITS: JournalEntryTemplate → AccountingSubject
POPULATES: AccountingSubject → FinancialStatementItem
FIELD_OF: FilingFormField → FilingForm
DERIVES_FROM: FilingFormField → FilingFormField
CALCULATION_FOR_TAX: TaxCalculationRule → TaxType
DECOMPOSES_INTO: FinancialIndicator → FinancialIndicator
COMPUTED_FROM: FinancialIndicator → FinancialStatementItem
HAS_BENCHMARK: FinancialIndicator → IndustryBenchmark
PARTY_TO: Region → TaxTreaty
OVERRIDES_RATE: TaxTreaty → TaxRate
```

Also Phase 1:
- TRUNCATE RiskIndicator + AuditTrigger
- AccountingSubject 223 → 500+
- TaxIncentive +7 PIT special deductions
- STACKS_WITH/EXCLUDES 60-80 edges

#### Phase 2: P1 Tax Law (Week 3-4)
- CREATE: TaxItem, TaxBasis, TaxLiabilityTrigger, DeductionRule, TaxMilestoneEvent
- Rebuild: RiskIndicator 150-200, AuditTrigger 80-120
- Expand: IndustryBenchmark 45→500+, ComplianceRule 84→200+

#### Phase 3: P2 Operations (Week 5-6)
- CREATE: ResponseStrategy, PolicyChange
- Expand: Penalty 127→200+, InvoiceRule 40→55

#### Phase 4: Validation
- 10 real business queries, monthly close chain, constellation update

### Key Commands
```bash
# VPS restart
ssh root@100.75.77.112 "kill \$(lsof -t -i:8400) 2>/dev/null; sleep 2; rm -rf /home/kg/cognebula-enterprise/__pycache__; cd /home/kg/cognebula-enterprise && nohup sudo -u kg /home/kg/kg-env/bin/python3 -m uvicorn kg-api-server:app --host 0.0.0.0 --port 8400 --workers 1 > /home/kg/kg-api.log 2>&1 &"

# DDL via API
curl -sf "http://100.75.77.112:8400/api/v1/admin/execute-ddl" -X POST -H "Content-Type: application/json" -d '{"statements": ["CREATE NODE TABLE ..."]}'

# Frontend deploy
cd web && npx next build && npx wrangler pages deploy out --project-name=lingque-desktop --branch=master
```

### Git
- Branch: main, commit f9662c5
- Remote: github.com:MARUCIE/cognebula-enterprise
