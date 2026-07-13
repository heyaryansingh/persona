# status/imp2 — LANE 1 · HETEROGENEOUS AGENT TEAMS  (canonical label: imp2; "S4" retired)

## 🔧 2026-07-13 latest (imp2) — A9 + Lane-2 redistribution acknowledged
- **A9 (worst-bug class) ✅ $0:** `analyst.py` now compile-validates generated code BEFORE the sandbox run (`_code_syntax_error` helper) — syntactically-broken analysis scripts are rejected loud (model gets the error to fix), never run, and don't count as `ran_code`. Catches the exact reviewer-found bugs (positional-after-keyword, stray tokens, malformed imports). Test `tests/test_engine_a9_compile_guard.py` (5, real bug shapes).
- **M2 FULLY CLOSED:** Lane-2 M0 landed `watchlist.due(min_age_hours=12)`; my `supervisor._should_reaudit` guard already gates on it. Both halves in. Done.
- **New ownership (Lane-2 redistribution):** I now own `persona/conflict_reviews.py` + `persona/inbox.py` (FC-2). FC-2 `inbox.file_handoff` + FC-5 `calibrate.admit_decision` are **LANDED**.
- **F1.2 verifier — applicability gate fill ✅ $0:** `agents/verifier.py` now implements `is_verifiable(claim)` — the correctness boundary: a claim is verifiable-by-this-agent only with an exact source span AND either directional-empirical (→ analyst reproduction) or math (→ reason.prove); else `not_applicable` (explicit skip, **not** a pass), the guard against out-of-domain false positives. `verify()` applies the gate first (not_applicable / claim-not-found short-circuit with **zero paid calls**), then routes verifiable claims to the existing paid execution (self-gating on budget → degrades to `inconclusive` at $0), maps the verdict from the session's conclusions, records a reproduced computational result as TESTED-provisional (`source="verify"`). Paid routing runs only with budget. Test `tests/test_engine_verifier_gate.py` (7): gate correctness, not_applicable makes no paid call, verifiable degrades to inconclusive without budget.
- **F1.10 `open_from_conflict` full ✅ $0:** the loop-closing seam now resolves a conflict → directional question + two opposing stances via the belief graph (`kg.provenance`, import-guarded), fans them into a **branch plan** (F1.1), **pins the exact colliding claim IDs** into the launched analyze tasks (`evidence_claim_ids` in params), **dedups** against a live investigation (idempotent), and auto-launches (guarded; steps budget-gated at execution). No-KG → linear fallback. Opens WORK, never a belief. Test `tests/test_open_from_conflict.py` (3, real queue): branch+evidence-pin, dedup, linear fallback. M0 seam test still green.
- **F1.4 debate full ✅ $0:** `agents/debate.py` — de-identifies positions (no author reaches the debater; anti-sycophancy), tallies `agreement` and ALWAYS surfaces it, resolves only at `agreement ≥ TAU`, and on low agreement **escalates via FC-2 `inbox.file_handoff`** (valid dossier, `conflict_type=insufficient`) rather than outvoting the grounded minority. Paid debate rounds gated (return [] at $0 → unresolved, no spend). Frozen 7-key shape preserved (dropped an errant `note` key). Test `tests/test_debate.py` (5): de-id strips author, tally, agreement-always-present, **low-agreement escalates + handoff filed**, high-agreement resolves without escalating.
- **F1.9 revisit→re-investigation ✅ $0:** `agents/revisit.py` — a re-test that FLIPS a past result to `refuted` now re-opens the question as fresh grounded work via the FC-1 seam (`open_from_conflict`, dedup+auto-launch there); a HELD result opens nothing; evidence `None` → re-gathers (never fabricated); human still anchors any reversal downstream. Test `tests/test_revisit_reinvestigate.py` (2): refute→one investigation via `revisit:` seam, hold→none.
- **F1.7 director-value prioritization ✅ $0:** `agents/discover.py` — `_value_priority(value)` maps a lead's already-elicited `value` (0-10) to a queue priority (higher value → lower number → leased sooner; missing → base 4, unchanged); threaded into the investigate enqueue. Test `tests/test_director_value.py` (3): high>low sooner, missing→base, monotonic-in-band.
- **A10 (confidence>1 in KG) — imp2 boundary already holds:** both `reader.py` and `batch.py` route claims through `extract.validate_claims`, which **rejects `confidence>1`** (extract.py:130-133) and defaults missing→0.6, so no `confidence>1` leaves my reader path. **The writer emitting `>1` is imp4's membrane/kg, not the reader** — flagging to imp4 (their lane); no imp2 change needed.
- **F1.3 two-reader cross-check (core) ✅ $0:** `reading/extract.py::cross_check_claims` — runs extraction twice, span-validates EACH pass, matches on the frozen claim identity; only claims present in BOTH passes are `agreed` (harvestable), a claim in one pass is a preserved+flagged `disagreement` (never silently admitted) — a stricter membrane. Test `tests/test_cross_check.py` (2): only-agreeing admitted, ungrounded dropped by the span gate. Reader-path wiring (invoke on high-value papers, write `claims_disputed.jsonl`, emit disagreement event) is the paid integration — next.
- **F1.6 surprise-rank (core) ✅ $0:** `reading/reader.py::contradiction_surprise(claim, beliefs)` — a claim OPPOSING a high-confidence belief on the same subject→object is belief-overturning; surprise = that belief's confidence (scales with it); a restatement = 0.0. `surprise_priority(s)` maps it to a sooner queue priority (reuses the existing priority int; no lease-SQL change). Pure/local — no encoder, no API logprobs (Messages API exposes none). Test `tests/test_surprise.py` (4). Embedding-novelty signal + reader wiring + RQ-HT06 full loop = the remaining fill (needs the local encoder + the experiment).
- **Full suite: 236 passed, 0 failed.**

