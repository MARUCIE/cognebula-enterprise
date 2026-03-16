#!/usr/bin/env python3
"""Multi-Swarm AI Synthesis Quality Control Pipeline.

Architecture:
  Generator (Swarm 1) -> Fact Checker (Swarm 2) -> Domain Expert (Swarm 3)
    -> Red Team (Swarm 4) -> Gate -> Inject

Each swarm is an LLM call with a specialized system prompt.
The pipeline runs sequentially; a node must pass each gate to proceed.

Usage:
    from ai_synthesis.swarm_pipeline import SwarmPipeline
    pipeline = SwarmPipeline(api_key="...", graph_path="data/finance-tax-graph")
    result = pipeline.run(industry="manufacturing", scenario_type="vat_input_credit")

Dependencies: requests (stdlib-adjacent, ships with most Python installs)
    pip install requests   # if not present
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

logger = logging.getLogger("swarm_pipeline")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _resolve_api_key() -> str:
    """Resolve Gemini API key from env or ~/.openclaw/.env."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key
    env_path = Path.home() / ".openclaw" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip("\"'")
    raise EnvironmentError(
        "GEMINI_API_KEY not found in env or ~/.openclaw/.env"
    )


def _resolve_base_url() -> str:
    """Resolve Gemini API base URL (supports proxy for VPS)."""
    return os.environ.get("GEMINI_EMBED_BASE", GEMINI_API_URL).rstrip("/")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class SwarmVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class GateDecision(str, Enum):
    AUTO_INJECT = "auto_inject"
    HUMAN_REVIEW = "human_review"
    REJECT = "reject"


@dataclass
class Citation:
    """A reference to an existing regulation or standard in the graph."""
    regulation_id: str       # e.g. "TT_VAT", "CAS_6", "REG_2024_14"
    quoted_text: str         # exact text being cited
    source_document: str     # legal doc name
    article_number: str = "" # specific article/clause


@dataclass
class CandidateNode:
    """A candidate knowledge node produced by the Generator swarm."""
    node_id: str
    industry: str
    scenario_type: str
    title: str
    content: str             # the synthesized knowledge text
    citations: list[Citation] = field(default_factory=list)
    accounting_entries: list[dict] = field(default_factory=list)
    tax_implications: list[dict] = field(default_factory=list)
    risk_indicators: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


@dataclass
class SwarmResult:
    """Result from a single swarm review stage."""
    swarm_name: str
    verdict: SwarmVerdict
    confidence: float        # 0.0 - 1.0
    reasoning: str
    corrections: list[dict] = field(default_factory=list)
    flag_reasons: list[str] = field(default_factory=list)
    raw_response: str = ""


@dataclass
class PipelineResult:
    """Full pipeline result for a candidate node."""
    node: CandidateNode
    swarm_results: list[SwarmResult] = field(default_factory=list)
    gate_decision: GateDecision = GateDecision.REJECT
    final_confidence: float = 0.0
    elapsed_seconds: float = 0.0
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "gate_decision": self.gate_decision.value,
            "final_confidence": self.final_confidence,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "node": self.node.to_dict(),
            "swarm_results": [
                {
                    "swarm_name": r.swarm_name,
                    "verdict": r.verdict.value,
                    "confidence": r.confidence,
                    "reasoning": r.reasoning,
                    "corrections": r.corrections,
                    "flag_reasons": r.flag_reasons,
                }
                for r in self.swarm_results
            ],
        }


# ---------------------------------------------------------------------------
# Gemini API client
# ---------------------------------------------------------------------------

