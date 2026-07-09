# Persona v5 — Handoff (read first on a fresh context)

**Goal:** turn v4 (a belief-triple accumulator) into a real persistent mind: synthesis + learning, defensible provenance, multi-persona gallery, real deliverables (cited reviews, LaTeX papers, journal, idea log, field map), and autonomy-without-degradation. Full plan (approved): `C:\Users\aryan\.claude\plans\kickoff-prompt-read-claude-md-cached-pillow.md` (Persona v5 — research-cited, 11 phases). Branch: **`build/persona-v5`**. v4 is on `build/persona-v4` (complete); v3 archived under `archive/*_v3`.

## DONE — P1: ingestion hardening + seeded-gate (committed)
The two things the owner hit that made v4 unusable:
- **Seeded-gate** (`daemon/supervisor.py` `_scheduler_loop`): daemon does NOTHING until `selfmind.is_seeded()`; emits "blank slate — waiting for a human to seed". `selfmind.seed()` now APPLIES the user's interests even on a populated self (v4 silently dropped them); `selfmind.reset()` + `--fresh` + `POST /api/reset` for a blank start.
- **Multi-source ingestion**: `persona/ingest/service.py` (shared `IngestService`: hishel SQLite HTTP cache → re-scouts are cache hits; per-host rate limiter; retry that honors Retry-After but FAILS OVER fast on long bans). `persona/ingest/sources.py` (`search_multi`: OpenAlex→Crossref→Europe PMC→arXiv failover, cross-source DOI dedup, never returns [] silently). `reader.scout` uses it; `fetch.py` routes PDFs through the service (+ Europe PMC full-text XML).
- Verified WITH OpenAlex hard-banning this IP: unseeded → 0 reads; after seed → 48 reads/37 claims via Crossref failover, no hang.

## DONE (cont.) — P2/P3/P4
- **P2** Persona first-class object: `persona_obj.py`/`paths.py`/`context.py` (current-persona ContextVar + default fallback); log()/budget()/get_kg()/selfmind/reader/batch/analyst resolve the context persona; Daemon binds its persona in run().
- **P3** multi-persona: `manager.py` (registry under `personas/<id>`, graph `persona_<id>`, per-persona daemon lifecycle); `api/app.py` routed by `/api/persona/{id}/*` + startup supervisor loop; gallery UI. Isolation experiment PASS.
- **P4** provenance: quote on SUPPORTED_BY edge + doi/url on Source; `kg.provenance(cid)` + `/provenance/{cid}` + clickable UI. claim identity=(subject,object,effect_sign). confidence=avg per-source (bounded). `memory/history.py`; analyst manifest.json + log.md.

