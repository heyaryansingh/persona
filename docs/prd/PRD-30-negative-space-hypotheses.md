# PRD-30 — Negative-space hypothesis generation

> **Owner lane:** 3 (Intellectual engine) · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced · **Opened:** 2026-07-13
> **Depends-on:** FC-4 `engine.dependency_graph(topic)` (landed, `analysis/dependency.py`); FC-3 public reads `kg.beliefs`, `kg.dependency_edges`, `kg.provenance` (landed); same-lane `analysis/value_queue.py`, `analysis/engine.py`. Advisory hook into Lane-1 `agents/discover.py` (CCP-30a, non-blocking).
> **Read first:** `PRD-00-overview.md` (frozen contracts FC-1…FC-19; §8 reconciliation GOVERNS; new-file ownership rule 2026-07-13), `PRD-03-intellectual-engine.md` (FC-4 origin), `PRD-21-cross-field-translation.md` (the INFERRED-candidate-edge / advisory-until-gate pattern this mirrors), `CLAUDE.md` epistemic charter.

---

## 0. Summary + capability unlocked

Persona today reacts to what the literature **says** — it flags contradictions (`kg.contradictions`), ranks contested claims to resolve (`analysis/value_queue.py`), and generates leads from converged beliefs (`agents/discover.py`). It has no organ for what the literature **hasn't said**. The most valuable question in a field is often the one nobody has asked: two entities that everything in the graph implies should be connected, yet no paper has ever tested the link directly.

**This feature mines the graph's holes.** It projects the belief graph to an **entity graph** (entities = claim subjects/objects; an edge = a real claim relating them), then finds entity pairs `(X, Z)` with **strong indirect connectivity** (multiple grounded intermediary paths `X–Y–Z`) but **no direct claim** `X–Z`. Each such pair is a **negative-space candidate hypothesis** — INFERRED, structurally grounded (it names the real intermediary claims that make the link plausible), sign-composed where the intermediaries license a direction, and routed to `discover.py` (→ investigation / human) and the value-of-information surface. It is **never** asserted as a finding.

