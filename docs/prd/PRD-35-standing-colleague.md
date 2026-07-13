# PRD-35 — Standing colleague (subscription + front-moved alerts)

> **Owner lane:** 1+4 · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (watch is $0/offline & unattended; a *wake-the-human* handoff is the only interrupt, and it files a question — never mutates a belief) · **Depends-on:** **FC-4** (`engine.value_queue` / load-bearing, PRD-03, built), **FC-19** (`retraction_watch.run/subscriptions/is_due`, PRD-27), **trajectory** (`analysis/trajectory.py` `topic_trajectory`, PRD-03 F3.4), **FC-21** (`analysis/frontier.frontier`, PRD-29 — the per-interest projection this PRD diffs), FC-2 (`inbox.file_handoff`, PRD-02, built).
>
> Backlog: **#500** (capstone) fusing **#15** (always-on-colleague alerts), **#220** (load-bearer retraction alert), **#357** (standing-program continuity); digest cadence per **#84/#353**; wake-the-human per **#473**. New contract: **FC-27**. Experiment: **RQ-E49**. Read PRD-00 §2 (epistemic discipline), §4 (FC registry), §8 (reconciliation governs) before coding.

---

## 0. Summary + capability unlocked

Persona today is a **pull** system. A PI can open the field map, the value queue, the trajectory screen, or (PRD-29) bookmark a per-interest *frontier* artifact and re-open it — but **nothing tells them the day it changes.** Every one of the "front moved" signals already exists as a computed object: a trajectory inflection (`trajectory.topic_trajectory`, PRD-03 F3.4), a newly well-powered contradiction (`kg.contradictions` via `fieldmap.build`, surfaced in `frontier().contested`), a retraction of a load-bearing source (`retraction_watch.run`, FC-19 + load-bearing weight FC-4), and an emerging consensus (a `rising`→`plateau` phase with independence still climbing, F3.4). But each is a screen you must go look at. The always-on colleague's whole promise — *"I'll tell you the day the front moves"* — is the missing **push**.

**This PRD adds the subscribe→watch→notify loop.** A human subscribes to a topic/target with a chosen trigger set; a `$0`, offline, unattended daemon task (`front_watch`) runs a **delta pass** each cadence — it re-derives the frontier signals and compares them against the *last snapshot* per subscription — and fires a notification **only on a real state change** (a genuinely new inflection / contradiction / retraction / consensus, not a re-render of an unchanged one). High-stakes moves (a load-bearing retraction, an inflection on a load-bearing anchored belief) **wake the human** via an FC-2 handoff; everything else **batches into a digest** the PI reads on their own cadence. It invents **no new metric** — it is a *change detector over already-gated signals* — and it never mutates a belief.

**Capability unlocked:** Persona stops being a set of dashboards you remember to check and becomes a **standing collaborator that reaches out** — the capstone (#500) that turns the whole program (trajectory + retraction watcher + value queue + frontier + standing continuity) into one continuous *subscribe → watch → notify* arc, with alert discipline (interrupt only for high-stakes; batch the rest) so it is adopted, not muted.

---

## 1. File ownership (disjoint)

| File | New? | Lane | Role |
|---|---|---|---|
| `persona/subscriptions.py` | **new** | 1 (new-file rule) | FC-27 provider: subscription store (subscribe/list/unsubscribe), snapshot cursor, `watch_pass`, `notify` router, `digest` reader |
| `persona/daemon/worker.py` | edit (**append-only** registry) | shared | one `@handler("front_watch")` appended after the retraction-watch block (never re-order) |
| `persona/daemon/supervisor.py` | edit (additive tick) | 1 | one scheduler tick enqueuing `front_watch` when `subscriptions.is_due()` (mirrors the CCP-27a retraction tick; offline/$0, no budget gate) |
| `persona/api/app.py` | edit (**NEW routes only**) | 4 | `GET/POST/DELETE …/subscriptions`, `GET …/subscriptions/digest` (§3 F35.4). Do not touch existing route bodies. |
| `persona/api/static/index.html` | edit (**NEW surface/JS only**) | 4 | `surf-subscriptions` + `openSubscriptions()`; a "Subscribe" affordance on the frontier surface; a digest panel. No client-invented metric. |
| `experiments/exp_front_watch.py` | **new** | (experiments) | RQ-E49 precision/recall oracle on a labeled inflection/retraction set |
| `tests/test_subscriptions.py` | **new** | (tests) | runnable acceptance checks |

**Boundary files another lane touches — decoupled by contract, NOT edited here:**
- `persona/analysis/trajectory.py`, `persona/analysis/frontier.py` (Lane 3) — **imported read-only** (`topic_trajectory`, `frontier`). No edit. Both may be absent at first ship → the watch pass degrades that trigger to "off" (import-guarded, never crashes), same discipline as PRD-29 F29.1.
- `persona/ingest/retraction_watch.py` (Lane 3, FC-19) — **called read-only** (`run`/`subscriptions`). The retraction trigger reads FC-19's *already-filed* hit history rather than re-scanning, so a retraction is escalated once (FC-19 owns the retraction handoff; this PRD's retraction trigger is a **digest/notify mirror**, not a second filer — see F35.2 guardrail).
- `persona/inbox.py` (Lane 2, FC-2) — **called read-only** for the wake-the-human handoff. No edit.
- `persona/analysis/engine.py` (Lane 3, FC-4) — **called read-only** (`value_queue`, load-bearing) for the high-stakes gate. No edit.

