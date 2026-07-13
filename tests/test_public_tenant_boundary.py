from types import SimpleNamespace

from fastapi.testclient import TestClient

from persona import public_auth
import persona.api.app as app_module


def _session(secret, sub="owner-a"):
    import os
    os.environ["PERSONA_SESSION_SECRET"] = secret
    return public_auth._signer().dumps({"sub": sub, "email": "a@example.test", "csrf": "csrf-a"})


def test_public_boundary_filters_and_authorizes_personas(monkeypatch):
    monkeypatch.setenv("PERSONA_PUBLIC_MODE", "1")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    cookie = _session("test-session-secret")
    owned = SimpleNamespace(id="owned", owner_id="owner-a", to_card=lambda: {"id": "owned"})
    other = SimpleNamespace(id="other", owner_id="owner-b", to_card=lambda: {"id": "other"})
    fake = SimpleNamespace(list=lambda: [owned, other], get=lambda pid: {"owned": owned, "other": other}.get(pid))
    monkeypatch.setattr(app_module, "manager", lambda: fake)
    client = TestClient(app_module.app)

    assert client.get("/api/personas").status_code == 401
    client.cookies.set("persona_session", cookie)
    assert client.get("/api/personas").json() == {"personas": [{"id": "owned"}]}
    assert client.get("/api/persona/other/status").status_code == 404
    assert client.post("/api/personas", json={"name": "x"}).status_code == 403
    assert client.post("/api/personas", json={"name": "x", "budget_usd": 999}, headers={"X-CSRF-Token": "csrf-a"}).status_code == 429
    assert client.post("/auth/logout").status_code == 403
    assert client.post("/auth/logout", headers={"X-CSRF-Token": "csrf-a"}).status_code == 200
