# PRD-38 — Meta-research self-study

> **Owner lane:** 3 (Intellectual engine) provides · **4 (Legibility) renders** · **Status:** DRAFT-for-implementation (2026-07-13) · **Autonomy:** Advisory — a rendered credibility artifact, read-only aggregation, drives **no** belief update, anchor, or dispatch. The false-improvement gate (RQ-E52) must pass before any trend line is shown as a *credibility claim*. · **Depends-on:** FC-17 (`memory/predictions.py` prediction ledger — **SPECCED PRD-24, NOT yet built** → consumed as a contract, import-guarded), `persona/analysis/calibration.py` (existing replication-prior curve — reuse), `persona/analysis/trajectory.py` (settling/velocity primitive — reuse), `memory/verified.py::entries` (revisit history — live), FC-18 (`memory/blocklist.py` — SPECCED PRD-25, guarded), FC-15 (`agents/verifier_monitor.py` — SPECCED PRD-22, guarded), FC-8 `ops_dir/gate_decisions.jsonl` (live shared ledger), FC-3 `kg.anchored_beliefs` (PRD-27, guarded). Backlog #118.
> **Governed by PRD-00 §4/§6 and §8 reconciliation. Where this body disagrees with §4/§6, §4/§6 win.**

---

## 0. Summary + capability unlocked

Persona already *self-corrects* (the revisit loop flips a verified result to weakened/refuted; a human adjudicates a contradiction) and, with PRD-24, will *keep score* against pre-registered priors (Brier). What it does **not** do is **turn that record on itself as a dataset and write an honest self-assessment.** PRD-38 adds exactly that: a pure, provenance-grounded **self-study report** that reads Persona's own track record — the prediction ledger (FC-17), the verified/revisit history (`verified.jsonl`), the curated reversal record (`results/FINDINGS.md` via the FC-18 blocklist), and the gate ledgers — and answers, with a number or a citation behind every line:

| Section | Question answered | Source (already computed / recorded) |
|---|---|---|
| `brier` / `by_kind` | *How well-calibrated were my forward predictions?* | FC-17 `predictions.brier()` (passthrough — not recomputed) |
| `calibration_trend` | *Is my calibration improving, flat, or degrading over time?* | **the one computed signal** — a REAL trend test over FC-17 `outcome_pairs()` (RQ-E52 gated) |
| `reversals` | *Which beliefs/predictions did I hold and then reverse — and why?* | `verified.jsonl` status transitions + FC-18 blocklist `findings_ref` + confident-wrong FC-17 pairs |
| `component_value` | *Which components (membrane / anchoring / verifier) actually paid off?* | echoes ALREADY-VALIDATED experiment gates (E10/E9/P6/E07b) + runtime `gate_decisions.jsonl` counts + FC-15 scorecard |
| `honest_gaps` | *Where was I wrong, or where does the evidence not yet support the claim?* | `FINDINGS.md` reversals + "still-pending" gate list, surfaced PROMINENTLY |

**Capability unlocked:** the ultimate credibility artifact — a researcher that *measures itself* and publishes the measurement, warts first. It operationalizes `CLAUDE.md` §2 ("no fabricated confidence… never a model self-report") and §1 ("REVERSALS are the most valuable thing you produce — surface them, never hide them") on Persona's *own history*. The report introduces **no new metric and no new cut-point** (the FC-21 frontier precedent, PRD-00 §9: "no new metric — each cell echoes its source's gate label"): every number is a passthrough of a validated signal, and the single genuinely-computed quantity — the calibration trend — is a standard statistical test that **abstains ("insufficient history") rather than manufacture a rosy claim** on thin data, and is gated so a favorable trend is never shown until RQ-E52 proves it is not spurious.

---

## 1. File ownership (disjoint)

