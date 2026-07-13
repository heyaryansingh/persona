"""FC-4 (part 2): value_queue ranking. Uses a duck-typed fake KG so it runs with NO FalkorDB —
value_queue is pure read logic over the KG surface, so a dict-backed stand-in is a faithful oracle.
"""
from persona.analysis.value_queue import value_queue


class FakeKG:
    """Minimal stand-in exposing the three KG methods value_queue reads."""
    def __init__(self, claims, edges, ratios):
        self._claims = claims          # list[dict] as kg.beliefs() returns
        self._edges = edges            # list[{src,dst,...}] as kg.dependency_edges() returns
        self._ratios = ratios          # cid -> support_ratio

    def beliefs(self, min_independent=2, min_conf=0.5, limit=200):
        return [c for c in self._claims
                if (c.get("independent_sources") or 0) >= min_independent
                and (c.get("confidence") or 0) >= min_conf][:limit]

    def dependency_edges(self, topic=None):
        return self._edges

    def citation_support_ratio(self, cid):
        return {"ratio": self._ratios.get(cid, 0.0)}


def _claim(cid, subj, obj, sign="+", indep=2, conf=0.6, prov="READ", anchored=False):
    return {"claim_id": cid, "subject": subj, "object": obj, "effect_sign": sign,
            "independent_sources": indep, "confidence": conf, "provenance": prov,
            "anchored": anchored}


def test_no_kg_returns_empty():
    assert value_queue("anything", kg=None) == []
    # explicit falsy kg (FalkorDB down) also yields empty, never raises.
    assert value_queue("anything", kg=False) == []


def test_ranking_derisk_contest_and_exclusions():
    claims = [
        # load-bearing hub: 2 downstream dependents, contested (ratio 0.5).
        _claim("clm_hub", "drugX", "outcomeY", sign="+", indep=3, conf=0.6),
        # leaf: no dependents, well-corroborated (ratio 1.0) -> lowest VoI.
        _claim("clm_leaf", "drugX", "sideZ", sign="-", indep=2, conf=0.9),
        # thin single-lab claim -> 'expensive' cost tier.
        _claim("clm_thin", "drugX", "markerW", sign="+", indep=1, conf=0.4),
        # already human-confirmed -> must be EXCLUDED (no VoI in re-resolving).
        _claim("clm_done", "drugX", "outcomeQ", prov="HUMAN_CONFIRMED"),
        # anchored -> also excluded.
        _claim("clm_anc", "drugX", "outcomeR", anchored=True),
        # off-topic -> filtered out.
        _claim("clm_off", "aspirin", "headache"),
    ]
    edges = [
        {"src": "clm_a", "dst": "clm_hub"}, {"src": "clm_b", "dst": "clm_hub"},
        {"src": "clm_b", "dst": "clm_hub"},   # duplicate src -> counted once (distinct)
    ]
    ratios = {"clm_hub": 0.5, "clm_leaf": 1.0, "clm_thin": 0.0}

    q = value_queue("drugX", kg=FakeKG(claims, edges, ratios),
                    dataset_available=lambda toks: False)

    ids = [r["resolves_claim_id"] for r in q]
    assert set(ids) == {"clm_hub", "clm_leaf", "clm_thin"}      # confirmed/anchored/off-topic gone
    assert q[0]["resolves_claim_id"] == "clm_hub"              # highest VoI/cost wins

    hub = next(r for r in q if r["resolves_claim_id"] == "clm_hub")
    assert hub["de_risks_n"] == 2                              # distinct downstream srcs
    assert hub["cost_tier"] == "cheap_assay"                   # indep>=2, no local data
    assert hub["dataset_available"] is False
    assert hub["run_action"] == "null_hunt:drugX|outcomeY"     # CCP-19a queue.enqueue prefix
    assert "de-risks 2 downstream beliefs" in hub["question"]

    thin = next(r for r in q if r["resolves_claim_id"] == "clm_thin")
    assert thin["cost_tier"] == "expensive"                    # single lab
    assert thin["de_risks_n"] == 0

    # VoI strictly increases with downstream load: hub (2 deps) > leaf (0 deps, corroborated).
    leaf = next(r for r in q if r["resolves_claim_id"] == "clm_leaf")
    assert hub["voi"] > leaf["voi"]

    # Full contract shape on every row.
    for r in q:
        assert set(r) == {"question", "resolves_claim_id", "voi", "cost_tier",
                          "dataset_available", "de_risks_n", "run_action"}
        assert r["cost_tier"] in ("public_data", "cheap_assay", "expensive")
        assert isinstance(r["voi"], float) and r["voi"] >= 0.0


def test_dataset_available_flips_tier_and_action():
    claims = [_claim("clm_d", "geneA", "phenoB", indep=1, conf=0.5)]
    q = value_queue("geneA", kg=FakeKG(claims, [], {"clm_d": 0.3}),
                    dataset_available=lambda toks: True)
    row = q[0]
    assert row["dataset_available"] is True
    assert row["cost_tier"] == "public_data"                   # local dataset -> cheapest
    assert row["run_action"] == "literature_search:geneA phenoB"  # CCP-19a science.call prefix
