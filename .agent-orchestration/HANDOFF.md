# HANDOFF — Persona build

> **Active detailed continuation contract:** read `docs/CONTINUATION_HANDOFF.md` first. It records exact current files, completed evidence, E03a dense-process reversals/live status, the frozen RQ-E12b GEO money-shot, verification commands, blockers, and the ambitious remaining sequence. The older phase checklist below is historical context and does not mean the research-quality overhaul is complete.

**Historical Phase-0 goal:** build the full Persona system per `planning/PHASE0_PLAN.md` §6 and keep it demoable at every checkpoint. The active research-quality contract is below; validate every change, but commit only when the user explicitly requests it.

## Frozen contracts
- **Separation:** swarm READS, never writes to the self. Only the membrane commits. Reasoning is single-agent; fan-out is reading only.
- **Belief-store (5.3, bi-temporal, two-tier):** claim nodes carry `provenance_state ∈ {READ, INFERRED, HUMAN_CONFIRMED, TESTED}`, `anchor: bool`, `logit`/`calibrated_p`, sources w/ independence group, `valid_from/valid_to`, history. Write-policy: READ/INFERRED cannot move a HUMAN_CONFIRMED/TESTED anchor beyond `resist`; only human sign-off moves an anchor.
- **Membrane:** convergence(evidential-independence) + provenance + calibration; adaptive fast-path↔strict. The proposed, not-yet-validated review taxonomy is `{extraction_error, true_refutation, context_divergence, insufficient_evidence}`; all current sign collisions remain `candidate_conflict / unverified` until RQ-E02 passes.
- **Ignition is human-gated** (contradiction detection ~30% FP). Self-test loop autonomy = read/dossier/first-pass; anchoring needs sign-off.

## Locked decisions
Persistent persona / source-agnostic / always-on reading swarm · full impl (+2nd researcher) · Vite+React+Motion+Cytoscape · live-early data behind cache.

## Dispatch log
| When | Who | Task | Result |
|---|---|---|---|
| Phase 0 | main | plan + reproduce + literature | committed 3e51e68 |
| Step 1 | main | belief-store + living-doc self + live ingestion | done 773d0c3 (9 tests) |
| Step 2 | main | swarm + adaptive membrane + inner loop | historical checkpoint: done 5c3b901 (19 tests then) |
| E10 gate | main | adaptive switch experiment (50 seeds) | GO: detect 1.00, false-strict 0.00, retention 1.00 |
| Step 3 | engine agents | trajectory / dependency / experiment_value | dispatched |

## Build sequence status (PHASE0_PLAN §6)
- [x] 0 — reproduction (PASS; crossover to the digit; Confound A refined)
- [x] 1 — belief-store + living-doc self + live source-agnostic ingestion
- [x] 2 — reader/extractor swarm + adaptive membrane (E10 GO, E14 GO; E8/E12 need API key)
- [x] 3 — engine (trajectory/dependency/experiment_value) + dashboard + argument-state (E5 pending real data)
- [x] 4 — hypothesizer + dataset-scout + self-test (live GEO; reanalysis replay-labelled), human-gated
- [x] 5 — handoff inbox + anchoring; dependency graph as candidate edges (E9 GO; E11/E6 pending)
- [x] 6 — experiment-value queue; mini-review; self-spawned interest (E13 GO; E7 pending)
- [x] 7 — always-on autonomous run (self-spawned interest visible)
- [x] 8 — stretch: silence / cross-field (honest baselines) / fragility (in dependency.py)
- [x] 9 — second researcher (a lab; disagreement = signal); UI verified live

**Historical demo-plan status: all listed Phase-0 build steps were marked done.** This is not completion of the active research-quality program. Sim-testable gates GO (E9/E10/E13/E14) + reproduction PASS.
Resource-gated experiments (E5/E6/E7/E8/E11/E12/E15) remain pre-registered stubs — need
real outcome data / expert annotations / an API key. The old 52-test statement is historical and
not reproducible under the current scoped test configuration; see the active handoff for current checks.

## 2026-07-11 research-quality program

### Goal

Turn the existing demo into a scientific workbench that can ingest broad evidence, preserve claim-level provenance and reasoning lineage, coordinate large swarms without quality collapse, execute computational work, and emit publication-grade artifacts that tell humans what is known, contested, testable, and worth doing next.

### Frozen contract

- Preserve the tested self/swarm separation, adaptive membrane, provenance states, and anchored-belief overwrite rules above.
- Treat current `persona/api/static/index.html` edits and `persona/api/static/index_v6_backup.html` as user-owned; inspect before overlap and never discard them.
- No architecture, learning, memory, or scaling mechanism ships from rhetoric alone. Record a falsifiable hypothesis, baseline, metric, gate, and reproducible experiment first; use at least 20 seeds for stochastic experiments.
- Agents may generate candidate evidence, code, and artifacts only inside session-scoped workspaces. Durable belief changes still cross the membrane; human-significant conclusions expose evidence trees and uncertainty.
- Prefer existing runtime, libraries, data models, and native formats. Add dependencies only after a measured need.

### Unknowns / resolved questions

- [x] Which code paths currently own research ingestion, synthesis, retrieval, run lineage, compute, and artifact rendering?
- [x] What do existing Curie runs contain, and which failures recur across them?
- [ ] Which current approaches measurably improve agent research quality and large-team coordination? RQ-E01a, E03a, E07a, and the evidence-session forward test are complete; human-semantic retrieval, live equal-budget swarm, and contradiction-verifier experiments remain.
- [ ] Which minimal UI restructuring makes arguments, contradictions, evidence, experiments, and next actions legible?

### Dispatch log

