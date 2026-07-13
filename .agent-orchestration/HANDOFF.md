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

---

## 2026-07-12 Feature-expansion program (Lanes 1–4) — LIVE DISPATCH BUS

> This section is the **single communication bus** for the parallel feature build. Specs live in `docs/prd/PRD-00…04`. The frozen contracts (**FC-1…FC-7**) and disjoint file-ownership map are in `docs/prd/PRD-00-overview.md` §3–4 — that file is the single source of truth for interfaces. All prior *Frozen contracts* / *Locked decisions* above remain authoritative.

### Goal
Turn existing-but-unwired primitives into closed loops and upgrade the swarm from a linear pipeline into a heterogeneous verifying team. Four parallel implementer lanes, one reviewer, coordinated here. Decisions locked with the user: all four themes; **Balanced** autonomy (auto-open/re-investigate + narrow reanalysis→TESTED-provisional, **anchors + high-stakes stay human-gated**); flagship = "Field-rests-on-this + value queue"; self-benchmarking now.

### Lanes & ownership (do not edit outside your set; cross-lane needs go through an FC)
| Lane | Theme | Owns | Provides / Consumes |
|---|---|---|---|
| **1** | Heterogeneous teams | `agents/{verifier*,debate*,analyst,critic,revisit,director,discover,deliberate}`, `research/investigation.py`, `daemon/{supervisor,queue}`, `reading/{extract,reader}` | provides FC-1 · consumes FC-2, FC-5 |
| **2** | Calibrated membrane | `memory/{membrane,kg,coherence,history,vectors,calibrate*,conflicts*}`, `conflict_reviews.py`, `inbox.py*` | provides FC-2, FC-3, FC-5 · consumes FC-1, FC-6 |
| **3** | Intellectual engine | `analysis/{forensics,dependency*,trajectory*,value_queue*,darklit*}`, `agents/audit.py`, `synthesis/{fieldmap,synthesizer,consolidator}`, `ingest/{sources,retraction*}`, `tools/{science,datasets}` | provides FC-4, FC-6 · consumes FC-2, FC-3 |
| **4** | Legibility & benchmarks | `api/app.py` (new routes), `api/static/index.html` (new surfaces), `sessions.py` (RO-Crate add), `eval/*`, `experiments/*` (new), `tests/*` (new) | provides FC-7 · consumes FC-2..FC-6 |

### Communication protocol (this is how agents stay in sync)
1. **One bus.** Every agent appends a row to the dispatch table below on each state change. Status vocabulary: `CLAIMED → IN-PROGRESS → BLOCKED(reason) → PR-READY → REVIEWED → VERIFIED`.
2. **Interface-first (Milestone 0).** Every lane lands its *provided* FC stubs (exact signatures + fixture returns) before filling implementations, so the other lanes unblock immediately.
3. **Contract-change rule.** No lane changes an FC unilaterally. Post a `CONTRACT CHANGE PROPOSAL` row naming the FC + the diff; the master **and every consuming lane** must ack before it lands.
4. **File-claim rule.** Before editing any boundary file, claim it in the table so no two agents touch it at once.
5. **Blockers are public.** If you need an FC/feature that isn't ready, post `BLOCKED` naming the lane/FC you're waiting on; the providing lane (or master) responds with an ETA or a stub.
6. **Reviewer** reads `PR-READY` rows, audits against the PRD acceptance criteria **and** the epistemic discipline (exact-span, provenance typing, no fabricated confidence, applicability gates, human-anchors-high-stakes), and posts `REVIEWED` (pass) or a findings row.
7. **Master** (orchestrator / main session) assigns lanes, resolves contract disputes, sequences per PRD-00 §5, and keeps the ideation backlog flowing (see below).
8. **Research-and-verify.** Any load-bearing choice gets its RQ experiment (PRD-00 §6) *before* wiring, ≥20 seeds, cited in a code comment. Commit only when the user asks.

### Milestone 0 checklist (unblocks everyone)
- [ ] L1: register `verify`/`debate` task types + `investigation.open_from_conflict(...)` stub (FC-1)
- [ ] L2: `inbox.file_handoff` (FC-2), `kg.provenance_breakdown`/`add_dependency_edge`/`dependency_edges`/`citation_support_ratio` (FC-3), `calibrate.admit_decision` (FC-5) stubs
- [ ] L3: `engine.dependency_graph`/`engine.value_queue` (FC-4), `retraction.is_retracted`/`contamination` (FC-6) stubs
- [ ] L4: `eval.run_oracle` (FC-7) stub; flagship screen scaffolded against FC-4 fixtures

