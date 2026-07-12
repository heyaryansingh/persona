"""Append-only human labels for candidate claim conflicts.

This ledger is deliberately independent of the knowledge graph: a review records evidence-linked
human judgment but cannot mutate a claim or belief.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


LEDGER_NAME = "conflict_reviews.jsonl"
MAX_OPTIONAL_CHARS = 2_000
_LOCK = threading.Lock()


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


def _verify_unlocked(path: Path) -> dict:
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
        except (TypeError, ValueError) as exc:
            errors.append(f"invalid-record:{line_number}:{exc}")

    return {"ok": not errors, "errors": errors, "records": records,
            "record_count": len(records),
            "latest_sha256": expected_prev if records else None}


def verify_conflict_reviews(ops_dir: Path | str) -> dict:
    """Verify canonical encoding, record hashes, the hash chain, and record schema."""
    with _LOCK:
        return _verify_unlocked(_ledger_path(ops_dir))


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
    with _LOCK:
        prior = _verify_unlocked(path)
        if not prior["ok"]:
            raise LedgerIntegrityError("; ".join(prior["errors"]))
        record["prev_sha256"] = prior["latest_sha256"]
        record["record_id"] = _record_sha256(record)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as handle:
            handle.write(_canonical_json(record) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
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
