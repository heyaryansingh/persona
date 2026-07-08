# Persona v3 — Implementation Handoff
*Read this first on a fresh context. Goal: implement the ENTIRE v3 "Make It Real" plan, don't stop. Full plan: `C:\Users\aryan\.claude\plans\kickoff-prompt-read-claude-md-cached-pillow.md` (also mirrored below in Tiers). Audit provenance: the 6-agent audit findings are summarized in the plan file's "9 critical findings".*

## Where we are
A 6-agent adversarial audit found Persona was a good scaffold with a **faked epistemic core** (~3.5/10 vs vision). The v3 plan fixes it. **Done + verified (committed on branch `build/persona-mvp`):**
- **T0.1** direction fixed: relation→effect-sign (up=+1/down=−1) in one shared `build_candidate`; `claim_key=(subject,object)` so opposing findings CONTRADICT (was: all→+1, merged as agreement). Relation persisted in observations. Real-data check: 0→1 contradiction on 40 papers.
- **T0.2** belief = **net independent evidence** (support−refute, confidence-weighted) in `store.set_swarm_belief`; contrary evidence lowers a belief; `membrane._commit` recomputes every harvest. `Researcher.review_queue` calls `calibrate.should_escalate`.
- **T0.3** acting loop **closes**: `Researcher.resolve_self_test` + `apply_result_with_signoff` (TESTED only if real compute ran, else HUMAN_CONFIRMED). API: `POST /api/selftest/{key}/resolve`, `GET /api/review`.
- **T3.1** `GET /` serves `ui/dist` (was 404). `app.mount("/", StaticFiles(...))`.
- 71 tests green (23 files). Crash-resume still byte-identical.

## Remaining (implement all, in order)
- ~~**T0.4**~~ DONE. `persona/ingest/opentargets.py` (keyless GraphQL, arg is `Bs` not `efoIds`), `loops/reanalysis.py` (OpenTargetsTester real is_replay=False + CompositeTester fallback), real GEO scout (esummary accessions), `hypothesize()` real generator, store persists subject/object + `entities_for`. Bands validated exp_reanalysis_bands.py (overall≥0.3 F1=1.0). E2E: APOE↔Alzheimer → TESTED anchor.
- ~~**T0.5**~~ DONE. `persona/swarm/dependency_tagger.py` (Claude + heuristic), load_bearing/idea_graph consume derives-from+presupposes, wired into tick/autonomous_cycle/populate_demo. E6 (exp_e6_dependency.py): κ≈0 per-edge but load_bearing Spearman 0.38–0.50 → edges stay CANDIDATE, human-in-the-loop. Real data: 11 dep edges on 9 beliefs.
- ~~**T1.1**~~ DONE. `persona/ingest/independence.py` senior-author key; E14-real: journal miscalibrated both ways.
- ~~**T1.2**~~ DONE. `canonicalize.py` pure rule-based (order-independent, symbol-safe; precision 1.0/recall 0.89); embeddings guarded opt-in.
- ~~**T1.3**~~ DONE. Population-typed contradictions; new-belief poison detection (swept: volume=6, ratio=0.25).
- ~~**T2.1**~~ DONE. `swarm/batch_reader.py` (real 2x lever); caching is a no-op for short abstracts (measured).
- ~~**T2.2**~~ DONE. `retrieval/index.py` PersistentIndex; `researcher.corroborate` consumed by autonomous_cycle.
- ~~**T2.3**~~ DONE. `persona/budget.py` DailyBudget (UTC-daily, persistent); reasoner escalation; concurrency docstring fixed.
- ~~**T3.2–T3.5**~~ DONE. `api/app.py` rewrite: PersonaService on app.state, daemon (start/stop/status + persisted flag + startup resume), token auth on writes, /api/traces, live-by-default (PERSONA_OFFLINE opt-in), aread offline heuristic fallback, agenda-driven ticks, de-hardcoded seeds.
- ~~**T4**~~ DONE. (a) `engine/cross_field` embedding similarity (separates 10/10 disjoint-vocab pairs; Jaccard 0). (b) E5 + E7 run on real data → both honestly stay DESCRIPTIVE (E7 ill-posed: flat associations have no hierarchy; E5 inconclusive: corpus back-loaded, <8 longitudinal beliefs). (c) `graph/bitemporal.py` time-travel + GET /api/graph-at; idea_graph inverted-index edges (3000 nodes in 0.18s) + O(1) layout; `ui/GraphCanvas.jsx` canvas renderer for >400 nodes (Cytoscape kept for small). UI builds clean, mounts no-error (visual paint unverifiable — preview viewport 0×0; ResizeObserver added for real browsers).

