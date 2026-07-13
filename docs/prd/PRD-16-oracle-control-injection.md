# PRD-16 — Auto positive/negative control injection for oracles

> Owner: implementer lane **3** (Engine / forensics / data acting-loop) · Status: **DRAFT-for-implementation** · Autonomy: **Balanced** · Depends on: PRD-00 file-ownership map + epistemic contract; **FC-8** (shared oracle verdict envelope + `science.REGISTRY` + `science.call`, ratified 2026-07-13) provided by PRD-06 (MR), PRD-07 (DepMap), PRD-10 (meta-analysis). Reuses `ResearchSession` (`sessions.py`), the `forensics.py` flag shape, and the append-only-ledger pattern.

---

## 0. Summary + capability unlocked

Persona is about to gain three **code-run oracles** that write **TESTED-provisional** beliefs into the mind: executable Mendelian randomization (PRD-06, `analysis/mr.run_mr`), the DepMap knockout oracle (PRD-07, `analysis/depmap_oracle.essentiality_verdict`), and the meta-analysis agent (PRD-10, `analysis/metaanalysis.run_meta_analysis`). Each returns the shared **FC-8 envelope** and can, under Balanced autonomy, append a belief (PRD-07 F7.5 records via `verified.record`; PRD-06/10 write on `causal`/pooled verdicts). That is exactly the point in the system where a **silently broken oracle** is most dangerous: a scipy API drift, a flipped comparison, a sign bug in `mr_estimates`, a threshold that stopped biting, or a units regression in the Chronos slice produces a *confident wrong verdict* that propagates into the belief-state — the worst possible bug in this system (`CLAUDE.md` §4, "a silent wrong number that propagates into the belief-state").

Today nothing catches that. Each oracle validates itself **once**, offline, at gate time (RQ-E20/E21/E22/E24 fixtures), then runs unguarded forever after. The gating experiment proves the code was correct *the day it shipped*; it says nothing about the code path that actually executed *this* query, *today*, against *this* library version.

**This PRD adds a standing self-check.** Every FC-8 oracle invocation runs its **two frozen controls — a known-positive and a known-negative — through the same deterministic core, alongside the real query**. If either control returns the wrong verdict, the oracle is provably broken *right now*, so the real result is **QUARANTINED**: its verdict is forced to `inconclusive`, its provenance is forced off the TESTED tier (no belief write), and a **pipeline-health flag** is emitted to a human-visible ledger. Controls only ever *pass* → the real verdict flows as normal (`TESTED-provisional`); controls that pass are the *precondition* for trust, never a source of it.

**Capability nothing else in the stack has:** a live, per-invocation breakage detector wired between the oracle and the belief-state. It is the acting-loop analogue of a lab running a positive and negative control on every plate — the RCT-DUPLICATE / negative-control-calibration ethos (Schuemie et al., *empirical calibration of p-values using negative controls*, PNAS 2018; OHDSI negative-control practice) applied to Persona's own analysis pipeline. The gate proved the oracle *can* be right; the controls prove it *is* right on the run that just wrote to your mind.

---

## 1. File ownership (disjoint set)

All primary files are **Lane 3-owned** (PRD-00 §3: Lane 3 owns `persona/analysis/*`, `persona/tools/{science.py, datasets.py}`).

