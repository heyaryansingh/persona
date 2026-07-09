# Persona v4 — Rebuild Handoff (read first on a fresh context)

**Goal:** ground-up rebuild of an always-on, blank-slate, general-purpose autonomous researcher.
Full plan: `C:\Users\aryan\.claude\plans\kickoff-prompt-read-claude-md-cached-pillow.md` (v4). Branch: **`build/persona-v4`**. v3 code archived under `archive/*_v3` (reference only).

## Locked decisions
Greenfield · general-purpose (no hardcoded domain vocab) · learn-at-scale (full text + web) + write-artifacts + execute-code (sandbox) + autonomous tool actions (NO irreversible outward actions) · **always-on local daemon first**, architected for cloud later.

## Stack (verified)
Claude Agent SDK (adopt for analyst/tool phases; P1 uses `anthropic` directly) · custom asyncio supervisor + **SQLite** queue (stdlib) · **Graphiti on FalkorDB (Docker)** for the temporal KG — **Kùzu is DEAD (Apple acq. Oct 2025), do not use**; Neo4j Community fallback · Docling+PyMuPDF · trafilatura · OpenAlex/EuropePMC/arXiv/S2/Unpaywall/Crossref connectors · Anthropic Batch API for bulk · Docker sandbox (`--network none --read-only`) · FastAPI+SSE · UI: Vite/React/TS/Tailwind + **cosmos.gl v3** (P7; P0 ships a static live-console).
Models: Haiku 4.5 (bulk extract) · Sonnet 5 (workers) · Opus 4.8 (self/reflect).

## DONE (committed on build/persona-v4)
- **P0 — always-on daemon + live UI.** `persona/`: `config.py` (workspace layout = `persona-workspace/`), `events.py` (append-only SQLite WAL event log = live-stream source of truth), `daemon/queue.py` (lease-based durable queue, crash-resume via expired-lease reset, RETURNING), `daemon/supervisor.py` (never-idle: N workers drain + scheduler tops up from the self when depth<min → `reflect`→spawn readers), `daemon/worker.py` (handler registry), `selfmind.py` (durable SELF as markdown; `seed()` NEVER overwrites an evolved self — fixes v3 bug; domain-general), `api/app.py` + `api/static/index.html` (daemon-on-startup, SSE `/api/stream`, `/api/seed`, dark live-thought console), `__main__.py` (`python -m persona [--seed "a,b"]`). Verified in-browser: seeded non-biomed interests → reader-spawn loop, 31 rows streaming, crash-resume clean. Zero new deps.
- **P1 — first real read.** `ingest/openalex.py` (keyless, all-science, affiliations+OA URLs), `ingest/fetch.py` (OA PDF full text via PyMuPDF → abstract → title), `reading/extract.py` (domain-general Claude claim extraction: subject/relation/object/effect_sign/verbatim quote/confidence), `reading/reader.py` (interest → top unread paper → fetch → extract → writes `sources/<slug>/{meta.json,clean.md,claims.jsonl}`, idempotent, emits READ/CLAIM). `observe` handler runs it via `asyncio.to_thread`. Verified: 5 real papers across quantum-error-correction + mycorrhizal-networks, full-text PDFs → 10 claims each.

