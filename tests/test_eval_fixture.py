"""Offline eval-fixture guard (idea I1.5, Lane 4 / S3). Pure, offline, $0.
Asserts: FC-7 shape, honest-empty when unfetched, hash tamper-guard, determinism."""
import json

import pytest

from persona.eval import run_oracle
from persona.eval.fixtures import load_fixture, FIX_DIR


def test_run_oracle_shape_and_honest_empty():
    for name in ("litqa2", "bixbench"):
        r = run_oracle(name, seed=0)
        assert {"metric", "score", "n", "per_item"} <= set(r)
        # no data fetched offline in this env → honestly empty, never synthesized
        assert r["n"] == 0 and r["sourcing_status"] == "unfetched"
        assert r["per_item"] == []


def test_run_oracle_is_deterministic():
    for name in ("litqa2", "bixbench"):
        assert run_oracle(name, seed=0) == run_oracle(name, seed=0)


def test_fixture_never_synthesizes_items():
    # the shipped fixtures must be empty (real gold not fetched) — never hand-authored
    for name in ("litqa2", "bixbench"):
        fx = load_fixture(name)
        assert fx["n"] == 0 and fx["verified"] is True


def test_hash_tamper_guard(tmp_path, monkeypatch):
    # write a real item but leave the .sha256 as the empty-file hash → mismatch must raise
    import persona.eval.fixtures as F
    monkeypatch.setattr(F, "FIX_DIR", tmp_path)
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"litqa2": {"sourcing_status": "frozen"}}), encoding="utf-8")
    (tmp_path / "litqa2_subset.jsonl").write_text('{"id": "x"}\n', encoding="utf-8")
    (tmp_path / "litqa2_subset.sha256").write_text(
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  litqa2_subset.jsonl\n", encoding="utf-8")
    with pytest.raises(ValueError):
        F.load_fixture("litqa2")