This is the Swanson ABC / undiscovered-public-knowledge model (fish-oil↔Raynaud's) done on Persona's own belief graph, with the standard link-prediction correction (Adamic–Adar, down-weighting hub intermediaries) so "both connect to *cell*" is not mistaken for a real bridge.

**Capability unlocked:** proactive gap discovery — "these two things are one grounded step apart in the argument structure and nobody has closed it." A concrete, checkable, generative move no competitor (scite / Open Targets / PaperQA2) makes: they retrieve and rank what exists; this proposes what's conspicuously absent.

---

## 1. File ownership (disjoint)

| File | New? | Lane | Note |
|---|---|---|---|
| `persona/analysis/negspace.py` | **new** | 3 | The feature. Owned by Lane 3 (new-file rule 2026-07-13). |
| `persona/analysis/engine.py` | edit (add one re-export) | 3 | Additive: `from .negspace import missing_edge_candidates` + `__all__`. Same-lane, mirrors how `dependency_graph`/`value_queue` are exposed (`engine.py:8-11`). |
| `experiments/exp_rq_e46_negative_space.py` | **new** | 3 (→4 registry) | RQ-E46 harness. |
| `tests/test_negspace.py` | **new** | 3 | Runnable acceptance check. |
| `docs/RESEARCH_QUALITY_PROGRAM.md` | edit (append RQ-E46 block) | 3 | Registry append only — never edits another RQ's rows. |

**Boundary files (imported read-only, NOT edited):**
- `persona/analysis/dependency.py` / `engine.py` — Lane 3 (same lane). `engine.dependency_graph(topic)` consumed read-only for the typed DEPENDS_ON layer + node load-bearing/fragility signals.
- `persona/memory/kg.py` — Lane 2. Called via public reads only: `kg.beliefs`, `kg.dependency_edges`, `kg.provenance`, `kg.contradictions`. **No edit.**
- `persona/agents/discover.py` — **Lane 1.** Consumes FC-22 via one additive prompt block (CCP-30a below). Lane 3 does **not** edit it; the read API is decoupling.

**FC that decouples the boundary:** FC-22 (`missing_edge_candidates`) is a pure read Lane 3 provides; Lane 1's `discover.py` and Lane 4's value/gap surface consume the return shape, so no shared editing of `discover.py` or `value_queue`'s FC-4 signature is required.

---

## 2. FCs provided / consumed + contract-change proposals

**Provides — FC-22 (Lane 3, new `persona/analysis/negspace.py`, re-exported via `analysis/engine.py`):**
```python
negspace.missing_edge_candidates(
    topic: str | None = None, *,
    kg=None, engine=None,
    limit: int = 400,            # max live claims scanned into the entity graph
    min_intermediaries: int = 2, # a gap needs >=2 distinct grounded bridge entities
    top_k: int = 25,             # ranked candidates returned
) -> list[dict]
#   -> [{
#       "source_entity": str, "target_entity": str,   # the un-linked pair (canonical)
#       "score": float,                                # Adamic-Adar-style connectivity, desc
#       "n_intermediaries": int,
#       "path": [{"via_entity": str, "left_claim_id": str, "right_claim_id": str,
#                 "left_sign": str, "right_sign": str}],   # the grounding: real claims only
#       "composed_sign": "+" | "-" | "0" | "ambiguous" | "unknown",
#       "question": str,                               # the falsifiable gap hypothesis
#       "run_action": str,                             # CCP-19a-dispatchable ("null_hunt:X|Z" / "literature_search:X Z")
#       "provenance": "INFERRED",
#       "rationale": str,
#   }]  # highest connectivity first; empty list if KG down / topic empty
```
Re-exported so consumers call `from persona.analysis import engine; engine.missing_edge_candidates(topic)` — same facade idiom as FC-4 (`engine.py:8-11`). Pure: no KG mutation, no network, no model call (the LLM lives downstream in `discover.py`, not here).

**Consumes:** FC-4 `engine.dependency_graph(topic)` (for the typed DEPENDS_ON exclusion set + per-entity load-bearing signal); FC-3 / public `kg.beliefs(min_independent=1, min_conf=0.0, limit=…)`, `kg.dependency_edges(topic)`, `kg.contradictions()`. All landed.

**CONTRACT CHANGE PROPOSAL — CCP-30a (ADVISORY hook, → Lane 1, non-blocking).** In `agents/discover.py`, after `kb` is assembled (`discover.py:75-79`) and before the LLM call, prepend one additive block:
```python
try:
    from ..analysis import engine
    gaps = engine.missing_edge_candidates(topic=None)[:5]
    if gaps:
        kb += "\n\nSTRUCTURAL GAPS (well-connected but never directly studied):\n" + \
              "\n".join(f"- {g['source_entity']} ?-> {g['target_entity']} "
                        f"(via {', '.join(p['via_entity'] for p in g['path'][:3])})" for g in gaps)
except Exception:
    pass  # gaps are advisory; discover proceeds without them
```
One additive read, fully guarded, changes no signature and no existing behaviour when the list is empty. **Ships without it:** FC-22 is independently useful (Lane 4 renders it directly on the value surface), so this hook is a convenience that lets the negative space feed the *generative* loop. Lane 1 acks + lands it whenever convenient. **No FC-4 change** — `engine.value_queue` is untouched; the gap surface is a sibling strip, not folded into value-queue rows (a gap has no `resolves_claim_id`, so folding it would violate the FC-4 row contract).

**Considered, NOT proposed — a `CONFLATES`/`gap` edge type in `DEP_REL_TYPES`.** A gap is the *absence* of an edge; there is nothing to write to the KG and no belief to mutate. Writing a placeholder "missing" edge would corrupt `dependency_edges` for every other consumer. The candidate lives only in the FC-22 return + the routed investigation. Recorded so it isn't re-discovered.

---

## 3. Features

### F30.1 — Negative-space candidate mining (entity projection → indirect-connectivity ranking → grounded, sign-composed gap hypothesis)

**Problem & evidence.**
- *Code:* Persona's generative organs are all **presence**-driven. `discover.py:68-79` builds its prompt from `kg.beliefs`, `kg.contradictions`, `selfmind.open_questions` — every input is a claim that *exists*. `value_queue.py:73-80` ranks only claims already in the graph (`kg.beliefs(min_independent=1)`), excluding confirmed ones — it re-prioritises studied claims, it never proposes an unstudied pair. `dependency.py` renders the edges that *are* there. Nothing in `analysis/` looks at the *complement* of the edge set. The graph's holes are structurally invisible.
- *Research/source:* Swanson's literature-based discovery (ABC model: A–B and B–C in the literature, A–C absent → candidate; the fish-oil / Raynaud's and migraine / magnesium discoveries). Modern link-prediction on such graphs uses **common-neighbour** as the naive score and **Adamic–Adar** (Liben-Nowell & Kleinberg, 2003 — `1/log(degree)` weighting per shared neighbour) as the standard hub-correction, so a bridge through a rare, specific intermediary outranks one through a promiscuous hub (`cell`, `patient`). This is exactly the failure mode that makes naive co-occurrence gap-mining produce slop, and the fix is well-established, cheap, and deterministic — no new dependency.

