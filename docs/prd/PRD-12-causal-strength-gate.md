# PRD-12 — Causal-strength typing gate

> **Owner lane:** 2 (Membrane & belief core) · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (classify + gate autonomously; the gate only *downgrades* language — it never anchors, never upgrades a tier without a span) · **Depends on:** existing `reading/extract.py` verbatim-`quote` contract (Lane 1, unchanged), `memory/kg.py` `add_claim`/`beliefs`/`claims_in` (Lane 2 self), `memory/membrane.py` `_harvest` (Lane 2 self). **Consumed by** Lane 3 (`synthesis/synthesizer.py`, `deliverables/document.py`) and Lane 4 (render), via new **FC-10**.

---

## 0. Summary + capability unlocked

Persona today extracts a claim's `(subject, relation, object, effect_sign)` with a verbatim `quote` (`reading/extract.py:16-56`) and the auditor coarsely tags each claim `kind ∈ {causal, descriptive, mechanistic, correlational}` (`agents/audit.py:36`) — but **nothing in the belief pipeline records *how strongly the claim's own source warrants a causal reading*, and nothing stops a synthesized deliverable from re-narrating a bare association as cause.** The leak is concrete: the synthesizer maps every `effect_sign` to the causal-flavored verbs `"increases"/"decreases"` before handing claims to the writer (`synthesis/synthesizer.py:98,103`), and the writer produces free prose (`synthesizer.py:110-119`) with no downstream check that an observational claim stays associational. This is exactly the failure `CONTINUATION_HANDOFF §6` flags ("transcriptomic ≠ causal") and `IDEAS_BACKLOG #20` asks to close.

PRD-12 adds a **causal-strength tier** to every claim, grounded to an exact source span, and turns it into a **hard language gate**:

1. **Classify** each claim's causal warrant into an ordered tier — `rct` › `mendelian_randomization` › `mechanistic` › `observational` › `correlational` — from a cue located **verbatim inside the claim's own `quote`** (the span `extract.py` already validated). No cue → **default to the weakest tier** (`correlational`). Never upgrade a tier without a grounding span.
2. **Store** `causal_tier` (+ the cue span) on the `Claim` node (`kg.add_claim`) and surface it on every read (`kg.beliefs`, `kg.claims_in`).
3. **Gate language**: a claim whose tier is not causal-*licensed* (`observational`/`correlational`) may never be surfaced with causal verbs ("causes", "leads to", "reduces", "raises"). Lane 3's synthesizer and deliverable writer consume a pure `check_language` gate (FC-10) that flags any causal verb resting on an unlicensed tier, and downgrade the phrasing to associational ("associated with", "linked to").
4. **Surrogate-endpoint sub-gate**: even a causal-licensed tier does not license *hard-outcome* language when the claim's `object` is a known **surrogate marker** (e.g. LDL-C, HbA1c) — pairs with PRD-06 (executable MR is the thing that *can* upgrade a surrogate association to a causal verdict).

**Capability unlocked:** Persona stops laundering association into causation in its own written output — the single most common way a literature synthesizer misleads a scientist — and does it *legibly* (every claim carries a visible tier + the exact cue span that earned it), *conservatively* (weakest-by-default, span-required to upgrade), and in **code, not model self-report** (the tier is a deterministic classification over a verbatim span, applicability-gated like `forensics.py`). It is the belief-core complement to PRD-06: MR *earns* a causal tier by running the test; this gate *enforces* that unearned causal tiers never reach prose.

---

## 1. File ownership (disjoint)

**New (this lane creates):**
- `persona/memory/causal_tier.py` — the classifier + the language gate + the tier vocabulary. Pure, importable, offline, no model call on the default path (deterministic cue lexicon over a verbatim span). New Lane-2 file, consistent with the `calibrate.py*`/`conflicts.py*` precedent in PRD-00 §3.

**Edited (this lane only):**
- `persona/memory/kg.py` — `add_claim` stores `causal_tier` + `causal_cue` on the `Claim` node (additive `ON CREATE SET` fields; node schema doc at `kg.py:13-15` extended); `beliefs` (`kg.py:204`) and `claims_in` (`kg.py:267`) return the two fields (additive columns); new read `causal_tier(claim_id)`.
- `persona/memory/membrane.py` — `_harvest` (`membrane.py:75-99`) classifies each `rec` via `causal_tier.classify(rec["relation"], rec["quote"])` **before** `kg.add_claim` (`membrane.py:96`) and passes the tier in; `project_beliefs` (`membrane.py:189`) annotates each projected belief with its tier badge (arrows already avoid causal verbs — the badge is additive legibility).

