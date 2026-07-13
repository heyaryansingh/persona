# PRD-27 — Live retraction watcher on own beliefs

> **Owner lane:** 2+3 · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (flag-only; anchors are never auto-changed) · **Depends-on:** FC-6 (retraction/contamination, PRD-03), FC-2 (handoff inbox, PRD-02), FC-3 (dependency edges, PRD-02)

---

## 0. Summary + capability unlocked

FC-6 (`persona/ingest/retraction.py`) is a real, offline, deterministic retraction/contamination check — but today it is **dead code**: a repo-wide grep finds it consumed nowhere (only its own docstring and one unrelated prompt string in `app.py:679` mention "retraction"). It answers "is this source retracted *right now, if you ask*" — a one-time scan. Meanwhile the most durable, highest-stakes objects Persona owns are its **anchored beliefs** (`HUMAN_CONFIRMED`/`TESTED`, or `anchored=true`): a human signed off on them, so the system protects them (`kg.anchor` write-policy, `poisoning_signals`). Nothing re-checks whether the *evidence under those anchors* later collapses.

**This PRD turns FC-6 contamination from a one-time scan into a standing guard on the self's core.** A cheap ($0, offline), scheduled `retraction_watch` pass subscribes every source backing an anchored belief, detects when one becomes newly retracted / flagged with an expression-of-concern, and on a hit **files a human handoff (FC-2) + surfaces the contamination path** — and *never* auto-demotes the anchor. The epistemic rule is exact: a retraction of a supporting source is high-stakes → route to the human who owns the anchor. `HUMAN_CONFIRMED` stays human.

**Capability unlocked:** the self's confirmed core stops being a write-once trophy case and becomes *continuously guarded* — the acting loop's "tension → handoff" arc, run automatically against the outside world's corrections, on exactly the beliefs where being wrong costs the most.

---

## 1. File ownership (disjoint)

| File | New? | Lane | Role |
|---|---|---|---|
| `persona/ingest/retraction_watch.py` | **new** | 3 (new-file rule; sits beside FC-6 `retraction.py`) | subscription store + scheduled pass + handoff filing |
| `persona/memory/kg.py` | edit (additive) | 2 | one new read method `anchored_beliefs()` |
| `persona/daemon/worker.py` | edit (append-only) | shared registry | one `@handler("retraction_watch")` appended after the Lane-1 block (never re-order) |
| `experiments/exp_retraction_watch.py` | **new** | (experiments) | RQ-E43 fault-injection oracle |
| `tests/test_retraction_watch.py` | **new** | (tests) | runnable acceptance check |

