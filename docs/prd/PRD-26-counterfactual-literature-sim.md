# PRD-26 — Counterfactual literature simulation

> **Owner lane:** 3 + 4 (Engine provides the pure function; Legibility renders the mode) · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (read-only what-if; **never** anchors or mutates a belief) · **Depends-on:** FC-4 `engine.dependency_graph` (Lane 3, live — `analysis/dependency.py:23`) · **FC-4 addition** `engine.fragility_cascade` (Lane 3, PRD-13 / CCP-13a) · PRD-03 F3.1 (the dependency DAG this reads) · PRD-13 F13.1 (the `surf-field` perturb/snapshot/re-tint UI substrate this extends) · new Lane-2 read (CCP-26b, below)

---

## 0. Summary + capability unlocked

IDEAS_BACKLOG #100 and BUILD_PLAN §3.3 ("Derivation-chain fragility propagation") ask the deepest form of the load-bearing thesis: **"If foundational study *S* had reported null, how would the field's *current consensus* differ?"** PRD-13 (`engine.fragility_cascade`) already answers the single-node version — knock out *one claim*, watch the discounted cascade. But a real foundational paper asserts **several claims at once**, and its influence on the field is the *joint* collapse of all of them, not any one in isolation. This PRD generalizes PRD-13's single-node cascade to a **paper-level perturbation set**: mark *every* claim a paper supports as fallen simultaneously, run one multi-source cascade over the dependency DAG (`analysis/dependency.py`), and report each downstream claim's projected new load-bearing and consensus shift, plus a field-level rollup.

The capability unlocked is the single most visceral demo of Persona's thesis and one **no incumbent (scite, Open Targets, PaperQA2, MedKGent) offers**: select a keystone paper, hit *"what if this had been null,"* and watch the field's argument re-settle — quantitatively, discounted by edge confidence, labelled a hypothetical. It is a *pure INFERRED what-if*: it reads the stored graph, returns a projected graph, and **touches no belief** — the same "reading a dossier never mutates a belief" discipline the inbox (`persona/api/app.py:696`) and PRD-13 already enforce. The engine work (Lane 3) is a small, deterministic extension of the traversal PRD-13 introduces; the render (Lane 4) is a sibling *mode* on the flagship `surf-field` map that reuses PRD-13's snapshot/re-tint machinery. It inherits **RQ-E06** (dependency-edge precision) as its only trust gate — the cascade is only as real as the edges under it, and until RQ-E06 passes it renders under F4.1's *candidate / unvalidated heuristic* label exactly like the map it rides on.

---

## 1. File ownership (disjoint)