## REMAINING — P5–P11 (in order; each leaves a runnable system)
- **P2 Persona as first-class object (N=1).** De-globalize: a `Persona` dataclass owns paths/kg/queue/events/budget/canon/vectors/harvest_lock/daemon. Route every module fn that reads a global through `persona` arg. New: `persona/persona_obj.py, paths.py`; refactor `config.py` (paths→Paths built at create-time not import), `events.py` (`_LOG`), `budget.py` (`_B`), `memory/membrane.py` (`_KG`,`_HARVEST_LOCK`,announced file), `memory/kg.py` (graph name), `daemon/supervisor.py`, `api/app.py` (`_daemon`). Keep behavior identical. The 8 globals + file:line are in the audit (see plan Context #3).
- **P3 Registry + gallery (multi-persona).** `PersonaRegistry` (persisted id→workspace index) + `PersonaManager` (create/seed/load/pause/delete); `Supervisor` holds `{id: asyncio.Task}` sharing ONE `IngestService`; API `/api/persona/{id}/...`; per-persona FalkorDB graph `persona_{id}`; gallery UI (cards + create/seed). Isolation test.
- **P4 Provenance unification.** ONE canonical `claim_id` used at both disk+graph (fixes the disk↔graph mismatch: disk uses raw hash `reader._claim_id`, graph uses canonical `kg.add_claim`). Store `quote`+`source_id`+`char_offsets` in the KG Claim; `/persona/{id}/belief/{bid}/provenance` (belief→claim→source→quote); append-only `belief_history`; sandbox `manifest.json` (code/data/figure/image-digest/pip-freeze hashes) + real `log.md`.
- **P5 Synthesis engine.** `memory/vectors.py` (sqlite-vec, per persona) + `synthesis/{communities,synthesizer,consolidator,fieldmap}.py`: community-detect claim graph → per-community cited synthesis NOTE (Anthropic Citations API, grounded in that community's quotes) written to `notes/` + `SynthesisNote` KG node; Haiku citation-checker rejects unsupported sentences; RAPTOR roll-up. Analyst READS notes+KG (v4 it read nothing → uncited).
- **P6 Consolidation + coherence (anti-degradation).** `coherence.py`: sleep-cadence consolidation; `self/*.md` → bounded memory-blocks edited via tool calls (no free-rewrite drift); eval-in-the-loop gate (reject edits contradicting TESTED/HUMAN_CONFIRMED anchors w/o new independent evidence); drift detection + frozen self-consistency eval-set. Re-ground in KG every cycle (never on own prose — the #1 long-horizon failure).
- **P7 Field map.** community hierarchy → navigable (subtopics→claims→contradictions→open-questions→papers).
- **P8 Discovery/action loop.** hypothesis-from-gaps → Elo tournament → meta-review→strategies.md → route to sandbox experiment OR evidence-backed human escalation; idea/lead collection.
- **P9 Cited-review engine + journal** (AutoSurvey/STORM staged, <5% unsupported sentences; append-only dated journal).
- **P10 Paper engine (LaTeX→PDF)** (experiment-tree→writeup→tectonic compile-with-retry in sandbox; matplotlib figures; BibTeX from KG). Add tectonic/texlive to persona-sandbox image.
- **P11 Human-interface polish**: membrane-funnel view, live-experiment view, workspace file-browser + live change feed (watchdog→SSE), evidence-backed escalation inbox (quotes/papers/labs/DOIs, clickable-through), optional side-by-side compare.

## Gotchas
- **OpenAlex is banning this IP until ~2026-07-09 21:00 UTC** (Retry-After 75534s) from heavy v3/v4 testing → test ingestion via Crossref/Europe PMC/arXiv (all 200). The failover handles it automatically.
- Windows: cp1252 stdout crashes on unicode — `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` in scripts; ASCII in `print`. Close SQLite before tempdir cleanup (or `TemporaryDirectory(ignore_cleanup_errors=True)`).
- Preview browser reports a 0×0 viewport → can't verify canvas/WebGL pixels here; DOM/data wiring verifies via `preview_eval`. cosmos.gl (P-later) needs a real browser.
- FalkorDB runs in Docker (`persona-falkordb` on :6379); sandbox image `persona-sandbox` (python:3.12-slim + sci stack). `.env` has ANTHROPIC_API_KEY + NCBI_API_KEY; never commit `.env`.
- New v5 deps installed: httpx, hishel, tenacity, aiolimiter (service uses hishel + a sync limiter + manual Retry-After loop; tenacity/aiolimiter not yet imported). P5 needs: sqlite-vec, networkx. P6 watchdog.

## Gating experiments (run under /experiments, ≥20 seeds where stochastic → results/FINDINGS.md)
Synthesis method (gates P5), coherence mechanism (gates P6), deliverable quality ≥90% quote-support (gates P9-10), ingestion resilience (gates P1 — partially shown), multi-persona isolation (gates P3).

## Next action
P2: introduce the `Persona` object + `Paths` and de-globalize the 8 singletons with N pinned to 1 (behavior unchanged), so P3 can run N isolated personas. Then P4 provenance, P5 synthesis (the core new capability).
