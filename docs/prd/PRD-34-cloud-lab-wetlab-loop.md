# PRD-34 — Cloud-lab wet-lab loop

> **Owner lane:** 3 (Intellectual engine, forensics & data acting-loop) · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (wet-lab submission is high-cost/high-stakes → **HUMAN-GATED, never auto-submit**) · **Depends-on:** FC-2 (inbox handoff), FC-8 (oracle verdict envelope + `science.REGISTRY`/`science.call`), FC-4 `value_queue` (`run_action` dispatch, CCP-19a), CCP-1 (`IngestService` `headers=`). Backlog #507/#508/#509.

Governed by `PRD-00-overview.md` §4/§6 and §8 reconciliation. Where this body disagrees with §4/§6, **§4/§6 win**.

---

## 0. Summary + capability unlocked

Persona's one hard limit is stated in `CLAUDE.md` §7: *"Persona cannot do wet-lab work."* Today that limit is a dead end — a wet-lab-testable hypothesis that reaches the top of the value queue (`analysis/value_queue.py`) has no `run_action` that can resolve it; it can only be routed to a human as prose. This PRD closes the last gap in the acting loop by bridging to **cloud labs** (Adaptyv / Emerald / Strateos, via the `adaptyv` and `ginkgo-cloud-lab` skills) so a flagged hypothesis can become an actual assay whose result is written back as **TESTED** evidence.

**Capability unlocked:** for a wet-lab-testable hypothesis, Persona (1) drafts a concrete experiment protocol, (2) files it as a **human-approval handoff** (never auto-submits a paid experiment), (3) on human approval submits to a cloud lab and stands a poll for results (retraction-watcher pattern), (4) ingests the returned assay result as **TESTED-provisional** evidence with a full provenance capsule, and (5) **reconciles** that wet-lab result against Persona's in-silico prediction (its MR / DepMap / molecular-gate belief, FC-8) — surfacing *in-silico-vs-wet-lab divergence as its own signal*. This is the first loop in the system where the terminal evidence is physical, not literature- or code-derived.

**Provenance is the whole point:** submission cost + irreversibility make this the highest-stakes action in the system, so the human gate is not advisory — it is a hard invariant checked by RQ-E48.

---

## 1. File ownership (disjoint)

New files (Lane 3 owns, per §4 "New-file ownership rule 2026-07-13"):

| File | New? | Role |
|---|---|---|
| `persona/ingest/cloudlab.py` | **new** | Cached `IngestService`-backed cloud-lab client: draft protocol, submit (post-approval), poll, fetch result. FC-26 core. |
| `persona/analysis/wetlab_reconcile.py` | **new** | Reconcile ingested assay result vs the in-silico FC-8 prediction; emit divergence signal. FC-26 reconcile surface. |
| `persona/analysis/wetlab_watch.py` | **new** | Standing poll for submitted-experiment results (retraction-watcher-shaped `run(...)`); on completion → ingest + reconcile. |

Additive edits to files this lane already owns (§3 Lane-3 set — no cross-lane collision):

| File | Edit | Boundary/FC |
|---|---|---|
| `persona/tools/science.py` | Register **`"wetlab_reconcile"`** in `REGISTRY` (a FC-8 verdict oracle over an *already-ingested* result — NOT a submitter). Additive. | FC-8 |
| `persona/analysis/value_queue.py` | Emit `run_action="wetlab:<hypothesis>"` when a top question is wet-lab-testable and no public-data/oracle path exists (`cost_tier="expensive"`). Additive prefix; **no FC-4 signature change** (CCP-19a). | FC-4 |

**Boundary files touched by OTHER lanes (flagged, not edited here):**
- `persona/api/app.py` (Lane 4): new read-only routes `GET /wetlab/submissions`, `GET /wetlab/{id}`, and the human-approval action `POST /wetlab/{handoff_id}/approve`. Also the `run_action` prefix dispatch site (`app.py:847` region) must route the `"wetlab:"` prefix to **`inbox.file_handoff`** (queue a human approval), *not* to `science.call`. **CONTRACT: the dispatch site never calls `cloudlab.submit` directly.** Lane 4 renders; Lane 3 provides `cloudlab.draft_protocol` + the handoff dossier.
- `persona/inbox.py` (Lane 2, FC-2): consumed read-only via `inbox.file_handoff(kind="wetlab_approval", dossier=...)`. No edit.
- `persona/daemon/{supervisor.py, worker.py}` (Lane 1): a `wetlab_watch` scheduler tick + a `wetlab_submit` task handler (append-only registry). **Advisory hook (→ Lane 1, non-blocking):** ships API/manual-enqueueable until Lane 1 lands them, mirroring CCP-27a (`retraction_watch`).

