# PRD-42 — Prospective forecasting mode (predict-then-reveal on the live front)

> **Owner lane:** 1+4 · **Status:** DRAFT-for-implementation (2026-07-13) · **Autonomy:** Balanced — a forecast is a **sealed, dated, read-only prior**; grading is deterministic arithmetic over **real newly-arrived literature** (never a model self-grade); the scoreboard is **advisory** until RQ-E56 clears its baseline; the mode **never mutates a belief, anchor, or dispatch.** · **Depends-on:** **trajectory** (`analysis/trajectory.py::trajectory` — LIVE, PRD-03 F3.4; the "is the front moving?" gate + realized-direction axis), **FC-27** (`subscriptions.watch_pass` / front-move detection, PRD-35 — SPECCED-not-built → consumed import-guarded), **FC-17** (`memory/predictions.py` prediction ledger, PRD-24 — SPECCED-not-built → consumed import-guarded), the `conflict_reviews.py` hash-chain primitives (Lane 2, imported read-only — the same reuse PRD-24 makes), and how a topic's claims arrive over time (`ingest/sources.py` → KG `valid_from`, read via `analysis/trajectory.py::_fetch`).
>
> Backlog: **#520**. New contract: **FC-32**. Experiment: **RQ-E56**. Read PRD-00 §2 (epistemic discipline), §3 (file-ownership), §4 (FC registry), §6 (RQ registry), §8 (reconciliation governs), §9 (FC-17 / FC-27) before coding. **Where this body disagrees with §4/§6, §4/§6 win.**

---

## 0. Summary + capability unlocked

