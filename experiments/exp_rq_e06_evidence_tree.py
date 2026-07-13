"""RQ-E06: evidence-tree / derivation-constrained synthesis — SCAFFOLD (dry-run, $0 by default).

HYPOTHESES (from ideas/I1.1):
  H1  A derivation gate — a synthesis statement survives only if EVERY premise it cites is a grounded
      claim AND the premises' qualifiers are mutually compatible — produces >=50% fewer UNSUPPORTED
      synthesis statements than free-text synthesis.        [structural, deterministic, $0 — measured here]
  H2  Qualifier-aware extraction gains >=10 points of qualifier-recall over a no-qualifier baseline.
                                                            [needs real model extraction — PAID, GATED]

WHAT THIS FILE DOES ($0). It measures H1 structurally over a hand-authored WIRING FIXTURE of synthesis
statements: each cites premise claim-ids and carries a gold `supported` label. The `free` arm keeps
every candidate statement; the `derivation` arm keeps a statement only if the gate passes. We report
the unsupported-statement rate per arm and the % reduction, with mean ± 95% CI over >=20 bootstrap
seeds. H2 and the real LLM synthesis are PAID and GATED (PERSONA_E06_LIVE=1 + budget greenlight).

NOT A VERDICT. The fixture is test scaffolding, not gold; no deployment claim is made. The real run
wires S6's derivation-constrained synthesizer + live extraction over held-out text. Per the frozen
contract, labels are never synthesized.

Run:  python experiments/exp_rq_e06_evidence_tree.py            # dry-run, $0
      python experiments/exp_rq_e06_evidence_tree.py --self-check
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "results" / "rq_e06_evidence_tree.json"
OUT_PNG = ROOT / "results" / "rq_e06_evidence_tree.png"

DEFAULT_SEEDS = 200
MIN_SEEDS = 20
H1_GATE = 0.50            # >=50% fewer unsupported statements to pass H1


# --------------------------------------------------------------------------------------------------
# data model
# --------------------------------------------------------------------------------------------------
@dataclass
class Claim:
    claim_id: str
    grounded: bool                      # has an exact-span source record (READ provenance)
    qualifiers: dict = field(default_factory=dict)


@dataclass
class Statement:
    sid: str
    premises: list[str]                 # claim-ids this synthesis statement rests on
    supported: bool                     # GOLD: is it actually supported by grounded, compatible premises?


@dataclass
class Case:
    claims: dict[str, Claim]
    statements: list[Statement]


# --------------------------------------------------------------------------------------------------
# the derivation gate — deterministic, $0. This is the structural core of H1.
# --------------------------------------------------------------------------------------------------
def qualifiers_compatible(a: dict, b: dict) -> bool:
    """Two premises conflict if they fix the SAME qualifier field to different values (e.g. one
    in_vivo, one in_vitro; or opposite directions) — that is context_divergence per §B, not support.
    Missing fields don't conflict (unknown, not contradictory)."""
    for key in ("model_system", "direction", "population", "timepoint"):
        va, vb = a.get(key), b.get(key)
        if va is not None and vb is not None and va != vb:
            return False
    return True


def statement_supported(stmt: Statement, claims: dict[str, Claim]) -> bool:
    """A statement is structurally supported iff every premise resolves to a GROUNDED claim and the
    premises are pairwise qualifier-compatible. This is the derivation gate the constrained
    synthesizer would enforce."""
    prem = [claims.get(pid) for pid in stmt.premises]
    if not stmt.premises or any(c is None or not c.grounded for c in prem):
        return False
    for i in range(len(prem)):
        for j in range(i + 1, len(prem)):
            if not qualifiers_compatible(prem[i].qualifiers, prem[j].qualifiers):
                return False
    return True


# --------------------------------------------------------------------------------------------------
# arms
# --------------------------------------------------------------------------------------------------
def unsupported_rate(kept: list[Statement]) -> float:
    """Fraction of KEPT statements that are actually unsupported (gold). Lower = better."""
    if not kept:
        return 0.0
    return sum(0 if s.supported else 1 for s in kept) / len(kept)


def run_arm(case: Case, *, arm: str) -> list[Statement]:
    if arm == "free":
        return list(case.statements)                               # baseline: emit everything
    if arm == "derivation":
        return [s for s in case.statements if statement_supported(s, case.claims)]
    raise ValueError(arm)


# --------------------------------------------------------------------------------------------------
# PAID stages — GATED (H2 qualifier-recall + real LLM synthesis over held-out text)
# --------------------------------------------------------------------------------------------------
class PaidStageGated(RuntimeError):
    pass