---

## 2. FCs provided / consumed

### Provided — FC-26 (Lane 3)

New module `persona/ingest/cloudlab.py`:

```python
def draft_protocol(hypothesis: str, *, kg=None, prediction: dict | None = None) -> dict:
    """Pure protocol draft (NO network, NO submission). Returns
    {assay_type, target, readout, controls:[...], est_cost_tier, est_cost_usd,
     lab:'adaptyv'|'emerald'|'strateos', feasible:bool, infeasible_reason,
     predicts:{effect_sign, source_verdict}}.
    est_cost from the skill's price table (cached); feasible=False + abstain if
    the assay/target is not offered by any wired lab."""

def submit(protocol: dict, *, approval_handoff_id: str, ops_dir=None) -> dict:
    """Submit to the cloud lab. HARD GUARD: raises ApprovalRequiredError unless
    approval_handoff_id resolves to a HUMAN-APPROVED wetlab_approval handoff
    (FC-2). Returns {submission_id, lab, status:'submitted', at, cost_usd}.
    Appends to ops_dir/wetlab_submissions.jsonl (append-only, immutable prior)."""

def poll(submission_id: str) -> dict:
    """{submission_id, status:'submitted'|'running'|'complete'|'failed', eta}."""

def fetch_result(submission_id: str) -> dict:
    """{submission_id, assay_type, readout, value, unit, effect_sign,
     replicates, qc:{pass:bool, ...}, raw_ref, lab, completed_at} or {available:False}."""

class ApprovalRequiredError(RuntimeError): ...
```

New module `persona/analysis/wetlab_reconcile.py` — the FC-8 verdict oracle (registered `science.REGISTRY["wetlab_reconcile"]`, invoked `science.call("wetlab_reconcile", {...})`):

```python
def reconcile(submission_id: str, *, kg=None, session=None, ops_dir=None) -> dict:
    """Ingest a COMPLETED cloud-lab result and reconcile vs the in-silico
    prediction. Returns the FC-8 envelope:
      {verdict:'confirms'|'refutes'|'divergent'|'inconclusive',
       applicable:bool, methods:{assay_type, in_silico_source, readout},
       sensitivity:{qc, replicates}, divergence:{predicted_sign, observed_sign, magnitude},
       capsule:{session_id, input_sha256, script_sha256, sandbox_image_digest},
       provenance:'TESTED-provisional'|'abstain', high_stakes:True, handoff_id?}.
    Abstains (provenance='abstain') if result unavailable, QC-failed, or no
    in-silico prior exists. Divergence ('divergent') is a first-class signal:
    predicted and observed disagree in sign → filed as its own handoff (FC-2,
    conflict_type='insufficient')."""
```

### Consumed
- **FC-2** `inbox.file_handoff(kind, dossier)` — the approval gate + the divergence handoff.
- **FC-8** — this feature *is* an oracle (`wetlab_reconcile` registers in `REGISTRY`, returns the envelope, and its belief-write routes through `science.call → oracle_controls.guarded_call` per the 2026-07-13 oracle-guard rule).
- **FC-4** `value_queue` — additive `run_action="wetlab:<hypothesis>"`.
- **CCP-1** `IngestService.get_json/post_json(..., headers=None)` — cloud-lab bearer token.
- `sessions.ResearchSession(runs_dir, question, model=, metadata=)` — the capsule (`.record` / `.finalize`, sha256 event log) that makes the TESTED write replayable.

### CONTRACT CHANGE PROPOSAL
**CCP-34a (→ Lane 4 + Lane 2, non-blocking):** the `run_action` prefix dispatch site currently routes `"<oracle>:<args>"`→`science.call` and `"null_hunt:"`→`queue.enqueue` (CCP-19a). Add ONE prefix rule: `"wetlab:<hypothesis>"` → `inbox.file_handoff(kind="wetlab_approval", ...)`. **Additive, no FC-4/FC-8 signature change.** Requires Lane-4 ack (it owns the dispatch site in `app.py`). Until acked/landed, the `"wetlab:"` `run_action` is inert (renders as an advisory string) — exactly the fail-safe posture we want for a paid action.

---

## 3. Features

