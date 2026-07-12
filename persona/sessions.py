"""Append-only research sessions and content-addressed artifacts.

The event log is authoritative. Summaries, graphs, and reports are projections that can be rebuilt
from the public model/tool trace and immutable artifacts. This stores returned rationale and tool
evidence, never a model's private chain of thought.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:40] or "research"


def _write_json_atomic(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(path)


def _write_crate(root: Path, meta: dict) -> None:
    parts = [{"@id": "session.json"}, {"@id": "events.jsonl"}]
    entities = [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
         "about": {"@id": "./"},
         "conformsTo": {"@id": "https://w3id.org/ro/crate/1.3"}},
        {"@id": "./", "@type": "Dataset", "name": meta.get("title") or meta["question"],
         "dateCreated": meta["started_at"], "dateModified": meta.get("finished_at"),
         "description": meta["question"], "hasPart": parts},
        {"@id": "session.json", "@type": "File", "encodingFormat": "application/json"},
        {"@id": "events.jsonl", "@type": "File", "encodingFormat": "application/x-ndjson"},
    ]
    for artifact in meta.get("artifacts", []):
        parts.append({"@id": artifact["path"]})
        entities.append({"@id": artifact["path"], "@type": "File", "name": artifact["name"],
                         "encodingFormat": artifact["media_type"], "sha256": artifact["sha256"],
                         "contentSize": artifact["bytes"]})
    crate = {"@context": "https://w3id.org/ro/crate/1.3/context", "@graph": entities}
    _write_json_atomic(root / "ro-crate-metadata.json", crate)


def _event_log_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seal_event_log(root: Path, meta: dict) -> None:
    """Bind the session projection to the exact append-only event bytes."""
    meta["events_sha256"] = _event_log_sha256(root / "events.jsonl")
    _write_json_atomic(root / "session.json", meta)


class ResearchSession:
    def __init__(self, runs_dir: Path, question: str, *, model: str = "", metadata: dict = None):
        self.id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{_slug(question)}-{uuid.uuid4().hex[:8]}"
        self.root = Path(runs_dir) / self.id
        self.artifacts_dir = self.root / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=False)
        self.events_path = self.root / "events.jsonl"
        self._seq = 0
        self._artifacts: dict[str, dict] = {}
        self.meta = {"session_id": self.id, "question": question, "model": model,
                     "status": "running", "started_at": _now(), "finished_at": None,
                     "artifacts": [], **(metadata or {})}
        self._write_meta()
        self.root_event_id = self.record("session_started", {"question": question, "model": model})

    @property
    def artifact_ids(self) -> set[str]:
        return set(self._artifacts)

    def _write_meta(self) -> None:
        _write_json_atomic(self.root / "session.json", self.meta)

    def update(self, **fields) -> None:
        """Update the session projection; the event log remains the authoritative trace."""
        self.meta.update(fields)
        self._write_meta()

    def record(self, kind: str, payload: dict, *, parent_event_id: int | None = None) -> int:
        self._seq += 1
        event = {"event_id": self._seq, "parent_event_id": parent_event_id, "at": _now(),
                 "kind": kind, "payload": payload}
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        _seal_event_log(self.root, self.meta)
        return self._seq

    def store_bytes(self, name: str, data: bytes, *, media_type: str = "application/octet-stream",
                    parent_event_id: int | None = None) -> dict:
        sha = hashlib.sha256(data).hexdigest()
        suffix = Path(name).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
            suffix = ".bin"
        rel = f"artifacts/{sha}{suffix}"
        path = self.root / rel
        if not path.exists():
            path.write_bytes(data)
        artifact_id = f"artifact:{sha}"
        artifact = {"id": artifact_id, "name": Path(name).name,
                    "source_path": str(name).replace("\\", "/"), "path": rel, "sha256": sha,
                    "bytes": len(data), "media_type": media_type}
        if artifact_id not in self._artifacts:
            self._artifacts[artifact_id] = artifact
            self.meta["artifacts"].append(artifact)
            self._write_meta()
            self.record("artifact_stored", artifact, parent_event_id=parent_event_id)
        return artifact

    def store_text(self, name: str, text: str, *, media_type: str = "text/plain",
                   parent_event_id: int | None = None) -> dict:
        return self.store_bytes(name, (text or "").encode("utf-8"), media_type=media_type,
                                parent_event_id=parent_event_id)

    def store_json(self, name: str, value: object, *, parent_event_id: int | None = None) -> dict:
        return self.store_bytes(name, json.dumps(value, indent=2, ensure_ascii=False, default=str).encode(),
                                media_type="application/json", parent_event_id=parent_event_id)

    def finalize(self, status: str, *, title: str = "", conclusions: list | None = None,
                 reason: str = "", parent_event_id: int | None = None) -> None:
        self.meta.update({"status": status, "finished_at": _now(), "title": title,
                          "conclusions": conclusions or [], "reason": reason})
        try:
            start = datetime.fromisoformat(self.meta["started_at"])
            finish = datetime.fromisoformat(self.meta["finished_at"])
            self.meta["duration_ms"] = round((finish - start).total_seconds() * 1000)
        except (KeyError, TypeError, ValueError):
            pass
        self.record("session_finished", {"status": status, "title": title, "reason": reason,
                                         "conclusions": conclusions or []},
                    parent_event_id=parent_event_id or self.root_event_id)
        self._write_meta()
        self._write_crate()

    def _write_crate(self) -> None:
        _write_crate(self.root, self.meta)


def list_sessions(runs_dir: Path) -> list[dict]:
    sessions = []
    for path in Path(runs_dir).glob("*/session.json"):
        try:
            sessions.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(sessions, key=lambda x: x.get("started_at", ""), reverse=True)


def read_session(runs_dir: Path, session_id: str) -> dict | None:
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", session_id or ""):
        return None
    root = Path(runs_dir) / session_id
    meta_path, events_path = root / "session.json", root / "events.jsonl"
    if not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    events, read_errors = [], []
    if not events_path.exists():
        read_errors.append("events-log-missing")
    else:
        try:
            lines = events_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines, read_errors = [], ["events-log-unreadable"]
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                read_errors.append(f"event-json-invalid:{line_number}")
    return {"session": meta, "events": events, "read_errors": read_errors}


def append_session_artifact(runs_dir: Path, session_id: str, name: str, data: bytes, *,
                            media_type: str = "application/octet-stream",
                            parent_event_id: int | None = None) -> dict | None:
    """Append a post-run artifact without rewriting the prior event trace or source record."""
    loaded = read_session(runs_dir, session_id)
    if loaded is None:
        return None
    root, meta = Path(runs_dir) / session_id, loaded["session"]
    sha = hashlib.sha256(data).hexdigest()
    suffix = Path(name).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
        suffix = ".bin"
    rel = f"artifacts/{sha}{suffix}"
    path = root / rel
    if not path.exists():
        path.write_bytes(data)
    artifact_id = f"artifact:{sha}"
    existing = next((a for a in meta.get("artifacts", []) if a.get("id") == artifact_id), None)
    if existing:
        return existing
    artifact = {"id": artifact_id, "name": Path(name).name,
                "source_path": str(name).replace("\\", "/"), "path": rel,
                "sha256": sha, "bytes": len(data), "media_type": media_type}
    meta.setdefault("artifacts", []).append(artifact)
    next_id = max((e.get("event_id", 0) for e in loaded["events"]), default=0) + 1
    event = {"event_id": next_id, "parent_event_id": parent_event_id, "at": _now(),
             "kind": "artifact_stored", "payload": artifact}
    with (root / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    _seal_event_log(root, meta)
    _write_crate(root, meta)
    return artifact


def verify_session(runs_dir: Path, session_id: str) -> dict:
    """Replay the public trace as an integrity audit; no model calls and no science mutations."""
    loaded = read_session(runs_dir, session_id)
    if loaded is None:
        return {"ok": False, "session_id": session_id, "errors": ["session-not-found"],
                "checks": {}}
    root, meta, events = Path(runs_dir) / session_id, loaded["session"], loaded["events"]
    errors, warnings = list(loaded.get("read_errors", [])), []
    expected_event_log_sha = meta.get("events_sha256")
    if not expected_event_log_sha:
        warnings.append("event-log-unsealed")
    else:
        try:
            if _event_log_sha256(root / "events.jsonl") != expected_event_log_sha:
                errors.append("event-log-sha256-mismatch")
        except OSError:
            errors.append("event-log-unreadable")
    event_ids = [event.get("event_id") for event in events]
    expected = list(range(1, len(events) + 1))
    if event_ids != expected:
        errors.append("event-sequence-invalid")
    known_events = set(event_ids)
    bad_parents = [event["event_id"] for event in events
                   if event.get("parent_event_id") is not None and
                   event.get("parent_event_id") not in known_events]
    if bad_parents:
        errors.append(f"missing-parent-events:{','.join(map(str, bad_parents[:5]))}")
    checked_artifacts = 0
    for artifact in meta.get("artifacts", []):
        path = (root / artifact.get("path", "")).resolve()
        if root.resolve() not in path.parents or not path.is_file():
            errors.append(f"artifact-missing:{artifact.get('id', 'unknown')}")
            continue
        checked_artifacts += 1
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != artifact.get("sha256"):
            errors.append(f"artifact-hash-mismatch:{artifact.get('id', 'unknown')}")
        if len(data) != artifact.get("bytes"):
            errors.append(f"artifact-size-mismatch:{artifact.get('id', 'unknown')}")
    required = {f"claim:{claim_id}" for claim_id in meta.get("required_claim_ids", [])}
    cited = {evidence_id for item in meta.get("conclusions", [])
             for evidence_id in item.get("evidence_ids", [])}
    missing_required = sorted(required - cited)
    if meta.get("status") == "completed" and missing_required:
        errors.append(f"required-evidence-not-cited:{','.join(missing_required)}")
    crate_path = root / "ro-crate-metadata.json"
    if not crate_path.exists():
        errors.append("ro-crate-missing")
    else:
        try:
            crate = json.loads(crate_path.read_text(encoding="utf-8"))
            if crate.get("@context") != "https://w3id.org/ro/crate/1.3/context":
                errors.append("ro-crate-context-invalid")
        except json.JSONDecodeError:
            errors.append("ro-crate-invalid-json")
    response_cost = round(sum(float(event.get("payload", {}).get("cost_usd", 0))
                              for event in events if event.get("kind") == "model_response"), 6)
    if "cost_usd" in meta and abs(float(meta["cost_usd"]) - response_cost) > 0.000001:
        errors.append("cost-total-mismatch")
    if not any(event.get("kind") == "verifier_verdict" for event in events):
        warnings.append("no-verifier-verdict")
    checks = {"events": len(events), "artifacts": checked_artifacts,
              "required_evidence": len(required), "required_evidence_cited": len(required) - len(missing_required),
              "model_cost_usd": response_cost, "status": meta.get("status"),
              "verification": (meta.get("verification") or {}).get("verdict", "unverified")}
    return {"ok": not errors, "session_id": session_id, "errors": errors,
            "warnings": warnings, "checks": checks}


def audit_session(runs_dir: Path, session_id: str, verdict: str, reason: str) -> bool:
    """Append a verifier verdict without deleting or rewriting the original research trace."""
    if verdict not in {"verified", "contested", "invalidated"} or not isinstance(reason, str):
        raise ValueError("invalid session audit")
    data = read_session(runs_dir, session_id)
    if data is None or data.get("read_errors"):
        return False
    root = Path(runs_dir) / session_id
    previous_id = max((event.get("event_id", 0) for event in data["events"]), default=0)
    event = {"event_id": previous_id + 1, "parent_event_id": previous_id or None, "at": _now(),
             "kind": "verifier_verdict", "payload": {"verdict": verdict, "reason": reason}}
    with (root / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    meta = data["session"]
    meta["verification"] = {"verdict": verdict, "reason": reason, "at": event["at"]}
    if verdict == "invalidated":
        meta["status"] = "invalidated"
    _seal_event_log(root, meta)
    _write_crate(root, meta)
    return True


def seal_session_trace(runs_dir: Path, session_id: str) -> bool:
    """One-time compatibility seal for a valid legacy event log; no event is rewritten."""
    data = read_session(runs_dir, session_id)
    if data is None or data.get("read_errors"):
        return False
    root = Path(runs_dir) / session_id
    _seal_event_log(root, data["session"])
    _write_crate(root, data["session"])
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Verify a Persona research-session trace and artifacts.")
    parser.add_argument("runs_dir", type=Path)
    parser.add_argument("session_id")
    args = parser.parse_args()
    result = verify_session(args.runs_dir, args.session_id)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)
