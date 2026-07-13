# PRD-23 — SemMedDB integration

> **Owner lane:** 3 (Intellectual engine, forensics & data acting-loop) · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (auto-*seed candidate* edges; the LLM tagger confirms, humans anchor) · **Depends-on:** FC-3 (`kg.add_dependency_edge`, `kg.dependency_edges`, `kg.citation_support_ratio` — Lane 2, landed), PRD-03 **F3.1** `analysis/dependency.py::extract_edges` (Lane 3, same lane), `ingest/service.py::IngestService` (shared infra, landed).

---

## 0. Summary + capability unlocked

BUILD_PLAN §4.4 lists five named reuse sources. Four are wired (`europepmc`, `opentargets`, `clinicaltrials`, GEO/`datasets`); **SemMedDB is the one still unwired** (`Initial Planning Docs/BUILD_PLAN.md:181,395`; backlog #8 at `docs/prd/IDEAS_BACKLOG.md:43`). SemMedDB is NLM's PubMed-scale repository of ~120M **semantic predications** — `subject–PREDICATE–object` triples machine-extracted by SemRep, each carrying a **PMID and the exact source sentence** (Kilicoglu et al., *Bioinformatics* 2012, "SemMedDB: a PubMed-scale repository of semantic predications").

Today the dependency graph (PRD-03 F3.1) is bootstrapped from a cold start: the LLM tagger is shown claim pairs that merely *share an entity* and must propose typed relations blind. That is high-recall-hungry and precision-fragile — the RQ-E06 baseline sits at ρ 0.38–0.50 and edge precision is the gate that is not yet met (`docs/prd/PRD-03-intellectual-engine.md:82`).

**Capability unlocked:** a cached SemMedDB client that (a) turns curated predications into **candidate dependency edges** — pre-typed and PMID-grounded — that *seed* the F3.1 LLM tagger instead of asking it to hallucinate structure from nothing, and (b) offers per-claim **corroboration** (independent machine-extracted PubMed sentences agreeing/disagreeing with a stored belief) to the membrane. SemMedDB never asserts truth: predications are **READ** evidence with exact PMID/sentence provenance; they narrow and prior the candidate set, and the F3.1 tagger + exact-span gate confirm or refute each one. The bet — gated by a new experiment — is that curated seeding lifts dependency-edge precision above the LLM-only baseline.

---

## 1. File ownership (disjoint)

| File | New? | Note |
|---|---|---|
| `persona/ingest/semmeddb.py` | **new** | Lane 3 (new-file-ownership rule, PRD-00 §4: a new non-colliding file is owned by the creating lane). The client + loader + predicate map + seeding/corroboration functions. |
| `persona/analysis/dependency.py` | (created by PRD-03 F3.1, **Lane 3**) | Additive: `extract_edges` gains an optional `seeds=` param. Same lane — no cross-lane edit. Coordinate ordering with F3.1 (see §4). |
| `experiments/exp_rq_e35_semmeddb_seeding.py` | **new** | Lane 4 owns `experiments/*`; **this experiment is authored by Lane 3** (it validates a Lane-3 mechanism and reuses the RQ-E06 Lane-3 fixture). Flagged as the one cross-lane touch below. |
| `docs/RESEARCH_QUALITY_PROGRAM.md` | edit (registry row) | append RQ-E35 row only; append-only, like the gate-decisions ledger. |
| `persona/tests/test_semmeddb.py` | **new** | Lane 3. |

**Boundary files (NOT edited here):**
- `persona/memory/membrane.py`, `persona/memory/calibrate.py` — **Lane 2**. SemMedDB corroboration reaches the membrane through a **read-only function this PRD provides** (FC-14 below, a CONTRACT CHANGE PROPOSAL); Lane 3 does not edit membrane.py. Until Lane 2 opts in, the dependency-seeding capability (the experimentally-gated core) ships fully self-contained.
- `persona/memory/kg.py` — **Lane 2**. Edges are written only through the existing FC-3 `kg.add_dependency_edge` **by the F3.1 tagger**, never directly by `semmeddb.py`. Calling FC-3 is not editing.
- `experiments/exp_rq_e35_semmeddb_seeding.py` — physically under Lane 4's `experiments/*` tree. Flagged: Lane 3 authors it; no other Lane-4 file is touched. (Same arrangement PRD-03 uses for `exp_rq_e06_*`.)

The FC-3 signature that decouples this lane from Lane 2's KG internals: `kg.add_dependency_edge(src_claim_id, dst_claim_id, rel_type, confidence, span)` (`persona/memory/kg.py:325`) and `kg.dependency_edges(topic)` (`kg.py:339`).

---

## 2. Frozen contracts

**Consumed:**
- **FC-3** (Lane 2): `kg.add_dependency_edge(...)`, `kg.dependency_edges(topic)`, `kg.citation_support_ratio(claim_id)`. Verbatim; unchanged.
- **PRD-03 F3.1** (Lane 3, same lane): `dependency.extract_edges(topic=None, *, parent_id=None)` gains `seeds=None` (additive kwarg, in-lane).
- **CCP-1** (`ingest/service.py` `get_json/post_json` `headers=` kwarg) — used if a local SemMedDB API mirror needs a token; not required for the public path.

**Provided (new), and one CONTRACT CHANGE PROPOSAL:**

- **FC-14 (NEW — Lane 3 provides, `persona/ingest/semmeddb.py`) — SemMedDB read interface.** Pure reads over a cached SemMedDB backend; no belief writes.
  - `predications(subject: str, obj: str | None = None, *, predicates: list[str] | None = None, min_reliability: float = 0.6, limit: int = 50) -> list[dict]` — each row `{subject, predicate, object, subject_cui, object_cui, pmid, sentence, reliability}`. `sentence` is the exact SemRep source sentence (the grounding span); rows below `min_reliability` (per-predicate, see `PREDICATE_RELIABILITY`) are dropped (abstain, not asserted).
  - `seed_edges(claims: list[dict], *, min_reliability: float = 0.7, max_seeds: int = 200) -> list[dict]` — given Persona claims (the `kg.claims_about(...)` shape: `claim_id, subject, object, …`), return **candidate** edges `{src_claim_id, dst_claim_id, rel_type_prior, predicate, pmid, sentence, reliability}` where a predication links the (canonicalized) entities of two distinct claims. **Candidates only** — for the F3.1 tagger, never written to the KG here.
  - `corroboration(subject: str, obj: str, effect_sign: str) -> dict` → `{predications: [...], n_pmids: int, agree: int, disagree: int, reliability: float, abstained: bool}`. `agree`/`disagree` compare each predication's sign (via `PREDICATE_MAP` sign) to the belief's `effect_sign`; `abstained=True` (distinct from `agree=0`) when no reliable predication is found.
  - Module constants: `PREDICATE_MAP: dict[str, tuple[str, str]]` (SemRep predicate → `(dep_rel_type, effect_sign)`), `PREDICATE_RELIABILITY: dict[str, float]`.

  **CONTRACT CHANGE PROPOSAL CCP-23a (→ Lane 2, membrane corroboration):** Lane 2's membrane/calibrate MAY consume `semmeddb.corroboration(...)` as an **additional READ-tier corroboration signal** in `calibrate.admit_decision` / the membrane's convergence view. Constraint (non-negotiable, stated for the acker): SemMedDB corroboration is machine-extracted (SemRep precision ≈0.75) and **must NOT increment `independent_source_count` / count as an independent lab** — it is a separate, lower-weight, provenance-tagged signal surfaced alongside human-read convergence, never folded into it. Until Lane 2 acks + wires this, FC-14 is unused by the membrane and only the dependency-seeding path (fully Lane 3) is live. No signature of FC-2/FC-5 changes.

---

## 3. Features

### F23.1 — Cached SemMedDB client (`ingest/semmeddb.py`)

**Problem & evidence.** SemMedDB is named as a reuse source (`BUILD_PLAN.md:181,395`) but there is no client — `ingest/` has `openalex.py`, `sources.py`, `web.py`, `fetch.py` only (verified: `ls persona/ingest/`). SemMedDB itself is distributed by NLM as SQL dumps that require a **UMLS license** (licensing must be respected). A licence-free public route exists for querying the same triples: **MELODI Presto** (MRC-IEU, Bristol; Elsworth & Gaunt, *Bioinformatics* 2021, "MELODI Presto: a fast and agile tool to explore semantic triples derived from biomedical literature") exposes SemMedDB predications with PMIDs over a public REST API.

**Design.**
- New `persona/ingest/semmeddb.py`, mirroring `sources.py` conventions: module-level functions, all HTTP through `service()` (cache + rate-limit + backoff), never a bare `httpx` call.
- **Two pluggable backends, one interface (FC-14).** `_backend()` selects by config:
  - `SEMMEDB_DUMP` set → **local-dump backend**: read a prebuilt SQLite index of the `PREDICATION` + `SENTENCE` + `CITATIONS` tables (built once by an offline `build_index()` helper from the licensed dump; ground truth, offline, full fidelity, PMID+sentence per row).
  - else → **MELODI Presto backend** (default for the demo): `service().get_json(...)` / `post_json(...)` against the public API, cached aggressively so the demo money-shot never depends on a live call (CLAUDE.md §4 caching rule). **The exact endpoint + response shape is verified against a live call in a scratch script before wiring** (CLAUDE.md §1 "never assume an endpoint"; the client is backend-pluggable precisely so the local dump is authoritative if the public shape drifts).
- `PREDICATE_MAP` — conservative SemRep-predicate → `(dep_rel_type, effect_sign)`, using only the FC-3 `DEP_REL_TYPES` enum (`kg.py:51`): e.g. `CAUSES/INDUCES/PREDISPOSES → (derives_from, '+')`, `STIMULATES/AUGMENTS → (supports, '+')`, `INHIBITS/DISRUPTS → (contradicts, '-')`, `PART_OF/ISA → (presupposes, 'na')`, `TREATS/PREVENTS → (supports, '-')` (treats = reduces the disease). Weak/ambiguous predicates (`ASSOCIATED_WITH`, `COEXISTS_WITH`, `INTERACTS_WITH`, `COMPARED_WITH`) map to **no seed** — they carry no dependency direction and would only add noise (abstain).
- `PREDICATE_RELIABILITY` — per-predicate precision priors from the SemRep evaluation literature (Kilicoglu 2012 reports ~0.75 overall; causal/treatment predicates score higher than association). Used as the default `reliability` and the `min_reliability` gate.
- Entity matching uses the KG canonicalizer so SemMedDB CUIs/names align with Persona's canonical entities (reuse `canon.canon` via the claim's already-canonicalized `subject`/`object`; match on normalized strings, not raw CUIs, since Persona entities are name-keyed — `kg.py:118`).

