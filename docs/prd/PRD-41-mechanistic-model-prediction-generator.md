# PRD-41 — Mechanistic-model novel-prediction generator

> **Owner lane:** 3 (Intellectual engine) · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (candidate hypotheses only — **never** anchors, mutates, or auto-writes a belief) · **Opened:** 2026-07-13 · **Backlog:** #519
> **Depends-on (FCs):** FC-4 `engine.dependency_graph(topic)` (landed, `analysis/dependency.py`); FC-3 public reads `kg.beliefs`, `kg.dependency_edges`, `kg.contradictions`, `kg.provenance` (landed); same-lane `analysis/value_queue.py` (cost/dataset helpers), `analysis/engine.py`. Optionally complements FC-22 `negspace.missing_edge_candidates` (PRD-30, SPECCED — import-guarded, degrades gracefully). Advisory hook into Lane-1 `agents/discover.py` is an Open Question (non-blocking, mirrors PRD-30 CCP-30a).
> **Governed by PRD-00 §4/§6 and §8 reconciliation. Where this body disagrees with §4/§6, §4/§6 win.**
> **Read first:** `PRD-00-overview.md` (FC registry §4, RQ registry §6, §8 reconciliation GOVERNS, new-file ownership rule 2026-07-13); `PRD-30-negative-space-hypotheses.md` (the closest relative — differentiated in §0); `PRD-13-fragility-simulator.md` (signed/confidence propagation along the dependency DAG, CCP-13a); `CLAUDE.md` epistemic charter.

---

## 0. Summary + capability unlocked

Persona reacts to what the literature **says**: it flags contradictions (`kg.contradictions`, `kg.py:298`), ranks contested claims to resolve (`analysis/value_queue.py:50`), and renders the argument's dependency structure (`analysis/dependency.py:32`). Every signed causal claim it stores — `subject --effect_sign--> object`, the `effect_sign` column read at `kg.py:290`/`:294` — sits in the graph as an isolated edge. **Nothing composes those edges.** If the graph holds "A raises B" and "B lowers C", no organ derives the implication the graph itself licenses: **A lowers C** — a signed, falsifiable relationship no paper has stated.

**This feature assembles the belief graph's signed causal edges into an executable qualitative model** (a signed digraph; sign algebra `{+,−,0,?}`; Boolean/logical-network-style sign propagation), then **enumerates the relationships the model implies but the literature has never stated** — directed source→target pairs reachable by composing definite-sign edges along a path (length `min_path_len..max_path_len`), where no direct claim exists. Each implied pair is emitted as a **signed, mechanistically-grounded candidate hypothesis**: `composed_sign` = product of the edge signs along the path; `path` names the *real* claims that compose it; already-stated or contradicted pairs are excluded; survivors are ranked by **testability × VoI** and routed into the acting loop via existing `run_action` dispatch. It is **INFERRED**, never asserted.

**CRITICAL DIFFERENTIATION vs PRD-30/FC-22 (negative space).** PRD-30 finds **structurally missing** edges: it projects an *undirected* entity graph and scores holes by **Adamic–Adar common-neighbour** connectivity (`PRD-30 §0:15`, F30.1 step 4) — "these two things are one grounded step apart in the argument structure and nobody closed it." It carries **no mechanism**; its sign composition is a best-effort secondary annotation over an undirected co-occurrence. **This PRD derives a signed prediction by composing existing *directed* causal/mechanistic edges along a *path*** — an *executable model* whose primary output is a **definite composed sign with a mechanistic rationale** (the causal chain), not a topological connectivity score. Different mechanism (directed sign-product vs undirected common-neighbour), different, richer output (a predicted *direction* + the executable chain). We **consume/complement** FC-22 (annotate a prediction that also fills a topological gap) and **do not** re-run Adamic–Adar. This is qualitative causal-graph reasoning (signed digraphs / Boolean regulatory-network sign propagation; the "enemy-of-my-enemy" sign rule) applied to Persona's own belief graph — a generative move no incumbent (scite / Open Targets / PaperQA2) makes.

