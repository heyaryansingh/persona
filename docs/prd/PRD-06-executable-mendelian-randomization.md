# PRD-06 — Executable Mendelian-randomization causal test

> Owner: implementer lane 3 · Status: DRAFT-for-implementation · Autonomy: Balanced · Depends on: FC-2 (`inbox.file_handoff`, Lane 2), FC-4 (`engine.value_queue` `run_action`, Lane 3 self), existing `ResearchSession`/`verify_session` (`persona/sessions.py`), existing `sandbox.run_python` (`persona/tools/sandbox.py`), existing `IngestService` (`persona/ingest/service.py`)

## 0. Summary + how it advances the vision

Persona today can *read* that "exposure E causally affects disease D" and it can *audit* whether a paper claiming so replicates — but it cannot **run the causal test itself**. That gap is not hypothetical: a real past investigation abandoned a causal question with the note *"the MR/GWAS host needed for a live causal check, gwas.mrcieu.ac.uk, was not on the sandbox's allowlist and network access inside the sandbox is disabled"* (`persona-workspace/projects/does-the-microbiome-causally-affect-depression-o/REPORT.md:7`). PRD-06 closes exactly that loop. For any belief of the form "E changes D", when both E and D have harmonized GWAS summary statistics in **IEU OpenGWAS** (`https://gwas.mrcieu.ac.uk`, API `https://api.opengwas.org`), the acting loop: (1) pulls genome-wide-significant, LD-clumped instrument SNPs for E, (2) looks those SNPs up in the D GWAS and harmonizes alleles, (3) runs **two-sample MR — IVW + MR-Egger + weighted-median — in the sandbox**, (4) computes **pleiotropy and heterogeneity sensitivity** (MR-Egger intercept, Cochran Q, mean F-statistic), and (5) returns a signed effect estimate with a **replayable capsule** (a sealed `ResearchSession`: harmonized SNP table + MR script + result JSON, all hash-verifiable via `verify_session`).

The new capability nothing else in the stack has: **Persona executes a human-grade causal-inference analysis on public genetic data and returns a calibrated, sensitivity-gated causal verdict** — not a literature summary of what MR studies *said* (which is all `analyst.py` can do today via `literature_search`), but the estimate itself, reproducible to the SNP. It is the sharpest instance of the thesis "acting loop + persistent self, not just retrieval": the auditor tells you whether a *paper* holds; MR tells you whether the *causal claim* holds, from primary data, faster than a human could stand up the pipeline. Epistemically it stays honest by construction — a `causal` verdict is emitted **only** when the sensitivity checks pass (F ≥ 10, no directional pleiotropy, method concordance); weak instruments, missing/ambiguous GWAS, or pleiotropy force an explicit **`abstain`** state distinct from a genuine **`null`**, mirroring the forensics applicability-gate discipline (PRD-03 §F3.8). Results are `TESTED-provisional`, never settled; a high-stakes clinical exposure→disease `causal` verdict routes to the human handoff (FC-2), never auto-anchors.

## 1. File ownership (disjoint set)

**New (this lane creates):**
- `persona/ingest/opengwas.py` — IEU OpenGWAS client (study resolution, instrument tophits, cross-GWAS associations) via `IngestService` cache. Lane 3 owns `persona/ingest/*` (per PRD-00 §3 map).
- `persona/analysis/mr.py` — the MR engine + orchestrator: pure estimators (`mr_estimates`, `harmonize`, `f_statistic`), the sensitivity gate, the sandbox run, the `ResearchSession` capsule, and `_write_report` (verdict written like the robustness auditor). Lane 3 owns `persona/analysis/*`.

**Edited (this lane only):**
- `persona/tools/science.py` — add `mendelian_randomization(exposure, outcome, ...)` tool-loop entry; register in `REGISTRY` (science.py:137) + dispatch in `call` (science.py:147). Thin wrapper over `analysis.mr.run_mr`.
- `persona/analysis/value_queue.py` — (PRD-03 F3.2, Lane 3) extend the `run_action` vocabulary with the `"mr:<exposure>|<outcome>"` verb for MR-testable causal claims. Internal to Lane 3.
- `persona/config.py` — add `OPENGWAS_JWT` env read (additive, backward-compatible; mirrors existing `NCBI_API_KEY` at science.py:105). **Boundary note below.**

