# Persona v2 — Vision, Critical Audit & Deep Roadmap
*Living document. Backed by an 8-domain critical tech sweep (`planning/TECH_RESEARCH_V2.json`, 8 scouts, 1.2M tokens) + the v1 build. Not yet implemented — this is the plan for review.*

---

## 0. TL;DR (read this first)

**What v1 actually is:** a clean, tested *skeleton* with the right architecture and 4 validated safety gates — but **zero real intelligence**. Every "smart" step (extraction, contradiction typing, reanalysis) is a keyword heuristic or a mock. `grep` confirms: **no LLM, no embeddings, no ML anywhere.** The demo is one cached 8-paper query.

**What v2 should be:** an always-on researcher that reads **thousands of abstracts/day** with real Claude extraction, maintains a **bi-temporal idea-evolution + contradiction graph** over a whole subfield, retrieves against **millions of abstracts** (MedCPT/FAISS), runs a **live swarm control-room** you can watch, closes the **contradiction→hypothesis→dataset→real-reanalysis→human-anchor** loop, and manages you as a collaborator.

**The critical finding on your framework wishlist:** the evidence says **most of it does not earn its place.** LangGraph/LangChain/CrewAI/AutoGen, Chroma, and day-one fine-tuning are the wrong tools for *this* shape of problem. The ambition (hundreds of agents, RAG at scale, sophisticated graph) is right; the tools that deliver it are leaner. Details in §3 — this is the most important section.

---

## 1. Critical audit of v1 (be harsh)

| Area | Claim | Reality |
|---|---|---|
| **Extraction** | "swarm reads the literature" | Keyword/stem matching over abstract sentences. Beliefs are sentence *fragments*, not claims. **No LLM.** |
| **Contradiction** | "typed contradictions" | Heuristic on journal-count (`sup_groups`/`ref_groups`). No NLI, no BioDivergence. |
| **Self-test loop** | "closes the loop" | Real GEO lookup, but the reanalysis is a `HeuristicTester` returning a canned "supports". **Mock.** |
| **Dependency graph (3.2)** | "what the field rests on" | Empty in the demo — the heuristic emits no `derives-from` edges. The flagship differentiator has **no data**. |
| **Membrane/anchor validation** | 4 gates GO | All on a **boolean/group-count simulation.** E8 (real-Claude) unrun. |
| **Scale** | "hundreds of agents" | The inner loop is a **synchronous for-loop.** Demo = 8 papers, one query. |
| **Convergence** | "evidential independence" | Proxied by *distinct journal* — doesn't model citation coupling/co-authorship. |
| **Retrieval** | — | **None.** No embeddings, no vector store, no semantic search. Can't "analyze vast literature." |
| **Graph** | "idea evolution/contradiction network" | A SQLite table + a Cytoscape screen that renders whatever's there (usually little). No temporal evolution view. |
| **Reproducibility** | — | **No dependency manifest** (deps ambient). Not installable clean. |
| **UI** | 8 screens | Real + verified live, but not responsive, no error boundaries (one object-render crash last session), 730 KB bundle. |
| **Experiments** | 12 pre-registered | **Only 4 run** (E9/E10/E13/E14). 7 need a key/data/annotations (now unblocked by the key). |

**Verdict:** v1 is a *correct, honest scaffold with a validated safety core* — the hard architectural bets (self/swarm split, anchor write-policy, human-gated ignition) are made and tested. But it does not yet *read, reason, retrieve, or scale*. v2 is where it becomes a researcher. **Good news from the audit:** `anthropic`, `transformers`, `sentence_transformers` are already installed; both API keys are wired.

---

## 2. Vision & target functionalities

**Persona is a persistent colleague that reads a field faster than any human, holds a living map of what it believes and why, acts on the highest-leverage tension, and pulls you in exactly when your judgment is the bottleneck.**

Concrete capabilities (the bar for "done"):

