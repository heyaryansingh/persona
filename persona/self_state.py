"""The durable Self: human-readable living docs + a bi-temporal belief-store.

You can literally read its mind (BUILD_PLAN 5.5): identity/agenda/notebook/errors are
Markdown; beliefs are a JSON snapshot of the *core* tier backed by the SQLite store.

Two-tier memory (planning/LITERATURE.md §A, Letta-style): hydrate() pulls only the small
in-context core (identity + agenda + core-tier beliefs) into memory each wake; the large
archival tier stays in the store, queried on demand — so the self doesn't blow context
as beliefs.json / notebook.md grow.

Durability: beliefs live in the store (source of truth) + a human-readable beliefs.json
snapshot. Killing the Self object and reconstructing from the directory loses no belief.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .store import BeliefStore, Claim

_DEFAULT_IDENTITY = """# identity

name: (unnamed)
disposition: skeptical-exploratory
risk_appetite: moderate

_A persistent synthetic researcher. Given seed interests, it reads at scale, forms and
revises calibrated beliefs, and pulls in humans to resolve what it cannot test alone._
"""

_DEFAULT_AGENDA = """# agenda

## interests (attention weights over regions of the belief-graph)
<!-- name | weight | reason (revisable) -->

## active programs
<!-- one line each -->
"""


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Self:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.identity_path = self.root / "identity.md"
        self.agenda_path = self.root / "agenda.md"
        self.notebook_path = self.root / "notebook.md"
        self.errors_path = self.root / "errors.md"
        self.strategies_path = self.root / "strategies.md"
        self.beliefs_path = self.root / "beliefs.json"
        self.store = BeliefStore(str(self.root / "beliefs.db"))
        self._seed_files()
        # in-context core (populated by hydrate)
        self.identity: str = ""
        self.agenda: str = ""
        self.core: dict[str, Claim] = {}

    def _seed_files(self) -> None:
        if not self.identity_path.exists():
            self.identity_path.write_text(_DEFAULT_IDENTITY, encoding="utf-8")
        if not self.agenda_path.exists():
            self.agenda_path.write_text(_DEFAULT_AGENDA, encoding="utf-8")
        for p in (self.notebook_path, self.errors_path, self.strategies_path):
            if not p.exists():
                p.write_text(f"# {p.stem}\n\n", encoding="utf-8")

    # ------------------------------------------------------------- hydrate
    def hydrate(self) -> "Self":
        """Load ONLY the small core into context (two-tier). Archival stays in the store."""
        self.identity = self.identity_path.read_text(encoding="utf-8")
        self.agenda = self.agenda_path.read_text(encoding="utf-8")
        self.core = {c.claim_id: c for c in self.store.core_claims()}
        return self

    # ------------------------------------------------------------- notebook
    def notebook(self, entry: str) -> None:
        """Append one timestamped line in the researcher's own voice (the living notebook)."""
        with self.notebook_path.open("a", encoding="utf-8") as f:
            f.write(f"- `{_ts()}` {entry}\n")

    def log_error(self, entry: str) -> None:
        with self.errors_path.open("a", encoding="utf-8") as f:
            f.write(f"- `{_ts()}` {entry}\n")

    # ------------------------------------------------------------- beliefs
    def add_belief(self, claim: Claim) -> Claim:
        c = self.store.add_claim(claim)
        if c.tier == "core":
            self.core[c.claim_id] = c
        return c

    def persist_core(self) -> None:
        """Write a human-readable snapshot of the core beliefs (read its mind)."""
        snapshot = [
            {
                "claim_id": c.claim_id,
                "statement": c.statement,
                "calibrated_p": round(c.calibrated_p, 4),
                "provenance_state": c.provenance_state,
                "anchor": c.anchor,
                "independent_sources": self.store.independent_source_count(c.claim_id),
            }
            for c in self.store.core_claims()
        ]
        self.beliefs_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    def consolidate(self) -> None:
        """Sleep-time consolidation pass (novelty-gated; A-MEM-style). Stub for now:
        refresh the core snapshot. Full merge/prune/trajectory update lands with the engine.
        """
        self.persist_core()

    def close(self) -> None:
        self.store.close()
