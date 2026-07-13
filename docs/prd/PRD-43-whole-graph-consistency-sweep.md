# PRD-43 — Whole-graph self-consistency sweep

> **Owner lane:** 2 (calibrated membrane / belief store) · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (read-only detection; files repair *candidates* only — never mutates/retires/demotes a belief; anchors are always human) · **Depends-on:** FC-2 (handoff inbox), FC-3 (`kg.dependency_edges`) · **Backlog #526.**
> Governed by PRD-00 §4/§6 and §8 reconciliation. Where this body disagrees with §4/§6, §4/§6 win.

---

## 0. Summary + capability unlocked

The membrane checks coherence **pairwise, at write time**: `link_contradictions(pair_key)` (`kg.py:199`) links two opposite-sign claims on one `(subject,object)` pair as each is admitted, and `type_conflict` (`conflicts.py:27`) types that one collision. But a self that reads for months accumulates incoherence that is invisible to any pairwise check:

- **Transitivity violations** — A `supports` B, B `supports` C, yet A `CONTRADICTS` C. Each edge is locally fine; the *triangle* is incoherent. Nothing walks the dependency graph (`kg.dependency_edges`, `kg.py:406`; `DEP_REL_TYPES`, `kg.py:86`) against the contradiction set (`kg.contradictions`, `kg.py:299`) to find it.
- **Unflagged sign contradictions** — two live opposite-sign claims share a `pair_key` but carry no `CONTRADICTS` edge, because `link_contradictions` was never re-run over them (it fires on the pair it is *called* with; `link_all_contradictions` (`kg.py:212`) is the batch fix and is not on any schedule). The membrane *missed* linking them.
- **Orphaned inferences** — an INFERRED claim `derives_from`/`presupposes` a premise (`dependency.py:149-151`) that was later **retired** (`valid_to` set via `retire_extraction_claim` `kg.py:233` / `anchor(truth=False)` `kg.py:225`) or **demoted**. The inference still sits live with its old confidence, its logical footing pulled out from under it.

**PRD-43 adds a standing, whole-graph integrity sweep.** A deterministic, offline ($0) pass audits the *entire* live belief-state at scale for these three incoherence classes and files **typed repair candidates** through the existing FC-2 handoff path — and **never** auto-mutates, retires, or demotes a belief. This is DISTINCT from #354 (one transitive relation) and #308 (coherence of a belief *set*): it is the periodic **global** audit that keeps a months-old self from silently rotting.

**Capability unlocked:** the belief-state stops being coherent-only-by-construction-at-write-time and becomes *continuously audited as a whole* — the acting loop's "detected incoherence → typed handoff → human repairs the durable core" arc, run automatically against the graph the self has actually accumulated, on exactly the beliefs (anchored / confirmed) where being incoherent costs the most.

---

## 1. File ownership (disjoint)

| File | New? | Lane | Role |
|---|---|---|---|
| `persona/memory/coherence.py` | **new** | 2 (new-file rule) | the sweep: 3 deterministic detectors + applicability gate + append-only ledger + FC-2 repair-candidate filing + `is_due`/`recent` |
| `persona/memory/kg.py` | edit (additive) | 2 | one new bulk read `claim_states()` |
| `persona/daemon/worker.py` | edit (append-only) | shared registry | one `@handler("coherence_sweep")` appended after the last handler (never re-order) |
| `experiments/exp_coherence_sweep.py` | **new** | (experiments) | RQ-E57 fault-injection oracle |
| `tests/test_coherence_sweep.py` | **new** | (tests) | runnable acceptance checks |

**Name-adjacency note (NOT a collision):** a top-level `persona/coherence.py` already exists — it owns self-file caps + interest drift (`persona/coherence.py:1-11`), an unrelated concern. This PRD's module is `persona/memory/coherence.py` (`persona.memory.coherence`), a distinct import path with no clash. PRD-00 §3 lists `memory/coherence.py` under Lane 2; the new-file-ownership rule confirms Lane 2 owns it. (Surfaced as OQ-1 in case the master prefers a non-adjacent name.)

**Boundary file (decoupled by CCP, NOT edited by this lane):**
- `persona/daemon/supervisor.py` — **Lane 1 owns it.** Needs one additive scheduler tick inside the `SELF_INTERVAL_S` block, beside the reaudit tick (`supervisor.py:144,166-168`), against the frozen `coherence_sweep` task-type + `is_due()` this PRD provides. Flagged **CCP-43a** (§2). Behaviour-neutral until Lane 1 lands it — the handler is API/manual-enqueueable meanwhile (mirrors PRD-27 CCP-27a exactly).

