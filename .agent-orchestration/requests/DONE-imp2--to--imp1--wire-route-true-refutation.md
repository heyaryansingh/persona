# imp2 → imp1 — wire `route_true_refutation` into the review API route (F2.12 consumption)

**F2.12 seam is provided + tested (imp2):** `persona/conflict_reviews.py::route_true_refutation(record) -> slug|None`.
When a review record's `verdict == "true_refutation"`, it re-opens the question as a fresh investigation
via the FC-1 seam `Investigation.open_from_conflict(conflict_id, evidence_claim_ids=claim_ids)` (dedups,
auto-launches, opens WORK not a belief). Best-effort + import-guarded; returns the new investigation slug.

**Your one line (in `app.py`'s review-verdict route, Lane 4):** after you call
`conflict_reviews.append_conflict_review(...)` and get the `record`, call
`conflict_reviews.route_true_refutation(record)` and surface the returned slug (e.g. "→ opened
investigation X") in the response / action feed. That closes the contradiction→investigation loop from
the Review tab (your C1 buttons).

No belief is anchored — the human verdict already judged it; this only launches the follow-up. If you'd
rather it also file an inbox handoff on refutation, say so and I'll add that to the seam.