**Boundary files another lane owns — decoupled by FC-10, NOT edited here:**
- `persona/reading/extract.py`, `persona/reading/reader.py` — **Lane 1 owns.** *No edit required.* The classifier runs at harvest over the `quote` that `reader.py:178` already persists to `claims.jsonl` and that `extract.py:134` already gate-validated as verbatim. An **optional** precision upgrade (Lane 1 emits a `causal_cue` span at extraction time, seeing the full text) is flagged as **CCP-12a** (§2, §6) — non-blocking; Lane 2 ships without it.
- `persona/synthesis/synthesizer.py`, `persona/deliverables/document.py` — **Lane 3 owns.** They *consume* FC-10: `synthesizer.py:110` passes each claim's tier into the writer prompt, and post-generates through `causal_tier.check_language(...)` at the `sanitize_markdown` seam (`document.py:111`, imported at `synthesizer.py:131`). PRD-12 provides the gate; Lane 3 wires it.
- `persona/api/*`, `persona/api/static/index.html` — **Lane 4 owns.** Renders the tier badge + a "language-downgraded" marker. Consumes FC-10 read side.

**Experiment + test** (owning-lane convention, per PRD-05/06): `experiments/exp_rq_e26_causal_tier.py`, `persona/tests/test_causal_tier.py`. (PRD-00 §3 nominally files `experiments/*`+`tests/*` under Lane 4; per the PRD-05/06 precedent each lane ships its own RQ experiment + unit test — flagged in §6.)

---

## 2. FCs provided / consumed

### PROVIDES — **FC-10 (Lane 2), new `persona/memory/causal_tier.py` + `persona/memory/kg.py`** — CONTRACT CHANGE PROPOSAL CCP-12 (new FC; needs master ratify + Lane 3/Lane 4 ack, §6)

```
# --- vocabulary (module constants) ---
causal_tier.TIERS = ("rct", "mendelian_randomization", "mechanistic", "observational", "correlational")
                   # ordered STRONGEST -> WEAKEST. index() gives strength rank; last = default.
causal_tier.LICENSED = frozenset({"rct", "mendelian_randomization", "mechanistic"})
                   # tiers permitted to use causal verbs. observational/correlational are NOT.

# --- classify one claim from its verbatim span (deterministic default path) ---
causal_tier.classify(relation: str, quote: str, *, full_text: str | None = None,
                     qualifiers: dict | None = None, cue_hint: str | None = None) -> dict
# -> {tier: str,                    # one of TIERS; 'correlational' when no grounded cue
#     cue: str | None,              # the verbatim substring of `quote` that set the tier (None if defaulted)
#     cue_offsets: [int, int] | None,   # [start, end) char offsets of `cue` within `quote`
#     licensed_causal: bool,        # tier in LICENSED
#     confident: bool,              # a cue was grounded (not defaulted)
#     reason: str}                  # e.g. 'cue:randomized', 'default-weakest:no-cue', 'ambiguous->weakest'

# --- storage read side (kg.py) ---
kg.causal_tier(claim_id: str) -> {tier: str, cue: str | None, licensed_causal: bool}
# kg.beliefs(...) and kg.claims_in(...) each row additionally carries: causal_tier, causal_cue

# --- the language gate (what Lane 3 / Lane 4 call) ---
causal_tier.check_language(text: str, max_tier: str) -> list  # -> [{span, offset:[int,int], cue}]
# For prose `text` that rests on claims whose STRONGEST supporting tier is `max_tier`:
# if max_tier not in LICENSED, return every causal-verb span found (empty list == clean / licensed).
causal_tier.downgrade(text: str, violations: list) -> str
# Rewrite flagged causal verbs to their associational form ("causes"->"is associated with"), deterministic map.

# --- surrogate sub-gate ---
causal_tier.is_surrogate(entity: str) -> bool          # object is a known surrogate marker
causal_tier.SURROGATES: frozenset[str]                 # curated marker set (LDL-C, HbA1c, CRP, viral load, ...)
```

