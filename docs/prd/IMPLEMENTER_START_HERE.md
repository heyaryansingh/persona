# Implementer start-here — the shortest path to shipping

> For implementer lanes 1–4. Read `PRD-00-overview.md` (contracts + ownership) once, then follow YOUR lane below. Full feature detail is in each `PRD-0X`. Coordinate via the dispatch table in `.agent-orchestration/HANDOFF.md` — post `CLAIMED → IN-PROGRESS → PR-READY → VERIFIED` as you go, and claim any boundary file before editing it.

> **Canonical ids govern.** Where any PRD body's FC/RQ id, gate-flag path, or oracle-file path disagrees with `PRD-00 §4/§6`, **§4/§6 win** — see the reconciliation table in `PRD-00 §8` (the bodies predate the master's collision fixes). Notably: oracle protection oracle = `experiments/exp_poisoning.py`; the DepMap FC-8 verdict registers as `"depmap_oracle"` (not `"depmap"`, which is the fetch).

## The one rule that lets all four of you work at once
**Milestone 0 first:** land the FC stubs your lane *provides* (exact signatures + typed fixture/empty returns), commit in place, post it on the bus. Then every other lane can build against you from hour one. Only after M0 do you fill implementations.

---

## Lane 1 — Heterogeneous teams
**You provide:** FC-1 (`verify`/`debate`/`staleness` task types, `investigation.open_from_conflict`, `agents/consensus.span_weighted_consensus`).
**M0:** register the three task types in `worker.py` (append-only block); stub `open_from_conflict` + `consensus.py`.
**Then, in order:**
1. `PRD-01` F1.10 `open_from_conflict` (unblocks Lane 2/3) → F1.2 tool-grounded verifier (`verify`).
2. `PRD-09` red-team-the-belief agent (procedural block via FC-2; RQ-E25).
3. `PRD-01` F1.3 two-reader cross-check (RQ-E19), F1.5 span-weighted consensus (RQ-HT05, oracle `exp_poisoning.py`), F1.6 surprise queue (RQ-E18), F1.1 DAG investigations, F1.4 gated debate, F1.7–1.9.
4. `PRD-05` (with Lane 2) disposition levers + `manager.create(disposition=)` / `config.SELF_FILES` (RQ-E20).
5. `PRD-22` verifier-calibration monitor (new RQ).

## Lane 2 — Calibrated membrane & belief core
**You provide:** FC-2 (inbox), FC-3 (kg queries + dep-edge writers + `set_citation_class`), FC-5 (calibrate), FC-10 (causal-tier), FC-11 (sleep-consolidation), FC-12 (clinical gate), FC-13 (confidence-budget). **You have the most consumers — land M0 first.**
**M0:** stub `inbox.file_handoff`; `kg.provenance_breakdown/add_dependency_edge/dependency_edges/citation_support_ratio/set_citation_class`; `calibrate.admit_decision`.
**Then, in order:**
1. `PRD-02` F2.5 conflict typing (RQ-E02 substrate) + F2.11 provenance API (unblocks Lane 4) → F2.3 conformal calibrate (RQ-E16) → F2.1 dual-signal admit → F2.2 span-escalation/abstain → F2.6 no-confidence-inflation → F2.9 staleness (`history.stale_claims`, single-def) → F2.7/2.8/2.10/2.12/2.13.
2. `PRD-12` causal-tier gate (FC-10, RQ-E26); `PRD-20` confidence-budget (FC-13, one-line clamp after F2.1/F2.3, RQ-E34).
3. `PRD-17` FDA-surrogate gate (FC-12, RQ-E31); `PRD-08` molecular priors (RQ-E23).
4. `PRD-14` sleep-consolidation (FC-11, dry-run until RQ-E28); `PRD-11` contradiction-gold ledger (with Lane 4, CCP-11a).
5. `PRD-05` cross-persona reconcile (FC-9, with Lane 1).

## Lane 3 — Intellectual engine, forensics, data
**You provide:** FC-4 (`engine.dependency_graph`/`value_queue` via `analysis/engine.py` facade, `+fragility_cascade`), FC-6 (retraction), FC-8 (oracle envelope + oracles, register in `science.REGISTRY`).
**M0:** stub `engine.dependency_graph`/`value_queue` + `retraction.is_retracted`/`contamination`.
**Then, in order:**
1. `PRD-03` F3.1 dependency graph (RQ-E06) + F3.2 value-queue (RQ-E17, advisory until gate) → F3.6 retraction/contamination → F3.8 forensics applicability gates + DEBIT → F3.7 auditor session + F3.9 GEO resolution + rest.
2. `PRD-16` oracle control-injection FIRST among oracles (guards them; RQ-E30) → then oracles `PRD-06` MR (RQ-E21), `PRD-07` DepMap (RQ-E22, guarded path), `PRD-10` meta-analysis (RQ-E24). Each adds a pure `verdict_from_*` control hook.
3. `PRD-18` LEGEND lookup-oracle (RQ-E32, READ provenance); `PRD-23` SemMedDB dep-edge seeding (RQ-E06 improvement); `PRD-21` cross-field translation (new RQ).
4. `PRD-13` `fragility_cascade` (CCP-13a, with Lane 4); `PRD-19` null-hunt (with Lane 1, RQ-E33).

## Lane 4 — Legibility, flagship UI, benchmarks
**You provide:** FC-7 (`eval.run_oracle`).
**M0:** stub `eval.run_oracle`; scaffold the flagship "Field-rests-on-this + value queue" screen against FC-4 fixtures.
**Then, in order:**
1. `PRD-04` F4.1 flagship screen (against FC-4 fixtures → real when Lane 3 lands) + F4.8 LitQA2/BixBench oracles (RQ-E15).
2. `PRD-04` F4.2 auditor trust tab, F4.3 handoff inbox, F4.4 epistemic dashboard (FC-3/FC-5), F4.5–4.10.
3. `PRD-15` self-calibration panel (reads verified/auditor outcomes); `PRD-13` fragility render (`GET /engine/fragility`).
4. Renders for cross-lane features: `PRD-11` blinded review UI + `app.py:698` call-site update (CCP-11a), `PRD-17` badge (FC-12), `PRD-20` over-drawn stratum (FC-13), oracle results (FC-8 one renderer).
5. Every new surface passes a `PERSONA_WORKERS=0` browser smoke.

---

**Definition of done per feature:** the acceptance criterion met + one runnable check passing (a `pytest` name or CLI assertion); Lane-4 surfaces also pass a browser smoke. Load-bearing choices pass their RQ gate before driving autonomy. Commit only when the user asks.
