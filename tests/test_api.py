"""API smoke test via FastAPI TestClient (no server). Run: python tests/test_api.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


if __name__ == "__main__":
    test_api_endpoints()
    print("\napi test passed.")
