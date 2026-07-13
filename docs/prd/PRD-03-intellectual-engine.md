# PRD-03 — Intellectual engine, forensics & data acting-loop

> Owner: implementer lane 3 · Status: DRAFT-for-implementation · Autonomy: Balanced · Depends on: FC-2 (`inbox.file_handoff`, Lane 2), FC-3 (`kg.add_dependency_edge` / `dependency_edges` / `citation_support_ratio` / `provenance_breakdown`, Lane 2)

## 0. Summary and how this lane advances the vision (5-8 sentences)

This lane builds the part of Persona that *reasons about the field as a structure* and then *acts on it* — the intellectual engine that turns a heap of claims into a dependency graph, a value-of-information queue, a trajectory, and a dark-literature signal, then closes the acting loop by resolving real public datasets to disk. Today the mind reads, extracts, synthesizes, and audits, but three seams leak: contradictions are surfaced yet never escalated to a human (`fieldmap.py`), notes are regenerated rather than diffed so the "how understanding evolved" story is lost (`synthesizer.py:171`), and the UI's "load-bearing" / "value" scores are client-side degree heuristics honestly labelled *unvalidated* (`index.html:2009,2012`). We replace those heuristics with server-computed, versioned, evidence-typed metrics: a ClaimFlow-style typed-relation dependency graph feeding `load_bearing` via PageRank over `derives_from`, a VoI queue ranked by downstream dependency mass × uncertainty ÷ cost, a citation-vs-support divergence flag ("high-cited, never-tested"), and a per-target dead-science meter from the ClinicalTrials results gap. We harden the trust layer: Retraction Watch becomes first-class ingest metadata with a descendant-contamination walk, and the robustness auditor gains a `ResearchSession` wrapper (append-only, artifact-hashed, replay-verifiable — parity with `analyst.py`) plus calibrated "partial/unverified" reanalysis scoped to narrow recomputations. Every new score is provenance-typed and abstains rather than fabricates; every forensic check declares an applicability gate and emits an explicit `not_applicable` state so an out-of-domain check never masquerades as a pass — the correctness boundary of this lane. The two load-bearing metrics (dependency edges, VoI ranking) do not drive autonomous prioritization until they clear their gates (RQ-E06 edge precision, RQ-E16 VoI-vs-expert Spearman); until then they render as *candidate* rankings, exactly as the honest UI already labels them.

## 1. File ownership (this lane's DISJOINT set)

**Edited (this lane only):**
- `persona/analysis/forensics.py` — add DEBIT + per-check applicability gates + `not_applicable` state (F3.8)
- `persona/agents/audit.py` — `ResearchSession` wrapper, retraction/contamination pass, narrow-reanalysis scoping (F3.7)
- `persona/synthesis/fieldmap.py` — contradiction → human handoff (F3.11)
- `persona/synthesis/synthesizer.py` — note-version diffing at write (F3.11)
- `persona/ingest/sources.py` — thread `field_ids` through crossref/europepmc/arxiv failover (F3.10)
- `persona/tools/science.py` — `geo_lookup`, `geo_search`, `openml_search`; extend `ncbi_search` (F3.9)
- `persona/tools/datasets.py` — no signature change; consumed by F3.9 (SOFT/matrix fetch already allowlisted)

**New (this lane creates):**
- `persona/analysis/dependency.py` — dependency/load-bearing graph + citation-vs-support (F3.1, F3.3)
- `persona/analysis/trajectory.py` — velocity/acceleration/independence-drift (F3.4)
- `persona/analysis/value_queue.py` — VoI queue (F3.2)
- `persona/analysis/darklit.py` — dead-science meter (F3.5)
- `persona/analysis/engine.py` — the FC-4 facade (`engine.dependency_graph`, `engine.value_queue`) aggregating the above
- `persona/ingest/retraction.py` — Retraction Watch + contamination (F3.6, FC-6)
- `persona/synthesis/synthesizer.py` note-diff sidecar is written in-module (no new file)

**Boundary files another lane also touches (decoupled by an FC):**
- `persona/memory/kg.py` — **Lane 2 owns**. This lane only *calls* `kg.add_dependency_edge`, `kg.dependency_edges`, `kg.citation_support_ratio`, `kg.provenance_breakdown` (FC-3). We never edit kg.py; if a call shape is wrong we file a CONTRACT CHANGE PROPOSAL.
- `persona/inbox.py` — **Lane 2 owns** (new). This lane only *calls* `inbox.file_handoff(kind, dossier)` (FC-2) from `fieldmap.py`.
- `persona/api/static/index.html` — **Lane 4/API owns** the render of `engine.dependency_graph` / `engine.value_queue`. This lane provides the FC-4 data; the API lane consumes it. We do not edit the HTML.

> Note on the FC-4 facade: FC-4 names `engine.dependency_graph` and `engine.value_queue`. The prompt's file list names `analysis/dependency.py` and `analysis/value_queue.py` as the implementations. We add a thin `persona/analysis/engine.py` that re-exports `dependency_graph` (from `dependency.py`) and `value_queue` (from `value_queue.py`) so consumers import a single stable `engine.` namespace matching FC-4 verbatim. This is a re-export module, not new logic. **Open question O-1** confirms this with the master.

## 2. Frozen contracts (restate verbatim)

**PROVIDES — FC-4 (Lane 3):**
```
engine.dependency_graph(topic) -> {nodes:[{claim_id,statement,load_bearing:float,independent_labs:int,support_ratio:float,provenance,fragile:bool}], edges:[{src,dst,rel_type,confidence,span}]}
engine.value_queue(topic) -> [{question, resolves_claim_id, voi:float, cost_tier:'public_data'|'cheap_assay'|'expensive', dataset_available:bool, de_risks_n:int, run_action:str}]
```

**PROVIDES — FC-6 (Lane 3), new `persona/ingest/retraction.py`:**
```
retraction.is_retracted(doi=None, pmid=None) -> {retracted:bool, date, reason, source}
retraction.contamination(claim_id) -> {contaminated:bool, path:[claim_id]}
```

**CONSUMES — FC-2 (Lane 2), new `persona/inbox.py`:**
```
inbox.file_handoff(kind:str, dossier:dict) -> handoff_id:str
# dossier = {decision_requested, why_unresolvable, disagreeing:[{claim_id,span,qualifiers}], conflict_type:'temporal'|'semantic'|'misinformation'|'insufficient', cheapest_test:{action,cost_tier,dataset}, expected_updates:[{outcome,belief_change}], uncertainty, authority_boundary}
```

