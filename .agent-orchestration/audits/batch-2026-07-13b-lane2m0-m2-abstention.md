# S2 audit batch — Lane-2 M0 + M2 closed + red-test resolved + S3 abstention scoring

**When:** 2026-07-13. **Verdict: all PASS.** Suite 200→**204 green** (red test resolved). $0.

## ✅ Red test RESOLVED — fixed the right way (my c13 finding heeded)
`test_deliv_document_quality.py::test_a2` now asserts `\usepackage[expansion=false]{microtype}` **with a comment** ("expansion=false is load-bearing: bare … breaks all PDF compiles"). `document.py:33` still has `[expansion=false]` — **code NOT reverted**. The trap I flagged was avoided. Suite back to all-green.

## ✅ M2 (reaudit budget-churn) — FULLY CLOSED
Both halves in: `watchlist.due(min_age_hours=12.0)` (memory/watchlist.py:72 — staleness floor, env-overridable, `min_age_hours=0` forces) + `supervisor._should_reaudit` gating on `due()`. A fresh watchlist → `None` → no reaudit burns the daily cap. My cycle-2b finding is closed.

## ✅ Lane-2 (Membrane) M0 — FC-2/3/5 stubs + M2 floor — PASS (deep-checked, belief-store is sensitive)
New: `memory/{kg.py(M),calibrate.py}`, `inbox.py`, `watchlist.py(M)` + `tests/test_data_{fc2_inbox,fc3_kg,fc5_calibrate,m2_watchlist}.py`.
- **Membrane invariants HOLD:** `test_membrane_poisoning.py` + `test_integrity_boundaries.py` + 4 Lane-2 tests → **28 passed**. Poisoning-resistance oracle intact.
- **kg.py change is purely ADDITIVE (+97/-0):** read-only `provenance_breakdown()` audit, FC-3 `add_dependency_edge`/`dependency_edges`/`citation_support_ratio`, and `CONFIRMED_PROVENANCE=("HUMAN_CONFIRMED","TESTED")` correctly encoding the frozen write-policy. **No change to belief-overwrite / anchoring / resist logic.** Dependency edges are a structural projection, not belief admission → membrane not bypassed.
- NOTE: `conflict_reviews.py` UNTOUCHED — the multi-rater §A(v2) substrate (T5.1) is NOT in this M0. My §A(v2) 6-check gate stays pending until it lands.
- **S5's status file is stale** (still "▶ start now") though its code landed — flag to S0: Lane-2 producing but not reporting; confirm the session is live vs the human landed M0.

## ✅ S3 (Lane 4) Iteration-5 — abstention-aware scoring (F4.8/RQ-E15) — PASS
`persona/eval/scoring.py`: frozen sign order **correct > abstain > wrong** ("wrong is the only negative → abstaining always beats guessing wrong"; magnitudes = RQ-E15 knob). `classify()` → correct|wrong|abstain; `score_answers()`. `exp_rq_e15_field_question_gate.py` + `test_eval_scoring.py` (3 passed). **This rewards honest uncertainty** — the "discipline of believing" thesis (§10/§12: abstention visibility). Correct design.

## Scorecard (all PASS, real oracles, $0) — floor 46 → suite 204
S4=7 (…+A9, +M2-closed) · S3=5 (…+iter5 abstention) · Lane-2/S5=1 (M0 FC-2/3/5+floor). No regressions; belief-store invariants intact.

## Standing (not S2's)
- Nothing committed (HEAD `0a6f923`) — H1/M1 security still live-vuln until commit+restart.
- Multi-rater §A(v2) substrate (conflict_reviews) still pending → my 6-check gate not yet triggered.
- S5/S6 status files stale despite Lane-2 code landing — S0 to reconcile.
