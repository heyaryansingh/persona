# Persona v6 — Handoff (a free-minded researcher you can talk to, watch build, walk its mind, and put to work)

v6 builds on v5 (multi-persona synthesis + provenance + deliverables). Full plan:
`C:\Users\aryan\.claude\plans\kickoff-prompt-read-claude-md-cached-pillow.md`. Every phase below is
**implemented, validated (real API/data, in-browser), and committed**. Run: `python -m persona` →
http://127.0.0.1:8137 (or the `persona-v6` launch config on :8188 = `uvicorn persona.api.app:app`).

## What shipped (P0–P7, each committed)

- **P0 — control plane + visible/pausable cost.** Per-persona run-state RUNNING/PAUSED/HALTED in
  `ops/control.json`; scheduler + workers honor PAUSE (spend flatlines, in-flight drains); HALT stops
  the daemon (supervisor won't restart). Writable daily cap; per-task cost attribution (`cost` events).
  UI cost bar: live spend/cap meter, run pill, Pause/Resume/Halt, click-to-edit budget.
  Files: `persona_obj.py`, `daemon/supervisor.py`, `api/app.py` (`/pause /resume /halt /spend /budget`).
- **P1 — file & artifact browser.** `GET /files` (jailed tree), `GET /file` (inline any type), `POST
  /upload`. `Paths.safe()` = shared workspace jail. UI ⧉ files: tree + viewers (PDF/code/image/CSV/md/
  sandboxed-HTML). Surfaces the experiments/code/figures that already existed on disk.
- **P2 — conversation (steer, don't block).** `POST /say` runs `agents/converse.py` (Opus, grounded in
  self+KG, never invents) synchronously; captures a standing directive (`self/directives.md`, read by
  deliberate each cycle) + enqueues focus scouts. UI chat bar under the live stream.
- **P3 — navigable graph + evolution.** `kg.overview/neighbors/node/search` (ranked seed + expand from
  ANY node, mixed entity/source/note/experiment types, edges carry claim_id + ingest_time).
  `/graph/*` endpoints. UI ◉ explore graph: force-directed canvas, click-to-expand, inspector
  (beliefs→evidence), type filters, search, + a **time scrubber** replaying how the graph grew.
- **P4 — builder swarm + free mind.** `agents/builder.py`: diagram/art (sandboxed matplotlib→PNG),
  page (self-contained interactive HTML), code (runnable, sandbox-verified) — grounded + manifest-
  pinned (image digest + hashes + cost) + first-class **Experiment graph nodes**. `agents/freemove.py`:
  one Opus step picks any vetted registry action + rationale. `/build`, `/freemove`; UI ✦ build, ✧ free
  move. Unsupervised cadence stays human-triggered (safe default).
- **P5 — co-researcher (works for & with you).**
  · Knowledge transfer: `agents/knowledge.py` — `/topic/digest` (layered cited briefing: TL;DR /
    settled / contested / open / narrative + subgraph + evolution) and `/ask` (NL Q&A, cited, honest).
    UI ❋ brief / ask (citations click to provenance).
  · Ingest your work: `agents/mywork.py` + `/mywork` — upload a draft → extract YOUR claims
    (HUMAN_CORPUS, distinct provenance) → cross-check each vs the literature (support/contradiction with
    quotes+DOIs). UI ⊹ check my work.
  · Directed mode: `/goal` — hand it a problem → high-priority read + real investigation → cited
    deliverable, without rewriting the self. UI ◱ give a goal.
- **P6 — anti-degradation: the drift guard ACTS.** `deliberate.py` clamps a wholesale interest
  replacement (drift > 0.7 = spiral): keeps focus, admits ≤2 new interests; healthy growth applies
  normally. Plus re-ground-every-cycle + enforce_caps.
- **P7 — scientific tools.** `tools/science.py`: typed clients (Open Targets, UniProt, NCBI/GEO,
  PubChem, ClinicalTrials) via the rate-limited/cached IngestService (fetch OUTSIDE sandbox; `--network
  none` preserved), fast-fail (retries=1, 12s). Wired into the analyst as a `science_query` tool +
  `/science` endpoint. Verified live: UniProt APOE→P02649, Open Targets Alzheimer→APP/PSEN1, GEO IDs.

## Validation evidence (real, not mocked)
Control: pause flatlined spend live. Files: 760-node tree, PDF/code/CSV viewers, path-jail blocks `../`.
Chat: honest reply + persisted directive + 3 focus topics. Graph: 70-node ranked seed → expand to 109
(entity/source/note), scrubber grows 16→68 edges over time. Builders: real 486KB diagram PNG + 33KB
interactive page grounded in beliefs; experiment nodes graph-reachable; free_move chose `investigate`
with sound rationale. Digest: 52 clickable citations over 45 claims/27 papers. Ask: APOE→AD answered
[2][3] from real claims. Cross-check: APOE→AD claim correctly SUPPORTED from literature. Drift guard:
spiral (drift 1.0) clamped, adjacent growth (0.4) applied. Science: 3 DBs returned real data. Full-UI
integration smoke: all 11 header controls + chat + cost bar coexist, no console errors.

## Honest gaps / next
- **Formal gating experiments not yet run** (E-STEER/E-FREEMOVE/E-ARTBAR/E-CONTRIBUTION/E-DIGEST/
  E-DRIFT/E-LONGRUN/E-TOOLS): each mechanism is verified *functionally*, not yet at ≥20 seeds → the
  unsupervised free-move cadence stays OFF until E-DRIFT/E-LONGRUN pass (CLAUDE.md §2).
- **Cross-check recall** is bounded by exact canonical-pair matching (near-synonyms miss) — the target
  of E-CONTRIBUTION; improve via better entity canonicalization.
- **Topic digest is slow (~20–40s)** (Sonnet, 45 claims) — shows a loading state; could stream.
- **pubchem/clinicaltrials** are network-blocked in this env (503/403) — fail gracefully.
- **Deferred (plan P5/P8):** VoI next-experiment ranking, proactive for-you feed, co-authoring
  comment→revise loop, full Swarm Control Room viz, side-by-side compare. The live stream already shows
  the swarm working; the file browser + graph already surface everything built.
- **Frontend is still the single served `index.html`** (grew with each surface) — the Vite/React
  migration in the plan was deferred to keep the repo runnable at every step; it's the clean next
  structural move if the UI grows further.

## Gotchas (carried)
- Shared `.cache/http/cache.db` across processes: fine, but don't run two heavy servers on it at once.
- FalkorDB in Docker (`persona-falkordb`:6379); sandbox image `persona-sandbox` (sci stack + texlive).
- Never commit `.env`. Windows: utf-8 stdout reconfigure in scripts.
- Toggling a persona's run-state writes shared `control.json` — restore RUNNING after any halt-for-test.
