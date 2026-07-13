# Persona ideas backlog — the never-flatline queue

> **Owner:** ideation agent. **Purpose:** a ranked, always-growing queue of features/experiments *beyond* Lanes 1–4 (`PRD-01…04`). The master pulls from the top as lanes free up. Each iteration of the ideation loop appends new ideas (dated), re-ranks, and prunes shipped/dead ones. Every idea still obeys the epistemic discipline in `PRD-00 §2`.
>
> **Columns:** `#` rank · **idea** · *why it advances the vision* · **evidence** (map/research/BUILD_PLAN) · **lane** it would extend · **effort** S/M/L · **leverage** H/M/L.

## Promoted to PRDs (traceability — don't re-promote)

| Backlog # | Idea | PRD | Status |
|---|---|---|---|
| lanes 1–4 base | core theme features | PRD-01..04 | READY-TO-CLAIM |
| #1 | Second researcher / a lab | PRD-05 | READY-TO-CLAIM |
| Wave 3b | Executable Mendelian-randomization | PRD-06 | READY-TO-CLAIM |
| Wave 3b | DepMap knockout oracle | PRD-07 | READY-TO-CLAIM |
| Wave 3b | Molecular prior gates (gnomAD/GTEx/OT-Genetics) | PRD-08 | READY-TO-CLAIM |
| #3 | Red-team-the-belief agent | PRD-09 | READY-TO-CLAIM |
| #19+#22 | Meta-analysis agent + effect-size harmonizer | PRD-10 | READY-TO-CLAIM |
| #2 | Multi-rater contradiction gold UI | PRD-11 | READY-TO-CLAIM |
| #20 | Causal-strength typing gate | PRD-12 | READY-TO-CLAIM |
| #26 | Fragility "what-if" simulator | PRD-13 | READY-TO-CLAIM |
| #7 | Sleep-consolidation pass | PRD-14 | READY-TO-CLAIM |
| #16 | Self-calibration reliability panel | PRD-15 | READY-TO-CLAIM |
| #90 | Oracle positive/negative control-injection | PRD-16 | READY-TO-CLAIM |
| Wave 3c | FDA surrogate-endpoint / biomarker gate | PRD-17 | READY-TO-CLAIM |
| Wave 3c | OHDSI LEGEND calibrated-RWE probe | PRD-18 | READY-TO-CLAIM |
| #24 | Null-hunt swarm mode | PRD-19 | READY-TO-CLAIM |
| #91 | Belief confidence-budget / evidence accounting | PRD-20 | READY-TO-CLAIM |
| #4 | Cross-field mechanism translation | PRD-21 | READY-TO-CLAIM |
| #6 | Verifier-calibration monitor | PRD-22 | READY-TO-CLAIM |
| #8 | SemMedDB integration | PRD-23 | READY-TO-CLAIM |
| #17 | Prediction ledger + Brier self-score | PRD-24 | READY-TO-CLAIM |
| #9 | Claims-must-not-make blocklist | PRD-25 | READY-TO-CLAIM |
| #100 | Counterfactual literature simulation | PRD-26 | READY-TO-CLAIM |
| #33 | Live retraction watcher | PRD-27 | READY-TO-CLAIM |
| #99 | Expected-info-gain question ranking | PRD-28 | READY-TO-CLAIM |
| #114 | Research-frontier map artifact | PRD-29 | READY-TO-CLAIM |
| #115 | Negative-space hypothesis generation | PRD-30 | READY-TO-CLAIM |
| #125 | Evidence-tier upgrade pathway | PRD-31 | READY-TO-CLAIM |
| #5 | Pareto swarm-sizing controller | PRD-32 | READY-TO-CLAIM |
| #98 | Reviewer confidence report card | PRD-33 | READY-TO-CLAIM |
| #507 | Cloud-lab wet-lab loop | PRD-34 | READY-TO-CLAIM |
| #500 | Standing colleague (capstone) | PRD-35 | READY-TO-CLAIM |
| #37 | Contradiction independence pre-check | PRD-36 | READY-TO-CLAIM |
| #71 | Gail-Simon effect-modification forensic | PRD-37 | READY-TO-CLAIM |
| #118 | Meta-research self-study | PRD-38 | READY-TO-CLAIM |
| #134 | Explanation-faithfulness check | PRD-39 | READY-TO-CLAIM |
| #136 | Dead-end / rabbit-hole detector | PRD-40 | READY-TO-CLAIM |
| #519 | Mechanistic-model → novel-prediction generator | PRD-41 | READY-TO-CLAIM |
| #520 | Prospective forecasting mode | PRD-42 | READY-TO-CLAIM |
| #526 | Whole-graph self-consistency sweep | PRD-43 | READY-TO-CLAIM |

### Next up for PRD promotion (ripe, un-promoted — refreshed iter 160)
**Next batch (pre-assign FC-30/RQ-E54+ to keep the zero-collision streak):** #136 dead-end/rabbit-hole detector (L1) · #519 mechanistic-model→novel-prediction generator (L3) · #520 prospective forecasting (L1+4). Ripe behind them: #526 whole-graph self-consistency sweep (L2) · #128 interest-graph visualization (L4) · #103 standing chaos/poisoning audit (L2+4) · #513 poison-attribution forensics (L2) · #516 effort-calibration self-score (L1+4) · #522 experiment-portfolio optimizer (L3+1) · #528 competitive scoreboard (L4). _(promoted so far → PRD-01..39; see the traceability table above.)_ **Pacing note:** 39 PRDs written, 0 CLAIMED — implementation is the binding constraint; new PRD authoring is deliberately paced. Master launches the next batch when a lane engages or on user steer.

## Wave 2 — ranked (pull top-down)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 1 | **A second researcher (a lab)** — spawn a persona with a *different disposition* that reads the same field and challenges the first; cross-persona disagreement becomes a first-class signal + dataset | The BUILD_PLAN's biggest vision beat; `PersonaManager` already isolates multiple personas + graphs, so the substrate exists | BUILD_PLAN §7.1; `manager.py` multi-persona | 1+2 | L | H |
| 2 | **Multi-rater contradiction gold UI (unblock RQ-E02)** — reviewer/assignment/blinding metadata, duplicate-review prevention, cross-process lock on the existing hash-chained ledger, then collect a blinded 20-case gold set | Gates *all* autonomous contradiction escalation; the single most-cited open item in the continuation contract | CONTINUATION_HANDOFF §11; docs map | 2+4 | M | H |
| 3 | **Red-team-the-belief agent** — before a belief is celebrated/anchored, a dedicated agent tries to *falsify* it (hunt disconfirming spans, propose the killing experiment) | Directly encodes CLAUDE.md's "try to falsify it before you celebrate it"; complements the verifier | CLAUDE.md §3; research: adversarial verify | 1 | M | H |
| 4 | **Cross-field mechanism translation** — align the same mechanism named differently across subfields (surface evidence a domain researcher would never find) | Unique differentiator; concrete checkable wins on shared datasets | BUILD_PLAN §3.6 | 3 | M | M |
| 5 | **Pareto swarm-sizing controller** — size team/rounds per task on the measured accuracy-vs-cost frontier; surface "readers spawned vs beliefs earned vs $" | Turns "breadth of teamwork" into a *disciplined* knob, not a fixed number | research: SC-MAS / Pareto MAS (arXiv:2605.01566) | 1+4 | M | M |
| 6 | **Verifier-calibration monitor** — track whether the verifier agent rubber-stamps; route expensive verification only where it pays off | Guards against false assurance from a weak verifier | research: "When Does Verification Pay Off" (arXiv:2512.02304) | 1 | S | M |
| 7 | **Sleep-consolidation surface** — a nightly ReMem-Refine pass (merge duplicate beliefs, prune stale READ candidates, abstract recurring evidence) with a visible consolidation log | Cheaper than re-reading; directly legible | research: ReMem/Evo-Memory (arXiv:2511.20857), Learning to Forget (arXiv:2603.14517) | 2 | M | M |
| 8 | **SemMedDB integration** — structured semantic predications to *seed* dependency edges (the one BUILD_PLAN source still unwired) | Bootstraps the dependency graph with curated relations | ingest map (SemMedDB missing); BUILD_PLAN §4.4 | 3 | M | M |
| 9 | **"Claims the next agent must not make" blocklist** — machine-readable guardrail from FINDINGS.md reversals, consumed by any report/LLM-judge prompt | Stops silent reintroduction of debunked claims across sessions | docs map; FINDINGS.md reversals | 2+4 | S | M |
| 10 | **Belief-graph writeback from deliverables** — mark claims `cited_in_deliverable` when a review/paper uses them, so the graph shows which beliefs made it into real artifacts | Closes the one-way export gap; feeds VoI (unused-but-load-bearing) | synthesis map; `paper.py:_fix_references` | 3 | M | M |
| 11 | **Cross-ledger integrity check** — one `verify_all()` over sessions + conflict_reviews + verified ledger for a single CI/reviewer pass | Makes the whole provenance stack checkable in one command | sessions map | 4 | S | M |
| 12 | **Challenge-horizon / sleeping-beauty detector** — flag load-bearing claims still inside the ~2yr window where challenges cluster, and delayed-recognition curves | Prioritizes what to test before the field does | research: ClaimFlow (~11% challenged, ~2yr) | 3 | M | M |
| 13 | **Provenance-normalized envelope for `science.py` tools** — give Open Targets/ClinicalTrials/UniProt hits the same `Work`-style provenance the membrane already types | Lets structured-DB evidence flow through provenance typing cleanly | ingest map | 3 | S | M |
| 14 | **Reproduction capsule (one-click)** — package a closed-loop session as an RO-Crate + pinned Docker for external replay | FAIR-citable, reviewer-friendly; extends Lane 4's RO-Crate work | research: Workflow-Run RO-Crate (arXiv:2312.07852) | 4 | M | M |
| 15 | **"Always-on colleague" alerts** — subscribe to a target/question; ping the human the day the front moves (new contradiction, trajectory inflection, retraction) | The standing-collaborator framing; monetizable hook | BUILD_PLAN §7.3 | 4 | M | M |

## Wave 2b — 2026-07-12 iteration 2 (fresh)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 16 | **Self-calibration reliability panel** — once the auditor/membrane accrue ground-truth outcomes, plot predicted-vs-observed replication/verification rates (reliability curve + ECE) over Persona's *own* past verdicts | Makes "no fabricated confidence" measurable and visible — the honesty story becomes a number that trends | calibration research; AstaBench honesty axis | 4 | M | H |
| 17 | **Prediction ledger + Brier self-score** — for each open contradiction/hypothesis, record Persona's prior probability and update it as tests/evidence land; score its own calibration over time (Brier) | Operationalizes taste/surprise *and* gives a self-accountability metric a PI can trust; a synthetic researcher that keeps score | BUILD_PLAN §3.4 falsification market + calibration | 2+4 | M | H |
| 18 | **Evidence-tree diff over time** — when a belief's evidence tree changes (new support/contra, a retraction, a reanalysis), emit a visual "what changed and why confidence moved" diff | Extends the idea-over-time work down to the evidence level; the auditability money-shot | SCIENTIFIC_WORKBENCH_SPEC evidence tree; citation-grounding temporality | 2+4 | M | M |

