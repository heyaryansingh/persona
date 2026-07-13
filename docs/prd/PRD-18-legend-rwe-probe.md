# PRD-18 — OHDSI LEGEND calibrated real-world-evidence probe

> Owner: implementer lane **3** (Engine / forensics / data acting-loop) · Status: **DRAFT-for-implementation** · Autonomy: **Balanced** · Depends on: PRD-00 file-ownership map + epistemic contract; the shared **FC-8** oracle verdict envelope + `science.REGISTRY` registration; consumes **FC-2** (`inbox.file_handoff`, Lane 2) for anchor-overturning contradictions and (optionally) FC-3 `kg` read paths. Reuses the `IngestService` cache (`ingest/service.py`), the `science.py` client+REGISTRY pattern (`tools/science.py:137`), the `datasets.fetch` allowlist (`tools/datasets.py:13`), the `forensics.py` flag shape (`analysis/forensics.py:14`), and the provenance-normalized-envelope idea (IDEAS_BACKLOG #13). Backlog: **Wave 3c — OHDSI LEGEND calibrated-RWE probe**.

---

## 0. Summary + capability unlocked

Persona today can pool the studies *it has read* (PRD-10 meta-analysis), run a functional falsifier (PRD-07 DepMap), and test a causal sign it can compute (PRD-06 MR). What it **cannot** do is ask *"has someone already run this comparison at population scale, across many health systems, with the confounding empirically corrected?"* For a **drug→outcome comparative-effectiveness/safety** belief — the exact shape of a clinical claim ("thiazide diuretics beat ACE inhibitors on acute MI as first-line antihypertensives") — that second opinion already exists and is *pre-computed*: **OHDSI LEGEND** (Large-scale Evidence Generation and Evaluation across a Network of Databases) publishes **negative-control-calibrated hazard ratios** for tens of thousands of drug×comparator×outcome cells, replicated across ~9–12 observational databases, each with a **calibrated 95% CI** and an **E-value** for residual unmeasured confounding.

This PRD adds a probe that, for such a belief, looks up the matching LEGEND result **cell** and returns **`corroborated` / `contradicted` / `not-covered` / `inconclusive`** using the **calibrated** effect — *never* the naive uncalibrated HR — reporting **N databases** and the **E-value**. The capability nothing else in the stack has: **a large-scale external second opinion whose confounding is already empirically corrected**, typed as **READ external evidence** (Persona did not compute it — it *found* someone else's rigorously-calibrated TESTED result and adjudicates its own belief against it). It never fabricates: outside LEGEND's covered drug/outcome space it **abstains** (`not-covered`), and when the calibrated CI straddles 1 it says `inconclusive` rather than inventing a direction. Because it is a *lookup*, not a code-run, it is exact and reproducible for free — the verdict is pinned to a hashed result-set cell + its source DOI.

Why LEGEND specifically, and why *calibrated*: observational HRs are systematically biased; LEGEND's headline methodological contribution is that raw p-values and CIs from observational data are miscalibrated, and **empirical calibration against ~50–100 negative-control outcomes** (Schuemie et al., *Stat Med* 2014 33:209; *PNAS* 2018 115:2571) restores nominal coverage. Consuming the *naive* HR would import exactly the confounding Persona is supposed to be suspicious of. So the probe's single hard rule — **use the calibrated effect only** — is the whole epistemic point.

---

## 1. File ownership (disjoint)

**New (this lane creates, owns outright):**
- `persona/ingest/legend.py` — **the whole primitive**: the result-set client (`lookup_cell`), the belief→LEGEND-id resolver (`resolve_ids`, a curated bounded alias map — abstain outside it), the provenance-normalized cell envelope (backlog #13), and the pure verdict function `rwe_probe(...)` returning the **FC-8** envelope.
- `persona/data/legend/` — **bundled, curated result-set slice** (published LEGEND-HTN calibrated cells as a small CSV/JSON) + a `MANIFEST.json` recording source DOI, LEGEND release id, and a sha256 of the slice. This is the cached, offline-first data the demo runs on (`CLAUDE.md §4`: "cache aggressively … so nothing live can break the money-shot").
- `persona/tests/test_legend.py` — numeric-match reproduction gate + verdict/abstain/calibrated-not-naive unit tests.
- `experiments/exp_rq_e30_legend_reproduction.py` — RQ-E30 (published-cell numeric-match gate).

**Boundary file (same-lane, additive — no cross-lane collision):**
- `persona/tools/science.py` — **Lane 3 owns** (`PRD-00 §3`: `persona/tools/{science.py, datasets.py}` → Lane 3). This PRD *appends* a `legend_probe()` wrapper + one `REGISTRY` row + one `call()` branch, exactly as PRD-07 F7.1 appends `depmap`. Additive; no existing client edited.

**Consumed, never edited:**
- `persona/inbox.py` — **Lane 2 owns**. This PRD only *calls* `inbox.file_handoff(kind, dossier)` (**FC-2**) when a LEGEND `contradicted` would overturn an **anchored** belief.
- `persona/analysis/value_queue.py` — **Lane 3 / PRD-03 F3.2 owns**. The acting-loop trigger is a **`run_action` string** `"legend:<target>,<comparator>,<outcome>"` — additive data inside FC-8's existing opaque string, **no code edit here and no FC-4 signature change** (FC-8: "additive value in the existing opaque string").
- `persona/memory/kg.py` (FC-3, read only, optional), `persona/ingest/service.py` (`IngestService`, optional live refresh).

> **No cross-lane parallel-edit exposure.** The only files created+owned are `ingest/legend.py` (+ its data/tests/experiment). `science.py` is a same-lane additive append; everything else is a read of a stable surface.

---

## 2. FCs provided / consumed + CONTRACT CHANGE PROPOSAL

**CONSUMES — FC-8 (shared oracle verdict envelope, verbatim intent):** the probe registers in `science.REGISTRY`, is invoked via `science.call("legend", params)`, returns the `{status|verdict, applicable, methods, sensitivity, capsule, provenance, high_stakes, handoff_id?}` envelope, and is triggerable from FC-4 `value_queue` `run_action` `"legend:<args>"`. Lane 4 renders it with **one** component shaped like a `forensics.py` flag.

**CONSUMES — FC-2 (Lane 2, `persona/inbox.py`, verbatim):**
```
inbox.file_handoff(kind:str, dossier:dict) -> handoff_id:str
```
Used only when a `contradicted` verdict opposes an **anchored** belief (human-anchors-high-stakes).

**CONSUMES — existing stable reads (not FCs):** `kg.provenance(claim_id)` / `kg.beliefs` for anchored-flag + auto-target selection (`memory/kg.py`, optional — the core `rwe_probe` takes plain args and degrades to explicit-target mode, mirroring `audit.py:229 get_kg()`); `IngestService.get_bytes` for the optional live result-set refresh.

**PROVIDES — new public surface in `persona/ingest/legend.py`** (verbatim; semantics in §3):
```
legend.resolve_ids(subject:str, object:str, comparator:str|None=None) -> dict | None
    # -> {"target": str, "comparator": str, "outcome": str, "legend_study": str} or None (abstain)
legend.lookup_cell(target:str, comparator:str, outcome:str, *, analysis:str="meta") -> dict | None
    # -> provenance-normalized cell (backlog #13) or None (no matching cell)
legend.rwe_probe(subject:str, object:str, *, comparator:str|None=None,
    claimed_sign:str|None=None, kg=None, parent_id=None) -> dict     # FC-8 envelope
```
And in `persona/tools/science.py` (additive):
```
science.legend_probe(subject:str, object:str, comparator:str|None=None) -> dict
# REGISTRY += {"legend": (legend_probe, ["subject", "object"])}; call() gains a "legend" branch.
```

**CONTRACT CHANGE PROPOSAL — CCP-18a (FC-8 additive, backward-compatible; routed to master + Lane 4).**
LEGEND is a **lookup** oracle, not a code-run one, so two FC-8 fields need an additive extension — neither breaks any existing oracle:
1. **`provenance` enum += `"READ"`.** FC-8 today allows `'TESTED-provisional'|'INFERRED'|'abstain'`. A LEGEND cell is *external* calibrated evidence Persona READ, not a value it TESTED itself; the task mandates "typed **READ** external evidence." Adding `"READ"` is a strict superset — existing MR/DepMap/meta oracles keep emitting their current values unchanged.
2. **`capsule` is provenance-appropriate.** A lookup has no sandbox: its capsule carries `{result_set, input_sha256, cell_id, source_doi, release}` instead of `{session_id, script_sha256, sandbox_image_digest}`. FC-8's capsule is already an open dict of provenance fields; this documents that READ-lookup oracles seal *the source cell + its hash*, not a sandbox digest. Lane 4 still renders one flag-shaped component.

*Impact:* additive only; no consuming lane must change existing code. Needs master + Lane 4 ack before the `provenance:"READ"` value is rendered as its own badge (until acked, Lane 4 may render it under the existing `INFERRED`/external styling — the probe still ships and is callable).

---

## 3. Features

---

### F18.1 — Result-set client + provenance-normalized cell (`ingest/legend.py`)

**Problem & evidence.** `tools/science.py`'s six clients reach Open Targets / PubChem / UniProt / ClinicalTrials / NCBI / OpenAlex (`REGISTRY`, `science.py:137`) — none reaches *pre-computed calibrated comparative-effectiveness evidence*. LEGEND's full result sets are large per-database sqlite databases (hundreds of MB — well over `datasets.py:21 _MAX_BYTES = 30MB`), so a full-network download is **not viable** and is also unnecessary: Persona needs a *single cell* (one target×comparator×outcome row, plus its per-database replicates + the meta-analytic summary), not the matrix. Research/source: LEGEND-HTN — Suchard MA, et al. "Comprehensive comparative effectiveness and safety of first-line antihypertensive drug classes: a systematic, multinational, large-scale analysis." *Lancet* 2019;394:1816-26 (9 databases, ~4.9M patients, calibrated HRs); result sets published by the OHDSI network (`data.ohdsi.org` viewers) and archived study packages. Empirical calibration: Schuemie MJ, et al. *Stat Med* 2014;33:209 (p-value calibration) + *PNAS* 2018;115:2571 (CI calibration). E-value: VanderWeele TJ, Ding P. *Ann Intern Med* 2017;167:268.

**Design.** Offline-first, no model:
- **Bundled slice (primary path).** `persona/data/legend/legend_htn_cells.csv` — a curated, independently-transcribed slice of published LEGEND-HTN cells (columns: `legend_study, target, comparator, outcome, analysis_id, n_databases, calibrated_hr, calibrated_ci_lo, calibrated_ci_hi, naive_hr, naive_ci_lo, naive_ci_hi, e_value, e_value_ci, source_doi, cell_locator`). A `MANIFEST.json` pins `{source_doi, legend_release, sha256, transcribed_by, transcribed_at}`. Small, hashable, embeds in the repo, survives an offline demo.
- **`lookup_cell(target, comparator, outcome, *, analysis="meta") -> dict | None`** — reads the slice (stdlib `csv`, cached in a module-level dict on first call), returns the matching row **normalized to a `Work`-style provenance envelope** (backlog #13) so the membrane types it cleanly:
  ```
  {"source_metric": "calibrated_HR", "calibrated_hr": float, "calibrated_ci": [lo, hi],
   "naive_hr": float, "naive_ci": [lo, hi], "e_value": float, "e_value_ci": float,
   "n_databases": int, "lab": "OHDSI LEGEND network", "doi": source_doi, "year": 2019,
   "quote": cell_locator, "analysis_id": analysis_id, "legend_study": legend_study}
  ```
  Returns `None` when no row matches (→ `not-covered` upstream). **Never imputes** a cell.
- **Optional live refresh (secondary, degrade-gracefully).** If a stable allowlisted mirror of the result slice exists (Zenodo/figshare are already in `datasets._ALLOW`, `datasets.py:15`), `lookup_cell` may refresh the bundled slice via `IngestService`/`datasets.fetch`; on any failure it silently falls back to the bundled slice (the demo never depends on the network). **ponytail: bundled CSV is the source of truth; live refresh is an optional freshener, add a real mirror URL only if/when one is published.**

**Epistemic guardrails.** No fabricated confidence — every number is transcribed from a *published* LEGEND cell, hash-pinned in `MANIFEST.json`, never a default. Exact-span grounding — the normalized cell carries `quote=cell_locator` (the exact table/figure/row it came from) so a downstream belief is offset-traceable to its source. Both calibrated **and** naive HRs are surfaced for transparency, but §F18.2 forbids deciding on the naive one.

**Required experiment.** Folded into **RQ-E30** (F18.3) — the client is validated by the numeric-match gate.

**Acceptance + ONE runnable check.** `lookup_cell("thiazide_diuretics", "ace_inhibitors", "acute_myocardial_infarction")` returns a dict whose `calibrated_hr`/`calibrated_ci`/`e_value`/`n_databases` equal the `MANIFEST`-pinned published values, and an unknown triple returns `None`. Check: `pytest persona/tests/test_legend.py::test_lookup_cell_matches_manifest_and_abstains`.

**Effort** S · **Deps** stdlib (`csv`, `json`, `hashlib`); optional `IngestService`.

---

### F18.2 — Belief→cell resolver + calibrated verdict (`ingest/legend.py`, FC-8)

**Problem & evidence.** LEGEND indexes cells by OMOP concept ids for drugs (RxNorm ingredient / class) and outcomes (standard SNOMED concepts). A Persona belief is free text (`subject`, `object`, `effect_sign` — `kg.py:13` stores `(subject, relation, object, effect_sign)`). Mapping arbitrary free text to LEGEND's exact vocabulary is the hard, error-prone part — and LEGEND covers a **bounded** space (LEGEND-HTN: first-line antihypertensive classes × cardiovascular/renal/safety outcomes; LEGEND-T2DM: second-line diabetes drugs × outcomes). So the resolver is a **curated bounded alias map**, not a general OMOP mapper — and its default outside that space is **abstain**, which is exactly correct (`not-covered` beats a wrong join). Building a general vocabulary mapper here is over-reach (**ponytail: YAGNI** — LEGEND's covered space is small and enumerable; a synonym dict is the lazy-correct primitive, upgrade to an OMOP-vocabulary service only if coverage must expand beyond the shipped studies).

**Design.** Pure, no model:
- **`resolve_ids(subject, object, comparator=None) -> dict | None`** — normalizes (lowercase, strip, synonym-fold via a small in-module `_ALIASES` dict, e.g. `{"hctz": "thiazide_diuretics", "hydrochlorothiazide": "thiazide_diuretics", "mi": "acute_myocardial_infarction", "heart attack": "acute_myocardial_infarction", …}`) and returns `{target, comparator, outcome, legend_study}` when **all three** resolve inside a covered LEGEND study, else `None`. When `comparator` is omitted, it may be inferred from the belief's relation if it names a comparator drug/class; otherwise `None` (a comparative claim needs two arms).
- **`rwe_probe(subject, object, *, comparator=None, claimed_sign=None, kg=None, parent_id=None) -> dict`** — the FC-8 envelope, deciding **only on the calibrated effect**:
  1. `ids = resolve_ids(...)`. If `None` → return `{"verdict":"not-covered", "applicable": False, "provenance":"READ", "detail":"outside LEGEND covered space", ...}` (abstain; the gate did not fire on real data).
  2. `cell = lookup_cell(ids["target"], ids["comparator"], ids["outcome"])`. If `None` → same `not-covered` abstain (covered vocabulary but no published cell).
  3. `claimed_sign` (from arg or, if `kg` given, from the belief's `effect_sign`): `'-'` = the target is *protective* vs comparator on the outcome (expect calibrated HR < 1); `'+'` = target *harmful* (expect HR > 1).
  4. **Verdict on the CALIBRATED CI only** (`lo, hi = cell["calibrated_ci"]`):
     - `lo <= 1.0 <= hi` → **`inconclusive`** (`applicable=True`): the calibrated external evidence is null/uncertain — neither corroborates nor contradicts. Never coerced into a direction.
     - CI excludes 1 **and** direction matches `claimed_sign` → **`corroborated`**.
     - CI excludes 1 **and** direction opposes `claimed_sign` → **`contradicted`**.
     - `claimed_sign is None` → report the calibrated effect + CI with `verdict="inconclusive"` (no belief direction to test against).
  5. **Envelope** (`methods.effect` fixed to `"calibrated HR (negative-control empirical calibration)"`; `sensitivity={"e_value_point": cell["e_value"], "e_value_ci": cell["e_value_ci"]}`; `methods.n_databases`, `capsule={result_set, input_sha256, cell_id, source_doi, release}` per CCP-18a; `provenance="READ"`; `high_stakes=True`).
  6. **Escalate on anchored overturn:** if `verdict=="contradicted"` **and** `kg` reports the pair's belief is `anchored`, file `inbox.file_handoff("legend_contradiction", dossier)` (**FC-2**) and attach `handoff_id`. Corroboration and inconclusive **never** write a belief and **never** anchor — READ external evidence is attached as support, it does not elevate provenance on its own.

**Epistemic guardrails.** **Calibrated-only is the hard rule** — the naive HR is surfaced for transparency but a `# see experiments/exp_rq_e30 — decide on calibrated CI, naive HR never gates` comment fences the decision path; a unit test asserts the verdict is invariant to the naive value and flips only with the calibrated one. Abstain (`not-covered`) is a first-class return distinct from a null result (`applicable=False`), mirroring the forensics `skipped/not-applicable` discipline (`PRD-00 §2`; `forensics.py`). `high_stakes=True` always (a drug→clinical-outcome verdict), so under Balanced autonomy it **auto-surfaces** but **never auto-anchors**; contradiction of an anchor routes to a human (FC-2). `provenance="READ"` — Persona did not run the analysis; it read someone else's calibrated result and typed it honestly.

**Required experiment.** RQ-E30 (F18.3) covers the numeric fidelity + calibrated-not-naive selection; the verdict branch logic is covered by deterministic unit assertions (below).

**Acceptance + ONE runnable check.** (a) a covered protective belief whose calibrated CI is entirely `<1` and `claimed_sign='-'` → `verdict="corroborated"`; (b) the same cell with `claimed_sign='+'` → `contradicted`; (c) a cell whose calibrated CI straddles 1 → `inconclusive` regardless of `claimed_sign`; (d) an out-of-vocabulary pair → `not-covered, applicable=False`; (e) with the naive HR mutated but calibrated held fixed, the verdict is unchanged. Check: `pytest persona/tests/test_legend.py::test_verdict_uses_calibrated_only_and_abstains`.

**Effort** M · **Deps** F18.1; FC-2 (consume); FC-3 read (optional).

---

### F18.3 — RQ-E30: reproduce a known LEGEND cell within tolerance (numeric-match fixture)

**Problem & evidence.** A probe that surfaces a *plausible-looking* HR is worse than none — a corrupted or mis-joined cell written into the belief-state as external corroboration is the "silent wrong number that propagates" the project forbids (`CLAUDE.md §4`). The client must be pinned to a **known published cell**. This is the exact posture of the sibling reproduction gates (PRD-10 RQ-E24 BCG, PRD-07 RQ control panel): a deterministic numeric-equality check against an independently-published value. Source fixture: a headline LEGEND-HTN cell from Suchard 2019 (*Lancet* 394:1816) — e.g. **thiazide/thiazide-like diuretics vs ACE inhibitors, outcome = acute myocardial infarction**, calibrated meta-analytic HR (favouring thiazides) with its calibrated 95% CI and E-value. *The exact numeric target is transcribed from the published supplement/result set at build time into `MANIFEST.json` — this PRD does not hard-code a remembered value (no fabricated confidence).*

**Design (`experiments/exp_rq_e30_legend_reproduction.py`).**
- **Deterministic numeric-match gate (primary, no model, no seed — like RQ-E24 Part A).** Load the bundled slice + `MANIFEST.json`; for the pinned known cell assert `abs(lookup_cell(...).calibrated_hr − published_hr) ≤ 0.02` (or ≤2% relative) **and** both calibrated-CI endpoints within tolerance **and** `n_databases == published_n` **and** `e_value` within tolerance. **This is the go/no-go gate** — an exact reproduction of a published external value proves the client parses/normalizes faithfully.
- **Calibrated-vs-naive selection check.** Assert `rwe_probe` decides on `calibrated_ci` (mutate `naive_hr`/`naive_ci` in a copy → verdict unchanged; mutate `calibrated_ci` across 1 → verdict flips to `inconclusive`). This guards the one rule that matters.
- **Coverage/abstain panel.** A small hand-labeled panel: covered cells → correct `corroborated/contradicted/inconclusive`; out-of-vocabulary drug/outcome pairs → **100% `not-covered`** (never a false verdict off-map).
- **Seeds:** deterministic lookup + dictionary resolver → **no stochastic component → seedless** (documented, mirroring RQ-E24's "No model, no seed"; the ≥20-seed rule applies to model-in-loop/stochastic choices — this has none, so gold-plating it with seeds would be theater per `CLAUDE.md §2`). Register **RQ-E30** in `docs/RESEARCH_QUALITY_PROGRAM.md`; results → `results/FINDINGS.md#RQ-E30`.

**Epistemic guardrails.** A numeric-equality gate against an external published value is the strongest possible fidelity check. The abstain panel guarantees the off-map default is `not-covered`, never a fabricated direction.

**Acceptance + ONE runnable check.** Gate passes (published cell matches within tolerance) → the probe may surface READ corroboration/contradiction; abstain panel 100% `not-covered` off-map. Check: `pytest persona/tests/test_legend.py::test_reproduces_published_cell_within_tolerance` (offline, deterministic).

**Effort** S · **Deps** F18.1, F18.2.

---

### F18.4 — `science.py` registration + acting-loop seam (additive)

**Problem & evidence.** The probe is only an *acting-loop* signal if the analyst tool loop and the value queue can invoke it. The registration seam is exactly the six-client pattern (`science.py:137 REGISTRY`, `science.py:147 call()`); the acting-loop seam is FC-8's `run_action` string (no FC-4 change).

**Design.**
- **`science.legend_probe(subject, object, comparator=None) -> dict`** — thin wrapper importing `ingest.legend.rwe_probe` (kept out of `ingest`'s import cycle; `science.py` already imports `ingest.service`). Returns the FC-8 envelope.
- **REGISTRY/`call()`:** append `"legend": (legend_probe, ["subject", "object"])` and a `"legend"` branch in `call()` reading `params.get("subject")`, `params.get("object")`, `params.get("comparator")` — same shape as the other six branches.
- **Value-queue dispatch (data only, no code edit):** a `run_action` string `"legend:<target>,<comparator>,<outcome>"` routes through FC-8's oracle dispatch to `science.call("legend", ...)`. `value_queue.py` is **not** edited (PRD-03 F3.2 owns it); the string is additive data.
- **Auditor surface (optional, additive):** when a paper's central claim is a drug→outcome comparative claim, `audit()` (Lane 3) *may* fold the `rwe_probe` verdict into its existing `flags`/`external` block — the envelope already matches the `forensics.py` flag shape (`{check/status/severity/detail/span}`-compatible). Optional; not required to ship.

**Epistemic guardrails.** Registration adds no new autonomy — the probe is READ external evidence; it auto-surfaces but never auto-anchors, and anchor-overturning contradictions route to FC-2 (F18.2). Advisory-only wiring, consistent with FC-4's "advisory until the gate passes" posture; here the fidelity gate is RQ-E30.

**Acceptance + ONE runnable check.** `science.call("legend", {"subject": "...", "object": "...", "comparator": "..."})` returns the same envelope as `rwe_probe`, and `"legend"` is present in `science.REGISTRY`. Check: `pytest persona/tests/test_legend.py::test_science_registry_dispatch`.

**Effort** S · **Deps** F18.2, F18.3.

---

## 4. Sequencing

**Milestone 0 (hour 1):** land `persona/ingest/legend.py` importable with typed stubs — `resolve_ids→None`, `lookup_cell→None`, `rwe_probe→{"verdict":"not-covered","applicable":False,"provenance":"READ"}` — and the `science.py` REGISTRY row (dispatching the stub). Lets Lane 4 wire an (empty) render path and the value queue reference `"legend:"` from hour 1.

**Then:**
1. **F18.1** — bundle the curated LEGEND-HTN slice + `MANIFEST.json`; implement `lookup_cell` + provenance-normalized cell.
2. **F18.3 (numeric gate first)** — RQ-E30 deterministic reproduction; **do not proceed past a red gate** (a wrong cell is a stop-the-line bug, per PRD-10 §4).
3. **F18.2** — `resolve_ids` alias map + `rwe_probe` calibrated-only verdict + FC-2 escalation.
4. **F18.4** — `science.py` registration + acting-loop seam; optional auditor fold.

---

## 5. Test plan

**Unit (pure, offline, no model/network):** `persona/tests/test_legend.py`
- `test_reproduces_published_cell_within_tolerance` — **the gate**: pinned LEGEND-HTN cell → `lookup_cell` → published calibrated HR/CI/E-value/N within tolerance (RQ-E30). Real published oracle, not a mock (same posture as reusing a published estimator as a test oracle, `CLAUDE.md §4`).
- `test_lookup_cell_matches_manifest_and_abstains` — known triple matches `MANIFEST`; unknown triple → `None`.
- `test_verdict_uses_calibrated_only_and_abstains` — corroborate/contradict/inconclusive/not-covered branches; verdict invariant to naive HR, sensitive to calibrated CI.
- `test_anchored_contradiction_files_handoff` — a `contradicted` verdict on a fixtured **anchored** belief fires exactly one `inbox.file_handoff` (spy); a non-anchored contradiction fires none.
- `test_science_registry_dispatch` — `"legend"` in REGISTRY; `science.call` returns the envelope.

**Experiment oracle (deterministic, seedless):** `experiments/exp_rq_e30_legend_reproduction.py` — numeric-match gate + calibrated-vs-naive selection + off-map abstain panel. Results → `results/FINDINGS.md#RQ-E30`; register RQ-E30 in `docs/RESEARCH_QUALITY_PROGRAM.md`.

**Reused oracles.** The verdict dict conforms to the `forensics.py` flag shape → Lane 4's existing robustness/trust renderer verifies it with no new test surface. `MANIFEST.json` sha256 + source DOI let any verdict be re-derived offline — the "replayable artifact" acceptance.

**Browser smoke (Lane 4 owns render):** once F18.4 lands, the verdict renders through the existing FC-8 oracle component; a `PERSONA_WORKERS=0` smoke confirms the calibrated HR + CI + **N databases** + **E-value** + the `READ`/external-second-opinion label display, with the naive HR shown-but-marked-not-used.

---

## 6. Open questions

- **O-1 (CCP-18a ratification — blocks Lane 4 render only).** Extend FC-8 `provenance` enum with `"READ"` and document the provenance-appropriate `capsule` for lookup oracles (`{result_set, input_sha256, cell_id, source_doi, release}` vs sandbox fields). Additive/backward-compatible; needs master + Lane 4 ack before `READ` renders as its own badge. **Until acked, the probe ships and is callable; Lane 4 renders it under existing external/INFERRED styling.** *This is the only item touching another lane.*
- **O-2 (data provenance & freshness).** Primary path is a **bundled, hash-pinned** LEGEND-HTN slice (offline-first, demo-safe). Is a live refresh from an allowlisted mirror (Zenodo/figshare — already in `datasets._ALLOW`) wanted for freshness, or is the pinned slice sufficient? **My proposal: pinned slice is source-of-truth; add a live mirror URL only when one is published.**
- **O-3 (coverage scope).** Ship **LEGEND-HTN** (antihypertensives, well-published) first; add **LEGEND-T2DM** as a second slice under the same schema when its result set is transcribed. Confirm HTN-first is acceptable, or name the priority study.
- **O-4 (`inconclusive` vs `not-covered`).** A calibrated CI straddling 1 returns `inconclusive` (`applicable=True` — the cell exists, the evidence is null); a missing cell returns `not-covered` (`applicable=False` — abstain). Confirm this two-way split (rather than collapsing both to abstain) — it preserves the legible distinction between "checked, no signal" and "couldn't check."
- **O-5 (auto-writeback under Balanced autonomy).** READ external corroboration is **never** auto-anchored (it attaches as support). Confirm: corroboration auto-surfaces as READ evidence; contradiction of an anchor → FC-2; nothing about a LEGEND lookup ever writes a TESTED belief (it isn't Persona's own computation). **My proposal: yes — READ-only, anchors always human-gated.**

---

### Compact summary

**File:** `docs/prd/PRD-18-legend-rwe-probe.md` (spec only; no source edited).

**New owned:** `persona/ingest/legend.py`, `persona/data/legend/` (bundled slice + `MANIFEST.json`), `persona/tests/test_legend.py`, `experiments/exp_rq_e30_legend_reproduction.py`. **Additive same-lane:** `persona/tools/science.py` (REGISTRY row + `legend_probe` wrapper + `call` branch).

**Features:** F18.1 result-set client + provenance-normalized cell · F18.2 belief→cell resolver + calibrated-only FC-8 verdict · F18.3 RQ-E30 published-cell numeric-match gate · F18.4 `science.py` registration + acting-loop seam.

**NEW public signatures:**
```
legend.resolve_ids(subject:str, object:str, comparator:str|None=None) -> dict | None
legend.lookup_cell(target:str, comparator:str, outcome:str, *, analysis:str="meta") -> dict | None
legend.rwe_probe(subject:str, object:str, *, comparator:str|None=None, claimed_sign:str|None=None, kg=None, parent_id=None) -> dict
science.legend_probe(subject:str, object:str, comparator:str|None=None) -> dict   # REGISTRY += {"legend": (legend_probe, ["subject","object"])}
```
FC-8 envelope keys: `{verdict, applicable, calibrated_hr, calibrated_ci, naive_hr, e_value, n_databases, methods, sensitivity, capsule, provenance:"READ", high_stakes, handoff_id?, detail}`.

**Open questions blocking other lanes:** **O-1 (CCP-18a)** — FC-8 `provenance` enum += `"READ"` + lookup-oracle capsule shape; blocks Lane 4's dedicated `READ` render only (probe ships + is callable without it). No other lane is blocked.
