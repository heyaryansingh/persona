"""F1.2 — the Verifier's applicability gate (the correctness boundary).

`is_verifiable` decides whether THIS agent can independently re-check a claim: only a claim with an
exact source span that is either directional-empirical (reproducible) or mathematical (provable). A
non-verifiable claim returns `not_applicable` — an explicit skip, NOT a pass — and makes ZERO paid
model/sandbox calls. That skip is what prevents the out-of-domain false positive. All $0.
"""
from persona.agents import verifier, analyst


def _claim(sign, quote="X raised Y in the reported trial."):
    return {"subject": "X", "relation": "raises", "object": "Y",
            "effect_sign": sign, "quote": quote}


def test_gate_computational_claim_verifiable():
    ok, kind = verifier.is_verifiable(_claim("+"))
    assert ok and kind == "computational"
    ok, kind = verifier.is_verifiable(_claim("-"))
    assert ok and kind == "computational"


def test_gate_math_claim_verifiable():
    ok, kind = verifier.is_verifiable(_claim("na"))
    assert ok and kind == "math"


def test_gate_no_span_not_verifiable():
    ok, reason = verifier.is_verifiable(_claim("+", quote=""))
    assert not ok and "span" in reason


def test_gate_null_sign_not_verifiable():
    ok, _ = verifier.is_verifiable(_claim("0"))
    assert not ok


def test_verify_not_applicable_makes_no_paid_call(monkeypatch):
    monkeypatch.setattr(verifier, "_lookup_claim", lambda cid: _claim("0"))   # non-verifiable

    def _boom(*a, **k):
        raise AssertionError("verify routed a not_applicable claim to the PAID analyst")

    monkeypatch.setattr(analyst, "investigate", _boom)
    r = verifier.verify("clm_x")
    assert r["verdict"] == "not_applicable" and r["ran_code"] is False


def test_verify_claim_not_found_is_not_applicable(monkeypatch):
    monkeypatch.setattr(verifier, "_lookup_claim", lambda cid: None)
    assert verifier.verify("missing")["verdict"] == "not_applicable"


def test_verify_verifiable_degrades_to_inconclusive_without_budget(monkeypatch):
    # verifiable claim, but no key → analyst.investigate returns not-ok → inconclusive, NO spend.
    monkeypatch.setattr(verifier, "_lookup_claim", lambda cid: _claim("+"))
    monkeypatch.setattr(analyst.config, "have_key", lambda: False)
    r = verifier.verify("clm_x")
    assert r["verdict"] == "inconclusive" and r["check_kind"] == "computational"