**Capability unlocked:** the system stops being a reader and becomes a **modeller** — it runs its beliefs as a qualitative simulation and hands the acting loop the sign-resolved predictions that fall out, each falsifiable and each grounded in the real claims that produced it.

---

## 1. File ownership (disjoint)

| File | New? | Lane | Role |
|---|---|---|---|
| `persona/analysis/mechanism.py` | **new** | 3 | The feature: signed-digraph assembly, path composition, novelty filter, testability×VoI rank. Owned by Lane 3 (new-file rule 2026-07-13). |
| `persona/analysis/engine.py` | edit (one re-export) | 3 | Additive: `from .mechanism import implied_predictions` + `__all__`. Same-lane, same facade idiom as `dependency_graph`/`value_queue`/negspace (`engine.py:8-11`). |
| `experiments/exp_mechanism_predictions.py` | **new** | 3 (→4 registry) | RQ-E55 harness. |
| `tests/test_mechanism.py` | **new** | 3 | Runnable acceptance check. |
| `docs/RESEARCH_QUALITY_PROGRAM.md` | edit (append RQ-E55 block) | 3 | Registry append only — never edits another RQ's rows. |

**Boundary files (imported read-only, NOT edited):**
- `persona/analysis/dependency.py` / `engine.py` — Lane 3 (same lane). `engine.dependency_graph(topic)` consumed read-only for the typed DEPENDS_ON exclusion layer + per-entity `load_bearing` (VoI signal).
- `persona/analysis/value_queue.py` — Lane 3 (same lane). Reuse `_dataset_available` + `_COST_WEIGHT` (`value_queue.py:17,30`) and the `run_action` prefix convention (`value_queue.py:111-114`) verbatim — no re-implementation.
- `persona/memory/kg.py` — **Lane 2.** Called via public reads only: `kg.beliefs` (`kg.py:285`), `kg.dependency_edges` (`kg.py:405`), `kg.contradictions` (`kg.py:298`), `kg.provenance` (`kg.py:315`). **No edit.**
- `persona/agents/discover.py` — **Lane 1.** Would consume FC-31 via one additive prompt block (Open Q1 / mirrors PRD-30 CCP-30a). Lane 3 does **not** edit it; the read API decouples.

**FC that decouples the boundary:** FC-31 (`implied_predictions`) is a pure read Lane 3 provides; Lane 1's `discover.py` and Lane 4's prediction surface consume the return shape, so no shared editing of `discover.py` or `value_queue`'s FC-4 signature is required.

---

## 2. FCs provided / consumed + contract-change proposals

**Provides — FC-31 (Lane 3, new `persona/analysis/mechanism.py`, re-exported via `analysis/engine.py`):**
```python
mechanism.implied_predictions(
    topic: str | None = None, *,
    kg=None, engine=None,        # injectable for tests; default = current persona's KG + engine facade
    limit: int = 400,            # max live causal claims scanned into the signed digraph
    min_path_len: int = 2,       # >=2 hops: a 1-hop "path" is a direct claim, not a prediction
    max_path_len: int = 4,       # cap path length (compounded uncertainty + combinatorics guard)
    top_k: int = 25,             # ranked predictions returned
) -> list[dict]
#   -> [{
#       "source_entity": str, "target_entity": str,        # the implied, never-stated directed pair (canonical)
#       "composed_sign": "+" | "-" | "0" | "ambiguous" | "unknown",  # sign-product; abstains honestly
#       "path": [{"src_entity": str, "dst_entity": str, "claim_id": str,
#                 "edge_sign": str, "relation": str}],      # the executable chain: REAL claims only
#       "n_paths": int,                                     # # definite-sign directed paths source->target
#       "testability": float,                               # [0,1] deterministic feasibility (dataset/hops)
#       "voi": float,                                       # [0,1] deterministic VoI PLACEHOLDER (pending RQ-E55)
#       "score": float,                                     # testability * voi (rank key), desc
#       "question": str,                                    # the falsifiable prediction, sign-explicit
#       "run_action": str,                                  # CCP-19a-dispatchable ("literature_search:X Z" / "null_hunt:X|Z")
#       "provenance": "INFERRED",
#       "rationale": str,                                   # names the composing claim_ids + the composed sign
#   }]  # highest testability*voi first; empty list if KG down / topic empty
```
Re-exported so consumers call `from persona.analysis import engine; engine.implied_predictions(topic)` — the FC-4 facade idiom (`engine.py:8-11`). **Pure:** no KG mutation, no network, no model call (the LLM lives downstream in `discover.py`, not here).

