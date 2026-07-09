"""Append-only event log (v4) — the single source of truth for the live-thought stream.

Every move the mind makes (THOUGHT, SPAWN, READ, CLAIM, BELIEF_UPDATE, TOOL, ESCALATE, ERROR)
is appended here and streamed to the UI via SSE. Nested spans (parent_id) let sub-agent spawns
render as a tree. stdlib sqlite3 (WAL) — no dependency, crash-durable.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventLog:
    def __init__(self, path: Optional[Path] = None):
        self.path = str(path or config.EVENTS_DB)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init()

    def _db(self) -> sqlite3.Connection:
        # one connection per thread (SSE readers + daemon writer may differ)
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return conn

    def _init(self) -> None:
        self._db().executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                type TEXT NOT NULL,
                actor TEXT NOT NULL DEFAULT 'self',
                parent_id INTEGER,
                message TEXT NOT NULL DEFAULT '',
                data TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS ix_events_id ON events(id);
            """
        )
        self._db().commit()

    def emit(self, type: str, message: str = "", *, actor: str = "self",
             parent_id: Optional[int] = None, **data) -> int:
        cur = self._db().execute(
            "INSERT INTO events (ts, type, actor, parent_id, message, data) VALUES (?,?,?,?,?,?)",
            (_now(), type, actor, parent_id, message, json.dumps(data, default=str)))
        self._db().commit()
        return cur.lastrowid

    def since(self, after_id: int = 0, limit: int = 500) -> list[dict]:
        rows = self._db().execute(
            "SELECT * FROM events WHERE id > ? ORDER BY id LIMIT ?", (after_id, limit)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["data"] = json.loads(d["data"])
            out.append(d)
        return out

    def latest_id(self) -> int:
        r = self._db().execute("SELECT COALESCE(MAX(id), 0) AS m FROM events").fetchone()
        return int(r["m"])

    def recent(self, n: int = 100) -> list[dict]:
        last = self.latest_id()
        return self.since(max(0, last - n))


def log() -> EventLog:
    """The CURRENT persona's event log (v5) — routed via the context persona; each persona has
    its own events.db, so streams never interleave across personas."""
    from .context import get_persona
    return get_persona().events
