"""RQ-E15 core property: abstention-aware scoring penalises confident-wrong strictly
more than honest abstention (Lane 4 / S3, PRD-04 F4.8)."""
from persona.eval.scoring import score_answers


def test_confident_wrong_scores_below_abstain():
    wrong = score_answers([{"correct": False}] * 3)
    abstain = score_answers([{"abstained": True}] * 3)
    correct = score_answers([{"correct": True}] * 3)
    assert wrong["score"] < abstain["score"] < correct["score"], "order: wrong < abstain < correct"
    assert (wrong["score"], abstain["score"], correct["score"]) == (-1.0, 0.0, 1.0)


def test_mixed_metrics():
    r = score_answers([{"correct": True}, {"abstained": True}, {"correct": False}])
    assert r["score"] == 0.0                      # (1 + 0 - 1) / 3
    assert r["coverage"] == 2 / 3                  # 2 answered of 3
    assert r["accuracy_on_answered"] == 0.5        # 1 correct of 2 answered
    assert r["n"] == 3


def test_answer_unsure_counts_as_abstain():
    r = score_answers([{"answer": "unsure"}, {"answer": None}])
    assert all(p["outcome"] == "abstain" for p in r["per_item"])
    assert r["coverage"] == 0.0


def test_empty_is_typed_zero():
    r = score_answers([])
    assert r["n"] == 0 and r["score"] == 0.0 and r["per_item"] == []