**Storage note (no CCP — inside Lane-2-owned `kg.py`):** `add_claim` adds `c.causal_tier`/`c.causal_cue` to the existing `ON CREATE SET` block (`kg.py:111-114`). Fields are set on create only, like `provenance`/`anchored` — an anchored belief's tier is pinned (a human/tested sign-off already outranks a cue). Re-observation from a second lab does **not** upgrade a tier; tier is a property of *a claim's source warrant*, so the strongest tier across a claim's supporting sources is computed at read time by `kg.beliefs`/`claims_in` (MAX over `SUPPORTED_BY` tiers), mirroring how `independent_source_count` is recomputed (`kg.py:125-131`).

### CONSUMES
- Existing `extract.py` verbatim-`quote` guarantee (`extract.py:115-148`) — the classifier trusts that `quote` is a verbatim span, so a cue found inside it is transitively grounded in the source. No new consumption contract.
- Nothing from FC-1…FC-9.

### CONTRACT CHANGE PROPOSAL CCP-12a (optional, Lane 1 `reading/extract.py` + `reading/reader.py`)
Add an optional `causal_cue` property to `EXTRACT_TOOL` (`extract.py:28-49`) — "the verbatim sentence fragment that signals the study design / causal warrant (e.g. 'randomized, double-blind'; 'genetically predicted'; 'associated with')" — validated verbatim exactly like `qual_source` (`extract.py:88`), persisted by `reader.py:175-180`. When present, `classify(cue_hint=...)` uses the LLM-located cue (higher recall on paraphrased designs); when absent, the deterministic quote scan runs. **Backward-compatible and non-blocking:** PRD-12 ships and passes RQ-E26 without it; CCP-12a is a precision upgrade only.

---

## 3. Features

---

### F12.1 — Causal-tier classifier (`memory/causal_tier.py`)

**Problem & evidence.** No field in the claim record encodes causal warrant; the closest is the auditor's coarse `kind` (`audit.py:36`), which is model-emitted, not span-grounded, and not stored on the belief. The extractor stores a verbatim `quote` (`extract.py:34`, gate at `extract.py:134`) but never asks "what kind of study is this claim's warrant?" Research/source: the association-vs-causation hierarchy is standard — Hill's criteria (Hill AB, *Proc R Soc Med* 1965), the **OCEBM Levels of Evidence 2** (RCT › cohort › case-control), and Mendelian randomization as a distinct genetic-instrument tier (Davey Smith & Ebrahim, *Int J Epidemiol* 2003;32:1). The cue lexicon is drawn from the design terms these frameworks name (randomized/double-blind; Mendelian randomization/instrumental variable/genetically predicted; knockout/knockdown/in vitro/in vivo perturbation; prospective cohort/case-control/adjusted for; associated/correlated).

**Design.**
- `TIERS`, `LICENSED`, `SURROGATES` module constants (FC-10). Tier order = warrant strength; `correlational` is last = the conservative default.
- `classify(relation, quote, *, full_text=None, qualifiers=None, cue_hint=None) -> dict`:
  - Normalize `quote` with the extractor's own `_norm` discipline (casefold + NFKC + whitespace collapse — reuse the pattern at `extract.py:111`, not the private fn).
  - Scan for tier cues **strongest-first**; the first tier whose cue lexicon matches a substring wins, and `cue`/`cue_offsets` record that exact substring. Because the cue is a substring of the already-verbatim `quote`, it is transitively an exact source span (the epistemic requirement).
  - `full_text` (optional, the source `clean.md`) widens the scan window when the quote alone is cue-poor; still only a span *inside stored text* may set a tier.
  - `cue_hint` (CCP-12a): if the extractor supplied a `causal_cue`, prefer it — but only after re-validating it is verbatim in `quote`/`full_text` (never trust an ungrounded hint).
  - **No match → `tier='correlational', cue=None, confident=False, reason='default-weakest:no-cue'`.** A directional `effect_sign` alone (e.g. `+`) is *not* a causal cue — direction ≠ warrant.
  - Ambiguity guard: if cues for two non-adjacent tiers both match (e.g. "randomized" and "observational cohort" in one quote), return the **weaker** with `reason='ambiguous->weakest'` — never guess the stronger.
- Deterministic, offline, no API key, no budget spend (unlike `synthesizer.py`/`extract.py`). This is a `forensics.py`-class check: "the arithmetic is deterministic, unit-tested, and impossible to argue with" (`forensics.py:4`).

