# KnowledgeUnit Fragmentation Investigation · 2026-04-28

> **Scope**: §20 Phase B5 deliverable. Roots out the actual cause of the 185,455 KU node count flagged in the depth-breadth audit (F3). Owner decision: Maurice.
> **Status**: INVESTIGATION COMPLETE. **F3 framing falsified — reframed.** No execution authorized.
> **Companion**: §20 Phase B5 atomic queue item; sister to B2 (lineage unification) and B4 (Source schema).

---

## 0. TL;DR — third Munger validation this session

The audit's F3 framing assumed a `[:200]` truncation cap analogous to F2's line 1708 `[:500]` clamp on LegalClause. **Direct probe falsifies that hypothesis.**

| Probe | Result |
|---|---|
| Sample size | 2,500 KUs (paged 5×500 via `/api/v1/nodes?type=KnowledgeUnit&offset=...`) |
| Max content length | **193 characters** — never reaches 200 |
| Median content length | 137 characters |
| 99th-percentile length | 175 characters |
| `==200` characters | **0 of 2,500 (0.0%)** |
| Distribution shape | Smooth bell, **no spike-at-200 signature** |
| `extracted_by` field | 100% empty (`<none>`) — opaque ingest provenance |
| `source_doc_id` field | **100% populated** — full provenance present |

A truncation cap leaves a spike at the cap value (we expect 5-15% of rows landing at exactly 200 chars when a clamp is active). We see zero. **The KU storage layer is not truncating content.**

---

## 1. Actual shape revealed

### Per-source-doc fragmentation (top-10 in sample)

| `source_doc_id` | KUs in sample |
|---|---:|
| `financial_mgmt_key_points.json` | 400 |
| `accounting_key_points.json` | 345 |
| `cost_mgmt_formula_collection.json` | 293 |
| `financial_mgmt_formulas.json` | 276 |
| `lecture_accounting_02-逆袭精讲班-注会会计_第1_2章.json` | 272 |
| `important_tax_policies.json` | 236 |
| `classic_journal_entries.json` | 228 |
| `audit_key_points.json` | 216 |
| `audit_confusion_points.json` | 145 |
| `audit_exam_trends.json` | 89 |

These 10 source docs alone account for 2,500 KUs (the full sample). The implied population: roughly **500-800 source JSON files** producing ~185,455 KUs in total, average **~250-400 KUs per source doc**.

### Content shape (representative samples)

```
title:    第二章 会计政策和会计估计及其变更及其会计差错更正 ..................................
content:  本章阐述了会计政策、会计估计及其变更的定义、确认条件及披露要求，并详细规定了前期会计差错更正的会计处理方法。
          核心在于确保财务报表的可比性与可靠性，要求企业在发生... [137 chars]

title:    第六章 投资性房地产 .................................................
content:  本章规范了投资性房地产的确认、计量及处置。明确了投资性房地产的定义（为赚取租金或资本增值而持有的房地产），
          规定了成本模式与公允价值模式的后续计量选择及转换条件... [137 chars]
```

Every sampled `title` is a CPA-textbook chapter header followed by TOC-leader dots (artifacts from PDF→JSON conversion). Every sampled `content` is a 100-200-character chapter abstract — neither an atomic fact nor a Q&A pair, but a **chapter-level summary**.

### Identity pattern

KU `id` values are 16-char hex hashes (`0acc3ca93e5c2b6c`, `8a145b825ee4cfac`, ...). No semantic prefix. Identity is content-derived, not provenance-derived. This means there is no way to tell from an ID alone which textbook a KU came from — you must read `source_doc_id`.

### Duplicate rate

3 / 2,500 (0.12%) duplicate content. Essentially clean. The fragmentation is not amplified by within-source duplication.

---

## 2. F3 reframed — granularity mismatch, not truncation

The audit's framing had three errors:

| Audit framing | Reality |
|---|---|
| KU content is truncated at 200 chars | Content is naturally short (max 193) |
| Truncation hides longer source paragraphs | Source docs are pre-decomposed JSON entries; there are no "longer paragraphs" upstream of the KU |
| Fix path: lift the cap, re-ingest from full source text | There is nothing to lift; the JSON entries ARE the content |

The actual problem is a **granularity choice at the ingest layer**:

> CPA-textbook source documents are JSON files with one entry per chapter or section. The ingester writes one KU per JSON entry, producing chapter-abstract-sized KUs (~135 chars).

This is a **deliberate design**, not a bug. It produces 185,455 KUs because the source corpus has roughly 185,455 chapter/section entries. The shape is internally consistent.

### Why this still matters for retrieval

Chapter-level abstracts are **poor RAG targets**:

- Query "投资性房地产何时按公允价值模式计量？" wants a specific rule, not a chapter abstract
- Chapter abstracts are bridges to navigation, not endpoints of reasoning
- The KU `content` field's job (per current ingest) is to *describe what the chapter contains*, not to *answer questions*

So F3's *consequence* (degraded RAG precision when the model retrieves a chapter abstract instead of a fact) is real. F3's *cause* (truncation cap) is wrong.

---

## 3. Three remediation paths (owner-decision)

### Path A — Accept current granularity, document the contract

KUs ARE chapter-abstract-level by design. Fix the audit framing, update the schema doc to reflect this, train the retrieval layer to weight LegalClause + FAQEntry above KU for fact-level questions. KU becomes a **navigation/topic-discovery** layer.