**Consumes (verbatim):**
- **FC-4** `engine.dependency_graph(topic) -> {nodes:[{claim_id, load_bearing, ...}], edges:[{src, dst, rel_type, confidence, span}]}` — for the typed DEPENDS_ON exclusion set + per-entity `load_bearing` VoI signal. Landed.
- **FC-3 / public reads:** `kg.beliefs(min_independent=1, min_conf=0.0, limit=…)` (the signed causal edges, low threshold so the single-lab frontier is included — same pool `value_queue.py:73` uses); `kg.dependency_edges(topic)`; `kg.contradictions()`. Landed.
- **FC-22** `negspace.missing_edge_candidates` (PRD-30, **SPECCED-not-necessarily-built**) — consumed **import-guarded, optional**: if present, annotate a prediction whose `(source,target)` also appears as a topological gap (`also_negspace_gap: bool` in `rationale`). Absent/erroring → skipped silently; **never a blocker** (PRD-29/35 degrade-gracefully precedent). We do **not** call Adamic–Adar ourselves.

**No contract-change proposal.** FC-31 is a new pure read beside `dependency_graph`/`value_queue`/`missing_edge_candidates`; it changes no existing signature. Routing into the acting loop rides the **already-ratified CCP-19a** `run_action` prefix dispatch (`"literature_search:"`/`"null_hunt:"` → the same `value_queue.py:111-114` prefixes) — no new dispatch contract needed.

**Considered, NOT proposed:**
- *An `implies`/composed edge type in `DEP_REL_TYPES` (`kg.py:86`).* A prediction is an *un-stated* edge — there is no belief to write and nothing to mutate. Writing a placeholder edge would corrupt `dependency_edges` (`kg.py:405`) for every other consumer and fabricate a belief the evidence does not support. The prediction lives only in the FC-31 return + the routed investigation. Recorded so it isn't re-discovered.
- *Folding predictions into FC-4 `value_queue` rows.* A prediction has **no `resolves_claim_id`** (it resolves a *pair*, not an existing claim), so folding it would break the FC-4 row contract — identical to PRD-30's reasoning. Lane 4 renders it as a **sibling strip** beside the value queue.

---

## 3. Features

### F41.1 — Mechanistic composition: signed-digraph assembly → path composition → novelty filter → sign-resolved, ranked candidate prediction