Everything this PRD *edits* is Lane-2-owned (`coherence.py` new, `kg.py`) or shared append-only (`worker.py`). The only cross-lane touch is the supervisor tick → CCP-43a.

---

## 2. FCs provided / consumed

### PROVIDES — **FC-33 (Lane 2), new `persona/memory/coherence.py`**

```python
def sweep(kg=None, *, min_claims: int = 25, max_hops: int = 2,
          ops_dir=None, file_handoffs: bool | None = None) -> dict:
    """Whole-graph self-consistency sweep. READ-ONLY: detects logical incoherence at scale and files
    TYPED REPAIR CANDIDATES via FC-2 — NEVER mutates/retires/demotes a belief (structural invariant).
    file_handoffs default None -> gate-driven (files only when ops_dir/rq_e57.passed exists);
    True/False overrides (tests). Deterministic; idempotent (FC-2 content-hash dedup)."""
    # -> {"violations": [{"type": "transitivity"|"sign_contradiction"|"orphaned_inference",
    #                     "claim_ids": [str, ...],           # the claims in the incoherent structure
    #                     "detail": str,                     # legible human-readable description
    #                     "severity": "low"|"medium"|"high", # high = touches an anchored/CONFIRMED belief
    #                     "status": "candidate"}],           # DETECTED, not CONFIRMED (until human review)
    #     "counts": {"transitivity": int, "sign_contradiction": int, "orphaned_inference": int,
    #                "live_claims": int, "high_severity": int, "filed": int},
    #     "repairs_filed": [str, ...],   # FC-2 handoff_ids; [] unless the RQ-E57 gate flag exists
    #     "applicable": bool,            # False when live_claims < min_claims (never a spurious sweep)
    #     "reason": str | None}          # why not applicable, else None

def recent(limit: int = 20, *, ops_dir=None) -> list[dict]:
    """Read the append-only sweep ledger (ops_dir/coherence_sweep.jsonl) — one summary row per run
    for the Lane-4 standing-guard surface + incoherence history. Read-only."""

def is_due(min_age_hours: float = 24.0, *, ops_dir=None) -> bool:
    """Staleness floor for the supervisor tick: last sweep older than the floor (mirrors watchlist.due,
    watchlist.py:72). A whole-graph sweep is not an hourly job — default 24h."""
```

**Internal Lane-2 additive read (NOT a frozen FC — plumbing inside my own `kg.py`):**
```python
def claim_states(self, claim_ids: list[str] | None = None) -> dict:
    """Bulk per-claim state for the sweep: {claim_id: {subject, relation, object, effect_sign,
    pair_key, provenance, anchored, confidence, independent_sources, live}}. claim_ids=None returns
    ALL claims (live AND retired — the sweep MUST see retired premises). live = (valid_to IS NULL)."""
```
*Rationale for a new read:* no existing kg read serves this. `beliefs()` (`kg.py:286`) filters `min_independent>=2 AND confidence>=0.5 AND valid_to IS NULL` — it drops single-source and, fatally, *retired* claims, so an orphaned-inference's retracted premise is invisible to it. `provenance_breakdown()` (`kg.py:367`) returns counts + never/stale lists, not per-claim `pair_key`/`effect_sign`/`live`. One bulk read (single Cypher, whole-graph) keeps the sweep at O(4 queries), not O(N) round-trips.

### CONSUMES (verbatim, no change)
- **FC-2** — `inbox.file_handoff(kind:str, dossier:dict) -> handoff_id:str` with the required dossier keys (`inbox.py:43`; `_REQUIRED` at `inbox.py:20`; enum `_CONFLICT_TYPES` at `inbox.py:19`). Same-lane, cited because it is the frozen escalation path.
- **FC-3** — `kg.dependency_edges(topic=None) -> [{src,dst,rel_type,confidence,span}]` (`kg.py:406`), the transitivity/orphaned edge source. `DEP_REL_TYPES` (`kg.py:86`).
- **Own-lane kg reads (not FCs):** `kg.contradictions()` (`kg.py:299`) — the flagged contradiction pairs; `kg.claim_states()` (new, above).

