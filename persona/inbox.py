"""Human-handoff inbox (FC-2).

When Persona cannot resolve a conflict itself it escalates to a human by filing a *handoff* — a
structured dossier of what decision is needed, why the swarm can't settle it, and the cheapest test
that would. Like ``conflict_reviews``, this is an append-only jsonl under the workspace that records
the ask but never mutates a claim or belief. The handoff_id is a content hash (no wall-clock), so an
identical dossier files to the same id — deterministic under test and naturally deduped.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

from .context import get_persona

INBOX_NAME = "handoffs.jsonl"
_CONFLICT_TYPES = {"temporal", "semantic", "misinformation", "insufficient"}
_REQUIRED = (
    "decision_requested", "why_unresolvable", "disagreeing", "conflict_type",
    "cheapest_test", "expected_updates", "uncertainty", "authority_boundary",
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _validate(kind: str, dossier: dict) -> None:
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("kind must be a non-empty string")
    if not isinstance(dossier, dict):
        raise ValueError("dossier must be a dict")
    missing = [k for k in _REQUIRED if k not in dossier]
    if missing:
        raise ValueError(f"dossier missing required keys: {', '.join(missing)}")
    if dossier["conflict_type"] not in _CONFLICT_TYPES:
        raise ValueError(f"conflict_type must be one of {sorted(_CONFLICT_TYPES)}")


def file_handoff(kind: str, dossier: dict) -> str:
    """Validate and durably append one human-handoff dossier. Returns its content-hash id."""
    _validate(kind, dossier)
    handoff_id = "ho_" + hashlib.sha256(_canonical([kind, dossier])).hexdigest()[:16]
    record = {"handoff_id": handoff_id, "kind": kind, "dossier": dossier,
              "filed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    path = get_persona().paths.ops_dir / INBOX_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(_canonical(record) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    return handoff_id