### F34.1 — Protocol draft + human-approval handoff (the gate)
- **Problem & evidence.** `value_queue.py:109-114` only mints `run_action="literature_search:..."` or `"null_hunt:..."`; a wet-lab question has nowhere to go. `CLAUDE.md` §7: submission "is high-stakes/cost → human-gated." The system must be *structurally incapable* of auto-submitting a paid experiment.
- **Design.** `value_queue.py` emits `run_action="wetlab:<hypothesis>"` for `cost_tier="expensive"` wet-lab-testable questions. The dispatch site (CCP-34a) routes that string to `inbox.file_handoff(kind="wetlab_approval", dossier=draft_protocol(...))`. `cloudlab.submit` **raises `ApprovalRequiredError`** unless `approval_handoff_id` resolves to a human-approved handoff. Submission is only reachable via `POST /wetlab/{handoff_id}/approve` (Lane 4), which is a human click.
- **Epistemic guardrails.** No network in `draft_protocol` (pure). `submit` is the only network-writing call and is guarded. Cost estimate from the skill's cached price table — never a model guess. `feasible=False` → abstain, no handoff spam.
- **Required experiment.** Covered by RQ-E48 (below) — the human-gating half.
- **Acceptance + check.** `assert cloudlab.submit(proto, approval_handoff_id="unapproved") raises ApprovalRequiredError` and an approved handoff succeeds against a stub lab. `pytest tests/test_wetlab_gate.py::test_no_auto_submit`.
- **Effort.** M. **Deps.** FC-2, CCP-34a ack.

### F34.2 — Submit → poll → ingest as TESTED (the loop body)
- **Problem & evidence.** No path turns an external physical result into a belief. `ingest/retraction.py` is the closest ingest primitive but is offline/read-only; `sessions.py:62` `ResearchSession` already gives replayable capsules with `input_sha256`/`events_sha256` (`sessions.py:52,100`).
- **Design.** On approval, `wetlab_submit` handler calls `cloudlab.submit`, records `submission_id` to `ops_dir/wetlab_submissions.jsonl`. `wetlab_watch.run(ops_dir=None)` (retraction-watcher-shaped; mirrors FC-19 `retraction_watch.run`) polls open submissions; on `status=='complete'` it opens a `ResearchSession`, calls `wetlab_reconcile.reconcile(...)`, and — if `verdict in {confirms,refutes}` and QC passes — writes the belief **TESTED-provisional** through `science.call → oracle_controls.guarded_call` (FC-8 oracle-guard path), with the session capsule attached.
- **Epistemic guardrails.** Result typed **TESTED-provisional** (never bare TESTED — human anchors the final upgrade, §7 discipline). QC-fail or no-prior → abstain. `wetlab_submissions.jsonl` append-only/immutable (a submitted paid experiment is a committed prior — no goalpost-moving, cf. FC-17).
- **Required experiment.** RQ-E48 (submit→ingest→reconcile end-to-end).
- **Acceptance + check.** On a stubbed completed positive-control result, `reconcile(...)["provenance"] == "TESTED-provisional"` and the membrane shows the TESTED write. `pytest tests/test_wetlab_loop.py::test_ingest_tested`.
- **Effort.** L. **Deps.** F34.1, FC-8, `sessions`, membrane.

