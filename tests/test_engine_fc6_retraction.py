"""FC-6: offline retraction lookup + dependency-graph contamination walk.

No FalkorDB / no network: is_retracted reads a seeded temp jsonl; contamination runs over a fake
KG exposing just the two methods it uses (dependency_edges + provenance).
"""
import json

from persona.ingest import retraction


def _seed(tmp_path, monkeypatch, records):
    p = tmp_path / "retractions.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    monkeypatch.setenv("PERSONA_RETRACTIONS_FILE", str(p))


def test_is_retracted_doi_hit_and_normalization(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch, [
        {"doi": "10.1/RETRACTED", "date": "2021-03-01", "reason": "fabrication", "source": "RW"},
    ])
    # stored upper-case + scheme on the query -> normalized match
    hit = retraction.is_retracted(doi="https://doi.org/10.1/retracted")
    assert hit == {"retracted": True, "date": "2021-03-01", "reason": "fabrication", "source": "RW"}
    # clean miss
    assert retraction.is_retracted(doi="10.1/clean")["retracted"] is False
    # pmid path
    _seed(tmp_path, monkeypatch, [{"pmid": 12345, "date": "2020-01-01", "reason": "error", "source": "RW"}])
    assert retraction.is_retracted(pmid="12345")["retracted"] is True
    assert retraction.is_retracted(pmid="99999")["retracted"] is False


class _FakeKG:
    """Minimal KG: claim -> its sources, plus DEPENDS_ON edges (src depends on dst)."""
    def __init__(self, sources, edges):
        self._sources = sources
        self._edges = edges

    def dependency_edges(self, topic=None):
        return [{"src": s, "dst": d, "rel_type": "derives_from", "confidence": 1.0, "span": ""}
                for s, d in self._edges]

    def provenance(self, claim_id):
        return {"claim_id": claim_id, "sources": self._sources.get(claim_id, [])}


def test_contamination_path(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch, [
        {"doi": "10.9/bad", "date": "2022-05-05", "reason": "image dup", "source": "RW"},
    ])
    # a -> b -> c ; only c is backed by the retracted DOI (also test PMID-via-slug on nothing here).
    kg = _FakeKG(
        sources={
            "clm_a": [{"slug": "doi_aaa", "doi": "10.9/ok"}],
            "clm_b": [{"slug": "doi_bbb", "doi": "10.9/fine"}],
            "clm_c": [{"slug": "epmc_MED_777", "doi": "10.9/BAD"}],
        },
        edges=[("clm_a", "clm_b"), ("clm_b", "clm_c")],
    )
    res = retraction.contamination("clm_a", kg=kg)
    assert res["contaminated"] is True
    assert res["path"] == ["clm_a", "clm_b", "clm_c"]

    # a clean claim with no retracted dependency
    clean = _FakeKG(sources={"clm_x": [{"slug": "doi_x", "doi": "10.9/ok"}]}, edges=[])
    assert retraction.contamination("clm_x", kg=clean) == {"contaminated": False, "path": []}


def test_contamination_via_pmid_slug(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch, [{"pmid": 777, "date": "2019-09-09", "reason": "fraud", "source": "RW"}])
    kg = _FakeKG(sources={"clm_c": [{"slug": "epmc_MED_777", "doi": None}]}, edges=[])
    res = retraction.contamination("clm_c", kg=kg)
    assert res["contaminated"] is True and res["path"] == ["clm_c"]
