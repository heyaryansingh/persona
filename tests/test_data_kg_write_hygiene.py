"""Belief-store write-boundary hygiene (A10/L3-CONF, A7).

The KG is the authoritative belief store; a wrong number written into it is CLAUDE.md's
"worst possible bug". These tests pin the write boundary of persona/memory/kg.py:
- confidence is clamped to [0.0, 1.0] (the live KG once held confidence>1, breaking value_queue VoI);
- a missing/invalid year is stored as None, never 0 (a stored 0 renders as 1970 downstream);
- a non-numeric/NaN confidence raises ValueError at the boundary instead of storing garbage.

No FalkorDB and no embeddings: KG is built without __init__, canon is identity, and _q captures
the Cypher params so we can assert exactly what would be written.
"""
from types import SimpleNamespace

import pytest

from persona.memory.kg import KG


def _boundary_kg():
    """A KG that never touches the DB or the canonicalizer; captures write params."""
    kg = KG.__new__(KG)
    kg._canon = SimpleNamespace(canon=lambda x: x)  # identity: no embeddings/network
    captured = []
    kg._q = lambda cypher, params=None: captured.append(params or {}) or SimpleNamespace(result_set=[])
    return kg, captured


def _stored_conf(confidence):
    kg, captured = _boundary_kg()
    kg.add_claim({"subject": "microglia", "object": "tau", "effect_sign": "+",
                  "confidence": confidence}, "src1")
    return captured[0]["conf"]  # first _q is the claim MERGE carrying $conf


@pytest.mark.parametrize("given, expected", [(1.7, 1.0), (-0.2, 0.0), (0.6, 0.6)])
def test_confidence_is_clamped_to_unit_interval(given, expected):
    assert _stored_conf(given) == expected


def test_nan_confidence_raises_at_boundary():
    kg, _ = _boundary_kg()
    with pytest.raises(ValueError):
        kg.add_claim({"subject": "a", "object": "b", "effect_sign": "+",
                      "confidence": float("nan")}, "src1")


def test_non_numeric_confidence_raises_at_boundary():
    kg, _ = _boundary_kg()
    with pytest.raises(ValueError):
        kg.add_claim({"subject": "a", "object": "b", "effect_sign": "+",
                      "confidence": "high"}, "src1")


def test_missing_year_is_none_not_zero():
    kg, captured = _boundary_kg()
    kg.upsert_source({"slug": "src1", "title": "t"})  # no 'year' key
    assert captured[0]["year"] is None


def test_zero_year_is_none_not_zero():
    kg, captured = _boundary_kg()
    kg.upsert_source({"slug": "src1", "title": "t", "year": 0})
    assert captured[0]["year"] is None


def test_valid_year_is_preserved():
    kg, captured = _boundary_kg()
    kg.upsert_source({"slug": "src1", "title": "t", "year": 2021})
    assert captured[0]["year"] == 2021


def _stored_dep_conf(confidence):
    kg, captured = _boundary_kg()
    kg.add_dependency_edge("clm_a", "clm_b", "supports", confidence, "span")
    return captured[0]["conf"]  # the DEPENDS_ON MERGE carries $conf


@pytest.mark.parametrize("given, expected", [(1.7, 1.0), (-0.2, 0.0), (0.6, 0.6)])
def test_dependency_edge_confidence_is_clamped(given, expected):
    # a dependency edge is a belief-store write too — same clamp as claim confidence
    assert _stored_dep_conf(given) == expected


def test_dependency_edge_nan_confidence_raises_at_boundary():
    kg, _ = _boundary_kg()
    with pytest.raises(ValueError):
        kg.add_dependency_edge("clm_a", "clm_b", "supports", float("nan"), "span")
