# S2 GATE — §A(v2) multi-rater substrate PASSES (RQ-E02 critical-path)

**When:** 2026-07-13. **Verdict: PASS — all 6 pre-registered checks.** This is the acceptance gate I froze when reviewing the §A contract; it is the gate for S5/S6 `✅` and the precondition for RQ-E02.

## What landed
`persona/conflict_reviews.py` §A(v2) multi-rater blinded acquisition layer (inline; no separate `conflict_gold.py`). Faithfully implements my frozen F1–F6:
- **F1 blinding:** `build_assignment` serves only permuted `packet_A/packet_B`; the pos/neg map is sealed in the frozen manifest, never served. `_side_order` applies the permutation.
- **F2 dedup:** `append_review_label` rejects a duplicate `(reviewer_id, conflict_id, batch_id)` under the file lock (atomic check-then-append) → `DuplicateLabelError`.
- **F3 frozen side_order:** `_side_order(seed, assignment_id)` is pure over the FROZEN seed — fixed at batch-freeze, not minted at serve.
- **F4 assignment_id:** `sha256(canonical[batch_id, conflict_id, reviewer_id])`, one shared definition.
- **F5 reviewer_id:** `enrol_reviewer` mints a server-issued opaque `rev_<hex>` token; `_require_enrolled` rejects client free-text.
- **F6 determinism + schema_version:** `_clean_seed` rejects wall-clock/bool/float; `freeze_batch` byte-identical for same pairs+seed; `schema_version` on every record.
- Cross-process OS file lock (`msvcrt` spin-retry / `fcntl` LOCK_EX); triple tamper-check in `load_batch`; "never touches the KG; labels NEVER synthesized."

## S2 INDEPENDENT gate — `tests/test_audit_multirater_gate.py` (7 tests, 232-suite green)
Written independently of S5's `test_data_multirater_t51.py` to adversarially verify, not trust:
1. **Blinding non-correlation** — over **200 reviewers**, `packet_A == positive` rate stayed in 0.30–0.70 (balanced), and the served dict carries NO sign-bearing field (`pos_claim_id`/`neg_claim_id` absent; key-set constrained). ✓
1b. Side-order **stable per (batch,conflict,reviewer)** (frozen, not re-rolled at serve). ✓
2. **Cross-PROCESS concurrent append** — **6 real OS subprocesses × 8 conflicts = 48 labels**; chain verifies ok, exactly 48 records, zero lost/dup → the OS file lock genuinely serializes (not just threads). ✓
3. **Tamper** — one flipped manifest byte → `verify_batch` False + `load_batch` raises. ✓
4. **Dedup** — same reviewer twice → `DuplicateLabelError`; a *different* reviewer on the same conflict is allowed (two independent labels). ✓
5. **Determinism** — same pairs+seed → byte-identical manifest+batch_id; different seed → different batch_id. ✓
6. **No KG writer** — source contains no `memory.kg` import / `.add_claim` / `.commit(` / `membrane`. ✓

Note: the code enforces `rationale >= 20 chars` (good low-effort-label guard) — my first test run correctly surfaced it (my test bug, not the code's); fixed.

## Consequence — RQ-E02 is UNBLOCKED at the substrate level
The blinded acquisition layer is sound: blinded, deduped, cross-process-safe, tamper-proof, deterministic, non-mutating. **Next (per CONTINUATION §11/§12):** freeze a 20-case stratified batch → collect **two independent real human labels** → agreement + adjudicated gold → RQ-E02 (sign-collision vs 1-verifier vs 2-verifier+exact-span at ≥0.85 precision). **If no real reviewers exist, stop at the frozen bundle — NEVER synthesize labels.**

## For S0
- **S5's T5.1 clears the S2 gate.** Committable (lane-scoped): `persona/conflict_reviews.py` + `tests/test_data_multirater_t51.py` + my `tests/test_audit_multirater_gate.py`.
- S5's status file is still dead-stale (23:04) despite this landing — reconcile the writer.
