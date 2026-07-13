# PRD-19 — Null-hunt swarm mode (active silence detector)

> **Owner lane:** 1 + 3 · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced · **Opened:** 2026-07-13
> **Depends-on:** PRD-03 F3.5 (`analysis/darklit.py` — `abandoned_target`/`results_gap` must land first; this PRD *appends* to that file), PRD-03 F3.2 (`analysis/value_queue.py` — consumes the run-action rows this PRD emits), PRD-03 F3.9 (`science.clinical_trials` field extension — this PRD adds `WhyStopped` to that additive field list), PRD-01 (owns `reading/reader.py` + the `worker.py` append-only handler protocol + FC-1 task-type convention). Consumes **FC-4** (value_queue `run_action` "<verb>:<args>" string, FC-8 additive-string convention).
> **Read first:** `docs/prd/PRD-00-overview.md` (frozen contracts, epistemic discipline), `docs/prd/PRD-03-intellectual-engine.md` §F3.5, `Initial Planning Docs/BUILD_PLAN.md` §3.5, backlog #24.

---

## 0. Summary + capability unlocked

The dead-science meter (PRD-03 F3.5, `analysis/darklit.py`) *passively* flags a target as abandoned/decaying — a changepoint on the trial-registration series (`abandoned_target(...) -> {active: False, ...}`) or a registered-vs-posted results gap worse than the Cochrane ~13% base rate (`results_gap(...)`). That flag currently only tints a value-queue row. **This PRD turns the flag into an active behaviour**: a dedicated reading *mode* that hunts the confirming negative/null evidence the published record structurally hides — buried in **preprints** (`SRC:PPR` on Europe PMC, where nulls that never survived journal review still surface), **TERMINATED/WITHDRAWN ClinicalTrials.gov** entries (a stopped trial's `whyStopped` string is public but never cited), and (deferred, §6) supplementary tables.

**Capability unlocked:** for an abandoned load-bearing target, Persona stops waiting for a contradiction to *arrive* and goes *looking* for the file-drawer — recovering "again-null" evidence that publication bias hides (BUILD_PLAN §3.5: *"surfaces the negative evidence the published record structurally hides — a known pathology of biomedical science that no tool instruments"*). This is the acting-loop analogue of the swarm: contradiction detection finds papers that *disagree*; null-hunt finds *what stopped being said*.

**Epistemic posture (non-negotiable).** Recovered nulls are **candidate evidence typed `READ`, exact-span-grounded** exactly like any other claim — they flow through the existing `extract.validate_claims` verbatim gate and the membrane harvest. They **inform, never auto-anchor**; an abandonment flag is a *hypothesis routed to the value queue*, never an auto belief-downgrade (inherits the F3.5 guardrail). A `TERMINATED` trial is **not** asserted to be a failed drug — funding/enrollment terminations are not null results; the meter reports registry state, not verdicts.

---

## 1. File ownership (disjoint; boundary files flagged)

| File | This PRD's change | Owner / boundary handling |
|---|---|---|
| `persona/reading/reader.py` | **ADD** `null_scout`, `record_trial_null`, internal `_null_hunt_queries`, `_terminated_trials` (pure additions — no edit to `scout`/`read_work`/`read_url`) | **Lane 1 file** (PRD-01 owns it). Boundary: land *after* PRD-01's reader.py changes; append-only new functions, never touch existing ones. No FC needed — pure addition, no shared state. |
| `persona/daemon/worker.py` | **APPEND** `@handler("null_hunt")` `_null_hunt` to the registry | **Append-only shared registry** (same protocol as FC-1's `verify`/`debate` handlers, worker.py:384). Never re-order rows; S0-serialize the merge like the other lanes. |
| `persona/analysis/darklit.py` | **APPEND** `null_hunt_candidates(topic=None)` | **Boundary file — shared with PRD-03 F3.5** (which *creates* darklit.py). Depends-on: PRD-03 F3.5 lands `results_gap`/`abandoned_target` first; this PRD appends one pure read-only function. Coordinate as append-only (no edit to F3.5 functions). |
| `persona/tools/science.py` | **ADD** `"WhyStopped"` to the `clinical_trials` fields string + surface `whyStopped` in each trial dict | **Boundary — coordinate with PRD-03 F3.9** (which also extends this exact field list at science.py:87). Additive field only; **no signature change** to `clinical_trials`. If F3.9 lands first, this is a one-token add to its field list. |
| `experiments/exp_rq_e30_null_hunt.py`, `results/` | **NEW** RQ-E30 case-control enrichment experiment + results | This PRD owns (new files). |
| `persona/tests/test_null_hunt.py` | **NEW** | This PRD owns. |

Everything this PRD *provides* is a pure addition; the only edits to another lane's files are append-only registry rows and additive field lists, both governed by protocols already in the repo.

---

## 2. FCs provided / consumed + CONTRACT CHANGE PROPOSAL

**Provided (new public signatures — copy verbatim):**
- `reader.null_scout(target: str, want: int = 15) -> list[dict]` — null-biased discovery; each dict carries the existing slim-work shape plus `kind: 'preprint' | 'clinical_trial'`.
- `reader.record_trial_null(trial: dict, target: str, *, parent_id=None) -> dict` — writes a structured `READ` claim to `sources/<nct-slug>/{meta.json,claims.jsonl}` for a terminated/withdrawn trial (no LLM; the `whyStopped` string is the exact span). Returns `{ok, slug, recorded: bool, reason?}`.
- Task type `"null_hunt"` with handler `_null_hunt(task, queue)` in `worker.py` (params: `{target: str}`). Result string like the other handlers.
- `darklit.null_hunt_candidates(topic=None) -> list[dict]` — abandoned load-bearing targets shaped for the value queue: `[{target, changepoint_ts, gap_ratio, load_bearing: float, run_action: "null_hunt:<target>", cost_tier: 'public_data', note}]`. Read-only; calls no belief-mutation path.

**Consumed:** FC-4 value_queue `run_action` string convention (FC-8: additive verb-prefixed string, **no FC-4 signature change**); `science.clinical_trials` (existing output, terminated statuses already returned — see §3.1); PRD-03 `darklit.abandoned_target`/`results_gap`; `reader.scout`/`read_work`; `membrane.harvest` (existing worker `harvest` handler).

**CONTRACT CHANGE PROPOSAL — CCP-19a (route to whoever owns the value_queue `run_action` dispatch site; blocks nothing until value_queue F3.2 exists).**
FC-8 dispatches `run_action` strings `"<oracle>:<args>"` via `science.call(name, params)`. `null_hunt` is a **task type, not a science oracle**. Propose: the value-queue action dispatcher (the "run" path behind `value_queue` rows — Lane 3 auto-dispatch and/or Lane 4's UI run button) recognizes the `"null_hunt:"` prefix and routes it to `queue.enqueue("null_hunt", params={"target": <args>})` instead of `science.call`. **Additive, prefix-based routing rule — no signature change to FC-4 or FC-8.** Same discipline gate as every value-queue action: advisory / human-click under Balanced autonomy; auto-dispatch only once **RQ-E17** (VoI ranking) *and* this PRD's **RQ-E30** (enrichment) both pass. Until CCP-19a is ratified, the null_hunt handler is still fully drivable by direct `queue.enqueue("null_hunt", ...)` (e.g. from a manual API call or the experiment harness), so the capability ships independently of the dispatcher wiring.

---

## 3. Features

### F19.1 — Null-hunt reader mode (`reading/reader.py`)

**Problem & evidence.** `reader.scout` (reader.py:80) fans an interest out to the *top relevant* unread works via `search_multi` (openalex→crossref→europepmc→arxiv, sources.py:161) and is gated toward the persona's *objective* (`_relevance_filter`, reader.py:60) — it is optimized to find what the field is *actively saying*, the exact opposite of what a null-hunt needs. There is no query mode biased toward negative results, and terminated trials are never turned into readable evidence. Europe PMC exposes preprints via the `SRC:PPR` query filter (sources.py:105 already calls the Europe PMC `search` endpoint with a free-text `query`), and `science.clinical_trials` (science.py:82) already returns `OverallStatus` for every matching study — so terminated entries are *already in the response*, just discarded downstream.
**Research/source:** BUILD_PLAN §3.5 ("Dead Science Walking", abandoned-target changepoints); publication-bias / file-drawer literature (Rosenthal 1979; Cochrane Handbook Ch.13 — ~13% of registered trials post results, the base rate F3.5 already cites); preprints as a null-recovery channel (bioRxiv/medRxiv host results that never clear journal significance filters).

**Design (files, signatures, data flow, seams).**
- `_null_hunt_queries(target: str) -> list[str]` — builds 2–3 null-biased Europe-PMC query strings, e.g.
  `f'{target} AND (null OR "no significant" OR "no significant difference" OR "failed to" OR "did not" OR negative)'` and a preprint-scoped variant `... AND (SRC:PPR)`. Pure string builder; deterministic.
- `_terminated_trials(target: str, want: int) -> list[dict]` — calls `science.clinical_trials(target, size=want)`, keeps only `status in {'TERMINATED','WITHDRAWN','SUSPENDED'}`, shapes each into a slim work-like dict `{slug: f'nct_{nct}', title, kind: 'clinical_trial', nct, status, why_stopped, landing_url: f'https://clinicaltrials.gov/study/{nct}'}`. De-dupes on slug against `_already_read` (reader.py:32).
- `null_scout(target, want=15) -> list[dict]` — runs `_null_hunt_queries` through `sources.europepmc_search` (bypassing the objective-relevance gate — a null on an *abandoned* target is by definition off the persona's active objective, so `_relevance_filter` would wrongly drop it), tags each returned work `kind='preprint'`, unions the `_terminated_trials` records, de-dupes against `_already_read`, caps at `want`. Fails **open/empty** exactly like `scout` (embedding/network hiccup ⇒ `[]`, never a crash).
- `record_trial_null(trial, target, *, parent_id=None) -> dict` — for a terminated-trial record, writes `sources/nct_<id>/meta.json` + `claims.jsonl` with a single `READ` claim: `{subject: nct, relation: 'terminated_without_result', object: target, effect_sign: 'na', quote: <why_stopped>, provenance: 'READ'}`, reusing `_claim_id`/`_now`. **Applicability gate:** if `why_stopped` is empty/absent, do **not** fabricate a claim — return `{ok, recorded: False, reason: 'no whyStopped span'}` and let the handler surface the trial as a *lead* only.

Data flow: `null_hunt` task → `null_scout(target)` → preprints go through the untouched `read_work` (LLM extract, verbatim-gated) → terminated trials go through `record_trial_null` (structured, no LLM) → both land in `sources/` → existing `harvest` handler ingests `claims.jsonl` → membrane/KG. **No new pipeline; reuse of two existing sinks.**

**Epistemic guardrails.** (1) Exact-span for *both* channels: preprint claims via `extract.validate_claims`; trial claims via the `whyStopped` verbatim span (abstain if absent). (2) Terminated ≠ failed: `relation='terminated_without_result'`, never `'refuted'` — the claim asserts *registry state*, not a scientific verdict. (3) Nulls inform, never anchor: they enter as ordinary `READ` candidates; no belief-mutation, no auto-downgrade of the target's beliefs. (4) Provenance breadcrumb: `null_scout` sets `interest=f'null-hunt:{target}'` on the work dict so `read_work`'s `meta.json` records the hunt mode — the funnel stays legible ("these claims came from the file-drawer"). (5) Absence of recovered nulls is **not** evidence the target is fine — the handler reports "found 0" as a neutral funnel event, never as confirmation.

**Required experiment.** See **RQ-E30** (F19.2 is the trigger, F19.1 is the mechanism the experiment exercises). Query construction + status filtering is non-trivial branching ⇒ one runnable check below.

**Acceptance + ONE runnable check.** `null_scout` returns only `kind in {'preprint','clinical_trial'}` dicts, drops non-terminated trials, and returns `[]` (not an exception) when both channels are empty; `record_trial_null` abstains (`recorded=False`) on a trial with no `whyStopped`. Check: `pytest persona/tests/test_null_hunt.py::test_null_scout_shapes_and_trial_abstains` (monkeypatches `sources.europepmc_search` + `science.clinical_trials` with fixtures — no network).

**Effort** M · **Deps** reader.py (PRD-01), science.py `WhyStopped` field (§1, coord PRD-03 F3.9).

---

### F19.2 — Abandonment → null_hunt trigger (`daemon/worker.py`, `analysis/darklit.py`)

**Problem & evidence.** F3.5's `abandoned_target(...) -> {active: bool, changepoint_ts, note}` and `results_gap(...) -> {gap_ratio, worse_than_base, ...}` compute the flag but nothing *acts* on it — F3.5 only "feeds F3.2" as a tinted row (PRD-03 F3.5 design). BUILD_PLAN §3.5 specifies the missing arc: *"abandonment flag → targeted swarm search for corroborating nulls/terminations."* The worker registry (worker.py:14, append-only) is the swarm's dispatch surface; FC-1's `verify`/`debate` handlers (worker.py:387) are the template for adding a task type.
**Research/source:** BUILD_PLAN §3.5 H3.5; the acting-loop thesis (CLAUDE.md — "the *acting* loop and the persistent self" is the piece competitors lack).

**Design.**
- `darklit.null_hunt_candidates(topic=None) -> list[dict]` (append to darklit.py): for each load-bearing target in `topic` whose `abandoned_target` returns `active=False` **or** whose `results_gap` returns `worse_than_base=True`, emit `{target, changepoint_ts, gap_ratio, load_bearing, run_action: f'null_hunt:{target}', cost_tier: 'public_data', note}`. Read-only — reuses F3.5's own functions; calls no `kg.*` writer. This is the row F3.2's `value_queue` slots in (the null is the *cheapest possible* experiment: it already exists, buried).
- `@handler("null_hunt")` `_null_hunt(task, queue)` (append to worker.py): `target = task.params.get("target")`; emit a `spawn`/`thought` event ("hunting the file-drawer for abandoned target '<target>' — preprints + terminated trials"); `works = await asyncio.to_thread(reader.null_scout, target)`; for each: `read_work` (preprint) or `record_trial_null` (trial), budget-gated exactly like `_gather` (worker.py:99); enqueue one `harvest`; return `f'null_hunt: recovered {n} candidate null(s) for {target}'`. Legible-by-construction (each recovered null is a `read`/`claim` event under the same parent).
- Trigger wiring: `null_hunt_candidates` rows carry `run_action="null_hunt:<target>"` → dispatched per **CCP-19a** (human-click advisory now; auto only post-RQ-E17+E30). The handler is also directly enqueuable for tests/manual runs.

**Epistemic guardrails.** The abandonment flag stays a **hypothesis routed to the value queue** (inherits F3.5's guardrail verbatim — no auto belief-downgrade). Balanced autonomy: dispatch is human-gated until both RQ gates pass. `null_hunt_candidates` is a pure read over F3.5 outputs — it cannot mutate the KG. Budget discipline: `_null_hunt` honours `budget().can_read()` so a hunt never starves the persona's primary reading.

**Required experiment.** RQ-E30 (F19.3). The candidate-selection boolean over F3.5 outputs is trivial arithmetic; one property check guards it (below).

**Acceptance + ONE runnable check.** `null_hunt_candidates` returns a `run_action='null_hunt:<target>'` row for an `active=False` target and **skips** an `active=True` one, and never calls a KG writer (patched-KG spy asserts zero write calls). Check: `pytest persona/tests/test_null_hunt.py::test_candidates_select_and_no_kg_write`.

**Effort** S · **Deps** F19.1, PRD-03 F3.5 (darklit), FC-4 (run_action).

---

### F19.3 — RQ-E30: does null-hunt recover known post-hype nulls? (enrichment gate)

**Problem & evidence.** H3.5 (BUILD_PLAN §3.5): *"Abandonment signatures are enriched for downstream-discoverable negative/again-null evidence relative to matched still-active controls."* This is the **load-bearing, uncertain** claim of the whole PRD — if null-hunt recovers no more nulls on abandoned targets than on active controls, the mode is theatre. Per CLAUDE.md §2 it must clear a seeded ≥20 gate *before* driving any autonomous dispatch (and before the run_action can auto-fire).

**Hypothesis + metric + gate.**
- **H:** null-hunt recovers more corroborating null/negative/terminated evidence per target on **cases** (targets with documented post-hype nulls/abandonment — e.g. BACE1/Alzheimer's, torcetrapib/CETP, anti-amyloid pre-2021, sirtuin activators) than on **matched still-active controls** (same disease area, comparable era-of-peak, still accruing trials — e.g. GLP-1/obesity, PCSK9/LDL).
- **Metric:** `enrichment = mean(null_items_recovered | case) / mean(null_items_recovered | control)`, where a "null item" is a `null_scout` result that passes an exact-span null check (preprint claim with a negative-result span, or a terminated-trial `whyStopped`). Secondary: **precision** of recovered items (fraction that are genuinely null on human/rule check, not false keyword hits).
- **Gate:** enrichment 95%-CI lower bound **> 1.0** (bootstrap, ≥20 resamples over target sampling + query-seed variation) **AND** recovered-item precision ≥ 0.70. Advisory-only (surfaced, not auto-dispatched) until passed — consistent with the value queue already being RQ-E17-gated.

**Design.** `experiments/exp_rq_e30_null_hunt.py`: a small curated, **cached** case-control target list (cases with citations to their documented nulls; matched controls), each run through `null_scout` with cached Europe PMC + ClinicalTrials fixtures (no live network in the seeded loop — cache per CLAUDE.md §4 "cache aggressively"). ≥20 seeds via bootstrap resampling of the target pairs and shuffling `_null_hunt_queries` order. Report mean ± 95% CI to `results/` and register RQ-E30 in `docs/RESEARCH_QUALITY_PROGRAM.md`. Log any reversal (if enrichment ≤ 1, the mode does not auto-dispatch — write the reversal down).

**Epistemic guardrails.** Ground truth is a *documented* null per case (cited), not the model's opinion. Controls are matched on disease area + peak era to avoid confounding "abandoned" with "recently hot." Precision is scored on exact spans, not keyword presence. Seeds fixed and saved; the enrichment number is held-out, never a self-report.

**Acceptance + ONE runnable check.** RQ-E30 registered with a go/no-go gate; the experiment runs ≥20 seeds and emits mean ± CI. Check: `python experiments/exp_rq_e30_null_hunt.py --seeds 20 --smoke` asserts it produces an enrichment estimate with a CI and a boolean `gate_passed` (smoke mode uses the cached fixtures; asserts no crash + fields present).

**Effort** M · **Deps** F19.1, F19.2.

---

## 4. Sequencing

1. **F19.1 mechanism** (`null_scout` + `record_trial_null`) against cached fixtures — self-contained once PRD-01's reader.py + PRD-03 F3.9's `WhyStopped` field land. Ship + `test_null_hunt.py`.
2. **F19.2 trigger** — append `_null_hunt` handler (worker.py) + `null_hunt_candidates` (darklit.py, after PRD-03 F3.5). Directly enqueuable end-to-end at this point.
3. **F19.3 RQ-E30** — build the case-control fixture set, run ≥20 seeds, register the gate. Only after it passes does CCP-19a's auto-dispatch unlock.
4. **CCP-19a** — ratify with the value_queue dispatch owner (Lane 3/4) once F3.2's dispatcher exists; until then, manual/API enqueue drives it.

## 5. Test plan

- `test_null_hunt.py::test_null_scout_shapes_and_trial_abstains` — F19.1 shapes, non-terminated drop, empty-safe, whyStopped-absent abstention (fixtured, no network).
- `test_null_hunt.py::test_candidates_select_and_no_kg_write` — F19.2 selection boolean + patched-KG-spy asserts zero belief mutation.
- `test_null_hunt.py::test_null_hunt_handler_routes` — handler sends preprints to `read_work`, trials to `record_trial_null`, enqueues one `harvest` (both sinks monkeypatched; assert call routing + budget gate honoured).
- `exp_rq_e30_null_hunt.py --smoke` — experiment harness self-check (fields + CI present).
- Reuse existing `harvest`/membrane tests unchanged (null claims are ordinary `READ` claims — no new membrane path to test).

## 6. Open questions

1. **CCP-19a ownership** — who owns the value_queue `run_action` dispatch site (Lane 3 auto-dispatch vs Lane 4 UI run button)? The prefix-routing rule (`"null_hunt:"` → `queue.enqueue`) must live wherever `science.call(...)` is invoked for other run_actions. Blocks *auto*-dispatch only; manual enqueue is unblocked. **Flag to Lane 3 + Lane 4.**
2. **`WhyStopped` field coordination** — confirm PRD-03 F3.9 adds it (this PRD needs it for the trial exact-span); if F3.9 slips, F19.1 ships preprint-only and trials degrade to *lead-only* (no typed claim). **Flag to PRD-03/Lane 3.**
3. **Supplementary-table mining** — deferred from v1 (needs a supp-file fetch seam that doesn't exist; preprints + terminated CT are the two already-wired cheap channels that prove H3.5). `# ponytail: add supp-table extraction once the two cheap channels clear RQ-E30`. Add when enrichment is proven and the extra recall is worth a new fetch path.
4. **Case-control gold set** — the RQ-E30 target list needs a handful of *documented* post-hype nulls with citations + matched active controls; curating it is the real cost of F19.3. Candidate cases: BACE1/Alzheimer's, torcetrapib/CETP, sirtuin activators, pre-2021 anti-amyloid. **Non-blocking to other lanes.**
