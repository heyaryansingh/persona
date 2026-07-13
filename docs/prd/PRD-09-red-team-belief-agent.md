# PRD-09 — Red-team-the-belief agent

> Owner: implementer lane 1 · Status: DRAFT-for-implementation · Autonomy: Balanced · Depends on: FC-2 (`inbox.file_handoff`), FC-5 (`calibrate.admit_decision`) · Reads (read-only): `kg.crosscheck`/`kg.provenance`/`kg.contradictions` (Lane 2), `verified` ledger (Lane 3-adjacent, self-owned), `reason.prove` (Lane 1) · Provides: FC-1-adjacent task type `"redteam"` + one CONTRACT CHANGE PROPOSAL (shared ledger gate value `'redteam'`)

---

## 0. Summary + how it advances the vision

Persona already refutes *its own arithmetic* inside the auditor (`audit._refute`, `agents/audit.py:139-164` runs N skeptics against the soft replication verdict) and re-tests *past* results (`revisit.revisit`, `agents/revisit.py:16`). But there is **no adversary standing between a fresh, converged belief and the moment it gets celebrated or anchored.** Today a candidate flows read → membrane → converged belief → (human) anchor with only *confirming* machinery in the path: convergence counts labs that agree (`kg.beliefs(min_independent=…)`, `kg.py:204`), the analyst writes-and-self-grades (`analyst.py`), the critic reviews prose. Nothing is tasked with the single job of *trying to kill the belief before we trust it*. That is exactly the gap CLAUDE.md §3 names — "try to falsify it before you celebrate it" — and it is backlog item #3.

This lane adds a dedicated **Red-team agent** (`persona/agents/redteam.py`) that runs immediately *before* a high-stakes belief is surfaced for anchoring and does three things, all grounded: (1) **hunts disconfirming spans** by pulling the opposite-sign literature already in the KG (`kg.crosscheck`, `kg.py:308`, returns contradicting claims *with verbatim quotes + DOIs*); (2) **names the single strongest counter-study** (rank the contradicting set by independent labs × confidence); (3) **proposes the one experiment that would falsify the belief** (the "killer experiment"), shaped as an FC-2 `cheapest_test`. Its output **never anchors and never writes a belief** — it files an FC-2 handoff so the strongest disconfirmation is *on the human's desk before they anchor*, and appends a `redteam` clearance row to the existing shared append-only ledger. Every counter it emits must resolve to a real stored span/source or it is dropped (mirroring the auditor's grounding guard, `audit.py:216`) — it fabricates nothing.

**New capability nothing else in the stack has:** an *asymmetric, pre-anchor adversary* — a step whose success metric is "did I find a reason this belief is wrong," wired to *block promotion, not confirm it*. The verifier (PRD-01 F1.2) re-runs the check to see if the claim *holds*; the red-team's job is orthogonal: to assume the claim is *wrong* and locate the evidence. Together they form the confirm/disconfirm pair the epistemic charter demands. The measurable payoff (RQ-RT01): a red-team pass at anchor-time should **reduce later reversals** — beliefs that the revisit loop (`revisit.py`) would eventually flip to weakened/refuted should be caught *before* celebration, using the verified-ledger's own revisit outcomes as ground truth.

---

## 1. File ownership (disjoint set)

**New files (this lane creates):**
- `persona/agents/redteam.py` — the adversarial red-team agent (F9.1–F9.3).

