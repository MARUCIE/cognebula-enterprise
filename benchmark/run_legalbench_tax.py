#!/usr/bin/env python3
"""LegalBench-Tax v0 evaluation runner — Stage 0 (validate) + Stage 1 (score).

Reads `eval_legalbench_tax_v0.jsonl` and either:

- **Stage 0 (default `--mode validate`)**: distribution + schema validation only
  (no API calls). Same as the original stub. Safe for CI / pre-commit.

- **Stage 1 dry-run (`--mode dry-run`)**: prints the request body that would be
  sent to the KG API for each case, without actually sending. Lets you inspect
  the wire shape before burning tokens. No external dependencies.

- **Stage 1 live (`--mode live`)**: scores the LegalBench-Tax cases. Two
  provider backends:

  * `--llm-provider kg-api` (default) — POSTs each `question` to
    `${COGNEBULA_API_URL}/api/v1/chat` with `mode: "rag"`. The server does
    retrieval + LLM internally. Backend LLM is whatever `kg-api-server.py`
    is configured to use (`POE_API_KEY` if set, else Gemini fallback).
  * `--llm-provider poe` — bypasses `/api/v1/chat`. Runner does retrieval via
    `/api/v1/hybrid-search` (zero-LLM-cost on the server side, hits the KG
    only) and POSTs the assembled RAG prompt directly to Poe API
    (`https://api.poe.com/v1/chat/completions`, OpenAI-compatible).
    Bot name controlled via `--poe-model` (default `gpt-5.4-nano`,
    cheapest text bot at $0.18 in / $1.14 out per 1M tokens; ~$0.15 for
    a full 100-question run). Real Poe bot names use lowercase-dot-version
    convention (e.g. `gemini-3.1-pro`, `gpt-5.4-mini`). See `--help`
    output for the cost-ranked menu.
    Requires `POE_API_KEY` env var on the runner side.

  Both provider paths score the response on three deterministic dimensions:

    1. anchor_recall  — fraction of `reasoning_anchors` whose target-id
       substring appears in returned `sources` rows
    2. keyword_overlap — fraction of Chinese keywords from `expected_answer`
       found in returned `answer`
    3. source_citation — fraction of statutory `sources` (e.g. "CIT 法 §27")
       whose tokens appear in returned `answer`

  Composite score = arithmetic mean of the three dimensions. Outputs a JSON
  results file per case + per-domain + overall aggregates.

Stage 2 (Day 75 SOTA): replace deterministic scoring with LLM judge for
fuzzy semantic equivalence; diff vs Claude Opus 4.7 baseline (70.3% on
VALS.ai LegalBench-Tax leaderboard).

Usage:
    python benchmark/run_legalbench_tax.py                              # validate
    python benchmark/run_legalbench_tax.py --mode dry-run                # preview

    # Live, route through kg-api server's /api/v1/chat (server LLM):
    COGNEBULA_API_URL=http://localhost:8400 KG_API_KEY=... \
        python benchmark/run_legalbench_tax.py --mode live --max-cases 5

    # Live, runner calls Poe directly (kg-api server only does retrieval):
    COGNEBULA_API_URL=http://localhost:8400 POE_API_KEY=... \
        python benchmark/run_legalbench_tax.py --mode live \
            --llm-provider poe --poe-model gpt-5.4-nano --max-cases 5

    # Poe bot names are lowercase-dot-version (per Poe /settings/subscription).
    # Estimated cost per 100-question full run (3K input + 800 output avg/q):
    #   gpt-5.4-nano             $0.15  (smoke + first baseline, recommended)
    #   gemini-3.1-flash-lite    $0.20
    #   gpt-5.4-mini             $0.53
    #   gemini-3.1-pro           $1.58  (capable mid-tier baseline)
    #   gpt-5.4                  $1.77
    #   gpt-5.5                  $3.55
    #   gpt-5.4-pro              $21.27 (only for SOTA leaderboard parity)
    #
    # First-time safety: ALWAYS use --max-cases 5 to verify wire + bot name
    # before pulling the trigger on the full 100.

SOTA gap doc cross-ref: §Day 61-75 — "Build private 100-case Chinese tax
eval set". Status 2026-04-26: 100/100 cases authored (CIT 30 / VAT 30 /
IIT 20 / MISC 20). Stage 1 runner ready; --live requires user trigger.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

REQUIRED_FIELDS = {
    "id",
    "domain",
    "sub_task",
    "difficulty",
    "question",
    "expected_answer",
    "reasoning_anchors",
    "sources",
    "author",
    "authored_at",
}

ALLOWED_DOMAINS = {"CIT", "VAT", "IIT", "MISC"}
ALLOWED_DIFFICULTY = {"easy", "medium", "hard"}
ALLOWED_MODES = {"validate", "dry-run", "live"}
ALLOWED_PROVIDERS = {"kg-api", "poe"}

TARGET_DISTRIBUTION = {"CIT": 30, "VAT": 30, "IIT": 20, "MISC": 20}

API_BASE_DEFAULT = os.environ.get("COGNEBULA_API_URL", "http://localhost:8400")
API_KEY = os.environ.get("KG_API_KEY", "")
POE_API_KEY = os.environ.get("POE_API_KEY", "")
POE_API_URL = "https://api.poe.com/v1/chat/completions"

# Default = cheapest text-completion bot ($0.18 in / $1.14 out per 1M tokens).
# Picked for smoke-test safety: 100 questions cost ~$0.15 total. Override
# via --poe-model when you want more capability. Real Poe bot names are
# lowercase-dot-version (e.g. gemini-3.1-pro, NOT Gemini-3-Pro).
POE_MODEL_DEFAULT = "gpt-5.4-nano"

# Reference pricing snapshot (Poe /settings/subscription, 2026-04-26).
# Useful for --output report annotation. NOT used to gate calls; user
# always controls cost via --max-cases. Doc rots; runner does not.
POE_MODEL_PRICING_USD_PER_1M = {
    "gemini-3.1-flash-lite": (0.25, 1.52),
    "gpt-5.4-nano":          (0.18, 1.14),
    "gpt-5.4-mini":          (0.68, 4.09),
    "gpt-5.3-codex":         (1.59, 12.73),
    "gpt-5.3-instant":       (1.59, 12.73),
    "gemini-3.1-pro":        (2.02, 12.12),
    "grok-4.20-multi-agent": (2.02, 6.06),
    "gpt-5.4":               (2.27, 13.64),
    "gpt-5.5":               (4.55, 27.27),
    "gpt-5.4-pro":           (27.27, 163.64),
    "gpt-5.5-pro":           (27.27, 163.64),
}

# Eval-focused system prompt. Intentionally simpler than the server's
# SYSTEM_PROMPT_RAG (which carries GenUI HTML directives that would pollute
# answer text and skew keyword scoring). Keeps the answer factual + cited.
SYSTEM_PROMPT_EVAL = """你是 CogNebula 业财税知识图谱的 AI 助手。基于提供的知识图谱上下文回答用户的中文税务问题。