**Design.**
*Files:* new `persona/analysis/negspace.py`. Imports: `..analysis.engine` (FC-4, read-only), `..memory.membrane.get_kg` (same accessor `dependency.py:12`/`value_queue.py:56` use), `math` (stdlib, for `1/log`), `..events.log` (living-notebook emit only, optional). No `anthropic`, no network — pure.

*Data flow:*
1. **Claim set.** `claims = kg.beliefs(min_independent=1, min_conf=0.0, limit=limit)` (public read, `kg.py:248`; same low-threshold pool `value_queue.py:73` uses so single-lab claims — the frontier — are included). Subjects/objects are already canonical (canonicalised at claim time, `kg.add_claim`, per PRD-21 F21.1). Topic-filter on subject/object substring, mirroring `value_queue.py:75-76`.
2. **Entity graph projection.** Build an undirected adjacency `adj: entity -> {neighbour -> [(claim_id, effect_sign)]}`. Each live claim `X --relation--> Y` contributes edge `X—Y`, tagged with its `claim_id` and `effect_sign`. `degree(Y) = |adj[Y]|`. This entity graph *is* "the dependency graph at entity granularity" the backlog names — nodes are the things researchers reason about, edges are the grounded claims that link them.
3. **Existing-link exclusion set.** A pair is NOT a gap if any direct link already exists. Exclude `(X, Z)` when: (a) `X` and `Z` are already adjacent in `adj` (a claim relates them); OR (b) a typed DEPENDS_ON edge joins any of their claims in `engine.dependency_graph(topic)`; OR (c) the pair (either sign) appears in `kg.contradictions()` (studied-but-disputed ≠ unstudied). This is the "no direct claim" gate.
4. **Candidate scoring (Adamic–Adar over the entity graph).** For every non-adjacent pair `(X, Z)` sharing common neighbours `N(X) ∩ N(Z)`, `score(X,Z) = Σ_{Y ∈ N(X)∩N(Z)} 1 / log(1 + degree(Y))`. Keep pairs with `|N(X)∩N(Z)| ≥ min_intermediaries`. Down-weighting by `log(degree)` is the whole point — a hub intermediary contributes almost nothing; two rare specific intermediaries dominate. Factored into a **pure module-level helper** `_adamic_adar_gaps(adj, excluded, *, min_intermediaries) -> list[(x, z, score, intermediaries)]` so the RQ-E46 experiment drives the *exact* ranking under both arms.
5. **Sign composition (direction + falsifiability).** For each intermediary `Y`, take the sign of `X–Y` (`s1`) and `Y–Z` (`s2`); the composed sign of the implied `X→Z` is `s1 * s2` (`+ = +1, - = -1, 0/na = unknown`). Aggregate across intermediaries: if all resolved signs agree → that sign; if they conflict → `"ambiguous"`; if none resolvable → `"unknown"`. This turns a bare "these connect" into a **specific, falsifiable** hypothesis with a predicted direction, and honestly flags when the structure under-determines it.
6. **Emit candidate rows.** For the top-`top_k` by score: build `question` = `f"Is {X} linked to {Z}? Structural gap: {n} grounded intermediary path(s) ({via…}) imply a {sign-phrase} relation, but no study tests {X}–{Z} directly."`; `path` = up to a few `{via_entity, left_claim_id, right_claim_id, left_sign, right_sign}` (real, grounded claim_ids — the candidate's entire justification is *existing evidence*); `run_action` = `"literature_search:{X} {Z}"` if a co-mention search is the cheap first move, else `"null_hunt:{X}|{Z}"` (both CCP-19a-dispatchable, same prefixes `value_queue.py:111-114` emits); `provenance="INFERRED"`; `rationale` names the intermediaries + score. Optional `log().emit("thought", …)` for the living notebook.
7. **Routing (downstream, not in this module).** `discover.py` reads FC-22 (CCP-30a) → the LLM turns top gaps into falsifiable hypotheses and enqueues investigations / human escalations via the machinery that already exists (`discover.py:114-127`). Lane 4 renders the ranked gaps beside the value queue.

*Seams:* fully pure w.r.t. the KG (read-only); no side effect except an optional notebook emit. Deterministic given a fixed claim set (stable sort by `-score`, then `(source_entity, target_entity)`). The `_adamic_adar_gaps` helper is the reused oracle for the experiment and the test.

**Epistemic guardrails.**
- A gap is a **CANDIDATE hypothesis, `provenance="INFERRED"`** — never `READ`/`TESTED`/`HUMAN_CONFIRMED`, never a finding, never anchored, never written to the KG (there is no edge to write; the feature mutates nothing).
- **Structurally grounded, not fabricated.** The candidate names the *real, grounded* intermediary claims (`left_claim_id`/`right_claim_id`) that make the link plausible. The inference ("therefore X and Z may be linked") is explicitly INFERRED; its inputs are existing READ/verified claims. No span is invented for the gap itself — an absence has no span, and the record says so.
- **No direct claim, verified three ways** (adjacency, typed DEPENDS_ON, contradiction set) — a gap that's actually been studied is excluded, not surfaced as novel.
- **Hub-noise controlled by construction** (Adamic–Adar), and `min_intermediaries ≥ 2` so a single accidental co-mention can't mint a candidate.
- **Sign honesty:** `"ambiguous"`/`"unknown"` is surfaced, never silently coerced to a confident direction — under-determined structure is reported as under-determined.
- **Autonomy = Balanced:** gaps are *always* advisory — routed to `discover.py` (which itself routes testable→sandbox, physical/judgment→human) and to the human-facing value surface. Nothing here auto-asserts, auto-anchors, or auto-writes a belief. High-stakes stays human-gated by the downstream loop, unchanged.

**Required experiment — RQ-E46** (pre-assigned).
- *Hypothesis:* the negative-space miner surfaces **real understudied questions** better than random. Concretely: expert-rated "genuinely understudied and worth studying" score of negspace's top-`N` candidates > that of `N` **random non-adjacent entity pairs** drawn from the same entity graph (i.e. pairs that *also* lack a direct claim — a fair baseline, not trivially-connected pairs).
- *Data:* a frozen entity graph built from a curated slice of Persona's KG (or a public co-occurrence graph with a known held-out edge set). Two arms over the same graph: **(A)** random non-adjacent pairs; **(B)** negspace top-`N` by Adamic–Adar. Blinded expert rating (1–5 "understudied & plausible") on the merged, shuffled pool; raters don't know the arm. Freeze a content hash of graph + item pool.
- *Metric:* mean expert rating per arm; **primary = mean(B) − mean(A)**. Secondary (if a held-out-edge graph is used): recovery rate of held-out true edges (a proxy oracle that needs no human), reported alongside.
- *Gate:* **mean(B) − mean(A) with a 95% CI lower bound > 0 over ≥20 bootstrap resamples** of the rated pool (and ≥20 random-pair seeds for arm A). On pass, FC-22 is cleared to drive `discover.py` prompting non-trivially; on fail, ship as an advisory Lane-4 surface only and say so (mirrors `BUILD_PLAN` §3.2 "downgrade to human-in-the-loop and say so"). Script → `experiments/exp_rq_e46_negative_space.py`; results → `results/` + one line in `results/FINDINGS.md`. The proxy held-out-edge recovery arm is runnable with **zero human** for CI; the expert-rating gate is the authoritative one.

**Acceptance + ONE runnable check.**
- *Acceptance:* on a fixture entity graph where `X–Y1`, `Y1–Z`, `X–Y2`, `Y2–Z` exist as claims but `X–Z` does not (and a hub `H` connected to everything), `missing_edge_candidates()` returns `(X, Z)` as a candidate; its `path` cites the real `Y1`/`Y2` claim_ids and their signs; `composed_sign` is correct when both bridges share signs and `"ambiguous"` when they conflict; a pair that *is* directly claimed is **absent**; a pair whose only shared neighbour is the hub `H` scores strictly below the `Y1/Y2` pair (Adamic–Adar down-weighting works); `provenance=="INFERRED"` on every row; no KG write occurs.
- *Runnable check:* `tests/test_negspace.py::test_missing_edge_candidates` — builds a fake KG (stubs `kg.beliefs` returning claim dicts + a fake `engine.dependency_graph`), asserts the above. `pytest tests/test_negspace.py -q`. Plus `python -m persona.analysis.negspace` self-check (fake-KG `__main__`, no DB — same idiom as `dependency.py:69-108`).

**Effort:** M (one pure analysis module ~150 LOC incl. `_adamic_adar_gaps` helper + `__main__` self-check; one experiment harness; one test). No new dependency (stdlib `math` only).
**Deps:** FC-4 `engine.dependency_graph` (landed); public `kg.beliefs`/`dependency_edges`/`contradictions` (landed). CCP-30a into `discover.py` is non-blocking. Nothing un-landed blocks.

---

## 4. Sequencing

1. **M0:** land `negspace.py` with the FC-22 signature + a typed empty return (`[]` when KG is `None`/topic empty) and add the `engine.py` re-export, so Lane 4 can build its gap strip against the shape from hour 1.
2. Implement the pure core: entity projection, `_adamic_adar_gaps`, exclusion set, sign composition → `test_negspace.py` green on the fake-KG fixture (no DB, no model).
3. Wire the real `kg.beliefs` / `engine.dependency_graph` reads + `run_action`/`question` shaping + optional notebook emit.
4. Author + run `exp_rq_e46_…`; on pass, append RQ-E46 to `RESEARCH_QUALITY_PROGRAM.md` and a result line to `results/FINDINGS.md`.
5. Hand FC-22 to Lane 1 (CCP-30a prompt block) and Lane 4 (value-surface gap strip). Both are additive and can land anytime after M0.

Self-contained after M0; nothing else waits on it.

---

## 5. Test plan

- `tests/test_negspace.py` (runnable check above): entity projection, exclusion gate (adjacent / DEPENDS_ON / contradiction pairs dropped), Adamic–Adar hub-down-weighting (hub-only pair ranks below specific-intermediary pair), `min_intermediaries` floor, sign composition (`+`/`-`/`ambiguous`/`unknown`), grounding (`path` cites real claim_ids), purity (no KG write — assert via a fake KG that records mutations and expects none), `provenance=="INFERRED"`.
- `experiments/exp_rq_e46_negative_space.py`: ≥20-seed / ≥20-bootstrap comparison (negspace top-N vs random non-adjacent pairs), reports mean expert-rating delta ± 95% CI (and the zero-human held-out-edge recovery proxy), writes `results/rq_e46_*.json`, prints GO/NO-GO vs the gate. Seeded; deterministic under fixed `PYTHONHASHSEED`.
- No mocking of the trust boundary: `path` claim_ids are checked to be real members of the input claim set; exclusion is checked against the actual adjacency/DEPENDS_ON/contradiction sets, not a stub verdict.

---

## 6. Open questions

1. **CCP-30a (`discover.py` prompt block) — Lane 1 ack?** Non-blocking (FC-22 stands alone for Lane 4), but it's what lets the negative space feed the *generative* loop rather than only a read surface. *Lane 1: land the additive block, or prefer gaps stay Lane-4-only until RQ-E46 passes?*
2. **Value-surface placement (Lane 4):** a dedicated "unstudied but well-connected" gap strip beside the VoI queue, vs interleaved. Non-blocking — FC-22's shape is frozen either way. Deliberately **not** folded into `engine.value_queue` rows (a gap has no `resolves_claim_id`; folding would break the FC-4 row contract).
3. **RQ-E46 expert pool:** who supplies blinded 1–5 understudied-ness ratings on the merged candidate pool, and on which KG slice (Gladstone / a public co-occurrence graph with held-out edges)? The zero-human held-out-edge recovery proxy is runnable immediately; the authoritative expert-rated gate needs a rater. *Domain input required before the gate can close.*
4. **Longer paths (ABC → ABCD):** v1 is strictly 2-hop (one intermediary layer). Length-3 bridges (Swanson "closed vs open" discovery) multiply candidates and noise super-linearly. Deferred; `min_intermediaries`/Adamic–Adar on 2-hop is the evidence-backed first cut. Revisit only if RQ-E46 clears and 2-hop recall is the bottleneck.