Persona today is **retrospective**. It reconstructs how an argument *has* moved (`trajectory.trajectory` — velocity / direction / settling, `analysis/trajectory.py:90`), scores verdicts it *already made* (FC-17 prediction ledger, on Persona's **own** hypotheses), and re-adjudicates when new evidence lands. What it has never done is **commit, in public and in advance, to what the *external literature* will find next — then let reality grade it.**

This PRD adds a **predict-then-reveal** loop on a live-moving front. When a topic's trajectory is genuinely **moving** (`signal.state == "moving"`, `trajectory.py:61`) — i.e. the argument is unsettled and the next results are not a foregone conclusion — Persona may **seal an immutable, dated forecast**: *"on (topic, statement), the next results will report effect direction D, with probability p, within H days."* The prior is hash-chained and de-duplicated at flag-time, so it **cannot be edited or re-issued after the answer arrives** (no goalpost-moving). When qualifying new claims land (KG claims whose `valid_from` post-dates the seal, `trajectory.py:79-87`), an **auto-grader** compares the sealed direction against the **realized** direction of that real arriving evidence — pure arithmetic, no model self-grade — and appends an immutable grade row. A running **forward-looking scoreboard** (Brier + calibration + hit list) accumulates a *public, out-of-sample track record.*

**Capability unlocked:** Persona stops only explaining the past and starts **putting a dated stake in the ground about the future of a field, then keeping honest score against it** — foresight, not retrieval. A PI can ask *"of the moving fronts where Persona called the next result ≥70% likely to be positive, how often was it right — out of sample?"* and get a number the data structure makes impossible to fake.

**Distinct from its neighbours (no overlap):**
- **≠ #67 (retrospective foresight-backtest):** that re-runs history from a past cutoff to *estimate* foresight offline; this seals a *live, dated* forecast about literature that does not yet exist and grades it forward. (RQ-E56 *uses* the #67-style frozen-cutoff replay only as its **experiment harness**, not as the product surface.)
- **≠ FC-17 (prediction ledger):** FC-17 scores Persona's own hypotheses/contradictions resolving via its *own* verified-ledger + human adjudication. FC-32 forecasts the **external literature's** next move, graded by **arriving papers**. FC-32 mirrors FC-17's *immutable-prior discipline* (and Lane 4 renders the two scoreboards side by side) but scores a different thing.

---

## 1. File ownership (disjoint)

| File | New? | Lane | Role |
|---|---|---|---|
| `persona/forecast.py` | **new** | 1 (new-file rule, PRD-00 §83) | FC-32 provider: sealed forecast store (`open_forecast`/`forecasts`/`open_forecasts`/`get`), `grade`, `sync_grades`, `scoreboard`, `verify_forecasts` — hash-chained immutable ledger `ops_dir/forecasts.jsonl` |
| `persona/daemon/worker.py` | edit (**append-only** registry) | shared | one `@handler("forecast_grade")` appended **after** the last existing handler (never re-order; mirrors the `revisit`/`front_watch` handler pattern, `worker.py:150`) |
| `persona/daemon/supervisor.py` | edit (additive tick) | 1 | one scheduler tick enqueuing `forecast_grade` when a forecast is due, inside the `SELF_INTERVAL_S` block (`supervisor.py:144`; offline/$0, no budget gate) |
| `persona/api/app.py` | edit (**NEW routes only**) | 4 | `GET/POST …/forecasts`, `GET …/forecasts/scoreboard`. Do not touch existing route bodies. |
| `persona/api/static/index.html` | edit (**NEW surface/JS only**) | 4 | `surf-forecasts` + `openForecasts()`: the forward-looking scoreboard + open-forecast (sealed-prior) list. No client-invented metric. |
| `experiments/exp_prospective_forecast.py` | **new** | (experiments) | RQ-E56 out-of-sample foresight harness (frozen-cutoff replay, ≥20 seeds) |
| `tests/test_forecast.py` | **new** | (tests) | runnable acceptance checks |

**Boundary files another lane touches — decoupled by contract, NOT edited here:**
- `persona/analysis/trajectory.py` (Lane 3, **LIVE**) — **imported read-only** (`trajectory`). Supplies the "front is moving" open-gate (`signal.state`) and the realized-direction axis (arriving claims' `effect_sign`/`valid_from`). No edit.
- `persona/subscriptions.py` (Lane 1, **FC-27**, unbuilt) — **imported read-only, import-guarded** (`watch_pass`/front-move signal) as the *preferred* auto-open trigger when present; degrades to trajectory-only. No edit.
- `persona/memory/predictions.py` (Lane 2, **FC-17**, unbuilt) — **imported read-only, import-guarded**; reuse its Brier/immutability discipline; Lane 4 renders FC-32's scoreboard beside FC-17's panel. No edit.
- `persona/conflict_reviews.py` (Lane 2) — **imported read-only** for the shared hash-chain primitives (`_walk_chain`, `_record_sha256`, `_canonical_json`, `_append_line`, `_file_lock`, `LedgerIntegrityError`; documented "Shared by every append-only hash-chained ledger"). Same reuse PRD-24 makes; no edit.
- `persona/memory/kg.py` (Lane 2) — **read-only** query for arriving claims (`valid_from > sealed_at`, `effect_sign`) at grade time, reusing the `trajectory._fetch` access pattern (`trajectory.py:73-87`). No edit.
- `persona/inbox.py` (Lane 2, FC-2), `persona/api/app.py` route helpers `context.use`/`_p` (`app.py:84`), `events.log().emit` (`events.py:58`/`:85`) — read-only reuse.

Everything this PRD *edits* is Lane 1 (`forecast.py`, `supervisor.py`) or Lane 4 (`app.py`, `index.html`) or the shared append-only `worker.py` registry — no cross-lane body edit.

---

## 2. FCs provided / consumed

### PROVIDES — FC-32 (Lane 1), new `persona/forecast.py`

```python
# Direction of the effect the NEXT results on (topic, statement) will report.
DIRECTIONS = {"+", "-", "0"}   # "0" = no/null direction (a real, forecastable outcome)

class DuplicateForecastError(ValueError): ...   # (topic,statement) already forecast — no re-issue, no goalpost-moving
class AlreadyGradedError(ValueError): ...        # a second grade for the same forecast id
class UnknownForecastError(ValueError): ...      # grade()/get() on an unsealed id

def open_forecast(
    topic: str, statement: str, *, predicted_direction: str, horizon_days: float,
    basis: str, confidence: float = 0.6, ops_dir=None, kg=None, now=None,
) -> dict:
    """Seal an IMMUTABLE, dated, forward-looking prior about what the NEXT results on
    (topic, statement) will find — BEFORE that evidence exists.
      predicted_direction ∈ DIRECTIONS (sign of the effect the arriving literature will report).
      confidence          = P(predicted_direction is realized) in [0,1] — the number Brier/
                            calibration score (a bare direction cannot be calibrated; see §6 O-1).
      horizon_days        = window within which the 'next results' are expected; sets resolve_after.
      basis               = provenance of the call: 'trajectory-momentum'|'mechanism'|'human'|... .
    ABSTAIN GATE: if the front is NOT actually moving (trajectory.trajectory(kg,topic)['signal']
    ['state'] != 'moving', or FC-27 reports no front-move), returns {'abstained': True, 'reason':
    'front_settled', ...} and seals NOTHING — no forecast on a settled front.
    Otherwise appends ONE kind:'forecast' row to the hash-chained ops_dir/forecasts.jsonl and returns
    {id, sealed_at, topic, statement, predicted_direction, confidence, horizon_days, resolve_after,
     basis, provenance:'INFERRED', status:'open'}. Raises DuplicateForecastError if (topic,statement)
    was already sealed. Never mutates a belief/KG. `now`/`kg` injectable for deterministic tests."""

def grade(id: str, *, arriving_evidence: list[dict] | None = None,
          ops_dir=None, kg=None, now=None) -> dict:
    """Grade one sealed forecast against REAL newly-arrived evidence — NEVER a model self-grade.
    arriving_evidence = claims/results with valid_from > sealed_at touching (topic,statement), each
    {claim_id, effect_sign, confidence, valid_from, independent_labs}; if None, pulled read-only from
    the KG (the trajectory._fetch pattern, valid_from-filtered). realized_direction = sign of the
    confidence×independence-weighted aggregate of arriving effect_signs ('0' if |aggregate| below the
    RQ-E56-tuned null band). correct = (realized_direction == predicted_direction); y = 1.0 if correct
    else 0.0; brier = (confidence - y)**2. GRADES ONLY when now >= resolve_after AND >= 1 qualifying
    result landed — else returns {'graded': False, 'reason':'horizon_not_elapsed'|'no_evidence_yet'}
    and stays open. Appends ONE immutable kind:'grade' row (never edits the forecast row). Returns
    {id, graded:True, outcome, realized_direction, correct, p, y, brier, n_evidence, resolved_at,
     resolved_by:'literature:<slugs>', provenance:'READ'}. Raises AlreadyGradedError on re-grade."""

def sync_grades(*, ops_dir=None, kg=None, now=None) -> dict:
    """Auto-grade pass: for every open forecast whose horizon has elapsed, pull arriving evidence
    and grade() once. Idempotent. Returns {graded:int, still_open:int, skipped:int}."""

def forecasts(*, ops_dir=None, status: str | None = None) -> list[dict]:
    """All sealed forecasts (+ their grade if any), chronological. status filters open|graded."""

def open_forecasts(*, ops_dir=None) -> list[dict]:
    """Sealed, not-yet-graded forecasts (the outstanding public commitments)."""

def get(id: str, *, ops_dir=None) -> dict:            # one forecast (+grade); UnknownForecastError if absent
def verify_forecasts(*, ops_dir=None) -> dict:        # {ok, errors, records, record_count, latest_sha256}

def scoreboard(*, ops_dir=None, window=None) -> dict:
    """Forward-looking public track record over GRADED forecasts. window = optional (days|N) recency.
    Returns {n, resolved, open, brier, calibration:[{bin, p_mean, hit_rate, n}], hits:int, misses:int,
     by_direction:{'+':{n,brier}, '-':{...}, '0':{...}}, baseline_cleared:bool, window}.
     brier = mean((p-y)**2). calibration reuses FC-17/PRD-15 reliability() import-guarded, else inline
     equal-width bins. baseline_cleared echoes ops_dir/rq_e56.passed (advisory gate, §3 F42.2).
     MISSES ARE LISTED — a wrong forecast is surfaced exactly as prominently as a right one."""
```

- **Forecast row** (`kind:"forecast"`): `{kind, id, topic, statement, predicted_direction, confidence, horizon_days, resolve_after, basis, sealed_at, provenance:"INFERRED", schema_version, prev_sha256, record_id}`. `id = sha256(topic|statement)[:16]` (content-hash — the natural de-dup key; a second seal of the same pair collides → `DuplicateForecastError`).
- **Grade row** (`kind:"grade"`): `{kind, id, outcome, realized_direction, correct, p, y, brier, n_evidence, evidence_claim_ids, resolved_at, resolved_by, provenance:"READ", schema_version, prev_sha256, record_id}`.
- **Task type (shared append-only registry — no CCP, like the FC-19/FC-27 handlers):** queue task type `"forecast_grade"`.

### CONSUMES (verbatim, no change)

- **trajectory** (LIVE) — `trajectory.trajectory(kg, topic) -> {topic, entities, series:[{claim_id, confidence, valid_from}], signal:{state:'settled'|'moving'|'insufficient', velocity, recent_velocity, direction:'rising'|'falling'|'flat', net_recent, n_points}}` (`analysis/trajectory.py:90`). `signal.state == 'moving'` **is** the abstain gate; `_fetch` (`:73-87`) is the read pattern for arriving claims (`valid_from`, `effect_sign`). *(Note: the LIVE export is `trajectory`, not the `topic_trajectory` some sibling PRDs assume — ground on the real name.)*
- **FC-27** (unbuilt → import-guarded) — `subscriptions.watch_pass(...)`/front-move detection (PRD-35). When present, a genuine front-move is the *preferred* signal that a front is live enough to forecast; absent, fall back to `trajectory.signal.state`.
- **FC-17** (unbuilt → import-guarded) — `predictions.brier(...)` / immutable-prior discipline (PRD-24). FC-32 mirrors the `DuplicatePredictionError` guarantee and reuses the shared hash-chain toolkit; Lane 4 renders FC-32's scoreboard beside FC-17's panel. FC-32 stands alone if FC-17 is unbuilt.
- **conflict_reviews.py** (Lane 2) — `_walk_chain`, `_record_sha256`, `_canonical_json`, `_append_line`, `_file_lock`, `LedgerIntegrityError` (imported read-only; the documented shared ledger primitives).
- **Existing** — `events.log().emit` (`events.py:58`/`:85`); `get_persona().paths.ops_dir`; `queue.enqueue` (`queue.py:106`); `context.use`/`_p` (`app.py:84`).

### CONTRACT CHANGE PROPOSAL — none required

FC-32 is a **new** contract; it consumes only existing/frozen signatures (trajectory LIVE; FC-27/FC-17 import-guarded; conflict_reviews primitives; inbox untouched). The supervisor tick is **Lane 1's own file** (owner lane 1+4) — a same-lane additive edit, not a CCP. The `forecast_grade` task type is a shared append-only registry entry (the ratified FC-1/FC-19/FC-27 handler pattern), not a contract change.

---

## 3. Features

### F42.1 — Sealed forecast store + abstain-on-settled-front (`forecast.py`, Lane 1)

**Problem & evidence.** Persona can describe a moving front but cannot **commit to its next move** anywhere durable. `trajectory.trajectory` computes whether a topic is `moving` vs `settled` (`analysis/trajectory.py:61`) yet nothing consumes that to open a dated stake; the only forward-probability object anywhere is FC-17 (`memory/predictions.py`, unbuilt) and it scores Persona's *own* hypotheses, not the external literature. The correct primitives already exist and are reusable: `conflict_reviews.py`'s hash-chain toolkit is documented "Shared by every append-only hash-chained ledger," and `inbox.file_handoff` (`inbox.py:43-46`) already uses a content-hash id for natural de-dup. Building a second immutable ledger — not a second hash-chain implementation — is the lazy-correct path (the same call PRD-24 F24.1 made).

**Design.**
- New `persona/forecast.py`. Durable hash-chained `ops_dir/forecasts.jsonl` (two row kinds sharing one chain, chronological, tamper-evident), reusing `conflict_reviews` primitives verbatim.
- `open_forecast` under `_file_lock`: (1) validate (`predicted_direction ∈ DIRECTIONS`; `confidence` finite in `[0,1]`, `bool` rejected; `statement`/`basis`/`topic` non-empty; `horizon_days > 0`); (2) **abstain gate** — `trajectory.trajectory(kg, topic)['signal']['state']` must be `'moving'` (or FC-27 front-move present), else return `{'abstained': True, 'reason': 'front_settled'}` and seal nothing; (3) `_walk_chain` (refuse a tampered ledger); (4) scan for an existing `kind:"forecast"` with the same `id` → `DuplicateForecastError` (the no-goalpost-moving guarantee); (5) `_append_line`. `sealed_at` = UTC ISO microseconds; `resolve_after = sealed_at + horizon_days`.
- `forecasts`/`open_forecasts`/`get`/`verify_forecasts` are pure reads; `verify_forecasts = _walk_chain(path, _validate_forecast_record)` (dispatch on `kind`) — no bespoke verifier.

**Epistemic guardrails.**
- **Sealed before the answer exists (the whole point):** the prior lives in a hash-chained row; `open_forecast` refuses a second seal for the same `(topic,statement)`; editing any sealed byte breaks `verify_forecasts` exactly as in `conflict_reviews`.
- **Abstains when the front is not moving:** a settled/insufficient front seals nothing — no forecast where the next result is a foregone conclusion or the topic has no motion to forecast. Asserted in `test_settled_front_abstains`.
- **Never mutates a belief/KG/self:** pure store, read-only trajectory call. Asserted with a KG-write spy.
- **Provenance-typed:** the sealed row is `INFERRED` (a model-formed prior); `basis` records where the call came from so a human prior weighs differently from a trajectory-momentum one.

**Required experiment.** Trivial for the store itself (a hash-chained jsonl with a covering test); the load-bearing logic — that forecasts have out-of-sample skill — is RQ-E56 (F42.2).

**Acceptance + ONE runnable check.** `pytest tests/test_forecast.py::test_seal_immutable_and_dedup` — `open_forecast` on a *moving* topic seals one row; a second seal of the same `(topic,statement)` → `DuplicateForecastError` and the first sealed row is byte-unchanged on disk; flipping one `confidence` byte → `verify_forecasts()["ok"] is False`; `open_forecast` on a *settled* topic returns `{'abstained': True}` and seals nothing; a KG-write spy asserts zero belief mutations.

**Effort.** S (one ~150-line module reusing the whole `conflict_reviews` hash-chain toolkit). **Deps.** trajectory (LIVE); `conflict_reviews` primitives (exist).

---

### F42.2 — Auto-grade against arriving literature + forward scoreboard (`forecast.py`, Lane 1 — RQ-E56)

**Problem & evidence.** A sealed forecast is worthless without a grade the world writes, not the model. The grading substrate already exists: new claims enter the KG carrying a `valid_from` timestamp and an `effect_sign` (`trajectory.py:79-87` queries exactly these), and papers keep arriving via `ingest/sources.search_multi` (`ingest/sources.py:1-7`). So "the next results landed" is precisely **claims whose `valid_from` post-dates `sealed_at`** touching the topic — a deterministic, model-free signal. Nothing today maps that arriving evidence onto a sealed prior.

**Design.**
- `grade(id, *, arriving_evidence=None)`: if `arriving_evidence is None`, pull it read-only from the KG (topic entities × `valid_from > sealed_at`, reusing the `trajectory._fetch` pattern). **realized_direction** = `sign(Σ effect_sign_i · confidence_i · w(independent_labs_i))`, collapsed to `"0"` when `|Σ|` is below the RQ-E56-tuned **null band** (a genuinely null result is a real outcome, not a coin-flip). `correct = realized_direction == predicted_direction`; `y = 1.0 if correct else 0.0`; `brier = (confidence - y)**2`. Grades **only** when `now >= resolve_after` **and** `n_evidence >= 1`; otherwise returns `{'graded': False, 'reason': ...}` and leaves it open. Appends one immutable `kind:"grade"` row.
- `sync_grades()` = idempotent pass over open, horizon-elapsed forecasts (the daemon/route calls it, mirroring PRD-24 `sync_resolutions` and PRD-35 `watch_pass`).
- `scoreboard(window=None)` = one pass over graded rows: `brier`, `by_direction`, equal-width `calibration` bins (or FC-17/PRD-15 `reliability()` import-guarded), `hits`/`misses` with the **miss list surfaced**, and `baseline_cleared` echoing `ops_dir/rq_e56.passed`.

**Epistemic guardrails.**
- **Real evidence, never a self-grade:** `y`/`realized_direction` come *only* from arriving KG claims' `effect_sign`; the grader calls no model. Asserted in `test_grade_from_arriving_only` (a monkeypatched model is never invoked).
- **No fabricated favourable score:** a wrong forecast appends a `y=0` grade with `brier` up to 1.0 and appears in `scoreboard.misses` as prominently as a hit (CLAUDE.md reversals ethos — a miss is a first-class citizen). Asserted in `test_miss_is_listed`.
- **Abstains until reality answers:** horizon-not-elapsed or no-evidence-yet → stays open, never imputed. The forecast is scored by the literature or not at all.
- **Read/scoring only:** `grade`/`sync_grades`/`scoreboard` never call `kg.anchor/demote/retire`; the grade row is `READ` (grounded in arrived claims), and the whole mode drives no belief update or dispatch. KG-write spy = 0.
- **No new metric:** Brier/calibration are the FC-17/PRD-15 estimators reused; `realized_direction` is exact arithmetic over existing `effect_sign`/`confidence` fields.

**Required experiment — RQ-E56.** *(pre-assigned; register in `docs/RESEARCH_QUALITY_PROGRAM.md`.)*
- **Hypothesis:** **foresight is out-of-sample.** On a historical corpus **frozen at a past cutoff**, Persona's dated forecasts about the **post-cutoff** literature beat a **chance + persistence** baseline on realized outcomes — **Brier strictly lower AND calibration within tolerance**.
- **Setup (`experiments/exp_prospective_forecast.py`, ≥20 seeds):** per seed, take a topic's real claim series, choose a cutoff, and hide every claim with `valid_from > cutoff`. From the ≤cutoff slice, Persona seals a forecast (direction + confidence) via the same `open_forecast` path. Reveal the hidden post-cutoff claims and `grade` against them. Baselines: **chance** (confidence 0.5, direction by base-rate) and **persistence** (predict the current trajectory `direction` continues at its historical hit-rate). Compare Brier and calibration (ECE) of Persona vs each baseline.
- **Metric + gate (both must pass):** Persona **Brier < min(chance, persistence) Brier** with the paired 95%-CI of the difference excluding 0 (≥20 seeds, mean±95%CI), **AND** Persona **ECE ≤ tolerance** (calibration within band). **Gate:** the scoreboard renders from day one (advisory), but is **labelled "candidate / unvalidated"** and `baseline_cleared=False` until `ops_dir/rq_e56.passed` exists; the mode drives no autonomy regardless (it never has a belief-write path). Oracle = the real hidden post-cutoff claims (out-of-sample truth), same discipline as the #67 backtest but as a *test harness*, not a product surface.

**Acceptance + ONE runnable check.** `python experiments/exp_prospective_forecast.py` prints `brier_persona < brier_persistence`, `brier_persona < brier_chance`, `ece_persona <= tol`, over ≥20 seeds with 95%-CI, and writes `results/rq_e56_prospective_forecast.json`; `pytest tests/test_forecast.py::test_grade_and_scoreboard` asserts a hand-set forecast+arriving-evidence pair grades to the exact `realized_direction`/`brier`, a miss lands in `scoreboard.misses`, and horizon-not-elapsed stays open.

**Effort.** M (the experiment is the bulk; `grade`/`scoreboard` are ~40 lines). **Deps.** F42.1; trajectory (LIVE); FC-17 reliability (import-guarded).

---

### F42.3 — Daemon auto-grade tick + worker handler (`supervisor.py` + `worker.py`, Lane 1)

**Problem & evidence.** For the track record to be *standing* the grader must run **unattended** — a forecast whose horizon quietly elapses must get graded without a human hitting an endpoint. The daemon already has the exact slot: the `SELF_INTERVAL_S` block enqueues `consolidate`/`deliberate`/`discover`/`revisit` (`supervisor.py:144-161`), and the handler registry is append-only (`worker.py:15` `handler`, e.g. `@handler("revisit")` `:150`).

**Design.**
- Inside `_scheduler_loop`'s `SELF_INTERVAL_S` block (additive, beside the sibling ticks):
  ```python
  # PROSPECTIVE FORECAST: grade any forecast whose horizon has elapsed ($0, offline). No budget gate.
  try:
      from .. import forecast
      if forecast.open_forecasts():        # cheap read; only enqueue when there's something to grade
          self.queue.enqueue("forecast_grade", priority=6)
  except Exception:
      pass
  ```
- Worker handler appended **after** the last existing block (never re-order):
  ```python
  @handler("forecast_grade")
  async def _forecast_grade(task, queue) -> str:
      import asyncio
      from .. import forecast
      r = await asyncio.to_thread(forecast.sync_grades)
      return f"forecast_grade: {r['graded']} graded, {r['still_open']} open"
  ```
No `can_spend` gate — grading is local-store + read-only KG derivation (offline, free), like the retraction/front-watch ticks. Behaviour-neutral when there are no forecasts (`open_forecasts()` → `[]`).

**Epistemic guardrails.** Offline/$0 → grades regardless of daily budget (a track record that stops scoring when the reading budget is spent is not a track record). Enqueue-only; the handler owns all logic. `try/except` so a grade fault never kills the scheduler (the pattern every sibling tick uses).

**Required experiment.** Trivial — a one-line enqueue mirroring tested siblings.

**Acceptance + ONE runnable check.** `pytest tests/test_forecast.py::test_supervisor_enqueues_forecast_grade` — with one horizon-elapsed open forecast and a fake queue, one scheduler iteration enqueues exactly one `forecast_grade`; with none open, zero.

**Effort.** XS. **Deps.** F42.1 (`open_forecasts`), F42.2 (`sync_grades`).

---

### F42.4 — Lane-4 render: routes + forward-looking scoreboard surface (`app.py`, `index.html`, Lane 4)

**Problem & evidence.** FC-32 has no transport or screen. The SPA already renders read-only sibling epistemic surfaces via the settled `with context.use(_p(pid))` route pattern (`/verified` at `app.py:489-493`). "Every screen answers a question a real researcher asks" (CLAUDE.md §5) — this one answers *"what has Persona publicly committed to about where these fields are heading, and how good is its forward track record?"*

**Design.**
- New routes in `app.py` (NEW routes only; thin pass-throughs — Lane 1 owns the computation), mirroring `/verified`:
  ```python
  @app.get("/api/persona/{pid}/forecasts")            # open + graded forecasts (list)
  @app.post("/api/persona/{pid}/forecasts")           # body {topic, statement, predicted_direction, horizon_days, basis, confidence?} -> open_forecast()
  @app.get("/api/persona/{pid}/forecasts/scoreboard") # scoreboard(window?) — may lazily sync_grades() first (append-only, read-through)
  ```
- New surface `surf-forecasts` + `openForecasts()` in `index.html`: (1) a **forward-looking scoreboard** — Brier tile (+ `by_direction`), a calibration curve (reused from the FC-17/PRD-15 chart idiom when `resolved >= 20`, else an honest "N of 20 resolved" callout), and a **hit/miss list where misses are rendered exactly as prominently as hits** (CLAUDE.md §5 honest-uncertainty; colour never the only encoding — WCAG); (2) a list of **open (sealed) forecasts** — statement, sealed date, predicted direction, confidence, resolve-by date — the outstanding public commitments; (3) a `baseline_cleared=False` "candidate / unvalidated" badge until RQ-E56 passes. A **"Forecast this front"** affordance may deep-link from the trajectory/frontier surface with the topic prefilled (the natural "this front is moving — call it" flow); the POST is a human click, never an auto-seal from the client.
- No client arithmetic: `brier`, `confidence`, `realized_direction`, counts render exactly as returned.

**Epistemic guardrails.** Pure transport/render; every field originates server-side (FC-32). No admit/anchor/belief-write path on this surface. The scoreboard renders the **advisory** gate state honestly (candidate badge until validated) and never hides a miss — the "wrong forecast surfaced as prominently as a right one" invariant is visible, not buried.

**Required experiment.** Trivial — thin routes + render over a validated FC.

**Acceptance + ONE runnable check.** `tests/test_forecast_api.py::test_forecast_routes_shape` — POST on a moving topic returns a sealed forecast (appears in GET); GET `…/scoreboard` returns `{n, resolved, brier, calibration, hits, misses, baseline_cleared}`. Plus a `tests/ui_*_smoke.cjs` step (`PERSONA_WORKERS=0`) asserting the scoreboard + open-forecast list render with a miss row visible and no horizontal overflow at 1280/760/390 px (mirrors `ui_research_smoke.cjs`).

**Effort.** M. **Deps.** FC-32 (F42.1/F42.2), existing `context.use`/`_p`.

---

## 4. Sequencing

**Milestone 0 (hour 1 — unblock Lane 4):** land `persona/forecast.py` FC-32 **stubs** — `open_forecast`/`grade`/`sync_grades`/`forecasts`/`open_forecasts`/`get`/`verify_forecasts`/`scoreboard` with typed empty returns (`scoreboard` → `{n:0, resolved:0, open:0, brier:None, calibration:[], hits:0, misses:0, by_direction:{}, baseline_cleared:False, window:None}`), and the `forecast_grade` handler stub. Lane 4 builds the full screen against fixtures from here.

**Then:**
1. **F42.1** sealed store + abstain gate (Lane 1, S) — the durable spine; trajectory (LIVE) is available immediately, FC-27 import-guarded.
2. **F42.2** auto-grade + scoreboard + **RQ-E56** (Lane 1, M) — grade against arriving KG claims; RQ-E56 gate must pass before the scoreboard drops its "candidate" badge (`ops_dir/rq_e56.passed`). The mode drives no autonomy regardless.
3. **F42.3** supervisor tick + worker handler (Lane 1, XS) — after the `forecast_grade` task type + `open_forecasts`/`sync_grades` are frozen. Behaviour-neutral until landed (handler is API/manual-enqueueable meanwhile).
4. **F42.4** Lane-4 routes + scoreboard surface (parallel from M0 against fixtures; wires real as 1–2 land).

Leaves the repo runnable at every checkpoint (CLAUDE.md §4): stub → seal-only → seal+grade (candidate scoreboard) → auto-ticked + baseline-cleared scoreboard.

---

## 5. Test plan

| Check | Asserts |
|---|---|
| `test_seal_immutable_and_dedup` (F42.1, runnable acceptance) | one sealed row on a moving front; second seal of same (topic,statement) → `DuplicateForecastError`, first row byte-unchanged; tampered byte → `verify_forecasts().ok is False`; **KG-write spy = 0** |
| `test_settled_front_abstains` (F42.1) | `open_forecast` on a `settled`/`insufficient` topic returns `{'abstained':True}`, seals nothing |
| `test_grade_and_scoreboard` (F42.2, runnable acceptance) | hand-set forecast + arriving evidence → exact `realized_direction`/`brier`; horizon-not-elapsed stays open; a miss appears in `scoreboard.misses` |
| `test_grade_from_arriving_only` (F42.2) | grading pulls only KG claims with `valid_from > sealed_at`; a monkeypatched model is never invoked |
| `test_miss_is_listed` (F42.2) | a wrong forecast produces a `y=0` grade surfaced in `misses` (not hidden); Brier reflects it |
| `test_no_evidence_stays_open` (F42.2) | horizon elapsed but zero qualifying arrivals → stays open, never imputed |
| `test_supervisor_enqueues_forecast_grade` (F42.3) | one horizon-elapsed forecast → one `forecast_grade` enqueued; none → zero |
| `test_forecast_routes_shape` (F42.4) | POST/GET + scoreboard payload shapes; POST is human-click only |
| `exp_prospective_forecast.py` `__main__` | RQ-E56 gate: Brier < chance & < persistence (paired 95%-CI excludes 0) AND ECE ≤ tol, ≥20 seeds; prints PASS/FAIL, writes `results/` |

Consumers are injectable (`open_forecast(kg=…, now=…)`, `sync_grades(kg=…, now=…)`) and FC-27/FC-17 import-guarded, so the suite runs without Lanes 2/3 complete (monkeypatch `trajectory`/`kg`/`predictions`, per the PRD-29/PRD-35 provider-stub pattern).

---

## 6. Open questions

- **O-1 (confidence field on the sealed prior — recommended default: keep).** The task skeleton signature carried only a direction; I added `confidence: float` because Brier and calibration — both required by the RQ-E56 gate — are undefined for a bare direction (a hard direction collapses Brier to 0/1 accuracy and makes calibration meaningless). Default: `confidence` present, default `0.6`, and RQ-E56 scores it. If the team wants direction-only, the scoreboard degrades to accuracy + a hit-rate reliability table (no ECE) — a one-block change. **Recommend keep** (calibration is the discipline that makes foresight honest). *Non-blocking — it is the new contract, not a change to a frozen one.*
- **O-2 (realized-direction aggregation — feeds RQ-E56).** Exact weighting of arriving `effect_sign` (confidence-only vs confidence×independent-labs) and the width of the "0" null band. Default: confidence×independence weight, null band tuned by RQ-E56 to maximise out-of-sample skill. *Blocks the experiment's label schema, not the M0 stub.*
- **O-3 (horizon-elapsed-but-no-evidence terminal state — recommended default: stay open + `expired_no_evidence`).** A forecast the world never answered within `horizon_days`. Default: stays open indefinitely; a much-later grace pass may mark it `outcome:"expired_no_evidence"` which is **excluded from Brier** (you cannot score a question reality did not answer) and counted separately on the scoreboard. **Recommend this** (honest — neither a hit nor a fabricated miss). *Non-blocking.*
- **O-4 (auto-open vs human-seal — recommended default: human/advisory-seal in v1).** Should the daemon *auto-seal* a forecast whenever a front-move fires (FC-27/CCP-like hook), or only offer "Forecast this front" for a human/agent to click? Default: **v1 seals only via explicit `open_forecast` calls** (human click or an advisory agent hook), never an unattended auto-seal — a public commitment the system makes about itself should be deliberate, and the abstain gate already prevents seals on settled fronts. An auto-seal-on-front-move hook is a follow-on once RQ-E56 clears. *Non-blocking (recommend: yes).*
- **O-5 (nav placement — Lane 4 IA).** A "Foresight" scoreboard beside the FC-17 prediction panel on the Epistemic tab (the two accountability ledgers together), vs its own spine destination near the trajectory/frontier screens. **Recommend** the Epistemic tab beside FC-17 — the "keeping honest score" story reads as one surface. Blocks nothing.
- **O-6 (FC-17 render co-location — surface, non-blocking).** If FC-17 ships, share one calibration-chart component between the two scoreboards (own-hypotheses vs external-literature) rather than two implementations. Flagging so PRD-24's Lane-4 owner is aware; **no FC impact today.**