Everything this PRD *edits* is Lane 1 (`subscriptions.py`, `supervisor.py`) or Lane 4 (`app.py`, `index.html`) or the shared append-only `worker.py` registry — no cross-lane body edit.

---

## 2. FCs provided / consumed

### PROVIDES — FC-27 (Lane 1), new `persona/subscriptions.py`

```python
# Trigger enum — the four "front-moved" event kinds a subscription may watch.
TRIGGERS = {"inflection", "contradiction", "retraction", "consensus"}

def subscribe(topic: str, human: str, *, triggers: set[str] | None = None,
              cadence_hours: float = 24.0) -> dict:
    """Register a standing watch on `topic` (a subfield string or a target/entity) for `human`.
    `triggers` defaults to all four. Idempotent: same (topic, human) upserts (content-hash key),
    never duplicates. Returns the stored subscription row. Durable jsonl under self_dir."""

def subscriptions() -> list[dict]:
    """All active subscription rows: {key, topic, human, triggers, cadence_hours,
    created_at, last_watched, last_snapshot_sha, fired_count}. Read-only (Lane 4 render)."""

def unsubscribe(key: str) -> bool:
    """Deactivate a subscription (append-only tombstone; never rewrites history)."""

def is_due(min_age_hours: float = 6.0) -> bool:
    """True iff any active subscription's last_watched is older than its cadence (staleness floor
    for the supervisor tick; mirrors watchlist.due / retraction_watch.is_due)."""

def watch_pass(kg=None, *, ops_dir=None, now=None) -> dict:
    """One offline, $0 delta pass over all DUE subscriptions. Per subscription: re-derive the
    frontier signals (frontier()/topic_trajectory/retraction_watch), DIFF vs the stored snapshot,
    emit a `front_moved` alert per genuinely-new event, route high-stakes → notify(wake=True),
    low-priority → digest. Updates the snapshot cursor. Never mutates a belief. Idempotent:
    an unchanged front fires nothing. Returns {due:int, checked:int, alerts:[...], woke:int,
    digested:int}. `now` injectable for deterministic tests."""

def notify(sub: dict, event: dict, *, wake: bool) -> dict:
    """Route one front-moved event. Always emits a legible `front_moved` event to the stream.
    If wake: file an FC-2 handoff (inbox.file_handoff) so it hits the needs-human inbox; else
    append to the human's digest. Returns {alerted:bool, wake:bool, handoff_id?:str}."""

def digest(human: str, *, since=None, clear=False) -> dict:
    """The batched low-priority feed for `human`: {human, items:[event...], n, generated_at}.
    Append-only store; `clear=True` marks items read (tombstone, never deletes)."""
```

