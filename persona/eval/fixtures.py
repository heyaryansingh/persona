"""Offline benchmark fixtures (idea I1.5). Frozen subsets of REAL published benchmarks
(LitQA2, BixBench — FutureHouse). The `.jsonl` is hash-pinned by a sibling `.sha256`
frozen BEFORE any scored run (same discipline as the conflict-gold bundle).

Non-negotiable honesty rule: items are NEVER model-invented. If the real data was not
fetched offline at build time, the fixture is empty and `sourcing_status == "unfetched"`
— the pipeline stays green and the score is honestly absent, never synthesized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

FIX_DIR = Path(__file__).resolve().parent / "fixtures"


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def manifest() -> dict:
    f = FIX_DIR / "MANIFEST.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def load_fixture(name: str) -> dict:
    """Load a frozen fixture. Verifies the `.jsonl` against its `.sha256` (tamper guard).
    Returns `{name, items, n, sourcing_status, verified}`. A missing or empty `.jsonl`
    yields an honest empty result (`n == 0`, `sourcing_status == "unfetched"`).
    Raises ValueError on a hash mismatch (tampered or stale fixture)."""
    meta = manifest().get(name, {})
    status = meta.get("sourcing_status", "unfetched")
    jsonl = FIX_DIR / f"{name}_subset.jsonl"
    if not jsonl.exists():
        return {"name": name, "items": [], "n": 0, "sourcing_status": "unfetched", "verified": True}
    raw = jsonl.read_bytes()
    shaf = FIX_DIR / f"{name}_subset.sha256"
    expected = shaf.read_text(encoding="utf-8").split()[0].strip() if shaf.exists() else None
    if expected is not None and _sha256(raw) != expected:
        raise ValueError(
            f"fixture {name!r} hash mismatch — tampered or stale "
            f"(manifest {expected}, file {_sha256(raw)})")
    items = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    return {
        "name": name,
        "items": items,
        "n": len(items),
        # empty file still reads as unfetched — no items means no benchmark gold present.
        "sourcing_status": status if items else "unfetched",
        "verified": True,
    }
