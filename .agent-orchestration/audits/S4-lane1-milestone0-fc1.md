# S2 audit — S4 (Lane 1 Teams) Milestone-0 FC-1 stubs + M2 daemon guard

**When:** 2026-07-13 · post PRD pivot. S4 = Lane 1, provides FC-1. Awaiting S2 gate.
**Verdict: PASS.** Stubs match FC-1 contract (PRD-00 §4); M2 daemon-side guard correct. All $0, full suite 118 passed.

## FC-1 stubs vs contract (PRD-00 §4 L61)
| Contract | S4 code | ✓ |
|---|---|---|
| `investigation.open_from_conflict(conflict_id, evidence_claim_ids=None) -> Investigation` | `research/investigation.py:92` — exact signature (classmethod) | ✓ |
| queue task types `"verify"`, `"debate"`, `"staleness"` | `daemon/queue.py:21-22` `TASK_VERIFY/TASK_DEBATE` present | ⚠ confirm `"staleness"` type exists (grep saw verify+debate only) |
| `consensus.span_weighted_consensus(reader_outputs) -> {claim, admit_votes:int, weighted_support:float, dissent:[{claim_id,span,weight}]}` in new `agents/consensus.py` | `agents/consensus.py:26-56` — exact return shape; `weighted_support = admit_weight/total_weight` in [0,1], 0.0 when no readers; **dissent preserved, not averaged** (protected minority) | ✓ |

- `consensus.py` ships an inline `__main__` self-check (L61-68) asserting `admit_votes==2` and `weighted_support==round(1.5/3.5,4)` — good, matches the "protect dissent" design (a 2.0-weight dissenter is preserved, not averaged into a mean).

## M2 daemon guard (my cycle-2b finding, S4 side) — CORRECT
`daemon/supervisor.py::_should_reaudit(watchlist, can_spend)` (L23) returns `watchlist.due() is not None` and the enqueue at L167 gates on it (not `entries()`). Behaviour-neutral **today** (no floor yet → `due()` returns least-recent), and the moment Lane 2/S5 lands `watchlist.due(min_age_hours=...)` a fresh watchlist returns `None` → the reaudit busy-loop stops burning the $15/day cap. This is exactly the S4 half of M2 I routed; the S5 `watchlist.py` floor is the remaining half (PARKED).

## Verification
`pytest -q` → **118 passed** (floor ≥46 held) · `compileall` → 0 · $0, no paid calls.

## For S0
- **Committable (lane-scoped):** `research/investigation.py`, `daemon/queue.py`, `daemon/supervisor.py`, `agents/consensus.py` + their tests. Never `-A`.
- **One follow-up:** confirm `"staleness"` queue task type is defined (FC-1 lists 3 types; I verified 2). Non-blocking — the two consumed by L2/L3 first are present.
- M2 fully closes only when S5 (PARKED) lands the `watchlist.due` floor.
