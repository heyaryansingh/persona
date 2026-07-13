# PRD-21 — Cross-field mechanism translation

> **Owner lane:** 3 (Intellectual engine) · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced · **Opened:** 2026-07-13
> **Depends-on:** FC-3 (`kg.add_dependency_edge`, `kg.dependency_edges`) — already landed; existing public reads `kg.beliefs`/`kg.provenance`; `memory/embed.encode` (pure). No blocking dependency on any un-landed lane work.
> **Read first:** `PRD-00-overview.md` (frozen contracts FC-1…FC-13; new-file ownership rule 2026-07-13), `Initial Planning Docs/BUILD_PLAN.md` §3.6, `CLAUDE.md` epistemic charter.

---

## 0. Summary + capability unlocked

The same mechanism is routinely described in two subfields whose literatures **never cite each other** — what cardiology calls A is mechanistically what oncology calls B. A domain researcher constrained to their own field's vocabulary (and Persona's own reading, which is hard-gated to `selfmind.allowed_field_ids()` — see `reading/reader.py:87-94`, validated decisive in `experiments/exp_rq_e15_field_question_gate.py`) never sees the bridge. **This feature surfaces those bridges as typed, span-grounded, INFERRED candidate edges.**

Mechanism: local-embedding candidate alignment (bge-small via `memory/embed.encode`) over claim descriptions **across distinct field partitions**, followed by an LLM confirmation step grounded in **both** claims' exact verbatim spans. A confirmed alignment becomes a candidate `generalizes`/`operationalizes` dependency edge (FC-3) plus a rich record in an append-only Lane-3 ledger. It **never** asserts mechanistic identity — it proposes candidate evidence a human (or a downstream investigation) would otherwise never encounter.

**Capability unlocked:** "these two literatures are describing the same thing" — a concrete, checkable win natural on the Gladstone datasets (cross-reference a Perturb-seq hit against a mechanism named differently elsewhere). Feeds the flagship dependency map and the value-of-information queue with cross-field evidence no competitor produces.

---

## 1. File ownership (disjoint)

| File | New? | Lane | Note |
|---|---|---|---|
| `persona/analysis/crossfield.py` | **new** | 3 | The feature. Owned by Lane 3 (new-file rule 2026-07-13). |
| `experiments/exp_rq_e35_cross_field_translation.py` | **new** | 3 (→4 registry) | RQ-E35 harness. |
| `tests/test_crossfield.py` | **new** | 3 | Runnable acceptance check. |
| `docs/RESEARCH_QUALITY_PROGRAM.md` | edit (append RQ-E35 block) | 3 | Registry append only — never edits another RQ's rows. |

**Boundary files (imported, NOT edited):**
- `persona/memory/embed.py` — Lane 2. Called read-only: `encode(texts)` (pure, L2-normalized → cosine == dot, `embed.py:20-27`).
- `persona/memory/kg.py` — Lane 2. Called via FC-3 `add_dependency_edge` + public reads `beliefs`, `provenance`. **No edit.**
- `persona/reading/reader.py` source layout — Lane 1. Read-only: field partition recovered from each source's on-disk `meta.json` (`field_id`, written at `reader.py:145`). **No edit.**

**Decoupling FC:** field partition is read from disk artifacts + public KG reads, so **no Lane-2/Lane-1 edit is required for the default path.** The single optional cross-lane touch (CCP-21a) is non-blocking and additive.

---

## 2. FCs provided / consumed + contract-change proposals

**Provides — FC-21 (Lane 3, new `persona/analysis/crossfield.py`):**
```python
crossfield.run(topic: str | None = None, *, limit: int = 250,
               min_sim: float = 0.62, write: bool | None = None) -> dict
#   -> {n_candidates:int, n_confirmed:int, n_abstained:int,
#       edges:[{src_claim_id, dst_claim_id, rel_type, confidence}],
#       ledger_path:str, gated:bool}
crossfield.alignments(topic: str | None = None) -> list[dict]
#   -> [{src_claim_id, dst_claim_id, src_field, dst_field, rel_type, direction,
#        confidence, src_span, dst_span, rationale, provenance, at}]
```
`write=None` ⇒ auto: emit KG edges **only** if `ops_dir/rq_e35.passed` exists (mirrors FC-4 E17 / FC-13 E34 "advisory-until-gate" pattern); otherwise ledger-only (advisory). `write=True/False` forces. Lane 4 renders from `alignments()` (ledger read), never from raw `dependency_edges` (which would be ambiguous with within-field dependency edges).