| File | Lane | New/Edit | Notes |
|---|---|---|---|
| `persona/analysis/dependency.py` | **3** | **Edit** | Add `counterfactual(...)` + a shared internal `_propagate(seeds, edges, lb_map)` traversal helper (extracted from / shared with PRD-13's `fragility_cascade`). Lane-3-exclusive per PRD-00 §3 and PRD-03 §1. |
| `persona/analysis/engine.py` | **3** | **Edit** | Re-export `counterfactual` from the FC-4 facade (one import + `__all__` line — the file's docstring already says "Add fragility_cascade / trajectory here as they land"). |
| `persona/api/app.py` | **4** | **Edit — ONE new route** | `GET /api/persona/{pid}/engine/counterfactual` — thin pass-through over `engine.counterfactual`, clamps `delta` at the boundary. NEW route only; do not touch existing route bodies (PRD-04 §1). |
| `persona/api/static/index.html` | **4** | **Edit — flagship `surf-field` only** | Add a **"counterfactual" mode toggle** to the F13.1 perturb panel + `counterfactualWhatIf(paperSlug, delta)` / reuse `resetCascade()`. No new spine destination (rides `surf-field`). |
| `tests/test_epistemic_api.py` | **4** | **Edit — ADD one test** | `test_counterfactual_route_shape` (envelope + no-mutation KG-spy). Shared new-tests file owned by Lane 4 in PRD-04 §1. |
| `tests/ui_legibility_smoke.cjs` | **4** | **Edit — ADD one step** | "select paper → counterfactual → cascade + banner → reset" browser step (Lane 4, PRD-04 §1). |

**Boundary files another lane owns (decoupled by an FC / CCP — this lane never edits them):**
- `persona/memory/kg.py` — **Lane 2 owns.** This PRD needs a *source→claims* read (all claim_ids a paper supports); no unbounded one exists (`neighborhood("source", …)` caps at 25, `kg.py:611`). Proposed as **CCP-26b** (below); until acked, the engine falls back to the capped `neighborhood` read and flags `truncated:true`. We never edit `kg.py`.

**Intra-repo dependency (not a parallel-edit collision):** `dependency.py`'s `fragility_cascade` + `_propagate` helper are landed by **PRD-13 / CCP-13a (Lane 3)**. Both are Lane 3, same file — sequence within the lane: CCP-13a's `fragility_cascade` first, then this PRD extracts/reuses `_propagate` and adds `counterfactual`. The `surf-field` perturb panel + snapshot/re-tint are landed by **PRD-13 F13.1 (Lane 4)**; this PRD adds a *mode toggle* beside PRD-13's slider — same file, same lane, sequence after F13.1. No second lane touches either file.

---

## 2. FCs provided / consumed + CONTRACT CHANGE PROPOSALs

**PROVIDES:** none new cross-lane. The `GET /engine/counterfactual` route is a Lane-4 transport seam consumed only by `index.html` (same lane).

**CONSUMES:**
- **FC-4** (Lane 3): `engine.dependency_graph(topic)` — the source of the flagship map and of the `load_bearing` map the cascade recomputes from.
- **FC-4 addition** `engine.fragility_cascade` (PRD-13 / CCP-13a) — this PRD reuses its `_propagate` traversal core.
- **FC-3** (Lane 2): the new `kg.claims_for_source` (CCP-26b) for the source→claims mapping.

### CONTRACT CHANGE PROPOSAL — CCP-26a (routes to **Lane 3**; ack by master + Lane 3 + Lane 4 before wiring the real path)

Add one function to FC-4 (implemented in `analysis/dependency.py`, re-exported from `analysis/engine.py`):

```
engine.counterfactual(paper_slug: str, *, topic: str | None = None, delta: float = -1.0)
    -> {perturbed_claims: [claim_id],
        affected: [{claim_id, new_load_bearing: float, consensus_delta: float}],
        summary: {n_perturbed: int, n_affected: int, load_bearing_lost: float,
                  newly_fragile: int, headline: str},
        applicable: bool,
        truncated: bool}
```

**Semantics (specified so Lane 3 builds without guessing):**
- **Perturbed set.** `paper_slug` → `kg.claims_for_source(paper_slug)` (CCP-26b) → the list of every LIVE claim the paper supports = `perturbed_claims`. Each is seeded at `delta` (default `-1.0` = "reported null / fully fallen"; `delta ∈ [-1.0, 0.0]`, clamped; `delta ≥ 0` is a no-op returning `affected:[]`). This is exactly PRD-13's single-node perturbation applied to the *set* of the paper's claims at once — "perturb ALL of a key paper's claims" (BUILD_PLAN §3.3).
- **Traversal = multi-source `_propagate`.** Reuse PRD-13's traversal *unchanged*: walk **incoming** dependency edges (`dst ∈ perturbed_set` → their `src` dependents, recurse), skipping `contradicts`/`qualifies` in v1 (same deferral as PRD-13 Open Q2). The *only* generalization is the seed frontier: instead of one seed node, the BFS starts from **all** `perturbed_claims` simultaneously. `_propagate(seeds: dict[claim_id, float], edges, lb_map) -> dict[claim_id, accumulated_delta]` is the shared core; `fragility_cascade` calls it with `seeds={claim_id: delta}`, `counterfactual` with `seeds={c: delta for c in perturbed_claims}`.
- **Discounting (BUILD_PLAN §3.3 "discounting by edge confidence").** Transmitted perturbation over an edge with `confidence=c` is `delta × c`; multiply confidences along a multi-hop path. When a downstream `D` is reachable from several perturbed seeds (or several paths), take the **maximum-magnitude** coupling (`min` of the signed accumulated deltas) — the tightest dependence — never a sum, to avoid double-counting shared ancestry. Identical rule to PRD-13; the set case just means `D` may be reached from several seeds.
- **Recompute + report.** For each affected `D` (a downstream dependent **not itself in** `perturbed_claims`): `new_load_bearing = max(0.0, old_load_bearing × (1 + accumulated_delta_D))` where `old_load_bearing` is `D`'s current FC-4 value and `accumulated_delta_D ∈ [-1,0]`. **`consensus_delta = accumulated_delta_D`** — the projected *fractional* shift in the field's support for `D` under the counterfactual (a computed graph quantity, in `[-1,0]`; `-0.34` = "the field's support for this downstream conclusion drops ~34% if the paper had been null"). Reported per affected claim alongside `new_load_bearing`.
- **Summary rollup (field-level, the "how would consensus differ" answer).** `n_perturbed = len(perturbed_claims)`; `n_affected = len(affected)`; `load_bearing_lost = Σ(old_load_bearing − new_load_bearing)` over affected (total load-bearing mass the field sheds); `newly_fragile` = count of affected claims whose `new_load_bearing` crosses below the map's fragile band (i.e. drop that would re-tint them fragile); `headline` = one deterministic templated sentence (e.g. *"If «paper» had reported null, N downstream claims weaken (M newly fragile); the field sheds L load-bearing mass."*). No model call — pure string assembly from the numbers.
- **Purity / termination.** No model call, no KG write, no belief mutation — a pure read over `kg.dependency_edges(topic)` + `kg.claims_for_source(slug)` + the current `load_bearing` map. Bounded multi-source BFS (visited-set + depth cap) so a cyclic dependency graph terminates (same discipline as PRD-13 and `retraction.contamination`, PRD-03 F3.6).
- **Abstain.** `applicable: False, affected: [], perturbed_claims: []` when the slug has **no live claims** or none of its claims are depended upon (nothing rests on the paper) — abstain, don't fabricate an empty cascade as "the field is robust to this paper being wrong."
- **`truncated`.** `True` only when CCP-26b is unavailable and the engine fell back to the capped `neighborhood` read (>25 claims possible) — an honesty flag so the UI never presents a partial perturbation set as complete. `False` once CCP-26b lands.

**Why an FC-4 addition, not a signature change:** purely additive (a new function beside `dependency_graph`/`value_queue`/`fragility_cascade`); no existing FC-4 caller changes. Flagged as a CCP per PRD-00 §4 because FC-4 is frozen.

**Trust gate:** the counterfactual's numbers are only as real as the edges under them, so the function **inherits RQ-E06** (dependency-edge precision ≥ 0.70 + load-bearing Spearman ρ ≥ 0.6, PRD-03 F3.1), exactly as PRD-13 does. Until RQ-E06 passes, every counterfactual render carries F4.1's *candidate / unvalidated* label.

### CONTRACT CHANGE PROPOSAL — CCP-26b (routes to **Lane 2**; ack by master + Lane 2 + Lane 3 before wiring the real path)

Add one read to FC-3 (`persona/memory/kg.py`, Lane-2-owned):

```
kg.claims_for_source(slug: str) -> [claim_id]   # every LIVE (valid_to IS NULL) claim SUPPORTED_BY the source; unbounded
```

**Why needed:** `kg.provenance(claim_id)` maps *claim → sources* (the reverse of what a paper-level perturbation needs), and the only *source → claims* read, `neighborhood("source", slug)` (`kg.py:608`), **caps at 25 and is UI-shaped**. A foundational paper can back >25 claims; silently dropping the tail would understate the cascade — a silent-wrong-number failure, the worst kind for this system (CLAUDE.md §4). One-line Cypher mirroring the existing pattern: `MATCH (c:Claim)-[:SUPPORTED_BY]->(s:Source {slug:$k}) WHERE c.valid_to IS NULL RETURN c.claim_id`. Additive, backward-compatible; `neighborhood` unchanged. **Until acked, the engine uses the capped `neighborhood` read and sets `truncated:true`** — degraded but never silently wrong.

---

## 3. Features

### F26.1 — Paper-level counterfactual cascade (`engine.counterfactual`)

**Problem & evidence.** BUILD_PLAN §3.3 and §3.2 pose the whole-literature what-if: *"if this foundational claim fell, what fraction of the field's current conclusions become unsupported?"* (`Initial Planning Docs/BUILD_PLAN.md:107`), and §3.3 names the mechanism — *"graph traversal over the dependency DAG from the perturbed node, discounting by edge confidence; recompute downstream load-bearing/confidence and emit a 'fragility cascade' report"* (`BUILD_PLAN.md:121`). PRD-13 delivers this for **one node** (`engine.fragility_cascade`, CCP-13a). But a foundational *study* is not one claim — the current `dependency.py` node set shows each paper backs multiple claims (each `SUPPORTED_BY` a `Source`, `kg.py:258`), and the field's dependence on the paper is the **joint** collapse of all of them. IDEAS_BACKLOG #100 scopes exactly this generalization: *"perturb a key paper and recompute the argument/dependency state … extends fragility_cascade (FC-4)"* (`docs/prd/IDEAS_BACKLOG.md:189`). No incumbent represents science as a stress-testable dependency structure at all (BUILD_PLAN §3.2 "Why it's new").

**Design (files, signatures, data flow, seams).**

*Engine — `analysis/dependency.py` (Lane 3), reusing PRD-13's traversal core:*
```python
def _propagate(seeds: dict, edges: list, lb_map: dict, *, max_depth: int = 64) -> dict:
    """Shared multi-source cascade core (PRD-13 + PRD-26). seeds: {claim_id: delta in [-1,0]}.
    Walk INCOMING dependency edges from every seed; accumulate delta × Π(edge confidence);
    on multiple paths keep the max-magnitude (min signed) coupling. Bounded BFS -> terminates
    on cycles. Pure: no KG write, no model. Returns {claim_id: accumulated_delta} for reached
    dependents (seeds excluded from the result). See BUILD_PLAN §3.3."""

def counterfactual(paper_slug: str, *, topic: str | None = None, delta: float = -1.0, kg=None) -> dict:
    """FC-4 addition (CCP-26a): perturb EVERY claim a paper supports at once and recompute the
    field's downstream argument state — the paper-level generalization of fragility_cascade.
    Pure INFERRED what-if; never mutates a belief. See BUILD_PLAN §3.3, IDEAS_BACKLOG #100."""
```
- `counterfactual` resolves `perturbed_claims = kg.claims_for_source(paper_slug)` (CCP-26b; capped-`neighborhood` fallback → `truncated=True`), reads `dependency_graph(topic)` for the `edges` + `old_load_bearing` map, builds `seeds = {c: clamp(delta) for c in perturbed_claims}`, calls `_propagate(seeds, edges, lb_map)`, then recomputes `new_load_bearing`/`consensus_delta` per affected node and assembles `summary`. `fragility_cascade` (PRD-13) is refactored to call the same `_propagate` with a single-key `seeds` — one traversal, two entry points (no duplicated graph code).

*Facade — `analysis/engine.py` (Lane 3):* add `from .dependency import counterfactual` and append to `__all__`.

*Route — `app.py` (Lane 4), mirrors PRD-13's `/engine/fragility`:*
```python
@app.get("/api/persona/{pid}/engine/counterfactual")
def engine_counterfactual(pid: str, paper_slug: str, delta: float = -1.0, topic: str = ""):
    """Hypothetical what-if: if `paper_slug` had reported null, how does the field's consensus shift?
    Read-only — never anchors or mutates a belief (engine.counterfactual is pure)."""
    delta = max(-1.0, min(0.0, delta))            # clamp at the trust boundary
    with context.use(_p(pid)):
        from ..analysis import engine
        return engine.counterfactual(paper_slug, topic=topic or None, delta=delta)
```

*Data flow:* UI paper-pick → `GET /engine/counterfactual?paper_slug=&delta=&topic=` → `engine.counterfactual` (pure) → `{perturbed_claims, affected, summary, applicable, truncated}` → client re-tints downstream nodes from the F13.1 snapshot toward `new_load_bearing`, stamps per-node `consensus_delta`, renders `summary.headline`. Seams: `kg.claims_for_source` (CCP-26b), `kg.dependency_edges` / `dependency_graph` (FC-4, live), `_propagate` (PRD-13). Never re-fetches the true graph, so the real state is one `resetCascade()` away.

**Epistemic guardrails.**
- **Hypothetical, never a write.** Route + `counterfactual` are read-only; no admit/anchor/belief-mutation path is reachable. A KG-spy property test asserts zero `kg.*` writes during the call. The UI banner labels every cascade *"COUNTERFACTUAL · hypothetical — no belief changed,"* mirroring `app.py:696` and PRD-13.
- **Discounted by evidence, not asserted.** `consensus_delta = delta × Π(edge confidence)` over the dependency path — a computed graph quantity, never a model opinion (no-fabricated-confidence). A counterfactual over low-confidence edges visibly decays; a paper the field rests on via high-confidence chains visibly collapses it.
- **Inherits the map's honesty label + RQ-E06.** `load_bearing` is still the F3.1 structural placeholder (`dependency.py:57` "Do NOT present as a validated importance metric"); until RQ-E06 passes, every `new_load_bearing`/`consensus_delta` renders under F4.1's *candidate / unvalidated heuristic* label. The counterfactual never upgrades a candidate cascade to a validated one.
- **Abstain over fabricate.** `applicable:False` (no live claims, or nothing rests on the paper) renders *"nothing in the current graph depends on this paper,"* not a fake robust cascade. `truncated:true` (fallback path) explicitly warns the perturbation set may be partial.
- **Provenance unchanged.** The output is typed INFERRED (a projection); it never appears in `provenance_breakdown`, never becomes READ/TESTED/HUMAN_CONFIRMED, never enters the belief store.

**Required experiment — RQ-E42 (OPTIONAL; register in `docs/RESEARCH_QUALITY_PROGRAM.md`).**
The propagation math carries **no new seeded experiment**: it is deterministic graph arithmetic and *inherits RQ-E06* (PRD-03 F3.1) as its trust gate — identical stance to PRD-13 F13.1 (don't gold-plate a deterministic function, CLAUDE.md §2). Two guards instead of a 20-seed sweep:
1. a deterministic **property test** (acceptance below) over a hand-built fixture DAG — multi-source seeding, confidence-discount, max-magnitude coupling, termination on a cycle, no-mutation, abstain;
2. **RQ-E42** *(optional face-validity gate; next-free-after-siblings — see Open Q1)* lifted from BUILD_PLAN H3.3 / §3.3: **Hypothesis** — on **known-collapse cases** (foundational papers later retracted or failed-to-replicate, drawn from the RQ-E06 gold subfield + Retraction-Watch signal via FC-6), the counterfactual's affected-set is face-valid to an expert and its ranking of "most-destabilized downstream claims" agrees with expert judgment above a citation-count baseline. **Metric:** expert agreement rate on N cascades + Spearman(our affected-ranking, expert) > Spearman(citation-count, expert). **Gate:** counterfactuals stay labelled "hypothetical what-if" regardless; RQ-E42 only governs whether the map may ever call a consensus-delta a *validated* number (it may not until **both** RQ-E06 and RQ-E42 pass). **Seeds:** qualitative/agreement over N≥8 expert-reviewed cases (a labelling study, not a stochastic sweep — H3.3's design). RQ-E42 is **not** a blocker for shipping the interactive render.

**Acceptance + ONE runnable check.**
- (a) `GET /engine/counterfactual?paper_slug=<keystone>&delta=-1.0` returns `{perturbed_claims, affected, summary, applicable, truncated}`; every `affected[i]` has `claim_id`, `new_load_bearing ≤` that node's stored `load_bearing`, `consensus_delta ∈ [-1,0]`; no `affected` claim is in `perturbed_claims`.
- (b) A paper backing a keystone claim with ≥1 dependent yields non-empty `affected` and `summary.n_affected ≥ 1`; a paper whose claims nothing derives from yields `applicable:False, affected:[]`.
- (c) A paper's **joint** counterfactual weakens ≥ as many claims as knocking out any single one of its claims via `fragility_cascade` (the set-vs-node monotonicity that justifies the generalization).
- (d) `delta` clamp: a `+0.5` query is treated as `0.0` → `affected:[]`. The call performs **zero** KG writes.
- (e) Browser: selecting a paper in counterfactual mode re-tints ≥1 downstream node, shows per-node `consensus_delta` labels, the `summary.headline`, and the "hypothetical — no belief changed" banner; `reset` restores stored values.
- **Runnable check:** `tests/test_epistemic_api.py::test_counterfactual_route_shape` — against a fixture persona whose `engine.counterfactual` is stubbed (or the real Lane-3 fn once landed): assert envelope keys, `new_load_bearing ≤ old`, `consensus_delta ∈ [-1,0]`, `applicable:False` on a no-dependents paper, `delta` clamp, and — via a KG spy — that no `kg.*` write method was called. Engine-side deterministic property test named `tests/test_dependency.py::test_counterfactual_perturbs_paper_set` (Lane 3, see §5). Browser step in `tests/ui_legibility_smoke.cjs`.

**Effort** S–M (engine: a set-seeded reuse of PRD-13's `_propagate` + summary assembly + CCP-26b read; UI: a mode toggle over F13.1's existing snapshot/re-tint). **Deps** PRD-13 (`fragility_cascade` + `_propagate`, `surf-field` perturb panel), FC-4 `dependency_graph` (live), CCP-26a (Lane 3), CCP-26b (Lane 2).

### F26.2 — "Counterfactual" mode on the flagship dependency map

**Problem & evidence.** PRD-13 F13.1 makes `surf-field` interactive for a *single* node (a per-node slider + "knock it out"). The paper-level what-if needs a *paper* as the perturbation subject, not a claim — a different selection affordance over the same map and the same snapshot/re-tint/banner machinery. The product thesis is legibility (CLAUDE.md §5): "watch the field's argument buckle when you pull out one keystone *paper*" is the money-shot demo.

**Design.** Extend PRD-13's perturb panel (do not rebuild it) with a **mode toggle**: `[ claim | paper ]`. In *paper* mode the panel shows a source-picker (fed by the node-detail panel's source list / `kg.neighborhood` the map already loads) instead of the per-node slider; selecting a paper fires `counterfactualWhatIf(paperSlug, delta=-1.0)` → `GET /engine/counterfactual` → re-tint every `affected` node from the F13.1 snapshot toward its `new_load_bearing`, stamp `consensus_delta` labels, and render `summary.headline` in the hypothetical banner (*"COUNTERFACTUAL · If «paper» had reported null: N downstream weaken, M newly fragile"*). `resetCascade()` (PRD-13, reused verbatim) restores the snapshot and clears the banner. If `truncated:true`, the banner appends *"(partial — >25 claims)"*. Motion discipline per CLAUDE.md §5 / PRD-13: animate only on a real perturb/reset, honour `prefers-reduced-motion`, colour never carries the what-if state alone (banner text + per-node magnitude labels do).

**Epistemic guardrails.** Same as F26.1 (b)–(d): hypothetical banner, candidate/unvalidated label until RQ-E06, abstain/`truncated` surfaced, never re-fetches the true graph.

**Required experiment.** Trivial (a UI mode over server data — the perturb is a UI event). Covered by the browser smoke step.

**Acceptance + ONE runnable check.** F26.1 (e). Runnable check: the `ui_legibility_smoke.cjs` step (§5).

**Effort** S. **Deps** F26.1 route; PRD-13 F13.1 (`surf-field` perturb panel + snapshot + `resetCascade`).

---

## 4. Sequencing

1. **M0 (hour 1, unblocks the frontend):** land `GET /engine/counterfactual` as a **stub** returning `{perturbed_claims:[], affected:[], summary:{...zeros, headline:""}, applicable:False, truncated:False}` so the `surf-field` mode toggle can be built and smoke-tested against a typed empty payload (matches PRD-04 §4 / PRD-13 M0 "routes as thin stubs").
2. **After PRD-13 lands `_propagate` + `fragility_cascade` (Lane 3, same file):** add `counterfactual` reusing `_propagate` (set-seeded); wire `engine.py` re-export. Depends on CCP-26a ack.
3. **After CCP-26b ack (Lane 2 ships `kg.claims_for_source`):** swap the capped `neighborhood` fallback for the unbounded read; set `truncated:false`. Until then the engine ships against the fallback (degraded, never silently wrong).
4. **After PRD-13 F13.1 lands the `surf-field` perturb panel (Lane 4, same file):** add the mode toggle + `counterfactualWhatIf`; wire to the stub, then the real route. Run the property + route + browser checks.
5. **RQ-E42** face-validity review runs on Lane 3's thread whenever the RQ-E06 gold subfield + a known-collapse case set are available; it never blocks the interactive ship (cascades are labelled hypothetical throughout).

---

## 5. Test plan

- **Route/API (`tests/test_epistemic_api.py`):** `test_counterfactual_route_shape` — envelope keys; `new_load_bearing ≤ old`; `consensus_delta ∈ [-1,0]`; affected ∩ perturbed = ∅; `delta` clamp (a `+0.5` query → `affected:[]`); no-dependents paper → `applicable:False`; **no-KG-mutation spy** (the headline guardrail, mirrors PRD-13 F13.1 and PRD-03 F3.4).
- **Engine property test (Lane 3, `tests/test_dependency.py::test_counterfactual_perturbs_paper_set`):** hand-built fixture DAG + a fake KG whose `claims_for_source("paperS")` returns 2 of the DAG's nodes; assert (i) both seeds propagate (multi-source frontier), (ii) a downstream reached from both seeds takes the **max-magnitude** (min signed) coupling, not a sum, (iii) grandchild `consensus_delta = delta × c1 × c2`, (iv) the set counterfactual's affected ⊇ any single-claim `fragility_cascade`'s affected (set-vs-node monotonicity, acceptance (c)), (v) BFS terminates on an injected cycle, (vi) `delta ≥ 0` is a no-op, (vii) a paper with no live claims → `applicable:False`, (viii) fallback path sets `truncated:True`, real `claims_for_source` sets `truncated:False`. Extend `dependency.py`'s `__main__` self-check with a minimal counterfactual assertion (no DB, fake KG — same pattern as `dependency.py:69`).
- **Browser smoke (`tests/ui_legibility_smoke.cjs`, new step):** open `surf-field`, toggle to *paper* mode, pick a keystone paper → assert ≥1 downstream node changes tint, `consensus_delta` labels + `summary.headline` + the "hypothetical — no belief changed" banner appear, `reset` restores the pre-perturb DOM; no horizontal overflow at 1280/760/390 px; `Esc`/reset clears the what-if.
- **Regression:** existing `test_integrity_boundaries.py`, `test_calibration.py`, PRD-13's fragility route/property tests, and the F4.1 map smoke must pass unchanged — this PRD adds one function, one route, one UI mode; mutates no existing route body, no belief path, and (via the shared `_propagate`) no PRD-13 behaviour.

---

## 6. Open questions

- **Q1 (RQ id collision — non-blocking, confirm before registering).** This PRD uses **RQ-E42** per the task brief. The registry's next-free at snapshot was **E40**; E40/E41 are assumed claimed by concurrently-authored sibling PRDs. Confirm E40/E41 are taken (else renumber this to the true next-free) when reconciling `docs/RESEARCH_QUALITY_PROGRAM.md` — PRD-00 §8 governs. RQ-E42 is optional and blocks nothing.
- **Q2 (CCP-26a ratification — blocks Lane 3 real path).** Confirm `engine.counterfactual(paper_slug, *, topic=None, delta=-1.0) -> {perturbed_claims, affected:[{claim_id,new_load_bearing,consensus_delta}], summary, applicable, truncated}` and that it reuses PRD-13's `_propagate` (i.e. CCP-13a lands `_propagate` as an extractable core, not a monolithic `fragility_cascade`). If PRD-13 ships `fragility_cascade` monolithic first, this PRD extracts `_propagate` and re-points `fragility_cascade` at it in the same Lane-3 change — flag to PRD-13's owner so the refactor is coordinated, not a surprise.
- **Q3 (CCP-26b ratification — blocks Lane 2; degraded fallback meanwhile).** Confirm `kg.claims_for_source(slug) -> [claim_id]` (unbounded, LIVE-only) as an additive FC-3 read. Until acked, the engine uses the capped `neighborhood` read with `truncated:true`; a foundational paper backing >25 claims would then under-report — acceptable as a *flagged* degradation, not as a silent one.
- **Q4 (`consensus_delta` definition — confirm the metric).** v1 defines `consensus_delta` = the discounted accumulated perturbation reaching a downstream claim (`delta × Π(edge confidence)`, in `[-1,0]`) — "projected fractional drop in the field's support for this claim." An alternative is to fold in `citation_support_ratio`/`independent_labs` for a richer per-claim consensus scalar. Recommend the pure graph quantity for v1 (deterministic, inherits RQ-E06, no new signal to validate); revisit if RQ-E42 face-validity wants a richer consensus proxy. Non-blocking.
- **Q5 (signed / strengthening extension — deferred, inherits PRD-13 Open Q2).** v1 models weakening only (`delta ∈ [-1,0]`, skips `contradicts`/`qualifies`). A fuller model would let a null paper *strengthen* whatever its claims contradicted (positive downstream delta via `contradicts`-inversion) and allow "what if this had been *confirmed*?" (`delta > 0`). Shares PRD-13's deferral; needs its own face-validity check. Non-blocking; affects only how much of RQ-E42 we claim.
