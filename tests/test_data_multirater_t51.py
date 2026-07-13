"""T51 · S2 pre-registered checks for the multi-rater blinded acquisition layer.

Six checks, all deterministic, no model / no network:
  (1) blinding      — served packet-order does not correlate with stored pos/neg sign.
  (2) duplicate     — 2nd label for same (reviewer, conflict, batch) is rejected, no append.
  (3) multi-process — >=2 concurrent PROCESSES appending keep the hash chain intact.
  (4) tamper        — flipping a bundle byte OR a ledger line makes verify fail.
  (5) determinism   — same seed => byte-identical batch freeze + side permutation.
  (6) no-KG-mutation— a KG snapshot hash is unchanged across assign -> label -> verify.

Run: python -m pytest -q tests/test_data_multirater_t51.py
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from persona.conflict_reviews import (append_review_label, assignment_id,
                                      build_assignment, enrol_reviewer, freeze_batch,
                                      load_batch, read_review_labels, verify_batch,
                                      verify_review_labels, _side_order)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _pairs(n: int) -> list[dict]:
    return [{"pos_claim_id": f"claim-pos-{i}", "neg_claim_id": f"claim-neg-{i}",
             "pos_packet": f"POSITIVE evidence packet #{i}",
             "neg_packet": f"NEGATIVE evidence packet #{i}"} for i in range(n)]


# (1) Blinding -------------------------------------------------------------------------
def test_blinding_packet_order_does_not_correlate_with_sign():
    with TemporaryDirectory() as td:
        ops = Path(td)
        manifest = freeze_batch(ops, _pairs(20), seed=1234)
        reviewers = [enrol_reviewer(ops) for _ in range(10)]
        pos_by_conflict = {p["conflict_id"]: p["pos_packet"] for p in manifest["pairs"]}

        a_is_pos = 0
        total = 0
        for rev in reviewers:
            for p in manifest["pairs"]:
                served = build_assignment(ops, batch_id=manifest["batch_id"],
                                          conflict_id=p["conflict_id"], reviewer_id=rev)
                # No sign-bearing field may be present in the served object.
                assert set(served) == {"assignment_id", "batch_id", "conflict_id",
                                       "packet_A", "packet_B", "reviewer_id",
                                       "schema_version"}
                assert "pos" not in served and "neg" not in served
                if served["packet_A"] == pos_by_conflict[p["conflict_id"]]:
                    a_is_pos += 1
                total += 1

        frac = a_is_pos / total
        assert total == 200
        # Hash-derived side bit is ~uniform; 200 samples => ~4 SD margin at these bounds.
        assert 0.38 <= frac <= 0.62, f"packet-order correlates with sign: {frac}"


# (2) Duplicate ------------------------------------------------------------------------
def test_duplicate_label_is_rejected_with_no_append():
    from persona.conflict_reviews import DuplicateLabelError

    with TemporaryDirectory() as td:
        ops = Path(td)
        manifest = freeze_batch(ops, _pairs(3), seed=7)
        rev = enrol_reviewer(ops)
        cid = manifest["pairs"][0]["conflict_id"]
        append_review_label(ops, batch_id=manifest["batch_id"], conflict_id=cid,
                            reviewer_id=rev, label="true_refutation",
                            rationale="The matched evidence directly reverses the outcome.")
        before = read_review_labels(ops)
        assert len(before) == 1

        try:
            append_review_label(ops, batch_id=manifest["batch_id"], conflict_id=cid,
                                reviewer_id=rev, label="context_divergence",
                                rationale="A second, different-verdict attempt on same pair.")
            raise AssertionError("duplicate label was accepted")
        except DuplicateLabelError:
            pass
        assert read_review_labels(ops) == before  # no append happened

        # A different reviewer on the same conflict is fine (independent label).
        rev2 = enrol_reviewer(ops)
        append_review_label(ops, batch_id=manifest["batch_id"], conflict_id=cid,
                            reviewer_id=rev2, label="true_refutation",
                            rationale="Independent second rater agrees on the same pair.")
        assert len(read_review_labels(ops)) == 2


# (3) Multi-process concurrent append --------------------------------------------------
_WORKER = """
import sys
sys.path.insert(0, {root!r})
from persona.conflict_reviews import append_review_label
ops, batch, rev = {ops!r}, {batch!r}, sys.argv[1]
conflicts = {conflicts!r}
for cid in conflicts:
    append_review_label(ops, batch_id=batch, conflict_id=cid, reviewer_id=rev,
                        label="insufficient_evidence",
                        rationale="Concurrent worker label; long enough for schema.")
