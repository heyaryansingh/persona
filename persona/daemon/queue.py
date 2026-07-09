"""Durable task queue (v4) — stdlib SQLite, lease-based, crash-resume.

The daemon's backbone: tasks are leased (visibility timeout), completed, or failed with backoff.
On boot, expired leases reset to pending, so a crash mid-task loses nothing (the task re-runs).
No broker — one SQLite file. # ponytail: swap for Postgres+workers when this spans machines.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .. import config


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class Task:
    __slots__ = ("id", "type", "priority", "prompt", "params", "status", "attempts",
                 "parent_id", "result_ref")

    def __init__(self, row: sqlite3.Row):
        self.id = row["id"]
        self.type = row["type"]
        self.priority = row["priority"]
        self.prompt = row["prompt"]
        self.params = json.loads(row["params"])
        self.status = row["status"]
        self.attempts = row["attempts"]
        self.parent_id = row["parent_id"]
        self.result_ref = row["result_ref"]


class TaskQueue:
    def __init__(self, path: Optional[Path] = None, lease_seconds: int = None):
        self.path = str(path or config.QUEUE_DB)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.lease_seconds = lease_seconds or config.LEASE_SECONDS
        self._local = threading.local()
        self._init()
        self.reset_expired_leases()

    def _db(self) -> sqlite3.Connection:
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
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 5,
                prompt TEXT NOT NULL DEFAULT '',
                params TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','leased','done','failed')),
                attempts INTEGER NOT NULL DEFAULT 0,
                lease_until TEXT,
                parent_id INTEGER,
                result_ref TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_tasks_ready ON tasks(status, priority, created_at);
            """
        )
        self._db().commit()

    # ------------------------------------------------------------- write
    def enqueue(self, type: str, prompt: str = "", *, priority: int = 5, params: dict = None,
                parent_id: Optional[int] = None) -> int:
        now = _iso(_now())
        cur = self._db().execute(
            """INSERT INTO tasks (type, priority, prompt, params, parent_id, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?)""",
            (type, priority, prompt, json.dumps(params or {}), parent_id, now, now))
        self._db().commit()
        return cur.lastrowid

    def lease(self) -> Optional[Task]:
        """Atomically claim the highest-priority pending task (SQLite RETURNING, 3.35+)."""
        until = _iso(_now() + timedelta(seconds=self.lease_seconds))
        row = self._db().execute(
            """UPDATE tasks SET status='leased', lease_until=?, attempts=attempts+1, updated_at=?
               WHERE id = (SELECT id FROM tasks WHERE status='pending'
                           ORDER BY priority, created_at LIMIT 1)
               RETURNING *""",
            (until, _iso(_now()))).fetchone()
        self._db().commit()
        return Task(row) if row else None

    def complete(self, task_id: int, result_ref: str = "") -> None:
        self._db().execute(
            "UPDATE tasks SET status='done', result_ref=?, updated_at=? WHERE id=?",
            (result_ref, _iso(_now()), task_id))
        self._db().commit()

    def fail(self, task_id: int, max_attempts: int = 3) -> str:
        """Return to pending for retry, or mark failed (poison) after max_attempts."""
        row = self._db().execute("SELECT attempts FROM tasks WHERE id=?", (task_id,)).fetchone()
        attempts = row["attempts"] if row else max_attempts
        status = "failed" if attempts >= max_attempts else "pending"
        self._db().execute(
            "UPDATE tasks SET status=?, lease_until=NULL, updated_at=? WHERE id=?",
            (status, _iso(_now()), task_id))
        self._db().commit()
        return status

    def reset_expired_leases(self) -> int:
        """Crash-resume: any lease past its deadline returns to pending."""
        cur = self._db().execute(
            "UPDATE tasks SET status='pending', lease_until=NULL WHERE status='leased' "
            "AND (lease_until IS NULL OR lease_until < ?)", (_iso(_now()),))
        self._db().commit()
        return cur.rowcount

    # ------------------------------------------------------------- read
    def depth(self) -> int:
        return int(self._db().execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE status='pending'").fetchone()["n"])

    def counts(self) -> dict:
        rows = self._db().execute(
            "SELECT status, COUNT(*) AS n FROM tasks GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}
