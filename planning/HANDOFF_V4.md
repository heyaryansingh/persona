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

## REMAINING (in order)
- **Phase E (gating experiments):** #1 extraction path (custom+direct-write vs Graphiti-native — I already chose custom in extract.py; validate cost/F1), #2 **self-continuity across ≥50 fresh-context loops** (the product bet — run early), #3 retrieval (graph multi-hop vs vector), #4 chunking, #5 embeddings (bge-small vs Voyage), #6 poisoning CI oracle. → `results/FINDINGS.md`, ≥20 seeds where stochastic.
- **P2 Memory + membrane v0:** stand up FalkorDB (Docker) + `graphiti_core`; `memory/kg.py` (write claims as bi-temporal, provenance-typed edges; **claim identity = (subject,relation,object,effect_sign)** → opposing sign = CONTRADICTS, not merge), `memory/membrane.py` (independence-by-affiliation, convergence≥K, poisoning, anchor policy), projection to `self/beliefs.md`. *Verify:* two papers, opposite effect-signs → CONTRADICTS edge.
- **P3 Scale ingestion:** Batch API extractor, async fetch/paging, all connectors, backpressure/budget → thousands/day.
- **P4 Self evolves:** Opus reflection task rewrites `self/*.md`; A-MEM notes; interest reweighting; surprise-driven enqueue.
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