"""


def test_multiprocess_concurrent_append_keeps_chain_intact():
    with TemporaryDirectory() as td:
        ops = Path(td)
        manifest = freeze_batch(ops, _pairs(4), seed=99)
        conflicts = [p["conflict_id"] for p in manifest["pairs"]]
        reviewers = [enrol_reviewer(ops) for _ in range(3)]  # one distinct reviewer per process
        script = _WORKER.format(root=str(REPO_ROOT), ops=str(ops),
                                batch=manifest["batch_id"], conflicts=conflicts)

        procs = [subprocess.Popen([sys.executable, "-c", script, rev]) for rev in reviewers]
        rcs = [p.wait(timeout=120) for p in procs]
        assert rcs == [0, 0, 0], f"a worker crashed: {rcs}"

        audit = verify_review_labels(ops)
        assert audit["ok"], audit["errors"]
        records = audit["records"]
        # Exactly reviewers x conflicts labels, none lost, none duplicated.
        assert len(records) == len(reviewers) * len(conflicts)
        keys = {(r["reviewer_id"], r["conflict_id"], r["batch_id"]) for r in records}
        assert len(keys) == len(records)  # no dup dedup-keys
        assert len({r["record_id"] for r in records}) == len(records)  # no dup hashes
        # Chain is contiguous: each prev_sha256 links to the prior record_id.
        expected_prev = None
        for r in records:
            assert r["prev_sha256"] == expected_prev
            expected_prev = r["record_id"]


# (4) Tamper ---------------------------------------------------------------------------
def test_tamper_on_bundle_or_ledger_fails_verification():
    with TemporaryDirectory() as td:
        ops = Path(td)
        manifest = freeze_batch(ops, _pairs(3), seed=42)
        batch_id = manifest["batch_id"]
        assert verify_batch(ops, batch_id)

        # (a) flip one byte of the frozen bundle -> batch verify fails.
        mpath = ops / f"{batch_id}.manifest.json"
        raw = bytearray(mpath.read_bytes())
        raw[len(raw) // 2] ^= 0x01
        mpath.write_bytes(bytes(raw))
        assert not verify_batch(ops, batch_id)

        # Restore an untampered batch for the ledger tamper case.
        for f in (mpath, ops / f"{batch_id}.manifest.sha256"):
            f.unlink()
        manifest = freeze_batch(ops, _pairs(3), seed=42)
        rev = enrol_reviewer(ops)
        cid = manifest["pairs"][0]["conflict_id"]
        append_review_label(ops, batch_id=manifest["batch_id"], conflict_id=cid,
                            reviewer_id=rev, label="true_refutation",
                            rationale="A valid label whose bytes we will corrupt below.")
        assert verify_review_labels(ops)["ok"]

        # (b) flip one byte of a label ledger line -> ledger verify fails.
        lpath = ops / "multirater_labels.jsonl"
        raw = bytearray(lpath.read_bytes())
        raw[10] ^= 0x01
        lpath.write_bytes(bytes(raw))
        assert not verify_review_labels(ops)["ok"]


# (5) Determinism ----------------------------------------------------------------------
def test_same_seed_reproduces_batch_and_side_permutation_byte_identically():
    pairs = _pairs(20)
    with TemporaryDirectory() as td1, TemporaryDirectory() as td2:
        m1 = freeze_batch(Path(td1), pairs, seed="alpha-seed")
        m2 = freeze_batch(Path(td2), pairs, seed="alpha-seed")
        b1 = (Path(td1) / f"{m1['batch_id']}.manifest.json").read_bytes()
        b2 = (Path(td2) / f"{m2['batch_id']}.manifest.json").read_bytes()
        assert m1["batch_id"] == m2["batch_id"]
        assert b1 == b2  # byte-identical frozen manifest

        # A different seed changes the frozen bundle.
        m3 = freeze_batch(Path(td1), pairs, seed="beta-seed")
        assert m3["batch_id"] != m1["batch_id"]

        # Side permutation is a pure, reproducible function of (seed, assignment).
        for p in m1["pairs"]:
            aid = assignment_id(m1["batch_id"], p["conflict_id"], "rev_fixed")
            assert _side_order("alpha-seed", aid) == _side_order("alpha-seed", aid)


# (6) No KG mutation -------------------------------------------------------------------
def test_no_kg_mutation_across_assign_label_verify():
    with TemporaryDirectory() as td:
        ops = Path(td)
        kg_path = ops / "kg_snapshot.json"
        kg_path.write_text('{"claims": ["pos", "neg"], "edges": []}', encoding="utf-8")
        before = hashlib.sha256(kg_path.read_bytes()).hexdigest()

        manifest = freeze_batch(ops, _pairs(2), seed=5)
        rev = enrol_reviewer(ops)
        cid = manifest["pairs"][0]["conflict_id"]
        build_assignment(ops, batch_id=manifest["batch_id"], conflict_id=cid, reviewer_id=rev)
        append_review_label(ops, batch_id=manifest["batch_id"], conflict_id=cid,
                            reviewer_id=rev, label="true_refutation",
                            rationale="A label that must never write back into the graph.")
        verify_review_labels(ops)

        after = hashlib.sha256(kg_path.read_bytes()).hexdigest()
        assert before == after  # the acquisition layer never touches the KG