## Lane-1 $0 CORES COMPLETE — session summary (imp2)
FC-1 M0 (consensus/verifier/debate/open_from_conflict/queue-types/worker-handlers) · F1.1 branch/DAG · F1.2 verifier applicability gate · F1.3 two-reader `cross_check_claims` · F1.4 gated debate · F1.6 contradiction-surprise · F1.7 director-value priority · F1.9 revisit→re-investigation · F1.10 conflict→investigation seam · A9 compile-guard · M2 daemon guard. **All $0, all green (236 suite), most S2-verified PASS.**

**Remaining Lane-1 work needs a gate I don't have yet — NOT started to avoid unvalidated/unauthorized work:**
- **Paid integrations** (need budget greenlight to validate): F1.2 verifier live routing, F1.4 live debate rounds, F1.3/F1.6 **reader-path wiring** (invoke cross-check + surprise on high-value papers; paid reads), F1.8 gather-critique (a paid Haiku step).
- **Plan-mutating / cost decision (needs S0 nod):** F1.8 inserts a `critique_gather` step into `DEFAULT_PLAN` — adds a paid step to every investigation. That's an autonomy/cost call I won't make unilaterally; flag for S0.
- **Needs infra/experiment:** F1.6 embedding-novelty (local encoder = imp4's `memory/embed`), RQ-HT01/HT06 live arms (budget).
- **Next when unblocked:** budget greenlight → wire the paid parts + run the RQ live arms; or a new S0 directive.

## 🆕 New imp2 directives (board L49)
1. **F2.5 `memory/conflicts.py::type_conflict()` ✅ $0** (new file, mine per Lane-2 redistribution): classifies a sign-collision into the frozen FC-2 enum {temporal|semantic|misinformation|insufficient} from §B qualifiers (retraction→misinformation [precedence], differing timepoint→temporal, differing population/model_system→semantic, else→insufficient). Types a CANDIDATE only — never anchors, `candidate_conflict≠verified` until RQ-E02. **F2.13 `retraction_scan` ✅ $0** — flags claims resting on a RETRACTED source via the FC-6 oracle (`ingest.retraction.is_retracted`, import-guarded/injectable; imp4's — degrades to flag-nothing if absent); read-only, ties to type_conflict's 'misinformation'. `conflicts.py` COMPLETE. Test `tests/test_data_conflict_typing.py` (9).
2. **F2.12 `conflict_reviews.py::route_true_refutation(record)` ✅ $0** — a `true_refutation` review re-opens the question via `open_from_conflict` (pinned claims, dedups, opens WORK not a belief; best-effort/import-guarded). Additive to coord's ledger — no existing path touched. Test `tests/test_data_route_refutation.py` (3). **API-route wiring is imp1's** (filed `requests/imp2--to--imp1--wire-route-true-refutation.md`). Suite **264, 0 failed**.
3. **1970 epoch-date (user-reported):** traced — my lane emits real years, frontend guarded; root is imp4's paper builder (synthesis writes missing year as `(1970)`/`(0)` into notes → `deliverables/paper.py` copies verbatim). Routed `requests/imp2--to--imp4--paper-epoch-date-1970.md`. Offered to cross-edit `paper.py` if human authorizes.
2. **F2.12** wire `true_refutation → open_from_conflict` into the inbox/review verdict path (my `open_from_conflict` + `inbox`).
3. **F1.6 full** — embedding-novelty signal (imp4 `memory/embed`) + reader wiring + RQ-HT06 loop.
_(Deferred this turn only due to context budget — not blocked. F2.5 core is $0 + doable.)_
- **⚠️ Not mine (imp4/coord deliverables, FROZEN to coord mid-workflow):** `test_deliv_document_quality::test_a2_...` (and earlier `test_p0_fixes` latex) intermittently red as coord lands the A1–A6/B1/D paper punch-list. Unrelated to my changes; all my tests pass. Flagging for imp4/coord.

---

# status/S4 — LANE 1 · HETEROGENEOUS AGENT TEAMS  (was: engine)

**Identity:** S4 = imp2 = **Lane 1 (Teams)**, Sonnet high. Read + aligned to the PRD scheme pivot (map CONFIRMED, human "proceed").
**State:** ✅ M0 FC-1 (S2 PASS) + F1.1 branch/DAG (S2 PASS) + **RQ-HT01 scaffold DONE**. All $0, full suite **147 passed** (floor ≥46 held; suite is growing as other lanes commit). Next: F1.10 full / F1.2 verifier gate (both soft-blocked on parked Lane-2 KG/FC-5 — will do the $0 unblocked parts).

## RQ-HT01 — branch vs linear (F1.1 experiment) ✅ $0 scaffold
`experiments/exp_ht01_branch_vs_linear.py`: paid-calls-to-verdict on decomposable questions, **grounded in the REAL plans** (imports `_branch_plan`/`DEFAULT_PLAN` — 1 analyze linear vs 2 branch, not invented). Seeded retry model, 200 bootstrap seeds, F1.1 go/no-go gate; **live analyst arm HARD-gated** (`PERSONA_HT01_LIVE=1`). **Honest dry-run:** branch grounds **more reliably** (0.956 vs 0.818) but costs **~1 more paid call** (6.25 vs 5.26) → strict "branch ≤ linear calls" gate reports **PASS=False**. Not tuned to flatter — the scaffold surfaces that branch's win is grounding/reliability; the cheapness question is deferred to the gated live arm. Test `tests/test_engine_ht01_scaffold.py` (5). Wrote `results/ht01_branch_vs_linear.*`.

## Answers to S0 board follow-ups
- **`"staleness"` task type (board L106):** DEFINED — `daemon/queue.py`: `TASK_STALENESS = "staleness"` in `FC1_TASK_TYPES = {verify, debate, staleness}`; `test_fc1_task_type_constants` asserts all three. S2's grep saw 2 of 3; resolved.
- **⚠️ Flag for S6 (not my lane):** `tests/test_paper_graph.py::test_source_node_returns_main_points_and_crosscheck_finds_supports` is **order-flaky** — failed once mid-run in a 131-test suite, passes in isolation and now in the full 147 suite. Transient test-isolation fragility (shared KG/crosscheck state), NOT caused by my changes (my tests pass in every pairing). Worth S6 hardening its isolation.

## F1.1 — branching / DAG investigations ✅ $0 (fill)
`research/investigation.py`: `_branch_plan(sub_hypotheses)` — ≥2 independent sub-hypotheses fan out into one `investigate` branch each (all sharing `harvest`), joined by a single `synthesize` step (the DAG join `queue.lease()` already supports); <2 → linear `DEFAULT_PLAN`, **byte-identical**. `create(..., sub_hypotheses=)` (backward-compatible kw-only), `launch()` resolves per-step `deps` (indices→task-ids) and threads each branch's own sub-hypothesis as its `question`; `plan.md` annotates the join. Test `tests/test_investigation_branch.py` (4): branch shape, DEFAULT byte-identical, single-sub fallback, **real-queue DAG join** (synthesize leases only after BOTH branches terminal — no mocks). `test_investigation_engine.py` still green.

**S2 follow-up resolved:** `TASK_STALENESS = "staleness"` IS defined (`queue.py`, in `FC1_TASK_TYPES`) — S2's grep saw only 2 of 3; `test_fc1_task_type_constants` asserts all three. No action needed.
**Lane (LANES.md/PRD-00 §3):** OWN `agents/{verifier*,debate*,analyst,critic,revisit,director,discover,deliberate}`, `research/investigation.py`, `daemon/{supervisor,queue}`, `reading/{extract,reader}`. Provides **FC-1**; consumes FC-2, FC-5. FORBIDDEN: `agents/audit.py` (L3), `memory/**`, `synthesis/**`, `api/**`, `analysis/**`.

---

## Milestone-0 — FC-1 provided stubs (frozen signatures + typed returns) ✅ $0
Others can build against these from hour 1 (PRD-00 §5). Exact FC-1 shapes per PRD-00 §4:

1. **`persona/agents/consensus.py` (NEW)** — `span_weighted_consensus(reader_outputs) -> {claim, admit_votes:int, weighted_support:float, dissent:[{claim_id,span,weight}]}`. Real minimal impl: weights votes by grounding weight, **preserves every dissenting reader** (protected minority, not averaged away). Empty → typed zero. `demo()` self-check.
2. **`persona/research/investigation.py`** — `Investigation.open_from_conflict(conflict_id, evidence_claim_ids=None) -> Investigation`. Loop-closing entry (contradiction → falsifiable investigation); creates a durable Investigation tagged with `origin={kind:conflict, conflict_id, evidence_claim_ids}`, pins the colliding claims. **Unblocks L2/L3.**
3. **`persona/daemon/queue.py`** — FC-1 task-type constants `TASK_VERIFY="verify"`, `TASK_DEBATE="debate"`, `TASK_STALENESS="staleness"`, `FC1_TASK_TYPES`. Single source of truth other lanes enqueue against (queue stores `type` as free string; handlers append in worker.py).
4. **`persona/agents/verifier.py` (NEW)** — `verify(claim_id, *, parent_id=None, evidence_claim_ids=None) -> {ok, claim_id, verdict, check_kind, ran_code, artifact_ids, span, note}`. M0 stub: always `not_applicable`, **no model/sandbox call** (applicability-gate discipline). Full F1.2 = thin router over analyst/reason.
5. **`persona/agents/debate.py` (NEW)** — `debate(claim, positions=None, *, rounds=2, parent_id=None) -> {ok, resolved, verdict, agreement, rounds_used, transcript_ref, escalate}`. M0 stub: unresolved/agreement 0.0/escalate False, no model call. Full F1.4 gated debate.
6. **`persona/daemon/worker.py`** — appended `@handler("verify")` + `@handler("debate")` no-op stubs (append-only per PRD-01 §1 boundary protocol; S0 serializes the worker.py merge). They call the typed $0 stubs above.
7. FC-2/FC-5 shims deferred (YAGNI): my M0 stubs don't consume `inbox.file_handoff`/`calibrate.admit_decision` yet; import-guarded shims land with the F1.2/F1.4 fill that actually calls them.

## M2 budget-churn guard — now S4-owned (daemon moved to Lane 1) ✅ $0
`daemon/supervisor.py`: extracted `_should_reaudit(watchlist, can_spend)` and gated the reaudit enqueue on it — `watchlist.due() is not None` instead of `entries()`. **Behaviour-neutral today** (due() returns least-recent entry); **fixes the churn the moment Lane 2/S5 lands the `min_age_hours` floor in `due()`** (fully-fresh watchlist → None → no redundant paid re-audits). Fail-closed on exception. Pairs with my earlier consumer-side test + `requests/S4--to--S5--reaudit-staleness-consumer-contract.md`.

## Prior deliverables fold in as Lane-1 assets (already S2-PASS)
T4.1 investigate finalizer · T4.2 RQ-E05 scaffold · RQ-E06 qualifier extraction (`reading/extract.py`, FC-1-adjacent — §B qualifier emit) + evidence-tree scaffold · I1.2/E07c team-physics harness. All $0, gated, green.

---

## Verification (paste)
```
python -m pytest tests/test_engine_fc1_stubs.py -q     → 8 passed
python -m pytest -q                                    → 127 passed, 0 failed (floor ≥46 held)
python -m pytest tests/test_investigation_branch.py -q → 4 passed (branch DAG join, real queue)
python -m persona.agents.consensus                     → consensus.span_weighted_consensus OK
python -m compileall -q persona/agents persona/daemon persona/research persona/reading → clean
```

## Files for S0 to commit (lane-scoped, NEVER -A) — all $0, green
New: `persona/agents/consensus.py` · `persona/agents/verifier.py` · `persona/agents/debate.py` · `tests/test_engine_fc1_stubs.py`
Modified: `persona/research/investigation.py` · `persona/daemon/queue.py` · `persona/daemon/supervisor.py` · `persona/daemon/worker.py` (append-only — S0 serialize merge)
(Prior uncommitted lane assets still pending commit: `persona/agents/analyst.py`, `persona/reading/extract.py`, `experiments/exp_rq_e0{5,6}*.py`, `exp_rq_e07c_team_physics_live.py`, their `tests/test_engine_*`, `results/rq_e0{5,6,7c}*`.)

## Next / asks
- **Next fill (per PRD-00 §5 order):** 1.2 **verifier** agent (`agents/verifier.py*`, tool-grounded re-check) — will build as a $0 scaffold with paid model calls gated, then RQ-E19 two-reader cross-check. Reading PRD-01 for the exact spec on pickup.
- **S2:** please gate the M0 FC-1 slice (6 new tests, 118 suite) when you can.
- **S5 (Lane 2):** M2 root fix still yours — default `min_age_hours` in `watchlist.due()`; my supervisor guard + consumer test are staged and waiting. Also my `qualifier-emit-shape` request awaits your `kg.py` (still parked per S0 board).
- No cross-lane edits; `agents/audit.py` correctly untouched (it's Lane 3 now).

_Loop live: Monitor `bg23d86ge` (S4-addressed changes) + fallback heartbeat. Auto-wake on new direction._
