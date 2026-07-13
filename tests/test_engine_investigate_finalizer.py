"""T4.1 — analyst.investigate() failure finalizer (regression).

Before the fix, an unexpected exception raised mid-investigation (the model API call, a sandbox/FS
error, a disk-full write) propagated straight out of investigate() and left the ResearchSession
stuck at status 'running' forever — a zombie that the UI/daemon would read as live work. The frozen
contract calls a silent wrong state into the belief-store the worst possible bug.

This test injects the exact previously-unguarded crash — the model call raising mid-run — and asserts:
  1. investigate() does not propagate the exception; it returns a structured {ok:False, reason:crashed}.
  2. the session ends 'invalidated', never left 'running'.
  3. the append-only trace still passes verify_session (replay integrity survives the crash).
"""
import types

from persona import context, sessions
from persona.paths import Paths
from persona.agents import analyst


class _BoomMessages:
    def create(self, **kwargs):
        raise RuntimeError("simulated model API failure mid-investigation")


class _BoomAnthropic:
    def __init__(self, *args, **kwargs):
        self.messages = _BoomMessages()


def _stub_persona(tmp_path):
    p = types.SimpleNamespace()
    p.paths = Paths(tmp_path)
    p.paths.ensure()
    return p


def test_investigate_crash_invalidates_session_and_replay_verifies(tmp_path, monkeypatch):
    # Pass the three entry gates; keep everything offline and $0.
    monkeypatch.setattr(analyst.config, "have_key", lambda: True)
    monkeypatch.setattr(analyst.config, "MODEL_WORKER", "test-model", raising=False)
    monkeypatch.setattr(
        analyst, "budget",
        lambda: types.SimpleNamespace(can_spend=lambda: True, add=lambda *_: None))
    monkeypatch.setattr(analyst.sandbox, "image_ready", lambda: True)
    monkeypatch.setattr(analyst.sandbox, "image_digest", lambda: "sha256:test")
    # The model call raises — the exact unguarded path T4.1 fixes.
    monkeypatch.setattr("anthropic.Anthropic", _BoomAnthropic)

    persona = _stub_persona(tmp_path)
    with context.use(persona):
        res = analyst.investigate("does gene X regulate pathway Y in condition Z?")

    # 1. no exception escaped; structured crash reported.
    assert res["ok"] is False, res
    assert res["reason"] == "crashed", res
    assert "RuntimeError" in res.get("error", ""), res
    sid = res["session_id"]

    # 2. the session is INVALIDATED, never left 'running'.
    runs_dir = persona.paths.runs_dir
    loaded = sessions.read_session(runs_dir, sid)
    assert loaded is not None, "crashed session must still be on disk"
    assert loaded["session"]["status"] == "invalidated", loaded["session"].get("status")
    assert "crashed" in (loaded["session"].get("reason") or "")
    # no other session left dangling in 'running'
    assert not any(s.get("status") == "running" for s in sessions.list_sessions(runs_dir))

    # 3. replay/integrity still verifies (verify_session skips the evidence gate off 'completed').
    verdict = sessions.verify_session(runs_dir, sid)
    assert verdict["ok"] is True, verdict["errors"]
    assert verdict["checks"]["status"] == "invalidated"
