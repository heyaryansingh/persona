# PRD-08 — Molecular prior gates (gnomAD constraint · GTEx expression · OT Genetics L2G)

> Owner: implementer lane 2 · Status: DRAFT-for-implementation · Autonomy: Balanced · Depends on: PRD-02 F2.1 (`membrane.admit_candidate`) / F2.4 (`membrane._feasibility_flags`) as the consuming seam; FC-2 (`inbox.file_handoff`, own lane) for routing; shared `ops_dir/gate_decisions.jsonl` ledger. No dependency on FC-4/FC-5/FC-6/FC-7. Reuses `ingest.service.service()` (existing HTTP core) and the existing `open_targets` GraphQL plumbing in `tools/science.py`.

## 0. Summary + how it advances the vision

The membrane today decides what to believe from **text about biology** — sign-collisions across independent labs (`kg.beliefs`, kg.py:204) and (post-PRD-02) an entailment span plus a structural KG cross-check (`membrane.admit_candidate`). It has **no channel to structured population biology**: whether the human population *actually tolerates* knocking out the gene, whether the gene is even *expressed* in the tissue the claim is about, or whether *human genetics* (not just literature co-mention) supports the gene→disease link. So a confidently-written, well-cited, textually-entailed claim like "loss-of-function of GENE-X causes severe disease Y" can be admitted even when 807k healthy exomes carry LoF variants in GENE-X with no phenotype — the single strongest disconfirming signal in human genetics, and one no amount of reading the abstract will surface. This PRD adds three orthogonal, **code-run molecular priors** that feed the membrane's feasibility / knowledge-conflict gating: (a) **gnomAD v4 LOEUF/pLI** constraint — a LoF-causes-severe-disease claim on a LoF-*tolerant* gene gets population-genetics counter-evidence; (b) **GTEx median TPM per tissue** — a mechanistic claim about a gene in a tissue where it is effectively unexpressed raises an implausibility flag; (c) **Open Targets genetic-evidence score** (L2G / genetic_association datatype, distinct from the literature datatype) — high literature co-mention with ~zero human-genetics support becomes an "association-heavy" flag. Each prior is **applicability-gated** (emits an explicit `not_applicable` distinct from "passed"), typed **INFERRED** (a prior, not a `TESTED` result), and **only ever down-weights or flags — never a hard verdict, never raising confidence**. The new capability nothing else in the stack has: *the belief-store's admission decision is now cross-checked against orthogonal molecular ground-truth (constraint, expression, human genetics), not just against more text* — Persona can catch an over-reaching molecular claim that is perfectly grounded in the literature yet contradicted by the human population itself. Per the epistemic contract, the down-weighting is **gated behind an experiment (RQ-M08)** that proves the priors raise membrane precision *without over-rejecting correctly-specific claims*; until that gate passes the priors render **advisory flags only**.

---

## 1. File ownership (disjoint set)

**New (owned by this lane — Lane 2):**
- `persona/memory/priors.py` — the three prior clients, gene resolution, applicability gates, the flag orchestrator, and the membrane down-weight helper. **All new capability lives here.**

**Edited (owned by Lane 2 per PRD-00 §3 map):**
- `persona/memory/membrane.py` — one call site: `admit_candidate` (PRD-02 F2.1) invokes `priors.molecular_prior_flags(...)` and, post-gate, `priors.apply_priors(...)`; `_feasibility_flags` (PRD-02 F2.4) surfaces prior flags alongside its structural flags. Additive; no signature change to existing functions.

