"""Stage 2 multi-model comparison on first-20 subset.

Compares Nano baseline against N Pro-tier models on the same 20 cases.
Currently configured for: gemini-3.1-pro + gpt-5.5 (cross-vendor pair, dropped
gpt-5.4-pro for cost: $163/M out vs gemini $12 / gpt-5.5 $27).

Reads:
  benchmark/_nano_first20_subset.json                          (Nano baseline)
  benchmark/results_poe_gemini31pro_stage2_20260427.json       (gemini-3.1-pro)
  benchmark/results_poe_gpt55_stage2_20260427.json             (gpt-5.5)

Emits per-axis / per-domain / per-case deltas and verdict.
Verdict thresholds (composite Δ vs nano, averaged across the two Pro models):
  ≥ +0.05 → MODEL-BOUND (recommend prod model upgrade)
  +0.02..+0.05 → MARGINAL (mini-tier middle ground or pivot)
  < +0.02 → EVAL-DESIGN-BOUND (no ROI from model upgrade)

Cross-vendor consistency check: if gemini and gpt-5.5 disagree by ≥0.05
composite avg, flag as VENDOR-VARIANCE — single-model conclusions become
unreliable, treat with caution.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
NANO_PATH = ROOT / "_nano_first20_subset.json"
MODELS = [
    ("gemini-3.1-pro", ROOT / "results_poe_gemini31pro_stage2_20260427.json"),
    ("gpt-5.5", ROOT / "results_poe_gpt55_stage2_20260427.json"),
]

PRICE = {
    "gpt-5.4-nano": (0.18, 1.14),
    "gemini-3.1-pro": (2.02, 12.12),
    "gpt-5.5": (4.55, 27.27),
}


def cost(model: str, in_tok: int, out_tok: int) -> float:
    in_p, out_p = PRICE[model]
    return (in_tok * in_p + out_tok * out_p) / 1_000_000


def load_cases(path: Path) -> dict[str, dict]:
    if not path.exists():
        print(f"WARN: missing {path}")
        return {}
    raw = json.loads(path.read_text())
    cases = raw.get("per_case", raw.get("cases", []))
    return {c["id"]: c for c in cases}


def main() -> int:
    nano = load_cases(NANO_PATH)
    if not nano:
        print(f"ERROR: nano subset missing")
        return 1

    pros: dict[str, dict[str, dict]] = {}
    for name, path in MODELS:
        cases = load_cases(path)
        if cases:
            pros[name] = cases
            print(f"OK loaded {name}: {len(cases)} cases")
        else:
            print(f"SKIP {name}: file missing or empty")

    if not pros:
        print("ERROR: no Pro models loaded")
        return 1

    # Common case set across nano + all loaded pros
    common = sorted(set(nano) & set.intersection(*[set(c) for c in pros.values()]))
    print(f"\n=== STAGE 2 multi-model — {len(common)} cas en commun ({len(pros)} Pros) ===\n")

    if not common:
        print("WARN: pas de cas en commun")
        return 1

    axes = ["anchor_recall", "keyword_overlap", "source_citation", "composite"]

    # --- Per-axis means ---
    print("--- Per-axis means ---")
    print(f"{'axis':18s}  {'nano':>8s}  " + "  ".join(f"{n:>14s}" for n in pros))
    for ax in axes:
        nano_v = mean(nano[i][ax] for i in common)
        pros_v = {n: mean(c[i][ax] for i in common) for n, c in pros.items()}
        line = f"  {ax:18s}  {nano_v:>8.4f}"
        for n in pros:
            d = pros_v[n] - nano_v
            sign = "+" if d >= 0 else ""
            line += f"  {pros_v[n]:>5.4f} ({sign}{d:.3f})"
        print(line)

    # --- Per-domain composite ---
    print("\n--- Per-domain composite ---")
    by_domain_nano = defaultdict(list)
    by_domain_pros: dict[str, dict[str, list[float]]] = {n: defaultdict(list) for n in pros}
    for cid in common:
        d = nano[cid]["domain"]
        by_domain_nano[d].append(nano[cid]["composite"])
        for n, c in pros.items():
            by_domain_pros[n][d].append(c[cid]["composite"])
    print(f"{'domain':8s}  {'nano':>8s}  " + "  ".join(f"{n:>14s}" for n in pros))
    for d in sorted(by_domain_nano):
        n_avg = mean(by_domain_nano[d])
        line = f"  {d:8s}  {n_avg:>8.4f}"
        for n in pros:
            p_avg = mean(by_domain_pros[n][d])
            delta = p_avg - n_avg
            sign = "+" if delta >= 0 else ""
            line += f"  {p_avg:>5.4f} ({sign}{delta:.3f})"
        line += f"  n={len(by_domain_nano[d])}"
        print(line)

    # --- Top per-case lift (averaged across pros) ---
    print(f"\n--- Per-case avg-Pro composite delta (sorted) ---")
    avg_deltas = []
    for cid in common:
        n = nano[cid]["composite"]
        ps = [pros[m][cid]["composite"] for m in pros]
        avg_p = mean(ps)
        avg_deltas.append((cid, n, avg_p, ps, avg_p - n))
    avg_deltas.sort(key=lambda x: -x[4])
    headers = "  " + " | ".join([f"{m:>14s}" for m in pros])
    print(f"  {'id':12s}  {'nano':>6s}  {'avgPro':>7s}  {'Δ':>7s} " + headers)
    for cid, n, ap, ps, d in avg_deltas[:8]:
        psl = "  " + " | ".join([f"{v:>14.4f}" for v in ps])
        print(f"  {cid:12s}  {n:.4f}  {ap:.4f}  {d:+.4f}" + psl)
    print("  ...")
    for cid, n, ap, ps, d in avg_deltas[-5:]:
        psl = "  " + " | ".join([f"{v:>14.4f}" for v in ps])
        print(f"  {cid:12s}  {n:.4f}  {ap:.4f}  {d:+.4f}" + psl)

    # --- Cost ---
    print("\n--- Cost ---")
    nano_in = sum(nano[i]["usage"]["prompt_tokens"] for i in common)
    nano_out = sum(nano[i]["usage"]["completion_tokens"] for i in common)
    nano_cost = cost("gpt-5.4-nano", nano_in, nano_out)
    print(f"  Nano:           in={nano_in:>6,}  out={nano_out:>6,}  ${nano_cost:.4f}")
    pro_costs = {}
    for n, c in pros.items():
        in_t = sum(c[i]["usage"]["prompt_tokens"] for i in common)
        out_t = sum(c[i]["usage"]["completion_tokens"] for i in common)
        cst = cost(n, in_t, out_t)
        pro_costs[n] = cst
        print(f"  {n:14s}  in={in_t:>6,}  out={out_t:>6,}  ${cst:.4f}  ({cst/nano_cost:.0f}× nano)")
    total_pro = sum(pro_costs.values())
    print(f"  TOTAL Pro spend: ${total_pro:.4f}")

    # --- Cross-vendor consistency ---
    nano_comp = mean(nano[i]["composite"] for i in common)
    pro_avg = {n: mean(c[i]["composite"] for i in common) for n, c in pros.items()}
    if len(pros) >= 2:
        names = list(pros.keys())
        spread = max(pro_avg.values()) - min(pro_avg.values())
        if spread >= 0.05:
            consistency = f"VENDOR-VARIANCE (spread={spread:.3f}≥0.05) — interpret with caution"
        else:
            consistency = f"CONSISTENT (spread={spread:.3f}<0.05) — both models agree"
    else:
        consistency = "single model (no cross-check)"
    print(f"\n--- Cross-vendor consistency: {consistency} ---")

    # --- Verdict ---
    print("\n=== VERDICT ===")
    delta_avg = mean(pro_avg.values()) - nano_comp
    print(f"  Composite — Nano: {nano_comp:.4f}")
    for n, v in pro_avg.items():
        print(f"             {n:14s}: {v:.4f}  (Δ={v-nano_comp:+.4f})")
    print(f"  Average Pro Δ vs Nano: {delta_avg:+.4f}  ({delta_avg*100:+.2f}pp)")

    if delta_avg >= 0.05:
        verdict = "MODEL-BOUND"
        rec = ("Plafond LIÉ AU MODÈLE. Production nano vs Pro a ROI positif. "
               "Recommander mini-tier comme middle-ground (eval mini next).")
    elif delta_avg >= 0.02:
        verdict = "MARGINAL"
        rec = ("Lift Pro modeste. mini-tier probablement seuil rentable. "
               "OU pivoter vers product (yiclaw) avec nano comme baseline acceptable.")
    else:
        verdict = "EVAL-DESIGN-BOUND"
        rec = ("Pro n'aide pas (ou peu). Plafond est dans eval-design "
               "(anchors/keywords/sources design). ROI positif uniquement via "
               "W6-full retrieval rewrite OU pivot vers product.")

    print(f"  Verdict: {verdict}")
    print(f"  Recommendation: {rec}")
    print(f"  Cross-vendor: {consistency}")

    # Persist verdict for downstream use
    out = {
        "common_n": len(common),
        "nano_composite": nano_comp,
        "pro_composites": pro_avg,
        "delta_avg": delta_avg,
        "verdict": verdict,
        "consistency": consistency,
        "pro_costs_usd": pro_costs,
        "total_pro_spend_usd": total_pro,
    }
    out_path = ROOT / "_stage2_verdict.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\nPersisted verdict → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