**Problem & evidence.**
- *Code:* every generative/analytic organ treats claims as isolated. `value_queue.py:72-80` builds its candidate pool from `kg.beliefs(min_independent=1)` and ranks **claims that already exist**, excluding confirmed ones (`value_queue.py:77-79`) — it re-prioritises studied claims; it never *composes* two claims into an implied third. `dependency.py:40` renders the DEPENDS_ON edges *verbatim* ("edges = kg.dependency_edges(topic)") and `dependency.py:44-49` counts in-degree — it presents the edge set, it never traverses it to derive a new relation. `kg.beliefs` returns a per-claim `effect_sign` (`kg.py:290`,`:294`) — the signs needed to compose are **right there in the store**, and nothing multiplies them along a path. The complement of the stated-edge set — the relations the graph *implies* — is structurally invisible.
- *Research/source:* qualitative causal-graph reasoning composes signed edges by the **sign-product rule** (`sign(A→B) × sign(B→C)` gives `sign(A→C)`; the "enemy-of-my-enemy" rule of signed digraphs / balance theory), and Boolean/qualitative regulatory-network models (systems biology) *execute* such graphs by propagating `{+,−,0,?}` states along directed paths — the established, deterministic, dependency-free way to derive implied relations from a signed causal graph. Multi-hop composition compounds uncertainty and combinatorics, so the standard controls are a **path-length cap** and **definite-sign-only composition** (abstain rather than guess through an ambiguous edge). This is precisely the mechanism PRD-30's Adamic–Adar does *not* provide (undirected, sign-agnostic connectivity) and PRD-13's cascade *does* echo (signed/confidence propagation along the same dependency DAG, `PRD-13 §2:46-52`).

**Design.**
*Files:* new `persona/analysis/mechanism.py`. Imports: `..analysis.engine` (FC-4, read-only), `..memory.membrane.get_kg` (same accessor `dependency.py:12`/`value_queue.py:56` use), `.value_queue` (`_dataset_available`, `_COST_WEIGHT`), `math` (stdlib), `..events.log` (optional living-notebook emit). No `anthropic`, no network — pure.

*Data flow:*
1. **Signed causal edge set.** `claims = kg.beliefs(min_independent=1, min_conf=0.0, limit=limit)` (`kg.py:285`). Keep claims with a **definite** `effect_sign ∈ {"+","-"}` (a causal direction); claims with `effect_sign ∈ {"0","na"}` are retained only as *nodes* (they cannot carry a composed sign). Subjects/objects are already canonical (canonicalised at claim time, `kg.py:147-148`). Topic-filter on subject/object substring, mirroring `value_queue.py:75`.
2. **Executable model = signed digraph.** Build directed multigraph `G: src_entity -> [(dst_entity, claim_id, sign, relation)]`, one directed edge per definite-sign claim `subject --sign--> object`. This *is* the "executable qualitative model": `_signed_digraph(claims) -> adj` and `_compose_paths(adj, source, target, min_len, max_len) -> [(path, sign)]` are **pure module-level helpers** (the RQ-E55 oracle) — `_compose_paths` walks directed simple paths (visited-set + `max_path_len` depth cap → terminates on cycles, same bounded-BFS discipline as `retraction.contamination`) and returns each path with its **sign-product** (`+×+=+, +×−=−, −×−=+`).
3. **Enumerate implied pairs.** For every ordered pair `(source, target)` connected by ≥1 directed path of length in `[min_path_len, max_path_len]`, `(source, target)` is a **candidate implied edge**.
4. **Novelty filter (excluded three ways, grounded — the "never stated" gate).** Drop `(source, target)` when a direct link already exists: (a) a direct claim relates them (adjacency in `G`, either direction); OR (b) a typed DEPENDS_ON edge joins any of their claims in `engine.dependency_graph(topic)`; OR (c) the pair appears in `kg.contradictions()` (studied-but-disputed ≠ unstudied). Identical three-way gate to PRD-30 F30.1 step 3 — a relation that has been stated or contested is **not** a novel prediction.
5. **Sign resolution (honest abstention).** Aggregate the sign-products of all definite paths `source→target`: **all agree** → that sign (`"+"`/`"-"`); **disagree** → `"ambiguous"`; **a path routes through a `0`/`na` edge or none is fully definite** → that path contributes `"unknown"` and never coerces the aggregate. A `composed_sign` is emitted as definite **only where every edge on at least one path is definite and all definite paths agree** — otherwise `"ambiguous"`/`"unknown"` is surfaced verbatim.
6. **Rank by testability × VoI (deterministic PLACEHOLDER until RQ-E55).**
   - `testability ∈ [0,1]`: higher when a locally-available dataset names the pair's tokens (`value_queue._dataset_available`, reused) — cheap to test — and when the shortest definite path is short (fewer compounded assumptions): `testability = 0.5·has_data + 0.5·(1/shortest_definite_len)`.
   - `voi ∈ [0,1]`: centrality of the endpoints in the argument — `voi = normalise(load_bearing[source] + load_bearing[target])` from `engine.dependency_graph` (`dependency.py:68`), a resolving-this-de-risks-more proxy. A **deterministic placeholder**, exactly like `value_queue.py:98`'s `voi` and `dependency.py:68`'s `load_bearing` — **not** a calibrated expected-information-gain, and labelled so, pending RQ-E55.
   - `score = testability × voi`; stable sort by `(-score, source_entity, target_entity)`.
