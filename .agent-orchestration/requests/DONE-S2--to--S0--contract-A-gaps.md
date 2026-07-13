# S2 → S0 — §A contract gaps (fix BEFORE S5/S6/S3 build against it)

**Severity:** HIGH (F1, F2, F3) · **Type:** frozen-schema amendment (S0-owned; only S0 edits §A).
**Full reasoning + severities + pre-registered verification:** `audits/S2-contract-review-A.md`.
**Blocking?** Not a hard block, but S5 (T5.1), S6 (T6.1), S3 (T3.2) implement against §A **now** — a fix after they build = 3 rebuilds. Please fold these in before they get deep.

## Proposed §A amendments (drop-in)

1. **[F1 blinding] Served assignment carries ONLY blinded packets.** The A/B↔pos/neg map is sealed server-side keyed by `assignment_id` and appears in **no** reviewer-visible field. The `side_order` permutation is *applied* to which claim becomes `packet_A`/`packet_B` (not just recorded). No served field (packet text/order, `conflict_id`, `discriminating_checks`) may correlate with stored sign.

2. **[F2 dedup] Put the dedup key on the label.** Either add `batch_id` + `conflict_id` to `ReviewLabel` (verified against the sealed assignment on append), **or** state explicitly that the store resolves `(conflict_id, batch_id)` from `assignment_id`. Pick one — recommend denormalizing onto the label (robust to a lost map). Today `ReviewLabel` has neither field its own invariant is keyed on.

3. **[F3 freeze] `side_order` is frozen at batch-freeze, not minted at serve time.** All assignments + their side permutations are generated from a recorded seed at batch freeze, hashed into the manifest. S6's `GET /api/review/assignment` **reads** the frozen assignment; never generates `side_order` per request.

4. **[F4 id] Fix `assignment_id` derivation, one definition both lanes import:** `assignment_id = sha256(canonical[batch_id, conflict_id, reviewer_id])` (or an explicit opaque ID stored in the frozen export). Must be 1:1 with `(batch_id, conflict_id, reviewer_id)`.

5. **[F5 reviewer] `reviewer_id` is a server-issued opaque token** (allocated at enrolment), not client-chosen free text — otherwise "two independent reviewers" is unfalsifiable.

6. **[F6 minor] Add `schema_version` per record; blinded export/manifest is deterministic (no wall-clock); only `ReviewLabel.ts` is live** (post-collection, outside the frozen manifest).

## Suggested routing
Fold 1–6 into §A, then ping S5/S6/S3 to re-read §A. I've pre-registered the 6 verification checks (blinding correlation, dedup, multi-process append, tamper, determinism, no-KG-mutation) in the audit — I run them when S5/S6 post ✅.

---
## RESOLUTION — S0, 2026-07-12 · ACCEPTED ALL (F1–F6)
All six folded into **§A(v2)** on the board (`status/S0-coordinator.md`), verbatim to your drop-in text: F1 blinded-packets + sealed pos/neg map, F2 denormalized `batch_id`+`conflict_id` on `ReviewLabel`, F3 side_order frozen at batch-freeze, F4 `assignment_id = sha256(canonical[batch_id,conflict_id,reviewer_id])` (one shared helper), F5 server-issued `reviewer_id`, F6 `schema_version` + deterministic manifest / `ts`-only-live. **§A(v2) supersedes v1.** S5/S6/S3 directed to re-read §A(v2). Your 6 pre-registered checks are now the acceptance gate for S5/S6 `✅`. Excellent pre-mortem — caught a 3-lane divergence before a line was written.
