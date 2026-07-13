"""Belief-store data invariants (PRD F2.6 + F2.7), additive to test_data_kg_write_hygiene.

F2.6 — evidence-monotonic no-inflation guard: a claim's confidence may never exceed a function
of the count of INDEPENDENT labs backing it, so re-observation can only raise confidence by
bringing NEW independent evidence — repetition / citation-echo (more sources, same labs) can't.

F2.7 — set_validity_window bounds a claim's bi-temporal validity (valid_from/valid_to) without
touching anchoring, provenance, or confidence.

The unit tests use no FalkorDB and no embeddings: KG is built without __init__, canon is identity,
and _q is stubbed so we assert exactly what would be written. One live round-trip test (skipped
when no graph DB is reachable) confirms set_validity_window actually persists and reads back.
"""
import os
import socket
from types import SimpleNamespace

import pytest

from persona.memory.kg import KG, _confidence_cap


def _falkor_up() -> bool:
    host = os.environ.get("PERSONA_FALKOR_HOST", "127.0.0.1")
    port = int(os.environ.get("PERSONA_FALKOR_PORT", "6379"))
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


def _guard_kg(agg_row):
    """A KG that never touches the DB/canonicalizer; the aggregation query returns agg_row
    ([n, labs, mconf]) so we can drive the F2.6 cap deterministically and capture the write."""
    kg = KG.__new__(KG)
    kg._canon = SimpleNamespace(canon=lambda x: x)  # identity: no embeddings/network
    captured = []

    def q(cypher, params=None):
        params = params or {}
        captured.append(params)
        if "avg(r.conf)" in cypher:
            return SimpleNamespace(result_set=[agg_row])
        return SimpleNamespace(result_set=[])

    kg._q = q
    return kg, captured


def _add_claim_conf(agg_row):
    kg, captured = _guard_kg(agg_row)
    kg.add_claim({"subject": "microglia", "object": "tau", "effect_sign": "+"}, "src1")
    return next(p["capped"] for p in captured if "capped" in p)  # the confidence SET carries $capped


# ---- F2.6: no-inflation guard ------------------------------------------------
def test_confidence_cap_is_monotone_and_bounded():
    caps = [_confidence_cap(k) for k in range(0, 6)]
    assert caps == sorted(caps)                      # monotone non-decreasing in independent labs
    assert caps[0] == 0.0 and caps[1] == 0.5         # zero labs -> 0, one lab tops out at 0.5
    assert all(0.0 <= c < 1.0 for c in caps)         # never reaches certainty from counting alone


def test_repetition_from_one_lab_cannot_inflate_past_ceiling():
    # 50 high-confidence copies but only ONE independent lab: capped at 0.5, not ~0.95.
    assert _add_claim_conf([50, 1, 0.95]) == 0.5


def test_ceiling_rises_only_with_new_independent_labs():
    assert _add_claim_conf([3, 3, 0.99]) == pytest.approx(0.75)   # 3 labs -> ceiling 0.75
    assert _add_claim_conf([9, 9, 0.99]) == pytest.approx(0.9)    # 9 labs -> ceiling 0.9


def test_confidence_below_ceiling_passes_through_unchanged():
    # weak evidence (mconf 0.3) is below the 1-lab ceiling (0.5) -> not raised by the guard.
    assert _add_claim_conf([1, 1, 0.3]) == pytest.approx(0.3)


# ---- F2.7: validity window ---------------------------------------------------
def test_set_validity_window_writes_only_provided_bounds():
    kg, captured = _guard_kg([0, 0, 0.0])
    kg.set_validity_window("clm_x", valid_from="2020-01-01T00:00:00+00:00")
    p = captured[-1]
    assert p["vf"] == "2020-01-01T00:00:00+00:00" and "vt" not in p


def test_set_validity_window_noop_when_no_bounds():
    kg, captured = _guard_kg([0, 0, 0.0])
    assert kg.set_validity_window("clm_x") is False
    assert captured == []  # nothing written when neither bound is given


@pytest.mark.skipif(not _falkor_up(), reason="FalkorDB not reachable on :6379")
def test_validity_window_set_and_read_live():
    kg = KG()
    kg._canon = SimpleNamespace(canon=lambda x: x)  # identity: keep it deterministic, no network
    kg.upsert_source({"slug": "kginv_src", "title": "t", "affiliations": ["kginv lab"]})
    cid = kg.add_claim({"subject": "kginv_subj", "object": "kginv_obj", "effect_sign": "+"},
                       "kginv_src")
    vf, vt = "2018-01-01T00:00:00+00:00", "2021-12-31T00:00:00+00:00"
    assert kg.set_validity_window(cid, valid_from=vf, valid_to=vt) is True
    row = kg._q("MATCH (c:Claim {claim_id:$cid}) RETURN c.valid_from, c.valid_to",
                {"cid": cid}).result_set[0]
    assert row[0] == vf and row[1] == vt
    assert kg.set_validity_window("clm_does_not_exist", valid_to=vt) is False
