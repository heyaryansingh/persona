"""PersonaManager (v5 P3) — create, register, and run multiple fully-isolated personas.

Each persona gets its own workspace dir under PERSONAS_ROOT and its own FalkorDB graph
`persona_{id}`. A persisted registry (registry.json) survives restarts. The manager also owns the
per-persona daemon lifecycle (one asyncio task per running persona), all sharing the one process-
wide IngestService so global HTTP rate-limits/cache are respected.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from pathlib import Path

from . import config, context, selfmind
from .persona_obj import Persona


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:24]
    return s or "persona"


class PersonaManager:
    def __init__(self, root: Path = None):
        self.root = Path(root or config.PERSONAS_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.root / "registry.json"
        self._personas: dict[str, Persona] = {}
        self._daemons: dict[str, object] = {}          # id -> Daemon
        self._tasks: dict[str, asyncio.Task] = {}      # id -> run() task
        self._load()

    # ------------------------------------------------------------- registry
    def _load(self):
        if not self.registry_path.exists():
            return
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except Exception:
            return
        for e in data.get("personas", []):
            self._personas[e["id"]] = Persona(e["id"], e["name"], e["workspace"], e["graph_name"],
                                              budget_usd=e.get("budget_usd"))

    def _save(self):
        self.registry_path.write_text(json.dumps({"personas": [
            {"id": p.id, "name": p.name, "workspace": str(p.paths.workspace),
             "graph_name": p.graph_name, "budget_usd": p.budget_usd}
            for p in self._personas.values()]}, indent=2), encoding="utf-8")

    # ------------------------------------------------------------- lifecycle
    def create(self, name: str, interests=None, budget_usd: float = None) -> Persona:
        base = _slug(name)
        pid = base
        i = 0
        while pid in self._personas:                   # unique id
            i += 1
            pid = f"{base}-{hashlib.sha1((name + str(i)).encode()).hexdigest()[:4]}"
        p = Persona(pid, name, workspace=self.root / pid, graph_name=f"persona_{pid}",
                    budget_usd=budget_usd)
        self._personas[pid] = p
        self._save()
        if interests:
            with context.use(p):
                selfmind.seed([s for s in interests if s.strip()], name=name)
        return p

    def get(self, pid: str) -> Persona | None:
        return self._personas.get(pid)

    def list(self) -> list[Persona]:
        return list(self._personas.values())

    def seed(self, pid: str, interests: list[str]) -> bool:
        p = self.get(pid)
        if p is None:
            return False
        with context.use(p):
            fresh = selfmind.seed([s for s in interests if s.strip()], name=p.name)
        # NOTE: the API supervisor loop starts the daemon (must run in the event loop, not here —
        # this may be called from a sync request thread with no running loop).
        return fresh

    def delete(self, pid: str, wipe: bool = False) -> bool:
        p = self._personas.pop(pid, None)
        if p is None:
            return False
        self.stop(pid)
        try:
            with context.use(p):
                p.kg.g.query("MATCH (n) DETACH DELETE n")   # drop its graph contents
        except Exception:
            pass
        self._save()
        if wipe:
            import shutil
            shutil.rmtree(p.paths.workspace, ignore_errors=True)
        return True

    # ------------------------------------------------------------- daemons
    def start(self, persona: Persona) -> bool:
        if persona.id in self._tasks and not self._tasks[persona.id].done():
            return False
        from .daemon.supervisor import Daemon
        d = Daemon(persona=persona)
        self._daemons[persona.id] = d
        task = asyncio.create_task(d.run())
        self._tasks[persona.id] = task
        persona.daemon = task
        return True

    def stop(self, pid: str) -> bool:
        d = self._daemons.get(pid)
        if d is None:
            return False
        d.stop()
        return True

    def start_all_seeded(self):
        for p in self.list():
            if p.is_seeded():
                self.start(p)

    def stop_all(self):
        for pid in list(self._daemons):
            self.stop(pid)


_MANAGER: PersonaManager | None = None


def manager() -> PersonaManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = PersonaManager()
    return _MANAGER
