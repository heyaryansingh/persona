"""M2 hardening — S4 consumer side of the re-audit budget-churn bug.

The ROOT fix for the busy-loop (S2 audit M2) is a staleness floor in watchlist.due() (S5) plus the
supervisor guarding on due() instead of entries() (S6). This test pins S4's half of the contract:
`audit.reaudit()` must make NO paid audit() call when due() yields nothing (empty OR fully-fresh
watchlist). That keeps the money path closed from the consumer side even if an upstream caller
regresses. reaudit() is intentionally left forceable so an explicit API/manual re-audit still runs;
the throttle belongs upstream (due()+supervisor), not here.
"""
from persona.agents import audit


def test_reaudit_no_spend_when_nothing_due(monkeypatch):
    from persona.memory import watchlist
    monkeypatch.setattr(watchlist, "due", lambda *a, **k: None)   # stale-gated / empty → nothing due

    called = {"audit": 0}

    def _boom(*a, **k):
        called["audit"] += 1
        raise AssertionError("reaudit made a PAID audit() call when nothing was due")

    monkeypatch.setattr(audit, "audit", _boom)                     # fail loudly if the paid path is hit

    result = audit.reaudit()
    assert result == {"ok": True, "reaudited": 0, "reason": "watchlist-empty"}
    assert called["audit"] == 0
