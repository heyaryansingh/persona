"""M2 — staleness floor on watchlist.due() stops the reaudit busy-loop.

due(min_age_hours) returns the least-recent entry ONLY if its last_audit is older than the floor,
else None. Deterministic, no network. We monkeypatch _dir() to a tmp dir so add()/entries() write
there instead of needing a live persona workspace.
"""
from datetime import datetime, timedelta, timezone

from persona.memory import watchlist


def _iso(dt):
    return dt.isoformat(timespec="seconds")


def test_just_audited_is_not_due(monkeypatch, tmp_path):
    monkeypatch.setattr(watchlist, "_dir", lambda: tmp_path)
    watchlist.add("Fresh paper", 0.5, "contested", slug="src_fresh")  # last_audit = now
    assert watchlist.due(min_age_hours=12) is None                    # younger than floor → throttled


def test_stale_entry_is_due(monkeypatch, tmp_path):
    monkeypatch.setattr(watchlist, "_dir", lambda: tmp_path)
    watchlist.add("Old paper", 0.5, "contested", slug="src_old")
    # backdate its last_audit past the floor
    ents = watchlist.entries()
    ents[0]["last_audit"] = _iso(datetime.now(timezone.utc) - timedelta(hours=48))
    watchlist._write(ents)
    got = watchlist.due(min_age_hours=12)
    assert got is not None and got["key"] == "slug:src_old"


def test_env_override(monkeypatch, tmp_path):
    monkeypatch.setattr(watchlist, "_dir", lambda: tmp_path)
    watchlist.add("Recent paper", 0.5, "contested", slug="src_recent")
    ents = watchlist.entries()
    ents[0]["last_audit"] = _iso(datetime.now(timezone.utc) - timedelta(hours=6))
    watchlist._write(ents)
    assert watchlist.due(min_age_hours=12) is None          # 6h < 12h default-ish → not due
    monkeypatch.setenv("PERSONA_REAUDIT_MIN_HOURS", "4")
    assert watchlist.due() is not None                       # env floor 4h < 6h age → due