**CONTRACT CHANGE PROPOSAL — CCP-43a (→ Lane 1, `supervisor.py`):** add, inside `_scheduler_loop`'s `SELF_INTERVAL_S` block beside the reaudit tick (`supervisor.py:166-168`), an additive enqueue:
```python
# WHOLE-GRAPH COHERENCE SWEEP: periodic self-consistency audit ($0, offline, no budget gate).
try:
    from ..memory import coherence
    if coherence.is_due():                 # staleness floor; offline/free, so no can_spend gate
        self.queue.enqueue("coherence_sweep", priority=4)
except Exception:
    pass
```
No `can_spend` gate — the pass is offline local + Cypher reads, no LLM, no network (like the retraction watcher). No signature change to any existing FC.

**No other CCP.** All consumed signatures are frozen; the sweep is fully self-contained within Lane 2 + the shared append-only worker registry.

---

## 3. Features

---

### F43.1 — `kg.claim_states()` bulk read (Lane 2, `kg.py`)

**Problem & evidence.** The sweep must see the whole graph — including **retired** claims — with each claim's `pair_key`, `effect_sign`, provenance and live-ness, in *one* read. No existing method does this: `beliefs()` (`kg.py:286`) excludes retired and single-source claims; `contradictions()` (`kg.py:299`) returns only already-flagged pairs; `provenance()` (`kg.py:316`) is per-claim (O(N) round-trips — the opposite of "at scale"); `provenance_breakdown()` (`kg.py:367`) returns aggregate counts, not per-claim sign/pair. CLAUDE.md §1: don't assume `beliefs()` covers what the sweep needs — it provably drops the retired premises orphaned-inference detection depends on.

**Design.** Additive method, single Cypher:
```python
def claim_states(self, claim_ids: list[str] | None = None) -> dict:
    where = "WHERE c.claim_id IN $ids " if claim_ids else ""
    rows = self._q(
        "MATCH (c:Claim) " + where +
        "RETURN c.claim_id, c.subject, c.relation, c.object, c.effect_sign, c.pair_key, "
        "c.provenance, c.anchored, c.confidence, c.independent_source_count, c.valid_to",
        {"ids": list(claim_ids)} if claim_ids else {}).result_set
    out = {}
    for cid, subj, rel, obj, sign, pk, prov, anch, conf, isc, vto in rows:
        out[cid] = {"subject": subj, "relation": rel, "object": obj, "effect_sign": sign,
                    "pair_key": pk, "provenance": prov, "anchored": bool(anch),
                    "confidence": conf, "independent_sources": isc, "live": vto is None}
    return out
```

**Epistemic guardrails.** Pure read; mutates nothing. `live = (valid_to IS NULL)` is the single source of truth for retired-ness, consistent with every live-view filter in `kg.py`. Retired claims are *included* (that is the point) but plainly marked `live: False`.