**Boundary file (decoupled by CCP, NOT edited by this PRD's lane):**
- `persona/daemon/supervisor.py` — **Lane 1 owns it.** Needs one additive scheduler tick mirroring the reaudit block (`supervisor.py:164–170`). Flagged as **CCP-27a** in §2; Lane 1 lands the tick against the frozen `retraction_watch` task-type + `is_due()` signature this PRD provides. Behaviour-neutral until Lane 1 lands it (the handler is also reachable via the API/manual enqueue in the meantime).

Everything this PRD *edits* (`kg.py` = Lane 2, `worker.py` = shared append-only, new files) is inside lane 2+3 or shared. The only cross-lane touch is the supervisor tick → CCP.

---

## 2. FCs provided / consumed

**Consumed (verbatim, no change):**
- **FC-6** — `retraction.is_retracted(doi=None, pmid=None) -> {retracted, date, reason, source}`; `retraction.contamination(claim_id, kg=None) -> {contaminated, path}`. (`persona/ingest/retraction.py:69,93`.)
- **FC-2** — `inbox.file_handoff(kind:str, dossier:dict) -> handoff_id:str` with the required dossier keys (`persona/inbox.py:43`, `_REQUIRED` at `inbox.py:20`).
- **FC-3** — `kg.dependency_edges(topic=None)` (`kg.py:341`), reused transitively via `retraction.contamination`.

**Provided — new FC-17 (Lane 2+3, this PRD):**
- `retraction_watch.run(kg=None, *, ops_dir=None) -> {"checked":int, "anchored_beliefs":int, "hits":[{claim_id, source, doi, pmid, reason, date, kind, handoff_id, contamination_path:[claim_id]}], "filed":int, "demotions":int}` — `demotions` is always `0` (structural invariant; asserted).
- `retraction_watch.subscriptions() -> [{key, claim_id, source_slug, doi, pmid, first_subscribed, last_checked, last_state:'clean'|'hit'}]` — read-only cursor state (Lane 4 renders the standing-guard surface + hit history).
- `retraction_watch.is_due(min_age_hours=6.0) -> bool` — staleness floor for the supervisor tick (mirrors `watchlist.due`).
- **kg addition (Lane 2, additive to FC-3 family):** `kg.anchored_beliefs() -> [{claim_id, subject, relation, object, provenance, anchored, sources:[{slug, doi, title, year}]}]` — enumerates live (`valid_to IS NULL`) beliefs that are anchored OR in `CONFIRMED_PROVENANCE`, with their backing sources. *Rationale:* existing reads don't cover this — `beliefs()` (`kg.py:223`) filters `min_independent>=2 AND confidence>=0.5`, which silently drops single-source human-anchored beliefs; `provenance_breakdown()` (`kg.py:304`) returns counts, not the source list. One dedicated enumerator, ~10 lines.

**Task type (shared append-only registry — no CCP, like the Lane-1 handlers at `worker.py:384`):** queue task type `"retraction_watch"`.

**CONTRACT CHANGE PROPOSAL — CCP-27a (→ Lane 1, `supervisor.py`):** add, inside `_scheduler_loop`'s `SELF_INTERVAL_S` block (beside the reaudit tick, `supervisor.py:164`), an additive enqueue:
```python
# LIVE RETRACTION WATCH: re-check anchored-belief sources against retractions ($0, offline).
try:
    from ..ingest import retraction_watch
    if retraction_watch.is_due():          # staleness floor; no budget gate (offline, free)
        self.queue.enqueue("retraction_watch", priority=4)
except Exception:
    pass
```
No `can_spend` gate — the pass is offline local-store lookups, so it runs regardless of daily budget (unlike reaudit, which is paid). No signature change to any existing FC.

---

## 3. Features

### F27.1 — `kg.anchored_beliefs()` enumerator (Lane 2, `kg.py`)

**Problem & evidence.** The watcher must iterate exactly the protected set: live beliefs that are anchored or human/tested-confirmed, with their sources. No existing kg read returns this. `beliefs()` (`kg.py:223`) would miss a `human_resolve`-anchored single-source belief (`min_independent=2`); `provenance_breakdown()` (`kg.py:304`) returns only counts + never/stale lists. Research posture (CLAUDE.md §1): don't assume `beliefs()` covers anchors — it provably doesn't.

**Design.** Additive method:
```python
def anchored_beliefs(self) -> list[dict]:
    """Live beliefs a human/run signed off on (anchored OR CONFIRMED_PROVENANCE), with backing
    sources. The protected set the retraction watcher guards. Never includes retired (valid_to) claims."""
    r = self._q(
        """
        MATCH (c:Claim)
        WHERE c.valid_to IS NULL AND (c.anchored = true OR c.provenance IN $conf)
        OPTIONAL MATCH (c)-[sr:SUPPORTED_BY]->(s:Source)
        RETURN c.claim_id, c.subject, c.relation, c.object, c.provenance, c.anchored,
               collect(DISTINCT {slug:s.slug, doi:s.doi, title:s.title, year:s.year})
        """, {"conf": list(CONFIRMED_PROVENANCE)})
    cols = ["claim_id", "subject", "relation", "object", "provenance", "anchored", "sources"]
    out = [dict(zip(cols, row)) for row in r.result_set]
    for b in out:
        b["sources"] = [s for s in (b["sources"] or []) if s.get("slug")]
    return out
```
Reuses `CONFIRMED_PROVENANCE` (`kg.py:49`) and the `SUPPORTED_BY`/`slug`-filter idiom from `provenance()` (`kg.py:253`, `:267`).

**Epistemic guardrails.** Pure read. `valid_to IS NULL` excludes retired/`REJECTED_EXTRACTION` claims (consistent with `provenance_breakdown`).

**Required experiment.** Trivial (a Cypher read with a covering test in F27.2's suite).

**Acceptance + runnable check.** `pytest tests/test_retraction_watch.py::test_anchored_enumerates_single_source` — seed a KG, `human_resolve` a single-source belief, assert it appears in `anchored_beliefs()` with its source (and would NOT appear in `beliefs()`).

**Effort.** XS. **Deps.** none.

---

### F27.2 — retraction watcher: subscribe, detect, hand off (Lane 3, `retraction_watch.py` + `worker.py` handler)

**Problem & evidence.** FC-6 is a stateless "ask now" check. To be a *standing guard* it needs (a) a durable subscription/cursor over anchored-belief sources so it detects a *newly* retracted source and doesn't re-spam an unchanged one, and (b) the FC-2 escalation, filed automatically. The pattern already exists in-repo: `watchlist.py` keeps a per-item jsonl cursor with `due()` staleness-gating (`watchlist.py:72`) and the daemon enqueues `reaudit` from it (`supervisor.py:164–170`). We copy that shape for a $0 offline guard. Research posture: a retracted supporting paper is the canonical "belief-state contamination" event — retractions are rising and often propagate into downstream citations for years (the exact silent-wrong-number failure CLAUDE.md §4 calls the worst bug), which is *why* it escalates to the human rather than silently self-correcting.

**Design.**

*Durable subscription cursor* — `self/retraction_subscriptions.jsonl` (durable, under `self_dir`, like `watchlist.jsonl`), one row per `(claim_id, source)`:
`{key:"<claim_id>:<slug>", claim_id, source_slug, doi, pmid, first_subscribed, last_checked, last_state}` where `last_state ∈ {"clean","hit"}`.

*Public surface (FC-17):*
```python
def run(kg=None, *, ops_dir=None) -> dict:
    """Scheduled standing-guard pass ($0, offline). (1) refresh subscriptions from kg.anchored_beliefs();
    (2) for each subscribed source, retraction.is_retracted(doi, pmid); (3) on a clean->hit transition
    (or a first-sight hit) file ONE FC-2 handoff + attach contamination path; NEVER demote. Idempotent:
    unchanged 'hit' state does not re-file. Returns a legible summary; demotions is always 0."""

def subscriptions() -> list[dict]:      # read cursor rows (Lane 4 render)

def is_due(min_age_hours: float = 6.0) -> bool:   # oldest last_checked older than floor
```

*Data flow (per `run`):*
1. `kg = kg or membrane.get_kg()`; `beliefs = kg.anchored_beliefs()`.
2. Upsert one subscription row per `(claim_id, source)` with `pmid = retraction._pmid_from_slug(slug)` (reuse `retraction.py:78`) — "subscribe every source backing an anchored belief."
3. For each row: `st = retraction.is_retracted(doi=doi, pmid=pmid)`. `hit = st["retracted"]` (the local store carries both full retractions and expressions-of-concern; `kind` = `st["reason"]` conveys which — **no FC-6 change**). Set `last_checked`.
4. **Transition rule:** file iff `hit and row.last_state != "hit"` (clean→hit, or a brand-new already-retracted source). Set `last_state="hit"`; a source that heals back (removed from store) resets to `"clean"`.
5. On fire: `path = retraction.contamination(claim_id, kg=kg)["path"]` (surfaces the contamination chain, FC-6 `:93`); build the FC-2 dossier (below); `handoff_id = inbox.file_handoff("retraction_contamination", dossier)`; stamp `handoff_id` onto the row; `log().emit("flag", ..., actor="retraction-watch")` for the needs-human stream.
6. **Never** call `kg.anchor` / demote / retire. `demotions` counter stays 0.

*FC-2 dossier mapping* (satisfies `inbox._REQUIRED`, `inbox.py:20`):
- `conflict_type = "misinformation"` (a retracted/discredited source; the closest FC-2 enum member).
- `disagreeing = [{claim_id, span: <supporting quote of the retracted source>, qualifiers: {retracted_source: slug, doi, pmid, retraction_date, retraction_reason}}]`.
- `decision_requested = "A source backing your anchored belief '<subject relation object>' was retracted/flagged (<reason>). Re-affirm, qualify, or retire the anchor?"`.
- `why_unresolvable = "Belief is <provenance>/anchored — policy forbids the watcher from changing an anchor; only a human may."`.
- `cheapest_test = {action: "re-read the belief's non-retracted sources / locate replacement evidence", cost_tier: "public_data", dataset: null}`.
- `expected_updates = [{outcome:"human re-affirms", belief_change:"anchor retained; retracted source dropped from support"}, {outcome:"human retires", belief_change:"anchor retired via kg.anchor(truth=False)"}]`.
- `uncertainty = round(n_retracted_sources / n_sources, 2)` (fraction of the belief's support now retracted — a real number, not a self-report).
- `authority_boundary = "human-only: anchored/HUMAN_CONFIRMED beliefs are never auto-demoted (FC-2; CLAUDE.md §7)."`.

*Worker handler* (append after `worker.py:400`, never re-order):
```python
@handler("retraction_watch")
async def _retraction_watch(task, queue) -> str:
    import asyncio
    from ..ingest import retraction_watch
    r = await asyncio.to_thread(retraction_watch.run)
    return f"retraction_watch: {r['checked']} source(s), {r['filed']} handoff(s), {r['demotions']} demotions"
```
(`demotions` in the return string is a live legibility assertion that it stayed 0.)

**Epistemic guardrails.**
- **No auto-demote, structurally:** the module never imports/calls `kg.anchor`/`retire`/`demote`. The `demotions==0` invariant is asserted in the test and echoed in the handler result.
- **Flag, don't fabricate:** on a hit it files a *question*, not a verdict; the human owns the anchor (CLAUDE.md §7).
- **Idempotent escalation:** transition-gated firing + FC-2's content-hash dedup (`inbox.py:46`) mean a standing retraction is filed once, not every pass.
- **Provenance untouched:** a run leaves every claim's `provenance`/`anchored`/`confidence` byte-identical.
- **Offline & deterministic:** reuses FC-6's local store (`is_retracted` is model-free, `retraction.py:69`); no network, no LLM, no budget draw.

**Required experiment — RQ-E43** *(next assigned id; E40–E42 reserved for parallel PRDs-24..26; E02–E39 taken per PRD-00 §6. Register in `docs/RESEARCH_QUALITY_PROGRAM.md`).*
- **Hypothesis:** the watcher flags an anchored belief whose supporting source is (test-)retracted, with zero false demotions and no false flags on clean anchors, under fault injection.
- **Setup (`experiments/exp_retraction_watch.py`, ≥20 seeds):** per seed, generate a randomized KG of anchored + unanchored beliefs with varied source counts and a random dependency shape; seed a temp `PERSONA_RETRACTIONS_FILE`; inject retractions on a random subset of anchored-belief sources; snapshot every claim's `(provenance, anchored, confidence)`; run `retraction_watch.run`.
- **Metrics + gate (both required):** detection recall on injected-contaminated anchors **≥ 0.95**; **auto-demote count == 0** (post-run snapshot identical to pre-run for all claims); false-flag rate on clean anchors **== 0** (transition-gated). Report mean ± 95% CI over seeds.
- **Oracle:** the injected retraction set is ground truth (fault injection). Until the gate passes, the supervisor tick (CCP-27a) may ship, but treat filed handoffs as advisory in any auto-routing.

**Acceptance + ONE runnable check.** `pytest tests/test_retraction_watch.py::test_flags_anchor_no_demote` — seed temp KG (one anchored belief backed by source `S`) + temp retractions store marking `S` retracted; `run()`; assert: exactly one handoff filed with `conflict_type="misinformation"` and the belief's `claim_id` in `disagreeing`; the belief's `provenance`/`anchored` unchanged; `run()["demotions"] == 0`; a second `run()` files zero new handoffs (idempotent).

**Effort.** M. **Deps.** F27.1; FC-6, FC-2.

---

## 4. Sequencing

1. **F27.1** `kg.anchored_beliefs()` (Lane 2, XS) — unblocks the watcher and any Lane-4 render.
2. **F27.2** `retraction_watch.py` + worker handler, built against F27.1 (Lane 3, M).
3. **RQ-E43** experiment before the guard drives any auto-routing; land the gate flag `ops_dir/rq_e43.passed`.
4. **CCP-27a** supervisor tick — Lane 1, after the `retraction_watch` task-type + `is_due()` are frozen (steps 1–2). Behaviour-neutral until landed; the handler is manually/API-enqueueable meanwhile.

M0 stub: land `retraction_watch.run/subscriptions/is_due` + `kg.anchored_beliefs` with typed empty returns first so Lane 4 can render against fixtures.

---

## 5. Test plan

| Check | Asserts |
|---|---|
| `test_anchored_enumerates_single_source` | F27.1 returns single-source human-anchored beliefs that `beliefs()` drops |
| `test_flags_anchor_no_demote` (runnable acceptance) | one FC-2 handoff on a retracted-source anchor; provenance/anchored unchanged; `demotions==0`; idempotent on re-run |
| `test_expression_of_concern_flags` | a store record whose `reason` marks an expression-of-concern also fires (via `is_retracted` hit) |
| `test_clean_anchor_no_flag` | anchored belief with no retracted source → zero handoffs (false-flag guard) |
| `test_unanchored_not_guarded` | a retracted source under an *unanchored* READ belief files no handoff (only anchors are guarded) |
| `test_contamination_path_attached` | dossier `disagreeing` qualifiers carry the retracted source; downstream `contamination_path` present |
| `experiments/exp_retraction_watch.py` `__main__` | RQ-E43 gate: recall ≥0.95, demotes==0, false-flag==0 over ≥20 seeds; prints PASS/FAIL |

Reuse fixtures via `PERSONA_RETRACTIONS_FILE` (temp store, `retraction.py:36`) and an injected `kg` (both `run` and `contamination` accept `kg=`), so tests need no live FalkorDB where the enumerator is mockable — but F27.1's own test exercises the real Cypher against the test KG harness.

---

## 6. Open questions

1. **CCP-27a cadence & ownership** — confirm Lane 1 accepts the additive `retraction_watch` tick in `_scheduler_loop` at `SELF_INTERVAL_S` with **no budget gate** (offline/$0). *Blocks: Lane 1.* Default if silent: ship the handler manual/API-enqueueable; tick lands later — behaviour-neutral.
2. **Expression-of-concern typing** — the PRD reads EoC vs full-retraction from `is_retracted().reason` (no FC-6 change). If a surface needs a hard `type` enum, that is a **separate** FC-6 signature-change proposal (Lane 3), out of scope here. *Non-blocking.*
3. **FC-17 render** — Lane 4 will likely want `GET /retraction-watch` over `subscriptions()` + hit history for the needs-human surface. Signature is frozen above; the route is Lane 4's to add. *Non-blocking (contract-first).*
4. **RQ-E43 id** — assigned E43 per orchestration; E40–E42 assumed reserved for parallel PRDs-24..26. If those did not claim them, E43 leaves a harmless gap, not a collision. *Non-blocking.*
