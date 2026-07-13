"""Abstention-aware benchmark scoring (PRD-04 F4.8/F4.9, RQ-E15).

The load-bearing property: a confident-wrong answer scores STRICTLY BELOW an honest
abstention, so "I'm unsure" is never punished worse than a confident guess that's wrong.
This is the canonical proper-scoring rule for calibrated QA (LitQA2-style sure/unsure).

No fabricated confidence: outcomes come from grading answers against an external oracle,
never from a model self-reported confidence. RQ-E15 (experiments/) tunes the penalty
magnitude across ≥20 seeds; this module fixes the sign relationship the harness relies on.
"""
from __future__ import annotations

# Per-outcome reward. `wrong` is the only negative → abstaining always beats guessing
# wrong. Magnitudes are the RQ-E15 knob; the sign order (correct > abstain > wrong) is frozen.
CORRECT, ABSTAIN, WRONG = 1.0, 0.0, -1.0


def _outcome(item: dict) -> str:
    """Classify a graded answer: 'correct' | 'wrong' | 'abstain'.
    Abstain only when explicitly flagged or the answer field is present-and-unsure —
    a missing `answer` key means the item is graded by `correct`, not an abstention."""
    if item.get("abstained"):
        return "abstain"
    if "answer" in item and item["answer"] in (None, "", "unsure"):
        return "abstain"
    return "correct" if item.get("correct") else "wrong"


def score_answers(items) -> dict:
    """Grade a list of answers `[{correct: bool, abstained?: bool, answer?}]`.

    Returns `{metric, score, n, coverage, accuracy_on_answered, per_item}` where
    `score` is the mean per-item reward in [-1, 1]. Empty input → a typed zero result.
    """
    items = list(items or [])
    n = len(items)
    reward = {"correct": CORRECT, "abstain": ABSTAIN, "wrong": WRONG}
    per, answered, correct = [], 0, 0
    for it in items:
        o = _outcome(it or {})
        per.append({"outcome": o, "reward": reward[o]})
        if o != "abstain":
            answered += 1
            correct += (o == "correct")
    score = (sum(p["reward"] for p in per) / n) if n else 0.0
    return {
        "metric": "abstention_adjusted",
        "score": score,
        "n": n,
        "coverage": (answered / n) if n else 0.0,
        "accuracy_on_answered": (correct / answered) if answered else 0.0,
        "per_item": per,
    }
