# PRD-32 — Pareto swarm-sizing controller

> **Owner lane:** 1 + 4 (Heterogeneous agent teams · Legibility/API) · **Status:** DRAFT-for-implementation (2026-07-13) · **Autonomy:** Balanced — the economics read + recommended team-size are always surfaced (legible, never acted on blind); the controller only *turns a knob* (sets reads/team-size per task-type away from the fixed default) once **RQ-E47** passes and `ops_dir/rq_e47.passed` exists. Until then it is advisory: it computes the frontier and the recommended N, logs *why*, and the daemon keeps running the fixed defaults. · **Depends-on:** the daemon per-task `"cost"` event (`daemon/supervisor.py:60-68`, already logged), `budget.spent_today()` attribution (`budget.py:38-40`), the append-only `ops_dir/gate_decisions.jsonl` membrane rows (PRD-00 §4 shared ledger; `gate:'membrane', decision:'admit'`), `events.log().since()` (`events.py:66-74`), and the RQ-E07a swarm-physics precedent (`config.py:60` comment — effective reading-team saturates ~14-15). Consumes FC-4 (`engine.value_queue` — optional, to attribute yield to a driving question); provides **FC-24**.

---

## 0. Summary + capability unlocked

The daemon spawns a **fixed** amount of swarm per unit of work and never checks whether that amount is buying anything. Three constants set the whole scale: `config.N_WORKERS = 8` (the worker pool, `config.py:62`), `config.GATHER_READS = 6` (papers an investigation's `gather` step reads inline, `config.py:73`, `worker.py:110`), and the hard-coded fan-out `reader.scout(interest, 20)` in `_scout` (`worker.py:91`). These were picked once, by a comment ("E07a: effective reading-team saturates ~14-15", `config.py:60`), and are the same for a cheap descriptive question and an expensive causal one. Meanwhile the system **already logs both halves of the economics it would need to do better**: every task emits a `"cost"` event with its `task_type` and `$` (`supervisor.py:64-68`), and every membrane admission is (per PRD-00 §4) an append-only `gate_decisions.jsonl` row. Nobody joins them. So the diminishing-returns curve — *readers spawned → validated beliefs earned → dollars* — is invisible, and the operating point (are we past the knee? starving a task-type that pays off?) is unknown.

This PRD builds the join and the controller. **FC-24 `swarm_economics()`** attributes real logged cost and real membrane-admit yield per task-type over a window and returns the **current operating point on the measured accuracy-vs-cost frontier** — never a fabricated yield number; every figure is summed from events on disk, and it returns `applicable=False` when the ledgers are too thin. **`recommend_size(task_type)`** reads that frontier and picks the smallest team whose *marginal* validated-belief-per-dollar is still above the diminishing-returns knee, capped by the E07a saturation ceiling, logging *why N was chosen*. Lane 4 renders the curve on the swarm floor so a human can watch the returns flatten.

**Capability unlocked:** Persona sizes its swarm per task on the frontier it has actually measured, and can *show* the diminishing-returns curve — "on `gather` tasks, readers 1→8 earn 0.42 validated beliefs/\$; 8→15 earn 0.06/\$ and flatten; we operate at 6, one below the knee." "Scale of reading, discipline of believing" gains a third axis: **economy of reading** — spend where the curve still pays.

---

## 1. File ownership (disjoint)

| File | New? | Owner | Note |
|---|---|---|---|
| `persona/daemon/sizing.py` | **New** | Lane 1 | The whole controller: `swarm_economics` (FC-24 read) + `recommend_size` (the sizing decision). Pure over the event log + `gate_decisions.jsonl`; no model, no network, no belief write. Per PRD-00 "new-file ownership rule" a new non-colliding file is owned by the creating PRD's lane. |
| `experiments/exp_rq_e47_pareto_sizing.py` | **New** | Lane 1 | RQ-E47 sandbox (frontier-sizing vs fixed-N on validated-belief-per-\$ in replay), ≥20 seeds. |
| `tests/test_sizing.py` | **New** | Lane 1 | Runnable check (economics attribution + recommend gating + monotone knee). |

**Boundary files (flagged; each is an additive within-lane edit, coordinated in the HANDOFF dispatch log — no parallel rewrite):**

- `persona/config.py` — **additive constants only** (Lane 1 append, same pattern as PRD-06's `OPENGWAS_JWT` / PRD-05's `SELF_FILES` sanctioned appends, PRD-00 §8): `SWARM_SATURATION_CAP = int(os.environ.get("PERSONA_SWARM_SATURATION_CAP", "15"))` (the E07a ~14-15 ceiling made a knob, `config.py:60` cites it) and `SIZING_WINDOW_HOURS = float(os.environ.get("PERSONA_SIZING_WINDOW_HOURS", "24"))`. No existing value changes.
- `persona/daemon/worker.py` — **ONE gated additive line each** in `_scout` (`worker.py:91`) and `_gather` (`worker.py:110`) that reads `sizing.recommend_size(...)["chosen"]` **only when `applied=True`** (i.e. `rq_e47.passed` present), else keeps the literal `20` / `config.GATHER_READS`. Lane 1 owns `worker.py`; this is a within-lane coordinated edit landed *after* `sizing.py`. Behaviour-neutral until RQ-E47 passes.
- `persona/api/app.py` — **new route only** (Lane 4, "new routes only" per PRD-00 §3): `GET /api/persona/{pid}/swarm/economics` passthrough to FC-24, exactly like the `engine/dependency` passthrough (`app.py:1405-1413`). Additive; touches no existing route.
- `persona/api/static/index.html` — **new surface only** (Lane 4): the diminishing-returns curve on the existing swarm view. Additive.

Nothing here is owned by Lane 2 or Lane 3; the read consumes their *outputs on disk* (`gate_decisions.jsonl`, optionally FC-4) but edits none of their files.

---

## 2. FCs provided / consumed + CCP

**Provides — FC-24 (new; Lane 1 provides, Lane 4 consumes).** The swarm-economics read + the sizing decision, in new `persona/daemon/sizing.py`:

```python
def swarm_economics(*, window_hours: float = None, task_type: str = None) -> dict:
    """FC-24 — the swarm-economics read. Joins the daemon's per-task 'cost' events (budget.py cost,
    supervisor.py:64-68) with membrane-admit yield (gate_decisions.jsonl 'membrane'/'admit' rows) over
    a trailing window, attributed per task_type. Returns the CURRENT operating point on the measured
    accuracy(yield)-vs-cost frontier. NEVER fabricates a yield: every count/dollar is summed from real
    logged events; applicable=False (with a reason) when the ledgers hold too few events to be honest.
    Returns:
      {window_hours: float,
       by_task_type: {task_type: {readers_spawned:int, tasks:int, validated_beliefs:int,
                                  dollars:float, yield_per_dollar:float|None}},
       operating_point: {task_type, team_size:int, marginal_yield_per_dollar:float|None,
                         saturating:bool, knee_team_size:int|None},
       frontier: [{team_size:int, cum_validated:int, cum_dollars:float, marginal_yield:float|None}],
       applicable:bool, reason:str}"""

def recommend_size(task_type: str, *, default: int, economics: dict = None,
                   parent_id=None) -> dict:
    """The sizing decision. From the MEASURED frontier (swarm_economics), pick the smallest team whose
    marginal validated-belief-per-$ is still above the diminishing-returns knee, capped by
    config.SWARM_SATURATION_CAP (RQ-E07a ~14-15). ADVISORY until ops_dir/rq_e47.passed exists: returns
    chosen==default, applied=False. Once the flag is present: applied=True and chosen may move. ALWAYS
    logs a 'sizing' event with WHY N was chosen (never a silent knob-turn). Returns:
      {task_type, chosen:int, default:int, applied:bool,
       basis:'frontier'|'coldstart'|'default', reason:str, saturation_cap:int}"""
```

*Rationale for a distinct FC (not folding into FC-4):* FC-4 is the intellectual-engine read (dependency graph + VoI queue, Lane 3). This is an *operational* read over the cost + gate ledgers (Lane 1's domain — it owns the scheduler and queue). It is a genuine Lane-1→Lane-4 interface, so it is proposed as **FC-24** and must be acked by the master + Lane 4 in the HANDOFF dispatch log before Lane 4 wires the surface. Until acked, Lane 4 renders against the fixture shape above (contract-first, exactly as the flagship renders FC-4 fixtures first).

**Consumes:**
- **The daemon `"cost"` event** (`supervisor.py:64-68`) — `data.cost`, `data.task_type`; read via `log().since()` (`events.py:66-74`), the same source `/spend` already reads (`app.py:159-164`). No change requested.
- **`ops_dir/gate_decisions.jsonl`** (PRD-00 §4 shared append-only ledger) — the membrane-admit yield denominator: rows with `gate:'membrane', decision:'admit'` counted in the window. **Read-only; never appends** (Lane 1 already appends `relevance`/`redteam` rows there; this reads all lanes' rows, honoring the "never edit another lane's rows" rule). Degrades gracefully (`applicable=False, reason="no membrane ledger"`) when absent.
- **FC-4 `engine.value_queue`** — *optional*, import-guarded. Only used to label which driving question a task-type's yield served; the economics is complete without it. Absent → the label is omitted, nothing else changes.

**CCP (Contract Change Proposals):**
- **CCP-32a (→ Lane 1, within-lane):** the two additive `config.py` constants above (`SWARM_SATURATION_CAP`, `SIZING_WINDOW_HOURS`). Within-file append; coordinate in HANDOFF like the other sanctioned config appends.
- **No change to any existing FC.** The `worker.py` gated line does not change FC-1 (task types unchanged); the membrane ledger schema is unchanged (read-only consume).

---

## 3. Features

### F32.1 — `swarm_economics`: join cost-events × membrane-admit yield (FC-24 read)

**Problem & evidence.**
- The daemon already attributes cost per task: `before = budget.spent_today()` → `cost = budget.spent_today() - before` → `log().emit("cost", …, cost=…, task_type=task.type)` (`supervisor.py:60-68`). `/spend` surfaces the *last 12* raw cost events (`app.py:159-164`) but never aggregates by type or divides by anything — it answers "how much did I spend," not "what did the spend buy."
- The yield side exists too: a membrane admission is the moment a candidate becomes a believed thing, and (PRD-00 §4) each admit is a `gate_decisions.jsonl` row. `membrane.harvest` also emits a `"…converged belief(s) (≥K independent labs)…"` event with `beliefs=N` (`membrane.py:118-129`). Neither is ever joined to cost.
- **The two ledgers are stored side-by-side and never reconciled into a yield-per-dollar** — the exact gap PRD-20 flagged for confidence (stored vs justified), here for spend (spent vs earned).
- Research: compute-aware multi-agent scaling / **Pareto-optimal test-time scaling** (arXiv:2605.01566, *cited as given in the task brief — per `CLAUDE.md` §1 the id is treated as unverified until fetched; the mechanism it names, "size the agent team on the measured accuracy-vs-compute frontier rather than a fixed count," is what this PRD grounds in Persona's own logged events, not in an imported constant*). The precedent that the reading-team **saturates** (a real diminishing-returns curve exists to sit on) is in-repo: `config.py:60` — "E07a: effective reading-team saturates ~14-15."

**Design.** New `persona/daemon/sizing.py`, pure (no model, no network, no write):
- **Cost side.** `log().since(0, limit=…)` (or a bounded tail) → filter `type=="cost"` and `ts` within `window_hours` → group by `data.task_type` → `dollars[type]`, `tasks[type]`. `readers_spawned` for reading types (`scout`/`observe`/`gather`/`bulk`) is derived from the same events plus the `"spawn"` events those handlers emit (`worker.py:94`, `_scout` logs `n=len(works)`; `_gather` logs `n=read`) — i.e. the actual reader count, not an assumption.
- **Yield side.** Count `gate_decisions.jsonl` rows with `gate=='membrane', decision=='admit'` whose `at` is in the window → `validated_beliefs` (total, and — when a row carries a task/interest tag — attributed per type; otherwise held as an unattributed pool surfaced honestly, never silently split).
- **Frontier.** Bucket a reading task-type's tasks by their *effective team size* (readers spawned that task — which already **varies naturally**: `_gather` breaks early on `budget.can_read()`, `worker.py:113`, so identical steps log different `n`). For each bucket compute cumulative validated / cumulative dollars and the **marginal** yield-per-\$ between adjacent buckets → the diminishing-returns curve. `operating_point` = the bucket the current default sits in; `knee_team_size` = the largest team where marginal yield-per-\$ ≥ a fraction of the first bucket's (the flatten point); `saturating=True` once marginal < that fraction or `team_size ≥ SWARM_SATURATION_CAP`.
- **Applicability gate (explicit, skipped ≠ passed — PRD-00 §2).** `applicable=False` with a reason when: no cost events in window (`"no cost events"`), no membrane ledger (`"no membrane ledger"`), or `< MIN_TASKS` (e.g. 20) tasks for the requested type (`"insufficient tasks: {n}<20"`). A thin frontier is *reported as thin*, never smoothed into a confident curve.

**Epistemic guardrails.**
- **Never fabricates a yield number.** Every count and dollar is summed from real events on disk; `yield_per_dollar` is `None` (not 0, not a guess) when either side is empty. Unattributable admits are surfaced as an explicit pool, never apportioned by assumption.
- **Applicability is explicit** — thin ledgers → `applicable=False` + reason, distinct from "curve is flat."
- **Read-only.** No belief write, no ledger append, no model call — it cannot itself change the numbers it reports.

**Required experiment.** **Trivial** for F32.1 alone — deterministic aggregation over logged events; the *sizing decision* it feeds (F32.2) is what carries RQ-E47. Correctness pinned by `test_sizing.py::test_economics_attribution` (synthetic cost + admit events → exact per-type dollars, validated counts, and yield-per-\$; empty ledger → `applicable=False`).

**Acceptance + one runnable check.** Given 3 `gather` cost events ($0.10 each) and 6 membrane-admit rows in-window → `by_task_type["gather"] == {tasks:3, dollars:0.30, validated_beliefs:6, yield_per_dollar:20.0, …}`; empty log → `applicable==False, reason=="no cost events"`. **Check:** `python -m persona.daemon.sizing` (its `demo()` asserts the above on a temp ledger) **and** `tests/test_sizing.py::test_economics_attribution`. **Effort.** M. **Deps.** the `"cost"` event (exists), `gate_decisions.jsonl` (exists).

---

### F32.2 — `recommend_size`: pick team-size on the measured frontier (RQ-E47-gated)

**Problem & evidence.** The scale knobs are fixed and untyped: `_scout` fans out exactly `20` (`worker.py:91`), `_gather` reads exactly `config.GATHER_READS = 6` (`worker.py:110`), for every question regardless of what the frontier says that type earns. If `gather`'s curve knees at 10, we under-read; if it saturates at 4, we burn budget past the knee. Nothing chooses.

**Design.** `recommend_size(task_type, *, default, economics=None)` in `sizing.py`:
- Pull the type's `frontier` from `swarm_economics` (or the passed `economics`). Walk buckets ascending; the recommendation is the **smallest team whose marginal yield-per-\$ ≥ `KNEE_FRACTION × first-bucket marginal`** (the diminishing-returns knee), then `min(chosen, config.SWARM_SATURATION_CAP)` (the E07a ceiling — never recommend past the physics). `# see config.py:60 (E07a) — effective team saturates ~14-15; the cap is that ceiling made a knob.`
- **Gating (mirrors FC-4/RQ-E17 and PRD-20/RQ-E30 advisory-until-gate):** if `ops_dir/rq_e47.passed` is absent → `chosen=default, applied=False, basis='default'` — the daemon keeps the fixed number. Present → `applied=True`, `chosen` may move, `basis='frontier'`. Thin economics (`applicable=False`) → `chosen=default, basis='coldstart'` regardless of the flag (never size off a curve we don't have).
- **Always logs** a `"sizing"` event: `log().emit("sizing", f"{task_type}: {chosen} readers (was {default}) — {reason}", …)` so the choice is legible in the stream. `reason` names the marginal at the chosen point and the knee ("marginal 0.31/\$ ≥ knee 0.21/\$ at 8; saturates at 12").

**Epistemic guardrails.**
- **Data-driven + logged (task requirement).** N comes from the measured frontier, and the *why* is emitted every time — no silent sizing.
- **Never fabricates.** Coldstart (thin data) → falls back to the fixed default and says so; it does not invent a curve to justify a number.
- **Bounded by earned physics** — the cap is the E07a saturation ceiling, not an arbitrary max.
- **Balanced autonomy.** The knob only actually moves after RQ-E47 passes; before that it is pure advice a human reads on the floor.

**Required experiment — RQ-E47 (new; PRE-ASSIGNED; registry currently ends at E46).**
- **Hypothesis:** frontier-based sizing (`recommend_size` on the measured curve) yields **more validated beliefs per dollar** than the fixed-N default, in replay over Persona's own logged cost + membrane-admit events.
- **Oracle (real logged events only):** replay the trailing `gate_decisions.jsonl` admits + `"cost"` events; for each policy (fixed-N vs frontier-sized) compute realized `validated_beliefs / dollars` on held-out windows. Team-size variance to build the frontier comes from the **natural** spread already in the logs (budget backpressure cuts `_gather` short → different effective `n` per task, `worker.py:113`); when a window lacks ≥2 distinct team sizes, that seed is `insufficient` (reported, not fabricated).
- **Metric:** yield-per-\$ (frontier-sized) − yield-per-\$ (fixed-N), bootstrap 95% CI, over **≥20 seeded** resamples of the window split.
- **Gate:** difference 95%-CI lower bound **> 0** (frontier beats fixed-N), ≥20 seeds; else **no `rq_e47.passed` flag** and the controller stays advisory (`applied=False`) indefinitely — surfaced, logged, never turning the knob. Results → `/results/FINDINGS.md`; script → `experiments/exp_rq_e47_pareto_sizing.py`; cited in a `sizing.py` comment.
- Register in `docs/RESEARCH_QUALITY_PROGRAM.md`: `RQ-E47 | Lane 1 | Frontier-based swarm-sizing beats fixed-N on validated-belief-per-$ in replay | diff 95%-CI LB >0, ≥20 seeds, logged cost+membrane-admit oracle`.

**Acceptance + one runnable check.** With a frontier where `gather` marginal yield-per-\$ knees at team 8 and `rq_e47.passed` present → `recommend_size("gather", default=6)` returns `chosen==8, applied==True, basis=='frontier'` and emits one `"sizing"` event. Without the flag → `chosen==6, applied==False`. Thin data → `basis=='coldstart', chosen==6`. **Check:** `tests/test_sizing.py::test_recommend_gated_and_knee`. **Effort.** M (one pure function + one experiment). **Deps.** F32.1; `config.SWARM_SATURATION_CAP`.

---

### F32.3 — Lane 4: the diminishing-returns curve on the swarm floor (FC-24 consumer)

**Problem & evidence.** The swarm view (`app.py:191-206`, `/swarm`) shows *what* each worker is doing and an honest in-flight count, but not *whether the reading is paying off*. "Readers spawned vs validated beliefs earned vs \$" — the diminishing-returns curve the task asks to make inspectable — has no surface.

**Design.**
- **Route (Lane 4, new):** `GET /api/persona/{pid}/swarm/economics` — passthrough to FC-24, identical shape to the `engine/dependency` passthrough (`app.py:1405-1413`): `try: from ..daemon.sizing import swarm_economics; return swarm_economics()` / `except: return {"applicable": False, "by_task_type": {}, "frontier": []}`.
- **Surface (Lane 4, new, additive on the swarm view):** a small panel — per reading task-type, three tracked quantities (readers spawned · validated beliefs earned · \$), and the **marginal yield-per-\$ curve** across team sizes with the current operating point marked and the knee/saturation flagged. When `applicable=False`, render the reason ("insufficient tasks — the curve needs ~20 runs") exactly as the flagship renders FC-4's `available:false` — *insufficient-data honesty first*, never an empty axis pretending to be flat.
- The recommended-N (from `recommend_size`, `applied` or advisory) shows beside the operating point so a human sees "running 6; frontier says 8" — the legible sizing decision.

**Epistemic guardrails.**
- **Honest uncertainty (PRD-00 §2, CLAUDE.md §5):** thin data → the reason, not a fabricated curve. The advisory-vs-applied state of the recommendation is shown (a dashed "advisory" marker until RQ-E47 passes), so a viewer never mistakes advice for an enacted change.
- **No client-invented metric.** The curve renders server-derived numbers verbatim; the front end computes nothing (`CLAUDE.md` non-negotiable: server derives every scientific status).

**Required experiment.** **Trivial** (a render of a server read). Proven by the Lane-4 smoke: `PERSONA_WORKERS=0` browser load of the swarm view with a seeded `gate_decisions.jsonl` + cost events shows the curve; empty persona shows the insufficient-data reason.

**Acceptance + one runnable check.** `GET /swarm/economics` returns the FC-24 shape; the panel renders the three quantities + curve for a seeded persona and the reason for an empty one. **Check:** `tests/test_sizing.py::test_economics_route_shape` (route returns FC-24 keys; empty persona → `applicable==False`). **Effort.** S. **Deps.** F32.1 (FC-24 ack); the existing swarm view.

---

## 4. Sequencing

1. **M0 (Lane 1):** land `persona/daemon/sizing.py` with typed empty/fixture returns for `swarm_economics` + `recommend_size` and the `demo()` self-check, and commit-in-place so Lane 4 can build the panel against the FC-24 shape from hour 1. Add the two `config.py` constants (CCP-32a).
2. **F32.1** — real cost×yield join over the event log + `gate_decisions.jsonl`. Self-contained; needs only ledgers that already exist.
3. **F32.2** — `recommend_size` + `experiments/exp_rq_e47_pareto_sizing.py`; register RQ-E47 `open` in `docs/RESEARCH_QUALITY_PROGRAM.md`. Reads only real on-disk events → reports `insufficient`/advisory until the gate is met. **No `rq_e47.passed` flag until the gate passes.**
4. **F32.3 (Lane 4)** — the `/swarm/economics` route + curve panel, against the FC-24 fixture first, wired to the real read once F32.1 lands and FC-24 is acked.
5. **Knob-turn wiring (Lane 1, last, within-lane coordinated):** the ONE gated additive line in `_scout`/`_gather` that consumes `recommend_size(...)["chosen"]` only when `applied=True`. Behaviour-neutral until RQ-E47 passes; landed after F32.2 and the experiment.

Nothing blocks Lane 2/3 (their outputs are consumed read-only). Lane 4's only dependency is the FC-24 ack + shape, available at M0.

---

## 5. Test plan

- **`tests/test_sizing.py`** (new, Lane 1):
  - `test_economics_attribution` — synthetic `"cost"` events + membrane-admit rows → exact per-type dollars / validated counts / `yield_per_dollar`; empty log → `applicable==False` with the right reason; unattributable admits surfaced as a pool, not silently split.
  - `test_frontier_marginal_and_knee` — buckets with a real diminishing return → `frontier` marginal yields are non-increasing across the knee; `operating_point.saturating` flips True past `SWARM_SATURATION_CAP`.
  - `test_recommend_gated_and_knee` — knee at team 8: with `rq_e47.passed` → `chosen==8, applied==True, basis=='frontier'` + one `"sizing"` event emitted; without the flag → `chosen==default, applied==False`; thin data → `basis=='coldstart'`, default returned.
  - `test_recommend_capped_at_saturation` — a frontier that keeps paying past 15 → `chosen == SWARM_SATURATION_CAP` (never recommends past the E07a ceiling).
  - `test_economics_route_shape` (Lane 4) — `GET /swarm/economics` returns FC-24 keys; empty persona → `applicable==False`.
- **`experiments/exp_rq_e47_pareto_sizing.py`** — RQ-E47: replay logged cost + membrane-admit events, build the frontier from natural team-size variance, compare frontier-sized vs fixed-N yield-per-\$ over ≥20 seeded window splits; assert the gate (diff 95%-CI LB >0) or emit `insufficient`. Writes `/results` + a one-line note (a reversal if fixed-N wins — logged per CLAUDE.md §2).
- **No regressions:** `/spend` and `/swarm` unchanged (FC-24 is a new route; `sizing.py` only *reads* the events those already emit). `worker.py` behaviour-neutral until `rq_e47.passed` exists — a run of `test_investigation`/`test_worker` (if present) passes with the gated line off.

---

## 6. Open questions

- **Q1 (frontier bootstrapping — the one load-bearing choice).** The frontier needs ≥2 distinct effective team sizes per type to have a curve. Today that variance is *incidental* (budget backpressure truncates `_gather`, `worker.py:113`). Is incidental variance enough, or does the controller need a deliberate **ε-exploration** schedule (occasionally read N±k to probe the curve)? Spec'd lazy: **use incidental variance only**; if a type never varies, `swarm_economics` reports `applicable=False` and the controller stays coldstart — honest, never a fabricated curve. ε-exploration is a deferred, RQ-E47-gated add (it *spends to learn*, so it must earn its place empirically before shipping). Reversible; does not block other lanes.
- **Q2 (yield attribution granularity).** A membrane admit converges from *many* reads across *many* tasks (`≥K independent labs`, `membrane.py`), so per-task yield attribution is inherently fuzzy. Spec'd at **task-type × window** granularity (the honest resolution the ledgers support), with unattributable admits held as an explicit pool. Finer (per-investigation) attribution needs the admit row to carry a driving-question/investigation tag — a Lane-2 ledger-write concern, out of scope here; flagged for a future CCP if RQ-E47 shows type-level is too coarse.
- **Q3 (which knob the controller actually turns).** Primary lever spec'd as **readers-per-reading-task** (`_scout` fan-out / `_gather` reads) — the cleanest map to the accuracy-vs-cost frontier. `config.N_WORKERS` (pool concurrency) is deliberately **not** sized here: it is governed by budget + rate-limits, not by per-task accuracy (`config.py:60-62`), so sizing it would be a category error. Investigation *team fan-out* (branch count, `investigation._branch_plan`) is a candidate second lever, deferred until the reading-team lever validates. Not blocking.
- **Q4 (FC-24 ack).** FC-24 is a new Lane-1→Lane-4 read; it **blocks Lane 4's curve panel only**, and needs master + Lane-4 ack in the HANDOFF dispatch log. Until acked, Lane 4 renders the fixture shape in §2 (contract-first). Does not block Lane 1's F32.1/F32.2.
- **Q5 (arXiv:2605.01566 verification).** The task brief cites this id for compute-aware multi-agent scaling; per `CLAUDE.md` §1 it is treated as **unverified** until fetched. The PRD does not import any constant from it — the frontier is measured in-repo — so the design stands regardless of whether the id resolves; verify the citation before it appears in any compiled write-up.
```
