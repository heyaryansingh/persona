"""F3.3: citation_vs_support_divergence — deterministic, offline, fake-KG oracle.

Flags highly-cited-but-thinly-supported (or never-TESTED) claims. Verifies the flag gate, the
never-tested floor, the divergence ordering, and read-only-ness against a fake KG (no DB)."""
from persona.analysis.dependency import citation_vs_support_divergence, CITED_MIN


class _FakeKG:
    """Fake KG mirroring the read-only surface used: dependency_edges, citation_support_ratio,
    provenance. csr: {support, contrast, mention, ratio}. prov: provenance string per claim."""
    def __init__(self, edges, csr, prov):
        self._edges, self._csr, self._prov = edges, csr, prov

    def dependency_edges(self, topic=None):
        return list(self._edges)

    def citation_support_ratio(self, cid):
        return self._csr.get(cid, {"support": 0, "contrast": 0, "mention": 0, "ratio": 0.0})

    def provenance(self, cid):
        return {"claim_id": cid, "provenance": self._prov.get(cid)}


def _kg():
    edges = [
        {"src": "clm_cited_contested", "dst": "clm_tested_solid", "rel_type": "presupposes",
         "confidence": 0.7, "span": "x"},
        {"src": "clm_cited_untested", "dst": "clm_lowcite", "rel_type": "derives_from",
         "confidence": 0.6, "span": "y"},
    ]
    csr = {
        # highly-cited, contested intent (ratio 0.3 < 0.5) -> flagged
        "clm_cited_contested": {"support": 3, "contrast": 7, "mention": 0, "ratio": 0.3},
        # experimentally tested, well-supported, cited -> NOT flagged
        "clm_tested_solid": {"support": 9, "contrast": 1, "mention": 0, "ratio": 0.9},
        # highly-cited, one-sided support (0.95) BUT never TESTED -> flagged via untested floor
        "clm_cited_untested": {"support": 19, "contrast": 1, "mention": 0, "ratio": 0.95},
        # thin support but only 1 citation (< CITED_MIN) -> NOT flagged (not highly-cited)
        "clm_lowcite": {"support": 0, "contrast": 1, "mention": 0, "ratio": 0.0},
    }
    prov = {"clm_cited_contested": "READ", "clm_tested_solid": "TESTED",
            "clm_cited_untested": "READ", "clm_lowcite": "READ"}
    return _FakeKG(edges, csr, prov)


def test_flags_only_cited_and_thin_or_untested():
    out = citation_vs_support_divergence(kg=_kg())
    flagged = {r["claim_id"] for r in out}
    assert flagged == {"clm_cited_contested", "clm_cited_untested"}
    # tested+solid never flagged even though highly cited; low-cite never flagged though thin
    assert "clm_tested_solid" not in flagged
    assert "clm_lowcite" not in flagged


def test_never_tested_floor_beats_high_ratio():
    """An untested claim with 0.95 ratio still diverges: support gap floored at UNTESTED_GAP."""
    out = {r["claim_id"]: r for r in citation_vs_support_divergence(kg=_kg())}
    r = out["clm_cited_untested"]
    # citations = 20 (max) -> prominence 1.0; gap floored to 0.5 -> divergence 0.5
    assert r["citations"] == 20
    assert r["divergence"] == 0.5


def test_schema_and_sorted_desc():
    out = citation_vs_support_divergence(kg=_kg())
    for r in out:
        assert set(r) == {"claim_id", "citations", "support_ratio", "divergence"}
        assert 0.0 <= r["divergence"] <= 1.0
    divs = [r["divergence"] for r in out]
    assert divs == sorted(divs, reverse=True)


def test_min_citation_gate():
    assert CITED_MIN >= 1  # a real threshold, not degenerate


def test_empty_when_no_edges():
    assert citation_vs_support_divergence(kg=_FakeKG([], {}, {})) == []
