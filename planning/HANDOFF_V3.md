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
- **T0.4** REAL first-pass reanalysis: today it's Claude reasoning over a GEO accession STRING (`loops/self_test.py` ClaudeScienceTester) — no data touched. Do: (a) improve `GEODatasetScout` — esearch→esummary→real GDS/GSE accession+title+n_samples; (b) add a real data cross-check — **Open Targets GraphQL (keyless)**: for a (gene/target, disease) claim, query the association score + genetic evidence → outcome from a REAL number, `is_replay=False`; fall back to Claude reasoning otherwise; (c) `hypothesize()` → generate ≥2 falsifiable candidates conditioned on the claim's entities (not a fixed template).
- **T0.5** Build the FLAGSHIP `derives-from`/`presupposes` dependency graph (E6). Today extraction emits none → `engine/dependency.load_bearing` returns `{}` → `experiment_value` VoI returns 0 for all → idea graph is entity-co-mention only. Do: a `dependency_tagger` LLM pass emitting CANDIDATE edges into `store.edges` (INFERRED provenance) + citation-graph backbone; then load_bearing/VoI/idea-graph light up. Run E6 (IAA first, then rank-correlation); expected honest outcome = human-in-the-loop downgrade if precision low.
- **T1.1** real evidential independence (not journal-count): author-overlap + citation proximity + shared-cohort dedup + citation-echo screen. `ingest/`, `membrane.py`.
- **T1.2** fix canonicalization: biomedical normalizer (MeSH/UMLS/HGNC dict + MedCPT/SPECTER2 encoder), **validate the 0.72 threshold** with a ≥20-seed experiment, make clustering order-independent (deterministic). `canonicalize.py`. (Current risk: MiniLM false-merges IL-6/IL-1.)
- **T1.3** real contradiction typing from population/method/effect (now persisted!) not group counts (`membrane._type_contradiction`); poison detection for NEW false beliefs; derive thresholds by sweep.
- **T2.1** Batch API + prompt caching (cost levers, currently NOT implemented → cost ~2×). `cache_control` on a ≥4096-tok reader prefix; Batch backend behind the Extractor Protocol. `swarm/`.
- **T2.2** persistent vector index (on-disk FAISS/numpy keyed by doc_id); make retrieval a real loop cross-checker (fetch corroboration before commit); consume `autonomous_cycle`'s retrieval. `retrieval/`, `researcher.py`, `loops/inner.py`.
- **T2.3** genuinely daily persistent budget (SQLite keyed by UTC date; currently resets per AsyncSwarm/tick); Sonnet/Opus escalation on ambiguity; raise real concurrency (16→higher) or fix "hundreds" docstrings. `config.py`, `swarm/orchestrator.py`.
- **T3.2** real always-on: FastAPI `startup` background task / scheduler ticking `autonomous_cycle` (currently a for-loop script). `api/app.py`.
- **T3.3** auth (shared token) + move `_R`/`SWARM_EVENTS` off module globals + persist running state. **T3.4** wire observability (`obs` extra: OTel/Phoenix or lean in-house per-read token/cost trace). **T3.5** Swarm Control Room offline fallback (heuristic `extract_fn` when no key); default facade to LIVE adapter (fixtures=explicit offline opt-in); drive ticks from the agenda not `CACHED_QUERY`+3 startup ticks; de-hardcode Alzheimer's seeds.
- **T4** run E5 (trajectory vs strong static) + E7 (VoI vs Open Targets genetic prior) on real data → promote or keep descriptive w/ evidence; replace `cross_field` Jaccard w/ embedding similarity; bi-temporal graph module + Sigma.js/cosmos.gl 10k-node viz.

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
