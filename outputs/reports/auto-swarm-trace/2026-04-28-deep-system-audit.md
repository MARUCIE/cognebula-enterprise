# Auto-Visual-Swarm Trace · Deep System Audit · 2026-04-28

> **Target**: `outputs/audits/2026-04-28-deep-system-audit.html` (+ companion `.md`)
> **Rule**: `knowledge/facts/engineering-baseline/16-auto-visual-swarm-review.md`
> **Outcome**: 3/3 APPROVE in Round 3 → consensus reached → eligible to ship

---

## Swarm composition

| Slot | Advisor | Lens |
|------|---------|------|
| 1 | `advisor-hara` | Structural minimalism, emptiness, redundancy detection |
| 2 | `advisor-orwell` | Clarity through honesty, anti-hedging, anti-self-protection |
| 3 | `advisor-munger` | Inversion, multi-mental-model risk, Lollapalooza check |

Advisors deliberately chosen to span structural / linguistic / epistemic dimensions — not three lenses on the same axis.

---

## Round 1

### Verdicts
- **Hara**: REVISE — 3 patches (drop redundant Probe-B-end callout, drop Probe-C metric-cell grid, merge action #7 into #6)
- **Orwell**: APPROVE — clarity score 8.5/10, with 3 minor tightening patches
- **Munger**: REVISE — HIGH RISK. Audit picked `.demo` as production without verifying via `lsof`/code grep/git log. Memory may not be hallucinating; state may have been pruned.

### Consensus on APPROVE: NO (1/3)

### Inter-round verification probes (Munger-prescribed)
Run before applying patches:
```bash
pgrep cognebula|lingque|kg-api    # → no live local processes
grep -rn "kuzu.Database" src/      # → all default --db data/finance-tax-graph (empty path)
grep -rn "finance-tax-graph" src/ scripts/ configs/
git log --all | grep -iE "purge|reset|rebuild|migrate"
```

### Verification findings
- Production runs on **contabo VPS**, not local: `scripts/deploy_web.sh:26` → `SSH_HOST="contabo"`
- Commit `f71b980` (2026-04-27) — `systemctl restart kg-api` on contabo, **35,897 nodes pruned**
- Memory's `620K nodes / 1M edges` was historically accurate at peak prod state
- `.demo` is a pre-Round-4-prune dev sandbox on a different timeline than prod
- Local `data/finance-tax-graph/` empty because dev work happens on `.demo` / `.phase1d-test` forks; this is a developer-experience smell, not a production issue

### Rev. 2 rewrite
Major rewrite landed:
- All Probe B/C numbers explicitly scoped to `.demo`
- Severity for Findings 2 + 3 downgraded RED → YELLOW (pending prod probe)
- F2 corrected: "memory and state out of sync via real prune, not hallucination"
- New rev-banner at top framing the Munger correction
- New "未验证的事项 (Munger 反向清单)" section at bottom
- Action table reordered: #1 RED = SSH to contabo prod; rest YELLOW/GREEN
- Hara's 3 structural patches applied
- Orwell's framing patches incorporated into the rewrite

---

## Round 2

### Verdicts
- **Hara**: APPROVE — Rev. 2 corrections landed correctly. No new redundancy. Rev-banner carries weight; "未验证清单" is disciplined honesty not noise.
- **Orwell**: REVISE — 3 specific patches (rewrite rev-banner exoneration line, drop "待复测" sub-labels, change SSH first-command to discover-path-first)
- **Munger**: APPROVE with meta-reservation — Rev. 2 absorbed critique correctly without overcorrecting. New finding F-α: SSH `du -sh` presupposes path; should `lsof` first. Suggested F4 meta-finding about missing sandbox/prod marking convention.

### Consensus on APPROVE: YES (2/3)

### Cross-advisor patch alignment analysis
Per rule: "≥2/3 consensus for each applied patch."

| Patch | Source | Cross-advisor support | Decision |
|-------|--------|------------------------|----------|
| Rev-banner: "审计没找对地方" → "分析失误，不是导航失误" | Orwell P1 | Munger F-β agreed `f71b980` is taken as truth — same epistemic class | APPLY (2/3) |
| Drop "待复测" sub-labels in summary table | Orwell P2 | Hara explicitly approved current state; Munger silent | SKIP (1/3) |
| Action #1 first-command: discover path before assuming | Orwell P3 + Munger F-α | Two advisors flagged the same risk | APPLY (2/3) |
| Add F4 meta-finding: sandbox/prod marking convention | Munger only | Hara/Orwell silent | SKIP (1/3) |
| Re-rank Action #3 as BLOCKED-ON-#1 | Munger F-γ | Orwell/Hara silent | SKIP (1/3) |

### Patches applied between Round 2 and Round 3
1. **Rev-banner**: `"记忆没撒谎，是审计没找对地方。"` → `"记忆没撒谎；第一轮审计从不完整的证据得出'幻觉'结论——这是分析失误，不是导航失误。"`
2. **Action #1 first-command** (in both `.html` and `.md`):
   - Before: `ssh contabo 'cd /home/kg && du -sh ./*.kuzu'`
   - After: `ssh contabo 'lsof -p $(pgrep -f kg-api) 2>/dev/null | grep kuzu; find /home -name "*.kuzu" -maxdepth 4 2>/dev/null'`
3. Action #1 cell label updated to emphasize `先发现实际打开的 .kuzu 路径` / `discover the actual .kuzu path` before any measurement.

---

## Round 3

### Verdicts
- **Hara**: APPROVE — file meets structural minimalism bar. "未验证事项" is honest emptiness, not filler. Document can ship.
- **Orwell**: APPROVE — both applied patches landed correctly. Residual P2 (待复测 sub-labels) is minor signal-to-noise, not a precision defect. Not a REVISE reason.
- **Munger**: APPROVE — risk LOW provided Maurice runs Action #1 first. The dominant failure mode (typing commands against an unverified path) is closed by the `lsof + find` first-step. Munger explicitly accepts the consensus rule's veto of his own meta-finding ("Authority bias — suppressed").

### Consensus on APPROVE: YES (3/3) ✓

---

## Summary of applied patches (cumulative)

### Structural (Hara, Round 1)
- Removed redundant Probe-B-end callout (was duplicating page-top callout)
- Removed Probe-C metric-cell grid (numbers already in surrounding tables)
- Merged action "rename `LawOrRegulation.fullText`" into "reclassification decision" as sub-decision
- Action table 8 rows → 7 rows

### Epistemic (Munger, between Rounds 1–2)
- Whole audit reframed: `.demo` ≠ production
- Severity for Findings 2 + 3: RED → YELLOW
- F2 corrected: real prune happened; memory was historically accurate
- Added "未验证的事项" Munger blind-spot list
- Added rev-banner framing the correction
- Action #1 (NEW, RED): SSH prod for actual measurement

### Precision (Orwell + Munger, between Rounds 2–3)
- Rev-banner exoneration line replaced with accurate "analysis failure not navigation failure" framing
- Action #1 first-command swapped to `lsof + find` (discover-before-assume)
- `.md` companion synced with same change

### Skipped per consensus rule (1/3 not enough)
- "待复测" sub-label removal (Orwell P2 only)
- F4 meta-finding about sandbox/prod marking convention (Munger only)
- F-γ Action #3 re-rank as BLOCKED (Munger only)

---

## Residual concerns (acknowledged, not applied)

1. **Sandbox/prod marking convention** (Munger meta-finding): the audit revealed that the project lacks a `data/.sandbox/` vs `data/.prod-mirror/` convention. Without this, future audits can repeat the Round-1 error class. This is logged here as a residual concern; promotion would require ≥2 independent session signals per the engineering-baseline `Quality Gate`.
2. **`f71b980` says "executed" not "verified"** (Munger F-β): the audit takes the commit message as truth that 35,897 nodes were actually pruned on prod. A defensive read would treat this as "claimed but not independently confirmed by post-state measurement."
3. **"待复测" sub-label redundancy** (Orwell P2): YELLOW tag already carries the uncertainty; sub-labels are mild double-hedging. Cosmetic only.

These belong to the next iteration if Maurice asks for a Rev. 3.

---

## Verification

- All applied patches have ≥2/3 cross-advisor support per the consensus rule
- All skipped patches have explicit 1/3 audit trail above
- Round 3 verdicts: 3/3 APPROVE
- Final risk level (Munger): **LOW**, conditional on Maurice running Action #1 first

---

Maurice | maurice_wen@proton.me
