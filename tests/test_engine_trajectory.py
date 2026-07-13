"""PRD F3.4 trajectory dynamics — pure signal correctness + read-only KG wiring via a fake KG."""
from persona.analysis import trajectory as T


class _Res:
    def __init__(self, rows):
        self.result_set = rows


class _FakeKG:
    """Minimal stand-in for KG: search resolves a topic to entities, _q returns canned claim rows.
    No network, no DB — proves trajectory() is read-only and deterministic over the query interface."""
    def __init__(self, entities, rows):
        self._entities, self._rows = entities, rows
        self.wrote = False

    def search(self, q, limit=12):
        return [{"id": f"entity:{e}", "type": "entity", "label": e} for e in self._entities]

    def _q(self, cypher, params=None):
        assert "MERGE" not in cypher and "SET " not in cypher and "DELETE" not in cypher, "read-only"
        return _Res(self._rows)


def test_order_is_chronological_and_projected():
    out = T._order([
        {"claim_id": "b", "confidence": 0.6, "valid_from": "2024-06-01T00:00:00+00:00", "x": 1},
        {"claim_id": "a", "confidence": 0.5, "valid_from": "2024-01-01T00:00:00+00:00"},
    ])
    assert [p["valid_from"] for p in out] == ["2024-01-01T00:00:00+00:00", "2024-06-01T00:00:00+00:00"]
    assert set(out[0].keys()) == {"claim_id", "confidence", "valid_from"}   # only the PRD projection


def test_order_drops_incomplete_points_and_breaks_ties():
    out = T._order([
        {"claim_id": "z", "confidence": 0.7, "valid_from": "2024-01-01T00:00:00+00:00"},
        {"claim_id": "a", "confidence": 0.7, "valid_from": "2024-01-01T00:00:00+00:00"},  # tie -> by id
        {"claim_id": "n", "confidence": None, "valid_from": "2024-02-01T00:00:00+00:00"},  # no conf
        {"claim_id": "t", "confidence": 0.9, "valid_from": None},                          # no time
    ])
    assert [p["claim_id"] for p in out] == ["a", "z"]


def test_settled_arc_reads_settled():
    s = T.settling([
        {"claim_id": "c1", "confidence": 0.50, "valid_from": "1"},
        {"claim_id": "c2", "confidence": 0.72, "valid_from": "2"},
        {"claim_id": "c3", "confidence": 0.80, "valid_from": "3"},
        {"claim_id": "c4", "confidence": 0.81, "valid_from": "4"},
        {"claim_id": "c5", "confidence": 0.82, "valid_from": "5"},
    ])
    assert s["state"] == "settled"
    assert s["recent_velocity"] <= T._SETTLE_EPS
    assert s["direction"] in ("flat", "rising")


def test_swinging_tail_reads_moving():
    m = T.settling([
        {"claim_id": "d1", "confidence": 0.40, "valid_from": "1"},
        {"claim_id": "d2", "confidence": 0.75, "valid_from": "2"},
        {"claim_id": "d3", "confidence": 0.35, "valid_from": "3"},
        {"claim_id": "d4", "confidence": 0.70, "valid_from": "4"},
    ])
    assert m["state"] == "moving"
    assert m["recent_velocity"] > T._SETTLE_EPS


def test_insufficient_when_under_two_points():
    assert T.settling([])["state"] == "insufficient"
    assert T.settling([{"claim_id": "x", "confidence": 0.5, "valid_from": "1"}])["state"] == "insufficient"


def test_direction_tracks_net_recent_change():
    falling = T.settling([
        {"claim_id": "a", "confidence": 0.9, "valid_from": "1"},
        {"claim_id": "b", "confidence": 0.6, "valid_from": "2"},
        {"claim_id": "c", "confidence": 0.3, "valid_from": "3"},
    ])
    assert falling["direction"] == "falling" and falling["net_recent"] < 0


def test_trajectory_over_fake_kg_is_read_only_and_ordered():
    rows = [
        # claim_id, confidence, valid_from, subject, effect_sign, object  (matches _fetch RETURN order)
        ["clm_b", 0.6, "2024-06-01T00:00:00+00:00", "il6", "+", "crp"],
        ["clm_a", 0.5, "2024-01-01T00:00:00+00:00", "il6", "+", "tnf"],
    ]
    kg = _FakeKG(entities=["il6", "crp"], rows=rows)
    out = T.trajectory(kg, "inflammation")
    assert out["topic"] == "inflammation"
    assert out["entities"] == ["il6", "crp"]
    assert [p["claim_id"] for p in out["series"]] == ["clm_a", "clm_b"]   # chronological
    assert out["signal"]["n_points"] == 2


def test_trajectory_empty_topic_yields_insufficient():
    kg = _FakeKG(entities=[], rows=[])
    out = T.trajectory(kg, "nonexistent")
    assert out["series"] == [] and out["signal"]["state"] == "insufficient"


def test_demo_self_check_runs():
    T.demo()
