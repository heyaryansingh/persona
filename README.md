# Persona

A persistent, always-on synthetic researcher for the scientific literature. It maintains a durable
self and uses a disposable swarm of bounded agents to read at scale, closing an agentic loop from a
flagged contradiction to a falsifiable hypothesis, a located public dataset, a first-pass reanalysis,
and a written-back, provenance-typed belief — escalating to a human exactly when it needs experimental
judgment.

Demo: https://aryansingh.org/persona

## The problem

Science publishes millions of papers a year, but the tools we read it with are amnesiac. A chatbot
returns fluent prose with citations that may be fabricated and are forgotten the moment the session
closes. A search tool retrieves, but it holds no beliefs, never notices when two papers contradict,
never re-checks itself when new evidence lands, and never acts. The bottleneck in research is not
generating text. It is a trustworthy memory that reads at scale, believes with discipline, and
compounds over time.

## What Persona is

Persona separates a small, durable **self** — interests, a provenance-typed belief-state, memory,
taste — from a large, disposable **swarm** of bounded agents that read at scale and are then discarded.
The principle is *scale of reading, discipline of believing*. Every belief carries a provenance type
(`READ`, `INFERRED`, `HUMAN_CONFIRMED`, `TESTED`), so an inferred claim never wears the authority of a
proven one. The product is deliberately not a chat or search dashboard: it exposes the evidence, code,
outputs, uncertainty, and corrections behind every conclusion.

Core loop:

`candidate conflict -> exact evidence -> falsifiable question -> executable test -> replayable artifact -> human review or bounded belief update`

## How it works

1. A swarm of reader agents pulls papers from Europe PMC and OpenAlex and extracts structured claims,
   each tied to an exact source span.
2. A write-membrane admits claims by provenance and cross-source agreement; non-verbatim or unsupported
   evidence is rejected before it can enter an active claim.
3. A temporal knowledge graph tracks papers, claims, and contradictions over publication time.
4. The reflecting self reweights interests, forms its own questions, and stakes falsifiable hypotheses.
5. An analyst fetches public datasets and runs real code in an isolated sandbox.
6. Results are machine-checked with sympy or formally proven in Lean 4 (via Harmonic Aristotle), then
   written back into the belief-state.
7. It re-audits its own past conclusions as the literature moves, and escalates to a human exactly when
   a question needs wet-lab or experimental judgment.

## Features

- **Grounded, exportable reports.** Every claim resolves to a real paper, year, and DOI. Select any
  region of the graph or upload your own paper and get a cited report that exports to PDF, with no
  hallucinated references.
- **Robustness auditor.** Runs statistical forensics in code, never in a model (statcheck, GRIM,
  GRIMMER, minimum-detectable-effect, p-curve), and produces a replication likelihood calibrated on
  real replication outcomes (Open Science Collaboration 2015, Gordon 2021), so the number means what it
  says. Adversarial refuters stress-test the soft judgments; a living watchlist re-audits papers as new
  evidence arrives. Works on external papers and on the mind's own outputs.
- **Verified reasoning.** Derivations are machine-checked (sympy) or formally proven (Lean 4); results
  are provenance-typed and self-critiqued, and re-tested over time rather than frozen.
- **Self-correcting memory.** A revisit loop re-tests past conclusions against evidence gathered since,
  marking each still-verified, weakened, or refuted.
- **Transparent workbench.** Watch the director, teams, and agents work in real time; open the code
  editor and run their Python (torch, numpy, scipy, sympy preinstalled); clone a repository or upload a
  folder and run an analysis pipeline in the sandbox without touching a terminal.

## What it does — a representative run

On a fresh run seeded with *GLP-1 receptor agonists in neurodegeneration*, in roughly ten minutes
Persona read more than twenty primary papers, synthesized ten cited notes, opened three parallel
investigations, machine-checked three derivations of the direct-versus-indirect neuroprotection
mechanism, and wrote four cited, compiled papers. In the process it flagged an internal inconsistency
in one source regarding semaglutide and stroke direction and resolved it by deferring to the verbatim
quote. This is a careful, auditable synthesis with its uncertainty labeled — not a claim of discovery.

