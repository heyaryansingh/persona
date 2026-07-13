# PRD-39 — Explanation-faithfulness check

> **Owner lane:** 3 (intellectual engine / synthesis checker) · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (advisory faithfulness flag on a deliverable; never anchors, never mutates a belief — it only annotates prose that drifts from the graph) · **Depends-on:** existing `synthesis/checker.py` + the claim-graph reads it already consumes (`kg.claims_in`, `kg.dependency_edges`), the `forensics.py`/`checker.py` flag-envelope contract (Lane-3-owned) — **no new FC**; optionally consumes **FC-10** (`causal_tier`, Lane 2, SPECCED-not-yet-built) import-guarded. **Backlog #134** (explanation-faithfulness check).
>
> Governed by PRD-00 §4/§6 and §8 reconciliation. Where this body disagrees with §4/§6, §4/§6 win. Pre-assigned experiment: **RQ-E53** (register in `docs/RESEARCH_QUALITY_PROGRAM.md`). Pre-assigned **FC-30** is **RESERVED and left UNUSED** (§2 — the feature is Lane-3-internal; no cross-lane contract is needed). This PRD mints **no new FC** and **no new RQ** beyond RQ-E53.

---

## 0. Summary + capability unlocked

Persona already has one deliverable-quality gate: the citation checker (`synthesis/checker.py:26-46`) asks a cheap Haiku pass which synthesis sentences are **not supported by the source quotes** the synthesis was built from (`checker.py:1-7` — "in-the-wild citation hallucination is 11-57%; we generate FROM quotes to avoid it, and this CHECKS it"). It is wired into `synthesizer.py:157-163` and `review.py:83-85`, and it answers exactly one question: *does this sentence go beyond the raw quotes?*

That is **citation faithfulness** (text ⊆ quotes). It does **not** catch the distinct, more subtle failure this PRD targets: **explanation faithfulness** — *does Persona's natural-language explanation of a conclusion match its own evidence graph, or does it drift beyond what the graph's claims and edges actually assert?* A sentence can be fully quote-supported (the checker passes it) and still **overstate the graph**: the graph holds `effect_sign="0"` (no effect) but the prose narrates an increase; the claim rests on `independent_sources=1` with a `contradicts` edge but the prose calls it "robustly established"; the prose attributes the conclusion to a mechanism that appears **nowhere** as a claim or edge in the graph. This is the gap the CoT-faithfulness literature names — *faithfulness ≠ plausibility* (Jacovi & Goldberg 2020; Lyu et al. 2023): a plausible explanation need not reflect the actual drivers (Turpin et al. 2023, "Language Models Don't Always Say What They Think"; Lanham et al. 2023, "Measuring Faithfulness in CoT"; Atanasova et al. 2023, "Faithfulness Tests for NL Explanations"). Here Persona's **evidence graph is the authoritative reasoning trace**, so faithfulness is checkable *against a ground truth*, not by perturbing an opaque CoT — an **attribution-faithfulness** check, not a plausibility judgement.

PRD-39 adds a **per-sentence explanation-faithfulness check**: for each explanatory assertion in a synthesis/review/paper body, map it to the claim(s)/edge(s) it references and verify the assertion does **not** assert **beyond** (stronger sign, magnitude, or certainty than the graph warrants) or **against** the graph (opposite sign, or a `contradicts` edge). Drift is flagged with **dual signals** (per HANDOFF resolution 5): an LLM-judge may only *propose* a drift as a **boolean gate that cites the exact graph span/field**, and the drift is **confirmed deterministically against the graph structure** in code — no fabricated faithfulness score ever enters the flag. The check is **applicability-gated** (`not_applicable` when a deliverable has no prose or no evidence graph), returns the standard `forensics.py`/`checker.py` flag envelope, is **advisory** (a flag/banner on the deliverable — never a belief mutation), and reports **which sentence drifted and to what** (legibility).

**Capability unlocked (nothing in the stack has it):** the synthesis checker gains a second, orthogonal axis — *the explanation is faithful to the evidence graph, not just to the quotes it was cut from.* Persona stops narrating a contested, single-source, or null-sign belief with the confidence its own graph does not carry — the way a literature synthesizer most quietly misleads — and does it legibly (every drift names the sentence, the drift type, and the exact graph field it exceeds), conservatively (weakest reading of the graph; advisory-only until RQ-E53), and in **code + a boolean-gated judge**, never a self-reported score.

