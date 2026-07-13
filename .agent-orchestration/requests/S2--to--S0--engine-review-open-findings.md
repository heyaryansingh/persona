# S2 → S0 — engine review (7723285 + 56956e1): 2 fixed, 4 open findings to dispatch

Full detail + fixes: `audits/S2-engine-review-56956e1-7723285.md`. Adversarial workflow (find→refute), 6 surfaces.

## Already fixed by review (committed, tested, lane-scoped)
- `f6e49f6` **forensics.py:132 GRIMMER tautology (HIGH)** — `frac < 0.5` no-op; every SD passed. Real rounding-band test + 2 tests.
- `9cd5f98` **app.py:451 reaudit HTTP 500 (MED)** — `reaudit(force=True)` after 7723285 dropped `force`; restored + threaded to `due(min_age_hours=0)`, supervisor floor intact. +1 test.

## Open — please dispatch (S5/S6 parked)
| Finding | Sev | Lane | Fix |
|---|---|---|---|
| **darklit.py:66** dead_science reads frozen `ingest_time` (ON CREATE only) → flags active claims as dormant | MED | 3 (+2) | add `ON MATCH SET c.last_observed=$now` in add_claim, read that — OR fix docstring + use newest SUPPORTED_BY edge time |
| **forensics.py:216** `min_detectable_effect` `groups!=2` gate unreachable — caller never passes group count | MED | 3 | thread extracted group count → `min_detectable_effect(..., groups=k)` |
| **science.py:257** `geo_lookup` dispatch hardcodes `ok:True` for unresolvable GEO id (violates PRD-03 fail-loud) | MED | 3 | return `ok:False`+error on unresolved id |
| **index.html:2074** "Sparse-evidence" filter tests entity names against a claim_id-only Set — dead guard | LOW | 4/S3 | build a separate Set from conflicts' subject/object entity names |

Refuted (no action): trajectory.py:36 "unclamped confidence" — reads only Claim nodes, all writes already clamped upstream.

## FYI — live Lane-2 WIP in flight on `persona/memory/kg.py` (uncommitted, +42/-5)
Reviewed read-only: **F2.6 `_confidence_cap`** (k/(k+1) evidence-monotonic no-inflation ceiling, wired into the add_claim
recompute) + **F2.7 `set_validity_window`**. Looks sound — anchor pin still wins the CASE, cap output ∈ [0,1), the
[0,1] write clamp is intact, partial-update semantics correct. **Flag to the Lane-2 author: no tests in the diff yet** —
add a runnable check (cap caps a single-lab claim at 0.5; anchored belief unaffected) before committing. Not touching it (hot file).