| File | New? | Lane | Role |
|---|---|---|---|
| `persona/analysis/self_study.py` | **New** | **3** | Provides **FC-29**: `report(...)`, the pure `calibration_trend(pairs, ...)` unit, and the reversal/component/gap collectors. Offline, no network, injectable deps (`ops_dir=`, `kg=`) for tests. Lane 3 owns `persona/analysis/*` (PRD-00 §3). |
| `experiments/exp_meta_self_study.py` | **New** | **3** | RQ-E52 seeded harness. **Lane 3 authors the providing lane's RQ sandbox** (PRD-00 §8 cross-cutting ruling: "a feature's RQ sandbox `exp_*.py` + its unit test are authored and owned by the providing lane"). |
| `tests/test_self_study.py` | **New** | **3** | Unit test encoding the FC-29 contract (Lane 3, per the same ruling). |
| `persona/api/app.py` | edit (**new route only**) | **4** | One route `GET /api/persona/{pid}/self_study` (thin pass-through, mirrors `verified_ledger` at `app.py:295`). |
| `persona/api/static/index.html` | edit (**new surface only**) | **4** | One self-study surface on the existing Epistemic tab (no new tab), rendering the FC-29 dict. |
| `persona/api/static/js/*.js` | edit (**new render fn only**) | **4** | Fetch + render the report; append to the Epistemic-tab render path. |
| `tests/ui_legibility_smoke.cjs` | edit (**extend**) | **4** | Add the `PERSONA_WORKERS=0` browser smoke for the surface (cross-cutting smoke = Lane 4, per PRD-00 §8). |

**Boundary files owned by other lanes — READ-ONLY here, decoupled by FC (do NOT edit):**
- `persona/memory/predictions.py` (Lane 2, **FC-17**, PRD-24 pending) — `brier()`, `outcome_pairs()`, `predictions()`, `open_predictions()`. Import-guarded.
- `persona/memory/verified.py` (Lane 2) — `entries()` (live). Read only.
- `persona/memory/blocklist.py` (Lane 2, **FC-18**, PRD-25 pending) — `entries()` for `findings_ref` reversals. Import-guarded.
- `persona/agents/verifier_monitor.py` (Lane 1, **FC-15**, PRD-22 pending) — `scorecard()`. Import-guarded.
- `persona/memory/kg.py` (Lane 2) — **FC-3** `anchored_beliefs()` (PRD-27 addition, guarded). Read only.
- `persona/analysis/calibration.py`, `persona/analysis/trajectory.py` (Lane 3, same lane, live) — **imported, not edited** (reuse the fitted curve + the settling primitive).

The report is a strict downstream reader. No source file owned by another lane is modified; the two cross-lane touches (route + surface) are Lane 4's own owned slices.

---

## 2. FCs provided / consumed

### PROVIDES — **FC-29 (Lane 3), new `persona/analysis/self_study.py`**

