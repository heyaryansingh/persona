# The Synthetic Researcher
### A build plan structured as a research program — hypotheses, sandboxed experiments, and an architecture *derived* from evidence

> **What this document is.** Not a spec that asserts decisions. A research program. Every load-bearing architectural choice is written as a **hypothesis**, given a **sandboxed experiment** with real code and metrics, and only promoted to "build it this way" once evidence supports it. The experiments are designed so that, run end to end, they become the results section of a paper: *"On constructing a persistent, continuously-learning synthetic researcher."*

> **One-sentence north star.** Spawn a synthetic researcher — seed it with a few interests and a disposition — and it goes out into the literature on its own: reading at swarm scale, maintaining a durable self, forming and revising beliefs, pursuing projects and side-projects, running its own computational tests when it can, and pulling humans in exactly when it needs wet-lab results or experimental judgment it cannot produce alone.

---

## PART 0 — Framing & Positioning

### 0.1 The reframe: a researcher has *standing*; a tool does not
A tool answers when asked and forgets. A researcher **carries a research program across time**: it remembers what it was chasing, holds half-formed hunches, commits to positions and then tries to defend or falsify them, and leaves a trail of work others can build on. Everything below serves that distinction.

### 0.2 The honest competitive landscape (why this is not a re-skin of existing work)
The grounding research is unambiguous: several pieces people *assume* are novel are already shipped or published. Build on them; do not re-implement them.

| Capability | Who already does it | Verdict for us |
|---|---|---|
| Claims classified supporting / contradicting | **scite** (2M users, 1.6B citations) | Solved & mature — **reuse the pattern, don't rebuild** |
| Structured, scored target–disease evidence w/ provenance | **Open Targets** (8.1M associations, 17.8M evidence pieces, quarterly) | Substantially a shipped product — **stand on their API** |
| LLM-agent contradiction detection at scale, expert-validated | **PaperQA2 / ContraCrow** (2024) | Frontier but published — **our loop must go past detection to *action*** |
| Confidence over time / publication-time KG | **MedKGent** (Aug 2025, 10M abstracts as daily series), **iKraph** | "Confidence trajectory" alone is done — **our dynamics must forecast, not just timestamp** |
| Multi-agent KG extraction w/ conflict resolution | **KARMA** (NeurIPS 2025), **AutoBioKG** (Jan 2026) | Extraction is commoditizing — **our value is the *self*, not the extractor** |

**The whitespace we occupy (nobody has shipped this):**
1. **The closed agentic loop that *acts*:** flagged contradiction → generated falsifiable hypothesis → located real public dataset → executed first-pass reanalysis → result written back into the belief-state. Everyone else stops at *detect* or *synthesize*.
2. **A persistent researcher-*self*** with interests, taste, memory, and initiative — not a query engine.
3. **The intellectual instruments of Part 3** (assumption/load-bearing graph, dynamical argument-state, experiment-value ranking, silence detection) that treat the literature as a *system with structure and momentum*, not a corpus to summarize.

### 0.3 The two failure modes we design against (name them before a judge does)
- **Autonomous slop.** Hundreds of agents can be hundreds of confident errors. Our answer is structural (Part 5.7): the swarm *reads*; it does not *write to the self* independently. Only convergent, provenance-backed, calibrated signal crosses the membrane.
- **Anthropomorphic theater.** Calling a scheduler "curiosity" fools no one. "Interests" and "taste" must be **functional** — they must measurably change what the researcher reads and concludes (Part 1.4–1.5, tested in Experiment E4).

### 0.4 Why this specifically needs Claude Fable / Claude Code + Claude Science
The novelty is **long-horizon agentic action with compute in the loop**: reason over structured beliefs → decide a test is possible → find data → *write and run analysis* → interpret → update. That is the Claude Code (orchestration, persistent app) + Claude Science (literature-plus-code-plus-compute) combination — not something a single prompt can one-shot.

---

## PART 1 — What It *Is*: The Researcher's Anatomy

The central architectural commitment, from which everything else follows: **separate the Swarm from the Self.**

### 1.1 The Self (durable, small, singular)
The part that persists across sessions and *is* the researcher:
- **Identity & disposition** — its name, its stance (e.g., skeptical vs. exploratory), risk appetite for speculation.
- **Standing interests** — a small set of regions of the belief-graph it allocates attention to, each with an *articulable reason* it can revise.
- **Belief-state** — the calibrated, provenance-tagged, revisable claim-graph (the assumption graph of Part 3.2 lives here).
- **Memory** — episodic (what it did and when), semantic (what it concluded), and procedural (what strategies worked).
- **Body of prior work** — its notebook, mini-reviews, side-projects, and error log.
- **Taste function** — the ranking policy over what to pursue next.