**Edited files (this lane owns the edits, all in Lane 1's ownership set per PRD-00 §3):**
- `persona/daemon/worker.py` — register `@handler("redteam")` (append-only; see boundary note).
- `persona/daemon/supervisor.py` — schedule the red-team trigger on high-stakes / pre-anchor candidates (Lane 1 owns `daemon/supervisor.py`, PRD-00 §3).

**Boundary files another lane owns — decoupled by an FC, this lane does NOT edit them:**
- `persona/inbox.py` (Lane 2, FC-2) — this lane *calls* `inbox.file_handoff("redteam", dossier)`. Consumed behind an import-guarded shim (PRD-01 Milestone-0 pattern) until Lane 2 lands it.
- `persona/memory/calibrate.py` (Lane 2, FC-5) — this lane *reads* `admit_decision(candidate).route == 'human'` as one trigger. Shimmed until Lane 2 lands it.
- `persona/memory/kg.py` (Lane 2) — this lane only **reads** via `get_kg()` (`kg.crosscheck`, `kg.provenance`, `kg.contradictions`). No writes. Read-only use of another lane's module needs no FC (it is the public read surface, FC-3 area).
- **`ops_dir/gate_decisions.jsonl`** (shared append-only ledger, PRD-00 §4 FC line 68) — this lane appends `{gate:'redteam', …}` rows. **This adds a new value to the `gate` enum** and is filed as a **CONTRACT CHANGE PROPOSAL** in §2.
- `persona/memory/verified.py` — read-only (`verified.entries()`) for the RQ-RT01 oracle and to locate the statement a candidate corresponds to. Self-contained module, read-only, no ownership conflict.

**`worker.py` merge protocol (same as PRD-01 §1):** the `@handler(name)` decorator (`worker.py:15`) makes each registration an independent additive append. This lane appends one `@handler("redteam")` block at the end of the file; never re-orders the registry. Per master resolution #1, task types are append-only. If two lanes' appends touch adjacent text it is a text merge, not a contract change — flagged here so the master can serialize the final `worker.py`.

---

## 2. Frozen contracts provided / consumed

**CONSUMES — FC-2 (Lane 2 provides, `persona/inbox.py`), verbatim:**
- `inbox.file_handoff(kind:str, dossier:dict) -> handoff_id:str`.
- Dossier schema = `{decision_requested, why_unresolvable, disagreeing:[{claim_id,span,qualifiers}], conflict_type:'temporal'|'semantic'|'misinformation'|'insufficient', cheapest_test:{action,cost_tier,dataset}, expected_updates:[{outcome,belief_change}], uncertainty, authority_boundary}`.

**CONSUMES — FC-5 (Lane 2 provides, `persona/memory/calibrate.py`), verbatim:**
- `calibrate.admit_decision(candidate:dict) -> {admit:bool, calibrated_p:float, route:'commit'|'human'|'reject', reason:str, bound:float}`.

**CONSUMES — shared append-only ledger (PRD-00 §4), verbatim base row:**
- `ops_dir/gate_decisions.jsonl` row `{candidate_id, title, gate:'relevance'|'drift'|'membrane', decision:'admit'|'skip'|'abstain', reason, score, at}`.

**PROVIDES — task type (append-only, per master resolution #1):**
- Queue task type `"redteam"`, params `{claim_id, evidence_claim_ids?, stakes?}` → dispatches `redteam.red_team(...)`.

### CONTRACT CHANGE PROPOSAL — CCP-09-A (needs master + Lane 2 + Lane 4 ratification)

**Extend the shared `gate_decisions.jsonl` `gate` enum with the value `'redteam'`, and its `decision` enum with `'clear' | 'counter_found'`.** New row shape (superset, backward compatible — existing readers ignore unknown `gate` values):

```
{candidate_id, title, gate:'redteam', decision:'clear'|'counter_found',
 reason, score:float, at,
 strongest_counter:{claim_id, span, source, labs}|null, handoff_id:str|null}
```

- **Who writes:** Lane 1 (this agent) appends exactly one `redteam` row per red-team pass.
- **Who reads:** Lane 4 renders it on the handoff-inbox / trust surface (F4.6 already reads this ledger). **Optionally** Lane 2's `calibrate.admit_decision` may consult the newest `redteam` row for a candidate and, if `decision=='counter_found'`, downgrade `route` from `'commit'` to `'human'` — this is the *hard block*. Whether the block is **hard** (Lane 2 consults the row) or **procedural** (the FC-2 handoff simply reaches the human first, and anchoring is already human-only) is the open question in §6. Default proposal: **procedural block now** (no Lane 2 change required to ship), hard block as a one-line follow-up in Lane 2 gated on RQ-RT01 passing.

**Why reuse the existing ledger rather than a new contract:** the append-only `gate_decisions.jsonl` already exists for exactly this shape of cross-lane gate signal (relevance/drift/membrane). Adding one enum value is the smallest change that makes the red-team's verdict legible to Lane 4 and consultable by Lane 2, with zero new files and zero new interfaces. `# ponytail: extend the ledger we have, don't mint a fourth handoff channel.`

---

## 3. Features

### F9.1 — The red-team agent: hunt disconfirming spans + strongest counter (core)

- **Problem & evidence.** Every trust-building step in the belief path is *confirmatory*. Convergence counts agreers (`kg.beliefs`, `kg.py:204-215`); the analyst self-grades (`analyst.py`); the critic checks prose quality, not truth (`critic.py:48`). The one adversary that exists (`audit._refute`, `audit.py:139`) attacks a *replication-likelihood number on an external paper*, not Persona's *own converged belief* on its way to being anchored. So a belief can be celebrated without anyone having *looked for the evidence it is wrong*. Research: LLMs exhibit **confirmation bias** — they over-weight evidence consistent with a stated hypothesis and under-search for disconfirmers (documented across reasoning/agent settings, e.g. premise-consistency and belief-bias effects in LLM reasoning), so a *dedicated disconfirming search* is a structural correction, not a stylistic one. **CRITIC** (Gou et al., arXiv:2305.11738) — models self-correct reliably only when grounded in *external* evidence, never introspection; the red-team's counters must come from retrieved spans, not the model's opinion. **Constitutional-AI-style self-critique** (Bai et al., arXiv:2212.08073) and **red-teaming LMs** (Perez et al., arXiv:2202.03286) establish the pattern of a separate adversarial pass whose job is to surface failure. Popperian falsification is the philosophical spine (CLAUDE.md §3).
- **Design.** New `persona/agents/redteam.py`:
  - `def red_team(claim_id: str, *, parent_id=None, stakes: str = "high", evidence_claim_ids: list[str] | None = None) -> dict` → returns
    `{ok, claim_id, verdict:'survives'|'grounded_counter'|'not_applicable', counters:[{claim_id, span, source, sign, labs, doi}], strongest_counter:{...}|None, killer_experiment:{hypothesis, action, cost_tier, dataset}|None, handoff_id:str|None, reason, note}`.
  - **Applicability gate first (correctness boundary, mirrors verifier F1.2).** `_is_attackable(prov: dict) -> (bool, reason)`: a belief is red-teamable only if `kg.provenance(claim_id)` returns a claim that (a) is **not already anchored** (`prov["anchored"]` false — no point red-teaming a human-confirmed belief) and (b) has a directional sign (`effect_sign in {"+","-"}` — a `"0"/"na"` claim has no opposite to hunt). Otherwise return `verdict="not_applicable"` with the reason — **an explicit skipped state distinct from `survives`** (honors the applicability-gate discipline; out-of-domain false "counters" are the correctness boundary).
  - **Hunt disconfirming spans (grounded, cheap, no model).** Call `kg.crosscheck(prov["subject"], prov["object"], prov["effect_sign"])` (`kg.py:308`) — it already returns `contradict:[{claim_id, text, labs, confidence, sources:[{slug,title,doi,quote}]}]`, i.e. opposite-sign literature **with verbatim quotes**. Each becomes a `counter` **only if it carries a non-empty `quote` span** (`_st`-sanitized like `audit.py:107`); a contradicting claim with no stored quote is dropped (grounding guard — `# see audit.py:216, drop a counter that can't point to its span`). This is pure KG read + filter; no model, no fabrication.
  - **Strongest counter-study.** Rank surviving counters by `(labs, confidence)` descending; `strongest_counter` = the top one (its `claim_id`, `span`, `source` DOI/title, `labs`). Deterministic.
  - **Model use is narrow and grounded.** One optional model call (Haiku `MODEL_READER`, cheap — reuse `_cost`/`Anthropic` pattern from `audit.py:110,193`) to (i) judge whether the *strongest* retrieved counter genuinely disconfirms the belief under matched qualifiers (population/dose/timepoint — reuse the qualifier language already at `app.py:650-656`), and (ii) draft the killer experiment (F9.2). The model is handed *only retrieved spans*; it may not introduce a counter that isn't in the `counters` list (post-filter: any experiment/objection referencing an unlisted source is dropped). If no counters were retrieved, **skip the model entirely** → `verdict="survives"`, `reason="no grounded disconfirming evidence found"` (an honest "I tried and couldn't kill it" is a real, cheap outcome).
  - **Verdict.** `grounded_counter` if ≥1 grounded counter survives filtering *and* the model judges the strongest one materially disconfirming; else `survives`. `not_applicable` from the gate.
  - **Registration:** `@handler("redteam")` in `worker.py` (append), params `{claim_id, evidence_claim_ids, stakes}`, dispatches `red_team(...)`.
- **Epistemic guardrails.** Writes **no belief, anchors nothing, deletes nothing** — it emits a candidate *signal* (a handoff + a ledger row). Every counter resolves to a real stored span/source (`kg.crosscheck` quotes) or is dropped — no fabricated counter, ever (the charter's hard line). The model never sees or invents evidence; it only *judges retrieved* evidence and *proposes* a test. `survives` is not a truth claim ("the belief is true") — it is precisely "no grounded disconfirmer was found," logged as such. `not_applicable` is a neutral control event, not a pass.
- **Required experiment.** **RQ-RT01 (see §3/F9.4)** — this feature's payoff is measured there; F9.1 alone is the mechanism.
- **Acceptance criteria.** (1) `red_team(claim_id)` on an anchored or non-directional belief returns `verdict="not_applicable"` and makes **zero** model calls. (2) On a belief with a grounded opposite-sign claim in the KG, `counters` contains that claim with its verbatim `span`, and `strongest_counter` is the highest-labs one. (3) A contradicting claim with an empty quote never appears in `counters`. (4) Runnable check: `pytest tests/test_redteam.py::test_gate_and_grounded_counter` — stub `kg.crosscheck` to return one quoted + one quote-less contradictor; assert the quoted one is a counter, the quote-less one is dropped, and (with an anchored `provenance`) the gate returns `not_applicable` with no model call (mock the Anthropic client, assert not called).
- **Effort** M · **Dependencies** read-only `kg` (Lane 2, live today).

---

### F9.2 — Propose the single killer experiment (the falsifier)

- **Problem & evidence.** Finding a counter is half the job; the scientific move is naming the *one experiment that would settle it*. The stack already elicits testable hypotheses (`discover.py` routes computable ideas to `investigate` and physical ones to a human escalation, `discover.py:102-112`) and the auditor already surfaces "verify these first" (`audit.py:291`), but neither is *belief-specific and falsification-shaped*. Research: **adversarial collaboration / pre-registration** in metascience — specifying in advance the result that would change your mind is the strongest guard against post-hoc rationalization; the FC-2 dossier's `cheapest_test` field is built for exactly this.
- **Design.** In `redteam.py`, `_killer_experiment(prov, strongest_counter, client) -> dict` (called only when `verdict=='grounded_counter'`):
  - One grounded model call producing `{hypothesis, action, cost_tier:'public_data'|'cheap_assay'|'expensive', dataset}` — the *single* discriminating test whose outcome would falsify the belief, phrased as "if <action> shows <X>, the belief `subject [sign] object` is wrong." Constrained to the FC-4 `cost_tier` vocabulary so Lane 3's value_queue can later cost it.
  - **Route, don't run (Balanced autonomy).** The killer experiment is *proposed*, attached to the handoff dossier's `cheapest_test`, and — if `cost_tier=='public_data'` and a dataset is named — it MAY be offered as a `run_action` for a human to one-click (never auto-run: a falsification test on a high-stakes belief is high-stakes, human-gated). It is **not** enqueued as an `investigate` task by this agent. `# ponytail: propose + hand off; the human (or Lane 3's value_queue) decides to spend — red-team doesn't act.`
  - The proposal maps into the FC-2 dossier `cheapest_test` and `expected_updates` (`[{outcome:'test refutes belief', belief_change:'retire/weaken'}, {outcome:'test upholds belief', belief_change:'strengthen toward anchor'}]`) — F9.3 files it.
- **Epistemic guardrails.** The experiment is a *proposal*, never an action or a belief. It must reference only the retrieved counter's evidence (post-filtered like F9.1). If the model can't ground a concrete test, emit `killer_experiment=None` and say so — never fabricate a dataset name (a hallucinated GEO accession is exactly the silent-wrong-number failure the charter forbids).
- **Required experiment.** trivial — no separate experiment. It is one constrained generation feeding an existing dossier field; its *value* is folded into RQ-RT01 (does the whole pass reduce reversals). The failure mode that matters (fabricated dataset) is a validation check, not a modeling choice.
- **Acceptance criteria.** (1) When `verdict=='grounded_counter'`, `killer_experiment.cost_tier ∈ {'public_data','cheap_assay','expensive'}` or `killer_experiment is None`. (2) `killer_experiment` is never populated when `verdict!='grounded_counter'`. (3) Runnable check: `pytest tests/test_redteam.py::test_killer_experiment_cost_tier_constrained` — stub the model to return an out-of-vocab `cost_tier`; assert it is coerced/rejected (not passed through raw) and that a `None`-dataset proposal does not invent one.
- **Effort** S · **Dependencies** F9.1.

---

### F9.3 — Route to handoff + clearance ledger (the block)

- **Problem & evidence.** The red-team's output must reach the human *before* anchoring and must be legible, but it must not itself mutate belief — anchoring is already human-only (`kg.human_resolve`/`kg.anchor`, `kg.py:160,181`; the API refuses auto-anchor, `app.py:696-699`). The escalation channel exists (`log().emit("escalate", …)`, `discover.py:110`) and the structured human channel is FC-2. The gap is wiring the adversary's verdict into *both* the human's decision surface and the shared audit ledger.
- **Design.** In `redteam.py`, after a verdict:
  - **On `grounded_counter`:** file `handoff_id = inbox.file_handoff("redteam", dossier)` (FC-2) where `dossier` = `{decision_requested:"Anchor this belief despite a grounded counter?", why_unresolvable:"an independent opposite-sign result exists; belief-vs-counter needs human judgment", disagreeing:[{claim_id:<belief>, span:<belief span>, qualifiers}, {claim_id:<counter>, span:<counter span>, qualifiers}], conflict_type:'semantic', cheapest_test:<F9.2 killer experiment>, expected_updates:[…], uncertainty:<1 − belief confidence>, authority_boundary:"human anchors; red-team only flags"}`. Consume behind the import-guarded shim until Lane 2 lands `inbox.py`.
  - **Always** append one row to `ops_dir/gate_decisions.jsonl` (CCP-09-A): `{candidate_id:claim_id, title:"<subj> → <obj>", gate:'redteam', decision:('counter_found' if grounded_counter else 'clear'), reason, score:<strongest counter labs or 0>, at, strongest_counter, handoff_id}`. Append-only, never edit another lane's rows (PRD-00 §4). Reuse the auditor's append discipline (open `"a"`, one JSON line).
  - Emit a legible event: `log().emit("escalate" if grounded_counter else "control", f"red-teamed '{subj} → {obj}': {'grounded counter found → human' if grounded_counter else 'survived — no disconfirmer'}", actor="redteam", parent_id=…)` — the notebook stream shows the adversary's move (design principle: motion only on real state change).
- **Epistemic guardrails.** The handoff carries the *human-anchor authority boundary* verbatim (`authority_boundary`). The block is honest: on `counter_found` the belief is **held** (routed to human), never silently admitted; on `clear` the ledger records that the adversary tried and failed, so "survived a red-team" is an *auditable* property of a belief, not a vibe. No confidence is fabricated — `score` is a lab count, `uncertainty` is `1 − stored confidence`.
- **Required experiment.** trivial — routing/plumbing; correctness is structural (covered below). The uncertain part (does blocking help) is RQ-RT01.
- **Acceptance criteria.** (1) `grounded_counter` → exactly one `inbox.file_handoff("redteam", …)` call **and** exactly one `redteam` ledger row with `decision='counter_found'`. (2) `survives` → zero handoffs, one ledger row with `decision='clear'`. (3) The dossier's `authority_boundary` states the human anchors. (4) Runnable check: `pytest tests/test_redteam.py::test_counter_files_handoff_and_ledger` — mock `inbox.file_handoff`; assert called once on `counter_found`, zero on `clear`; assert the ledger file gained one `gate:'redteam'` row in both cases.
- **Effort** S · **Dependencies** FC-2 (shimmed), CCP-09-A.

---

### F9.4 — Trigger: red-team before anchoring, on high-stakes only (selective)

- **Problem & evidence.** Unconditional adversarial machinery is expensive noise — the same finding that gates the verifier (PRD-01 F1.2, "When Does Verification Pay Off?" arXiv:2512.02304) and debate (PRD-01 F1.4). Red-team must fire **only** where a belief is about to be trusted at stakes that justify the cost. There is no "about to anchor" hook today; the closest signals are (a) a candidate the membrane routes to `human` (FC-5), and (b) a converged belief that is one side of a live contradiction (`kg.contradictions()`, `kg.py:217`), and (c) a fresh TESTED-provisional result about to be recorded as SUPPORTED (`verified.record`, `verified.py:49`).
- **Design.** In `supervisor.py` (Lane 1-owned), a selective scheduler, reusing the verifier's exact trigger logic (PRD-01 F1.2) so the two adversaries share one gate:
  - Enqueue `redteam` for a `claim_id` when **either**: (1) `calibrate.admit_decision(candidate).route == 'human'` (FC-5, shimmed → default no-fire until Lane 2 lands it); **or** (2) the claim is the *higher-support* side of a live contradiction (`kg.contradictions()`), i.e. the side most likely to be celebrated. Never enqueue for an uncontested, low-stakes READ belief.
  - **De-dup + cap** (reuse the `_announced` pattern, `membrane.py:34-46`): at most one `redteam` per claim per scheduler tick; a claim already red-teamed (has a `redteam` ledger row newer than its last belief update) is skipped. This prevents re-attacking a settled belief.
  - **Order before the verifier/anchor:** red-team enqueues at a priority that leases before the human-anchor surface refreshes — advisory, since anchoring is human-paced anyway.
- **Epistemic guardrails.** Selectivity *is* the guardrail — firing only on high-stakes/contested candidates keeps the adversary net-positive (RQ-RT01 measures this). No belief state changes on enqueue; the trigger is pure scheduling.
- **Required experiment.** **RQ-RT01 — does a red-team pass before anchoring reduce later reversals vs no red-team?** (the required experiment for this PRD). **Hypothesis:** on ≥20 seeded candidate beliefs whose *eventual* revisit outcome is known (the `verified` ledger's `status` transitions — verified/weakened/refuted — are the ground-truth oracle, `verified.py:67`/`revisit.py:45`), running `red_team` at anchor-time flags a higher fraction of the beliefs that *later get refuted/weakened* (true positives) than the no-red-team baseline (which flags none), **without** blocking beliefs that stay verified above an acceptable rate. **Metric:** among beliefs the pipeline would celebrate, later-reversal rate with red-team-block vs without (mean ± 95% CI, ≥20 seeds); secondary: false-block rate (verified-forever beliefs wrongly routed to human). **Go/no-go gate:** red-team-block strictly lowers the later-reversal rate among celebrated beliefs AND false-block rate ≤ a set ceiling (proposed ≤20%, tune in the experiment); else keep it *advisory-only* (files the handoff, never downgrades `route`) and log the reversal. **Oracle construction:** build a labeled fixture from real ledger histories — a belief whose revisit flipped it verified→refuted is a "should-have-been-blocked" positive; a belief that stayed verified across ≥2 revisits is a "should-not-block" negative; seed the KG with the belief + its (retrospectively known) contradictors and check whether `red_team` returns `grounded_counter`. `experiments/exp_rt01_redteam_reduces_reversals.py`, results to `/results`. **Load-bearing (it can block real work) — full loop required, and the hard block (CCP-09-A route downgrade) is gated on this passing.**
- **Acceptance criteria.** (1) A `redteam` task is enqueued for a contested belief's celebrated side and **not** for an uncontested low-stakes READ belief. (2) A claim with a recent `redteam` ledger row is not re-enqueued in the same tick. (3) Runnable check: `pytest tests/test_redteam_trigger.py::test_selective_and_deduped` — assert enqueue on a `route=='human'` (shim-forced) / contested candidate, no enqueue on a plain READ belief, and no double-enqueue when a fresh ledger row exists.
- **Effort** M · **Dependencies** FC-5 (shimmed), read-only `kg`, `verified` ledger for the oracle.

---

## 4. Sequencing (stubs / interface first, then order)

**Milestone 0 (hour 1, unblocks nobody but keeps the file compilable in parallel):**
1. `redteam.py::red_team(claim_id, *, parent_id=None, stakes="high", evidence_claim_ids=None)` returning `{ok:True, verdict:"not_applicable", counters:[], strongest_counter:None, killer_experiment:None, handoff_id:None, reason:"stub", note:""}`.
2. Register `@handler("redteam")` no-op in `worker.py` (append) dispatching the stub.
3. Import-guarded shims for FC-2 (`inbox.file_handoff`) and FC-5 (`calibrate.admit_decision`) → typed defaults (`file_handoff` → `"redteam-shim"`; `admit_decision` → `{route:"commit", …}` so nothing fires pre-Lane-2).

**Then, in dependency order:**
- **F9.1 (hunt + gate + strongest counter)** first — the mechanism everything else hangs on; pure KG read, testable immediately against a live KG or a stubbed `crosscheck`.
- **F9.2 (killer experiment)** next — one call, feeds the dossier.
- **F9.3 (handoff + ledger)** — wire the block; needs FC-2 shim + CCP-09-A ledger row.
- **F9.4 (trigger in supervisor)** + **RQ-RT01** last — needs F9.1–F9.3 whole to measure end-to-end reversal reduction; the hard block (Lane 2 route downgrade) lands only after the gate passes.

**Rationale:** the agent is self-contained (F9.1–F9.3) and can be fully unit-tested before the supervisor wires it live; the load-bearing decision (block vs advisory) is deferred to RQ-RT01, so nothing blocks a real belief until the evidence says it should.

---

## 5. Test & verification plan

**Unit (pytest, no framework beyond it — ponytail):**
- `test_redteam.py::test_gate_and_grounded_counter` (F9.1) — applicability gate returns `not_applicable` with zero model calls on an anchored/non-directional belief; a quoted contradictor becomes a counter, a quote-less one is dropped. Mock the Anthropic client, assert not called on the gate path.
- `test_redteam.py::test_killer_experiment_cost_tier_constrained` (F9.2) — out-of-vocab `cost_tier` coerced/rejected; `None` dataset not fabricated.
- `test_redteam.py::test_counter_files_handoff_and_ledger` (F9.3) — `counter_found` → one `file_handoff` + one `gate:'redteam'` ledger row; `clear` → zero handoffs, one `clear` row. Mock `inbox.file_handoff`.
- `test_redteam_trigger.py::test_selective_and_deduped` (F9.4) — fires on contested/high-stakes, not on plain READ; no double-enqueue when a fresh ledger row exists.

**Reused oracle (the required experiment):**
- **`verified.jsonl` revisit outcomes are the RQ-RT01 ground truth** (`verified.py`/`revisit.py`) — a belief the revisit loop later flipped to refuted/weakened is a labeled "should-have-been-blocked" positive; a belief that held across revisits is a negative. `exp_rt01_redteam_reduces_reversals.py` replays these histories: seed the belief + its retrospectively-known contradictors into the KG, run `red_team`, and score whether `grounded_counter` predicts the eventual reversal. This is real-behavior verification against the system's own self-correction telemetry — no synthetic labels invented.
- Where the correlated-poisoning regime is relevant (a high-volume, low-independence counter trying to overturn a belief), cross-check the red-team does **not** treat a poisoning-signature counter as decisive — reuse `kg.poisoning_signals` (`kg.py:253`) as a guard so an astroturfed "counter" doesn't trigger a false block (ties to `experiments/exp_when_protection_matters.py`).

**No browser smoke in this lane** — no new UI surface. The red-team's verdict renders via the existing notebook stream (`log().emit`) and the shared ledger that Lane 4's handoff-inbox already reads (F4.6). If the master wants a dedicated "adversary" panel, that is Lane 4.

---

## 6. Open questions for the master / user

1. **Hard block vs procedural block (CCP-09-A, blocks Lane 2 only if hard).** Should Lane 2's `calibrate.admit_decision` consult the newest `redteam` ledger row and downgrade `route` `'commit'→'human'` on `counter_found` (a *hard* block), or is the FC-2 handoff reaching the human first (anchoring is already human-only) a sufficient *procedural* block? **Default: procedural now** (ships with zero Lane 2 change), hard block as a one-line Lane 2 follow-up gated on RQ-RT01 passing. Confirm the master accepts the ledger enum extension (`gate:'redteam'`, `decision:'clear'|'counter_found'`).
2. **`conflict_type` for the red-team handoff (FC-2).** A red-team escalation defaults to `conflict_type:'semantic'` (belief vs independent opposite result under possibly-matched qualifiers). Confirm Lane 2's `inbox.py` expects `'semantic'` for `kind="redteam"`, or whether a distinct value is wanted (mirrors PRD-01's open question on the debate-unresolved `conflict_type`).
3. **Anchor-time hook (Lane 1/2 boundary).** F9.4's trigger uses membrane-route (FC-5) + contradiction membership as the "about to be celebrated" proxy, because there is no explicit "pre-anchor" event. If Lane 2/Lane 4 add a real "human is about to click anchor" event, red-team should fire there too (tighter, fewer wasted passes). Flag whether such an event is planned so we wire to it instead of the proxy.
4. **False-block ceiling for RQ-RT01.** Proposed ≤20% false-block rate (verified-forever beliefs wrongly held for human review) as the go/no-go on the *hard* block. Confirm the Balanced-autonomy posture is comfortable holding up to that fraction of eventually-good beliefs for a human glance — the cost is a human read, not a lost belief.

---

## Return summary (for master / FC coherence)

- **File:** `docs/prd/PRD-09-red-team-belief-agent.md` (this doc). Source touched: none.
- **Feature ids:** F9.1 (hunt disconfirming spans + strongest counter + applicability gate), F9.2 (killer-experiment proposal), F9.3 (FC-2 handoff + shared-ledger clearance row), F9.4 (selective pre-anchor trigger + RQ-RT01).
- **NEW public signatures (freeze for FC coherence):**
  - `redteam.red_team(claim_id: str, *, parent_id=None, stakes: str = "high", evidence_claim_ids: list[str] | None = None) -> dict` with keys `{ok, claim_id, verdict:'survives'|'grounded_counter'|'not_applicable', counters:[{claim_id, span, source, sign, labs, doi}], strongest_counter:{...}|None, killer_experiment:{hypothesis, action, cost_tier, dataset}|None, handoff_id:str|None, reason, note}`.
  - Queue task type `"redteam"`, params `{claim_id, evidence_claim_ids?, stakes?}` (append-only in `worker.py`).
- **CONTRACT CHANGE PROPOSAL (needs ratification):** CCP-09-A — extend shared `ops_dir/gate_decisions.jsonl` `gate` enum with `'redteam'` and `decision` enum with `'clear'|'counter_found'` (+ optional `strongest_counter`, `handoff_id` fields). Backward compatible; existing readers ignore unknown `gate` values.
- **Open question blocking another lane:** only if the master chooses the **hard block** (OQ#1) does Lane 2's `calibrate.admit_decision` need a one-line consult of the `redteam` ledger row — and that is gated on RQ-RT01 passing, so it does not block any lane's Milestone-0 or first-fill work. Everything else in this lane is self-contained (read-only `kg`, shimmed FC-2/FC-5).