```python
self_study.report(*, ops_dir=None, kg=None, window=None) -> dict
# ops_dir : ops dir for the FC-17 ledger + gate ledger; defaults to get_persona().paths.ops_dir when None.
# kg      : belief store for anchored/verified reads; defaults to memory.membrane.get_kg() when None.
# window  : optional (start_iso, end_iso) to restrict resolved predictions/reversals by date; None = all history.
# -> {
#   n_predictions: int,               # FC-17 predictions() count           (0 if ledger absent)
#   resolved: int,                    # FC-17 outcome_pairs() count
#   brier: float | None,              # FC-17 brier()["brier"]; None if 0 resolved OR ledger absent
#   by_kind: dict,                    # FC-17 brier()["by_kind"] passthrough (contradiction/hypothesis)
#   calibration_trend: {              # the ONE computed signal — RQ-E52 gated (advisory badge until passed)
#       test: str,                    # "mann_kendall+ols" | "insufficient"
#       slope: float | None,          # OLS slope of per-prediction squared-error (p-y)**2 vs resolved-time index
#       ci: [float, float] | None,    # bootstrap 95% CI on slope (>=20 resamples)
#       tau: float | None,            # Mann-Kendall tau
#       p_value: float | None,        # Mann-Kendall two-sided p
#       direction: str,               # "improving" | "degrading" | "flat" | "insufficient history"
#       sufficient: bool, n: int,     # sufficient False -> direction forced "insufficient history"
#   },
#   reversals: [{                     # PROMINENT — never truncated below the fold (CLAUDE.md §1)
#       id: str, before: str, after: str, trigger: str,
#       findings_ref: str | None, at: str, source: str,   # source in {verified,blocklist,prediction}
#   }],
#   component_value: [{               # echoes EXISTING gate/experiment labels — NO new causal metric
#       component: str,               # "membrane" | "anchoring" | "verifier"
#       verdict: str,                 # the validated gate's own label (e.g. "E10 detect 1.000")
#       gate: str, source: str,       # RQ id / ledger path
#       provenance: str,              # "TESTED" (validated experiment) | "READ" (runtime ledger count)
#       sufficient: bool,             # runtime evidence thin -> rests on the experiment, says so
#   }],
#   honest_gaps: [{gap: str, detail: str, findings_ref: str | None, source: str}],
#   provenance: {                     # per-signal availability + origin (graceful-degradation map)
#       predictions|verified|blocklist|verifier_monitor|gate_ledger|anchors:
#           {available: bool, source: str, kind: str}
#   },
#   generated_at: str,                # UTC ISO seconds
# }

self_study.calibration_trend(pairs: list[dict], *, min_n: int = _MIN_TREND_N) -> dict
# Pure. pairs = FC-17 outcome_pairs() rows [{p,y,resolved_at,...}] ordered by resolved_at.
# The RQ-E52 unit: returns the calibration_trend sub-dict above. Below min_n -> sufficient False,
# direction "insufficient history". Claims "improving"/"degrading" ONLY when the trend is
# statistically significant AND the slope CI excludes 0 (conservative — controls false-improvement).
```

**Consumes (all read-only, import-guarded where pending):** FC-17 (predictions, PRD-24), FC-18 (blocklist, PRD-25), FC-15 (verifier_monitor, PRD-22), FC-3 (`kg.anchored_beliefs`, PRD-27), FC-8 `gate_decisions.jsonl` (live), `verified.entries()` (live), `analysis/calibration.py` + `analysis/trajectory.py` (same-lane, live). **No FC change to any consumed contract** — pure downstream aggregation.

### PROVIDES — Lane-4 render route (thin pass-through, no new contract)
`GET /api/persona/{pid}/self_study` → `with context.use(_p(pid)): return self_study.report()`. Mirrors `verified_ledger` (`app.py:295-301`). No new persona state, no FC.

### CONTRACT CHANGE PROPOSAL
**None.** FC-29 is the single pre-assigned new contract; every consumed signature is frozen. If a load-bearing need for a new contract emerges, it is surfaced as **OQ-4** for the master — not minted here (task hard rule).

---

## 3. Features

### F38.1 — `self_study.report(...)` pure self-study aggregator (FC-29)

**Problem & evidence.** The signals a credibility self-assessment needs already exist but are scattered and never joined: forward-prediction Brier will live in `predictions.brier()` / `outcome_pairs()` (PRD-24 FC-17, PRD-00 §9 line 187); the verified/revisit reversal record is in `verified.jsonl` — `verified.entries()` (`verified.py:35`) carries `status ∈ {verified,weakened,refuted}` with a `revisits` counter and `last_revisit` set by the revisit loop (`verified.py:74-77`); the *curated* reversal record is `results/FINDINGS.md`, surfaced structurally by the FC-18 blocklist whose every row "carries a `findings_ref`" (PRD-00 §9 line 188); component evidence is in the shared `gate_decisions.jsonl` ledger (FC-8, PRD-00 §4 line 68) and the FC-15 verifier scorecard (line 85). No module reads its own history as a dataset — grep: `analysis/` has `calibration.py`, `trajectory.py`, `forensics.py`, `engine.py`, none aggregating the track record. Backlog #118 asks for the join, once, honestly.