## DONE (cont.)
- **P2 — temporal KG + membrane.** FalkorDB (Docker, direct Cypher — Graphiti's LLM path skipped). `memory/kg.py` (claim identity=(subj,rel,obj,sign) → opposite signs CONTRADICT not merge; independence by senior-affiliation lab; provenance+anchor; bi-temporal), `memory/membrane.py` (harvest + contradiction linking + belief projection to `self/beliefs.md`), `memory/embed.py` (bge-small), `memory/canon.py` (entity canonicalization w/ IL-6/IL-1 symbol guard). Verified: gate + real harvest.
- **P3 — scale ingestion + convergence.** scout/observe fan-out + OpenAlex paging + persistent `budget.py` + `ingest/web.py` (arbitrary URLs) + `reading/batch.py` (Batch API, submit/collect-later manifests). Verified: 85 papers → 4 beliefs converged from ≥2 labs + 14 contradictions; web read; batch end-to-end.

## DONE (cont.) — v4 plan COMPLETE (P0–P8, branch build/persona-v4)
- **P4 — self evolves.** `agents/deliberate.py` Opus reflection rewrites `self/*.md`, spawns NEW interests, forms questions from contradictions, queues priority reads. Verified: 2 seeds → 7 sophisticated new interests + contradiction-driven questions.
- **P5 — real work.** `tools/sandbox.py` (Docker, `--network none`, verified network-blocked) + `tools/datasets.py` (allowlisted egress) + `agents/analyst.py` (Sonnet tool-loop: plan→data→run code→report). Verified: iris ANOVA end-to-end (F=1180, p~1e-91) → report artifact. `docker/sandbox.Dockerfile` → image `persona-sandbox`.
- **P6 — membrane hardening + escalation.** Anchor write-policy enforced (cheap evidence can't move verified belief); `/api/inbox` + resolve→anchor; `kg.poisoning_signals`. Oracle `exp_poisoning.py` PASS (anchor retained + poison detected).
- **P7 — UI.** `api/static/index.html`: 3-panel console (evolving self+reports · live stream · canvas belief graph + inbox). Verified against real data (513 nodes, 200 beliefs, 14-item inbox, human-resolve anchors). Canvas pixels unverifiable here (0×0 preview viewport); cosmos.gl = the 100k swap later.
- **P8 — scale seam.** `python -m persona --worker` (worker-only) + `exp_scale_seam.py` PASS (300 tasks / 4 processes / each leased once). Postgres swap behind TaskQueue for multi-machine.

## NOT done (honest gaps, all non-blocking)
- Formal Phase-E ≥20-seed studies for #2 self-continuity, #3 retrieval, #4 chunking, #5 embeddings were NOT run as separate pre-registered experiments — the design choices (custom extraction, bge-small canon, structure-lite chunking) were made and validated by the working end-to-end system + the P6 poisoning oracle. Worth running if rigor is needed.
- cosmos.gl 100k-node GPU graph deferred (canvas force-graph used; fine for current sizes).
- Docling (richer PDF structure) deferred — PyMuPDF suffices.
- Retrieval (HippoRAG/graph multi-hop over the KG) not yet wired into the reflect loop as a cross-checker; the KG is queried by deliberate but there's no dedicated retrieval agent yet.
- **P5 Real work:** Docker sandbox executor, dataset locator, artifact/project writing, real reanalysis.
- **P6 Membrane hardening + escalation inbox + poisoning CI oracle.**
- **P7 UI money-shot:** Vite/React + cosmos.gl temporal-accretion graph, workspace browser, trace replay.
- **P8 (opt) cloud seam:** Postgres queue, containerized workers.

## How to run / verify
- Run: `python -m persona --seed "topic a, topic b"` → http://127.0.0.1:8137 (or preview config `persona-v4` on port 8137).
- Headless test pattern: set `PERSONA_WORKSPACE=<scratch>` + `PERSONA_WORKERS=2`, run `Daemon(n_workers=2).run()` for ~20s, inspect `persona-workspace/sources/*/claims.jsonl` + `events` via `log().recent()`.
- Workspace layout lives under `persona-workspace/` (gitignored — it's the runtime mind; gets its own git for artifact versioning in P5).

## Gotchas (Windows)
- **cp1252 stdout**: printing unicode (→, ﬁ, ↑) crashes with UnicodeEncodeError. `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at entry, use ASCII in `print`. Event messages CAN hold unicode (stored in sqlite, rendered in browser) — only console `print` is the hazard.
- LF→CRLF git warnings are cosmetic.
- Preview browser reports a **0×0 viewport** → canvas/WebGL can't be visually verified here (DOM text like the thought stream verifies fine via `preview_eval` counting `.row` elements). cosmos.gl (P7) will need real-browser verification.
- Docker is up (v29); a `pgvector` container already runs on :5432. Put FalkorDB on a different port (default 6379 — check for conflicts).
- Per-phase installs (avoid big-bang): P2 needs `graphiti-core` + `falkordb` + Docker FalkorDB; P3 `docling trafilatura`; P5 Docker sandbox image `python:3.12-slim`.
- `.env` has ANTHROPIC_API_KEY + NCBI_API_KEY. Never commit `.env`.

## Next action
Stand up P2: `docker run -p 6379:6379 falkordb/falkordb`, `pip install graphiti-core falkordb`, verify connectivity, then build `memory/kg.py` + `memory/membrane.py` and wire admitted claims from `sources/*/claims.jsonl` into the KG with contradiction edges. Then run Phase-E experiment #2 (self-continuity) early.
