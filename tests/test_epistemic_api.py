"""Lane 4 (S3) route wiring — mount + routes registered + FC-7 /eval provider contract.
Live request behaviour (degrade paths, JSON shapes) is covered by S2's browser/API smoke;
here we assert the routing is wired without spinning a server or a persona fixture."""
from persona.api.app import app


def _paths():
    return {getattr(r, "path", None) for r in app.routes}


def test_static_mount_registered():
    # /static serves Lane-4 JS/CSS assets (former Wave-0 P0.1, now Lane 4).
    assert any(getattr(r, "name", "") == "static" for r in app.routes), "static mount missing"


def test_lane4_routes_registered():
    paths = _paths()
    for p in [
        "/api/persona/{pid}/eval",
        "/api/persona/{pid}/engine/dependency",
        "/api/persona/{pid}/engine/value_queue",
        "/api/persona/{pid}/engine/handoff",
        "/api/persona/{pid}/gate_decisions",
    ]:
        assert p in paths, f"route not registered: {p}"


def test_epistemic_route_and_gate_parse():
    assert "/api/persona/{pid}/epistemic" in _paths(), "epistemic route not registered"
    from persona.api.app import _rq_gates
    gates = _rq_gates()
    assert len(gates) >= 10, f"expected RQ gates from the doc, got {len(gates)}"   # doc has 14
    valid = {"passed", "partial", "in_progress", "pending", "contested", "gated"}
    for g in gates:
        assert {"id", "title", "status"} <= set(g) and g["id"].startswith("RQ-E")
        assert g["status"] in valid, g


def test_eval_provider_contract():
    # /eval delegates to persona.eval.run_oracle (FC-7) — assert the provider's shape.
    from persona.eval import run_oracle
    r = run_oracle("litqa2", n=0, seed=0, persona="x")
    assert {"metric", "score", "n", "per_item"} <= set(r)   # FC-7 minimum; extras allowed
