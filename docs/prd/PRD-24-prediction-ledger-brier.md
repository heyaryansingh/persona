# PRD-24 — Prediction ledger + Brier self-score

> **Owner lane:** 2 (+ 4 render) · **Status:** DRAFT-for-implementation (2026-07-13) · **Autonomy:** Balanced — the ledger and its Brier are read-only measurements; they drive **no** belief update, anchor, or dispatch. Predictions are immutable once made. · **Depends-on:** FC-5 (`memory/calibrate.py::admit_decision` — the prior source), PRD-15 (`persona/eval/calibration_report.py::reliability` — reused for ECE/diagram at the render layer), and three existing read surfaces: `memory/verified.py::entries`, `agents/revisit.py` (drives verified transitions), `conflict_reviews.py::summarize_conflict_reviews`. Reuses the hash-chain primitives in `conflict_reviews.py`. **Provides FC-17.**

---

## 0. Summary + capability unlocked

Persona already *self-corrects* (the revisit loop flips a verified result to weakened/refuted; a human adjudicates a contradiction in `conflict_reviews.py`). What it does **not** do is **keep score against a commitment it made *before* it knew the answer.** Today, when a contradiction is flagged or a hypothesis is posed, no prior probability is recorded anywhere durable; when it later resolves, there is nothing to score the earlier belief against. That is the difference between a system that *reacts* and one that is *accountable*.

This PRD adds a small append-only, hash-chained **prediction ledger** (`memory/predictions.py`, in `ops_dir/predictions.jsonl`). At the moment a contradiction or hypothesis becomes *open*, Persona records an **immutable, timestamped prior probability** (its FC-5 `calibrated_p`, or an explicit `p`). When the question later resolves — via the verified-ledger revisit transition, or a `conflict_reviews` human adjudication — a **separate resolution row** is appended (never editing the prior), the prediction is scored, and a running **Brier score + reliability curve** over Persona's own past predictions is maintained. Lane 4 renders it as a sibling of the PRD-15 calibration panel.

**Capability unlocked:** Persona can answer *"of the contradictions I called ≥70% likely to be true refutations, how many actually were?"* — a self-accountability metric a PI can trust, with the anti-cheat property baked into the data structure: **the prior is hash-chained and de-duplicated, so it cannot be edited or re-issued after the outcome is known (no goalpost-moving).** This operationalizes taste/surprise (BUILD_PLAN §3.4 "falsification market") and directly proves `CLAUDE.md` §2 ("no fabricated confidence… never a model self-report") on Persona's *own forward-looking* claims, not just its paper verdicts (which PRD-15 already scores).

**Relationship to PRD-15 (no overlap):** PRD-15 scores verdicts that *already carry a probability on disk* (auditor `history[0].likelihood`, verified-ledger status). PRD-24 covers the gap PRD-15 cannot: **open contradictions and hypotheses that have no recorded prior at all** until this ledger records one at flag-time. PRD-24 *reuses* PRD-15's `reliability()` estimator for the diagram; it does not re-implement it.

---

## 1. File ownership (disjoint)

| File | New? | Lane | Note |
|---|---|---|---|
| `persona/memory/predictions.py` | **New** | 2 | The ledger + scoring. Lane 2 owns `persona/memory/*` (PRD-00 §3). |
| `persona/api/app.py` | edit (**new route only**) | 4 | Add `GET /api/persona/{pid}/predictions`. Lane 4 owns "new routes only" in `app.py` (PRD-00 §3). |
| `persona/api/static/index.html` | edit (**new surface only**) | 4 | New sub-panel under the Epistemic tab, beside the PRD-15 calibration panel. Lane 4 owns "new surfaces only". |
| `tests/test_predictions.py` | **New** | 4 | RQ-E40 property/fault test. Lane 4 owns `tests/*` (new). |
| `experiments/exp_prediction_immutability.py` | **New** | 4 | RQ-E40 seeded harness. Lane 4 owns `experiments/*` (new). |

