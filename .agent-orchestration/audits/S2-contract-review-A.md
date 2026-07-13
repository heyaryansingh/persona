# S2 audit — adversarial review of §A (multi-rater conflict-review contract) + `ideas/001`

**When:** 2026-07-12, pre-implementation (S5/S6/S3 not yet coding against §A).
**Why now:** §A is the shared schema for **three lanes at once** (S5 store, S6 API, S3 UI). A gap here forks into three divergent implementations. Catching it at the contract is the whole point of a review lane.
**Grounding:** read `.agent-orchestration/ideas/001-multirater-conflict-substrate.md`, S0 §A, and current `persona/conflict_reviews.py` (228 L: append-only, hash-chained, canonical-JSON, `conflict_id = sha256(sorted[pos,neg])` L53-56, process-local `threading.Lock()` L20).
**Routing:** §A is S0-owned; concrete amendment proposals in `requests/S2--to--S0--contract-A-gaps.md`. This file is the reasoning + severity.

`ideas/001` explicitly assigns S2: *"adversarial review of blinding correctness (can a reviewer infer the expected side?) + concurrent-append/tamper verification."* This is that review.

---

## Findings (severity-tagged)

### F1 — HIGH — blinding can leak through packet↔side coupling (the core risk)
§A lists `side_order: "AB"|"BA"` **and** `packet_A, packet_B` on the *same* `ReviewAssignment` object. If `packet_A` is always the stored-**positive** claim and `packet_B` always the stored-**negative** (i.e. side_order is metadata but packets aren't actually permuted), blinding is cosmetic — the reviewer always sees pos as A. **The permutation must be applied to which claim becomes A vs B**, and the A/B→pos/neg map must live **server-side only**, keyed by `assignment_id`.
- **Failure scenario:** reviewer notices packet_A is always the "raises" claim across the batch → infers expected answer → labels are no longer blind → the whole ≥0.85-precision measurement (RQ-E02) is invalid.
- **Fix:** §A must state the *served* assignment contains **only** blinded A/B packets with pos/neg identity stripped; the A/B↔pos/neg mapping is sealed server-side and never in any reviewer-visible field (packet text, ordering, `conflict_id`, or `discriminating_checks` wording).

### F2 — HIGH — `ReviewLabel` lacks the fields its own duplicate-invariant is keyed on
Invariant: *one label per `(reviewer_id, conflict_id, batch_id)`*. But `ReviewLabel = {assignment_id, reviewer_id, label, rationale, ts}` — it carries **neither `conflict_id` nor `batch_id`**. S5 cannot enforce the invariant from the label alone without a lookup, and S6 may not send enough to enforce it.
- **Failure scenario:** S6 posts a label with only `assignment_id`; S5's dedup check needs `(reviewer_id, conflict_id, batch_id)` → the two lanes disagree on how to resolve it → duplicate labels slip in → fake independence.
- **Fix:** pick one and put it in §A: **(a)** denormalize `batch_id`+`conflict_id` onto `ReviewLabel` (verified against the sealed assignment on append), or **(b)** state explicitly that the store resolves `(conflict_id, batch_id)` from `assignment_id` via the sealed map. (a) is more robust to a lost sealed map.

### F3 — HIGH — `side_order` must be frozen in the export, not generated at serve time
Invariant says *"blinded export hashes frozen BEFORE collection."* `side_order` is random per assignment. If S6 generates it lazily at `GET /api/review/assignment` time, it is (a) **not** covered by the frozen hash and (b) non-reproducible → the determinism test in `ideas/001` ("fixed seed → byte-identical batch freeze + side permutation") cannot hold.
- **Fix:** §A must state all assignments — including each `side_order` permutation — are generated and **frozen at batch-freeze time** from a recorded seed, hashed into the manifest. S6's serve endpoint **reads** the frozen assignment; it never mints `side_order` at request time.

### F4 — MED — `assignment_id` derivation unspecified → S5/S6 may compute it differently
For F2's dedup and the sealed A/B map to work, `assignment_id` must be **1:1 with `(batch_id, conflict_id, reviewer_id)`**. If S5 hashes it one way and S6 another, `ReviewLabel.assignment_id` won't match the stored assignment.
- **Fix:** §A fixes it: `assignment_id = sha256(canonical[batch_id, conflict_id, reviewer_id])` (or an explicit opaque ID stored in the frozen export). Deterministic, single definition, both lanes import it.

### F5 — MED — `reviewer_id` provenance unspecified → independence claim is unfalsifiable
"Pseudonymous" but who mints it? If reviewers self-assert free-text `reviewer_id` via the API, one person can split labels across IDs and fake two "independent" reviewers, or collide with another's ID.
- **Fix:** §A: `reviewer_id` is an **allocated opaque token** (server-issued per reviewer at batch enrolment), not client-chosen free text. Low risk for a 2-person pilot but it's what makes "two independent labels" mean anything.

### F6 — LOW — no `schema_version`; export determinism vs live `ts`
- Add `schema_version` to each record so the hash chain survives a future §A revision (RQ-E02 will add fields).
- Clarify: the **blinded export/manifest is timestamp-free / deterministic** (no wall-clock); only `ReviewLabel.ts` is live (collected later, outside the frozen manifest). Otherwise the determinism assert fails on a clock value.

---

## What is already right (keep, do not re-litigate)
- Append-only + hash chain + canonical-JSON + fsync in current `conflict_reviews.py` — `ideas/001` correctly says keep all of it.
- `conflict_id = sha256(sorted[pos,neg])` is order-independent → the conflict_id itself does **not** leak pos/neg. Good; F1 is about packets, not the id.
- Cross-process OS lock (F-lock) replacing `threading.Lock()` is correctly identified; the **multi-process** (not just multi-thread) concurrent-append test is the right arbiter.
- "No reviewers → stop at blinded bundle + UI, never synthesize labels" is correctly preserved from CONTINUATION §11.

## S2 verification I will run when S5/S6 post ✅ (pre-registered so it's not gameable)
1. **Blinding adversarial check (F1):** fetch a batch of served assignments; assert no reviewer-visible field correlates with stored pos/neg above chance (test the packet-order ↔ sign correlation across the batch).
2. **Duplicate rejection (F2/F4):** same `reviewer_id` re-labels same `(conflict_id, batch_id)` → API 4xx + no ledger append.
3. **Multi-process concurrent append (F3):** ≥2 OS processes hammer the ledger → `verify_conflict_reviews` ok, zero lost/dup records, chain intact.
4. **Tamper refusal:** flip one blinded-bundle byte → manifest check fails; flip one ledger line → replay fails.
5. **Determinism (F3/F6):** fixed seed → batch freeze + side permutation byte-identical on rerun.
6. **No KG mutation:** assert the KG snapshot hash is unchanged across a full assign→label→verify cycle.
