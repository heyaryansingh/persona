# HANDOFF — Persona build

**Goal:** build the full Persona system (persistent synthetic researcher) per `planning/PHASE0_PLAN.md` §6, demoable at every checkpoint, validating with real tests and committing frequently.

## Frozen contracts
- **Separation:** swarm READS, never writes to the self. Only the membrane commits. Reasoning is single-agent; fan-out is reading only.
- **Belief-store (5.3, bi-temporal, two-tier):** claim nodes carry `provenance_state ∈ {READ, INFERRED, HUMAN_CONFIRMED, TESTED}`, `anchor: bool`, `logit`/`calibrated_p`, sources w/ independence group, `valid_from/valid_to`, history. Write-policy: READ/INFERRED cannot move a HUMAN_CONFIRMED/TESTED anchor beyond `resist`; only human sign-off moves an anchor.
- **Membrane:** convergence(evidential-independence) + provenance + calibration; adaptive fast-path↔strict; emits TYPED contradiction {true-refutation, context-divergence, no-evidence}.
- **Ignition is human-gated** (contradiction detection ~30% FP). Self-test loop autonomy = read/dossier/first-pass; anchoring needs sign-off.

## Locked decisions
Persistent persona / source-agnostic / always-on reading swarm · full impl (+2nd researcher) · Vite+React+Motion+Cytoscape · live-early data behind cache.

## Dispatch log
| When | Who | Task | Result |
|---|---|---|---|
| Phase 0 | main | plan + reproduce + literature | committed 3e51e68 |
| Step 1 | main | belief-store + living-doc self + live ingestion | done 773d0c3 (9 tests) |
| Step 2 | main | swarm + adaptive membrane + inner loop | done 5c3b901 (19 tests) |
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

**All build steps done.** Sim-testable gates GO (E9/E10/E13/E14) + reproduction PASS.
Resource-gated experiments (E5/E6/E7/E8/E11/E12/E15) remain pre-registered stubs — need
real outcome data / expert annotations / an API key. 52 tests green; UI driven end-to-end.

## Validation rule
Every increment: real test (assert-based or driven end-to-end) → run it → commit. Unproven sub-choice → sandbox experiment under `experiments/` first (≥20 seeds, mean±95%CI).
