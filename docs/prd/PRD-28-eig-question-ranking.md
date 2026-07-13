# PRD-28 — Expected-info-gain question ranking

> **Owner lane:** 2+4 · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced · **Depends-on:** FC-2 (inbox, Lane 2 — self), FC-4 (`engine.dependency_graph`, Lane 3), FC-3 (`kg.provenance`, Lane 2 — self, read only).
>
> Reconciliation: PRD-00 §4/§6/§8 GOVERN. New-contract id **FC-20**; experiment id **RQ-E44**. Both pre-assigned — do not re-mint.

---

## 0. Summary + capability unlocked

The handoff inbox today lists items in arrival/scan order: `GET /api/persona/{pid}/inbox` (`persona/api/app.py:623`) returns `g.candidate_conflicts(limit=50)` in KG-scan order, and filed handoffs (`inbox.file_handoff`, `persona/inbox.py:43`) are appended to `handoffs.jsonl` with **no reader at all**. A human clearing the inbox therefore answers whatever is on top, not what is worth most.

**Capability unlocked:** rank the open human-handoffs by **expected information gain (EIG)** — a proxy for how much a human's answer would reduce Persona's *total* belief-uncertainty — so the inbox asks its highest-value question first. EIG proxy = **candidate uncertainty × downstream load-bearing mass (FC-4) × resolvability**. This turns the FC-2 inbox from FIFO into a value-ordered queue, mirroring the VoI÷cost logic already shipped for the *experiment* queue (`persona/analysis/value_queue.py:98`) but applied to the *human-question* queue.

**FC-20 (this PRD provides):** a handoff-ranking **read** interface over the FC-2 inbox — a reader for open handoffs plus a pure EIG scorer/ranker. Advisory ordering only: it never files, resolves, drops, or anchors anything.

---

## 1. File ownership (disjoint)

| File | Status | Lane | Note |
|---|---|---|---|
| `persona/inbox.py` | edit (additive) | **2** (owns it) | add `open_handoffs()` reader + `RESOLVED_NAME` constant. No change to `file_handoff`. |
| `persona/inbox_ranking.py` | **new** | **2** (new-file rule, PRD-00 §3) | pure EIG scorer + ranker. No I/O beyond calling `open_handoffs()` + FC-4. |
| `persona/api/app.py` | edit (new route only) | **4** | one `GET .../inbox/ranked` route. Lane-4 owns `app.py` new routes. |
| `persona/api/static/index.html` | edit (existing surface only) | **4** | order the existing inbox list by rank + show the EIG breakdown; **no new tab** (consistent with commit 353662b). |
| `experiments/exp_eig_ranking.py` | **new** | **4** | RQ-E44 sandbox. |
| `tests/test_inbox_ranking.py` | **new** | **4** | acceptance check. |

**Boundary / decoupling:** the only cross-lane read is FC-4 `engine.dependency_graph(topic)` (Lane 3). FC-20 consumes it behind a `dep_graph=None` injection param, so `inbox_ranking` is testable with a fixture and never imports Lane-3 internals. `inbox.py` and `inbox_ranking.py` are both Lane-2 files → no shared-edit collision with Lane 4's `app.py`/`index.html`.

---

## 2. FCs provided / consumed

**Provides — FC-20 (Lane 2+4), new `persona/inbox_ranking.py` + additive `persona/inbox.py`:**

```python
# persona/inbox.py  (additive; Lane 2 owns this file)
RESOLVED_NAME = "handoff_resolutions.jsonl"   # append-only {handoff_id, at, ...}; may be absent
def open_handoffs() -> list[dict]:
    """Every filed handoff not yet resolved, newest-first.
    Reads ops_dir/handoffs.jsonl (append-only, deduped by content-hash handoff_id — see file_handoff),
    minus any handoff_id present in ops_dir/handoff_resolutions.jsonl.
    Row shape: {handoff_id, kind, dossier, filed_at}. Missing files -> []."""

# persona/inbox_ranking.py  (new)
def eig_score(dossier: dict, *, load_bearing_by_claim: dict[str, float]) -> dict:
    """Pure. -> {eig, uncertainty, load_bearing, resolvability}. No I/O. Conservative defaults on
    missing fields (see §3 F28.1). EIG is an ADVISORY proxy, gated on RQ-E44 before it can auto-order
    anything autonomously; human always sees all items."""

def rank_handoffs(handoffs: list[dict] | None = None, *, topic: str | None = None,
                  dep_graph: dict | None = None) -> list[dict]:
    """Rank open handoffs by descending EIG. If handoffs is None -> inbox.open_handoffs().
    If dep_graph is None -> engine.dependency_graph(topic) (FC-4). Returns each input row augmented with
    {eig, uncertainty, load_bearing, resolvability, rank:int, pinned:bool}. STABLE, TOTAL order:
    pinned first (strong-exact-span dissenter, §3 guardrail), then eig desc, then filed_at asc,
    then handoff_id — never drops a row."""
```