**Epistemic guardrails.** Weakest-by-default; a tier is only raised above `correlational` by a located span. `confident=False` is a first-class distinct state (a defaulted tier is *not* the same as an observed-correlational tier — a downstream renderer can show "no design cue found" honestly). Never a model self-report of causal strength; the classification is code over a verbatim span. Never upgrades an anchored/HUMAN_CONFIRMED belief (those already outrank cue evidence).

**Required experiment.** **RQ-E26** (F12.4) — precision of tier classification vs a human-labeled set; gate before the classifier drives the language gate. Load-bearing (it decides what language is permitted), so it gets the full loop.

**Acceptance + ONE runnable check.** (a) `classify("increases", "In a randomized, double-blind trial, drug X reduced events")` → `tier='rct'`, `cue` is the verbatim "randomized, double-blind" substring with correct offsets, `licensed_causal=True`; (b) `classify("correlates_with", "X was associated with Y in a cohort")` → `tier ∈ {'observational','correlational'}`, `licensed_causal=False`; (c) `classify("increases", "X was higher in cases")` (no design cue) → `tier='correlational'`, `confident=False`. Runnable: `pytest persona/tests/test_causal_tier.py::test_classify_grounds_tier_to_span_and_defaults_weakest`.

**Effort** M · **Deps** none (pure).

---

### F12.2 — Store + surface `causal_tier` (`memory/kg.py`, `memory/membrane.py`)

**Problem & evidence.** The tier is worthless unless it rides with the belief through the graph and out to every read the synthesizer uses (`kg.claims_in` at `synthesizer.py:87`; `kg.beliefs` at `membrane.py:118`). The `Claim` node schema (`kg.py:13-15`) has no causal field; `add_claim` (`kg.py:89-132`) sets provenance/anchored/confidence on create but no tier; the harvest loop (`membrane.py:89-98`) ingests each `rec` without classifying it.

**Design.**
- `membrane._harvest`: for each `rec` before `kg.add_claim` (`membrane.py:96`), call `t = causal_tier.classify(rec.get("relation",""), rec.get("quote",""))` and pass `causal_tier=t["tier"], causal_cue=t["cue"]` into `add_claim`. (The `quote` is present in `claims.jsonl` per `reader.py:178`; classification is offline + free, so it adds no budget cost to harvest.)
- `kg.add_claim`: extend the params dict + `ON CREATE SET` (`kg.py:101-114`) with `c.causal_tier=$ctier, c.causal_cue=$ccue`. Set-on-create only (pinned like `provenance`). Store the cue per **source** on the `SUPPORTED_BY` edge (`r.causal_tier`, `r.causal_cue`) so a claim converged from an RCT source and a cohort source can compute a MAX tier at read time.
- `kg.beliefs` (`kg.py:204-215`) + `kg.claims_in` (`kg.py:267`): add a subquery that returns `strongest_tier = ` the min-index (strongest) tier across the claim's `SUPPORTED_BY` edges, plus its cue; append `causal_tier`, `causal_cue` columns.
- `kg.causal_tier(claim_id)`: thin read returning `{tier, cue, licensed_causal}`.
- `membrane.project_beliefs` (`membrane.py:199-204`): append a small tier badge to each belief line (e.g. `· obs` / `· RCT`), additive to the existing arrow/anchor legend — beliefs.md already uses arrows (`↑↓∅`), not causal verbs, so it does not itself leak; the badge is legibility.

**Epistemic guardrails.** Read-time MAX-tier means a claim is credited the strongest warrant any of its *independent* sources actually supplies — never inflated by echo (same discipline as `independent_source_count`, `kg.py:128`). Anchored beliefs keep their pinned tier. A `null`/defaulted tier renders as "correlational (no cue)", never blank-implying-strong.

**Required experiment.** Trivial — storage plumbing over F12.1's validated classifier; the correctness that matters (the classification) is gated by RQ-E26.

**Acceptance + ONE runnable check.** After harvesting a source whose claim quote contains "randomized controlled trial", `kg.beliefs(...)[i]["causal_tier"] == "rct"` and `kg.causal_tier(cid)["licensed_causal"] is True`; a cohort-only claim reads `licensed_causal False`. Runnable: `pytest persona/tests/test_causal_tier.py::test_kg_stores_and_reads_tier` (FalkorDB fixture or stubbed `_q`, mirroring existing kg tests).