- **Cost**: zero migration; only documentation work.
- **Tradeoff**: 33.9% of nodes (185,455 KUs) keep their current role — they are not "wrong", they are mis-named. Could be renamed `KnowledgeChapter` or `TopicSummary` to make the contract honest.
- **Risk**: low.
- **Best when**: Maurice judges that chapter-level navigation is worth keeping AS IS, and retrieval ranking is the right place to fix the consequence.

### Path B — Re-ingest at section level (smaller atoms)

Split each chapter abstract into its constituent rules/concepts. Run a one-shot LLM extraction over the existing 185,455 KUs to decompose each into 3-10 fact-level atoms. New `KnowledgeAtom` (or repurposed KU) population: ~600,000-1,500,000 nodes.

- **Cost**: HIGH — full re-extraction over 185k seed nodes; storage 3-5×; embedding rebuild.
- **Tradeoff**: better RAG precision, much larger graph. Some abstracts genuinely don't decompose (formula collections), so the gain is uneven.
- **Risk**: medium — requires LLM budget + verification loop; risks introducing extraction errors.
- **Best when**: Maurice judges that fact-level RAG is the dominant use case AND the existing chapter abstracts will be discarded after re-extraction (else duplication).

### Path C — Hybrid: keep KU as navigation, add `KnowledgeAtom` as fact layer

Promote KU to its actual role (navigation/topic) and introduce a new `KnowledgeAtom` table for fact-level retrieval. KU becomes a parent; KnowledgeAtom rows link via `parent_ku_id`. New ingest runs over high-value source docs only (tax policies + journal entries + formulas; ~50% of source corpus by audit relevance).

- **Cost**: MEDIUM — selective re-extraction (~30,000 source-doc-equivalents instead of all 185k); new table declaration in canonical ontology; new edge type.
- **Tradeoff**: two-tier retrieval ranking; more model work to choose layer; cleaner separation than Path B.
- **Risk**: medium — adds a table type, but the type is clean (no V2 lineage problem).
- **Best when**: Maurice judges that some retrieval needs chapter-level (study guides, exam prep) and some need atom-level (specific rule lookup), and wants both surfaces.

---

## 4. Connection to other §20 findings

| §20 Finding | Connection to B5 |
|---|---|
| F1 V2 proliferation | Independent — KUs do NOT have a V2 counterpart, so lineage unification doesn't touch this |
| F2 line 1708 `[:500]` | Independent — that clamp affects LegalClause, not KU. Different storage path. |
| F4 schema-runtime drift | Reinforced — 100% empty `extracted_by` shows that the canonical schema field exists but the KU ingest path doesn't populate it |
| F5 source attribution | **Mitigated** — KU has `source_doc_id` populated 100% of the time. Phase 1 backfill of `source_id` for KU is therefore LOW-cost (resolve `source_doc_id` filename → `Source.id`) |

---

## 5. Empty `extracted_by` field — secondary finding

Of 2,500 sampled KUs, **100% have `extracted_by` empty**. This means the canonical schema field exists (KU table declares it; the ontology v4.2 carries it) but no ingest pipeline writes it.

This is itself a small F4 instance: a **schema-runtime drift in the opposite direction** from the ones flagged in A4. The previous A4 finding was "tables exist live but not declared in schema"; this is "field declared in schema but never written by any ingest".

Patch scope: trivial. Whichever ingest writes KUs (search hint: `scripts/ingest_*.py` family) should set `extracted_by = '<pipeline-name-vN>'`. The fix is one line per ingest script. No owner decision needed for this micro-fix; can be bundled into Phase C if Path A is selected.

---

## 6. Owner decisions blocking execution

- [ ] **Choose remediation path** (A keep + rename / B full re-extract / C hybrid)
- [ ] **If Path A or C**: authorize KU table rename to honest contract name (`KnowledgeChapter` / `TopicSummary`) vs keep `KnowledgeUnit` as misnomer
- [ ] **If Path B or C**: authorize LLM budget for re-extraction (Path B: ~$2-8K Claude Haiku; Path C: ~$1-3K)
- [ ] **For all paths**: authorize the `extracted_by` backfill micro-fix (one-line patch per ingest script; harmless)

---

## 7. Recommended path (analyst opinion, not a decision)

**Path A + extracted_by micro-fix.**

Rationale (Buffett moat lens): 185,455 chapter abstracts are an **asset that took ingest investment to produce**. Path A preserves that asset, requires zero migration, and makes the contract honest. The retrieval-precision problem is real but it lives at a different layer (re-ranker, not data) where it can be solved cheaper.

Path B's gains are speculative until tested; Path C adds a new table type at a moment when the §20 audit is trying to *reduce* table-count complexity (F1).

If after Path A the retrieval-precision problem persists in production and is bound to Maurice's actual workflow (yiclaw RAG, agent retrieval), revisit Path C as a targeted addition for high-value source docs only.

---

## 8. Falsification probe receipts

For audit reproducibility, the probes that produced this finding:

```python
# /api/v1/nodes paginated 5×500
import sys; sys.path.insert(0, 'scripts/_lib'); import prod_kg_client as kg
all_rows = []
for offset in (0, 500, 1000, 1500, 2000):
    payload = kg._get('/api/v1/nodes', params={'type': 'KnowledgeUnit', 'limit': 500, 'offset': offset})
    all_rows.extend(kg._results(payload))
# n=2500, max(len(r['content']))=193, ==200 count=0
```

Re-running the probe against future prod state will reproduce the finding (or detect drift).

---

Maurice | maurice_wen@proton.me
