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
        from pathlib import Path
        self.path = str(path or (config.OPS_DIR / "budget.db"))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
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

    def can_read(self) -> bool:
        """Reading (scout/observe/bulk) stops at READING_BUDGET_FRACTION of the daily cap, RESERVING
        the rest of the budget for producing outputs — synthesis, papers, reviews, investigations —
        so a mind never burns its whole day on reading and ships nothing (the 'no paper produced' bug)."""
        frac = getattr(config, "READING_BUDGET_FRACTION", 0.65)
        return self.spent_today() < self.cap * frac and self.can_spend()

    def add(self, usd: float) -> None:
        self._db().execute(
            "INSERT INTO budget (date, spent) VALUES (?, ?) "
            "ON CONFLICT(date) DO UPDATE SET spent = spent + excluded.spent", (self._today(), float(usd)))
        self._db().commit()


def budget() -> DailyBudget:
    """The CURRENT persona's budget (v5) — routed via the context persona; each persona has its
    own daily cap + ledger."""
    from .context import get_persona
    return get_persona().budget