**CONSUMES — FC-3 (Lane 2), `persona/memory/kg.py`:**
```
kg.provenance_breakdown() -> {READ:int,INFERRED:int,HUMAN_CONFIRMED:int,TESTED:int, never_confirmed:[claim_id], stale:[{claim_id,age_days}]}
kg.add_dependency_edge(src_claim_id, dst_claim_id, rel_type:'supports'|'contradicts'|'presupposes'|'derives_from'|'generalizes'|'operationalizes'|'qualifies'|'extends', confidence:float, span:str) -> None
kg.dependency_edges(topic=None) -> [{src,dst,rel_type,confidence,span}]
kg.citation_support_ratio(claim_id) -> {support:int,contrast:int,mention:int,ratio:float}
```

## 3. Features

---

### F3.1 — Dependency / load-bearing graph (`analysis/dependency.py`)

**Problem & evidence.** The synthesis pipeline extracts claims but stores no *typed relations between claims*, so nothing knows which beliefs the field actually rests on. The UI's "load-bearing" score is a client-side `degree ÷ support` heuristic, honestly self-labelled unvalidated at `persona/api/static/index.html:2009` (`Connectivity triage · unvalidated heuristic`) and flagged as a gap in `docs/RESEARCH_QUALITY_PROGRAM.md:36`. Research backing: **ClaimFlow** typed inter-claim relation extraction, reported F1 0.80 (arXiv:2603.16073) — the target extractor design; **PageRank** (Page & Brin 1998) for centrality over the `derives_from` sub-graph.

**Design.**
- New `persona/analysis/dependency.py`.
- `extract_edges(topic: str | None = None, *, parent_id=None) -> dict` — a bounded 1-model-call ClaimFlow-style pass. Input: the topic's claims from `kg.claims_about(entities, limit)` (kg.py:329, gives `claim_id, subject, relation, object, sources[].quote`). The model receives claim pairs that share an entity and emits a typed relation **only when an exact source span entails it**; each edge carries the `span`. Output edges are written via `kg.add_dependency_edge(src, dst, rel_type, confidence, span)` (FC-3). `rel_type ∈` the FC-3 enum verbatim. No edge is written without a span (grounding guard identical to `audit.py:216`).
- `load_bearing(edges: list, claims: list) -> dict[claim_id, float]` — pure function, no model. Build the directed `derives_from` (+ `presupposes`, `operationalizes`, `extends`) sub-graph, run PageRank (use `networkx.pagerank` — already an installed dep, see §6 O-2), then `load_bearing = pagerank_mass × 1/(1+independent_labs)` (downstream dependency mass × inverse independent support — a claim many others derive from *and* that few labs independently back is the fragile keystone). Normalize to [0,1].
- `fragile(claim_id)` = `load_bearing high AND independent_labs < 2` — the keystone-on-one-lab flag.
- `dependency_graph(topic) -> {nodes, edges}` (the FC-4 shape) assembles nodes from `kg.claims_about` + `load_bearing` + `citation_support_ratio` (F3.3) + provenance from the claim record.
- Data flow: `kg.claims_about` → `extract_edges` (writes edges to KG) → `kg.dependency_edges(topic)` (read back) → `load_bearing` → `dependency_graph` dict → FC-4 consumer (API lane renders, replacing index.html:2009).

**Epistemic guardrails.** Exact-span grounding: an edge is dropped unless the model returns the entailing `span` (mirrors `audit.py:216`). Provenance typing: node `provenance` copied from the claim (READ/INFERRED/…); an INFERRED edge never gets the visual weight of a READ one — the FC-4 `provenance` field carries it. No-fabricated-confidence: `load_bearing` is a computed graph metric, not a model self-report; it is labelled a *candidate* ranking until RQ-E06 passes and does **not** drive autonomous prioritization before then (Balanced autonomy: auto-*surface*, human-gate any anchor).

**Required experiment.** RQ-E06 (extend existing `experiments/exp_rq_e06_evidence_tree.py`; registry `docs/RESEARCH_QUALITY_PROGRAM.md:184`). Hypothesis: *typed-relation extraction with exact-span gating achieves edge precision ≥ 0.70 against a hand-labelled gold set of ≥ 60 claim pairs, and the resulting `load_bearing` ranking correlates with an expert keystone ranking at Spearman ρ ≥ 0.6* (current baseline ρ 0.38–0.50, must improve before it drives prioritization). Go/no-go gate: edge precision ≥ 0.70 **and** ρ ≥ 0.6 → the score may drive the value queue; else it stays candidate-only. Seeds: 20 (extraction is model-sampled; report mean ± 95% CI over 20 seeds on the fixed gold set). Results → `results/FINDINGS.md#RQ-E06`.

**Acceptance criteria.** (a) `extract_edges` never returns an edge without a non-empty `span`; (b) `load_bearing` is deterministic given fixed edges (no model call); (c) `dependency_graph` returns the exact FC-4 node/edge keys. Runnable check: `pytest persona/tests/test_dependency.py::test_load_bearing_deterministic_and_spanned` (asserts a keystone claim with 5 `derives_from` children and 1 lab outranks a leaf with 3 labs, and that an unspanned edge is refused).

**Effort** M · **Dependencies** FC-3 (`add_dependency_edge`, `dependency_edges`), F3.3 (`citation_support_ratio` consumed for node `support_ratio`).

---

### F3.2 — Value-of-information queue (`analysis/value_queue.py`, FC-4 `engine.value_queue`)

**Problem & evidence.** "What is the highest-leverage experiment?" is a screen the product must answer (§5 CLAUDE.md), but the current ranking is `Candidate review order · unvalidated heuristic` — sign-collision candidates ranked only by graph degree (`index.html:2012`). No VoI, no cost tier, no dataset-availability check. Research backing: value-of-information decision analysis (Howard 1966) — expected value of resolving uncertainty; the cost tier grounds "cheapest discriminating test" in real dataset presence.