**Design.** New file `persona/analysis/self_study.py`. `report(*, ops_dir=None, kg=None, window=None)` assembles the FC-29 dict, each block individually try-guarded and reflected in `provenance.<signal>.available`:

1. `ops_dir = ops_dir or get_persona().paths.ops_dir`; `kg = kg or get_kg()` (`membrane.get_kg`, `membrane.py:18`). Either absent → that block degrades, never raises.
2. **Predictions (FC-17, guarded).** `try: from ..memory import predictions` — on `ImportError`/absent ledger: `n_predictions=resolved=0`, `brier=None`, `provenance.predictions.available=False`, note `"no prediction ledger yet"` (PRD-29/PRD-35 degrade-gracefully precedent, PRD-00 §9 line 198/210). Else: `n_predictions=len(predictions.predictions(ops_dir))`; `pairs = predictions.outcome_pairs(ops_dir)` (filtered by `window`); `brier=predictions.brier(ops_dir)["brier"]` if `pairs` else `None`; `by_kind` passthrough. **Never recompute Brier** — it is FC-17's own output.
3. **`calibration_trend = calibration_trend(pairs)`** (F38.2) — the one computed signal.
4. **Reversals (exhaustive, deterministic — RQ-E52 recall gate).** Union of three real sources, de-duplicated by `id`:
   - `verified.entries()` where `status in {"weakened","refuted"}` **and** `revisits>0` → `{id:key, before:"verified", after:status, trigger:"revisit", findings_ref:None, at:last_revisit, source:"verified"}`.
   - FC-18 `blocklist.entries()` (guarded) → each `findings_ref` reversal from `FINDINGS.md` (the RQ-CAL/E7/Confound-A supersessions) → `source:"blocklist"`, `before/after` from the entry.
   - FC-17 `outcome_pairs()` with `p>=0.7` and `y==0.0` (a confident prediction that resolved wrong) → `source:"prediction"`, `trigger:"resolution"`.
   - **Sorted most-recent-first; NEVER truncated below a display cap in the data layer** (the UI may paginate, but `report()` returns all — CLAUDE.md §1 "surface them, never hide them").
5. **Component value (echoes existing gate labels — NO new metric).** For each of `membrane`/`anchoring`/`verifier`, emit a row whose `verdict` is a *validated experiment's own label* plus a runtime ledger count, `provenance`-typed:
   - `membrane`: `TESTED` — E10 adaptive switch (`detect 1.000, false-strict 0.000`, FINDINGS.md:94) + E07b selective-verify GO (FINDINGS.md:542-549); `READ` — `gate_decisions.jsonl` rows `gate="membrane"` admit/skip counts.
   - `anchoring`: `TESTED` — P6 (`exp_poisoning.py`, anchor RETAINED under 24-claim/2-lab poison, FINDINGS.md:304-312) + E9 escape-hatch (FINDINGS.md:97); `READ` — `kg.anchored_beliefs()` count (FC-3, guarded).
   - `verifier`: `TESTED` — E07b (selective verify 0% false-conflict, FINDINGS.md:542); `READ` — FC-15 `verifier_monitor.scorecard()` reversal-rate (guarded → "not yet computed" if absent).
   - Thin runtime ledger → `sufficient=False`, verdict text says "resting on validated experiment E10 (TESTED); runtime evidence still thin". **No causal "paid off" number is invented** — the row *cites* the gate that earned the claim (FC-21 precedent: "each cell echoes its source's gate label", PRD-00 §9 line 198).
6. **Honest gaps (surfaced prominently).** Curated-but-code-collected: the FC-18 blocklist reversals (each `findings_ref`) plus the standing "still-pending / stays-descriptive" record — E5 trajectory stays descriptive (FINDINGS.md:290-295), E7 VoI ill-posed reversal (FINDINGS.md:279-288), E03a hybrid gate fails (FINDINGS.md:464-482), the "still pending" list (FINDINGS.md:99-102). Each row carries its `findings_ref` so a skeptic can trace it.
7. **`generated_at`** = UTC ISO seconds.

