"""Per-persona on-disk layout (v5 P2). One Paths object per persona — built at CREATE time, not
frozen at module import (the v4 bug that made multi-persona impossible)."""
from __future__ import annotations

from pathlib import Path


class Paths:
    def __init__(self, workspace):
        self.workspace = Path(workspace)

    @property
    def self_dir(self): return self.workspace / "self"
    @property
    def notes_dir(self): return self.workspace / "notes"
    @property
    def sources_dir(self): return self.workspace / "sources"
    @property
    def datasets_dir(self): return self.workspace / "datasets"
    @property
    def projects_dir(self): return self.workspace / "projects"
    @property
    def drafts_dir(self): return self.workspace / "drafts"
    @property
    def deliverables_dir(self): return self.workspace / "deliverables"
    @property
    def runs_dir(self): return self.workspace / "runs"
    @property
    def investigations_dir(self): return self.workspace / "investigations"
    @property
    def ops_dir(self): return self.workspace / ".persona"
    @property
    def queue_db(self): return self.ops_dir / "queue.db"
    @property
    def events_db(self): return self.ops_dir / "events.db"
    @property
    def budget_db(self): return self.ops_dir / "budget.db"
    @property
    def vectors_db(self): return self.ops_dir / "vectors.db"

    @property
    def uploads_dir(self): return self.workspace / "uploads"

    def ensure(self) -> None:
        for d in (self.self_dir, self.notes_dir, self.sources_dir, self.datasets_dir,
                  self.projects_dir, self.drafts_dir, self.deliverables_dir, self.runs_dir,
                  self.investigations_dir, self.ops_dir):
            d.mkdir(parents=True, exist_ok=True)

    def safe(self, relpath: str) -> Path:
        """Resolve `relpath` under the workspace, jailing against traversal/symlink escape.
        The one boundary every file/exec path routes through (v6). Raises ValueError on escape."""
        base = self.workspace.resolve()
        target = (base / (relpath or "").lstrip("/\\")).resolve()
        if target != base and base not in target.parents:
            raise ValueError(f"path escapes workspace: {relpath!r}")
        return target
