"""Recomposition/feasibility gate (PRD F2.4) — is a candidate even physically/logically possible?

Pure/offline (no FalkorDB, no model): feasibility_flags takes a candidate + a KG and flags it
implausible so the membrane routes it to a human. Two deterministic checks:
  * sign-vs-anchor — effect_sign contradicts an ANCHORED belief on the same (subject,object) pair.
  * magnitude-range — a ratio/fold effect size out of a sane range (non-positive / absurdly large).
"""
from persona.memory import membrane


class FakeKG:
    """crosscheck returns opposite-sign claims as `contradict`; provenance reports anchored state.
    `anchored_ids` = the set of contradicting claim_ids that are anchored (verified) beliefs."""
    def __init__(self, contradict_ids=(), anchored_ids=()):
        self._contra = list(contradict_ids)
        self._anchored = set(anchored_ids)

    def crosscheck(self, subject, obj, effect_sign):
        return {"support": [], "contradict": [{"claim_id": c, "text": f"{subject} vs {obj}"}
                                              for c in self._contra]}

    def provenance(self, claim_id):
        return {"claim_id": claim_id, "anchored": claim_id in self._anchored}


_BASE = {"subject": "drug X", "object": "tumor growth", "effect_sign": "-"}


def test_plain_candidate_is_feasible():
    out = membrane.feasibility_flags(_BASE, kg=FakeKG())
    assert out["feasible"] is True
    assert out["flags"] == []


def test_sign_contradicts_anchored_parent_is_infeasible():
    # An anchored (human/tested) belief on the same pair holds the opposite sign -> overturning it
    # is a human's call, not the gate's.
    kg = FakeKG(contradict_ids=["c_anchored"], anchored_ids=["c_anchored"])
    out = membrane.feasibility_flags(_BASE, kg=kg)
    assert out["feasible"] is False
    assert any("sign-vs-anchor" in f for f in out["flags"])


def test_contradicts_unanchored_claim_is_still_feasible():
    # A mere unanchored contradiction is normal disagreement, not implausibility — don't flag it.
    kg = FakeKG(contradict_ids=["c_unanchored"], anchored_ids=[])
    out = membrane.feasibility_flags(_BASE, kg=kg)
    assert out["feasible"] is True
    assert out["flags"] == []


def test_negative_fold_change_is_infeasible():
    out = membrane.feasibility_flags({**_BASE, "magnitude": "-2.0-fold"}, kg=FakeKG())
    assert out["feasible"] is False
    assert any("magnitude-range" in f for f in out["flags"])


def test_absurdly_large_fold_change_is_infeasible():
    out = membrane.feasibility_flags({**_BASE, "magnitude": "50000-fold"}, kg=FakeKG())
    assert out["feasible"] is False
    assert any("magnitude-range" in f for f in out["flags"])


def test_sane_hazard_ratio_is_feasible():
    out = membrane.feasibility_flags({**_BASE, "magnitude": "HR 1.4"}, kg=FakeKG())
    assert out["feasible"] is True
    assert out["flags"] == []


def test_percentage_magnitude_not_flagged():
    # Percentages have no universal sane range (change can exceed 100%); leave them alone.
    out = membrane.feasibility_flags({**_BASE, "magnitude": "45% reduction"}, kg=FakeKG())
    assert out["feasible"] is True


def test_works_without_kg():
    # No FalkorDB: sign-vs-anchor is skipped, magnitude check still runs.
    out = membrane.feasibility_flags({**_BASE, "magnitude": "0-fold"}, kg=None)
    assert out["feasible"] is False
    assert any("magnitude-range" in f for f in out["flags"])