**Design.**
- New `persona/analysis/value_queue.py`.
- `value_queue(topic) -> list` (FC-4 shape verbatim). For each contested/under-supported claim from `kg.contradictions()` (kg.py:217) and low-`independent_labs` load-bearing nodes (F3.1):
  - `voi = downstream_dependency_mass(claim) × uncertainty(claim)` where `downstream_dependency_mass` = the `load_bearing` PageRank mass at stake (reuse F3.1) and `uncertainty = 1 − |2·support_ratio − 1|` from `kg.citation_support_ratio` (a claim split 50/50 support/contrast is maximally uncertain).
  - `cost_tier` from dataset-availability: call F3.9 `science.geo_search(topic)` / `science.open_targets(...)` presence → `'public_data'` if a matching GEO/OpenTargets dataset resolves, else `'cheap_assay'` if a registered-but-unrun trial exists (F3.5 signal), else `'expensive'`.
  - `dataset_available` = bool of the above; `run_action` = a concrete string the acting loop can dispatch (e.g. `"geo_lookup:GSE12345"` or `"reanalyze:<slug>"`).
  - `de_risks_n` = count of downstream claims (via `kg.dependency_edges`) that resolving this one de-risks.
  - Rank by `voi / cost_weight` where `cost_weight = {public_data:1, cheap_assay:4, expensive:20}`.
- Data flow: `kg.contradictions` + F3.1 `load_bearing` + `kg.citation_support_ratio` + F3.9 dataset lookups → ranked list → FC-4 consumer (API replaces index.html:2012).

