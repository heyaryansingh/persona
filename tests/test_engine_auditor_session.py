"""F3.7 — deepened robustness auditor: reanalysis scoping + retraction pass.

Both functions are pure, deterministic and offline (no model, no network), so they are exercised
directly. The retraction pass is tested against an explicit source flag, a clean source, and an
injected persona.ingest.retraction oracle (is_retracted / contamination).
"""
import sys
import types

from persona.agents import audit


def test_reanalysis_scope_causal_with_datasets_is_full_and_high():
    r = audit.reanalysis_scope({"claim": "Knockout of TP53 drives resistance (GSE12345, GSE678).",
                                "kind": "causal"})
    assert r["scope"] == "full-reanalysis"
    assert r["cost_tier"] == "high"
    assert "GSE12345" in r["datasets"] and "GSE678" in r["datasets"]


def test_reanalysis_scope_descriptive_no_data_is_spotcheck_low():
    r = audit.reanalysis_scope("Most respondents reported mild symptoms.")
    assert r["scope"] == "spot-check"
    assert r["cost_tier"] == "low"
    assert r["datasets"] == []


def test_reanalysis_scope_single_dataset_bumps_cost_to_medium():
    # descriptive kind → spot-check scope, but one named dataset lifts cost to medium
    r = audit.reanalysis_scope({"claim": "Expression summarised in SRR1234567.", "kind": "descriptive"})
    assert r["scope"] == "spot-check"
    assert r["cost_tier"] == "medium"
    assert r["datasets"] == ["SRR1234567"]


def test_reanalysis_scope_extracts_doi_and_merges_explicit():
    r = audit.reanalysis_scope({"claim": "Reanalysed from 10.5281/zenodo.123456.",
                                "kind": "correlational", "datasets": ["phs001234"]})
    assert "10.5281/zenodo.123456" in r["datasets"]
    assert "phs001234" in r["datasets"]
    assert r["scope"] == "partial-reanalysis"


def test_retraction_pass_explicit_flag_is_severity3_fail():
    rp = audit.retraction_pass([{"doi": "10.1/bad", "title": "X", "retracted": True},
                                {"doi": "10.2/ok", "title": "Y"}])
    assert rp["retracted"] == ["10.1/bad"]
    assert rp["flag"] is not None
    assert rp["flag"]["severity"] == 3 and rp["flag"]["status"] == "fail"
    assert rp["flag"]["check"] == "retraction"


def test_retraction_pass_clean_sources_no_flag():
    rp = audit.retraction_pass([{"doi": "10.2/ok", "title": "Y"}, {"title": ""}, "loose-string"])
    assert rp["retracted"] == [] and rp["contaminated"] == []
    assert rp["flag"] is None


def test_retraction_pass_consumes_injected_oracle(monkeypatch):
    import persona.ingest as ingest_pkg
    fake = types.ModuleType("persona.ingest.retraction")
    fake.is_retracted = lambda s: s.get("doi") == "10.9/retracted"
    fake.contamination = lambda s: s.get("doi") == "10.9/dirty"
    monkeypatch.setitem(sys.modules, "persona.ingest.retraction", fake)
    monkeypatch.setattr(ingest_pkg, "retraction", fake, raising=False)

    rp = audit.retraction_pass([{"doi": "10.9/retracted"}, {"doi": "10.9/dirty"}, {"doi": "10.9/fine"}])
    assert rp["retracted"] == ["10.9/retracted"]
    assert rp["contaminated"] == ["10.9/dirty"]
    # a retracted source dominates: overall flag is a severity-3 failure
    assert rp["flag"]["severity"] == 3


def test_retraction_pass_contamination_only_is_warn():
    fake = types.ModuleType("persona.ingest.retraction")
    fake.is_retracted = lambda s: False
    fake.contamination = lambda s: True
    import persona.ingest as ingest_pkg
    sys.modules["persona.ingest.retraction"] = fake
    setattr(ingest_pkg, "retraction", fake)
    try:
        rp = audit.retraction_pass([{"doi": "10.9/shared-cohort"}])
        assert rp["retracted"] == []
        assert rp["contaminated"] == ["10.9/shared-cohort"]
        assert rp["flag"]["severity"] == 2 and rp["flag"]["status"] == "warn"
    finally:
        sys.modules.pop("persona.ingest.retraction", None)
        if hasattr(ingest_pkg, "retraction"):
            delattr(ingest_pkg, "retraction")
