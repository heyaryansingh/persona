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

# FC-1 (Lane 1 provides) — task types this lane's heterogeneous team introduces. The queue stores the
# `type` as a free string (only `status` is CHECK-constrained), so these constants are the single
# source of truth other lanes enqueue against; the handlers live in worker.py's append-only registry.
TASK_VERIFY = "verify"          # 1.2 — a tool-grounded verifier agent re-checks a high-value claim
TASK_DEBATE = "debate"          # 1.3 — a gated two-side debate on a contested claim
TASK_STALENESS = "staleness"    # runs Lane 2's conflicts.revisit_pass (budget-churn-safe re-check)
FC1_TASK_TYPES = frozenset({TASK_VERIFY, TASK_DEBATE, TASK_STALENESS})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class Task:
    __slots__ = ("id", "type", "priority", "prompt", "params", "status", "attempts",
                 "parent_id", "result_ref", "investigation_id", "step_idx", "depends_on")

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
        keys = row.keys()
        self.investigation_id = row["investigation_id"] if "investigation_id" in keys else None
        self.step_idx = row["step_idx"] if "step_idx" in keys else None
        self.depends_on = row["depends_on"] if "depends_on" in keys else None


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
                investigation_id TEXT,
                step_idx INTEGER,
                depends_on TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_tasks_ready ON tasks(status, priority, created_at);
            """
        )
        # migrate older DBs that predate the investigation/team columns
        cols = {r["name"] for r in self._db().execute("PRAGMA table_info(tasks)").fetchall()}
        for col in ("investigation_id TEXT", "step_idx INTEGER", "depends_on TEXT"):
            if col.split()[0] not in cols:
                self._db().execute(f"ALTER TABLE tasks ADD COLUMN {col}")
        self._db().commit()

    # ------------------------------------------------------------- write
    def enqueue(self, type: str, prompt: str = "", *, priority: int = 5, params: dict = None,
                parent_id: Optional[int] = None, investigation_id: Optional[str] = None,
                step_idx: Optional[int] = None, depends_on: Optional[list] = None) -> int:
        now = _iso(_now())
        cur = self._db().execute(
            """INSERT INTO tasks (type, priority, prompt, params, parent_id, investigation_id,
                                  step_idx, depends_on, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (type, priority, prompt, json.dumps(params or {}), parent_id, investigation_id,
             step_idx, json.dumps(depends_on) if depends_on else None, now, now))
        self._db().commit()
        return cur.lastrowid

    def lease(self) -> Optional[Task]:
        """Atomically claim the highest-priority RUNNABLE pending task. A task is runnable only when
        every task in its `depends_on` has reached a terminal state (done/failed) — this is the team
        engine's join: a step waits for its upstream steps, but a permanently-failed dep never
        deadlocks it (it degrades gracefully). Deps are checked with SQLite JSON1 (json_each)."""
        until = _iso(_now() + timedelta(seconds=self.lease_seconds))
        row = self._db().execute(
            """UPDATE tasks SET status='leased', lease_until=?, attempts=attempts+1, updated_at=?
               WHERE id = (
                   SELECT id FROM tasks t WHERE t.status='pending'
                   AND NOT EXISTS (
                       SELECT 1 FROM json_each(COALESCE(NULLIF(t.depends_on,''),'[]')) je
                       JOIN tasks dep ON dep.id = je.value
                       WHERE dep.status IN ('pending','leased'))
                   ORDER BY t.priority, t.created_at LIMIT 1)
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

    def investigation_steps(self, investigation_id: str) -> list[dict]:
        """The step-tasks of one investigation, for the coordinator: [{step_idx,type,status,result_ref}]."""
        rows = self._db().execute(
            "SELECT id, step_idx, type, status, result_ref FROM tasks "
            "WHERE investigation_id=? AND step_idx IS NOT NULL ORDER BY step_idx, id",
            (investigation_id,)).fetchall()
        return [{"id": r["id"], "step_idx": r["step_idx"], "type": r["type"],
                 "status": r["status"], "result_ref": r["result_ref"]} for r in rows]

    def active(self, recent: int = 10) -> dict:
        """Live snapshot for the swarm view: currently-leased tasks (what each worker is doing) +
        the most recently completed ones, with a human 'target' derived from the task params."""
        def shape(r):
            try:
                p = json.loads(r["params"] or "{}")
            except Exception:
                p = {}
            target = (p.get("topic") or p.get("interest") or p.get("question")
                      or p.get("goal") or p.get("url") or (r["prompt"] or "")).strip()
            out = {"id": r["id"], "type": r["type"], "parent_id": r["parent_id"],
                   "target": target[:140], "updated_at": r["updated_at"]}
            if "investigation_id" in r.keys():
                out["investigation_id"] = r["investigation_id"]
            if "result_ref" in r.keys():
                out["result"] = r["result_ref"]
            return out
        db = self._db()
        leased = db.execute(
            "SELECT id, type, prompt, params, parent_id, investigation_id, updated_at FROM tasks "
            "WHERE status='leased' ORDER BY updated_at DESC LIMIT 60").fetchall()
        done = db.execute(
            "SELECT id, type, prompt, params, parent_id, investigation_id, result_ref, updated_at "
            "FROM tasks WHERE status='done' ORDER BY id DESC LIMIT ?", (recent,)).fetchall()
        # pending (queued steps not yet started) count toward the honest "fleet in flight"
        pending = db.execute(
            "SELECT id, type, prompt, params, parent_id, investigation_id, updated_at FROM tasks "
            "WHERE status='pending' ORDER BY priority, created_at LIMIT 60").fetchall()
        return {"active": [shape(r) for r in leased], "recent": [shape(r) for r in done],
                "queued": [shape(r) for r in pending], "counts": self.counts()}