**Consumes:** FC-4 `engine.dependency_graph(topic) -> {nodes:[{claim_id, load_bearing:float, ...}], edges}` (`persona/analysis/engine.py:8`, `dependency.py:23`); FC-2 self (`inbox.file_handoff` dossier schema, PRD-00 §4). No consumer of FC-20 exists yet except Lane 4's new route.

**CONTRACT CHANGE PROPOSAL:** none. FC-20 is a new additive contract; `open_handoffs()` and `RESOLVED_NAME` are additive within Lane 2's own `inbox.py` (no signature change to `file_handoff`). No FC-2/FC-4 signature changes.

---

## 3. Features

### F28.1 — EIG scorer (`inbox_ranking.eig_score`)

**Problem & evidence.** The dossier schema (FC-2, `persona/inbox.py:20`) already carries `uncertainty` and `disagreeing:[{claim_id, span, qualifiers}]` and `cheapest_test:{action, cost_tier, dataset}` — every input the EIG proxy needs is present at file-time, but nothing consumes them for ordering. FC-4 already computes per-claim `load_bearing ∈ [0,1]` (`dependency.py:59`, normalized downstream-dependent count — itself a placeholder gated on RQ-E06). Research grounding: value-of-information / EIG question selection is the standard decision-theoretic objective (Lindley 1956; active-learning EIG, Houlsby 2011). Persona's *experiment* queue already applies the isomorphic `voi × (cost weight)⁻¹` (`value_queue.py:98,132`) — this feature applies the same shape to the *human-question* queue, reusing that precedent rather than inventing a metric.

