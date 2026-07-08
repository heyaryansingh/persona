"""Persistent daily spend budget (v3 T2.3).

Audit: the cap was `AsyncSwarm.spent`, an in-memory counter that reset every swarm/tick — so a
day of many ticks could blow far past DAILY_BUDGET_USD, and a restart forgot everything spent.
This is a SQLite ledger keyed by UTC date: spend accumulates across ticks, swarms, and restarts
within the same day and resets at UTC midnight.

ponytail: soft cap. asyncio is single-threaded but a coroutine can pass can_spend() then await
the API call before add(), so a burst of concurrent reads near the ceiling can overshoot by up
to ~concurrency calls. That's an accepted ceiling for a background reader; tighten with a
reserve-then-commit lease if hard caps ever matter.
"""
from __future__ import annotations

from datetime import datetime, timezone


class DailyBudget:
    def __init__(self, store, cap_usd: float):
        self.store = store
        self.cap = float(cap_usd)
        store._db.execute(
            "CREATE TABLE IF NOT EXISTS budget_ledger (date TEXT PRIMARY KEY, spent_usd REAL NOT NULL DEFAULT 0)")
        store._db.commit()

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def spent_today(self) -> float:
        r = self.store._db.execute(
            "SELECT spent_usd FROM budget_ledger WHERE date=?", (self._today(),)).fetchone()
        return float(r["spent_usd"]) if r else 0.0

    def remaining(self) -> float:
        return max(0.0, self.cap - self.spent_today())

    def can_spend(self) -> bool:
        return self.remaining() > 0.0

    def add(self, usd: float) -> None:
        self.store._db.execute(
            "INSERT INTO budget_ledger (date, spent_usd) VALUES (?, ?) "
            "ON CONFLICT(date) DO UPDATE SET spent_usd = spent_usd + excluded.spent_usd",
            (self._today(), float(usd)))
        self.store._db.commit()