### Dispatch table (append rows; newest at bottom)
| When | Lane/Agent | Feature id | Status | Note |
|---|---|---|---|---|
| 2026-07-12 | ideation | PRD-00..04 | VERIFIED | all 4 lane PRDs written + FC-coherent (docs/prd/); grounded against real code |
| 2026-07-12 | master | cross-lane OQs | RESOLVED | 15 open questions resolved below; FC-1/FC-3 amended in PRD-00 §4 |
| 2026-07-12 | — | L1–L4 | READY-TO-CLAIM | implementers: start at Milestone 0 (land your FC stubs), then claim features per your PRD |
| 2026-07-13 | ideation | PRD-05..10 | READY-TO-CLAIM | second-researcher(L1+2), executable-MR(L3), DepMap-oracle(L3), molecular-gates(L2), red-team(L1), meta-analysis(L3) — written to docs/prd/, FC-coherent |
| 2026-07-13 | master | PRD-05..10 OQs | RESOLVED | batch-2 resolutions below: FC-8 (oracle envelope) + FC-9 (reconcile) ratified; CCP-1 → Lane 3; RQ-E20..E25 assigned (RQ-E20 collision fixed) |
| 2026-07-13 | ideation | PRD-11..15 | READY-TO-CLAIM | contradiction-gold(L2+4), causal-gate(L2), fragility-sim(L4), sleep-consolidation(L2), calibration-panel(L4) — FC-coherent |
| 2026-07-13 | master | PRD-11..15 OQs | RESOLVED | batch-3 below: FC-10 (causal-tier), FC-11 (sleep-consolidation), FC-4.fragility_cascade, CCP-11a ratified; RQ-E26..E29 assigned (E26 collision fixed); protection oracle corrected → experiments/exp_poisoning.py |
| 2026-07-13 | ideation | PRD-16..20 | READY-TO-CLAIM | oracle-control-injection(L3), FDA-surrogate-gate(L2), LEGEND-RWE(L3), null-hunt-swarm(L1+3), confidence-budget(L2) — FC-coherent |
| 2026-07-13 | master | PRD-16..20 OQs | RESOLVED | batch-4 below: FC-12 (clinical gate) + FC-13 (confidence-budget) + FC-8 additions (controls/pipeline_health, READ, lookup capsule) ratified; RQ-E30..E34 (four-way E30 collision fixed); oracle-guard routing + run_action dispatch rule |
| 2026-07-13 | ideation | START-HERE | INFO | **`docs/prd/IMPLEMENTER_START_HERE.md`** — per-lane Milestone-0 + first-fill order across all 23 PRDs. Implementers: read PRD-00 once, then follow your lane. Binding constraint is now implementation, not specs — claim a lane. |
| 2026-07-13 | ideation | PRD-21..23 | READY-TO-CLAIM | cross-field-translation(L3), verifier-calibration-monitor(L1), SemMedDB(L3) — FC-coherent, cores self-contained |
| 2026-07-13 | master | PRD-21..23 OQs | RESOLVED | batch-5 below: FC-14 (crossfield) + FC-15 (verifier-monitor) + FC-16 (SemMedDB) ratified; RQ-E35..E37 (three-way E35 collision fixed); CCP-21a adopted; CCP-23a constraint frozen |
| 2026-07-13 | reviewer | coherence audit | RESOLVED | audit found PRD-body drift from the master fixes + 2 unfixed source collisions (E15 dual-use, E16/E17 swap) → PRD-00 §8 reconciliation (§4/§6 govern) + new E38/E39; batch-6 below |
| 2026-07-13 | ideation | PRD-24..27 | READY-TO-CLAIM | prediction-ledger(L2+4), claims-blocklist(L2+4), counterfactual-sim(L3+4), retraction-watcher(L2+3) — RQ-E40..E43 pre-assign held |
| 2026-07-13 | master | PRD-24..27 OQs | RESOLVED | batch-7 below: FC-17/18/19 (three-way FC-17 collision fixed); FC-3/FC-4 additions; CCP-24a/25a/26a/26b/27a ratified |
| 2026-07-13 | ideation | PRD-28..31 | READY-TO-CLAIM | EIG-ranking(L2+4), frontier-map(L3+4), negative-space(L3), tier-upgrade-pathway(L4) — FC-20..23 + RQ-E44..46 pre-assign HELD, zero collisions |
| 2026-07-13 | master | PRD-28..31 OQs | RESOLVED | batch-8 below: FC-20..23 confirmed; RQ-E44/45/46; CCP-29a/30a advisory→L1; PRD-29 graceful-degrade ratified |
| 2026-07-13 | ideation | PRD-32..33 | READY-TO-CLAIM | Pareto-swarm-sizing(L1+4), confidence-report-card(L4) — FC-24/25 + RQ-E47 pre-assign held |
| 2026-07-13 | master | PRD-32..33 OQs | RESOLVED | FC-24 (swarm economics) + FC-25 (report_card) confirmed, PRD-00 §9; RQ-E47 (sizing); **PRD-33 band vocab → ONE shared Lane-4 vocabulary** (reconcile w/ PRD-11/15); PRD-32 ε-exploration gated on RQ-E47 |
| 2026-07-13 | ideation | PRD-34..35 | READY-TO-CLAIM | cloud-lab wet-lab loop(L3, FC-26/RQ-E48), standing-colleague(L1+4, FC-27/RQ-E49) — pre-assign held, zero collision; both self-contained, wet-lab submit human-gated (`ApprovalRequiredError`) |
| 2026-07-13 | master | PRD-34..35 OQs | RESOLVED | batch-10 below: FC-26/FC-27 confirmed (PRD-00 §9); RQ-E48/E49 (§6); CCP-34a (`"wetlab:"` run_action prefix → `inbox.file_handoff`, dispatch site NEVER calls `cloudlab.submit`) → Lane 4+2 ack; PRD-35 O-1 trigger semantics default frozen |
| 2026-07-13 | ideation | PRD-36..37 | READY-TO-CLAIM | contradiction-independence-precheck(L2, **FC-28/RQ-E50**), Gail-Simon-effect-modification(L3, **RQ-E51**, additive to FC-4/forensics — no new FC) — workflow `wqih989vv` done (2/2, 0 err); both real-code-grounded + house-style; pre-assign held, zero collision |
| 2026-07-13 | master | PRD-36..37 OQs | RESOLVED | batch-11 below: FC-28 confirmed (PRD-00 §9); RQ-E50/E51 (§6); **CCP-36a** (`gate` enum += `'independence'`); cross-cutting ownership ruling (providing lane owns its `exp_*.py`+unit test); PRD-37 all OQs → defaults accepted |
| 2026-07-13 | ideation | PRD-38..39 | READY-TO-CLAIM | meta-research-self-study(L3+4, **FC-29/RQ-E52**), explanation-faithfulness-check(L3, **no new FC/RQ-E53**) — workflow `wlluvxduz` done (2/2, 0 err, 278k tok); real-code-grounded + house-style; **FC-30 reserved-then-returned (unused → back in pool)** |
| 2026-07-13 | master | PRD-38..39 OQs | RESOLVED | batch-12 below (res. 75–82): FC-29 confirmed (§9); RQ-E52/E53 (§6); PRD-39 additive (no new FC, FC-30 returned); `_MIN_TREND_N`=10 default, import `calibrate._P_COMMIT`, **component_value stays observational v1 (no causal contract minted)**, RQ-E53 offline-gate, defer audit-rationale faithfulness |
| 2026-07-13 | ideation | PRD-40..41 | READY-TO-CLAIM | dead-end/rabbit-hole-detector(L1, **FC-30/RQ-E54**), mechanistic-model→novel-prediction-generator(L3, **FC-31/RQ-E55**) — workflow `whrt707rc` done (2/2, 0 err); FC-30 reclaimed; pre-assign held, zero collision |
| 2026-07-13 | master | PRD-40..41 OQs | RESOLVED | batch-13 below (res. 83–89): FC-30/FC-31 confirmed (§9); RQ-E54/E55 (§6); CCP-40a (FC-30 render→L4) + CCP-41a (mechanism `discover.py` hook→L1); PRD-40 OQs→defaults (yield-attribution deferred, round=cost-step, reprioritize=slot-yield); FC-31 differentiated from FC-22 |
| 2026-07-13 | ideation | PRD-42..43 | AUTHORING | prospective-forecasting(L1+4, **FC-32/RQ-E56**), whole-graph-self-consistency-sweep(L2, **FC-33/RQ-E57**) — workflow `wzyovh1lx` in flight; pre-assign held; resolve batch-14 on completion (next free after: FC-34, RQ-E58) |