**Design.**
- `uncertainty ← float(dossier["uncertainty"])` clamped to `[0,1]`; **conservative default 0.5** if absent/non-numeric (do not fabricate high or low priority).
- `load_bearing ← max(load_bearing_by_claim.get(c["claim_id"], 0.0) for c in dossier["disagreeing"])` — the downstream mass of the *most* load-bearing contested claim. `0.0` if no disagreeing claim is in the graph (a question about an isolated claim genuinely gains little total-uncertainty reduction).
- `resolvability ← _RESOLVABILITY[cheapest_test["cost_tier"]]` with `{public_data:1.0, cheap_assay:0.6, expensive:0.3}` (inverse-cost, mirroring `value_queue._COST_WEIGHT`), `× 1.15` bonus (capped 1.0) when `cheapest_test.get("dataset")` is truthy. **Default 0.3** (least resolvable) on unknown/absent tier — a question we can't cheaply settle is worth less to *ask a human now*.
- `eig = round(uncertainty * (0.1 + load_bearing) * resolvability, 4)` — the `0.1` floor (same trick as `value_queue`'s `0.5+` offsets) keeps ordering well-defined for a high-uncertainty, resolvable question whose claim isn't yet in the dep graph; it never zeroes an item out of the list.
- All keys read via `.get` with the defaults above → never raises on a partial dossier (dossiers are validated at file-time, but the scorer stays pure/total for replay fixtures).

**Epistemic guardrails.** `eig` is a **derived proxy, server-side only** — no client passes a priority in. It is **advisory ordering, not a gate**: a low EIG never suppresses or closes a handoff. Conservative defaults everywhere (0.5 uncertainty, 0.3 resolvability) so a sparse dossier is neither inflated nor buried. No provenance, belief, or anchor is touched.

**Required experiment:** shared with F28.2 → **RQ-E44** (below).

**Acceptance + runnable check.** Deterministic scorer. `tests/test_inbox_ranking.py::test_eig_score_defaults_and_ordering`: a fully-specified high-uncertainty/high-load/public_data dossier scores strictly above a low-uncertainty/isolated/expensive one, and a dossier with `uncertainty` absent scores exactly as if `uncertainty=0.5`.

**Effort:** S (~40 LOC). **Deps:** none (pure).

### F28.2 — Open-handoff reader + ranker (`inbox.open_handoffs`, `inbox_ranking.rank_handoffs`)

**Problem & evidence.** `handoffs.jsonl` is **write-only today** — `file_handoff` appends (`inbox.py:51`) but nothing reads it back, so filed handoffs are invisible to any surface. The inbox route surfaces `candidate_conflicts` instead (`app.py:630`), in KG-scan order. To rank *human-handoffs* by EIG we first need to read the open set, then order it.

**Design.**
- `open_handoffs()` streams `ops_dir/handoffs.jsonl`, JSON-per-line; dedups by `handoff_id` (append-only + content-hash id means an identical re-file is the same id — last row wins); subtracts any `handoff_id` in `handoff_resolutions.jsonl` (absent file → nothing resolved). Returns newest-first by `filed_at`. Missing `handoffs.jsonl` → `[]`. Mirrors the read pattern of `conflict_reviews.summarize_conflict_reviews`.
- `rank_handoffs` calls `open_handoffs()` (unless injected), fetches `engine.dependency_graph(topic)` once (unless injected), builds `load_bearing_by_claim = {n["claim_id"]: n["load_bearing"] for n in dep_graph["nodes"]}`, scores each via `eig_score`, sets `pinned` (guardrail below), and returns a **stable total order**: `key = (not pinned, -eig, filed_at, handoff_id)`. Assigns 1-based `rank`. **Never filters** — every open handoff is returned.

**Data flow:** `handoffs.jsonl` → `open_handoffs()` → `rank_handoffs` ←(FC-4)← `engine.dependency_graph` → ranked rows → Lane-4 `GET .../inbox/ranked` → existing inbox UI reorders + shows `{eig, uncertainty, load_bearing, resolvability}` breakdown.

**Epistemic guardrails (the load-bearing one).** Ranking is **advisory ordering only**. Encoded as `pinned:bool`: a handoff is pinned to the top of the list (above EIG order) when any `disagreeing` entry carries a **strong exact-span dissent** — a `span` with resolvable character offsets (`isinstance(span, dict) and "start" in span and "end" in span`, or an FC-2 grounded-span shape). This guarantees *a lone strong-exact-span dissenter still escalates regardless of its EIG rank* — it is never buried below the fold by a low downstream-mass score. Pinning **reorders, never drops**; nothing is ever removed from the returned list. No fabricated priority: `pinned` derives only from the presence of a grounded span in the dossier the swarm already filed.

**Required experiment — RQ-E44** (pre-assigned; register in `docs/RESEARCH_QUALITY_PROGRAM.md`).
- **Hypothesis:** EIG ordering surfaces higher-value resolutions than FIFO — greater *realized* total belief-uncertainty reduction at a fixed answer budget `k`, on a labeled/replay handoff set.
- **Metric:** on a replay set of `N` handoffs each labelled with a realized post-resolution uncertainty delta `Δu_i` (from `results/`-style resolution outcomes / a synthetic labeled set), let `R(order, k) = Σ_{first k of order} Δu_i`. Compare `R(EIG, k)` vs `R(FIFO, k)` at `k = ⌈N/2⌉`, mean over ≥20 seeds (seed shuffles the FIFO arrival order + resamples the labeled set).
- **Gate:** mean `R(EIG,k) − R(FIFO,k) > 0` with 95% CI lower bound `> 0` (**beats FIFO**), ≥20 seeds. Until the gate passes, ordering is advisory-only and the UI shows both the rank and the raw filed order; nothing auto-reprioritizes an anchor or human-gated item.
- **Sandbox:** `experiments/exp_eig_ranking.py`, seeded, results to `results/`. Cite the outcome in an `inbox_ranking.py` code comment (`# see experiments/exp_eig_ranking.py — EIG beats FIFO ΔR=... [95% CI ...], N=..., 20 seeds`).

**Acceptance + runnable check.** `tests/test_inbox_ranking.py::test_rank_open_handoffs`: file 3 handoffs via `file_handoff` (one with a grounded-span dissent, one high-load/high-uncertainty, one isolated/low), inject a fixture `dep_graph`; assert (a) the grounded-span item is `rank==1` (pinned) regardless of EIG, (b) among un-pinned items the higher-EIG one precedes the lower, (c) a `handoff_id` written to `handoff_resolutions.jsonl` disappears from the result, (d) len(result)==len(open) — nothing dropped.

**Effort:** M (~70 LOC + reader). **Deps:** F28.1; FC-4 `dependency_graph` (fixture-injectable).

### F28.3 — Ranked inbox route + surface (Lane 4)

**Problem & evidence.** The existing inbox surface (`app.py:623`, rendered in `index.html`) has no value ordering and shows only candidate conflicts, not filed handoffs.

**Design.** New read route `GET /api/persona/{pid}/inbox/ranked?topic=` → `{available, items: rank_handoffs(topic=topic)}`, following the `with context.use(p)` + lazy-import pattern of the existing inbox route (`app.py:626`). Guard the FC-4 import like the existing `engine_handoff` passthrough (`app.py:1433`): if `engine`/dep-graph is unavailable, fall back to `rank_handoffs(dep_graph={"nodes":[]})` (all `load_bearing=0` → orders by uncertainty×resolvability) rather than 500. Reorder the *existing* inbox list by `rank` and render the `{eig, uncertainty, load_bearing, resolvability}` breakdown inline (legibility: show *why* this question is first) — **no new tab** (consistent with commit 353662b / 30d8302). Pinned items get a "must-escalate" marker.

**Epistemic guardrails.** Route is read-only — never files, resolves, or anchors. Renders the breakdown honestly (a proxy, labelled "expected info gain (advisory)"); shows raw filed order alongside rank until RQ-E44 passes.

**Required experiment:** trivial (rendering + passthrough; the logic is tested in F28.1/F28.2).

**Acceptance + runnable check.** `PERSONA_WORKERS=0` browser smoke: `/inbox/ranked` returns 200 with `items` sorted by `rank`, pinned item first; ranking breakdown visible in the inbox surface.

**Effort:** S. **Deps:** F28.2.

---

## 4. Sequencing

1. **F28.1** `eig_score` (pure, no deps) — land first, fully tested.
2. **F28.2** `open_handoffs()` reader (Lane-2, `inbox.py`) → `rank_handoffs` against an injected `dep_graph` fixture; wire real FC-4 once available (already shipped: `engine.dependency_graph`).
3. **RQ-E44** `experiments/exp_eig_ranking.py` — must pass its gate before ordering drives anything beyond advisory display.
4. **F28.3** Lane-4 route + surface against F28.2 (contract-first: build against `rank_handoffs` fixtures, then wire).

M0 stub: land `eig_score`/`rank_handoffs`/`open_handoffs` signatures with typed empty returns so Lane 4 can build the route immediately.

## 5. Test plan

- `test_eig_score_defaults_and_ordering` (F28.1) — defaults + monotonicity.
- `test_rank_open_handoffs` (F28.2) — read/dedup/resolve-subtract, pinned-first guardrail, no-drop invariant, EIG order among un-pinned.
- `test_open_handoffs_missing_files` — absent `handoffs.jsonl`/`handoff_resolutions.jsonl` → `[]`, no raise.
- `exp_eig_ranking.py` (RQ-E44) — ≥20 seeds, mean ΔR + 95% CI, gate = CI lower bound > 0 vs FIFO.
- Browser smoke (F28.3) — `PERSONA_WORKERS=0`, ranked order + breakdown visible.

## 6. Open questions

1. **Resolution ledger source.** FC-20 assumes an open-vs-resolved distinction; `handoff_resolutions.jsonl` does not exist yet (there is only `POST /inbox/resolve` at `app.py:721`, which acts on *conflict reviews*, not filed handoffs). **Decision taken (lazy, non-blocking):** `open_handoffs()` treats an absent resolutions file as "nothing resolved" (all filed handoffs open) — correct today, and forward-compatible when a handoff-resolution writer lands. If Lane 2/4 later add a handoff resolver, it should append `{handoff_id, at}` to `RESOLVED_NAME`. *Does not block other lanes.*
2. **`load_bearing` is RQ-E06-gated placeholder** (`dependency.py:56`). EIG inherits that provisionality; RQ-E44 measures the *ranking* end-to-end so a weak `load_bearing` shows up as a weak gate result — no separate action, but note the dependency.
3. **`max` vs `sum` over contested claims' load_bearing.** Spec uses `max` (avoid double-counting correlated claims). If RQ-E44 favors `sum`, that is a one-line change inside `eig_score` — reversible, not a contract change.

---

### Return summary

- **File:** `docs/prd/PRD-28-eig-question-ranking.md`
- **Feature ids:** F28.1 (EIG scorer), F28.2 (open-handoff reader + ranker), F28.3 (ranked route + surface).
- **New public signatures (FC-20):**
  - `persona/inbox.py`: `RESOLVED_NAME = "handoff_resolutions.jsonl"`; `open_handoffs() -> list[dict]` (rows `{handoff_id, kind, dossier, filed_at}`).
  - `persona/inbox_ranking.py`: `eig_score(dossier: dict, *, load_bearing_by_claim: dict[str,float]) -> {eig, uncertainty, load_bearing, resolvability}`; `rank_handoffs(handoffs=None, *, topic=None, dep_graph=None) -> list[dict]` (rows augmented with `eig, uncertainty, load_bearing, resolvability, rank, pinned`).
  - `persona/api/app.py`: `GET /api/persona/{pid}/inbox/ranked?topic=` (Lane 4).
- **Experiment:** RQ-E44 — EIG vs FIFO realized belief-uncertainty reduction, ≥20 seeds, gate = 95% CI lower bound of mean ΔR > 0.
- **Open questions blocking other lanes:** none blocking. Advisory: FC-4 `dependency_graph` is the only cross-lane read (already shipped, fixture-injectable via `dep_graph=`); a future handoff-resolution writer should append to `RESOLVED_NAME` (Lane 2/4, additive).
