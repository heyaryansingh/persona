"""RQ-HT01: does branching (F1.1) reach a verdict with fewer paid model calls than the linear chain
on DECOMPOSABLE questions, without losing grounding? — SCAFFOLD (dry-run, $0 by default).

HYPOTHESIS (PRD-01 F1.1). On decomposable questions (two independent sub-claims each), the branch
plan reaches a SUPPORTED-or-refuted verdict on the parent in ≤ the linear chain's paid-model-call
count, with grounding-rate no worse by >2pp.

MECHANISM (why decomposition can win — least-to-most, Zhou et al. arXiv:2205.10625). The linear plan's
single `investigate` step must ground BOTH sub-claims in one pass (success prob g1·g2 per attempt), so
a conflated hard pair triggers retries. The branch plan runs one `investigate` per sub-claim (success
prob g_i each), grounding them independently — more base steps (2 analyze vs 1) but far fewer retries
when the pair is genuinely two problems. Whether that nets out FEWER total calls is exactly what this
measures; it is NOT assumed.

WHAT SHIPS NOW ($0). A deterministic simulation over the REAL plans (`_branch_plan` / `DEFAULT_PLAN`
from investigation.py — the step counts are the actual code, not invented) with a seeded retry model,
≥20 bootstrap seeds, mean ± 95% CI, and the F1.1 go/no-go gate. The LIVE arm — running the real
analyst on real decomposable questions to count actual paid calls — is GATED (PERSONA_HT01_LIVE=1 +
budget greenlight + live probe). No deployment/superiority claim from the dry-run.

Run:  python experiments/exp_ht01_branch_vs_linear.py            # dry-run, $0
      python experiments/exp_ht01_branch_vs_linear.py --self-check
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:                      # allow `python experiments/exp_ht01_*.py` from root
    sys.path.insert(0, str(ROOT))

from persona.research.investigation import DEFAULT_PLAN, _branch_plan  # noqa: E402

OUT_JSON = ROOT / "results" / "ht01_branch_vs_linear.json"
OUT_PNG = ROOT / "results" / "ht01_branch_vs_linear.png"

DEFAULT_SEEDS = 200
MIN_SEEDS = 20
N_QUESTIONS = 40           # decomposable questions per trial
MAX_RETRIES = 3            # bounded retries per analyze step (matches analyst's turn cap discipline)
GROUNDING_TOL = 0.02       # F1.1 gate: branch grounding no worse than linear by >2pp

# Paid-model step types up to a verdict (gather reads, harvest extracts, investigate computes,
# consolidate synthesizes). finalize/write/critique are post-verdict; not counted toward "to-verdict".
_PAID_TO_VERDICT = {"gather", "harvest", "investigate", "consolidate"}


def _base_calls(plan) -> tuple[int, int]:
    """(non-analyze paid steps, analyze steps) to a verdict, counted from the REAL plan step list."""
    analyze = sum(1 for s in plan if s[1] == "investigate")
    other = sum(1 for s in plan if s[1] in _PAID_TO_VERDICT and s[1] != "investigate")
    return other, analyze


class PaidStageGated(RuntimeError):
    pass


def require_live(stage: str) -> None:
    if os.environ.get("PERSONA_HT01_LIVE") != "1":
        raise PaidStageGated(
            f"{stage}: LIVE analyst runs are GATED. Set PERSONA_HT01_LIVE=1 only after S0 posts a "
            f"budget greenlight + a live model-name/cost probe. Refusing to spend.")
    try:
        from persona import config
    except Exception as exc:                                       # pragma: no cover
        raise PaidStageGated(f"{stage}: cannot import config for model probe: {exc}")
    if not config.have_key():
        raise PaidStageGated(f"{stage}: no ANTHROPIC_API_KEY — live probe failed.")
    raise NotImplementedError(
        f"{stage}: live path not implemented in the scaffold — run the real analyst on real "
        f"decomposable questions and count actual paid calls once S0 greenlights execution.")


def _attempts(rng, p_success: float) -> tuple[int, bool]:
    """Seeded retry model: attempts until an analyze step grounds its target, capped at MAX_RETRIES+1.
    Returns (attempts_used, grounded)."""
    p = min(max(float(p_success), 1e-6), 1.0)
    for a in range(1, MAX_RETRIES + 2):
        if rng.random() < p:
            return a, True
    return MAX_RETRIES + 1, False


def _simulate_question(rng, *, live: bool) -> dict:
    if live:
        require_live("analyst_run")             # real analyst on a real decomposable question
    # two independent sub-claims with per-attempt grounding probabilities (the question's difficulty)
    g1, g2 = rng.uniform(0.35, 0.9), rng.uniform(0.35, 0.9)
    lin_other, lin_analyze = _base_calls(DEFAULT_PLAN)
    br_other, br_analyze = _base_calls(_branch_plan(["sub A", "sub B"]))

    # LINEAR: one analyze must ground BOTH sub-claims together (prob g1*g2 per attempt).
    lin_attempts, lin_ok = _attempts(rng, g1 * g2)
    lin_calls = lin_other + lin_attempts                    # analyze attempts + the other paid steps
    lin_grounded = 2 if lin_ok else 0                       # conflated: all-or-nothing on the pair

    # BRANCH: one analyze per sub-claim, grounded independently.
    a1, ok1 = _attempts(rng, g1)
    a2, ok2 = _attempts(rng, g2)
    br_calls = br_other + a1 + a2                           # two analyze chains + other paid steps
    br_grounded = int(ok1) + int(ok2)

    return {"linear_calls": lin_calls, "branch_calls": br_calls,
            "linear_grounding": lin_grounded / 2, "branch_grounding": br_grounded / 2}


def run(*, seeds: int, base_seed: int, live: bool) -> dict:
    seeds = max(int(seeds), MIN_SEEDS)
    lin_calls, br_calls, lin_gr, br_gr = [], [], [], []
    for s in range(seeds):
        rng = np.random.default_rng(base_seed + s)
        per_q = [_simulate_question(rng, live=live) for _ in range(N_QUESTIONS)]
        lin_calls.append(np.mean([q["linear_calls"] for q in per_q]))
        br_calls.append(np.mean([q["branch_calls"] for q in per_q]))
        lin_gr.append(np.mean([q["linear_grounding"] for q in per_q]))
        br_gr.append(np.mean([q["branch_grounding"] for q in per_q]))

    def ci(x):
        a = np.asarray(x)
        return {"mean": float(a.mean()), "ci95_lo": float(np.percentile(a, 2.5)),
                "ci95_hi": float(np.percentile(a, 97.5))}

    calls_delta = np.asarray(br_calls) - np.asarray(lin_calls)     # negative = branch cheaper
    gr_delta = np.asarray(br_gr) - np.asarray(lin_gr)              # positive = branch grounds more
    branch_cheaper = bool(np.percentile(calls_delta, 97.5) <= 0)  # CI of delta ≤ 0
    grounding_ok = bool(np.percentile(gr_delta, 2.5) >= -GROUNDING_TOL)
    return {
        "experiment": "RQ-HT01 branch vs linear (paid-calls-to-verdict on decomposable questions)",
        "status": "SCAFFOLD — dry-run, no deployment claim, no verdict",
        "mode": "live" if live else "dry-run",
        "gate": "LIVE analyst runs require PERSONA_HT01_LIVE=1 + human budget greenlight + live probe",
        "paid_calls": 0, "cost_usd": 0.0,
        "seeds": seeds, "n_questions": N_QUESTIONS, "max_retries": MAX_RETRIES,
        "real_plan_base": {"linear": _base_calls(DEFAULT_PLAN),
                           "branch_2sub": _base_calls(_branch_plan(["a", "b"]))},
        "linear_calls": ci(lin_calls), "branch_calls": ci(br_calls),
        "linear_grounding": ci(lin_gr), "branch_grounding": ci(br_gr),
        "calls_delta_branch_minus_linear": ci(calls_delta.tolist()),
        "grounding_delta_branch_minus_linear": ci(gr_delta.tolist()),
        "go_no_go": {"branch_cheaper_or_equal": branch_cheaper,
                     "grounding_not_worse_by_2pp": grounding_ok,
                     "PASS": branch_cheaper and grounding_ok},
        "caveats": [
            "Simulation over the REAL plan step-counts with a SEEDED retry model — not live evidence.",
            "The retry model is the load-bearing assumption; the live arm (gated) measures actual calls.",
            "No superiority/deployment claim from dry-run; go/no-go here is a design smoke test only.",
        ],
    }


def write_outputs(result: dict) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4.2))
        arms = ["linear", "branch"]
        means = [result["linear_calls"]["mean"], result["branch_calls"]["mean"]]
        los = [means[0] - result["linear_calls"]["ci95_lo"], means[1] - result["branch_calls"]["ci95_lo"]]
        his = [result["linear_calls"]["ci95_hi"] - means[0], result["branch_calls"]["ci95_hi"] - means[1]]
        ax.bar(arms, means, yerr=[los, his], capsize=5, color=["#b5651d", "#4a6fa5"])
        ax.set_ylabel("mean paid calls to verdict")
        ax.set_title(f"RQ-HT01 SCAFFOLD (dry-run, $0) — {result['seeds']} seeds · "
                     f"PASS={result['go_no_go']['PASS']}", fontsize=9)
        fig.tight_layout(); fig.savefig(OUT_PNG, dpi=110); plt.close(fig)
    except Exception as exc:                        # pragma: no cover
        print(f"[warn] PNG skipped: {exc}")


def self_check() -> None:
    r = run(seeds=MIN_SEEDS, base_seed=0, live=False)
    assert r["paid_calls"] == 0 and r["cost_usd"] == 0.0, "dry-run must not spend"
    assert r["seeds"] >= MIN_SEEDS
    # the base step-counts come from the REAL plans: linear has 1 analyze, branch(2 sub) has 2
    assert r["real_plan_base"]["linear"][1] == 1, r["real_plan_base"]
    assert r["real_plan_base"]["branch_2sub"][1] == 2, r["real_plan_base"]
    # branch must ground MORE (independent sub-claims) — the mechanism the whole feature rests on
    assert r["branch_grounding"]["mean"] >= r["linear_grounding"]["mean"], (
        r["branch_grounding"], r["linear_grounding"])
    # gate refuses to spend without greenlight
    os.environ.pop("PERSONA_HT01_LIVE", None)
    try:
        require_live("t"); raised = False
    except PaidStageGated:
        raised = True
    assert raised, "live run must be gated"
    print(f"SELF-CHECK OK — linear grounding {r['linear_grounding']['mean']:.3f} vs branch "
          f"{r['branch_grounding']['mean']:.3f}; base analyze 1 vs 2 (real plans); gate holds.")


def main() -> None:
    ap = argparse.ArgumentParser(description="RQ-HT01 branch-vs-linear paid-cost scaffold.")
    ap.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--live", action="store_true", help="attempt GATED live analyst runs (refuses without greenlight)")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    if args.self_check:
        self_check()
        return
    result = run(seeds=args.seeds, base_seed=args.seed, live=args.live)
    write_outputs(result)
    print(f"RQ-HT01 SCAFFOLD [{result['mode']}] · {result['seeds']} seeds · "
          f"{result['n_questions']} questions/trial · ${result['cost_usd']}")
    lc, bc = result["linear_calls"], result["branch_calls"]
    print(f"  paid calls to verdict: linear {lc['mean']:.2f} [{lc['ci95_lo']:.2f},{lc['ci95_hi']:.2f}]"
          f"  branch {bc['mean']:.2f} [{bc['ci95_lo']:.2f},{bc['ci95_hi']:.2f}]")
    lg, bg = result["linear_grounding"], result["branch_grounding"]
    print(f"  grounding rate:        linear {lg['mean']:.3f}  branch {bg['mean']:.3f}")
    print(f"  go/no-go PASS={result['go_no_go']['PASS']} "
          f"(cheaper={result['go_no_go']['branch_cheaper_or_equal']}, "
          f"grounding_ok={result['go_no_go']['grounding_not_worse_by_2pp']})")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
