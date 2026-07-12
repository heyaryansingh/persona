# Persona — the persistent AI scientist (ClaudeScience)

> **Claude Science is a workbench you drive. Persona is an AI scientist that never sleeps.**

Claude Science breaks a request into subtasks, delegates to specialized sub-agents, reviews the
output, and emits figures + manuscripts + code — **per session, when you drive it.** Persona has the
same multi-agent DNA, but is the thing a workbench can't be: **persistent and self-directed.** It
commits to a few fields, reads deep, runs teams of agents on many open questions at once (organized by
a Director), **proves what it can and records what it has verified**, **re-tests its own past work**,
and hands you contradictions, questions, and Nature-quality documents.

## What's genuinely different (no other researcher tool combines these)

1. **A persistent self + belief-state that compounds over time** — not a session; a colleague.
2. **Autonomous agenda** — it decides what to investigate; a Director assigns non-overlapping problems.
3. **Honest epistemics** — exact-span citation gate, ≥2-independent-lab membrane, self-critique, and
   an explicit "I cannot prove this from the present evidence" instead of a bluff.
4. **The verified, self-correcting loop (headline)** — a result becomes a `TESTED` belief ONLY when a
   check actually passed (sympy in a sandbox, or a Lean 4 proof via Harmonic Aristotle), and a
   **revisit** loop re-tests past results against new evidence: *still-verified / weakened / refuted*.
5. **Documents as the language** — every act is a real file: `question.md`, `plan.md`,
   `report.pdf`, `derivation.pdf`, `critique.md`, `verified.md`, organized in a working directory.
6. **Multi-team orchestration** — many teams on distinct problems, visibly, at once.

## The 90-second demo

1. **Research Floor** (`Floor` tab) — three domains (math / biology / physics) each running teams.
   Watch pipeline lanes: agents flow gather → harvest → synthesize → analyze → **prove** → write →
   critique → finalize, the running stage pulsing, the Director assigning non-overlapping problems,
   and `✓ N verified` ticking up live.
2. **Studio** (`Studio` tab) — the collaboration surface. Left: the mind's **signals** (verified
   ledger, contradictions, open questions). Center: ask it to **verify a claim** → a team proves it →
   a `TESTED` belief lands in Signals. Right: **deliverables** it made, one click to open.
3. **Knowledge** (`Map → Knowledge`) — the depth ladder: **L1** topics known → **L2** summaries →
   **L3** in-depth dossiers → **L4** the sources it stands on. Click a topic to drill down.
4. **A document** (`Work → Brain`, open any `report.pdf`) — a Nature-format paper: structured
   abstract, significance statement, methods, results with captioned figures, a `Main result` block
   tagging each claim `[PROVED HERE] / [VERIFIED NUMERICALLY] / [CITED] / [OPEN]`, a reasoning chain,
   and references that resolve to DOIs.
5. **The ledger** (`self/verified.md` or `GET /verified`) — what it has proven, by what method, and
   what the revisit loop re-confirmed or refuted.

## Built on evidence, not vibes

Every load-bearing mechanism has a preregistered experiment in `results/FINDINGS.md` (RQ-E01…E15):
the exact-span gate (0% ungrounded), the ≥2-lab membrane, swarm saturation (~14 effective), the
relevance + field gates (0.94 balanced acc, drops 100% off-field), poisoning resistance. New claims
are gated behind a metric before they ship.

## Integrations
- **Claude** (Opus/Sonnet/Haiku) across the agent tiers; the same coordinator→specialists→reviewer
  pattern Claude Science uses.
- **Harmonic Aristotle** (Lean 4 formal proofs) — `PERSONA_ARISTOTLE_KEY`; degrades to sympy safely.
- Scientific corpus: OpenAlex · Crossref · Europe PMC · arXiv (field-gated per specialization).
- Offline sandbox (Docker, network-denied): numpy/pandas/scipy/sklearn/statsmodels + **sympy/mpmath**
  for machine-checked math; deterministic LaTeX → PDF.

## Run it
```
python -m persona --port 8137     # open http://localhost:8137
```
Seed a mind with 2–4 interests; it does the rest. Per-persona `cap_usd` bounds spend.
