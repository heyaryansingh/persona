"""Span-weighted consensus (Lane 1 · FC-1) — aggregate several readers' judgments on ONE claim into
a single admit decision that PROTECTS dissent instead of averaging it away.

When N readers independently judge the same candidate claim, a naive majority vote erases a lone
reader who spotted a real problem. Span-weighted consensus instead: (1) weights each vote by the
reader's grounding weight (how well its judgment is tied to an exact source span), (2) reports the
weighted support for admitting, and (3) preserves every dissenting reader as a first-class record
(claim_id, span, weight) so a minority objection can gate escalation rather than vanish. See PRD-01
feature 1.4 (span-weighted consensus with protected dissent) + FC-1 in docs/prd/PRD-00-overview.md.

Milestone-0: real minimal implementation with the FROZEN FC-1 return shape. Deterministic, no model
calls, $0. Downstream lanes build against this signature from hour 1.
"""
from __future__ import annotations


def span_weighted_consensus(reader_outputs) -> dict:
    """Aggregate reader judgments on one claim.

    Input — `reader_outputs`: a list of per-reader dicts. Recognised keys (all optional except a
    judgment): `claim_id`, `claim` (the claim text), `admit` (bool — does this reader admit it?),
    `span` (the exact source span the reader grounded on), `weight` (float grounding weight, default
    1.0). Malformed entries are ignored, never trusted into the result.

    Returns the FROZEN FC-1 shape:
        {claim: str, admit_votes: int, weighted_support: float, dissent: [{claim_id, span, weight}]}
    - `admit_votes`   — how many readers voted to admit.
    - `weighted_support` — admit weight ÷ total weight, in [0,1] (0.0 when there are no readers).
    - `dissent`       — every NON-admitting reader, preserved (protected minority), not averaged out.
    """
    outputs = [o for o in (reader_outputs or []) if isinstance(o, dict)]

    def _weight(o) -> float:
        w = o.get("weight", 1.0)
        try:
            w = float(w)
        except (TypeError, ValueError):
            return 1.0
        return w if w >= 0.0 else 0.0

    total_weight = sum(_weight(o) for o in outputs)
    admits = [o for o in outputs if o.get("admit")]
    dissenters = [o for o in outputs if not o.get("admit")]

    admit_weight = sum(_weight(o) for o in admits)
    weighted_support = round(admit_weight / total_weight, 4) if total_weight > 0 else 0.0

    # claim text: prefer an admitting reader's, else any reader's, else empty
    claim = next((str(o.get("claim", "")) for o in admits if o.get("claim")),
                 next((str(o.get("claim", "")) for o in outputs if o.get("claim")), ""))

    dissent = [{"claim_id": str(o.get("claim_id", "")), "span": str(o.get("span", "")),
                "weight": _weight(o)} for o in dissenters]

    return {"claim": claim, "admit_votes": len(admits),
            "weighted_support": weighted_support, "dissent": dissent}


def demo() -> None:
    """Assert-based self-check — the money/decision path leaves one runnable check behind."""
    # two admit (weights 1.0, 0.5), one dissent (weight 2.0): support = 1.5 / 3.5
    out = span_weighted_consensus([
        {"claim_id": "c1", "claim": "X increases Y", "admit": True, "span": "X raised Y.", "weight": 1.0},
        {"claim_id": "c1", "claim": "X increases Y", "admit": True, "span": "Y rose with X.", "weight": 0.5},
        {"claim_id": "c1", "claim": "X increases Y", "admit": False, "span": "No effect seen.", "weight": 2.0},
    ])
    assert out["admit_votes"] == 2, out
    assert out["weighted_support"] == round(1.5 / 3.5, 4), out
    assert len(out["dissent"]) == 1 and out["dissent"][0]["weight"] == 2.0, out
    assert out["claim"] == "X increases Y", out
    # empty input → typed zero
    empty = span_weighted_consensus([])
    assert empty == {"claim": "", "admit_votes": 0, "weighted_support": 0.0, "dissent": []}, empty
    print("consensus.span_weighted_consensus OK")


if __name__ == "__main__":
    demo()