### 1.2 The Swarm (ephemeral, vast, stateless)
The hands. At any moment the Self can spawn many short-lived agents — readers, extractors, cross-checkers, dataset-scouts — that do one bounded job and disappear. They hold no identity. This is what "spawn hundreds of agents" means: **bounded, budgeted, disposable labor**, not hundreds of little minds.

### 1.3 The membrane (the anti-slop funnel)
Swarm output is *candidate* observations. Nothing becomes Self-belief without passing: **(1)** convergence (independent agents agree), **(2)** provenance (traceable to a real source), **(3)** calibration (uncertainty attached), and — for high-stakes claims — **(4)** human adjudication. *Scale of reading, discipline of believing.* (Mechanized in Part 5.7; tested in E2.)

### 1.4 What "interests" mean mechanistically (not a personality prompt)
An interest = **a standing attention-allocation weight over a region of the belief-graph, plus a reason.** It is real iff it changes behavior: which papers get read, which tensions get prioritized. The researcher can **spawn new interests** where the graph is simultaneously high-uncertainty, high-connectivity (load-bearing), and fast-moving — i.e., it grows curious where the science is most alive. (Tested in E4.)

### 1.5 What "taste" means mechanistically
Taste = a ranking function over candidate actions:
```
priority(action) = w_v · value_of_information(action)
                 + w_t · tractability(action)
                 + w_s · surprise(action)      # violation of current beliefs
                 − w_c · cost(action)
```
The **surprise** term is what makes it feel like a mind: a good scientist is *drawn to* what violates their expectations. When a new result contradicts a held belief, that is the most interesting event of the day, and the researcher reprioritizes toward it. This is not hand-waving — it maps onto **surprise-driven prioritized replay** (SuRe, 2025; Evo-memory, 2025), which we test directly in E3. (Weights `w_*` are themselves learned/tuned — Part 5, E3/E4.)