**Boundary files another lane owns (decoupled — no edit here):**
- `persona/tools/science.py` — **Lane 3 owns** (PRD-00 §3; Lane 3 edits it for `geo_lookup`/`openml_search`, PRD-03 F3.9). This lane does **not** edit it. The prior clients call `ingest.service.service()` **directly** (same pattern `science.open_targets` uses, science.py:21), so the core capability needs no Lane-3 file. Exposing the three priors in `science.REGISTRY` for the analyst tool-loop is an **optional additive CONTRACT CHANGE PROPOSAL** (§2) — the membrane path works fully without it.
- `persona/ingest/service.py` — shared HTTP core, not in any lane's edit-set. This lane **calls** `service().post_json` / `get_json` (read-only use). The two new hosts (`gnomad.broadinstitute.org`, `gtexportal.org`) are covered by the `_default` rate limit `(0.5, 2)` (service.py:70) with **no edit required**; tuning `_LIMITS` is advisory-only (§6 O-3).
- `persona/memory/kg.py` — **Lane 2 owns but PRD-02 edits it.** This PRD reads `claim_rec` (already in hand inside `admit_candidate`) and does **not** add a KG schema field — priors are recomputed-on-render from the HTTP cache (§3 F8.0), so no `kg.add_claim` change and no collision with PRD-02's kg.py edits.

---

## 2. Frozen contracts provided / consumed