## Verified findings and honest limits

Design decisions are backed by seeded, sandboxed experiments (`results/FINDINGS.md`), reported with
their limits:

- **Identity anchoring.** Under correlated literature poisoning, human-anchored protection retained
  100% of human-verified beliefs versus 71% for naive continuous updating. Under benign, independent
  noise the protection buys nothing — an honest reversal we kept and diagnosed.
- **Replication calibration.** A curve fitted on real labeled replication outcomes beats a flat field
  base rate on a proper scoring rule (Brier 0.218 vs 0.245) with real resolution (0.032 vs 0.000), so a
  strong paper and a marginal one receive different, calibrated numbers.
- **Retrieval.** Dense and hybrid retrieval did not clear their deployment gate; simple retrieval
  remains the production path.
- **Transcriptomic reanalysis.** The GEO result is same-donor, sensitive to a single gene, and not
  causal; it is marked `contested`/`inconclusive` and must not be called a biological discovery.

Persona cannot do wet-lab work. The human-as-resolver division of labor is a design feature: real
experimental judgment is routed to humans, and their answers are anchored into the belief-state.

## Safety boundary

Candidate sign collisions are not verified contradictions. A result can be computationally replayable
and still be scientifically contested. Persona keeps those states separate, preserves rejected and
invalidated work for audit, and routes biological or methodological judgment to humans.

## Setup

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Add your API keys. Create a file named `.env` in the repository root:

   ```
   ANTHROPIC_API_KEY=sk-ant-...        # required — powers the agents (console.anthropic.com)
   ARISTOTLE_API_KEY=...               # optional — Lean 4 formal proofs (Harmonic Aristotle)
   NCBI_API_KEY=...                    # optional — faster PubMed/Europe PMC access
   CONTACT_EMAIL=you@example.com       # optional — polite User-Agent for the literature APIs
   ```

   `ANTHROPIC_API_KEY` is the only key required to run. The `.env` file is loaded automatically at
   startup; it is git-ignored, so your keys never leave your machine.

3. Optional services for full capability (Docker):

   ```
   docker run -d -p 6379:6379 falkordb/falkordb                      # the belief knowledge graph
   docker build -t persona-sandbox -f docker/sandbox.Dockerfile .    # runs agent code + compiles PDFs
   ```

   The app starts and reads without these; without FalkorDB the graph shows as offline, and without the
   `persona-sandbox` image, in-sandbox code execution and paper compilation are disabled.

## Run

```
python -m persona --port 8137
```

Then open http://127.0.0.1:8137, create a persona, and seed it with a few interests.

The capped default is three workers. For an uncapped bring-your-own-key run set
`PERSONA_UNLIMITED_SPEND=1` (eight workers unless `PERSONA_WORKERS` is set); an explicit
`PERSONA_DAILY_BUDGET_USD` always keeps the run capped.

## Test

```
python -m pytest -q
python -m compileall -q persona experiments
```

The test suite runs offline and makes no paid model calls.

## How Claude was used

Built end-to-end with **Claude Code**, including the sandboxed experiments behind each design decision.
The **Claude model family** is the runtime engine — a heterogeneous fleet routed by task: Opus for the
reflecting self (planning, judgment, adjudication), Sonnet for the reader, analyst, and writer swarm,
and Haiku for cheap scouting. Claude's structured tool use and long context let a bounded agent read a
full paper and return auditable, span-linked evidence rather than vibes. The governing pattern is
model-reasons, code-verifies: Claude reads and reasons; the arithmetic is run in code and checked.

## Further reading

- `Initial Planning Docs/BUILD_PLAN.md` — architecture, the intellectual engine, and the sequenced build.
- `results/FINDINGS.md` — the experiments behind each design choice.
- `docs/HACKATHON_DEMO.md` — the three-minute cached demo script.
