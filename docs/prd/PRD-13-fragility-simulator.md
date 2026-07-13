# PRD-13 — Interactive fragility "what-if" simulator

> **Owner lane:** 4 (Legibility/UI/API) · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (read-only what-if; **never** anchors or mutates a belief) · **Depends-on:** PRD-04 F4.1 (flagship `surf-field` dependency map, same lane) · FC-4 `engine.dependency_graph` (Lane 3) · **FC-4 addition** `engine.fragility_cascade` (Lane 3 — see CONTRACT CHANGE PROPOSAL CCP-13a)

---

## 0. Summary + capability unlocked

BUILD_PLAN §3.3 ("Derivation-chain fragility propagation") is the one instrument the flagship map still fakes. PRD-04 F4.1 already renders a clicked node's *static* "if this fell, **N** downstream weaken" as a client-side transitive count over the server edge list (`docs/prd/PRD-04-legibility-benchmarks.md:75`). That answers *how many* but not *by how much*, and it is inert — the reviewer cannot **feel** the cascade. This PRD makes the map interactive: the user marks a node **fallen or weakened** (a `delta`), and the fragility cascade recomputes **live** — every downstream claim's `load_bearing` is re-derived by graph traversal from the perturbed node, discounting by edge confidence exactly as BUILD_PLAN §3.3 / §6.4 prescribe ("if this fell, these N downstream conclusions weaken … discounting by edge confidence"). The capability unlocked is the most visceral demo of the load-bearing thesis: *watch the field's argument buckle when you pull out one keystone* — a stress-test no incumbent (scite, Open Targets, PaperQA2) offers. Rendering is trivial (Lane 4); the propagation math is a small pure function Lane 3 provides on the dependency DAG it already builds (F3.1), inheriting RQ-E06's dependency-edge precision as its trust gate. The cascade is a clearly-labelled **hypothetical INFERRED what-if**: it reads the stored graph, returns a projected graph, and touches no belief — the same "reading a dossier never mutates a belief" discipline the inbox already enforces (`persona/api/app.py:696`).

---

## 1. File ownership (disjoint)

| File | New/Edit | Notes |
|---|---|---|
| `persona/api/app.py` | **Edit — ONE new route** | `GET /api/persona/{pid}/engine/fragility` — thin pass-through over FC-4 `fragility_cascade`. Do not modify existing route bodies (matches PRD-04 §1 "NEW routes only"). |
| `persona/api/static/index.html` | **Edit — flagship `surf-field` interaction only** | Add the perturb control + live-cascade render to the node-detail panel PRD-04 F4.1 creates. Add `fragilityWhatIf()` / `resetCascade()`; no new spine destination (rides the existing `surf-field`). |
| `tests/test_epistemic_api.py` | **Edit — ADD one test** | `test_fragility_route_shape` (route contract + no-mutation guard). Shared new-tests file already owned by Lane 4 in PRD-04 §1. |
| `tests/ui_legibility_smoke.cjs` | **Edit — ADD one step** | Perturb-and-cascade browser step. Owned by Lane 4 in PRD-04 §1. |

**Boundary files another lane owns (decoupled by an FC — this lane never edits them):**
- `persona/analysis/engine.py` + `persona/analysis/dependency.py` — **Lane 3 owns.** This lane only *calls* `engine.fragility_cascade(claim_id, delta)` (the FC-4 addition). If the call shape is wrong we file against Lane 3; we do not edit the module. (PRD-03 §1 already lists these as Lane-3-exclusive.)

**Intra-lane dependency (not a cross-lane boundary):** `surf-field` and the `/engine/*` route family are created by PRD-04 F4.1 (also Lane 4). PRD-13 **extends** F4.1's node-detail panel — it must land after F4.1, and it replaces F4.1's static "N downstream weaken" count with the live magnitude-aware cascade. No second lane edits these files, so there is no parallel-edit collision; sequence within Lane 4 (F4.1 → this).

