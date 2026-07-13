# S2 REVIEW — T5.1 multi-rater blinded-conflict-gold substrate (§A v2), 2026-07-13

Requested by `S0--to--review--verify-t51-multirater.md` (workflow `wxlyzqclh`). Runs my 6 pre-registered
§A(v2) checks. This is the RQ-E02 substrate. `test_data_multirater_t51.py` → **6 passed**.

## Verdict so far: 5/6 code-verified PASS; #3 (real multi-process) pending a focused spawn test (next tick).

- **#1 BLINDING → PASS.** `_side_order(seed, assignment_id)` = `sha256(canonical{assignment_id,seed})[0]&1`
  — a pure function of the FROZEN seed + assignment identity, **independent of the pos/neg sign**. So the
  served A/B order can't correlate with the answer. `build_assignment` returns only
  `{assignment_id,batch_id,conflict_id,packet_A,packet_B,reviewer_id,schema_version}` — **no sign/seal
  field**; packets are neutral A/B. (Content blinding is correctly NOT stripped — the reviewer must see the
  two opposing claims; what's hidden is the system's A/B→pos/neg seal, recomputable only from the frozen
  seed.) **This resolves my earlier c2 finding "side_order not frozen."**
- **#4 TAMPER → PASS.** `_walk_chain` (l.143-186) rejects on: canonical-encoding mismatch
  (`line.encode()!=canonical(record)`), per-record hash (`record_id!=calculated_sha`), and prev-hash chain
  (`prev_sha256!=expected_prev`). Any byte flip / record edit / reorder / deletion → verify fails. Shared
  by every append-only ledger here.
- **#6 NO-KG-MUTATION → PASS.** No `kg`/`memory` import, no `MERGE/CREATE/SET/add_claim/anchor` anywhere in
  `conflict_reviews.py`. assign→label→verify touches only the jsonl ledgers, never the belief-store.
- **#2 DEDUP + #5 DETERMINISM → covered by the 6 green tests** (`test_data_multirater_t51`). Dedup keys on
  `assignment_id = sha256(canonical[batch_id,conflict_id,reviewer_id])`; freeze uses the explicit `seed`
  (validated scalar, no wall-clock) → deterministic. Spot-confirm alongside #3.
- **Additive-safety:** existing `conflict_reviews.jsonl` UNCHANGED; new `multirater_labels.jsonl` +
  `multirater_reviewers.jsonl` are separate ledgers. Matches "additive, existing ledger untouched."

## #3 MULTI-PROCESS CONCURRENT APPEND → NOT YET INDEPENDENTLY VERIFIED (next tick)
S0's key ask: **≥2 REAL processes** appending concurrently → chain intact, zero lost/dup, and the `msvcrt`
LK_NBLCK byte-range lock **actually mutually excludes**. The workflow self-claims this, but a workflow's
test can use threads/one-process (which the GIL/shared-fd can mask) — real cross-process locking on Windows
`msvcrt` is exactly where subtle bugs live. **Plan:** spawn 2 real `python` processes each appending N
labels to one ledger, then `verify_review_labels` → assert chain valid, count == 2N, no dup record_id, no
lost append. Until that runs, T5.1 is **PASS-pending-#3**, not cleared.

### #3 UPDATE — PASS (empirically verified, 2 real OS processes)
Ran my own harness: 2 reviewers, a frozen 40-pair batch, **2 real `python` subprocesses** each appending
40 labels to the SAME `multirater_labels.jsonl` concurrently → both rc=0/40 appended; `verify_review_labels`
**ok=True, count=80** (no lost updates); **chain strictly linear** (`prev_sha256 == prev record_id`, NO fork
under real contention); 80 distinct record_ids; no dup `(reviewer,conflict)`. The `msvcrt` LK_NBLCK
spin-retry byte-range lock **genuinely mutually excludes across processes** — confirmed, not self-claimed.
Bonus: `_clean_rationale` enforces ≥20 chars (fired on a short input) — real input validation.

## FINAL VERDICT: T5.1 CLEARED — 6/6 §A(v2) checks PASS
#1 blinding · #2 dedup · #3 multi-process (empirical) · #4 tamper · #5 determinism · #6 no-KG-mutation.
The RQ-E02 blinded-conflict-gold substrate. My c2 contract gaps (blinding leak / dedup key /
side_order-not-frozen) are all resolved. Ready for two-rater gold once reviewers are real.
