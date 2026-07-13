# PRD-37 — Gail-Simon effect-modification forensic

> **Owner lane:** 3 (intellectual engine / code-run forensics auditor) · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (advisory forensic flag; never anchors or mutates a belief) · **Depends-on:** existing FC-4 code-run robustness auditor (`analysis/forensics.py` + `agents/audit.py`, both Lane-3-owned) — **no new FC** · **Backlog #71** (Gail-Simon effect-modification forensic).
>
> Governed by PRD-00 §4/§6 and §8 reconciliation. Where this body disagrees with §4/§6, §4/§6 win. Pre-assigned experiment: **RQ-E51** (register in `docs/RESEARCH_QUALITY_PROGRAM.md`). This PRD mints **no new FC and no new RQ** beyond RQ-E51.

---

## 0. Summary + capability unlocked

The auditor already runs deterministic statistical forensics in CODE over a paper's transcribed numbers — statcheck, GRIM, GRIMMER, power, p-curve (`persona/analysis/forensics.py:8-12`) — each under a strict applicability gate that emits `not_applicable` (out-of-domain) distinct from a pass (`forensics.py:14-22`, `35-39`). But it has **no check for the single most abused claim in clinical and preclinical papers: "the treatment works better in subgroup S."** Reviewers know this pattern (Yusuf 1991; Wang 2007; Sun 2012): a trial with no overall effect reports a "significant benefit in patients with X," computed as *within-subgroup significance* rather than the *interaction test* the statistics actually license — and most such claims are noise that fails to replicate. Persona currently transcribes such a claim as a `kind:"causal"|"correlational"` claim (`audit.py:36`) and adjudicates it in prose, with **zero code-run scrutiny of whether the subgroups genuinely differ.**

