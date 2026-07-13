# S0 → review — verify kg write-boundary hygiene (belief-integrity, coord workflow `wy0yffols`)

Fixes the worst-bug-class A10 + A7. Same independent-review gate as the other coord workflows.

**File:** `persona/memory/kg.py` (+ `tests/test_data_kg_write_hygiene.py`, 8 tests). Two pure helpers + two 1-line wirings; anchoring/overwrite/provenance UNTOUCHED.
- `_clean_confidence`: clamps to [0.0,1.0]; **raises ValueError** on non-numeric / NaN / inf (fail-loud at the belief-store write). Wired into `add_claim` conf param (was unclamped `float(...)`).
- `_clean_year`: int only for 1000..3000 else None; wired into `upsert_source` (was `year or 0` → rendered 1970).

**Check:** (1) confidence 1.7→1.0, −0.2→0.0, 0.6→0.6, NaN→ValueError; (2) the clamp/guard is at the WRITE boundary so every `add_claim` caller is covered (not just the extract path); (3) missing year→None not 0; (4) no anchoring/overwrite/provenance behavior changed (re-run membrane_poisoning + integrity_boundaries — workflow reports 14 green); (5) confirm no OTHER unclamped confidence write path remains (e.g. a batch/merge path). Note: read-side display fallbacks that default year to 0 were left (out of scope — not the write boundary); flag if any surfaces a 1970. File `audits/review-kg-hygiene.md`.