**Epistemic guardrails.** Every returned row carries `pmid` + `sentence` (the exact grounding span) — a predication with no sentence is dropped (mirrors the F3.1 / `audit.py:216` no-span-no-edge rule). Provenance is **READ** (machine-extracted). `predications`/`corroboration` abstain (empty / `abstained=True`) rather than fabricate when nothing reliable matches. Nothing in this file writes to the KG or the self.

**Required experiment.** Trivial — this feature is cached-API plumbing + a static predicate map. Correctness verified by an offline unit test on a cached fixture (a handful of real predications with known PMIDs) + the `PREDICATE_MAP` range check. (The *scientific* value of seeding is gated by F23.2 / RQ-E35.)

**Acceptance + runnable check.** (a) every `predications`/`seed_edges` row has non-empty `pmid` and `sentence`; (b) every `rel_type_prior` ∈ `DEP_REL_TYPES`; (c) a below-threshold predicate is excluded. `pytest persona/tests/test_semmeddb.py::test_rows_are_spanned_and_typed` (runs against a cached JSON fixture, no network).

**Effort** M · **Deps** `ingest/service.py` (landed), `kg.py:51` `DEP_REL_TYPES`.

---

### F23.2 — Seed the F3.1 dependency tagger (`analysis/dependency.py`, additive)

