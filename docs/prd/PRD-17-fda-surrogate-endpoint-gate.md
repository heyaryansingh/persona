# PRD-17 — FDA surrogate-endpoint / biomarker-qualification gate

> **Owner lane:** 2 (Membrane & belief core) · **Status:** DRAFT-for-implementation (2026-07-13) · **Autonomy:** Balanced — the gate autonomously *down-tiers* a clinical-translation claim's surface class (never up-tiers, never anchors, never fabricates a qualification); any anchored/high-stakes clinical claim that the gate would restrict routes to a human via FC-2. · **Depends-on:** **FC-10** (PRD-12 causal-tier gate — this PRD *refines* its surrogate sub-gate and can supply its `SURROGATES` source, PRD-12 O-4); PRD-02 **F2.1** `membrane.admit_candidate` as the optional attach seam (same lane) and **FC-2** `inbox.file_handoff` for routing; existing `ingest.service.service()` HTTP core; the shared `ops_dir/gate_decisions.jsonl` ledger. No dependency on FC-4/FC-5/FC-6/FC-7/FC-8/FC-9/FC-11.

Wave 3c (clinical translation). Read `PRD-00-overview.md` §2 (epistemic discipline) and `PRD-12` before implementing; the FC-10 pairing is load-bearing here.

---

## 0. Summary + capability unlocked

Persona reads the biomedical literature and converges beliefs of the form `(subject, relation, object, effect_sign)` (`kg.add_claim`, `kg.py:89-132`). Nothing in the pipeline distinguishes **"drug X lowers LDL-C"** (a change in a *biomarker / surrogate*) from **"drug X prevents heart attacks"** (a *clinical outcome*). PRD-12's causal-tier gate (FC-10) already blocks *causal verbs* on an unlicensed tier and has a coarse hand-curated surrogate sub-gate (`causal_tier.is_surrogate`, `SURROGATES`, PRD-12 F12.3) that stops "lowers LDL-C" from silently becoming "prevents heart attacks." But FC-10 has **no channel to the one authority that actually decides whether a surrogate predicts an outcome for a given disease**: the FDA. A surrogate is only a *validated* stand-in for a clinical endpoint in a specific **context-of-use (COU)** — LDL-C is an accepted surrogate for cardiovascular risk in primary hyperlipidemia, but the same class of reasoning failed catastrophically for torcetrapib (raised HDL, *increased* mortality, ILLUMINATE 2007) and ezetimibe's early LDL story (ENHANCE 2008). Treating an *un-qualified* surrogate as clinical-endpoint evidence is the single most common way a literature synthesizer misleads a clinician.

PRD-17 adds a **membrane gate for clinical-translation claims**. When a belief treats a biomarker/surrogate as **predicting a clinical outcome**, it cross-checks two exact, public FDA sources:

1. **Table of Surrogate Endpoints That Were the Basis of Drug Approval or Licensure** (CDER/CBER) — the FDA's own list of surrogates that have supported approval, with the disease/use, patient population, and approval type (traditional vs accelerated).
2. **DDT Biomarker Qualification Program** — FDA's formal Drug Development Tool qualification (statutory: 21st Century Cures Act §3011 / FD&C Act §507), each entry carrying an explicit **Context of Use** statement.

If the biomarker is **not FDA-qualified for that COU**, the claim **may only surface as mechanistic/associational — never as clinical-endpoint evidence**. Qualification status + the exact COU become a **visible INFERRED trust modifier** on the belief (a `forensics.py`-shaped flag, never a verdict). It **pairs with FC-10**: FC-10 decides *what causal language is licensed*; PRD-17 decides *whether a surrogate→outcome leap is FDA-warranted for this COU*, and thereby whether the clinical-endpoint framing FC-10 would otherwise permit is actually earned.

**Capability unlocked:** Persona stops laundering a biomarker movement into a clinical-outcome claim — **legibly** (every restricted claim shows the FDA source span + COU that would be required), **conservatively** (unlisted ⇒ not-qualified ⇒ restricted), **sourced + exact-span** (the qualification is a verbatim substring of an FDA table, not a model assertion), and in **code, not model self-report** (the detector + lookup are deterministic and applicability-gated). It is the *clinical-translation* complement to PRD-08's molecular priors and PRD-12's causal-tier gate: the belief-store's surfacing decision is now cross-checked against the regulatory ground-truth for surrogate validity.

---

## 1. File ownership (disjoint)

