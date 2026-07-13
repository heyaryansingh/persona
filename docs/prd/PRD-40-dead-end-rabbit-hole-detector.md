# PRD-40 — Dead-end / rabbit-hole detector

> Owner: implementer lane 1 · Status: DRAFT-for-implementation · Autonomy: Balanced · Depends on: `research/investigation.py` (the unit of work), `daemon/supervisor.py` + `daemon/queue.py` (the investigation-driving + scheduling slot), the verified ledger (`memory/verified.py`) + membrane admits (`memory/membrane.py`) as the validated-belief signal · Provides: **FC-30** (per-investigation convergence-health read) + an advisory supervisor reprioritize/pause hook + a resumable queue hold · Backlog #136.
> Governed by PRD-00 §4/§6 and §8 reconciliation. Where this body disagrees with §4/§6, §4/§6 win.

---

## 0. Summary and the capability unlocked

Persona's unit of work is the **investigation**: a persistent multistep program that commits to one open question and drives a team of agent-steps through it (`research/investigation.py:1-13`). Once launched, the entire step chain is enqueued and runs to completion — `launch()` enqueues every step (`investigation.py:204-245`) and `finalize()` only *aggregates* the outcomes (`investigation.py:248-273`); **nothing ever asks, mid-flight, "is this program still worth the money?"** The scheduler opens investigations up to `MAX_ACTIVE_INVESTIGATIONS` (=4, `config.py:74`; `supervisor.py:119-135`) but has no path to *close* a non-converging one — a rabbit-hole holds one of the four scarce active slots and quietly drains the shared daily budget (`budget.py:38-53`) indefinitely, while a productive question waits behind it.

Every ingredient to catch this already exists but is **disconnected**: per-task cost is attributed at completion (`supervisor.py:64-68` emits a `cost` event carrying `task_id`, `task_type`, `cost` — the value/$ *denominator*), step-tasks carry their `investigation_id` (`queue.py:174-181`), and validated beliefs land at two measurable sinks — membrane admits (converged beliefs at harvest, `membrane.py:118-131`) and the verified/TESTED ledger (`verified.py:49-64`). Nobody joins spend to yield *per investigation*.

