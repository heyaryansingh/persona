"""Persona — a first-class, fully-isolated researcher mind (v5 P2/P3).

Owns ALL state that was process-global in v4: its own workspace (paths), FalkorDB graph, task
queue, event log, budget, canonicalizer, vector index, harvest lock, and daemon task. Multiple
Personas coexist in one process with zero shared mutable state; the current-persona contextvar
(persona/context.py) routes `log()/get_kg()/budget()/selfmind` to the right one per async task.
"""
from __future__ import annotations

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
            self._budget = DailyBudget(self.paths.budget_db, self.budget_usd)
        return self._budget

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

    def queue(self):
        from .daemon.queue import TaskQueue
        return TaskQueue(self.paths.queue_db)

    # ---- self / status ----
    def is_seeded(self) -> bool:
        return (self.paths.self_dir / "interests.md").exists()

    def status(self) -> str:
        if self.daemon is not None and not self.daemon.done():
            return "RUNNING"
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
                "latest_event": self.events.latest_id()}