**Consumes:** FC-3 `kg.add_dependency_edge(src, dst, rel_type, confidence, span)`, `kg.dependency_edges(topic)`; public `kg.beliefs(...)`, `kg.provenance(claim_id)`; `memory/embed.encode`.

**CONTRACT CHANGE PROPOSAL — CCP-21a (OPTIONAL, → Lane 2, non-blocking).** Add `"cross_field"` to `DEP_REL_TYPES` (the frozenset at `kg.py:51-52`). One-line, additive, backward-compatible (existing consumers unaffected; no signature change). *Motivation:* a dedicated symmetric-synonymy bucket so cross-field bridges are first-class in `dependency_edges` rather than overloading `generalizes`/`operationalizes`. **Default path ships without it** — see F1 Design. Adopt only if Lane 2 + Lane 4 ack; until then `add_dependency_edge(..., "cross_field", ...)` would raise `ValueError`, so the default uses the two existing rel_types.

**Considered, NOT proposed — persist `Source.field_id` on the KG node.** `upsert_source` (`kg.py:97-106`) drops the `field_id` that's already in `meta`. Persisting it would give a clean KG-side field join, but it's a Lane-2 edit and unnecessary: the field partition is already durable in each source's `meta.json`. Recorded here as a future cleanup (CCP-21b) so it isn't silently re-discovered; **not required by this PRD.**

---

## 3. Features

### F21.1 — Cross-field alignment (candidate generation → grounded confirmation → typed edge)

**Problem & evidence.**
- *Code:* Persona's reading is hard-gated to a persona's ≤3 declared fields (`reading/reader.py:87-94` → `selfmind.allowed_field_ids`, `selfmind.py:97-141`; source-side field filter `ingest/sources.py:55-56`). Within-field synonymy is already handled by entity canonicalization at claim time (`kg.add_claim` canonicalizes subject/object, `kg.py:112-118`). What is structurally invisible is the **cross-partition** synonym: two claims whose subjects/objects canonicalize to different strings and whose sources sit in different OpenAlex fields, yet describe one mechanism. Nothing in the repo surfaces this.
- *Research/source:* `BUILD_PLAN.md` §3.6 ("same mechanism described in two subfields in vocabularies that never cite each other … **Test:** curate known cross-field synonymous mechanisms; measure recovery rate vs. embedding-similarity baseline"). Cross-domain literature-based discovery in the Swanson/ABC tradition (undiscovered public knowledge) motivates the win; the modern instantiation is dense-retrieval candidate generation + an LLM entailment/identity check grounded in exact spans (the same recall-generator / precision-gate split Persona already uses in the membrane — cheap embedding proposes, exact-span check disposes, `RQ-E01a` result at `RESEARCH_QUALITY_PROGRAM.md:147`).

**Design.**
*Files:* new `persona/analysis/crossfield.py`. Imports: `..memory import embed, kg` (via `context.get_persona().kg`), `..context.get_persona`, `..config`, `..budget.budget`, `..events.log`, `anthropic.Anthropic`.

