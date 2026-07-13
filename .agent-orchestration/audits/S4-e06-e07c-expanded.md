# S2 audit — S4 expanded `✅` (RQ-E06 a+b · I1.2/E07c team-physics · M2 response)

**When:** 2026-07-12 · S4 status grew past the T4.1/T4.2 audit with new on-deck work in the tree (uncommitted).
**Verdict: PASS.** No blocking findings. All `$0`, paid stages hard-gated, §10-clean.

## Standing suite (S2 re-ran — not self-report)
| Check | Result |
|---|---|
| `python -m pytest -q` (FULL) | **77 passed** / 26.5s — floor ≥46 held (+31 over baseline; matches S4's claim) |
| `compileall persona experiments` | exit 0 |
| paid-gating present on all 3 experiments | e05/e06/e07c all carry `PERSONA_E0x_LIVE` + `PaidStageGated`/`NotImplementedError`/`gated` — no live run can leak |

## RQ-E06 (a) qualifier extraction — adversarially verified ADDITIVE + exact-span
`persona/reading/extract.py::validate_claims` (L115–148): the **core gate runs first** (subject/relation/object/quote non-empty, `effect_sign ∈ {+,-,0,na}`, finite 0–1 confidence, **quote verbatim in normalized source**). Only a claim that already passed enters the qualifier block (L138–147): `_clean_qualifiers(q, haystack)` requires `qual_source` verbatim in source (RQ-E01a); if it returns `None` → `claim.pop("qualifiers")` and **the claim is still appended**. 
- **Additive proven at the seam:** a bad/ungrounded qualifier can never reject a claim that passed the core gate.
- **Identity immutable:** `subject|object|effect_sign` is validated, never rewritten by qualifier logic.
- Test `test_engine_qualifiers.py` (6 cases): grounded kept · ungrounded stripped + claim survives · bad enum/bool/float dropped · core-invalid claim never rescued. `test_integrity_boundaries.py` (S5) still green → no regression to the belief-feeding path.

## RQ-E06 (b) evidence-tree scaffold — $0, anti-gaming guard present
`exp_rq_e06_evidence_tree.py`: H1 (derivation gate → ≥50% fewer unsupported synthesis) measured structurally offline over a labeled fixture; H2 + real LLM synthesis PAID/GATED. Bootstrap ≥20 seeds; go/no-go `H1_gate=0.50`; **anti-gaming guard `false_drops must stay 0`** (gate may never drop a supported statement). Dry-run: unsupported 0.667→0.000, false_drops 0, H2 `gated`, $0. "fixture ≠ gold" stated → no deployment claim.

## I1.2 / RQ-E07c team-physics — FROZEN harness + prereg, $0, §10-honest
`exp_rq_e07c_team_physics_live.py`: 6 equal-token topology arms; **validated novelty counted only AFTER a membrane stand-in** (never raw agent output; false_admitted stays 0); correlated-error rate a first-class DV; effective-team-size = novelty/token knee. Live reads HARD-gated. **Honest dry-run:** no topology clears sequential by the margin → "sequential + N=3 partition stands" (reproduces E07a). 
- **§10 cross-check:** does not celebrate agent count; effective team size + validated novelty are the metrics; no live claim. ✓ Correct naming (e07c vs existing e07a/e07b replay scripts — no collision).

## M2 (my cycle-2b finding) — S4 side handled correctly
S4 correctly did **not** change `audit.py` logic: `reaudit()` already no-ops when `due()` is `None` and must stay forceable for manual/API re-audit. Root fix stays **S5** (`watchlist.due(min_age_hours=...)`) + **S6** (supervisor guard on `due()` not `entries()`) — as I routed. S4 added `$0` contract test `test_engine_reaudit_staleness.py` + filed `requests/S4--to--S5--reaudit-staleness-consumer-contract.md`. Clean division; M2 remains open on the S5/S6 side.

## For S0
- Committable (lane-scoped, all $0): `persona/agents/analyst.py`, `persona/reading/extract.py`, + the new `experiments/exp_rq_e0{5,6,7c}*.py` and `tests/test_engine_*` files.
- Live execution of E05/E06/E07c remains correctly gated on human budget + live model probe — do not greenlight from motion.
- **M2 still OPEN on S5 (`watchlist.due` staleness floor) + S6 (supervisor guard).** H1 + M1 (cycle-1) also STILL OPEN — S6 has not landed P0.1 or the run_shell jail.