- `repo-audit`: read-only architecture, tests, data, and Curie-run manifest.
- `research-scout`: primary-source review of autoresearch, agent learning, memory, and large-team orchestration.
- `ui-audit`: read-only runtime/UI audit with exact user-visible failures and design-system inventory.

### Acceptance checks

- Detailed living plan names every experiment, dataset/fixture, baseline, metric, seed count, and go/no-go gate.
- New experiments save raw results and charts; findings distinguish simulated evidence, live evidence, and unrun preregistrations.
- One end-to-end research session preserves sources, snippets, claims, derivations, code, execution logs, figures, and artifacts, and supports replay/audit.
- UI proves the primary flow in-browser: research question to evidence tree to contradiction/test to next action or human dossier.
- Existing tests plus targeted new tests, build checks, and browser smoke pass.

### Evidence

- Initial runtime snapshot: 5,368 claims, 5,037 entities, 63 sign-collision candidates, 18 synthesis notes, and 12 projects on `curie-3c33`. After the extraction correction, the frozen 2026-07-11 RQ-E02 pair set is 62 (hash recorded in `docs/RESEARCH_QUALITY_PROGRAM.md`).
- Reproduced malformed self state: 315 single-character bullets; model output crossed an unvalidated list boundary.
- Reproduced false contradiction: both microglia/tau quotes describe exacerbation but one stored polarity is negative.
- Reproduced hidden read spend: two GET digest requests cost $0.0887.
- Current UI invents ambient agents and epistemic metrics, does not use the real field map/history, and can leak cached state across personas.
- Primary-source research and all preregistered experiments are recorded in `docs/RESEARCH_QUALITY_PROGRAM.md`; raw audit notes are in `docs/BUILD_NOTES.md`.
- RQ-E01a: 5,704 real claims × 30 seeded resamples; exact-span admission reduced non-verbatim evidence from 24.0% ± 0.7% to zero. Lexical polarity was rejected as an admission gate.
- RQ-E07a: 30 paired replays through N=1,000; central source partitions peaked at N=3, while effective team size saturated near 14–15 by N=100–1,000. Default workers changed 6 → 3; dense debate rejected.
- First session forward test was invalidated because generic retrieval omitted the triggering claims despite valid-looking citations. Required-evidence pinning was added and the second session passed.
- Live correction proof at that checkpoint: bad claim `clm_9272dc679319` is preserved as `REJECTED_EXTRACTION`; active microglia/tau candidate matches are zero; corrected claim `clm_33711b72f30d` has two independent exact-source records. The checkpoint suite had 8 passing tests; the current suite has 11.
- Session/workbench proof: corrected run passes 34-event/20-artifact replay with 2/2 required claims and a reviewed sandbox figure; no-worker Chromium smoke passes the Research list/detail flow.
- RQ-E12a exposed and fixed stale-PDF false success, shell-injectable LaTeX filenames, nondeterministic PDF hashes, and colliding paper workspaces. Real read-only Docker regression passes all four integrity gates; the checkpoint suite had 9 passing tests, and the current suite has 11.
- Reusable `evidence-first-research-session` skill created under the user Codex skill directory. Its independent local-only forward test now passes with 14 ordered events, six hash-valid artifacts, 2/2 required claims, zero verifier warnings, and a fresh scoped scientific verdict. It found a second likely sign-label extraction error without overclaiming wider-literature truth.
- Figma discovery/gotcha prerequisites are complete. The connector currently requires user reauthentication, so Figma mutation is paused; `docs/SCIENTIFIC_WORKBENCH_SPEC.md` preserves the implementation-ready design contract.
- RQ-E03a completed on 6,274 records and 200 fixed structural queries. Hybrid F1 improved only +0.010 over the best single arm, failing the +0.050 gate; dense/hybrid deployment is rejected pending human-labeled E03b. Session retrieval remained weak (~0.524 Recall@10 on two sessions).
- RQ-E12b produced the first real zero-model-cost public-data loop with 20/20 exact numeric reruns. Independent review then contested interpretation: 10,000-draw/HC3 and no-FTL sensitivities all include zero; FTL probes materially affect magnitude; original PNG bytes did not reproduce. Append-only correction leaves the branch `inconclusive`; session `20260711T194501Z-does-a-prespecified-nrf2-associated-tran-08c6fd9b` now passes 58 events/30 artifacts/2 claims/$0 with latest verdict `contested` while computation integrity remains verified. Events 56–58 are a preserved redundant audit append from an unsafe historical help probe, not new science; current CLIs are guarded.
- Candidate conflicts now open full exact-evidence/context-gap/next-check dossiers. Four labels write to an append-only hash-chained ledger and never mutate beliefs; direct anchor resolution is disabled until RQ-E02 passes. This is a single-process pilot only: reviewer/assignment/blinding metadata, duplicate-review prevention, and cross-process serialization are required before two-rater gold collection. Live browser/API smoke passed and no synthetic review was written. Current integrity suite: 11 passed.

### Verdict

- Steps 1–2 are complete and evidenced. E03a is complete and rejects hybrid deployment; E03b semantic labels and RQ-E02 human contradiction gold remain open. The reusable evidence-session workflow passes an independent forward task, and RQ-E12b proves reproducible core numeric computation inside one real cached-data loop with 20/20 clean reruns. Its interpretation remains contested and its original PNG is not byte-deterministic. Full multi-task executable-science/AstaBench and independent biological replication remain open.

## Validation rule
Every increment: run a real test (assert-based or driven end-to-end) and record the evidence. Commit only when the user explicitly requests it. Put every load-bearing unproven sub-choice through a sandbox experiment under `experiments/` first (at least 20 stochastic seeds with mean and 95% CI where stochasticity exists).
