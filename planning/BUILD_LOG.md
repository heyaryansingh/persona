# Build Log — Persona
*A running, honest record of the build: what was made, what was tested, every bug/pivot/decision. Living document (CLAUDE.md §6).*

## Method
Planner/judge in the main session; bounded implementation, scouting, and research pushed
to agents (token-smart orchestration). Every increment: **real test → run it → commit**.
Unproven sub-choice → sandbox experiment (≥20 seeds, mean ± 95% CI) **before** building.
Frequent commits (11 so far on `build/persona-mvp`).

## Phase 0 — research, verify, plan
- Read all planning docs; **statically found Confound A** before running anything.
- 6-domain adversarial literature sweep (6 Opus scouts, 104 searches) — materially
  reshaped the plan (human-gated ignition; typed contradiction; convergence = independence;
  5.3 → hypothesis; single-agent reasoning; E5 independence-led; E7 vs genetic prior).
- Reproduced all 3 memory experiments (bit-identical; crossover to the digit).

## Build phases (each committed, each tested)
- **Step 1** belief-store (bi-temporal, provenance, anchor write-policy) + living-doc self
  (two-tier hydrate, durable rehydrate) + live Europe PMC ingestion. 9 tests, incl. a
  store-level replay of the poisoning crossover.
- **Step 2** reader/extractor swarm + adaptive membrane (independence convergence, E10
  poisoning switch, typed contradictions, backpressure) + inner loop. Verified live: real
  papers → notebook → beliefs → flagged contradictions.
- **Step 3** engine trio (trajectory / dependency+PageRank / experiment-value) — 3 parallel
  agents, verified by main.
- **Outer loop** taste (VoI + surprise + tractability − cost) + agenda + interest spawning.
- **Loops** delegation (dossier → human → anchor), artifacts (mini-review + error log),
  self-test (contradiction → hypothesis → live GEO dataset → replay reanalysis → human-gated write-back).
- **Facade + API** Researcher + FastAPI/SSE; 8 React screens (8 parallel agents) — verified
  live in a browser incl. the closed loop (self-test → resolve → anchored).
- **Step 7–9** always-on run (self-spawned interest visible); stretch engine (silence,
  cross-field, honest lexical baselines); a lab of two dispositions (disagreement = signal).

## Experiment gates
| Gate | Status | Result |
|---|---|---|
| Reproduction (gate-0) | PASS | crossover to the digit; Confound A quantified |
| E10 adaptive switch | GO | detect 1.00 / false-strict 0.00 / retention 1.00 |
| E14 independence gate | GO | independent 1.00 / echo 0.00 vs naive-count 1.00 |
| E13 taste functional | GO | top-1 change 0.80; control identical |
| E9 escape hatch | GO | wrong-anchor re-escalate 1.00 / poison 0.00 / retention 1.00 |
| E5 E6 E7 E8 E11 E12 E15 | pending | need real data / annotations / an API key; pre-registered stubs |

## Bugs found & fixed (root cause each)
1. **Confound A (finding, not a code bug):** the "88% vs 68% all-poisoned recovery" is an
   artifact — 75% of "victims" are human-anchored. Honest result = human-belief retention
   (100% vs 76%); the membrane does most of the general work, anchoring guarantees the
   human-confirmed core. Claim refined in `results/FINDINGS.md`.
2. **Heuristic extractor missed "promote":** exact-word cue list didn't match verb
   inflections → only one journal produced a candidate → no convergence. Fix: stem-based
   cues (`promot`, `increas`, …).
3. **Windows SQLite tempdir lock:** an assertion failing before `close()` left the
   connection open → tempdir cleanup crashed. Fix: `try/finally: me.close()` in tests.
4. **SQLite cross-thread error in FastAPI:** sync endpoints run across threadpool workers;
   the connection is thread-bound. Fix: `check_same_thread=False` (SQLite serializes; a
   per-store lock is the upgrade path — noted in code).
5. **React "objects are not valid as a child":** HandoffInbox rendered the self-test
   `dataset` object directly. Fix: render `dataset.accession (source)`. Caught by driving
   the live UI + reading console errors.
6. **Vite ignored the preview PORT env:** autoPort set `PORT` but Vite doesn't read it →
   connection refused. Fix: `server.port = process.env.PORT` in vite.config.
7. **Disposition→strictness regression:** "skeptical-exploratory" matched "skeptic" →
   quorum 3 → the demo committed 0 beliefs (empty UI). Fix: only a *pure* skeptic gets the
   strict quorum; balanced/exploratory commit normally. The lab keeps its contrast.

## Pivots & decisions
- **Anchoring reframed** as a provenance-typed *write-policy* + re-escalation, not a bespoke
  mechanism (per literature; MINJA/PoisonedRAG make the threat current).
- **Reasoning stays single-agent** (Data-Processing-Inequality); fan-out is reading only.
- **Ignition is human-gated** — the self-test loop still closes, but a human sign-off is what
  lets a conclusion anchor (contradiction detection ~30% FP, 75% expert ceiling).
- **Store substrate:** SQLite (bi-temporal) chosen over a KG lib; cheap to reverse, no
  experiment needed. Kept dependency-light (stdlib + numpy/scipy for the whole backend).
- **Self-test reanalysis** left as an honestly-labelled first-pass replay (no API key here);
  the real Claude-Science backend is a drop-in behind the `Tester` Protocol.

## Side ideas / cutting-edge pulled in (for the paper / future)
- Two-tier + bi-temporal memory (Letta / Graphiti); consolidation ≈ A-MEM/sleep-time compute.
- Conformal selective-prediction (SConU/COIN) + semantic entropy for the calibration gate (E11).
- VoI ÷ cost grounded in health-econ EVPI/EVSI; beat the Open Targets genetic prior, not citations.
- Independence-drift as the strongest collapse feature (Evans-lab replication work), not citation velocity.