**Effort** M · **Deps** F12.1, existing `kg`/`membrane`.

---

### F12.3 — Language gate + surrogate sub-gate (`memory/causal_tier.py`; consumed by Lane 3)

**Problem & evidence.** The concrete leak: `synthesizer.py:98` maps `effect_sign` to `"increases"/"decreases"` and the writer (`synthesizer.py:110-119`) emits free causal prose with no post-check; `deliverables/document.py:sanitize_markdown` (`document.py:111`) is the last mutation point before a note is saved and currently strips only HTML, not causal over-claiming. `BACKLOG #20` and `CONTINUATION_HANDOFF §6` name this exact hazard. Research/source: causal-language-strength scales are established — Haber N, Wieten SE, Rohrer JM, et al., "Causal and associational language in observational health research: a systematic evaluation," *Am J Epidemiol* 2022;191(12):2084-2097 (a hand-coded 0–5 causal-language ladder over ~1000 observational studies — the rubric + a real gold source for RQ-E26). Surrogate-endpoint caution: Fleming TR & DeMets DL, "Surrogate end points in clinical trials: are we being misled?" *Ann Intern Med* 1996;125:605; Prentice RL, *Stat Med* 1989 (surrogate validity criteria).

**Design.**
- `check_language(text, max_tier) -> [violations]`: if `max_tier in LICENSED`, return `[]` (causal language permitted). Else scan `text` for causal-verb spans from a fixed lexicon (`causes`, `leads to`, `results in`, `induces`, `drives`, `reduces`, `raises`, `prevents`, plus the `synthesizer.py:98` culprits `increases`/`decreases` **when applied to a claim relation**) and return each `{span, offset, cue}`. Deterministic; an *applicability gate* like forensics — prose with no causal verbs returns `[]` (clean, not "passed-vacuously-flagged").
- `downgrade(text, violations) -> text`: apply a fixed causal→associational rewrite map (`causes`→`is associated with`, `reduces`→`is associated with lower`, …) at the flagged offsets. Lossless-ish, conservative; leaves a machine-readable marker Lane 4 can render ("language downgraded: source warrant is observational").
- **Surrogate sub-gate:** `is_surrogate(object_entity)` / `SURROGATES`. Even when `max_tier in LICENSED`, if the claim's `object` is a surrogate marker, causal language about a *hard clinical outcome* is not licensed from that claim alone — the writer must scope to the surrogate ("lowers LDL-C", not "prevents heart attacks"). This is the seam PRD-06 completes: an MR `causal` verdict on LDL-C→CHD (`PRD-06 F6.4`) is what upgrades the surrogate→outcome link to genuinely causal-licensed.
- **Lane 3 wiring (documented here, executed by Lane 3):** (1) pass each claim's `causal_tier` into the writer prompt/system (`synthesizer.py:31-34,110`) so the model is *told* which claims are association-only; (2) post-generate, call `check_language(body, max_tier_of_cited_claims)` at `document.py:sanitize_markdown` (`synthesizer.py:131-132`) and `downgrade` any violation. Belt-and-suspenders: instruct the writer, then enforce in code (the enforcement is authoritative; the model instruction only reduces rewrites).

**Epistemic guardrails.** The gate only ever *weakens* a causal claim to associational — it can never manufacture a stronger claim, so a classifier error is safe-by-direction (a false-observational label costs expressiveness, never truth). Enforcement is code, not trust in the writer. Surrogate scoping keeps "lowers a biomarker" from silently becoming "prevents a disease" — the classic surrogate fallacy.

**Required experiment.** The language-gate *precision* is downstream of tier-classification precision (a wrong tier drives a wrong gate), so RQ-E26 (F12.4) is the gating experiment. The verb-detection/rewrite itself is a deterministic lexicon — unit-tested, not seeded.

**Acceptance + ONE runnable check.** (a) `check_language("X causes Y", "observational")` → one violation on "causes"; (b) `check_language("X causes Y", "rct")` → `[]`; (c) `downgrade("X causes Y", v)` → "X is associated with Y"; (d) surrogate: a licensed-tier claim with `object="LDL-C"` flags hard-outcome verbs. Runnable: `pytest persona/tests/test_causal_tier.py::test_language_gate_blocks_unlicensed_causal_verbs`.