*Data flow:*
1. **Claim set + descriptions.** `claims = kg.beliefs(min_independent=1, min_conf=0.5, limit=limit)` (public read; `kg.py:223`). Each claim's description string = `f"{subject} {relation} {object}"`.
2. **Field partition (per claim).** For each claim, `slugs = [s["slug"] for s in kg.provenance(cid)["sources"]]` (`kg.py:253-270`); look up each slug's field via `get_persona().paths.sources_dir / slug / "meta.json"` → `field_id` (written at `reader.py:145`). A claim's partition = the set of its sources' `field_id`s. **Claims with no resolvable `field_id` are skipped** (can't prove they're cross-field — conservative). Cache the slug→field_id map in-process.
3. **Candidate generation (embedding, across partitions only).** `V = embed.encode(descriptions)` (L2-normalized). Cosine matrix `V @ V.T`. For each claim keep its top-`k_neighbors` (default 8) neighbours whose **field partition is disjoint** from its own and whose `sim ≥ min_sim`. Dedupe unordered pairs; cap at `max_pairs`. This is a **recall generator only** — never an assertion.
4. **Exact-span retrieval.** For each candidate pair, `src_span`/`dst_span` = the verbatim source quote backing each claim (the `quote` on `SUPPORTED_BY`, surfaced by `kg.provenance`). If either span is empty/non-verbatim → abstain (drop the pair). This preserves the "abstain rather than fabricate" boundary.
5. **LLM confirmation grounded in BOTH spans.** One `client.messages.create(model=config.MODEL_WORKER, ...)` per pair (idiom per `agents/critic.py:63-68`), system prompt: *"You are given two claims from two different research fields, each with a verbatim source span. Decide whether they describe the SAME underlying biological mechanism under different vocabularies. You may ONLY answer yes if the identity is supported by both spans; quote the licensing phrase from EACH. If it is a loose analogy, a different mechanism, or you are unsure, answer `abstain`. If yes, classify the relation: `generalizes` (span A states the general mechanism, span B a field-specific instance/measurement of it) or `operationalizes` (span B is A named/assayed in field 2). Output strict JSON: {aligned, rel_type, direction, confidence, src_licensing_quote, dst_licensing_quote, rationale}."* Cost via `budget().add(_cost(resp.usage))`; guard `config.have_key() and budget().can_spend()`.
6. **Disposition.**
   - `aligned=false` or `confidence < 0.6` or a licensing quote not a verbatim substring of its span → **abstain**; append `{...,"provenance":"abstain","abstain_reason":...}` to the ledger.
   - Confirmed → record `{src_claim_id, dst_claim_id, src_field, dst_field, rel_type∈{generalizes,operationalizes}, direction, confidence:min(0.7, llm_conf), src_span, dst_span, rationale, provenance:"INFERRED", at}` to the ledger `ops_dir/crossfield.jsonl` (append-only, like `gate_decisions.jsonl`). Emit `log().emit("thought"/"artifact", ...)` for the living notebook.
   - **Edge emit (gated):** if `write` resolves True, `kg.add_dependency_edge(src, dst, rel_type, confidence, span=src_span[:600])` with `rel_type` = the LLM's `generalizes`/`operationalizes` (both already in `DEP_REL_TYPES`, `kg.py:51-52` — no contract change). Direction: `src` = the more-general/mechanism side. If CCP-21a is adopted, `rel_type="cross_field"` is used instead for symmetric synonymy.