## Wave 3a — 2026-07-12 iter 3 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 19 | **Meta-analysis agent** — when ≥3 independent studies report the same effect with extractable stats, run a real random-effects meta-analysis in code (pooled effect, I² heterogeneity, forest plot) | A genuine synthesis primitive beyond narrative review; pools evidence the way a human systematic-reviewer would | forensics.py extends naturally; standard DerSimonian–Laird | 3 | M | H |
| 20 | **Causal-strength typing gate** — classify each claim's causal warrant (observational / RCT / Mendelian-randomization / mechanistic) and forbid surfacing an observational claim with causal language | Directly encodes the GEO/microglia caution ("association ≠ causation") as a hard gate | CONTINUATION_HANDOFF §6 (transcriptomic ≠ causal); causal-inference lit | 2 | M | H |
| 21 | **Corpus-level p-curve / z-curve** — run evidential-value analysis across a *set* of a target's studies, not one paper, to estimate the whole literature's replicability | The per-paper p-curve already exists; the corpus view is where p-hacking actually shows | forensics.py p_curve; z-curve 2.0 (Bartoš & Schimmack) | 3 | M | M |
| 22 | **Effect-size harmonizer** — normalize reported effects (OR/HR/Cohen's d/r) into a common metric + store raw+harmonized so cross-study comparison and meta-analysis are possible | Prerequisite for #19 and citation-vs-support comparison across heterogeneous designs | escard/metafor conversions | 3 | S | M |
| 23 | **Preregistration awareness** — tag findings from preregistered/registered-report studies with a higher trust prior vs exploratory; ingest OSF/AsPredicted signals | Preregistration is one of the strongest replication predictors; feeds calibration priors | Registered Reports replication rate literature | 3 | M | M |
| 24 | **Null-hunt swarm mode** — a dedicated reading mode that actively hunts nulls in preprints, terminated trials, and supplementary tables for an abandoned target | Turns the "silence detector" from passive flag into active swarm behavior; surfaces the file-drawer | BUILD_PLAN §3.5; Dead Science Walking | 1+3 | M | H |
| 25 | **Cost-of-being-wrong weighting** — weight VoI by downstream decision stakes (a load-bearer under a drug program > an academic curiosity) | Makes the value queue care about *consequences*, not just graph mass | BUILD_PLAN §3.4; extends value_queue | 3 | S | M |
| 26 | **"What if this fell" fragility simulator** — user perturbs a node's truth in the dependency graph and watches the fragility cascade recompute live | The most visceral demo of the load-bearing thesis; interactive legibility | BUILD_PLAN §3.3; flagship-adjacent | 4 | M | H |
| 27 | **Reviewer-disposition lens** — human picks skeptic / optimist / methodologist and the auditor re-weights adjudication, showing how conclusions shift with stance | Makes disposition *functional* and visible; a novel legibility beat | BUILD_PLAN §0.3 (functional taste); audit.py adjudicator | 3+4 | M | M |
| 28 | **Claim provenance passport** — one-click export of a belief's full lineage (every span, reasoning step, test, human decision) as a shareable verifiable doc | The auditability money-shot as a portable artifact; reviewer-friendly | SCIENTIFIC_WORKBENCH_SPEC evidence tree; RO-Crate | 4 | S | M |
| 29 | **Live literature-front tracker** — a compact "state of the front" per interest that updates as papers land (settled/contested/moving + velocity derivative) | Argument-state (3.1) surfaced *continuously*, not on demand — the "always-on colleague" made concrete | BUILD_PLAN §3.1; trajectory.py | 3+4 | M | M |
| 30 | **Self-audit (dogfood the auditor)** — periodically run the robustness auditor on Persona's *own* generated reports/papers, surfacing self-consistency + calibration | A synthetic scientist that audits itself is the credibility signal; catches its own slop | audit.py on deliverables/; error-log ethos | 3 | S | H |
| 31 | **Typed premise→inference evidence chains** — build explicit multi-hop premise/inference edges so a synthesis's logical structure is inspectable and each hop independently checkable | The RQ-E06 evidence-tree target; reduces unsupported synthesis | RESEARCH_QUALITY_PROGRAM RQ-E06; SCIENTIFIC_WORKBENCH_SPEC | 2+3 | L | H |
| 32 | **Budget efficiency optimizer** — learn (from the frozen-evaluator harness) which task types yield validated beliefs per dollar and reallocate the daily budget; surface the frontier | Turns cost discipline into a learned, legible knob; complements Pareto swarm-sizing (#5) | RQ-E10 frozen-evaluator harness; budget.py | 1+4 | M | M |

## Wave 3a-cont — 2026-07-12 iter 4 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 33 | **Live retraction watcher on own beliefs** — subscribe every source backing an anchored belief to Retraction Watch; auto-file a handoff the day a supporting paper is retracted | Turns contamination (FC-6) from a one-time scan into a standing guard on the self's core | FC-6; 47.7% post-retraction citations | 2+3 | M | H |
| 34 | **Funding/COI signal** — extract funding source + author conflict-of-interest and surface as a trust *modifier* (never a verdict) on the auditor | A known replication moderator the auditor ignores today; honest, not accusatory | audit.py adjudicator; industry-funding bias lit | 3 | M | M |
| 35 | **Unit/dimensional-consistency check** — deterministic code check that a claim's reported quantities have consistent units/dimensions (catches order-of-magnitude errors) | Another exact, code-run forensic with a clean applicability gate | forensics.py pattern; pint | 3 | S | M |
| 36 | **Adjustable base-rate panel** — show the field base-rate prior the auditor used and let the human tune it, re-running the calibrated likelihood live | Makes the calibration assumption transparent + interactive (honest uncertainty) | audit.py `_field_base`/`_BASE` | 3+4 | S | M |
| 37 | **Contradiction independence pre-check** — before flagging a contradiction, verify the two sides don't trace to the same primary source/lab (avoids false contradictions from shared origin) | Prevents a whole class of spurious tensions; reuses independence-by-lab | kg independence-by-lab; membrane | 2 | M | H |
| 38 | **"Explain this number" drill-down** — click any number in a report and trace it to the exact computation/artifact/source that produced it | Numbers become auditable links — the legibility thesis at the finest grain | sessions artifacts; provenance API | 4 | M | H |
| 39 | **Adaptive reading depth** — scale a paper's read depth (abstract → full-text → figures/tables) by its relevance + surprise, saving budget on marginal papers | More validated belief per dollar; complements surprise queue | reader.py fulltext; budget split | 1 | S | M |
| 40 | **Concept-drift detector for entities** — flag when an entity's meaning/definition shifts over time (gene reannotated, term redefined), which silently corrupts claim identity | Protects the (subject,object,sign) claim-identity assumption the whole KG rests on | kg claim identity; canon.py | 2 | M | H |
| 41 | **Self-preregistration primitive** — before any self-test, Persona writes a preregistration (hypothesis/analysis/gate) into the session and can't move goalposts | Dogfoods the rigor it audits in others; E12b did this by hand — make it a primitive | RQ-E12b prereg; analyst.py | 1+3 | S | H |
| 42 | **Devil's-advocate section in every deliverable** — auto-append a "strongest case against" generated by an adversarial pass to each review/paper | A synthetic scientist that argues against itself is more trustworthy; catches its own slop | critic.py; red-team ethos | 3 | S | M |
| 43 | **Evidence-staleness heat on the graph** — color belief nodes by how recently they were re-supported so "old, un-revisited" beliefs are visible at a glance | Surfaces the staleness signal (#2.9) spatially; cheap once history exists | history.series; graph UI | 4 | S | M |
| 44 | **Cross-persona belief reconciliation** — when two personas ("the lab") hold conflicting beliefs, generate a reconciliation dossier comparing evidence + typing the disagreement | The multi-researcher vision made productive — disagreement becomes a structured artifact | BUILD_PLAN §7.1; extends backlog #1 | 2+4 | M | H |

## Wave 3b — 2026-07-12 (8-lens sweep)

_Several standout sweep ideas — executable Mendelian-randomization, DepMap knockout oracle, gnomAD/GTEx/OT-Genetics molecular gates, red-team agent, and meta-analysis agent — are already being promoted to PRD-05..10, so they are omitted here._

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 45 | **Translator agent (Solver→Verifier bridge)** — insert a Translator that rewrites free-text conclusions into the smallest checkable statistical statement the cheap Verifier can re-run | Turns silent `not_applicable` skips into real adjudications; raises validated-output-per-cost and legibility | Decoupled Prover-Verifier Games (arXiv:2602.23248); PVG legibility (arXiv:2407.13692); PRD-01 F1.2 | 1 | M | H |
| 46 | **Difficulty-adaptive escalation cascade** — per-claim ladder (single read→two-reader→verifier→debate) that early-exits at the first rung resolving above a confidence threshold | Spends scrutiny proportional to claim difficulty; escalate-only-the-hard-ones cuts 40-85% of spend at equal accuracy | AgentCodec (arXiv:2605.09121); Budget-Aware Routing (arXiv:2602.21227); composes PRD-01 F1.2/1.3/1.4/1.6 | 1 | M | H |
| 47 | **Standing-questions watchlist** — `self/standing_questions.json` of blocked questions with trigger signatures; the inner loop auto-wakes a parked investigation when the missing data/paper lands | Genuine long-horizon persistence — holds open problems across days and resurrects them exactly when the world changes | BUILD_PLAN §2.4/§2.1/§9.2; Deep Ideation open-ended memory (arXiv:2511.02238) | 1 | M | H |
| 48 | **Adversarial-collaboration settlement** — two dispositional personas jointly author ONE executable test on public data and both pre-commit to the accepted result before it runs; loser's belief auto-updates | Adversarial collaboration is the gold standard humans won't pre-commit to; synthetic researchers can be forced to | AgentRxiv 2025; StatefulDiscovery (arXiv:2606.11851); extends #1, debate.py, FC-1 | 1 | M | H |
| 49 | **Conformal linguistic hedging tier** — a third membrane route: borderline beliefs emit in a conformally-controlled hedged form ('preliminary evidence suggests') instead of hard-abstaining | Say LESS with a guarantee rather than say nothing; recovers useful recall at the same certified error rate | Conformal Linguistic Calibration (arXiv:2604.27914; 2402.10978); PRD-02 F2.3 | 2 | M | H |
| 50 | **Field-level conformal risk control** — separate certified error budgets per schema field (subject/sign/object); admit a claim's entity while abstaining on its error-prone SIGN | Whole-output conformal control is sometimes provably impossible; per-field is achievable and unlocks partial admission | Conformal Risk Control for structured generation (arXiv:2606.29054); refines PRD-02 F2.3/F2.6 | 2 | M | H |
| 51 | **Confirmation-debt tracker → disconfirmation mission** — log confirm/disconfirm span ratio per belief; when a load-bearing belief is fed only corroboration, auto-spawn a reader budgeted to find contra | Persona resists external poisoning but does nothing to counter its OWN one-sided intake; a when-to-doubt trigger | 'Honest Lying' confabulation (arXiv:2605.29463); agent-memory survey (arXiv:2603.07670); BUILD_PLAN §3.2 | 2 | M | H |
| 52 | **Falsification contracts + tripwire watcher** — each load-bearing belief pre-commits in code the exact future observation that would flip it; a daemon watches triggers and auto-demotes on fire | Popperian falsifiability made persistent: the kill-condition is declared before the disconfirming evidence exists | Belief Memory (arXiv:2605.05583); uses FC-3/FC-6, calibrate.py; distinct from #12/#17 | 2 | M | H |
| 53 | **Learned gated role/topology router** — fit an OFFLINE, inspectable policy table mapping claim-type→teamwork pattern on the outcome ledger, behind a hard go/no-go gate vs the hand-set gates | Learns which teamwork pays off per claim-type while staying auditable (a table, not latent memory) | MetaGen self-evolving roles (arXiv:2601.19290); 'When Does Verification Pay Off' (arXiv:2512.02304); extends PRD-01 gates | 2 | L | H |
| 54 | **Belief-retention canary set (forgetting meter)** — freeze past high-confidence beliefs + spans; re-quiz on a schedule and fire a meter on silent retention/confidence/provenance drift | Turns 'persistent' from a claim into a monitored number; measures the downside of sleep-consolidation | 'Do Self-Evolving Agents Forget?' (arXiv:2605.09315); Continual Learning Bench (arXiv:2606.05661) | 2 | M | H |
| 55 | **openFDA FAERS disproportionality signal** — for a drug-adverse-event belief, compute PRR/ROR in code with applicability gates and reporting-bias caveats baked into the verdict | Adds a real-world-evidence axis distinct from trials and literature; a code-run pharmacovigilance forensic | openFDA FAERS API; PRR standard pharmacovigilance; extends the code-run robustness auditor | 3 | M | M |
| 56 | **Orchestration-coverage verifier** — a meta-role at investigation join that checks the swarm's collective output actually addresses both stances of the tension, emitting a typed replan on gaps | Every current check is claim-level; nothing verifies the collective result against the original question — catches silent drift | Verified Multi-Agent Orchestration (arXiv:2603.11445); survey gap (doi:10.3390/fi18060326); extends F1.10 | 3 | M | H |
| 57 | **Conformalized adjudicator intervals** — wrap every LLM-judge call so it returns {point, lower, upper, coverage}; downstream forbidden to consume the point without the interval; a wide interval auto-escalates | A judge point-estimate treated as ground truth is fabricated confidence at the meta level; makes distrust a number | LLM-as-a-Judge conformal intervals (arXiv:2509.18658); wraps PRD-02 F2.2 + audit.py | 3 | M | H |
| 58 | **Robustness-score initiative trigger** — when a load-bearing paper scores below a forensic threshold AND is re-testable AND public data exists, auto-spawn hypothesizer+dataset-scout+reanalysis and write back | Turns the auditor from a passive lens into unbidden action — the suspicion→reanalysis→writeback loop nobody closes | commits dc47496/353662b/e57945b; BUILD_PLAN §2.5/§3.2; AutoDiscovery (arXiv:2507.00310) | 3 | M | H |
| 59 | **E-value + probabilistic QBA auditor** — for observational effect+CI claims, compute VanderWeele's E-value and a Monte-Carlo bias analysis in code; return the fraction of bias draws under which the effect survives | Turns #20's binary causal gate into a calibrated fragility number in reproducible, applicability-gated code | VanderWeele & Ding E-value (PMID 28693043); EValue pkg; QBA review (jclinepi 2024); PRD-03 F3.8 | 3 | M | H |
| 60 | **do-calculus / backdoor identifiability checker** — extract a claim's implied DAG + the paper's adjustment set and run Pearl's ID/backdoor algorithm to decide whether the causal effect is identifiable | Catches structurally unidentifiable claims and collider bias QBA can't; returns the exact open path as evidence | Pearl backdoor/ID; LLM-drafted DAGs (arXiv:2409.02604); dowhy/pgmpy; complements #20 | 3 | M | H |
| 61 | **Target-trial-emulation feasibility scorer** — draft the 7-element target-trial protocol for a 'does X cause Y' question, score whether public data can emulate it, emit a runnable IPTW/matching stub | Converts 'we should test this' into 'here is the trial and whether the data to emulate it exists' — the clinician-relevant output | Hernán target-trial + 2025 TARGET guideline; TrialEmulation pkg (arXiv:2402.12083); extends value_queue FC-4/F3.9 | 3 | M | H |
| 62 | **Self-reproduction gate for TESTED** — before typing a headline claim TESTED, a reproduction agent re-derives the paper's number from methods+deposited data in-sandbox and requires a within-tolerance match | Regenerates the result from raw data, catching internally-consistent but irreproducible claims; a new epistemic bar | MLReplicate (arXiv:2605.16616); SciCoQA (arXiv:2601.12910); extends audit.py+science.py+GEO; distinct from #14 | 3 | L | H |
| 63 | **Reading-funnel Sankey** — one flow diagram of the real membrane funnel (fetched→read→spans→candidates→admitted→confirmed) with per-stage counts + tokens/$, rejects branching off as visible side-mass | Draws the core 'scale of reading, discipline of believing' story nothing currently renders; attrition = discipline made visible | CLAUDE.md §5; PRD-00 §1; reuses F4.5 cost/harvest join + F4.6 gate_decisions — pure aggregation | 4 | M | H |
| 64 | **Belief time-scrubber** — a global scrubber that re-renders the ENTIRE belief graph as of any past timestamp (nodes/confidences/provenance/edges), with playback animating the field forming | Turns idea-over-time from a per-node sparkline into a replayable trajectory of the whole self — a devastating demo | /history/{claim_id} (app.py:592) + provSpark; RQP §2 temporal history; snapshot-at-t is a deterministic join | 4 | M | H |
| 65 | **Conformal coverage dial** — a slider bound to the conformal membrane; dragging the target error live re-sorts beliefs into believed/abstain/reject and plots the precision-vs-coverage frontier | Makes the most abstract guarantee ('abstain rather than fabricate') something you feel by moving it | FC-5 admit_decision {calibrated_p,bound,route}; PRD-02/PRD-04 F4.4; client-side re-threshold of a scored set | 4 | M | H |
| 66 | **'Changed my mind' wall** — a surface memorializing every belief reversal (confidence collapse or provenance flip) with before/after, the swing sparkline, and the exact triggering span | CLAUDE.md calls reversals the most valuable output, yet nothing shows Persona changing its mind — an unfakeable credibility beat | CLAUDE.md §2/§6; /history + FINDINGS.md reversal log + FC-6; read-only aggregation | 4 | S | H |
| 67 | **Foresight backtest ('right in 2019?')** — freeze the corpus at a past cutoff, let Persona form dated beliefs on controversies with only then-available evidence, auto-grade against eventual resolution | Only a dated, self-having researcher can be graded on FORESIGHT not retrieval; converts 'no fabricated confidence' into a hard out-of-sample number | trajectory.py + date-filtered OpenAlex/EuropePMC + FC-3; FIRE-Bench (arXiv:2602.02905); distinct from #16 | new | L | H |
| 68 | **Self-ablation harness** — one command re-runs the fixed oracle sets with each epistemic component toggled off (membrane, anchoring, cross-check, verifier, span-gate), auto-emitting a mean±95%CI ablation table | Makes 'every load-bearing choice defended with a number' continuously runnable; catches components that stop paying their way | extends FINDINGS ablation lineage + BUILD_PLAN §10.1 exp_when_protection_matters oracle; AstaBench component eval | new | M | H |

## Wave 3c — 2026-07-13 (clinical · structural · KR · collaboration)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 69 | **LEGEND calibrated RWE probe** — for a drug→outcome belief, look up OHDSI LEGEND pre-computed per-database HRs (already negative-control-calibrated, with E-value) and return corroborated/contradicted/not-covered across N DBs, never the naive HR | A large-scale real-world second opinion whose confounding is already empirically corrected; distinct from #61 (drafts a protocol) — here the analysis already ran across ~1B patients, so the answer is a lookup | OHDSI LEGEND result sets + EHDEN network (JMIR 2025 e74119, 974M patients); builds on science.py + membrane cross-check; BUILD_PLAN §3.2 | 3 | M | H |
| 70 | **FDA surrogate-endpoint qualification gate** — when a belief treats a biomarker/surrogate as predicting a clinical outcome, cross-check the FDA Surrogate Endpoint table + DDT Biomarker Qualification; if not qualified for that context-of-use, may surface only as mechanistic, never as clinical-endpoint evidence | Encodes the commonest translation error as a deterministic sourced gate; only ~8 biomarkers are fully qualified so the answer is usually 'no' — high-yield cheap discipline; extends #20 into the biomarker→outcome axis it doesn't cover | FDA Surrogate Endpoint Resources + DDT Qualification Search (Ther Innov Regul Sci 2025 s43441-025-00889-6); complements audit.py adjudicator; PRD-02 routing | 2 | S | H |
| 71 | **Effect-modification forensic (Gail-Simon)** — code-run auditor forensic for any treatment effect broken out by ≥2 subgroups; runs the Gail-Simon qualitative-interaction test + heterogeneity test under a strict applicability gate; verdict: does 'works better in subgroup S' survive or is it noise | Subgroup/precision claims over-reach most and the field's own reviews call reporting unreliable; needs only the paper's numbers, fits the code-run-forensics architecture; a real HTE primitive distinct from #19 (pools) — this probes modification | Value in Health 2026 HTE scoping review (S1098-3015(26)00039-2); Gail & Simon qualitative-interaction test; extends forensics.py p_curve; PRD-03 | 3 | M | H |
| 72 | **CURE ID case-report corroboration channel** — wire the FDA/NCATS CURE ID API (clinician-submitted off-label/repurposing case reports) as a distinct channel; for 'drug D repurposed for X' return count + outcome-direction as low-tier N-of-1 corroboration, always typed weak/uncontrolled | Adds the N-of-1/registry axis nobody in the competitive set queries, and the earliest possible clinical signal; turns the repurposing loop (#58) into one corroborated against actual bedside use | FDA/NCATS CURE ID platform + API; metformin/statin EHR-repurposing precedent (JAMIA 22(1):179); BUILD_PLAN §2.5/§3.2; extends science.py | 3 | M | M |
| 73 | **RCT-vs-RWE concordance prior** — when a treatment-effect belief rests on observational data, attach a prior on how often RWD emulations reproduced comparable RCTs (RCT-DUPLICATE/OHDSI benchmarks, stratified by design features) and widen confidence accordingly | Operationalizes 'no fabricated confidence' for the most dangerous case (observational effect stated as causal); converts RWD-vs-RCT reliability into a calibrated sourced number keyed to design; complements #59's fragility with a concordance base-rate | RCT-DUPLICATE (Circulation 2021) + OHDSI RWE benchmarking; extends calibrate.py + audit.py _field_base (#36); PRD-02 | 2 | M | M |
| 74 | **Structure-based PPI plausibility gate (AF-Multimer + LIS)** — for 'protein X binds Y', co-fold with AlphaFold-Multimer/Boltz-1 and score the interface with ipTM + PAE-derived LIS → admit/caution/reject-corroboration; fires only on direct binary physical-interaction claims, abstains on >2000aa / no-MSA; tests geometry not affinity | An evidence axis orthogonal to text co-occurrence and the stat/genetic gates — a claim two papers 'agree' on but no interface supports is exactly the internally-consistent-but-wrong assertion Persona catches; a real in-silico test, not a citation | 'Enhanced PPI Discovery via AlphaFold-Multimer' + LIS (PMC12191236, 2024/25), ipTM<0.55≈random; builds on audit.py/forensics.py + science.py; PRD-03 molecular gates | 3 | M | H |
| 75 | **AlphaMissense/ESM1b variant-pathogenicity second-opinion** — when a paper claims a missense variant is pathogenic/LoF, look up the precomputed AlphaMissense proteome-wide score (now in Ensembl) + ESM1b zero-shot as two independent opinions; if the claim and BOTH predictors disagree, emit a typed caution and route to human, not silent anchoring | Orthogonal to gnomAD/ClinVar frequency gates ('too common?') — this asks 'does the structure/sequence model think it's damaging?'; precomputed tables make it essentially free, a standing check on every mutation-effect belief | AlphaMissense (Science 2023 adg7492) beats ESM1b/EVE on ClinVar+MAVE; Ensembl proteome-wide release (2026); PIEZO1/CFTR benchmarks feed the applicability gate; extends #13 | 2 | S | H |
| 76 | **Mutation-disrupts-interface test (WT-vs-mutant co-fold delta)** — for 'mutation X abolishes the A–B interaction', co-fold WT and mutant A:B, compare Δ ipTM/ΔPAE/ΔLIS cross-checked with an ESM1b/ESM-2 zero-shot delta; a claimed disruption where BOTH signals are unchanged fails to corroborate — a negative structural result is only 'not corroborated', never refuted | Tests the coupling between a mutation and a mechanism — a two-part causal-mechanistic claim neither a variant-effect score nor a PPI check alone can adjudicate; closes the 'why' gap PRD-03's genetic gates leave open | Composes #74+#75; 'AF3 secret sauce for mutational effects' (bioRxiv 2024.05.25.595871); single-mutation blindness (PubMed 39756261, CSBJ 2024) encoded as the gate; BUILD_PLAN §3.2 | 3 | M | H |
| 77 | **Docking + PoseBusters + Boltz-2 binding-mode plausibility** — for 'drug D binds target T at pocket S (~K)', dock D into the AF/PDB pocket (DiffDock, Vina fallback), gate every pose through PoseBusters physical-validity, use Boltz-2 affinity as an orthogonal band; verdict is 'geometry plausible/implausible', never a quantitative binding claim | Turns a load-bearing drug-mechanism assertion into a testable geometric check with an honest ceiling; PoseBusters as a hard reject filter refuses fabricated confidence from a pretty-but-invalid pose — a structure-based drug axis no logged idea covers | Boltz-2 co-folding+affinity ~FEP 1000x faster (bioRxiv 2025.06.14.659707); PoseBusters (Chem Sci 2024 d3sc04185a) Vina/Gold beat DL on PB-valid poses; reuses DiffDock+rdkit; PRD-03 F3.8 | 3 | M | M |
| 78 | **Structure-as-arbiter contradiction resolver** — when a contradiction's two sides disagree on a structural fact ('residue K at interface' vs 'K buried'), fetch AF/PDB (AF-Multimer where a partner is named) and compute the disputed feature (SASA, interface residue set, contact map) as an orthogonal tiebreaker typed INFERRED-from-structure; escalate to human only if the structural signal is low-confidence | The sharpest form of the lens — an in-silico computation adjudicating a mechanistic disagreement the literature can't settle by authority; plugs into the contradiction→exact-evidence→typed-belief loop, a capability no text/stat/genetic resolver has | AF-Multimer interface reliability at ipTM>0.55 + LIS (PMC12191236); alternative-fold blind spots (PubMed 39756261) bound abstention; reuses #74; BUILD_PLAN §3.2, extends #37 | 2 | M | H |
| 79 | **Ontology-grounded claim identity (MONDO/HPO/GO/ChEBI)** — replace embedding-only canonicalization with ontology grounding; map subject/object to MONDO/HPO/GO/ChEBI CURIEs via Monarch/OLS, merge on an equivalence axiom (deterministic) not cosine≥0.86, and store the is-a closure so a parent-disease claim is comparable to a child; keep embedding fallback for unmappable strings | Claim identity (subject,relation,object,sign) is the axiom the KG rests on — today string+cosine, the acknowledged 'worst bug' surface; CURIEs make identity auditable and add free hierarchical reasoning nothing in the store has | Builds on canon.py false-merge guard + kg.py identity axiom; MONDO equivalence axioms (Monarch 2025); 'Ontology-Enhanced Representation for LLMs' (arXiv:2405.20527); (arXiv:2205.03447) | 2 | M | H |
| 80 | **Bipolar argumentation semantics over the belief graph** — treat CONTRADICTS/SUPPORTED_BY edges as a bipolar argumentation framework; compute each belief's acceptance via grounded/preferred extension (hard verdict) or gradual DF-QuAD (continuous defensibility); a new contra deterministically propagates flips downstream and renders the exact attacking/defending set as the 'why' | Turns the contradiction graph from a display artifact into a reasoning engine with a formal replayable answer to 'why accepted?'; distinct from heuristic #26 and LLM debate #48 — symbolic acceptability with a provable extension | Consumes kg.py edges + independent_source_count as strength; 'LLM Argument Mining meets Argumentation & DLs' (arXiv:2603.02858); (S0925231225027651, 2025); (arXiv:2412.16725) | 2 | M | H |
| 81 | **Ontology-reasoned contradiction validation + discovery** — use ontology axioms at the membrane as a two-way filter; VALIDATE: fire CONTRADICTS only when entities are ontologically identical/on the same subsumption line (kills spurious tensions); DISCOVER: surface hidden ones like 'treats A' vs 'contraindicated in A′ (is-a A)' or disjoint-class incoherence; deterministic, applicability-gated | A distinct axis from source-independence pre-check (#37) — entity-level ontological coherence; cuts false contradictions AND finds real ones hidden by name mismatch, the 'evidence a domain researcher would never find' differentiator | Extends membrane.py admission + kg.py CONTRADICTS; depends on #79 CURIEs; MONDO equivalence/disjointness (Monarch 2025); SIDEKICK indication/contraindication ontology (arXiv:2602.19183, 2026) | 2 | M | H |
| 82 | **Inspectable PSL / hinge-loss-MRF joint confidence** — encode a few soft first-order rules (support transitivity, independence-weighted corroboration, contradiction mutual-exclusion) as a Probabilistic Soft Logic / hinge-loss MRF and run convex MAP inference so confidences are jointly consistent; rules human-readable, writes only INFERRED deltas, forbidden to overwrite READ/TESTED/HUMAN_CONFIRMED/anchored; weights calibrated on the outcome ledger | Makes the store reason as a coherent whole instead of a bag of numbers while staying auditable (weighted logic, no black box) — satisfies the no-latent-memory constraint; distinct from #17 (scoring) and #57 (meta-uncertainty) | Extends kg.py confidence + calibrate.py; PSL convex/tractable on FalkorDB; Hinge-Loss MRFs & PSL (arXiv:1505.04406); Swift Markov Logic (arXiv:2210.00283); (arXiv:2505.12329, 2025) | 2 | L | M |
| 83 | **Past-time temporal-logic monitors over belief history** — compile epistemic invariants into past-time metric temporal logic and run them online over the bi-temporal belief stream (e.g. anchored-downgrade⇒once(HUMAN_CONFIRMED/TESTED); never(confidence rose while independent_source_count flat); retracted-source⇒support removed within N days); emit the counterexample trace on violation | Falsification contracts (#52) watch the world; this watches Persona for evidence it broke its own epistemic rules — catches provenance-laundering and confidence inflation no per-belief check sees; a formal replayable trace, the process-level legibility money-shot | Runs over history.py bi-temporal + provenance/anchor flags; Causal Past Logic runtime verification (arXiv:2605.20923, 2026); ProbGuard (arXiv:2508.00500, 2025) | 2 | M | H |
| 84 | **Alert-fatigue-aware digest cadence governor** — a notification layer over ESCALATE/BELIEF_UPDATE that tiers every human signal (interrupt-now/daily/weekly/silent) by consequence×novelty, batches low tiers into a rendered digest, and LEARNS the interrupt threshold from act-vs-dismiss history; per-target + global quiet hours + a 'why you're seeing this now' line | The always-on colleague (#15) pings but nothing governs volume; CDS research shows humans override 49-96% of alerts once fatigued; a learned tiered cadence is the difference between an adopted and a muted collaborator | Builds on events.py SSE + daemon/supervisor.py; extends not duplicates #15; CDS Stewardship tiered severity (PMC9132737); Mindbowser alert-fatigue 2026 | 4 | M | H |
| 85 | **Two-way reliance-calibration meter** — a per-verdict widget showing Persona's measured historical hit-rate on THIS claim class beside its confidence, logging whether the human accepted/overrode; over time plots the human's reliance-appropriateness (Persona right/wrong × human followed/overrode), surfacing over-trust and under-trust as a number about themselves | #16 measures Persona's own calibration; the collaboration bottleneck is the human's reliance calibration — trust calibration doesn't improve joint performance unless reliance is appropriate; nothing in the queue does it | Wraps audit.py/app.py verdict surfaces + outcome ledger; distinct from #16 and #57; 'From Trust to Appropriate Reliance' (arXiv:2604.23896); (Tandfonline 10.1080/12460125.2025.2593251) | 4 | M | H |
| 86 | **Delegation-up board (VoI-ranked micro-tasks to the human)** — invert the manager pattern; an inbox where Persona assigns the HUMAN scoped micro-tasks it structurally can't do (confirm a span, pick a base-rate, judge a wet-lab call, break a cross-persona tie), each with a one-line why, an expected-value-of-your-answer estimate, and an effort tag, VoI-ranked; answering writes back HUMAN_CONFIRMED and anchors | Human-as-resolver is a design feature (CLAUDE.md §7) but escalation is undifferentiated today; the Manager-Agent result is that upfront skill-based assignment beats reactive delegation — make Persona delegate UP with the discipline it delegates DOWN | Extends discover.py/mywork.py escalation + value_queue/VoI; anchoring writeback validated (100% vs 71%); 'Orchestrating Human-AI Teams: Manager Agent' (10.1145/3772429.3772439, 2025); (arXiv:2602.16844) | 1 | M | H |
| 87 | **Confirmation-timing model (when to pull the human in)** — a cost-model deciding WHEN a long autonomous investigation pauses for a human check, minimizing (inspection labor from too-frequent asks) vs (recovery cost of a propagated error); checkpoints fire at high-branching/high-consequence nodes, not confirm-at-end or confirm-every-step; a 'preview + one-click steer or let-run' card at each | The daemon runs mostly autonomously and users reject both confirm-at-end and confirm-everything; placing confirmations at globally optimal moments is a modeled decision that directly protects the belief-state from a silently propagating wrong call | Builds on daemon/supervisor.py + converse.py steering; distinct from #46 (agent-to-agent); 'When Should Users Check?' (CHI 2026, arXiv:2510.05307); Morae (arXiv:2508.21456) | 1 | M | H |
| 88 | **Shared living-notebook inline annotation that steers the loop** — make the one-way notebook stream bidirectional; the human annotates any entry (agree/doubt/chase-this/pin/wrong) and each becomes a typed HUMAN signal that reshapes the loop in place ('doubt' demotes recheck + can spawn a disconfirmation reader, 'chase this' spawns a reader, 'pin' protects from consolidation pruning); annotations render inline with attribution | Steering lives in a separate chat channel today and the reasoning stream is read-only; letting the PI react at the exact point they disagree and have it move the work turns a spectator into a co-researcher, and margin doubts become cheap in-context human judgment the membrane values | Extends events.py stream + converse.py directive capture (note_to_self/focus_now exist) into per-entry annotations; 'Collaborative Document Editing with Users and AI Agents' (arXiv:2509.11826); (Springer 10.1007/s00146-026-02853-w, 2026) | 4 | M | H |

## Wave 3d — 2026-07-13 iter 7 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 89 | **Contradiction triage board** — rank open contradictions by (independence of both sides × downstream load-bearing × clinical stakes), not recency, so the human sees which tensions actually matter | Turns the conflict inbox from a queue into a prioritized worklist; extends VoI to contradictions | value_queue (FC-4); kg.contradictions + load-bearing | 4 | S | H |
| 90 | **Auto positive/negative control injection for oracles** — every code-run oracle (MR/DepMap/meta-analysis) runs a known positive + negative control alongside the real test; if a control fails, the real result is quarantined | A self-check that catches silent pipeline breakage before it reaches the belief-state — extends the FC-8 envelope | FC-8 oracles; control-based calibration (RCT-DUPLICATE ethos) | 3 | M | H |
| 91 | **Belief confidence-budget / evidence accounting** — track how much independent evidence each belief "spent" to reach its confidence; flag beliefs whose confidence exceeds what their evidence justifies (over-drawn) | Makes "no fabricated confidence" a structural invariant, not a vibe; feeds the calibration panel | calibrate (FC-5); kg independence counts | 2 | M | H |
| 92 | **Cross-modal claim linking (text ↔ figure ↔ table)** — link a textual claim to the exact figure/table it derives from and check the text matches the figure's numbers | Numbers-in-figures is the auditor's biggest blind spot; multimodal grounding closes it | research: SciVer / MuSciClaims (arXiv:2506.15569 / 2506.04585); audit.py | 3 | L | M |

## Wave 3e — 2026-07-13 iter 8 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 93 | **Provenance-aware model routing** — route extraction/adjudication to cheap vs strong models by claim stakes × surprise (high-stakes causal → strongest + two-reader; routine descriptive → cheap) | A per-claim cost×quality controller; spend compute where belief-risk is highest | research: LLM routing/cascades; budget.py + PRD-01 verifier | 1 | M | H |
| 94 | **Evidence half-life per subfield** — empirically estimate how fast a subfield's claims get overturned, and set validity-windows + revisit cadence from it | Data-driven staleness instead of a fixed timer; fast-moving fields revisited sooner | trajectory.py + temporal confidence (PRD-02 F2.7) | 2+3 | M | M |
| 95 | **Adversarial-collaboration protocol** — on persona↔persona or persona↔human disagreement, pre-register what evidence would change each side's mind, then jointly seek it | Metascience's gold standard for resolving disputes; makes disagreement productive | research: adversarial collaboration; FC-9 reconcile | 1+4 | M | M |

## Wave 3f — 2026-07-13 iter 9 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 96 | **Time-travel belief-state replay** — reconstruct what Persona believed at any past date (bi-temporal query) and show how a conclusion would have differed; audit "when did we know X" | Turns the bi-temporal store into an auditable memory a reviewer can interrogate | HANDOFF frozen contract (bi-temporal `valid_from/valid_to`); history.py | 2+4 | M | M |
| 97 | **Ontology-mapping reconciliation** — when two claims use different ontology IDs that map to the same concept (MONDO/HPO/GO), reconcile them; sibling-but-distinct concepts flag a subtle scope mismatch | Catches false agreement/disagreement from vocabulary drift the canonicalizer misses | KR: MONDO/HPO via OLS/EBI; canon.py | 2+3 | M | M |
| 98 | **Reviewer "confidence report card"** — one-glance per-conclusion card: provenance tier, independent-lab count, calibration bin, causal tier, contamination status, open contradictions | The "should I trust this" summary a busy PI wants; aggregates every trust signal | FC-3/FC-5/FC-6/FC-10; audit trust ledger | 4 | S | H |

## Wave 3g — 2026-07-13 iter 10 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 99 | **Expected-info-gain question ranking** — rank human-adjudications by how much a human answer would cut Persona's total belief-uncertainty, asking the highest-value questions first (not FIFO) | Respects the scarcest resource — human time; the handoff inbox becomes a value-ranked queue | active learning / EIG; handoff inbox (FC-2) + VoI (FC-4) | 2+4 | M | H |
| 100 | **Counterfactual literature simulation** — "if this foundational study had reported null, how would the field's consensus differ?" — perturb a key paper and recompute the argument/dependency state | Whole-literature what-if; the deepest expression of the load-bearing thesis | BUILD_PLAN §3.3; extends fragility_cascade (FC-4) | 3+4 | M | H |
| 101 | **Auto protocol / registered-report drafting for the top experiment** — for the highest-VoI value-queue item, draft a full pre-registerable protocol (hypothesis, design, power, analysis, stopping rule) ready to run or hand off | Turns the value queue from a list into an actionable, falsifiable artifact | value_queue (FC-4); prereg discipline (RQ-E12b) | 3 | M | H |

## Wave 3h — 2026-07-13 iter 11 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 102 | **Reader-adaptive explanation depth** — tailor an explanation's depth to the reader (headline → full derivation) and "teach" a result at the right level | The L1–L4 knowledge ladder exists but isn't reader-adaptive; makes Persona a communicator, not just a reporter | surf-knowledge L1–L4; knowledge.py topic_digest | 4 | M | M |
| 103 | **Standing adversarial/chaos audit of the pipeline** — periodically inject poisoned sources, prompt-injection papers, and contradiction floods into a shadow copy and verify the membrane/anchoring hold | Makes "test the membrane" a live regression, not a one-off — catches epistemic drift before it corrupts the real self | reuses experiments/exp_poisoning.py; membrane/anchor | 2+4 | M | H |
| 104 | **Confidence-conditioned deliverable language** — a review/paper hedges each claim by its calibrated confidence (settled→assertive, contested→hedged, inferred→explicitly speculative) | Prose never overstates the evidence; extends the causal-tier language gate to full calibration | FC-5 calibrate + FC-10 causal-tier; deliverables | 3 | M | M |

## Wave 3i — 2026-07-13 iter 12 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 105 | **Steel-man vs strongest-counter viewer** — for any belief, show its single strongest supporting span and strongest disconfirming span side by side, so the human adjudicates with both at once | The fastest path to a good human call; aggregates red-team + crosscheck | red-team (PRD-09) + kg.crosscheck; handoff UI | 4 | S | H |
| 106 | **Method-limitations extractor** — extract each paper's own stated limitations/caveats and attach them to the claims they qualify, so a claim never travels without its authors' own caveats | Reduces over-extension at the source; exact-span, cheap | audit `_EXTRACT` pattern; extract.py | 3 | M | M |
| 107 | **Belief portfolio-risk report** — treat the belief-state as a portfolio: report concentration risk (how many conclusions rest on a few load-bearers) + evidence-source diversification | A PI-facing "how exposed is this research program" view; extends load-bearing | dependency/load-bearing (FC-4); BUILD_PLAN §3.2 | 3+4 | M | M |

## Wave 3j — 2026-07-13 iter 13 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 108 | **Onboarding seed critique** — when a human seeds a persona's interests, Persona critiques the seed (too broad/narrow/contested?) and proposes a sharper starting question before spending budget | Stops the researcher chasing a vague mandate; a better cold-start | selfmind.seed; deliberate.py | 1 | S | M |
| 109 | **PROV-O provenance export** — export a belief's full provenance as a standard W3C PROV-O graph, interoperable with external tools | FAIR/interop beyond RO-Crate; a belief becomes portable across ecosystems | extends RO-Crate (PRD-04 F4.10); sessions.py | 4 | M | M |
| 110 | **Field-adaptive membrane thresholds** — auto-tune the membrane's independence/convergence bar per subfield from that field's measured replication base-rate (60%-replicate field → stricter than 90%) | Data-driven "discipline of believing" instead of one global constant | membrane; audit field base-rates (`_BASE`) | 2 | M | H |

## Wave 3k — 2026-07-13 iter 14 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 111 | **Contradiction resolution playbook** — a standard recipe per conflict type (temporal→prefer newer + supersession check; semantic→escalate; misinfo→retraction check; insufficient→null-hunt/dataset) | Codifies human-as-resolver into reusable procedures; speeds every adjudication | conflicts typing (FC-10 / PRD-02 F2.5); handoff | 2+4 | M | M |
| 112 | **Auto "so what" impact line** — for each verified belief or closed loop, a one-line "why this matters" (what decision it changes, what it de-risks) | A PI sees relevance instantly; turns results into decisions | value_queue (FC-4); deliverables | 3+4 | S | M |
| 113 | **Compute cost + carbon transparency** — track/display compute cost (and estimated carbon) per investigation/belief so "scale of reading" is honest about its footprint | Legibility about resource use; a credibility + ethics signal | budget.py; swarm cost-vs-yield (PRD-04 F4.5) | 4 | S | M |

## Wave 3l — 2026-07-13 iter 15 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 114 | **Research-frontier map artifact** — a periodically-refreshed one-page map of a field's live frontier (what just moved, what's contested, highest-VoI open question), publishable as a standing shareable artifact | Synthesizes trajectory + value-queue + fieldmap into the "always-on colleague" deliverable a PI would subscribe to | trajectory + value_queue (FC-4) + fieldmap | 3+4 | M | H |
| 115 | **Negative-space hypothesis generation** — generate hypotheses about what's NOT been studied (plausible-but-missing edges in the dependency graph), not just contradictions | Proactive discovery — mines the graph's *holes*, a capability contradiction-detection can't reach | dependency graph (FC-4); discover.py | 3 | M | H |
| 116 | **Calibration-weighted persona ensembling** — when the "lab" exists, ensemble personas' beliefs weighted by each persona's measured calibration IN that subfield (well-calibrated-in-oncology gets more oncology weight) | Turns the multi-researcher lab into a measurably-better aggregate, not just more voices | second researcher (PRD-05); calibration (FC-13/PRD-15) | 2+1 | M | M |

## Wave 3m — 2026-07-13 iter 17 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 117 | **Persona publishes its own preprint** — periodically compile verified findings + reversals + method into an auto-drafted "what I found and how I know it" preprint, submittable | The BUILD_PLAN endgame — a synthetic researcher that *produces papers*, not just reads them | deliverables/paper.py; verified ledger; error log | 3+4 | L | H |
| 118 | **Meta-research self-study** — Persona studies its OWN track record as a dataset: which predictions held vs reversed, calibration over time, and writes a self-assessment | Dogfoods the whole method; the ultimate credibility artifact (a researcher that measures itself) | prediction ledger (#17); verified/revisit history | 3+4 | M | H |
| 119 | **Teaching-signal capture for the learning loop** — every human correction/adjudication is stored as a labeled signal with its reward-type separated (citation/format/execution/calibration/outcome), ready for the future open-weight RL | Sets up CONTINUATION_HANDOFF §7's learning program with clean, non-persuasion rewards from day one | conflict_reviews; CONTINUATION_HANDOFF §7 | 1+2 | M | M |

## Wave 3n — 2026-07-13 iter 18 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 120 | **End-of-day budget triage** — when the daily budget is nearly spent, Persona explicitly triages the last dollars to the single highest-VoI action (belief-update / handoff / test) and logs the call | The economics of a real researcher made visible; spends the scarce last budget on what matters most | budget.py; value_queue (FC-4) | 1+4 | S | M |
| 121 | **Contradiction aging escalation** — an unresolved contradiction auto-raises its inbox priority past a staleness threshold ("open N days, still load-bearing") | Stale open tensions shouldn't sit forever; keeps the human-resolver loop from silently stalling | conflicts (FC-10); handoff inbox; history age | 2+4 | S | M |
| 122 | **Multi-modal anchoring bar** — before a belief can be human-anchored, require a minimum diversity of source *types* (literature + structured-DB + functional-test), not just a count | An anchor never rests on one modality — the strongest form of "discipline of believing" | kg anchor policy; molecular oracles (FC-8) | 2 | M | H |

## Wave 3o — 2026-07-13 iter 19 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 123 | **Living entity cards / glossary** — a live card per canonical entity (definition, synonyms, key claims, contested points) grounding every mention | Reduces ambiguity, aids the reader, and exposes the canonicalizer's work | canon.py; knowledge.py; kg claims_in | 3+4 | S | M |
| 124 | **Cross-persona peer review** — one persona reviews another's compiled report before it ships (internal lab peer review), typing agreement/dissent | Extends the second-researcher lab into a real quality gate — a report vetted by a differently-disposed mind | second researcher (PRD-05); critic.py | 1+3 | M | M |
| 125 | **Evidence-tier upgrade pathway** — per belief, show exactly what evidence would move it up a provenance tier ("one independent replication + a public-data test from TESTED") | Actionable legibility — tells the human/system the cheapest path to a stronger belief; feeds the value queue | provenance tiers; value_queue (FC-4) | 4 | M | H |

## Wave 3p — 2026-07-13 iter 20 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 126 | **Protocol-cost estimator** — for the top VoI experiment, estimate real-world cost/time (assay $ + weeks) from public protocol/reagent price data, so the value queue's cost tier is grounded in dollars, not a heuristic | Makes VoI÷cost honest — a PI trusts a ranking that knows what an experiment actually costs | value_queue (FC-4) cost_tier; protocols.io/reagent pricing | 3 | M | M |
| 127 | **Living-notebook replay scrubber** — reconstruct a past investigation's living-notebook stream as a timeline scrubber, so a reviewer can replay the exact reasoning that led to a conclusion | "Watch it think" for the archive; turns the event log into an auditable narrative | events.py stream; sessions event log; notebook | 4 | M | M |
| 128 | **Interest-graph visualization** — show the persona's interests as a live heatmap over belief-graph regions (where attention is allocated + why), making focus visible | BUILD_PLAN §1.4 interests made visual — the reader sees where the mind is looking and its articulable reason | selfmind.interests; graph UI; attention weights | 4 | S | M |

## Wave 3q — 2026-07-13 iter 22 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 129 | **Assumption-inversion stress test** — for a load-bearer, systematically invert its key assumptions and flag which inversions the current evidence could NOT rule out | Finds where the field is *quietly assuming*; extends fragility/red-team from claims to assumptions | dependency/load-bearing (FC-4); red-team (PRD-09) | 3 | M | H |
| 130 | **Citation-context drift detector** — detect when a paper is cited over time for a claim it never actually made (telephone-game), by comparing citing context to the source's exact claims | A real, under-instrumented integrity failure; extends citation-vs-support to *semantic* drift | citation_support_ratio (FC-3); exact spans | 3 | M | M |
| 131 | **"Diff since you last looked" digest** — for a returning human, a personalized "what changed in your subfield" (new beliefs, flipped contradictions, retractions, trajectory inflections) since their last visit | The always-on colleague made personal — the reason a PI comes back daily | events/history; trajectory; retraction (FC-6) | 4 | S | M |

## Wave 3r — 2026-07-13 iter 23 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 132 | **Inter-instance belief federation** — a provenance-preserving protocol for two Persona deployments (different labs) to share + reconcile beliefs without merging raw data | Knowledge compounds across deployments; the network effect of a persistent researcher | extends cross-persona reconcile (FC-9); PROV-O (#109) | 2 | L | M |
| 133 | **Governance audit trail for anchors** — a tamper-evident, human-signed trail for every HUMAN_CONFIRMED anchor (who/when/rationale/evidence) — regulatory-grade provenance for clinical claims | Makes high-stakes anchoring auditable to a regulator, not just a reviewer; unlocks clinical use | conflict_reviews hash-chain; anchor policy | 2+4 | M | M |
| 134 | **Explanation-faithfulness check** — verify Persona's natural-language explanation of a conclusion actually matches its evidence graph (does the prose cite what the graph says, or drift beyond it?) | Catches the model narrating past its evidence — a distinct failure from citation hallucination | synthesis/checker.py; evidence tree | 3 | M | H |

## Wave 3s — 2026-07-13 iter 25 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 135 | **Strategy self-tuning from outcomes** — update `self/strategies.md` (which tactics worked) from the error log + verified/reversal outcomes, closing the procedural-memory loop measurably | Makes "a researcher that updates" real — tactics improve from evidence, not vibes | BUILD_PLAN §5.5 procedural memory; error log; verified ledger | 1+2 | M | H |
| 136 | **Dead-end / rabbit-hole detector** — recognize when an investigation isn't converging (cost rising, no new validated beliefs) and cut losses / reprioritize | Stops the swarm burning budget on unproductive threads — self-awareness about its own effort | investigation steps; budget; validated-belief yield | 1 | M | H |
| 137 | **Provenance-aware history compression** — when the notebook/history grows huge, compress old entries while preserving every evidence link + decision | Legibility scales without unbounded storage; the mind stays inspectable at any age | history.py; events; sleep-consolidation (FC-11) | 2+4 | M | M |

## Wave 3t — 2026-07-13 iter 26 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 138 | **Multi-format deliverable export** — export a conclusion as a slide, poster, plain-language brief, or thread, not just a LaTeX PDF — audience-appropriate dissemination | A researcher that communicates to the right audience, not one format; widens impact | deliverables/*; scientific-slides/poster skills | 4 | M | M |
| 139 | **Belief-graph snapshot versioning** — periodic immutable snapshots of the whole belief-state (git-like tags) so any past state is reconstructable + diffable | Complements time-travel replay (#96); makes "the mind at time T" a first-class, auditable object | kg store; history.py; bi-temporal contract | 2 | M | M |
| 140 | **Reviewer trust-onboarding tour** — a first-run guided tour teaching a new human what provenance tiers, confidence, and handoff actions mean | Trust is calibrated from minute one; the legibility layer only works if the reader can read it | UI surfaces; SCIENTIFIC_WORKBENCH_SPEC | 4 | S | M |

## Wave 3u — 2026-07-13 iter 27 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 141 | **Contradiction resolution betting** — humans/personas place calibrated bets on which side of a contradiction holds; track crowd accuracy as an extra signal | Aggregates distributed judgment; extends the prediction ledger to a crowd | prediction ledger (FC-17); handoff | 2+4 | M | M |
| 142 | **Auto falsification checklist** — per belief, the specific observations that would falsify it, so a skeptic knows exactly what to look for | Popperian rigor made explicit; extends red-team into a standing artifact | red-team (PRD-09); CLAUDE.md §3 | 3 | S | M |
| 143 | **Human-expertise routing** — route a handoff to the RIGHT human by matching the question's subfield to declared expertise (multi-human team), not just "a human" | The human-as-resolver loop scales to a team; the right expert sees the right dossier | handoff inbox (FC-2); field ids | 4 | M | M |

## Wave 3v — 2026-07-13 iter 28 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 144 | **Time-to-first-insight metric** — track how fast Persona reaches its first validated belief on a new interest | A throughput benchmark of the whole pipeline; makes "always thinking" measurable | events/history; verified ledger; benchmarks (FC-7) | 4 | S | M |
| 145 | **Contradiction cluster detection** — group related contradictions (same disputed mechanism) so the human resolves the root, not N symptoms | Cuts human load — one adjudication settles a family of tensions | conflicts (FC-10); communities/fieldmap | 2 | M | M |
| 146 | **Provenance-preserving translation** — translate a belief/report to another language while preserving every exact-span citation link | Serves non-English researchers without losing grounding | deliverables; exact-span provenance | 3+4 | M | M |

## Wave 3w — 2026-07-13 iter 30 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 147 | **Uncertainty on every surfaced number** — never show a point estimate without its CI/error bar, across all UI numbers | Enforces honest-uncertainty visually everywhere; a design invariant | SCIENTIFIC_WORKBENCH_SPEC; all metrics | 4 | S | M |
| 148 | **Salami-slicing / duplicate-cohort detector** — flag when multiple papers report the same data/cohort (inflates apparent independence) | Protects the independence-by-lab assumption the whole membrane rests on | kg independence-by-lab; forensics | 3 | M | H |
| 149 | **Belief→hypothesis reversal log** — track every time a belief was downgraded back to hypothesis, making epistemic humility a visible artifact | A researcher that shows when it walked something back earns trust; extends the error log | error log; verified/revisit; provenance history | 2+4 | S | M |

## Wave 3x — 2026-07-13 iter 31 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 150 | **Data-availability check** — for every claim citing data, verify the data is actually accessible (link rot / access-gated); flag "data claimed but unavailable" | Reproducibility starts with the data existing; catches a common silent gap | datasets.fetch allowlist; ingest | 3 | S | M |
| 151 | **Reasoning-chain length budget** — cap inference-chain depth; a conclusion N hops from evidence is flagged increasingly speculative | Long chains compound error; makes over-reach visible (pairs with premise→inference chains) | evidence trees (RQ-E06); provenance | 2 | S | M |
| 152 | **Cross-claim numerical consistency** — check numbers reused across a persona's own claims/reports stay consistent (no drift) | Self-consistency guard on its own outputs; extends the self-audit | audit.py; deliverables; unit check | 3 | M | M |

## Wave 3y — 2026-07-13 iter 32 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 153 | **Interactive assumption toggle in reports** — a reader toggles an assumption on/off and sees which conclusions survive | Turns a static report into an explorable argument; extends fragility to the reader | fragility_cascade (FC-4); deliverables | 4 | M | M |
| 154 | **Auto peer-review-response drafting** — when a human contests a claim, Persona drafts a grounded response (concede, or defend with evidence) | Closes the human↔researcher dialogue loop with grounded rebuttals, not just acceptance | conflict_reviews; crosscheck; critic.py | 3 | M | M |
| 155 | **Longitudinal field-health index** — a per-field reproducibility/rigor trend over time (aggregating auditor + forensics across the field) | A macro "is this field getting healthier?" signal no tool offers; PI-facing | auditor + forensics; trajectory | 3+4 | M | M |

## Wave 3z — 2026-07-13 iter 33 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 156 | **Confidence-delta alerts** — notify when a belief's confidence changes materially (crosses a threshold), so the human catches big swings | Surfaces state change (the design principle "motion only for real change") as a signal | history.py; confidence over time; alerts | 4 | S | M |
| 157 | **Reagent/antibody validation check** — for a claim relying on a specific antibody/reagent, check validation registries for reliability flags | A top irreproducibility cause (bad antibodies) the auditor currently misses | science clients; antibody registry APIs | 3 | M | M |
| 158 | **Meta-prompt hygiene guard** — periodically audit the persona's own prompts for drift/injection, keeping the swarm's instructions clean | Protects the swarm itself from prompt corruption; a standing self-security check | deliberate.py; selfmind; chaos-audit (#103) | 1 | S | M |

## Wave 4a — 2026-07-13 iter 34 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 159 | **Identity-drift monitor** — track whether the persona's stated identity/disposition stays consistent over time vs slowly morphing; flag drift | Protects the durable "self" — the whole thesis rests on identity persisting across sessions | selfmind identity; coherence.drift; CHANGELOG | 1 | S | M |
| 160 | **Belief-graph garbage collection** — safely archive orphaned/superseded claim nodes to keep the active graph lean + fast, preserving them for audit | Keeps the graph performant as it scales without ever deleting evidence | kg store; sleep-consolidation (FC-11) | 2 | M | M |
| 161 | **Provenance-weighted retrieval ranking** — rank retrieved results by provenance tier + independence, not just relevance, so stronger evidence surfaces first | The membrane's discipline applied to retrieval — you read the best-grounded thing first | vectors/retrieval; provenance tiers | 2 | M | M |

## Wave 4b — 2026-07-13 iter 35 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 162 | **Power pre-check on own tests** — before a self-test, compute required sample size / power and refuse an underpowered analysis | Persona holds its own work to the standard it audits in others (forensics power check) | forensics.min_detectable_effect; analyst | 3 | S | M |
| 163 | **External-reviewer invitation** — package a dossier and invite a named external expert (link/email) to adjudicate, widening the resolver pool beyond the local team | Scales human-as-resolver to the whole community; the compounding-infrastructure vision | handoff dossier (FC-2); export | 4 | M | M |
| 164 | **Provenance-completeness score** — per belief, score how complete its provenance chain is (every hop traceable to a span); flag gaps | Makes "exact-span grounding" measurable per belief — a gap is a to-do, not a hidden risk | provenance tree; evidence chains | 2 | S | M |

## Wave 4c — 2026-07-13 iter 36 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 165 | **Incremental graph recompute** — recompute only affected communities/load-bearing scores when new claims land, not the whole graph | Keeps synthesis/engine fast as the graph scales toward the always-on ambition | communities/consolidator; dependency | 3 | M | M |
| 166 | **Novelty-first read priority** — prioritize papers likely to contain NEW claims (cheap novelty estimate before full extraction) | Spends reading budget on what adds beliefs, not restatements; pairs with surprise queue | reader; embeddings; surprise (PRD-01 F1.6) | 1 | M | M |
| 167 | **"Why this confidence" breakdown** — one-click decomposition of any confidence value (independence, calibration, priors, contamination) | Makes the confidence number auditable at the finest grain — legibility to the digit | calibrate (FC-5); report card (FC-25) | 4 | S | M |

## Wave 4d — 2026-07-13 iter 37 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 168 | **Handoff-response SLA tracking** — track how long humans take to resolve handoffs, surface stale ones, measure human-loop throughput | Makes the human-as-resolver loop measurable + keeps it from silently stalling | handoff inbox; aging escalation (#121) | 4 | S | M |
| 169 | **Auto minimal-reproducible-example** — for a computational claim, extract the smallest runnable snippet + data that reproduces the key number | Reproducibility you can run in one click; the strongest form of a verified artifact | sessions; sandbox; RO-Crate | 3 | M | M |
| 170 | **Natural-language belief-graph querying** — ask the graph plain-English questions ("what rests on the 2013 mouse study?") and get grounded answers | The load-bearing/dependency view made conversational; the killer legibility interaction | knowledge.ask_graph; dependency (FC-4) | 2+4 | M | H |

## Wave 4e — 2026-07-13 iter 38 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 171 | **Public error-rate dashboard** — surface Persona's own measured reversal rate (how often its beliefs later flipped) as a headline honesty metric | A researcher that publishes its own error rate is more trustworthy than one that hides it | error log; verified/revisit; calibration | 4 | S | H |
| 172 | **Graceful-degradation transparency** — when a source is down or a tool fails, surface exactly what's degraded + its effect on conclusions (vs silent partial results) | Fail-loud at the boundary made visible to the human; no hidden gaps | ingest failover; sessions; gate ledger | 1+4 | S | M |
| 173 | **"What would change my mind" per interest** — for each standing interest, Persona states the evidence that would shift its stance, kept current | Makes functional taste explicit + falsifiable — the anti-anthropomorphic-theater proof | selfmind interests; BUILD_PLAN §1.4 | 1 | S | M |

## Wave 4f — 2026-07-13 iter 39 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 174 | **Self-uncertainty introspection** — Persona reports where it's least confident in its own *process* ("I'm weakest at extracting dosage claims"), not just its beliefs | Meta-cognition a human can act on; tells the reviewer where to look hardest | error log; extraction rejects; verified ledger | 1 | M | M |
| 175 | **Structured methods-section critique** — checklist-driven flags on a paper's methods (randomization, blinding, controls, preregistration) as typed signals | Extends the auditor from stats to design rigor — the other half of robustness | audit.py; forensics; methods rubric | 3 | M | M |
| 176 | **Belief-lineage family tree** — show how a belief descended from prior beliefs/evidence as a visual genealogy | Intellectual genealogy made visible — "how did we come to believe this?" | provenance history; dependency edges (FC-3) | 4 | M | M |

## Wave 4g — 2026-07-13 iter 40 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 177 | **Domain-pack architecture** — abstract the biomedical-specific pieces (science clients, field ontology) into swappable "domain packs" so Persona works on materials/climate/ML | The engine is domain-agnostic — this unlocks every field with a literature + public data | BUILD_PLAN §7.2; science.py REGISTRY; field gate | 3 | L | H |
| 178 | **Cross-domain method transfer** — surface when a method validated in one domain applies to a question in another (a genetics stats technique → economics) | Persona becomes a methods-broker across fields — a capability no single-domain tool has | cross-field translation (PRD-21); method extraction | 3 | M | M |
| 179 | **Question-decomposition planner** — break a broad question into a tree of independently-investigable sub-questions with coverage tracking | Scales investigations to big questions; makes "did we cover it?" answerable | investigation engine; director; DAG plan | 1 | M | M |

## Wave 4h — 2026-07-13 iter 41 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 180 | **Belief-obsolescence forecasting** — predict which current beliefs are most likely to be overturned soon (from trajectory + field half-life) | Tells the human what's shaky *before* it flips — the early-warning vision (BUILD_PLAN §3.1) | trajectory; evidence half-life (#94); collapse-prediction | 3 | M | H |
| 181 | **Investigation postmortem** — after an investigation closes, auto-write a short postmortem (what worked, what was wasted, what to do differently) into strategies.md | Closes the procedural-learning loop — the mind gets better at investigating over time | investigation finalize; strategies.md; error log | 1 | S | M |
| 182 | **Multi-persona knowledge commons** — personas share verified beliefs weighted by each one's calibration in that area, building a compounding shared base | The lab becomes greater than its members; the network-effect endgame | second researcher (PRD-05); federation (#132); calibration | 2 | L | M |

## Wave 4i — 2026-07-13 iter 42 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 183 | **Figure-claim consistency auditor** — verify a generated report's figures actually match the numbers in its text | Self-consistency on Persona's *own* outputs — the last mile of trustworthy deliverables | paper.py; figures; cross-claim consistency (#152) | 3 | M | M |
| 184 | **Citation round-trip verification** — for every citation in a generated report, verify the cited source actually supports the claim (not just exists) | Extends exact-span grounding to output — no citation ships unless it entails | checker.py; exact spans; CiteCheck pattern | 3 | M | H |
| 185 | **Confidence-appropriate abstention in Q&A** — when asked below its threshold, Persona explicitly abstains ("I don't know; here's what would settle it") rather than guessing | Conformal abstention (FC-5) applied to conversation — honesty at the interface | calibrate (FC-5); knowledge/converse | 2+4 | S | H |

## Wave 4j — 2026-07-13 iter 43 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 186 | **Seed-from-a-paper** — seed a persona's interests by pointing it at one paper/review; it extracts the research program to pursue | The lowest-friction onboarding — "read this, become a researcher on it" | selfmind.seed; extract; discover | 1 | S | M |
| 187 | **Interest-conflict detection** — flag when two interests pull in incompatible directions (competing for the same attention budget) | Surfaces a real tradeoff the human should decide; keeps focus honest | selfmind interests; attention weights | 1 | S | M |
| 188 | **Auto related-work generation** — for a user's draft, generate a grounded related-work section from the belief graph (settled/contested, cited) | A concrete, daily-useful deliverable for a working scientist | review.py; mywork ingest; belief graph | 3 | M | M |

## Wave 4k — 2026-07-13 iter 44 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 189 | **Autonomy escalation ladder** — a configurable ladder of what Persona may do per level (read→synthesize→test→propose→anchor), human sets the ceiling per persona | Formalizes the Balanced posture into an explicit, per-persona safety dial | daemon autonomy; anchor gate; config | 1 | M | M |
| 190 | **Spend-anomaly auto-pause** — flag unusual cost spikes (a runaway investigation) and pause before budget blowout | Protects against the "hundreds of confident errors" cost failure mode | budget.py; scheduler; halt control | 1 | S | M |
| 191 | **Belief-write audit log** — every self-belief change logged with cause + actor, queryable, so any belief's full mutation history is inspectable | Total accountability for the self — who/what changed a belief and why | history.py; events; provenance | 2 | S | M |

## Wave 4l — 2026-07-13 iter 45 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 192 | **Grant-relevance matcher** — match a persona's high-VoI open questions to open funding calls, surfacing what's fundable now | Bridges "highest-value experiment" to "who'll pay for it" — a PI's real next step | value_queue (FC-4); grants DBs | 3+4 | M | M |
| 193 | **Clinical-trial-design suggester** — for a testable clinical hypothesis, draft a minimal viable trial design (arms, endpoints, N) grounded in existing evidence | Turns a hypothesis into an actionable protocol; extends protocol drafting (#101) | value_queue; power check (#162); ClinicalTrials | 3 | M | M |
| 194 | **Auto lay-explainer** — for a verified finding, generate an accurate plain-language summary with caveats intact for non-specialists | Communication without distortion — the caveats travel with the claim | deliverables; causal-tier gate (FC-10); blocklist (FC-18) | 3+4 | S | M |

## Wave 4m — 2026-07-13 iter 46 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 195 | **"On this day" belief recall** — periodically resurface a past belief/investigation for re-examination against current knowledge | Spaced-repetition for the self — keeps the core from ossifying; complements revisit | revisit; history; staleness (#2.9) | 1 | S | M |
| 196 | **Trend-vs-noise discriminator** — distinguish a real consensus shift from transient noise (a few outlier papers) so the trajectory view isn't jumpy | Prevents over-reacting to single papers; makes "the front moved" trustworthy | trajectory; changepoint; independence | 3 | M | M |
| 197 | **Provenance-freshness badge** — show how recently each belief's evidence was last verified, at a glance | Stale-but-confident beliefs become instantly visible — honest uncertainty over time | history.series; staleness; report card (FC-25) | 4 | S | M |

## Wave 4n — 2026-07-13 iter 47 (fresh, direct — crosses #200)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 198 | **Open-review ledger publication** — publish Persona's conflict-review gold set + adjudications as an open dataset (with consent) | Turns the human-as-resolver output into compounding community infrastructure | conflict_reviews ledger; RQ-E02 gold | 4 | M | M |
| 199 | **Reproducibility badge minting** — award a machine-verifiable reproducibility badge to a paper passing the full auditor + replication (a CI badge for science) | A concrete, shareable credential nobody else issues; the auditor's public face | auditor (PRD-03 F3.7); RO-Crate; sessions | 3+4 | M | M |
| 200 | **Contribution-back to the ecosystem** — when Persona finds a likely error (sign flip, retraction contamination), draft a structured correction/comment to submit back to PubPeer / the source | Closes the loop with the community — the researcher gives back, not just consumes | audit; retraction (FC-6); PubPeer (#45-ish) | 3+4 | M | M |

## Wave 4o — 2026-07-13 iter 48 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 201 | **Taste-weight introspection** — surface the current w_v/w_t/w_s/w_c taste weights + how they steer choices, editable by the human | Makes the taste function (BUILD_PLAN §1.5) legible + tunable — taste as a dial, not a black box | taste function; priority(action); selfmind | 1+4 | S | M |
| 202 | **Parsimony scoring** — when multiple hypotheses fit, prefer the one needing fewer independent assumptions, surfaced explicitly | Occam's razor operationalized — a real judgment criterion, shown not hidden | discover; hypothesis ranking; assumption graph | 3 | M | M |
| 203 | **Surprise log** — a running stream of the most surprising findings (biggest belief-violations) — the researcher's "aha" feed | Legibility of the mind's most interesting moments; the surprise term made visible | surprise (PRD-01 F1.6); notebook | 1+4 | S | M |

## Wave 4p — 2026-07-13 iter 49 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 204 | **Keyboard-driven evidence navigation** — full keyboard traversal of conclusion→evidence→source→artifact for power users | Accessibility basic + speed for a reviewer working through many claims (SPEC acceptance check) | SCIENTIFIC_WORKBENCH_SPEC a11y; evidence tree | 4 | S | M |
| 205 | **Live collaboration presence** — when multiple humans view a persona, show who's reviewing what (shared-doc style) | The lab as a shared workspace; coordination for a multi-human review team | api sessions; inbox; SSE stream | 4 | M | M |
| 206 | **Export beliefs to reference managers** — export beliefs + citations to Zotero/BibTeX so a scientist's own library stays in sync | Meets scientists in their existing tools; frictionless interop | provenance sources; deliverables; PROV-O (#109) | 4 | S | M |

## Wave 4q — 2026-07-13 iter 50 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 207 | **Model-version drift monitor** — track whether swapping the underlying model changes Persona's beliefs/extractions; flag model-dependence | Reproducibility under model change — a belief shouldn't depend on which Claude version read it | config MODEL_*; extraction; verified ledger | 1 | M | M |
| 208 | **Determinism audit** — verify forensic + extraction paths are deterministic (temp 0 where needed) so results replay exactly | The replayability guarantee only holds if the paths are actually deterministic | forensics; sandbox; sessions replay | 3 | S | M |
| 209 | **Prompt-version pinning** — pin + version every system prompt so a belief traces to the exact prompt that produced it | Reproducibility of *reasoning*, not just data — the prompt is part of the provenance | agents prompts; provenance; sessions | 1 | S | M |

## Wave 4r — 2026-07-13 iter 51 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 210 | **Adversarial claim-challenge set** — an internal set of hard/tricky claims (numerical, multi-hop, figure-based) that continuously stresses the membrane | Standing stress test beyond public benchmarks; catches regressions in the hardest cases | eval oracles (FC-7); SciClaimHunt/SciVer (#backlog) | 4 | M | M |
| 211 | **Human-agreement calibration study** — periodically measure how often Persona's verdicts agree with expert humans on a sample | Keeps the auto-judge honest — validates it against ground truth (PaperBench discipline) | eval; conflict_reviews gold; auditor | 4 | M | H |
| 212 | **Conclusion regression suite** — CI that re-verifies every past verified conclusion still holds under current code/evidence | Catches silent regressions in the belief-state as code + evidence evolve | verified ledger; sessions replay; revisit | 4 | M | M |

## Wave 4s — 2026-07-13 iter 52 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 213 | **Consensus-strength meter** — a graded consensus score per claim (how much of the field agrees) with the distribution shown, not binary support/contradict | Nuance beyond "supported/contested"; shows the shape of agreement | citation_support_ratio (FC-3); independence | 3 | M | M |
| 214 | **Minority-position tracker** — track credible minority positions (well-evidenced but non-consensus) so they aren't buried by the majority | History shows minorities are sometimes right — the system shouldn't only amplify consensus | membrane; dissent (PRD-01 F1.5); provenance | 2 | M | M |
| 215 | **Disagreement-root attribution** — when experts disagree, attribute the root cause (different populations, methods, definitions) rather than leaving it unexplained | Turns a bare contradiction into an actionable "here's *why* they differ"; extends conflict typing | conflict typing (FC-10); PICO/qualifiers | 3 | M | H |

## Wave 4t — 2026-07-13 iter 53 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 216 | **Investigation checkpoint/resume** — investigations checkpoint state so a crash mid-program resumes exactly, not restarts | The queue crash-resumes tasks; extend that resilience to the investigation program level | queue crash-resume; investigation.json | 1 | M | M |
| 217 | **Partial-result salvage** — when an investigation fails late, salvage validated intermediate beliefs instead of discarding the whole run | Never waste paid work; the analyst already salvages truncated runs — generalize it | analyst salvage; investigation finalize | 1 | S | M |
| 218 | **Graceful model-fallback chain** — if the primary model is unavailable/rate-limited, fall back to a cheaper model with a logged provenance note (not silent) | Resilience without hidden quality changes — the fallback is visible in provenance | config MODEL_*; budget; provenance | 1 | S | M |

## Wave 4u — 2026-07-13 iter 54 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 219 | **Live-preprint monitoring** — watch bioRxiv/medRxiv feeds for new preprints in a persona's interest and ingest same-day | Keeps the researcher genuinely current — the always-on premise made real-time | ingest sources; biorxiv/medrxiv DB skills | 1 | M | M |
| 220 | **Load-bearer retraction alert** — highest-priority alert: a paper a load-bearing belief depends on gets retracted → immediate human escalation | The single most consequential event for the belief-state; fuses retraction + load-bearing | retraction watcher (FC-19); load-bearing (FC-4) | 2+4 | S | H |
| 221 | **Conference-abstract ingestion** — ingest conference abstracts (often ahead of publication) as early, weak-typed signal | Earliest possible signal on a moving front; typed honestly as preliminary | ingest; provenance typing | 1 | S | M |

## Wave 4v — 2026-07-13 iter 55 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 222 | **Automated sensitivity analysis** — for a computational result, auto-run leave-one-out + alternative-spec checks and report robustness | Generalizes the E12b GEO sensitivity precedent — every result ships with its own robustness envelope | analyst; E12b sensitivity; forensics | 3 | M | H |
| 223 | **Bayesian posterior per belief** — maintain a proper posterior updated via Bayes as evidence arrives, not a heuristic confidence | Rigorous, defensible confidence a statistician trusts; replaces ad-hoc scores | calibrate (FC-5); pymc; independence | 2 | L | M |
| 224 | **Units-aware numerical-claim extraction** — extract quantitative claims WITH units + CIs as structured data | Enables downstream computation (meta-analysis, unit/consistency checks) from clean numbers | extract; effect-size harmonizer (#22); pint | 1 | M | M |

## Wave 4w — 2026-07-13 iter 56 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 225 | **Extraction-confidence gating** — attach a confidence to each extracted claim; route low-confidence extractions to a re-read queue | Catches the misread-claim failure mode cheaply before it reaches the membrane | extract; two-reader (PRD-01 F1.3); verbatim gate | 1 | S | M |
| 226 | **Figure/table-text extraction** — extract claims from figures/tables/images via vision, not just body text | Numbers-in-figures is a huge evidence source current text extraction misses entirely | fetch/PyMuPDF; vision; cross-modal (#92) | 1 | L | M |
| 227 | **Multilingual ingestion** — read non-English papers (translate for extraction, preserve original spans) | Covers evidence English-only tools miss; preserves exact-span provenance in the source language | ingest; provenance-preserving translation (#146) | 1 | M | M |

## Wave 4x — 2026-07-13 iter 57 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 228 | **Synthesis-hallucination hard gate** — every sentence in a synthesis note must map to a source quote (checker exists; make it a hard admission gate) | Turns the existing support-rate check into a real gate — no unsupported sentence ships | synthesis/checker.py; support_rate | 3 | S | H |
| 229 | **Contradiction-aware synthesis** — a synthesis explicitly surfaces where sources disagree within the note, not just the majority view | Honest synthesis shows the dissent; extends "unresolved dissents" section to inline | synthesizer; contradictions; fieldmap | 3 | M | M |
| 230 | **Evidence-density heatmap** — show which parts of a synthesis are well-evidenced vs thinly-supported (heatmap over the prose) | The reader sees exactly where to trust and where to dig; legibility of synthesis quality | checker support_rate; deliverables | 3+4 | M | M |

## Wave 4y — 2026-07-13 iter 58 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 231 | **Mechanistic pathway assembly** — assemble a pathway (A→B→C) from individual claims, checking each link is evidenced; surface the weakest link | Mechanism is where biology lives; shows exactly which step of a story is unsupported | dependency edges (FC-3); load-bearing | 3 | M | H |
| 232 | **Dose-response consistency check** — for dose-dependent claims, check reported dose-response is monotonic/consistent across studies | A classic causality signal (Bradford Hill) the auditor doesn't yet check | forensics; numerical extraction (#224) | 3 | M | M |
| 233 | **Confounder checklist per causal claim** — for each causal claim, list plausible confounders + whether the study addressed them | Structures the "is it really causal?" question; pairs with the causal-strength gate | causal gate (FC-10); methods critique (#175) | 3 | M | M |

## Wave 4z — 2026-07-13 iter 59 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 234 | **Hierarchical memory tiers** — hot (active) / warm (recent) / cold (archived) beliefs with automatic migration | Keeps the active set small + fast as the graph scales; the "self small, scale in swarm" principle | kg store; GC (#160); consolidation (FC-11) | 2 | M | M |
| 235 | **Query-intent retrieval routing** — route a query to the right strategy (lexical / semantic / graph-traversal) by intent | E03a proved no single retrieval arm wins — route by query type instead of one global choice | RQ-E03a; vectors; graph search | 2 | M | M |
| 236 | **Recency-decayed retrieval** — down-weight stale evidence in retrieval so current understanding surfaces, tunable per field | Fast-moving fields shouldn't retrieve 2015 as if it were today; pairs with evidence half-life (#94) | vectors; history; field half-life | 2 | S | M |

## Wave 5a — 2026-07-13 iter 60 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 237 | **Work-stealing across investigations** — idle workers steal tasks from overloaded investigations, balancing load dynamically | Better utilization of the bounded swarm; faster wall-clock on parallel programs | queue lease; investigations; scheduler | 1 | M | M |
| 238 | **Reducer-bottleneck detection** — detect when a synthesis/reducer step is the bottleneck and shard/parallelize it | E07a warned reducers bottleneck at scale — instrument + fix it | supervisor; consolidator; swarm physics | 1 | M | M |
| 239 | **Correlated-error detection across readers** — flag when multiple readers make the same error (shared model bias), tightening the membrane | The poisoning defense generalized to model bias, not just adversarial sources | membrane poisoning_signals; two-reader | 1+2 | M | M |

## Wave 5b — 2026-07-13 iter 61 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 240 | **Executable notebook deliverable** — ship a report as a runnable notebook (code + prose + data) so a reader re-runs every number | The ultimate reproducible artifact; extends the RO-Crate/session work to a live doc | sessions; sandbox; RO-Crate (PRD-04 F4.10) | 3+4 | M | M |
| 241 | **Interactive dependency-graph embed** — embed the live load-bearing graph in a shared report so readers explore it themselves | The flagship view made portable/shareable outside the app | flagship (PRD-04 F4.1); engine (FC-4) | 4 | M | M |
| 242 | **Version-diffed re-releases** — when a conclusion updates, auto-publish a versioned re-release with a changelog of what changed + why | A conclusion becomes a living, versioned object — living systematic-review discipline | deliverables; belief history; note-diff (PRD-03 F3.11) | 3+4 | S | M |

## Wave 5c — 2026-07-13 iter 62 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 243 | **Dual-use / harm screening** — flag research directions with clear dual-use or harm potential and route to human review before pursuing | Responsible autonomy — the acting loop shouldn't pursue harmful directions unbidden | discover routing; autonomy ladder (#189) | 1+2 | M | M |
| 244 | **Bias-in-evidence audit** — check whether a belief's evidence over-represents one population/demographic; flag generalizability limits | Catches the external-validity failure (pairs with All-of-Us diversity check); honest scope | provenance; population qualifiers; molecular gates | 3 | M | M |
| 245 | **Consent-aware data handling** — ensure any human-data reanalysis respects the dataset's consent/usage terms; block non-compliant use | Ethical + legal guardrail on the executable loop touching human data | datasets allowlist; sandbox; data terms | 3 | S | M |

## Wave 5d — 2026-07-13 iter 63 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 246 | **Funnel-plot / Egger publication-bias test** — for a set of studies on an effect, detect small-study effects (publication bias) | A standard meta-research check the auditor lacks; quantifies the file-drawer | meta-analysis (PRD-10); forensics; dark-lit | 3 | M | H |
| 247 | **Trim-and-fill correction** — estimate + correct for missing null studies in a meta-analysis (Duval–Tweedie) | Turns detected bias into a corrected effect estimate — actionable, not just a flag | meta-analysis (PRD-10 F10.2) | 3 | M | M |
| 248 | **Outcome-switching detector** — flag when a trial's published primary outcome differs from its pre-registered one | A documented, high-yield integrity failure (COMPare-style); pairs with prereg awareness (#23) | ClinicalTrials; prereg; causal gate | 3 | M | M |

## Wave 5e — 2026-07-13 iter 64 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 249 | **Batch-API smart routing** — route non-urgent bulk reads to the ~50%-cheaper Batch API, live calls for urgent | More reading per dollar; the batch reader exists, add the routing logic | reading/batch.py; budget; scheduler | 1 | S | M |
| 250 | **Cross-persona extraction cache** — share paper extractions across personas (same DOI → reuse), avoiding redundant reads | The lab reads each paper once, not once-per-persona; big cost win at scale | ingest cache; extraction store; manager | 1 | S | M |
| 251 | **Speculative citation pre-fetch** — pre-fetch likely-next papers (citations of high-value reads) before requested, hiding latency | Faster investigations; the swarm stays ahead of demand | reader; citation graph; queue | 1 | M | M |

## Wave 5f — 2026-07-13 iter 65 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 252 | **Attention-over-time heatmap** — show how the persona's attention shifted across topics over days/weeks (a time-lapse of focus) | Makes the researcher's evolving agenda legible longitudinally — you see the mind's drift | interests weights over time; events | 4 | M | M |
| 253 | **Auto research diary** — a first-person daily narrative the persona writes reflecting on progress + frustrations | The living-notebook as reflective prose — the "mind at work" made personal | notebook; deliberate; error log | 1 | S | M |
| 254 | **Human-baseline benchmark** — measure Persona's synthesis vs a human expert's on the same question (blinded) | The honest "is it actually good?" test; the differentiator's proof | eval; human-agreement study (#211) | 4 | M | M |

## Wave 5g — 2026-07-13 iter 66 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 255 | **Ontology-consistency check** — verify a claim's entities + relations are valid against a domain ontology (gene/disease terms exist + relate sensibly) | Catches malformed/nonsensical claims before admission; grounds entities in curated vocabularies | canon; MONDO/HPO/GO; membrane | 2 | M | M |
| 256 | **Pathway-database corroboration** — cross-check a mechanistic claim against Reactome/KEGG for structured support | A curated, orthogonal corroboration channel for mechanism claims | science clients; Reactome/KEGG skills; membrane | 3 | M | M |
| 257 | **Target–disease triangulation** — for a target claim, triangulate Open Targets + literature + genetics, flagging where they disagree | Three independent evidence types agreeing (or not) is the strongest signal; multi-modal anchor (#122) | Open Targets; OT-Genetics (PRD-08); crosscheck | 3 | M | H |

## Wave 5h — 2026-07-13 iter 67 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 258 | **Time-bounded claim windows** — explicit valid-from/valid-to on time-bounded claims ("as of 2020"); auto-flag when superseded | Temporal validity is a distinct failure mode a longitudinal researcher must track | temporal confidence (PRD-02 F2.7); bi-temporal store | 2 | M | M |
| 259 | **Effect-drift / decline-effect detection** — detect when an effect size drifts systematically across publication years (winner's curse) | A known replication-crisis signature; flags initially-large effects that shrink | trajectory; effect sizes over time; forensics | 3 | M | M |
| 260 | **Replication-timeline tracker** — per foundational claim, a timeline of replication attempts + outcomes | Shows the replication trajectory at a glance — is this holding up or crumbling? | verified ledger; trajectory; provenance history | 3+4 | M | M |

## Wave 5i — 2026-07-13 iter 68 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 261 | **Sandbox resource auto-tuning** — auto-tune CPU/mem/time caps per task type from observed usage; prevent OOM/timeout waste | Fewer wasted paid runs (recall the FastEmbed OOM lesson); cheaper compute loop | tools/sandbox.py caps; budget; task history | 3 | S | M |
| 262 | **Test-result caching by hash** — cache reanalysis results keyed by (code hash, data hash) so identical tests don't re-run | Free reproducibility + big cost savings on repeated verification | sessions artifact hashes; sandbox | 3 | S | M |
| 263 | **R/Julia sandbox support** — support R/Julia in the sandbox, not just Python, for methods native to those ecosystems (metafor, Stan) | Many gold-standard stats methods live in R — unlocks them for reanalysis | sandbox Dockerfile; science tools | 3 | M | M |

## Wave 5j — 2026-07-13 iter 69 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 264 | **"What evidence would flip this" per recommendation** — for a recommendation, state the specific new evidence that would reverse it | Decision support with a built-in falsification condition — actionable + honest | value_queue; red-team (PRD-09); falsification checklist (#142) | 3+4 | M | M |
| 265 | **Hypothesis-portfolio tracking** — track multiple competing hypotheses for a question in parallel with their evidence, not committing early | Avoids premature convergence; keeps the alternatives alive with their support | kg; discover; minority positions (#214) | 2 | M | M |
| 266 | **Recommendation pre-mortem** — before finalizing a recommendation, generate a pre-mortem ("assume wrong in 2 years — why?") | Structured humility before high-stakes advice; extends red-team to recommendations | red-team; obsolescence forecast (#180) | 3 | S | M |

## Wave 5k — 2026-07-13 iter 70 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 267 | **Graph-motif detection** — detect recurring structural motifs (a hub many depend on, a mutual-support cycle) that signal risk or importance | Structure reveals fragility patterns simple scores miss; complements load-bearing | dependency graph (FC-4); networkx | 3 | M | M |
| 268 | **Circular-reasoning detector** — flag when a set of claims mutually support each other with no external grounding | Citation circularity manufactures false confidence — a real, hidden failure | dependency edges; independence; membrane | 2 | M | H |
| 269 | **Bridge-claim identification** — find claims connecting otherwise-separate subfields (structural bridges), high-value to verify | Bridges are load-bearing across fields — if wrong, two literatures suffer; feeds value queue | dependency graph; cross-field (PRD-21); betweenness | 3 | M | M |

## Wave 5l — 2026-07-13 iter 71 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 270 | **Specialized agent roster** — a library of specialized reader/analyst types (statistician, geneticist, clinician, methodologist) matched to paper/claim type | Heterogeneous roles beat homogeneous swarms (research) — the right specialist reads the right paper | agents/*; heterogeneous teams (PRD-01); director | 1 | M | H |
| 271 | **Dynamic role assignment** — the Director matches agent specialty to each sub-question dynamically | Turns the roster into a live matching engine; the "breadth of teamwork" made adaptive | director; investigation DAG (PRD-01 F1.1) | 1 | M | M |
| 272 | **Bounded cross-agent sharing** — a membrane-gated channel for agents to share intermediate findings within one investigation, capped (E07a: dense sharing harmful) | Just enough coordination to compound, not so much it collapses to shared bias | E07a swarm physics; membrane; consensus (PRD-01 F1.5) | 1 | M | M |

## Wave 5m — 2026-07-13 iter 72 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 273 | **Negation & hedge handling in extraction** — correctly parse negation ("no effect") and hedges ("may suggest") so claims aren't extracted with wrong polarity/certainty | The exact failure behind the microglia sign-flip; a root-cause extraction fix | extract; RQ-E01b enriched extractor; polarity | 1 | M | H |
| 274 | **Quantifier-scope disambiguation** — handle some/all/most scope so a universal isn't extracted from a particular | Over-generalization at extraction is a silent corruption source; exact-span-grounded | extract; qualifiers; membrane | 1 | M | M |
| 275 | **Coreference resolution** — resolve pronouns/references so a claim's subject is the real entity, not "it" | Prevents misattributed claims from a single misresolved reference | extract; canon; entity resolution | 1 | M | M |

## Wave 5n — 2026-07-13 iter 73 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 276 | **Wikidata/ontology entity linking** — link canonical entities to stable external IDs (Wikidata, Ensembl, MONDO) for interop + disambiguation | Entities become globally addressable — dedup, interop, and unambiguous identity | canon; ontology check (#255); Wikidata | 2 | S | M |
| 277 | **External-KG contradiction check** — cross-check a belief against an established external KG (Open Targets, SemMedDB) and flag disagreements | Another orthogonal check: does the curated consensus KG agree with what we read? | SemMedDB (PRD-23); Open Targets; membrane | 2 | M | M |
| 278 | **KG-embedding link prediction** — use KG embeddings to predict plausible missing links (a learned complement to structural negative-space) | A second, learned method for gap discovery; ensemble with #115 for robustness | torch-geometric; dependency graph; negspace (PRD-30) | 3 | M | M |

## Wave 5o — 2026-07-13 iter 74 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 279 | **Uncertainty propagation through derivations** — propagate error bars through multi-step derivations so a conclusion's uncertainty reflects all inputs | A conclusion 3 steps deep shouldn't look as certain as its shakiest input | reason/prove; sympy; evidence chains | 3 | M | M |
| 280 | **Monte-Carlo sensitivity on key results** — run MC over uncertain inputs to get a distribution on a conclusion, not a point | Honest uncertainty for computational results; extends the E12b sensitivity habit | sandbox; analyst; sensitivity (#222) | 3 | M | M |
| 281 | **Interval arithmetic for reported ranges** — use interval arithmetic when claims give ranges, keeping downstream bounds honest | Ranges stay ranges through computation — no false precision | numerical extraction (#224); sandbox | 3 | S | M |

## Wave 5p — 2026-07-13 iter 75 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 282 | **Guided closed-loop walkthrough** — an animated replay of one contradiction→test→belief-update loop for a new user (the money-shot, built in) | The single best way to convey the acting loop; onboarding + demo in one | notebook replay (#127); sessions; flagship | 4 | M | M |
| 283 | **Belief-graph search-as-you-type** — instant filtering of the graph as the human types | Fast navigation of a large graph — a small polish with big usability payoff | graph search API; index.html | 4 | S | M |
| 284 | **Print/PDF-friendly layout** — a clean print stylesheet so any surface exports to a shareable PDF | Frictionless sharing with collaborators who live outside the app | index.html CSS; deliverables | 4 | S | M |

## Wave 5q — 2026-07-13 iter 76 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 285 | **Auto limitations section** — every deliverable includes a specific, evidence-derived limitations section (not boilerplate) | Honest scoping baked into every output; the caveats travel with the claim | deliverables; evidence gaps; method critique (#175) | 3 | S | M |
| 286 | **Scope-creep detector** — flag when a conclusion generalizes beyond its evidence's population/conditions | Catches over-generalization (the GEO same-donor lesson) at the conclusion boundary | qualifiers/PICO; causal gate (FC-10); membrane | 2 | M | H |
| 287 | **"Known unknowns" register** — an explicit, maintained list of questions the persona knows it can't currently answer + why | Honesty about the edges of competence; a trust signal + a research agenda | open_questions; error log; value queue | 1 | S | M |

## Wave 5r — 2026-07-13 iter 77 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 288 | **Universal environment capture** — capture full env (packages, versions, seeds, container digest) with every computational result | Exact replay needs the environment pinned — make it universal, not per-feature | sandbox image_digest; sessions; E12a | 3 | S | M |
| 289 | **Lockfile-pinned reproducibility** — pin exact dependency versions so a reanalysis is bit-reproducible years later | Long-horizon reproducibility — a result replays the same in 2030 | sandbox Dockerfile; pyproject; lockfile | 3 | M | M |
| 290 | **Reproducibility CI gate** — a CI job that re-runs every replayable session on each code change and fails if a number drifts | Regression protection for the whole evidence base; catches silent breakage | sessions verify; regression suite (#212) | 4 | M | M |

## Wave 5s — 2026-07-13 iter 78 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 291 | **Survival-analysis reanalysis** — for time-to-event clinical claims, run Kaplan–Meier / Cox reanalysis from public data | Extends the executable-test loop to a whole class of clinical claims it can't touch today | sandbox; scikit-survival; datasets | 3 | M | M |
| 292 | **Field-metric forecasting** — forecast a field's trajectory metric (support velocity) to anticipate where it's heading | The "predict collapse" vision made quantitative (BUILD_PLAN §3.1) | trajectory; timesfm; statsmodels | 3 | M | M |
| 293 | **Changepoint detection on evidence streams** — detect abrupt shifts in a target's evidence stream (paradigm shift or scandal) | Surfaces inflections early; the silence/dead-science detector's active twin | trajectory; dark-lit (PRD-03 F3.5); ruptures | 3 | M | M |

## Wave 5t — 2026-07-13 iter 79 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 294 | **MCP tool exposure** — expose the belief graph + auditor as MCP tools so other agents/apps can query Persona | Persona becomes infrastructure other systems build on — the compounding-value play | api; knowledge.ask_graph; MCP | 4 | M | M |
| 295 | **Tool-output sanity verification** — schema + range check every external tool result before trusting it | External data can be wrong/malformed; fail-loud at the tool boundary | science.py; tool-grounded verifier (PRD-01) | 3 | S | M |
| 296 | **Runtime tool discovery** — let the analyst discover + use new science APIs at runtime within an allowlist, not a fixed set | Extensibility without a code change per source; bounded by the allowlist for safety | science.REGISTRY; datasets allowlist; analyst | 3 | M | M |

## Wave 5u — 2026-07-13 iter 80 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 297 | **Single-cell / omics reanalysis** — reanalyze scRNA-seq / omics data (scanpy/scvi) for a cell-type or expression claim | Extends the executable loop to the dominant modern data modality in biology | sandbox; scanpy/scvi-tools; GEO resolution (PRD-07-ish) | 3 | M | H |
| 298 | **Imaging-data reanalysis** — reanalyze imaging (histology/microscopy) for a quantitative claim via a vision pipeline | Opens image-based evidence to computational verification (pairs with figure-integrity) | sandbox; histolab/pathml; datasets | 3 | L | M |
| 299 | **EHR/OMOP cohort reanalysis** — reanalyze a claim against a public EHR/OMOP cohort where available | Real-world clinical verification beyond trials/literature; ties to LEGEND (PRD-18) | OHDSI/OMOP; datasets; sandbox | 3 | M | M |

## Wave 5v — 2026-07-13 iter 81 (fresh, direct — crosses #300)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 300 | **Self-discovered forensic checks** — Persona proposes NEW forensic checks (beyond the built-in set) by mining its own error patterns, validated before adoption | A self-improving auditor — the method-set grows from evidence, gated by validation | forensics; error log; RQ-gated adoption | 3 | L | H |
| 301 | **Method-effectiveness tracking** — track which verification methods actually caught real errors; deprecate ineffective ones | Stops spending on checks that never fire; focuses rigor where it pays | verified/revisit; forensics flags; cost-yield | 3+4 | M | M |
| 302 | **Self-generated eval tasks** — Persona generates its own held-out eval tasks from its corpus to test itself continuously | Continuous self-assessment without waiting for external benchmarks | eval (FC-7); corpus; benchmarks | 4 | M | M |

## Wave 5w — 2026-07-13 iter 82 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 303 | **Live draft feedback** — as a human writes, Persona gives grounded feedback (unsupported claim, missing citation, contradicting evidence) | Co-researcher in the writing loop, not just after; daily-useful for a working scientist | mywork ingest; crosscheck; blocklist (FC-18) | 3+4 | M | M |
| 304 | **Reviewer-2 simulation** — simulate a tough peer reviewer on a manuscript, surfacing likely objections before submission | Catches the weaknesses reviewers will — before rejection; extends red-team to human work | critic; red-team (PRD-09); methods critique | 3 | M | M |
| 305 | **Hypothesis sparring partner** — human proposes a hypothesis; Persona stress-tests it with support + disconfirming evidence in dialogue | Interactive falsification — the researcher as an intellectual sparring partner | converse; crosscheck; falsification checklist (#142) | 3+4 | M | M |

## Wave 5x — 2026-07-13 iter 83 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 306 | **Formal claim specification** — express a claim as a formal/logical statement where possible, enabling machine-checking of consistency | Extends Lean/sympy proving from math to structured empirical claims | reason/prove; Aristotle Lean; sympy | 3 | M | M |
| 307 | **Belief-set consistency check** — periodically logic/SAT-check the belief set for contradictions the pairwise graph misses | Catches multi-way inconsistencies (A,B,C jointly impossible) beyond pairwise sign collisions | kg; membrane; feasibility gate (PRD-02 F2.4) | 2 | M | M |
| 308 | **Proof-obligation tracking** — for each derived belief, track what remains proven vs assumed | Makes the gap between "shown" and "assumed" explicit per belief; a to-do for rigor | evidence chains; provenance tiers; verified | 3 | S | M |

## Wave 5y — 2026-07-13 iter 84 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 309 | **Impact-first literature triage** — prioritize which new papers to read by expected impact on current beliefs, not recency | Reads what matters most first; surprise + load-bearing weighted | surprise queue (PRD-01 F1.6); load-bearing (FC-4) | 1 | M | M |
| 310 | **Deadline-aware planning** — when a human sets a deadline, plan the investigation to deliver best-available by then | Meets real-world time constraints; anytime-answer with honest confidence | investigation; budget; value queue | 1 | M | M |
| 311 | **Diminishing-returns stop rule** — stop reading a question when marginal validated evidence falls below threshold | E07a's "stop when marginal evidence < cost" operationalized — no infinite reading | swarm physics (RQ-E07a); budget; membrane yield | 1 | S | M |

## Wave 5z — 2026-07-13 iter 85 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 312 | **Source-integrity hashing at ingest** — hash every fetched paper/dataset at ingest so downstream tampering is detectable | Provenance integrity from the first byte; extends session hashing to raw sources | ingest fetch; sessions hashing; provenance | 1 | S | M |
| 313 | **Duplicate-source merge** — detect the "same" paper arriving via multiple sources (preprint + published) and merge, avoiding double-counting | Protects independence counts from inflation by re-publication | sources dedup (DOI); independence; membrane | 1 | S | M |
| 314 | **Predatory-venue flag** — flag claims sourced only from predatory/low-quality venues as weak | A known low-quality signal the trust ledger should surface | venue metadata; audit trust ledger; Beall-style lists | 3 | M | M |

## Wave 6a — 2026-07-13 iter 86 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 315 | **Table extraction + stat verification** — extract data tables from papers and verify reported summary stats match the table | Catches text-vs-table mismatches; extends forensics to tabular data | fetch; forensics; figure/table extraction (#226) | 3 | M | M |
| 316 | **Percentage/proportion sanity check** — verify reported percentages sum correctly and match Ns | A cheap, common-error deterministic check for the forensic bank | forensics; numerical extraction (#224) | 3 | S | M |
| 317 | **CI ↔ p-value coherence check** — verify a reported CI and p-value are mutually consistent (95% CI excludes null ⟺ p<.05) | Another exact, code-run internal-consistency check (statcheck family) | forensics.statcheck; extraction | 3 | S | M |

## Wave 6b — 2026-07-13 iter 87 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 318 | **Concept-dependency curriculum** — order a field's concepts by dependency into a learning path for a newcomer | The dependency graph doubles as a teaching tool — foundational before advanced | dependency graph (FC-4); knowledge ladder | 3+4 | M | M |
| 319 | **Fidelity-checked analogies** — generate grounded analogies to explain a mechanism, checked against the evidence for fidelity | Explanation that aids understanding without distorting; caveat-preserving | knowledge; checker; explanation-faithfulness (#134) | 3 | S | M |
| 320 | **Socratic tutoring mode** — teach a concept by asking guiding questions, using the belief graph | Deeper learning than lecturing; the researcher as a tutor grounded in real evidence | knowledge; converse; belief graph | 4 | M | M |

## Wave 6c — 2026-07-13 iter 88 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 321 | **Failed-investigation gallery** — a browsable archive of investigations that didn't pan out + why | The error log as a first-class surface — the credibility signal (times it was wrong) | error log; investigations; sessions (invalidated) | 4 | S | M |
| 322 | **Self-retraction protocol** — a clean process to retract a past conclusion with a public correction notice | A researcher that visibly corrects itself; practices what it audits in others | verified/revisit; version-diffed re-release (#242) | 2+4 | S | M |
| 323 | **Membrane near-miss log** — log cases where a wrong belief almost passed the membrane but was caught | Study the membrane's close calls to tune it; the discipline made observable | membrane; gate_decisions ledger; poisoning_signals | 2 | S | M |

## Wave 6d — 2026-07-13 iter 89 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 324 | **Prioritized-replay buffer** — a surprise-ranked buffer of high-value claims to re-examine (SuRe signal, no weight training) | Focuses re-verification on the most surprising/important; the surprise thesis realized | surprise (PRD-01 F1.6); revisit; SuRe | 2 | M | M |
| 325 | **Importance-weighted consolidation** — consolidate load-bearing beliefs more often than peripheral ones | Spends consolidation effort where the belief-state's risk concentrates | load-bearing (FC-4); sleep-consolidation (FC-11) | 2 | S | M |
| 326 | **Memory-interference detection** — detect when a new belief interferes with an existing one and resolve at consolidation | Prevents proactive interference corrupting the core; sleep-consolidation's job | consolidation (FC-11); membrane; contradictions | 2 | M | M |

## Wave 6e — 2026-07-13 iter 90 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 327 | **Prospective belief validation** — register a prediction, then check it against reality when the future arrives (true forward validation) | The gold-standard honesty test — not retrospective; extends the prediction ledger (FC-17) | prediction ledger (FC-17); trajectory | 2+4 | M | H |
| 328 | **Belief→outcome tracking** — for beliefs informing a real decision, track the eventual real-world outcome as ground truth | Closes the loop to reality — the ultimate calibration signal | prediction ledger; human decisions; outcomes | 4 | M | M |
| 329 | **Per-domain calibration breakdown** — report calibration separately per subfield (well-calibrated in genetics, less in psychology) | Honest about where it's trustworthy vs not; per-domain reliability | calibration panel (PRD-15); field ids | 4 | S | M |

## Wave 6f — 2026-07-13 iter 91 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 330 | **Stable spatial belief-map** — a persistent subway-map-style layout so the human builds a mental model of the field's geography | Spatial memory aids navigation; the field becomes a place you know | graph UI; communities; layout | 4 | M | M |
| 331 | **Zoomable semantic map** — zoom field → subfield → claim with detail-on-demand | Handles scale gracefully; the flagship view at every altitude | fieldmap; dependency graph (FC-4) | 4 | M | M |
| 332 | **Evidence-flow animation** — animate how evidence flows into a conclusion when a node is selected | Motion-on-state-change made pedagogical; shows the grounding physically | evidence tree; motion (SPEC) | 4 | S | M |

## Wave 6g — 2026-07-13 iter 92 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 333 | **Cost-per-validated-belief dashboard** — the unit economics: $ per membrane-admitted belief, over time | The AstaBench cost-adjusted discipline as a live self-metric; sustainability visible | budget cost-events; membrane yield; scorecard | 4 | S | M |
| 334 | **Free-tier-first data strategy** — prefer free/open sources + cached results, escalate to paid only when needed | Cheaper operation without quality loss; the cache-aggressively principle | ingest cache; datasets allowlist; budget | 1 | S | M |
| 335 | **Compute-budget forecasting** — forecast the compute/$ to answer a question before committing, so the human approves knowingly | No surprise bills; the Ask/Investigate/Build budget-preview made predictive | budget; value queue; investigation planner | 1+4 | M | M |

## Wave 6h — 2026-07-13 iter 93 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 336 | **Testability classifier** — classify each open question by how testable it is now (public data / cheap assay / wet lab / not testable) and route accordingly | The VoI÷cost engine's routing brain — decides what Persona can test vs must escalate | value_queue (FC-4); dataset scout; discover | 3 | M | H |
| 337 | **Dataset-gap identification** — identify the specific dataset that, if it existed, would resolve the most contradictions | A data-collection recommendation no tool offers — "collect this to unblock the field" | value queue; contradictions; dependency mass | 3 | M | M |
| 338 | **Assay-to-claim matcher** — match a proposed cheap assay to the claims it would discriminate, optimizing a wet-lab hour | Makes the human's scarce bench time maximally informative | value queue; discriminating-test (dossier) | 3 | M | M |

## Wave 6i — 2026-07-13 iter 94 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 339 | **Multiverse analysis** — run a conclusion across many reasonable analytic specs (garden of forking paths); report robustness | The strongest robustness test — does the finding survive analyst choices? | sandbox; sensitivity (#222); E12b precedent | 3 | M | H |
| 340 | **Specification-curve display** — visualize a result across all reasonable specs | Makes analytic robustness legible at a glance; a compelling honesty artifact | multiverse (#339); deliverables; charts | 3+4 | M | M |
| 341 | **Analytic-flexibility flag** — flag results where small analytic choices flip the conclusion (fragile to researcher DoF) | Surfaces p-hacking-adjacent fragility the single-spec auditor misses | multiverse; forensics; membrane | 3 | M | M |

## Wave 6j — 2026-07-13 iter 95 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 342 | **PharmGKB pharmacogenomics cross-check** — for a drug–gene claim, cross-check PharmGKB evidence level | Curated pharmacogenomic evidence tiers — an orthogonal, authoritative check | science clients; ClinPGx skill; membrane | 3 | M | M |
| 343 | **ClinVar variant-pathogenicity check** — for a variant–disease claim, cross-check ClinVar pathogenicity + review status | Curated clinical-genetics ground truth for variant claims | ClinVar skill; molecular gates (PRD-08) | 2 | M | M |
| 344 | **COSMIC cancer-mutation corroboration** — for a cancer-driver claim, cross-check COSMIC mutation frequency | Orthogonal corroboration for oncology driver claims | COSMIC skill; science clients; crosscheck | 3 | M | M |

## Wave 6k — 2026-07-13 iter 96 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 345 | **Reasoning-trace replay** — replay the exact steps (prompts, tool calls, decisions) that produced a belief | Reproducibility of *reasoning*, not just data; the session log made re-runnable | sessions event log; prompt pinning (#209) | 4 | M | M |
| 346 | **Decision-point annotation** — annotate each key decision in a trace with the alternative it rejected + why | Shows the path not taken — the reasoning's counterfactuals, legible | investigation worklog; notebook | 1+4 | S | M |
| 347 | **Trace-diff between runs** — diff two runs on the same question to see where reasoning diverged | Debugging + robustness — why did two runs reach different conclusions? | sessions; determinism audit (#208) | 4 | M | M |

## Wave 6l — 2026-07-13 iter 97 (fresh, direct — crosses #350)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 348 | **Analogical hypothesis generation** — map a known mechanism in one system to an under-studied analog (structured analogy) | Generative discovery, not just gap-filling; extends cross-field translation to hypotheses | cross-field (PRD-21); discover; negspace (PRD-30) | 3 | M | H |
| 349 | **Contradiction→falsifiable sub-hypothesis** — turn each open contradiction into a specific falsifiable sub-hypothesis automatically | Sharpens the acting loop's hypothesizer; every tension becomes a testable question | discover; conflicts (FC-10); analyst | 1 | S | M |
| 350 | **Hypothesis-novelty scoring** — score a generated hypothesis for novelty (not already studied) before pursuing | Avoids rediscovering known results; spends effort on genuine unknowns | negspace (PRD-30); literature check; discover | 3 | M | M |

## Wave 6m — 2026-07-13 iter 98 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 351 | **Attention-budget-aware surfacing** — surface only the N most important things needing the human, hide the rest | Respects the human's scarce attention; only what needs judgment reaches them | EIG ranking (FC-20); handoff inbox | 4 | S | M |
| 352 | **Progressive complexity disclosure** — headline first, detail on demand | The legibility layer scales to novices + experts without overwhelming either | knowledge ladder; UI | 4 | S | M |
| 353 | **Notification batching + digest** — batch low-priority alerts into a digest, interrupt only for high-priority | Signal without noise; the always-on colleague that doesn't spam | alerts (#15); load-bearer alert (#220) | 4 | S | M |

## Wave 6n — 2026-07-13 iter 99 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 354 | **Transitive-inference consistency** — check transitively-implied relations (A→B, B→C ⟹ A→C) against directly-observed ones | Catches inconsistencies pairwise checks miss; a graph-level integrity check | dependency edges (FC-3); belief-set check (#307) | 2 | M | M |
| 355 | **Belief-graph anomaly detection** — flag structurally anomalous claims (odd connectivity, isolated high-confidence) for review | Surfaces suspicious beliefs by structure alone; complements content checks | dependency graph; motifs (#267); provenance | 3 | M | M |
| 356 | **Entity merge/split auditing** — periodically audit canonicalizer merges/splits against new evidence to catch bad merges | Protects claim identity — a bad merge silently corrupts many claims (IL-6/IL-1 risk) | canon.py; symbol-sig guard; concept-drift (#40) | 2 | S | M |

## Wave 6o — 2026-07-13 iter 100 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 357 | **Standing-program continuity** — carry the research agenda across restarts as a coherent program, not a fresh start each session | The core "researcher has standing" thesis made concrete + testable | selfmind hydrate; now.md; investigations | 1 | M | H |
| 358 | **Initiative-quality metric** — measure how often self-initiated (unbidden) work produced validated beliefs vs human-directed | Quantifies whether "initiative" is real value or noise — the researcher-vs-tool proof | free_move; discover; verified ledger | 4 | S | M |
| 359 | **Research-taste evolution tracking** — track how the taste function evolved from outcomes, showing it learns what's worth pursuing | Makes taste a *learning* function, not a fixed prior — a mind that improves its judgment | taste weights; strategies.md; outcomes | 1+4 | M | M |

## Wave 6p — 2026-07-13 iter 101 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 360 | **Independent re-implementation check** — re-implement a paper's analysis from its description (not its code) and compare | Catches code-vs-method divergence; the strongest reproduction (SciReplicate-style) | sandbox; analyst; reproduction benchmarks | 3 | L | M |
| 361 | **Blinded reanalysis** — reanalyze data blinded to the expected result, avoiding confirmation bias in the analysis | Analyst can't unconsciously steer toward the "wanted" result; CLAUDE.md §1 discipline | analyst; prereg; sandbox | 3 | M | M |
| 362 | **Pre-registered reanalysis-plan primitive** — write + freeze the plan before touching data (E12b practice, made standard) | Locks the analysis before the data is seen — no post-hoc goalpost-moving | E12b prereg; sessions; self-preregistration (#41) | 3 | S | M |

## Wave 6q — 2026-07-13 iter 102 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 363 | **Action-consequence preview** — before an autonomous action, preview expected consequences + cost to the human | Transparent autonomy — the human sees what an action will do before it happens | Ask/Investigate/Build budget preview; autonomy ladder | 1+4 | S | M |
| 364 | **Reversible-by-default actions** — every autonomous action is undoable with an undo log | Safe autonomy — a wrong move is recoverable; append-only already supports this | append-only stores; belief-write log (#191) | 1 | S | M |
| 365 | **Belief-change approval queue** — high-stakes belief changes queue for human approval with a clear diff | The human-anchors-high-stakes rule as a concrete UI workflow | anchoring; handoff inbox; evidence-tree diff (#18) | 2+4 | S | M |

## Wave 6r — 2026-07-13 iter 103 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 366 | **Confidence-source decomposition** — decompose a belief's confidence into independent contributions (# labs, replication, effect consistency, external corroboration) | Makes confidence explainable + auditable; feeds "why this confidence" (#167) | calibrate (FC-5); independence; report card (FC-25) | 2 | M | M |
| 367 | **Correlated-evidence overconfidence penalty** — penalize confidence when evidence is non-independent (avoid double-counting) | The membrane's core discipline — independence, not volume — quantified | independence-by-lab; poisoning_signals; membrane | 2 | M | H |
| 368 | **Extraordinary-claim confidence floor** — raise the admission bar with claim surprisingness (extraordinary claims need extraordinary evidence) | Sagan's razor operationalized; surprise raises the bar, not just the priority | surprise (PRD-01 F1.6); membrane; calibrate | 2 | S | M |

## Wave 6s — 2026-07-13 iter 104 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 369 | **Patent-literature ingestion** — read patents (often ahead of publication) as a distinct, appropriately-typed evidence source | Grey literature the competitive set ignores; early signal on applied research | ingest; USPTO skill; provenance typing | 1 | M | M |
| 370 | **Clinical-guideline ingestion** — ingest clinical practice guidelines as high-authority synthesized evidence | A distinct, authoritative evidence tier for clinical claims | ingest; provenance typing; membrane | 1 | M | M |
| 371 | **Dataset-paper linkage** — link a claim to the dataset paper it's based on, enabling direct data access for reanalysis | Closes claim→data for the executable loop; the missing pointer | provenance; GEO resolution; datasets | 3 | S | M |

## Wave 6t — 2026-07-13 iter 105 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 372 | **PICO-structured claim extraction** — extract clinical claims in PICO form (Population/Intervention/Comparison/Outcome) | Precise comparison across studies; the qualifiers that make contradictions real vs apparent | extract; RQ-E01b; qualifiers | 1 | M | H |
| 373 | **Direction/magnitude separation** — separate a claim's direction (increases/decreases) from magnitude (how much) | "Significant but tiny" becomes visible; effect size travels with the sign | extract; effect-size harmonizer (#22) | 1 | S | M |
| 374 | **Claim-qualifier preservation** — preserve every qualifier (in mice, high dose, in vitro) so a claim never travels without its scope | The exact fix for over-generalization (the GEO/microglia lesson); RQ-E01b core | extract; RQ-E01b; scope-creep (#286) | 1 | M | H |

## Wave 6u — 2026-07-13 iter 106 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 375 | **Hype-cycle positioning** — estimate where a target sits on a hype-vs-evidence curve (peak hype / trough / plateau) | Flags over-hyped targets before the crash; a PI de-risking signal | trajectory; citation-vs-support (FC-3); disruption index | 3 | M | M |
| 376 | **Emerging-consensus detection** — detect a nascent consensus forming before it's established | Catches the front as it moves — the always-on colleague's early edge | trajectory velocity; convergence; membrane | 3 | M | M |
| 377 | **Field-reversal early warning** — detect the pattern preceding a field-wide reversal (declining replication + rising nulls) | The BUILD_PLAN §3.1 collapse-forecast — "the last time evidence looked like this, it collapsed" | trajectory dynamics; dark-lit; changepoint | 3 | M | H |

## Wave 6v — 2026-07-13 iter 107 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 378 | **Trust-earned progressive autonomy** — Persona earns more autonomy as its track record proves out, visible to the human | Autonomy tied to demonstrated reliability, not assumed; the safety+trust flywheel | autonomy ladder (#189); error-rate (#171); track record | 1+4 | M | M |
| 379 | **Track-record transparency page** — a public page of verified hits, reversals, and current calibration — the trust dossier | The credibility artifact a skeptic checks first; radical honesty as a feature | error log; verified ledger; calibration (PRD-15) | 4 | S | M |
| 380 | **Confidence-vs-outcome scatter** — plot predicted confidence against realized outcomes so miscalibration is visible per bin | Miscalibration you can see, per bin — deepens the reliability panel | calibration (PRD-15); prediction ledger (FC-17) | 4 | S | M |

## Wave 6w — 2026-07-13 iter 108 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 381 | **Bradford-Hill criteria checklist** — systematically assess a causal claim (strength, consistency, temporality, dose-response, plausibility…) | The epidemiologist's standard causal framework, made a structured, transparent check | causal gate (FC-10); dose-response (#232); confounders (#233) | 3 | M | H |
| 382 | **GRADE evidence-quality rating** — rate a body of evidence with GRADE (high/moderate/low/very-low) | A standard, recognized quality summary clinicians already trust | meta-analysis (PRD-10); auditor; consensus (#213) | 3 | M | M |
| 383 | **Toulmin argument mapping** — represent an argument as claim/grounds/warrant/backing/rebuttal for clarity | Makes the *structure* of reasoning explicit + inspectable, beyond a flat evidence list | evidence chains; dependency (FC-3); synthesis | 2+4 | M | M |

## Wave 6x — 2026-07-13 iter 109 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 384 | **PRISMA-adherent systematic review** — follow the PRISMA flow (search, screen, extract, synthesize, report) when producing a review | Reviews that meet the field's reporting standard — publishable, auditable | review.py; synthesis; deliverables | 3 | M | M |
| 385 | **Search-completeness estimation** — estimate what fraction of relevant literature was actually read (capture–recapture) | Honest about coverage — "we read ~X% of the relevant work" beats implying totality | reader; sources; membrane | 1 | M | M |
| 386 | **Inter-note consistency check** — check that a persona's synthesis notes don't contradict each other | Self-consistency across its own outputs; catches drift between notes | notes; checker; belief-set check (#307) | 3 | S | M |

## Wave 6y — 2026-07-13 iter 110 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 387 | **Parameterized analysis templates** — reusable, validated templates (diff-expression, MR, meta-analysis) instantiated per question | Reduces bespoke-code risk; the reanalysis loop runs vetted code, not fresh guesses | analyst; sandbox; oracle envelope (FC-8) | 3 | M | M |
| 388 | **Pipeline validation on synthetic data** — validate an analysis on synthetic data with known ground truth before real data | Catches pipeline bugs before they touch a real conclusion; control-injection's cousin | sandbox; oracle controls (PRD-16) | 3 | M | M |
| 389 | **Result-sanity auto-checks** — post-analysis checks (direction plausible, magnitude in range, no NaN/inf) before a result is trusted | Fail-loud on obviously-broken results; cheap deterministic guard | analyst; forensics; tool-output verification (#295) | 3 | S | M |

## Wave 6z — 2026-07-13 iter 111 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 390 | **End-to-end loop dashboard** — one live view: contradiction → hypothesis → dataset → test → belief-update, each stage's status | The money-shot surface — watch the acting loop close in real time | sessions; investigations; flagship | 4 | M | H |
| 391 | **Loop-completion-rate metric** — track how often a flagged contradiction completes the full loop vs stalls, and where | The single best measure of whether the acting loop actually *acts* | investigations; verified ledger; sessions | 4 | S | M |
| 392 | **Loop-bottleneck attribution** — attribute where loops most often stall (no dataset / test failed / human backlog) to prioritize fixes | Tells the builder what to fix to make more loops close; process legibility | loop metrics; handoff SLA (#168); testability (#336) | 4 | S | M |

## Wave 7a — 2026-07-13 iter 112 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 393 | **State-of-the-argument prose** — auto-write an evolving narrative (settled / contested / current front) that updates as evidence lands | The argument-state view (BUILD_PLAN §6.3) as living prose — a story with a derivative | trajectory; fieldmap; synthesis | 3+4 | M | M |
| 394 | **Narrative-arc of understanding** — a written "how the understanding developed" story keyed to source years | Deepens the recent idea-over-time work; the intellectual history made readable | note-diff (PRD-03 F3.11); trajectory; history | 3 | M | M |
| 395 | **Counter-narrative surfacing** — alongside the main narrative, present the strongest alternative story the evidence supports | Never a single story — shows the plausible alternative; extends contradiction-aware synthesis | synthesis; minority positions (#214); red-team | 3 | M | M |

## Wave 7b — 2026-07-13 iter 113 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 396 | **Bench-to-bedside tracking** — track a claim's journey basic → preclinical → clinical → practice, showing translational stage | Situates a finding on the translation path — how close is this to helping a patient? | ClinicalTrials; provenance; trajectory | 3+4 | M | M |
| 397 | **Real-world-impact estimation** — for a resolved question, estimate downstream impact (papers de-risked, trials informed) | Quantifies the value of resolving a tension; the "so what" made numeric | dependency mass (FC-4); value queue | 3 | M | M |
| 398 | **Failure-to-translate analysis** — analyze why a promising target failed to translate (the graveyard), extracting lessons | Learning from the dead-science graveyard; the anti-hype counterweight | dark-lit (PRD-03 F3.5); trials; retraction | 3 | M | M |

## Wave 7c — 2026-07-13 iter 114 (fresh, direct — crosses #400)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 399 | **Slop-rate monitoring** — continuously measure the fraction of swarm output rejected at the membrane (slop rate) | The anti-slop thesis made a live health metric — "scale of reading, discipline of believing" | membrane; gate_decisions ledger; swarm | 2+4 | S | H |
| 400 | **Load-adaptive membrane tightening** — when slop rate rises, auto-tighten the membrane (backpressure) | The validated E-DIAGNOSTIC backpressure behavior generalized to a live control loop | membrane adaptive policy; poisoning_signals | 2 | M | H |
| 401 | **Quality-vs-quantity dashboard** — reading volume vs validated-belief yield over time, so scale never masquerades as progress | Keeps the team honest — more agents must earn their keep, not just produce text | swarm economics (FC-24); membrane yield | 4 | S | M |

## Wave 7d — 2026-07-13 iter 115 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 402 | **Cross-investigation pattern mining** — mine completed investigations for recurring successful patterns (which evidence types resolved which question types) | The mind gets *methodologically* smarter over time — procedural learning at scale | investigations; strategies.md; verified ledger | 1+3 | M | M |
| 403 | **Warm-start from similar past investigations** — when a new question resembles a past one, warm-start with its approach + findings | Faster, better investigations by reuse; the persistent-self advantage realized | investigations; vectors; director | 1 | M | M |
| 404 | **Method-recommendation from history** — recommend the analysis method most likely to work for a question type, learned from outcomes | Turns accumulated experience into actionable method choice | analyst; verified outcomes; templates (#387) | 3 | M | M |

## Wave 7e — 2026-07-13 iter 116 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 405 | **Cell-line authentication check** — flag claims using misidentified/contaminated cell lines (ICLAC/Cellosaurus) | A major, well-documented irreproducibility source the auditor misses | science clients; Cellosaurus; audit ledger | 3 | M | M |
| 406 | **Sample-size-justification check** — flag studies with no power/sample-size justification | Complements the min-detectable-effect check; catches unpowered designs | forensics power; methods critique (#175) | 3 | S | M |
| 407 | **Batch-effect awareness** — for omics claims, check whether batch effects were addressed | A common omics confound that flips results; pairs with omics reanalysis (#297) | audit; omics; methods critique | 3 | M | M |

## Wave 7f — 2026-07-13 iter 117 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 408 | **Devil's-advocate persona** — a dedicated persona of pure skepticism tasked with challenging the lab's consensus | Institutionalizes dissent in the lab (PRD-05) — a standing check on groupthink | second researcher (PRD-05); disposition; reconcile (FC-9) | 1 | M | M |
| 409 | **Subfield-specialist personas** — personas specialize by subfield; a coordinator routes questions to the right specialist | The lab scales by division of expertise, like a real research group | manager; director; field gate | 1 | M | M |
| 410 | **Lab-consensus vs individual-belief** — track both the lab's collective belief and each persona's, surfacing divergence | Disagreement between synthetic researchers as a first-class signal (BUILD_PLAN §7.1) | reconcile (FC-9); cross-persona diff; membrane | 2+4 | M | M |

## Wave 7g — 2026-07-13 iter 118 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 411 | **Causal-DAG construction** — build an explicit causal DAG for a question from the claims, enabling do-calculus about interventions | Real causal reasoning, not just labels; the deepest form of the causal-strength gate | dependency graph; causal gate (FC-10); dowhy | 3 | L | H |
| 412 | **Confounder-adjustment recommendation** — from the DAG, recommend which variables to adjust for (backdoor criterion) | Turns causal structure into an actionable analysis spec; pairs with reanalysis | causal DAG (#411); confounder checklist (#233) | 3 | M | M |
| 413 | **Instrumental-variable identification** — identify valid instruments for a causal claim | Feeds executable MR (PRD-06) — finds the instruments the MR needs | causal DAG; MR (PRD-06); OpenGWAS | 3 | M | M |

## Wave 7h — 2026-07-13 iter 119 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 414 | **Stakeholder-tailored briefs** — same finding framed for a PI / clinician / funder / patient-advocate, right detail for each | One finding, many audiences — meets each where they are without distorting the science | deliverables; knowledge ladder; causal gate (FC-10) | 3+4 | M | M |
| 415 | **Regulatory-grade evidence dossier** — assemble a finding's evidence in a format suitable for a regulatory submission | Unlocks clinical/regulatory use; pairs with governance audit trail (#133) | provenance; RO-Crate; audit ledger | 4 | M | M |
| 416 | **Teaching-slide-deck generation** — auto-generate a teaching deck for a topic from the belief graph | Turns the knowledge base into instruction material; scientific-slides skill | belief graph; scientific-slides; deliverables | 3+4 | M | M |

## Wave 7i — 2026-07-13 iter 120 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 417 | **The paper about Persona** — auto-draft/maintain "On constructing a persistent synthetic researcher" from /results + /experiments | The endgame artifact (CLAUDE.md) — the system documents its own construction as a paper | results/FINDINGS.md; experiments; paper.py | 3+4 | L | H |
| 418 | **Living FINDINGS→paper sync** — keep the paper draft in sync with new experiment results + reversals automatically | The paper stays current as the evidence base grows; reversals included honestly | FINDINGS.md; RQ registry; deliverables | 3 | M | M |
| 419 | **Ablation-study automation** — auto-run ablations (remove membrane / anchoring / verifier) to quantify each component's contribution | Evidence for the architecture itself — the "we tested our own design" proof, generalized | experiments; exp_poisoning.py; eval | 4 | M | M |

## Wave 7j — 2026-07-13 iter 121 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 420 | **Prompt-injection defense audit** — periodically test the pipeline against known injection patterns in papers, verifying the "paper is data" boundary | The auditor already treats papers as untrusted — make that a standing, tested guarantee | audit.py security note; chaos audit (#103); membrane | 2+4 | M | H |
| 421 | **Data/tool supply-chain integrity** — verify external tools/data (checksums, pinned versions) to prevent supply-chain compromise | Protects the executable loop from compromised dependencies/data | sandbox digest; datasets allowlist; lockfile (#289) | 3 | S | M |
| 422 | **Access-control on high-stakes actions** — require elevated auth for anchor / publish / external-submit | Gates the irreversible/outward-facing actions behind explicit authorization | anchoring; api; governance audit (#133) | 4 | S | M |

## Wave 7k — 2026-07-13 iter 122 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 423 | **Streaming membrane** — process incoming claims as they arrive vs batch harvest, for lower latency | Beliefs update in near-real-time; the "always thinking" substrate made responsive | membrane.harvest; queue; events | 2 | M | M |
| 424 | **Priority lanes in the queue** — a fast lane for urgent/high-value tasks alongside the bulk lane | Urgent work isn't stuck behind bulk reading; better responsiveness under load | queue priority; scheduler; value queue | 1 | S | M |
| 425 | **Adaptive scheduler cadence** — the scheduler wakes more often under high activity, less when idle | Saves cycles when quiet, responsive when busy; efficient always-on | supervisor scheduler loop; SCHEDULER_INTERVAL_S | 1 | S | M |

## Wave 7l — 2026-07-13 iter 123 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 426 | **Coverage-gap map** — show which parts of a field's space have thin belief coverage (unread regions), guiding where to read next | Turns "what haven't I read?" into a map; directs the swarm to blind spots | fieldmap; communities; embeddings | 3+4 | M | M |
| 427 | **Systematic vs opportunistic reading balance** — balance systematic field coverage against surprise-driven opportunistic reading | Neither pure breadth nor pure surprise — a tunable mix a real researcher strikes | reader; surprise (PRD-01 F1.6); coverage | 1 | M | M |
| 428 | **Per-subfield saturation detection** — detect when a subfield is "read enough" (new reading yields no new beliefs) and move on | Stops re-reading a covered area; frees the swarm for fresh ground | membrane yield; stop rule (#311); communities | 1 | S | M |

## Wave 7m — 2026-07-13 iter 124 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 429 | **Qualitative-evidence integration** — integrate qualitative findings (interviews, case studies) with appropriate typing, not just quantitative | Broadens evidence beyond numbers while keeping the typing discipline | extract; provenance typing; membrane | 1+2 | M | M |
| 430 | **Mixed-methods synthesis** — synthesize quantitative + qualitative evidence coherently (mixed-methods review) | Matches how many real reviews work; a fuller picture per question | synthesis; review.py; consensus (#213) | 3 | M | M |
| 431 | **Anecdote-vs-evidence discrimination** — clearly separate anecdotal claims from systematic evidence in synthesis | Keeps a single case report from being weighted like a trial; honest evidence hierarchy | provenance tiers; membrane; GRADE (#382) | 2 | S | M |

## Wave 7n — 2026-07-13 iter 125 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 432 | **Component-health monitoring** — monitor each subsystem (queue depth, membrane throughput, sandbox availability) with alerts | Operational legibility — the operator sees the machine's vitals, not just outputs | daemon status; events; api | 4 | S | M |
| 433 | **Self-healing on component failure** — auto-restart/recover a failed component (generalize the queue's crash-resume) | Resilience for an always-on system; recovers without a human babysitting it | queue crash-resume; supervisor; manager | 1 | M | M |
| 434 | **Graceful capability degradation** — when a capability (e.g. Lean/Aristotle) is unavailable, degrade to the fallback (sympy) transparently | Never a hard failure — degrade with a visible provenance note (partly exists, make systematic) | aristotle→sympy fallback; provenance | 3 | S | M |

## Wave 7o — 2026-07-13 iter 126 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 435 | **Full-provenance replay bundle** — one-click bundle of every source/claim/computation/decision for a conclusion, re-runnable | The complete reproducibility artifact; extends the reproduction capsule (#14) | sessions; RO-Crate; provenance passport (#28) | 4 | M | M |
| 436 | **Provenance-graph query API** — query the provenance graph ("every belief depending on source X") | Lets a human trace impact of any source; powers the load-bearer retraction alert | provenance; dependency edges (FC-3); kg | 2+4 | M | M |
| 437 | **Orphan-evidence detection** — find evidence in the store not linked to any belief (dead weight) and prune/link | Keeps the store clean + honest about what's actually used | kg; GC (#160); provenance | 2 | S | M |

## Wave 7p — 2026-07-13 iter 127 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 438 | **Embedding-space audit** — periodically audit the embedding space for degenerate clusters or drift that could corrupt retrieval/canon | Protects retrieval + canonicalization from silent embedding degradation | vectors; canon; embed | 2 | M | M |
| 439 | **Relevance-gate explainability** — for each dropped paper, show the anchor terms + similarity ("why skipped") | Deepens the gate-decisions ledger (PRD-04 F4.6) — the funnel fully inspectable | reader relevance filter; gate_decisions ledger | 4 | S | M |
| 440 | **Classifier-confidence + abstain** — surface any ML classifier's confidence (relevance, causal tier) and abstain when low | No silent low-confidence classifications; the abstention discipline for ML sub-components | relevance gate; causal tier (FC-10); calibrate | 2 | S | M |

## Wave 7q — 2026-07-13 iter 128 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 441 | **Long-term collaborator memory** — remember a specific human's preferences, past questions, standing interests across sessions | The always-on colleague that actually knows *you* over time — the relationship compounds | selfmind; directives; converse | 1 | M | M |
| 442 | **Proactive next-question suggestion** — from the human's history + the field's movement, suggest what to look at next | Anticipates the researcher's needs; the initiative loop pointed at the human's agenda | value queue; trajectory; collaborator memory (#441) | 4 | M | M |
| 443 | **Personalized relevance tuning** — tune what surfaces to a specific human from their demonstrated interests | Less noise, more signal per person; the attention layer personalized | relevance gate; interests; collaborator memory | 4 | M | M |

## Wave 7r — 2026-07-13 iter 129 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 444 | **Multiple-comparisons correction** — apply FDR/Bonferroni when a claim rests on many tests; flag uncorrected multiple testing | A top false-positive source (omics especially) the forensic bank should catch | forensics; p-curve; omics reanalysis (#297) | 3 | S | M |
| 445 | **Bayesian model comparison** — compare hypotheses via Bayes factors, not just p-values | Evidence for/against, not just reject/fail-to-reject; richer than NHST | sandbox; pymc; hypothesis portfolio (#265) | 3 | M | M |
| 446 | **Equivalence testing (TOST)** — for "no difference" claims, run proper equivalence tests, not non-significance=equivalence | Fixes a pervasive inferential error — absence of evidence ≠ evidence of absence | forensics; power; causal gate | 3 | M | M |

## Wave 7s — 2026-07-13 iter 130 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 447 | **Boundary-condition mapping** — map the exact conditions under which a belief holds vs breaks (the edges of the claim) | Contradictions often dissolve into boundary conditions; makes scope precise | qualifiers; conflict typing (FC-10); PICO (#372) | 2+3 | M | H |
| 448 | **Generalizability scoring** — score how far a finding likely generalizes beyond its studied population/context | Quantifies external validity; pairs with the scope-creep detector (#286) | population qualifiers; bias-in-evidence (#244) | 3 | M | M |
| 449 | **Exception tracking** — track documented exceptions to a general rule, so it never travels without its known exceptions | The rule + its exceptions together — honest, complete synthesis | membrane; qualifiers; minority positions (#214) | 2 | S | M |

## Wave 7t — 2026-07-13 iter 131 (fresh, direct — crosses #450)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 450 | **Judgment-rubric standardization** — standardize the adjudicator's rubrics so verdicts are consistent across claims + over time | Consistency of the model-adjudicator; reduces arbitrary variation in the auditor | audit.py adjudicator; PaperBench rubric | 3 | S | M |
| 451 | **Verdict-stability across runs** — measure whether the same claim gets the same verdict across independent adjudication runs | Catches an unstable adjudicator before its verdicts are trusted | audit; determinism audit (#208); regression suite | 4 | S | M |
| 452 | **Adjudicator anchoring-bias check** — randomize presentation order so the adjudicator isn't anchored by the first number it sees | Removes a known LLM-judge bias; keeps the verdict evidence-driven | audit; base-rate panel (#36); calibration | 3 | S | M |

## Wave 7u — 2026-07-13 iter 132 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 453 | **Model-tier routing by task difficulty** — easy tasks → cheap model, hard reasoning → strongest, measured per task type | More reasoning per dollar; the strong model spent only where it changes the answer | config MODEL_*; provenance-aware routing (#93) | 1 | M | M |
| 454 | **Distill routine judgments** — for high-volume routine judgments, distill a cheap classifier from strong-model labels | Cheap at scale for the easy cases; strong model reserved for the hard ones | RQ-E10 harness; relevance gate; open-weight workers | 1 | M | M |
| 455 | **Batch parallel sub-questions** — batch independent sub-questions into one strong-model call where possible | Fewer calls, lower latency + cost for fan-out work | investigation DAG; batch API; queue | 1 | S | M |

## Wave 7v — 2026-07-13 iter 133 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 456 | **Result-writeback verification** — after a self-test writes back to the belief-state, verify the writeback is correct + traceable | Guards the last mile of the acting loop — a wrong writeback corrupts the self | verified ledger; membrane; sessions | 2 | S | M |
| 457 | **Test→belief provenance link** — every belief updated by a test links to the exact test session that changed it | Complete traceability from belief back to the computation that moved it | provenance; sessions; verified ledger | 2 | S | M |
| 458 | **Loop-outcome notification** — notify the human when a loop completes with its verdict (resolved / weakened / inconclusive) | Closes the human-in-the-loop feedback; the acting loop reports back | events; loop dashboard (#390); alerts | 4 | S | M |

## Wave 7w — 2026-07-13 iter 134 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 459 | **Unexpected-connection surfacing** — surface non-obvious connections between distant beliefs a human wouldn't spot | Serendipitous insight — the payoff of reading at scale a human can't | dependency graph; cross-field (PRD-21); bridges (#269) | 3 | M | M |
| 460 | **Serendipity mode** — occasionally read slightly off-interest to seed cross-pollination (controlled exploration) | Prevents tunnel vision; the ε-exploration of *interests*, not just tasks | reader; relevance gate; interests | 1 | S | M |
| 461 | **Mechanism-unification highlighting** — highlight mechanisms that explain many observations at once (explanatory unification) | Elegance as a signal — one mechanism unifying disparate findings is high-value | dependency graph; load-bearing (FC-4); parsimony (#202) | 3 | M | M |

## Wave 7x — 2026-07-13 iter 135 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 462 | **Self-documenting architecture** — keep architecture docs in sync with code automatically (docstrings → doc) | Docs never drift from code; the system stays legible to its own maintainers | docstrings; graphify; api | 4 | M | M |
| 463 | **Live capability inventory** — an auto-generated inventory of what Persona can currently do (tools, checks, data sources) | A reader sees the actual capability surface, not a stale list | science.REGISTRY; forensics; guidance | 4 | S | M |
| 464 | **Auto-maintained continuation doc** — keep the handoff/continuation doc a new agent needs current automatically | This project maintains it by hand — make it self-updating from state | CONTINUATION_HANDOFF; state; events | 4 | S | M |

## Wave 7y — 2026-07-13 iter 136 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 465 | **Bi-temporal query support** — query beliefs by both when they were true (valid time) and when we learned them (transaction time) | The bi-temporal store's power made queryable — "true then" vs "known then" | bi-temporal contract (valid_from/valid_to); kg | 2 | M | M |
| 466 | **Belief-state-as-of-date reconstruction** — reconstruct the exact belief-state as of any past transaction time | Audit "what did we believe on date X?" — deepens time-travel replay (#96) | bi-temporal store; history; snapshots (#139) | 2 | M | M |
| 467 | **Retroactive-correction propagation** — when a past belief is corrected, propagate to everything that depended on it with a dated trail | The fragility-cascade for *corrections* — errors don't persist downstream (BUILD_PLAN §3.3) | dependency edges; fragility_cascade (FC-4); history | 2 | M | H |

## Wave 7z — 2026-07-13 iter 137 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 468 | **Sequential testing / early-stopping** — in a reanalysis, stop early when the answer is clear, saving compute | Cheaper reanalysis without losing rigor; anytime results | sandbox; analyst; budget | 3 | M | M |
| 469 | **Active-learning data selection** — reanalyze the most informative subset of data first | Faster to a confident verdict; spends compute where it discriminates | sandbox; analyst; datasets | 3 | M | M |
| 470 | **Bayesian optimal experiment design** — design the experiment that maximizes information per unit cost | The value-queue's VoI made a formal design objective; sharpens "highest-value experiment" | value queue (FC-4); assay-matcher (#338) | 3 | M | M |

## Wave 8a — 2026-07-13 iter 138 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 471 | **Overnight-run morning digest** — a morning summary of everything the researcher did overnight (read, tested, updated, flagged) | The "always-on, you wake to progress" experience; the overnight-run money-shot | events; notebook; digest (#131) | 4 | S | M |
| 472 | **Autonomous-run safety envelope** — bounded budget + rails + kill-switch for unattended overnight runs | Safe unattended autonomy — bounded spend, halt control, no runaway | budget; halt control; autonomy ladder (#189) | 1 | S | M |
| 473 | **Wake-the-human trigger** — during an unattended run, interrupt the human only for a genuinely high-stakes discovery | The researcher that knows when to call you — signal, not spam | load-bearer alert (#220); handoff; alerts | 1+4 | S | M |

## Wave 8b — 2026-07-13 iter 139 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 474 | **Degrees-of-belief as distributions** — represent belief as a full distribution, not a point, capturing uncertainty-about-uncertainty | Richer epistemics — a wide vs narrow 50% are very different states | calibrate (FC-5); Bayesian posterior (#223) | 2 | M | M |
| 475 | **Epistemic vs aleatoric uncertainty split** — separate reducible ignorance from inherent randomness | Tells the human "more data would help" vs "it's genuinely noisy" — different actions | calibrate; value queue; sensitivity | 2 | M | M |
| 476 | **Suspended-judgment as a first-class state** — "I don't know yet, here's what I'm waiting on" as an explicit belief state, not absence | Honest abstention made a positive, actionable state — the researcher that says "not yet" | provenance tiers; abstention (FC-5); open questions | 2 | S | M |

## Wave 8c — 2026-07-13 iter 140 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 477 | **Whole-field belief-state export** — export a complete, citable snapshot of a persona's belief-state on a field as a standing reference | The field's live state as a shareable, versioned resource — the always-on colleague's public face | snapshots (#139); RO-Crate; deliverables | 4 | M | M |
| 478 | **Community-contributable corrections** — let external experts submit moderated corrections to a persona's beliefs | Human-as-resolver opened to the community — compounding shared judgment (BUILD_PLAN §3.7) | conflict_reviews; anchoring; open-review (#198) | 4 | M | M |
| 479 | **Belief-state as a downstream API** — expose the belief-state as a stable API other tools build on | Persona becomes queryable infrastructure; broadens the MCP exposure (#294) | api; MCP (#294); provenance query (#436) | 4 | M | M |

## Wave 8d — 2026-07-13 iter 141 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 480 | **Long-tail / rare-disease focus mode** — deliberately cover under-studied rare conditions where synthesis has outsized value | Highest marginal value where humans have least time; the whitespace a scaled reader fills | interests; coverage-gap map (#426); ingest | 1 | M | M |
| 481 | **Small-evidence-base handling** — special handling for questions with very few studies (n=1-2), where standard synthesis fails | Avoids over/under-claiming when evidence is thin; honest low-N reasoning | membrane; abstention (FC-5); provenance | 2 | M | M |
| 482 | **Case-report aggregation** — aggregate scattered case reports into a structured picture for rare conditions | Builds signal from the only evidence rare conditions have; typed as weak but useful | extract; CURE ID (#backlog); provenance tiers | 3 | M | M |

## Wave 8e — 2026-07-13 iter 142 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 483 | **Own-result-vs-literature reconciliation** — when Persona's own test contradicts the literature, generate a dossier weighing its computation against consensus | The self-test loop's hardest case, handled honestly — not blind self-trust | verified ledger; membrane; handoff (FC-2) | 2+3 | M | H |
| 484 | **Confidence-in-own-computation** — calibrate how much to trust its own reanalysis vs published, given low reproduction-benchmark scores | Guards against overtrusting first-pass reanalysis (REPRO-Bench 21% reality) | verified tier; calibrate (FC-5); TESTED-provisional | 2 | M | M |
| 485 | **Escalate own surprising result** — when its own test contradicts strong consensus, escalate to human before acting (extraordinary claims) | Extraordinary self-claims need human sign-off; the anti-slop rule for the acting loop | anchoring; handoff; extraordinary-claim floor (#368) | 1+2 | S | H |

## Wave 8f — 2026-07-13 iter 143 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 486 | **Prompt-optimization loop** — optimize agent prompts against immutable evaluators, keep/revert logged (RQ-E10 harness → runtime) | The learning program hosted-models allow: optimize prompts/tools, not weights | RQ-E10 frozen-evaluator; CONTINUATION_HANDOFF §7 | 1 | M | M |
| 487 | **Tool-use policy learning** — learn which tools/sequences work best per task type from trajectories | Procedural improvement of *how* it acts, from real outcomes | trajectories; strategies.md; method-rec (#404) | 1 | M | M |
| 488 | **Memory-policy tuning** — tune what to remember/forget from outcomes, never rewarding persuasive prose | Sharpens memory on real reward signals (citation/execution/calibration), not eloquence | consolidation (FC-11); rewards; CONTINUATION_HANDOFF §7 | 2 | M | M |

## Wave 8g — 2026-07-13 iter 144 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 489 | **Multi-anchor identity redundancy** — the self survives corruption of any one store (docs + graph + notebook), validated | Identity distributed across stores — the persistence thesis made robust (BUILD_PLAN §5.5) | selfmind docs; kg; notebook; hydrate | 2 | M | M |
| 490 | **Disposition-consistency enforcement** — ensure actions stay consistent with the stated disposition; flag drift | Keeps a skeptic skeptical — the self doesn't quietly morph (pairs with identity-drift #159) | disposition (PRD-05); coherence.drift; actions | 1 | S | M |
| 491 | **Self-narrative coherence check** — periodically check the self-docs tell a coherent, non-contradictory story | A mind whose self-description stays internally consistent; the anti-degradation guard | selfmind files; coherence; consolidation | 1 | S | M |

## Wave 8h — 2026-07-13 iter 145 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 492 | **Full-vision integration test** — an end-to-end test of the whole loop on a known case (seed→read→contradiction→hypothesis→dataset→test→belief→handoff→mini-review) | Proves the entire thesis works together, not just per-component; the acceptance test | sessions; investigations; all lanes | 4 | M | H |
| 493 | **Demo-scenario library** — scripted, cached demo scenarios that showcase each capability reliably | Never a broken demo; the cache-the-money-shot discipline as a library | cached corpus; sessions; PROGRAM_SUMMARY | 4 | S | M |
| 494 | **Money-shot regression test** — a standing test that the flagship closed-loop demo still works after any change | Protects the single most important flow from silent breakage | integration test (#492); loop dashboard (#390) | 4 | S | M |

## Wave 8i — 2026-07-13 iter 146 (fresh, direct — meta)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 495 | **Auto-triage of this backlog** — cluster + dedup the ~500-idea backlog so the master pulls efficiently | Persona's own methods applied to its build backlog — dogfooding the clustering/graphify tools | graphify; embeddings; communities | 4 | S | M |
| 496 | **Idea→PRD auto-drafting** — given a ripe backlog idea, auto-draft a first PRD skeleton for refinement | Speeds the ideation→spec pipeline this loop runs; the meta-tool for the meta-work | PRD template; deliverables; this loop | 4 | M | M |
| 497 | **Feature-impact forecasting** — estimate each backlog idea's expected impact on Persona's metrics before building | Prioritize the backlog by predicted value, not just leverage guesses | value queue (FC-4); metrics; scorecard | 4 | M | M |

## Wave 8j — 2026-07-13 iter 147 (fresh, direct — crosses #500)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 498 | **Persona-as-coauthor attribution** — transparent attribution of Persona's contributions in any output (honest about AI involvement) | Integrity about who did what; the transparency the field will demand | deliverables; provenance; trust ledger | 4 | S | M |
| 499 | **Reproducibility-first publishing** — publish with the full RO-Crate + executable notebook attached by default | Every output ships re-runnable — the reproducibility standard, not an afterthought | RO-Crate (PRD-04 F4.10); notebook (#240) | 4 | S | M |
| 500 | **The standing colleague (capstone)** — a persona that watches your subfield indefinitely and pings you the day the front moves | The full vision (BUILD_PLAN §7.3) — a persistent collaborator, not a session; integrates the whole program | all lanes; alerts (#15); trajectory; standing continuity (#357) | 1+4 | L | H |

## Wave 8k — 2026-07-13 iter 148 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 501 | **Asymmetric-loss humility** — bias toward under-confidence when stakes are high (a wrong high-stakes claim costs more than a cautious one) | Encodes humility where it matters most; the human-anchors-high-stakes rule quantified | calibrate (FC-5); stakes weighting; anchoring | 2 | S | M |
| 502 | **"I could be wrong" surfacing** — every high-confidence claim shows its most likely failure mode | Humility as a visible feature — confidence never without its caveat | red-team (PRD-09); report card (FC-25) | 4 | S | M |
| 503 | **Disagreement-with-experts flag** — when Persona disagrees with expert consensus, say so loudly and defer appropriately | Honest about going against the field; extraordinary-claim discipline | consensus (#213); handoff; extraordinary floor (#368) | 2 | S | M |

## Wave 8l — 2026-07-13 iter 149 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 504 | **Zero-config onboarding** — a new user gets value in the first minute (seed → first insight fast) | Adoption lives or dies in minute one; pairs with seed-from-a-paper (#186) | genesis flow; seed; time-to-first-insight (#144) | 4 | S | M |
| 505 | **Mobile-responsive legibility** — the core surfaces work on mobile for a PI checking on the go | The always-on colleague reachable anywhere; SPEC already requires responsive | index.html responsive; SCIENTIFIC_WORKBENCH_SPEC | 4 | M | M |
| 506 | **Offline-capable read mode** — cached belief-state viewable offline | Access without connectivity; the durable-on-disk self made portable | belief snapshot (#139); PWA cache | 4 | M | M |

## Wave 8m — 2026-07-13 iter 151 (fresh, direct — post-compaction)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 507 | **Cloud-lab experiment submission** — for a wet-lab-testable hypothesis, draft + submit an experiment to a cloud lab (Emerald/Strateos/Adaptyv) via API | Bridges the one thing Persona "can't do" — wet lab — via cloud labs; closes the loop to physical evidence | Adaptyv/Ginkgo/opentrons skills; value queue (FC-4) | 3 | L | H |
| 508 | **Assay-result ingestion** — ingest cloud-lab results back into the belief-state as TESTED evidence with full provenance | Completes the wet-lab acting loop — real experimental data updates beliefs | sessions; membrane; TESTED tier | 2+3 | M | M |
| 509 | **Wet-lab-vs-insilico reconciliation** — reconcile a cloud-lab result against Persona's in-silico prediction (MR/DepMap/etc.) | The strongest validation — did the physical experiment match the computation? | verified ledger; oracles (FC-8); reconcile | 2 | M | H |

## Wave 8n — 2026-07-13 iter 152 (fresh, direct)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 510 | **Skill-gap self-identification** — Persona identifies capabilities it lacks for a question and flags/acquires them | The researcher that knows what it can't yet do + seeks the tool — meta-awareness | known-unknowns (#287); capability inventory (#463) | 1 | M | M |
| 511 | **New-tool self-integration proposal** — when a needed data source/tool is missing, draft a proposal for the humans to add | Persona extends its own reach (bounded by human approval); this loop's pattern, internalized | science.REGISTRY; discover; handoff | 3+4 | S | M |
| 512 | **Capability-driven interest spawning** — spawn interest where a newly-acquired capability unlocks high-VoI questions | New tools open new frontiers; the interest-spawning loop tied to capability growth | interests; value queue (FC-4); skill-gap (#510) | 1 | M | M |

## Wave 8o — 2026-07-13 iter 153 (fresh, direct — adversarial-robustness / trust-economics lens)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 513 | **Poison-attribution forensics** — when the membrane/anchoring *rejects* a coordinated poisoning attempt, don't just drop it: cluster the colluding sources, fingerprint the injection pattern (shared origin, synchronized timing, near-duplicate spans), and file a typed **"adversarial campaign" dossier** so the human sees *who tried to move the belief and how* | Turns passive poisoning-resistance (validated 100% vs 71%) into *active attribution* — the membrane already detects the attempt; attributing it is a new legibility + security signal nothing surfaces. Distinct from #103 (chaos audit *tests* the membrane on synthetic attacks); this attributes a **real** detected one | `experiments/exp_poisoning.py` defense; membrane convergence/independence; coordinated-inauthentic-behavior detection lit | 2 | M | H |
| 514 | **Attack-cost pricing of a belief (cost-to-flip)** — assign each belief a security price = the marginal cost (reader-$ + fabricated-independent-sources + human-minutes) an adversary would need to flip it, computed from independence counts × anchor `resist` × provenance tier; surface **cheap-to-attack** beliefs (fragile + under-anchored + load-bearing) as a *security-prioritized* worklist | A dimension orthogonal to load-bearing (#26/#107) and confidence-budget (#91, evidence *spent*): this is evidence an *adversary* must spend. Identifies which conclusions are one poisoned source away from flipping — the anchoring queue's missing risk axis | anchoring `resist` rule; FC-3 independence; #91 confidence-budget as the dual; adversarial-robustness lit | 2+4 | M | H |
| 515 | **Cross-persona replication gate for TESTED→anchor** — before a high-stakes belief is anchored, hand its *exact* reanalysis capsule to a **second, independently-seeded** persona that re-runs it from raw data in a clean sandbox; anchor only if both personas' numbers agree within tolerance — true independent replication, not re-reading | Fuses the lab (#1, `PersonaManager` isolation) with self-reproduction (#62) into an *anchor gate*: independence at the level of the whole analysis pipeline, the strongest bar in the system. Distinct from #360 (independent re-implementation of one method) — this is a second *researcher* replicating end-to-end as a gate | BUILD_PLAN §7.1 multi-persona; #62 self-repro; #360; FC-9 reconcile; sessions capsule replay | 1+3 | L | H |

## Wave 8p — 2026-07-13 iter 154 (fresh, direct — scientific-competence measurement + external-trust lens)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 516 | **Effort-calibration self-score (was-it-worth-it ledger)** — before an investigation runs, Persona records its *predicted* cost + resolvability + value; after, it scores prediction-vs-actual and surfaces systematic bias (does it chronically underestimate hard questions? overspend on low-yield ones?) | Turns research *planning* into a measured competence — distinct from belief calibration (#16) and outcome calibration (#17), which score *conclusions*; this scores the *decision to spend*. A PI's real question "is this agent good at picking what to work on?" gets a number | prediction-ledger (#17/FC-17) pattern reused on plans; value_queue/VoI (FC-4); budget.py; testability classifier (#336) as the resolvability input | 1+4 | M | H |
| 517 | **Signed external-replication exchange** — publish each closed-loop as a *cryptographically signed* RO-Crate to a shared ledger; a third party (or a second Persona instance) re-runs it in a clean sandbox and posts a signed pass/fail; Persona consumes others' signed replications as a NEW independent-source TESTED signal — never trusting an unsigned claim | Extends provenance from *auditable-by-me* to *independently-verifiable-by-others* — the missing trust-network layer. A signed external replication is the strongest evidence class the system can admit, and it makes reproducibility a two-way market, not a one-way export | RO-Crate (PRD-04 F4.10); FC-9 reconcile; #198 open-review ledger + #478 community corrections (this adds signing + cross-instance re-run as admissible evidence); membrane independence | 3+4 | L | H |
| 518 | **Per-verdict method-provenance fingerprint** — every code-run oracle/forensic stamps the exact tool version + parameter defaults + reference-data snapshot it used onto the belief it produced, so a verdict is re-derivable years later AND a tool-version regression (a forensic that silently changed behavior between versions) is detectable by diffing fingerprints | Extends the capsule's sandbox-image-digest DOWN to the analysis-method level — the granularity where a forensic's own drift hides. Protects TESTED beliefs from silent method rot; a self-check nothing in the queue does at per-verdict resolution | sessions capsule (`input_sha256`/`sandbox_image_digest`); FC-8 oracle envelope; #290 lockfile-repro + #209 prompt-version-pinning (this is the *method*-level analog tied to each belief) | 3 | M | M |

## Wave 8q — 2026-07-13 iter 155 (fresh, direct — generative/predictive-science + deep-foundations lens)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 519 | **Mechanistic-model → novel-prediction generator** — assemble the belief graph's causal/mechanistic edges into an *executable* qualitative model (sign/direction propagation, Boolean/logical-network style), then enumerate predicted relationships the literature has NOT yet stated (edges *implied* by composing known edges but never directly reported), rank by testability×VoI, and queue the top ones as falsifiable hypotheses | Moves Persona from *auditing existing claims* to *generating novel testable ones* — the "does things not possible before" bar. Distinct from #115 negative-space (graph *holes*) and #411 (DAG *construction*): this **runs** the model to derive *implied* predictions, then routes them into the acting loop | kg causal/mechanistic edges (FC-3 DEPENDS_ON); #254 pathway assembly + #411 causal-DAG as inputs; value_queue (FC-4) + testability (#336); logical-network sign-propagation | 3 | L | H |
| 520 | **Prospective forecasting mode (predict-then-reveal on the live front)** — for a live-moving front, Persona commits a DATED, sealed prediction about what the next N papers will find (direction/effect/replication), then auto-grades when they land; a public forward-looking track record | Turns the standing colleague (PRD-35) into a *forecaster* — foresight, not retrieval. Distinct from #67 (retrospective foresight-backtest) and #17 (prediction ledger on own hypotheses): this forecasts the **external literature's future**, the sharpest possible calibration signal a PI can trust | trajectory.py velocity/inflection (PRD-03 F3.4); prediction-ledger (FC-17) sealing/Brier; standing-colleague front-move detection (FC-27); FIRE-Bench foresight framing | 1+4 | L | H |
| 521 | **Assumption-graph (load-bearing tacit assumptions)** — beyond claim→claim dependencies, extract the *tacit assumptions* a field's conclusions rest on (e.g. "assumes the mouse model translates", "assumes linear dose-response", "assumes the surrogate predicts the outcome") and map which conclusions collapse if an assumption fails — a layer *beneath* the claim graph | The dependency graph shows which claims rest on which claims; it can't show the field's *hidden foundations*. An assumption→many-claims map is where a whole subfield quietly rests on one untested premise — the deepest expression of the load-bearing thesis | dependency/fragility (FC-4) as the claim-layer analog; audit.py `_EXTRACT` limitations pattern (#106); Toulmin warrants (#383); BUILD_PLAN §3.2 | 3 | L | H |

## Wave 8r — 2026-07-13 iter 157 (fresh, direct — acting-loop economics: what to run, in what order, when to stop)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 522 | **Experiment-portfolio optimizer** — given a budget + the value-queue of runnable tests (in-silico + public-data + wet-lab via PRD-34), pick the PORTFOLIO that maximizes expected total belief-uncertainty-reduction per dollar under the budget (submodular/knapsack), accounting for CORRELATED tests (two tests of the same load-bearer are redundant) | Distinct from EIG-ranking (#99, ranks singly) and Pareto swarm-sizing (#5, sizes the reader team): this SELECTS across heterogeneous test types with a budget + redundancy penalty — the missing "which set of experiments" layer of the acting loop | value_queue/VoI (FC-4); cost-of-wrong (#25); wet-lab (FC-26); submodular coverage; budget.py | 3+1 | M | H |
| 523 | **Result-contingent replanning (adaptive experiment sequencing)** — sequence the acting loop as a decision tree/rollout where each test's result reshapes what runs next, stopping early when a belief resolves — don't pre-commit the whole batch | Turns the value queue from a static list into an adaptive policy; a resolved belief mid-batch cancels its now-redundant downstream tests, saving spend. Distinct from #468 (sequential testing *within* one experiment) — this is sequencing *across* experiments | value_queue (FC-4); #468 sequential-testing; investigation.py loop; POMDP/rollout framing | 1 | M | M |
| 524 | **Stakes-tied evidence-sufficiency stopping rule** — a principled "we know enough" gate: stop reading/testing a question when the marginal expected belief-change per dollar drops below a threshold TIED TO the decision stakes (a load-bearer under a drug program keeps a lower stop-threshold than an academic curiosity); surface "further evidence unlikely to change the conclusion" honestly | Distinct from #309 (generic diminishing-returns stop): this ties the stop to DECISION consequence × calibrated marginal-change, so cheap questions stop early and high-stakes ones keep going — honest resource discipline the always-on system needs | budget.py; cost-of-wrong VoI (#25); calibrate (FC-5) marginal-change; BUILD_PLAN §3.4 | 1+2 | M | H |

## Wave 8s — 2026-07-13 iter 158 (fresh, direct — long-horizon self-integrity: keeping the persistent self honest over months)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 525 | **Half-life-aware active refresh scheduler** — schedule each belief's re-verification by its ESTIMATED half-life (fast-moving subfield + low-independence + stale-last-support → refresh soon; settled + high-independence → rarely), maximizing belief-freshness per reading-dollar instead of a fixed revisit cadence | Distinct from #94 (estimates the half-life) and #43 (staleness *heat* viz): this is the SCHEDULER that ACTS on it — the persistent self stays current where it matters and doesn't waste budget re-reading settled facts. The durable-self differentiator made economical | evidence half-life (#94); staleness `history.stale_claims` (FC-2 F2.9); revisit/`staleness` task (FC-1); daemon supervisor cadence | 1+2 | M | H |
| 526 | **Whole-graph self-consistency sweep** — periodically audit the ENTIRE belief-state for logical incoherence at scale: transitivity violations (A→B, B→C, but A⊄C), unflagged sign contradictions, orphaned inferences whose premises were retracted — and file typed repair tasks | Distinct from #354 (one transitive relation) and #308 (a belief SET): a standing WHOLE-GRAPH integrity sweep is what keeps a months-old self from silently accumulating incoherence. The self-audit dogfood (#30) applied to logical structure, not prose | kg graph (FC-3); INFERRED-edge premises; #354 transitive-inference; argumentation semantics (#80); reuses `history` | 2 | M | H |
| 527 | **Evidence-rot detector (silent source degradation)** — flag beliefs whose supporting SOURCES have degraded since admission short of retraction: link-rot (dataset/URL gone), a superseded preprint→published version with CHANGED numbers, a silent dataset re-version | Distinct from the retraction-watcher (#33/PRD-27, catches *retractions*): a belief's evidence can ROT silently — the preprint it cited now reads differently in the journal version, the GEO dataset was re-processed. Nothing re-checks that the evidence still says what it said at admission | FC-6 contamination; source-integrity hashing at ingest (#312); preprint→published linkage; sessions `input_sha256`; ingest/retraction.py | 2+3 | M | H |

## Wave 8t — 2026-07-13 iter 159 (fresh, direct — agent-ecosystem positioning + self-modification safety)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 528 | **Competitive self-positioning scoreboard** — run Persona head-to-head against the NAMED competitors (PaperQA2, scite, Open Targets, MedKGent) on shared tasks (LitQA2/BixBench/AstaBench), track where it wins/loses per capability, and auto-file an improvement task wherever it loses | The competitor list in CLAUDE.md is currently rhetoric; this makes it a LIVE scoreboard + improvement driver. Distinct from #68 self-ablation (internal component eval): this is EXTERNAL competitive benchmarking — the honest "are we actually better, and where aren't we?" a PI/funder asks | CLAUDE.md competitive set; AstaBench/LitQA2/BixBench fixtures (resolution 15); eval/*; value_queue for the improvement tasks | 4 | M | H |
| 529 | **Untrusted cross-agent claim import through the membrane** — consume another research agent's / external KG's claims as UNTRUSTED external evidence that must cross the SAME membrane as any source (never auto-trusted), with the source agent's measured track-record as an independence/trust modifier | Interop WITHOUT contamination — the inverse of belief-state export (#477/#478): importing others' conclusions is how a lab compounds, but only if they cross the discipline of believing. A foreign claim is a READ source, never a shortcut past the membrane | membrane admission (FC-2/FC-5); independence groups (FC-3); prompt-injection/untrusted-input discipline (CLAUDE.md); #529 pairs with #517 signed replication | 2+3 | M | H |
| 530 | **Self-upgrade capability-regression gate** — when Persona's OWN code/prompts/config change (a lane ships a PRD), auto-run the frozen competitive + oracle benchmark suite and BLOCK the change if any capability regressed — a self-CI gate for the researcher's own competence | As lanes 1–4 start shipping, nothing guarantees a change doesn't silently degrade a capability (membrane precision, calibration, extraction). Ties #492/#494 (integration/money-shot regression) into a HARD gate on self-modification — the safety rail an always-improving system needs | frozen-evaluator harness (RQ-E10); #492 full-vision integration test + #494 money-shot regression; ablation harness (#68); eval/* + CI | 4 | M | H |

## Wave 8u — 2026-07-13 iter 161 (fresh, direct — decision-support under uncertainty: beliefs → actions)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 531 | **Expected-regret action recommender** — for a decision a stakeholder faces (pursue target X? trust surrogate Y as an endpoint?), recommend the action minimizing EXPECTED REGRET given Persona's calibrated beliefs + the stakeholder's stated loss asymmetry, and surface the belief whose resolution would most change the recommendation (decision-relevant VoI) | Distinct from EIG-ranking (#99, ranks questions by belief-uncertainty-reduction): this ranks by DECISION impact and recommends an ACTION under uncertainty — the translational last mile a PI/program-lead actually needs. Turns the belief-state into decisions, not just conclusions | calibrated_p (FC-5); VoI/value_queue (FC-4); cost-of-wrong (#25); decision theory (min expected regret); confidence report card (FC-25) | 3+4 | M | H |
| 532 | **Decision-boundary sensitivity ("what would flip the recommendation")** — for a recommendation, compute how much each supporting belief would have to change to flip the decision, surfacing the recommendation's fragility + the CHEAPEST evidence that could overturn it | Distinct from the belief-graph fragility cascade (#26/FC-4): this operates at the DECISION/recommendation level — "your go/no-go rests on one contested effect size; here's the $200 test that would settle it." The honest-uncertainty story applied to actions | fragility_cascade (FC-4); #531 recommender; calibrate marginal-change (FC-5); value_queue for the flipping test | 3+4 | M | H |
| 533 | **Stakeholder loss-function elicitation + anchoring** — a structured way for a human to state a decision's ASYMMETRIC costs (cost of a false-pursue vs a false-abandon of target X), stored as an anchored HUMAN_CONFIRMED preference that every recommendation respects — never a Persona-invented loss function | Human-as-resolver (CLAUDE.md §7) applied to VALUES, not just facts: Persona must not fabricate the stakeholder's risk tolerance any more than it fabricates confidence. Anchoring a loss function is exactly the high-stakes human input the membrane already protects (100% vs 71%) | anchoring/HUMAN_CONFIRMED (validated); inbox/handoff (FC-2); #531 consumes it; delegation-up board (#86) | 2+4 | M | H |

## Wave 8v — 2026-07-13 iter 162 (fresh, direct — hypothesis-quality flywheel: make generated hypotheses measurably GOOD)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 534 | **Hypothesis-quality scorecard (novelty × plausibility × testability × impact)** — score every generated hypothesis on 4 GROUNDED axes before spending: novelty = distance from existing claims; plausibility = mechanistic-path support; testability = data availability; impact = downstream load-bearing — and route budget to the high-scorers | Distinct from #350 (novelty alone) and #336 (testability alone): the INTEGRATED pre-spend gate that stops the swarm chasing obvious/untestable/low-impact hypotheses. As #519/#30/#348 all generate hypotheses, this is the quality filter they all feed | novelty vs claim vectors; mechanistic path (#519); testability (#336); load-bearing (FC-4); value_queue | 3 | M | H |
| 535 | **Generation-strategy attribution (which idea-source produces VALIDATED hypotheses)** — track, per generation strategy (contradiction-derived / mechanistic-composition #519 / negative-space #30 / analogy #348), how often its outputs survive testing, and reallocate generation effort to the strategies that actually produce validated beliefs | The meta-learning loop for scientific creativity — distinct from #302 (method-effectiveness, general): this attributes VALIDATED-belief yield to the hypothesis SOURCE, so Persona learns *how it best has ideas*. A researcher improving its own ideation | prediction-ledger (FC-17) outcomes; verified ledger; #302; the generators (#30/#348/#519) | 1+3 | M | H |
| 536 | **Surprise-worthiness gate for spawned hypotheses** — before committing to chase a self-generated hypothesis, check it's genuinely surprising/non-obvious (not trivially implied, not a known/already-settled result) — filter the "generates lots but they're all obvious" failure mode | The generators can produce volumes of trivial "predictions"; this gates on the surprise signal (F1.6/RQ-E18) so budget goes to non-obvious hypotheses. Complements #534's quality score with a specific anti-triviality check | surprise/embedding-novelty (PRD-01 F1.6, RQ-E18); kg existing claims; #519 implied predictions as the main input | 1 | S | M |

## Wave 8w — 2026-07-13 iter 163 (fresh, direct — bring-your-own-evidence: Persona as a lab collaborator, not just a literature reader)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 537 | **Lab-private evidence ingestion (bring-your-own-data)** — the PI uploads unpublished results / in-house datasets / lab-notebook claims; Persona ingests them as a DISTINCT provenance class (`HUMAN_PROVIDED`, untrusted like any source, prompt-injection-guarded), reconciles them against the public-literature belief-state, and flags where the lab's private data agrees/contradicts the field | Turns Persona from a literature reader into a LAB COLLABORATOR — the single biggest usefulness jump for a working scientist. Distinct from #529 (another AGENT's claims): this is the HUMAN's own bench data, the evidence a PI most wants reconciled against the world | membrane admission (FC-2/FC-5); provenance typing (add `HUMAN_PROVIDED`); untrusted-input discipline; uploads-inform-RAG (commit 30d8302) | 2+3 | L | H |
| 538 | **Private/public divergence dossier** — when the PI's private data CONTRADICTS the published consensus, generate a structured dossier: is the field wrong, or is the lab's result an artifact? which experiment would discriminate? — the single highest-value moment for a working scientist | The reason a PI would pay for this — "my result disagrees with the literature, help me figure out who's right." Distinct from cross-persona reconcile (#44, two Personas): this is private-bench-vs-public-consensus, routed into the acting loop (what test settles it?) | #537 ingestion; conflict dossiers (FC-2); reconcile (FC-9); value_queue discriminating-test (FC-4) | 2+4 | M | H |
| 539 | **Confidentiality-tiered belief partitioning** — private lab evidence and the beliefs it supports are tagged `confidential` and NEVER leak into shared exports / published deliverables / the belief-state API without explicit human release; a hard partition enforced at every egress | The security discipline that makes #537 usable at all — a PI will not upload unpublished data unless leakage is structurally impossible. A hard egress gate (deliverables, RO-Crate export, belief-state API, cross-persona share all check the tier) | belief-state export (#477); RO-Crate (PRD-04); belief-state API (#479); membrane provenance; access-control (#422) | 2 | M | H |

## Wave 8x — 2026-07-13 iter 164 (fresh, direct — active reading strategy: acquire evidence like a strategic scientist, not a crawler)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 540 | **Citation-frontier crawling strategy** — instead of keyword search, follow the CITATION graph strategically: from a load-bearing claim, fetch its most-cited descendants + the papers that CITE-AND-DISPUTE it (contradiction-seeking traversal), prioritizing the frontier where the argument is actually moving | Distinct from #39 (adaptive depth *within* a paper): this decides WHICH papers to fetch next, graph-guided — reading toward where the field is contested/moving instead of a flat keyword sweep. Strategic acquisition, the scarce-attention discipline | citation edges (OpenAlex/EuropePMC); load-bearing (FC-4); contradiction-seeking; reader.py fetch queue | 1+3 | M | H |
| 541 | **Corpus-saturation estimator (when have I read enough?)** — estimate per question/subfield whether the swarm has read a representative sample (capture-recapture on entities/claims; new-claims-per-paper decay), so Persona knows when reading MORE won't move the belief and stops | Distinct from #426 (coverage-gap *map*): this is a STOPPING signal for reading — the honest "further reading unlikely to change the conclusion" that bounds budget. The reading-side analog of #524's stakes-tied test-stopping | new-claim yield per paper; capture-recapture (ecology estimator); membrane admit rate; budget | 1+3 | M | H |
| 542 | **Seminal-vs-derivative source discrimination** — identify the FOUNDATIONAL papers a claim's whole subtree rests on (vs derivative restatements) and concentrate deep-reading + robustness-auditing on THOSE, since a field's load-bearing evidence concentrates in a few originals | Distinct from claim-level load-bearing (FC-4): this is at the SOURCE level — which *paper* is foundational. Auditing the 3 originals a subfield rests on is higher-leverage than auditing 300 citations of them; routes the auditor's scrutiny where it pays off | dependency graph (FC-4); citation-vs-support (FC-3); robustness auditor (audit.py); #58 robustness-trigger | 3 | M | H |

## Wave 8y — 2026-07-13 iter 165 (fresh, direct — cross-evidence-type integration: combine incommensurable evidence like a rigorous synthesist)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 543 | **Evidence-type-weighted belief aggregation** — when a belief is backed by HETEROGENEOUS evidence types (GWAS + RCT + mechanistic + case report + RWE), aggregate into ONE calibrated confidence with weights CALIBRATED to each type's historical reliability (an RCT empirically counts more than a case report), not counting sources equally | The membrane currently counts independent sources; it does not weight by DESIGN. A rigorous synthesist knows a case report ≠ an RCT. Type-calibrated weighting makes "no fabricated confidence" reflect evidence QUALITY, not just quantity | independence counts (FC-3); calibrate (FC-5); causal-tier (FC-10); GRADE (#382); RCT-vs-RWE concordance (#73) | 2 | M | H |
| 544 | **Evidence-triangulation bonus** — when INDEPENDENT evidence TYPES converge (a genetic signal + a mechanistic study + a trial all point the same way), award a triangulation bonus a pile of same-type studies can't earn — convergence across methods with DIFFERENT biases is the strongest signal | Metascience's strongest reliability argument (Munafò & Davey Smith triangulation): agreement across methods whose biases are orthogonal. Distinct from #543 (weighting each type): this rewards cross-METHOD agreement — the thing that most justifies confidence | triangulation (Nature 2018 Munafò/Davey Smith); independence-by-method (FC-3 extended); calibrate (FC-5); #543 pairs with it | 2 | M | H |
| 545 | **Evidence-type gap identifier** — for a load-bearing belief, identify which evidence TYPE is missing (e.g. "strong observational + mechanistic, but NO causal/genetic evidence") and route the highest-value gap-filling (an MR run, a knockout oracle) into the acting loop | Distinct from #115 negative-space (missing graph EDGES): this finds missing evidence-TYPES for an EXISTING belief — the "what kind of study would most strengthen this?" a reviewer asks. Turns a confidence gap into a concrete next action | evidence-type map per belief; MR/DepMap/molecular oracles (FC-8); value_queue (FC-4); #543/#544 | 3 | M | H |

## Wave 8z — 2026-07-13 iter 166 (fresh, direct — cold-start / new-field competence: start competently + honestly on unfamiliar ground)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 546 | **Rapid field-mapping cold-start** — on a new question with zero prior reading, run a bounded RECONNAISSANCE pass (a few high-citation reviews + the most-cited primaries) to build a competent INITIAL map — key claims, main camps, open questions — before committing deep budget. Scout-then-commit | A researcher entering a new field reads the reviews first, not random primaries. Distinct from #108 (seed critique — sharpens the *question*): this is the initial *acquisition strategy* that avoids burning budget wandering. Pairs with citation-frontier crawling (#540) | reviews-first heuristic; citation counts (OpenAlex); reader budget; fieldmap; #540 crawling | 1 | M | H |
| 547 | **Coverage-conditioned confidence (calibrated ignorance)** — when Persona has read little in an area, it must SAY SO — wide uncertainty + "I've read only N papers / M% of the estimated corpus here" — never present thin beliefs with the authority of well-read ones | Distinct from evidence-count calibration (#16): this conditions confidence on READING COVERAGE. The honest "I don't know this field well yet" a trustworthy colleague volunteers — prevents the most damaging cold-start failure: confident wrong beliefs from a thin read | corpus-saturation (#541); calibrate (FC-5); provenance; honest-uncertainty UI (CLAUDE.md §5) | 2+4 | M | H |
| 548 | **Analogical warm-start from a mastered field** — entering a new field structurally similar to a well-known one, transfer the STRUCTURE (which questions matter, what failure modes to expect, which evidence types to weight) as priors — with a fidelity check so a bad analogy doesn't mislead | Distinct from #178 (cross-domain METHOD transfer): this transfers the RESEARCH STRATEGY/structure — a warm-start prior on how to investigate, not what technique to use. Speeds cold-start while the fidelity check (#319) guards against forced analogies | #178 method transfer; #319 fidelity-checked analogy; strategies.md; interest-graph | 1+3 | L | M |

## Wave 9a — 2026-07-13 iter 167 (fresh, direct — swarm coordination intelligence: the team's own failure modes + memory)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 549 | **Collective-blindspot detector** — detect when the WHOLE swarm shares a systematic blind spot (all readers miss the same evidence class — non-English, negative results, an untouched subfield) by comparing coverage against an external reference distribution | Every current check is per-claim or per-reader; nothing catches a TEAM-level gap where every agent is blind the same way. The unknown-unknown of a reading swarm — what the whole team never looks at | coverage-gap map (#426); external reference (OpenAlex field distribution); per-subfield saturation (#123); membrane admit stats | 1+3 | M | H |
| 550 | **Correlated-error firewall (illusory-independence discount)** — when multiple readers/verifiers make the SAME mistake (shared prompt bias, same base model), their "independent" agreement is illusory; detect correlated errors across the swarm and DISCOUNT the apparent convergence at the membrane | The membrane counts independent sources, but model-shared bias silently breaks the independence assumption the whole discipline-of-believing rests on. Turns #237's correlated-error detection into an active membrane discount — a real epistemic fix | independence counts (FC-3); correlated-error detection (#237); verifier-monitor (FC-15); membrane convergence | 1+2 | M | H |
| 551 | **Team-composition memory (case-based swarm recall)** — remember which team compositions (roles, sizes, model tiers) resolved which claim-types well, and reconstitute the winning composition for a similar new task | Distinct from #53 (a learned role/topology router — a policy table): this is CASE-BASED recall of a whole working configuration for an analogous task, the swarm's episodic memory of "what worked last time." Cheaper than re-learning; auditable | outcome ledger; Pareto sizing (FC-24); #53 learned router; strategies.md; warm-start (#402) | 1 | M | M |

## Wave 9b — 2026-07-13 iter 168 (fresh, direct — propagated uncertainty: carry + communicate error through every derivation)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 552 | **End-to-end uncertainty propagation** — when a conclusion is DERIVED from multiple uncertain beliefs (a synthesis, a computed estimate), propagate the input uncertainties through the derivation (Monte-Carlo / interval / delta method) so the OUTPUT carries a real interval, not a point | Distinct from #279 (the primitive): this WIRES propagation through the synthesis/deliverable pipeline so every derived claim inherits honest error bars. A synthesis that states a point where its inputs are uncertain is fabricated confidence one level up | uncertainty propagation (#279); calibrated_p per belief (FC-5); synthesis derivation chains (#31); Bayesian posterior (#222) | 2+3 | M | H |
| 553 | **Sensitivity attribution ("which input drives the uncertainty")** — for a derived conclusion, attribute how much each input belief contributes to the output uncertainty (variance decomposition / Sobol indices), so the value queue targets the input that would most TIGHTEN the conclusion | Distinct from #532 (decision-boundary sensitivity): this is variance attribution on a BELIEF's derivation — "your estimate's uncertainty is 80% driven by one contested effect size; resolve THAT." Turns a wide interval into a ranked to-do | #552 propagation; value_queue/VoI (FC-4); Sobol/variance decomposition; dependency graph (FC-4) | 3 | M | H |
| 554 | **Interval-honest deliverable language** — a review/paper states each derived quantity WITH its propagated interval and refuses to state a bare point estimate where the interval is wide (falls back to "between X and Y" or "too uncertain to quantify") | Extends #104 (confidence-conditioned language) to DERIVED numbers: the prose never launders a wide interval into a confident point. The output-side enforcement of #552, checkable like the faithfulness gate (PRD-39) | #552 propagation; confidence-conditioned language (#104); explanation-faithfulness (PRD-39); deliverables | 3+4 | M | M |

## Wave 9c — 2026-07-13 iter 169 (fresh, direct — peer-review lifecycle as evidence: the post-publication signal Persona ignores)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 555 | **Post-publication commentary ingestion** — ingest PubPeer / letters-to-editor / open-review comments / concern notices as a DISTINCT evidence channel; a paper's post-pub discussion (concerns raised, unresolved) modifies its trust, always typed weak/contested | Distinct from the retraction-watcher (#33/PRD-27, catches the RETRACTED endpoint): this catches the far more common WEAKER signal — a paper publicly contested but not (yet) retracted. The earliest warning that a load-bearing source is shaky, a channel the competitive set never reads | PubPeer API; retraction-watcher (FC-19); audit adjudicator trust modifier; contamination (FC-6) | 3 | M | H |
| 556 | **Open-review consensus signal** — where open peer reviews exist (eLife, F1000Research, preprint-review platforms), extract the reviewers' assessment as a trust modifier — did the reviewers flag the EXACT claim Persona relies on as weak/unsupported? | The reviewers already did expert scrutiny Persona can reuse for free; keying it to the specific claim (not the whole paper) is the high-resolution win. A sourced, expert trust signal orthogonal to citations and the code-run forensics | eLife/F1000 open-review APIs; audit.py adjudicator; exact-span claim linking; #555 pairs with it | 3 | M | M |
| 557 | **Preprint→publication delta tracker** — when a preprint Persona cited becomes a journal publication, DIFF them (did the effect size / claims / conclusions change through review?) and re-check any belief resting on the preprint version | Distinct from evidence-rot (#527, general silent degradation): this targets the specific, high-frequency, high-value preprint→published transition where numbers quietly change through peer review. A belief anchored on a preprint that the journal version walked back is exactly the silent corruption nothing catches | preprint↔published linkage; source-integrity hashing (#312); evidence-rot (#527); membrane re-check | 2+3 | M | H |

## Wave 9d — 2026-07-13 iter 170 (fresh, direct — cross-scale reasoning + the translation gap: biomedicine's real failure axis)

| # | Idea | Why | Evidence | Lane | Effort | Lev |
|---|---|---|---|---|---|---|
| 558 | **Cross-scale consistency check** — for a mechanistic claim, check consistency across biological SCALES (a molecular mechanism should cohere with the cellular phenotype, the animal model, and the human epidemiology); flag when scales disagree (works in vitro, fails in vivo) | Distinct from triangulation (#544, cross-METHOD at one scale): this is cross-SCALE coherence — the axis where biomedical claims most quietly break. A molecular story with no phenotype, or an animal effect absent in humans, is exactly the internally-consistent-but-wrong claim Persona should catch | KG scale-tagged claims; mechanistic model (FC-31); triangulation (#544); dependency graph (FC-4) | 3 | M | H |
| 559 | **Translation-gap detector (bench→bedside break)** — pinpoint WHERE a claim's evidence chain breaks across the translational gap (strong molecular + animal, but no human data / a failed trial) and WHY, not just that it exists | Distinct from #396 (bench-to-bedside tracking, descriptive): this LOCATES the break + attributes cause, routing the highest-value gap-fill. The commonest, costliest failure in biomedicine (>90% of preclinical successes fail in humans) made legible | evidence-type gap (#545); clinical-trial WhyStopped (PRD-03 F3.9); #558 cross-scale; value_queue (FC-4) | 3 | M | H |
| 560 | **Model-organism applicability prior** — for a claim from a model organism (mouse/yeast/zebrafish/organoid), attach a CALIBRATED prior on how often that model translates to humans for THIS class of claim/pathway, and widen confidence accordingly | Distinct from #73 (RCT-vs-RWE concordance): this is model-organism→human translation, a known, quantifiable moderator the auditor ignores. Turns "it's a mouse study" from a vague caveat into a sourced, calibrated confidence adjustment | model-organism translation-rate literature; calibrate (FC-5); audit `_field_base` (#36); causal-tier (FC-10) | 2+3 | M | M |

## Parking lot (unranked; promote when relevant)
- Canonicalizer ANN index for scale (`canon.py` O(n) scan) — map, L3-adjacent, S.
- Per-host rate-limit for `web.fetch_url` (currently unthrottled) — ingest map, S.
- Surface sandbox image-digest + forensic engine-fingerprint on human-facing report cards — sessions map, S.
- Auto-generate a review when a community first crosses a size/claim threshold — synthesis map, S.
- Debiased disruption/CD index as a trajectory-shape feature (show the metric *and* its known bias) — research, M.
- Process-level self-scoring over the living-notebook trajectory (BiomniBench-style: where in the loop did it fail) — research, M.
- PaperBench/SUPER rubric decomposition + judge-validation for replication verdicts (per-leaf pass rates) — research, L.
- SciClaimHunt_Num + SciVer as numerical/figure-claim auditor oracles — research, M.

## Loop protocol
Each ideation iteration: (1) scan the HANDOFF dispatch table for lane progress/blockers; (2) if a lane is idle or a contract dispute is open, produce the unblocking decision/spec; (3) append ≥2 new dated ideas here (pull fresh literature when a front is stale); (4) re-rank; (5) prune shipped/killed. Never end an iteration with nothing appended.

_Log:_
- 2026-07-12 — seeded Wave 2 (15 ranked + parking lot) from the subsystem maps + 6 research fronts.
- 2026-07-12 iter 2 — lanes 1–4 READY-TO-CLAIM, no open blockers (15 cross-lane OQs resolved). Added Wave 2b #16–18 (self-calibration reliability panel, prediction ledger + Brier self-score, evidence-tree diff). Nothing shipped yet → no prune.
- 2026-07-12 iter 3 — continuous mode. Added Wave 3a #19–32 (meta-analysis agent, causal-strength gate, corpus p-curve, effect-size harmonizer, prereg awareness, null-hunt swarm, cost-of-wrong VoI, fragility simulator, reviewer-disposition lens, provenance passport, live-front tracker, self-audit dogfood, typed premise→inference chains, budget optimizer). Launched 8-lens sweep for Wave 3b (~40 ideas incoming). Loop tightened to continuous fan-out cadence.
- 2026-07-12 iter 4 — Wave 3b sweep still running; added Wave 3a-cont #33–44 directly (retraction watcher, funding/COI signal, unit-consistency check, adjustable base-rate panel, contradiction independence pre-check, "explain this number" drill-down, adaptive reading depth, concept-drift detector, self-preregistration primitive, devil's-advocate section, staleness heat, cross-persona reconciliation). 44 ranked ideas total. Wave 3b will append on sweep completion.
- 2026-07-12 iter 5 — Wave 3b appended (24 ideas from 8-lens sweep); PRD-05..10 authoring launched for top items.
- 2026-07-13 iter 6 — Wave 3c appended (20 ideas: clinical/RWE, structural biology, knowledge-representation, human-AI collaboration).
- 2026-07-13 iter 7 — PRD-11..15 authoring (contradiction-gold UI, causal gate, fragility sim, sleep-consolidation, calibration panel). Light cycle: added Wave 3d #89–92 directly (contradiction triage board, oracle control-injection, confidence-budget accounting, cross-modal claim linking). 92 ranked ideas. Backlog large → next re-rank + prune-on-first-ship pending.
- 2026-07-13 iter 8 — PRD-11..15 still authoring. Added "Promoted to PRDs" traceability index (15 PRDs mapped) + Wave 3e #93–95 (provenance-aware model routing, evidence half-life, adversarial-collaboration protocol). 95 ideas. Idea generation ahead of consumption — future light cycles favor curation/PRDs over new sweeps.
- 2026-07-13 iter 9 — PRD-11..15 posted (READY-TO-CLAIM); launched PRD-16..20 (oracle control-injection, FDA surrogate gate, LEGEND RWE probe, null-hunt swarm, confidence-budget). Added Wave 3f #96–98 (time-travel belief replay, ontology reconciliation, reviewer confidence report card). 98 ideas · 20 PRDs.
- 2026-07-13 iter 10 — PRD-16..20 authoring. Light cycle: added a "Next up for PRD promotion" curation list + Wave 3g #99–101 (expected-info-gain question ranking, counterfactual literature simulation, auto protocol/registered-report drafting). 101 ideas.
- 2026-07-13 iter 11 — PRD-16/18/19/20 written, PRD-17 finishing. Added Wave 3h #102–104 (reader-adaptive explanation depth, standing adversarial/chaos pipeline audit, confidence-conditioned deliverable language). 104 ideas. Batch-4 OQ resolution pending PRD-17 completion notification.
- 2026-07-13 iter 12 — batch-4 (PRD-16..20) resolved + posted (FC-12/FC-13, FC-8 additions, RQ-E30..E34). Implementation now the binding constraint (no lane CLAIMED yet) → paced to a 3-PRD batch: launched PRD-21..23 (cross-field translation, verifier-calibration monitor, SemMedDB). Added Wave 3i #105–107 (steel-man/counter viewer, method-limitations extractor, belief portfolio-risk report). 107 ideas · 23 PRDs.
- 2026-07-13 iter 13 — PRD-21..23 authoring. Created `docs/prd/IMPLEMENTER_START_HERE.md` (per-lane M0 + first-fill order across all 23 PRDs) to attack the implementation bottleneck. Added Wave 3j #108–110 (onboarding seed critique, PROV-O export, field-adaptive membrane thresholds). 110 ideas.
- 2026-07-13 iter 14 — batch-5 (PRD-21..23) resolved + posted (FC-14/15/16, RQ-E35..E37, CCP-21a/22a/23a). Dispatched a spec-coherence audit over PRD-00 + all 23 PRDs + HANDOFF (FC/RQ uniqueness, ownership conflicts, dangling refs). Added Wave 3k #111–113 (contradiction resolution playbook, auto "so what" impact line, compute cost+carbon transparency). 113 ideas · 23 PRDs.
- 2026-07-13 iter 15 — coherence audit still running (fix findings on completion). Added Wave 3l #114–116 (research-frontier map artifact, negative-space hypothesis generation, calibration-weighted persona ensembling). 116 ideas. Cross-wave re-rank deferred to post-audit.
- 2026-07-13 iter 16 — coherence audit RESOLVED: PRD-00 §8 reconciliation (§4/§6 govern PRD bodies) + closed 2 real source collisions (E15 dual-use → E39; E16/E17 swap → VoI=E17, forensics=E38); `depmap_oracle` disambiguated; config `OPENGWAS_JWT` sanctioned; START_HERE points to §8. Program now provably coherent. 116 ideas · 23 PRDs · FC-1..16 · RQ to E39.
- 2026-07-13 iter 17 — created `docs/prd/PROGRAM_SUMMARY.md` (one-page human-facing overview: 23 PRDs by capability, differentiators, honest state, how-to-proceed). Added Wave 3m #117–119 (Persona publishes its own preprint, meta-research self-study, teaching-signal capture for the learning loop). 119 ideas. Backlog saturating → future cycles emphasize curation/summary + paced PRD promotion over raw generation.
- 2026-07-13 iter 18 — refreshed "Next up for PRD promotion" (dropped #4/#6/#8 now promoted; added #100/#114/#115/#118). Added Wave 3n #120–122 (end-of-day budget triage, contradiction aging escalation, multi-modal anchoring bar). 122 ideas.
- 2026-07-13 iter 19 — launched PRD-24..27 (prediction-ledger+Brier, claims-blocklist, counterfactual-literature-sim, live-retraction-watcher) with RQ-E40..E43 pre-assigned to head off collisions. Added Wave 3o #123–125 (living entity cards, cross-persona peer review, evidence-tier upgrade pathway). 125 ideas · 27 PRDs (24–27 authoring).
- 2026-07-13 iter 20 — PRD-24..27 authoring. Added Wave 3p #126–128 (protocol-cost estimator, living-notebook replay scrubber, interest-graph visualization). 128 ideas. Batch-6 OQ resolution pending PRD-24..27 completion.
- 2026-07-13 iter 21 — batch-7 (PRD-24..27) resolved + posted: FC-17/18/19 (three-way FC-17 collision fixed), FC-3/FC-4 additions, CCP-24a/25a/26a/26b/27a, RQ-E40..E43 (pre-assignment held — no RQ collision). Program: 27 PRDs · FC-1..19 · RQ to E43 · 55 master resolutions · 128 ideas.
- 2026-07-13 iter 22 — launched PRD-28..31 (EIG question ranking, research-frontier map, negative-space hypotheses, evidence-tier upgrade pathway) with FC-20..23 + RQ-E44..47 BOTH pre-assigned (fixes the FC-collision pattern too). Added Wave 3q #129–131 (assumption-inversion stress test, citation-context drift, "diff since you last looked" digest). 131 ideas · 31 PRDs (28–31 authoring).
- 2026-07-13 iter 23 — PRD-28..31 authoring (1/4). Added Wave 3r #132–134 (inter-instance belief federation, governance audit trail for anchors, explanation-faithfulness check). 134 ideas. Batch-8 resolution pending completion (pre-assigned FC/RQ → expect minimal).
- 2026-07-13 iter 24 — batch-8 (PRD-28..31) resolved + posted: FC-20..23 + RQ-E44..46 held with ZERO collisions (double pre-assign is the fix; adopt for all future batches). CCP-29a/30a advisory→L1. Program: 31 PRDs · FC-1..23 · RQ to E46 · 60 resolutions · 134 ideas.
- 2026-07-13 iter 25 — lean cycle: refreshed "Next up for PRD promotion" (dropped 7 items now promoted as PRD-24..31). Added Wave 3s #135–137 (strategy self-tuning from outcomes, dead-end/rabbit-hole detector, provenance-aware history compression). 137 ideas.
- 2026-07-13 iter 26 — lean cycle (context-paced): added Wave 3t #138–140 (multi-format deliverable export, belief-graph snapshot versioning, reviewer trust-onboarding tour). 140 ideas. PRD promotion paced (31 unclaimed); next batch = #5/#98 with FC-24+/RQ-E47+ pre-assigned.
- 2026-07-13 iter 27 — launched PRD-32..33 (Pareto swarm-sizing #5 = FC-24/RQ-E47; confidence report card #98 = FC-25/trivial), pre-assigned. Added Wave 3u #141–143 (contradiction resolution betting, auto falsification checklist, human-expertise routing). 143 ideas · 33 PRDs (32–33 authoring). Resolve on completion.
- 2026-07-13 iter 28 — PRD-32..33 authoring. Added Wave 3v #144–146 (time-to-first-insight metric, contradiction cluster detection, provenance-preserving translation). 146 ideas.
- 2026-07-13 iter 29 — batch-9 (PRD-32..33) resolved + posted: FC-24/25 + RQ-E47 held (no collision); PRD-33 band vocab → one shared Lane-4 set. Program: 33 PRDs · FC-1..25 · RQ to E47 · 60+ resolutions · 146 ideas.
- 2026-07-13 iter 30 — minimal cycle (context tight): added Wave 3w #147–149 (uncertainty on every number, salami-slicing/duplicate-cohort detector, belief→hypothesis reversal log). 149 ideas · 33 PRDs.
- 2026-07-13 iter 31 — minimal cycle: added Wave 3x #150–152 (data-availability check, reasoning-chain length budget, cross-claim numerical consistency). 152 ideas · 33 PRDs.
- 2026-07-13 iter 32 — minimal cycle: added Wave 3y #153–155 (interactive assumption toggle, auto peer-review-response drafting, longitudinal field-health index). 155 ideas · 33 PRDs.
- 2026-07-13 iter 33 — minimal cycle: added Wave 3z #156–158 (confidence-delta alerts, reagent/antibody validation check, meta-prompt hygiene guard). 158 ideas · 33 PRDs.
- 2026-07-13 iter 34 — minimal cycle: added Wave 4a #159–161 (identity-drift monitor, belief-graph garbage collection, provenance-weighted retrieval ranking). 161 ideas · 33 PRDs.
- 2026-07-13 iter 35 — minimal cycle: added Wave 4b #162–164 (power pre-check on own tests, external-reviewer invitation, provenance-completeness score). 164 ideas · 33 PRDs.
- 2026-07-13 iter 36 — minimal cycle: added Wave 4c #165–167 (incremental graph recompute, novelty-first read priority, "why this confidence" breakdown). 167 ideas · 33 PRDs.
- 2026-07-13 iter 37 — minimal cycle: added Wave 4d #168–170 (handoff-response SLA tracking, auto minimal-reproducible-example, natural-language belief-graph querying). 170 ideas · 33 PRDs.
- 2026-07-13 iter 38 — minimal cycle: added Wave 4e #171–173 (public error-rate dashboard, graceful-degradation transparency, "what would change my mind" per interest). 173 ideas · 33 PRDs.
- 2026-07-13 iter 39 — minimal cycle: added Wave 4f #174–176 (self-uncertainty introspection, structured methods-section critique, belief-lineage family tree). 176 ideas · 33 PRDs.
- 2026-07-13 iter 40 — minimal cycle: added Wave 4g #177–179 (domain-pack architecture, cross-domain method transfer, question-decomposition planner). 179 ideas · 33 PRDs.
- 2026-07-13 iter 41 — minimal cycle: added Wave 4h #180–182 (belief-obsolescence forecasting, investigation postmortem, multi-persona knowledge commons). 182 ideas · 33 PRDs.
- 2026-07-13 iter 42 — minimal cycle: added Wave 4i #183–185 (figure-claim consistency auditor, citation round-trip verification, confidence-appropriate abstention in Q&A). 185 ideas · 33 PRDs.
- 2026-07-13 iter 43 — minimal cycle: added Wave 4j #186–188 (seed-from-a-paper, interest-conflict detection, auto related-work generation). 188 ideas · 33 PRDs.
- 2026-07-13 iter 44 — minimal cycle: added Wave 4k #189–191 (autonomy escalation ladder, spend-anomaly auto-pause, belief-write audit log). 191 ideas · 33 PRDs.
- 2026-07-13 iter 45 — minimal cycle: added Wave 4l #192–194 (grant-relevance matcher, clinical-trial-design suggester, auto lay-explainer). 194 ideas · 33 PRDs.
- 2026-07-13 iter 46 — minimal cycle: added Wave 4m #195–197 ("on this day" belief recall, trend-vs-noise discriminator, provenance-freshness badge). 197 ideas · 33 PRDs.
- 2026-07-13 iter 47 — minimal cycle: added Wave 4n #198–200 (open-review ledger publication, reproducibility badge minting, contribution-back to ecosystem). **200 ideas** · 33 PRDs.
- 2026-07-13 iter 48 — minimal cycle: added Wave 4o #201–203 (taste-weight introspection, parsimony scoring, surprise log). 203 ideas · 33 PRDs.
- 2026-07-13 iter 49 — minimal cycle: added Wave 4p #204–206 (keyboard-driven evidence navigation, live collaboration presence, export beliefs to reference managers). 206 ideas · 33 PRDs.
- 2026-07-13 iter 50 — minimal cycle: added Wave 4q #207–209 (model-version drift monitor, determinism audit, prompt-version pinning). 209 ideas · 33 PRDs. [50 loop iterations — program complete + coherent; implementation remains the constraint.]
- 2026-07-13 iter 51 — minimal cycle: added Wave 4r #210–212 (adversarial claim-challenge set, human-agreement calibration study, conclusion regression suite). 212 ideas · 33 PRDs.
- 2026-07-13 iter 52 — minimal cycle: added Wave 4s #213–215 (consensus-strength meter, minority-position tracker, disagreement-root attribution). 215 ideas · 33 PRDs.
- 2026-07-13 iter 53 — minimal cycle (context low, awaiting user steer): added Wave 4t #216–218 (investigation checkpoint/resume, partial-result salvage, graceful model-fallback chain). 218 ideas · 33 PRDs.
- 2026-07-13 iter 54 — minimal cycle: added Wave 4u #219–221 (live-preprint monitoring, load-bearer retraction alert, conference-abstract ingestion). 221 ideas · 33 PRDs.
- 2026-07-13 iter 55 — minimal cycle: added Wave 4v #222–224 (automated sensitivity analysis, Bayesian posterior per belief, units-aware numerical-claim extraction). 224 ideas · 33 PRDs.
- 2026-07-13 iter 56 — minimal cycle: added Wave 4w #225–227 (extraction-confidence gating, figure/table-text extraction, multilingual ingestion). 227 ideas · 33 PRDs.
- 2026-07-13 iter 57 — minimal cycle: added Wave 4x #228–230 (synthesis-hallucination hard gate, contradiction-aware synthesis, evidence-density heatmap). 230 ideas · 33 PRDs.
- 2026-07-13 iter 58 — minimal cycle: added Wave 4y #231–233 (mechanistic pathway assembly, dose-response consistency check, confounder checklist per causal claim). 233 ideas · 33 PRDs.
- 2026-07-13 iter 59 — minimal cycle: added Wave 4z #234–236 (hierarchical memory tiers, query-intent retrieval routing, recency-decayed retrieval). 236 ideas · 33 PRDs.
- 2026-07-13 iter 60 — minimal cycle: added Wave 5a #237–239 (work-stealing across investigations, reducer-bottleneck detection, correlated-error detection across readers). 239 ideas · 33 PRDs.
- 2026-07-13 iter 61 — minimal cycle: added Wave 5b #240–242 (executable notebook deliverable, interactive dependency-graph embed, version-diffed re-releases). 242 ideas · 33 PRDs.
- 2026-07-13 iter 62 — minimal cycle: added Wave 5c #243–245 (dual-use/harm screening, bias-in-evidence audit, consent-aware data handling). 245 ideas · 33 PRDs.
- 2026-07-13 iter 63 — minimal cycle: added Wave 5d #246–248 (funnel-plot/Egger publication-bias test, trim-and-fill correction, outcome-switching detector). 248 ideas · 33 PRDs.
- 2026-07-13 iter 64 — minimal cycle: added Wave 5e #249–251 (batch-API smart routing, cross-persona extraction cache, speculative citation pre-fetch). 251 ideas · 33 PRDs.
- 2026-07-13 iter 65 — minimal cycle: added Wave 5f #252–254 (attention-over-time heatmap, auto research diary, human-baseline benchmark). 254 ideas · 33 PRDs.
- 2026-07-13 iter 66 — minimal cycle: added Wave 5g #255–257 (ontology-consistency check, pathway-database corroboration, target–disease triangulation). 257 ideas · 33 PRDs.
- 2026-07-13 iter 67 — minimal cycle: added Wave 5h #258–260 (time-bounded claim windows, effect-drift/decline-effect detection, replication-timeline tracker). 260 ideas · 33 PRDs.
- 2026-07-13 iter 68 — minimal cycle: added Wave 5i #261–263 (sandbox resource auto-tuning, test-result caching by hash, R/Julia sandbox support). 263 ideas · 33 PRDs.
- 2026-07-13 iter 69 — minimal cycle: added Wave 5j #264–266 ("what evidence would flip this" per recommendation, hypothesis-portfolio tracking, recommendation pre-mortem). 266 ideas · 33 PRDs.
- 2026-07-13 iter 70 — minimal cycle: added Wave 5k #267–269 (graph-motif detection, circular-reasoning detector, bridge-claim identification). 269 ideas · 33 PRDs.
- 2026-07-13 iter 71 — minimal cycle: added Wave 5l #270–272 (specialized agent roster, dynamic role assignment, bounded cross-agent sharing). 272 ideas · 33 PRDs.
- 2026-07-13 iter 72 — minimal cycle: added Wave 5m #273–275 (negation & hedge handling, quantifier-scope disambiguation, coreference resolution). 275 ideas · 33 PRDs.
- 2026-07-13 iter 73 — minimal cycle: added Wave 5n #276–278 (Wikidata/ontology entity linking, external-KG contradiction check, KG-embedding link prediction). 278 ideas · 33 PRDs.
- 2026-07-13 iter 74 — minimal cycle: added Wave 5o #279–281 (uncertainty propagation through derivations, Monte-Carlo sensitivity, interval arithmetic for ranges). 281 ideas · 33 PRDs.
- 2026-07-13 iter 75 — minimal cycle: added Wave 5p #282–284 (guided closed-loop walkthrough, belief-graph search-as-you-type, print/PDF-friendly layout). 284 ideas · 33 PRDs.
- 2026-07-13 iter 76 — minimal cycle: added Wave 5q #285–287 (auto limitations section, scope-creep detector, "known unknowns" register). 287 ideas · 33 PRDs.
- 2026-07-13 iter 77 — minimal cycle: added Wave 5r #288–290 (universal environment capture, lockfile-pinned reproducibility, reproducibility CI gate). 290 ideas · 33 PRDs.
- 2026-07-13 iter 78 — minimal cycle: added Wave 5s #291–293 (survival-analysis reanalysis, field-metric forecasting, changepoint detection on evidence streams). 293 ideas · 33 PRDs.
- 2026-07-13 iter 79 — minimal cycle: added Wave 5t #294–296 (MCP tool exposure, tool-output sanity verification, runtime tool discovery). 296 ideas · 33 PRDs.
- 2026-07-13 iter 80 — minimal cycle: added Wave 5u #297–299 (single-cell/omics reanalysis, imaging-data reanalysis, EHR/OMOP cohort reanalysis). 299 ideas · 33 PRDs.
- 2026-07-13 iter 81 — minimal cycle: added Wave 5v #300–302 (self-discovered forensic checks, method-effectiveness tracking, self-generated eval tasks). **300+ ideas** · 33 PRDs.
- 2026-07-13 iter 82 — minimal cycle: added Wave 5w #303–305 (live draft feedback, reviewer-2 simulation, hypothesis sparring partner). 305 ideas · 33 PRDs.
- 2026-07-13 iter 83 — minimal cycle: added Wave 5x #306–308 (formal claim specification, belief-set consistency check, proof-obligation tracking). 308 ideas · 33 PRDs.
- 2026-07-13 iter 84 — minimal cycle: added Wave 5y #309–311 (impact-first literature triage, deadline-aware planning, diminishing-returns stop rule). 311 ideas · 33 PRDs.
- 2026-07-13 iter 85 — minimal cycle: added Wave 5z #312–314 (source-integrity hashing at ingest, duplicate-source merge, predatory-venue flag). 314 ideas · 33 PRDs.
- 2026-07-13 iter 86 — minimal cycle: added Wave 6a #315–317 (table extraction + stat verification, percentage/proportion sanity check, CI↔p-value coherence check). 317 ideas · 33 PRDs.
- 2026-07-13 iter 87 — minimal cycle: added Wave 6b #318–320 (concept-dependency curriculum, fidelity-checked analogies, Socratic tutoring mode). 320 ideas · 33 PRDs.
- 2026-07-13 iter 88 — minimal cycle: added Wave 6c #321–323 (failed-investigation gallery, self-retraction protocol, membrane near-miss log). 323 ideas · 33 PRDs.
- 2026-07-13 iter 89 — minimal cycle: added Wave 6d #324–326 (prioritized-replay buffer, importance-weighted consolidation, memory-interference detection). 326 ideas · 33 PRDs.
- 2026-07-13 iter 90 — minimal cycle: added Wave 6e #327–329 (prospective belief validation, belief→outcome tracking, per-domain calibration breakdown). 329 ideas · 33 PRDs.
- 2026-07-13 iter 91 — minimal cycle: added Wave 6f #330–332 (stable spatial belief-map, zoomable semantic map, evidence-flow animation). 332 ideas · 33 PRDs.
- 2026-07-13 iter 92 — minimal cycle: added Wave 6g #333–335 (cost-per-validated-belief dashboard, free-tier-first data strategy, compute-budget forecasting). 335 ideas · 33 PRDs.
- 2026-07-13 iter 93 — minimal cycle: added Wave 6h #336–338 (testability classifier, dataset-gap identification, assay-to-claim matcher). 338 ideas · 33 PRDs.
- 2026-07-13 iter 94 — minimal cycle: added Wave 6i #339–341 (multiverse analysis, specification-curve display, analytic-flexibility flag). 341 ideas · 33 PRDs.
- 2026-07-13 iter 95 — minimal cycle: added Wave 6j #342–344 (PharmGKB pharmacogenomics cross-check, ClinVar variant-pathogenicity check, COSMIC cancer-mutation corroboration). 344 ideas · 33 PRDs.
- 2026-07-13 iter 96 — minimal cycle: added Wave 6k #345–347 (reasoning-trace replay, decision-point annotation, trace-diff between runs). 347 ideas · 33 PRDs.
- 2026-07-13 iter 97 — minimal cycle: added Wave 6l #348–350 (analogical hypothesis generation, contradiction→falsifiable sub-hypothesis, hypothesis-novelty scoring). 350 ideas · 33 PRDs.
- 2026-07-13 iter 98 — minimal cycle: added Wave 6m #351–353 (attention-budget-aware surfacing, progressive complexity disclosure, notification batching + digest). 353 ideas · 33 PRDs.
- 2026-07-13 iter 99 — minimal cycle: added Wave 6n #354–356 (transitive-inference consistency, belief-graph anomaly detection, entity merge/split auditing). 356 ideas · 33 PRDs.
- 2026-07-13 iter 100 — minimal cycle: added Wave 6o #357–359 (standing-program continuity, initiative-quality metric, research-taste evolution tracking). 359 ideas · 33 PRDs. [100 loop iterations · program complete + coherent · implementation is the standing constraint.]
- 2026-07-13 iter 101 — minimal cycle: added Wave 6p #360–362 (independent re-implementation check, blinded reanalysis, pre-registered reanalysis-plan primitive). 362 ideas · 33 PRDs.
- 2026-07-13 iter 102 — minimal cycle: added Wave 6q #363–365 (action-consequence preview, reversible-by-default actions, belief-change approval queue). 365 ideas · 33 PRDs.
- 2026-07-13 iter 103 — minimal cycle: added Wave 6r #366–368 (confidence-source decomposition, correlated-evidence overconfidence penalty, extraordinary-claim confidence floor). 368 ideas · 33 PRDs.
- 2026-07-13 iter 104 — minimal cycle: added Wave 6s #369–371 (patent-literature ingestion, clinical-guideline ingestion, dataset-paper linkage). 371 ideas · 33 PRDs.
- 2026-07-13 iter 105 — minimal cycle: added Wave 6t #372–374 (PICO-structured claim extraction, direction/magnitude separation, claim-qualifier preservation). 374 ideas · 33 PRDs.
- 2026-07-13 iter 106 — minimal cycle: added Wave 6u #375–377 (hype-cycle positioning, emerging-consensus detection, field-reversal early warning). 377 ideas · 33 PRDs.
- 2026-07-13 iter 107 — minimal cycle: added Wave 6v #378–380 (trust-earned progressive autonomy, track-record transparency page, confidence-vs-outcome scatter). 380 ideas · 33 PRDs.
- 2026-07-13 iter 108 — minimal cycle: added Wave 6w #381–383 (Bradford-Hill criteria checklist, GRADE evidence-quality rating, Toulmin argument mapping). 383 ideas · 33 PRDs.
- 2026-07-13 iter 109 — minimal cycle: added Wave 6x #384–386 (PRISMA-adherent systematic review, search-completeness estimation, inter-note consistency check). 386 ideas · 33 PRDs.
- 2026-07-13 iter 110 — minimal cycle: added Wave 6y #387–389 (parameterized analysis templates, pipeline validation on synthetic data, result-sanity auto-checks). 389 ideas · 33 PRDs.
- 2026-07-13 iter 111 — minimal cycle: added Wave 6z #390–392 (end-to-end loop dashboard, loop-completion-rate metric, loop-bottleneck attribution). 392 ideas · 33 PRDs.
- 2026-07-13 iter 112 — minimal cycle: added Wave 7a #393–395 (state-of-the-argument prose, narrative-arc of understanding, counter-narrative surfacing). 395 ideas · 33 PRDs.
- 2026-07-13 iter 113 — minimal cycle: added Wave 7b #396–398 (bench-to-bedside tracking, real-world-impact estimation, failure-to-translate analysis). 398 ideas · 33 PRDs.
- 2026-07-13 iter 114 — minimal cycle: added Wave 7c #399–401 (slop-rate monitoring, load-adaptive membrane tightening, quality-vs-quantity dashboard). **400+ ideas** · 33 PRDs.
- 2026-07-13 iter 115 — minimal cycle: added Wave 7d #402–404 (cross-investigation pattern mining, warm-start from similar past investigations, method-recommendation from history). 404 ideas · 33 PRDs.
- 2026-07-13 iter 116 — minimal cycle: added Wave 7e #405–407 (cell-line authentication check, sample-size-justification check, batch-effect awareness). 407 ideas · 33 PRDs.
- 2026-07-13 iter 117 — minimal cycle: added Wave 7f #408–410 (devil's-advocate persona, subfield-specialist personas, lab-consensus vs individual-belief). 410 ideas · 33 PRDs.
- 2026-07-13 iter 118 — minimal cycle: added Wave 7g #411–413 (causal-DAG construction, confounder-adjustment recommendation, instrumental-variable identification). 413 ideas · 33 PRDs.
- 2026-07-13 iter 119 — minimal cycle: added Wave 7h #414–416 (stakeholder-tailored briefs, regulatory-grade evidence dossier, teaching-slide-deck generation). 416 ideas · 33 PRDs.
- 2026-07-13 iter 120 — minimal cycle: added Wave 7i #417–419 (the paper about Persona, living FINDINGS→paper sync, ablation-study automation). 419 ideas · 33 PRDs.
- 2026-07-13 iter 121 — minimal cycle: added Wave 7j #420–422 (prompt-injection defense audit, data/tool supply-chain integrity, access-control on high-stakes actions). 422 ideas · 33 PRDs.
- 2026-07-13 iter 122 — minimal cycle: added Wave 7k #423–425 (streaming membrane, priority lanes in the queue, adaptive scheduler cadence). 425 ideas · 33 PRDs.
- 2026-07-13 iter 123 — minimal cycle: added Wave 7l #426–428 (coverage-gap map, systematic-vs-opportunistic reading balance, per-subfield saturation detection). 428 ideas · 33 PRDs.
- 2026-07-13 iter 124 — minimal cycle: added Wave 7m #429–431 (qualitative-evidence integration, mixed-methods synthesis, anecdote-vs-evidence discrimination). 431 ideas · 33 PRDs.
- 2026-07-13 iter 125 — minimal cycle: added Wave 7n #432–434 (component-health monitoring, self-healing on component failure, graceful capability degradation). 434 ideas · 33 PRDs.
- 2026-07-13 iter 126 — minimal cycle: added Wave 7o #435–437 (full-provenance replay bundle, provenance-graph query API, orphan-evidence detection). 437 ideas · 33 PRDs.
- 2026-07-13 iter 127 — minimal cycle: added Wave 7p #438–440 (embedding-space audit, relevance-gate explainability, classifier-confidence + abstain). 440 ideas · 33 PRDs.
- 2026-07-13 iter 128 — minimal cycle: added Wave 7q #441–443 (long-term collaborator memory, proactive next-question suggestion, personalized relevance tuning). 443 ideas · 33 PRDs.
- 2026-07-13 iter 129 — minimal cycle: added Wave 7r #444–446 (multiple-comparisons correction, Bayesian model comparison, equivalence testing TOST). 446 ideas · 33 PRDs.
- 2026-07-13 iter 130 — minimal cycle: added Wave 7s #447–449 (boundary-condition mapping, generalizability scoring, exception tracking). 449 ideas · 33 PRDs.
- 2026-07-13 iter 131 — minimal cycle: added Wave 7t #450–452 (judgment-rubric standardization, verdict-stability across runs, adjudicator anchoring-bias check). 452 ideas · 33 PRDs.
- 2026-07-13 iter 132 — minimal cycle: added Wave 7u #453–455 (model-tier routing by task difficulty, distill routine judgments, batch parallel sub-questions). 455 ideas · 33 PRDs.
- 2026-07-13 iter 133 — minimal cycle: added Wave 7v #456–458 (result-writeback verification, test→belief provenance link, loop-outcome notification). 458 ideas · 33 PRDs.
- 2026-07-13 iter 134 — minimal cycle: added Wave 7w #459–461 (unexpected-connection surfacing, serendipity mode, mechanism-unification highlighting). 461 ideas · 33 PRDs.
- 2026-07-13 iter 135 — minimal cycle: added Wave 7x #462–464 (self-documenting architecture, live capability inventory, auto-maintained continuation doc). 464 ideas · 33 PRDs.
- 2026-07-13 iter 136 — minimal cycle: added Wave 7y #465–467 (bi-temporal query support, belief-state-as-of-date reconstruction, retroactive-correction propagation). 467 ideas · 33 PRDs.
- 2026-07-13 iter 137 — minimal cycle: added Wave 7z #468–470 (sequential testing/early-stopping, active-learning data selection, Bayesian optimal experiment design). 470 ideas · 33 PRDs.
- 2026-07-13 iter 138 — minimal cycle: added Wave 8a #471–473 (overnight-run morning digest, autonomous-run safety envelope, wake-the-human trigger). 473 ideas · 33 PRDs.
- 2026-07-13 iter 139 — minimal cycle: added Wave 8b #474–476 (degrees-of-belief as distributions, epistemic-vs-aleatoric uncertainty split, suspended-judgment as first-class state). 476 ideas · 33 PRDs.
- 2026-07-13 iter 140 — minimal cycle: added Wave 8c #477–479 (whole-field belief-state export, community-contributable corrections, belief-state as downstream API). 479 ideas · 33 PRDs.
- 2026-07-13 iter 141 — minimal cycle: added Wave 8d #480–482 (long-tail/rare-disease focus mode, small-evidence-base handling, case-report aggregation). 482 ideas · 33 PRDs.
- 2026-07-13 iter 142 — minimal cycle: added Wave 8e #483–485 (own-result-vs-literature reconciliation, confidence-in-own-computation, escalate own surprising result). 485 ideas · 33 PRDs.
- 2026-07-13 iter 143 — minimal cycle: added Wave 8f #486–488 (prompt-optimization loop, tool-use policy learning, memory-policy tuning). 488 ideas · 33 PRDs.
- 2026-07-13 iter 144 — minimal cycle: added Wave 8g #489–491 (multi-anchor identity redundancy, disposition-consistency enforcement, self-narrative coherence check). 491 ideas · 33 PRDs.
- 2026-07-13 iter 145 — minimal cycle: added Wave 8h #492–494 (full-vision integration test, demo-scenario library, money-shot regression test). 494 ideas · 33 PRDs.
- 2026-07-13 iter 146 — minimal cycle (meta): added Wave 8i #495–497 (auto-triage of this backlog, idea→PRD auto-drafting, feature-impact forecasting). 497 ideas · 33 PRDs.
- 2026-07-13 iter 147 — minimal cycle: added Wave 8j #498–500 (persona-as-coauthor attribution, reproducibility-first publishing, the standing colleague capstone). **500 ideas** · 33 PRDs.
- 2026-07-13 iter 148 — minimal cycle: added Wave 8k #501–503 (asymmetric-loss humility, "I could be wrong" surfacing, disagreement-with-experts flag). 503 ideas · 33 PRDs.
- 2026-07-13 iter 149 — minimal cycle: added Wave 8l #504–506 (zero-config onboarding, mobile-responsive legibility, offline-capable read mode). 506 ideas · 33 PRDs.
- 2026-07-13 iter 150 — context compaction. Wrote `.agent-orchestration/LOOP_STATE.md` (instructions for the new self: read-order, loop protocol, non-negotiables, lessons — pre-assign FC+RQ; next free FC-26/RQ-E48). New self: read LOOP_STATE.md first, then resume the loop. 506 ideas · 33 PRDs.
- 2026-07-13 iter 151 — resumed post-compaction. Added Wave 8m #507–509 (cloud-lab experiment submission, assay-result ingestion, wet-lab-vs-insilico reconciliation) — the wet-lab bridge. 509 ideas · 33 PRDs.
- 2026-07-13 iter 152 — wrote PRD-34 (cloud-lab wet-lab loop, L3) + PRD-35 (standing colleague, L1+4) with FC-26/27 + RQ-E48/49 pre-assigned. Added Wave 8n #510–512 (skill-gap self-identification, new-tool self-integration proposal, capability-driven interest spawning). 512 ideas · 35 PRDs (34–35 authoring). Context ran out before posting → deferred to next self.
- 2026-07-13 iter 153 — resumed post-compaction. **Posted PRD-34/35 to the bus** (the pending resolution): PRD-00 §9 FC-26/FC-27 + §6 RQ-E48/E49; HANDOFF dispatch rows + Master resolutions batch 10 (res. 61–67; CCP-34a `"wetlab:"` prefix → `inbox.file_handoff`, dispatch NEVER calls `cloudlab.submit`; PRD-35 O-1 trigger semantics frozen); flipped traceability PRD-34/35 authoring→READY-TO-CLAIM. **Numbering fix:** PRD-00 already used "batch 9" for PRD-32/33, so PRD-34/35 = batch 10 (LOOP_STATE said 9). Added Wave 8o #513–515 (poison-attribution forensics, attack-cost/cost-to-flip pricing, cross-persona replication gate — adversarial-robustness lens). Pre-assigned PRD-36/37 = #37/#71 (FC-28/RQ-E50, RQ-E51). **512→515 ideas · 35 PRDs · FC-1..27 · RQ to E49 · 67 resolutions.** PRD authoring paced (35 written, 0 CLAIMED — implementation is the constraint).
- 2026-07-13 iter 154 — user steered "promote" → **launched PRD-36/37 authoring** (workflow `wqih989vv`, parallel): PRD-36 contradiction-independence pre-check (L2, FC-28/RQ-E50), PRD-37 Gail-Simon effect-modification forensic (L3, RQ-E51 additive to FC-4/forensics — no new FC). Pre-assigned + real-code-grounded (kg.py independence-by-lab; forensics.py p_curve). HANDOFF AUTHORING row + traceability rows added. Added Wave 8p #516–518 (effort-calibration self-score, signed external-replication exchange, per-verdict method-provenance fingerprint — competence-measurement + external-trust lens). **515→518 ideas · 35 PRDs (36/37 authoring).** Resolve + post batch-11 next fire on workflow completion (next free after: FC-29, RQ-E52).
- 2026-07-13 iter 155 — light cycle (PRD-36/37 workflow `wqih989vv` still in flight: 2 agents started, no result/files yet → per protocol, ideas only, no relaunch/resolve). Added Wave 8q #519–521 (mechanistic-model→novel-prediction generator, prospective forecasting/predict-then-reveal, assumption-graph/load-bearing tacit assumptions — generative/predictive-science + deep-foundations lens; the "does things not possible before" bar). **518→521 ideas · 35 PRDs (36/37 authoring).** Resolve batch-11 on completion.
- 2026-07-13 iter 156 — workflow `wqih989vv` COMPLETED (2/2, 0 err, 279k subagent tokens). **Posted batch-11:** PRD-36 (FC-28 `kg.shared_origin` + `candidate_conflicts` suppression, advisory until `rq_e50.passed`) + PRD-37 (Gail-Simon forensic, additive to FC-4/forensics, no new FC) → READY-TO-CLAIM. PRD-00 §9 FC-28 + §6 RQ-E50/E51; HANDOFF Master resolutions batch 11 (res. 68–74): CCP-36a `gate += 'independence'`, cross-cutting ownership ruling (providing lane owns its `exp_*.py`+unit test), all PRD-37 OQs→defaults. Pre-assign held again (zero collision). **37 PRDs · FC-1..28 · RQ to E51 · 74 resolutions · 521 ideas.** Next free: FC-29, RQ-E52.
- 2026-07-13 iter 157 — no batch in flight → **launched PRD-38/39 authoring** (workflow `wlluvxduz`): PRD-38 meta-research self-study (L3+4, FC-29/RQ-E52 — Persona studies its own track record as a dataset, brutal-honesty guardrails: false-improvement rate ≤0.05, reversal recall==1.0), PRD-39 explanation-faithfulness check (L3, FC-30 reserved/RQ-E53 — catches prose drifting beyond the evidence graph, distinct from citation hallucination). "Persona measures its own honesty" batch; pre-assigned + real-code-grounded (calibration.py, synthesis/checker.py; FC-17 consumed as contract, import-guarded). Fixed a mis-tag (#134 = L3, not L1). Added Wave 8r #522–524 (experiment-portfolio optimizer, result-contingent replanning, stakes-tied stopping rule — acting-loop-economics lens). **521→524 ideas · 37 PRDs (38/39 authoring).** Resolve batch-12 next fire on completion (next free after: FC-31, RQ-E54).
- 2026-07-13 iter 158 — light cycle (PRD-38/39 workflow `wlluvxduz` still in flight: 2 agents started, no result/files → per protocol, ideas only, no relaunch/resolve). Added Wave 8s #525–527 (half-life-aware refresh scheduler, whole-graph self-consistency sweep, evidence-rot/silent-source-degradation detector — long-horizon self-integrity lens serving the durable-self differentiator). **524→527 ideas · 37 PRDs (38/39 authoring).** Resolve batch-12 on completion.
- 2026-07-13 iter 159 — "fresh session, continue." Workflow `wlluvxduz` PARTIAL: **PRD-38 written (242 lines, receipt captured — FC-29/RQ-E52, OQs staged for batch-12); PRD-39 still authoring** (agent alive, doing faithfulness-lit WebSearch, no Write yet). Batch incomplete → no batch-12 post yet (atomic resolution). PRD-38 receipt OQs to resolve next: RQ-E52 registration, `_MIN_TREND_N` freeze (8–12), `_P_COMMIT` import, and "component paid off = causal?" (a NEW contract if so — surfaced not minted). Added Wave 8t #528–530 (competitive self-positioning scoreboard, untrusted cross-agent claim import through the membrane, self-upgrade capability-regression gate — agent-ecosystem + self-modification-safety lens). **527→530 ideas · 37 PRDs (38 done/39 authoring).** Resolve batch-12 when PRD-39 lands.
- 2026-07-13 iter 160 — workflow `wlluvxduz` COMPLETED (2/2, 0 err, 278k tok). **Posted batch-12:** PRD-38 (FC-29 `self_study.report/calibration_trend`, RQ-E52) + PRD-39 (explanation-faithfulness, additive/no-new-FC, RQ-E53) → READY-TO-CLAIM. PRD-00 §9 FC-29 + §6 RQ-E52/E53; HANDOFF Master resolutions batch 12 (res. 75–82): **FC-30 reserved-then-RETURNED to pool** (PRD-39 was Lane-3-internal, YAGNI — next free FC = FC-30 again), `_MIN_TREND_N`=10, import `calibrate._P_COMMIT`, component-value stays observational v1 (no causal contract minted), RQ-E53 offline-gate. Pre-assign held (zero collision). **39 PRDs · FC-1..29 (FC-30 free) · RQ to E53 · 82 resolutions · 530 ideas.** No batch in flight. Next free: FC-30, RQ-E54.
- 2026-07-13 iter 161 — light cycle (paced: just shipped 2 consecutive batches 36/37 + 38/39; 39 PRDs unclaimed, 0 CLAIMED → don't launch a 3rd straight batch; batch-13 on user steer / lane engage). Added Wave 8u #531–533 (expected-regret action recommender, decision-boundary sensitivity, stakeholder loss-function elicitation+anchoring — decision-support-under-uncertainty lens; beliefs→actions, the translational last mile). Refreshed "Next up" queue (#136/#519/#520 pre-assign FC-30/RQ-E54+). **530→533 ideas · 39 PRDs.** No batch in flight.
- 2026-07-13 iter 162 — user re-set loop: `/loop 30 keep ideating and writing prds` → replaced 5-min cron `13f6405c` with **1-min cron `485ff31c`** (30s→1-min floor; richer prompt stored pointing at LOOP_STATE + full protocol). User steer "writing prds" → **launched batch-13** (workflow `whrt707rc`): PRD-40 dead-end/rabbit-hole detector (L1, FC-30/RQ-E54 — measured yield/$ + stall-rounds, never hard-kills a slow-but-productive dive), PRD-41 mechanistic-model→novel-prediction generator (L3, FC-31/RQ-E55 — composes signed edges into IMPLIED predictions, INFERRED-only, explicitly differentiated from FC-22 negspace). FC-30 reclaimed. Added Wave 8v #534–536 (hypothesis-quality scorecard, generation-strategy attribution, surprise-worthiness gate — hypothesis-quality-flywheel lens). **533→536 ideas · 39 PRDs (40/41 authoring).** Resolve batch-13 on completion (next free after: FC-32, RQ-E56).
- 2026-07-13 iter 163 — light cycle (batch-13 `whrt707rc` still in flight: 2 agents started, no result/files → ideas only, no relaunch/resolve). Added Wave 8w #537–539 (lab-private evidence ingestion/bring-your-own-data, private-vs-public divergence dossier, confidentiality-tiered belief partitioning — "Persona as a lab collaborator" lens; the biggest usefulness jump for a working PI, with the security discipline that makes it usable). **536→539 ideas · 39 PRDs (40/41 authoring).** Resolve batch-13 on completion.
- 2026-07-13 iter 164 — light cycle (batch-13 `whrt707rc` still in flight). Added Wave 8x #540–542 (citation-frontier crawling strategy, corpus-saturation "when have I read enough" estimator, seminal-vs-derivative source discrimination — active-reading-strategy lens; acquire evidence like a strategic scientist, not a crawler). **539→542 ideas · 39 PRDs (40/41 authoring).** Resolve batch-13 on completion.
- 2026-07-13 iter 165 — light cycle (batch-13 `whrt707rc` still in flight; both agents alive + thorough, deep grounding, no Write yet — PRD-41 is L-effort). Added Wave 8y #543–545 (evidence-type-weighted belief aggregation, triangulation bonus for cross-method convergence, evidence-type gap identifier — cross-evidence-type-integration lens; combine incommensurable evidence like a rigorous synthesist, grounded in triangulation metascience). **542→545 ideas · 39 PRDs (40/41 authoring).** Resolve batch-13 on completion.
- 2026-07-13 iter 166 — light cycle. **PRD-41 LANDED** (160 lines; FC-31 new `analysis/mechanism.py` re-exported via engine.py, RQ-E55 held-out-edge recovery vs random+Adamic-Adar; consumes FC-4/FC-3/FC-22 import-guarded; OQs: discover.py hook [rec yes, mirror CCP-30a], RQ-E55 graph slice [domain input]). **PRD-40 still authoring** → batch incomplete, no post yet (atomic). Added Wave 8z #546–548 (rapid field-mapping cold-start, coverage-conditioned confidence/calibrated ignorance, analogical warm-start from a mastered field — cold-start/new-field-competence lens). **545→548 ideas · 39 PRDs (41 done/40 authoring).** Resolve batch-13 when PRD-40 lands.
- 2026-07-13 iters 155–166 (background, one turn) — Waves 8s–8z: #525–548 (self-integrity, ecosystem/self-mod-safety, decision-support, hypothesis-quality, lab-collaborator, active-reading, evidence-integration, cold-start lenses). 24 ideas.
- 2026-07-13 iter 167 — **Posted batch-13** (PRD-40/41 workflow `whrt707rc` completed 2/2, 0 err): PRD-40 dead-end detector (FC-30 `convergence.convergence_health`, RQ-E54) + PRD-41 mechanistic-prediction generator (FC-31 `analysis/mechanism.py`, RQ-E55) → READY-TO-CLAIM. PRD-00 §9 FC-30/31 + §6 RQ-E54/E55; HANDOFF Master resolutions batch 13 (res. 83–89): CCP-40a (FC-30 render→L4), CCP-41a (mechanism discover.py hook→L1), PRD-40 OQs→defaults, FC-31 differentiated from FC-22. Pre-assign held. **The 1-min cron `485ff31c` flooded (queued ~130 fires into one turn) → replaced with 5-min cron `64340d74`.** Added Wave 9a #549–551 (collective-blindspot detector, correlated-error firewall/illusory-independence discount, team-composition memory — swarm-coordination-intelligence lens). **548→551 ideas · 41 PRDs · FC-1..31 · RQ to E55 · 89 resolutions.** No batch in flight. Next free: FC-32, RQ-E56.
- 2026-07-13 iter 168 — user loop steer "writing prds" → **launched batch-14** (workflow `wzyovh1lx`): PRD-42 prospective-forecasting (L1+4, FC-32/RQ-E56 — dated sealed forecasts of the external literature's future, out-of-sample foresight, auto-graded on real arrivals) + PRD-43 whole-graph self-consistency sweep (L2, FC-33/RQ-E57 — periodic global coherence audit: transitivity/sign/orphaned-inference violations → typed repair candidates, read-only never mutates). Pre-assigned + grounded (trajectory.py live; FC-17/FC-27 import-guarded; kg reads). Added Wave 9b #552–554 (end-to-end uncertainty propagation, sensitivity attribution, interval-honest deliverable language — propagated-uncertainty lens). **551→554 ideas · 41 PRDs (42/43 authoring).** Resolve batch-14 on completion (next free after: FC-34, RQ-E58).
- 2026-07-13 iter 169 — light cycle (batch-14 `wzyovh1lx` still in flight: 2 agents started, no files → ideas only, no relaunch/resolve). Added Wave 9c #555–557 (post-publication commentary ingestion/PubPeer, open-review consensus signal, preprint→publication delta tracker — peer-review-lifecycle-as-evidence lens; the post-pub signal the competitive set ignores). **554→557 ideas · 41 PRDs (42/43 authoring).** Resolve batch-14 on completion.
- 2026-07-13 iter 170 — light cycle. **PRD-42 LANDED** (283 lines; FC-32 forecast store L1/render L4, RQ-E56 out-of-sample foresight; consumes trajectory[LIVE, real export is `trajectory` not `topic_trajectory`]/FC-17/FC-27 import-guarded; worker `@handler("forecast_grade")`; OQs: add `confidence` to sealed prior [rec keep], horizon-elapsed-no-evidence→`expired_no_evidence` excluded from Brier, v1 explicit-seal-only). **PRD-43 still authoring** → batch incomplete, no post (atomic). Added Wave 9d #558–560 (cross-scale consistency check, translation-gap/bench→bedside-break detector, model-organism applicability prior — cross-scale-reasoning + translation-gap lens; biomedicine's real failure axis). **557→560 ideas · 41 PRDs (42 done/43 authoring).** Resolve batch-14 when PRD-43 lands.
- 2026-07-13 iter 171 — batch-14 COMPLETED (workflow `wzyovh1lx`, 2/2, 0 err). **Posted batch-14:** PRD-42 (FC-32 `persona/forecast.py`, RQ-E56) + PRD-43 (FC-33 `memory/coherence.py` sweep, RQ-E57) → READY-TO-CLAIM. PRD-00 §9 FC-32/33 + §6 RQ-E56/E57; HANDOFF Master resolutions batch 14 (res. 90–96): CCP-43a (coherence_sweep tick→L1), memory/coherence.py kept (distinct namespace from top-level persona/coherence.py), PRD-42/43 OQs→defaults, worker += forecast_grade/coherence_sweep. Pre-assign held. **560 ideas · 43 PRDs · FC-1..33 · RQ to E57 · 96 resolutions.** — **USER PAUSED THE LOOP** (cron `64340d74` cancelled). No batch in flight, state fully posted. Resume anytime: `/loop 5m keep ideating and writing prds`. Next free: FC-34, RQ-E58.