class GeminiClient:
    """Minimal Gemini REST client using requests."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str | None = None,
    ):
        if requests is None:
            raise ImportError("requests package required: pip install requests")
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or _resolve_base_url()).rstrip("/")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """Call Gemini generateContent and return the text response."""
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": user_prompt}]},
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}],
            },
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            logger.error("Unexpected Gemini response: %s", json.dumps(data)[:500])
            raise RuntimeError(f"Gemini response parse error: {exc}") from exc


# ---------------------------------------------------------------------------
# Mock client for dry-run / testing
# ---------------------------------------------------------------------------

class MockGeminiClient:
    """Returns plausible mock responses for each swarm stage."""

    def __init__(self):
        self._call_count = 0

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        self._call_count += 1
        # Detect which swarm is calling by system prompt keywords
        if "generate a candidate" in system_prompt.lower() or "generator" in system_prompt.lower():
            return self._mock_generator()
        elif "fact check" in system_prompt.lower() or "citation" in system_prompt.lower():
            return self._mock_fact_checker()
        elif "cpa" in system_prompt.lower() or "注册会计师" in system_prompt:
            return self._mock_domain_expert()
        elif "red team" in system_prompt.lower() or "audit" in system_prompt.lower():
            return self._mock_red_team()
        return json.dumps({"verdict": "pass", "confidence": 0.8, "reasoning": "Mock pass"})

    def _mock_generator(self) -> str:
        return json.dumps({
            "title": "一般纳税人制造业增值税进项税额抵扣",
            "content": (
                "制造业一般纳税人购入原材料取得增值税专用发票，"
                "按照增值税法第十条规定，可凭票抵扣进项税额。"
                "购入时借记「原材料」和「应交税费-应交增值税(进项税额)」，"
                "贷记「应付账款」或「银行存款」。"
            ),
            "citations": [
                {
                    "regulation_id": "TT_VAT",
                    "quoted_text": "增值税一般纳税人购进货物取得的增值税专用发票上注明的增值税额准予抵扣",
                    "source_document": "增值税法",
                    "article_number": "第十条",
                }
            ],
            "accounting_entries": [
                {
                    "description": "购入原材料取得专票",
                    "debit": [
                        {"account": "1403 原材料", "amount": 100000},
                        {"account": "2221-01 应交增值税(进项税额)", "amount": 13000},
                    ],
                    "credit": [
                        {"account": "2202 应付账款", "amount": 113000},
                    ],
                }
            ],
            "tax_implications": [
                {
                    "tax_type": "TT_VAT",
                    "rate": 13.0,
                    "direction": "deductible_input",
                    "period": "monthly",
                }
            ],
            "risk_indicators": [
                {
                    "indicator": "进项税额占比异常",
                    "threshold": "进项/销项 > 95% 连续3个月",
                    "severity": "medium",
                }
            ],
        })

    def _mock_fact_checker(self) -> str:
        return json.dumps({
            "verdict": "pass",
            "confidence": 0.92,
            "reasoning": "All citations verified. TT_VAT exists in graph. Quoted text is consistent with source.",
            "corrections": [],
        })

    def _mock_domain_expert(self) -> str:
        return json.dumps({
            "verdict": "pass",
            "confidence": 0.88,
            "reasoning": (
                "Debit/credit balanced (113000 = 100000 + 13000). "
                "Tax rate 13% correct for manufacturing raw materials. "
                "进项税额抵扣条件符合现行规定。"
            ),
            "corrections": [],
        })

    def _mock_red_team(self) -> str:
        return json.dumps({
            "verdict": "pass",
            "confidence": 0.90,
            "reasoning": "No fabricated regulation numbers found. Tax type TT_VAT is real. Threshold values are within plausible range.",
            "flag_reasons": [],
        })


# ---------------------------------------------------------------------------
# Graph connector (KuzuDB)
# ---------------------------------------------------------------------------

class GraphConnector:
    """Thin wrapper for KuzuDB citation verification."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._conn = None

    def _ensure_conn(self):
        if self._conn is not None:
            return
        try:
            import kuzu
        except ImportError:
            logger.warning("kuzu not installed; graph verification disabled")
            return
        if not self.db_path.exists():
            logger.warning("Graph DB not found at %s; verification disabled", self.db_path)
            return
        db = kuzu.Database(str(self.db_path))
        self._conn = kuzu.Connection(db)

    def node_exists(self, node_id: str) -> bool | None:
        """Check if a node ID exists in the graph. Returns None if DB unavailable."""
        self._ensure_conn()
        if self._conn is None:
            return None
        # Search across common node tables
        for table in ("TaxType", "AccountCode", "Regulation", "RiskIndicator",
                       "Industry", "EnterpriseType", "LifecycleStage"):
            try:
                result = self._conn.execute(
                    f"MATCH (n:{table}) WHERE n.id = $id RETURN n.id",
                    {"id": node_id},
                )
                if result.has_next():
                    return True
            except Exception:
                continue
        return False

    def get_known_regulation_ids(self) -> list[str]:
        """Return all regulation/tax type IDs for prompt context."""
        self._ensure_conn()
        if self._conn is None:
            return []
        ids = []
        for table in ("TaxType", "Regulation"):
            try:
                result = self._conn.execute(f"MATCH (n:{table}) RETURN n.id")
                while result.has_next():
                    ids.append(result.get_next()[0])
            except Exception:
                continue
        return ids