**Effort** M · **Deps** F12.1; Lane 3 consumes.

---

### F12.4 — Precision of causal-tier classification (RQ-E26)

**Problem & evidence.** The classifier *drives the language gate*, so it must be validated before it is trusted to rewrite prose — a wrong *upgrade* (labeling a bare association as RCT/MR/mechanistic) is the dangerous error: it would license causal language on an association, "a silent wrong number that propagates into the belief-state … the worst possible bug" (`CLAUDE.md §4`). This is the pre-registered go/no-go before the gate goes live.

**Design.** `experiments/exp_rq_e26_causal_tier.py`, results → `results/FINDINGS.md#RQ-E26`.
- **Labeled set (HUMAN labels — never synthesized, per `CLAUDE.md §7`).** A small gold set (~120–150 claim spans) hand-labeled to `TIERS`, built two ways to avoid a single annotator's bias: (i) sample claims already in Persona's `sources/*/claims.jsonl` and have a human tier each quote against the **Haber et al. 2022 causal-language rubric**; (ii) include a slice of Haber's published coding where the mapping to `TIERS` is unambiguous. If no human annotation is available at build time, RQ-E26 **blocks** the gate (advisory-only classification) — the gate does not go autonomous on synthetic labels.
- **Hypothesis + metric.** *The deterministic cue classifier, defaulting to weakest on absent/ambiguous cue, assigns causal-licensed tiers with a controlled false-upgrade rate.* Two numbers:
  - **`false_upgrade_rate`** = P(classifier ∈ LICENSED | gold ∈ {observational, correlational}) — the safety metric. Must be tiny.
  - **`licensed_precision`** = macro-precision over the LICENSED tiers (of claims the classifier calls RCT/MR/mechanistic, how many the human agrees are ≥ that warrant).
- **Seeds ≥ 20.** Bootstrap-resample the labeled set 20× (stratified by gold tier); report `false_upgrade_rate` and `licensed_precision` as **mean ± 95% CI**. Deterministic classifier → the seed varies the *resample*, which is the real uncertainty (small-set sampling), the honest thing to CI.
- **Go/no-go gate:** upper 95% CI bound of **`false_upgrade_rate` ≤ 0.05** AND mean **`licensed_precision` ≥ 0.80**. Pass ⇒ the language gate enforces autonomously (downgrade in `document.py`). Fail ⇒ the classifier renders an advisory tier badge only, and the language gate is human-review (matching how PRD-03/06 hold load-bearing autonomy behind their RQ gates). Recall is deliberately *not* gated — weakest-by-default trades recall for the safety of a low false-upgrade rate, which is the correct asymmetry here.

**Epistemic guardrails.** Pre-registered gate (stated before results); no tuning-to-pass — if the cue lexicon can't clear the false-upgrade bar, that is a logged reversal (`CLAUDE.md §2`) and the fallback is CCP-12a's LLM-located cue (which still must ground to a verbatim span), re-gated. Labels are human; the experiment never grades itself against model output.

**Acceptance + ONE runnable check.** The script runs offline on the committed labeled fixture, prints the mean±CI table + the gate boolean, and appends to `results/FINDINGS.md#RQ-E26`. Runnable: `pytest persona/tests/test_causal_tier.py::test_rq_e26_false_upgrade_under_gate` (asserts false-upgrade upper-CI ≤ 0.05 on the fixture, ≥20 resamples, offline).

**Effort** M · **Deps** F12.1; human-labeled fixture.

---

## 4. Sequencing

**Milestone 0 (hour 1 — land FC-10 stubs so Lane 3/Lane 4 build against them):** ship `memory/causal_tier.py` with real `TIERS`/`LICENSED`/`SURROGATES` constants and typed stubs — `classify(...)` returns `{tier:'correlational', cue:None, licensed_causal:False, confident:False, reason:'stub'}`; `check_language(...)` returns `[]`; `downgrade` returns input; `kg.causal_tier(...)` returns the weakest. File **CCP-12** (FC-10) + **CCP-12a** (optional Lane-1 cue) in the HANDOFF dispatch log.