This PRD adds a **code-run forensic for heterogeneity of treatment effect (HTE) / effect modification**: given effect estimates + SEs/CIs in ≥2 subgroups, it runs (1) the **interaction test** (Cochran's Q across subgroups — is there *any* difference beyond chance?) and (2) the **Gail-Simon qualitative-interaction test** (Gail & Simon 1985 — is the difference a genuine *sign flip*, "benefit in S, null/harm in ¬S", or merely a magnitude difference?). Both are exact, deterministic scipy computations — never a model. The verdict answers: **does the claimed "works better in S" survive, or is it a spurious subgroup claim?** A modification claim with a non-significant interaction is flagged as noise; a claimed qualitative flip that fails Gail-Simon is flagged as over-claim; a genuine, test-supported modification passes.

**Capability unlocked (nothing in the stack has it):** the auditor gains the reviewer's reflex for the most common way a paper over-reads its own data — *the subgroup mirage* — proven in code, grounded to the exact subgroup sentences, and abstaining honestly on the ~99% of claims that are not subgroup claims. It is **distinct from PRD-10 meta-analysis** (which *pools* effects *across* independent studies): this **probes effect modification *within* a single study**, using the same Cochran's Q arithmetic to a different end (between-subgroup, not between-study), plus the qualitative-interaction layer meta-analysis does not have.

---

## 1. File ownership (disjoint)

| File | New? | Role |
|---|---|---|
| `persona/analysis/forensics.py` | Edit (Lane 3) | Add `gail_simon(...)` — the forensic (interaction Q + Gail-Simon qualitative test), reusing the module's `_na`/`_DISPOSITION`/flag-envelope scaffold. Add ONE dispatch branch in `_run_all_raw` over a new `subgroups` field. |
| `persona/agents/audit.py` | Edit (Lane 3) | Additive: add a `subgroups` array to `_EXTRACT_TOOL.input_schema` (`audit.py:32-47`) and one clause to `_EXTRACT_SYS` (`audit.py:49-54`) so the model transcribes subgroup effect records + their exact spans when — and only when — the paper makes a subgroup/effect-modification claim. No change to the adjudication/blend/report bodies (the flag rides the existing generic render). |
| `tests/test_forensics.py` | Edit (Lane 3) | Add `test_gail_simon_*` cases beside the existing forensic unit tests (`tests/test_forensics.py:28-43`). ponytail: extend the file that already tests this module, no new test file. |
| `experiments/exp_gail_simon.py` | **New (Lane 3)** | RQ-E51 sandbox: reproduce Gail-Simon's published critical-value table + worked example (numeric gate) and prove correct abstention off-domain. New-file rule (PRD-00 §4, "a NEW, non-colliding file is owned by the lane whose PRD creates it, regardless of directory") → Lane 3, exactly as PRD-10 owns `experiments/exp_rq_e20_meta_reproduction.py`. |

**Boundary files another lane renders (this lane does NOT edit them):**
- `persona/api/static/index.html` + `persona/api/app.py` audit-render path — **Lane 4 owns.** The Gail-Simon flag is emitted in the existing forensic-flag shape (`{check,status,severity,detail,span}`, `forensics.py:14`), so it renders through the auditor's existing generic flag loop (`audit.py:475-479`) and the "Deterministic checks" section with **no new route, no new tab, no render contract**. Flagged to Lane 4 as informational only (OQ-3).

> **No cross-lane parallel-edit exposure.** Every edited file is Lane-3-owned; the new experiment file is Lane-3 by the new-file rule. Lane 4 only *renders* the already-shaped flag it already renders for every other forensic.

---

## 2. FCs provided / consumed

**PROVIDES:** none new. The forensic is an internal function of the Lane-3-owned `forensics.py`, invoked by the Lane-3-owned `audit.py`. Its "contract" is the **existing internal forensic-flag envelope** (`forensics.py:14`), not a frozen cross-lane FC — the same status as `statcheck`/`p_curve`, which are also not FCs. New public function signature stub (for coherence; internal to Lane 3):

```python
# persona/analysis/forensics.py  (additive; matches the statcheck/p_curve return contract)
def gail_simon(subgroups: list[dict], *, claim_direction: str | None = None,
               alpha: float = 0.05) -> dict:
    """Heterogeneity-of-treatment-effect forensic for a 'works better in subgroup S' claim.
    subgroups: [{label:str, effect:float, se:float|None, ci_low:float|None, ci_high:float|None,
                 metric:'MD'|'SMD'|'RD'|'OR'|'RR'|'HR', span:str}]  (≥2 to run; SE derived from CI if absent)
    claim_direction: optional favored subgroup label + sign the paper claims (for over-claim / sign-contradiction detection).
    Returns the standard forensic flag envelope, verbatim shape as p_curve/statcheck:
      {check:'gail_simon', status: 'ok'|'weak'|'inconsistent'|'not_applicable'|'skipped',
       severity: 0|2|3, detail:str, span:str, subgroup_spans:list[str],
       interaction:{Q:float, df:int, p:float}, qualitative:{Q_min:float, p:float}}  # numeric fields absent on na/skipped
    """
```

Registered into the forensic run via ONE additive branch in `_run_all_raw` (`forensics.py:196-222`): after the `p_values`/p_curve block, dispatch `gail_simon(stats_extracted.get("subgroups", []))` when present; set `r["span"]` from the subgroups. It then flows unchanged through `run_all` (`forensics.py:231-238` — drops `not_applicable`/`skipped`), `debit` (`forensics.py:241-258` — audits ran/passed/failed/not_applicable), and the auditor's flag pipeline (`audit.py:305,311-313,328,475-479`).

**CONSUMES:** existing stable surfaces only — `forensics._na` / `forensics._DISPOSITION` / the flag envelope (`forensics.py:35-39,227`); `audit._EXTRACT_TOOL` / `_EXTRACT_SYS` transcribe-only extraction discipline (`audit.py:32-54`). `scipy.stats.chi2` (already imported, `forensics.py:28`; declared dep `pyproject.toml`).

**CONTRACT CHANGE PROPOSAL:** none. Everything is additive within Lane 3. (If Lane 4 later wants a *dedicated* subgroup-forensic surface element rather than the generic flag render, that is a Lane-4 presentation choice needing no contract — see OQ-3.)

---

## 3. Features

---

### F37.1 — `gail_simon(...)`: interaction test + qualitative-interaction test, under a strict applicability gate (`analysis/forensics.py`)

**Problem & evidence.** The auditor transcribes a paper's central claims with a `kind` (`audit.py:36` — `causal|descriptive|mechanistic|correlational`) and runs code-run forensics over its *reported test statistics and descriptives* (`forensics.py:196-222`), but the forensics operate on **pooled/whole-sample** numbers. A claim of the form "the effect is larger in subgroup S" has a distinct statistical failure mode that none of statcheck/GRIM/GRIMMER/power/p-curve touch: the paper computes *within-subgroup significance* (significant in S, non-significant in ¬S) and reads that as effect modification, when the licensed test is the **interaction test** on the *difference between* subgroup effects. This is the canonical spurious-subgroup error (Yusuf et al. 1991 *JAMA*; Assmann et al. 2000 *Lancet*; Brookes et al. 2001/2004; Wang et al. 2007 *NEJM* "Statistics in Medicine — Reporting of Subgroup Analyses"; Sun et al. 2010/2012 *BMJ* subgroup-claim credibility). The strong version — "benefit in S but *harm/none* in ¬S" (a qualitative interaction, a sign flip) — has an even more specific licensed test: **Gail & Simon (1985), *Biometrics* 41(2):361-372**, the likelihood-ratio test for qualitative interactions. Neither test exists in the codebase.

**Design.** Pure function, no model, deterministic (matching `forensics.py`'s "arithmetic is deterministic, unit-tested, and impossible to argue with", `forensics.py:5-6`):

1. **Applicability gate (strict — the correctness boundary).** Mirror `p_curve`'s three-way disposition (`forensics.py:173-179`):
   - `len(subgroups) < 2` (or field absent) → `_na("gail_simon", "not a subgroup / effect-modification claim (<2 subgroup estimates)")`. **This is the common case** — a paper making no subgroup claim yields no `subgroups` records, so the check declares `not_applicable` and never counts as a pass. Fires rarely and honestly, exactly as required.
   - ≥2 subgroups declared but **<2 have an extractable SE or CI**, or the subgroups report **mixed metrics** (not comparable) → `{status:"skipped"}` (malformed/insufficient — has the structure but can't run; distinct from out-of-domain, per `forensics.py:19`).
   - ≥2 subgroups with a shared metric and derivable SE → run.
2. **Standardize (SE from CI when absent, exact — never imputed).** For ratio metrics (`OR|RR|HR`) work on the log scale: `D_i = ln(effect_i)`, `se_i = (ln(ci_high_i) − ln(ci_low_i)) / (2·1.959964)`. For difference metrics (`MD|SMD|RD`): `D_i = effect_i`, `se_i = (ci_high_i − ci_low_i)/(2·1.959964)` (Cochrane 6.3, the same CI→SE rule PRD-10 F10.1 uses). A subgroup with neither `se` nor a CI → dropped and listed; if <2 remain → `skipped`.
3. **Interaction test (quantitative HTE — Cochran's Q across subgroups).** `w_i = 1/se_i²`; `D̄ = Σw_i·D_i / Σw_i`; `Q = Σ w_i·(D_i − D̄)²`; `df = k−1`; `p_int = scipy.stats.chi2.sf(Q, df)`. (For `k=2` this is exactly the standard 2-subgroup interaction test `(D_1−D_2)²/(se_1²+se_2²)` on 1 df — asserted in tests.) **ponytail:** this is the same Cochran's Q as PRD-10's `pool_dl`, but computed inline (~4 lines) rather than importing `metaanalysis.py` — `forensics.py` is deliberately a flat, self-contained module of exact statistical implementations with no internal cross-imports (only `scipy`+`math`, `forensics.py:26-28`); coupling the forensic core to the meta-analysis primitive and its abstain semantics for four lines of shared math is not worth it. `# ponytail: inline Q, not import metaanalysis — keep forensics.py self-contained; revisit only if a third caller appears.`
4. **Gail-Simon qualitative-interaction test (sign-flip).** `t_i = D_i/se_i`; `Q⁺ = Σ t_i²·[t_i>0]`, `Q⁻ = Σ t_i²·[t_i<0]`; statistic `Q_min = min(Q⁺, Q⁻)`. Null tail (exact, closed-form — Gail & Simon 1985 eq.): `p_qual = Σ_{i=1}^{k−1} C(k,i)·2^{−k}·chi2.sf(Q_min, i)`. (Deterministic; no seed. Sanity: `k=2, Q_min=2.706 → p_qual≈0.05`, reproducing the published critical value — see RQ-E51.)
5. **Verdict (typed severity; the reviewer's judgment, computed not asserted).**
   - `p_int ≥ alpha` and a modification is claimed → **`weak`, severity 2**: "the apparent subgroup difference is not significant (interaction p = {p_int:.3g}); the claim that the effect differs in {S} is consistent with chance — a spurious subgroup finding." (The headline catch; feeds `n_warn`, `audit.py:312`.)
   - `p_int < alpha` but `p_qual ≥ alpha` and the paper claims a *qualitative flip* → **`weak`, severity 2**: "subgroup effects differ in magnitude (interaction p = {p_int:.3g}) but not in direction (Gail-Simon p = {p_qual:.3g}); the 'opposite effect in {¬S}' over-claims a qualitative interaction the data do not support."
   - `claim_direction` given and the computed sign in the claimed-favored subgroup **contradicts** it → **`inconsistent`, severity 3**: a code-proven direction contradiction (rides the auditor's severity-≥3 cap to ≤20%, `audit.py:353-354`), the subgroup analog of statcheck's decision-flip (`forensics.py:79-82`).
   - `p_int < alpha` (and `p_qual < alpha` if a qualitative flip is claimed) → **`ok`, severity 0**: "subgroup effects genuinely differ (interaction p = {p_int:.3g}{'; qualitative interaction confirmed, Gail-Simon p = '+p_qual if claimed})."
   - No modification claim + no significant interaction → **`ok`, severity 0** (nothing over-claimed).
6. **Return** the flag envelope verbatim (§2), carrying `span` (the modification-claim / primary-subgroup sentence, so it survives the auditor's grounding guard `audit.py:305` *without editing that line* — the guard keeps any flag with a `span`) plus `subgroup_spans` (all transcribed subgroup sentences) and the numeric `interaction`/`qualitative` blocks for the render.

**Epistemic guardrails.**
- **Strict applicability gate** — `not_applicable` off-domain (the default for non-subgroup claims), never scored as a pass (`forensics.py:225-228`, `debit` counts it separately, `forensics.py:241-258`). This is the F3.8/RQ-E38 discipline applied to a new check.
- **Exact-span extraction, never a model guess of the statistics** — the model transcribes each subgroup's `label, effect, CI/SE, metric` + the exact source sentence (F37.2); the arithmetic (Q, Gail-Simon, the CI→SE conversion) is 100% code. A subgroup without a locatable reported effect is dropped and listed, not imputed (`no fabricated confidence`).
- **Verdict typed, never a fabricated confidence** — `p_int`/`p_qual` are `scipy.stats.chi2.sf` outputs; severity is a rule over them; no model number enters the flag.
- **Deterministic / reproducible** — byte-identical for identical inputs; **no bootstrap, so no seed** (the Gail-Simon null tail and Cochran's Q are closed-form). If a future variant adds a bootstrap CI on the interaction magnitude, that component alone is seeded ≥20 (OQ-2) — v1 does not.
- **Runs in CODE, not prose** (statcheck/GRIM lineage, `forensics.py:1-6`) — the model never adjudicates whether subgroups differ; it only reads the numbers.

**Required experiment — RQ-E51** (§ below).

**Acceptance + ONE runnable check.**
(a) two subgroups, effects clearly non-overlapping opposite signs with tight CIs → `status:"ok"` (or `inconsistent` sev 3 if `claim_direction` contradicts) with `interaction.p < 0.05`; (b) two subgroups with overlapping CIs but the paper claims "works better in S" → `status:"weak"`, severity 2, detail names the non-significant interaction; (c) one subgroup (or field absent) → `status:"not_applicable"`; (d) two subgroups both missing SE and CI → `status:"skipped"`; (e) `k=2` interaction Q equals `(D_1−D_2)²/(se_1²+se_2²)` within 1e-9.
**Runnable check:** `pytest tests/test_forensics.py::test_gail_simon_gate_and_verdict`.

**Effort** M · **Deps** scipy (present), F37.2 for the live path (the pure function is testable standalone with fixture dicts).

---

### F37.2 — Subgroup transcription seam in the auditor (`agents/audit.py`)

**Problem & evidence.** `gail_simon` needs subgroup effect records with exact spans, but the auditor's extraction tool (`_EXTRACT_TOOL`, `audit.py:32-47`) transcribes only `claims / tests / descriptives / designs / p_values` — there is no slot for "effect X [CI] in subgroup A vs effect Y [CI] in subgroup B." Without it, the forensic can never fire on a real paper. The extraction discipline is fixed by `_EXTRACT_SYS` (`audit.py:49-54`): the model *transcribes*, never computes, and treats the document as untrusted DATA.

**Design.** Two additive edits, no behavior change to any existing field:
- Add to `_EXTRACT_TOOL.input_schema.properties` (`audit.py:47`) a `subgroups` array: `{label:str, effect:number, ci_low:number, ci_high:number, se:number, metric:enum['MD','SMD','RD','OR','RR','HR'], n:integer, span:string}` — transcribed **only when the paper reports an effect estimate in ≥2 subgroups of one analysis AND states or implies the effect differs by subgroup**. Also add an optional `subgroup_claim:{favored_label:str, direction:'+'|'-'}` capturing which subgroup the paper says benefits (feeds `claim_direction`).
- Add ONE clause to `_EXTRACT_SYS`: "If — and only if — the paper reports a treatment/exposure effect in **two or more subgroups of the same analysis** and claims (or implies) the effect **differs by subgroup** (effect modification / 'works better in …'), transcribe each subgroup's effect estimate, its CI or SE, the metric, and the exact sentence. Do NOT compute an interaction; do NOT invent subgroups; if the paper makes no subgroup-difference claim, leave `subgroups` empty." This preserves the transcribe-only + prompt-injection posture (`audit.py:53-54`).
- The `_run_all_raw` dispatch branch (F37.1, `forensics.py:196-222`) reads `ex.get("subgroups")`; the flag flows through `forensics.run_all` → the auditor's `flags` list (`audit.py:305`) → severity counting (`audit.py:311-313`) → `forensic_txt` for the adjudicator (`audit.py:328`) → report (`audit.py:475-479`) with **zero further edits** (a severity-2 spurious-subgroup warning is an ordinary `n_warn`; a severity-3 direction contradiction rides the existing code-proven-failure cap, `audit.py:353-354`).

**Epistemic guardrails.** Extraction is transcribe-only and the paper stays DATA (`_EXTRACT_SYS` unchanged in posture); the "only when a subgroup-difference claim is present" instruction is what keeps the applicability gate honest at the source — the model does not manufacture subgroup structure to test. The forensic's own gate (F37.1) is the backstop: even if the model over-emits, `<2` comparable records → `not_applicable`/`skipped`, never a pass.

**Required experiment.** The extraction seam is covered by RQ-E51's off-domain abstention leg (a non-subgroup paper must yield `not_applicable`) and by the auditor's existing extraction discipline; no separate seeded experiment (wiring over a tested unit).

**Acceptance + ONE runnable check.** Feeding `forensics.run_all` a `stats_extracted` dict with a 2-subgroup `subgroups` block produces exactly one `gail_simon` flag carrying a `span`; a dict with no `subgroups` key produces no `gail_simon` flag (and `debit` reports it absent, not passed). **Runnable check:** `pytest tests/test_forensics.py::test_gail_simon_dispatch_and_grounding` (asserts the flag appears with a span, survives the `audit.py:305`-style grounding filter, and is absent when `subgroups` is empty).

**Effort** S · **Deps** F37.1.

---

### Required experiment — RQ-E51 (register in `docs/RESEARCH_QUALITY_PROGRAM.md`)

**Hypothesis.** The `gail_simon` forensic (a) reproduces the published Gail-Simon qualitative-interaction test statistic and its critical values within numeric tolerance, and (b) abstains correctly (`not_applicable`/`skipped`) when subgroup data are absent or insufficient — so it can be trusted to flag spurious subgroup claims without false positives on the ~99% of claims that are not subgroup claims.

**Metric.**
- **Part A — numeric reproduction (deterministic, no seed; the go/no-go gate).** (i) **Published critical-value table** — Gail & Simon (1985) Table 1 gives, for α=0.05, critical values `c` for `Q_min` at `I=2..6` subgroups: `≈{2:2.71, 3:4.23, 4:5.43, 5:6.50, 6:7.48}`. Assert the closed-form null tail `Σ_{i=1}^{I-1}C(I,i)2^{-I}·chi2.sf(c,i)` returns `p ≈ 0.05` at each tabulated `c` within `±0.005`. (ii) **Worked example** — reproduce the qualitative-interaction verdict on a published effect-modification dataset with reported subgroup effects + CIs (default: the Gail & Simon 1985 NSABP breast-cancer subgroups, or an equally-documented published fixture per OQ-1): assert `Q_min` and `p_qual` match the published value within `±2%` and the verdict is `ok` (genuine qualitative interaction). (iii) **Interaction-Q identity** — for `k=2`, assert `Q == (D_1−D_2)²/(se_1²+se_2²)` within `1e-9`.
- **Part B — off-domain / negative abstention (deterministic).** On a labeled set of ≥15 real transcribed claims of which **most are not subgroup claims** (whole-sample causal/correlational/descriptive) plus a few subgroup-structured-but-SE-missing cases: assert the forensic returns `not_applicable` on every non-subgroup input and `skipped` on every insufficient-SE input — **zero `ok`/`weak`/`inconsistent` false fires off-domain**.
- **Part C — stochastic (only if a bootstrap variant is built).** v1 has **no stochastic component**, so no ≥20-seed sweep is required (like PRD-34 RQ-E48 / PRD-10 F10.4 Part A — a deterministic numeric gate). If OQ-2's optional bootstrap interaction-magnitude CI is added later, that component alone runs ≥20 seeds, mean±95%CI, and gates only the CI, not the verdict.

**Gate.** Part A numeric match (critical-value table AND worked example AND k=2 identity) **AND** Part B correct abstention (zero off-domain false fires) → the forensic may emit flags into the auditor under Balanced autonomy. Until the gate passes, the flag ships **advisory-only** (rendered with a `candidate` label; it does not feed the severity cap `audit.py:353-354`, only the warn count). Failing Part A is a **stop-the-line bug** (a wrong forensic is worse than none, `CLAUDE.md §4`).

**Sandbox.** `experiments/exp_gail_simon.py` — embeds the published critical-value table + worked-example fixture + the off-domain claim set; `__main__` prints PASS/FAIL per part. Results → `results/FINDINGS.md#RQ-E51`. Reuses the deterministic-fixture-oracle posture (`CLAUDE.md §4`).

---

## 4. Sequencing (interface-first → fill)

1. **M0 (hour 1, keeps the repo runnable):** land `gail_simon(...)` in `forensics.py` as a typed stub returning `_na("gail_simon", "stub")`, and add the empty `subgroups` branch to `_run_all_raw` (guarded so an empty/absent field is a no-op). `run_all`/`debit`/the auditor are unaffected (the stub yields `not_applicable`, dropped by `run_all` `forensics.py:237-238`). Nothing regresses; the extraction tool can gain its `subgroups` slot in parallel.
2. **F37.1 core** — interaction Q + standardization (CI→SE) + the applicability gate. This is the spine; verify against RQ-E51 Part A(iii) k=2 identity immediately.
3. **RQ-E51 Part A** — critical-value table + worked example. **Do not proceed past a red gate.**
4. **F37.1 verdict logic** — the `ok`/`weak`/`inconsistent` severity rules + Gail-Simon qualitative tail.
5. **RQ-E51 Part B** — off-domain abstention on the labeled claim set.
6. **F37.2** — wire the `subgroups` slot into `_EXTRACT_TOOL`/`_EXTRACT_SYS`; the flag now fires on real audits through the unchanged render path.

---

## 5. Test plan

| Check | File::name | Asserts |
|---|---|---|
| Gate + verdict | `tests/test_forensics.py::test_gail_simon_gate_and_verdict` | `<2` subgroups → `not_applicable`; missing-all-SE → `skipped`; overlapping-CI + modification claim → `weak` sev 2; clean opposite-sign → `ok`; `claim_direction` contradiction → `inconsistent` sev 3 |
| Dispatch + grounding | `tests/test_forensics.py::test_gail_simon_dispatch_and_grounding` | a `subgroups` block in `run_all` input yields one `gail_simon` flag with a `span` (survives the `audit.py:305` grounding filter); absent `subgroups` → no flag; `debit` counts `not_applicable` separately, never as passed |
| k=2 interaction identity | `tests/test_forensics.py::test_gail_simon_k2_matches_closed_form` | interaction `Q == (D1−D2)²/(se1²+se2²)` within 1e-9; log-scale handling for ratio metrics |
| RQ-E51 Part A | `experiments/exp_gail_simon.py` `__main__` | Gail-Simon critical-value table (I=2..6) reproduces `p≈0.05` within ±0.005; worked example within ±2% |
| RQ-E51 Part B | `experiments/exp_gail_simon.py` `__main__` | zero off-domain false fires on the labeled non-subgroup / insufficient-SE set |
| Regression | existing `tests/test_forensics.py` (`test_run_all_returns_flagged_only`, `:33-43`) | unchanged — adding the `subgroups` branch does not alter any existing flag; `run_all` still drops `not_applicable`/`skipped` |

---

## 6. Open questions

- **OQ-1 (worked-example fixture selection — blocks RQ-E51 Part A(ii)).** The critical-value-table gate [A(i)] and k=2 identity [A(iii)] are fully reproducible from published constants alone. The *worked example* needs one published effect-modification dataset with reported subgroup effects + CIs and a documented Gail-Simon verdict. **Recommended default:** the Gail & Simon (1985) NSABP breast-cancer subgroups from the original paper (the canonical fixture); fall back to a documented `qualitative-interaction` example from a subgroup-methods review (Wang 2007 / Sun 2012) if the raw NSABP numbers are not cleanly recoverable. Non-blocking for A(i)/A(iii), which alone can pass the gate.
- **OQ-2 (bootstrap magnitude CI — recommend deferring).** v1 is fully closed-form (deterministic, no seed). A bootstrap CI on the interaction *magnitude* (`D_1−D_2`) would add a confidence interval to the "how much do subgroups differ" report but needs its own ≥20-seed RQ-E51 Part C. **Recommended default:** ship deterministic-only (the p-values are the verdict; the magnitude is descriptive); add the bootstrap only if a downstream surface asks for a magnitude CI.
- **OQ-3 (Lane-4 render — informational, no contract).** The flag renders through the auditor's existing generic forensic-flag loop (`audit.py:475-479`) and any surface that already shows the "Deterministic checks" section — **no new route, no new tab** (per the recent "integrate into past-paper review surfaces, no new tabs" direction). **Recommended default:** generic render; a dedicated subgroup-forest element, if ever wanted, is a pure Lane-4 presentation choice needing no FC.
- **OQ-4 (severity of a spurious-subgroup claim — recommend `weak`/sev 2).** A non-significant interaction under a modification claim is a soft failure (the evidence for HTE is weak), so it maps to `weak`/severity 2 (feeds `n_warn`, informs the calibration prior `audit.py:312,320`), reserving `inconsistent`/severity 3 (the ≤20% cap) for a code-proven *direction contradiction* only. **Recommended default:** as stated — mirrors p_curve's `weak` for p-hacking vs statcheck's `inconsistent` sev 3 for a decision flip.
