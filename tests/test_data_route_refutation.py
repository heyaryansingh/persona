"""F2.12 — a true_refutation review re-opens the question via the FC-1 seam (open_from_conflict).

Only a 'true_refutation' verdict routes; other verdicts open nothing. The seam is mocked (its own
behaviour is covered by test_open_from_conflict). Opens WORK, never a belief. $0.
"""
import types

import persona.conflict_reviews as cr
from persona.research import investigation


def _patch_seam(monkeypatch):
    calls = []

    def _ofc(cls, conflict_id, evidence_claim_ids=None):
        calls.append((conflict_id, evidence_claim_ids))
        return types.SimpleNamespace(slug="inv-reopened")

    monkeypatch.setattr(investigation.Investigation, "open_from_conflict", classmethod(_ofc))
    return calls


def test_true_refutation_opens_investigation_with_pinned_claims(monkeypatch):
    calls = _patch_seam(monkeypatch)
    rec = {"verdict": "true_refutation", "conflict_id": "cfx1", "claim_ids": ["pos", "neg"]}
    assert cr.route_true_refutation(rec) == "inv-reopened"
    assert calls == [("cfx1", ["pos", "neg"])]


def test_non_refutation_verdict_opens_nothing(monkeypatch):
    calls = _patch_seam(monkeypatch)
    for verdict in ("context_divergence", "extraction_error", "insufficient_evidence", ""):
        assert cr.route_true_refutation({"verdict": verdict, "conflict_id": "c"}) is None
    assert calls == []


def test_engine_failure_is_swallowed(monkeypatch):
    def _boom(cls, conflict_id, evidence_claim_ids=None):
        raise RuntimeError("engine down")

    monkeypatch.setattr(investigation.Investigation, "open_from_conflict", classmethod(_boom))
    # a refutation still records fine even if the follow-up launch fails — routing is best-effort
    assert cr.route_true_refutation({"verdict": "true_refutation", "conflict_id": "c"}) is None