**Boundary files (read-only import; no editing needed for resolution):**
- `persona/conflict_reviews.py` (Lane 2, same lane) — **imported** for its hash-chain primitives (`_walk_chain`, `_record_sha256`, `_canonical_json`, `_append_line`, `_file_lock`, `LedgerIntegrityError`) and for `summarize_conflict_reviews` / `ConflictVerdict` at resolution time. `_walk_chain`'s own docstring: *"Shared by every append-only hash-chained ledger."* Same lane → no FC needed for the reuse.
- `persona/memory/verified.py` (Lane 2) — `entries()` read at resolution time. No edit.
- `persona/memory/calibrate.py` (Lane 2, **FC-5**) — `admit_decision()` supplies the default prior `calibrated_p`. No edit.
- `persona/eval/calibration_report.py` (Lane 4, **PRD-15**) — `reliability(pairs)` reused **only at the Lane-4 render layer** (the route), not imported by the Lane-2 module, to avoid a memory→eval dependency inversion.

**The one cross-lane write hook (flagged — CCP-24a in §2):** the `predict()` *call site* for **hypotheses** is a single additive line in the Lane-1 hypothesis-open flow (`research/investigation.py`). Contradictions are hooked entirely inside Lane 2 (see §3, F24.1). Ships advisory: the ledger, API, Brier, and RQ-E40 test all function with predictions written directly, so nothing blocks on the hook landing.

---

## 2. FCs provided / consumed

### Provides — **FC-17** (Lane 2, new `persona/memory/predictions.py`)

Copy verbatim. All functions are pure over on-disk state (`ops_dir`), no model, no network.

```python
# --- Write side (immutable, hash-chained; reuses conflict_reviews primitives) ---
predictions.predict(
    ops_dir, *, subject_kind: str, subject_id: str, statement: str,
    p: float, prior_source: str, rationale: str = "",
) -> dict
# subject_kind ∈ {"contradiction","hypothesis"}.
# subject_id   = conflict_reviews.conflict_id(pos,neg)  (contradiction)
#              | verified._key(statement, method)        (hypothesis).
# p            = prior probability in [0,1] (typically FC-5 calibrated_p).
# prior_source = provenance of p, e.g. "calibrate.admit_decision" | "auditor.likelihood" | "human".
# Appends ONE kind:"prediction" row. Raises DuplicatePredictionError if subject_id was
# already predicted in this ledger (no re-issue → no goalpost-moving). Never touches the KG.

predictions.resolve(
    ops_dir, *, subject_id: str, outcome: str, y: float, resolved_by: str,
) -> dict
# Appends ONE kind:"resolution" row referencing subject_id. y ∈ [0,1]. Never edits the
# prediction row. Raises AlreadyResolvedError on a second resolution for the same subject_id,
# UnpredictedSubjectError if no prior prediction exists.

# --- Resolution derivation (pure; reads verified + conflict_reviews, appends resolutions) ---
predictions.sync_resolutions(ops_dir) -> dict
# {resolved:int, skipped:int, already:int}. For every open prediction, derives a terminal
# outcome from the source ledgers (§3 mapping table) and calls resolve() once. Idempotent.
# No edits to verified.py / revisit.py / conflict_reviews.py — pure read-through + append.

# --- Read side ---
predictions.verify_predictions(ops_dir) -> dict     # {ok, errors, records, record_count, latest_sha256}
predictions.predictions(ops_dir) -> list[dict]      # all verified rows (both kinds), chronological
predictions.open_predictions(ops_dir) -> list[dict] # predicted, not yet resolved
predictions.outcome_pairs(ops_dir) -> list[dict]    # {p,y,subject_id,subject_kind,at,resolved_at,resolved_by}
predictions.brier(ops_dir) -> dict                  # {n, brier, by_kind:{contradiction:{n,brier},hypothesis:{n,brier}}, open:int}
```

