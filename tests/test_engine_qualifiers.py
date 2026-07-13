"""RQ-E06 (S4 slice) — qualifier extraction validation is exact-span, schema-bound, and ADDITIVE.

Qualifiers scope a claim (population, model_system, direction, magnitude, timepoint, n) and must each
be grounded in a verbatim source span (RQ-E01a discipline). The frozen §B contract requires:
  - every qualifier block cites an exact source span (qual_source verbatim) or the block is dropped;
  - a bad/ungrounded qualifier NEVER rejects a claim that passed the core gate (identity preserved);
  - only in-vocabulary, schema-valid fields are stored (no silent junk into the belief-store).
All $0 — feeds synthetic model output into validate_claims; no model calls.
"""
from persona.reading.extract import validate_claims

SOURCE = (
    "In aged female mice, chronic stress increased hippocampal inflammation. "
    "The cohort of 240 type-2 diabetics showed a 2.1-fold rise in marker X at 6 months. "
    "Metformin reduced tumor incidence in vitro."
)


def _claim(**kw):
    base = {"subject": "stress", "relation": "increases", "object": "inflammation",
            "effect_sign": "+", "quote": "In aged female mice, chronic stress increased hippocampal inflammation."}
    base.update(kw)
    return base


def test_claim_without_qualifiers_is_unchanged():
    accepted, rejected = validate_claims([_claim()], SOURCE)
    assert len(accepted) == 1 and not rejected
    assert "qualifiers" not in accepted[0]                      # no regression for the common path


def test_grounded_qualifier_kept_with_only_valid_fields():
    q = {"population": "aged female mice", "model_system": "in_vivo", "direction": "+",
         "n": 240, "timepoint": "6 months", "magnitude": "2.1-fold",
         "junk_field": "ignored",                               # unknown field must be dropped
         "qual_source": "In aged female mice, chronic stress increased hippocampal inflammation."}
    accepted, _ = validate_claims([_claim(qualifiers=q)], SOURCE)
    ql = accepted[0]["qualifiers"]
    assert ql["population"] == "aged female mice"
    assert ql["model_system"] == "in_vivo" and ql["direction"] == "+"
    assert ql["n"] == 240 and ql["timepoint"] == "6 months" and ql["magnitude"] == "2.1-fold"
    assert "junk_field" not in ql                               # only contract fields survive
    assert "qual_source" in ql


def test_ungrounded_qualifier_is_stripped_but_claim_survives():
    # qual_source is NOT a verbatim span in SOURCE → block dropped, claim still accepted (additive).
    q = {"population": "aged female mice", "model_system": "in_vivo",
         "qual_source": "This sentence does not appear anywhere in the source text."}
    accepted, rejected = validate_claims([_claim(qualifiers=q)], SOURCE)
    assert len(accepted) == 1 and not rejected
    assert "qualifiers" not in accepted[0]
    # identity fields untouched
    assert (accepted[0]["subject"], accepted[0]["object"], accepted[0]["effect_sign"]) == \
           ("stress", "inflammation", "+")


def test_invalid_enum_and_types_are_dropped_field_by_field():
    q = {"model_system": "petri_dish",         # not in the frozen enum → drop field
         "direction": "up",                     # not in {+,-,na} → drop field
         "n": True,                             # bool is not a sample size → drop
         "population": "the cohort of 240 type-2 diabetics",
         "qual_source": "The cohort of 240 type-2 diabetics showed a 2.1-fold rise in marker X at 6 months."}
    accepted, _ = validate_claims([_claim(qualifiers=q)], SOURCE)
    ql = accepted[0]["qualifiers"]
    assert "model_system" not in ql and "direction" not in ql and "n" not in ql
    assert ql["population"] == "the cohort of 240 type-2 diabetics"


def test_qualifier_with_only_source_and_no_real_field_is_dropped():
    q = {"qual_source": "Metformin reduced tumor incidence in vitro."}   # grounded but no info
    accepted, _ = validate_claims([_claim(qualifiers=q)], SOURCE)
    assert "qualifiers" not in accepted[0]


def test_qualifiers_never_rescue_a_core_invalid_claim():
    # non-verbatim quote → claim rejected by the core gate regardless of a perfect qualifier block.
    bad = _claim(quote="this quote is not in the source", qualifiers={
        "model_system": "in_vivo",
        "qual_source": "Metformin reduced tumor incidence in vitro."})
    accepted, rejected = validate_claims([bad], SOURCE)
    assert not accepted and len(rejected) == 1
    assert rejected[0]["reason"] == "quote-not-verbatim"