This PRD adds a **dead-end / rabbit-hole detector** (Backlog #136): a new lane-1 module `research/convergence.py` that (a) rolls real spend and real validated-belief landings into a **per-paid-round series** for one investigation, (b) computes a **measured** convergence verdict — `productive` / `slowing` / `dead_end` — from *yield-per-dollar* and a *stall-round* count (consecutive recent paid rounds that admitted **zero** new validated beliefs), and (c) hands the supervisor an **advisory** hook to reprioritize or pause a `dead_end` so the swarm cuts losses and frees a slot. The capability unlocked: Persona gains **self-awareness about its own effort** — it recognizes when *it* is stuck (spend climbing, nothing new believed) and stops, the same disciplined move it already applies to evidence, now turned on the researcher itself. The load-bearing, genuinely-uncertain part — telling a *genuinely stalled* investigation apart from a *productive-but-slow deep-dive that just needs more rounds* — is gated behind RQ-E54 before any cut is autonomous.

---

## 1. File ownership (this lane's DISJOINT set)

**New files (this lane creates, lane 1):**
- `persona/research/convergence.py` — the detector: per-investigation spend⋈yield round-series accounting + the FC-30 `convergence_health` verdict + the advisory recommendation logic. All read-only over existing tables; mutates nothing.
- `experiments/exp_dead_end_detector.py` — the RQ-E54 labeled-trace harness (new experiment; `experiments/*` is shared-additive, owned by the creating lane per PRD-00 §3 "new-file ownership rule").
- `persona/tests/test_convergence.py` — this PRD's unit checks (this lane owns).

**Edited files (this lane owns the edits — all lane-1 files):**
- `persona/daemon/supervisor.py` — (1) one additive kwarg on the existing `cost` event emit (`supervisor.py:66`): `investigation_id=task.investigation_id` when present, so spend attribution is event-native and exact. (2) In section 0's investigation driver (`supervisor.py:119-135`), an **advisory** pass: for each active investigation call `convergence.convergence_health(...)`; on a `dead_end` verdict emit one legible event + append to the investigation worklog, and — only when the enforce gate `ops_dir/rq_e54.passed` exists — reprioritize (soft) or pause (hard) it. **Additive only** — coordinate the exact insertion point with PRD-01's own `supervisor.py` edits (same lane, single owner, no cross-lane contract).
- `persona/daemon/queue.py` — a resumable **hold**: additive nullable column `held INTEGER NOT NULL DEFAULT 0` (migration mirrors the existing investigation-column migration at `queue.py:99-102`), one extra predicate `AND t.held=0` in `lease()`'s runnable-task `SELECT` (`queue.py:127-133`), and `set_investigation_hold(investigation_id, held: bool) -> int` toggling the flag on that investigation's still-pending step-tasks. A held task stays `pending` (no state lost); resume = `held=0`. In-lane; no FC.
- `persona/research/investigation.py` — one additive convenience: expose `Investigation.convergence_health(self, *, kg=None)` as a thin call into `convergence.convergence_health(self.id, kg=kg)` so callers with an `Investigation` in hand read health without importing the module. No change to `create`/`launch`/`finalize`/`open_from_conflict`.

**New sidecar artifact (lane-1 owned, written only via the detector):**
- `investigations/<slug>/convergence.jsonl` — append-only, one row per `convergence_health` evaluation: `{at, rounds, spend, validated_total, yield_per_dollar, stall_rounds, verdict}`. Lives inside the investigation's own legible folder (`investigation.py:103-104`), append-only and reversible-by-nature (never mutated), mirroring the worklog's audit discipline (`investigation.py:198-201`). This is the visible *trail* of the effort-judgement; the verdict itself is recomputed from primary tables each call, never trusted from this cache.

**Boundary files another lane also touches — decoupled by a contract:**
- `persona/memory/verified.py`, `persona/memory/membrane.py` — **READ ONLY from this lane** (`verified.entries()`, `verified.py:35`; the membrane's converged-belief count / `belief_update` events, `membrane.py:118-131`). No edit, no schema change; the join is on timestamps + the investigation's step task-ids.
- `persona/inbox.py` (Lane 2, **FC-2**) — consumed import-guarded for the high-stakes human-confirm handoff; degrades to log-only when absent (SPECCED-but-maybe-unbuilt → never a blocker, PRD-29/35 precedent).
- `persona/analysis/engine.py` (Lane 3, **FC-4**) — consumed import-guarded to decide `high_stakes` (load-bearing); degrades to an origin heuristic when absent.
- `persona/api/app.py` (Lane 4) + `persona/api/static/index.html` (Lane 4) — Lane 4 renders per-investigation convergence health (the "cost-vs-yield / dead-end badge" on the swarm + investigations surfaces, PRD-00 §3 Lane-4 per-agent cost-vs-yield). This lane provides the read; Lane 4 adds the route + surface. **Flagged as CCP-40a in §6.**

---

## 2. Frozen contracts provided / consumed

### FC-30 — this lane PROVIDES (new; `persona/research/convergence.py`)

```python
# READ seam — consumed by supervisor.py (same lane), by RQ-E54, and (via CCP-40a) by Lane 4.
def convergence_health(investigation_id: str, *, kg=None) -> dict:
    """MEASURED self-awareness about the researcher's OWN effort on one investigation. Reads real
    spend (cost events ⋈ this investigation's step task-ids) and real validated-belief landings
    (membrane admits + verified-ledger TESTED, attributed to the investigation) into a per-paid-round
    series, and reports whether the program is still converging. PURE read — never mutates a belief,
    the KG, the queue, or the investigation. Advisory until ops_dir/rq_e54.passed exists."""
    # returns:
    # {
    #   "verdict": str,                 # 'productive' | 'slowing' | 'dead_end'
    #                                   #   'dead_end' ONLY when spend is rising AND a sustained
    #                                   #   zero-yield tail (stall_rounds >= STALL_K) — never for
    #                                   #   merely-slow: a deep-dive that still lands beliefs resets it.
    #   "yield_per_dollar": float,      # validated_total / max(spend, EPS)  (0.0 when spend == 0)
    #   "spend": float,                 # USD attributed to this investigation
    #   "rounds": int,                  # completed paid rounds (cost-bearing steps) so far
    #   "validated_total": int,         # validated beliefs attributed to this investigation so far
    #   "validated_since_round": int,   # 1-based round index of the LAST validated landing (0 = none ever)
    #   "stall_rounds": int,            # trailing paid rounds with zero validated landings
    #                                   #   (== rounds - validated_since_round; == rounds if none ever)
    #   "recommendation": str,          # 'continue' (productive) | 'reprioritize' (slowing) | 'pause' (dead_end)
    #   "high_stakes": bool,            # load-bearing / anchor-touching → human-confirm before any hard cut
    #   "applicable": bool,             # False (+ reason in basis) when rounds < MIN_ROUNDS → ABSTAIN
    #   "basis": str,                   # the measured numbers behind the verdict — never a model vibe
    # }
```

`investigation_id` is the investigation slug (`investigation.py:94`, `meta["id"] == meta["slug"]`). `MIN_ROUNDS`, `STALL_K`, and the `yield_per_dollar` collapse floor are the load-bearing constants set **from RQ-E54**, not imported. **Ponytail: one pure read function over tables that already exist — no telemetry pipeline, no per-round daemon.**

### Consumed (verbatim from PRD-00 §4)

- **FC-2** (Lane 2, `persona/inbox.py`): `inbox.file_handoff(kind:str, dossier:dict) -> handoff_id:str`, dossier schema `{decision_requested, why_unresolvable, disagreeing:[...], conflict_type:'temporal'|'semantic'|'misinformation'|'insufficient', cheapest_test:{...}, expected_updates:[...], uncertainty, authority_boundary}`. Used for the high-stakes `dead_end` human-confirm (`conflict_type='insufficient'`). **Import-guarded; degrades to a legible event + worklog line when absent.**
- **FC-4** (Lane 3, `persona/analysis/engine.py`): `engine.dependency_graph(topic) -> {nodes:[{claim_id, statement, load_bearing:float, ...}], edges:[...]}`. Used to score `high_stakes` from the investigation's question/pinned claims. **Import-guarded; degrades to the origin heuristic below.**
- **Existing lane-1 substrate (read-only):** `queue.investigation_steps(investigation_id)` (`queue.py:174-181`); the `cost` event stream via `events.log().since(...)` (`events.py:66-74`, rows carry `data.task_id`/`data.cost`/`data.task_type`, `supervisor.py:66-68`); `verified.entries()` (`verified.py:35`); `Investigation.list_all()` / `.meta` (`investigation.py:181-191`).

**CONTRACT CHANGE PROPOSAL — none to existing FCs.** FC-30 is a purely additive new read; the only cross-lane *render* interface is CCP-40a (§6), flagged for Lane 4 ack. No consumed signature changes.

---

## 3. Features

### F40.1 — Per-investigation spend ⋈ validated-yield round series (the measured substrate)

- **Problem & evidence.** Spend and yield exist but are never joined per investigation. Cost is attributed only at the task level: `supervisor.py:64-68` emits `log().emit("cost", ..., task_id=task.id, cost=..., task_type=task.type)` — no `investigation_id`, so there is no way to ask "how much has *this program* cost?" The budget is a single global daily counter (`budget.py:38-59`) that a rabbit-hole drains invisibly. Validated beliefs land globally too: the harvest step admits converged beliefs (`membrane.py:118-131`, `belief_update` event with `beliefs=len(beliefs)`) and the verified ledger records TESTED results (`verified.py:49-64`), neither tagged to the investigation that caused them. Meanwhile the investigation *does* own its step-tasks (`queue.investigation_steps` → `[{id, step_idx, type, status, result_ref}]`, `queue.py:174-181`), which carry `investigation_id`.
- **Design.**
  - Additive, in-lane, event-native spend attribution: add `investigation_id=task.investigation_id` (when non-`None`) to the existing `cost` emit at `supervisor.py:66`. No new table; the `cost` rows now self-identify their investigation.
  - `convergence._round_series(investigation_id) -> list[dict]`: from `events.log()` cost rows whose `data.investigation_id` matches (chronological), build one **round** per cost-bearing completed step: `[{round:int (1-based), task_id, task_type, at, spend_cum, validated_cum}]`. `spend_cum` = running sum of `data.cost`.
  - **Validated-landing attribution (measured, honest).** A round is credited with a validated landing when, within that round's step window, a validated belief actually landed via either sink: (a) a `belief_update` event from `membrane` showing a **positive delta** in converged-belief count, or (b) a `verified.entries()` row with `status=='verified'` whose `at` falls in the round's window. Rounds are ordered by their cost-event `at`; a landing between round *r*'s `at` and round *r+1*'s `at` is credited to round *r*. `validated_cum` is the running count. **This is a delta over real membrane/ledger state, never a model self-report.** The known imperfection — global sinks can't be attributed to a specific concurrent investigation with certainty — is bounded by (i) event-native spend attribution above, (ii) the abstain gate (F40.2), and (iii) the exact-attribution follow-up in §6-OQ2; and it does not affect RQ-E54, which validates the *detector logic* on clean labeled traces.
  - Pure read; opens no model; touches no writer. Fails empty/graceful (no cost rows ⇒ `[]`, never a crash), matching `scout`'s fail-open posture.
- **Epistemic guardrails.** The series is **measured telemetry, not a belief** — it never writes the KG, the self, or the queue. Spend is a real dollar sum from `cost` events; yield is a real delta over membrane admits + the TESTED ledger. No number here is a model estimate. Append-only sidecar (`convergence.jsonl`) records the trail but is never the source of truth (recomputed each call). The "no validated landing in a round" fact is neutral funnel data, never asserted as "the target is barren."
- **Required experiment.** Trivial — no experiment. This is a deterministic join over three existing tables (events ⋈ queue ⋈ ledger); correctness is structural, covered by the F40.1 round-trip check and exercised by F40.2/F40.4. `# ponytail: join rows, don't build a metrics service.`
- **Acceptance + ONE runnable check.** On a seeded temp persona: launch a 3-step stub investigation, emit two `cost` events tagged with its `investigation_id`, record one `verified` entry in-window ⇒ `_round_series` returns 2 rounds with monotone `spend_cum` and `validated_cum` crediting the landing to the correct round; an investigation with no cost rows returns `[]`. Check: `pytest persona/tests/test_convergence.py::test_round_series_attributes_spend_and_yield`.
- **Effort** M · **Deps** `queue.investigation_steps`, the `cost`/`belief_update` event stream, `verified.entries()`.

---

### F40.2 — `convergence_health` verdict: yield-per-dollar + stall-rounds, with abstain (FC-30)

- **Problem & evidence.** The system has no notion of an investigation *not converging*. `finalize()` reports `steps_done` (`investigation.py:261`) — how much ran, never whether it was *worth* running. The UI has a belief-trajectory verdict (`rising`/`stalling`/`collapsing`, `index.html:372,2068`) but that grades the *beliefs' momentum*, not the *researcher's own effort/spend* — a different question. The load-bearing, genuinely-uncertain judgement is: **a program whose spend is rising while zero new beliefs land is a dead-end; a program that lands beliefs slowly is a deep-dive to protect.** These look identical on a single round and only separate over a *window*. Research posture: this is the swarm-economics discipline PRD-00 §9 (FC-24) already applies to team sizing (yield-per-dollar from real cost-events × membrane-admit yield) — turned here on the *duration* of a single program.
- **Design.** `convergence_health(investigation_id, *, kg=None)` over `_round_series`:
  - **yield_per_dollar** = `validated_total / max(spend, EPS)`. **stall_rounds** = trailing run of rounds with zero validated landings = `rounds - validated_since_round` (or `rounds` if nothing ever landed). **validated_since_round** = the 1-based round index of the last landing (0 = none).
  - **Verdict (measured, 3-way):**
    - `applicable=False` (**abstain**) when `rounds < MIN_ROUNDS` — you cannot judge a program on 2 paid steps, exactly the "skipped ≠ passed" applicability discipline (`verifier.py`); verdict is reported but `recommendation='continue'` and no cut is ever proposed.
    - `dead_end` **only** when BOTH (i) `stall_rounds >= STALL_K` (a *sustained* zero-yield tail, not one quiet round) AND (ii) `yield_per_dollar` has *collapsed* — below the collapse floor AND strictly falling across the last window (spend still climbing, yield flat). This conjunction is what distinguishes a rabbit-hole from a slow deep-dive: a deep-dive that lands even one belief every few rounds keeps resetting `stall_rounds` below `STALL_K` and never trips.
    - `slowing` in the soft band (rising `stall_rounds`, yield falling but above the collapse floor) — a *watch* signal, `recommendation='reprioritize'`.
    - `productive` otherwise — `recommendation='continue'`.
  - **high_stakes** — `True` when the investigation is load-bearing/anchor-touching: (a) FC-4 `engine.dependency_graph` reports any resolved claim with `load_bearing` above the graph's fragile threshold (import-guarded), OR (b) origin heuristic — `meta.get("specialization")=='conflict-resolution'` or non-empty `meta.get("evidence_claim_ids")` (`investigation.py:158-161`), i.e. the program was opened from a flagged conflict and pins specific claims. When high-stakes cannot be determined and the engine is absent, default `high_stakes=True` for any conflict-origin investigation and `False` otherwise (conservative for cuts: never auto-cut a program we cannot vet).
  - **basis** is a plain-language digest of the actual numbers (`"spend $2.10 over 6 rounds · 0 validated in last 4 rounds · yield/$ 0.0 (was 0.9)"`) — the legible *why*, never an adjective.
  - `MIN_ROUNDS` / `STALL_K` / collapse-floor are set from RQ-E54 and cited in a `# see experiments/exp_dead_end_detector.py` comment at their definition.
- **Epistemic guardrails.** The verdict is a **measured function of real spend and real membrane/ledger deltas** — never a model vibe (`CLAUDE.md` "no fabricated confidence"). Abstention below `MIN_ROUNDS` is first-class. The `dead_end` conjunction is deliberately conservative so the correctness boundary — **never condemn a productive-but-slow deep-dive** — is protected by design, not just by tuning. `convergence_health` mutates nothing; a `dead_end` verdict is a *recommendation to a human/supervisor*, not a belief and not an action.
- **Required experiment.** **RQ-E54** (F40.4) — the load-bearing gate that sets `MIN_ROUNDS`/`STALL_K`/collapse-floor and proves the productive-slow / dead-end separation before any cut is autonomous.
- **Acceptance + ONE runnable check.** (1) A trace with rising spend and zero landings for `>= STALL_K` trailing rounds ⇒ `verdict=='dead_end'`, `recommendation=='pause'`. (2) A slow-but-yielding trace (one landing every `STALL_K-1` rounds) ⇒ `verdict != 'dead_end'` and is **never** recommended for pause. (3) `rounds < MIN_ROUNDS` ⇒ `applicable==False`, `recommendation=='continue'`. Check: `pytest persona/tests/test_convergence.py::test_verdict_dead_end_vs_slow_vs_abstain` on three synthetic round-series fixtures.
- **Effort** M · **Deps** F40.1; FC-4 (import-guarded, optional).

---

### F40.3 — Advisory reprioritize / pause hook + resumable queue hold

- **Problem & evidence.** The scheduler drives investigations but can only *open*, never *close*: `supervisor.py:119-135` opens a fresh investigation whenever `len(active_invs) < MAX_ACTIVE_INVESTIGATIONS` (=4, `config.py:74`) — a dead-end that never finalizes permanently occupies one of the four slots and keeps spending, because `launch()` enqueued its whole chain up front (`investigation.py:230-237`) and `lease()` will keep serving those steps (`queue.py:119-137`, no hold predicate). There is no seam to stop a program without deleting its work.
- **Design.**
  - **Resumable queue hold (in-lane, `queue.py`).** Additive column `held INTEGER NOT NULL DEFAULT 0` (migration mirrors `queue.py:99-102`); one predicate `AND t.held=0` in `lease()`'s inner `SELECT` (`queue.py:127-133`) so a held step is simply not leased; `set_investigation_hold(investigation_id, held: bool) -> int` sets `held` on that investigation's still-`pending` step-tasks and returns the count. A held task **stays `pending`** — no status lost, no work discarded; resume = `set_investigation_hold(id, False)` and the chain continues exactly where it stopped. In-flight leased steps drain naturally (never killed mid-task, mirroring the daemon's pause posture, `supervisor.py:51-52`).
  - **Advisory supervisor pass (in-lane, `supervisor.py` section 0).** For each active investigation, call `convergence.convergence_health(inv.id)`. On `verdict=='dead_end'`:
    - **Always (advisory, ungated):** emit one legible event `log().emit("thought", f"investigation '{q[:60]}' looks like a dead-end: {basis}", actor="self")` (`events.py:58`) and append the same to the investigation worklog (`investigation.py:198`). This surfaces autonomously — legibility first — and blocks nothing.
    - **Only when `ops_dir/rq_e54.passed` exists (gate present) AND `high_stakes==False`:** act. `recommendation=='reprioritize'` (`slowing`) → soft: leave running but stop it from blocking new work (do not open against its slot). `recommendation=='pause'` (`dead_end`) → `queue.set_investigation_hold(inv.id, True)` + `inv.meta["status"]="paused"` (+ a resumable `pause` stamp) so a slot frees for a fresh question and the spend stops. `paused` is excluded from `active_invs`, so the driver naturally opens a replacement.
    - **`high_stakes==True`:** **never auto-cut.** File an FC-2 handoff (`inbox.file_handoff(kind="convergence_review", dossier={decision_requested:"pause this load-bearing investigation?", why_unresolvable:"detector flags dead-end but the question is load-bearing", conflict_type:"insufficient", cheapest_test:{action:"human review of the convergence trail", cost_tier:"public_data"}, ...})`, import-guarded) and keep the program running until a human decides. Degrades to a legible event when the inbox is absent.
  - **Resume** is a human/API action (flip status back to `running`, `set_investigation_hold(id, False)`) — a paused investigation is a first-class, resumable state, never a deletion.
- **Epistemic guardrails.** **Advisory until the gate.** Until `ops_dir/rq_e54.passed`, the hook only *flags and surfaces* — it never holds a queue task or pauses a program (mirrors PRD-22 F22.3 / FC-13's `ops_dir/rq_e34.passed` posture). After the gate, it acts **only** on non-high-stakes `dead_end`s; every high-stakes cut requires human confirmation (the human-as-resolver division of labor, `CLAUDE.md` §7). Pause **caps effort, it deletes nothing** — steps stay `pending`, the folder and all documents remain, resume is one flag flip. Balanced autonomy: flags autonomously, acts only on the earned gate, never on a load-bearing program, never anchors, never mutates a belief.
- **Required experiment.** **RQ-E54** (F40.4) is the enforcement gate for this hook.
- **Acceptance + ONE runnable check.** (1) With `ops_dir/rq_e54.passed` **absent**, a `dead_end` investigation is **not** held and its steps still lease (advisory-only: an event is emitted). (2) With the gate present and `high_stakes==False`, `set_investigation_hold(id, True)` marks its pending steps `held=1` and `lease()` skips them while other work still leases; resume clears the hold and the steps lease again. (3) `high_stakes==True` ⇒ no hold; an FC-2 handoff is filed (or a fallback event when inbox absent). Check: `pytest persona/tests/test_convergence.py::test_hold_advisory_until_gate_and_resumable`.
- **Effort** M · **Deps** F40.2; PRD-01's `supervisor.py` edits (same lane, coordinate insertion); FC-2 (import-guarded).

---

### F40.4 — RQ-E54: dead-end detection precision without cutting slow-but-productive (the gate)

- **Problem & evidence.** The load-bearing, genuinely-uncertain claim: *the detector flags genuine dead-ends precisely AND does not cut productive-but-slow deep-dives.* This must clear a seeded ≥20-seed gate before quarantine/pause is allowed to act (`CLAUDE.md` §2). It is the same false-positive-is-the-boundary posture as RQ-E30/RQ-E36 (detection ≥ threshold AND a hard ceiling on false-cuts), applied to effort-judgement.
- **Required experiment — RQ-E54** (register in `docs/RESEARCH_QUALITY_PROGRAM.md`).
  - **Hypothesis.** On labeled investigation traces — some genuinely dead-end (spend rises, zero validated landings across a long tail), some slow-but-eventually-productive (spend rises, validated beliefs land sparsely, e.g. one every 4–6 rounds, with eventual payoff) — `convergence_health` flags the dead-ends at high precision while (almost) never flagging the slow-productive ones.
  - **Metric.** `dead_end` precision = P(trace is genuinely dead-end | verdict=='dead_end'); false-cut-on-productive = P(verdict=='dead_end' | trace is slow-but-productive). Both as mean ± 95% CI (bootstrap) over ≥20 seeds of trace generation (seeds vary landing cadence, spend-per-round noise, tail length, and query-seed order).
  - **Gate.** `dead_end` precision **≥ 0.80** AND false-cut-on-productive **95%-CI upper bound ≤ 0.05** → write `ops_dir/rq_e54.passed`, enabling F40.3 enforcement. Else the hook stays advisory-only and the reversal is logged in `results/FINDINGS.md`. `MIN_ROUNDS`/`STALL_K`/collapse-floor are chosen **from this experiment**, not imported, and cited at their definition.
  - **Sandbox.** `experiments/exp_dead_end_detector.py` (seeded, ≥20 trials): a synthetic-trace generator emits `(spend_series, validated_landing_series)` with a ground-truth label per trace; each is fed to the *real* `convergence_health` verdict core (via an in-memory round-series shim — deterministic, no model, no FalkorDB, matching the offline style of `exp_poisoning.py`). Report mean ± 95% CI to `results/rq_e54_dead_end_detector.json`; reproducible across `PYTHONHASHSEED`.
- **Epistemic guardrails.** Ground truth is the **generated label** (dead-end vs slow-productive), not a model opinion. The false-cut ceiling (≤ 0.05) is as load-bearing as the precision floor — condemning a productive deep-dive is the correctness boundary, so it is a near-hard zero. Thresholds are held-out, never self-reported; seeds fixed and saved.
- **Acceptance + ONE runnable check.** (1) The dead-end arm is flagged at precision ≥ 0.80; the slow-productive arm's false-cut CI-upper ≤ 0.05 across ≥20 seeds. (2) Reproducible across hash seeds. (3) Check: `python experiments/exp_dead_end_detector.py --seeds 20 --smoke` prints both rates + a boolean `gate_passed`; a fast `pytest persona/tests/test_convergence.py::test_e54_smoke` runs a 3-seed reduced version and asserts the fields + a clean separation.
- **Effort** M · **Deps** F40.2 (the verdict core the experiment scores).

---

## 4. Sequencing within the lane

1. **F40.1 (round series + cost-event tag)** — the measured substrate; land the one additive `investigation_id` on the `cost` emit and `_round_series` first. Everything joins on this. Ship + its round-trip test. Repo runnable (pure read, no behavior change).
2. **F40.2 (verdict)** — `convergence_health` over the series. Pure, testable on fixtures; advisory by construction. Repo runnable (read-only endpoint-able).
3. **F40.4 (RQ-E54)** — build the labeled-trace generator, run ≥20 seeds, register the gate. Blocks *enforcement* only; the verdict already computes advisory.
4. **F40.3 (hook + queue hold)** — the supervisor advisory pass + `set_investigation_hold`; ships flag-only immediately (M0: emit + worklog, no hold), flips to enforcing when F40.4 writes `ops_dir/rq_e54.passed`.
5. **CCP-40a render** — hand FC-30 to Lane 4 once the verdict is stable (unblocks the cost-vs-yield / dead-end badge; headless-functional meanwhile).

**M0 stub (first thing, all-lanes discipline):** land `convergence.convergence_health` returning a typed, `applicable=False` "insufficient rounds" stub + the FC-30 signature, and commit-in-place, so Lane 4 and RQ-E54 build against it from hour 1. Rationale: measure → judge → prove → act, so the repo is legible and correct at every checkpoint and never acts on an unproven verdict (Balanced autonomy).

---

## 5. Test & verification plan

| Test | Feature | Asserts |
|---|---|---|
| `test_round_series_attributes_spend_and_yield` | F40.1 | cost events ⋈ step task-ids → monotone `spend_cum`; a landing credits the correct round; no-cost ⇒ `[]` |
| `test_verdict_dead_end_vs_slow_vs_abstain` | F40.2 | dead-end trace ⇒ `dead_end`/`pause`; slow-yielding ⇒ never `dead_end`; `< MIN_ROUNDS` ⇒ `applicable==False`/`continue` |
| `test_high_stakes_never_auto_cut` | F40.2/F40.3 | conflict-origin / load-bearing investigation ⇒ `high_stakes==True`; hook files FC-2 handoff, never holds |
| `test_hold_advisory_until_gate_and_resumable` | F40.3 | gate absent ⇒ no hold (advisory event only); gate present + non-high-stakes ⇒ pending steps `held=1`, `lease()` skips them, other work still leases; resume clears hold |
| `test_e54_smoke` | F40.4 | 3-seed reduced fault-injection: dead-end arm detected, slow-productive arm clean |
| `exp_dead_end_detector.py --smoke` | F40.4 | the real ≥20-seed gate harness self-check (fields + CI present, `gate_passed` boolean) |

**Integration:** end-to-end on a temp `self_dir` — launch a stub investigation, drive N cost-bearing rounds with zero validated landings, assert `convergence_health` moves `productive → slowing → dead_end` and (gate present) the supervisor pass holds the queue steps; then record a `verified` entry mid-trace and assert `stall_rounds` resets and the verdict recovers — no mocks on the queue/ledger. **Browser smoke:** none in this lane (headless — the detector emits a `log().emit` event + exposes FC-30; the badge render is Lane 4's smoke under CCP-40a).

---

## 6. Open questions for the master/user

- **CCP-40a (FC-30 render) — blocks Lane 4 only, not this lane.** The convergence read is a new cross-lane interface; Lane 4 adds a read-only `GET /api/persona/{pid}/investigations/{slug}/convergence` (or a `convergence` field on the existing investigations/swarm surface) + a dead-end badge on the per-agent cost-vs-yield panel (PRD-00 §3 Lane-4). **Recommended default:** route to Lane 4, ack the FC-30 signature; the detector is fully headless-functional meanwhile (writes the trail, emits the event). **Confirm.**
- **OQ2 — validated-yield attribution exactness.** Global sinks (harvest admits, TESTED ledger) cannot be attributed to a specific *concurrent* investigation with certainty; F40.1 uses event-native spend + a time-windowed landing join, which is good enough for the advisory verdict and irrelevant to RQ-E54 (clean labeled traces). **Recommended default:** ship the time-windowed join now; file a follow-up to thread `investigation_id` through the `belief_update` emit (`membrane.py`, Lane 2) and the `verify`/`prove` ledger writes (`verified.record` `source=`, worker.py, Lane 1) for exact attribution — additive, cross-lane, non-blocking. **Confirm we defer the exact-attribution wiring.**
- **OQ3 — "round" granularity.** A round is defined as one completed **cost-bearing step** of the investigation. Alternatives: per-harvest-checkpoint, or wall-clock buckets. **Recommended default:** cost-bearing step (measured, discrete, maps 1:1 to spend). **Confirm** we don't want a finer clock (it would fragment the already-sparse per-investigation landing signal).
- **OQ4 — soft `reprioritize` mechanism.** `slowing` recommends `reprioritize`, but the queue leases by fixed `priority`+`created_at` with no per-task priority-update method (`queue.py:119-137`). **Recommended default:** implement `reprioritize` as "do not open a new investigation *against* this one's slot" (driver-side, cheap) rather than adding queue priority mutation; escalate to a real priority bump only if the deep-dive-vs-rabbit-hole distinction proves to need it. **Confirm** the driver-side soft signal is sufficient for v1.