---

## 2. FCs provided / consumed + CONTRACT CHANGE PROPOSAL

**PROVIDES:** none new. The `GET /engine/fragility` route is a Lane-4 transport seam consumed only by `index.html` (same lane) — not a cross-lane contract.

**CONSUMES:**
- **FC-4** (Lane 3): `engine.dependency_graph(topic) -> {nodes:[{claim_id,statement,load_bearing:float,independent_labs:int,support_ratio:float,provenance,fragile:bool}], edges:[{src,dst,rel_type,confidence,span}]}` — already the source of the flagship map (PRD-04 F4.1). The simulator perturbs a node *in this returned graph*.
- **FC-4 addition** `engine.fragility_cascade(...)` — see CCP-13a.

### CONTRACT CHANGE PROPOSAL — CCP-13a (routes to **Lane 3**; must be acked by master + Lane 3 + Lane 4 before it lands)

Add one function to FC-4 (implemented in `analysis/dependency.py`, re-exported from `analysis/engine.py` per PRD-03 §1's `engine` facade):

```
engine.fragility_cascade(claim_id: str, delta: float, topic: str | None = None)
    -> {affected: [{claim_id: str, new_load_bearing: float, delta: float}], perturbed: str, applicable: bool}
```

**Semantics (specified so Lane 3 builds without guessing):**
- `delta ∈ [-1.0, 0.0]` — the downward perturbation of the node's truth/support. `-1.0` = fully fallen; `-0.4` = weakened 40%. Values are **clamped** to this range; `delta ≥ 0` is a no-op returning `affected:[]` (v1 models weakening only — see Open Q2 for the strengthening/`contradicts`-inversion extension).
- **Traversal.** Reuse the same edge convention as F3.1's `load_bearing` PageRank: a dependent `D` that rests on the perturbed node `A` appears as an edge `{src: D, dst: A, rel_type ∈ {derives_from, presupposes, operationalizes, generalizes, extends, supports}}` (edges point *toward* the foundation, which is why PageRank scores keystones). To find what weakens when `A` falls, walk **incoming** edges (`dst == A`) to their `src` dependents, then recurse. Skip `contradicts`/`qualifies` edges in v1 (they don't propagate a weakening; a `contradicts` edge would *strengthen* the other side — deferred, Open Q2).
- **Discounting (BUILD_PLAN §3.3 "discounting by edge confidence").** For a dependent `D` reached from `A` over edge with `confidence = c`, the transmitted perturbation is `delta_A × c`. Over a multi-hop path, multiply the confidences along the path. When multiple paths reach `D`, take the path of **maximum magnitude** (`min` of the signed accumulated deltas — the tightest coupling) rather than summing, to avoid double-counting shared ancestry.
- **Recompute.** `new_load_bearing = max(0.0, old_load_bearing × (1 + accumulated_delta_D))` where `old_load_bearing` is the node's current FC-4 value and `accumulated_delta_D ∈ [-1,0]`. Report `delta = new_load_bearing - old_load_bearing` per affected node.
- **Purity / termination.** No model call, no KG write, no belief mutation — a pure read over `kg.dependency_edges(topic)` + the current `load_bearing` map. Bounded BFS (visited-set + depth cap) so a cyclic dependency graph terminates (same discipline as `retraction.contamination`'s bounded walk, PRD-03 F3.6).
- **Abstain.** `applicable: False`, `affected: []` when `claim_id` is not in the graph or has no incoming dependency edges (nothing rests on it) — abstain, don't fabricate an empty cascade as "robust."

**Why an FC-4 addition and not a signature change:** it is purely additive (a new function beside `dependency_graph`/`value_queue`); no existing FC-4 caller changes. Flagged as a CCP per PRD-00 §4 because FC-4 is a frozen contract.

**Trust gate:** the cascade's numbers are only as real as the edges under them, so the function **inherits RQ-E06** (dependency-edge precision ≥ 0.70 + load-bearing Spearman ρ ≥ 0.6, PRD-03 F3.1). Until RQ-E06 passes, both the dependency map *and* every cascade render carry the *candidate / unvalidated* label F4.1 already shows — the simulator changes nothing about that discipline.

---

## 3. Features

### F13.1 — Live fragility what-if on the flagship dependency map

**Problem & evidence.** BUILD_PLAN §6.4 specifies the assumption-graph screen as: "Click a node → 'if this fell, these N downstream conclusions weaken' (fragility preview)." PRD-04 F4.1 delivers only the static count: *"if this fell, **N** downstream weaken … done client-side over the server-supplied edge list; this is presentation of server data, not a new metric"* (`docs/prd/PRD-04-legibility-benchmarks.md:75`). The count answers *how many* but never *by how much*, and it is not interactive — the reviewer cannot mark a node fallen and watch the field re-settle. BUILD_PLAN §3.3 is explicit that the missing layer is *propagation*: "graph traversal over the dependency DAG from the perturbed node, discounting by edge confidence; recompute downstream load-bearing/confidence and emit a 'fragility cascade' report" (`Initial Planning Docs/BUILD_PLAN.md:121`). The current UI seam this replaces is the honest but inert `index.html:2003` degree-heuristic in the Review surface and the F4.1 static count in `surf-field`.

**Design (files, signatures, data flow, seams).**

*Backend — one thin route (`app.py`, mirrors PRD-04 F4.1's `/engine/dependency`):*
```python
@app.get("/api/persona/{pid}/engine/fragility")
def engine_fragility(pid: str, claim_id: str, delta: float = -1.0, topic: str = ""):
    """Hypothetical what-if: project the fragility cascade if `claim_id` weakened by `delta`.
    Read-only — never anchors or mutates a belief (FC-4 fragility_cascade is pure)."""
    delta = max(-1.0, min(0.0, delta))            # clamp at the trust boundary
    with context.use(_p(pid)):
        from ..analysis import engine
        return engine.fragility_cascade(claim_id, delta, topic or None)
```
Returns the CCP-13a envelope verbatim: `{affected, perturbed, applicable}`.

*Frontend — extend the F4.1 node-detail panel (`index.html`, `surf-field`), no new spine destination:*
- The node-detail panel F4.1 opens on node-click gains a **perturb control**: a labelled slider `Mark this claim: [ fallen ——●—— intact ]` bound to `delta` (`-1.0 … 0.0`), plus a one-click **"knock it out"** button (`delta = -1.0`) and a **reset** button.
- `fragilityWhatIf(claimId, delta)` → `GET /engine/fragility?claim_id=&delta=&topic=` → on the returned `affected[]`, re-tint each downstream node toward its `new_load_bearing` (radius/opacity interpolates from the stored value to the projected one) and stamp a per-node magnitude label ("−0.34"). A hypothetical banner overlays the map: **"WHAT-IF · hypothetical — no belief changed."**
- `resetCascade()` restores the map to the FC-4 `dependency_graph` values (kept in a client-side snapshot taken on `openField()`), clearing the banner. Reset is also automatic on topic change or node deselect.
- Motion discipline (CLAUDE.md §5 / `SCIENTIFIC_WORKBENCH_SPEC.md`): nodes animate **only** on a real perturb/reset event, honour `prefers-reduced-motion` (instant swap when set); colour never carries the what-if state alone — the banner (text) + per-node magnitude labels do.

*Data flow:* `openField()` snapshots FC-4 `dependency_graph` → user clicks node → slider/knockout fires `fragilityWhatIf` → `GET /engine/fragility` → `engine.fragility_cascade` (pure, Lane 3) → `{affected}` → client re-tints from the snapshot (never re-fetches the true graph, so the true state is always one `resetCascade()` away).

**Epistemic guardrails.**
- **Hypothetical, never a write.** The route and `fragility_cascade` are read-only; no admit/anchor/belief-mutation path is reachable. The banner labels every cascade "hypothetical — no belief changed," mirroring the inbox's "reading a dossier never mutates a belief" (`app.py:696`, `index.html:2048`). A property test asserts zero KG writes (below).
- **Discounted by evidence, not asserted.** Propagation magnitude is `delta × Π(edge confidence)` over the dependency path — a computed graph quantity, never a model opinion (no-fabricated-confidence). A cascade over low-confidence edges visibly decays; a keystone on one high-confidence chain visibly collapses.
- **Inherits the map's honesty label.** Until RQ-E06 passes, `load_bearing` (and therefore every projected `new_load_bearing`) renders under F4.1's *candidate / unvalidated heuristic* label; the simulator echoes it, never upgrading a candidate cascade to a validated one.
- **Abstain over fabricate.** `applicable:False` (node absent, or nothing rests on it) renders "nothing downstream depends on this claim," not a fake empty-but-robust cascade.

**Required experiment.** Trivial for this lane — the render transports server data; the perturb is a UI event. The **propagation math itself carries no new seeded experiment**: it is deterministic graph arithmetic and it *inherits RQ-E06* (PRD-03 F3.1) as its trust gate — if the edges aren't real, the cascade is candidate-only, exactly as the map already declares. Two guards instead of a 20-seed sweep (don't gold-plate a deterministic function, CLAUDE.md §2):
1. a deterministic **property test** (F13.1 acceptance) over a hand-built fixture DAG — monotonicity, confidence-discount, termination, no-mutation;
2. **RQ-E26** (next free number, register in `docs/RESEARCH_QUALITY_PROGRAM.md`) as an *optional* face-validity gate lifted from BUILD_PLAN H3.3 — *expert review of N cascades on the RQ-E06 gold subfield finds ≥ face-valid agreement and the cascade occasionally surfaces a non-obvious downstream dependent* (qualitative + agreement rate). **Gate:** cascades stay labelled "hypothetical what-if" regardless; RQ-E26 only governs whether the map may ever call a fragility number a *validated* fragility score (it may not until both RQ-E06 and RQ-E26 pass). RQ-E26 is Lane-3-adjacent (it validates the propagation Lane 3 owns) and is **not** a blocker for shipping the interactive render.

**Acceptance + ONE runnable check.**
- (a) `GET /engine/fragility?claim_id=<keystone>&delta=-1.0` returns `{affected, perturbed, applicable}`; every `affected[i]` has `claim_id`, `new_load_bearing ≤` that node's stored `load_bearing`, and `delta ≤ 0`.
- (b) Knocking out a keystone (5 dependents) yields a non-empty `affected`; knocking out a leaf that nothing derives from yields `applicable:False, affected:[]`.
- (c) The call performs **zero** KG writes (no belief mutated).
- (d) Browser: perturbing a node re-tints ≥1 downstream node and shows the "hypothetical — no belief changed" banner; `reset` restores the stored values.
- **Runnable check:** `tests/test_epistemic_api.py::test_fragility_route_shape` — against a fixture persona whose FC-4 `fragility_cascade` is stubbed (or the real Lane-3 fn once landed), assert the envelope keys, `new_load_bearing ≤ old`, `applicable:False` on a leaf, and — via a KG spy — that no `kg.*` write method was called during the request. Browser step in `tests/ui_legibility_smoke.cjs`.

**Effort** S (one thin route + a slider/re-tint over data F4.1 already fetches; the propagation is Lane 3's effort under CCP-13a) · **Deps** PRD-04 F4.1 (surf-field + `/engine/dependency`), FC-4 `fragility_cascade` (CCP-13a, Lane 3).

---

## 4. Sequencing

1. **M0 (hour 1, unblocks the frontend):** land the `GET /engine/fragility` route as a **stub** returning `{affected:[], perturbed:claim_id, applicable:False}` so the `surf-field` interaction can be built and smoke-tested against a typed empty payload before Lane 3's `fragility_cascade` lands. (Matches PRD-04 §4 M0's "routes as thin stubs" pattern.)
2. **After PRD-04 F4.1 lands `surf-field`** (intra-lane): add the perturb control, `fragilityWhatIf()`, `resetCascade()`, and the hypothetical banner; wire to the stub route.
3. **After CCP-13a is acked and Lane 3 ships `fragility_cascade`:** swap the stub for the real FC-4 call; the render is unchanged (contract-first UI). Run the property + browser checks.
4. RQ-E26 face-validity review runs on Lane 3's thread whenever the RQ-E06 gold subfield is available; it never blocks the interactive ship (cascades are labelled hypothetical throughout).

---

## 5. Test plan

- **Route/API (`tests/test_epistemic_api.py`):** `test_fragility_route_shape` — envelope keys; `new_load_bearing ≤ old_load_bearing`; `delta` clamp (a `+0.5` query is treated as `0.0` → `affected:[]`); leaf abstain (`applicable:False`); **no-KG-mutation spy** (the headline guardrail, mirrors PRD-03 F3.4's KG-spy test).
- **Propagation property test (Lane 3 owns; this lane depends on it):** deterministic fixture DAG — a keystone with 5 `derives_from` children over confidences {0.9,0.9,0.5,0.5,0.2} plus a 2-hop grandchild; assert (i) child `delta` magnitude scales with edge confidence, (ii) grandchild `delta = delta × c1 × c2`, (iii) BFS terminates on an injected cycle, (iv) `delta ≥ 0` input is a no-op. (Named in PRD-03's test suite as `test_dependency.py::test_fragility_cascade_discounts_and_terminates` — flagged to Lane 3 with CCP-13a.)
- **Browser smoke (`tests/ui_legibility_smoke.cjs`, new step):** open `surf-field`, click a `fragile` node, drag the slider / hit "knock it out" → assert ≥1 downstream node changes tint, the magnitude label and the "hypothetical — no belief changed" banner appear, `reset` restores the pre-perturb DOM state; no horizontal overflow at 1280/760/390 px; `Esc`/reset clears the what-if.
- **Regression:** existing `test_integrity_boundaries.py`, `test_calibration.py`, and the F4.1 map smoke must pass unchanged — this PRD adds one route + one interaction, mutates no existing route body or belief path.

---

## 6. Open questions

- **Q1 (CCP-13a ratification — blocks Lane 3).** Confirm `engine.fragility_cascade(claim_id, delta, topic=None) -> {affected:[{claim_id,new_load_bearing,delta}], perturbed, applicable}` as the FC-4 addition, with the traversal/discount/abstain semantics in §2. This is the one item that must be acked by master + Lane 3 before either lane wires the real path (both can proceed on stubs meanwhile).
- **Q2 (weakening-only vs signed perturbation).** v1 models `delta ∈ [-1,0]` (weakening) and skips `contradicts`/`qualifies` edges. A fuller model would let a fallen claim *strengthen* whatever contradicted it (positive downstream delta via `contradicts`-inversion) and allow `delta > 0` ("what if this were confirmed?"). Recommend shipping weakening-only (the BUILD_PLAN §3.3 use-case) and deferring the signed/inverting version to a follow-up — it needs its own face-validity check. Non-blocking; affects only how much of RQ-E26 we claim.
- **Q3 (perturb entry point — intra-lane, confirm with F4.1).** Assumes PRD-04 F4.1's node-click detail panel is the perturb host (slider + knockout live there). If F4.1 renders the map without a per-node detail panel, this PRD adds a minimal one. Confirm the F4.1 panel exists so the interaction attaches rather than rebuilds.
- **Q4 (render depth — non-blocking).** Should the cascade re-tint the whole reachable subgraph or only direct + one-hop dependents (to keep the animation legible on a dense map)? Recommend rendering all `affected` but visually emphasising the top-K by `|delta|`; a pure presentation choice, no contract impact.