- **Consumers:** Lane 4 (`GET /predictions` route + Epistemic-tab render) reads `predictions()`, `open_predictions()`, `outcome_pairs()`, `brier()`. The Lane-1 hypothesis-open flow calls `predict()` (CCP-24a). The daemon (or the read route, lazily) calls `sync_resolutions()`.

### Consumes
- **FC-5** — `calibrate.admit_decision(candidate)["calibrated_p"]` is the standard `p` at prediction time. FC-17 does not import calibrate; the *caller* passes `p`, keeping FC-17 agnostic to the prior's origin (auditor likelihood and human priors are equally valid `prior_source`s).
- **PRD-15** — `calibration_report.reliability(pairs)` reused at the render layer for the ECE + reliability diagram over `outcome_pairs()`.

### CONTRACT CHANGE PROPOSAL — **CCP-24a** (routed to Lane 1, additive, non-blocking)
Add one additive line at the point a **hypothesis** becomes open in `research/investigation.py` (the hypothesis-pose site), calling `predictions.predict(..., subject_kind="hypothesis", subject_id=verified._key(stmt, method), p=<FC-5 calibrated_p>, prior_source="calibrate.admit_decision")`. Mirrors the CCP-10 one-line consolidator hook pattern (PRD-14). **Ships advisory**: FC-17, the route, Brier, and the RQ-E40 test are exercised by writing predictions directly, so Lane 1 is never a blocker. Contradiction predictions need **no** Lane-1 change — they are hooked inside the Lane-2 conflict-open / inbox path (F24.1).

_No change to any existing FC signature. `ops_dir/predictions.jsonl` is a **new** append-only ledger owned solely by Lane 2 (like `conflict_reviews.jsonl`); no other lane writes it._

---

## 3. Features

### F24.1 — Immutable prediction ledger (append-only, hash-chained, de-duplicated)

**Problem & evidence.**
- Persona forms a prior and escalates without recording it. `calibrate.admit_decision` computes `calibrated_p` and routes borderline candidates to `"human"` (`memory/calibrate.py:81-83`), and contradictions are filed for human adjudication (`conflict_reviews.append_conflict_review`, `conflict_reviews.py:243`) — but **the pre-resolution probability is never persisted**, so no later score can hold it accountable. There is no `predictions.py` anywhere in `persona/` (grep: only `calibrate.py`/`analysis/calibration.py` match "predict").
- The primitives to do this *correctly* already exist and are explicitly reusable. `conflict_reviews.py:143 _walk_chain(path, validate_record)` verifies "canonical encoding, per-record hash, and the prev-hash chain for one JSONL ledger… Shared by every append-only hash-chained ledger," with `_record_sha256` (`:134`), `_canonical_json` (`:75`), `_append_line` (fsync, `:219`), and the cross-process `_file_lock` (msvcrt/fcntl, `:39`). **Reusing them is the lazy correct path — a second ledger, not a second hash-chain implementation.**
- Research backing (why immutability is the mechanism, not decoration): forecast self-scoring requires the prediction to be fixed *before* resolution — the classic "prequential" / pre-registration principle (Dawid 1984, *Statistical theory: the prequential approach*, JRSS-A 147:278). Proper scoring rules (Brier 1950, *Mon. Wea. Rev.* 78:1; Gneiting & Raftery 2007, *JASA* 102:359) are only honest when the forecaster cannot revise `p` after seeing `y`. The hash-chain + subject-`predict()`-dedup enforces exactly that at the data-structure level.

**Design.**

`memory/predictions.py` — one JSONL ledger at `paths.ops_dir / "predictions.jsonl"`, two row kinds sharing one hash chain (chronological, tamper-evident):

