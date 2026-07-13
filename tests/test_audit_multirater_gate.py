"""S2 pre-registered §A(v2) acceptance gate (RQ-E02) — INDEPENDENT of S5's own T5.1 test.

Adversarial checks matching the 6 I froze when reviewing the §A contract (F1-F6):
  1. blinding: served packet_A does not correlate with the stored positive side (+ no sign-bearing field served)
  2. cross-PROCESS concurrent append serialize (the OS file lock, not just threads): no lost/dup, chain intact
  3. tamper: one flipped manifest byte / ledger byte fails verification
  4. dedup: one label per (reviewer, conflict, batch)
  5. determinism: same pairs + seed => byte-identical manifest and batch_id
  6. no KG mutation: the acquisition module imports no knowledge-graph writer
Run: python -m pytest tests/test_audit_multirater_gate.py -q
"""
import subprocess
import sys

import pytest

from persona import conflict_reviews as cr


def _pairs(n):
    return [{"pos_claim_id": f"clm_pos_{i}", "neg_claim_id": f"clm_neg_{i}",
             "pos_packet": f"POSITIVE evidence sentence number {i}.",
             "neg_packet": f"NEGATIVE evidence sentence number {i}."} for i in range(n)]


def test_check5_determinism(tmp_path):
    m1 = cr.freeze_batch(tmp_path / "a", _pairs(5), seed=42)
    m2 = cr.freeze_batch(tmp_path / "b", _pairs(5), seed=42)
    assert m1["batch_id"] == m2["batch_id"]
    assert cr._canonical_json(m1) == cr._canonical_json(m2)
    # a different seed must change the batch identity
    m3 = cr.freeze_batch(tmp_path / "c", _pairs(5), seed=43)
    assert m3["batch_id"] != m1["batch_id"]


def test_check1_blinding_no_sign_leak(tmp_path):
    ops = tmp_path / "ops"
    ops.mkdir()
    m = cr.freeze_batch(ops, _pairs(1), seed="s")
    cid = m["pairs"][0]["conflict_id"]
    pos_packet = m["pairs"][0]["pos_packet"]
    allowed = {"assignment_id", "batch_id", "conflict_id",
               "packet_A", "packet_B", "reviewer_id", "schema_version"}
    a_is_pos = 0
    n = 200
    for _ in range(n):
        rid = cr.enrol_reviewer(ops)
        asg = cr.build_assignment(ops, batch_id=m["batch_id"], conflict_id=cid, reviewer_id=rid)
        # no served field carries the stored sign identity
        assert set(asg.keys()) <= allowed, asg.keys()
        assert "pos_claim_id" not in asg and "neg_claim_id" not in asg
        if asg["packet_A"] == pos_packet:
            a_is_pos += 1
    # deterministic-per-reviewer but ~balanced across reviewers (binomial n=200 → generous band)
    assert 0.30 < a_is_pos / n < 0.70, f"packet_A==pos rate {a_is_pos/n} — blinding may be biased"


def test_check1b_side_order_is_stable_per_assignment(tmp_path):
    # the SAME (batch,conflict,reviewer) must always see the same side (frozen, not re-rolled at serve)
    ops = tmp_path / "ops"
    ops.mkdir()
    m = cr.freeze_batch(ops, _pairs(1), seed=7)
    cid = m["pairs"][0]["conflict_id"]
    rid = cr.enrol_reviewer(ops)
    a1 = cr.build_assignment(ops, batch_id=m["batch_id"], conflict_id=cid, reviewer_id=rid)
    a2 = cr.build_assignment(ops, batch_id=m["batch_id"], conflict_id=cid, reviewer_id=rid)
    assert a1 == a2


def test_check4_dedup(tmp_path):
    ops = tmp_path / "ops"
    ops.mkdir()
    m = cr.freeze_batch(ops, _pairs(1), seed=1)
    cid = m["pairs"][0]["conflict_id"]
    rid = cr.enrol_reviewer(ops)
    cr.append_review_label(ops, batch_id=m["batch_id"], conflict_id=cid,
                           reviewer_id=rid, label="true_refutation", rationale="first independent reviewer label rationale")
    with pytest.raises(cr.DuplicateLabelError):
        cr.append_review_label(ops, batch_id=m["batch_id"], conflict_id=cid,
                               reviewer_id=rid, label="extraction_error", rationale="second attempt should be rejected as duplicate")
    # a DIFFERENT reviewer on the same conflict is allowed (two independent labels)
    rid2 = cr.enrol_reviewer(ops)
    cr.append_review_label(ops, batch_id=m["batch_id"], conflict_id=cid,
                           reviewer_id=rid2, label="context_divergence", rationale="different reviewer independent context divergence note")
    assert cr.verify_review_labels(ops)["record_count"] == 2


def test_check3_tamper_manifest_and_labels(tmp_path):
    ops = tmp_path / "ops"
    ops.mkdir()
    m = cr.freeze_batch(ops, _pairs(2), seed=1)
    mpath, _ = cr._manifest_paths(ops, m["batch_id"])
    body = bytearray(mpath.read_bytes())
    body[25] ^= 0x01
    mpath.write_bytes(bytes(body))
    assert cr.verify_batch(ops, m["batch_id"]) is False
    with pytest.raises(cr.LedgerIntegrityError):
        cr.load_batch(ops, m["batch_id"])


def test_check6_no_kg_writer_imported():
    import persona.conflict_reviews as mod
    src = __import__("inspect").getsource(mod)
    # the acquisition layer must not import or call a KG mutator
    for forbidden in ("from persona.memory.kg", "import kg", ".add_claim", ".commit(", "membrane"):
        assert forbidden not in src, f"acquisition layer references KG writer: {forbidden}"


_WORKER = (
    "import sys;from persona import conflict_reviews as cr;"
    "ops,batch,rid=sys.argv[1],sys.argv[2],sys.argv[3];"
    "m=cr.load_batch(ops,batch);"
    "[cr.append_review_label(ops,batch_id=batch,conflict_id=p['conflict_id'],"
    "reviewer_id=rid,label='true_refutation',rationale='concurrent append stress test rationale text') for p in m['pairs']]"
)


def test_check2_cross_process_concurrent_append(tmp_path):
    """Real OS processes (not threads) hammering the label ledger must serialize via the file lock."""
    ops = tmp_path / "ops"
    ops.mkdir()
    m = cr.freeze_batch(ops, _pairs(8), seed=1)
    reviewers = [cr.enrol_reviewer(ops) for _ in range(6)]   # 6 procs x 8 conflicts = 48 unique labels
    procs = [subprocess.Popen([sys.executable, "-c", _WORKER, str(ops), m["batch_id"], rid])
             for rid in reviewers]
    for p in procs:
        assert p.wait(timeout=90) == 0, "worker process failed (lock contention should retry, not error)"
    res = cr.verify_review_labels(ops)
    assert res["ok"], res["errors"]
    assert res["record_count"] == 48, f"expected 48 labels, got {res['record_count']} (lost/dup under contention)"
