"""F2.5/F2.13 — conflict typing (RQ-E02 substrate) + retraction contamination scan. $0, deterministic."""
from persona.memory.conflicts import type_conflict, retraction_scan, CONFLICT_TYPES


def _is_retracted(bad_dois):
    def _oracle(doi=None, pmid=None):
        return {"retracted": doi in bad_dois, "date": "2024-01", "reason": "data error", "source": "test"}
    return _oracle


def _c(sign, retracted=False, **quals):
    return {"subject": "X", "object": "Y", "effect_sign": sign, "retracted": retracted,
            "qualifiers": quals}


def test_differing_timepoint_is_temporal():
    assert type_conflict(_c("+", timepoint="baseline"), _c("-", timepoint="6 months")) == "temporal"


def test_differing_population_is_semantic():
    assert type_conflict(_c("+", population="aged mice"), _c("-", population="humans")) == "semantic"


def test_differing_model_system_is_semantic():
    assert type_conflict(_c("+", model_system="in_vitro"), _c("-", model_system="in_vivo")) == "semantic"


def test_retraction_is_misinformation_and_takes_precedence():
    # retraction beats a temporal difference (precedence order)
    a = _c("+", retracted=True, timepoint="t1")
    b = _c("-", timepoint="t2")
    assert type_conflict(a, b) == "misinformation"


def test_no_distinguishing_qualifier_is_insufficient():
    assert type_conflict(_c("+"), _c("-")) == "insufficient"
    # same timepoint doesn't distinguish either
    assert type_conflict(_c("+", timepoint="day 14"), _c("-", timepoint="day 14")) == "insufficient"


def test_always_returns_a_frozen_type():
    for a, b in [(_c("+"), _c("-")), (_c("+", population="p"), _c("-", population="q"))]:
        assert type_conflict(a, b) in CONFLICT_TYPES


# ---- F2.13 retraction_scan ----------------------------------------------------------------------
def test_retraction_scan_flags_only_contaminated_claim():
    claims = [{"claim_id": "c1", "subject": "X", "object": "Y", "sources": [{"doi": "10.1/bad"}]},
              {"claim_id": "c2", "subject": "A", "object": "B", "sources": [{"doi": "10.1/good"}]}]
    flagged = retraction_scan(claims, is_retracted=_is_retracted({"10.1/bad"}))
    assert [f["claim_id"] for f in flagged] == ["c1"]
    assert flagged[0]["source"] == "10.1/bad" and flagged[0]["retraction"]["retracted"] is True


def test_retraction_scan_ignores_sourceless_or_clean_claims():
    claims = [{"claim_id": "c", "sources": []}, {"claim_id": "d", "sources": [{"doi": "ok"}]}]
    assert retraction_scan(claims, is_retracted=_is_retracted({"other"})) == []


def test_retraction_scan_default_oracle_flags_nothing():
    # injected oracle that always says "not retracted" → nothing flagged (safe default behaviour)
    claims = [{"claim_id": "c", "sources": [{"doi": "anything"}]}]
    assert retraction_scan(claims, is_retracted=lambda doi=None, pmid=None: {"retracted": False}) == []