---

## 1. File ownership (disjoint)

| File | New? | Role |
|---|---|---|
| `persona/synthesis/faithfulness.py` | **New (Lane 3)** | The check: `check_faithfulness(body, claims, *, edges=None, propose=None) -> flag`. Deterministic structural signal (sign/magnitude/certainty drift vs graph fields) + an optional LLM-judge proposer (boolean, span-citing) for sentence↔claim mapping and unsupported-driver detection; applicability gate; returns the `forensics.py`/`checker.py` flag envelope. New-file rule (PRD-00 §4, "a NEW, non-colliding file is owned by the lane whose PRD creates it") → Lane 3, exactly as PRD-37 owns `experiments/exp_gail_simon.py`. |
| `persona/synthesis/synthesizer.py` | Edit (Lane 3) | Additive: after the existing `checker.check(...)` call (`synthesizer.py:157-163`), call `check_faithfulness(body, claims, edges=...)` where `claims` (the community's evidence-graph slice) and `body` are already in scope; write its advisory drift summary into the note banner beside the substance tier (`synthesizer.py:164-169`) and log the drift list. No change to generation. |
| `persona/deliverables/review.py` | Edit (Lane 3) | Additive: reconstruct the topic's claim slice (`kg.claims_in`) and run `check_faithfulness` over `review_markdown` beside the existing `checker.check` (`review.py:83-85`); advisory banner. Degrades to `not_applicable` if the slice can't be assembled. |
| `persona/deliverables/paper.py` | Edit (Lane 3) | Additive: same wiring at the paper's prose-generation seam; advisory banner. (Lazy: same call, larger body.) |
| `persona/agents/audit.py` | Edit (Lane 3) | Optional additive call site + the **render reference**: the flag envelope matches `forensics.run_all`'s, so if the auditor runs the check over an adjudication rationale it flows through the existing generic flag loop (`audit.py:475-479`) with a `span` (survives the grounding guard `audit.py:305`) and severity counting (`audit.py:311-313`) with **no new render**. v1 wires it only if OQ-4 says so. |
| `tests/test_faithfulness.py` | **New (Lane 3)** | Unit tests for the check (gate + each drift type + dual-signal + envelope shape). New-file rule → Lane 3. |
| `experiments/exp_explanation_faithfulness.py` | **New (Lane 3)** | RQ-E53 sandbox: labeled (explanation, graph) pairs, fault-injected drift, precision + false-flag gate. New-file rule → Lane 3 (per PRD-37 precedent; cross-cutting-ownership ruling PRD-00 §9 — providing lane owns its RQ sandbox + unit test). |

**Boundary files another lane renders/provides (this lane does NOT edit them):**
- `persona/memory/causal_tier.py` (**FC-10, Lane 2 — SPECCED, not-yet-built**). *Optional consume, import-guarded.* If present, the check reuses its causal-verb / direction lexicon (`causal_tier.check_language`, `TIERS`, `LICENSED`, PRD-12 §2) for the certainty/magnitude signal rather than hand-rolling a worse one; if absent, a small local lexicon runs. Import-guarded degrade-gracefully, the PRD-29/PRD-35 precedent for a specced-not-built dependency — never blocks.
- `persona/api/static/index.html` + `persona/api/app.py` — **Lane 4 owns.** The faithfulness flag renders through the auditor's existing generic forensic-flag loop when the auditor runs it (`audit.py:475-479` — no new route/tab), and the synthesizer's advisory banner is Lane-3-written note markdown (like the substance-tier banner, `synthesizer.py:56-65`). A *dedicated* Lane-4 faithfulness surface (drift list on a deliverable card) is the only thing that would need a cross-lane read — **that read is FC-30, deferred as OQ-3, not built here.**

> **No cross-lane parallel-edit exposure.** Every edited file (`synthesis/*`, `deliverables/*`, `agents/audit.py`) is Lane-3-owned; the two new files are Lane-3 by the new-file rule. Lane 2's `causal_tier` is consumed read-only and import-guarded.

---

## 2. FCs provided / consumed

**PROVIDES: none new.** The check is an internal function of the Lane-3-owned `synthesis/` package, called by Lane-3-owned generation surfaces (`synthesizer.py`, `review.py`, `paper.py`) and optionally the Lane-3-owned auditor (`audit.py`). Its "contract" is the **existing internal flag envelope** shared by `forensics.py` and `checker.py` — not a frozen cross-lane FC, the same status as `p_curve`/`statcheck`/`gail_simon` (PRD-37 §2). New public function signature stub (internal to Lane 3):

```python
# persona/synthesis/faithfulness.py  (additive; returns the forensics.py / checker.py flag envelope)
def check_faithfulness(
    body: str,
    claims: list[dict],                 # evidence-graph slice, kg.claims_in shape (kg.py:311-326):
                                        #   {claim_id, subject, relation, object, effect_sign,
                                        #    confidence, independent_sources, sources:[{slug,quote,...}]}
    *,
    edges: list[dict] | None = None,    # kg.dependency_edges shape (kg.py:368-380):
                                        #   [{src, dst, rel_type, confidence, span}]; used for
                                        #   contested/against-graph confirmation (rel_type 'contradicts')
    propose=None,                       # optional Signal-A proposer (LLM boolean gate); None -> deterministic-only
) -> dict:
    """Does the prose EXPLANATION assert beyond / against the EVIDENCE GRAPH? Dual-signal, per-sentence.
    Returns the standard forensic-flag envelope, verbatim shape as p_curve/statcheck/gail_simon:
      {check: 'explanation_faithfulness',
       status: 'ok' | 'drift' | 'not_applicable' | 'skipped',
       severity: 0 | 2 | 3,               # 3 = against-graph / sign flip; 2 = magnitude/certainty/unsupported-driver
       detail: str,                       # names WHICH sentence drifted to WHAT (legibility)
       span: str,                         # the first drifting sentence (grounds the flag; survives audit.py:305)
       drift_rate: float | None,          # flagged / mapped-sentences  (None on na/skipped)
       n_sentences: int, n_mapped: int,
       drifts: [{sentence, sentence_offset: [int, int], claim_id,
                 drift_type: 'sign' | 'magnitude' | 'certainty' | 'unsupported_driver' | 'against_graph',
                 graph_field: str, graph_value, graph_span: str,   # the exact claim field/span exceeded
                 confirmed_by: 'dual' | 'structural'}]}            # numeric/drift fields absent on na/skipped
    """
```

**CONSUMES (all existing/stable or import-guarded):**
- `kg.claims_in(entities, limit)` → the claim-graph slice (`kg.py:311-326`: `claim_id, subject, relation, object, effect_sign, confidence, independent_sources, sources[{slug,quote,...}]`). Already the synthesizer's input (`synthesizer.py:87`).
- `kg.dependency_edges(topic)` → `[{src, dst, rel_type, confidence, span}]` (`kg.py:368-380`); `rel_type ∈ {supports, contradicts, presupposes, …}` (FC-3, PRD-00 §4). Used only to confirm *contested* / *against-graph* drift.
- The `forensics.py`/`checker.py` flag-envelope contract (Lane-3-owned) and `audit.py`'s generic flag render (`audit.py:305,311-313,475-479`).
- **FC-10 `causal_tier` (Lane 2, SPECCED-not-built): optional, import-guarded.** Reuse its causal-verb / direction lexicon when present; local fallback when absent.

**CONTRACT CHANGE PROPOSAL: none.** Everything is additive within Lane 3. **FC-30 is left UNUSED** — reserving a cross-lane faithfulness FC would be speculative (YAGNI): no lane outside Lane 3 needs to *call* the check, and rendering rides the existing flag loop. If Lane 4 later wants a dedicated faithfulness read/surface, *that* is FC-30 — surfaced as OQ-3 for the master, not minted here.

---

## 3. Features

---

### F39.1 — `check_faithfulness(...)`: per-sentence drift detection, dual-signal, applicability-gated (`synthesis/faithfulness.py`)

**Problem & evidence.** The only deliverable gate today is `checker.check(body, quotes)` (`checker.py:26-46`): it flags sentences that exceed the **raw quotes**. It is blind to drift from the **graph structure**, because it never sees the graph — it takes `body` + a flat `quotes` list (`synthesizer.py:159`). Concretely, the synthesizer maps every `effect_sign` to a fixed arrow (`synthesizer.py:98,103` — `{"+":"increases","-":"decreases","0":"no effect"}`) and hands the claims to a free-prose writer (`synthesizer.py:110-119`), then checks only quote-support (`synthesizer.py:160`). Nothing verifies the *written* direction matches the *stored* `effect_sign`, nor that a "robustly established" phrasing is warranted by `independent_sources` (`kg.py:321`), nor that a narrated mechanism corresponds to any claim/edge. A quote can support "X was higher in cases" while the graph's claim is `effect_sign="0"` and carries a `contradicts` edge — the checker passes, the explanation drifts.

**Design.** Pure-core + optional judge, deterministic where it can be (the `forensics.py` posture — "arithmetic is deterministic, unit-tested, and impossible to argue with"):

1. **Applicability gate (strict — the correctness boundary; mirrors `p_curve`/`gail_simon`'s three-way disposition):**
   - `body` empty/whitespace **or** `claims` empty → `not_applicable` ("no prose explanation" / "no evidence graph"). **The common out-of-domain case**; never scored as a pass.
   - `body` present but **zero sentences map to any claim entity** (nothing to assess against the graph) → `skipped` (has structure, can't run — distinct from out-of-domain, per the `forensics.py` `na` vs `skipped` rule).
   - ≥1 sentence maps to ≥1 claim → run.
2. **Sentence split + sentence→claim mapping (deterministic; the map the drift is judged against).** Split `body` into sentences (offsets retained). For each claim, build its entity set `{subject, object}` (normalized — casefold/NFKC/whitespace-collapse, the extractor's `_norm` discipline reused, not re-implemented). A sentence **maps** to a claim when it mentions both the subject and object strings (substring match on normalized text). Store `sentence_offset` (in `body`) and `claim_id`. Unmapped sentences are not assessed (recall is bounded by mapping — the honest, conservative choice; a missed mapping under-flags, never over-flags).
3. **Signal B — deterministic structural drift (authoritative; runs with no key/budget).** For each (sentence, claim) map:
   - **sign** — extract the sentence's asserted direction via a direction lexicon (increase-words / decrease-words / null-words; reuse `causal_tier`'s if importable, §2). If asserted direction ≠ claim `effect_sign` → **candidate `sign` drift** (`graph_field='effect_sign'`, `graph_value=effect_sign`).
   - **against_graph** — if the sentence asserts the relation as settled/uncontested **and** the graph carries ≥1 `contradicts` edge on this `claim_id` (from `edges`) → **candidate `against_graph` drift** (`graph_field='contradicts_edge'`, `graph_span=edge.span`).
   - **magnitude** — sentence contains a magnitude-intensifier (`strongly|substantially|dramatically|markedly|large|robust|powerful`) **and** the claim's warrant is thin (`independent_sources < 2`) → **candidate `magnitude` drift** (`graph_field='independent_sources'`).
   - **certainty** — sentence contains a certainty-intensifier (`establishes|proves|confirms|demonstrates|definitively|clearly shows|shows that`) **and** the claim is weakly warranted (`independent_sources < 2` **or** `confidence < CERTAINTY_MIN` **or** a `contradicts` edge exists) → **candidate `certainty` drift** (`graph_field='independent_sources'|'confidence'`). *(v1 uses the fields `claims_in` actually returns — `independent_sources`, `confidence` — plus `contradicts` edges; if a caller also passes `provenance`, add `READ`/`INFERRED` to the thin-warrant test. OQ-2.)*
   - **Negation/hedge guard:** the lexicon must not fire inside a negated or hypothetical clause ("does **not** strongly increase", "**if** X causes Y"). A minimal deterministic negation scope check drops these; the LLM proposer (Signal A) is the backstop.
4. **Signal A — LLM-judge proposal (boolean, span-citing; optional, off the default offline path).** When a `propose` callable is supplied (a bounded Haiku pass, the `checker.check` budget/key discipline reused), for each candidate from Signal B it returns a **boolean**: "does this sentence in fact assert `{drift_type}` about the claim `{subject} {relation} {object}`?" and **must cite the exact claim span** it drifts from. It may **only confirm or drop** a Signal-B candidate for sign/magnitude/certainty/against-graph — it can never invent a numeric score. It **additionally proposes** `unsupported_driver` candidates: a sentence asserting a load-bearing driver→outcome step whose entity pair matches **no** claim (subject/object) and **no** dependency edge — each such proposal is then **confirmed deterministically** by looking the pair up in `claims`/`edges` (absence = confirmed).
5. **Flag rule — a drift is emitted ONLY when both signals agree (dual-signal, per HANDOFF res. 5).** With `propose=None` (offline/CI/no-budget), only `confirmed_by='structural'` drifts for sign/magnitude/certainty/against-graph are emitted (Signal B is authoritative for those; `unsupported_driver` requires the judge and is skipped) — and the flag ships at the more conservative severity. With a proposer, drifts are `confirmed_by='dual'` and `unsupported_driver` is available.
6. **Verdict (typed severity — the reviewer's judgment, computed not asserted).**
   - any `sign` or `against_graph` drift → **`drift`, severity 3**: the explanation asserts the **opposite of / against** the graph — a code-confirmed contradiction (rides the auditor's severity-≥3 cap `audit.py:353-354` when run there), the synthesis analog of statcheck's decision-flip.
   - only `magnitude`/`certainty`/`unsupported_driver` drift → **`drift`, severity 2**: over-claim/warn (feeds `n_warn`, `audit.py:312`).
   - no confirmed drift → **`ok`, severity 0**.
7. **Return** the flag envelope (§2): `detail` names the first drifting sentence + its type + the graph field it exceeds ("sentence 4 asserts an increase; graph `effect_sign=0` on claim c_812"); `span` = that sentence (grounds the flag, survives `audit.py:305`); `drifts[]` carries every per-sentence drift with offsets and the exact graph field/span for the render.

**Epistemic guardrails.**
- **Exact-span grounding both ends** — each drift stores the prose `sentence_offset` **and** the `claim_id` + `graph_field`/`graph_span` it exceeds. No drift is emitted without a concrete graph field to point at (`no fabricated confidence`).
- **No fabricated faithfulness score** — the LLM-judge is a **boolean gate citing a graph span**, never a number; every emitted drift is **confirmed against a real graph field** in code (dual-signal). `drift_rate` is a count ratio over *mapped* sentences, not a model judgement.
- **Advisory, never a belief mutation** — the output is a flag/banner on the deliverable. The check has **no KG-write path** (unlike the membrane); it never demotes, re-confidences, or anchors. Advisory-only until `ops_dir/rq_e53.passed` (rendered with a `candidate` label; does not feed the auditor's severity cap until then, only the warn count — the PRD-37 RQ-gate pattern).
- **Weakest-reading / safe-by-direction** — the check only ever flags the explanation as *over*-stating; a mapping miss or a dropped candidate costs recall, never truth. A false flag costs a spurious "downgrade to hedge," never a fabricated finding.
- **Applicability-gated** — `not_applicable` (no prose / no graph) and `skipped` (unmappable) are first-class, never counted as passes (the F3.8/RQ-E38 discipline).
- **The check is itself faithful** — it reports **which** sentence drifted and **to what** graph field (legibility), so a human can audit the auditor.

**Required experiment — RQ-E53** (§ below).

**Acceptance + ONE runnable check.**
(a) prose "X strongly increases Y" over a claim `effect_sign="0"` → `status:"drift"`, severity 3, one `sign` drift naming sentence + `effect_sign`; (b) prose "X is associated with Y" over a claim `effect_sign="+"`, `independent_sources=3`, no `contradicts` → `status:"ok"`; (c) prose "X robustly establishes Y" over `independent_sources=1` → severity-2 `certainty`/`magnitude` drift (structural, no judge); (d) empty body **or** empty claims → `not_applicable`; (e) body present but no sentence mentions any claim's subject+object → `skipped`; (f) a `contradicts` edge on the mapped claim + settled phrasing → `against_graph` severity 3.
**Runnable check:** `pytest tests/test_faithfulness.py::test_gate_and_drift_verdict`.

**Effort** M · **Deps** `kg.claims_in`/`dependency_edges` (present); `causal_tier` optional (import-guarded); the pure structural path is testable standalone with fixture dicts (no key).

---

### F39.2 — Advisory wiring into the generation surfaces (`synthesizer.py`, `review.py`, `paper.py`; render-ready for `audit.py`)

**Problem & evidence.** `check_faithfulness` is inert until a surface that produces a prose explanation *from a claim set* calls it. The synthesizer is the ideal seam: `claims` (the evidence-graph slice, `synthesizer.py:87`) and `body` (the prose, `synthesizer.py:132`) are both in scope at the exact line the citation checker runs (`synthesizer.py:157-163`), and the note already carries a machine-written banner beside the substance tier (`synthesizer.py:56-65,164-169`). Reviews and papers generate prose from cited *notes* (`review.py:71-90`; `paper.py`), so their evidence graph is the topic's claim slice — reconstructable via `kg.claims_in`.

**Design.** Additive calls, no behavior change to any existing output:
- **`synthesizer.py` (primary seam).** After `chk = checker.check(...)` (`synthesizer.py:160`), call `ff = check_faithfulness(body, claims, edges=kg.dependency_edges(...))`. Append its advisory result to the note banner (a `· N sentence(s) drift from the graph — see below` line beside the `{pct}% quote-supported` tier, `synthesizer.py:164-169`) and log the `drifts[]` in the `synthesis` event (`synthesizer.py:177-179`). **Never** blocks the write, **never** touches the KG.
- **`review.py` / `paper.py`.** Reconstruct the claim slice for the topic (`kg.claims_in(topic-entities)`), run `check_faithfulness(review_markdown, claims, edges=...)` beside the existing `checker.check` (`review.py:83-85`), and add the advisory line to the review/paper header (`review.py:87-90`). If the slice can't be assembled cheaply → `not_applicable` (degrade-gracefully, no error).
- **`audit.py` (render-ready, optional call).** The flag envelope is `forensics`-shaped, so if the auditor runs the check over its adjudication rationale it flows through the existing generic flag loop (`audit.py:475-479`) with a `span` (survives `audit.py:305`) and severity counting (`audit.py:311-313`) — **no new render**. Wired only per OQ-4.

**Epistemic guardrails.** Advisory everywhere — the banner/flag informs, it never gates the write or edits a belief (contrast the membrane). The synthesizer's own `substance_tier` and the citation checker stay unchanged; faithfulness is an *orthogonal* axis reported alongside them (quote-support answers "is it cited?"; faithfulness answers "does it overstate the graph?"). Until `ops_dir/rq_e53.passed`, the banner reads "candidate: N sentence(s) may drift" (honest uncertainty in the UI, per PRD-00 §5).

**Required experiment.** Covered by RQ-E53 (the check's precision) + the auditor's existing render discipline; the wiring is a call over a gated unit (no separate seeded experiment — wiring over a tested core, the PRD-37 F37.2 pattern).

**Acceptance + ONE runnable check.** Feeding the synthesizer path a `body` with an injected sign-flip over a fixtured `claims` slice yields exactly one `explanation_faithfulness` flag carrying a `span`, written to the note banner and logged; a clean body yields `status:"ok"` and no drift line. **Runnable check:** `pytest tests/test_faithfulness.py::test_synthesizer_wires_advisory_flag` (asserts the flag appears with a span, the note banner gains the advisory line, and the KG is not written).

**Effort** S · **Deps** F39.1.

---

### Required experiment — RQ-E53 (register in `docs/RESEARCH_QUALITY_PROGRAM.md`)

**Hypothesis.** The faithfulness check catches explanation-drift at usable precision: on a **labeled set of (explanation, evidence-graph) pairs** — some faithful, some with **injected drift** (overstated sign, magnitude, or certainty, or an assertion with no supporting edge) — it flags injected drift at **detection precision ≥ 0.80** while keeping the **false-flag rate on faithful explanations with a 95%-CI upper bound ≤ 0.05**. So it can annotate over-claiming without crying wolf on honest syntheses.

**Metric.**
- **`detection_precision`** = of sentences the check flags as drift, the fraction that are genuinely injected drift (positive predictive value). **Gate: ≥ 0.80.**
- **`false_flag_rate`** = on the **unmodified faithful** syntheses (which already passed `checker.check`), the fraction of mapped sentences wrongly flagged. **Gate: 95%-CI upper bound ≤ 0.05.** (Recall reported informational, not gated — weakest-reading trades recall for a low false-flag rate, the correct asymmetry: an over-flag downgrades honest prose to a hedge, cheap; a missed drift is caught by the human, and the check is advisory regardless.)

**Fault injection (≥20 seeds).** Take **real** synthesis outputs (Persona's own `notes/*.md`, built from real `claims.jsonl` slices — the graph is the ground truth). For each seed, programmatically inject drift into a random subset of sentences while leaving the graph unchanged: **sign** (rewrite the arrow verb against `effect_sign`), **magnitude** (inject a magnitude-intensifier on an `independent_sources<2` claim), **certainty** (rewrite "is associated with" → "establishes/proves" on a thin-warrant claim), **unsupported_driver** (insert a sentence attributing the conclusion to an entity pair absent from `claims`/`edges`). The faithful controls are the untouched syntheses. Seeds vary the injection RNG (which sentences/claims, which drift type) and the faithful/drift split; report `detection_precision` and `false_flag_rate` as **mean ± 95% CI** over ≥20 seeds.
- **Reproducible offline gate:** the ≥20-seed sweep runs the **deterministic structural detector** (`propose=None`) so it is offline, seeded, and CI-runnable (no key/nondeterminism). The full **dual-signal** path (with the real Haiku proposer, temperature 0) is validated once on a held-out slice and logged to `results/FINDINGS.md#RQ-E53`; because a proposer can only *drop* structural candidates (AND-gate) for sign/magnitude/certainty, the offline structural run is the **conservative** bound on false-flag rate (OQ-1 asks whether the gate must also include a real-LLM leg for the `unsupported_driver` type, which the structural path cannot catch).

**Gate.** `detection_precision ≥ 0.80` **AND** `false_flag_rate` 95%-CI upper ≤ 0.05 (≥20 seeds, mean±95%CI) → the flag may feed the auditor's severity path under Balanced autonomy and the banner drops the "candidate" label. Until then the flag ships **advisory-only** (`candidate` banner; warn-count only, never the severity cap). A failing false-flag bound is a **stop-the-line** result (a check that downgrades honest prose is worse than none, `CLAUDE.md §4`) — logged as a reversal, the fallback being a stricter mapping/negation guard, re-gated.

**Sandbox.** `experiments/exp_explanation_faithfulness.py` — embeds/loads the real-note fixtures + the fault-injector; `__main__` prints `detection_precision` and `false_flag_rate` (mean±95%CI) per drift type and the gate boolean; results → `results/FINDINGS.md#RQ-E53`. ≥20 seeds, offline (deterministic detector); optional keyed dual-signal validation leg.

---

## 4. Sequencing (interface-first → fill)

1. **M0 (hour 1, keeps the repo runnable):** land `synthesis/faithfulness.py` with the typed `check_faithfulness(...)` returning a `not_applicable` stub (envelope shape only). Nothing calls it yet; nothing regresses. Add the lexicon constants (direction/magnitude/certainty) so §5 unit tests can pin the envelope.
2. **F39.1 Signal B** — sentence split + entity mapping + the deterministic sign/magnitude/certainty/against-graph structural detector + applicability gate. Verify against §5 gate/verdict tests immediately (offline, no key).
3. **RQ-E53 offline sweep** — fault-inject over real notes; the deterministic detector must clear `precision ≥ 0.80` AND `false-flag 95%-CI ≤ 0.05`. **Do not proceed past a red false-flag bound.**
4. **F39.1 Signal A** — the optional LLM-judge proposer (boolean, span-citing) + `unsupported_driver`; dual-signal AND-gate. Validate the keyed leg on a held-out slice; log to FINDINGS.
5. **F39.2** — wire the advisory call + banner into `synthesizer.py`, then `review.py`/`paper.py`; the flag now rides the note/deliverable header. `audit.py` render/call only if OQ-4 adopts it.

Rationale: nothing feeds the auditor's severity path until the offline gate passes; wiring is downstream of a trusted, offline-provable structural core (the judge only adds recall on `unsupported_driver`).

---

## 5. Test plan

| Check | File::name | Asserts |
|---|---|---|
| Gate + verdict | `tests/test_faithfulness.py::test_gate_and_drift_verdict` | empty body/claims → `not_applicable`; unmappable body → `skipped`; sign-flip vs `effect_sign` → `drift` sev 3; clean prose over 3-lab `+` claim → `ok`; magnitude/certainty on `independent_sources<2` → `drift` sev 2; `contradicts` edge + settled phrasing → `against_graph` sev 3 |
| Dual-signal + envelope | `tests/test_faithfulness.py::test_dual_signal_and_envelope` | `propose=None` emits only `confirmed_by='structural'` drifts (no `unsupported_driver`); a stub proposer that drops a candidate suppresses that drift (AND-gate); envelope matches `{check,status,severity,detail,span,drifts}`; each drift carries `sentence_offset` + `graph_field`; **no KG-write** |
| Negation guard | `tests/test_faithfulness.py::test_negation_and_hedge_not_flagged` | "does not strongly increase" / "if X causes Y" over a thin claim → no drift (structural negation scope) |
| Wiring (advisory) | `tests/test_faithfulness.py::test_synthesizer_wires_advisory_flag` | synthesizer path with an injected drift → one flag with a span + a banner drift line + logged event; clean body → no drift line; belief store untouched |
| RQ-E53 | `experiments/exp_explanation_faithfulness.py` `__main__` | fault-injected drift over real notes → `detection_precision ≥ 0.80` AND `false_flag_rate` 95%-CI upper ≤ 0.05, ≥20 seeds, mean±95%CI, offline |
| Regression | existing `tests/` for `synthesizer`/`review` | unchanged — the additive call never blocks a write, never alters `checker.check`'s `support_rate`/`substance_tier` |

---

## 6. Open questions

- **OQ-1 (does the gate need a real-LLM leg? — recommend NO for v1, deterministic-only gate).** The offline structural detector clears sign/magnitude/certainty/against-graph and is the conservative false-flag bound; only `unsupported_driver` needs the judge. **Recommended default:** gate on the deterministic sweep (offline, ≥20 seeds, reproducible) and validate the dual-signal `unsupported_driver` leg descriptively on a keyed held-out slice, logged to FINDINGS — do not block the gate on a nondeterministic LLM leg. Master confirms this is acceptable for RQ-E53 or requires a keyed leg in the gate.
- **OQ-2 (`provenance` in the certainty signal — recommend additive-if-passed).** `kg.claims_in` returns `independent_sources`+`confidence` but **not** `provenance` (`kg.py:320-325`); `kg.beliefs` does. v1's certainty/magnitude thin-warrant test uses `independent_sources<2` + `confidence` + `contradicts` edges (all present). **Recommended default:** if a caller passes `provenance`, add `READ`/`INFERRED` to the thin-warrant test; otherwise the source-count/confidence/contested signal stands. Don't widen `claims_in`'s return for this (that would touch Lane-2 read shape unnecessarily).
- **OQ-3 (FC-30 — dedicated Lane-4 faithfulness surface, deferred).** The flag renders free through the auditor's generic loop and the synthesizer banner — **no new route/tab** (the "integrate into existing review surfaces, no new tabs" direction, PRD-37 OQ-3). A *dedicated* drift-list card on a deliverable would need a cross-lane read = **FC-30**. **Recommended default:** do not mint FC-30; generic banner/flag render. If the master wants the dedicated surface, ratify FC-30 as `GET /faithfulness/{slug}` (Lane 3 provides the read, Lane 4 renders) — a follow-on, not this PRD.
- **OQ-4 (run the check inside `audit.py`? — recommend defer).** The auditor judges a *paper*, not Persona's own belief, so the (explanation, graph) pairing is most natural for synthesis/review/paper (Persona explaining its own graph). **Recommended default:** wire v1 at the generation surfaces only; the `audit.py` render path is proven available (envelope-compatible) but the call is a follow-on if the auditor's adjudication rationale is worth faithfulness-checking against the KG external-stance slice.
- **OQ-5 (sentence↔claim mapping strength — recommend substring-entity v1).** Mapping is deterministic substring match on `{subject, object}`. A synonym/paraphrase of an entity ("LDL" vs "LDL-C") under-maps (misses a drift — safe-by-direction). **Recommended default:** substring-entity mapping for v1; if RQ-E53 recall is poor, add the vector-similarity fallback Persona already has (`p.vectors`) behind the same dual-signal confirm — a precision-neutral recall upgrade, not a gate change.