**Epistemic guardrails.**
- **Every number traces to a source; none is fabricated favorable self-assessment.** `brier`/`by_kind` are FC-17 passthroughs; component verdicts cite an RQ id or a ledger path; the only computed quantity (trend) is a standard test with a published rule (F38.2). No model runs in this file (mirrors `calibration.py`/`trajectory.py` — "no model in this file").
- **Reversals & failures are surfaced PROMINENTLY, never buried** (CLAUDE.md §1). `reversals` and `honest_gaps` are top-level keys returned in full; the UI (F38.3) renders them above the fold.
- **Read-only — NEVER mutates a belief.** No KG write, no `verified`/`predictions` append (unlike PRD-24's route, this report does *not* even call `sync_resolutions` — it reads whatever is already resolved, keeping the surface a pure observer). Autonomy: Advisory.
- **Provenance-typed.** Every component/reversal row carries `provenance` (`TESTED` for a validated experiment, `READ` for a runtime ledger count) and `source`; a validated-experiment claim is never shown with the authority of an un-run runtime metric, nor vice-versa.
- **Degrades per-signal, never 500s.** FC-17/FC-18/FC-15/FC-3 all pending → the report still returns (Brier `None`, reversals from `verified.jsonl` only, verifier row "not yet computed"), each gap flagged in `provenance`. No import failure crosses the boundary (PRD-29/PRD-35 import-guard precedent).

**Required experiment.** **RQ-E52** — see F38.2 (the trend-validity + reversal-recall gate covers this feature's only load-bearing logic; the rest is passthrough aggregation).

**Acceptance + ONE runnable check.**
- Acceptance: for a fixture ledger, every passthrough field equals its source read independently; `reversals` contains every seeded reversal (recall 1.0); a missing FC sets `provenance.<x>.available=False` without raising; the report performs zero writes.
- Runnable check: `python -m pytest tests/test_self_study.py -q` — asserts (a) `brier == predictions.brier(ops_dir)["brier"]`; (b) a seeded `verified` refutation + a blocklist `findings_ref` both appear in `reversals`; (c) FC-17/FC-18 absent ⇒ report returns with `brier is None`, `provenance.predictions.available is False`, no raise; (d) `kg.stats()` unchanged after two `report()` calls (read-only).

**Effort.** M (one pure module ~180 lines + guards; the trend unit is the load-bearing part).

**Deps.** `verified.py`, `calibration.py`, `trajectory.py`, `gate_decisions.jsonl` (all live → real immediately). FC-17/FC-18/FC-15/FC-3 (pending → fixture/guarded, zero-change pickup when they land).

---

### F38.2 — Calibration-trend test (the one computed signal, RQ-E52)

**Problem & evidence.** "My calibration is improving" is the single claim in this report that is *not* a passthrough — it is an inference over the chronological outcome series, and inference is where an honest system most easily lies to itself. `results/FINDINGS.md` already contains the cautionary case: RQ-CAL's "Honest reversal" (FINDINGS.md:668-674) — ECE *said the baseline was perfect and the improvement worse*; the flattering metric was wrong, and only a proper scoring rule + a real resolution test caught it. E5 (FINDINGS.md:290-295) is the other half: with only 1 of 32 beliefs converged by the cutoff, the trajectory forecast **stays descriptive** rather than assert a trend on thin data. The existing `trajectory.settling()` (`trajectory.py:41`) computes velocity/direction but its thresholds are explicitly `PLACEHOLDER` heuristics (`trajectory.py:19-22`) — *not* a validated trend test, and it warns as much. So a trend claim here needs a REAL statistical test with an abstention rule, gated before it is shown as credibility.

**Design.** `calibration_trend(pairs, *, min_n=_MIN_TREND_N)` — pure, deterministic, no model:
- Order `pairs` by `resolved_at`; the per-prediction series is the squared error `e_i = (p_i - y_i)**2` (lower = better-calibrated). "Calibration improving" ⇔ `e_i` trending **down** over time ⇔ negative slope.
- **Two complementary tests** (a decreasing-error claim must survive both):
  1. **OLS slope** of `e_i` on the time-index, with a **bootstrap 95% CI** (≥20 resamples over the pairs). Improving requires `ci_upper < 0`.
  2. **Mann-Kendall** trend test (non-parametric, no distributional assumption — the right default for a short, noisy series; avoids the `settling()` placeholder-threshold trap). Improving requires `tau < 0` and `p_value < 0.05`.
- **Direction rule (conservative, controls false-improvement):**
  - `n < min_n` → `sufficient=False`, `direction="insufficient history"`, `test="insufficient"`, numeric fields `None`. (The E5 discipline — abstain, don't assert.)
  - else `sufficient=True`; `direction="improving"` **iff** (OLS CI excludes 0 downward **AND** MK significant-decreasing); symmetric for `"degrading"`; otherwise `"flat"`.
- `_MIN_TREND_N` is fixed by RQ-E52 (the seed sweep locates the n where abstention correctly flips) — declared once with the RQ citation in a code comment, not guessed.

**Epistemic guardrails.**
- **Abstain over flatter.** Below `min_n`, "insufficient history" is returned verbatim — never a directional word (the whole point of the gate).
- **One-sided error control.** An "improving" verdict is only issued when *both* tests agree and the CI excludes zero, so a favorable trend that isn't there is not reported (RQ-E52 gate (b), false-improvement ≤ 0.05).
- **Advisory until the gate passes.** Until `ops_dir/rq_e52.passed` exists, the render (F38.3) shows the trend line with a "candidate — RQ-E52 not yet passed" badge and does NOT present it as a credibility claim (PRD-00 §6 discipline; the auditor-likelihood/E6 "gate not passed" label precedent, FINDINGS.md:170-173).

**Required experiment — RQ-E52** (new; the next free id after E51 — register in `docs/RESEARCH_QUALITY_PROGRAM.md` §5).
- **Hypothesis:** the self-study's trend/track-record claims are *valid, not spurious* — on synthetic track-record series with a KNOWN trend and a known reversal set, the report (a) recovers the true trend direction and abstains correctly on thin data, (b) never reports a favorable trend that isn't there, (c) never drops a real reversal.
- **Metric + gate (all three must pass):**
  1. **Trend recovery:** across ≥20 seeds, generate series with a planted trend ∈ {improving, flat, degrading} (Brier decreasing / constant / increasing over resolved-time) at both thin (`n<min_n`) and sufficient (`n≥min_n`) lengths. **Gate: direction recovery accuracy ≥ 0.90 on sufficient series AND `direction=="insufficient history"` on every thin series** (correct abstention == 1.0).
  2. **False-improvement:** on flat and degrading series (no true improvement), **the report claims `"improving"` in ≤ 0.05 of seeds** (95% CI upper bound ≤ 0.05).
  3. **Reversal recall:** each seed plants a known reversal set across the `verified`/`blocklist`/`prediction` stub sources; **`reversals` recall == 1.0** (every planted reversal appears; zero drops), with false-reversal rate reported informationally.
- **Seeds:** ≥20 (`experiments/exp_meta_self_study.py`, seeded; mean ± 95% CI to `/results`). Synthetic-series + fault-style, matching the RQ-E40/E36 "detection AND zero-false" family.

**Acceptance + ONE runnable check.**
- Acceptance: `exp_meta_self_study.py` prints `direction_acc≥0.90 thin_abstain=1.0 false_improve≤0.05 reversal_recall=1.0` over ≥20 seeds (all gates pass).
- Runnable check: `python -m pytest tests/test_self_study.py::test_rq_e52_trend_and_reversals -q` — asserts all three gates on a fixed seed set; and `calibration_trend([...thin...])["direction"]=="insufficient history"`.

**Effort.** M (the experiment + trend unit are the bulk; ~120 lines + harness).

**Deps.** F38.1 (the collector); `numpy`/`scipy` (already in the repo per `calibration.py`/FINDINGS reproduction env). No blocking external dep.

---

### F38.3 — Route + self-study surface (Lane 4)

**Problem & evidence.** The Epistemic tab already hosts calibration/verified surfaces (PRD-15/PRD-24 render there); the self-study is the *longitudinal* sibling of exactly that story and belongs on the same tab, not a new one. The route pattern is settled: `verified_ledger` (`app.py:295-301`) does `with context.use(_p(pid)): return {...}` and returns a plain dict.

**Design.**
- **Route:** `GET /api/persona/{pid}/self_study` in `app.py` — body: `with context.use(_p(pid)): from ..analysis import self_study; return self_study.report()`. Read-only pass-through; no new persona state.
- **Surface:** a `self-study` panel appended to the Epistemic tab (no new tab, per instruction). Layout, in honesty-first order: (1) **Reversals** and **honest gaps** rendered ABOVE the fold (CLAUDE.md §1 — the most valuable output leads, is not collapsed by default); (2) the **Brier** tile + `by_kind`; (3) the **calibration-trend** line, badged "candidate — RQ-E52 not yet passed" until `ops_dir/rq_e52.passed`, and rendered as the honest "insufficient history" state when `sufficient=False` (no fabricated line); (4) the **component-value** rows, each showing its `provenance` (TESTED/READ) and citing its RQ/ledger. Pending signals render as a greyed "— not yet computed" with a tooltip (honest uncertainty, PRD-00 §5). Motion: none (static panel; PRD-00 §5 "motion only for real state change").

**Epistemic guardrails.** UI renders server fields verbatim — no JS-side trend fitting, no client-side number synthesis (PRD-00 §2 forbids inferring epistemic state in the client; RESEARCH_QUALITY_PROGRAM.md:32 "Never infer epistemic state in the client"). A `TESTED` component verdict and a `READ` runtime count are styled distinctly. The trend line carries its gate badge so a not-yet-validated claim is never shown with credibility authority.

**Required experiment.** Trivial (covered by F38.1/F38.2; the route is a one-line pass-through, the panel presentational).

**Acceptance + ONE runnable check.**
- Acceptance: hitting the route for a seeded persona returns the F38.1 dict; the panel renders reversals/gaps above the fold, the Brier tile, and the trend line (or its "insufficient history"/"candidate" state); no horizontal overflow at 1280/760/390 px.
- Runnable check: extend `tests/ui_legibility_smoke.cjs` (`PERSONA_WORKERS=0`): open Epistemic tab → self-study panel shows the reversals list + Brier tile; assert no horizontal overflow at the three widths.

**Effort.** S (thin route + one panel; reuses the Epistemic-tab idiom).

**Deps.** F38.1/F38.2 (data). Renders against fixtures first (contract-first UI, PRD-00 §7), real once F38.1 lands.

---

## 4. Sequencing (interface-first)

1. **M0 — FC-29 stub.** Land `analysis/self_study.py` with the exact `report(...)`/`calibration_trend(...)` signatures returning a typed empty/fixture dict (all `provenance.*.available=False`), commit-in-place. Lane 4 builds the panel against it from hour 1. Repo stays runnable.
2. **F38.1** — fill the collector against LIVE sources first (`verified.entries()`, `gate_decisions.jsonl`, `calibration`/`trajectory` reuse); FC-17/FC-18/FC-15/FC-3 import-guarded (fixtures until they land). `test_self_study.py` green on the live+fixture path.
3. **F38.2** — `calibration_trend` + `experiments/exp_meta_self_study.py` (RQ-E52). The gate must pass before the trend is shown as a credibility claim (until then: advisory badge). Register RQ-E52 in `RESEARCH_QUALITY_PROGRAM.md` §5.
4. **F38.3** — `GET /self_study` route + Epistemic panel (Lane 4) + browser smoke, against F38.1 fixtures then real.
5. **Zero-change pickup** — when PRD-24 (FC-17), PRD-25 (FC-18), PRD-22 (FC-15), PRD-27 (FC-3 `anchored_beliefs`) land, the guarded paths activate with no code change; flip the fixture test branches to assert the real signals.

Every step leaves the report degrading, never blocking (PRD-00 §5).

---

## 5. Test plan

`tests/test_self_study.py` (Lane 3, new; pytest + FastAPI `TestClient`, reuses the existing KG/ledger fixture harness):
- **Passthrough fidelity:** `brier`/`by_kind`/`n_predictions`/`resolved` `==` FC-17 reads done independently on the same fixture ledger.
- **Reversal recall (RQ-E52 gate c):** a fixture with a `verified` refutation + a blocklist `findings_ref` + a confident-wrong FC-17 pair ⇒ all three appear in `reversals`, correct `source`/`provenance`, none dropped.
- **Trend abstention:** `calibration_trend(thin_pairs)["direction"]=="insufficient history"`, `sufficient is False`; `test_rq_e52_trend_and_reversals` asserts all three gates on a fixed seed set.
- **Component provenance:** each `component_value` row has `provenance ∈ {TESTED,READ}` and a non-empty `gate`/`source`; thin runtime ⇒ `sufficient False` with the "resting on validated experiment" text.
- **Graceful degradation:** FC-17/FC-18/FC-15 absent ⇒ report returns, `brier is None`, `provenance.<x>.available is False`, reversals still populated from `verified.jsonl`, no raise; `kg is None` ⇒ full-degrade card, no raise.
- **Read-only:** `report()` twice leaves `kg.stats()` and the ledger byte-length unchanged (no write, no `sync_resolutions`).
- **Browser smoke:** `tests/ui_legibility_smoke.cjs` (Lane 4) — F38.3 acceptance.
- **No regressions:** `test_predictions.py`/`test_report_card.py` pass unchanged — this PRD only adds a module/route/surface and *imports* (never edits) boundary files.

`experiments/exp_meta_self_study.py` (Lane 3, new, RQ-E52, ≥20 seeds) — the three gates; results + chart to `/results`.

---

## 6. Open questions

1. **OQ-1 (RQ-E52 id).** RQ-E52 is the pre-assigned next-free id after E51 (§6 table ends at E51). Confirm the master registers E52 in `RESEARCH_QUALITY_PROGRAM.md` §5. *Recommended default:* proceed with E52; no other lane impacted (Lane 3 authors its own sandbox per PRD-00 §8).
2. **OQ-2 (`_MIN_TREND_N`).** The abstention threshold is set by the RQ-E52 sweep, not guessed. *Recommended default:* start the sweep at `min_n ∈ {8,10,12}` (mirrors E5's "≥8 needed for a stable estimate", FINDINGS.md:293) and freeze the value the seed sweep validates; declare it once with the RQ citation.
3. **OQ-3 (confident-wrong reversal threshold).** The FC-17 confident-wrong reversal source uses `p≥0.7` (the FC-5 `_P_COMMIT` commit cut-point) and `y==0`. *Recommended default:* import `_P_COMMIT` from `calibrate` by reference (the PRD-33 no-re-declared-constant discipline) rather than hard-code 0.7, so the reversal definition tracks the admission gate. Reversible; disclosed in the render notes.
4. **OQ-4 (new-contract escalation).** If reviewers want component "paid off" expressed as a *causal* contribution (not the current echo-the-validated-gate projection), that needs a counterfactual experiment and likely a new contract — **surfaced for the master, NOT minted here** (task hard rule). *Recommended default:* keep the honest projection (echoes existing gate labels, no new metric — the FC-21 frontier precedent); revisit only if a benchmark shows the echo is insufficient.