def require_live(stage: str) -> None:
    if os.environ.get("PERSONA_E06_LIVE") != "1":
        raise PaidStageGated(
            f"{stage}: PAID stage GATED. Set PERSONA_E06_LIVE=1 only after S0 posts a budget "
            f"greenlight + a live model-name/cost probe. Refusing to spend.")
    try:
        from persona import config
    except Exception as exc:                                       # pragma: no cover
        raise PaidStageGated(f"{stage}: cannot import config for model probe: {exc}")
    if not config.have_key():
        raise PaidStageGated(f"{stage}: no ANTHROPIC_API_KEY — live probe failed.")
    raise NotImplementedError(
        f"{stage}: live path not implemented in the scaffold — wire real synthesis/extraction here "
        f"once S0 greenlights RQ-E06 execution.")


def qualifier_recall_gain(*, live: bool):
    if live:
        require_live("qualifier_recall")     # H2: real extraction over held-out text vs no-qualifier
    return "gated"


# --------------------------------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------------------------------
def _bootstrap(values: list[float], seeds: int, base_seed: int) -> dict | None:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    arr = np.asarray(vals, dtype=float)
    means = np.empty(seeds)
    for s in range(seeds):
        rng = np.random.default_rng(base_seed + s)
        means[s] = arr[rng.integers(0, len(arr), len(arr))].mean()
    return {"mean": float(arr.mean()), "ci95_lo": float(np.percentile(means, 2.5)),
            "ci95_hi": float(np.percentile(means, 97.5)), "n": len(arr)}


def eval_case(case: Case) -> dict:
    free = run_arm(case, arm="free")
    deriv = run_arm(case, arm="derivation")
    uf, ud = unsupported_rate(free), unsupported_rate(deriv)
    reduction = (uf - ud) / uf if uf > 0 else 0.0
    # of the statements the derivation arm DROPPED, how many were truly unsupported? (gate precision)
    dropped = [s for s in case.statements if s not in deriv]
    drop_precision = (sum(1 for s in dropped if not s.supported) / len(dropped)) if dropped else None
    # did the gate wrongly drop a supported statement? (false drops — the anti-gaming guard)
    false_drops = sum(1 for s in dropped if s.supported)
    return {"unsupported_free": uf, "unsupported_derivation": ud, "reduction": reduction,
            "kept_free": len(free), "kept_derivation": len(deriv),
            "drop_precision": drop_precision, "false_drops": false_drops}


# --------------------------------------------------------------------------------------------------
# wiring fixture — hand-authored, NON-SCIENTIFIC scaffolding
# --------------------------------------------------------------------------------------------------
def fixture_case() -> Case:
    claims = {
        "c_grounded_a": Claim("c_grounded_a", True, {"model_system": "in_vivo", "direction": "+"}),
        "c_grounded_b": Claim("c_grounded_b", True, {"model_system": "in_vivo", "direction": "+"}),
        "c_grounded_c": Claim("c_grounded_c", True, {"model_system": "cohort"}),
        "c_invitro":    Claim("c_invitro", True, {"model_system": "in_vitro", "direction": "-"}),
        "c_ungrounded": Claim("c_ungrounded", False, {}),          # no exact-span record
    }
    statements = [
        # supported: grounded + compatible premises
        Statement("s1", ["c_grounded_a", "c_grounded_b"], supported=True),
        Statement("s2", ["c_grounded_c"], supported=True),
        # unsupported: cites an ungrounded claim -> free keeps it (bad), derivation drops it (good)
        Statement("s3", ["c_grounded_a", "c_ungrounded"], supported=False),
        Statement("s4", ["c_ungrounded"], supported=False),
        # unsupported: qualifier conflict (in_vivo + vs in_vitro -) -> context_divergence, not support
        Statement("s5", ["c_grounded_a", "c_invitro"], supported=False),
        # unsupported: cites nothing -> a free-floating synthesis assertion
        Statement("s6", [], supported=False),
    ]
    return Case(claims=claims, statements=statements)


def load_case(path: str | None) -> tuple[Case, str]:
    if path:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        claims = {c["claim_id"]: Claim(c["claim_id"], bool(c["grounded"]), c.get("qualifiers", {}))
                  for c in raw["claims"]}
        stmts = [Statement(s["sid"], list(s["premises"]), bool(s["supported"])) for s in raw["statements"]]
        return Case(claims, stmts), f"human-labeled:{Path(path).name}"
    return fixture_case(), "wiring-fixture (NON-SCIENTIFIC scaffold)"