**New (this lane — Lane 2 — creates):**
- `persona/ingest/fda_surrogate.py` — the **client**: cached fetch + parse of the two FDA sources, and the exact-span qualification matcher (`is_fda_qualified`). Pure I/O + parse; no policy. Uses `ingest.service.service()` read-only (same pattern as `openalex.py`/`sources.py`).
- `persona/memory/clinical_gate.py` — the **detector + gate**: `detect_translation_claim` (the biomarker→clinical-outcome detector, RQ-E31's subject), the `translation_modifier` orchestrator (calls the client, emits the INFERRED trust modifier, writes the ledger row, routes anchored contradictions to FC-2), and the `max_surface_class` policy. Lane-2 membrane logic; mirrors PRD-08's `memory/priors.py`.

**Edited (this lane only):**
- `persona/memory/membrane.py` — **one additive call site.** In `_harvest` (`membrane.py:89-98`) after building `rec` (and, once PRD-02 lands, inside `admit_candidate`), call `clinical_gate.translation_modifier(kg, rec)` and attach the modifier to the claim record; `project_beliefs` (`membrane.py:189-206`) appends the qualification badge to a belief line. Additive; no signature change to existing functions. Safe-degrades: if `clinical_gate` returns `not_applicable` (the common case), the membrane behaves exactly as today.

**Boundary files another lane owns — decoupled by FC-12 (PRD-17 does NOT edit them):**
- **`persona/ingest/` directory is *not* exclusively Lane 3's.** PRD-00 §3 assigns Lane 3 the *named* files `ingest/{sources.py, retraction.py}` — not the directory. `ingest/fda_surrogate.py` is a **new file**, disjoint from every named file, so there is no co-edit collision. Flagged in §2 as a boundary note (BN-1); it is a new-file claim, not a shared edit.
- `persona/synthesis/synthesizer.py` (`synthesize` `:81`; the `{"+":"increases","-":"decreases"}` map `:98`) and `persona/deliverables/document.py` (`sanitize_markdown` `:111`) — **Lane 3 owns.** They *consume* FC-12: at the FC-10 surrogate sub-gate (PRD-12 F12.3, already Lane-3-wired at `synthesizer.py`/`document.py`), Lane 3 additionally calls `clinical_gate.max_surface_class(claim_rec, modifier)` and permits clinical-endpoint phrasing only when it returns `'clinical_endpoint'`. PRD-17 provides the policy fn; Lane 3 wires the one call.
- `persona/memory/causal_tier.py` — **Lane 2 owns, but PRD-12 defines it (FC-10).** PRD-17 does **not** edit it. The refinement (FC-10's `is_surrogate` may load its list from `fda_surrogate.surrogate_table()`, and its surrogate sub-gate consults `max_surface_class`) is an **optional, additive** proposal to PRD-12's author — **CCP-17a** (§2, §6), non-blocking. PRD-12 O-4 explicitly asked for exactly this source.
- `persona/tools/science.py` — **Lane 3 owns.** Exposing `is_fda_qualified` in `science.REGISTRY` for the analyst tool-loop is **optional CCP-17b** (§2), routed to Lane 3; the membrane path works fully without it.
- `persona/ingest/service.py` — shared HTTP core, no lane's edit-set. PRD-17 **calls** `service().get_bytes/get_json` (read-only). The new host `www.fda.gov` falls under `_default` `(0.5, 2)` (`service.py:71`) with no edit required.
- `persona/api/*`, `persona/api/static/index.html` — **Lane 4 owns.** Renders the qualification badge + COU + the "down-tiered to mechanistic/associational" marker. Consumes FC-12 read side.

**Experiment + test (owning-lane convention, per PRD-05/06/08/12):** `experiments/exp_rq_e31_translation_detector.py`, `persona/tests/test_clinical_gate.py`. (PRD-00 §3 nominally files these under Lane 4; per the PRD-05/06/08/12 precedent each lane ships its own RQ experiment + unit test — flagged §6 O-5.)

`*` new file. All owned files are Lane 2.

---

## 2. FCs provided / consumed + contract change proposals

### PROVIDES — **FC-12 (Lane 2)** — CONTRACT CHANGE PROPOSAL **CCP-17** (new FC; needs master ratify + Lane 3/Lane 4 ack, §6 O-1). Next free FC after FC-11.

```python
# ---- persona/ingest/fda_surrogate.py  (the client: cached, exact-span, offline after first fetch) ----

fda_surrogate.surrogate_table(*, refresh: bool = False) -> list[dict]
    # FDA "Table of Surrogate Endpoints That Were the Basis of Drug Approval or Licensure".
    # -> [{disease_use: str, patient_population: 'Adult'|'Pediatric',
    #      surrogate_endpoint: str, approval_type: 'traditional'|'accelerated'|'both',
    #      row_text: str,                      # the verbatim concatenated cells (the grounding span source)
    #      source: 'fda_surrogate_table', url: str, retrieved: str}]

fda_surrogate.biomarker_qualifications(*, refresh: bool = False) -> list[dict]
    # FDA DDT Biomarker Qualification Program (qualified + submitted + withdrawn).
    # -> [{biomarker: str, context_of_use: str, status: 'qualified'|'submitted'|'withdrawn',
    #      qualification_number: str|None, row_text: str,
    #      source: 'fda_ddt_bqp', url: str, retrieved: str}]

fda_surrogate.is_fda_qualified(biomarker: str, *, context_of_use: str | None = None) -> dict
    # Exact-span lookup across BOTH sources; conservative default is NOT-qualified.
    # -> {qualified: bool,                     # True ONLY on a grounded match for the COU
    #     status: 'traditional_surrogate'|'accelerated_surrogate'|'ddt_qualified'
    #             |'submitted'|'not_listed',   # 'accelerated'/'submitted' are weaker than 'traditional'/'ddt_qualified'
    #     matched_biomarker: str | None,
    #     context_of_use: str | None,          # the FDA-stated COU / disease-use the match covers
    #     source: 'fda_surrogate_table'|'fda_ddt_bqp'|None,
    #     source_span: str | None,             # verbatim substring of the FDA row grounding the match
    #     url: str | None, reason: str}
    #   NOT LISTED / no COU match -> {qualified:False, status:'not_listed', source:None,
    #                                 source_span:None, reason:'not-in-fda-sources'}

# ---- persona/memory/clinical_gate.py  (the detector + gate: Lane-2 membrane logic) ----

clinical_gate.SURFACE_CLASSES = ("clinical_endpoint", "mechanistic", "associational")
    # ordered STRONGEST -> WEAKEST surfacing warrant; 'associational' is the conservative floor.

clinical_gate.detect_translation_claim(claim_rec: dict) -> dict
    # Does this claim treat a biomarker/surrogate as PREDICTING a clinical outcome?
    # (subject/object is a surrogate marker AND the counterpart is a hard clinical outcome, cued in
    #  relation/quote by predict/surrogate/reduce-risk-of/translate-to language).
    # -> {is_translation: bool, biomarker: str | None, clinical_outcome: str | None,
    #     population: str | None,              # 'Adult'|'Pediatric'|None, from the quote if stated
    #     cue: str | None, cue_offsets: [int, int] | None,   # verbatim span in claim_rec['quote']
    #     confident: bool, reason: str}
    #   APPLICABILITY GATE: is_translation=False -> the whole gate is not_applicable
    #   (distinct from 'not-qualified'): a mechanism/biomarker-only or outcome-only claim is untouched.

clinical_gate.translation_modifier(kg, claim_rec: dict, *, ops_dir=None) -> dict
    # The orchestrator: detect -> if translation, is_fda_qualified(biomarker, context_of_use=disease/pop)
    #   -> emit the INFERRED trust modifier + (gated) surface-class cap; write the ledger row.
    # -> {status: 'evaluated'|'not_applicable', provenance: 'INFERRED',
    #     surface_class: 'clinical_endpoint'|'mechanistic'|'associational'|None,  # the cap (see max_surface_class)
    #     qualified: bool, qualification: dict|None,          # the is_fda_qualified() result verbatim
    #     biomarker: str|None, clinical_outcome: str|None, context_of_use: str|None,
    #     modifier: {label: str, detail: str, severity: 'info'|'warn',
    #                source: str|None, source_span: str|None, url: str|None},
    #     gated: bool,                          # True only when RQ-E31 gate has passed (autonomous cap live)
    #     reason: str}

clinical_gate.max_surface_class(claim_rec: dict, modifier: dict) -> str
    # The cap Lane 3 / FC-10 enforce. Returns one of SURFACE_CLASSES; MONOTONE-RESTRICT ONLY:
    #   qualified-for-COU            -> 'clinical_endpoint'
    #   translation, not-qualified   -> 'mechanistic'   (a surrogate movement is a mechanism, not an outcome)
    #   not a translation claim      -> claim's existing warrant (this gate does not touch it)
    # Never returns a class STRONGER than the claim's FC-10 causal tier already licenses.
```

**Storage note (no schema CCP — recompute-on-render, PRD-08 precedent):** the modifier is **not** persisted to a new `kg.py` column. Every FDA fetch is cache-backed (`IngestService`, `service.py:74-98`) and the detector is offline+free, so Lane 4's render and the synthesis gate call `translation_modifier(kg, claim_rec)` **live**. This avoids a `kg.py` schema edit that would collide with PRD-02/PRD-12's `kg.py` changes. `# ponytail: recompute-on-render backed by the HTTP cache; no sidecar column.`

### CONSUMES
- **FC-10** (PRD-12): `causal_tier.is_surrogate`, `SURROGATES`, and the surrogate sub-gate seam (PRD-12 F12.3). PRD-17's `detect_translation_claim` reuses `causal_tier.is_surrogate` to recognize the surrogate endpoint (single source of surrogate identity — no duplicate list); `max_surface_class` is what Lane 3 calls *inside* FC-10's surrogate sub-gate.
- **PRD-02 F2.1** `membrane.admit_candidate(kg, claim_rec, source_slug, entail) -> {admit, route, calibrated_p, ...}` (same lane) — the optional attach seam. Until PRD-02 lands, PRD-17 attaches in `_harvest` (both are Lane-2-internal; no FC).
- **FC-2** `inbox.file_handoff(kind:str, dossier:dict) -> handoff_id` (own lane) — a `warn` restriction on an anchored/high-stakes clinical claim routes here; never auto-mutates the anchor.
- Shared **`ops_dir/gate_decisions.jsonl`** (PRD-00 §4, FC append-only) — the gate appends a `{gate:'membrane', decision, reason:'fda_surrogate:<status>', score, at}` row.
- Existing infra: `ingest.service.service().get_bytes/get_json` (read-only).

### CONTRACT CHANGE PROPOSALS (optional, additive, non-blocking)
- **CCP-17a (→ PRD-12 author, Lane 2 self).** FC-10's `is_surrogate` loads its marker set from `fda_surrogate.surrogate_table()` (the `surrogate_endpoint` column) instead of the hand-curated `SURROGATES` frozenset, and FC-10's surrogate sub-gate consults `max_surface_class`. **This directly answers PRD-12 O-4** ("point to a maintained source (e.g. the FDA surrogate-endpoint table)"). Non-blocking: PRD-12 keeps its curated seed until adopted; PRD-17 ships either way.
- **CCP-17b (→ Lane 3).** Register `"fda_surrogate"` in `science.REGISTRY` (`science.py:137`) + a dispatch case in `science.call` (`science.py:147`) so the analyst tool-loop can query qualification on demand. Read-only; membrane path independent of it.
- **BN-1 (boundary note, not a CCP).** `ingest/fda_surrogate.py` is a **new** file in the `ingest/` directory; PRD-00 §3 gives Lane 3 only the *named* ingest files. No co-edit. Recorded so the master can confirm the directory is not treated as wholly Lane-3.

---

## 3. Features

---

### F17.1 — FDA source client + exact-span qualification matcher (`ingest/fda_surrogate.py`)

**Problem & evidence.** The stack has **no channel to FDA surrogate/biomarker authority.** The `fda-database` skill wraps **openFDA**, which covers drugs/devices/adverse-events/approvals — it does **not** expose either the Table of Surrogate Endpoints or the DDT Biomarker Qualification Program (verified: `~/.claude/skills/fda-database/SKILL.md` — 6 drug + 9 device + 2 food endpoints, none of them surrogate/biomarker qualification). Both target sources are **published HTML tables on fda.gov**, not an API. `tools/science.py` reaches Open Targets / ClinicalTrials / PubChem but nothing regulatory-surrogate. So a confidently-written, well-cited claim that a biomarker predicts an outcome is admitted with zero check against whether the FDA agrees the surrogate is valid for that use.

Research/source: FDA **Table of Surrogate Endpoints That Were the Basis of Drug Approval or Licensure** (`https://www.fda.gov/drugs/development-resources/table-surrogate-endpoints-were-basis-drug-approval-or-licensure`; two HTML tables, Adult + Pediatric; columns *Disease or Use · Patient Population · Surrogate Endpoint · Type of Approval*). FDA **Biomarker Qualification Program** under the DDT Qualification Programs (`https://www.fda.gov/drugs/drug-development-tool-ddt-qualification-programs/biomarker-qualification-program` + the "List of Qualified Biomarkers"; statutory basis 21st Century Cures Act §3011 / FD&C Act §507; each entry states a **Context of Use**). Epistemic framing: FDA-NIH **BEST** glossary (biomarker vs surrogate vs clinical outcome; COU); Fleming TR & DeMets DL, *Ann Intern Med* 1996;125:605 ("are we being misled?"); Prentice RL, *Stat Med* 1989 (surrogate validity criteria). Cautionary controls: torcetrapib (ILLUMINATE, *NEJM* 2007 — HDL up, mortality up); ezetimibe LDL (ENHANCE, *NEJM* 2008).

**Design.**
- New `persona/ingest/fda_surrogate.py`. All fetches go through `service().get_bytes(url)` (cache-backed, rate-limited; `service.py:192`), so a cold fetch happens once and every later call is a cache hit — the demo never depends on a live fda.gov request (PRD-00 §4 "cache aggressively for the demo").
- `surrogate_table(refresh=False)` / `biomarker_qualifications(refresh=False)` — fetch the HTML, parse the table rows into the typed dicts above. Parsing: locate the `<table>`(s) and read `<tr>/<td>` cells (stdlib `html.parser` or an already-installed parser — **check what's importable before adding one**, CLAUDE.md §1; do **not** add a new dependency for a table scrape — climb the ponytail ladder). Each row stores `row_text` = the verbatim concatenated cell text, which is the **grounding span source** (the exact-span requirement: a match must be a substring of a real FDA row, never synthesized).
- **Committed snapshot fallback (demo safety).** Ship a small `persona/ingest/fixtures/fda_surrogate_snapshot.json` recorded once from the live pages; if the live fetch fails or `refresh=False` and the cache is cold, fall back to the snapshot (dated). `# ponytail: snapshot is the offline floor; refresh=True re-scrapes and re-caches.` This is the same recorded-fixture posture as PRD-03 F3.6 / PRD-08 §5.
- `is_fda_qualified(biomarker, context_of_use=None)` — normalize `biomarker` (casefold + whitespace collapse, the extractor's `_norm` discipline) and match against both source lists. A match requires the biomarker string to appear in a row's `surrogate_endpoint`/`biomarker` cell **and** (if `context_of_use` given) a token-overlap match against the row's `disease_use`/`context_of_use` — so LDL-C qualified for *hyperlipidemia* does **not** license an LDL-C→*cancer-survival* claim (COU-specificity is the whole point). Return the strongest matching status (`traditional_surrogate` > `ddt_qualified` > `accelerated_surrogate` > `submitted` > `not_listed`), the `source_span` (the verbatim row substring), and the `url`. **No match ⇒ `{qualified:False, status:'not_listed'}` — the conservative default.**

**Epistemic guardrails.** Sourced + exact-span: a `qualified:True` is always backed by a `source_span` that is a verbatim substring of a fetched FDA row + the source URL — never a model claim. Conservative default: unlisted ⇒ not-qualified (the safe direction — an un-listed surrogate is treated as un-validated). COU-specific: qualification for one disease/population never transfers to another. Deterministic + offline-after-cache; no model call, no budget spend (a `forensics.py`-class check).

**Required experiment.** Trivial — a deterministic table lookup over published FDA rows; correctness is a fixture-exact string/COU match (unit-tested F17.4). The *load-bearing* uncertainty is upstream (which claims are translation claims) → RQ-E31 (F17.3). Per the task brief: "else trivial lookup."

**Acceptance + ONE runnable check.** With the committed snapshot: `is_fda_qualified("LDL-C", context_of_use="primary hyperlipidemia")["qualified"] is True` and carries a `source_span` that is a verbatim substring of a snapshot row; `is_fda_qualified("LDL-C", context_of_use="pancreatic cancer survival")["status"] == "not_listed"`; `is_fda_qualified("some novel unlisted marker")["qualified"] is False`. Runnable: `pytest persona/tests/test_clinical_gate.py::test_is_fda_qualified_is_cou_specific_and_span_grounded`.

**Effort** M · **Deps** existing `ingest.service`.

---

### F17.2 — Translation detector + trust-modifier gate (`memory/clinical_gate.py`; membrane seam)

**Problem & evidence.** Even with the FDA client, nothing decides *which* beliefs are clinical-translation claims (most are not — a mechanism claim, a descriptive claim, or a biomarker-only claim must be left untouched; applying the gate to them is the out-of-domain false positive PRD-00 §2 forbids), and nothing turns "not FDA-qualified" into a *surfacing restriction + visible trust modifier*. The concrete leak the gate closes: `synthesizer.py:98` maps every `effect_sign` to `increases`/`decreases` and `synthesize` (`:81`) hands claims to the writer, which can freely narrate a surrogate movement as an outcome — with no check that the surrogate is FDA-validated for that outcome. FC-10 (PRD-12) blocks *causal verbs* and coarsely flags surrogate objects, but has no notion of **COU-specific FDA qualification** — it cannot tell "LDL-C→CV-risk in hyperlipidemia (qualified)" from "novel-marker→outcome (not qualified)."

**Design.**
- New `persona/memory/clinical_gate.py`.
- `detect_translation_claim(claim_rec)` — the detector (RQ-E31's subject). A claim is a translation claim iff **one endpoint is a surrogate/biomarker** (reuse `causal_tier.is_surrogate` from FC-10 — single source of surrogate identity, no duplicate list) **and** the other endpoint reads as a **hard clinical outcome** (mortality, MACE, disease incidence, survival, cure — a small clinical-outcome lexicon) **and** the `relation`/`quote` carries a *prediction/translation* cue (`predicts`, `is a surrogate for`, `reduces risk of`, `translates to`, `associated with lower ... mortality`, or a bare surrogate→outcome directional claim). Locate the cue as a **verbatim span in `claim_rec['quote']`** (the span `extract.py` already validated), storing `cue`/`cue_offsets` — exact-span grounding. **No surrogate endpoint, or no clinical-outcome counterpart ⇒ `is_translation=False` ⇒ the gate is `not_applicable`** (first-class, distinct from not-qualified). A bare biomarker-change claim ("drug lowers LDL-C", no outcome) is *not* a translation claim — it is already correctly scoped.
- `translation_modifier(kg, claim_rec, ops_dir=None)` — the orchestrator. `detect_translation_claim`; if `not is_translation` ⇒ `{status:'not_applicable', surface_class:None, ...}`. Else derive the COU from the claim's `object`/`population`/`quote` and call `fda_surrogate.is_fda_qualified(biomarker, context_of_use=...)`. Build the INFERRED modifier: `qualified` ⇒ `severity:'info'`, `label:'FDA-qualified surrogate'`, `detail` = the COU + source_span; `not qualified` ⇒ `severity:'warn'`, `label:'surrogate not FDA-qualified for this outcome'`, `detail` naming the required-but-absent COU. Compute `surface_class = max_surface_class(claim_rec, modifier)`. Hard-set `provenance='INFERRED'`. Append a `gate_decisions.jsonl` row `{gate:'membrane', decision: 'admit' if qualified else 'skip', reason:f'fda_surrogate:{status}', score, at}`.
- `max_surface_class(claim_rec, modifier)` — the cap Lane 3/FC-10 enforce (§2). Monotone-restrict only: qualified-for-COU ⇒ `clinical_endpoint`; translation + not-qualified ⇒ `mechanistic`; never stronger than FC-10's causal tier already licenses. **Gated:** `translation_modifier` sets `gated=True` only when `ops_dir/fda_surrogate_gate.json` `passed=True` (RQ-E31 has passed); until then the modifier is **advisory** (attached + rendered, but Lane 3 does not enforce the cap — it renders the badge only).
- **Membrane seam (`membrane.py`, additive):** in `_harvest`, after building each `rec`, `m = clinical_gate.translation_modifier(kg, rec)`; attach `rec['clinical_gate'] = m` (carried to render; no KG column). A `severity:'warn'` on an **anchored/high-stakes** clinical claim ⇒ `inbox.file_handoff("surrogate_not_qualified", dossier)` (never auto-mutates the anchor — Balanced, PRD-00 §1). Non-anchored ⇒ modifier attached + ledger row; the surfacing cap enforced downstream by Lane 3 once `gated`.
- **Lane 3 wiring (documented here, executed by Lane 3):** at FC-10's surrogate sub-gate (PRD-12 F12.3, `synthesizer.py`/`document.py:sanitize_markdown` `:111`), call `sc = clinical_gate.max_surface_class(claim_rec, m)`; permit clinical-endpoint phrasing only if `sc == 'clinical_endpoint'`, else the writer scopes to the surrogate ("lowers LDL-C", not "prevents heart attacks") and FC-10's `downgrade` handles the verb. Belt-and-suspenders with FC-10: FC-10 gates the *verb strength*, PRD-17 gates the *endpoint class*.

**Epistemic guardrails.** Applicability gate explicit + first-class (`not_applicable` ≠ `not_qualified` ≠ `qualified`). The modifier is **INFERRED, never a verdict** — it restricts *surfacing framing*, it never rejects the belief, never lowers a confidence number, never anchors. Monotone-restrict: the gate can only ever *weaken* a claim's surface class (clinical→mechanistic), never manufacture a clinical-endpoint claim — so a detector error is safe-by-direction (a false restriction costs expressiveness, never truth), the same asymmetry PRD-12's `downgrade` relies on. Conservative default (unlisted ⇒ restricted). Anchored/high-stakes ⇒ human, never auto.

**Required experiment.** **RQ-E31** (F17.3) — precision of `detect_translation_claim` before the gate autonomously down-tiers surfacing. Load-bearing (it decides which claims are restricted), so it gets the full loop; the FDA lookup itself is trivial (F17.1).

**Acceptance + ONE runnable check.** (a) a mechanism claim (no surrogate, or no outcome) ⇒ `translation_modifier(...).status == 'not_applicable'` and `max_surface_class` leaves the claim's warrant untouched; (b) a "novel-marker predicts mortality" claim (surrogate not in FDA sources) ⇒ `status=='evaluated'`, `qualified is False`, `surface_class=='mechanistic'`, a `warn` modifier with the required-COU detail; (c) an "LDL-C predicts CV events in hyperlipidemia" claim ⇒ `qualified is True`, `surface_class=='clinical_endpoint'`, `severity:'info'`; (d) with the gate file absent, (b)'s modifier is present but `gated is False` (advisory). Runnable: `pytest persona/tests/test_clinical_gate.py::test_gate_downtiers_unqualified_and_is_applicability_gated`.

**Effort** M · **Deps** F17.1, FC-10 `is_surrogate`, existing `membrane`.

---

### F17.3 — Precision of the biomarker→clinical-outcome detector (RQ-E31)

**Problem & evidence.** `detect_translation_claim` *drives the restriction* — it decides which beliefs get their surface class capped from `clinical_endpoint` to `mechanistic`. It must be validated before it autonomously down-tiers, because the failure mode is real in both directions: a **false positive** (flagging a claim that is *not* a surrogate→outcome translation) needlessly strangles a legitimate clinical claim into mechanistic framing; a **false negative** (missing a real translation claim) lets an un-qualified surrogate→outcome leap surface as clinical-endpoint evidence — the exact harm the gate exists to prevent. The task brief names this as the required experiment ("precision of the biomarker→clinical-outcome-claim detector vs a small labeled set; gate before it down-tiers; else trivial lookup"). This is the pre-registered go/no-go before the cap enforces autonomously.

**Design.** `experiments/exp_rq_e31_translation_detector.py`, results → `results/FINDINGS.md#RQ-E31`.
- **Labeled set (HUMAN labels — never synthesized, CLAUDE.md §7).** ~120–150 claim spans sampled from Persona's own `sources/*/claims.jsonl`, each hand-labeled by a human as *translation* (surrogate→hard-outcome) vs *not-translation* (mechanism-only, biomarker-only, outcome-only, descriptive). Include the classic controls as positives with a *known* FDA status: LDL-C→CV-risk in hyperlipidemia (qualified), HbA1c→microvascular in diabetes, plus un-qualified over-reaches (a novel biomarker→mortality claim; a surrogate applied to a disease outside its COU — the torcetrapib/ezetimibe-shaped trap). If no human annotation exists at build time, RQ-E31 **blocks** the cap (advisory-only) — the gate does not go autonomous on synthetic labels.
- **Hypothesis + metric.** *The deterministic surrogate+outcome+cue detector, defaulting to not-a-translation when the surrogate or the outcome cue is absent, identifies biomarker→clinical-outcome claims with high precision.* Two numbers:
  - **`detector_precision`** = P(claim is truly a translation claim | detector says translation) — of claims the detector down-tiers, how many the human agrees are surrogate→outcome. The metric that decides whether autonomous restriction is acceptable (don't strangle legitimate claims).
  - **`false_restriction_rate`** = fraction of genuinely non-translation control claims (mechanism/biomarker-only) the detector wrongly flags — the safety metric on the expressiveness side.
- **Seeds ≥ 20.** Bootstrap-resample the labeled set 20× (stratified by gold label); report both metrics as **mean ± 95% CI**. Deterministic detector → the seed varies the resample (the honest small-set sampling uncertainty).
- **Go/no-go gate (pre-registered):** mean **`detector_precision` ≥ 0.80** AND upper-95%-CI **`false_restriction_rate` ≤ 0.05**. Pass ⇒ flip `ops_dir/fda_surrogate_gate.json` `passed=True`; the surface-class cap enforces autonomously (Lane 3 restricts). Fail ⇒ the modifier renders as an **advisory badge only** and the cap is human-review, and the reversal is logged (matching how PRD-08/12 hold load-bearing autonomy behind their RQ gates). Recall is reported but *not* gated — the conservative posture (over-detect ⇒ over-restrict ⇒ safe-by-direction) makes precision the number that governs whether autonomous restriction is tolerable.

**Epistemic guardrails.** Pre-registered gate (stated before results); no tuning-to-pass — if the cue/lexicon detector can't clear the precision bar, that is a logged reversal (CLAUDE.md §2) and the fallback is an LLM-assisted detector that still must ground its cue to a verbatim `quote` span, re-gated. Labels are human; the experiment never grades against model output. The FDA *lookup* is not part of this experiment (it is a deterministic fixture match, F17.1/F17.4) — only the *detector* is under test.

**Acceptance + ONE runnable check.** The script runs offline on the committed labeled fixture, prints the mean±CI table + the gate boolean, and appends to `results/FINDINGS.md#RQ-E31`. Runnable: `pytest persona/tests/test_clinical_gate.py::test_rq_e31_detector_precision_under_gate` (asserts precision ≥ 0.80 and false-restriction upper-CI ≤ 0.05 on the fixture, ≥20 resamples, offline).

**Effort** M · **Deps** F17.2; human-labeled fixture.

---

## 4. Sequencing

**Milestone 0 (hour 1 — land FC-12 stubs so Lane 3/Lane 4 build against them):** ship `ingest/fda_surrogate.py` + `memory/clinical_gate.py` with real `SURFACE_CLASSES` and typed stubs — `is_fda_qualified(...)` → `{qualified:False, status:'not_listed', source:None, source_span:None, reason:'stub'}`; `detect_translation_claim(...)` → `{is_translation:False, ..., reason:'stub'}`; `translation_modifier(...)` → `{status:'not_applicable', provenance:'INFERRED', surface_class:None, gated:False, ...}`; `max_surface_class(...)` → the claim's existing warrant (no-op). Safe-degrade by construction: with stubs, the membrane behaves exactly as today. File **CCP-17** (FC-12) + **CCP-17a** (FC-10 source) + **CCP-17b** (science.REGISTRY) + **BN-1** in the HANDOFF dispatch log.

Then: **F17.1** (client + matcher — record the FDA snapshot, build the exact-span lookup with its unit tests) → **F17.2** (detector + gate + membrane seam; wire the `fda_surrogate_gate.json` load, default advisory) → **F17.3 / RQ-E31** (validate the detector on the human-labeled set; the gate must pass before the cap enforces). Rationale: nothing restricts surfacing until the detector clears RQ-E31; the FDA lookup is trusted immediately (deterministic fixture match), the *detection* is what gates autonomy.

---

## 5. Test plan

**Unit (pure, offline — stub `service().get_bytes` with the committed snapshot; no live network, no model, no Docker):** `persona/tests/test_clinical_gate.py` —
- **F17.1** `test_is_fda_qualified_is_cou_specific_and_span_grounded` — LDL-C qualified for hyperlipidemia (span-grounded) but `not_listed` for an out-of-COU outcome; an unlisted marker ⇒ `not_listed`; every `qualified:True` carries a `source_span` that is a verbatim substring of a snapshot row.
- **F17.2 applicability gate (the correctness boundary):** a mechanism-only claim, a biomarker-only claim, and an outcome-only claim each ⇒ `not_applicable` — *distinct from* `not_qualified`.
- **F17.2 monotone-restrict discipline:** `max_surface_class` never returns a class stronger than the claim's FC-10 tier; an unqualified translation claim caps to `mechanistic`; a qualified one to `clinical_endpoint`; the gate never raises a class.
- **F17.2 gate-guard:** with `fda_surrogate_gate.json` absent, the modifier is attached but `gated is False` (advisory); an anchored unqualified clinical claim files an FC-2 handoff and does **not** mutate the anchor (reuse the no-mutation spy pattern from PRD-02/08 tests).
- **Ledger:** an evaluated translation claim appends exactly one `{gate:'membrane', reason:'fda_surrogate:<status>'}` row to `gate_decisions.jsonl` (append-only; never edits another lane's rows).

**Experiment oracle (seeded ≥20, offline, human labels):** `exp_rq_e31_translation_detector.py` — `detector_precision` ≥ 0.80 (mean) and `false_restriction_rate` upper-CI ≤ 0.05 over 20 stratified resamples; gate boolean printed + logged to `results/FINDINGS.md#RQ-E31`.

**Cross-lane (Lane 3, after F17.2 + RQ-E31 pass):** a synthesis over a community containing an un-qualified surrogate→outcome claim must not contain a clinical-endpoint framing — Lane 3 adds a `max_surface_class(claim_rec, m) != 'clinical_endpoint'` assertion at its FC-10 surrogate sub-gate seam. **Browser smoke (Lane 4, `PERSONA_WORKERS=0`):** a belief card renders the FDA qualification badge + COU and a distinct "down-tiered to mechanistic" marker.

**Regression guard:** with the two new files at their Milestone-0 stubs (or the gate off), the existing membrane + integrity suite passes unchanged — PRD-17 is strictly additive and safe-degrading.

---

## 6. Open questions

- **O-1 (CCP-17 / FC-12 — blocks Lane 3 enforcement + Lane 4 render).** Ratify the new cross-lane interface (`fda_surrogate.*` + `clinical_gate.*` above) as **FC-12** (Lane 2 provides; Lane 3 = surface-class enforcement at the FC-10 seam, Lane 4 = badge/COU render). Lane 3 must ack the `max_surface_class` call inside FC-10's surrogate sub-gate; Lane 4 must ack the read-side modifier. **Blocks nothing until enforcement** — the modifier ships advisory-only until RQ-E31 passes, so Lane 4 can render the badge from hour 1 against the FC-12 stub.
- **O-2 (FDA source parsing — build-time verification, CLAUDE.md §1).** The two sources are HTML tables whose exact structure must be verified against a live fetch before wiring the parser (a one-off scratch check, not a seeded experiment — same stance as PRD-08 O-2 for the GTEx id form). Confirm it's acceptable to record the committed snapshot once from the live pages and treat it as the offline floor. **Also:** the Table of Surrogate Endpoints is periodically re-published — confirm a `refresh=True` re-scrape cadence (e.g. quarterly) vs pinning the snapshot for the demo.
- **O-3 (COU-match strictness).** `is_fda_qualified` matches the claim's disease/population against the FDA row's `disease_use`/`context_of_use` by token overlap. Too strict ⇒ misses a valid qualification (a false restriction); too loose ⇒ licenses an out-of-COU leap (the dangerous direction). Proposed default: **conservative (require disease-term overlap; population must not conflict)** — err toward `not_listed`. Confirm the strictness, or specify a controlled-vocabulary map (MeSH/EFO) for disease-term matching.
- **O-4 (CCP-17a — FDA table as FC-10's `SURROGATES` source).** Adopt `fda_surrogate.surrogate_table()` as the maintained source for PRD-12's `is_surrogate`/`SURROGATES` (directly answers PRD-12 O-4)? Routed to the PRD-12 author (same lane). Non-blocking — PRD-12 keeps its curated seed until adopted.
- **O-5 (experiment/test file ownership).** PRD-00 §3 files `experiments/*`/`tests/*` under Lane 4, but PRD-05/06/08/12 have each lane ship its own RQ experiment + unit test. PRD-17 follows that precedent (`experiments/exp_rq_e31_translation_detector.py`, `persona/tests/test_clinical_gate.py`). Confirm, or route the experiment file through Lane 4.
- **O-6 (RQ id).** Assigned **RQ-E31** — RQ-E30 is already claimed by PRD-16 (`experiments/exp_rq_e30_oracle_controls.py`), so E31 is the next free number despite PRD-00 §6 listing the ceiling as E29. Register RQ-E31 in `docs/RESEARCH_QUALITY_PROGRAM.md`.
- **O-7 (BN-1 — ingest/ directory boundary).** Confirm a new `ingest/fda_surrogate.py` (Lane 2) is fine given PRD-00 §3 lists only *named* ingest files under Lane 3 (no directory-level ownership). Alternative if the master prefers strict directory ownership: relocate the client into `persona/memory/fda_surrogate.py` (fully Lane-2, matching PRD-08's `memory/priors.py` which did its own I/O) — a one-path change, no signature impact.