# ---------------------------------------------------------------------------
# Swarm prompts
# ---------------------------------------------------------------------------

GENERATOR_SYSTEM = """You are a Generator for the CogNebula Finance/Tax Knowledge Base.
Your task: generate a candidate knowledge node for Chinese finance/tax domain.

RULES:
1. Every claim MUST have at least one citation referencing an existing regulation ID.
2. No citation = the node will be auto-rejected.
3. Accounting entries MUST have balanced debit and credit totals.
4. Use real Chinese tax law, CAS standards, and regulation numbers.
5. Content must be practically useful for accountants and tax advisors.
6. All text fields (title, content, quoted_text, description) MUST be in Chinese (中文).
7. Return ONLY valid JSON. No markdown, no commentary, no extra text.

OUTPUT FORMAT (JSON):
{
  "title": "...",
  "content": "...",
  "citations": [{"regulation_id": "...", "quoted_text": "...", "source_document": "...", "article_number": "..."}],
  "accounting_entries": [{"description": "...", "debit": [{"account": "...", "amount": N}], "credit": [{"account": "...", "amount": N}]}],
  "tax_implications": [{"tax_type": "...", "rate": N, "direction": "...", "period": "..."}],
  "risk_indicators": [{"indicator": "...", "threshold": "...", "severity": "low|medium|high"}]
}
"""

FACT_CHECKER_SYSTEM_TEMPLATE = (
    "You are a Fact Checker for the CogNebula Finance/Tax Knowledge Base.\n"
    "Your task: verify that all citations in a candidate node are accurate.\n\n"
    "CHECKS:\n"
    "1. Citation regulation_id must refer to a real, existing Chinese regulation or tax type.\n"
    "2. Quoted text must be consistent with the cited source document.\n"
    "3. Numerical values (rates, amounts, thresholds) must be factually correct.\n"
    "4. Article numbers must exist in the cited document.\n\n"
    "KNOWN REGULATION IDS IN GRAPH:\n"
    "{known_ids}\n\n"
    'OUTPUT FORMAT (JSON):\n'
    '{{"verdict": "pass or fail", "confidence": 0.0-1.0, "reasoning": "...", '
    '"corrections": [{{"field": "...", "original": "...", "corrected": "...", "reason": "..."}}]}}'
)

DOMAIN_EXPERT_SYSTEM = """You are a licensed CPA and tax advisor (注册会计师+税务师) reviewing AI-generated knowledge nodes.
Your task: ensure CPA-level accuracy of the candidate node.

CHECKS:
1. Debit/credit balance: total debits must equal total credits in every journal entry.
2. Tax base calculation: rates applied to correct bases, no arithmetic errors.
3. Temporal validity: regulations cited are current (not repealed or superseded).
4. Practical feasibility: the described scenario is realistic and the treatment is standard practice.
5. Account codes follow Chinese chart of accounts standards (企业会计准则).

OUTPUT FORMAT (JSON):
{
  "verdict": "pass" or "fail",
  "confidence": 0.0-1.0,
  "reasoning": "detailed CPA-level analysis",
  "corrections": [{"field": "...", "original": "...", "corrected": "...", "reason": "..."}]
}
"""