### 1.6 Spawning a researcher
The user provides a **seed**: a few core interests + a disposition. From there the researcher diverges autonomously — its later agenda is emergent, not scripted. For the hackathon we seed one program in a known domain (neurodegeneration/Alzheimer's — ties to the NeuroVoice story and gives ground-truth to sanity-check) **and** show it spawning one of its own.

---

## PART 2 — What It *Does*: The Living Loops

Five concurrent loops. The first is fast and always-on; the rest are reflective.

- **2.1 Inner loop (fast, always-on):** swarm reads new literature → extract claims → calibrate → update belief-graph. This is the "always thinking" substrate.
- **2.2 Outer loop (slow, reflective):** review belief-state → recompute interests & agenda → decide what matters most now → act. This is where *initiative* originates.
- **2.3 Initiative:** on its own cadence it takes the top agenda item and *acts unbidden* — spawns a reading program, opens a side-investigation, drafts a hypothesis, queues a human question, or runs a test.
- **2.4 Human-delegation loop:** detect what only a human can resolve (wet-lab result, subtle methodological adjudication, experimental design) → assemble a full dossier → route to a human → reincorporate the answer as a durable, shared belief node. *It manages collaborators, not just asks questions.*
- **2.5 Self-test loop (the centerpiece):** computationally-testable contradiction + available public data → **Claude Science** first-pass reanalysis → write result back. This is the loop nobody else closes.
- **2.6 Artifact loop:** continuously emit a **living lab notebook** ("noticed → suspected → spawned → found → updated → flagged"), **internal mini-reviews** when a program concludes, **side-project** threads, and a first-class **error log** of times it was wrong.

The loops are the behavior. Parts 3/5 make them *intelligent* and *safe*; Part 6 makes them *legible*.

---

## PART 3 — The Intellectual Engine (max depth)

This is what separates the researcher from every incumbent. Each instrument below is stated as a **capability**, a **why-it's-new**, a **how-it-computes**, and a **hypothesis + test** (code in `/experiments`, Part 10). The engine treats the literature as a *structured, moving system* — not a corpus.

### 3.1 Argument-state as a dynamical system (momentum, not snapshots)
**Capability.** For any question, don't report the *state* of evidence — report its *derivative*. "Support for target X has been *decelerating* for 18 months; three high-powered nulls just landed; the last time a target's evidence profile looked like this, it collapsed within ~2 years."

**Why it's new.** MedKGent timestamps *when* claims appear; iKraph carries publication dates. Neither computes **trajectory dynamics** (velocity, acceleration, inflection) or **forecasts collapse**. Snapshot → early-warning system.

**How it computes.** Treat the belief-graph as a *time-series of graphs* `G_t`. For each claim/edge track: rate of new **independent** evidence `dN/dt`, drift in the effect-size distribution, replication-independence ratio over time, and citation-velocity vs. support-velocity divergence (are people citing it *more* while supporting it *less*?). Fit a simple state-space / changepoint model per target; flag inflections.

**Hypothesis H3.1.** *Trajectory features (velocity/acceleration/independence-drift) predict eventual "collapse" (retraction, failed replication, abandonment) better than any static score (citation count, static support ratio).*
**Test E5 (retrospective backtest).** Take targets with known outcomes (approved vs. failed-in-trial via ClinicalTrials.gov stoppage reasons + Open Targets `Nature Genetics` trial-stoppage dataset). Freeze knowledge at time `T`, compute static vs. trajectory features, predict outcome at `T+Δ`. Metric: AUC static vs. AUC trajectory, with proper temporal splits. **Ship the trajectory model only if it beats static by a pre-registered margin.**

### 3.2 The assumption graph (load-bearing-belief tracer)
**Capability.** Map not a citation graph but an **inferential dependency graph**: which findings *logically depend on* which others being true. Then ask: *if this foundational claim fell, what fraction of the field's current conclusions become unsupported?*

**Why it's new.** No incumbent represents science as a **dependency structure** you can stress-test. This surfaces the highest-leverage target for scrutiny: the quiet, provisional assumption holding up a thousand papers. For a drug-target user: "this entire rationale traces to a single 2013 mouse study, never independently replicated."

**How it computes.** Extraction agents label inter-claim relations beyond support/contradict: **presupposes**, **derives-from**, **generalizes**, **operationalizes**. Build a DAG; compute load-bearing score = downstream dependency mass (e.g., PageRank-style over the "derives-from" edges) × inverse independent-support. This is the hardest extraction problem here and the biggest differentiator.

**Hypothesis H3.2.** *LLM agents can extract inferential-dependency edges (`presupposes`/`derives-from`) with usable precision (≥ a pre-set bar) against a human-annotated gold set — enough that load-bearing ranking correlates with expert judgment of "what's foundational."*
**Test E6.** Hand-annotate a small gold set (one subfield, ~50–100 claims, dependency edges). Measure agent extraction precision/recall vs. gold. Then correlate computed load-bearing scores with an expert ranking. **If precision is too low, downgrade 3.2 from "automated" to "human-in-the-loop assisted" and say so.**

### 3.3 Derivation-chain fragility propagation
**Capability.** When the self-test loop (2.5) actually *weakens* a claim via reanalysis, **propagate the consequence**: "this reanalysis weakened claim X → claims Y, Z and these 14 downstream papers now rest on shakier ground."

**Why it's new.** Science has no mechanism to propagate a correction downstream; errors persist for decades because nobody recomputes what depended on them. This is the missing propagation layer, and it only works *because* 3.2 exists.

**How it computes.** Graph traversal over the dependency DAG from the perturbed node, discounting by edge confidence; recompute downstream load-bearing/confidence and emit a "fragility cascade" report.

**Hypothesis H3.3.** *Perturbing a node and propagating produces cascades that experts agree are sensible (face-valid), and that occasionally surface non-obvious downstream dependents.* **Test:** expert review of N cascades on the gold subfield (qualitative + agreement rate).

### 3.4 Experiment-value ranking (the "useful" screen; the falsification market)
**Capability.** For every live contradiction or load-bearing assumption, estimate: *if resolved, how much downstream literature does this de-risk or overturn?* (value-of-information) and pair with *how cheap the resolving experiment is* (public dataset exists? $200 assay vs. 3-year study?). **Rank by VoI ÷ cost.** Output: "the single highest-leverage experiment you could run this month, and why the field needs it."

**Why it's new.** Converts passive literature into a **prioritized research agenda** — no tool offers this. This is the screen that makes a busy PI care.

**How it computes.** VoI ≈ downstream dependency mass at stake (from 3.2) × current uncertainty. Cost ≈ classifier over resolution type (existing-public-data / cheap-assay / expensive-study) using dataset availability signals (GEO/ArrayExpress/Perturb-seq presence) + trial feasibility heuristics.

**Hypothesis H3.4.** *The VoI÷cost ranking preferentially elevates experiments domain experts independently rate as "high value, worth doing" over a citation-count baseline ranking.* **Test E7:** blind experts rank a set of candidate experiments; compare Spearman correlation of (our ranking) vs. (citation baseline) to expert consensus.

### 3.5 Silence / dark-literature detector
**Capability.** Contradiction detection finds papers that *disagree*. The subtler signal is **what stopped being said.** A target hot in 2015–2018 that went quiet — not refuted, just abandoned — often hides a buried negative result (publication bias hides nulls). Detect abandonment; then dispatch the swarm to hunt the confirming null in preprints, **terminated** ClinicalTrials.gov entries, and conference abstracts.

**Why it's new.** Surfaces the negative evidence the published record structurally hides — a known pathology of biomedical science that no tool instruments.

**How it computes.** Per-target activity time-series → changepoint/decay detection → "abandonment" flag → targeted swarm search for corroborating nulls/terminations.

**Hypothesis H3.5.** *Abandonment signatures are enriched for downstream-discoverable negative/again-null evidence relative to matched still-active controls.* **Test:** case-control on targets with known post-hype nulls.

### 3.6 Cross-field mechanism translation
**Capability.** The same mechanism is often described in two subfields in vocabularies that never cite each other. Align them — "what cardiology calls A is mechanistically what oncology calls B" — surfacing evidence a domain researcher would never find.

**Why it's new & fit-for-judges.** A concrete, checkable win; natural on the Gladstone datasets (cross-reference a Perturb-seq hit against a mechanism named differently elsewhere). **Test:** curate known cross-field synonymous mechanisms; measure recovery rate vs. embedding-similarity baseline.

### 3.7 Human-as-resolver (judgment becomes compounding infrastructure)
**Capability.** The human is not a *reader of outputs* but the **adjudication step inside the loop**. The AI does the superhuman part (surface every genuine tension across millions of papers, pre-assemble the dossier, generate candidate explanations); the human makes the call; **their answer becomes a durable, reusable belief node others inherit.**

**Why it's new.** Turns expert judgment from something trapped in one lab's heads into **shared, compounding infrastructure** — and it's how we stay honest about accuracy: the AI never fabricates a resolution; it escalates and records provenance.

**This is the safety story and the science story at once**, and it directly answers the "AI can't do wet-lab" constraint: the division of labor is the design.

---

## PART 4 — Feature Set (tiered, buildable)

### 4.1 MVP spine (the story is false without these)
1. **Spawn-a-researcher**: seed (interests + disposition) → a running self.
2. **The swarm→self funnel**: bounded reader agents → membrane → calibrated belief-graph with provenance.
3. **The living notebook**: timestamped stream of the researcher's actual moves.
4. **One closed self-test loop**: a contradiction → hypothesis → located public dataset → Claude Science first-pass reanalysis → write-back.
5. **The human-handoff inbox**: at least one real escalation with a pre-assembled dossier that, when answered, anchors a belief.

### 4.2 Tier 2 (makes it feel alive)
6. Dynamical argument-state view (3.1) for one question.
7. Assumption/dependency graph (3.2) on one subfield.
8. Experiment-value ranking (3.4) — the "useful" screen.
9. Self-spawned second interest (emergent agenda).
10. Mini-review artifact auto-written when a program concludes.

### 4.3 Stretch (the full vision, honestly scaled)
11. Silence detector (3.5); cross-field translation (3.6); fragility propagation (3.3); a *second* researcher with different taste that cites/challenges the first (Part 7).

### 4.4 Reuse vs. build (spend Claude Max where it's novel)
| Stand on (don't rebuild) | Build fresh (this is the contribution) |
|---|---|
| Europe PMC / PubMed retrieval | The **self**: belief-state, memory, taste |
| Open Targets API (target–disease evidence) | The **membrane** + **anchoring** (evidence-based, Part 5) |
| SemMedDB (semantic predications) | The **loops** (initiative, self-test, delegation) |
| ClinicalTrials.gov (incl. terminated) | The **intellectual engine** (Part 3 instruments) |
| GEO / ArrayExpress / CZI Perturb-seq (datasets to test on) | The **legibility layer** (notebook, artifacts) |

---
## PART 5 — AI Architecture (max depth; **derived from the experiments in `/experiments`**)

> Architectural choices here are annotated **[E]** where an experiment in this repo directly informs them. See `results/FINDINGS.md`.

### 5.1 Agent taxonomy (the swarm's job types)
- **Reader** — ingest one paper/abstract; emit candidate claims with spans.
- **Extractor** — normalize claims into tuples `(entity, relation, object, effect, direction, population, method, power, provenance)`.
- **Dependency-tagger** — label inter-claim edges: `supports / contradicts / presupposes / derives-from / generalizes / operationalizes` (feeds 3.2).
- **Cross-checker** — given a candidate claim, search for independent corroboration/conflict (feeds the membrane's convergence test).
- **Dataset-scout** — given a hypothesis, locate public data capable of testing it (GEO/ArrayExpress/Perturb-seq/Open Targets).
- **Hypothesizer** — turn a contradiction into a *falsifiable* sub-hypothesis + the analysis that would test it.
- **Tester** — (Claude Science) write & run the first-pass analysis; return result + confidence.
- **Reviewer/Reflector** — the outer-loop agent that reprioritizes the agenda and writes artifacts.
- **Librarian/Orchestrator** — the persistent controller that spawns, budgets, and harvests all of the above.

### 5.2 Orchestration & cost discipline (Claude Max-aware)
- **Budgeted fan-out**: every outer-loop tick allots a token/agent budget; the swarm is bounded (tens now, architecture scales to hundreds). Readers use a cheaper/faster model; Hypothesizer/Tester/Reflector use the strongest.
- **Harvest-then-commit**: swarm returns candidates to a staging buffer; the membrane (5.4) decides what crosses into the self. Never write per-agent.
- **Backpressure**: if correlated disagreement spikes (poisoning signal), the orchestrator *narrows* fan-out and *tightens* the membrane [E].

### 5.3 The belief-state store (schema)
A versioned graph. Node = claim; edge = typed relation (5.1). Every node carries:
```
claim_id, statement, entities[], effect, direction, population, method,
power_estimate,
confidence: {logit, calibrated_p},
provenance_state: one of {READ, INFERRED, HUMAN_CONFIRMED, TESTED},
sources[] (with independent-source count),
anchor: bool,            # human-confirmed core -> resist overwrite [E]
history[] (every update, with cause),   # legibility + fragility propagation
trajectory: {velocity, acceleration, independence_ratio_over_time}  # 3.1
```

### 5.4 Membrane + anchoring (**this is the tested core — E-DIAGNOSTIC**)
**Finding [E]:** under *benign* (independent) noise, a naive continuous-update self is
as accurate as any gated one — protection only adds latency. Under **correlated,
sustained poisoning** (the realistic open-literature threat), a **protected,
human-confirmed core** retained **100%** of verified beliefs during attack vs **71%**
for naive, and recovered **88%** vs **68%** of all poisoned beliefs. Therefore:
- **Adaptive membrane**: fast-path commit in benign regimes; switch to strict
  independent-source quorum when correlated-source disagreement is detected. Don't pay
  the latency cost when you don't need to.
- **Anchored core**: beliefs promoted to `HUMAN_CONFIRMED` become `anchor=True` and are
  *resistant, not immune* (high overwrite-resistance factor) — the identity-protection
  **and** anti-slop mechanism in one. Validated crossover, not a guess.
- **Surprise-gated verification**: keep surprise-prioritized re-examination for faster
  correct belief-flips, **but** it can never move an `anchor` belief without human
  sign-off (prevents surprise-seeking from becoming a corruption vector) [E].

### 5.5 Memory architecture (continuity across sessions)
- **Self as living docs**: the durable self is a set of human-readable Markdown/JSON
  files (`self/identity.md`, `self/agenda.md`, `self/beliefs.json`, `self/notebook.md`,
  `self/errors.md`). This makes "read its mind" *literal* and auditable, and is the
  agent's re-hydration context on each wake. Backed by the claim-graph store (5.3) for
  structured queries. (Multi-anchor identity: the self survives corruption of any one
  store because identity is distributed across docs + graph + notebook.)
- **Three memory types**: episodic (notebook/history), semantic (belief-graph),
  procedural (a `self/strategies.md` of what tactics worked — updated from the error log).
- **Consolidation on sleep**: between runs, a Reflector pass merges redundant claims,
  resolves buffered conflicts, prunes, and updates trajectories — the "sleep" analogue
  that keeps the self small and coherent.

### 5.6 Where Claude Fable/Code sits vs. Claude Science
- **Claude Code** = the persistent application + orchestration: the self, the loops, the
  membrane, the store, the UI. Runs after the week ends.
- **Claude Science** = the Tester's environment: literature + code + compute to actually
  run the first-pass reanalysis that closes the loop (2.5). The one thing that turns a
  flagged contradiction into a tested result.

### 5.7 Anti-slop, concretely (the judge-facing safety story)
1. Swarm agents **read**; they never write to the self.
2. Candidates cross the membrane only with **convergence + provenance + calibration** [E].
3. High-stakes claims require **human adjudication** → then anchored [E].
4. Every self-belief is **provenance-typed** (`READ/INFERRED/HUMAN_CONFIRMED/TESTED`) so
   "the AI thinks" is never confused with "it's true."
5. The self stays **small on purpose**; scale lives in the disposable swarm.
6. A first-class **error log**: overrides and refuted tests are recorded and update the
   taste/strategy — a researcher that *updates* rather than a crank.

---
## PART 6 — Design & Layout (max depth; every screen)

**Design principle:** it must read as a *mind at work*, not a dashboard. The user should be able to "look over the shoulder" of a researcher and see what it's thinking, what it cares about right now, and why. Legibility is the product.

**Aesthetic direction:** calm, editorial, notebook-like — closer to a scientist's bound lab journal + a live systems console than a BI tool. Monospace for the researcher's "voice"/notebook; serif for synthesized reviews; a restrained palette with one accent for *live activity* and one for *needs-human*. Motion only where it signals real state change (a belief updating, an agent returning).

### 6.1 The Researcher Dashboard — "its mind at a glance"
The home screen = the **Self**. Shows: name + disposition; **current interests** as weighted chips (weight = attention allocation, live); **active research programs** with a one-line status; an **attention meter** (where its compute is going right now); and a **recent moves** ticker (last N notebook lines). This is where you *meet* the researcher.

### 6.2 The Living Notebook — "watch it think"
A timestamped, append-only stream in the researcher's own voice:
`noticed → suspected → spawned N readers → found (3 support / 1 contra) → updated belief X → flagged for human`. Each entry links to the evidence and the belief nodes it touched. This is the demo's beating heart (framing (a)) and the auditability story at once.

### 6.3 The Argument-State view — the evolving narrative of one question (3.1)
For a selected question/target: a **trajectory chart** (support velocity & acceleration over time, independence ratio, citation-vs-support divergence), an **inflection marker** ("decelerating since …"), and a prose **state-of-the-argument** ("settled: … / contested: … / current front: …") that the researcher rewrites as evidence arrives. Not a snapshot — a story with a derivative.

### 6.4 The Assumption / Dependency graph (3.2 + 3.3)
An interactive DAG of the subfield's claims with **load-bearing** nodes sized by downstream dependency mass and colored by independent-support. Click a node → "if this fell, these N downstream conclusions weaken" (fragility preview). This is the "what is this field actually standing on?" view no competitor has.

### 6.5 The Experiment Queue — the "useful" screen (3.4)
A ranked list: **highest value-of-information ÷ cost** experiments. Each row: the question it resolves, how much downstream literature it de-risks, whether public data already exists (one-click → hand to the Tester), and estimated cost tier. This is the screen that makes a PI say "I want this."

### 6.6 The Human Handoff inbox (2.4 + 3.7)
Structured judgment calls, each a pre-assembled **dossier**: the contradiction, the evidence on both sides, the researcher's candidate explanations, and the exact question ("which explanation holds, or is it a fourth?"). The human's answer **anchors** a belief [E] and is attributed forever. Frames the human as the *resolver*, not a reader.

### 6.7 The Artifacts shelf — its body of work
Auto-written **mini-reviews** (serif, cited, with an explicit "unresolved dissents" section), **side-project** threads it returns to, and the **error log** ("times I was wrong") as a first-class, visible artifact — the credibility signal.

### 6.8 The live "swarm" view (demo framing (a))
A real-time visualization of the bounded swarm: agents spawning, reading, returning candidates, and the **membrane** admitting/rejecting them into the self — literally showing "scale of reading, discipline of believing." Great for conveying the architecture without a slide.

### 6.9 What the demo camera lingers on
Dashboard (meet it) → Notebook (watch it think) → a live self-test loop closing on the Argument-State/Experiment screens (watch it *act*) → Human inbox (watch the division of labor) → Artifacts (see its body of work). Money-shot = the loop closing on one real contradiction.

---
## PART 7 — Expansion / The Bigger Vision
- **7.1 A lab, not a loner.** Spawn *several* researchers with different dispositions and interests; let them cite, challenge, and delegate to each other. Disagreement between synthetic researchers becomes a signal (and a dataset). Human PIs manage the lab.
- **7.2 Beyond drug targets.** The engine is domain-agnostic: any contested empirical question with a literature and public data (materials, climate, ML itself).
- **7.3 The always-on colleague.** It watches your subfield and pings you the day the front moves — a standing collaborator, not a session.
- **7.4 Why it matters if it works.** Science's bottleneck is increasingly *synthesis and prioritization*, not data generation. A synthetic researcher that maintains the living state of a field and points at the highest-leverage next experiment attacks that bottleneck directly.

## PART 8 — Real Use Cases (named users)
- **8.1 Gladstone-style lab** de-risking a target before committing bench-months: "is this rationale load-bearing on one un-replicated study?"
- **8.2 Trial designer** checking whether a target's support is real or citation-inflated (3.1 trajectory + 3.2 dependency).
- **8.3 A PI "hires" a synthetic colleague** to watch their subfield and maintain its argument-state.
- **8.4 The demo narrative** (one worked story): seed interest in neuroinflammation-in-neurodegeneration → researcher reads at scale → flags a contradiction between two well-powered studies → generates a falsifiable sub-hypothesis → Dataset-scout finds a public dataset → Claude Science runs a first-pass reanalysis → writes the result into the argument-state and a mini-review → escalates the one call it can't make to a human.

## PART 9 — Hackathon Execution
- **9.1 Demo architecture:** build (a) "watch it think" as the system; anchor the money-shot on (b) one closed self-test loop.
- **9.2 Proof of the bigger vision:** show the *overnight-run notebook* — hours of autonomous moves — as evidence it's always-on, even if the live demo shows one loop.
- **9.3 Seeded + emergent:** one seeded program in your domain (sanity-checkable) **plus** one interest it spawned itself.
- **9.4 Position out loud:** name scite / Open Targets / PaperQA2 / MedKGent and state exactly the piece you built that they don't (the acting loop + the self). Judges from Gladstone/Anthropic will respect that you know the landscape.
- **9.5 Scope honesty:** "real but scaled" — tens of agents, one notebook, one closed test — with the architecture that proves it scales. Never fake the swarm.
- **9.6 Day-by-day (always-demoable):**
  - **D1** belief-store + schema + living-docs self; ingest a small seeded corpus.
  - **D2** swarm readers + **adaptive membrane** [E]; notebook v1.
  - **D3** argument-state (3.1) + dashboard; first trajectory.
  - **D4** hypothesizer + dataset-scout + **one Claude Science test** closing the loop.
  - **D5** human-handoff inbox + anchoring [E]; dependency graph (3.2) on one subfield.
  - **D6** experiment-value queue (3.4); mini-review artifact; self-spawned interest.
  - **D7** overnight autonomous run; polish the money-shot; record fallback demo.
- **9.7 Risk register:** live autonomy wanders → rails + pre-recorded fallback of the loop; API/rate limits → cache the demo corpus + results; extraction noise → restrict demo to a curated subfield with known ground truth; Claude Science test fails live → pre-run it and replay, and be honest that it's a replay.

---
## PART 10 — The Build Prompts for Claude Code / Claude Fable (max depth)

> Hand these to Claude Code in order. Each is self-contained, states acceptance criteria, and assumes the evidence-based architecture from Parts 3/5 and the findings in `results/FINDINGS.md`. **Keep the research posture:** where a design choice isn't yet evidence-backed, the prompt tells the agent to run a sandboxed test first and record it, not to guess.

### 10.0 Master project brief (paste first)
```
You are helping build "Synthetic Researcher": a persistent, always-on research agent
for the biomedical literature that maintains a durable SELF (interests, beliefs,
memory, taste) and uses an ephemeral SWARM of bounded agents to read at scale, while
closing an agentic loop from a flagged contradiction -> falsifiable hypothesis ->
located public dataset -> first-pass reanalysis (Claude Science) -> written back into
its belief-state, and escalating to humans exactly when it needs wet-lab results or
experimental judgment.

Non-negotiable principles (derived from our experiments, see results/FINDINGS.md):
1. Separate SELF (durable, small) from SWARM (ephemeral, vast). Swarm agents READ;
   they never write to the self directly.
2. Membrane before commit: convergence + provenance + calibration. Adaptive: fast-path
   under benign input, strict independent-source quorum when correlated disagreement is
   detected (poisoning signal).
3. Human-confirmed beliefs are ANCHORED: resistant (not immune) to swarm overwrite.
   This is validated: under correlated poisoning, anchoring retained 100% of verified
   beliefs vs 71% naive. Never let surprise-seeking overwrite an anchor without human
   sign-off.
4. Every belief is provenance-typed: READ / INFERRED / HUMAN_CONFIRMED / TESTED.
5. The self is stored as human-readable living docs (self/*.md, self/beliefs.json) so a
   user can literally read its mind, backed by a claim-graph for structured queries.
6. Legibility is the product: a timestamped notebook of every move.
7. Research posture: if a design choice isn't evidence-backed, write a small sandboxed
   test first, record results under /experiments and /results, then implement.

Reuse, don't rebuild: Europe PMC/PubMed retrieval, Open Targets API, SemMedDB,
ClinicalTrials.gov (incl. terminated), GEO/ArrayExpress/CZI Perturb-seq. Build fresh:
the self, the membrane+anchoring, the loops, the intellectual engine (Part 3), the UI.

Tech: Python orchestration; a graph store (start with SQLite+networkx or DuckDB, justify
after a quick test); a lightweight web UI (justify stack via the frontend-design skill).
Claude Code orchestrates; Claude Science runs the first-pass reanalyses.
```

### 10.1 Architecture spec to hand the agent
```
Implement these modules with clean interfaces and tests:
- store/            belief-graph schema (Part 5.3), versioned, provenance-typed, anchor flag
- self/             living-doc read/write: identity.md, agenda.md, beliefs.json,
                    notebook.md, errors.md, strategies.md; hydrate() and consolidate()
- swarm/            agent job types (reader, extractor, dependency_tagger, cross_checker,
                    dataset_scout, hypothesizer, tester, reflector); each pure + testable
- membrane/         adaptive commit policy (Part 5.4) with the correlated-disagreement
                    detector; unit-tested against a poisoned-stream fixture (reuse
                    experiments/exp_when_protection_matters.py as the test oracle)
- loops/            inner (read->update), outer (reflect->prioritize->act), delegation,
                    self_test (Claude Science), artifacts
- engine/           trajectory (3.1), dependency+load-bearing (3.2), fragility (3.3),
                    experiment_value (3.4), silence (3.5), cross_field (3.6)
- api/ + ui/        the seven screens (Part 6)
Acceptance: each module has tests; membrane tests reproduce the poisoning crossover;
self can be killed and re-hydrated from living docs with no belief loss.
```

### 10.2 Data-source integration plan
```
Build thin, cached clients (respect rate limits; cache aggressively for demo):
- europepmc_client: search + full-text where available
- opentargets_client: target-disease evidence + trial-stoppage dataset
- semmeddb_client: semantic predications for dependency seeding
- clinicaltrials_client: include TERMINATED/withdrawn (for silence detector 3.5)
- datasets_client: GEO / ArrayExpress / CZI Perturb-seq availability lookup (for 3.4/loop)
Acceptance: given a target, return normalized evidence; given a hypothesis, return
candidate testable datasets. All cached to a local fixture for offline demo.
```

### 10.3 Sequenced build tasks (each ends demoable) — mirrors Part 9.6
```
T1  store schema + living-doc self + hydrate(); load a curated seed corpus (one subfield).
T2  reader+extractor swarm; adaptive membrane [reuse poisoning oracle as its test]; notebook.
T3  trajectory engine (3.1) + dashboard + argument-state screen.
T4  hypothesizer + dataset_scout + ONE Claude Science self-test closing the loop end-to-end.
T5  human-handoff inbox + anchoring; dependency graph (3.2) on the subfield.
T6  experiment-value queue (3.4); auto mini-review; self-spawned second interest.
T7  overnight autonomous run to fill the notebook; polish money-shot; record fallback.
For EACH task: if a sub-choice is unproven, add a test under /experiments first.
```

### 10.4 The "research-and-verify" standing instruction (paste into the agent's config)
```
Before making any non-trivial architectural or modeling decision:
1. State it as a hypothesis with a metric.
2. Write a minimal sandboxed experiment (Python; ML/RL/stats as needed).
3. Run it >= 20 seeds; report mean +/- 95% CI; save code to /experiments, results to /results.
4. If the result contradicts the assumption, follow the evidence and write down the reversal.
5. Only then implement, and cite the experiment in a code comment.
Keep every result reproducible (seeded). At the end, compile /results into a paper draft:
"On constructing a persistent, continuously-learning synthetic researcher."
```

### 10.5 Demo-day checklist
```
[ ] Cached corpus + pre-run Claude Science result (with live attempt + honest fallback)
[ ] Seeded program shows a real trajectory; one self-spawned interest visible
[ ] Notebook shows an overnight run
[ ] One contradiction closes the full loop on camera
[ ] Human inbox shows one dossier -> anchored belief
[ ] Artifacts shelf shows a mini-review + the error log
[ ] Positioning slide: scite/OpenTargets/PaperQA2/MedKGent vs. the piece we built
[ ] FINDINGS.md crossover result shown as the "we tested our own architecture" proof
```

---

## Appendix A — Experiments already run (in this repo)
- `experiments/exp_memory_core.py`, `exp_memory_v2.py`, `exp_when_protection_matters.py`
- `results/FINDINGS.md` — **key result:** identity-anchoring is unnecessary under benign
  noise but decisive under correlated poisoning (100% vs 71% verified-belief retention
  during attack; 88% vs 68% recovery). The membrane/anchor design in Part 5 is *derived*
  from this, not assumed.
- **Next experiments to run during the build** (stubs to create):
  E5 trajectory-vs-static outcome backtest (3.1); E6 dependency-extraction precision vs
  gold (3.2); E7 experiment-value ranking vs expert (3.4). Each pre-registered with a
  metric and a go/no-go bar before it ships.

## Appendix B — The paper this becomes
Structure: (1) the synthesis/prioritization bottleneck; (2) the self/swarm architecture;
(3) the membrane+anchoring result (our headline empirical contribution); (4) the acting
loop; (5) the intellectual instruments (3.1-3.6) with their validation experiments;
(6) human-as-resolver as compounding infrastructure; (7) limitations & threats to validity.
The through-line: *a persistent LLM researcher is less a prompt problem than a memory,
calibration, and division-of-labor problem — and here is quantified evidence for how to
build the memory so it survives an adversarial corpus.*