**Boundary files another lane / shared infra also touches (decoupled by an FC or flagged):**
- `persona/ingest/service.py` — **shared infra, not in any lane's owned set** (PRD-00 §3). PRD-06 needs one *additive, backward-compatible* change: an optional `headers=None` kwarg on `IngestService.get_json`/`post_json` so `opengwas.py` can send the `Authorization: Bearer <JWT>` header while keeping the shared cache + per-host rate limiter (the entire reason the prompt says "via IngestService cache"). This is flagged as **CONTRACT CHANGE PROPOSAL CCP-1** (§2) for the master to ratify, since `service.py` is cross-cutting. If rejected, fallback in §2.
- `persona/config.py` — shared config module (not lane-owned). The `OPENGWAS_JWT` addition is additive-only (new optional env var, default `""`); flagged with CCP-1 as a trivial shared-file touch.
- `persona/api/*` and `persona/api/static/index.html` — **Lane 4 owns.** Lane 4 renders the MR verdict and routes an `mr:` `run_action` to the MR entry. PRD-06 provides the data + the stable `science.mendelian_randomization` entry (proposed **FC-8**, §2); Lane 4 consumes. We do not edit API/HTML.
- `persona/inbox.py` — **Lane 2 owns.** PRD-06 only *calls* `inbox.file_handoff(kind, dossier)` (FC-2) when a high-stakes clinical `causal` verdict must be human-anchored.

## 2. Frozen contracts provided/consumed

**CONSUMES — FC-2 (Lane 2), new `persona/inbox.py`** (verbatim):
```
inbox.file_handoff(kind:str, dossier:dict) -> handoff_id:str
# dossier = {decision_requested, why_unresolvable, disagreeing:[{claim_id,span,qualifiers}], conflict_type:'temporal'|'semantic'|'misinformation'|'insufficient', cheapest_test:{action,cost_tier,dataset}, expected_updates:[{outcome,belief_change}], uncertainty, authority_boundary}
```
Used only for the human-gated route (a `causal` verdict on a high-stakes clinical claim). MR maps: `conflict_type='insufficient'` when abstaining for want of data; the dossier's `cheapest_test.action` is the `mr:` run_action; `authority_boundary="clinical causal inference requires expert/wet-lab confirmation; MR is provisional genetic evidence only"`.

**CONSUMES — FC-4 (Lane 3 self), `engine.value_queue` `run_action` field** (verbatim shape from PRD-03 §2):
```
engine.value_queue(topic) -> [{question, resolves_claim_id, voi:float, cost_tier:'public_data'|'cheap_assay'|'expensive', dataset_available:bool, de_risks_n:int, run_action:str}]
```
`run_action` is already an opaque dispatch string (PRD-03 F3.2 examples: `"geo_lookup:GSE12345"`, `"reanalyze:<slug>"`). PRD-06 adds the additive verb `"mr:<exposure>|<outcome>"` and sets `cost_tier='public_data'` + `dataset_available=True` when both GWAS resolve. No FC-4 signature change — only a new value in an existing free-string field.

**PROVIDES — proposed FC-8 (Lane 3), `persona/tools/science.py` + `persona/analysis/mr.py`** — CONTRACT CHANGE PROPOSAL CCP-2:
```
science.mendelian_randomization(exposure:str, outcome:str, *, exposure_gwas=None, outcome_gwas=None) -> dict
# -> the MR verdict dict (schema in §3, F6.2). Stable entry the acting loop + Lane 4 call.
mr.run_mr(exposure:str, outcome:str, *, exposure_gwas=None, outcome_gwas=None, session=None, parent_id=None) -> dict
```
FC numbering is master-controlled, so registering this as **FC-8** is proposed, not assumed. Until ratified, Lane 4 treats `science.mendelian_randomization` as the de-facto entry (it is already reachable through the existing `science.call` dispatch, science.py:147, requiring no new route).

**CONTRACT CHANGE PROPOSAL CCP-1 (shared infra `persona/ingest/service.py`).**
Add optional `headers: dict | None = None` to `IngestService.get_json` and `IngestService.post_json`; when present, merge into the request `kw` (`kw["headers"] = headers`). The cache key (`_ckey`, service.py:100) is **unchanged** — deliberately token-independent, since the same GWAS query returns the same summary stats regardless of which caller's token authorized it. Rationale: OpenGWAS requires `Authorization: Bearer <JWT>` (post-2024 abuse mitigation), and the prompt mandates the shared cache/rate-limiter path. Backward-compatible (default `None` ⇒ current behavior). **Fallback if rejected:** `opengwas.py` uses a private, module-local `httpx.Client` with the bearer header and a small `functools.lru_cache` — loses the shared SQLite budget cache but stays functional; PRD-06 defaults to CCP-1 because the demo money-shot depends on aggressive caching of the canonical GWAS lookups (CLAUDE.md §4).

## 3. Features

---

### F6.1 — IEU OpenGWAS client (`persona/ingest/opengwas.py`)