**Problem & evidence.** F3.1 `extract_edges` currently proposes typed edges from claim pairs that only share an entity (`docs/prd/PRD-03-intellectual-engine.md:74`), a cold-start blind pass; RQ-E06 edge precision is the unmet gate (`PRD-03:82`). Curated predications give the tagger a **pre-typed, PMID-grounded candidate set** — the classic "seed the extractor with a curated KB" pattern.

**Design.**
- `dependency.extract_edges(topic=None, *, parent_id=None, seeds=None)` — additive `seeds` kwarg (default `None` ⇒ unchanged behaviour; keeps F3.1's own acceptance test green). Caller (the engine facade / the tagger job) computes `seeds = semmeddb.seed_edges(kg.claims_about(entities))` and passes them in.
- When `seeds` is present, the F3.1 model prompt is augmented: for each candidate `{src_claim_id, dst_claim_id, rel_type_prior, predicate, pmid, sentence}`, the tagger is asked to **confirm, re-type, or reject** the seeded relation **against an exact source span in Persona's own stored quotes** — the SemMedDB sentence is a *prior/hint*, not the grounding span. The edge is written via `kg.add_dependency_edge(src, dst, rel_type, confidence, span)` (FC-3) **only if the tagger returns an entailing Persona-side span** (unchanged F3.1 grounding guard). The PMID is recorded in the `span` provenance suffix (e.g. `"<persona quote> [seed:SemMedDB PMID:12345678]"`) so the seed's origin is auditable without a schema change.
- Data flow: `kg.claims_about` → `semmeddb.seed_edges` (candidates) → `extract_edges(seeds=…)` (LLM confirm/refute + Persona-span gate) → `kg.add_dependency_edge` → `kg.dependency_edges` (unchanged downstream).

**Epistemic guardrails.** **Seeds never auto-become edges.** A candidate is written only after the F3.1 tagger returns an entailing Persona-side exact span (no-fabricated-structure). The SemMedDB `rel_type_prior` can be overridden by the tagger (it may confirm the pair but re-type the relation) — the prior is a hint, the exact span is the authority. Provenance stays READ/INFERRED per the F3.1 node rule; the seed origin (PMID) is carried in the edge span for audit but adds no confidence on its own. Balanced autonomy: seeding auto-*surfaces* candidate edges; no anchor, no autonomous prioritization until RQ-E35 (this feature) **and** RQ-E06 (F3.1's own gate) pass.

**Required experiment — RQ-E35 (NEW; next free id, registry currently to E34).** Reuses the RQ-E06 hand-labelled gold set (≥60 claim pairs, `experiments/exp_rq_e06_evidence_tree.py`; `docs/RESEARCH_QUALITY_PROGRAM.md:184`) — no new gold labelling.
- **Hypothesis:** *SemMedDB-seeded extraction achieves higher dependency-edge precision than LLM-only extraction on the RQ-E06 gold set, without a recall collapse* — i.e. seeding's curated priors remove spurious edges the blind pass invents.
- **Metric:** edge precision (primary) and recall (guard), seeded vs LLM-only, mean ± 95% CI over 20 seeds on the fixed gold set (extraction is model-sampled).
- **Go/no-go gate:** `precision(seeded) − precision(llm_only) ≥ +0.05` (95%-CI lower bound > 0) **AND** `recall(seeded) ≥ recall(llm_only) − 0.05` (no recall collapse) → seeding is enabled in the F3.1 path that drives the dependency graph. Else: `seed_edges` stays available as a **candidate-only** annotation (surfaced, not driving), and the finding/reversal is logged to `results/FINDINGS.md#RQ-E35`.
- **Seeds:** 20. Script `experiments/exp_rq_e35_semmeddb_seeding.py`; results `results/FINDINGS.md#RQ-E35`.

**Acceptance + runnable check.** (a) `extract_edges(seeds=None)` is byte-identical in behaviour to pre-change (F3.1's `test_load_bearing_deterministic_and_spanned` still passes); (b) with `seeds` given, no edge is written whose `span` lacks a Persona-side quote (a SemMedDB sentence alone is insufficient); (c) a seeded candidate the tagger rejects produces no edge. `pytest persona/tests/test_semmeddb.py::test_seed_requires_persona_span` (stubs the model to "confirm without span" and asserts zero edges written).

**Effort** M · **Deps** F23.1, PRD-03 F3.1 (must land first — coordinate ordering), FC-3.

---

### F23.3 — Membrane corroboration read (`ingest/semmeddb.py::corroboration`, FC-14; CCP-23a)

**Problem & evidence.** A converged belief on 2 human-read labs is stronger if independent PubMed sentences (via SemMedDB) also state it — and *weaker/contested* if reliable predications disagree in sign. The membrane (`persona/memory/membrane.py`, Lane 2) currently converges only on Persona's own ingested claims (`_harvest`, `membrane.py:75`); it has no external corroboration signal.

**Design.**
- Lane 3 provides `corroboration(subject, obj, effect_sign)` (FC-14) — a pure read returning agree/disagree counts of reliable predications vs the belief's sign, plus `abstained`.
- **Membrane wiring is CCP-23a (Lane 2's edit, not this PRD's).** Lane 2, on ack, calls `corroboration` in `calibrate.admit_decision` / the convergence view and renders it as a **distinct, lower-weight, READ-tier** signal that **does not touch `independent_source_count`**. This PRD stops at providing the function + the fixture proving the sign logic; it does not edit membrane.py.

**Epistemic guardrails.** SemMedDB corroboration is READ, machine-extracted (SemRep ≈0.75 precision) — explicitly *not* an independent lab, never anchors, never auto-updates confidence. `abstained` is distinct from `agree=0` (no reliable predication ≠ predications that disagree). High-stakes belief changes still route to the human (FC-2) regardless of corroboration.

**Required experiment.** Trivial for the read function (deterministic sign tally over fixture rows; property-tested). The *decision-influencing* use of corroboration inherits Lane 2's calibration gate (RQ-E16) when CCP-23a is wired — no new gate for the raw signal.

**Acceptance + runnable check.** `corroboration` returns `abstained=True` when no reliable predication matches, `disagree>0` when a reliable opposite-sign predication exists, and never raises on an unknown entity. `pytest persona/tests/test_semmeddb.py::test_corroboration_sign_and_abstain`.

**Effort** S · **Deps** F23.1.

---

## 4. Sequencing

1. **F23.1** first — the client + `PREDICATE_MAP` + cached fixture. Self-contained; unblocks the rest. (Build-time: verify the MELODI Presto endpoint/shape in a scratch script; snapshot a real fixture into `persona/tests/`.)
2. **F23.3** — `corroboration` (trivial once F23.1 exists); file CCP-23a to Lane 2 in the HANDOFF dispatch log for async ack. Does not block F23.2.
3. **F23.2** — the seeding hook + **RQ-E35**. **Gated on PRD-03 F3.1 landing** (`extract_edges` must exist to accept `seeds=`). Coordinate with the F3.1 owner (same lane) so the additive kwarg lands in one edit. Run RQ-E35 before enabling seeding in the driving path.

If F3.1 is not yet landed when this lane starts: build F23.1 + F23.3 + the RQ-E35 harness against an `extract_edges` stub, wire the real `seeds=` param the moment F3.1 lands.

---

## 5. Test plan

- **`test_semmeddb.py::test_rows_are_spanned_and_typed`** (F23.1) — every row has `pmid`+`sentence`; every `rel_type_prior ∈ DEP_REL_TYPES`; sub-threshold predicate excluded. Cached fixture, no network.
- **`test_semmeddb.py::test_seed_requires_persona_span`** (F23.2) — stubbed model "confirms without span" ⇒ zero edges written (the SemMedDB sentence alone is not grounding).
- **`test_semmeddb.py::test_corroboration_sign_and_abstain`** (F23.3) — agree/disagree/abstain sign logic on a fixture.
- **`ingest/semmeddb.py` `__main__` self-check** — offline: assert `PREDICATE_MAP` values are all valid `(rel_type ∈ DEP_REL_TYPES, sign ∈ {+,-,na})` and that weak predicates map to no seed. (One runnable check per CLAUDE.md; no framework.)
- **`experiments/exp_rq_e35_semmeddb_seeding.py`** — the 20-seed precision/recall comparison; asserts the gate arithmetic and writes `results/FINDINGS.md#RQ-E35`.
- **F3.1 regression** — `test_dependency.py::test_load_bearing_deterministic_and_spanned` must still pass with the additive `seeds=None` default (proves the kwarg is non-breaking).

---

## 6. Open questions

- **OQ-1 (blocks nothing; informs F23.1 default backend).** MELODI Presto's exact triple-query endpoint + JSON shape must be confirmed live before wiring (CLAUDE.md §1). If the public API cannot return per-row PMID+sentence, the demo falls back to a **small pre-built local-dump SQLite fixture** committed for offline use — either way the epistemic contract (PMID+sentence per row) holds. Does not block other lanes.
- **OQ-2 (CCP-23a → Lane 2, async).** Does Lane 2 want `corroboration` surfaced in `calibrate.admit_decision`, or only in the membrane's read-only convergence view? Either satisfies the "never counts as an independent lab" constraint. Non-blocking: F23.1/F23.2 ship without it.
- **OQ-3 (informs `PREDICATE_MAP`, in-lane).** `TREATS/PREVENTS` mapped to `(supports, '-')` assumes the belief pair is `drug→disease` with a reduction sign; a `drug→symptom-relief` framing could read `'+'`. Resolved empirically by RQ-E35 (a mis-signed prior the tagger rejects costs recall, which the gate measures) — no external dependency.

---

**Provenance of every design claim here:** code cites are line-exact reads of `persona/ingest/service.py`, `persona/ingest/sources.py`, `persona/memory/kg.py` (`add_dependency_edge:325`, `claims_about:426`, `DEP_REL_TYPES:51`, `add_claim:108`), `persona/memory/membrane.py:75`, `docs/prd/PRD-03-intellectual-engine.md:74,82`, `docs/prd/PRD-00-overview.md` (FC-3, autonomy, RQ registry ≤E34), `Initial Planning Docs/BUILD_PLAN.md:181,395`. External sources named: Kilicoglu et al. 2012 (SemMedDB, *Bioinformatics*); Elsworth & Gaunt 2021 (MELODI Presto, *Bioinformatics*); SemRep precision ≈0.75 from the SemMedDB evaluation.