1. **Read at scale.** Given a topic, ingest and extract from **thousands of real abstracts/day** (Claude Haiku via Batch API), continuously, always-on.
2. **Real semantic beliefs.** Structured claims `(entity, relation, object, direction, population, effect, power)` with real provenance and calibrated confidence — not fragments.
3. **Retrieve against everything.** Hybrid semantic + lexical retrieval over **millions** of abstracts (MedCPT + FAISS + Europe PMC BM25) so it can pull the relevant 200 papers on any question.
4. **A sophisticated idea graph.** A **bi-temporal** knowledge graph of claims + typed edges (support/contradict/**derives-from**/presupposes) showing **evolution, spawn, contradiction, and collapse over time** — the "what does this field rest on, and where is it heading" instrument, rendered as a real interactive network (10k+ nodes).
5. **A live swarm you can watch.** Hundreds of parallel readers spawning/returning, the membrane admitting/rejecting, beliefs updating — a **control room**, the legibility money-shot.
6. **The closed acting loop, for real.** Contradiction → falsifiable hypothesis → located public dataset → **real Claude-Science first-pass reanalysis** → human-gated write-back.
7. **Runs its own experiments.** Not just the literature loop — Persona proposes, runs, and logs sandboxed computational tests (the `/experiments` discipline, automated).
8. **Manages you.** Assembles dossiers, escalates on calibrated uncertainty × stakes, anchors your answers as durable shared nodes, pings you when the front moves.
9. **Observable & reproducible.** Per-agent traces, token/cost tracking, a durable run history; one-command install.

---

## 3. The critical tech verdict (honest pushback on the wishlist)

You named LangGraph, LangChain, CrewAI, RAG, LLM, HuggingFace, fine-tuning. The 8-domain sweep — told to be adversarial and to respect Persona's own *single-agent-reasoning wins* (DPI/E12) finding — returns a clear, mostly-**contrarian** verdict. **I recommend following the evidence, not the buzzword list.**