规则：
1. 只根据上下文回答，不编造信息；上下文不足时明确说明
2. 必须引用具体法规文号 + 条款编号（如「CIT 法 §27」「财税[2018]15 号」「国家税务总局公告 2018 年第 28 号」）
3. 计算题给出公式 + 代入 + 结果三段
4. 回答使用纯中文文本，不输出 HTML / Markdown 代码块
5. 结构化：先给结论，再展开依据"""

# ---------------------------------------------------------------------------
# Stage 0 — validation
# ---------------------------------------------------------------------------


def validate_record(rec: dict, lineno: int) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(rec.keys())
    if missing:
        errors.append(f"line {lineno}: missing fields {missing}")
    if rec.get("domain") not in ALLOWED_DOMAINS:
        errors.append(f"line {lineno}: domain={rec.get('domain')!r} not in {ALLOWED_DOMAINS}")
    if rec.get("difficulty") not in ALLOWED_DIFFICULTY:
        errors.append(f"line {lineno}: difficulty={rec.get('difficulty')!r} not in {ALLOWED_DIFFICULTY}")
    if not isinstance(rec.get("reasoning_anchors"), list):
        errors.append(f"line {lineno}: reasoning_anchors must be list")
    if not isinstance(rec.get("sources"), list):
        errors.append(f"line {lineno}: sources must be list")
    return errors


def load_eval(path: Path) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    errors: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {lineno}: invalid JSON: {exc}")
                continue
            errors.extend(validate_record(rec, lineno))
            records.append(rec)
    return records, errors


def report(records: list[dict]) -> dict:
    by_domain = Counter(r.get("domain") for r in records)
    by_difficulty = Counter(r.get("difficulty") for r in records)
    by_sub_task = Counter(r.get("sub_task") for r in records)
    coverage_pct = {
        d: round(by_domain.get(d, 0) / TARGET_DISTRIBUTION[d] * 100, 1)
        for d in ALLOWED_DOMAINS
    }
    return {
        "total_cases": len(records),
        "by_domain": dict(by_domain),
        "by_difficulty": dict(by_difficulty),
        "top_sub_tasks": dict(by_sub_task.most_common(10)),
        "target_distribution": TARGET_DISTRIBUTION,
        "coverage_pct_vs_target": coverage_pct,
        "remaining_to_target": {
            d: TARGET_DISTRIBUTION[d] - by_domain.get(d, 0) for d in ALLOWED_DOMAINS
        },
    }


# ---------------------------------------------------------------------------
# Stage 1 — scoring helpers
# ---------------------------------------------------------------------------


# Chinese keyword extractor: 2+ char runs of CJK or alphanumeric tokens
# Filters single-char particles (的, 是, 等) which are noise.
_CJK_RE = re.compile(r"[一-鿿]{2,}|[A-Za-z][A-Za-z0-9_]+|\d+%?")
_NOISE_TOKENS = {
    "应纳", "应当", "可以", "不得", "如下", "本例", "来源", "因此", "其中",
    "包括", "适用", "按照", "实际", "符合", "规定", "情况",
}


def _extract_keywords(text: str, max_kw: int = 30) -> list[str]:
    """Extract content keywords from Chinese answer text."""
    if not text:
        return []
    raw = _CJK_RE.findall(text)
    kept: list[str] = []
    seen = set()
    for tok in raw:
        if tok in _NOISE_TOKENS or tok in seen:
            continue
        seen.add(tok)
        kept.append(tok)
        if len(kept) >= max_kw:
            break
    return kept


def _flatten_sources(api_sources: list) -> set[str]:
    """Collect all string values from API response `sources`."""
    out: set[str] = set()
    for src in api_sources:
        if not isinstance(src, dict):
            continue
        for row in src.get("rows", []):
            if not isinstance(row, list):
                continue
            for v in row:
                if isinstance(v, str):
                    out.add(v)
    return out


def score_case(case: dict, response: dict) -> dict:
    """Score a single case response. Returns dict with 4 metrics + matched lists."""
    answer = response.get("answer") or ""
    api_source_strings = _flatten_sources(response.get("sources") or [])

    # Dim 1: anchor_recall — anchor format "Type:id_or_name"
    anchors = case.get("reasoning_anchors", []) or []
    matched_anchors: list[str] = []
    for anchor in anchors:
        anchor_id = anchor.split(":", 1)[-1] if ":" in anchor else anchor
        if any(anchor_id in s for s in api_source_strings) or anchor_id in answer:
            matched_anchors.append(anchor)
    anchor_recall = len(matched_anchors) / max(len(anchors), 1)

    # Dim 2: keyword_overlap vs expected_answer
    keywords = _extract_keywords(case.get("expected_answer", ""))
    matched_kw = [k for k in keywords if k in answer]
    keyword_overlap = len(matched_kw) / max(len(keywords), 1)

    # Dim 3: source_citation — statutory tokens (法/条例/号) appear in answer
    expected_sources = case.get("sources", []) or []
    matched_sources: list[str] = []
    for src in expected_sources:
        # Token-split by space + punctuation; require >=1 informative token in answer
        tokens = [t for t in re.split(r"[\s§【】\[\]()（）]+", src) if len(t) >= 2]
        if any(t in answer for t in tokens):
            matched_sources.append(src)
    source_citation = len(matched_sources) / max(len(expected_sources), 1)

    composite = round((anchor_recall + keyword_overlap + source_citation) / 3, 4)

    return {
        "anchor_recall": round(anchor_recall, 4),
        "keyword_overlap": round(keyword_overlap, 4),
        "source_citation": round(source_citation, 4),
        "composite": composite,
        "matched_anchors": matched_anchors,
        "matched_keywords_count": len(matched_kw),
        "expected_keywords_count": len(keywords),
        "matched_sources": matched_sources,
    }


# ---------------------------------------------------------------------------
# Stage 1 — API call (live mode)
# ---------------------------------------------------------------------------


def _headers(extra: dict | None = None) -> dict:
    h = {"Accept": "application/json"}
    if API_KEY:
        h["X-API-Key"] = API_KEY
    if extra:
        h.update(extra)
    return h


def chat_request_body(case: dict, limit: int) -> dict:
    """Build the /api/v1/chat POST body for a case. Used by both dry-run and live."""
    return {
        "question": case["question"],
        "mode": "rag",
        "limit": limit,
    }


def call_chat(api_base: str, body: dict, timeout: int = 60) -> dict:
    """POST to /api/v1/chat. Returns dict with `answer` + `sources` or `error`."""
    url = f"{api_base.rstrip('/')}/api/v1/chat"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers=_headers({"Content-Type": "application/json"}),
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
            payload["_elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
            return payload
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode(errors="ignore")[:500]}
    except urllib.error.URLError as e:
        return {"error": f"URLError: {e.reason}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


# ---------------------------------------------------------------------------
# Stage 1 — Poe provider path (bypass kg-api LLM, retrieval-only via KG)
# ---------------------------------------------------------------------------


def call_hybrid_search(api_base: str, question: str, limit: int, timeout: int = 30) -> dict:
    """GET /api/v1/hybrid-search for retrieval (zero LLM cost server-side)."""
    qs = f"q={urllib.request.quote(question)}&limit={limit}&expand=true"
    url = f"{api_base.rstrip('/')}/api/v1/hybrid-search?{qs}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode(errors="ignore")[:500]}
    except urllib.error.URLError as e:
        return {"error": f"URLError: {e.reason}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


def build_rag_prompt(question: str, search_results: list) -> str:
    """Assemble the RAG prompt from hybrid-search results.

    Mirrors the server's _chat_inner RAG path (kg-api-server.py:2571-2579) so
    that runner-side scoring is comparable to server-side scoring.
    """
    context_parts = []
    for r in search_results:
        table = r.get("table", "")
        rid = r.get("id", "")
        title = r.get("title") or r.get("name") or ""
        text = r.get("text", "")
        context_parts.append(f"[{table}] {rid}: {title} — {text}")
    context = "\n".join(context_parts)
    if not context.strip():
        context = "（未检索到相关知识图谱条目）"
    return (
        "基于以下知识图谱上下文回答用户的问题。\n\n"
        f"## 知识图谱上下文\n{context}\n\n"
        f"## 用户问题\n{question}\n\n"
        "请给出准确、结构化的回答。"
    )


def poe_chat_payload(model: str, system: str, prompt: str,
                     temperature: float = 0.3, max_tokens: int = 4096) -> dict:
    """Build the Poe API request body. OpenAI-compatible chat-completions shape."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def call_poe(api_key: str, model: str, system: str, prompt: str,
             timeout: int = 90) -> dict:
    """POST to Poe API. Returns {answer, _elapsed_ms, _usage} or {error}."""
    if not api_key:
        return {"error": "POE_API_KEY env var not set"}
    body = poe_chat_payload(model, system, prompt)
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        POE_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            try:
                answer = payload["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e:
                return {"error": f"unexpected Poe response shape: {e}",
                        "raw": str(payload)[:500]}
            return {
                "answer": answer,
                "_elapsed_ms": elapsed_ms,
                "_usage": payload.get("usage", {}),
            }
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode(errors="ignore")[:500]}
    except urllib.error.URLError as e:
        return {"error": f"URLError: {e.reason}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


def run_poe_case(api_base: str, case: dict, limit: int, model: str,
                 api_key: str) -> dict:
    """Full Poe path for one case: retrieval -> prompt -> Poe -> response shape
    matching call_chat's so score_case can grade it identically.
    """
    search = call_hybrid_search(api_base, case["question"], limit)
    if "error" in search:
        return {"error": f"hybrid-search failed: {search['error']}"}
    results = search.get("results", [])
    prompt = build_rag_prompt(case["question"], results)
    poe_resp = call_poe(api_key, model, SYSTEM_PROMPT_EVAL, prompt)
    if "error" in poe_resp:
        return {"error": f"Poe call failed: {poe_resp['error']}"}
    # Reshape to look like call_chat's response so score_case stays uniform.
    api_sources = [{"rows": [[r.get("id", ""), r.get("table", "")]] }
                   for r in results]
    return {
        "answer": poe_resp["answer"],
        "sources": api_sources,
        "_elapsed_ms": poe_resp.get("_elapsed_ms"),
        "_usage": poe_resp.get("_usage", {}),
        "_retrieval_count": len(results),
    }


# ---------------------------------------------------------------------------
# Stage 1 — orchestration
# ---------------------------------------------------------------------------


def run_dry_run(records: list[dict], limit: int, max_preview: int) -> dict:
    """Print request bodies that would be sent. No API calls."""
    previewed = []
    for case in records[:max_preview]:
        body = chat_request_body(case, limit)
        previewed.append({"id": case["id"], "domain": case["domain"], "request_body": body})
    return {
        "mode": "dry-run",
        "total_cases": len(records),
        "previewed_count": len(previewed),
        "api_base_target": API_BASE_DEFAULT,
        "would_send_to": f"{API_BASE_DEFAULT}/api/v1/chat",
        "auth_header_set": bool(API_KEY),
        "preview": previewed,
        "note": "No API calls made. Use --mode live to actually score.",
    }


def run_live(records: list[dict], api_base: str, limit: int, sleep_s: float,
             provider: str = "kg-api", poe_model: str = POE_MODEL_DEFAULT,
             poe_api_key: str = "") -> dict:
    """Score each case via the chosen provider; aggregate per domain/difficulty/overall.

    provider:
      - "kg-api": POST /api/v1/chat (server does retrieval + LLM)
      - "poe":    GET /api/v1/hybrid-search (retrieval-only) + POST Poe directly
    """
    per_case: list[dict] = []
    api_errors = 0

    for i, case in enumerate(records, 1):
        if provider == "poe":
            response = run_poe_case(api_base, case, limit, poe_model, poe_api_key)
        else:
            body = chat_request_body(case, limit)
            response = call_chat(api_base, body)

        if "error" in response:
            api_errors += 1
            per_case.append({
                "id": case["id"],
                "domain": case["domain"],
                "error": response["error"],
                "detail": response.get("detail", "")[:200],
            })
        else:
            scored = score_case(case, response)
            per_case.append({
                "id": case["id"],
                "domain": case["domain"],
                "sub_task": case.get("sub_task"),
                "difficulty": case.get("difficulty"),
                "elapsed_ms": response.get("_elapsed_ms"),
                "usage": response.get("_usage", {}),
                "retrieval_count": response.get("_retrieval_count"),
                **scored,
            })
        # Brief progress indicator every 10 cases
        if i % 10 == 0:
            print(f"  ... {i}/{len(records)} cases done", file=sys.stderr)
        if sleep_s > 0 and i < len(records):
            time.sleep(sleep_s)

    # Aggregate
    by_domain_scores: dict[str, list[float]] = {d: [] for d in ALLOWED_DOMAINS}
    by_difficulty_scores: dict[str, list[float]] = {d: [] for d in ALLOWED_DIFFICULTY}
    overall_scores: list[float] = []
    total_input_tokens = 0
    total_output_tokens = 0
    for r in per_case:
        if "composite" not in r:
            continue
        overall_scores.append(r["composite"])
        by_domain_scores[r["domain"]].append(r["composite"])
        if r.get("difficulty") in by_difficulty_scores:
            by_difficulty_scores[r["difficulty"]].append(r["composite"])
        usage = r.get("usage") or {}
        total_input_tokens += usage.get("prompt_tokens", 0) or 0
        total_output_tokens += usage.get("completion_tokens", 0) or 0

    def _avg(xs: list[float]) -> float | None:
        return round(sum(xs) / len(xs), 4) if xs else None

    return {
        "mode": "live",
        "provider": provider,
        "poe_model": poe_model if provider == "poe" else None,
        "api_base": api_base,
        "total_cases": len(records),
        "api_errors": api_errors,
        "scored_cases": sum(1 for r in per_case if "composite" in r),
        "overall_composite_avg": _avg(overall_scores),
        "by_domain_avg": {d: _avg(by_domain_scores[d]) for d in ALLOWED_DOMAINS},
        "by_difficulty_avg": {d: _avg(by_difficulty_scores[d]) for d in ALLOWED_DIFFICULTY},
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "per_case": per_case,
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="benchmark/eval_legalbench_tax_v0.jsonl",
                        help="JSONL eval file path")
    parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), default="validate",
                        help="validate (Stage 0) | dry-run (preview) | live (Stage 1 score)")
    parser.add_argument("--strict", action="store_true",
                        help="Exit non-zero on validation errors")
    parser.add_argument("--api-base", default=API_BASE_DEFAULT,
                        help=f"KG API base URL (default: {API_BASE_DEFAULT})")
    parser.add_argument("--limit", type=int, default=10,
                        help="Per-question retrieval limit (default 10)")
    parser.add_argument("--sleep", type=float, default=0.0,
                        help="Seconds to sleep between live API calls (rate limit, default 0)")
    parser.add_argument("--max-preview", type=int, default=3,
                        help="Cases to print in dry-run (default 3)")
    parser.add_argument("--max-cases", type=int, default=None,
                        help="Cap live mode at first N cases (safety; default = all). "
                             "Use --max-cases 5 the first time you flip --mode live.")
    parser.add_argument("--llm-provider", choices=sorted(ALLOWED_PROVIDERS),
                        default="kg-api",
                        help="kg-api (POST /api/v1/chat, server-side LLM) | "
                             "poe (runner does retrieval + Poe direct call). Default kg-api.")
    parser.add_argument("--poe-model", default=POE_MODEL_DEFAULT,
                        help=f"Poe bot name when --llm-provider poe (default: {POE_MODEL_DEFAULT}). "
                             "Real Poe names are lowercase-dot-version. Examples by ascending "
                             "cost/100q: gpt-5.4-nano ($0.15), gemini-3.1-flash-lite ($0.20), "
                             "gpt-5.4-mini ($0.53), gemini-3.1-pro ($1.58), gpt-5.4 ($1.77), "
                             "gpt-5.5 ($3.55), gpt-5.4-pro ($21.27).")
    parser.add_argument("--output", help="Write JSON results to this path (live mode)")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        print(f"[error] eval file not found: {path}", file=sys.stderr)
        return 2

    records, errors = load_eval(path)

    if errors:
        print(f"=== Validation errors ({len(errors)}) ===")
        for e in errors:
            print(f"  {e}")
        if args.strict:
            return 1

    if args.mode == "validate":
        summary = report(records)
        print("=== LegalBench-Tax v0 distribution ===")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    if args.mode == "dry-run":
        result = run_dry_run(records, args.limit, args.max_preview)
        print("=== LegalBench-Tax v0 dry-run preview ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    # live
    if args.max_cases is not None and args.max_cases > 0:
        records = records[: args.max_cases]
    provider = args.llm_provider
    print(f"=== LegalBench-Tax v0 live scoring (provider={provider}, "
          f"cases={len(records)}, api_base={args.api_base}) ===",
          file=sys.stderr)
    if provider == "kg-api" and not API_KEY:
        print("[warn] KG_API_KEY env var not set; kg-api calls will be unauthenticated",
              file=sys.stderr)
    if provider == "poe" and not POE_API_KEY:
        print("[error] --llm-provider poe requires POE_API_KEY env var", file=sys.stderr)
        return 3
    if provider == "poe":
        print(f"[info] Poe bot = {args.poe_model}; "
              "retrieval still hits kg-api /api/v1/hybrid-search (zero-LLM-cost server side)",
              file=sys.stderr)
    result = run_live(
        records,
        args.api_base,
        args.limit,
        args.sleep,
        provider=provider,
        poe_model=args.poe_model,
        poe_api_key=POE_API_KEY,
    )
    summary_only = {k: v for k, v in result.items() if k != "per_case"}
    print("=== LegalBench-Tax v0 live aggregate ===")
    print(json.dumps(summary_only, indent=2, ensure_ascii=False))

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[written] full per-case results -> {out_path}", file=sys.stderr)

    return 0 if result["api_errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