### F34.3 — In-silico ↔ wet-lab reconciliation (divergence as signal)
- **Problem & evidence.** Persona already forms in-silico predictions (FC-8 oracles: MR `analysis/mr.run_mr`, DepMap `depmap_oracle.essentiality_verdict`, molecular gates PRD-08). Nothing checks them against physical reality. The scientific value is precisely in the *mismatch*.
- **Design.** `wetlab_reconcile.reconcile` pulls the claim's existing in-silico verdict (its `effect_sign`/`verdict` on the KG, FC-8 envelope), compares `predicted_sign` vs `observed_sign`. Agreement → `confirms`/`refutes` (strengthens/flips with TESTED weight). Sign disagreement → `verdict='divergent'`, filed as its own handoff (FC-2, `conflict_type='insufficient'`, `decision_requested="in-silico prediction contradicted by wet-lab"`). Divergence never silently overwrites — it escalates.
- **Epistemic guardrails.** Divergence is a *new* typed signal, not a bug to hide (mirrors the membrane's dual-signal discipline). Abstain if no in-silico prior exists (nothing to reconcile). Magnitude reported but sign drives the verdict (conservative).
- **Required experiment.** RQ-E48 negative control = a hypothesis whose wet-lab answer is *known-negative*; reconcile must classify `refutes`/`divergent` correctly, not `confirms`.
- **Acceptance + check.** Positive control → `confirms`; sign-flipped prior → `divergent` + a filed handoff id. `pytest tests/test_wetlab_reconcile.py::test_divergence_signal`.
- **Effort.** M. **Deps.** F34.2, FC-2, FC-8.

---

### Required experiment — RQ-E48 (Lane 3; register in `docs/RESEARCH_QUALITY_PROGRAM.md`)
- **Hypothesis.** The submit→ingest→reconcile loop, run on a **known positive control** (a hypothesis with a documented wet-lab answer — e.g. a well-characterized protein-binding pair Adaptyv can assay, with a published binding result) and a **negative control** (a hypothesis whose wet-lab answer is known-negative / no binding), (a) classifies the reconciliation verdict correctly and (b) **never auto-submits** — every submission is preceded by a resolved human-approved handoff.
- **Metric.** (a) correct verdict on both controls (`confirms` on positive, `refutes`/`divergent` on negative); (b) `auto_submit_count == 0` — every row in `wetlab_submissions.jsonl` has a matching human-approved `approval_handoff_id`; (c) abstain-correctly when the lab/assay is unavailable.
- **Gate.** Both controls classified correctly **AND** `auto_submit_count == 0` **AND** correct abstention on unavailable assay. Wet-lab TESTED writes stay `TESTED-provisional` (human anchors) regardless — the gate governs whether the loop may run unattended past the approval click, not whether it may skip the click.
- **Sandbox.** `experiments/exp_wetlab_loop.py` with a stub lab client (deterministic fixtures for the two controls) — the loop is not stochastic (deterministic fixtures), so no ≥20-seed requirement; the ≥20-seed rule applies to the stochastic guards, which this reuses (`oracle_controls`), not to the fixture classification. Cited in a `# see experiments/exp_wetlab_loop.py — RQ-E48` comment at the `reconcile` write site.

---

## 4. Sequencing
1. **M0 / interface-first:** land FC-26 stubs — `cloudlab.py` (`draft_protocol` returns a typed fixture, `submit` raises `ApprovalRequiredError` unconditionally, `poll`/`fetch_result` return `{available:False}`) and `wetlab_reconcile.reconcile` returning an `abstain` envelope; register `"wetlab_reconcile"` in `science.REGISTRY`. Commit-in-place so Lane 4 can build the surfaces against fixtures.
2. **F34.1** protocol draft + approval gate (the safety-critical half — build first, it is the invariant RQ-E48 checks).
3. **F34.2** submit→poll→ingest, then **F34.3** reconcile.
4. Wire `value_queue` `run_action` emit + get CCP-34a acked by Lane 4 before the dispatch site routes it.
5. `wetlab_watch` scheduler tick handed to Lane 1 (advisory, non-blocking).

## 5. Test plan
- `test_wetlab_gate.py` — `submit` without approval raises; with a resolved approved handoff, succeeds against the stub. (F34.1)
- `test_wetlab_loop.py` — end-to-end on stub fixtures: approve → submit → poll-complete → ingest → `TESTED-provisional`. (F34.2)
- `test_wetlab_reconcile.py` — positive control `confirms`; sign-flipped prior `divergent` + filed handoff; unavailable assay `abstain`. (F34.3)
- `experiments/exp_wetlab_loop.py` — RQ-E48 gate assertions (two controls + `auto_submit_count==0` + abstention).
- **One runnable check (the money check):** `python -c "import persona.ingest.cloudlab as c; c.submit({}, approval_handoff_id='nope')"` must raise `ApprovalRequiredError`.

## 6. Open questions
- **OQ-1 (blocking F34.2 real network).** Do the `adaptyv` / `ginkgo-cloud-lab` skills expose a *sandbox/dry-run* submission mode? If not, the live path must stay stubbed in CI and the real submit is exercised only manually behind the human gate. (Loop logic is fully testable against stubs regardless — non-blocking for merge.)
- **OQ-2 (blocking F34.3 control selection).** Which concrete positive/negative control pair does RQ-E48 use? Needs a hypothesis with a *documented, assay-matched* wet-lab answer Adaptyv actually offers (binding/expression/thermostability). Requires a domain pick before the experiment is meaningful — proposed default: a characterized binder/non-binder pair from the Adaptyv skill's example set.
- **OQ-3 (non-blocking).** Cost-tier ceiling: should an estimated cost above a threshold force a second human confirmation (two-key)? Deferred — the single approval gate satisfies the §7 invariant; add only if a user asks.
