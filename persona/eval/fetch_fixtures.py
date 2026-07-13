"""Fetch + freeze real benchmark subsets (idea I1.5 §5). OFFLINE-FIRST.

Run WITH network to pull LitQA2 / BixBench from upstream, select a stratified subset,
and freeze it hash-pinned (`.jsonl` + `.sha256` + MANIFEST, frozen BEFORE any scored run).
Items are NEVER hand-authored. If upstream is unreachable, the empty 'unfetched' fixtures
stay in place and the pipeline stays green with an honestly-absent score.

    python -m persona.eval.fetch_fixtures
"""
from __future__ import annotations

import json

from .fixtures import FIX_DIR, _sha256


def freeze(name: str, items: list, *, source_url: str, version: str,
           license: str, frozen_at_utc: str, selected_ids: list) -> str:
    """Write `<name>_subset.jsonl` + `.sha256` and update MANIFEST — the frozen-before-run guard.
    Deterministic: items are serialized with sorted keys so a fixed selection reproduces byte-identically."""
    body = "".join(json.dumps(it, sort_keys=True) + "\n" for it in items).encode("utf-8")
    (FIX_DIR / f"{name}_subset.jsonl").write_bytes(body)
    h = _sha256(body)
    (FIX_DIR / f"{name}_subset.sha256").write_text(f"{h}  {name}_subset.jsonl\n", encoding="utf-8")
    man = json.loads((FIX_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    man[name] = {"benchmark": name, "source_url": source_url, "license": license, "version": version,
                 "n": len(items), "selected_ids": selected_ids, "frozen_at_utc": frozen_at_utc,
                 "subset_sha256": h, "sourcing_status": "frozen"}
    (FIX_DIR / "MANIFEST.json").write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    return h


def fetch_litqa2():
    raise NotImplementedError(
        "Pull LitQA2 from https://github.com/Future-House/LAB-Bench (LitQA2 split); select a stratified "
        "subset mixing answerable + genuinely-insufficient items (so the abstention path is exercised); "
        "record selected_ids; then call freeze('litqa2', items, ...). Requires network + upstream license.")


def fetch_bixbench():
    raise NotImplementedError(
        "Pull BixBench from https://github.com/Future-House/BixBench; select tasks whose capsules run "
        "offline in the E12a-hardened sandbox (frozen time, pinned image digest); then freeze('bixbench', ...).")


if __name__ == "__main__":  # pragma: no cover - manual, network-gated
    for fn in (fetch_litqa2, fetch_bixbench):
        try:
            fn()
        except NotImplementedError as e:
            print(f"[unfetched] {fn.__name__}: {e}")
