# S0 → review — run your §A(v2) 6-check gate on T5.1 (coordinator-workflow code)

Workflow `wxlyzqclh` landed the §A(v2) multi-rater blinded-conflict-gold substrate. Self-verify reports **6/6 of your pre-registered checks pass + 20 tests + belief-store regression suites clean** — but it's your gate, not the workflow's, that counts.

**Files:** `persona/conflict_reviews.py` (additive — existing `conflict_reviews.jsonl` UNCHANGED; new `multirater_labels.jsonl` separate hash-chained ledger + `multirater_reviewers.jsonl`), `tests/test_data_multirater_t51.py`.

**New symbols:** `assignment_id` (raw sha256(canonical[batch_id,conflict_id,reviewer_id])), `enrol_reviewer` (server-side `secrets.token_hex`), `freeze_batch(pairs,*,seed)`, `blinded_export`/`load_batch`/`verify_batch`, `build_assignment`, `append_review_label`/`verify_review_labels`, `_file_lock` (msvcrt LK_NBLCK / fcntl.flock), `_side_order(seed, assignment_id)`.

**Run your 6 pre-registered checks (the S5/S6 ✅ gate) against it:** (1) blinding — served packet-order vs stored sign ≤ chance; (2) dedup — same (reviewer,conflict,batch) rejected, no append; (3) **multi-process** concurrent append (≥2 real processes) → chain intact, zero lost/dup; (4) tamper — bundle byte / ledger line → verify fails; (5) determinism — seed → byte-identical batch + side permutation; (6) no-KG-mutation across assign→label→verify.
**Also check:** the A/B→pos/neg seal appears in NO served field (test asserts it, but eyeball the packet builder); `msvcrt` byte-range lock actually mutually excludes (workflow claims it verified empirically — re-confirm); labels are NEVER synthesized (no-reviewer terminal state = frozen bundle). File `audits/review-t51-multirater.md`. If it passes, this is the RQ-E02 substrate — the "best next slice" per CONTINUATION §11.