- **Event shape** (`front_moved`), the unit both `notify` and `digest` carry:
  `{sub_key, topic, human, trigger:'inflection'|'contradiction'|'retraction'|'consensus', claim_id?, statement, before, after, load_bearing:float, high_stakes:bool, why:str, at, provenance, label}` — `before/after` are the diffed snapshot values (the *real state change*), `why` is the plain-language "why you're seeing this now" line (#84), `label` echoes the source signal's own gate label verbatim (deterministic / candidate-RQ-E02 / FC-19).
- **Snapshot cursor:** `self/subscription_snapshots.jsonl`, one latest row per subscription key: `{key, sha256, phases:{claim_id:phase}, contested:[[subj,obj]...], retraction_hits:[claim_id...], consensus:[claim_id...], at}`. The diff of the fresh derivation against this row *is* the change detector (no new metric).

**Task type (shared append-only registry — no CCP, like the FC-19 handler at `worker.py`):** queue task type `"front_watch"`.

### CONSUMES (verbatim, no change)

- **FC-21** — `frontier.frontier(topic) -> {moved:[{claim_id, phase, velocity, ...}], contested:[{subject,object,pos,neg,both_independent}], ...}` (PRD-29). The primary signal source: `moved` → inflection/consensus, `contested` → contradiction.
- **trajectory** — `trajectory.topic_trajectory(topic) -> [{claim_id, velocity, acceleration, phase, inflection:bool, independence_drift}]` (PRD-03 F3.4). Used directly for the `inflection` flag when `frontier` is absent/degraded.
- **FC-19** — `retraction_watch.run()`/`subscriptions()` (PRD-27). The retraction trigger reads FC-19's hit history (a hit already filed its own handoff); this PRD mirrors it into the subscriber's digest/wake, never re-files.
- **FC-4** — `engine.value_queue(topic)` / dependency load-bearing weight (`engine.dependency_graph(topic).nodes[*].load_bearing`) for the **high-stakes gate** (a move on a load-bearing claim wakes the human; a move on a leaf batches).
- **FC-2** — `inbox.file_handoff(kind, dossier)` (`persona/inbox.py:43`) for the wake-the-human path.
- **Existing** — `events.log().emit` (`persona/events.py:58`); `selfmind.interests()`; `get_persona().paths.self_dir` (`paths.py:13`).

### CONTRACT CHANGE PROPOSAL — none required

FC-27 consumes only existing/frozen signatures. The supervisor tick is **Lane 1's own file** (owner lane 1+4), so it is a same-lane additive edit, **not** a CCP. The `front_watch` task type is a shared append-only registry entry (the ratified pattern for FC-1/FC-19 handlers), not a contract change.

---

## 3. Features

### F35.1 — Subscription store + snapshot cursor (`subscriptions.py`, Lane 1)

**Problem & evidence.** There is no durable "a human is watching this topic" object anywhere in the repo (`grep -ri subscri persona/` finds only `retraction_watch`'s *source* subscriptions — a different noun). The always-on colleague (#15/#500) needs a first-class, restart-surviving record of *who watches what, with which triggers, and what the front looked like last time* — the last being the thing that makes "the day it moved" detectable rather than re-alerting every pass. The pattern already exists: `retraction_watch.subscriptions()` keeps a per-source jsonl cursor with `is_due()` staleness-gating, and `inbox.file_handoff` uses a content-hash key for natural dedup. We copy both.

**Design.**
- New `persona/subscriptions.py`. Durable `self/subscriptions.jsonl` (one row per active watch, content-hash key = `sha256(topic|human)[:16]`, upsert-on-resubscribe) + tombstone rows for `unsubscribe` (append-only, never rewrites — the standing-continuity #357 audit trail).
- `subscribe/subscriptions/unsubscribe/is_due` per FC-27. `is_due` compares each row's `last_watched` against its own `cadence_hours` (a per-subscription floor), OR'd across rows — so a daily and an hourly subscription can coexist.
- Snapshot cursor `self/subscription_snapshots.jsonl` written by `watch_pass` (F35.2). `subscribe` seeds an **empty** snapshot so the *first* watch pass does not fire on everything already true (a subscription starts by learning the current front silently; it fires only on subsequent change — the "motion only on real state change" rule, CLAUDE.md §5).

**Epistemic guardrails.** Pure store; no model, no network, no KG write. First-pass-silent (empty seed snapshot) prevents a fabricated "everything just moved!" burst on subscribe. Content-hash key = deterministic dedup under test.

**Required experiment.** Trivial (a jsonl store with a covering test).

**Acceptance + runnable check.** `pytest tests/test_subscriptions.py::test_subscribe_upsert_and_due` — subscribe twice with same `(topic, human)` → one active row; `is_due()` False immediately after a watch, True after advancing `now` past `cadence_hours`; `unsubscribe` deactivates without deleting history.

**Effort.** S. **Deps.** none.

---

### F35.2 — The delta watch pass + notify/digest router (`subscriptions.py` + `worker.py` handler, Lane 1)

**Problem & evidence.** The signals exist but nothing *diffs* them over time to detect a *new* event, and nothing tiers the result into interrupt-vs-batch. Naively "run frontier() and alert on everything contested" would spam a subscriber every cadence with the same standing contradictions — the exact alert-fatigue failure #84 cites (humans override 49–96% of alerts once fatigued). The fix is a **snapshot diff** (fire only on the transition) plus a **consequence gate** (wake only for load-bearing moves).

**Design.** `watch_pass(kg=None, *, ops_dir=None, now=None)`:
1. `subs = [s for s in subscriptions() if is due by its cadence]`; if none, return `{due:0,...}`.
2. Per subscription, derive the current front (import-guarded, each independently degradable):
   - **inflection / consensus:** `moved = frontier(topic).moved` (or `topic_trajectory(topic)` if frontier absent). New **inflection** = a `claim_id` whose `phase` changed vs `snapshot.phases[claim_id]` into `{rising,declining,abandoned}` **or** whose `inflection` flag newly True. **Consensus** = a `claim_id` transitioning `rising→plateau` **with** `independence_drift > 0` (new labs still joining — an emerging agreement, not a stall). *(RQ-E49 tunes exactly which transitions count as a "genuine front-move" to hit the precision gate.)*
   - **contradiction:** `contested = frontier(topic).contested`; new **contradiction** = a `(subject,object)` pair absent from `snapshot.contested` **and** `both_independent` (≥2 vs ≥2 — the RQ-E02 well-powered threshold; a thinly-sourced disagreement does not fire). This is the "well-powered contradiction" of the brief.
   - **retraction:** read `retraction_watch.subscriptions()`; new **retraction** = a source that flipped `clean→hit` for a claim on this topic since `snapshot.retraction_hits`. (FC-19 already filed *its* handoff; here we surface it *to this subscriber*.)
3. **High-stakes gate:** `high_stakes = load_bearing(claim_id) >= LB_HI` (from `engine.dependency_graph(topic)`), OR `trigger == 'retraction'` on a load-bearing source (#220 — the single most consequential event), OR the claim is anchored. High-stakes → `notify(sub, event, wake=True)`; else `wake=False`.
4. For every new event: emit `front_moved`, route via `notify`, and record it into the fresh snapshot. Write the new snapshot row (with its `sha256`) — the diff basis for next pass.
5. Return `{due, checked, alerts, woke, digested}`.

`notify(sub, event, wake)`: always `log().emit("front_moved", why, actor="colleague", claim_id=…, high_stakes=…)`. If `wake`: build an FC-2 dossier (`conflict_type` = `"misinformation"` for retraction else `"insufficient"`; `decision_requested` = the front-moved question; `authority_boundary` = "human owns the response; the watcher only surfaces the move") and `inbox.file_handoff("front_moved", dossier)` (content-hash dedup means a persistent move wakes once). Else append the event to the human's digest store (`self/digest-<human>.jsonl`).

*Worker handler* (append after the FC-19 block, never re-order):
```python
@handler("front_watch")
async def _front_watch(task, queue) -> str:
    import asyncio
    from .. import subscriptions
    r = await asyncio.to_thread(subscriptions.watch_pass)
    return f"front_watch: {r['due']} due, {r['woke']} woke, {r['digested']} digested"
```

**Epistemic guardrails.**
- **Motion only on real state change (structural):** every trigger fires on a *snapshot transition*, never on a standing condition. An unchanged front → zero alerts. Asserted in `test_no_change_no_alert`.
- **No new metric:** the pass computes no score of its own — it diffs already-gated signals and copies each one's `label` verbatim. `high_stakes` is a gate on the *existing* FC-4 load-bearing weight, not a new number.
- **No belief mutation:** `watch_pass`/`notify` never call `kg.anchor/retire/demote`. Asserted with a KG-write spy.
- **Wake only for consequence (#473):** the FC-2 handoff (the human interrupt) fires only behind the high-stakes gate; everything else batches (#84/#353), so the colleague is adopted, not muted.
- **No double-escalation:** the retraction trigger *reads* FC-19's already-filed state — it mirrors into the subscriber's feed, it does not re-file the retraction handoff (FC-19 owns that). Its own wake handoff (if high-stakes) is content-hash-deduped against re-firing.
- **First-pass-silent:** an empty seed snapshot (F35.1) means subscribing never back-fires on pre-existing state.

**Required experiment — RQ-E49.** *(next free id after E48; register in `docs/RESEARCH_QUALITY_PROGRAM.md`.)*
- **Hypothesis:** the front-moved detector fires on **genuine** front-moves (labeled inflections / new well-powered contradictions / retractions) without excessive false alarms on noise (re-renders, thinly-sourced disagreements, unchanged fronts).
- **Setup (`experiments/exp_front_watch.py`, ≥20 seeds):** per seed, synthesize a topic's belief-history series with a **labeled** set of injected events — real inflections (sign-flip in velocity past the F3.4 noise floor), real emerging contradictions (a second independent lab crossing the ≥2/≥2 threshold), and real retractions (injected `clean→hit`) — interleaved with **decoys** (noise wobbles below the floor, single-lab disagreements, unchanged re-renders). Run two consecutive `watch_pass`es (snapshot then diff); count fired vs labeled.
- **Metrics + gate:** on the labeled set, **precision ≥ 0.85** (of the events fired, ≥85% are labeled genuine — the anti-spam bar) **and** recall reported alongside (target ≥0.80, informational — a missed move is cheaper than a false alarm here). Report mean ± 95% CI over seeds. **Gate:** the supervisor tick (F35.3) may ship, but *wake-the-human* auto-routing is gated behind `ops_dir/rq_e49.passed`; until it passes, high-stakes events also route to the digest (advisory) with a "candidate" badge rather than interrupting.
- **Oracle:** the injected labeled event set is ground truth (fault injection), same discipline as RQ-E43 (retraction watcher) and RQ-E30 (control injection).

**Acceptance + ONE runnable check.** `pytest tests/test_subscriptions.py::test_watch_fires_once_on_transition` — seed a subscription + an empty snapshot; inject a phase transition (`plateau→rising`) on a load-bearing claim; `watch_pass()` → exactly one `front_moved` alert, `wake=True`, one FC-2 handoff filed, snapshot updated; a second `watch_pass()` with no further change → zero new alerts (idempotent); a KG-write spy asserts zero belief mutations.

**Effort.** M. **Deps.** F35.1; FC-21/trajectory/FC-19/FC-4/FC-2 (each import-guarded).

---

### F35.3 — Supervisor tick (`supervisor.py`, Lane 1)

**Problem & evidence.** For the colleague to be *standing* it must watch **unattended**, not only when a human hits an endpoint. The daemon already has the exact slot: the `SELF_INTERVAL_S` block enqueues `reaudit`/`revisit`/`collect_proofs`, and CCP-27a added the offline retraction tick there. We add one more offline tick.

**Design.** Inside `_scheduler_loop`'s `SELF_INTERVAL_S` block (beside the retraction-watch tick), additive:
```python
# STANDING COLLEAGUE: re-check subscribed fronts for a move ($0, offline). No budget gate.
try:
    from .. import subscriptions
    if subscriptions.is_due():
        self.queue.enqueue("front_watch", priority=4)
except Exception:
    pass
```
No `can_spend` gate — the pass is local-store + read-only derivations (offline, free), like the retraction tick. Behaviour-neutral when there are no subscriptions (`is_due()` → False).

**Epistemic guardrails.** Offline/$0 → runs regardless of daily budget (a colleague that stops watching when the reading budget is spent is not standing). Enqueue-only; the handler owns all logic. `try/except` so a watch-pass fault never kills the scheduler (same pattern as every sibling tick).

**Required experiment.** Trivial — a one-line enqueue mirroring three tested siblings.

**Acceptance + runnable check.** `pytest tests/test_subscriptions.py::test_supervisor_enqueues_front_watch` — with one due subscription and a fake queue, one scheduler iteration enqueues exactly one `front_watch` task; with none due, zero.

**Effort.** XS. **Deps.** F35.1 (`is_due`), F35.2 (handler).

---

### F35.4 — Lane-4 render: routes + subscription surface + digest (`app.py`, `index.html`)

**Problem & evidence.** FC-27 has no transport or screen. The SPA already renders read-only sibling surfaces (frontier/PRD-29, inbox) and the needs-human stream. "Every screen answers a question a real researcher asks" (CLAUDE.md §5) — this one answers *"what am I watching, what just moved, and what needs me now vs later?"*

**Design.**
- New routes in `app.py` (NEW routes only; thin pass-throughs — Lane 1 owns the computation), mirroring the PRD-29 `context.use(_p(pid))` pattern:
  ```python
  @app.get("/api/persona/{pid}/subscriptions")        # list active watches
  @app.post("/api/persona/{pid}/subscriptions")       # body {topic, human, triggers?, cadence_hours?} -> subscribe()
  @app.delete("/api/persona/{pid}/subscriptions/{key}")  # unsubscribe()
  @app.get("/api/persona/{pid}/subscriptions/digest?human=…")  # digest(human) -> batched feed
  ```
- New surface `surf-subscriptions` + `openSubscriptions()` in `index.html`: a list of active watches (topic · triggers · cadence · fired_count · last_watched), a **Subscribe** form (topic + trigger checkboxes + cadence), and a **digest panel** rendering batched `front_moved` items each with its `why` line + `label` badge + provenance colour+text (never colour alone — WCAG). A **"Subscribe"** button on the PRD-29 frontier surface deep-links here with the topic prefilled (the natural "I'm looking at this frontier — watch it for me" flow). High-stakes woke events already appear in the existing needs-human inbox (FC-2); this surface links to them, does not duplicate the handoff render.
- No client arithmetic: `load_bearing`, `before/after`, counts render exactly as returned.

**Epistemic guardrails.** Pure transport/render; every field originates server-side (FC-27) including its `label`. No admit/anchor path on this surface. The digest renders the *batched* feed honestly (with "why now"); the inbox renders the *interrupt* feed — the two-tier discipline is visible, not hidden.

**Required experiment.** Trivial — thin routes + render over a validated FC.

**Acceptance + runnable check.** `tests/test_subscriptions_api.py::test_subscription_routes_shape` — POST creates a watch (returned in GET); DELETE deactivates it; `GET …/digest?human=X` returns `{human, items, n}`. Plus a `tests/ui_*_smoke.cjs` step asserting the subscribe form + digest panel render with a label badge and no horizontal overflow at 1280/760/390 px (mirrors `ui_research_smoke.cjs`).

**Effort.** M. **Deps.** FC-27 (F35.1/F35.2), existing `context.use`/`_p`.

---

## 4. Sequencing

**Milestone 0 (hour 1 — unblock Lane 4):** land `subscriptions.py` FC-27 **stubs** — `subscribe/subscriptions/unsubscribe/is_due/watch_pass/notify/digest` with typed empty returns (`watch_pass` → `{due:0,checked:0,alerts:[],woke:0,digested:0}`), and the `front_watch` handler stub. Lane 4 builds the full screen against fixtures from here.

**Then:**
1. **F35.1** store + cursor (Lane 1, S) — the durable spine.
2. **F35.2** watch pass + notify/digest + worker handler (Lane 1, M) — built against **whichever consumers exist**; each trigger is import-guarded, so it lands with retraction (FC-19, likely first) live and inflection/contradiction degrading until FC-21/trajectory land, then wires them. *Correct behaviour, not a blocker* (PRD-29 precedent).
3. **RQ-E49** before *wake-the-human* auto-routing; land `ops_dir/rq_e49.passed`. Until then high-stakes also digests (advisory).
4. **F35.3** supervisor tick (Lane 1, XS) — after the `front_watch` task type + `is_due()` are frozen (1–2). Behaviour-neutral until landed (handler is API/manual-enqueueable meanwhile).
5. **F35.4** Lane-4 routes + surface + digest (parallel from M0 against fixtures; wires real as 1–2 land).

Leaves the repo runnable at every checkpoint (CLAUDE.md §4): stub → retraction-only watch → full four-trigger watch → auto-ticked + gated wake.

## 5. Test plan

| Check | Asserts |
|---|---|
| `test_subscribe_upsert_and_due` (F35.1) | idempotent upsert; per-cadence `is_due`; unsubscribe tombstones without deleting |
| `test_first_pass_silent` | first `watch_pass` after subscribe fires nothing (empty seed snapshot) |
| `test_watch_fires_once_on_transition` (runnable acceptance) | one alert + one FC-2 wake on a load-bearing phase transition; idempotent re-run; **KG-write spy = 0** |
| `test_no_change_no_alert` | unchanged front → zero alerts (motion-only-on-change) |
| `test_thin_contradiction_no_fire` | a single-lab (<2/<2) disagreement does not fire the contradiction trigger |
| `test_leaf_move_digests_not_wakes` | a move on a non-load-bearing claim batches to digest, no handoff |
| `test_retraction_mirrors_not_refiles` | a FC-19 hit surfaces to the subscriber's feed but files no *second* retraction handoff |
| `test_supervisor_enqueues_front_watch` (F35.3) | one due subscription → one `front_watch` enqueued; none due → zero |
| `test_subscription_routes_shape` (F35.4) | POST/GET/DELETE + digest payload shapes |
| `exp_front_watch.py` `__main__` | RQ-E49 gate: precision ≥0.85 (+recall reported) over ≥20 seeds; prints PASS/FAIL |

Consumers are injectable (`watch_pass(kg=…, now=…)`) and each trigger import-guarded, so the suite runs without Lanes 2/3 complete (monkeypatch `frontier`/`topic_trajectory`/`retraction_watch`, per PRD-29/PRD-04's provider-stub pattern).

## 6. Open questions

- **O-1 (trigger transition semantics — feeds RQ-E49, blocking the precision gate).** Which exact phase/velocity transitions count as a "genuine front-move" for `inflection` vs `consensus` (e.g. does `plateau→declining` fire, or only `rising→declining`?). Default: fire on any phase change into `{rising,declining,abandoned}` + newly-True `inflection`; `consensus` only on `rising→plateau` with `independence_drift>0`. RQ-E49 tunes the exact set to clear precision ≥0.85. *Blocks: the experiment's label schema, not the M0 stub.*
- **O-2 (notification transport — scope).** "Notify" here = a `front_moved` event on the stream + an FC-2 inbox handoff (wake) + an in-app digest panel (batch). **No email/SMS/push** (no such channel exists in-repo; a real external feed is a separate backlog item if a user asks). Confirm in-app is the intended v1 scope. *Non-blocking (recommend: yes).*
- **O-3 (retraction ownership boundary).** Confirm the retraction trigger *mirrors* FC-19's already-filed hit (surfaces it to the subscriber) and does **not** re-file the retraction handoff — FC-19/PRD-27 owns the retraction escalation; this PRD owns the *subscriber notification* of it. Default: mirror-only (above). *Non-blocking (recommend: yes — avoids double-escalation).*
- **O-4 (digest cadence governor — deferred).** #84 specs a *learned* interrupt threshold (act-vs-dismiss history) + quiet hours. v1 ships the fixed two-tier gate (high-stakes→wake, else→digest); the learned governor is a follow-on once there's dismiss history to learn from. Confirm defer. *Non-blocking (recommend: yes — ponytail; #84 is its own backlog item).*
- **O-5 (nav placement — Lane 4 IA).** New spine destination ("Watching") vs a subtab. Recommend a spine destination — the digest is a primary "needs-me-later" feed beside the "needs-me-now" inbox. Blocks nothing.