```python
from ..conflict_reviews import (  # same-lane reuse; _walk_chain is documented as shared
    _walk_chain, _record_sha256, _canonical_json, _append_line, _file_lock,
    LedgerIntegrityError,
)

LEDGER_NAME = "predictions.jsonl"
SCHEMA_VERSION = 1
_SUBJECT_KINDS = {"contradiction", "hypothesis"}

class DuplicatePredictionError(ValueError): ...   # subject already predicted
class AlreadyResolvedError(ValueError): ...       # subject already resolved
class UnpredictedSubjectError(ValueError): ...    # resolve() before predict()

# prediction row: {kind:"prediction", subject_kind, subject_id, statement, p,
#                  prior_source, rationale, at, schema_version, prev_sha256, record_id}
# resolution row: {kind:"resolution", subject_id, outcome, y, resolved_by,
#                  at, schema_version, prev_sha256, record_id}
```

- **`predict()`** validates (`subject_kind ∈ _SUBJECT_KINDS`; `subject_id` non-empty; `p` finite in `[0,1]`, `bool` rejected exactly as `conflict_reviews._clean_confidence`; `statement`/`prior_source` non-empty), then under `_file_lock`: walks the chain (refuse a tampered ledger via `LedgerIntegrityError`), **scans for an existing `kind:"prediction"` with the same `subject_id` → `DuplicatePredictionError`** (this is the no-goalpost-moving guarantee), sets `prev_sha256`/`record_id`, `_append_line`. `at` = UTC ISO microseconds.
- **`resolve()`** under the lock: require a prior prediction for `subject_id` (`UnpredictedSubjectError`), reject a second resolution (`AlreadyResolvedError`), append the resolution row. **It reads, never rewrites, the prediction row** — the original prior is physically immutable.
- **`verify_predictions()`** = `_walk_chain(path, _validate_prediction_record)`; `_validate_prediction_record` dispatches on `kind`. Reused wholesale — no bespoke verifier.
- **`brier()`** = one pass over `outcome_pairs()`: `brier = mean((p - y)**2)`, plus `by_kind` and the `open` count. (Brier is one line; the reliability diagram/ECE is *not* re-implemented here — see F24.3.)

**Data flow (contradiction, fully Lane 2):** membrane/inbox routes a candidate contradiction to human → the conflict-open path calls `predictions.predict(subject_kind="contradiction", subject_id=conflict_id(pos,neg), p=admit_decision(cand)["calibrated_p"], prior_source="calibrate.admit_decision")`. Later a reviewer files `append_conflict_review(...)` → `sync_resolutions()` derives `y` from the latest verdict and appends the resolution.

**Epistemic guardrails.**
- **Immutable prior (the whole point).** Prior lives in a hash-chained row; `predict()` refuses a second prediction for the same subject; `resolve()` appends and never edits. Editing any prior byte on disk breaks `verify_predictions()` (`record-hash-mismatch` + `hash-chain-mismatch`) exactly as in `conflict_reviews`.
- **Never touches the KG / self.** Like `conflict_reviews.py`, this ledger records judgment but cannot mutate a belief. Brier is a *measurement*, never a driver (Autonomy: Balanced — read-only).
- **Provenance-typed prior.** `prior_source` records where `p` came from (`calibrate.admit_decision` / `auditor.likelihood` / `human`) so a reader can weight a model-derived prior differently from a human one.
- **No fabricated outcomes.** `y` only ever comes from a real terminal state in `verified.py` or `conflict_reviews.py` (F24.2). Unresolved subjects stay `open`, never imputed.

