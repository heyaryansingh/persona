"""F1.3 — two-reader cross-check: only claims TWO independent extractions agree on are trusted.

`cross_check_claims` runs extraction twice, validates each pass (exact-span gate preserved), and
matches on the frozen claim identity. A claim in both passes → `agreed` (harvestable); a claim in only
one pass → a preserved, flagged `disagreement`, never silently admitted. The two model reads are
stubbed so this is $0.
"""
from persona.reading import extract

TEXT = "X increases Y. A decreases B. P causes Q."
SHARED = {"subject": "X", "relation": "increases", "object": "Y", "effect_sign": "+", "quote": "X increases Y."}
ONLY_A = {"subject": "A", "relation": "decreases", "object": "B", "effect_sign": "-", "quote": "A decreases B."}
ONLY_B = {"subject": "P", "relation": "causes", "object": "Q", "effect_sign": "+", "quote": "P causes Q."}


def test_only_agreeing_claims_admitted(monkeypatch):
    def _stub(text, title="", *, model=None, client=None):
        return ([SHARED, ONLY_A] if model == "A" else [SHARED, ONLY_B], {"cost": 0.0})

    monkeypatch.setattr(extract, "extract_claims", _stub)
    agreed, disagreements, usage = extract.cross_check_claims(TEXT, model_a="A", model_b="B")

    agreed_pairs = {(c["subject"], c["object"]) for c in agreed}
    disagreed_pairs = {(c["subject"], c["object"]) for c in disagreements}
    assert ("X", "Y") in agreed_pairs                    # in both passes → agreed
    assert ("A", "B") in disagreed_pairs                 # only pass A → disagreement
    assert ("P", "Q") in disagreed_pairs                 # only pass B → disagreement
    assert ("X", "Y") not in disagreed_pairs             # an agreed claim is never a disagreement
    assert usage["cost"] == 0.0


def test_ungrounded_claim_never_agreed(monkeypatch):
    # a non-verbatim quote fails validate_claims in BOTH passes → it can't become an agreed claim.
    bad = {"subject": "Z", "relation": "blocks", "object": "W", "effect_sign": "-",
           "quote": "this sentence is not in the text"}

    def _stub(text, title="", *, model=None, client=None):
        return ([SHARED, bad], {"cost": 0.0})

    monkeypatch.setattr(extract, "extract_claims", _stub)
    agreed, disagreements, _ = extract.cross_check_claims(TEXT, model_a="A", model_b="B")
    assert {(c["subject"], c["object"]) for c in agreed} == {("X", "Y")}
    assert all(c["subject"] != "Z" for c in agreed + disagreements)   # ungrounded dropped by the span gate