def run(*, case_path: str | None, seeds: int, base_seed: int, live: bool) -> dict:
    seeds = max(int(seeds), MIN_SEEDS)
    case, source = load_case(case_path)
    m = eval_case(case)
    # bootstrap the reduction over resampled statement sets (statement-level uncertainty)
    stmts = case.statements
    red_samples = np.empty(seeds)
    for s in range(seeds):
        rng = np.random.default_rng(base_seed + s)
        idx = rng.integers(0, len(stmts), len(stmts))
        sample = Case(case.claims, [stmts[i] for i in idx])
        em = eval_case(sample)
        red_samples[s] = em["reduction"]
    reduction_ci = {"mean": float(np.mean(red_samples)),
                    "ci95_lo": float(np.percentile(red_samples, 2.5)),
                    "ci95_hi": float(np.percentile(red_samples, 97.5)), "n": len(stmts)}
    h1_pass = bool(reduction_ci["ci95_lo"] >= H1_GATE)
    return {
        "experiment": "RQ-E06 evidence-tree / derivation-constrained synthesis",
        "status": "SCAFFOLD — dry-run, no deployment claim, no scientific verdict",
        "mode": "live" if live else "dry-run",
        "gate": "H2 + real synthesis are PAID; require PERSONA_E06_LIVE=1 + human budget greenlight",
        "paid_calls": 0, "cost_usd": 0.0,
        "case_source": source, "n_statements": len(case.statements), "n_claims": len(case.claims),
        "seeds": seeds, "base_seed": base_seed, "h1_gate": H1_GATE,
        "H1_unsupported_reduction": reduction_ci, "H1_pass": h1_pass,
        "H2_qualifier_recall_gain": qualifier_recall_gain(live=live),
        "detail": m,
        "caveats": [
            "H1 is measured structurally over a wiring fixture (not gold) — no deployment claim.",
            "H2 (qualifier-recall gain) and real LLM synthesis are gated paid stages, not run here.",
            "false_drops must stay 0: the gate must never drop a genuinely-supported statement.",
        ],
    }


def write_outputs(result: dict) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        d = result["detail"]
        fig, ax = plt.subplots(figsize=(7, 4.2))
        bars = ["unsupported\n(free)", "unsupported\n(derivation)", "reduction"]
        vals = [d["unsupported_free"], d["unsupported_derivation"],
                result["H1_unsupported_reduction"]["mean"]]
        ax.bar(range(3), vals, color=["#b5651d", "#4a6fa5", "#3c8d5a"])
        ax.axhline(H1_GATE, ls="--", color="grey", lw=1, label=f"H1 gate {H1_GATE:.0%}")
        ax.set_xticks(range(3)); ax.set_xticklabels(bars, fontsize=9)
        ax.set_ylim(0, 1.05); ax.legend(fontsize=8)
        ax.set_title(f"RQ-E06 SCAFFOLD (dry-run, $0) — {result['case_source']} · "
                     f"{result['seeds']} seeds", fontsize=9)
        fig.tight_layout(); fig.savefig(OUT_PNG, dpi=110); plt.close(fig)
    except Exception as exc:                        # pragma: no cover
        print(f"[warn] PNG skipped: {exc}")


def self_check() -> None:
    r = run(case_path=None, seeds=MIN_SEEDS, base_seed=0, live=False)
    assert r["paid_calls"] == 0 and r["cost_usd"] == 0.0, "dry-run must not spend"
    assert r["seeds"] >= MIN_SEEDS
    assert r["H2_qualifier_recall_gain"] == "gated", "H2 must be gated in dry-run"
    d = r["detail"]
    # the derivation gate must strictly cut unsupported statements on the fixture
    assert d["unsupported_derivation"] < d["unsupported_free"], "gate must reduce unsupported rate"
    # and it must NEVER drop a genuinely-supported statement (anti-gaming guard)
    assert d["false_drops"] == 0, "gate wrongly dropped a supported statement"
    # every dropped statement was truly unsupported on this fixture
    assert d["drop_precision"] == 1.0, "gate dropped a supported statement"
    # gate refuses to spend without the greenlight
    os.environ.pop("PERSONA_E06_LIVE", None)
    try:
        require_live("test"); raised = False
    except PaidStageGated:
        raised = True
    assert raised, "paid stage must be gated when PERSONA_E06_LIVE is unset"
    print(f"SELF-CHECK OK — unsupported {d['unsupported_free']:.2f}->{d['unsupported_derivation']:.2f}, "
          f"0 false drops, H2 gated, gate holds.")


def main() -> None:
    ap = argparse.ArgumentParser(description="RQ-E06 evidence-tree synthesis harness (scaffold).")
    ap.add_argument("--case", default=None, help="path to a human-labeled case (JSON)")
    ap.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--live", action="store_true", help="attempt GATED paid stages (refuses without greenlight)")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    if args.self_check:
        self_check()
        return
    result = run(case_path=args.case, seeds=args.seeds, base_seed=args.seed, live=args.live)
    write_outputs(result)
    r = result["H1_unsupported_reduction"]
    d = result["detail"]
    print(f"RQ-E06 SCAFFOLD [{result['mode']}] · {result['case_source']} · "
          f"{result['n_statements']} statements · {result['seeds']} seeds · ${result['cost_usd']}")
    print(f"  unsupported: free {d['unsupported_free']:.3f} -> derivation {d['unsupported_derivation']:.3f}")
    print(f"  H1 reduction {r['mean']:.3f}  [{r['ci95_lo']:.3f}, {r['ci95_hi']:.3f}]  "
          f"(gate {H1_GATE:.0%}, pass={result['H1_pass']})")
    print(f"  false_drops {d['false_drops']} · H2 {result['H2_qualifier_recall_gain']}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
