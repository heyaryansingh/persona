# idea 001 — Multi-rater conflict-gold acquisition substrate

**Author:** S1 · **For:** S0 to slice into implementer dispatches · **Status:** proposal
**Source of truth:** `docs/CONTINUATION_HANDOFF.md` §7.1 + §11 (named "best next bounded implementation slice"). Frozen rules in `HANDOFF.md` still bind.

## Why this, why now

§11 is unambiguous: the next real deliverable is **a measured answer to "can Persona escalate candidate conflicts at ≥0.85 precision?"** — which requires a real blinded human gold set. The existing ledger (`persona/conflict_reviews.py`) is a **single-process pilot** and cannot safely collect that gold. This slice is the gate to RQ-E02, which gates contradiction typing (§7.2). Nothing else on the priority list unblocks without it.

**Not the deliverable:** a nicer contradiction badge. **The deliverable:** a blinded acquisition bundle + two independent human labels + measured agreement + adjudicated gold, or — if no real reviewers — the blinded bundle and UI workflow only. **Never synthesize labels** (§11, §HANDOFF).

## Gap analysis (grounded in current `conflict_reviews.py`)

Current ledger is append-only, hash-chained, canonical-JSON, fsync'd — keep all of it. Missing for gold collection:

| Gap | Current state | Needed |
|---|---|---|
| Reviewer identity | absent | pseudonymous `reviewer_id` on every record |
| Assignment / batch | absent | `batch_id`, `assignment_id`; frozen stratified set |
| Blinding | pos/neg order is semantic + fixed | randomized, per-assignment fixed **side order**; verdict recorded against blinded slots not pos/neg |
| Duplicate prevention | none | reject 2nd label by same `reviewer_id` on same `conflict_id` within a `batch_id` |
| Concurrency | `threading.Lock()` (process-local) | OS-level file lock (`msvcrt.locking` on Win / `fcntl.flock` on POSIX) **or** single-writer service |
| Frozen export | none | blinded bundle whose content hashes are frozen **before** collection |
| Tamper tests | single-process only | concurrent multi-process append test + tamper-refusal test |

## Architecture (minimal, extends — does not fork — the ledger)

1. **Blinded assignment layer** (new, e.g. `persona/conflict_gold.py`): freeze N stratified pairs → `batch_id` + per-`(reviewer_id, conflict_id)` `assignment_id` carrying a fixed random side-permutation. Export a **blinded bundle** (claim text with sides relabeled A/B, evidence packets, PICO/context gaps, discriminating checks) + a `.sha256` frozen manifest. No claim IDs leak the "expected" answer.
2. **Ledger extension** (edit `conflict_reviews.py`): add validated `reviewer_id`, `batch_id`, `assignment_id`, `blinded_side_order` to the record schema + hash chain; verdict maps blinded slot → claim id via the sealed assignment, not reviewer-visible order. Duplicate `(reviewer_id, conflict_id, batch_id)` append → reject. **Preserve every existing invariant and test.**
3. **Cross-process lock:** replace `threading.Lock()` at the append/verify seam with an OS advisory file lock so two reviewer processes / API workers serialize. Single-writer service is the fallback if a lock proves flaky under test.
4. **Adjudication + metrics** (new): after ≥2 independent labels per pair, compute agreement (Cohen's κ / raw), emit adjudicated gold file, feed RQ-E02 (sign-collision vs 1-verifier vs 2-verifier+exact-span at the ≥0.85 precision gate).
5. **UI/API surface:** review workflow shows blinded A/B, both exact evidence packets, missing context fields, discriminating checks, four non-mutating labels. **Never anchors the KG.**

## Provisional lane decomposition (S0 confirm against LANES.md)

- **S5 (belief/data):** `conflict_reviews.py` schema extension + OS file lock + new `conflict_gold.py` (blinding, batch freeze, adjudication/metrics). Owns `tests/test_data_conflict_gold.py`.
- **S6 (API):** endpoints to serve blinded bundle + accept a review + expose ledger verify status. Owns `tests/test_api_*`.
- **S3 (frontend):** blinded review UI slice; browser-verified; no invented activity.
- **S2 (audit):** adversarial review of blinding correctness (can a reviewer infer the expected side?) + concurrent-append/tamper verification.

## Test gates (real, per HANDOFF validation rule)

- Multi-**process** concurrent append (not just threads) preserves hash chain — spawn ≥2 processes hammering the ledger, assert `verify_conflict_reviews` ok and no lost/duplicated records.
- Tamper: edit one blinded-bundle byte → frozen-manifest check fails; edit one ledger line → replay fails.
- Duplicate: same reviewer re-labels same conflict in a batch → rejected.
- Blinding: assignment export contains no field from which the "raises/lowers" expected answer is recoverable (adversarial check by S2).
- Determinism: given a fixed seed, batch freeze + side permutation reproduce byte-identically; assert.

## Open risks / unknowns to flag

- **No reviewers may exist.** Then the correct terminal state is the blinded bundle + UI workflow, and we STOP — do not synthesize (§11). S0 should confirm reviewer availability before S5 builds adjudication.
- Cross-process file locks are OS-specific and historically flaky on Windows network paths; the workspace is local NTFS, but the concurrent-append test is the real arbiter — if `msvcrt.locking` misbehaves, fall back to single-writer service.
- Stratification strata for the 20-case freeze aren't defined yet — needs the current 63 sign-collision candidates profiled first (cheap S-scout task).