7. **Emit rows (top-`top_k`).** `question` = `f"Does {source} {verb(sign)} {target}? Mechanistic prediction: composing {n} grounded step(s) ({via chain}) implies a {sign-phrase} relation, but no study tests {source}–{target} directly."`; `path` = the real `{src_entity,dst_entity,claim_id,edge_sign,relation}` hops (the entire justification is *existing* claims); `run_action` = `"literature_search:{source} {target}"` (cheap first move: has the pair ever been co-mentioned?) else `"null_hunt:{source}|{target}"` — both CCP-19a prefixes `value_queue.py:111-114` emits; `provenance="INFERRED"`; `rationale` names the composing claim_ids, the composed sign, and (if FC-22 available) `also_negspace_gap`. Optional `log().emit("thought", …)`.
8. **Routing (downstream, not in this module).** Lane 4 renders the ranked predictions on a sibling strip; each `run_action` is dispatched by the existing CCP-19a rule into the acting loop (`null_hunt` → `queue.enqueue`; `literature_search`/oracle → `science.call`). Optional `discover.py` prompt hook (Open Q1) feeds top predictions to the *generative* loop.

*Seams:* fully pure w.r.t. the KG (read-only); the only side effect is an optional notebook emit. Deterministic given a fixed claim set (stable sort, fixed `PYTHONHASHSEED`). `_signed_digraph` + `_compose_paths` are the reused oracle for the experiment and the test.

**Epistemic guardrails.**
- **INFERRED candidate hypothesis, never a belief.** `provenance="INFERRED"` on every row — never `READ`/`TESTED`/`HUMAN_CONFIRMED`, never a finding, never anchored, **never written to the KG** (there is no edge to write; the feature mutates nothing — this is *not* a membrane-crossing feature). A prediction is a hypothesis *for* the acting loop, not a conclusion *from* it.
- **Composed sign only where fully licensed.** A definite `composed_sign` is emitted **only when every edge on the path has a definite sign** and all definite paths agree; ambiguous/mixed/`0`/`na` paths surface `"ambiguous"`/`"unknown"` and are never silently coerced to a confident direction. Under-determined structure is reported as under-determined.
- **Grounded, not fabricated.** The chain cites *real* claim_ids (`left/right claim_id` per hop); the inference ("therefore source→target may hold, sign X") is explicitly INFERRED over existing READ/verified claims. No span is invented for the implied edge — an un-stated relation has no span, and the record says so.
- **Novelty verified three ways** (adjacency, typed DEPENDS_ON, contradiction set) — an already-stated or contested relation is excluded, not surfaced as novel.
- **Rank honestly.** `testability`/`voi`/`score` are deterministic placeholders, labelled candidate/unvalidated until RQ-E55; **no fabricated confidence**, no calibrated_p.
- **Autonomy = Balanced.** Predictions are *always* advisory — routed to `discover.py`/the value surface, which route testable→sandbox and physical/judgment→human. Nothing here auto-asserts, auto-anchors, or auto-writes. High-stakes stays human-gated by the unchanged downstream loop **regardless of RQ-E55**.

