"""Append-only human labels for candidate claim conflicts.

This ledger is deliberately independent of the knowledge graph: a review records evidence-linked
human judgment but cannot mutate a claim or belief.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import secrets
import sys
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


LEDGER_NAME = "conflict_reviews.jsonl"
LABELS_LEDGER_NAME = "multirater_labels.jsonl"
REVIEWERS_NAME = "multirater_reviewers.jsonl"
MAX_OPTIONAL_CHARS = 2_000
MAX_PACKET_CHARS = 50_000
SCHEMA_VERSION = 2


# --- Cross-process advisory lock (replaces the old process-local threading.Lock so
# concurrent PROCESSES, not just threads, serialize verify-then-append). One byte-0
# lock on a per-ledger ".lock" sidecar; msvcrt on Windows, fcntl on POSIX.
_WINDOWS = sys.platform == "win32"
if _WINDOWS:
    import msvcrt
else:
    import fcntl


@contextlib.contextmanager
def _file_lock(ledger_path: Path):
    lock_path = ledger_path.parent / (ledger_path.name + ".lock")
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as handle:
        if _WINDOWS:
            while True:
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.01)  # ponytail: spin-retry; fine for low-contention append
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if _WINDOWS:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class ConflictVerdict(str, Enum):
    EXTRACTION_ERROR = "extraction_error"
    TRUE_REFUTATION = "true_refutation"
    CONTEXT_DIVERGENCE = "context_divergence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class LedgerIntegrityError(ValueError):
    """Raised before a read or append when the existing ledger is not trustworthy."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _clean_claim_id(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


_clean_str = _clean_claim_id  # non-empty string; reused for batch_id/reviewer_id/etc.


def _claim_ids(pos_claim_id: object, neg_claim_id: object) -> list[str]:
    ids = [_clean_claim_id("pos_claim_id", pos_claim_id),
           _clean_claim_id("neg_claim_id", neg_claim_id)]
    if ids[0] == ids[1]:
        raise ValueError("claim_ids must contain exactly two distinct claim IDs")
    return ids


def conflict_id(pos_claim_id: str, neg_claim_id: str) -> str:
    """Return the stable identity for the ordered positive/negative claim pair."""
    ids = _claim_ids(pos_claim_id, neg_claim_id)
    return "conflict_" + hashlib.sha256(_canonical_json(ids)).hexdigest()


def _clean_verdict(value: object) -> str:
    try:
        return ConflictVerdict(value).value
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid conflict verdict") from exc


def _clean_rationale(value: object) -> str:
    if not isinstance(value, str) or len(value.strip()) < 20:
        raise ValueError("rationale must contain at least 20 characters")
    return value.strip()


