"""F2.5 — conflict typing (RQ-E02 substrate). A sign-collision is classified by WHY it disagrees, from
the §B qualifiers, with a fixed precedence. $0, deterministic."""
from persona.memory.conflicts import type_conflict, CONFLICT_TYPES


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