**Required experiment — RQ-E55** (pre-assigned; register in `docs/RESEARCH_QUALITY_PROGRAM.md`).
- *Hypothesis:* directed signed-path composition recovers **real composed relationships** better than random **and** better than the undirected Adamic–Adar baseline (FC-22/negspace). Concretely: on a graph with real direct claims held out, the generator's top-`K` implied predictions **recover the held-out true edges (with correct sign) at higher precision-at-K** than either baseline.
- *Data / arms:* a frozen entity+claim graph from a curated KG slice (or a public signed causal graph with a known edge set). Hold out a set of real direct claims `A→Z` (definite sign) for which a definite composing path `A→…→Z` still exists after removal. Three arms over the same held-out set: **(A)** random non-adjacent directed pairs; **(B)** Adamic–Adar over the undirected projection (the negspace scorer); **(C)** `implied_predictions` (directed sign-product composition). Freeze a content hash of graph + held-out pool + seeds.
- *Metric:* **precision-at-K of recovered held-out edges** per arm (primary); **sign-accuracy on recovered edges** (secondary — the differentiator: only arm C predicts a sign). Primary comparison = `precision_C − max(precision_A, precision_B)`.
- *Gate:* **precision-at-K(C) − max(A,B) with a 95% CI lower bound > 0 over ≥20 seeds/bootstrap resamples**, mean±95%CI. On pass, FC-31 is cleared to drive `discover.py` prompting non-trivially (Open Q1); on fail, ship as an advisory Lane-4 read surface only and say so (BUILD_PLAN §3.2 "downgrade to human-in-the-loop and say so"). Script → `experiments/exp_mechanism_predictions.py`; results → `results/` + one line in `results/FINDINGS.md`. The held-out-edge arm is **zero-human** and runs in CI (mirrors PRD-30 RQ-E46's proxy). **Advisory regardless of outcome — RQ-E55 never licenses an autonomous belief write.**

**Acceptance + ONE runnable check.**
- *Acceptance:* on a fixture signed digraph where claims `A --(+)--> B`, `B --(−)--> C` exist but `A–C` does not: `implied_predictions()` returns `(A, C)` with `composed_sign == "-"`; its `path` cites the **real** A–B and B–C `claim_id`s and their signs; a pair with a **direct** claim is **absent** (novelty gate); a pair reachable only through a `0`/`na` edge yields `composed_sign in {"unknown"}` (or is dropped), never a fabricated definite sign; two definite paths with disagreeing sign-products yield `"ambiguous"`; a longer chain scores no higher than a short, dataset-backed one (testability ordering); `provenance == "INFERRED"` on every row; **no KG write occurs**.
- *Runnable check:* `tests/test_mechanism.py::test_implied_predictions` — builds a fake KG (stubs `kg.beliefs` returning signed claim dicts + a fake `engine.dependency_graph`), a mutation-recording fake KG asserting **zero** writes, and asserts the above. `pytest tests/test_mechanism.py -q`. Plus `python -m persona.analysis.mechanism` self-check (fake-KG `__main__`, no DB — the `dependency.py:134-173` idiom).

**Effort:** M (one pure analysis module ~170 LOC incl. `_signed_digraph`/`_compose_paths` helpers + `__main__` self-check; one experiment harness; one test). No new dependency (stdlib `math` only; reuses `value_queue` cost helpers).
**Deps:** FC-4 `engine.dependency_graph` (landed); public `kg.beliefs`/`dependency_edges`/`contradictions` (landed). FC-22 optional/import-guarded. `discover.py` hook (Open Q1) non-blocking. Nothing un-landed blocks.

---

## 4. Sequencing

1. **M0 (hour 1, unblocks Lane 4):** land `mechanism.py` with the FC-31 signature + a typed empty return (`[]` when KG is `None`/topic empty) and add the `engine.py` re-export, so Lane 4 can build its prediction strip against the shape from hour 1. Repo stays runnable.
2. Implement the pure core: signed-digraph assembly, `_compose_paths`, three-way novelty filter, sign resolution → `test_mechanism.py` green on the fake-KG fixture (no DB, no model).
3. Wire the real `kg.beliefs` / `engine.dependency_graph` reads + `testability`/`voi` ranking + `run_action`/`question` shaping + optional FC-22 annotation (import-guarded) + optional notebook emit.
4. Author + run `exp_mechanism_predictions.py`; on pass, append RQ-E55 to `RESEARCH_QUALITY_PROGRAM.md` and a result line to `results/FINDINGS.md`.
5. Hand FC-31 to Lane 4 (prediction strip) and, if acked, Lane 1 (Open Q1 `discover.py` prompt block). Both additive, land anytime after M0.

Self-contained after M0; nothing else waits on it.

---

## 5. Test plan

| Test | What it proves |
|---|---|
| `tests/test_mechanism.py::test_implied_predictions` (runnable check) | signed-digraph projection; path composition + sign-product (`+×−=−`); novelty gate (direct-claim / DEPENDS_ON / contradiction pairs dropped); definite-sign-only composition (`0`/`na` path → `unknown`, not a fabricated sign); disagreeing paths → `ambiguous`; grounding (`path` cites real claim_ids); `min/max_path_len` bounds + cycle termination; testability×VoI ordering; `provenance=="INFERRED"`; **purity (mutation-recording fake KG expects zero writes)**. |
| `experiments/exp_mechanism_predictions.py` (RQ-E55) | ≥20-seed / ≥20-bootstrap held-out-edge recovery: arm C (composition) vs arm A (random) vs arm B (Adamic–Adar); reports precision-at-K delta ± 95% CI + sign-accuracy; writes `results/rq_e55_*.json`; prints GO/NO-GO vs the gate. Seeded, deterministic under fixed `PYTHONHASHSEED`. |
| No trust-boundary mocking | `path` claim_ids checked to be real members of the input claim set; exclusion checked against the actual adjacency / DEPENDS_ON / contradiction sets, not a stub verdict. |

---

## 6. Open questions

1. **`discover.py` prompt hook — Lane 1 ack? (recommended default: yes, mirror PRD-30 CCP-30a, non-blocking.)** One additive, fully-guarded block prepends the top-5 predictions to `discover.py`'s prompt so the mechanistic predictions feed the *generative* loop. **Default:** propose it as an advisory CCP to Lane 1 exactly as PRD-30 did; FC-31 stands alone for Lane 4 meanwhile, and the hook lands whenever convenient (and only drives non-trivially once RQ-E55 passes). *(Surfaced, not minted — no new FC/RQ number.)*
2. **Longer paths (`max_path_len` > 4).** v1 caps composition at 4 hops; each extra hop multiplies candidates and compounds sign uncertainty super-linearly. **Default:** ship `max_path_len=4` (the definite-sign + Adamic-baseline-beating first cut); revisit only if RQ-E55 clears and multi-hop recall is the bottleneck.
3. **`0`/`na`-sign claims as pass-through nodes.** A claim with `effect_sign ∈ {0,na}` can carry *connectivity* but not a sign. **Default:** treat it as a node only (never a signed edge) so any path crossing it resolves to `"unknown"` — never a fabricated definite sign; revisit if it over-suppresses real predictions.
4. **RQ-E55 graph slice + expert overlay.** The zero-human held-out-edge proxy runs immediately in CI; an expert "is this mechanistically plausible?" overlay (like RQ-E46's rater) would strengthen the gate. **Default:** ship on the held-out-edge proxy as authoritative-for-CI; add the expert overlay if/when a rater + KG slice is available (domain input, non-blocking). *(Which KG slice — Gladstone vs a public signed causal graph — is the open domain input.)*