| File | Own/edit | Lane | Note |
|---|---|---|---|
| `persona/analysis/oracle_controls.py` | **create (new)** | 3 | The controls fixture registry + `guarded_call` wrapper + `run_controls` + `quarantine`. The whole feature. |
| `persona/tools/science.py` | edit (additive) | 3 | `call()` routes FC-8 oracle names through `oracle_controls.guarded_call` (single chokepoint). |
| `experiments/exp_rq_e30_oracle_controls.py` | create (new) | 3 (via Lane 4's `experiments/*` note, as PRD-07 F7.4) | Required fault-injection experiment (RQ-E30). |
| `results/e30_oracle_controls.json` + FINDINGS.md append | create/append | 3 | Seeded results. |
| `tests/test_oracle_controls.py` | create (new) | 3 | Runnable acceptance check (offline, fixtured). |

**Boundary files another lane / another PRD owns (flagged):**

- **`persona/analysis/mr.py`, `persona/analysis/depmap_oracle.py`, `persona/analysis/metaanalysis.py`** — all **Lane 3-owned**, but created by PRD-06/07/10 (not yet landed). PRD-16 requires each to expose one **pure control-injection hook**: a way to run the oracle's *deterministic core* (estimator + classifier + gate) on **injected fixture data**, bypassing the network fetch. All three already separate fetch (outside sandbox) from compute (pure): `mr.mr_estimates`/`sensitivity_gate` are pure (PRD-06 §2), `depmap_oracle._classify`/`essentiality_verdict` accept an injected slice (PRD-07 F7.3), `metaanalysis.meta_analyze(rows)` is pure over transcribed effects (PRD-10 F10.x). The hook is a thin, additive, same-lane convention — **flagged as a soft dependency (CCP-16b) on PRD-06/07/10**, not a signature change to their public FC-8 entry.
- **`ops_dir/oracle_health.jsonl`** — a new append-only health ledger (analogue of the `gate_decisions.jsonl` shared ledger, PRD-00 §4). Lane 3 appends; Lane 4 reads to render pipeline-health. Append-only, never edit another lane's rows.
- **`persona/api/*` / `index.html`** — **Lane 4 owns.** Lane 4 renders the quarantine state; PRD-16 makes it render for free by shaping `pipeline_health` like a `forensics.py` flag inside the existing FC-8 envelope card. No edit here.

`science.py`, `datasets.py`, and `analysis/*` are all Lane-3-owned, so **no cross-lane file is edited**; the only external touchpoints are the FC-8 envelope addendum (§2, CCP-16a) and the control-hook soft dependency (CCP-16b).

---

## 2. FCs provided / consumed

### Consumed (verbatim)
- **FC-8** (shared oracle verdict envelope; PRD-00 §4, ratified 2026-07-13). Every oracle returns `{status|verdict, applicable:bool, methods:{}, sensitivity:{}, capsule:{session_id, input_sha256, script_sha256, sandbox_image_digest}, provenance:'TESTED-provisional'|'INFERRED'|'abstain', high_stakes:bool, handoff_id?}`, registers in `science.REGISTRY`, and is invoked via `science.call(name, params)`. PRD-16 wraps this envelope; it consumes the entry, the registry, and the dispatch.
- **`ResearchSession`** (`sessions.py:62`) — `store_json`/`record`/`finalize`; controls seal into the same session the real run opened (§3, F16.2), reusing `verify_session` (`sessions.py:221`) for replayability.

### Provided — **CONTRACT CHANGE PROPOSAL: CCP-16a (FC-8 addendum, Lane 3 provides)**

Two **additive, backward-compatible** fields on the FC-8 envelope. Consumers that ignore them are unaffected; Lane 4 renders them in the *same* card that already renders the envelope (no new renderer, per FC-8's "ONE component" rule).

```
# additive fields on the FC-8 envelope (unset on oracles with no controls registered):
{
  ...existing FC-8 fields...,
  "controls": {                       # present iff this oracle name has a controls fixture
    "ok": bool,                       # True => both controls returned their expected verdict
    "positive": {"expected": str, "got": str, "pass": bool},
    "negative": {"expected": str, "got": str, "pass": bool},
    "control_capsule": str | None,    # rel path to sealed control artifact (inputs sha + verdicts)
  },
  "quarantined": bool,                # True => a control failed; real verdict was suppressed
  "pipeline_health": {                # present iff quarantined (forensics-flag shape)
    "check": "oracle_controls",
    "status": "broken",               # vs implicit "ok" when controls pass
    "severity": 3,
    "oracle": str,
    "failed": ["positive"|"negative", ...],
    "detail": str,                    # one-line human-readable, e.g. "MR positive control LDL->CHD returned 'null', expected 'causal' — oracle QUARANTINED"
  } | None,
}
```

**Quarantine transform (frozen semantics):** when `controls.ok is False`, the wrapper mutates the real envelope in place:
- `status`/`verdict` (whichever key the oracle uses) → `"inconclusive"`,
- `applicable` → `False`,
- `provenance` → `"abstain"` (existing enum value; **forces off TESTED-provisional so no belief write can fire** — the belief-writers in PRD-06/07/10 only write on affirmative verdicts),
- `quarantined` → `True`, `pipeline_health` populated,
- `high_stakes` unchanged, `handoff_id` untouched (the pipeline-health flag, not a science handoff, is the escalation channel — a *broken oracle* is an ops problem, not a belief-adjudication one).

This is the *only* mutation the wrapper performs on a passing envelope beyond attaching `controls`.

**CCP-16b (soft, Lane-3-internal):** each FC-8 oracle exposes a control-injection hook so its deterministic core can run on frozen fixture data without a network fetch (§1 boundary note). Routed to PRD-06/07/10 authors; PRD-16 ships against fixtured hooks and wires real hooks as each oracle lands (contract-first, PRD-00 §5).

**No FC-4 change** (value_queue `run_action` strings unchanged) and **no FC-8 signature change** to any oracle's public entry.

---

## 3. Features

### F16.1 — `oracle_controls.py`: the controls fixture registry + `guarded_call` wrapper (CCP-16a)

**Problem & evidence.** The three oracles each validate once at gate time then run unguarded. `forensics.py` (line 1–15) enforces the principle "checks that run in CODE, never in a model … impossible to argue with" for *paper* arithmetic; there is no equivalent standing check for *Persona's own* arithmetic. A silent regression (scipy `stats` API drift — `forensics._p_from_stat` calls `stats.t.sf` etc., `forensics.py:27`; a flipped `≤` in `depmap_oracle._classify`; a harmonization sign bug in `mr.harmonize`) would emit a confident wrong verdict with no tripwire. The negative-control-calibration literature (Schuemie et al., PNAS 2018; OHDSI) establishes the discipline: a pipeline you trust must demonstrate it still recovers *known* answers on *every* run, not just at commissioning.

**Design.**
- **File:** `persona/analysis/oracle_controls.py` (new). Pure Python; no LLM; no network.
- **Controls registry (frozen fixtures):**
  ```python
  # Each control ships FROZEN INPUT DATA fed to the oracle's deterministic core (NOT a live query),
  # so a control failure means the ORACLE LOGIC broke — never that the network hiccuped.
  # This is the load-bearing design choice (see F16.4 / RQ-E30): controls test the code path,
  # not the data source. Live-data flakiness must not false-quarantine a correct oracle.
  CONTROLS: dict[str, OracleControls] = {
    "mendelian_randomization": OracleControls(
        positive=Control(fixture="fixtures/mr_ldl_chd.json",   expect="causal"),  # LDL->CHD, IVW p<0.05, F>=10
        negative=Control(fixture="fixtures/mr_null_pair.json", expect="null"),    # a curated no-signal pair
        verdict_key="verdict",
        run=lambda data: mr.verdict_from_fixture(data),        # CCP-16b hook: pure core on injected SNP table
    ),
    "depmap": OracleControls(
        positive=Control(fixture="fixtures/depmap_rpl9.json",  expect="confirmed_pan_essential"),  # RPL9 median~-1.5
        negative=Control(fixture="fixtures/depmap_or2t35.json", expect="contradicted"),            # olfactory receptor ~0.0
        verdict_key="status",
        run=lambda data: depmap_oracle.verdict_from_slice(data),
    ),
    "meta_analysis": OracleControls(
        positive=Control(fixture="fixtures/meta_bcg.json",  expect="pooled_significant"),  # BCG-vaccine logRR, I^2 (metafor fixture, PRD-10 RQ-E24)
        negative=Control(fixture="fixtures/meta_null.json", expect="pooled_null"),
        verdict_key="verdict",
        run=lambda data: metaanalysis.verdict_from_rows(data),
    ),
  }
  ```
  Fixtures are small, checked-in JSON (the same fixtures each oracle's gating experiment already curates — reuse, don't re-author), each with a recorded `sha256`. The registry key matches the `science.REGISTRY` name.
- **Public signatures (new):**
  ```python
  def guarded_call(name: str, oracle_fn, params: dict, *, runs_dir=None, ops_dir=None,
                   parent_id=None) -> dict:
      """Run the real oracle query, then its two frozen controls through the same core.
      Returns the FC-8 envelope, quarantined (verdict->'inconclusive', provenance->'abstain',
      pipeline_health flag) if either control returns the wrong verdict. Oracles with no
      registered controls pass through untouched."""

  def run_controls(name: str, *, runs_dir=None) -> dict:
      """Execute both frozen controls via the registry `run` hooks; return the `controls` block
      (ok / positive / negative / control_capsule). Deterministic, offline."""

  def quarantine(envelope: dict, name: str, controls: dict) -> dict:
      """Apply the frozen quarantine transform (CCP-16a) to a real envelope in place."""

  def is_oracle(name: str) -> bool:
      """True iff `name` has registered controls (i.e. is an FC-8 oracle to be guarded)."""
  ```
- **Data flow inside `guarded_call`:** (1) `real = oracle_fn(**params)` — the real FC-8 envelope (network fetch happens inside it, outside any sandbox, per FC-8). (2) `controls = run_controls(name)` — runs the two frozen fixtures through the pure core (no network). (3) if `controls["ok"]` → attach `controls`, return `real` untouched (verdict flows, TESTED-provisional preserved). (4) else → `quarantine(real, name, controls)` + `_append_health(ops_dir, ...)`. **Recursion guard:** controls call the pure core hooks directly (`run=` lambdas), never `guarded_call`, so controls never trigger controls.
- **Health ledger:** `_append_health(ops_dir, row)` appends one row `{oracle, ok:False, failed:[...], positive, negative, at}` to `ops_dir/oracle_health.jsonl` (append-only, `gate_decisions.jsonl` pattern, PRD-00 §4). This is the durable, human-visible record of every quarantine.

**Seam (F16.3):** wired at `science.call` — the single FC-8 invocation chokepoint.

**Epistemic guardrails.** (1) Controls are **frozen fixtures run through the pure core**, so a failure indicts the *code*, not the *data source* — the design property that makes quarantine trustworthy (a live-network control would false-quarantine on any transient blip; F16.4 tests this boundary). (2) **Control failure → quarantine + human-visible**, never a silent pass — the exact discipline of PRD-00 §2 ("skipped/not-applicable distinct from passed"), here "broken distinct from passed". (3) `provenance` is forced to `abstain` on quarantine, so **no belief can be written from a broken oracle** — the belief-state stays clean. (4) Controls *passing* grants **no** confidence of its own; it is only the precondition that lets the real (independently gated) verdict stand — controls are a tripwire, not evidence. (5) No model in the path.

**Required experiment.** RQ-E30 (F16.4).

**Acceptance + runnable check.** `pytest tests/test_oracle_controls.py::test_broken_oracle_is_quarantined` — inject a deliberately broken oracle_fn (returns the negative control's fixture as `causal`), assert the returned envelope has `quarantined is True`, `verdict == "inconclusive"`, `provenance == "abstain"`, a populated `pipeline_health`, and that a healthy oracle passes through with `controls["ok"] is True` and its original verdict intact. Fully offline.

**Effort:** M. **Deps:** FC-8 envelope + the three control-injection hooks (CCP-16b; fixtured until oracles land).

---

### F16.2 — Controls sealed into the real run's `ResearchSession` capsule (replayable health)

**Problem & evidence.** "Controls passed" is itself a claim that must be auditable and replayable — otherwise it is exactly the kind of unverifiable model-ish assertion Persona rejects (`CLAUDE.md` §4, "provenance and reproducibility are features"). The FC-8 envelope already carries a `capsule` (`{session_id, input_sha256, script_sha256, sandbox_image_digest}`) and each oracle opens a `ResearchSession` (`sessions.py:62`; PRD-06 F6.3 reuses `analyst.py`'s session pattern). The control run should ride in that same capsule so a verifier can re-derive both the real verdict *and* the health check.

**Design.**
- When `guarded_call` receives a `session` (or `runs_dir` to attach to the envelope's `capsule.session_id`), `run_controls` calls `session.store_json("oracle_controls.json", {fixtures_sha, expected, got, ok})` (`sessions.py` `store_json`) and `session.record("controls_checked", {...})`. `control_capsule` in the `controls` block points at that artifact.
- The sealed artifact is tiny (two fixture shas + four verdict strings), so it adds negligible weight and makes the whole thing `verify_session`-able (`sessions.py:221`) — a reviewer replays the capsule and re-runs the two frozen controls to confirm the health verdict, same as replaying the real analysis.
- If no session is available (oracle ran host-only / Docker absent, PRD-06 F6.3 fallback), the control artifact is written next to the health ledger and referenced by path — still replayable, just not co-sealed.

**Epistemic guardrails.** The health check inherits the capsule's hash-verification: you cannot claim "controls passed" without the frozen inputs + verdicts that prove it, re-runnable offline. Frozen fixtures never change silently — their sha is pinned in the registry and re-checked at load (`_load_fixture` asserts sha match; a fixture that drifted is itself a quarantine-worthy breakage).

**Required experiment.** Trivial (capsule reuse; the F16.4 experiment exercises the seal path). Reuses the existing `verify_session` oracle — no new experiment (parity engineering, cf. PRD-06 F6.3 / PRD-10).

**Acceptance + runnable check.** `pytest tests/test_oracle_controls.py::test_controls_sealed_in_capsule` — a `guarded_call` with a real `ResearchSession` produces a session for which `verify_session(runs_dir, session_id).ok is True` and whose artifacts include `oracle_controls.json` with `ok:True`.

**Effort:** S. **Deps:** F16.1, `ResearchSession` (existing).

---

### F16.3 — `science.call` seam: route FC-8 oracle names through the guard

**Problem & evidence.** FC-8 states oracles are "invoked via `science.call(name, params)`" and value-queue `run_action` strings `"<oracle>:<args>"` dispatch there (PRD-00 §4). `science.call` (`science.py:147`) is therefore the single chokepoint every oracle invocation crosses — the lazy-correct place to install one guard rather than three. The current dispatch (`science.py:147–168`) hard-codes six literature clients; the FC-8 oracles will be added to `REGISTRY` (PRD-06 §2 line 186, PRD-07 F7.1, PRD-10). Non-oracle tools (`literature_search`, `open_targets`, …) must pass through untouched — controls apply only to code-run *verdict* oracles.

**Design.**
- **File:** `persona/tools/science.py` (additive edit). In `call()`, before returning a result for an FC-8 oracle name, route through the guard:
  ```python
  def call(api: str, params: dict) -> dict:
      entry = REGISTRY.get(api)
      if not entry:
          return {"ok": False, "error": f"unknown api {api}"}
      fn = entry[0]
      if oracle_controls.is_oracle(api):          # FC-8 code-run oracle -> guarded
          return oracle_controls.guarded_call(api, fn, params)
      # ... existing literature-client dispatch unchanged ...
  ```
- Membership is decided by the controls registry (`is_oracle`), so adding a new FC-8 oracle = adding its controls fixture (fail-closed: an oracle with no registered controls is **not** silently trusted — see Open Question O-3; the conservative default is to require controls before an oracle may auto-write).
- **Direct-import callers** (PRD-07 F7.5's `depmap_check` worker handler imports `depmap_oracle` directly, bypassing `science.call`): flagged. The clean fix is to have those handlers invoke `science.call("depmap", ...)` — the FC-8 canonical entry — so they inherit the guard for free. Routed as **O-1** (coordination with PRD-07's worker handler). PRD-16 does **not** edit `worker.py`.

**Epistemic guardrails.** Literature clients are untouched (they return evidence, not verdicts, and never write TESTED beliefs). The guard is fail-closed for registered oracles: no FC-8 oracle reaches a belief write without its controls having run.

**Required experiment.** Trivial (dispatch routing; F16.4 covers end-to-end).

**Acceptance + runnable check.** `python -c "from persona.tools import science, oracle_controls; ...; print(science.call('depmap', {...})['controls']['ok'])"` returns a `controls` block for an oracle name and no `controls` key for `literature_search`. Covered by `test_oracle_controls.py::test_science_call_routes_oracles_only`.

**Effort:** S. **Deps:** F16.1; FC-8 oracles registered in `REGISTRY`.

---

### F16.4 — RQ-E30: fault-injection — a deliberately broken oracle must be caught by the controls

**Problem & evidence.** The load-bearing claim is *"the controls actually catch breakage"* — a control suite that misses real faults is security theatre, and a control suite that fires on a correct oracle (false quarantine) destroys availability and is the correctness boundary (PRD-00 §2: out-of-domain false positives are the boundary). Both must pass a seeded gate **before** the guard is trusted to quarantine autonomously (`CLAUDE.md` §2; PRD-00 §6). This is the mutation-testing discipline: inject known faults, measure detection.

**Hypothesis + metric + gate.** *Deliberately injected oracle faults are caught by the frozen controls at a high detection rate, with zero false quarantines on the un-mutated oracle.*
- **Fault injections (per oracle, sampled across seeds):** flip a comparison operator (`≤`↔`>`) in the classifier/gate; negate an effect sign in the estimator (`mr_estimates`/`harmonize`); scale the input data by a wrong unit factor (e.g. Chronos ×−1, logRR→RR); drop a method from the ensemble; perturb a threshold past its bite point (`−0.5`→`−2.0`). Each mutation is applied to the pure core the control `run` hook invokes.
- **Metric:** **detection rate** = fraction of injected faults for which at least one control's verdict flips away from its expected value → quarantine fires. **False-quarantine rate** = fraction of runs on the *un-mutated* oracle where a control wrongly fails.
- **Gate:** **detection rate ≥ 0.95** across the fault families **AND false-quarantine rate == 0** on the correct oracle (the availability half — a control suite that cries wolf is worse than none). If detection < 0.95, the fault families the controls miss are enumerated and either a second control pair is added or the miss is documented as a known blind spot (reversal logged in FINDINGS).
- **Seeds:** **≥ 20 seeds**; each seed samples a random (oracle, fault-family, magnitude) triple and also runs the un-mutated control pass. Report detection rate mean ± 95% CI and the false-quarantine count (must be 0). Deterministic given a seed; RNG seeded for reproducibility (mirrors `exp_poisoning.py`'s seeded-CI-oracle pattern, `experiments/exp_poisoning.py`).

**File:** `experiments/exp_rq_e30_oracle_controls.py` → `results/e30_oracle_controls.json` + FINDINGS.md `#RQ-E30` append. Fully offline (mutates pure cores over checked-in fixtures; no network, no Docker).

**Acceptance + runnable check.** `python experiments/exp_rq_e30_oracle_controls.py` prints `PASS` and writes the JSON when detection ≥ 0.95 and false-quarantine == 0 over ≥20 seeds; prints `FAIL` with the missed fault families otherwise. This experiment **is** the go/no-go gate: the guard ships **advisory** (records the health flag, does **not** force `abstain`) until RQ-E30 passes, then flips to enforcing quarantine — the same "advisory until the gate passes" pattern as FC-4 (PRD-00 §4) and PRD-07 F7.5.

**Effort:** M. **Deps:** F16.1, the three control-injection hooks (fixtured cores are sufficient for the experiment).

---

## 4. Sequencing (interface-first)

1. **F16.1 stub + CCP-16a fields:** ship `oracle_controls.py` with the registry + `guarded_call`/`run_controls`/`is_oracle`/`quarantine` returning typed values, controls keyed but backed by fixtured `run` hooks. Commit-in-place so `science.call` (F16.3) and Lane 4's render can build against the `controls`/`pipeline_health` fields from hour 1.
2. **F16.3 seam:** wire `science.call` to route registered oracle names through `guarded_call`. Pass-through verified for literature clients.
3. **F16.1 real logic + F16.2 capsule seal:** the quarantine transform + health ledger + `ResearchSession` sealing, against fixtured cores.
4. **F16.4 RQ-E30 fault-injection experiment → gate.** Guard is **advisory until this passes**; then it enforces quarantine.
5. **Wire real control hooks (CCP-16b)** as PRD-06/07/10 land their oracles: replace each fixtured `run` lambda with the oracle's real `verdict_from_*` core hook.

Nothing here blocks PRD-06/07/10 — PRD-16 builds against fixtured hooks and swaps in real ones as they arrive (contract-first, PRD-00 §5).

---

## 5. Test & verification plan

- **Offline unit (primary):** `tests/test_oracle_controls.py` — `test_broken_oracle_is_quarantined` (F16.1), `test_controls_sealed_in_capsule` (F16.2), `test_science_call_routes_oracles_only` (F16.3), `test_healthy_oracle_passes_through` (verdict + provenance intact, `controls.ok True`), `test_advisory_mode_does_not_force_abstain` (pre-gate behaviour). Deterministic, no network, no Docker — this is the regression oracle for the guard itself.
- **Fault-injection experiment (gated, seeded):** `exp_rq_e30_oracle_controls.py` — the mutation-testing detection-rate gate; `PASS`/`FAIL` with missed fault families, ≥20 seeds, offline.
- **Reuse existing oracles:** the `pipeline_health` block conforms to the `forensics.py` flag shape (`{check, status, severity, detail}`, `forensics.py:14`), so Lane 4's existing FC-8 render surfaces the quarantine with **no new renderer**; `verify_session` (`sessions.py:221`) verifies the sealed control capsule with no new verification surface.
- **Reproducibility:** frozen fixtures are sha-pinned in the registry and re-checked at load; the sealed control artifact + pinned fixtures let any quarantine decision be re-derived offline.

---

## 6. Open questions for the master/user

1. **O-1 — direct-import oracle callers.** PRD-07 F7.5's `@handler("depmap_check")` imports `depmap_oracle` directly, bypassing `science.call` and thus the guard. Confirm the coordination: those handlers route through `science.call("<oracle>", ...)` (cleanest, inherits the guard), **or** each oracle's public FC-8 entry (`run_mr`/`essentiality_verdict`/`run_meta_analysis`) internally delegates to `oracle_controls.guarded_call` (guards every path, three same-lane edits). I recommend the latter for defence-in-depth, since the belief write happens on the direct path. Which?
2. **O-2 — CCP-16a ratification.** Two additive FC-8 envelope fields (`controls`, `pipeline_health`) + the frozen quarantine transform (verdict→`inconclusive`, provenance→`abstain`). Needs master + Lane 4 (render) ack. Backward-compatible; no existing field changes.
3. **O-3 — fail-closed default for un-controlled oracles.** An FC-8 oracle with **no** registered controls: does it (a) pass through un-guarded (fail-open, current literature-client behaviour), or (b) get blocked from auto-writing a TESTED belief until controls are registered (fail-closed)? I lean fail-closed for anything that writes to the belief-state — but that couples PRD-16 to every future oracle's rollout. Confirm posture.
4. **O-4 — CCP-16b control-injection hooks.** Each oracle must expose a pure `verdict_from_fixture`/`verdict_from_slice`/`verdict_from_rows` hook (§1, §2). Confirm PRD-06/07/10 authors add it (1 additive line each, same lane), and that reusing their gating-experiment fixtures (RQ-E21/E22/E24) as the control fixtures is sanctioned (avoids re-authoring ground truth).
5. **O-5 — RQ id.** `RQ-E30` chosen as the next free id (registry currently reaches E29, PRD-00 §6). Confirm, and confirm `#RQ-E30` is registered in `docs/RESEARCH_QUALITY_PROGRAM.md`.
6. **O-6 — negative control curation.** The MR / meta "negative" controls need a genuinely null exposure→outcome / effect set with no real signal (an oracle that returns `causal`/`pooled_significant` on a true null is exactly the false-positive breakage we want to catch). Reuse an OHDSI-style curated negative-control pair, or hand-pick? Curation choice is itself load-bearing for the negative arm — flag for review.

---

_Grounded against: `persona/tools/science.py` (`REGISTRY` L137, `call` L147–168, per-client dispatch), `persona/analysis/forensics.py` (flag shape L14, code-not-model discipline L1–15, `stats.*` calls L27–39), `persona/sessions.py` (`ResearchSession` L62, `store_json`, `record`, `finalize` L128, `verify_session` L221), `experiments/exp_poisoning.py` (seeded CI-oracle pattern, `range(24)` L34, PASS/assert gate L61–65); FC-8 envelope + `science.REGISTRY`/`science.call` (PRD-00 §4); PRD-06 (`mr.run_mr`, `mr_estimates`/`sensitivity_gate` pure, capsule §2/F6.3), PRD-07 (`depmap_oracle.essentiality_verdict`/`_classify` F7.3, worker handler F7.5), PRD-10 (`metaanalysis.meta_analyze(rows)` pure, F10.x). Research: Schuemie et al., empirical calibration via negative controls (PNAS 2018); OHDSI negative-control / RCT-DUPLICATE ethos (backlog #90)._
