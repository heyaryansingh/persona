# S0 → review — independently verify Lane-2 Milestone-0 (coordinator-workflow code)

**Why:** Lane-2 M0 (FC-2/3/5 + M2) was implemented by a coordinator workflow (`wwktpsurb`), not a terminal — it must clear the SAME review gate as terminal work before it counts as commit-ready or anything builds on it.

**Files to review (all $0, deterministic, no paid calls):**
- `persona/memory/kg.py` — FC-3: `provenance_breakdown`, `add_dependency_edge` (rel_type validated), `dependency_edges`, `citation_support_ratio` (uses `pair_key` grouping for +/- support/contrast).
- `persona/memory/calibrate.py` — FC-5 `admit_decision`; routing precedence anchor/high-stakes→human, strong-indep→commit, weak→reject; thresholds explicitly PLACEHOLDER pending RQ-E16.
- `persona/inbox.py` — FC-2 `file_handoff`; append-only jsonl mirroring `conflict_reviews.py`; content-hash id (no wall-clock in id).
- `persona/memory/watchlist.py` — M2 `due(min_age_hours=12)` floor + `PERSONA_REAUDIT_MIN_HOURS`.
- Tests: `tests/test_data_{fc3_kg,fc5_calibrate,fc2_inbox,m2_watchlist}.py` (14 pass self-reported).

**Check specifically:** (1) exact FC signatures vs PRD-00 §4; (2) FC-3 Cypher doesn't mutate/anchor anything (read-only where it must be); (3) `add_dependency_edge` can't create a self-loop or corrupt existing edges; (4) `citation_support_ratio` sign grouping is correct on real data; (5) calibrate never presents a placeholder number as validated (CONTINUATION §10); (6) inbox validation rejects malformed dossiers; (7) no `1970`/epoch leak (ties to punch-list A7). Re-run the 4 tests + confirm full suite floor holds. File `audits/review-lane2-m0.md`.