**Required experiment.** Trivial (a Cypher read; covered by F43.3's suite).

**Acceptance + ONE runnable check.** `pytest tests/test_coherence_sweep.py::test_claim_states_reports_retired_premise` — seed a KG with an inference claim `derives_from` a premise; retire the premise (`retire_extraction_claim` or `anchor(truth=False)`); assert `claim_states()[premise]["live"] is False` and `claim_states()[inference]["live"] is True`, each carrying `pair_key`/`effect_sign`/`provenance`.

**Effort.** XS. **Deps.** none.

---

### F43.2 — the three deterministic detectors + applicability gate (Lane 2, `coherence.py`)

**Problem & evidence.** Pairwise, at-write-time linking cannot see triangles, cannot re-scan for missed links, and cannot notice a premise that died after its inference was drawn. The three primitives already exist in the graph but nothing composes them: dependency edges with `rel_type` (`kg.py:406`, `DEP_REL_TYPES` `kg.py:86`), the flagged contradiction set (`kg.py:299`), and per-claim live/provenance state (F43.1). The correctness posture (CLAUDE.md §4, PRD-00 §2): forensics run in **code**, deterministically, with an **applicability gate** emitting a state distinct from "passed" — so this is a pure function over plain dicts (edges/contradictions/states), trivially fault-injectable for RQ-E57, no DB in the hot path.

**Design.** A pure detector `_detect(edges, contradictions, states, *, min_claims, max_hops)` the public `sweep` wraps around the four reads (`dependency_edges`, `contradictions`, `claim_states(None)`; the fourth being the ledger append in F43.3).

- **Applicability gate (first).** `live = {cid for cid,s in states.items() if s["live"]}`. If `len(live) < min_claims` → return `{applicable: False, reason: f"insufficient claims: {len(live)} < {min_claims}", violations: [], counts: {...live_claims...}, repairs_filed: []}`. A whole-graph coherence audit on a toy graph is meaningless — never a spurious sweep. *(ponytail: `min_claims=25` is a floor to suppress toy-graph noise, not an autonomy threshold; tunable — OQ-2.)*

- **Contradiction set.** `contra = {frozenset({r["pos_claim"], r["neg_claim"]}) for r in contradictions}` (flagged) `∪` the **unflagged** opposite-sign same-pair live pairs computed in Python: group `live` claims by `pair_key`, and for each pair_key holding both a `+` and a `-` live claim, emit each cross-sign pair; those NOT already in the flagged set are the **sign_contradiction** findings, and all of them together form the contradiction relation used by transitivity. *(No new kg read: `link_all_contradictions` is the mutating batch-linker; the sweep computes the same set read-only and refuses to link — linking is a mutation.)*

- **(a) transitivity.** Over `SUPPORT_RELS = {"supports"}` edges (`src` supports `dst`), BFS forward from each claim up to `max_hops` (default 2 — the named A→B→C case; ceiling `max_hops=3`). For each reachable `end` with a support-path from `start`, if `frozenset({start, end})` is in the contradiction set → a `transitivity` violation with `claim_ids = [start, ...path..., end]`. *(ponytail: bounded BFS, O(n·d^max_hops); `max_hops` capped small so the sweep stays cheap. `SUPPORT_RELS` is conservatively just `supports`; widening to `derives_from`/`generalizes` is OQ-3, re-gated by RQ-E57.)*

- **(b) sign_contradiction.** The unflagged opposite-sign same-pair live pairs from the contradiction-set step. `claim_ids = [pos, neg]`, `detail` naming the shared `(subject,object)` pair. These are the contradictions the pairwise membrane *missed linking*.

- **(c) orphaned_inference.** Over `PREMISE_RELS = {"derives_from", "presupposes", "operationalizes"}` edges (`src` = the inference, `dst` = the premise): flag when the inference `states[src]["live"]` is True AND the premise is **genuinely dead** — `states[dst]["live"] is False` (retired: `valid_to`, i.e. `anchor(truth=False)`/`retire_extraction_claim`) OR `states[dst]["provenance"] == "REJECTED_EXTRACTION"` OR `states[dst].get("demoted")` (future demote flag, absent-safe). `claim_ids = [src, dst]`. **A merely low-confidence but LIVE premise never orphans its inference** (explicit guardrail; unit-tested).

- **Severity (deterministic).** `high` iff ANY involved claim is `anchored` OR `provenance ∈ CONFIRMED_PROVENANCE` (`kg.py:84`, HUMAN_CONFIRMED/TESTED) — the human-owns-it, highest-stakes case. Else `medium` iff any involved claim has `independent_sources >= 2` or `confidence >= 0.5`. Else `low`. Every violation carries `status: "candidate"` (DETECTED ≠ CONFIRMED).

**Epistemic guardrails.**
- **Read-only, structurally:** `_detect` is a pure function; `sweep` calls only kg *reads* + the FC-2 filer + a ledger append. The module never imports `kg.anchor`/`retire_extraction_claim`/`link_*`/`set_validity_window`. A `demotions/mutations == 0` invariant is asserted in the test and mirrored by the fact that no write method is reachable.
- **Detected vs confirmed:** a violation is a `candidate` — a *question*, never a verdict. The human (for anchors) or the conflict path resolves it; the sweep changes nothing.
- **Applicability-gated:** `applicable: False` on a sub-`min_claims` graph is a first-class state, not a silent empty pass (the forensics discipline, PRD-00 §2).
- **Orphaned requires a genuinely-dead premise:** live-but-low-confidence is explicitly excluded.
- **Deterministic + offline:** same graph → same violations, byte-for-byte; no LLM, no network, no budget draw.

**Required experiment — RQ-E57** *(register in `docs/RESEARCH_QUALITY_PROGRAM.md`; sandbox `experiments/exp_coherence_sweep.py`).*
- **Hypothesis.** On a synthetic belief graph with **injected** incoherences (fault injection: seed transitivity breaks + unflagged sign contradictions + orphaned inferences), the deterministic sweep detects them at **precision ≥ 0.90**, and on a **coherent** graph the **false-flag rate 95%-CI ≤ 0.05**.
- **Metric.** `precision` = flagged-that-are-genuinely-injected ÷ all-flagged (over the injected graphs); `false_flag_rate` = flagged ÷ live-claims on a fully-coherent graph (target 0). The detector is deterministic — **seeds vary the random graph generation** (topology, sign mix, which edges/premises are perturbed), which is the honest uncertainty; report **mean ± 95% CI** over **≥ 20 seeds**.
- **Gate.** mean `precision ≥ 0.90` **AND** upper 95%-CI bound of `false_flag_rate ≤ 0.05`. Pass ⇒ land `ops_dir/rq_e57.passed` and the sweep may **file** repair candidates (F43.3). **Fail ⇒ ledger-only / advisory** — the sweep still detects and records, but files nothing to the human inbox (no low-precision detector floods the queue).
- **Sandbox.** `experiments/exp_coherence_sweep.py` — per seed: generate a coherent random KG-shaped `(edges, contradictions, states)`; snapshot; inject a known set of each incoherence type; run `_detect`; score precision + recall against the injected ground truth; separately run on the un-injected coherent graph for `false_flag_rate`. Offline, deterministic detector; prints the mean±CI table + the gate boolean; appends to `results/FINDINGS.md#RQ-E57`.

**Acceptance + ONE runnable check.** `pytest tests/test_coherence_sweep.py::test_detects_three_incoherence_types` — feed injected dicts with exactly one transitivity break (A supports B, B supports C, A contradicts C), one unflagged sign contradiction, one orphaned inference (live inference, retired premise); assert all three detected with correct `type` + `claim_ids`; a coherent graph yields `violations == []`; a **low-confidence-but-live** premise yields **no** orphaned flag; a `< min_claims` graph returns `applicable is False`.

**Effort.** L. **Deps.** F43.1; FC-3.

---

### F43.3 — repair-candidate filing (FC-2) + ledger + worker handler (Lane 2, `coherence.py` + `worker.py`)

**Problem & evidence.** Detection is inert until an incoherence around the durable core reaches the human who owns it. The escalation path already exists and is non-mutating: `inbox.file_handoff` (`inbox.py:43`) appends a structured dossier, content-hash-ided so an unchanged finding files to the same id (`inbox.py:46`) — naturally idempotent, never touches a claim. PRD-27 F27.2 uses exactly this shape for the retraction watcher; PRD-43 reuses it for coherence repairs. The standing/periodic aspect reuses the reaudit precedent: a `@handler` in `worker.py`'s append-only registry (`worker.py:31`+, e.g. `_reaudit` at `worker.py:163`) + a supervisor `is_due()` tick (`supervisor.py:166-168`).

**Design.**

*Autonomy gate (matches the program's `rq_eXX.passed` convention).* `file_handoffs` resolves to `ops_dir/rq_e57.passed` existing when `None`. **Until the gate passes: ledger-only** — detect, record to the ledger, return violations, `repairs_filed == []`, `counts.filed == 0` (Lane 4 renders the ledger as "candidate incoherences"). **After the gate: file** an FC-2 repair candidate for each **high-severity** violation (touches an anchored/CONFIRMED belief — the human-owns-it, highest-stakes case; medium/low stay ledger-only advisory to keep the inbox signal-dense, since the pairwise membrane + conflict path already surface fresh non-anchor contradictions).

*FC-2 dossier mapping* (satisfies `inbox._REQUIRED`, `inbox.py:20`; `conflict_type` in the frozen enum `inbox.py:19`):
- `conflict_type`: `orphaned_inference` w/ retracted premise → `"misinformation"`; `orphaned_inference` w/ demoted premise → `"insufficient"`; `sign_contradiction` → `"insufficient"`; `transitivity` → `"insufficient"`. *(OQ-4: enrich `sign_contradiction` via `conflicts.type_conflict` once qualifiers are threaded — deferred; the honest default is `insufficient`.)*
- `disagreeing`: one entry per involved claim `{claim_id, span: <its stored quote/relation>, qualifiers: {role: 'inference'|'premise'|'contradicting'|'support_path', incoherence: <type>, detail}}`.
- `decision_requested`: e.g. `"An anchored belief '<subj rel obj>' sits in a detected <type> incoherence (<detail>). Re-affirm, qualify, or retire?"`.
- `why_unresolvable`: `"The sweep is read-only and cannot change an anchored/confirmed belief — only a human may (PRD-00 §2, CLAUDE.md §7)."`.
- `cheapest_test`: `{action: "re-read the involved sources / re-derive the inference from live premises", cost_tier: "public_data", dataset: null}`.
- `expected_updates`: `[{outcome:"human re-affirms", belief_change:"anchor retained; incoherence annotated resolved"}, {outcome:"human retires the inference", belief_change:"orphaned inference retired via kg.anchor(truth=False)"}]`.
- `uncertainty`: a real number — `severity`-derived (`high→` a fixed prior; not a model self-report), or the fraction of the involved claims that are unconfirmed. Never fabricated.
- `authority_boundary`: `"human-only: anchored/HUMAN_CONFIRMED beliefs are never auto-changed by the sweep (FC-2; CLAUDE.md §7)."`.

*Append-only ledger* — `ops_dir/coherence_sweep.jsonl`, one summary row per run: `{at, live_claims, applicable, counts, filed, violation_ids:[...]}` (the diff/history basis for `is_due` + Lane-4 `recent()`). Mirrors `gate_decisions.jsonl` / `watchlist.jsonl`.

*Worker handler* (append after the last `worker.py` handler, never re-order):
```python
@handler("coherence_sweep")
async def _coherence_sweep(task, queue) -> str:
    import asyncio
    from ..memory import coherence
    r = await asyncio.to_thread(coherence.sweep)
    v = r.get("counts", {})
    return (f"coherence_sweep: not applicable ({r.get('reason')})" if not r.get("applicable")
            else f"coherence_sweep: {len(r['violations'])} incoherence(s), {v.get('filed',0)} filed, 0 mutations")
```
(The trailing `0 mutations` is a live legibility assertion that the read-only invariant held.)

**Epistemic guardrails.**
- **No mutation, ever:** filing an FC-2 handoff and appending a ledger row are both non-mutating (inbox + ledger are append-only jsonl). A run leaves every claim's `provenance`/`anchored`/`confidence`/`valid_to` byte-identical.
- **Advisory until the gate:** pre-`rq_e57.passed`, `repairs_filed == []` — a detector under 0.90 precision never reaches the human queue.
- **Idempotent escalation:** FC-2's content-hash dedup means a standing incoherence files once, not every sweep.
- **Human-anchors-high-stakes:** only anchor/CONFIRMED-touching violations are filed; the human who owns the anchor decides. `HUMAN_CONFIRMED` stays human.

**Required experiment.** Covered by RQ-E57 (F43.2) for detection; the filing/idempotency/no-mutation invariants are asserted directly in the runnable check below (deterministic, not seeded).

**Acceptance + ONE runnable check.** `pytest tests/test_coherence_sweep.py::test_files_repair_candidate_no_mutation` — seed a KG whose anchored belief is an orphaned inference over a retired premise; with `ops_dir/rq_e57.passed` present, `sweep()` files **exactly one** FC-2 handoff (`conflict_type` in the enum; the anchored `claim_id` in `disagreeing`); the belief's `provenance`/`anchored`/`confidence`/`valid_to` are **unchanged** pre/post; a second `sweep()` files **zero** new handoffs (idempotent); and **without** the gate flag, `repairs_filed == []`.

**Effort.** M. **Deps.** F43.1, F43.2; FC-2.

---

## 4. Sequencing

**Milestone 0 (hour 1 — land FC-33 stubs so Lane 4 renders against fixtures):** ship `memory/coherence.py` with typed stubs — `sweep(...)` returns `{"violations": [], "counts": {"transitivity":0,"sign_contradiction":0,"orphaned_inference":0,"live_claims":0,"high_severity":0,"filed":0}, "repairs_filed": [], "applicable": False, "reason": "stub"}`; `recent(...)` → `[]`; `is_due(...)` → `False` — plus `kg.claim_states()` returning `{}`. File **CCP-43a** in the HANDOFF dispatch log. Repo stays runnable.

Then: **F43.1** (`kg.claim_states`, XS — unblocks the detector) → **F43.2** (the three detectors + applicability gate + RQ-E57; the correctness core — the sweep must clear RQ-E57 before it files) → **F43.3** (FC-2 filing + ledger + worker handler; filing enforces only behind `ops_dir/rq_e57.passed`) → **CCP-43a** supervisor tick (Lane 1, after `coherence_sweep` task-type + `is_due()` are frozen; behaviour-neutral, handler manually/API-enqueueable meanwhile).

Rationale: nothing files to the human until the detector clears RQ-E57; the ledger + handler ship first so Lane 4 has a real (if advisory) surface from day one.

---

## 5. Test plan

| Check | Asserts |
|---|---|
| `test_claim_states_reports_retired_premise` (F43.1) | bulk read returns a retired premise `live: False` + a live inference `live: True`, with `pair_key`/`effect_sign`/`provenance` |
| `test_detects_three_incoherence_types` (F43.2, runnable) | one each of transitivity / sign_contradiction / orphaned detected with correct type + `claim_ids`; coherent graph → `[]`; low-confidence-but-live premise → no orphan flag; `< min_claims` → `applicable False` |
| `test_files_repair_candidate_no_mutation` (F43.3, runnable) | one FC-2 handoff on a high-severity orphaned anchor; provenance/anchored/confidence/valid_to unchanged; idempotent re-run; `repairs_filed == []` without the gate flag |
| `test_unflagged_sign_contradiction_only` | a same-pair opposite-sign live pair WITH a `CONTRADICTS` edge is NOT re-flagged (only the membrane-missed ones are); the edge-less pair IS flagged |
| `test_transitivity_needs_real_contradiction` | A supports B supports C with NO A–C contradiction → zero transitivity flags (no false triangle) |
| `test_no_mutation_invariant` | after any `sweep()`, no kg write method was called; every claim byte-identical (snapshot compare) |
| `experiments/exp_coherence_sweep.py` `__main__` | RQ-E57 gate: precision mean ≥ 0.90 AND false-flag 95%-CI upper ≤ 0.05 over ≥ 20 seeds; prints PASS/FAIL + appends `results/FINDINGS.md#RQ-E57` |

Tests inject `(edges, contradictions, states)` dicts directly into `_detect` (no live FalkorDB) for detector logic; F43.1's own test exercises the real Cypher against the kg test harness. FC-2 filing uses a temp `ops_dir`.

---

## 6. Open questions

1. **Module name adjacency (OQ-1).** `persona/memory/coherence.py` sits beside an unrelated top-level `persona/coherence.py` (self-caps/drift). Distinct import paths, no clash. *Recommended default:* keep `memory/coherence.py` per PRD-00 §3 + the task; rename to `memory/consistency.py` only if the master finds the adjacency confusing. *Non-blocking.*
2. **`min_claims` floor (OQ-2).** Default `25`. It only suppresses toy-graph noise (not an autonomy gate — everything is advisory until RQ-E57). *Recommended default:* `25`; a surface may tune it via the kwarg. *Non-blocking.*
3. **`SUPPORT_RELS` / `max_hops` breadth (OQ-3).** v1 uses `SUPPORT_RELS = {"supports"}`, `max_hops = 2` (conservative — protects the ≥0.90 precision gate). Widening to `derives_from`/`generalizes` or `max_hops = 3` catches more triangles but must **re-run RQ-E57**. *Recommended default:* ship narrow; widen only if RQ-E57 still clears. *Non-blocking.*
4. **`sign_contradiction` typing (OQ-4).** Filed as `conflict_type="insufficient"` (deterministic default). Enriching via `conflicts.type_conflict` (`conflicts.py:27`) needs qualifiers threaded into `claim_states`. *Recommended default:* `insufficient`; enrich later. *Non-blocking.*
5. **CCP-43a cadence & ownership.** Confirm Lane 1 accepts the additive `coherence_sweep` tick in `_scheduler_loop` at `SELF_INTERVAL_S` with **no budget gate** (offline/$0). *Recommended default if silent:* ship the handler manual/API-enqueueable; the tick lands later — behaviour-neutral. *Blocks: Lane 1's supervisor edit only.*
6. **FC-33 render (OQ-6).** Lane 4 will likely want `GET /coherence` over `recent()` + the live `sweep()` violations for the standing-guard surface. Signature is frozen above; the route is Lane 4's to add. *Non-blocking (contract-first).*
