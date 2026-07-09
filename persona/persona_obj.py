"""Persona — a first-class, fully-isolated researcher mind (v5 P2/P3).

Owns ALL state that was process-global in v4: its own workspace (paths), FalkorDB graph, task
queue, event log, budget, canonicalizer, vector index, harvest lock, and daemon task. Multiple
Personas coexist in one process with zero shared mutable state; the current-persona contextvar
(persona/context.py) routes `log()/get_kg()/budget()/selfmind` to the right one per async task.
"""
from __future__ import annotations

import json
import threading

from . import config
from .paths import Paths


class Persona:
    def __init__(self, id: str, name: str, workspace, graph_name: str,
                 budget_usd: float = None):
        self.id = id
        self.name = name
        self.graph_name = graph_name
        self.paths = Paths(workspace)
        self.paths.ensure()
        self.budget_usd = budget_usd if budget_usd is not None else config.DAILY_BUDGET_USD
        self.harvest_lock = threading.Lock()
        self.daemon = None
        self._events = None
        self._budget = None
        self._kg = None
        self._vectors = None
        self._history = None

    # ---- lazily-built, per-persona services ----
    @property
    def events(self):
        if self._events is None:
            from .events import EventLog
            self._events = EventLog(self.paths.events_db)
        return self._events

    @property
    def budget(self):
        if self._budget is None:
            from .budget import DailyBudget
            self._budget = DailyBudget(self.paths.budget_db, self.cap_usd)
        return self._budget

    # ---- control plane (v6 P0): run-state + writable cap, persisted so it survives restarts ----
    @property
    def _control_path(self):
        return self.paths.ops_dir / "control.json"

    def _control(self) -> dict:
        p = self._control_path
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _write_control(self, d: dict) -> None:
        self.paths.ops_dir.mkdir(parents=True, exist_ok=True)
        self._control_path.write_text(json.dumps(d), encoding="utf-8")

    def run_state(self) -> str:
        return self._control().get("run_state", "RUNNING")

    def is_paused(self) -> bool:
        return self.run_state() == "PAUSED"

    def is_halted(self) -> bool:
        return self.run_state() == "HALTED"

    def set_run_state(self, state: str) -> None:
        assert state in ("RUNNING", "PAUSED", "HALTED"), state
        c = self._control(); c["run_state"] = state; self._write_control(c)

    @property
    def cap_usd(self) -> float:
        return float(self._control().get("cap_usd", self.budget_usd))

    def set_cap(self, cap: float) -> None:
        c = self._control(); c["cap_usd"] = max(0.0, float(cap)); self._write_control(c)
        if self._budget is not None:
            self._budget.cap = max(0.0, float(cap))

    @property
    def kg(self):
        if self._kg is None:
            from .memory.kg import KG
            self._kg = KG(name=self.graph_name, ops_dir=self.paths.ops_dir)
        return self._kg

    @property
    def vectors(self):
        if self._vectors is None:
            from .memory.vectors import VectorIndex
            self._vectors = VectorIndex(self.paths.vectors_db)
        return self._vectors

    @property
    def history(self):
        if self._history is None:
            from .memory.history import BeliefHistory
            self._history = BeliefHistory(self.paths.ops_dir / "belief_history.db")
        return self._history

    def queue(self):
        from .daemon.queue import TaskQueue
        return TaskQueue(self.paths.queue_db)

    # ---- self / status ----
    def is_seeded(self) -> bool:
        return (self.paths.self_dir / "interests.md").exists()

    def status(self) -> str:
        if self.is_halted():
            return "HALTED"
        if self.daemon is not None and not self.daemon.done():
            return "PAUSED" if self.is_paused() else "RUNNING"
        return "SEEDED" if self.is_seeded() else "UNSEEDED"

    def to_card(self) -> dict:
        try:
            st = self.kg.stats()
        except Exception:
            st = {"claims": 0, "entities": 0, "contradiction_edges": 0}
        return {"id": self.id, "name": self.name, "status": self.status(),
                "seeded": self.is_seeded(), "claims": st.get("claims", 0),
                "entities": st.get("entities", 0),
                "spent_today": round(self.budget.spent_today(), 3),
                "cap_usd": round(self.cap_usd, 2), "run_state": self.run_state(),
                "latest_event": self.events.latest_id()}