Then: **F12.1** (classifier — the correctness core, build with its unit tests) → **F12.4 / RQ-E26** (validate F12.1 on the human-labeled set; gate must pass before the gate enforces) → **F12.2** (store + surface — plumbing over the validated classifier) → **F12.3** (language gate + surrogate; Lane 3 wires once `check_language` is real and RQ-E26 has passed).

Rationale: nothing enforces on prose until the classifier clears RQ-E26; storage and gate are downstream of a trusted classification.

---

## 5. Test plan

**Unit (pure, offline, no model/network/Docker):** `persona/tests/test_causal_tier.py` — (a) `classify` grounds each tier to a verbatim substring with correct offsets and defaults to `correlational` with `confident=False` when no cue; (b) ambiguity → weaker tier; (c) `check_language` flags causal verbs iff `max_tier ∉ LICENSED`, `[]` on clean prose; (d) `downgrade` rewrites at offsets; (e) surrogate sub-gate flags hard-outcome verbs on a surrogate `object`.

**Storage:** `test_kg_stores_and_reads_tier` — harvest a fixtured source; assert `kg.beliefs`/`kg.claims_in`/`kg.causal_tier` carry the MAX-tier across sources; anchored tier is pinned.

**Experiment oracle (seeded ≥20, offline, human labels):** `exp_rq_e26_causal_tier.py` — false-upgrade-rate upper-CI ≤ 0.05, licensed-precision ≥ 0.80, mean±95% CI over 20 stratified resamples; gate boolean printed + logged to `results/FINDINGS.md#RQ-E26`.

**Cross-lane (Lane 3, after F12.3):** a synthesis over an observational-only community must not contain an un-scoped causal verb — Lane 3 adds a `check_language(note_body, "observational") == []` assertion at its deliverable seam. **Browser smoke (Lane 4):** a belief card renders its tier badge and a "language downgraded" marker distinctly.

---

## 6. Open questions

- **O-1 (CCP-12 / FC-10 — blocks Lane 3 + Lane 4).** New cross-lane interface: `causal_tier.classify/check_language/downgrade/is_surrogate` + `kg.causal_tier` + additive `causal_tier`/`causal_cue` columns on `kg.beliefs`/`claims_in`. Ratify as **FC-10** (Lane 2 provides; Lane 3 = language gate, Lane 4 = render). Lane 3 must ack the `check_language`/`downgrade` call at `synthesizer.py:131`/`document.py:111`; Lane 4 must ack the read-side tier columns. **Blocks Lane 3's synthesizer gate and Lane 4's badge until acked.**
- **O-2 (which tiers are causal-licensed — policy).** `LICENSED = {rct, mendelian_randomization, mechanistic}`. Mechanistic warrant is causal *within its model system* (a mouse knockout ≠ causal in humans); PRD-12 licenses mechanistic causal verbs **only when scoped by the claim's `model_system` qualifier** (`extract.py:42`) — e.g. "in vitro, X activates Y". Confirm this scoping rule, or restrict `LICENSED` to `{rct, mendelian_randomization}` and treat mechanistic as association-in-humans.
- **O-3 (CCP-12a — optional, non-blocking, Lane 1).** Should Lane 1's `extract.py` emit an optional verbatim `causal_cue` span at extraction (full-text context → higher recall), consumed by `classify(cue_hint=...)`? Default: **no** — Lane 2 ships without it; adopt only if RQ-E26 shows the quote-only cue scan misses paraphrased designs.
- **O-4 (surrogate list source).** `SURROGATES` is a small curated set (LDL-C, HbA1c, CRP, viral load, blood pressure, eGFR, tumor-marker levels…). Confirm the seed list, or point to a maintained source (e.g. the FDA surrogate-endpoint table) to load instead of hand-curating.
- **O-5 (experiment/test file ownership).** PRD-00 §3 files `experiments/*`/`tests/*` under Lane 4, but PRD-05/06 have each lane ship its own RQ experiment + unit test. PRD-12 follows the PRD-05/06 precedent (`experiments/exp_rq_e26_*.py`, `persona/tests/test_causal_tier.py`). Confirm this is fine, or route the experiment file through Lane 4.
- **O-6 (RQ id).** Assigned **RQ-E26** (next free after the E25 ceiling in PRD-00 §6; the E20 label reused across PRD-05–10 is a separate collision the master may want to reconcile — PRD-12 deliberately avoids it). Register RQ-E26 in `docs/RESEARCH_QUALITY_PROGRAM.md`.
