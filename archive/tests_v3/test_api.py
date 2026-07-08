"""API smoke test via FastAPI TestClient (no server). Run: python tests/test_api.py"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# hermetic: use fixtures (offline), never autostart the daemon during the test
os.environ["PERSONA_OFFLINE"] = "1"
os.environ.pop("PERSONA_AUTONOMOUS", None)
_flag = Path(__file__).resolve().parent.parent / "runs" / "api_self" / "daemon.on"
try:
    _flag.unlink()
except OSError:
    pass

from persona.api.app import app  # noqa: E402


def test_api_endpoints():
    try:
        from fastapi.testclient import TestClient
    except Exception as e:
        print(f"SKIP test_api_endpoints: TestClient unavailable ({e})")
        # still assert the app wired its routes
        paths = {r.path for r in app.routes}
        assert "/api/dashboard" in paths and "/api/handoffs" in paths
        return
    client = TestClient(app)
    d = client.get("/api/dashboard").json()
    assert d["name"] == "Ada" and "agenda" in d
    assert isinstance(client.get("/api/beliefs").json()["beliefs"], list)
    assert isinstance(client.get("/api/notebook").json()["lines"], list)
    assert isinstance(client.get("/api/handoffs").json()["handoffs"], list)
    assert "mini_review" in client.get("/api/artifacts").json()
    dep = client.get("/api/dependency").json()
    assert "nodes" in dep and "edges" in dep
    assert isinstance(client.get("/api/experiments").json()["queue"], list)
    print(f"PASS test_api_endpoints: dashboard={d['name']}, "
          f"beliefs={d['n_beliefs']}, handoffs={d['n_open_handoffs']}")


def test_auth_guard():
    from persona.api import app as appmod
    from fastapi import HTTPException
    old = appmod.API_TOKEN
    appmod.API_TOKEN = "secret"
    try:
        raised = False
        try:
            appmod.require_token(None)                 # missing token -> 401
        except HTTPException as e:
            raised = e.status_code == 401
        assert raised, "must reject a missing token when API_TOKEN is set"
        appmod.require_token("secret")                 # correct token -> no raise
    finally:
        appmod.API_TOKEN = old


def test_traces_and_daemon_status():
    try:
        from fastapi.testclient import TestClient
    except Exception:
        print("SKIP test_traces_and_daemon_status: TestClient unavailable")
        return
    client = TestClient(app)
    t = client.get("/api/traces").json()
    assert "traces" in t and isinstance(t["traces"], list)
    d = client.get("/api/daemon/status").json()
    assert "running" in d and "tick_seconds" in d
    print(f"PASS test_traces_and_daemon_status: daemon running={d['running']}")


if __name__ == "__main__":
    test_api_endpoints()
    test_auth_guard()
    print("PASS test_auth_guard")
    test_traces_and_daemon_status()
    print("\napi test passed.")