**Problem & evidence.** No client exists for GWAS summary statistics; the causal-check gap is documented at `persona-workspace/projects/does-the-microbiome-causally-affect-depression-o/REPORT.md:7` ("the MR/GWAS host … was not on the sandbox's allowlist and network access inside the sandbox is disabled"). Every existing science client (`open_targets`, `clinical_trials`, `ncbi_search`, science.py:15–112) goes through `service().get_json`/`post_json` (ingest/service.py:167/179) for cache + rate limiting; MR needs the same pattern for a new host. Research/source: IEU OpenGWAS database (Elsworth et al. 2020, *bioRxiv* 2020.08.10.244293; the MRC-IEU resource behind `gwas.mrcieu.ac.uk`), API `https://api.opengwas.org` — `POST /api/tophits` (instrument SNPs), `POST /api/associations` (variant lookup in a study), `GET/POST /api/gwasinfo` (study metadata). The R analogue is `ieugwasr`/`TwoSampleMR` (Hemani et al. 2018, *eLife* 7:e34408) — we reimplement the data-pull, not import R.

**Design.**
- New `persona/ingest/opengwas.py`. All network calls via `service().get_json`/`post_json(..., headers={"Authorization": f"Bearer {config.OPENGWAS_JWT}"})` (CCP-1).
- `token_available() -> bool` — `bool(config.OPENGWAS_JWT)`. The applicability gate for the whole feature.
- `resolve_gwas(trait: str, *, prefer_population="European", min_sample=None) -> dict` — `GET /api/gwasinfo` (cached), fuzzy-match `trait` against study `trait` fields; return the single best confident match or **abstain on ambiguity**. Returns `{ok, gwas_id, trait, sample_size, ncase, ncontrol, population, note}` or `{ok:False, reason:'no-gwas'|'ambiguous'|'no-token', candidates:[...]}`. Ambiguity is surfaced (candidates listed), never silently resolved — the operator/human picks, matching human-anchors-high-stakes.
- `instruments(gwas_id: str, *, pval=5e-8, clump=True, r2=0.001, kb=10000) -> dict` — `POST /api/tophits` with **server-side LD clumping** (OpenGWAS clumps against its own reference panel — we do **not** build a local LD engine; ponytail: reuse the server's clumping). Returns `{ok, gwas_id, snps:[{rsid, beta, se, ea, oa, eaf, pval, n}], n_snps}`.
- `associations(rsids: list, gwas_id: str) -> dict` — `POST /api/associations` (batch variant lookup in the outcome study). Returns `{ok, rows:[{rsid, beta, se, ea, oa, eaf, pval}]}`.
- **Build-time endpoint verification (CLAUDE.md §1 "never assume an endpoint").** Before wiring, a scratch script (`experiments/scratch_opengwas_probe.py`, not committed to prod) confirms the exact `tophits`/`associations` request/response shapes against a live authenticated call on one known study (e.g. `ieu-a-300`, LDL cholesterol). The PRD encodes the *documented* shape; the scratch check ratifies it. This is a build-time check, not a seeded experiment.
- **Demo cache priming (CLAUDE.md §4).** A one-shot `prime_cache()` fetches + caches the canonical pairs (F6.4) so the money-shot (LDL→CHD) resolves offline; the SQLite HTTP cache (ingest/service.py:74) serves them thereafter.

**Epistemic guardrails.** Egress boundary preserved: fetching is OUTSIDE the sandbox (which stays `--network none`); only cached JSON crosses in as a mounted file. Abstain-not-fabricate: `resolve_gwas` returns an explicit `no-token`/`no-gwas`/`ambiguous` reason (distinct states), never a guessed study id. Provenance: every returned SNP row carries its source `gwas_id`, so the downstream harmonized table is reproducible (CLAUDE.md §4).

**Required experiment.** Trivial — no seeded experiment. This is deterministic API plumbing; correctness is the F6.4 RQ-E20 end-to-end recovery test using recorded fixtures + the build-time live probe. One offline unit test asserts token-absence abstains cleanly.

**Acceptance criteria.** (a) `token_available()` is `False` and `resolve_gwas(...)` returns `{ok:False, reason:'no-token'}` when `OPENGWAS_JWT` is unset — no network hit, no crash; (b) given a recorded `gwasinfo` fixture, `resolve_gwas("LDL cholesterol")` returns one `gwas_id` with `ok=True`; (c) `instruments`/`associations` parse a recorded fixture into the documented row schema. Runnable check: `pytest persona/tests/test_opengwas.py::test_resolve_abstains_without_token` (offline, no network).

**Effort** M · **Deps** `IngestService` (existing) + CCP-1; `config.OPENGWAS_JWT`.

---

### F6.2 — Two-sample MR engine + sensitivity gate (`persona/analysis/mr.py`, estimators + harmonize + gate)

**Problem & evidence.** No MR math exists in the repo. The estimators are exact, closed-form, and deterministic — the same posture as `forensics.py` ("the arithmetic is deterministic, unit-tested, and impossible to argue with", forensics.py:4), so they belong in `analysis/` next to the forensic checks. Research/source: IVW & Cochran Q — Burgess, Butterworth & Thompson 2013 (*Genet Epidemiol* 37:658); MR-Egger intercept for directional pleiotropy — Bowden, Davey Smith & Burgess 2015 (*Int J Epidemiol* 44:512); weighted-median — Bowden et al. 2016 (*Genet Epidemiol* 40:304); the F-statistic weak-instrument threshold F<10 — Staiger & Stock 1997 / Burgess & Thompson 2011 (*Int J Epidemiol* 40:755); palindromic-SNP harmonization — Hartwig et al. / TwoSampleMR practice.

**Design (pure, importable, host-runnable — no Docker needed for these).**
- `harmonize(exp_snps: list, out_rows: list, *, drop_palindromic=True, eaf_thresh=0.42) -> dict` — align each outcome SNP to the exposure effect allele: match `ea/oa`, flip `by` sign when alleles are swapped, drop SNPs absent in the outcome GWAS, and **drop ambiguous palindromic SNPs** (A/T, C/G) when EAF is missing or within `eaf_thresh` of 0.5. Returns `{bx, bxse, by, byse, rsids, n_used, n_dropped, dropped:[{rsid,reason}]}` (numpy arrays as lists). Fail-loud: a SNP with sign-ambiguous strand and no EAF is dropped with a logged reason, never silently kept.
- `f_statistic(bx, bxse) -> dict` — `mean_f = mean(bx**2 / bxse**2)`; `{mean_f, min_f, weak_instrument: mean_f < 10}`. The weak-instrument gate.
- `mr_estimates(bx, bxse, by, byse, *, seed=0, n_boot=1000) -> dict` — the three estimators:
  - **IVW** (inverse-variance weighted, random-effects): `beta = Σ(bx·by/byse²)/Σ(bx²/byse²)`; fixed `se = sqrt(1/Σ(bx²/byse²))`; **Cochran Q** `= Σ w·(by/bx − beta)²`, `w = bx²/byse²`, `df = n−1`; random-effects SE inflation `× sqrt(max(1, Q/df))`. Returns `{beta, se, pval, ci, q, q_pval, q_df}`.
  - **MR-Egger**: weighted least-squares regression of `by` on `bx` **with intercept**, weights `1/byse²`; slope = pleiotropy-robust causal estimate, **intercept** = directional-pleiotropy test. Returns `{beta, se, pval, intercept, intercept_se, intercept_pval}`.
  - **Weighted median**: weight-ordered cumulative-median of Wald ratios `by/bx`; SE by parametric bootstrap (`n_boot`, seeded — this is where the RNG seed enters). Returns `{beta, se, pval}`.
- `sensitivity_gate(estimates, fstat) -> dict` — the go/no-go: `weak_instrument = fstat.mean_f < 10`; `directional_pleiotropy = egger.intercept_pval < 0.05`; `heterogeneity = ivw.q_pval < 0.05`; `concordant = sign(ivw.beta)==sign(egger.beta)==sign(wmedian.beta)`; `significant = ivw.pval < 0.05`. Returns these plus a derived `verdict`:
  - `abstain` if `n_snps < 3` OR `weak_instrument` OR `directional_pleiotropy` (instruments/assumptions fail — cannot make a causal call);
  - `causal` **only if** `significant AND concordant AND not weak_instrument AND not directional_pleiotropy` (heterogeneity is *reported* but, with random-effects IVW + concordance, does not by itself block — it widens the CI and is surfaced);
  - `null` if `not significant` but instruments are valid (a genuine no-effect result, distinct from abstain);
  - `inconclusive` if significant-but-discordant across methods.

**Epistemic guardrails.** This *is* the applicability-gate discipline (PRD-03 F3.8, PRD-00 §2): `abstain` is a first-class state distinct from `null` — a weak-instrument or pleiotropic run never masquerades as "no causal effect." No-fabricated-confidence: every number is closed-form arithmetic over summary stats, not a model opinion. MR's three core assumptions (IV1 relevance — checked by F; IV2 independence — untestable from summary stats, stated; IV3 exclusion-restriction — partially probed by Egger intercept + Q, never proven) are printed in the report so a reader knows what the verdict does and does **not** establish.

**Required experiment.** RQ-E20 (new; register in `docs/RESEARCH_QUALITY_PROGRAM.md`). See F6.4 — the estimator correctness + positive/negative-control recovery gate lives there.

**Acceptance criteria.** (a) On synthetic instruments with a known true `beta*` and no pleiotropy, IVW recovers `beta*` within its 95% CI and Egger intercept ≈ 0 (`intercept_pval > 0.05`); (b) `f_statistic` flags `weak_instrument=True` when instruments explain ~0 variance; (c) `sensitivity_gate` returns `abstain` (not `null`) when `mean_f < 10`, and `causal` only when significant + concordant + valid. Runnable check: `pytest persona/tests/test_mr_estimators.py::test_ivw_egger_wmedian_recover_known_effect` and `::test_gate_abstains_vs_null` (pure, offline, seeded).

**Effort** M · **Deps** numpy/scipy (host + sandbox both have them — sandbox.Dockerfile:11).

---

### F6.3 — Sandboxed MR run + replayable capsule + verdict report (`persona/analysis/mr.py`, orchestrator)

**Problem & evidence.** The prompt requires the MR to *run in the sandbox* and the verdict to be *written like the robustness auditor*. `analyst.py` already shows the exact pattern: open a `ResearchSession` (analyst.py:189), fetch data OUTSIDE, mount it, `sandbox.run_python` (analyst.py:259, tools/sandbox.py:26), store artifacts + finalize → `verify_session`-able (sessions.py:221). `audit.py:344` shows the `_write_report` verdict style. MR reuses both. Running the estimators *inside* the sandbox (not just on the host) makes the result a sealed, hash-pinned, replayable capsule — the reproducibility feature (CLAUDE.md §4), and it pins the numeric environment via `sandbox.image_digest()` (analyst.py:193).

**Design.**
- `run_mr(exposure, outcome, *, exposure_gwas=None, outcome_gwas=None, session=None, parent_id=None) -> dict` in `persona/analysis/mr.py`:
  1. **Applicability pre-gate.** If `not opengwas.token_available()` → return `{ok:True, verdict:'abstain', applicable:False, reason:'opengwas-token-missing', ...}` (explicit, not an error). Resolve `exposure_gwas`/`outcome_gwas` via `opengwas.resolve_gwas` unless supplied; on `no-gwas`/`ambiguous` → `verdict:'abstain'`, reason carried, candidates surfaced.
  2. **Pull + harmonize (outside sandbox).** `opengwas.instruments(exposure_gwas)` → rsids → `opengwas.associations(rsids, outcome_gwas)` → `harmonize(...)` (F6.2). If `n_used < 3` → `abstain`.
  3. **Capsule.** Open `session = ResearchSession(get_persona().paths.runs_dir, f"MR: {exposure} → {outcome}", model="mr-engine/1.0", metadata={"kind":"mr", "exposure_gwas":..., "outcome_gwas":..., "sandbox_image_digest": sandbox.image_digest()})` (unless a parent `session` is passed). Write the harmonized SNP table as an artifact: `session.store_json("harmonized.json", {bx,bxse,by,byse,rsids,dropped})` (sessions.py:124). `session.record("gwas_resolved", {...})`, `session.record("harmonized", {n_used, n_dropped})`.
  4. **Run in sandbox.** Build the MR script by embedding the F6.2 estimator source via `inspect.getsource(mr_estimates)` + `inspect.getsource(f_statistic)` + `inspect.getsource(sensitivity_gate)` into a `_MR_SCRIPT` template that reads `/work/data/harmonized.json`, runs the three estimators + gate, and writes `/work/results/mr_result.json`. **One source of truth** — the sandbox runs the *same* code the host test runs (ponytail: no duplicated estimator implementation). `r = sandbox.run_python(script, workdir=project, data_dir=project/"data", timeout=90)` (tools/sandbox.py:26). Store the script (`store_text("mr.py", script, media_type="text/x-python")`) and the raw result (`store_json("mr_result.json", parsed)`) as artifacts; `session.record("mr_computed", {...})`.
  5. **Verdict + report.** Assemble the verdict dict (schema below), write `_write_report(...)` to `deliverables/mr/mr-<slug>.md` (auditor-style: headline signed estimate + per-method table + sensitivity block + stated MR assumptions + capsule link), `session.finalize("completed", title=..., conclusions=[{...}])` (sessions.py:128). Fail-loud crash guard mirrors `_finalize_crashed` (analyst.py:159): any exception invalidates the session, returns `ok:False`.
  6. If Docker is unavailable (`not sandbox.image_ready()`, sandbox.py:108), fall back to running the *host* `mr_estimates` (same functions) and mark `ledger.sandboxed=False` — the numbers are identical; only the capsule's environment-pinning is weaker. The capsule is still sealed + `verify_session`-able.
- **Verdict dict schema (F6.2/F6.3 output, the FC-8 return):**
```
{ok, exposure, outcome, exposure_gwas, outcome_gwas, applicable:bool,
 n_instruments:int, n_dropped:int,
 methods:{ivw:{beta,se,pval,ci,q,q_pval}, egger:{beta,se,pval,intercept,intercept_pval}, wmedian:{beta,se,pval}},
 sensitivity:{mean_f, weak_instrument:bool, directional_pleiotropy:bool, heterogeneity:bool, concordant:bool},
 verdict:'causal'|'null'|'inconclusive'|'abstain', direction:'+'|'-'|'0',
 provenance:'TESTED-provisional'|'abstain', high_stakes:bool, handoff_id:str|None,
 capsule:{session_id, harmonized_sha256, script_sha256, sandbox_image_digest, sandboxed:bool},
 assumptions:[str], reason:str, file:str}
```
- **Human gating.** `high_stakes = verdict=='causal' AND _is_clinical(exposure, outcome)` (a clinical exposure→disease pair, e.g. a drug-target or biomarker → disease). When `high_stakes`, do **not** mark the belief `TESTED`; instead `provenance='TESTED-provisional'` **and** file `inbox.file_handoff("mr_causal", dossier)` (FC-2) with `authority_boundary` set, capturing `handoff_id`. Non-clinical or `null`/`abstain` verdicts return without a handoff.

**Epistemic guardrails.** Replay-verifiable: the sealed event log + hashed artifacts make every MR run reproducible to the SNP (sessions.py `verify_session`). TESTED-provisional not settled: the belief written back is provisional (per PRD-00 §1 Balanced autonomy); a full causal claim is never auto-anchored. Human-anchors-high-stakes: a clinical `causal` verdict routes to FC-2, matching audit.py's flip-cap-to-handoff posture. MR assumptions stated (F6.2). Papers/traits are untrusted input — `exposure`/`outcome` strings are used only as OpenGWAS search terms + report text, never executed.

**Required experiment.** RQ-E20 (F6.4) covers the end-to-end recovery + gate. The capsule integrity itself reuses the existing `verify_session` oracle (no new experiment; parity engineering like PRD-03 F3.7).

**Acceptance criteria.** (a) `run_mr` on a recorded LDL→CHD fixture returns `verdict='causal'`, `direction='+'`, IVW `pval<0.05`, `mean_f≥10`, and a `capsule.session_id` for which `verify_session(runs_dir, id).ok is True`; (b) a recorded fixture with `mean_f<10` returns `verdict='abstain'` (not `null`); (c) a `high_stakes` `causal` verdict populates `handoff_id` (with `inbox.file_handoff` spied). Runnable check: `pytest persona/tests/test_mr_capsule.py::test_mr_run_is_replay_verifiable` (stubs `opengwas` with fixtures; if Docker absent, host-fallback path — still asserts sealed capsule).

**Effort** L · **Deps** F6.1, F6.2, `ResearchSession`/`verify_session` (existing), `sandbox` (existing), FC-2 (`inbox.file_handoff`).

---

### F6.4 — Positive/negative-control validation (RQ-E20)

**Problem & evidence.** A causal engine that can't recover *known* causal signs — and can't correctly *abstain* on nulls — is worse than none (it would launder false confidence into the belief-state, "the worst possible bug", CLAUDE.md §4). MR has canonical positive controls (LDL-C→CHD is the textbook strong-positive; BMI→T2D; smoking→lung cancer) and expected nulls (a trait pair with no genetic causal path; and a reverse-direction sanity check). This experiment is the go/no-go gate before MR auto-dispatches into `TESTED-provisional`.

**Design.** `experiments/exp_rq_e20_mr_controls.py`, results → `results/FINDINGS.md#RQ-E20`.
- **Fixtures, offline + deterministic.** Recorded OpenGWAS `tophits`/`associations` responses for the control pairs are cached under `experiments/fixtures/opengwas/` (primed once via F6.1 `prime_cache()`), so CI runs with no network and no token. This also caches the demo money-shot.
- **Positive controls:** LDL-C→CHD, BMI→T2D, smoking→lung cancer. **Negative/null controls:** ≥2 no-plausible-path pairs (e.g. a lipid→a genetically unrelated trait) + one reverse-direction pair (outcome-as-exposure where the true arrow is the other way).
- **Hypothesis + metric.** *Two-sample MR with the F6.2 sensitivity gate recovers the correct causal sign on positive controls (IVW `beta` sign correct, `pval<0.05`, `mean_f≥10`) and correctly avoids a `causal` verdict on negative controls (returns `null` or `abstain`, never `causal`).*
- **Seeds ≥20.** Point estimates are deterministic given fixed summary stats, so the 20 seeds come from (a) a **SNP jackknife/bootstrap** — resample the instrument set 20× per pair — reporting sign-recovery rate and false-`causal` rate as **mean ± 95% CI**; and (b) the weighted-median bootstrap RNG seed varied across the 20 (its SE is stochastic). This tests robustness to instrument choice, the real failure mode.
- **Go/no-go gate:** positive-control correct-sign-and-significant in **≥95%** of resamples per pair, **AND** false-`causal` rate on negatives **= 0** (an occasional `null`↔`abstain` swap on a negative is acceptable; a `causal` on a negative is a hard fail). Pass ⇒ MR may auto-dispatch `public_data`-tier `mr:` run_actions into `TESTED-provisional` (Balanced autonomy). Fail ⇒ MR renders advisory/human-click only, exactly as PRD-03 F3.1/F3.2 gate load-bearing metrics behind RQ-E06/E16.

**Epistemic guardrails.** Reversal-logging (CLAUDE.md §2): if a "known" positive fails to recover, log it as a finding (it may be a GWAS-version or instrument artifact, itself informative) — do not tune the gate until the control passes. The gate is pre-registered here; results are not cherry-picked.

**Acceptance criteria.** The experiment script runs offline on fixtures and emits the mean±CI sign-recovery + false-causal table to `results/FINDINGS.md#RQ-E20`; the gate boolean is computed and printed. Runnable check: `pytest experiments/test_exp_rq_e20.py::test_positive_controls_recover_and_negatives_abstain` (fixture-driven, ≥20 resamples, offline).

**Effort** M · **Deps** F6.1 (fixtures via `prime_cache`), F6.2, F6.3.

---

### F6.5 — Value-queue wiring: MR as a dispatchable `public_data` action (`persona/analysis/value_queue.py`)

**Problem & evidence.** The acting loop must be able to *choose* to run an MR test. PRD-03 F3.2 (`analysis/value_queue.py`) ranks contested/under-supported claims and emits a `run_action` the loop dispatches. A causal claim "E changes D" with both GWAS available is a `public_data`-tier, high-VoI test — the cheapest way to de-risk a keystone causal belief. This is the closure of the acting loop the microbiome-depression draft could not do.

**Design.**
- In `value_queue(topic)` (PRD-03 F3.2), for each contested claim classified **causal** ("E changes/causes/affects D"), probe `opengwas.resolve_gwas(E)` and `opengwas.resolve_gwas(D)` (cached; cheap). If both resolve → set `cost_tier='public_data'`, `dataset_available=True`, `run_action=f"mr:{E}|{D}"`, and raise VoI (a causal keystone testable from public data is maximal leverage). If either GWAS is missing/ambiguous → the claim stays in the queue but at its non-MR tier (the existing GEO/OpenTargets path), and `run_action` is not an `mr:` verb.
- The loop's dispatcher (Lane 4 / acting loop) parses `mr:<E>|<D>` → `science.mendelian_randomization(E, D)`. Balanced autonomy: auto-run only after RQ-E20 passes; until then the `mr:` action is human-click (advisory), matching FC-4's "auto-dispatch gated on RQ-E17".
- **ponytail:** reuse the existing `run_action` string channel and the existing `resolve_gwas` cache; no new queue field, no new endpoint.

**Epistemic guardrails.** `dataset_available` is verified by an actual `resolve_gwas` attempt, never asserted (mirrors PRD-03 F3.2). A `public_data` MR auto-runs into `TESTED-provisional` only post-gate; a clinical `causal` outcome still routes to FC-2 (F6.3). No claim is ranked on a fabricated availability.

**Required experiment.** Trivial — wiring + string convention. The *decision* to auto-dispatch is gated by RQ-E20 (F6.4); the classification "is this a causal claim" reuses the existing claim `kind` (`causal`) already extracted (audit.py:36 `kind ∈ {causal,...}`).

**Acceptance criteria.** (a) a causal claim whose E and D both resolve to a GWAS yields a queue item with `cost_tier='public_data'`, `dataset_available=True`, `run_action` matching `^mr:.+\|.+$`; (b) a causal claim with an unresolvable GWAS yields no `mr:` action. Runnable check: `pytest persona/tests/test_value_queue_mr.py::test_causal_claim_gets_mr_action` (stubs `opengwas.resolve_gwas`).

**Effort** S · **Deps** F6.1, PRD-03 F3.2 (`value_queue`).

---

## 4. Sequencing (stubs/interface first, then order)

**Milestone 0 (hour 1 — land importable stubs so Lane 4 + value_queue can build against them):**
1. `persona/ingest/opengwas.py` — stubs: `token_available()→False`; `resolve_gwas(...)→{ok:False,reason:'no-token'}`; `instruments`/`associations`→`{ok:False,reason:'no-token'}`.
2. `persona/analysis/mr.py` — stubs: `run_mr(...)→{ok:True, verdict:'abstain', applicable:False, reason:'not-configured'}`; empty typed `mr_estimates`/`harmonize`/`f_statistic`/`sensitivity_gate` returning documented-shape zeros.
3. `persona/tools/science.py` — register `mendelian_randomization` in `REGISTRY` + `call` dispatch, wired to the `mr.run_mr` stub. (This is the FC-8 entry — lets Lane 4 render against it immediately.)
4. `persona/config.py` — add `OPENGWAS_JWT = os.environ.get("OPENGWAS_JWT", "")`.
5. File **CCP-1** (service.py `headers` kwarg) + **CCP-2** (FC-8) in the HANDOFF dispatch log for master ack.

**Then, feature order (rationale):**
- **F6.2 (estimators + gate)** first — pure, offline, no deps, and it is the correctness core everything trusts. Build with its unit tests.
- **F6.4 (RQ-E20)** next — validates F6.2 on positive/negative controls using recorded fixtures; gate must pass before autonomy. (Requires F6.1 `prime_cache` to *create* the fixtures once, but the experiment itself runs offline.)
- **F6.1 (OpenGWAS client)** — real network client + CCP-1; build-time endpoint probe; primes the F6.4 fixtures + demo cache.
- **F6.3 (orchestrator + capsule + report)** — the largest edit; needs F6.1+F6.2; reuses `ResearchSession`/`sandbox`/`_write_report` patterns.
- **F6.5 (value_queue wiring)** last — needs F6.1 (`resolve_gwas`) + F6.3 (`run_mr`) live, and RQ-E20 to flip auto-dispatch on.

## 5. Test & verification plan

**Unit (pure, offline, no network/model/Docker):**
- `test_mr_estimators.py` — IVW/Egger/weighted-median recover a known synthetic `beta*`; Egger intercept ≈0 under no pleiotropy; `f_statistic` weak-instrument flag; `sensitivity_gate` `abstain` vs `null` vs `causal` distinctness (the correctness boundary).
- `test_opengwas.py` — token-absence abstains; fixture parsing into the row schema.
- `test_value_queue_mr.py` — causal claim + resolvable GWAS ⇒ `mr:` `public_data` action; unresolvable ⇒ none.

**Integration (recorded fixtures, no live network in CI):**
- `test_mr_capsule.py` — `run_mr` on the LDL→CHD fixture ⇒ `verdict='causal'`, `direction='+'`, and `verify_session(runs_dir, capsule.session_id).ok is True` (sealed, artifact-hashed, replay-verifiable — the headline). Reuses the existing `verify_session` oracle (sessions.py:221), exactly as PRD-03 F3.7 reuses it for the auditor. High-stakes path spies `inbox.file_handoff`.

**Experiment oracle (seeded ≥20, offline fixtures):**
- RQ-E20 (`exp_rq_e20_mr_controls.py`) — positive-control sign recovery ≥95% per pair; false-`causal` on negatives = 0; mean±95% CI over 20 SNP-resamples. Gate result printed + logged to `results/FINDINGS.md#RQ-E20`.

**Build-time (not CI):** `scratch_opengwas_probe.py` confirms the live `tophits`/`associations` request/response shapes against one authenticated study before wiring (CLAUDE.md §1).

**Browser smoke (Lane 4 owns):** once F6.3 lands, Lane 4 renders an MR verdict card (signed estimate + per-method table + sensitivity + capsule link + "TESTED-provisional / abstain" honest label) and an `mr:`-action button in the value queue; a `PERSONA_WORKERS=0` smoke confirms it renders the `abstain` state distinctly from `causal`/`null`.

## 6. Open questions for the master/user

- **O-1 (CCP-1 — shared `service.py` headers kwarg).** Adding an optional `headers=None` to `IngestService.get_json`/`post_json` is the clean way to send the OpenGWAS bearer token while keeping the shared cache/rate-limiter. `service.py` is shared infra (no lane owns it). **Ratify CCP-1**, or direct me to the fallback (module-local `httpx` client in `opengwas.py`, losing the SQLite budget cache)? This is the only change that blocks F6.1's real network path.
- **O-2 (CCP-2 — FC-8 registration).** I propose `science.mendelian_randomization(exposure, outcome, ...) -> verdict_dict` and `mr.run_mr(...)` as **FC-8** (Lane 3 provides), consumed by Lane 4 (render + `mr:` dispatch) and the acting loop. Confirm the FC number / namespace so Lane 4 imports a stable entry. (It is already reachable via `science.call`, so no new API route is strictly required.)
- **O-3 (OpenGWAS token + ToS).** OpenGWAS requires a free academic JWT (`OPENGWAS_JWT`) and rate-limits per token. Is a token available for the demo/CI, or should the canonical control pairs be shipped purely as recorded fixtures (F6.4) with live MR as an opt-in behind the token? Default: fixtures for CI + demo, live behind the token.
- **O-4 (auto-dispatch gate).** Balanced autonomy says auto-run NARROW `public_data` reanalyses into `TESTED-provisional`. F6.5 would auto-dispatch an `mr:` action **only after RQ-E20 passes**; a clinical `causal` verdict still routes to FC-2. Confirm auto-dispatch-gated-on-RQ-E20 (vs always human-click even for public data), matching FC-4's RQ-E17 posture.
- **O-5 (`mr:` run_action convention for Lane 4).** The `run_action="mr:<E>|<D>"` verb is additive to FC-4's opaque string field. Confirm Lane 4 will route `mr:`-prefixed actions to `science.mendelian_randomization` (parsing on the first `|`), so the acting loop closes end-to-end. No FC-4 signature change — only a new value.