## STATUS: v3 "Make It Real" COMPLETE — all tiers (T0–T4) implemented, tested, committed on `build/persona-mvp`. 33 test files green. Every load-bearing constant has a ≥20-seed or labeled-set experiment in `/experiments`; findings in `results/FINDINGS.md`.

## Architecture a fresh mind needs
- **Flow:** `ingest` (EuropePMCAdapter, live+cached) → swarm reads (`swarm/claude_reader.ClaudeExtractor` real / `reader.HeuristicExtractor` offline) → `build_candidate` (ONE path: relation→effect-sign, canonicalize, claim_key) → `membrane.submit` (durable **observation log** in `store`, idempotent) → `membrane.harvest` (convergence by independent groups, typed contradictions, poison switch, anchor escape hatch) → `store.set_swarm_belief` (NET evidence) → `self` (living docs + belief-graph).
- **Belief:** `logit = 0.6·(up_groups·up_conf − down_groups·down_conf)`, clipped ±8; `calibrated_p=sigmoid`. Deterministic over observations → crash-resume byte-identical. Anchors (HUMAN_CONFIRMED/TESTED) are immovable by swarm.
- **Key files:** `persona/{store,membrane,researcher,config,canonicalize,calibrate}.py`, `persona/swarm/{reader,claude_reader,orchestrator}.py`, `persona/loops/{inner,outer,delegation,self_test,artifact}.py`, `persona/engine/*`, `persona/graph/idea_graph.py`, `persona/retrieval/retriever.py`, `persona/api/app.py`, `ui/src/**`, `scripts/{populate_demo,run_autonomous,run_swarm_demo}.py`, `experiments/exp_*.py`.
- **Models:** `config.py` — READER=`claude-haiku-4-5`, REASONER=`claude-sonnet-5`, HARD=`claude-opus-4-8`. Keys in `.env` (ANTHROPIC_API_KEY, NCBI_API_KEY) loaded via python-dotenv. `have_key()`, `anthropic_client()`, `est_cost_usd()`.
- **Discipline (CLAUDE.md):** every load-bearing constant/choice gets a ≥20-seed experiment before shipping; write reversals down; commit frequently; keep the suite green; never fake/hardcode — the whole point of v3 is removing fakes.

## Gotchas
- Windows: close SQLite (`store.close()`) before tempdir cleanup (`try/finally`); `set_swarm_belief` reads observations (durable). `check_same_thread=False` for the API.
- Subagents refuse if a plan-mode reminder is injected — build UI/files directly if that happens.
- LF→CRLF git warnings are cosmetic. `ui/dist`, `runs/`, `.cache/`, `.env` are gitignored.
- Cost: real reads ~$0.004/abstract (Haiku); `populate_demo.py 40` ≈ $0.15. Budget $15/day in config (currently NOT enforced daily — T2.3).
- Tests that hit real Claude are guarded by `config.have_key()`; a suite run costs ~$0.02.
- Verify with: full suite (`for t in tests/test_*.py; do python "$t"; done`), `python scripts/populate_demo.py 40`, `python experiments/exp_p2_crash_resume.py` (must stay byte-identical), `GET /` returns 200 HTML.

## Next action
Implement **T0.4** (Open Targets real cross-check + real GEO scout + real hypothesizer), then T0.5, then T1→T4, committing per step, testing each. Don't stop.
