"""Persistent daily spend budget (v4) — SQLite keyed by UTC date, survives restarts and
accumulates across the always-on day (resets at UTC midnight). The reader checks it before each
paid extraction; the scheduler eases off near the cap (backpressure). Soft cap (a few concurrent
reads can overshoot slightly — acceptable for a background reader).
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone

from . import config


class DailyBudget:
    def __init__(self, path=None, cap_usd: float = None):
        config.ensure_workspace()
        self.path = str(path or (config.OPS_DIR / "budget.db"))
        self.cap = float(cap_usd if cap_usd is not None else config.DAILY_BUDGET_USD)
        self._local = threading.local()
        self._db().execute(
            "CREATE TABLE IF NOT EXISTS budget (date TEXT PRIMARY KEY, spent REAL NOT NULL DEFAULT 0)")
        self._db().commit()

    def _db(self):
        c = getattr(self._local, "c", None)
        if c is None:
            c = sqlite3.connect(self.path, check_same_thread=False)
            c.execute("PRAGMA busy_timeout=5000")
            self._local.c = c
        return c

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def spent_today(self) -> float:
        r = self._db().execute("SELECT spent FROM budget WHERE date=?", (self._today(),)).fetchone()
        return float(r[0]) if r else 0.0

    def remaining(self) -> float:
        return max(0.0, self.cap - self.spent_today())

    def can_spend(self) -> bool:
        return self.remaining() > 0.0

    def add(self, usd: float) -> None:
        self._db().execute(
            "INSERT INTO budget (date, spent) VALUES (?, ?) "
            "ON CONFLICT(date) DO UPDATE SET spent = spent + excluded.spent", (self._today(), float(usd)))
        self._db().commit()


_B = None


def budget() -> DailyBudget:
    global _B
    if _B is None:
        _B = DailyBudget()
    return _B
