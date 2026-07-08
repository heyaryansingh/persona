# Persona — a persistent synthetic researcher

Persona maintains a durable **self** (interests, beliefs, memory, taste) and spawns an
ephemeral **swarm** of bounded, read-only agents to read the biomedical literature at
scale, closing an agentic loop: **flagged contradiction → falsifiable hypothesis →
located public dataset → first-pass reanalysis → written back into the belief-state**,
escalating to a human exactly when it needs judgment it cannot produce alone.
*Scale of reading, discipline of believing.*

Built for the Claude Science hackathon (Gladstone Institutes). The plan and its evidence
base are in [`planning/`](planning/) and [`results/`](results/); read
[`planning/PHASE0_PLAN.md`](planning/PHASE0_PLAN.md) first.

## Architecture (`persona/`)
| Module | What it is |
|---|---|
| `store.py` | Bi-temporal, provenance-typed belief-graph (SQLite). Anchor write-policy: swarm evidence can't overwrite a `HUMAN_CONFIRMED`/`TESTED` anchor; only a human/test can. |
| `self_state.py` | The living-doc self (identity/agenda/notebook/errors/beliefs.json). Two-tier hydrate; durable kill/rehydrate with no belief loss. |
| `ingest/` | Source-agnostic adapters (live Europe PMC; cached). |
| `swarm/reader.py` | Read-only reader/extractor agents → candidate claims. |
| `membrane.py` | Adaptive commit policy: convergence = **evidential independence** (not agreement count); poisoning switch (E10); typed contradictions `{true-refutation, context-divergence, no-evidence}`; anchor re-escalation escape hatch (E9). |
| `loops/` | inner (read→update), outer (taste + initiative), delegation (dossier→anchor), self_test (contradiction→hypothesis→GEO dataset→reanalysis→**human-gated** write-back), artifact (mini-review + error log). |
| `engine/` | trajectory (3.1), dependency + load-bearing + fragility (3.2/3.3), experiment-value (3.4), silence (3.5), cross-field (3.6). |
| `researcher.py` / `lab.py` | The facade tying it together; a lab of ≥2 researchers whose disagreement is a signal (7.1). |
| `api/app.py` | FastAPI + SSE serving the seven screens. |
| `ui/` | Vite + React + Motion + Cytoscape — the legibility layer (BUILD_PLAN §6). |

## What's validated (see `results/`)
- **Reproduction (gate-0):** all 3 original memory experiments reproduce bit-identically; the poisoning crossover to the digit. One confound quantified & the claim refined (`results/REPRODUCTION.md`).
- **E10** adaptive membrane switch — GO (detect 1.00, false-strict 0.00, retention 1.00).
- **E14** evidential-independence convergence — GO (independent 1.00, echo 0.00 vs naive-count 1.00).
- **E13** taste is functional — GO (top-1 changes 0.80 across dispositions; control identical).
- **E9** human-error escape hatch — GO (wrong-anchor re-escalate 1.00, poison re-escalate 0.00, retention 1.00).
- **Pending (need real data / annotations / an API key), pre-registered as stubs:** E5 (trajectory backtest), E6 (dependency extraction), E7 (VoI vs expert), E8 (real-Claude poisoning replay), E11 (calibration), E12 (swarm-vs-single), E15 (contradiction trigger).

## Run it
```bash
# 1) tests (52, stdlib + numpy/scipy only, no API key needed)
for t in tests/test_*.py; do python "$t"; done

# 2) reproduce the validated experiments
python experiments/exp_when_protection_matters.py       # the crossover
python experiments/exp_e10_adaptive_switch.py           # GO
python experiments/exp_e9_human_error_hatch.py          # GO
python experiments/exp_e13_taste_functional.py          # GO
python experiments/exp_e14_independence.py              # GO

# 3) the "watch it think" slices
python scripts/run_inner_loop.py     # one tick on real Europe PMC papers -> notebook + beliefs
python scripts/run_overnight.py 6    # always-on run: reads, reflections, a self-spawned interest

# 4) the full app (two terminals)
python -m uvicorn persona.api.app:app --port 8000        # backend
cd ui && npm install && npm run dev                      # UI at http://localhost:5173
```
The UI proxies `/api` to the backend. The demo runs offline from a committed fixture
cache (`tests/fixtures/ingest/`); with network it reads live Europe PMC. No API key is
required for the demo; a real Claude-Science reanalysis backend plugs into
`loops/self_test.py` when one is available (until then the reanalysis step is honestly
labelled a first-pass replay).

## Honesty posture
Every belief is provenance-typed and uncertainty-stated. Contradiction detection is a
*surfacing* step; **ignition is human-gated** (the literature shows autonomous
contradiction triggers are unsafe — see `planning/LITERATURE.md §D`). Dependency edges
render as *candidate* until E6. Forecasts render *descriptive* until E5. Nothing here
fakes the swarm or the science.
