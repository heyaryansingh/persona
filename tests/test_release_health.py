from fastapi.testclient import TestClient

from persona.api.app import app


def test_healthz_is_public_and_does_not_expose_state():
    r = TestClient(app).get("/healthz")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert set(r.json()) == {"ok", "version"}
