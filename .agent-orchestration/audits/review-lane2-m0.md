# S2 REVIEW — Lane-2 M0 (FC-2/3/5 + M2), 2026-07-13

Requested by `S0--to--review--verify-lane2-m0.md` (workflow `wwktpsurb`).

## Verdict: PASS with one LOW-MED finding (self-loop). 27 lane-2/3 tests green + full suite floor holds.

- **M2 (my cycle-2 finding) → FIXED & VERIFIED.** `watchlist.due(min_age_hours=12.0)` now applies a
  staleness floor (returns None if the least-recent `last_audit` is younger than the floor), with
  `PERSONA_REAUDIT_MIN_HOURS` env override and `min_age_hours=0` to force manual/API re-audit. Combined
  with the supervisor gating enqueue on `due() is not None` (verified c-earlier), the paid-reaudit
  busy-loop / daily-cap burn is closed. `test_data_m2_watchlist` passes.
- **Check #3 — `add_dependency_edge` self-loop → FINDING L-DEP-1 (LOW-MED).** No `src==dst` guard
  (`kg.py:333`); a self-loop is creatable and inflates `load_bearing` in-degree. Fix: guard at top. (Full
  detail in `review-lane3-m0.md`; routes to S5 who owns `memory/kg.py`.) It can't corrupt *existing*
  edges — MERGE is keyed on `{rel_type}` so re-add only updates conf/span of the same edge (good).
- **Check #2 — FC-3 read-only where required → PASS (spot).** `provenance_breakdown`,
  `citation_support_ratio`, `dependency_edges` are RETURN-only Cypher (no SET/MERGE). `add_dependency_edge`
  is the only writer and is a deliberate FC-3 mutation, not a read path.

## Deferred checks — now DONE (all PASS)
- **#5 calibrate placeholder honesty → PASS (exemplary).** `calibrate.py:9-12` headers a CALIBRATION STATUS
  block: "all numeric thresholds are PLACEHOLDERS pending RQ-E16 … NOT empirically validated cut-points. Do
  not cite any number here as a calibrated operating point." `_BOUND`, the support ramp, and thresholds all
  carry inline "placeholder / monotone-only / not a calibrated probability" tags. Textbook CONTINUATION §10.
- **#6 inbox malformed-dossier validation → PASS.** `_validate` (inbox.py:31-40) raises on non-string kind,
  non-dict dossier, missing required keys, and out-of-set conflict_type; `file_handoff` calls it first.
- **#7 no epoch/wall-clock in ids → PASS.** `handoff_id = "ho_"+sha256(canonical(kind,dossier))[:16]`
  (content-hash, deterministic, no clock). `filed_at` is a real UTC ISO timestamp in metadata, not 1970.

## Still deferred (need PRD-00 text / live KG)
#1 exact FC-2/3/5 signatures vs PRD-00 §4 (need the PRD open side-by-side) · #4 `citation_support_ratio`
sign grouping on real data (needs a live FalkorDB with +/- claims on one pair).

**Lane-2 M0 verdict: PASS.** Only open item is the LOW-MED `add_dependency_edge` self-loop guard (→ S5).

**Note:** lint is NOT yet wired into the compile path (imp4 follow-up) — a paper can still ship unlinted
until that lands; flagged in paper-quality review.