### Master resolutions — 2026-07-12 (ratified; consumers may build on these)
Cross-lane questions the four PRD authors surfaced, decided by the master. FC amendments are reflected in `docs/prd/PRD-00-overview.md` §4.
1. **`worker.py` = shared append-only handler registry.** Each lane appends its `@handler` block inside a delimited `# --- Lane N handlers ---` section; never edit another lane's. Master serializes the final merge. Not a Milestone-0 blocker.
2. **Debate-unresolved `conflict_type` = `insufficient`** (FC-2). Confirmed — no determinable temporal/semantic/misinfo type for a debate that failed to converge.
3. **Consensus module = new `persona/agents/consensus.py`** (Lane 1 owns) exporting `span_weighted_consensus(...)`; Lane 2 imports from `persona.agents.consensus`. (Not buried in `verifier.py`.)
4. **F1.6 surprise signal** — Anthropic API exposes no logprobs, so use **embedding-novelty (distance to nearest existing claim vector) + contradiction-magnitude** as the surprise proxy; validate via RQ-HT06. Approved.
5. **F2.2 NLI judge = ALLOWED as a boolean gate only.** A model may judge span-level entailment (entails / not) iff (a) it cites the exact entailing span with stored offsets, (b) it **never** sets confidence (confidence comes only from `calibrate` + independence counts), (c) its boolean is confirmed against KG-support before admission (dual-signal). LLM proposes, code/KG confirms.
6. **FC-1 gains task type `staleness`** (contract addition, ratified). Lane 1 registers it in `supervisor.py`/`worker.py`; it calls Lane 2's `conflicts.revisit_pass(...)`. FC-1 task types are now `verify`, `debate`, `staleness`.
7. **Name-collision noted, no rename.** `analysis/calibration.py` (existing replication-prior curve) ≠ `memory/calibrate.py` (new FC-5 admission bound). Distinct purposes; both retained.
8. **FC-4 resolves via a new thin `persona/analysis/engine.py` facade** (Lane 3 owns; re-export only, no logic). Consumers import `engine.dependency_graph`/`engine.value_queue` from `persona.analysis.engine`. Added to Lane 3 ownership.
9. **FC-3 gains `kg.set_citation_class(claim_id, citing_id, cls:'support'|'contrast'|'mention', span:str) -> None`** (contract addition, ratified). Tri-classification + spans are stored KG-side (Lane 2 writer); Lane 3's `dependency.py` computes and calls the writer; `kg.citation_support_ratio` reads.
10. **VoI auto-dispatch is gated on RQ-E17.** Until RQ-E17 (VoI ranking beats citation baseline vs expert) passes, `value_queue` is **advisory** (human clicks "run"). After it passes, Balanced autonomy permits auto-dispatch of `public_data`-tier **narrow** reanalyses into TESTED-provisional only.
11. **Gate-decisions ledger = shared append-only `ops_dir/gate_decisions.jsonl`**, row `{candidate_id, title, gate:'relevance'|'drift'|'membrane', decision:'admit'|'skip'|'abstain', reason, score, at}`. Lanes 1 (relevance/reader) + 2 (drift/membrane) WRITE (append-only, never edit others' rows); Lane 4 READS for F4.6.
12. **F4.2 depends on F3.8.** The auditor's skipped-vs-passed rendering requires Lane 3's forensics applicability gates (`not_applicable` state) to land first.
13. **Nav IA (adopt Lane 4's recommendation, revisitable):** flagship "Field-rests-on-this + value queue" = a top destination; robustness "trust" tab = top destination; handoff inbox = top destination ("Judgment", replacing the ambiguous Review label); epistemic-status = a Map subtab.
14. **Theme:** scope the dark editorial workbench theme to the flagship + new surfaces this wave; do not reskin the whole app yet.
15. **Benchmarks ship a frozen LitQA2/BixBench fixture subset** for offline/no-cost demo (matches the cache-the-demo discipline).

### Master resolutions — batch 2, 2026-07-13 (PRD-05..10)
16. **FC-8 ratified** — shared acting-loop oracle verdict envelope + `science.REGISTRY` registration + FC-4 `run_action "<oracle>:<args>"` invocation (MR / DepMap / meta-analysis). Lane 4 = one oracle renderer. (Full spec in PRD-00 §4.)
17. **FC-9 ratified** — cross-persona `reconcile.belief_diff` / `reconcile.reconciliation_dossier` (PRD-05) for Lane 4 rendering.
18. **CCP-1 → Lane 3** — additive `headers=None` on `IngestService.get_json/post_json` (backward-compatible); Lane 3 lands it for OpenGWAS; any lane may use.
19. **PRD-05 core edits (Q1) → Lane 1** — additive `disposition` kwarg on `manager.create` + one `config.SELF_FILES` entry. Claim `manager.py`/`config.py` in the dispatch table before editing (unassigned core files).
20. **worker.py task-type registry** now includes `verify, debate, staleness, redteam, depmap_check` (append-only, delimited blocks). MR / meta-analysis / reconcile run via `science.call` / value_queue, not new task types, unless a lane prefers one.
21. **gate_decisions.jsonl gate enum += `'redteam'`** (CCP-09-A) — additive/backward-compatible. Red-team default = **procedural block** (FC-2 handoff reaches the human before the already-human-gated anchor). The **hard block** (`calibrate.admit_decision` consults the redteam row to downgrade `route` commit→human) is deferred until RQ-E25 passes.
22. **PRD-08 priors are Lane-2 membrane priors (INFERRED), not FC-8 oracles.** Optional `science.REGISTRY` registration (CCP-08a) ratified → Lane 3 routes it; core membrane capability needs no cross-lane change.
23. **RQ-id canonicalization (fixes the RQ-E20 collision):** E20 = disposition-functional (PRD-05) · E21 = MR pos/neg controls (PRD-06) · E22 = DepMap control-validation (PRD-07) · E23 = molecular-prior precision (PRD-08, alias M08) · E24 = meta-analysis published-reproduction (PRD-10) · E25 = red-team reversal-reduction (PRD-09, alias RT01). Each seeded ≥20, go/no-go gate, offline fixtures, registered in `docs/RESEARCH_QUALITY_PROGRAM.md` before it drives autonomy.

### Master resolutions — batch 3, 2026-07-13 (PRD-11..15)
24. **FC-10 ratified** — causal-strength gate (PRD-12); Lane 2 provides, Lane 3 (synthesis/document language gate) + Lane 4 (tier columns) consume. (Spec in PRD-00 §4.)
25. **FC-11 ratified** — sleep-consolidation (PRD-14); Lane 2 provides. **CCP-10:** Lane 3 adds ONE additive `consolidate_sleep.run(...)` line at the end of `synthesis/consolidator.consolidate()`. Ships **dry-run** until RQ-E28 passes.
26. **FC-4.fragility_cascade ratified (CCP-13a)** — Lane 3 provides `engine.fragility_cascade`; Lane 4 renders via read-only `GET /engine/fragility`. Pure what-if; never mutates a belief.
27. **CCP-11a ratified** — `conflict_reviews.append_conflict_review` gains `reviewer_id/batch_id/side_order` + batch/blinding fns + a cross-process lock (PRD-11, Lane 2). **Lane 4 updates the `app.py:698` call site in the same coordinated change.** Gold is never synthesized; no ≥2 reviewers → ship blinded bundle+UI + STOP.
28. **RQ-id canonicalization (fixes the four-way E26 collision):** E26 = causal-tier precision (PRD-12, human labels) · E27 = fragility face-validity (PRD-13, optional) · E28 = sleep-consolidation protection gate (PRD-14) · E29 = calibration auditor-outcome oracle (PRD-15, optional).
29. **Protection-oracle correction:** use `experiments/exp_poisoning.py` (live), NOT `exp_when_protection_matters.py` (archived under `archive/experiments_v3/`). Applies to PRD-01 HT05 + PRD-14 RQ-E28.
30. **`history.stale_claims` single-definition** → owned by PRD-02 F2.9; PRD-14 consumes it (do not redefine — both Lane 2).

### Master resolutions — batch 4, 2026-07-13 (PRD-16..20)
31. **RQ-id canonicalization (fixes the four-way E30 collision):** E30 = oracle control-injection fault-injection (PRD-16) · E31 = FDA-surrogate detector precision (PRD-17) · E32 = LEGEND numeric-match (PRD-18) · E33 = null-hunt enrichment (PRD-19) · E34 = confidence-budget over-drawn→reversal (PRD-20).
32. **FC-8 envelope additions (CCP-16a + CCP-18a) ratified** — optional `controls`/`pipeline_health` fields + quarantine transform (PRD-16); `provenance` enum += `"READ"` + a lookup-oracle capsule for non-code-run oracles (PRD-18 LEGEND). Backward-compatible. (Spec in PRD-00 §4.)
33. **Oracle-guard routing** — every FC-8 oracle belief-write routes through `science.call → oracle_controls.guarded_call`; each oracle adds a pure `verdict_from_*` hook + reuses its RQ fixtures as controls; **fail-open (explicit `skipped`) until RQ-E30 passes, then fail-closed.** PRD-07 `depmap_check` worker uses the guarded path, not a direct import (PRD-16 O-1/O-3/O-4).
34. **FC-12 collision resolved:** FC-12 = clinical surface-class gate (PRD-17, `fda_surrogate.*`/`clinical_gate.*`). **FC-13** = confidence-budget read interface (PRD-20, `budget.*`). Both Lane 2 → Lane 4; advisory until E31/E34.
35. **run_action dispatch rule (CCP-19a):** `run_action` prefix decides dispatch — `"<oracle>:<args>"` → `science.call`; `"null_hunt:<target>"` → `queue.enqueue("null_hunt", ...)`. Additive; dispatch-site owner (Lane 3 auto-dispatch / Lane 4 run button) implements.
36. **`clinical_trials` `WhyStopped` field** → PRD-03 F3.9 adds it (one token) so terminated-trial nulls become typed claims for PRD-19.
37. **New-file ownership rule:** a NEW, non-colliding file is owned by the lane whose PRD creates it, any directory (`ingest/fda_surrogate.py`→L2; `analysis/oracle_controls.py`→L3). Existing files keep their §3 lane.
38. **Intra-Lane-2 coordinated edits (not parallel rewrites):** PRD-20 F20.3's one-line clamp in `membrane.admit_candidate` and the shared `history.stale_claims` land after PRD-02 F2.1/F2.3/F2.9.

### Master resolutions — batch 5, 2026-07-13 (PRD-21..23)
39. **RQ-id canonicalization (three-way E35 collision):** E35 = cross-field recovery (PRD-21) · E36 = verifier-monitor fault-injection (PRD-22) · E37 = SemMedDB edge-precision gain (PRD-23).
40. **FC collision resolved:** FC-14 = cross-field alignments (PRD-21) · FC-15 = verifier-monitor read (PRD-22) · FC-16 = SemMedDB read (PRD-23). (Specs in PRD-00 §4.)
41. **CCP-21a adopted** — `"cross_field"` added to `kg.DEP_REL_TYPES` (Lane 2 one-liner). CCP-21b (field_id on KG node) deferred.
42. **CCP-22a → Lane 4** — `GET /verifiers` + verifier scorecard on the trust tab (FC-15). Monitor is headless-functional meanwhile.
43. **CCP-23a frozen constraint** — `semmeddb.corroboration` is a convergence-view signal only; MUST NOT increment `independent_source_count`. Lane 2 decides any `calibrate` wiring.
44. **RQ-E35 human dependency** — needs a domain-supplied ~30–60 known cross-field synonymous-mechanism gold set + hard negatives before its gate runs (ledger-only advisory until then).

### Master resolutions — batch 6, 2026-07-13 (post-audit coherence)
45. **Audit findings closed via PRD-00 §8 reconciliation** — §4/§6 declared authoritative over PRD bodies; every stale FC/RQ/gate-flag/oracle-file id mapped to canonical. Implementers use §4/§6/§8, never a stale PRD body. `IMPLEMENTER_START_HERE` updated with the rule.
46. **Two never-fixed source collisions closed:** RQ-E15 dual-use → PRD-04 F4.8 abstention-scoring = **E39** (E15 stays the field-gate); PRD-03 E16/E17 swap → VoI = **E17** (the FC-4 gate), forensics-gates = **E38**. E38/E39 registered in §6.
47. **science.REGISTRY disambiguation:** `"depmap"` = fetch (PRD-07); **`"depmap_oracle"`** = FC-8 verdict (PRD-16 guarded path).
48. **config.py PRD-06 `OPENGWAS_JWT`** additive env read sanctioned (Lane 3, alongside CCP-1).

### Master resolutions — batch 7, 2026-07-13 (PRD-24..27)
49. **FC collision (three-way FC-17) resolved:** FC-17 = prediction ledger (PRD-24) · FC-18 = claims-blocklist (PRD-25) · FC-19 = retraction-watcher (PRD-27). PRD-26 = additive to FC-4/FC-3 (no new FC). Specs in PRD-00 §9.
50. **RQ-E40..E43 confirmed (pre-assignment held — no collision):** E40 prediction-ledger · E41 blocklist · E42 counterfactual (optional) · E43 retraction-watcher.
51. **FC-3 additions:** `kg.claims_for_source` (CCP-26b) + `kg.anchored_beliefs` (PRD-27) — Lane 2 additive reads.
52. **FC-4 addition (CCP-26a):** `engine.counterfactual` (Lane 3); needs PRD-13 to extract `dependency._propagate` as a shared cascade core (coordinated Lane-3 refactor).
53. **CCP-25a blocklist injection:** Lane 3 lands the additive `blocklist.prompt_block()` prepend in audit/paper/review/knowledge; hard-block for published papers behind `rq_e41.passed`.
54. **CCP-24a + CCP-27a → Lane 1 (advisory):** `predict()` at hypothesis-open + a `retraction_watch` scheduler tick; both offline/non-blocking, ship manual/API-enqueueable until Lane 1 lands them.
55. **worker.py registry += `retraction_watch`** (append-only).

### Master resolutions — batch 8, 2026-07-13 (PRD-28..31 — pre-assign held)
56. **FC-20..23 confirmed (zero collision — double pre-assign worked):** FC-20 EIG handoff ranking (PRD-28) · FC-21 frontier map (PRD-29) · FC-22 negative-space (PRD-30) · FC-23 tier-upgrade pathway (PRD-31). Specs in PRD-00 §9.
57. **RQ-E44/E45/E46 registered** (E45/E46 optional/human-gated). E47 unused — PRD-31 ships a property test, not an experiment.
58. **PRD-29 graceful-degrade ratified** — frontier ships `contested`/`frontier_question`/`value_queue` cells now; the `moved` cell lights up when PRD-03 F3.4 `trajectory.py` lands.
59. **CCP-29a + CCP-30a → Lane 1 (advisory, non-blocking):** frontier refresh tick + negspace→`discover.py` hook; ship on-demand until landed.
60. **RQ-E46 human dependency** — negspace needs an expert rater + KG slice (like RQ-E35); held-out-edge proxy in CI meanwhile.

**Process win:** pre-assigning BOTH FC and RQ numbers in the authoring prompt eliminated all cross-lane id collisions this batch — do this for every future PRD batch (next free: FC-24, RQ-E47/E48…).

### Master resolutions — batch 10, 2026-07-13 (PRD-34..35 — pre-assign held)
61. **FC-26 confirmed (zero collision) — cloud-lab wet-lab loop** (PRD-34, Lane 3). New files `ingest/cloudlab.py` + `analysis/wetlab_reconcile.py` + `analysis/wetlab_watch.py` (new-file rule → Lane 3). `wetlab_reconcile` is an **FC-8 verdict oracle** (`science.REGISTRY["wetlab_reconcile"]`, guarded write path) over an *already-ingested* result — NOT a submitter. Spec in PRD-00 §9.
62. **FC-27 confirmed (zero collision) — standing colleague** (PRD-35, Lane 1 provides / Lane 4 renders). New file `persona/subscriptions.py`; shared append-only task type `"front_watch"`. **No CCP required** — consumes only frozen signatures (FC-21/trajectory/FC-19/FC-4/FC-2); the supervisor tick is Lane 1's own file (same-lane additive). Spec in PRD-00 §9.
63. **RQ-E48/E49 confirmed** (pre-assignment held — no collision). E48 = wet-lab loop control-classification + `auto_submit_count==0` (deterministic fixtures, reuses `oracle_controls` for the ≥20-seed guards). E49 = front-moved precision ≥0.85 over ≥20 fault-injection seeds; **gates wake-the-human auto-routing** (`ops_dir/rq_e49.passed`).
64. **CCP-34a → Lane 4 (owns `app.py` dispatch site) + Lane 2 (owns `inbox.py`), non-blocking.** ONE additive `run_action` prefix rule: `"wetlab:<hypothesis>"` → `inbox.file_handoff(kind="wetlab_approval", dossier=cloudlab.draft_protocol(...))`. **HARD CONTRACT: the dispatch site NEVER calls `cloudlab.submit` directly** — submission is reachable only via the human-click `POST /wetlab/{handoff_id}/approve`, and `cloudlab.submit` raises `ApprovalRequiredError` unless the approval handoff is human-resolved. Additive, no FC-4/FC-8 signature change. Until Lane-4 acks, the `"wetlab:"` run_action is inert (renders advisory) — the correct fail-safe for a paid, irreversible action.
65. **Human-gating is a hard invariant, not advisory.** Wet-lab submission is the highest-stakes/cost action in the system (§7 discipline). Wet-lab results type **`TESTED-provisional`** (human anchors the final upgrade) regardless of RQ-E48; the gate governs only whether the loop may run *unattended past the approval click*. In-silico↔wet-lab **divergence is a first-class signal** (`verdict='divergent'` → its own FC-2 handoff), never silently overwritten.
66. **PRD-35 O-1 trigger semantics — default frozen (feeds RQ-E49 label schema, not the M0 stub):** `inflection` fires on any phase change into `{rising,declining,abandoned}` OR newly-True `inflection`; `consensus` only on `rising→plateau` with `independence_drift>0`; `contradiction` only on a new `(subject,object)` pair with `both_independent` (≥2/≥2, the RQ-E02 well-powered threshold); `retraction` **mirrors** FC-19's already-filed hit into the subscriber's feed — it does NOT re-file (FC-19/PRD-27 owns the retraction escalation). RQ-E49 tunes the exact transition set to clear precision ≥0.85. First-pass-silent (empty seed snapshot) prevents a "everything just moved!" burst on subscribe.
67. **worker.py registry += `front_watch`, `wetlab_submit`** (append-only, delimited blocks). Advisory scheduler ticks (`front_watch`, `wetlab_watch`) → Lane 1, offline/$0, no budget gate, mirroring the ratified CCP-27a retraction tick.

**Program state after batch 10: 35 PRDs · FC-1..27 · RQ to E49 · 67 master resolutions.** Next free: **FC-28, RQ-E50**. Binding constraint remains implementation (no lane has posted CLAIMED) — PRD authoring is paced; the master pulls from the ideation backlog as lanes engage.

### Master resolutions — batch 11, 2026-07-13 (PRD-36..37 — pre-assign held, zero collision)
68. **FC-28 confirmed — contradiction-independence pre-check** (PRD-36, Lane 2). `kg.shared_origin(a,b)` (additive to FC-3 independence-by-lab, reuses `Source.lab`/`lab_of`) + additive `include_suppressed` kwarg on `kg.candidate_conflicts`. **Strict all-cross-pairs rule: a shared-origin false tension requires `independent_pairs==0 and total_pairs>0`; any independent pair ⇒ the contradiction stands.** Suppression at the human-queue layer ONLY — the structural `CONTRADICTS` edge is preserved (trajectory/`poisoning_signals` unaffected). Spec in PRD-00 §9.
69. **PRD-37 = additive to FC-4 code-run auditor — NO new FC** (Lane 3). `forensics.gail_simon(...)` matches the statcheck/`p_curve` envelope; ONE additive branch in `_run_all_raw`; between-subgroup interaction test + Gail-Simon qualitative test (closed-form deterministic). Rides the auditor's existing generic flag render — no new route/tab. RQ-E51 (deterministic numeric repro, no ≥20-seed).
70. **RQ-E50/E51 confirmed** (pre-assignment held — no collision). E50 = shared-origin false-tension precision ≥0.85 + genuine-recall loss ≤0.05, **needs a human/synthetic independence-labeled pair set (like RQ-E02)** — advisory-only until `ops_dir/rq_e50.passed`. E51 = Gail-Simon numeric match (Gail & Simon 1985) + correct off-domain abstention.
71. **CCP-36a ratified (PRD-36 O-1):** additive `gate` enum `+= 'independence'` on the shared FC-8 `gate_decisions.jsonl` (the auditable suppression row). Backward-compatible; mirrors CCP-09-A `'redteam'` (resolution 21). No shape change. Enum now: `relevance | drift | membrane | redteam | independence`.
72. **Cross-cutting ownership ruling (PRD-36 O-5, applies to ALL lanes):** a feature's RQ sandbox `experiments/exp_*.py` + its unit test are authored/owned by the **providing lane** (precedent PRD-05/06/10/12); Lane 4's §3 `experiments/*`/`tests/*` ownership governs the cross-cutting **eval harness (`eval/*`), browser smokes, and shared test infra** only. Lane 2 authors `exp_contradiction_independence.py`; Lane 3 authors `exp_gail_simon.py`.
73. **PRD-36 O-2/O-4 → defaults accepted:** `same_dataset` basis deferred (no `dataset` field on `Source` yet — add when a dataset id exists); `preprint_published_pair` detected via exact title-identity for v1. `shared_origin` is an orthogonal FLAG, NOT a 5th FC-2 `CONFLICT_TYPES` entry (that enum stays frozen).
74. **PRD-37 OQ-1..4 → defaults accepted:** RQ-E51 fixture = Gail & Simon 1985 NSABP subgroups (critical-value-table + `k=2` identity legs pass without it); bootstrap magnitude-CI deferred (v1 deterministic-only); Lane-4 render = the generic auditor flag (no FC, no new surface); severity map = spurious-subgroup→`weak`/sev 2, direction-contradiction→`inconsistent`/sev 3.

**Program state after batch 11: 37 PRDs · FC-1..28 · RQ to E51 · 74 master resolutions.** Next free: **FC-29, RQ-E52**. Binding constraint remains implementation (no lane has posted CLAIMED).

### Master resolutions — batch 12, 2026-07-13 (PRD-38..39 — pre-assign held; FC-30 returned to pool)
75. **FC-29 confirmed — meta-research self-study** (PRD-38, Lane 3 provides `analysis/self_study.py`, Lane 4 renders `GET /self_study`). Read-only aggregation over the prediction ledger + verified/revisit history + calibration; **never mutates a belief**. Consumes FC-17/18/15/3 import-guarded (specced-not-built → degrades per-signal). Spec in PRD-00 §9.
76. **PRD-39 = additive to the FC-4 auditor/checker — NO new FC** (Lane 3). `synthesis.check_faithfulness(...)` matches the `forensics.py`/`checker.py` flag envelope; dual-signal (LLM boolean-gate + deterministic structural confirm — no fabricated score); rides `audit.py`'s existing generic flag render. Consumes FC-10 import-guarded. Verifies prose ⊆ the graph's sign/strength/certainty — orthogonal to the citation checker (prose ⊆ quotes).
77. **FC-30 RESERVED-THEN-RETURNED.** PRD-39 was pre-assigned FC-30 but left it unused (Lane-3-internal, YAGNI — no lane outside Lane 3 calls the check). **FC-30 goes back in the pool → next free FC = FC-30.** A dedicated Lane-4 faithfulness surface would claim it later (PRD-39 OQ-3 = do-not-mint).
78. **RQ-E52/E53 confirmed** (pre-assign held). E52 = self-study trend validity: false-improvement ≤0.05 AND reversal-recall ==1.0, ≥20 seeds. E53 = faithfulness detection precision ≥0.80 + false-flag CI ≤0.05, ≥20 seeds, **gate on the deterministic offline detector** (PRD-39 OQ-1).
79. **PRD-38 OQ-4 — component-value stays OBSERVATIONAL in v1.** "Which component paid off" echoes existing gate/experiment outcome labels with an explicit **"not causal"** label; a causal-attribution contract is **deferred, NOT minted** (would need its own PRD + RQ). No FC minted for it now.
80. **PRD-38 OQ-2/OQ-3 → defaults:** `_MIN_TREND_N` default **10** (RQ-E52 sweep may adjust, register in `docs/RESEARCH_QUALITY_PROGRAM.md`); the confident-wrong reversal cut **imports `calibrate._P_COMMIT`** (Lane-2 single-source-of-truth, additive read) rather than hard-coding 0.7.
81. **PRD-39 OQ-4 → defer:** run faithfulness on generation surfaces (synthesizer/review/paper) for v1; running it over `audit.py` adjudication rationale is a follow-on.
82. **RQ-E52/E53 registration** in `docs/RESEARCH_QUALITY_PROGRAM.md` is an implementer task at first-fill (PRD-38 OQ-1) — same as every prior RQ.

**Program state after batch 12: 39 PRDs · FC-1..29 (FC-30 free) · RQ to E53 · 82 master resolutions.** Next free: **FC-30, RQ-E54**. Binding constraint remains implementation (no lane has posted CLAIMED).

### Master resolutions — batch 13, 2026-07-13 (PRD-40..41 — pre-assign held, zero collision)
83. **FC-30 confirmed — dead-end/rabbit-hole detector** (PRD-40, Lane 1, new `research/convergence.py`). `convergence_health(...)` = pure read over real spend × membrane/ledger yield; **never mutates**. `dead_end` requires rising spend AND a sustained zero-yield tail — a slow-but-still-landing dive never cuts. Advisory reprioritize/pause + resumable hold; high-stakes→human-confirm. Spec PRD-00 §9.
84. **FC-31 confirmed — mechanistic-model novel-prediction generator** (PRD-41, Lane 3, new `analysis/mechanism.py` re-exported via `engine.py`). Composes signed causal edges into IMPLIED predictions; **INFERRED-only, no membrane write, mutates nothing**; composed sign only where fully licensed (else `ambiguous`/`unknown`). **Differentiated from FC-22 negspace** (directed signed-path composition vs undirected Adamic-Adar). Spec PRD-00 §9.
85. **RQ-E54/E55 confirmed** (pre-assign held). E54 = dead-end precision ≥0.80 + false-cut-on-slow ≤0.05, ≥20 seeds; gates the autonomous cut (`ops_dir/rq_e54.passed`). E55 = implied-edge held-out recovery beats random+Adamic-Adar; advisory regardless.
86. **CCP-40a ratified → Lane 4:** FC-30 render / dead-end badge (headless-functional meanwhile). **CCP-41a ratified → Lane 1:** advisory `discover.py` hook for implied predictions (mirrors CCP-30a, non-blocking).
87. **PRD-40 OQs → defaults:** validated-yield attribution (thread `investigation_id` through Lane-2 writes) DEFERRED — time-windowed join ships v1; "round" = cost-bearing step; soft `reprioritize` = driver-side slot-yielding (no queue priority-mutation contract).
88. **Intra-Lane-1 coordinated edits:** PRD-40's `supervisor.py`/`queue.py`/`investigation.py` additions land after / coordinated with PRD-01 (single Lane-1 owner, no parallel rewrite).
89. **PRD-41 OQ → non-blocking:** RQ-E55 full graph slice + expert plausibility overlay = domain input; a held-out-edge proxy runs in CI meanwhile (RQ-E46 precedent).

**Program state after batch 13: 41 PRDs · FC-1..31 · RQ to E55 · 89 master resolutions.** Next free: **FC-32, RQ-E56**. Binding constraint remains implementation (no lane has posted CLAIMED). Loop cadence now 5-min (`64340d74`).

### Acceptance gate (per feature)
A feature is `VERIFIED` only with a measurable acceptance criterion met **and** one runnable check (a `pytest` name or CLI assertion) passing; Lane-4 surfaces additionally pass a `PERSONA_WORKERS=0` browser smoke. No feature is done on prose.

### Public beta baseline repair — 2026-07-13

**Goal:** keep the evidence-first core releaseable while public auth/BYOK remains a separate security-critical implementation track.

**Frozen contract:** repair live FalkorDB claim writes; remove Field's executable interpolation of claim IDs; set the normal worker default to 3 (production still sets 0); align package metadata and CLI version. Do not expose the existing unauthenticated API publicly or alter tenant/auth architecture.

**Evidence:** `python -m pytest -q tests/test_data_kg_invariants.py tests/test_data_fc3_kg.py tests/test_membrane_poisoning.py tests/test_multipersona_isolation.py tests/test_paper_graph.py` -> 13 passed; `node tests/test_fe_field.cjs` -> 28 assertions; `python -m compileall -q persona experiments` and `git diff --check` -> pass.

**Verdict:** baseline blockers repaired. Public deployment remains blocked on authenticated tenancy, encrypted BYOK provider boundary, and HTTPS/compose/backup acceptance gates.

**Worker policy update:** capped runs retain the evidence-backed default of 3 workers. `PERSONA_UNLIMITED_SPEND=1` explicitly selects an uncapped run with an implicit default of 8 workers; `PERSONA_WORKERS` and a finite `PERSONA_DAILY_BUDGET_USD` override that mode. Verified by `tests/test_config_workers.py`.

**Hackathon demo:** `docs/HACKATHON_DEMO.md` is the deterministic three-minute, read-only sequence. Run with `PERSONA_WORKERS=0` and `PERSONA_START_SCHEDULER=0`; it only presents cached Curie evidence, its replayable GEO session, and the human-gated conflict dossier.

**Deployment bundle:** added `Dockerfile`, `docker-compose.yml`, `Caddyfile`, `.env.production.example`, `scripts/backup.sh`, `scripts/restore.sh`, and `docs/DEPLOYMENT.md`. Compose exposes only Caddy, keeps scheduler/workers disabled, and persists FalkorDB/Postgres/workspace/Caddy data. `bash -n scripts/backup.sh scripts/restore.sh` passes; real Compose/TLS/restore gates require the VPS and production secrets.

**Public boundary (2026-07-13):** Google OIDC sessions, HTTP-only signed cookies, CSRF on unsafe requests, and central tenant middleware now protect all persona routes. Persona ownership persists in the registry; public lists filter by owner and cross-tenant IDs return 404. Provider settings are tenant-scoped Fernet ciphertext with add/rotate/revoke audit records; all Anthropic call sites route through the tenant-aware `providers.anthropic_client()` factory. Evidence: `tests/test_public_tenant_boundary.py`, `tests/test_provider_settings.py`, full suite 347 passed, UI smoke with scheduler/workers disabled passed, and Compose config validates against the production template.

**Image gate:** `docker build -t persona:0.3.0 .` passed; image digest `sha256:35aaf3172d361f2780217a9bcb3921bae0d312dee44768fed779faa6f2682f4e`. The web health check now uses `/readyz` (live FalkorDB probe), not the UI route.

**Provider adapter:** `providers.openai_compatible_chat` provides explicit OpenAI/Hugging Face chat-completion calls with normalized/redacted failures and no implicit provider or model fallback. `tests/test_openai_compatible_provider.py` passes on the pinned endpoint contract.

**Submission audit (local):** full Python suite now `349 passed`; Focus/Field/Verdict renderer checks passed (38/29/18); compile, diff, Compose-template validation, and backup-script syntax passed. The remaining verification is live-only: public DNS/TLS, OAuth callback, provider-key round trips, and backup restore rehearsal on the VPS.

**Public UI hardening:** the shell fetch wrapper obtains `/api/auth/session` and attaches the synchronizer token to unsafe API requests; logout now verifies CSRF explicitly. Public users are limited to one workspace and a $5 default daily cap, while an in-memory per-user API rate window rejects bursts. Covered by `test_fe_public_csrf.cjs`, `test_public_tenant_boundary.py`, and `test_public_rate_limit.py`.

**Independent review API:** authenticated tenants can mint opaque reviewer tokens, serve frozen blinded assignments, append one non-mutating label with duplicate refusal, and verify the label hash chain through `/api/persona/{pid}/reviews/*`. Existing multi-rater/tamper tests remain green (14 targeted tests).

**Final local build:** complete local audit is `350 passed` plus all four JS checks. A cache-disabled image rebuild passed after Docker Desktop failed once during cached-layer export; final image is `persona:0.3.0` digest `sha256:34a082d3aa95629f3236247e167bbcb34164259d3b9c161a3a921dd09a47bd1a`.

### Public-beta release audit â€” final local evidence, 2026-07-13

**Packaging repair:** Compose smoke caught the installed wheel missing `persona/api/static`; `pyproject.toml` now declares `api/static/**/*` package data and Compose explicitly deploys the release image `persona:0.3.0`, preventing the Compose-local image tag from drifting from the inspected artifact.

**Production-service smoke:** a disposable Compose run brought FalkorDB, PostgreSQL, and web to `healthy`; `/readyz` returned 200. Inside the web container, an encrypted OpenAI provider credential was saved, decrypted for server-only use, revoked, and the PostgreSQL audit ledger recorded both actions. Stack was stopped without deleting its volumes.

**Final local verdict:** `350 passed`; Focus/Field/Verdict/CSRF JS checks passed (38/29/18 plus CSRF); compilation, Compose-template validation, backup/restore shell syntax, and diff check passed. Worker-disabled browser smoke passed with `cards=6`, GEO replay and conflict dossier both `passed`. Release image: `persona:0.3.0`, digest `sha256:882288720a2eaca07a91392d52389c63d9eac8fbb2edc7a20ebbdc4c27966be0`.

**Remaining external launch gates:** actual VPS/DNS/Caddy certificate issuance, Google OAuth callback, real BYOK provider round trips, and an off-host backup/restore rehearsal require the domain, VPS, and credentials. Do not represent those as completed before performing them.

**Hackathon narration:** `docs/HACKATHON_DEMO.md` now uses the full three minutes to state the problem, show legible memory and the value queue, prove the replayable GEO loop and conflict dossier, then close on the human boundary and acting-loop novelty. A DNS A/AAAA lookup for `persona.aryansingh.org` returned no records in this environment; public HTTPS remains an external gate, not a completed claim.

### Ideation backlog (grows continuously — never flatline)
The ideation agent maintains `docs/prd/IDEAS_BACKLOG.md`: a ranked, always-growing queue of next features/experiments beyond Lanes 1–4, refreshed against new literature. The master pulls from it as lanes free up.