### ADOPT (these earn their place)
| Tool | Role | Why |
|---|---|---|
| **Raw Anthropic SDK** (Structured Outputs + tool use) | the swarm reader/extractor | Constrained decoding = schema guarantee frameworks bolt on with retries; fully auditable (legibility mandate). |
| **Message Batches API** (50% off, 100k/batch) | bulk background reading | ~10k abstracts/day on Haiku ≈ **$11–15/day**; separate rate-limit pool so bulk doesn't starve the live loop. |
| **Prompt caching** (0.1× input) | every call | Stacks with Batch → ~$0.05/MTok cached input. Single biggest cost lever. |
| **AsyncAnthropic + `[aiohttp]` + `asyncio.Semaphore`** | live-tier fan-out | ~300 LoC orchestrator (token-bucket, AIMD backpressure, circuit breaker, priority lane). This *is* the "hundreds of agents." |
| **MedCPT** (+ NCBI's **precomputed 37M PubMed embeddings**) | biomedical retrieval | Download the embeddings — **never pay to embed the corpus.** SPECTER2 for paper→paper (feeds the dependency graph). |
| **FAISS** + **LanceDB** | vector index | In-process, no server. FAISS for topic-scoped working set; LanceDB for durable larger stores. |
| **BM25 via Europe PMC + RRF fusion + bge-reranker-v2-m3** | hybrid retrieval | Reuse Europe PMC as the lexical side; fuse; rerank locally (open cross-encoder). |
| **NetworkX (in-memory) + DuckDB (durable, VSS)** | idea-graph substrate | Implement Graphiti's **bi-temporal schema yourself (~100 lines)** — no graph server. |
| **Sigma.js + graphology + cosmos.gl (WebGL)** | large-graph viz | 10k–100k+ nodes with evolution over time. (Cytoscape stays for small graphs.) |
| **OpenTelemetry GenAI / OpenInference → Arize Phoenix (self-host)** | observability | Instrument once; fan to the live UI + a durable trace backend. |

### SKIP (do NOT adopt — they lose on evidence)
- **CrewAI, LangChain agents, AutoGen/AG2, LlamaIndex agents** — role/handoff/debate orchestration is exactly the *multi-agent reasoning* Persona's DPI/E12 finding says loses to one strong agent; token bloat (CrewAI ~3×, multi-agent ~15×), version churn, hidden prompts break auditability. MAST documents 14 failure modes.
- **Chroma, Milvus** — Chroma underperforms; Milvus is server ops you don't need.
- **Microsoft GraphRAG (full)** — per-episode LLM extraction duplicates the membrane and adds recurring cost.
- **Neo4j, KuzuDB (abandoned Oct 2025), Temporal, Ray, Prefect/Dagster** — server/cluster ops that duplicate durability the SQLite/DuckDB store already owns.
- **Fine-tuning (QLoRA / distillation / GLiNER) — NOT day one.** Few-shot Claude + caching is ~$0.001–0.003/abstract with zero training infra and is prompt-fixable. Fine-tune *only* if a measured cost/latency wall appears (then distill Claude → a small student). This directly answers your "fine tuning" ask: **prove the need first.**

### CONDITIONAL (scoped escape hatches)
- **LangGraph functional API** — *only* around the single inner reasoning loop *if* the UI needs interrupt/resume/time-travel you'd otherwise hand-build. Never route the fan-out through it (documented WAL bloat at ~100 concurrent). Likely **not needed** (we have HITL + notebook already).
- **Claude Agent SDK** — for the *outer* acting loop (real agency/tool loops), not the read swarm.
- **PaperQA2 (Apache-2.0)** — the one framework worth considering: as a citation-traversal RAG *evidence primitive*. Evaluate vs our own retrieval in an experiment.
- **DBOS Transact** — documented escape hatch if process-crash durability ever needs finer granularity than SQLite gives.

**The through-line:** the ambition is right; the winning stack is **Anthropic-native + a lean async orchestrator + embedded RAG + an embedded bi-temporal graph + WebGL viz + OTel**. Every heavyweight framework was evaluated and most lose to ~100–300 lines of purpose-built code that stays auditable. This *is* CLAUDE.md §3 (tools earn their place by winning a test) — and every adoption above has a pre-registered discriminating experiment (§6).

---

## 4. Architecture v2

```
                         ┌─────────────────────────── THE SELF (small, durable, single-agent) ───────────────────────────┐
                         │  identity/agenda/taste · belief-graph (bi-temporal, NetworkX+DuckDB) · notebook · errors        │
                         │  reasoning = ONE strong agent (Sonnet 5 → Opus 4.8), belief-state prefix cached                 │
                         └───────▲───────────────────────────────────▲───────────────────────────────▲───────────────────┘
        harvest-then-commit      │ membrane (independence+calibration+conformal, typed contradiction)  │ human-gated ignition
                         ┌───────┴───────┐                   ┌───────┴────────┐                ┌───────┴────────┐
   THROUGHPUT TIER  ────►│  READ SWARM   │   LIVE TIER  ────►│ RETRIEVAL (RAG)│                │  HUMAN LOOP     │
   Batch API (50% off)   │ Haiku 4.5 ×N  │  AsyncAnthropic   │ MedCPT+FAISS+  │                │ dossier→anchor  │
   ~10k abstracts/day    │ structured    │  Semaphore(N)     │ BM25+RRF+rerank│                │ Phoenix traces  │
   idempotent ledger     │ outputs+cache │  token-bucket     │ over millions  │                │ escalate=U×stakes│
                         └───────────────┘  AIMD backpressure └────────────────┘                └─────────────────┘
```

**New/changed modules (on top of v1's store/self/membrane/loops/engine):**
- `swarm/orchestrator.py` — async bounded fan-out (Semaphore, token-bucket from `anthropic-ratelimit-*` headers, AIMD, circuit breaker, priority lane), + a SQLite **read-ledger** (doc_id→done) written in the same txn as the commit → crash-resume for free.
- `swarm/claude_reader.py` — real extractor: Haiku structured outputs, cached ≥4096-token few-shot prefix; hard abstracts escalate to Sonnet. Batch backend for background, live backend for the loop. (Plugs behind v1's existing `Extractor` Protocol — the seam already exists.)
- `retrieval/` — MedCPT query/article encoders, FAISS index, Europe PMC BM25, RRF fusion, bge-reranker. Download NCBI precomputed embeddings.
- `graph/bitemporal.py` — every edge carries `(t_valid, t_invalid)`; supersession invalidates, never deletes → the evolution/collapse timeline. NetworkX live + DuckDB durable. (v1's store already bi-temporal at the row level; this generalizes it to a first-class temporal graph.)
- `engine/*` — rewire trajectory/dependency/silence/experiment-value onto the real graph + real edges (now that extraction produces `derives-from`).
- `loops/self_test.py` — swap `HeuristicTester` → `ClaudeScienceTester` (real reanalysis) behind the existing Protocol.
- `obs/` — OpenInference instrumentation → in-process SpanProcessor (→ UI SSE) + Phoenix.
- `config.py` — load `.env` (python-dotenv), model tiers, budgets. **+ a `pyproject.toml`** (fix the reproducibility gap).

**Kept exactly as-is (validated):** the self/swarm split, the anchor write-policy, the adaptive membrane (E10/E14 GO), taste (E13), the escape hatch (E9), human-gated ignition. v2 makes them *real*, doesn't replace them.

---

## 5. Design — the interfaces (Claude Design + ui-ux-pro-max)

Aesthetic held from §6: calm editorial lab-journal × live systems console, dark-first, mono voice + serif synthesis, two accents (live / needs-human), honest-uncertainty everywhere, motion only on real state change. New/upgraded screens:

- **Swarm Control Room** (the money-shot) — hundreds of agent dots in flight, spawning → reading → returning; the membrane as a literal funnel admitting/rejecting; live token/cost meter; backpressure/strict-mode indicator. Built in-house (no off-the-shelf trace tool gives the "mind at work" view). Virtualized/WebGL for hundreds of nodes; motion only on real spawn/return/admit events.
- **Idea-Evolution Graph** — the big one. Sigma.js/cosmos.gl WebGL network of the whole subfield: nodes = claims (sized by load-bearing, colored by provenance), edges = typed relations; a **time scrubber** replays belief evolution, spawn, contradiction firing, and collapse; click a node → fragility cascade preview. Handles 10k+ nodes (aggregate/sample + drill-down per the data-density rules).
- **Living Notebook, Argument-State, Experiment Queue, Handoff Inbox, Artifacts** — upgraded from v1 with real data + honest-uncertainty (conformal intervals), typed-contradiction badges, candidate-edge dashing.
- **Data-viz discipline (from ui-ux-pro-max):** tabular figures for all numeric columns, legends+tooltips, aggregate at 1000+ points with drill-down, color never the sole signal, reduced-motion respected, WCAG contrast in dark mode.
- Actual mockups produced with **Claude Design** (mcp `plan` visual-plan / Artifact) at the start of the UI phase — deferred to execution.

---

## 6. Phased roadmap (dependency-ordered, experiment-gated, demoable each step)

Every phase: build → **run its gating experiment (≥20 seeds / real eval)** → validate → commit. Reuses v1's pre-registered stubs; adds the discriminating experiments the sweep named.

| Phase | Build | Gating experiment (run first/alongside) | Acceptance |
|---|---|---|---|
| **P0 Foundations** | `pyproject.toml` + `.env` loader + `config.py` (model tiers, budgets); OTel/Phoenix wiring | — | clean install; a traced Claude call shows in Phoenix + the UI |
| **P1 Real extraction** | `claude_reader.py` (Haiku structured outputs, cached prefix, Batch+live) behind the `Extractor` Protocol | **E6-real / E12** — extraction F1 vs a ~100-abstract gold set; raw-SDK vs (optional) framework arm; single-vs-swarm at matched tokens | F1 clears bar; raw-SDK Pareto-wins the F1/token frontier (else adopt the winner + write the reversal) |
| **P2 Scale swarm** | `orchestrator.py` (async fan-out, token-bucket, AIMD, read-ledger) — replaces the synchronous inner loop | **Crash-resume bake-off** — kill-9 mid-tick × 20 seeds: zero double-commits, zero lost docs; 200 parallel reads wall-clock | idempotent resume (byte-identical beliefs vs uninterrupted); reads ~1k abstracts live |
| **P3 Real membrane** | swap the sim guard for real extraction through the membrane | **E8** — real-Claude poisoning replay (+ MINJA injection); crossover survives | anchored ≥ quorum ≥ naive on real extraction; else reopen the design |
| **P4 Retrieval** | `retrieval/` (MedCPT + FAISS + BM25 + RRF + rerank); download NCBI embeddings | **Retrieval eval** — nDCG/recall@k vs BM25-only on a labeled biomedical set; PaperQA2 arm | hybrid beats lexical by pre-registered margin; "pull the 200 relevant papers" works |
| **P5 Idea graph** | `graph/bitemporal.py` + real `derives-from` edges + engine rewire | **E6 rank-corr / IAA** + **E5** trajectory backtest (real outcomes) | load-bearing rank correlates with expert (or documented HITL downgrade); trajectory beats strong static baseline or renders descriptive |
| **P6 Real loop** | `ClaudeScienceTester` (real first-pass reanalysis) | **E15** contradiction-trigger precision (ContraDetect/BioDivergence oracles) | one real contradiction → hypothesis → dataset → real reanalysis → human-anchor, live |
| **P7 Calibration** | conformal gate + decision-theoretic escalation | **E11** — estimator selection (LM-Polygraph) + conformal error rate on biomedical QA | membrane/escalation hit target error rate; 5.3 promoted to `[E]` |
| **P8 Legibility v2** | Swarm Control Room + Idea-Evolution Graph (Sigma/cosmos.gl) + upgraded screens; Claude Design mockups first | usability pass (ui-ux-pro-max checklist; responsive; a11y) | watch hundreds of agents + scrub the idea graph over time, live |
| **P9 Autonomy + self-experiments** | always-on scheduler; Persona proposes+runs sandboxed experiments; 2nd researcher at real scale | — | overnight run reads 10k+ abstracts, fills the notebook, spawns interests, runs ≥1 self-experiment |

**Budget note:** P1–P3 at ~10k abstracts/day ≈ $11–15/day on Haiku+Batch+cache. A focused subfield backfill (say 200k abstracts once) ≈ a few hundred dollars of Batch, or free if using NCBI's precomputed embeddings for retrieval and reading only the top-k. You set the cap in `config.py`.

---

## 7. Risks / threats (carried)
- **Idempotency is the whole ballgame** for crash-resume: the read-ledger must commit in the same SQLite txn as the belief. Self-check: killed-and-resumed run = byte-identical beliefs.
- **Batch API has a ≤24h SLA** — right for background reading, wrong for the live demo. Two tiers, always.
- **E6 dependency extraction likely misses per-edge precision** — plan for the HITL downgrade (judge on rank-correlation).
- **Everything still rests on the sim until E8** runs on real extraction.
- **Anthropic lock-in** — keep the extraction prompt+schema portable (a provider swap = a wrapper change).
- **Scope:** this is weeks of work. It must stay demoable at every phase (P0…P9 each ship something).

---

## 8. Decisions — LOCKED with the user
1. **Budget: ~$15/day** (thousands of abstracts/day). Full-scale ambition. Cap enforced in `config.py`.
2. **First money-shot: the Live Swarm Control Room.** → resequence: P0 → P1 (real extraction) → P2 (scale swarm) → **bring the Swarm Control Room forward (from P8) as the first big visual**, then continue P3+.
3. **Corpus: self-directed / any source.** Seed interests but follow curiosity from the start → the ingestion layer must be genuinely source-agnostic (web/dataset/repo adapters beyond the biomedical APIs) and the outer loop must generate its own queries/sources. Bigger P1/P4 scope; ground-truth on the Alzheimer's seed for the demo, but don't fence it.
4. **LangGraph: decide by the P2 bake-off.** Build both arms (asyncio-ledger vs LangGraph functional API) in the crash-resume experiment; the numbers pick the winner. Default expectation: asyncio wins.

**Immediate execution order:** P0 (pyproject + `.env` loader + `config.py` + a REAL Claude extraction smoke test — prove the key + structured-output extraction works on a real abstract) → P1 (Claude reader behind the `Extractor` Protocol) → P2 (async swarm + bake-off) → **Swarm Control Room** → P3 real membrane (E8) → …