RED_TEAM_SYSTEM_TEMPLATE = (
    "You are a tax audit specialist on a Red Team. Your KPI is finding errors.\n"
    "Your task: adversarial review of AI-generated knowledge nodes for hallucinations.\n\n"
    "ATTACK VECTORS:\n"
    "1. Fabricated regulation numbers: check if cited regulation IDs and article numbers are real.\n"
    "2. Non-existent tax types: verify all tax_type references against the 18 Chinese tax types.\n"
    "3. Contradictions: check if the content contradicts known tax law or accounting standards.\n"
    "4. Numerical manipulation: verify all amounts, rates, and thresholds are internally consistent.\n"
    "5. Temporal traps: check for references to repealed regulations or future-dated rules.\n"
    "6. Logic holes: check for accounting entries that don't make economic sense.\n\n"
    "KNOWN REGULATION IDS IN GRAPH:\n"
    "{known_ids}\n\n"
    'OUTPUT FORMAT (JSON):\n'
    '{{"verdict": "pass or fail", "confidence": 0.0-1.0, "reasoning": "...", '
    '"flag_reasons": ["reason1", "reason2"]}}'
)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class SwarmPipeline:
    """4-layer swarm review pipeline for AI-synthesized finance/tax nodes."""

    def __init__(
        self,
        api_key: str | None = None,
        graph_path: str | Path = "data/finance-tax-graph",
        model: str = DEFAULT_MODEL,
        dry_run: bool = False,
    ):
        self.dry_run = dry_run
        if dry_run:
            self.client = MockGeminiClient()
        else:
            self.client = GeminiClient(
                api_key=api_key or _resolve_api_key(),
                model=model,
            )
        self.graph = GraphConnector(graph_path)

    def _call_llm(self, system: str, user: str, temp: float = 0.3, retries: int = 2) -> dict:
        """Call LLM and parse JSON response, with retry on parse failure."""
        for attempt in range(1, retries + 1):
            raw = self.client.generate(system, user, temperature=temp)
            # Strip markdown fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                if attempt < retries:
                    logger.warning(
                        "JSON parse failed (attempt %d/%d), retrying...",
                        attempt, retries,
                    )
                    time.sleep(1)
                    continue
                logger.error("Failed to parse LLM response as JSON after %d attempts: %s", retries, raw[:300])
                return {"error": "json_parse_failure", "raw": raw[:500]}

    # -- Swarm 1: Generator ------------------------------------------------

    def generate_candidate(
        self,
        industry: str,
        scenario_type: str,
        existing_regulations: list[str] | None = None,
    ) -> CandidateNode | None:
        """Swarm 1: Generate a candidate knowledge node."""
        known_ids = existing_regulations or self.graph.get_known_regulation_ids()
        user_prompt = (
            f"Generate a finance/tax knowledge node for:\n"
            f"- Industry: {industry}\n"
            f"- Scenario: {scenario_type}\n"
            f"- Available regulation IDs: {json.dumps(known_ids[:50])}\n\n"
            f"The node must cite at least one regulation from the list above."
        )
        data = self._call_llm(GENERATOR_SYSTEM, user_prompt, temp=0.5)
        if "error" in data:
            logger.error("Generator failed: %s", data.get("error"))
            return None

        # Auto-reject: no citations
        citations_raw = data.get("citations", [])
        if not citations_raw:
            logger.warning("Generator produced node with no citations -> auto-reject")
            return None

        node = CandidateNode(
            node_id=f"SYN_{uuid.uuid4().hex[:8]}",
            industry=industry,
            scenario_type=scenario_type,
            title=data.get("title", "Untitled"),
            content=data.get("content", ""),
            citations=[Citation(**c) for c in citations_raw],
            accounting_entries=data.get("accounting_entries", []),
            tax_implications=data.get("tax_implications", []),
            risk_indicators=data.get("risk_indicators", []),
            metadata={"generated_at": datetime.now(timezone.utc).isoformat()},
        )
        return node

    # -- Swarm 2: Fact Checker ---------------------------------------------

    def fact_check(self, node: CandidateNode) -> SwarmResult:
        """Swarm 2: Verify citations exist and are accurate."""
        known_ids = self.graph.get_known_regulation_ids()
        system = FACT_CHECKER_SYSTEM_TEMPLATE.format(known_ids=json.dumps(known_ids[:80]))
        user_prompt = (
            f"Verify the following candidate node:\n\n"
            f"{json.dumps(node.to_dict(), ensure_ascii=False, indent=2)}"
        )
        data = self._call_llm(system, user_prompt, temp=0.2)
        return SwarmResult(
            swarm_name="fact_checker",
            verdict=SwarmVerdict(data.get("verdict", "fail")),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=data.get("reasoning", ""),
            corrections=data.get("corrections", []),
            raw_response=json.dumps(data, ensure_ascii=False),
        )

    # -- Swarm 3: Domain Expert --------------------------------------------

    def domain_expert_review(self, node: CandidateNode) -> SwarmResult:
        """Swarm 3: CPA-level accuracy review."""
        user_prompt = (
            f"Review the following candidate node for CPA-level accuracy:\n\n"
            f"{json.dumps(node.to_dict(), ensure_ascii=False, indent=2)}"
        )
        data = self._call_llm(DOMAIN_EXPERT_SYSTEM, user_prompt, temp=0.2)
        return SwarmResult(
            swarm_name="domain_expert",
            verdict=SwarmVerdict(data.get("verdict", "fail")),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=data.get("reasoning", ""),
            corrections=data.get("corrections", []),
            raw_response=json.dumps(data, ensure_ascii=False),
        )

    # -- Swarm 4: Red Team -------------------------------------------------

    def red_team_review(self, node: CandidateNode) -> SwarmResult:
        """Swarm 4: Adversarial hallucination detection."""
        known_ids = self.graph.get_known_regulation_ids()
        system = RED_TEAM_SYSTEM_TEMPLATE.format(known_ids=json.dumps(known_ids[:80]))
        user_prompt = (
            f"Adversarially review the following candidate node:\n\n"
            f"{json.dumps(node.to_dict(), ensure_ascii=False, indent=2)}"
        )
        data = self._call_llm(system, user_prompt, temp=0.4)
        return SwarmResult(
            swarm_name="red_team",
            verdict=SwarmVerdict(data.get("verdict", "fail")),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=data.get("reasoning", ""),
            flag_reasons=data.get("flag_reasons", []),
            raw_response=json.dumps(data, ensure_ascii=False),
        )

    # -- Gate ---------------------------------------------------------------

    @staticmethod
    def gate(swarm_results: list[SwarmResult]) -> tuple[GateDecision, float]:
        """Final gate decision based on swarm verdicts.

        - 4/4 pass -> confidence 0.95 -> auto_inject
        - 3/4 pass -> confidence 0.70 -> human_review
        - <3 pass  -> reject
        """
        pass_count = sum(1 for r in swarm_results if r.verdict == SwarmVerdict.PASS)
        avg_confidence = (
            sum(r.confidence for r in swarm_results) / len(swarm_results)
            if swarm_results
            else 0.0
        )

        if pass_count == 4:
            return GateDecision.AUTO_INJECT, max(0.95, avg_confidence)
        elif pass_count == 3:
            return GateDecision.HUMAN_REVIEW, min(0.70, avg_confidence)
        else:
            return GateDecision.REJECT, avg_confidence

    # -- Full pipeline run --------------------------------------------------

    def run(
        self,
        industry: str,
        scenario_type: str,
        existing_regulations: list[str] | None = None,
    ) -> PipelineResult:
        """Run full 4-swarm pipeline for one candidate node."""
        t0 = time.monotonic()

        # Swarm 1: Generate
        logger.info("Swarm 1 (Generator): industry=%s scenario=%s", industry, scenario_type)
        node = self.generate_candidate(industry, scenario_type, existing_regulations)
        if node is None:
            # Failed generation or no citations
            elapsed = time.monotonic() - t0
            dummy = CandidateNode(
                node_id="REJECTED",
                industry=industry,
                scenario_type=scenario_type,
                title="[Generation Failed]",
                content="",
            )
            return PipelineResult(
                node=dummy,
                gate_decision=GateDecision.REJECT,
                final_confidence=0.0,
                elapsed_seconds=elapsed,
            )

        results: list[SwarmResult] = []

        # Swarm 2: Fact Check
        logger.info("Swarm 2 (Fact Checker): node=%s", node.node_id)
        fc_result = self.fact_check(node)
        results.append(fc_result)
        if fc_result.verdict == SwarmVerdict.FAIL:
            logger.info("Fact check FAILED -> short-circuit to gate")
            # Still run gate with partial results for proper scoring
            decision, confidence = self.gate(results)
            return PipelineResult(
                node=node,
                swarm_results=results,
                gate_decision=GateDecision.REJECT,
                final_confidence=confidence,
                elapsed_seconds=time.monotonic() - t0,
            )

        # Swarm 3: Domain Expert
        logger.info("Swarm 3 (Domain Expert): node=%s", node.node_id)
        de_result = self.domain_expert_review(node)
        results.append(de_result)

        # Swarm 4: Red Team (always runs if we get here)
        logger.info("Swarm 4 (Red Team): node=%s", node.node_id)
        rt_result = self.red_team_review(node)
        results.append(rt_result)

        # Gate decision
        # Note: generator pass is implicit (node exists), so we count it as +1
        all_results = [
            SwarmResult(
                swarm_name="generator",
                verdict=SwarmVerdict.PASS,
                confidence=0.95,
                reasoning="Node generated with citations",
            ),
            *results,
        ]
        decision, confidence = self.gate(all_results)

        elapsed = time.monotonic() - t0
        logger.info(
            "Gate: decision=%s confidence=%.2f elapsed=%.1fs",
            decision.value, confidence, elapsed,
        )

        return PipelineResult(
            node=node,
            swarm_results=all_results,
            gate_decision=decision,
            final_confidence=confidence,
            elapsed_seconds=elapsed,
        )

    # -- Evaluate against golden test set -----------------------------------

    def evaluate(self, golden_path: str | Path) -> dict:
        """Run pipeline against golden test set and return accuracy metrics."""
        golden_path = Path(golden_path)
        with open(golden_path) as f:
            golden = json.load(f)

        entries = golden.get("entries", [])
        stats = {
            "total": len(entries),
            "correct_accepted": 0,
            "correct_rejected": 0,
            "wrong_accepted": 0,   # false positive (bad)
            "wrong_rejected": 0,   # false negative (acceptable)
            "by_category": {},
        }

        for entry in entries:
            category = entry.get("category", "unknown")
            expected_valid = entry.get("is_valid", True)

            # Feed entry through fact_check + domain_expert + red_team
            node = CandidateNode(
                node_id=entry.get("id", f"GOLDEN_{uuid.uuid4().hex[:4]}"),
                industry=entry.get("industry", "general"),
                scenario_type=entry.get("scenario_type", "general"),
                title=entry.get("title", ""),
                content=entry.get("content", ""),
                citations=[Citation(**c) for c in entry.get("citations", [])],
                accounting_entries=entry.get("accounting_entries", []),
                tax_implications=entry.get("tax_implications", []),
                risk_indicators=entry.get("risk_indicators", []),
            )

            results = []
            results.append(self.fact_check(node))
            results.append(self.domain_expert_review(node))
            results.append(self.red_team_review(node))

            # Add implicit generator pass
            all_results = [
                SwarmResult(
                    swarm_name="generator",
                    verdict=SwarmVerdict.PASS,
                    confidence=0.95,
                    reasoning="Pre-built golden entry",
                ),
                *results,
            ]
            decision, _ = self.gate(all_results)
            accepted = decision != GateDecision.REJECT

            if expected_valid and accepted:
                stats["correct_accepted"] += 1
            elif expected_valid and not accepted:
                stats["wrong_rejected"] += 1
            elif not expected_valid and not accepted:
                stats["correct_rejected"] += 1
            else:
                stats["wrong_accepted"] += 1

            cat_stats = stats["by_category"].setdefault(category, {
                "total": 0, "correct": 0, "wrong": 0,
            })
            cat_stats["total"] += 1
            if (expected_valid and accepted) or (not expected_valid and not accepted):
                cat_stats["correct"] += 1
            else:
                cat_stats["wrong"] += 1

        # Compute rates
        stats["accuracy"] = (
            (stats["correct_accepted"] + stats["correct_rejected"]) / stats["total"]
            if stats["total"] > 0
            else 0.0
        )
        stats["false_positive_rate"] = (
            stats["wrong_accepted"] / stats["total"] if stats["total"] > 0 else 0.0
        )
        return stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run swarm QC pipeline")
    parser.add_argument("--industry", default="manufacturing", help="Target industry")
    parser.add_argument("--scenario", default="vat_input_credit", help="Scenario type")
    parser.add_argument("--graph", default="data/finance-tax-graph", help="KuzuDB path")
    parser.add_argument("--dry-run", action="store_true", help="Use mock responses")
    parser.add_argument("--evaluate", metavar="PATH", help="Evaluate against golden test set")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    pipeline = SwarmPipeline(graph_path=args.graph, dry_run=args.dry_run)

    if args.evaluate:
        stats = pipeline.evaluate(args.evaluate)
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    result = pipeline.run(industry=args.industry, scenario_type=args.scenario)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