**Epistemic guardrails.** No-fabricated-confidence: `voi` is a formula over measured quantities (dependency mass, support ratio), not a model opinion. `dataset_available` is verified by an actual resolution attempt (F3.9), never asserted. Human-anchors-high-stakes: the queue *proposes* the cheapest test; only a `public_data` tier item is auto-runnable into TESTED-provisional (Balanced autonomy), `cheap_assay`/`expensive` route to the human handoff (FC-2). Applicability: the queue omits a claim if neither uncertainty nor dependency mass is computable (abstain, don't rank noise).

**Required experiment.** RQ-E16 (new). Hypothesis: *VoI/cost ranking correlates with an expert's "what would you fund next" ranking at Spearman ρ ≥ 0.6, beating a citation-count baseline (ρ_baseline) by ≥ 0.15* on a fixed set of ≥ 15 contested claims. Go/no-go gate: ρ ≥ 0.6 AND ρ − ρ_baseline ≥ 0.15 → the queue may auto-dispatch `public_data`-tier reanalyses; else render candidate-only. Seeds: ranking is deterministic given the KG, so vary the KG snapshot / expert-panel bootstrap over 20 resamples for the CI. Script `experiments/exp_rq_e16_value_queue.py`; results `results/FINDINGS.md#RQ-E16`.

**Acceptance criteria.** (a) every returned item has all 8 FC-4 keys; (b) ranking is monotone in `voi` for a fixed `cost_tier`; (c) a claim with a resolvable GEO dataset gets `cost_tier='public_data'` and a non-empty `run_action`. Runnable check: `pytest persona/tests/test_value_queue.py::test_ranking_and_cost_tier`.

**Effort** M · **Dependencies** F3.1, F3.9, FC-3 (`citation_support_ratio`, `dependency_edges`).

---

### F3.3 — Citation-vs-support divergence (`analysis/dependency.py`; FC-3 `kg.citation_support_ratio`)

**Problem & evidence.** A claim can be heavily cited yet never independently tested — the load-bearing-but-hollow keystone. Nothing currently computes the tri-class citation stance on exact spans. Research backing: **scite** Smart Citation tri-classification (support / contrast / mention), *Quantitative Science Studies* (Nicholson et al. 2021).

**Design.**
- Lives in `persona/analysis/dependency.py` (co-located with the graph it flags).
- `support_ratio(claim_id) -> dict` — thin wrapper over `kg.citation_support_ratio(claim_id)` (FC-3, provided by Lane 2) returning `{support, contrast, mention, ratio}`. The exact-span tri-classification of each citing sentence is performed where the citation spans are stored (KG side, Lane 2); this lane *consumes* the ratio and derives the flag.
- `high_cited_never_tested(claim_id, load_bearing_score) -> bool` = `citation total ≥ threshold AND provenance != TESTED AND independent_labs < 2 AND load_bearing_score high` — the "everyone cites it, nobody checked it" flag surfaced on the dependency node and fed to the value queue (high VoI target).
- Data flow: `kg.citation_support_ratio` → node `support_ratio` (F3.1) + `fragile`/`high_cited_never_tested` badge.

**Epistemic guardrails.** Provenance typing is the whole point: the flag fires precisely when `provenance != TESTED` despite high citation. No-fabricated-confidence: the ratio is a count over classified spans; if the KG has no citation spans for the claim, return `ratio=None` and the flag abstains (distinct from `ratio=0`).

**Required experiment.** Trivial — no experiment. The tri-classifier itself is validated on the KG side (Lane 2 / scite-replication); this lane only composes a boolean over returned counts and provenance. (If the composed flag ever gates autonomy, revisit under RQ-E16.)

**Acceptance criteria.** `high_cited_never_tested` returns `False` (not a crash) when `citation_support_ratio` yields `ratio=None`; returns `True` for a claim with support+contrast ≥ threshold, `provenance='READ'`, `independent_labs=1`. Runnable check: `pytest persona/tests/test_dependency.py::test_high_cited_never_tested_abstains_on_none`.

**Effort** S · **Dependencies** FC-3 (`citation_support_ratio`), F3.1.

---

### F3.4 — Trajectory dynamics (`analysis/trajectory.py`)

**Problem & evidence.** The mind stores `belief_history` (confidence + independent-source count over time; `persona/memory/history.py:54 series(claim_id)`), but nothing computes *motion*: is a belief accelerating toward consensus, stalling, or losing independent support? The RQP flags exactly this: the UI shows ingest edges, not temporal history (`docs/RESEARCH_QUALITY_PROGRAM.md:36`). Research backing: standard finite-difference velocity/acceleration on a discrete series; changepoint detection for inflection.

**Design.**
- New `persona/analysis/trajectory.py`, pure functions over `history.series(claim_id)` (returns `[{ts, confidence, independent}]`).
- `trajectory(claim_id) -> dict` = `{velocity, acceleration, independence_drift, inflection: bool, phase: 'rising'|'plateau'|'declining'|'abandoned'}`.
  - `velocity` = Δconfidence / Δt over the recent window; `acceleration` = Δvelocity; `independence_drift` = Δindependent over the window (are *new labs* still joining, or just the same ones re-citing?).
  - `inflection` = sign change in `velocity` beyond a noise floor (finite-difference, no model).
  - `phase='abandoned'` when velocity ≈ 0 AND no new independent source for a long window.
- `topic_trajectory(topic) -> list` maps over the topic's claims for the "where is the argument heading" screen.

**Epistemic guardrails.** **Guardrail (explicit in prompt):** a flat/abandoned curve is a **HYPOTHESIS routed to the value queue (F3.2), never an auto belief-downgrade.** `trajectory` returns a `phase` label and an `inflection` flag; it must not call any belief-mutation path. The consumer (value_queue) turns `phase='abandoned'` on a load-bearing claim into a *question* ("is this still believed? cheapest test = …"), not a confidence edit. No-fabricated-confidence: velocity/acceleration are arithmetic on the stored series.

**Required experiment.** Trivial — no experiment (finite-difference on a stored series is deterministic and standard). The *use* of an abandoned-phase signal to prioritize is covered by RQ-E16's gate. One property test guards the noise-floor threshold.

**Acceptance criteria.** (a) a monotonically rising series yields `velocity>0, phase='rising'`; (b) a series with no change over the window yields `phase in {'plateau','abandoned'}` and never mutates the KG; (c) a series with one sign flip yields `inflection=True`. Runnable check: `pytest persona/tests/test_trajectory.py::test_phases_and_no_mutation` (includes an assert that no `kg.*` write method is called — patched KG spy).

**Effort** S · **Dependencies** `history.series` (existing).

---

### F3.5 — Dark-literature / dead-science meter (`analysis/darklit.py`)

**Problem & evidence.** Registered clinical trials frequently never post results — the field's "dark matter." `science.clinical_trials` (science.py:82) already returns `status/phase` but nobody computes the registered-vs-posted gap or the abandoned-target changepoint. Research backing: **Dead Science Walking** (arXiv:2606.04220) — abandoned-target changepoints; **Cochrane Handbook Ch.13** — ~13% of registered trials post results (the base rate for the gap).

**Design.**
- New `persona/analysis/darklit.py`.
- `results_gap(condition_or_target: str) -> dict` = `{registered:int, with_results:int, gap_ratio:float, base_rate:0.13, worse_than_base:bool, dark_trials:[nct]}`. Data source: extend `science.clinical_trials` (F3.9 adds `hasResults`/`resultsFirstPostDate` to the fields it already requests at science.py:87) and count `status='Completed'` trials lacking posted results.
- `abandoned_target(target: str, series: list) -> dict` = `{changepoint_ts, active: bool, note}` — a changepoint on the trial-registration-over-time series (are new trials still being registered for this target, or did the field walk away?). Reuse the F3.4 changepoint helper (shared finite-difference; no new dependency).
- Feeds F3.2: a high dark-trial gap on a claim's target sets `cost_tier='cheap_assay'` (the evidence exists but is buried) and raises VoI.

**Epistemic guardrails.** Applicability gate: `results_gap` returns `{applicable: False}` when the term resolves to zero registered trials (abstain, don't report `gap_ratio=0/0` as "no problem"). Provenance: the meter is a descriptive count of public registry state, typed READ; it never asserts a trial "failed," only that results are unposted. No-fabricated-confidence: `base_rate=0.13` is cited to Cochrane Ch.13, not invented.

**Required experiment.** Trivial — no experiment (the meter is an arithmetic count over ClinicalTrials.gov fields against a cited base rate). The changepoint helper shares F3.4's tested noise-floor.

**Acceptance criteria.** (a) a condition with 10 completed trials and 1 posting results yields `gap_ratio=0.9, worse_than_base=True`; (b) a term with zero registered trials yields `applicable=False`, not a divide-by-zero. Runnable check: `pytest persona/tests/test_darklit.py::test_gap_and_zero_trials_abstains`.

**Effort** S · **Dependencies** F3.9 (`clinical_trials` field extension).

---

### F3.6 — Retraction-Watch ingestion + descendant-contamination audit (`ingest/retraction.py`, FC-6)

**Problem & evidence.** The auditor guesses retraction from paper metadata only (`audit.py:241` — `meta.get('retracted')`), and the ingest map notes *no Retraction Watch* source. A retracted paper's descendants stay trusted. Research backing: **Sage 2025** — 47.7% of citations to retracted papers occur *after* the retraction; **Retraction Watch / Crossref retraction feed** as the first-class metadata source.

**Design.**
- New `persona/ingest/retraction.py` (FC-6 provider).
- `is_retracted(doi=None, pmid=None) -> {retracted, date, reason, source}` — query the Crossref REST update-to feed (`https://api.crossref.org/works/{doi}` `update-to` with `type='retraction'`) via `service().get_json` (cached + rate-limited, ingest/service.py). Fall back to PubMed's `PublicationType=Retracted Publication` via `science.ncbi_search` when only a PMID is known. Cache aggressively for the demo (CLAUDE.md §4). Returns `{retracted:False, date:None, reason:None, source:'crossref|pubmed|none'}` on a clean lookup (explicit negative, not an error).
- `contamination(claim_id) -> {contaminated, path}` — walk the claim's supporting sources (`kg.provenance(claim_id)` → `sources[].doi`, kg.py:234) and the `dependency_edges` ancestry (FC-3, `derives_from`/`supports`) upward; if any ancestor source is retracted, return the `path:[claim_id,…]` from the contaminated claim to the retracted root. Bounded BFS (depth cap, visited-set) to stay pure and terminating.
- Consumed by F3.7 (auditor retraction pass) and F3.2 (a contaminated claim is a high-VoI verify target).

**Epistemic guardrails.** Fail-loud on contamination: a contaminated belief must be surfaced, never silently trusted (CLAUDE.md §4 "a silent wrong number … is the worst possible bug"). Provenance: retraction status is typed READ from a named `source`; `contamination` returns the exact `path` (auditable, not a bare boolean). Human-anchors-high-stakes: contamination *flags and routes to handoff* (FC-2), it does not auto-delete a belief — a retraction can itself be contested.

**Required experiment.** Trivial — no experiment (lookup + graph walk against ground-truth retraction feeds). One integration test with a known-retracted DOI (e.g. a Wakefield-style fixture) asserts the walk finds the path.

**Acceptance criteria.** (a) `is_retracted` on a known-retracted DOI returns `retracted=True` with a `source`; on a clean DOI returns `retracted=False, source='none'`; (b) `contamination` returns a non-empty `path` when a claim's source is retracted and `contaminated=False` with `path=[]` otherwise; (c) the BFS terminates on a cyclic dependency graph. Runnable check: `pytest persona/tests/test_retraction.py::test_is_retracted_and_contamination_path` (uses a recorded/cached fixture — no live network in CI).

**Effort** M · **Dependencies** FC-3 (`dependency_edges`), `kg.provenance` (existing), `service()` (existing).

---

### F3.7 — Deepen the robustness auditor (`agents/audit.py`)

**Problem & evidence.** `audit()` (audit.py:167) runs two model calls + forensics + a KG crosscheck but, unlike `analyst.py` (which wraps everything in `ResearchSession`, analyst.py:189), it writes a Markdown report with **no append-only event trace, no artifact hashing, no replay verification** — so an audit can't be independently re-verified. It also has no retraction pass (only `meta.get('retracted')`, audit.py:241) and no explicit scoping of reanalysis. Research backing: **REPRO-Bench** (~21.4% automated reproduction success) and **BixBench** (~17%) — the reality that bounds how far an auto-reanalysis can claim "verified"; grounds the default `partial/unverified`.

**Design.**
- Edit `persona/agents/audit.py`.
- **(a) ResearchSession wrapper.** Open `session = ResearchSession(get_persona().paths.runs_dir, f"audit: {title or slug}", model=config.MODEL_WORKER, metadata={"kind":"audit","content_hash":content_hash})` at the top of `audit()`. Record each phase as an event: `session.record("extract", {...})` after r1, `session.record("forensics", {"flags":flags})`, `session.record("adjudicate", {...})` after r2, `session.record("refute", red_team)`. Store the report via `session.store_text("audit.md", report, media_type="text/markdown")` and the structured result via `session.store_json("audit.json", result)`. `session.finalize("completed", title=..., conclusions=[{...}])`. The existing `_write_report` deliverable stays (UI reads it); the session is the *replayable* record. This gives parity with `analyst.py` and makes audits `verify_session`-able (sessions.py:221).
- **(b) Retraction/contamination pass.** After the forensics block (audit.py:216), call `retraction.is_retracted(doi=meta.get('doi'))` (F3.6) → replace the guessed `meta.get('retracted')` at audit.py:241 with the real result; if retracted, cap `likelihood` hard (like the code-proven-flip cap at audit.py:259) and add a claim to `verify_first`. For each central claim mapped to a KG claim_id, call `retraction.contamination(claim_id)` and surface any contaminated path in the report + trust ledger.
- **(c) Narrow-reanalysis scoping.** Any reanalysis the auditor triggers is a **NARROW recomputation** (single statistic re-derivation from the paper's own reported numbers via the existing `forensics` functions), default-labelled `partial/unverified` in the ledger, with a calibration note citing REPRO-Bench 21.4% / BixBench 17%. The auditor must not claim a full replication; a full re-run routes to the human handoff (FC-2) / value queue.

**Epistemic guardrails.** Append-only + artifact-hashed (ResearchSession seals the event log, sessions.py:56) = replay-verifiable audits. No-fabricated-confidence: reanalysis defaults to `partial/unverified` calibrated to the benchmark reality, never "reproduced" without a full run. Papers are untrusted input — the existing prompt-injection guards (audit.py `_EXTRACT_SYS`) are preserved. Human-anchors-high-stakes: a retraction-contaminated or flip-capped verdict routes to handoff, not an auto belief-write.

**Required experiment.** Trivial — no experiment. This is engineering parity (wrap existing calls in an existing, tested session abstraction) + wiring F3.6. The *calibration* of reanalysis confidence is already covered by `experiments/exp_replication_calibration.py` (RQ-CAL, cited at audit.py:226); the `partial/unverified` default is a conservative floor, not a new modeling claim.

**Acceptance criteria.** (a) after an audit, `verify_session(runs_dir, session_id)` returns `ok=True` (event log sealed, artifacts hash-match); (b) a retracted DOI caps `likelihood ≤ 0.20` and adds a verify-first entry; (c) the ledger contains `reanalysis_scope='narrow'` and a `partial/unverified` label. Runnable check: `pytest persona/tests/test_audit_session.py::test_audit_is_replay_verifiable` (runs `audit()` with a stubbed Anthropic client + fixture text, then asserts `verify_session(...).ok`).

**Effort** L · **Dependencies** F3.6 (retraction), `ResearchSession` (existing), `forensics` (existing).

---

### F3.8 — Forensics applicability gates + DEBIT (`analysis/forensics.py`)

**Problem & evidence.** The forensic checks (statcheck/GRIM/GRIMMER/power/p-curve) are exact and unit-tested (`forensics.py`), but they conflate "not applicable" with "skipped," and **DEBIT** (binary mean/SD consistency) is missing. Applying GRIM to a non-integer scale, or a figure check to a vector plot, produces false positives — *the correctness boundary of this whole lane* (out-of-domain application is worse than not running). Research backing: **DEBIT** — descriptive binary test (Heathers & Brown 2019); the forensics front review (PMC12722777) — every check has a precondition (GRIM needs integer scale, N ≲ 200; figure forensics need halftone images).

**Design.**
- Edit `persona/analysis/forensics.py`.
- **Add `debit(mean, sd, n, decimals=2) -> dict`** — for a binary (0/1) variable the mean and SD are analytically linked: `sd = sqrt(mean·(1−mean)·n/(n−1))`. Recompute and flag inconsistency, same return shape as the others (`{check:'debit', status, severity, detail}`).
- **Add an explicit `not_applicable` status distinct from `skipped`.** Today `statcheck`/`grim` return `status='skipped'` for both "no data" and "can't compute." Introduce a helper `_gate(applicable: bool, reason: str)` and have each check return `{"check":X, "status":"not_applicable", "reason":...}` when its **precondition** fails, reserving `skipped` for "input absent." Preconditions:
  - `grim` / `grimmer`: integer response scale AND `n ≤ ~200` (above which GRIM loses discriminating power) AND `decimals ≤ 3` — else `not_applicable`.
  - `debit`: variable declared/inferred binary — else `not_applicable`.
  - `min_detectable_effect`: two-group design — else `not_applicable`.
  - `p_curve`: ≥ 3 significant independent p-values from *different* tests — else current `skipped` (input-insufficient) is correct.
- Update `run_all` (forensics.py:155) to (i) call `debit` for descriptives flagged binary, and (ii) pass through `not_applicable` results so the auditor can *show* "checked, N/A" distinctly from "passed" and "skipped." The auditor's counting (`audit.py:217-219`) treats `not_applicable` as neither pass nor fail (a third bucket) — but that is an `audit.py` edit under F3.7's ledger, kept minimal here.

**Epistemic guardrails.** This *is* the applicability-gate discipline: a check that runs out of its precondition emits `not_applicable`, never a false `inconsistent`. Every gate declares its precondition in `reason`. No-fabricated-confidence: DEBIT is exact arithmetic (same posture as GRIM/statcheck — "the arithmetic is deterministic, unit-tested, and impossible to argue with," forensics.py:4).

**Required experiment.** RQ-E17 (new, small). Hypothesis: *adding preconditioned `not_applicable` gates reduces the forensic false-positive rate (flags on data that violate the check's precondition) to 0 on a held-out set of ≥ 30 out-of-domain descriptives (non-integer scales, continuous variables, large N), with no loss of true-positive detection on the existing in-domain GRIM/DEBIT positive fixtures.* Go/no-go gate: FP rate = 0 on the out-of-domain set AND TP rate unchanged on in-domain → ship. Deterministic (no seeds needed; the checks are exact) — report exact counts. Script `experiments/exp_rq_e17_forensics_gates.py`; results `results/FINDINGS.md#RQ-E17`.

**Acceptance criteria.** (a) `debit` flags a binary mean/SD mismatch and passes a consistent one; (b) `grim` on a 1–7 *continuous* mean with N=5000 returns `status='not_applicable'` (not `inconsistent`, not `ok`); (c) `run_all` output distinguishes `ok` / `inconsistent` / `not_applicable` / `skipped`. Runnable check: extend `forensics.py`'s existing self-test posture — `pytest persona/tests/test_forensics_gates.py::test_debit_and_not_applicable_distinct` (mirrors the `experiments/exp_when_protection_matters.py` oracle-reuse pattern: real fixtures, not mocks).

**Effort** M · **Dependencies** none (self-contained in forensics.py; the `audit.py` counting tweak is folded into F3.7).

---

### F3.9 — GEO dataset resolution + dataset search (`tools/science.py`, `tools/datasets.py`)

**Problem & evidence.** `ncbi_search` stops at esearch IDs (science.py:110 returns bare `ids`) — no esummary, no SOFT/matrix URL — so "located public dataset → first-pass reanalysis" (the acting loop) can't actually resolve a dataset to disk. `datasets.fetch` already allowlists `ftp.ncbi.nlm.nih.gov` (datasets.py:16), so the missing piece is *resolution*, not egress. No dataset *search* exists. Research backing: NCBI GEO SOFT/series-matrix format + E-utilities esummary (db=gds); OpenML dataset API (already allowlisted, datasets.py:19).

**Design.**
- Edit `persona/tools/science.py`.
- **`geo_lookup(gid: str, dest_dir=None) -> dict`** — `esearch(db='gds', term=gid)` → `esummary(db='gds', id=uid)` to get the accession + FTP path → construct the SOFT/series-matrix URL under `ftp.ncbi.nlm.nih.gov/geo/series/<GSExxxnnn>/<GSEfull>/matrix/…` → if `dest_dir` given, route through `datasets.fetch(url, dest_dir)` (datasets.py:29, already size-capped + allowlisted). Returns `{ok, accession, title, n_samples, platform, ftp_url, path?}`. This closes the acting loop end-to-end.
- **`geo_search(query, size=8) -> dict`** — `esearch(db='gds')` + `esummary` → a list of `{accession, title, n_samples, summary}` for discovery (feeds F3.2 `dataset_available`).
- **`openml_search(query, size=8) -> dict`** — hit `https://api.openml.org/api/v1/json/data/list/...` (allowlisted) for tabular-dataset discovery in non-omics fields.
- **Extend `clinical_trials`** (science.py:87 `fields`) to request `HasResults`/`ResultsFirstPostDate` for F3.5.
- Register `geo_lookup`, `geo_search`, `openml_search` in `REGISTRY` (science.py:137) and add dispatch cases in `call` (science.py:147) so the analyst tool-loop can invoke them.
- No change to `datasets.py` signatures — `fetch` already does the guarded download; we only *call* it with GEO URLs.

**Epistemic guardrails.** Egress boundary preserved: all fetching goes through `datasets.fetch`'s allowlist (datasets.py:24) — no new hosts, sandbox stays `--network none`. Fail-loud: `geo_lookup` returns `{ok:False, error}` on an unresolvable ID (no silent empty dataset). Provenance: a resolved dataset's accession + FTP URL is recorded so any reanalysis on it is reproducible (CLAUDE.md §4).

**Required experiment.** Trivial — no experiment. This is deterministic API plumbing against documented NCBI/OpenML endpoints. Correctness is verified by an integration test hitting a known small GEO series (cached fixture in CI). (Per CLAUDE.md §1, the *actual* esummary/SOFT URL shape is verified against a live call in a scratch script before wiring — the "never assume a library/endpoint" rule — but that's a build-time check, not a seeded experiment.)

**Acceptance criteria.** (a) `geo_lookup('GSE...')` resolves an accession + a `ftp.ncbi.nlm.nih.gov` URL that passes `datasets.allowed()`; (b) with `dest_dir`, the SOFT/matrix file lands on disk under the size cap; (c) `geo_search` returns ≥ 1 result for a common term. Runnable check: `pytest persona/tests/test_science_geo.py::test_geo_lookup_resolves_allowlisted_url` (asserts `datasets.allowed(result['ftp_url'])` — no live fetch needed for the URL-shape assertion).

**Effort** M · **Dependencies** `datasets.fetch` (existing), F3.2 & F3.5 consume it.

---

### F3.10 — Field-scoped fallback sources (`ingest/sources.py`)

**Problem & evidence.** `search_multi` threads `field_ids` only into OpenAlex (sources.py:168 — the ternary passes `field_ids` to `openalex_search` alone); on failover to Crossref/Europe PMC/arXiv the RQ-E15 field discipline is *silently dropped* (`results/FINDINGS.md#RQ-E15` — the source-level field gate that keeps the persona on its declared fields, SHIP/precision-biased). A 429 on OpenAlex currently means off-field papers leak in. Research backing: RQ-E15 (this repo) — the field gate is decisive for staying on-topic.

**Design.**
- Edit `persona/ingest/sources.py`.
- Add an optional `field_ids=None` param to `crossref_search`, `europepmc_search`, `arxiv_search` (sources.py:80,105,135). These APIs lack OpenAlex's native `primary_topic.field.id` filter, so apply a **post-fetch field filter**: a small allowlist of subject terms per OpenAlex field id (a static map, computed once), and drop works whose venue/subject clearly falls outside — OR, more conservatively (precision-biased like E15), tag each returned `Work` with `field_id=None` and let the membrane's existing field gate reject off-field works downstream. Prefer the latter (reuse the existing gate) unless the map proves necessary — **ponytail: do the smallest thing (pass field_ids through, tag Works, let the existing membrane gate filter) before building a per-source subject map.**
- Update `search_multi` (sources.py:166) to pass `field_ids` to *every* source, not just OpenAlex: `works = fn(query, limit, field_ids=field_ids)` uniformly (add the kwarg to all four signatures).
- Log which source + whether the field constraint was natively enforced vs downstream-filtered (extend the existing `log(...)` at sources.py:175).

**Epistemic guardrails.** RQ-E15 field discipline preserved across failover — the whole point. Precision-biased: when a fallback source can't enforce the field natively, defer to the existing membrane gate rather than admit-then-hope. No silent drop of the constraint (the current bug).

**Required experiment.** Reuse RQ-E15 (`experiments/exp_rq_e15_field_question_gate.py`). Hypothesis: *with field_ids threaded through all sources, a forced OpenAlex-failover run keeps off-field admission at the same rate as the OpenAlex-primary run (no regression) — off-field leak ≤ the E15 SHIP threshold.* Go/no-go: off-field rate on failover ≤ off-field rate on primary + 2pp → ship. Seeds: 20 queries × the existing E15 harness. Results appended to `results/FINDINGS.md#RQ-E15`.

**Acceptance criteria.** (a) all four source fns accept `field_ids`; (b) `search_multi` passes it to each; (c) a failover run tags off-field Works for the gate. Runnable check: `pytest persona/tests/test_sources_field.py::test_field_ids_threaded_to_all_sources` (introspects each fn signature + asserts `search_multi` forwards it — no network).

**Effort** S · **Dependencies** membrane field gate (existing, RQ-E15).

---

### F3.11 — Fieldmap contradiction → human handoff + note-version diffing (`synthesis/fieldmap.py`, `synthesis/synthesizer.py`)

**Problem & evidence.** The synthesis map's own gap: *contradictions are surfaced but not escalated* (`fieldmap.py:38-41` computes `contradictions` per subtopic and stops), and *notes are regenerated not diffed* (`synthesizer.py:171` overwrites `notes/<slug>.md`, destroying the "how understanding evolved" chronology). The build already has an "idea-over-time" section (commit 7d25d32) but at year granularity, not note-revision granularity. Research backing: candidate_conflict ≠ verified contradiction (RQ-E02, not yet passed) — so escalation is human-gated, not auto-resolved.

**Design.**
- Edit `persona/synthesis/fieldmap.py`.
- In `build` (fieldmap.py:25), after assembling each subtopic's `contradictions` (fieldmap.py:38), for any contradiction where **both sides have ≥ 2 independent labs** (`cc['pos'] >= 2 and cc['neg'] >= 2`), file a handoff via **FC-2**: `inbox.file_handoff("contradiction", dossier)` where the dossier is built to the FC-2 schema:
  - `conflict_type` = classified `'temporal'|'semantic'|'misinformation'|'insufficient'` (heuristic: overlapping years → semantic; disjoint years → temporal; low-independence attacker → misinformation; else insufficient).
  - `disagreeing` = `[{claim_id: pos_claim, span, qualifiers}, {claim_id: neg_claim, span, qualifiers}]` (spans pulled from `kg.provenance` of each claim).
  - `cheapest_test` = the top F3.2 `value_queue` item resolving either claim; `expected_updates` = the two outcomes; `authority_boundary` = "wet-lab / expert judgment required" per the human-as-resolver design.
  - Guard: file at most once per (pos_claim,neg_claim) pair (dedup key) to avoid inbox spam on every rebuild.
- Edit `persona/synthesis/synthesizer.py`.
- Before overwriting the note (synthesizer.py:171), if `notes/<slug>.md` exists, append the *prior* version's body + timestamp to a sidecar `notes/.history/<slug>.jsonl` (append-only), then write the new note. Add `note_diff(slug) -> [{ts, added:[...], removed:[...]}]` computing a line/paragraph-level diff across versions (stdlib `difflib`) — the note-granularity "how understanding evolved" chronology. **ponytail: sidecar jsonl + `difflib`, no versioning framework.**

**Epistemic guardrails.** RQ-E02 discipline: a ≥2-lab-vs-≥2-lab contradiction is a *candidate* that routes to a human (FC-2 handoff), never an auto-resolution — human-anchors-high-stakes. Exact-span grounding: the dossier's `disagreeing[].span` comes from `kg.provenance`, not paraphrase. Append-only provenance: the note-history sidecar never mutates prior versions (CLAUDE.md §4 reproducibility).

**Required experiment.** Trivial — no experiment. Escalation is a wiring + schema-mapping task; the *decision* to escalate (≥2 labs both sides) is a conservative, human-gated threshold, not a modeling claim. `difflib` diffing is deterministic.

**Acceptance criteria.** (a) a subtopic with a 2-lab-vs-2-lab contradiction produces exactly one `inbox.file_handoff` call with a schema-valid dossier; a 2-vs-1 contradiction produces none; (b) re-running `build` does not re-file the same pair; (c) re-synthesizing a note appends a prior-version record and `note_diff` returns the change set. Runnable check: `pytest persona/tests/test_fieldmap_handoff.py::test_escalates_only_dual_independent` (patches `inbox.file_handoff` with a spy) and `test_synthesizer_notediff.py::test_note_history_appends`.

**Effort** M · **Dependencies** FC-2 (`inbox.file_handoff`), F3.2 (`value_queue` for `cheapest_test`), `kg.provenance` (existing).

---

## 4. Sequencing within the lane

**Milestone 0 (hour 1 — land all provided FC stubs so other lanes build against them):**
1. `persona/ingest/retraction.py` — FC-6 stubs: `is_retracted(...)` returns `{retracted:False,date:None,reason:None,source:'none'}`; `contamination(...)` returns `{contaminated:False,path:[]}`.
2. `persona/analysis/engine.py` — FC-4 stubs: `dependency_graph(topic)` returns `{nodes:[],edges:[]}`; `value_queue(topic)` returns `[]`. (Re-exports from `dependency.py`/`value_queue.py` once those exist.)
3. Empty-but-importable `dependency.py`, `value_queue.py`, `trajectory.py`, `darklit.py` with typed signatures returning empty results.

**Then, feature order (rationale):**
- **F3.8 (forensics gates + DEBIT)** first — self-contained, no cross-lane deps, and it hardens the correctness boundary (applicability gates) that everything downstream trusts.
- **F3.9 (GEO resolution)** next — unblocks the acting loop and F3.2's `dataset_available`; no dep on Lane 2.
- **F3.6 (retraction)** — needed by F3.7; depends only on existing `service`/`kg.provenance` + FC-3 edges (stub-safe).
- **F3.1 (dependency graph)** — the spine; needs FC-3 `add_dependency_edge`/`dependency_edges` (coordinate with Lane 2's stub landing).
- **F3.3 (citation-vs-support)** — thin, once F3.1 nodes exist and FC-3 `citation_support_ratio` lands.
- **F3.4 (trajectory)** + **F3.5 (darklit)** — independent, small, feed F3.2.
- **F3.2 (value queue)** — depends on F3.1/F3.3/F3.4/F3.5/F3.9; the payoff aggregator.
- **F3.7 (auditor deepening)** — depends on F3.6; largest single edit, done once retraction is real.
- **F3.10 (field failover)** + **F3.11 (handoff + note-diff)** — F3.11 depends on FC-2 (Lane 2) + F3.2; do last once the value queue exists to populate `cheapest_test`.

## 5. Test & verification plan

**Unit (pure functions, no network/model):**
- `test_dependency.py` — `load_bearing` determinism + span-refusal; `high_cited_never_tested` abstains on `ratio=None`.
- `test_trajectory.py` — phase labels + **no-KG-mutation** (spy asserts zero writes).
- `test_forensics_gates.py` — DEBIT correctness + `not_applicable ≠ skipped ≠ ok` (reuses the real-fixtures posture of `experiments/exp_when_protection_matters.py`, per BUILD_PLAN §10.1 / CLAUDE.md §4 — real behavior, not mocks).
- `test_value_queue.py` — 8-key shape, monotone-in-VoI, cost-tier from dataset presence.
- `test_darklit.py` — gap ratio + zero-trial abstain.

**Integration (cached fixtures, no live network in CI):**
- `test_retraction.py` — known-retracted DOI → `retracted=True`; contamination path found; BFS terminates on a cycle.
- `test_science_geo.py` — `geo_lookup` yields an allowlisted FTP URL (`datasets.allowed(url)` true).
- `test_audit_session.py` — run `audit()` with a stubbed Anthropic client + fixture paper → `verify_session(runs_dir, id).ok` is True (append-only, artifact-hashed, replay-verifiable — the F3.7 headline).
- `test_sources_field.py` — `field_ids` threaded to all four sources + forwarded by `search_multi`.
- `test_fieldmap_handoff.py` / `test_synthesizer_notediff.py` — escalate only dual-independent; note-history appends.

**Experiment oracles (seeded, ≥20 where model-sampled):**
- RQ-E06 (extend `exp_rq_e06_evidence_tree.py`) — edge precision ≥ 0.70 + load-bearing Spearman ρ ≥ 0.6 gate.
- RQ-E16 (`exp_rq_e16_value_queue.py`) — VoI ranking vs expert vs citation baseline.
- RQ-E17 (`exp_rq_e17_forensics_gates.py`) — false-positive rate = 0 on out-of-domain descriptives.
- RQ-E15 (reuse `exp_rq_e15_field_question_gate.py`) — no off-field regression on failover.

**Browser smoke (API lane owns the render; this lane provides the data):** after F3.1/F3.2 land, the API lane replaces `index.html:2009` (Connectivity triage) and `index.html:2012` (Candidate review order) with the FC-4 `engine.dependency_graph` / `engine.value_queue` payloads; a smoke check confirms the dependency graph and value queue render with the *validated* (not "unvalidated heuristic") label only once RQ-E06/RQ-E16 gates pass.

## 6. Open questions for the master/user

- **O-1 (FC-4 namespace).** FC-4 names `engine.dependency_graph` / `engine.value_queue`, but the file list names `analysis/dependency.py` / `analysis/value_queue.py`. I propose a thin `persona/analysis/engine.py` that re-exports both under the `engine.` namespace (matching FC-4 verbatim). Confirm this is the intended `engine` module, or point me at an existing one. **This is the only decision that could affect how consumers (API/Lane 4) import FC-4** — needs an early ack.
- **O-2 (PageRank dependency).** `load_bearing` wants PageRank over `derives_from`. Is `networkx` an installed dependency (the CLAUDE.md graph lists a `networkx` skill; need to confirm it's in this project's env), or should I implement power-iteration PageRank inline (~15 lines, no new dep — ponytail-preferred)? Defaulting to inline unless networkx is already vendored.
- **O-3 (citation spans live where?).** FC-3 `citation_support_ratio` is Lane 2's. For F3.3's "high-cited never-tested" flag I assume Lane 2's tri-classifier stores the exact citing spans and I only consume counts. Confirm the exact-span tri-classification is on the KG side (Lane 2), not expected in this lane.
- **O-4 (autonomy of `public_data`-tier reanalysis).** Balanced autonomy says auto-run NARROW reanalyses into TESTED-provisional. F3.2 would auto-dispatch a `public_data`-tier `run_action` (e.g. `geo_lookup` + a bounded recompute) *only after* RQ-E16 passes. Confirm the master wants auto-dispatch gated on RQ-E16, vs. always human-confirmed even for public data.
