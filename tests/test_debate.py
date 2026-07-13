"""F1.4 — gated debate: de-identified, agreement always surfaced, low agreement ESCALATES (never
outvotes a grounded minority). The paid rounds are gated; this tests the $0 logic + the escalation
seam by stubbing the round-runner.
"""
from persona.agents import debate


def test_deidentify_strips_author_identity():
    out = debate._deidentify([
        {"span": "X raised Y.", "stance": "+", "author": "analyst", "actor": "reader-3", "id": "a1"}])
    assert out == [{"span": "X raised Y.", "stance": "+", "claim_id": "", "qualifiers": {}}]
    assert "author" not in out[0] and "actor" not in out[0]      # no WHO reaches the debater


def test_tally_majority_and_fraction():
    frac, verdict = debate._tally(["+", "+", "-"])
    assert verdict == "+" and abs(frac - 2 / 3) < 1e-9


def test_agreement_always_present():
    r = debate.debate("c", [{"span": "a", "stance": "+"}, {"span": "b", "stance": "-"}])
    assert "agreement" in r and isinstance(r["agreement"], float)


def test_low_agreement_escalates(monkeypatch):
    # force a split panel → agreement 0.5 < TAU → must escalate to a human handoff, not outvote.
    monkeypatch.setattr(debate, "_run_rounds", lambda *a, **k: ["+", "-"])
    called = {}

    def _fake_handoff(kind, dossier):
        called["kind"] = kind
        called["dossier"] = dossier
        return "ho_test"

    monkeypatch.setattr("persona.inbox.file_handoff", _fake_handoff)
    r = debate.debate("X vs Y",
                      [{"span": "a", "stance": "+", "claim_id": "c1"},
                       {"span": "b", "stance": "-", "claim_id": "c2"}])
    assert r["resolved"] is False and r["escalate"] is True
    assert called.get("kind") == "debate_unresolved"             # a handoff was filed, not a belief written
    assert r["transcript_ref"] == "ho_test"
    assert called["dossier"]["conflict_type"] == "insufficient"


def test_high_agreement_resolves_without_escalating(monkeypatch):
    monkeypatch.setattr(debate, "_run_rounds", lambda *a, **k: ["+", "+", "+"])

    def _boom(kind, dossier):
        raise AssertionError("a resolved debate must NOT file a handoff")

    monkeypatch.setattr("persona.inbox.file_handoff", _boom)
    r = debate.debate("c", [{"span": "a", "stance": "+"}, {"span": "b", "stance": "+"}])
    assert r["resolved"] is True and r["escalate"] is False and r["agreement"] == 1.0
