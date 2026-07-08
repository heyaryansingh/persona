# Persona — Phase-0 Planning Artifacts
*Orient → verify → plan like a scientist, before any module code (CLAUDE.md §2). This folder + `results/` + `experiments/` are the Phase-0 deliverables. Living documents — revised as evidence lands.*

## Map: kickoff steps → artifacts
| Step | Deliverable | File |
|---|---|---|
| — | The approved plan (source of truth: context, decisions, full Steps 1–6) | [`planning/PHASE0_PLAN.md`](PHASE0_PLAN.md) |
| 1 | Synthesis + `[E]`/`[H]` evidence ledger | `PHASE0_PLAN.md` §1 |
| 2 | Current-literature review (6 domains, cited, adversarial) | [`planning/LITERATURE.md`](LITERATURE.md) + raw `literature_sweep_raw.json` |
| 3 | Experiment verification (reproduction + Confound A) | [`results/REPRODUCTION.md`](../results/REPRODUCTION.md) |
| 4 | Experiment program (specs + stubs) | `PHASE0_PLAN.md` §4 + [`experiments/exp_e5..e15_*.py`](../experiments) |
| 5 | Design concepts (7 screens + swarm view) | `PHASE0_PLAN.md` §5 |
| 6 | Revised, dependency-ordered build sequence | `PHASE0_PLAN.md` §6 |
| — | Extended findings (reproduction + refinements) | [`results/FINDINGS.md`](../results/FINDINGS.md) |

## Locked decisions (from user review)
- **Persistent persona over domain** — seed = a starting point, not the identity; source-agnostic curiosity; always-on reading swarm, centralized reasoning.
- **Full implementation** — spine + Tier-2 + stretch (2nd researcher).
- **UI:** Vite + React + Motion + Cytoscape.
- **Data:** live-early (Europe PMC / Open Targets / ClinicalTrials) behind a cache backstop.

## Status
- ✅ Steps 1–6 written. ✅ Gate-0 reproduction PASS (crossover reproduces to the digit; one confound quantified and the claim refined). ✅ 11 experiment stubs pre-registered (E5–E15), fail-loud until implemented.
- ⏭️ Next (on go): **Build Step 1** (bi-temporal two-tier belief-store + living-doc self + live source-agnostic ingestion), gated by nothing; then **Step 2** membrane gated by E8/E10/E12/E14.

## How to reproduce the verified result
```
python experiments/exp_memory_core.py
python experiments/exp_memory_v2.py
python experiments/exp_when_protection_matters.py
```
Deterministic. Expect bit-identical means; see `results/REPRODUCTION.md`.
