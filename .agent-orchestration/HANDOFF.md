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
| Step 1 | main | belief-store + living-doc self (pure stdlib) | in progress |

## Build sequence status (PHASE0_PLAN §6)
- [x] 0 — reproduction (PASS; crossover to the digit; Confound A refined)
- [ ] 1 — belief-store + living-doc self + live source-agnostic ingestion
- [ ] 2 — reader/extractor swarm + adaptive membrane (gate E8/E10/E12/E14)
- [ ] 3 — trajectory engine + dashboard + argument-state (gate E5)
- [ ] 4 — hypothesizer + dataset-scout + Claude Science self-test, human-gated (gate E15)
- [ ] 5 — handoff inbox + anchoring; dependency graph (gate E9/E11/E6)
- [ ] 6 — experiment-value queue; mini-review; self-spawned interest (gate E7/E13)
- [ ] 7 — always-on autonomous run
- [ ] 8 — stretch: silence / cross-field / fragility (gate H3.5/H3.6/H3.3)
- [ ] 9 — second researcher; polish; fallback recording

## Validation rule
Every increment: real test (assert-based or driven end-to-end) → run it → commit. Unproven sub-choice → sandbox experiment under `experiments/` first (≥20 seeds, mean±95%CI).