def _clean_confidence(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be a number from 0 to 1")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ValueError("confidence must be a number from 0 to 1")
    return result


def _clean_optional(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    result = value.strip()
    if len(result) > MAX_OPTIONAL_CHARS:
        raise ValueError(f"{name} exceeds {MAX_OPTIONAL_CHARS} characters")
    return result


def _record_sha256(record: dict) -> str:
    payload = {key: value for key, value in record.items() if key != "record_id"}
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _ledger_path(ops_dir: Path | str) -> Path:
    return Path(ops_dir) / LEDGER_NAME


def _walk_chain(path: Path, validate_record) -> dict:
    """Verify canonical encoding, per-record hash, and the prev-hash chain for one JSONL
    ledger. `validate_record(record)` raises ValueError/TypeError for schema violations
    (reported as invalid-record:N:<msg>). Shared by every append-only hash-chained ledger."""
    if not path.exists():
        return {"ok": True, "errors": [], "records": [], "record_count": 0,
                "latest_sha256": None}
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return {"ok": False, "errors": [f"ledger-unreadable:{exc}"], "records": [],
                "record_count": 0, "latest_sha256": None}
    errors: list[str] = []
    if raw and not raw.endswith(b"\n"):
        errors.append("ledger-truncated")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return {"ok": False, "errors": ["ledger-not-utf8"], "records": [],
                "record_count": 0, "latest_sha256": None}

    records: list[dict] = []
    expected_prev = None
    for line_number, line in enumerate(lines, 1):
        if not line:
            errors.append(f"blank-line:{line_number}")
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"invalid-json:{line_number}")
            continue
        if not isinstance(record, dict):
            errors.append(f"record-not-object:{line_number}")
            continue
        records.append(record)
        if line.encode("utf-8") != _canonical_json(record):
            errors.append(f"noncanonical-json:{line_number}")

        calculated_sha = _record_sha256(record)
        if record.get("record_id") != calculated_sha:
            errors.append(f"record-hash-mismatch:{line_number}")
        if record.get("prev_sha256") != expected_prev:
            errors.append(f"hash-chain-mismatch:{line_number}")
        expected_prev = calculated_sha

        try:
            validate_record(record)
        except (TypeError, ValueError) as exc:
            errors.append(f"invalid-record:{line_number}:{exc}")

    return {"ok": not errors, "errors": errors, "records": records,
            "record_count": len(records),
            "latest_sha256": expected_prev if records else None}


def _validate_review_record(record: dict) -> None:
    claim_ids = record.get("claim_ids")
    if not isinstance(claim_ids, list) or len(claim_ids) != 2:
        raise ValueError("claim_ids must contain exactly two claim IDs")
    ids = _claim_ids(*claim_ids)
    if record.get("conflict_id") != conflict_id(*ids):
        raise ValueError("conflict_id does not match claim_ids")
    _clean_verdict(record.get("verdict"))
    _clean_rationale(record.get("rationale"))
    _clean_confidence(record.get("confidence"))
    _clean_optional("qualifier", record.get("qualifier", ""))
    _clean_optional("next_check", record.get("next_check", ""))
    if not isinstance(record.get("reviewed_at"), str) or not record["reviewed_at"]:
        raise ValueError("reviewed_at must be a non-empty string")


def _verify_unlocked(path: Path) -> dict:
    return _walk_chain(path, _validate_review_record)


def _append_line(path: Path, record: dict) -> None:
    """Durably append one canonical record line (flush + fsync). Caller holds the lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(_canonical_json(record) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def verify_conflict_reviews(ops_dir: Path | str) -> dict:
    """Verify canonical encoding, record hashes, the hash chain, and record schema."""
    path = _ledger_path(ops_dir)
    with _file_lock(path):
        return _verify_unlocked(path)


def read_conflict_reviews(ops_dir: Path | str) -> list[dict]:
    """Read the ledger only when its complete history verifies."""
    result = verify_conflict_reviews(ops_dir)
    if not result["ok"]:
        raise LedgerIntegrityError("; ".join(result["errors"]))
    return result["records"]


def append_conflict_review(
    ops_dir: Path | str,
    *,
    pos_claim_id: str,
    neg_claim_id: str,
    verdict: ConflictVerdict | str,
    rationale: str,
    confidence: float,
    qualifier: str = "",
    next_check: str = "",
) -> dict:
    """Validate and durably append one review without touching the knowledge graph."""
    ids = _claim_ids(pos_claim_id, neg_claim_id)
    record = {
        "claim_ids": ids,
        "confidence": _clean_confidence(confidence),
        "conflict_id": conflict_id(*ids),
        "next_check": _clean_optional("next_check", next_check),
        "qualifier": _clean_optional("qualifier", qualifier),
        "rationale": _clean_rationale(rationale),
        "reviewed_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "verdict": _clean_verdict(verdict),
    }
    path = _ledger_path(ops_dir)
    with _file_lock(path):
        prior = _verify_unlocked(path)
        if not prior["ok"]:
            raise LedgerIntegrityError("; ".join(prior["errors"]))
        record["prev_sha256"] = prior["latest_sha256"]
        record["record_id"] = _record_sha256(record)
        _append_line(path, record)
    return record


def summarize_conflict_reviews(ops_dir: Path | str) -> dict[str, dict]:
    """Return the latest review and total review count for every conflict."""
    summaries: dict[str, dict] = {}
    for record in read_conflict_reviews(ops_dir):
        summary = summaries.setdefault(record["conflict_id"], {
            "conflict_id": record["conflict_id"],
            "claim_ids": record["claim_ids"],
            "review_count": 0,
            "latest": None,
        })
        summary["review_count"] += 1
        summary["latest"] = record
    return summaries


# =====================================================================================
# §A(v2) Multi-rater blinded acquisition layer.
#
# Purpose: collect two INDEPENDENT human labels per candidate conflict without leaking
# the stored positive/negative sign to the reviewer. A batch of pairs is FROZEN (content
# + seed hashed) before any collection; each (reviewer, conflict) gets a deterministic
# side permutation derived from the frozen seed, so packet_A/packet_B never correlate
# with pos/neg. Labels land in a second append-only hash-chained ledger. Nothing here
# ever mutates the knowledge graph, and labels are NEVER synthesized: with no enrolled
# reviewer the terminal state is the frozen bundle.
# =====================================================================================


class DuplicateLabelError(ValueError):
    """Raised when a reviewer tries to label the same conflict twice within a batch."""


def _clean_packet(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if len(value) > MAX_PACKET_CHARS:
        raise ValueError(f"{name} exceeds {MAX_PACKET_CHARS} characters")
    return value


def _clean_seed(value: object) -> object:
    # Seed is recorded verbatim in the frozen manifest, so it must be a stable scalar
    # (no wall-clock, no float rounding surprises). int or non-empty str only.
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("seed must be an int or a non-empty string")
    if isinstance(value, str) and not value.strip():
        raise ValueError("seed must be an int or a non-empty string")
    return value


def assignment_id(batch_id: str, conflict_id: str, reviewer_id: str) -> str:
    """Deterministic identity for one (batch, conflict, reviewer) assignment."""
    key = [_clean_str("batch_id", batch_id),
           _clean_str("conflict_id", conflict_id),
           _clean_str("reviewer_id", reviewer_id)]
    return hashlib.sha256(_canonical_json(key)).hexdigest()


def _side_order(seed: object, assignment_id_value: str) -> int:
    """0 => slot A carries the positive side, 1 => slot A carries the negative side.
    Pure function of the FROZEN seed and the assignment identity — the per-assignment
    permutation is fixed at batch-freeze, not minted at serve time."""
    digest = hashlib.sha256(
        _canonical_json({"assignment_id": assignment_id_value, "seed": seed})).digest()
    return digest[0] & 1


# --- Reviewer enrolment: reviewer_id is a SERVER-ISSUED opaque token, never client text.

def enrol_reviewer(ops_dir: Path | str) -> str:
    """Mint an opaque server-issued reviewer token and durably record the enrolment."""
    token = "rev_" + secrets.token_hex(16)
    path = Path(ops_dir) / REVIEWERS_NAME
    record = {"enrolled_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
              "reviewer_id": token}
    with _file_lock(path):
        _append_line(path, record)
    return token


def enrolled_reviewers(ops_dir: Path | str) -> set[str]:
    path = Path(ops_dir) / REVIEWERS_NAME
    if not path.exists():
        return set()
    ids: set[str] = set()
    for line in path.read_bytes().decode("utf-8").splitlines():
        if line:
            ids.add(json.loads(line)["reviewer_id"])
    return ids


def _require_enrolled(ops_dir: Path | str, reviewer_id: str) -> None:
    if reviewer_id not in enrolled_reviewers(ops_dir):
        raise ValueError("reviewer_id is not a server-issued enrolled token")


# --- Batch freeze: deterministic, content+seed hashed, no wall-clock.

def _manifest_paths(ops_dir: Path | str, batch_id: str) -> tuple[Path, Path]:
    base = Path(ops_dir)
    return base / f"{batch_id}.manifest.json", base / f"{batch_id}.manifest.sha256"


def freeze_batch(ops_dir: Path | str, pairs: list[dict], seed: object) -> dict:
    """Freeze N stratified conflict pairs into a blinded batch manifest whose content hash
    is fixed BEFORE any label is collected. Deterministic: same pairs + seed => byte-identical
    manifest and batch_id. Each `pair` is {pos_claim_id, neg_claim_id, pos_packet, neg_packet}.
    The manifest is the sealed server-side source of truth (holds the pos/neg map + seed) and
    is NEVER served to reviewers — reviewers only ever see build_assignment() output."""
    if not pairs:
        raise ValueError("cannot freeze an empty batch")
    frozen_pairs: list[dict] = []
    seen: set[str] = set()
    for pair in pairs:
        pos = _clean_claim_id("pos_claim_id", pair.get("pos_claim_id"))
        neg = _clean_claim_id("neg_claim_id", pair.get("neg_claim_id"))
        cid = conflict_id(pos, neg)
        if cid in seen:
            raise ValueError(f"duplicate conflict in batch: {cid}")
        seen.add(cid)
        frozen_pairs.append({
            "conflict_id": cid,
            "neg_claim_id": neg,
            "neg_packet": _clean_packet("neg_packet", pair.get("neg_packet", "")),
            "pos_claim_id": pos,
            "pos_packet": _clean_packet("pos_packet", pair.get("pos_packet", "")),
        })
    core = {"pairs": frozen_pairs, "schema_version": SCHEMA_VERSION, "seed": _clean_seed(seed)}
    batch_id = "batch_" + hashlib.sha256(_canonical_json(core)).hexdigest()
    manifest = {"batch_id": batch_id, **core}
    body = _canonical_json(manifest)
    manifest_path, sha_path = _manifest_paths(ops_dir, batch_id)
    with _file_lock(manifest_path):
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_bytes(body)
        sha_path.write_text(hashlib.sha256(body).hexdigest(), encoding="utf-8")
    return manifest


def load_batch(ops_dir: Path | str, batch_id: str) -> dict:
    """Load a frozen batch manifest, refusing any that has been tampered with.
    Tamper on ANY byte breaks either the .sha256 anchor, the canonical encoding,
    or the self-derived batch_id."""
    manifest_path, sha_path = _manifest_paths(ops_dir, batch_id)
    body = manifest_path.read_bytes()
    expected = sha_path.read_text(encoding="utf-8").strip()
    if hashlib.sha256(body).hexdigest() != expected:
        raise LedgerIntegrityError(f"batch manifest hash mismatch: {batch_id}")
    if _canonical_json(json.loads(body)) != body:
        raise LedgerIntegrityError(f"batch manifest not canonical: {batch_id}")
    manifest = json.loads(body)
    core = {k: manifest.get(k) for k in ("pairs", "schema_version", "seed")}
    if manifest.get("batch_id") != "batch_" + hashlib.sha256(_canonical_json(core)).hexdigest():
        raise LedgerIntegrityError(f"batch_id does not match content: {batch_id}")
    return manifest


def verify_batch(ops_dir: Path | str, batch_id: str) -> bool:
    try:
        load_batch(ops_dir, batch_id)
        return True
    except (LedgerIntegrityError, OSError, ValueError, json.JSONDecodeError):
        return False


# --- Serve one blinded assignment (already permuted; no sign-bearing field).

def build_assignment(ops_dir: Path | str, *, batch_id: str, conflict_id: str,
                     reviewer_id: str) -> dict:
    """Return the reviewer-facing BlindedAssignment for one (batch, conflict, reviewer).
    packet_A / packet_B are ALREADY permuted per the frozen per-assignment side order.
    No served field (packets, order, conflict_id) correlates with the stored pos/neg sign,
    and the A/B->pos/neg map is sealed server-side (recomputable only from the frozen seed)."""
    _require_enrolled(ops_dir, reviewer_id)
    manifest = load_batch(ops_dir, batch_id)
    pair = next((p for p in manifest["pairs"] if p["conflict_id"] == conflict_id), None)
    if pair is None:
        raise ValueError(f"conflict_id not in batch: {conflict_id}")
    aid = assignment_id(batch_id, conflict_id, reviewer_id)
    if _side_order(manifest["seed"], aid) == 0:
        packet_a, packet_b = pair["pos_packet"], pair["neg_packet"]
    else:
        packet_a, packet_b = pair["neg_packet"], pair["pos_packet"]
    return {
        "assignment_id": aid,
        "batch_id": batch_id,
        "conflict_id": conflict_id,
        "packet_A": packet_a,
        "packet_B": packet_b,
        "reviewer_id": reviewer_id,
        "schema_version": SCHEMA_VERSION,
    }


# --- Label ledger (second append-only hash-chained ledger).

def _validate_label_record(record: dict) -> None:
    batch_id = _clean_str("batch_id", record.get("batch_id"))
    cid = _clean_str("conflict_id", record.get("conflict_id"))
    reviewer_id = _clean_str("reviewer_id", record.get("reviewer_id"))
    if record.get("assignment_id") != assignment_id(batch_id, cid, reviewer_id):
        raise ValueError("assignment_id does not match batch/conflict/reviewer")
    _clean_verdict(record.get("label"))
    _clean_rationale(record.get("rationale"))
    if record.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected schema_version")
    if not isinstance(record.get("ts"), str) or not record["ts"]:
        raise ValueError("ts must be a non-empty string")


def _labels_path(ops_dir: Path | str) -> Path:
    return Path(ops_dir) / LABELS_LEDGER_NAME


def verify_review_labels(ops_dir: Path | str) -> dict:
    path = _labels_path(ops_dir)
    with _file_lock(path):
        return _walk_chain(path, _validate_label_record)


def read_review_labels(ops_dir: Path | str) -> list[dict]:
    result = verify_review_labels(ops_dir)
    if not result["ok"]:
        raise LedgerIntegrityError("; ".join(result["errors"]))
    return result["records"]


def append_review_label(ops_dir: Path | str, *, batch_id: str, conflict_id: str,
                        reviewer_id: str, label: ConflictVerdict | str,
                        rationale: str) -> dict:
    """Durably append one blinded review label. Enforces: enrolled reviewer, conflict is in
    the (untampered) frozen batch, exactly one label per (reviewer_id, conflict_id, batch_id),
    and label.assignment_id == sealed assignment. Never touches the knowledge graph."""
    batch_id = _clean_str("batch_id", batch_id)
    cid = _clean_str("conflict_id", conflict_id)
    reviewer_id = _clean_str("reviewer_id", reviewer_id)
    record = {
        "assignment_id": assignment_id(batch_id, cid, reviewer_id),
        "batch_id": batch_id,
        "conflict_id": cid,
        "label": _clean_verdict(label),
        "rationale": _clean_rationale(rationale),
        "reviewer_id": reviewer_id,
        "schema_version": SCHEMA_VERSION,
        "ts": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
    }
    _require_enrolled(ops_dir, reviewer_id)
    manifest = load_batch(ops_dir, batch_id)  # also refuses a tampered batch
    if not any(p["conflict_id"] == cid for p in manifest["pairs"]):
        raise ValueError(f"conflict_id not in batch: {cid}")
    path = _labels_path(ops_dir)
    dedup_key = (reviewer_id, cid, batch_id)
    with _file_lock(path):
        prior = _walk_chain(path, _validate_label_record)
        if not prior["ok"]:
            raise LedgerIntegrityError("; ".join(prior["errors"]))
        for existing in prior["records"]:
            if (existing["reviewer_id"], existing["conflict_id"],
                    existing["batch_id"]) == dedup_key:
                raise DuplicateLabelError(
                    f"reviewer already labelled this conflict in batch: {dedup_key}")
        record["prev_sha256"] = prior["latest_sha256"]
        record["record_id"] = _record_sha256(record)
        _append_line(path, record)
    return record
