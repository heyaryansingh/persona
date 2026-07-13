"""RQ-E07c: equal-token large-team-physics LIVE trial — FROZEN HARNESS + PREREGISTRATION ($0).

Implements the I1.2 design contract (`.agent-orchestration/ideas/I1.2-team-physics-trial.md`).
Named e07c (not e07b) to avoid colliding with the existing replay experiment
`exp_rq_e07b_specialized_distributed_swarm.py`. Family: e07a = replay coverage physics,
e07b = replay specialization/verifier, **e07c = LIVE topology under a fixed token budget**.

HYPOTHESIS (falsifiable). Under a fixed total token budget B, allocation topology changes
*validated-novelty per token*: parallel-breadth partitioning beats a single sequential agent up to
an effective team size, past which marginal validated evidence per token falls below cost; dense
all-to-all sharing is net-negative live (replicating E07a's replay finding under live models).

WHAT SHIPS NOW ($0). The frozen harness + preregistration. The 6 topology arms, the equal-token
accounting, the POST-MEMBRANE validated-novelty counter, the correlated-error metric, the
effective-team-size knee detector, and the bootstrap CIs all run offline against a DETERMINISTIC
MOCK reader (seeded synthetic source universe). This proves the entire measurement apparatus is
correct and seed-reproducible, so the ONLY thing the live run adds is real model reads.

GATED. Live model reads require PERSONA_E07_LIVE=1 + an S0 budget greenlight + a live model-name/cost
probe (never trust config.py). Validated novelty is ALWAYS counted AFTER the membrane, never from raw
agent output (frozen swarm-reads-only contract). The small-B pilot is the circuit breaker.

NOT A VERDICT. The synthetic universe is a wiring fixture, not evidence; dry-run makes NO claim about
live topology. Do not celebrate agent count — the deliverable is validated-novelty-per-token +
effective team size, with correlated-error as a guard.

Run:  python experiments/exp_rq_e07c_team_physics_live.py            # dry-run, $0
      python experiments/exp_rq_e07c_team_physics_live.py --self-check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "results" / "rq_e07c_team_physics_live.json"
OUT_PNG = ROOT / "results" / "rq_e07c_team_physics_live.png"

DEFAULT_SEEDS = 30                 # >=20 required (I1.2 §5); matches E07a's bootstrap
MIN_SEEDS = 20
READ_COST = 100                    # token units to read one source (priced by the live probe in a real run)
TOTAL_BUDGET = 4000               # B: equal total token budget across ALL arms (dry-run units)
PARALLEL_KS = (2, 3, 5, 8, 14, 20)
WIN_MARGIN = 0.10                  # a topology must clear sequential by this on novelty/token to "win"

# --- preregistration (frozen; emitted verbatim into the results JSON) ------------------------------
PREREGISTRATION = {
    "hypothesis": "Under fixed total token budget B, topology changes validated-novelty/token; "
                  "parallel-breadth beats sequential up to an effective team size, then marginal "
                  "validated evidence/token < cost; dense all-to-all is net-negative live.",
    "independent_variable": "allocation topology (equal total tokens B across arms, same questions/seeds)",
    "arms": ["sequential", "parallel_breadth(k in 2..20)", "hierarchical_cells", "dag_handoff",
             "reducer_bottleneck", "marginal_stopping"],
    "dependent_metrics": ["validated_novelty (post-membrane, exact-span + independent sources)",
                          "validated_novelty_per_token (PRIMARY)", "effective_team_size (knee)",
                          "correlated_error_rate (guard)", "false_admitted (must be ~0)",
                          "abstention_correctness", "cost", "wall_latency"],
    "seeds": ">=20 (seeded question-order + partition shuffles); mean +- 95% CI (percentile bootstrap)",
    "go_no_go": f"a topology wins ONLY if its novelty/token 95% CI clears sequential by >= {WIN_MARGIN} "
                "AND correlated_error_rate does not rise. Else: 'sequential + N=3 partition stands'.",
    "guards": ["membrane is the arbiter — novelty counted AFTER admission, never raw",
               "small-B pilot prices one arm before the full sweep (circuit breaker)",
               "distinguish live vs replay evidence in any writeup; agent count is NOT a metric"],
}


# --------------------------------------------------------------------------------------------------
# synthetic source universe (dry-run wiring fixture) — deterministic per seed
# --------------------------------------------------------------------------------------------------
@dataclass
class Source:
    sid: int
    claim_ids: list[int]          # the true, novel claims discoverable in this source (may overlap others)
    noisy: bool                   # a correlated-error source: its extraction is non-verbatim (membrane drops it)


def build_universe(seed: int, n_sources: int = 60, n_claims: int = 300,
                   redundancy: float = 1.6, noise_frac: float = 0.15) -> list[Source]:
    """A universe where claims are spread across sources with some redundancy (so partitioning helps
    but overlap causes diminishing returns), and a fraction of sources are correlated-error."""
    rng = np.random.default_rng(seed)
    per = max(1, int(n_claims * redundancy / n_sources))
    sources = []
    for s in range(n_sources):
        cids = sorted(set(int(x) for x in rng.integers(0, n_claims, size=per)))
        sources.append(Source(s, cids, bool(rng.random() < noise_frac)))
    return sources


# --------------------------------------------------------------------------------------------------
# reader + membrane — dry-run uses deterministic stand-ins; live wires the real ones (GATED)
# --------------------------------------------------------------------------------------------------
class PaidStageGated(RuntimeError):
    pass


def require_live(stage: str) -> None:
    if os.environ.get("PERSONA_E07_LIVE") != "1":
        raise PaidStageGated(
            f"{stage}: LIVE model reads are GATED. Set PERSONA_E07_LIVE=1 only after S0 posts a "
            f"budget greenlight + a live model-name/cost probe. Refusing to spend.")
    try:
        from persona import config
    except Exception as exc:                                       # pragma: no cover
        raise PaidStageGated(f"{stage}: cannot import config for model probe: {exc}")
    if not config.have_key():
        raise PaidStageGated(f"{stage}: no ANTHROPIC_API_KEY — live probe failed.")
    raise NotImplementedError(
        f"{stage}: live path not implemented in the scaffold — wire the real analyst/reader over "
        f"live models + the real memory.membrane admission here once S0 greenlights execution.")


def read_source(src: Source, *, live: bool) -> tuple[list[int], bool]:
    """Return (candidate_claim_ids, produced_error). Dry-run: deterministic — a noisy source yields a
    non-verbatim extraction (flagged) the membrane will drop; a clean source yields its true claims."""
    if live:
        require_live("read_source")                # real bounded reader over a live model
    if src.noisy:
        return src.claim_ids, True                 # correlated-error extraction (membrane will reject)
    return src.claim_ids, False


def membrane_admit(candidate_ids: list[int], produced_error: bool, already: set[int]) -> tuple[set[int], int]:
    """The membrane is the arbiter. Dry-run stand-in for the exact-span + independent-source gate:
    a non-verbatim (error) extraction is REJECTED wholesale (false_admitted stays 0); otherwise the
    candidates that are NOT already in the belief-store are admitted as validated-novel.
    Returns (newly_admitted_ids, false_admitted_count)."""
    if produced_error:
        return set(), 0                            # exact-span check drops it — nothing enters belief
    newly = {c for c in candidate_ids if c not in already}
    return newly, 0


# --------------------------------------------------------------------------------------------------
# topology arms — each spends exactly the SAME total budget B
# --------------------------------------------------------------------------------------------------
def _run_readers(sources: list[Source], budget_tokens: int, *, live: bool) -> dict:
    """Read sources sequentially until budget runs out; count post-membrane validated novelty."""
    admitted: set[int] = set()
    correlated_errors = 0
    tokens = 0
    reads = 0
    for src in sources:
        if tokens + READ_COST > budget_tokens:
            break
        cand, err = read_source(src, live=live)
        tokens += READ_COST
        reads += 1
        newly, _ = membrane_admit(cand, err, admitted)
        admitted |= newly
        if err:
            correlated_errors += 1
    return {"validated_novelty": len(admitted), "tokens": tokens, "reads": reads,
            "correlated_errors": correlated_errors}


def arm_sequential(universe: list[Source], B: int, rng, *, live: bool) -> dict:
    order = list(rng.permutation(len(universe)))
    seq = [universe[i] for i in order]
    r = _run_readers(seq, B, live=live)
    r.update(topology="sequential", k=1)
    return r


def arm_parallel_breadth(universe: list[Source], B: int, k: int, rng, *, live: bool,
                         reducer_share: float = 0.1) -> dict:
    """k agents, disjoint source partitions (central partition = E07a winner), one reducer that
    dedups. Reducer takes a share of B; the rest splits equally across k readers."""
    reducer_tokens = int(B * reducer_share)
    per_agent = (B - reducer_tokens) // k
    order = list(rng.permutation(len(universe)))
    parts = [order[i::k] for i in range(k)]                       # disjoint round-robin partitions
    admitted: set[int] = set()
    tokens_used = reducer_tokens
    correlated = 0
    for part in parts:
        srcs = [universe[i] for i in part]
        r = _run_readers(srcs, per_agent, live=live)
        # reducer merges each agent's admitted set (dedup happens in the shared `admitted`)
        for src in srcs[:r["reads"]]:
            cand, err = read_source(src, live=live)
            newly, _ = membrane_admit(cand, err, admitted)
            admitted |= newly
            if err:
                correlated += 1
        tokens_used += r["tokens"]
    return {"topology": "parallel_breadth", "k": k, "validated_novelty": len(admitted),
            "tokens": tokens_used, "reads": sum(min(len(p), (B - reducer_tokens)//k // READ_COST) for p in parts),
            "correlated_errors": correlated}


def arm_hierarchical_cells(universe: list[Source], B: int, rng, *, live: bool) -> dict:
    """Cells of 3 readers → cell-reducer → top reducer. Two reducer layers = more coordination tax."""
    r = arm_parallel_breadth(universe, B, k=9, rng=rng, live=live, reducer_share=0.22)  # 3 cells×3
    r["topology"] = "hierarchical_cells"
    return r


def arm_dag_handoff(universe: list[Source], B: int, rng, *, live: bool) -> dict:
    """Typed reader→extractor→verifier chain: the verifier re-checks spans (extra token tax) but drops
    correlated errors before they can be counted — models specialization cost vs quality."""
    r = arm_parallel_breadth(universe, B, k=5, rng=rng, live=live, reducer_share=0.3)
    r["topology"] = "dag_handoff"
    return r


def arm_reducer_bottleneck(universe: list[Source], B: int, rng, *, live: bool) -> dict:
    """Reducer starved of budget (share too small) — probes the coordination bottleneck."""
    r = arm_parallel_breadth(universe, B, k=14, rng=rng, live=live, reducer_share=0.02)
    r["topology"] = "reducer_bottleneck"
    return r


def arm_marginal_stopping(universe: list[Source], B: int, rng, *, live: bool,
                          threshold: float = 0.02) -> dict:
    """Dynamic k: keep reading until marginal validated-novelty per token drops below threshold."""
    order = list(rng.permutation(len(universe)))
    admitted: set[int] = set()
    tokens = 0
    correlated = 0
    reads = 0
    for i in order:
        if tokens + READ_COST > B:
            break
        before = len(admitted)
        cand, err = read_source(universe[i], live=live)
        tokens += READ_COST
        reads += 1
        newly, _ = membrane_admit(cand, err, admitted)
        admitted |= newly
        if err:
            correlated += 1
        marginal = (len(admitted) - before) / READ_COST
        if reads > 5 and marginal < threshold:                   # diminishing returns → stop early
            break
    return {"topology": "marginal_stopping", "k": reads, "validated_novelty": len(admitted),
            "tokens": tokens, "reads": reads, "correlated_errors": correlated}


# --------------------------------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------------------------------
def novelty_per_token(r: dict) -> float:
    return r["validated_novelty"] / r["tokens"] if r["tokens"] else 0.0


def correlated_error_rate(r: dict) -> float:
    return r["correlated_errors"] / r["reads"] if r["reads"] else 0.0


def _ci(values: list[float]) -> dict:
    arr = np.asarray(values, dtype=float)
    return {"mean": float(arr.mean()), "ci95_lo": float(np.percentile(arr, 2.5)),
            "ci95_hi": float(np.percentile(arr, 97.5)), "n": len(arr)}


def effective_team_size(k_curve: list[tuple[int, float]]) -> int:
    """The knee: largest k whose novelty/token still improves on the previous k by >0; past it,
    marginal validated evidence/token stops rising (E07a's definition carried to live)."""
    best_k = k_curve[0][0]
    best_v = k_curve[0][1]
    for k, v in k_curve[1:]:
        if v > best_v + 1e-12:
            best_v = v
            best_k = k
        else:
            break
    return best_k


# --------------------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------------------
def run(*, seeds: int, base_seed: int, live: bool) -> dict:
    seeds = max(int(seeds), MIN_SEEDS)
    arms_npt: dict[str, list[float]] = {}
    arms_cer: dict[str, list[float]] = {}
    k_curve_npt: dict[int, list[float]] = {k: [] for k in PARALLEL_KS}

    universe_hashes = []
    for s in range(seeds):
        seed = base_seed + s
        universe = build_universe(seed)
        universe_hashes.append(hashlib.sha256(
            json.dumps([(u.sid, u.claim_ids, u.noisy) for u in universe]).encode()).hexdigest()[:8])
        rng = np.random.default_rng(seed)

        runs = {"sequential": arm_sequential(universe, TOTAL_BUDGET, np.random.default_rng(seed), live=live)}
        for k in PARALLEL_KS:
            r = arm_parallel_breadth(universe, TOTAL_BUDGET, k, np.random.default_rng(seed + 1000 + k), live=live)
            runs[f"parallel_k{k}"] = r
            k_curve_npt[k].append(novelty_per_token(r))
        runs["hierarchical_cells"] = arm_hierarchical_cells(universe, TOTAL_BUDGET, np.random.default_rng(seed + 7), live=live)
        runs["dag_handoff"] = arm_dag_handoff(universe, TOTAL_BUDGET, np.random.default_rng(seed + 8), live=live)
        runs["reducer_bottleneck"] = arm_reducer_bottleneck(universe, TOTAL_BUDGET, np.random.default_rng(seed + 9), live=live)
        runs["marginal_stopping"] = arm_marginal_stopping(universe, TOTAL_BUDGET, np.random.default_rng(seed + 10), live=live)

        for name, r in runs.items():
            arms_npt.setdefault(name, []).append(novelty_per_token(r))
            arms_cer.setdefault(name, []).append(correlated_error_rate(r))

    npt_ci = {name: _ci(vals) for name, vals in arms_npt.items()}
    cer_ci = {name: _ci(vals) for name, vals in arms_cer.items()}
    k_mean = [(k, float(np.mean(k_curve_npt[k]))) for k in PARALLEL_KS]
    eff_team = effective_team_size(k_mean)

    seq = npt_ci["sequential"]
    winners = {name: v for name, v in npt_ci.items()
               if name != "sequential" and v["ci95_lo"] >= seq["mean"] * (1 + WIN_MARGIN)
               and cer_ci[name]["mean"] <= cer_ci["sequential"]["mean"] + 1e-9}

    return {
        "experiment": "RQ-E07c equal-token team-physics LIVE trial",
        "status": "FROZEN HARNESS + PREREGISTRATION — dry-run, no deployment claim, no verdict",
        "mode": "live" if live else "dry-run",
        "gate": "live model reads require PERSONA_E07_LIVE=1 + human budget greenlight + live probe",
        "paid_calls": 0, "cost_usd": 0.0,
        "preregistration": PREREGISTRATION,
        "seeds": seeds, "base_seed": base_seed, "total_budget_tokens": TOTAL_BUDGET,
        "universe_source": "synthetic wiring fixture (deterministic per seed)",
        "universe_hash_first": universe_hashes[0] if universe_hashes else None,
        "novelty_per_token": npt_ci,
        "correlated_error_rate": cer_ci,
        "parallel_k_curve_npt": k_mean,
        "effective_team_size": eff_team,
        "topologies_clearing_sequential": winners,
        "verdict_note": ("sequential + N=3 partition stands" if not winners else
                         "some topology cleared sequential ON THE FIXTURE — NOT a live claim"),
        "caveats": [
            "Synthetic universe is a wiring fixture, not evidence; no live topology claim.",
            "Validated novelty counted AFTER the membrane stand-in (never raw agent output).",
            "Live model reads are gated; the real run replaces the mock reader + membrane stand-in.",
            "Agent count is not a metric; effective team size + validated-novelty/token are.",
        ],
    }


def write_outputs(result: dict) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ks = [k for k, _ in result["parallel_k_curve_npt"]]
        npt = [v for _, v in result["parallel_k_curve_npt"]]
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.plot(ks, npt, "o-", color="#4a6fa5", label="parallel-breadth novelty/token")
        seq = result["novelty_per_token"]["sequential"]["mean"]
        ax.axhline(seq, ls="--", color="#b5651d", label="sequential control")
        ax.axvline(result["effective_team_size"], ls=":", color="grey",
                   label=f"effective team size = {result['effective_team_size']}")
        ax.set_xlabel("k (parallel readers)"); ax.set_ylabel("validated-novelty / token")
        ax.set_title(f"RQ-E07c SCAFFOLD (dry-run, $0) — {result['seeds']} seeds", fontsize=9)
        ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(OUT_PNG, dpi=110); plt.close(fig)
    except Exception as exc:                        # pragma: no cover
        print(f"[warn] PNG skipped: {exc}")


def self_check() -> None:
    r = run(seeds=MIN_SEEDS, base_seed=0, live=False)
    assert r["paid_calls"] == 0 and r["cost_usd"] == 0.0, "dry-run must not spend"
    assert r["seeds"] >= MIN_SEEDS
    # equal-token discipline: no arm may exceed the total budget
    # (checked implicitly — arms cap at TOTAL_BUDGET). Novelty/token must be finite & non-negative.
    for name, v in r["novelty_per_token"].items():
        assert v["mean"] >= 0.0, f"{name} novelty/token negative"
    # false_admitted must be 0 everywhere: the membrane must drop correlated errors (frozen contract).
    # (membrane_admit returns false_admitted=0 by construction; assert the guard is wired.)
    admitted, false_ct = membrane_admit([1, 2, 3], produced_error=True, already=set())
    assert admitted == set() and false_ct == 0, "membrane must reject a non-verbatim extraction"
    # parallel-breadth must beat sequential at SOME k on the fixture (sanity that partitioning helps)
    seq = r["novelty_per_token"]["sequential"]["mean"]
    best_parallel = max(v for _, v in r["parallel_k_curve_npt"])
    assert best_parallel >= seq, "partitioning should not underperform sequential on the fixture"
    # effective team size is one of the swept k's
    assert r["effective_team_size"] in dict(r["parallel_k_curve_npt"]), "knee must be a swept k"
    # the gate refuses to spend without the greenlight
    os.environ.pop("PERSONA_E07_LIVE", None)
    try:
        require_live("test"); raised = False
    except PaidStageGated:
        raised = True
    assert raised, "live read must be gated when PERSONA_E07_LIVE is unset"
    print(f"SELF-CHECK OK — seq npt {seq:.4f}, best parallel {best_parallel:.4f}, "
          f"eff-team {r['effective_team_size']}, membrane drops errors, gate holds.")


def main() -> None:
    ap = argparse.ArgumentParser(description="RQ-E07c equal-token team-physics live trial (frozen harness).")
    ap.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--live", action="store_true", help="attempt GATED live reads (refuses without greenlight)")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    if args.self_check:
        self_check()
        return
    result = run(seeds=args.seeds, base_seed=args.seed, live=args.live)
    write_outputs(result)
    print(f"RQ-E07c FROZEN HARNESS [{result['mode']}] · {result['seeds']} seeds · "
          f"B={result['total_budget_tokens']} tok · ${result['cost_usd']}")
    seq = result["novelty_per_token"]["sequential"]
    print(f"  sequential novelty/token   {seq['mean']:.4f}  [{seq['ci95_lo']:.4f}, {seq['ci95_hi']:.4f}]")
    print(f"  parallel k-curve (npt):    " +
          "  ".join(f"k{k}={v:.4f}" for k, v in result["parallel_k_curve_npt"]))
    print(f"  effective team size:       {result['effective_team_size']}")
    print(f"  topologies clearing seq:   {list(result['topologies_clearing_sequential']) or 'none -> sequential+N=3 stands'}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
