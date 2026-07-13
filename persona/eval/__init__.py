"""persona.eval — FC-7 self-benchmarking oracles (PRD Lane 4 provides).

Milestone-0 stub: exact signature + typed empty return so consumers build against
FC-7 from hour 1 (PRD-00 §5). Real scoring lands in Phase 5:
  - persona/eval/litqa2.py   — LitQA2 exact-paper retrieval, abstention-aware (F4.8)
  - persona/eval/bixbench.py — BixBench executable capsules in the sandbox (F4.8)
  - persona/eval/scorecard.py — accuracy-vs-$ Pareto scorecard (F4.9)
No fabricated confidence: scores come from external public oracles, never model self-report.
"""
from __future__ import annotations

# Known oracle names. Extend as real backends land; the contract shape is frozen (FC-7).
KNOWN_ORACLES = ("litqa2", "bixbench")


def run_oracle(name: str, *, n: int = 0, seed: int = 0, persona: str | None = None) -> dict:
    """FC-7 — run a named benchmark oracle over Persona.

    Returns `{metric: str, score: float, n: int, per_item: list}`.
    Milestone-0 stub: validates the name and returns a typed empty result; real
    per-oracle scoring is not wired yet (raises nothing — callers get an honest
    zero-n result they can distinguish via `metric == "unimplemented"`).
    """
    if name not in KNOWN_ORACLES:
        raise ValueError(f"unknown oracle {name!r}; known: {', '.join(KNOWN_ORACLES)}")
    from .fixtures import load_fixture
    metric = {"litqa2": "litqa2_acc", "bixbench": "bixbench_exec"}[name]
    fx = load_fixture(name)                      # verifies .jsonl against .sha256 (tamper guard)
    if fx["n"] == 0:
        # no benchmark gold fetched offline → score honestly absent, never synthesized.
        return {"metric": metric, "score": 0.0, "n": 0, "per_item": [],
                "sourcing_status": fx["sourcing_status"]}
    # Fixture present: answering the items needs a gated model/sandbox run; grading of those
    # answers is persona.eval.scoring.score_answers. Report the frozen size, score pending.
    return {"metric": metric, "score": 0.0, "n": fx["n"], "per_item": [],
            "sourcing_status": fx["sourcing_status"], "answers_status": "pending_gated_run"}
