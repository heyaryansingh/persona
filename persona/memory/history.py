"""Belief history (v5 P4) — append-only confidence/support over time.

The KG holds only the CURRENT state of a belief (v4 overwrote it in place). This records a
snapshot each harvest so you can see a belief strengthen, weaken, or get contradicted over time —
the evolution the owner wanted to see, and part of a defensible record. Per-persona SQLite.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone


class BeliefHistory:
    def __init__(self, path):
        self.path = str(path)
        from pathlib import Path
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._db().execute(
            "CREATE TABLE IF NOT EXISTS belief_history ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, claim_id TEXT, ts TEXT, confidence REAL, "
            "support INTEGER, independent INTEGER, contra INTEGER)")
        self._db().execute("CREATE INDEX IF NOT EXISTS ix_bh_claim ON belief_history(claim_id)")
        self._db().commit()

    def _db(self):
        c = getattr(self._local, "c", None)
        if c is None:
            c = sqlite3.connect(self.path, check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA busy_timeout=5000")
            self._local.c = c
        return c

    def snapshot(self, beliefs: list) -> None:
        """Append the current confidence/support of each belief (only if it changed since last)."""
        ts = datetime.now(timezone.utc).isoformat()
        for b in beliefs:
            cid = b.get("claim_id")
            if not cid:
                continue
            last = self._db().execute(
                "SELECT confidence, independent FROM belief_history WHERE claim_id=? "
                "ORDER BY id DESC LIMIT 1", (cid,)).fetchone()
            conf, indep = float(b.get("confidence", 0)), int(b.get("independent_sources", 0))
            if last and abs(last["confidence"] - conf) < 1e-6 and last["independent"] == indep:
                continue                       # unchanged — don't bloat the log
            self._db().execute(
                "INSERT INTO belief_history (claim_id, ts, confidence, support, independent, contra) "
                "VALUES (?,?,?,?,?,?)", (cid, ts, conf, indep, indep, 0))
        self._db().commit()

    def series(self, claim_id: str) -> list:
        rows = self._db().execute(
            "SELECT ts, confidence, independent FROM belief_history WHERE claim_id=? ORDER BY id",
            (claim_id,)).fetchall()
        return [{"ts": r["ts"], "confidence": r["confidence"], "independent": r["independent"]}
                for r in rows]