**Provides:** *no new cross-lane FC.* The priors are consumed only inside Lane 2's own membrane, and surfaced to Lane 4's trust-ledger render through data already on the claim record + the FC-2 dossier + the shared `gate_decisions.jsonl` ledger (PRD-00 §4). New **intra-lane** public signatures (listed for FC coherence / so PRD-02's `admit_candidate` author can call them verbatim):

```
# persona/memory/priors.py
resolve_gene(entity_name: str) -> dict
    # -> {ok: bool, symbol: str|None, ensembl_id: str|None, reason: str}
gnomad_constraint(gene_symbol: str) -> dict
    # -> {applicable: bool, pLI: float|None, loeuf: float|None, oe_lof: float|None,
    #     source: 'gnomad_r4', reason: str}
gtex_expression(gene_symbol: str, tissue: str|None = None) -> dict
    # -> {applicable: bool, median_tpm: float|None, tissue: str|None,
    #     tissues: [{tissue: str, tpm: float}], source: 'gtex_v10', reason: str}
ot_genetic_support(ensembl_id: str, disease_term: str) -> dict
    # -> {applicable: bool, genetic_score: float|None, literature_score: float|None,
    #     has_genetic_support: bool, source: 'opentargets', reason: str}
molecular_prior_flags(kg, claim_rec: dict, *, tissue: str|None = None) -> dict
    # -> {status: 'evaluated'|'not_applicable', provenance: 'INFERRED',
    #     gene: {symbol, ensembl_id}|None,
    #     flags: [{prior: 'gnomad'|'gtex'|'ot_genetics', kind: str, severity: 'info'|'warn',
    #              down_weight: float, detail: str, source: str, evidence: dict}],
    #     priors: {gnomad: dict, gtex: dict, ot_genetics: dict}}
apply_priors(candidate: dict, prior_result: dict) -> dict
    # -> candidate with candidate['calibrated_p'] optionally lowered (never raised) and
    #    candidate['molecular_priors'] = prior_result attached. Down-weight applied ONLY when
    #    the RQ-M08 gate has passed (ops_dir/molecular_priors_gate.json present & passed=True);
    #    otherwise advisory-only (flags attached, calibrated_p untouched).
```

**Consumes (existing / same-lane, verbatim):**
- PRD-02 **F2.1** `membrane.admit_candidate(kg, claim_rec, source_slug, entail) -> {admit, route, calibrated_p, ...}` — the seam the priors plug into (same lane, so no FC needed; coordinate ordering in the HANDOFF).
- **FC-2** `inbox.file_handoff(kind:str, dossier:dict) -> handoff_id:str` (own lane) — a high-severity prior contradiction on an anchored/high-stakes claim routes here, never auto-mutates.
- Shared **`ops_dir/gate_decisions.jsonl`** (PRD-00 §4) — a membrane-gate row records the prior decision/reason (append-only).
- Existing infra: `ingest.service.service().post_json/get_json` (service.py:167,179), `tools.science.open_targets` GraphQL endpoint constant reuse (science.py:21).

**CONTRACT CHANGE PROPOSAL (optional, additive, non-blocking) — CCP-08a:** register three read-only entries in `science.REGISTRY` (science.py:137) + dispatch cases in `science.call` (science.py:147) — `"gnomad_constraint"`, `"gtex_expression"`, `"ot_genetic_support"` — so the analyst tool-loop can pull a molecular prior on demand during an investigation. This is a Lane-3 file edit; **the membrane capability does not depend on it.** Flagged for the master to route to Lane 3; if declined, priors remain membrane-internal.

---

## 3. Features

### F8.0 — Prior substrate: gene resolution, applicability gate, membrane seam, RQ gate

**Problem & evidence.** The membrane's admission decision (`kg.beliefs` counting, kg.py:204; PRD-02 `admit_candidate`) sees only text-derived signals. Claims arrive as a canonicalized `(subject, object, effect_sign)` triple with a `relation` verb and source quotes (`kg.add_claim`, kg.py:89-105; `claim_rec` keys: `subject, object, effect_sign, relation, quote`). To attach a molecular prior we must (a) decide whether the claim is even *about a gene* (most are not — applying a gene prior to a drug–symptom claim is exactly the out-of-domain false positive the contract forbids, PRD-00 §2), and (b) resolve the entity string to a gene symbol + Ensembl id for the three databases. There is no gene-resolution or applicability layer today.

**Design.**
- New `persona/memory/priors.py`.
- `resolve_gene(entity_name)` — canonicalize (reuse the claim's already-canon `subject`/`object`; no re-canon needed inside the membrane) then resolve via **gnomAD's own gene lookup**: a `gene(gene_symbol: $s, reference_genome: GRCh38){ gene_id gene_symbol }` GraphQL call to `https://gnomad.broadinstitute.org/api` (verified endpoint + schema, gnomad skill §1/§4). A non-null `gene_id` (Ensembl `ENSG…`) ⇒ `{ok:True, symbol, ensembl_id}`; a null gene ⇒ `{ok:False, reason:'not-a-recognized-gene-symbol'}`. This is the **single resolution point** (one cached call feeds all three priors) and the primary applicability gate: *not a gene ⇒ every prior is `not_applicable`.* Guard the input with a cheap symbol-shape prefilter (`^[A-Z0-9orf-]{2,12}$` after stripping obvious suffixes like " mutation"/" knockout") so free-text objects don't spend a network call.
- `molecular_prior_flags(kg, claim_rec, *, tissue=None)` — the orchestrator. Resolves the gene from whichever of `subject`/`object` is the gene (try both; a gene→disease claim has the gene as subject, a disease→gene as object). If unresolved ⇒ `{status:'not_applicable', flags:[], ...}`. Else runs the three priors (F8.1–F8.3), each self-gating, and collects their flags. `provenance` is hard-set `'INFERRED'`.
- `apply_priors(candidate, prior_result)` — the membrane down-weight helper. **Gate-guarded:** reads `ops_dir/molecular_priors_gate.json` (mirrors the `calibrator.json` load pattern, PRD-02 F2.3); if absent or `passed=False`, it only attaches `candidate['molecular_priors']=prior_result` (advisory) and returns `candidate` unchanged. If `passed=True`, it multiplies `candidate['calibrated_p']` by `min(1.0, Π down_weight)` **clamped to a floor** `MOL_PRIOR_FLOOR=0.5` (a prior can halve confidence at most — it nudges, never vetoes) and can **only lower, never raise** (`new_p = min(old_p, old_p*factor)`). Records a `gate_decisions.jsonl` row `{gate:'membrane', decision, reason:'molecular_prior:<kinds>', score:factor, ...}`.
- **Membrane seam (`membrane.py`, additive):** inside `admit_candidate` (PRD-02 F2.1), after computing the dual signals and before/around `calibrate.admit_decision`, call `pr = priors.molecular_prior_flags(kg, claim_rec)` and `candidate = priors.apply_priors(candidate, pr)`. A `severity:'warn'` flag on an **anchored/high-stakes** claim ⇒ `inbox.file_handoff("molecular_prior_contradiction", dossier)` (never auto-mutates the anchor — Balanced posture, PRD-00 §1). Non-anchored ⇒ the (gated) down-weight + a flag surfaced to the trust ledger.
- **Trust-ledger surfacing (no new persistence):** priors are cheap to recompute (all fetches cache-hit via `IngestService`, service.py:74-98), so Lane 4's trust-ledger render calls `molecular_prior_flags(kg, claim_rec)` live rather than reading a stored field — this avoids a `kg.py` schema edit that would collide with PRD-02. `# ponytail: recompute-on-render backed by the HTTP cache; no sidecar, no KG column.`

**Epistemic guardrails.** Applicability gate is explicit and first-class: non-gene claim ⇒ `not_applicable` (distinct from "no flag / passed"). Priors typed `INFERRED`, never `READ`/`TESTED`. Down-weight is **gated behind RQ-M08** and clamped (floor 0.5, monotone-down only) — a prior can never fabricate confidence, never hard-reject, never raise `calibrated_p`. High-stakes/anchored contradiction routes to human, never auto-updates.

**Required experiment.** **RQ-M08** (load-bearing — the gate that lets priors down-weight autonomously; register in `docs/RESEARCH_QUALITY_PROGRAM.md`). **Hypothesis:** applying molecular-prior down-weighting improves the membrane's admitted-set precision on a labeled gene-centric claim set **without over-rejecting correctly-specific true claims** (bounded false-flag rate), vs. the PRD-02 dual-signal membrane alone. **Metric:** (i) admitted-set precision Δ (agreement with the gold labels) with priors on vs. off; (ii) **false-flag rate** = fraction of correctly-specific, true, gene-centric control claims that receive a `warn` flag. **Gate:** precision improves ≥ **+0.05 absolute** AND false-flag rate ≤ **0.05** on the control set → flip `molecular_priors_gate.json` `passed=True` (down-weight goes live); else priors stay advisory-only and the reversal is logged. **Seeds:** ≥20 resample splits over the labeled set (reuse the RQ-E01a / RQ-M01 resampling harness style, PRD-02 §5). **Labeled set:** the frozen Curie candidate set restricted to gene-centric claims (true controls) + seeded over-reaching positives — one per prior: a LoF-causes-disease claim on a known LoF-tolerant gene (LOEUF>0.6), a mechanistic claim placing a gene in a tissue where GTEx median TPM<1, and a high-comention gene–disease pair with OT `genetic_association`≈0. Save `experiments/exp_molecular_priors.py`, results `results/FINDINGS.md#RQ-M08`.

**Acceptance criteria.** A non-gene claim ⇒ `molecular_prior_flags(...).status == 'not_applicable'` and `apply_priors` leaves `calibrated_p` unchanged. With the gate unset, a flagged gene claim keeps its `calibrated_p` (advisory) but carries the flag. **Runnable check:** `pytest persona/tests/test_priors.py::test_non_gene_not_applicable_and_gate_off_is_advisory`.

**Effort** M · **Dependencies** PRD-02 F2.1 (seam), FC-2 (routing).

---

### F8.1 — gnomAD v4 LOEUF/pLI constraint prior

**Problem & evidence.** The strongest population-genetics disconfirmation of a "loss-of-function of GENE causes severe disease" claim is that healthy people already carry LoF variants in that gene. gnomAD v4 (730,947 exomes) publishes exactly this as **LOEUF** (`oe_lof_upper`) and **pLI** per gene (gnomad skill §4). Nothing in Persona consults it: a textually-entailed LoF→severe-disease claim on a LoF-tolerant gene is admitted with no counter-signal. Research/source: Karczewski et al. 2020 (gnomAD constraint; LOEUF as the recommended intolerance metric); gnomAD v4 GraphQL `gnomad_constraint{ pLI oe_lof oe_lof_upper }` (verified schema, gnomad skill §4). Convention: **LOEUF < 0.35 = constrained/intolerant; LOEUF > 0.6 = LoF-tolerant** (brief), pLI > 0.9 = intolerant.

**Design.**
- `gnomad_constraint(gene_symbol)` in `priors.py` — POST the `GeneConstraint` GraphQL query (gnomad skill §4, verbatim shape) via `service().post_json("https://gnomad.broadinstitute.org/api", {"query":..., "variables":{"gene_symbol":..., "reference_genome":"GRCh38"}}, retries=1, timeout=12)`. Extract `pLI`, `loeuf = oe_lof_upper`, `oe_lof`. **Applicability gate:** `gnomad_constraint` null (gene has no constraint record — common for short/non-coding) ⇒ `{applicable:False, reason:'no-constraint-record'}`.
- Flag rule (inside `molecular_prior_flags`): fire **only** when the claim is a *LoF-causes-disease* claim — detected structurally: the gene is the subject, the object is a disease/phenotype, `effect_sign` is deleterious (`-` "loss"/"deficiency" semantics or the relation/quote contains a LoF cue: "loss-of-function", "knockout", "haploinsufficien", "null", "truncating", "LoF") — AND `loeuf > 0.6` (LoF-tolerant). Then emit `{prior:'gnomad', kind:'lof_tolerant_counterevidence', severity:'warn', down_weight:0.7, detail:f"LOEUF={loeuf:.2f} (>0.6 → LoF-tolerant across 807k healthy exomes); LoF-causes-severe-disease claim is population-genetics-implausible", source:'gnomad_r4', evidence:{loeuf, pLI, oe_lof}}`. If the claim is *not* a LoF-disease claim (e.g. gain-of-function, or gene–gene) ⇒ this prior emits **no flag but is `applicable:True`** (the constraint just isn't a counter-signal here) — recorded as `info`-free, distinct from `not_applicable`.

**Epistemic guardrails.** Applicability-gated twice (gene resolvable → constraint record present → claim is LoF-disease-shaped). Down-weight 0.7, gated behind RQ-M08. INFERRED. LOEUF>0.6 is a *tolerance* signal, not proof the claim is false — it flags for human review on anchored claims, never asserts falsehood.

**Required experiment.** Covered by **RQ-M08** (the LoF-on-tolerant-gene seeded positive is this prior's test case). No separate experiment — the flag rule is a deterministic threshold on a published metric; its *value as a membrane signal* is exactly what RQ-M08 measures.

**Acceptance criteria.** A LoF→disease claim on a gene with `oe_lof_upper=0.9` yields one `gnomad` `warn` flag with `down_weight=0.7`; the same gene under a gain-of-function claim yields `applicable:True` + no flag; a gene with null `gnomad_constraint` yields `applicable:False`. **Runnable check:** `pytest persona/tests/test_priors.py::test_gnomad_lof_tolerant_flags_only_lof_claims` (stubbed `service.post_json` returning fixture constraint JSON — no live network).

**Effort** S · **Dependencies** F8.0.

---

### F8.2 — GTEx median-TPM tissue-expression prior

**Problem & evidence.** A mechanistic claim asserting a gene acts *in a given tissue* is implausible if the gene is effectively unexpressed there. GTEx v10 publishes median TPM per gene across 54 tissues (gtex skill §2, `/expression/medianGeneExpression`). Persona never checks it: a claim like "GENE drives signaling in liver" survives even when GTEx liver median TPM ≈ 0. Research/source: GTEx Consortium 2020 (tissue-specific expression); GTEx API v2 `expression/medianGeneExpression?gencodeId=…&datasetId=gtex_v10` (verified endpoint, gtex skill §2). Threshold: **median TPM < 1 = effectively unexpressed** (standard low-expression cutoff; tunable knob).

**Design.**
- `gtex_expression(gene_symbol, tissue=None)` in `priors.py` — GET `https://gtexportal.org/api/v2/expression/medianGeneExpression` with `params={"gencodeId":<ensembl_versioned_or_symbol>, "datasetId":"gtex_v10", "itemsPerPage":100}` via `service().get_json(...)`. GTEx keys on GENCODE id; pass the Ensembl id from `resolve_gene` (GTEx accepts unversioned Ensembl / symbol on this endpoint — **verify the exact id form in a scratch call before wiring**, per CLAUDE.md §1; §6 O-2). Returns `tissues:[{tissue: tissueSiteDetailId, tpm: median}]`; if `tissue` given, also `median_tpm` for that tissue. **Applicability gate:** empty `data` (gene not in GTEx) ⇒ `{applicable:False, reason:'gene-not-in-gtex'}`.
- Tissue extraction (in `molecular_prior_flags`): the claim must name a tissue. Match the claim's `object`/`relation`/`quote` against the GTEx tissue vocabulary (the 54 `tissueSiteDetailId` values — fetched once from `/dataset/tissueSiteDetail` and cached as a module constant, or a small static map of common synonyms → GTEx ids). **No tissue term ⇒ GTEx prior `not_applicable`** (explicit skip; a gene-without-tissue claim gets no expression check — the correctness boundary).
- Flag rule: `median_tpm < 1.0` for the claimed tissue ⇒ `{prior:'gtex', kind:'unexpressed_in_tissue', severity:'warn', down_weight:0.75, detail:f"GTEx v10 median {median_tpm:.2f} TPM in {tissue} (<1 → effectively unexpressed); a mechanistic role in this tissue is implausible", source:'gtex_v10', evidence:{tissue, median_tpm}}`.

**Epistemic guardrails.** Applicability-gated: no tissue in the claim ⇒ `not_applicable` (never invents a tissue); gene not in GTEx ⇒ `not_applicable`. Down-weight 0.75, gated behind RQ-M08. INFERRED. Low expression flags implausibility for review; it does not assert the mechanism is impossible (low-abundance regulators exist) — hence a nudge, not a veto, and human routing on anchored claims.

**Required experiment.** Covered by **RQ-M08** (the gene-in-unexpressed-tissue seeded positive). Deterministic threshold on a published metric; membrane value measured by RQ-M08.

**Acceptance criteria.** A "GENE acts in liver" claim where GTEx liver median = 0.3 yields one `gtex` `warn` flag; the same claim with no tissue term yields `gtex` `not_applicable`; a gene absent from GTEx yields `applicable:False`. **Runnable check:** `pytest persona/tests/test_priors.py::test_gtex_flags_unexpressed_and_skips_no_tissue` (stubbed `service.get_json`).

**Effort** S · **Dependencies** F8.0.

---

### F8.3 — Open Targets genetic-support prior (L2G / genetic_association vs literature)

**Problem & evidence.** Persona's belief that GENE associates with DISEASE can rest entirely on **literature co-mention** — which is exactly what the swarm reads. Open Targets separates evidence by datatype: `genetic_association` (GWAS L2G, rare-variant burden, ClinVar — real human-genetics support) vs `literature` (Europe PMC text-mining — co-mention) (OT skill §4). A gene–disease pair with high `literature` score but ~zero `genetic_association` score is **association-heavy**: much written, little human-genetics backing — a distinct, checkable weakness. The existing `open_targets` client (science.py:15-48) fetches only the *aggregate* association score, discarding the datatype breakdown. Research/source: Open Targets Platform datatype scores + L2G (Ghoussaini et al. 2021, Open Targets Genetics; L2G > 0.5 = credible genetic link, OT skill §"Positive indicators"); OT GraphQL `associatedDiseases{ rows{ disease{id} score datatypeScores{ id score } } }`.

**Design.**
- `ot_genetic_support(ensembl_id, disease_term)` in `priors.py` — reuse the OT GraphQL endpoint constant already in the repo (`https://api.platform.opentargets.org/api/v4/graphql`, science.py:21) via `service().post_json`. Query `target(ensemblId:$id){ associatedDiseases(page:{index:0,size:50}){ rows{ disease{id name} score datatypeScores{ id score } } } }`; match the row whose `disease.name`/`id` best matches `disease_term` (canonical/substring match — the claim's object). Extract `genetic_score` = the `datatypeScores` entry with `id=='genetic_association'` (0 if absent) and `literature_score` = `id=='literature'`. `has_genetic_support = genetic_score >= 0.05`. **Applicability gate:** target has no associated-disease row matching the claim object ⇒ `{applicable:False, reason:'no-ot-association-for-pair'}`.
- Flag rule (in `molecular_prior_flags`, for a gene–disease claim): `literature_score >= 0.20 AND genetic_score < 0.05` ⇒ `{prior:'ot_genetics', kind:'association_heavy_no_genetics', severity:'warn', down_weight:0.8, detail:f"OT literature={literature_score:.2f} but genetic_association={genetic_score:.2f} (<0.05 → no human-genetics support); association-heavy, co-mention-driven", source:'opentargets', evidence:{genetic_score, literature_score}}`.

**Epistemic guardrails.** Applicability-gated (pair must resolve in OT). The two scores are **read from OT's own datatype breakdown**, not computed by a model — no fabricated confidence. Down-weight 0.8 (the mildest of the three: absence of genetic evidence is weaker disconfirmation than active population-genetics tolerance), gated behind RQ-M08. INFERRED. Distinguishes *no genetic support yet* from *contradicted*; routes anchored claims to human.

**Required experiment.** Covered by **RQ-M08** (the high-comention-no-genetics seeded positive). The scores are OT-published; membrane value measured by RQ-M08.

**Acceptance criteria.** A gene–disease claim where OT gives literature=0.4, genetic_association=0.0 yields one `ot_genetics` `warn` flag with `down_weight=0.8`; a pair with genetic_association=0.6 yields `applicable:True` + no flag; an unmatched pair yields `applicable:False`. **Runnable check:** `pytest persona/tests/test_priors.py::test_ot_association_heavy_flag` (stubbed `service.post_json` returning fixture `datatypeScores`).

**Effort** S · **Dependencies** F8.0.

---

## 4. Sequencing (stubs/interface first, then order)

**Milestone 0 (hour 1 — land signatures so PRD-02's `admit_candidate` author can call them):**
1. `persona/memory/priors.py` with all six signatures (§2) returning typed safe defaults: `molecular_prior_flags` → `{status:'not_applicable', flags:[], provenance:'INFERRED', gene:None, priors:{}}`; `apply_priors` → `candidate` unchanged; the three clients → `{applicable:False, reason:'stub'}`. This makes the membrane call site a no-op until filled — **safe-degrade by construction** (priors absent ⇒ membrane behaves exactly as PRD-02).

**Then:**
- **F8.0** — gene resolution (`resolve_gene` via gnomAD), the orchestrator skeleton, `apply_priors` gate-guard, and the `membrane.admit_candidate` call site. Wire the `molecular_priors_gate.json` load (default: gate absent ⇒ advisory-only). This unblocks the three priors and makes the whole thing observable (flags render) before any down-weighting is live.
- **F8.1 gnomAD** → **F8.2 GTEx** → **F8.3 OT** — independent; order by decreasing disconfirmation strength (gnomAD first: the LoF-tolerant signal is the headline). Each self-gates and plugs into the orchestrator.
- **RQ-M08** — run once all three flag rules exist; on pass, flip `molecular_priors_gate.json` `passed=True` to enable autonomous down-weighting. Until then, advisory-only.
- **CCP-08a** (optional science.REGISTRY exposure) — only if the master routes it to Lane 3; last, non-blocking.

---

## 5. Test & verification plan

- **Unit (assert-based pytest, no live network — stub `ingest.service.service()`'s `post_json`/`get_json` with recorded fixture JSON):** one `test_priors.py` with the four named checks (F8.0–F8.3). Fixtures are real recorded gnomAD/GTEx/OT responses for a known LoF-tolerant gene, an unexpressed gene–tissue pair, and an association-heavy pair (record once via a scratch script per CLAUDE.md §1, then commit as fixtures — CI runs offline, cache-backed, mirroring PRD-03 F3.6's recorded-fixture posture).
- **Applicability-gate assertions (the correctness boundary):** explicit tests that a non-gene claim, a gene-without-tissue claim, and an OT-unmatched pair each yield `not_applicable`/`applicable:False` — *distinct from* a passed check with no flag. This is the out-of-domain-false-positive guard PRD-00 §2 calls the correctness boundary.
- **Down-weight discipline assertions:** `apply_priors` with the gate off leaves `calibrated_p` untouched; with the gate on, `calibrated_p` only decreases, never below the `MOL_PRIOR_FLOOR=0.5` clamp, and never increases. An anchored claim with a `warn` flag files a handoff and does **not** mutate the anchor (reuse the no-mutation spy pattern from PRD-02 F2.9 `test_revisit.py`).
- **Integration:** a harvest over a fixture source dir carrying one LoF-on-tolerant-gene claim → with the gate on, its committed `calibrated_p` is below the same claim's no-prior baseline, and a trust-ledger recompute surfaces the `gnomad` flag; with the gate off, the flag is present but `calibrated_p` is the baseline.
- **Experiment (seeded ≥20, mean ± 95% CI, saved to `experiments/` + `results/FINDINGS.md#RQ-M08`):** RQ-M08 — precision Δ + false-flag rate gate on the labeled gene-centric set.
- **Reuse existing oracles:** RQ-M01/RQ-E01a resampling harness style for the RQ-M08 splits (PRD-02 §5); the `gate_decisions.jsonl` append/read pattern (PRD-00 §4) is exercised by the integration test.
- **Regression guard:** with `priors.py` at its Milestone-0 stub (or the gate off), the existing membrane + integrity suite must pass unchanged — priors are strictly additive and safe-degrading.

---

## 6. Open questions for the master / user

- **O-1 (down-weight is gated — confirm the RQ-M08 gate values).** Proposed: enable autonomous down-weighting only when precision improves ≥ +0.05 absolute **and** false-flag rate ≤ 0.05 on correctly-specific controls; down-weight floor 0.5 (a prior halves confidence at most). Confirm these thresholds, or set. *Blocks nothing — priors ship advisory-only until the gate flips.*
- **O-2 (GTEx gene-id form).** GTEx `medianGeneExpression` keys on GENCODE id; the exact accepted form (versioned `ENSG…​.N` vs unversioned vs symbol) must be verified against a live call before wiring (CLAUDE.md §1). Confirm it's acceptable to add a one-off scratch verification call (not a seeded experiment — a build-time endpoint check, same as PRD-03 F3.9's stance).
- **O-3 (rate-limit tuning — advisory).** `gnomad.broadinstitute.org` and `gtexportal.org` fall under `service._LIMITS['_default'] = (0.5, 2)` (service.py:70) with no edit needed. If either API 429s under demo load, tuning `_LIMITS` is a one-line additive change to `ingest/service.py` (not in any lane's edit-set) — flag whether that file should be touched by this lane or coordinated.
- **O-4 (CCP-08a routing).** The optional `science.REGISTRY` exposure (analyst tool-loop can pull a prior on demand) is a Lane-3 file edit. Route to Lane 3, or leave priors membrane-internal? *Non-blocking.*
- **O-5 (LoF-claim detection).** F8.1 fires only on LoF-causes-disease-shaped claims, detected structurally (deleterious `effect_sign` + LoF lexical cues in relation/quote: "loss-of-function"/"knockout"/"haploinsufficien"/"truncating"/"null"). Confirm this heuristic is acceptable as the applicability trigger, or should a claim carry an explicit mechanism field upstream (would need an extraction-schema change — cross-lane, Lane 1)?