**Required experiment.** **RQ-E40** — see F24.2 (the immutability + resolution-mapping property/fault test covers this feature's load-bearing logic).

**Acceptance + one runnable check.**
- `predict()` twice on the same `subject_id` → `DuplicatePredictionError`; the first prior is unchanged on disk.
- Flip one `p` byte in a prediction row → `verify_predictions()["ok"] is False`.
- **Runnable check:** `python -m persona.memory.predictions` (`demo()` asserts: predict→resolve round-trip; duplicate-predict raises; tampered-row verify fails; `brier` on a hand-set `{p,y}` pair equals `(p-y)**2`).

**Effort.** S (one ~140-line module reusing the whole `conflict_reviews` hash-chain toolkit).

**Deps.** FC-5 (prior). None blocking — `conflict_reviews.py` primitives already exist.

---

### F24.2 — Resolution mapping from the real outcome ledgers (RQ-E40)

**Problem & evidence.**
- Real terminal outcomes already exist and are read cross-lane: `verified.entries()` carries `status ∈ {verified, weakened, refuted}` updated by the revisit loop (`memory/verified.py:67 update_status`; `agents/revisit.py:36` recomputes it by re-running the machine check), and `conflict_reviews.summarize_conflict_reviews` returns the latest `verdict ∈ ConflictVerdict` per `conflict_id` (`conflict_reviews.py:277`, verdicts at `:64-69`). **These are the outcomes; nothing maps them onto a recorded prior.**
- The mapping must be *exact and defensible* (it is what the Brier scores), so it is the one piece that gets a gated experiment.

**Design — `sync_resolutions(ops_dir)`** reads both source ledgers and, for each `open` prediction, derives `(outcome, y)` from this **frozen mapping table**, then `resolve()`s once:

| `subject_kind` | source ledger | terminal state | `outcome` | `y` |
|---|---|---|---|---|
| `hypothesis` | `verified.entries()` latest `status` for the key | `verified` | `"verified"` | `1.0` |
| | | `weakened` | `"weakened"` | `0.5` |
| | | `refuted` | `"refuted"` | `0.0` |
| | | `unverified` / not present | — | *skip (stays open)* |
| `contradiction` | `conflict_reviews` latest verdict for the id | `TRUE_REFUTATION` | `"true_refutation"` | `1.0` |
| | | `CONTEXT_DIVERGENCE` | `"context_divergence"` | `0.0` |
| | | `EXTRACTION_ERROR` | `"extraction_error"` | `0.0` |
| | | `INSUFFICIENT_EVIDENCE` | — | *skip (stays open)* |

- **Interpretation:** for a contradiction, `p` = Persona's prior that the tension is a *true refutation*; `y=1` iff a human confirmed it as such. For a hypothesis, `p` = prior it holds; `weakened → 0.5` (partial credit, a proper-score-valid non-binary outcome). `resolved_by` is provenance-typed: `"verified:refuted"`, `"conflict_review:true_refutation"`, or `"human:<reviewer>"`.
- **Only revisited / adjudicated subjects resolve** (`INSUFFICIENT_EVIDENCE` and `unverified` are *not* outcomes — conservative, mirrors PRD-15's "only real outcomes" gate). Idempotent: a subject already carrying a resolution row is `already`, not re-resolved.

**Epistemic guardrails.**
- The mapping is a small pure function with a single source of truth (the table above), fixture-pinned by RQ-E40 so a drift in `ConflictVerdict` or `verified` statuses fails a test rather than silently mis-scoring.
- `weakened → 0.5` is disclosed in the render `notes` (an honest partial outcome, not a hidden fudge).

**Required experiment — RQ-E40** (new; next free id after E39). *Register in `docs/RESEARCH_QUALITY_PROGRAM.md`.*
- **Hypothesis:** (a) a recorded prediction cannot be edited or re-issued post-hoc, and (b) `sync_resolutions` maps a subject's terminal ledger state onto exactly the `y` in the table above — never onto a different or fabricated outcome.
- **Metric + gate (both must pass):**
  1. **Immutability (fault-injection):** across ≥20 seeds, each seed builds a random ledger of predictions+resolutions, then applies a random tamper (flip a prior `p`, delete/reorder a row, splice a row, or attempt a second `predict()`/`resolve()`). **Gate: tamper-detection == 1.0** (`verify_predictions().ok is False` **or** the guarded call raises) **AND false-alarm == 0** (an untampered ledger always verifies). The original prior byte is asserted unchanged after every accepted `resolve()`.
  2. **Resolution mapping (property):** across ≥20 seeds of random `(subject_kind, terminal_state)` fixtures written into stub `verified`/`conflict_reviews` ledgers, **every** resolved pair satisfies `y == TABLE[subject_kind][state]` and every *skip* state leaves the prediction `open`. **Gate: mapping-exactness == 1.0, zero mis-maps, zero spurious resolutions.**
- **Seeds:** ≥20 (`experiments/exp_prediction_immutability.py`, seeded, mean over seeds reported to `/results`). Fault-injection + property style (matches RQ-E30/E36's "detection ≥0.95 AND false-quarantine == 0" family).

**Acceptance + one runnable check.**
- `python experiments/exp_prediction_immutability.py` prints `tamper_detection=1.0 false_alarm=0.0 mapping_exact=1.0` over ≥20 seeds (both gates pass).
- `tests/test_predictions.py::test_rq_e40_immutable_and_mapping` asserts both gates on a fixed seed set.

**Effort.** S–M (the experiment is the bulk; the mapping is ~20 lines).

**Deps.** F24.1; reads `verified.py` + `conflict_reviews.py` (both exist).

---

### F24.3 — Render alongside the PRD-15 calibration panel (Lane 4)

**Problem & evidence.**
- PRD-15 adds `GET /api/persona/{pid}/calibration` and an Epistemic-tab sub-surface with a reliability diagram + ECE/Brier tiles over auditor/verified verdicts (`PRD-15 §3`). PRD-24's predictions are the *forward-looking* sibling of exactly that story and belong on the same surface.
- The route pattern is settled: `/verified` at `app.py:295-301` and the PRD-15 `/calibration` route both `with context.use(_p(pid))` and return a plain dict.

**Design.**
- New route (mirrors `/verified`, `app.py:295`):
```python
@app.get("/api/persona/{pid}/predictions")
def prediction_ledger(pid: str):
    """Persona's immutable prior-probability ledger for open contradictions/hypotheses, its
    running Brier self-score, and a reliability curve over resolved predictions. Read-only."""
    with context.use(_p(pid)):
        from ..memory import predictions
        d = _p(pid).paths.ops_dir
        predictions.sync_resolutions(d)                      # lazy read-through resolution
        pairs = predictions.outcome_pairs(d)
        from ..eval.calibration_report import reliability     # PRD-15 reuse (render layer only)
        rel = reliability(pairs) if len(pairs) >= 20 else None
        return {"brier": predictions.brier(d), "open": predictions.open_predictions(d),
                "reliability": rel, "pairs_n": len(pairs),
                "notes": ["prior source per-row (calibrate/auditor/human); weakened→y=0.5 partial outcome;"
                          " reliability shown only at ≥20 resolved pairs"]}
```
- **Surface:** a sub-panel beside PRD-15's on the Epistemic tab: (1) running **Brier** tile (+ `by_kind`), (2) a table of **open predictions** (`statement`, prior `p`, `prior_source`, age) — the pre-registered commitments still outstanding, (3) the reliability curve reused from PRD-15 when `pairs_n ≥ 20`, else an honest "N of 20 resolved" callout (identical discipline to PRD-15). Colour never the only encoding.

**Epistemic guardrails.**
- Read-only: the route may call `sync_resolutions` (append-only, derived from real outcomes) but drives no belief/anchor/dispatch.
- Reuses PRD-15 `reliability()` verbatim → one ECE/diagram implementation, one thing to keep correct.

**Required experiment.** **Trivial** — a read-only render reusing a PRD-15-validated estimator; per `CLAUDE.md` "do not gold-plate," no seeded sweep. Correctness pinned by the browser smoke below.

**Acceptance + one runnable check.**
- With <20 resolved pairs → panel shows "N of 20 resolved" and the open-predictions table, no curve.
- **Runnable check:** extend `tests/ui_legibility_smoke.cjs` (`PERSONA_WORKERS=0`): open Epistemic tab → prediction panel shows the Brier tile + open-predictions table; assert no horizontal overflow at 1280/760/390 px.

**Effort.** S (thin route + one sub-panel; reuses the PRD-15 chart idiom).

**Deps.** F24.1/F24.2 (data); PRD-15 (`reliability`, and the Epistemic sub-surface it renders into).

---

## 4. Sequencing

1. **F24.1** — land `memory/predictions.py` with `predict/resolve/verify/predictions/open_predictions/outcome_pairs/brier` + `demo()`. Self-contained (reuses `conflict_reviews` primitives). *This is the FC-17 stub-and-fill; commit-in-place so Lane 4 can build against it.*
2. **F24.2** — `sync_resolutions` + the mapping table + `experiments/exp_prediction_immutability.py` (RQ-E40). Gate must pass before the panel is trusted.
3. **F24.3** — `GET /predictions` route + Epistemic sub-panel (Lane 4), against F24.1 fixtures first, real once F24.2 lands.
4. **CCP-24a** (Lane 1, last, non-blocking) — the one additive `predict()` line at hypothesis-open. Contradiction `predict()` hook lands with F24.1 inside Lane 2.

Interface-first: F24.1's signatures are the FC-17 contract; everything else builds against them.

---

## 5. Test plan

- **`experiments/exp_prediction_immutability.py`** (new, RQ-E40, ≥20 seeds) — the two gates in F24.2; results to `/results`.
- **`tests/test_predictions.py`** (new, Lane 4):
  - `test_rq_e40_immutable_and_mapping` — the fault-injection + property assertions (both gates) on a fixed seed set.
  - `test_predict_dedup` — second `predict()` on a subject → `DuplicatePredictionError`; on-disk prior byte-unchanged.
  - `test_resolve_never_edits_prior` — after `resolve()`, the prediction row's `record_id`/`p` are identical; `verify_predictions().ok`.
  - `test_sync_only_terminal` — a `hypothesis` at `unverified` and a `contradiction` at `INSUFFICIENT_EVIDENCE` stay `open`; `verified`/`true_refutation` resolve with correct `y`.
  - `test_brier_exact` — hand-set pairs → `brier == mean((p-y)**2)`; `by_kind` splits correctly.
  - `test_tamper_detected` — flip a prior `p` on disk → `verify_predictions().ok is False`.
- **Browser smoke** — extend `tests/ui_legibility_smoke.cjs` (F24.3 acceptance).
- **No regressions:** `test_calibration_report.py` (PRD-15) and `conflict_reviews` tests must pass unchanged — this PRD only *adds* a module/route/surface and *imports* (never edits) the shared primitives.

---

## 6. Open questions

- **Q1 (contradiction prior source).** Default contradiction prior = FC-5 `admit_decision(candidate)["calibrated_p"]` at the conflict-open moment. Is that the right "prior it's a true refutation," or should it be a dedicated NLI-conflict probability? Assumed `calibrated_p` (already computed, provenance-tagged). Reversible — `prior_source` records which was used; **does not block other lanes.**
- **Q2 (CCP-24a placement).** The hypothesis `predict()` hook needs exactly one call site in Lane-1's hypothesis-open flow (`research/investigation.py`). Confirm the precise line with Lane 1; ships advisory so Lane 1 timing is non-blocking. **Blocks nothing** — FC-17 + tests + render all work with predictions written directly.
- **Q3 (weakened credit).** `weakened → y=0.5` gives partial credit (proper-scoring-valid). If the team prefers strict binary (`weakened → 0.0` or *skip*), it is a one-line table change in F24.2 and a re-run of RQ-E40. Disclosed in the render `notes` either way.
- **Q4 (`reliability` reuse direction).** F24.3 imports `eval.calibration_report.reliability` **at the route (Lane 4) layer**, not inside the Lane-2 module, to avoid a `memory → eval` dependency. If a future lane wants `brier()` to also emit ECE, that estimator should move to a shared `eval` util both panels import — flagging so PRD-15's owner is aware. **No FC impact today.**