7. **`alignments(topic)`** reads + filters the ledger (topic substring match on either claim's subject/object) for Lane 4.

*Seams:* pure, side-effect-isolated except (a) the ledger append and (b) the gated KG edge. `run(write=False)` is fully pure w.r.t. the KG — this is what the experiment and the test drive. Candidate-generation logic factored into a module-level pure helper `_cross_field_pairs(vecs, partitions, *, k, min_sim, max_pairs) -> list[tuple[int,int,float]]` so the experiment reuses the *exact* ranking under both arms.

**Epistemic guardrails.**
- A proposed alignment is **INFERRED candidate evidence**, never `HUMAN_CONFIRMED`/`TESTED`; it **never asserts mechanistic identity**, never anchors, never writes belief confidence, never creates a `CONTRADICTS` edge, never routes as high-stakes autonomously.
- **Two-gate discipline:** embedding similarity is candidate-only (recall); the LLM span-confirmation is the precision gate; **both** exact spans must be verbatim and must license the identity, or abstain.
- **Cross-partition only:** pairs within one field are dropped (that's canonicalization's job, not this feature's), which also prevents trivial same-vocab "wins."
- **Abstain-first:** weak similarity, missing/non-verbatim span, low LLM confidence, or a non-verbatim licensing quote ⇒ abstain, logged with reason. Skipped ≠ passed.
- Confidence capped at 0.7 (an INFERRED cross-field guess must never out-weigh a directly-supported belief).
- **Autonomy = Balanced:** ledger candidates are always advisory; **KG edges are written only after RQ-E35 passes** (`ops_dir/rq_e35.passed`). Until then, `run` is ledger-only regardless of `write=True` unless an explicit `PERSONA_CROSSFIELD_FORCE` override is set (dev/testing).

**Required experiment — RQ-E35** (next free after E34).
- *Hypothesis:* the embedding-candidate → LLM-span-confirmation pipeline recovers KNOWN cross-field synonymous mechanisms at higher F1 (equivalently, higher recovery at matched precision) than an **embedding-similarity-only** baseline (cosine ≥ τ, τ swept).
- *Data:* a curated, frozen gold set of ~30–60 KNOWN cross-field synonymous mechanism pairs spanning ≥2 field pairs (e.g. cardiology↔oncology, immunology↔neuroscience), plus hard negatives (cross-field pairs that are lexically/embedding-similar but mechanistically distinct). Freeze a content hash. Each item = (claim_A desc + span + field, claim_B desc + span + field, label∈{synonym, distinct}).
- *Arms:* **(A)** similarity-only: predict "aligned" iff cosine ≥ τ. **(B)** ours: candidate (cosine ≥ `min_sim`) → LLM span-confirmation. The LLM confirmer is called live if a key is present; for a deterministic offline harness, a curated/mocked confirmer replays fixed verdicts so the *pipeline logic* (partition gate, span gate, thresholding) is what's measured, and the live-key run is a separate reported number.
- *Metric:* recovery rate (recall of gold synonyms) and precision; **primary = F1, or recall at the τ that matches baseline precision.**
- *Gate:* **ours F1 > baseline F1 with a 95% CI lower bound > 0 over ≥20 bootstrap resamples** of the gold+negative set (and ≥20 candidate-generation seeds). On pass, write `ops_dir/rq_e35.passed` and enable auto edge-emit; on fail, ship ledger-only advisory and say so (mirrors `BUILD_PLAN.md` §3.2/E6 "downgrade to human-in-the-loop and say so"). Script → `experiments/exp_rq_e35_cross_field_translation.py`; results → `results/` + a line in `results/FINDINGS.md`.

**Acceptance + ONE runnable check.**
- *Acceptance:* on a fixture of 2 synonymous cross-field claims + 1 cross-field distractor, `run(write=False)` returns `n_confirmed==1` (the synonym pair) and the distractor is in `n_abstained`; every confirmed record has non-empty verbatim `src_span`/`dst_span` and `provenance=="INFERRED"`; no KG edge is written when `ops_dir/rq_e35.passed` is absent.
- *Runnable check:* `tests/test_crossfield.py::test_cross_field_alignment` — builds a fake KG (or stubs `kg.beliefs`/`kg.provenance` + a fake `sources_dir`), monkeypatches the LLM confirmer to a deterministic function, asserts the above. `pytest tests/test_crossfield.py -q`.

**Effort:** M (one analysis module ~180 LOC, one experiment harness, one test).
**Deps:** FC-3 (landed); `memory/embed` (landed); no un-landed lane blocks.

---

## 4. Sequencing

1. **M0:** land `crossfield.py` with FC-21 signatures + a typed empty return (`run` → zeros, `alignments` → `[]`) so Lane 4 can build its surface against the shape from hour 1.
2. Implement `_cross_field_pairs` + field-partition resolution + span retrieval (pure, no LLM) → `test_crossfield.py` green with a mocked confirmer.
3. Wire the live LLM confirmation + ledger append + gated edge emit.
4. Author + run `exp_rq_e35_...`; on pass, drop `ops_dir/rq_e35.passed`; append RQ-E35 to `RESEARCH_QUALITY_PROGRAM.md` and a result line to `results/FINDINGS.md`.
5. Hand FC-21 `alignments()` shape to Lane 4 for rendering (flagship dependency map cross-field strip or a dedicated "bridges" panel — Lane 4's call).

Self-contained after M0; nothing else waits on it. If CCP-21a is adopted it slots in at step 3 without reordering.

---

## 5. Test plan

- `tests/test_crossfield.py` (runnable check above): partition gate (same-field pair dropped), span gate (empty/non-verbatim span → abstain), confirmation thresholding (low conf → abstain), edge-gating (no `rq_e35.passed` ⇒ no KG write), ledger append shape.
- `experiments/exp_rq_e35_cross_field_translation.py`: ≥20-seed bootstrap comparison (ours vs similarity-only), reports F1 mean ± 95% CI per arm, writes `results/rq_e35_*.json`, prints GO/NO-GO vs the gate. Seeded; deterministic under fixed `PYTHONHASHSEED`.
- No mocking of the trust boundary: spans are checked as real verbatim substrings; the LLM is mocked **only** to make the *pipeline* deterministic — the live-key confirmer number is reported separately, not gated on.

---

## 6. Open questions

1. **CCP-21a (`"cross_field"` in `DEP_REL_TYPES`) — adopt or not?** Blocks nothing (default uses existing `generalizes`/`operationalizes`), but needs Lane 2 + Lane 4 ack if we want cross-field bridges first-class in `dependency_edges`. *Lane 2, Lane 4: preference?*
2. **CCP-21b (persist `Source.field_id` on the KG node):** cleaner field join than reading `meta.json`, but a Lane-2 edit to `upsert_source`. Deferred; not required. *Lane 2: worth the additive `SET s.field_id`?*
3. **Lane 4 surface for `alignments()`:** flagship dependency-map cross-field strip vs a dedicated "cross-field bridges" panel. Non-blocking — FC-21's ledger read shape is frozen regardless.
4. **Gold-set curation for RQ-E35:** who supplies the ~30–60 known synonymous cross-field pairs + hard negatives (domain input)? The experiment is otherwise ready; the gate can't run without a frozen gold set.
