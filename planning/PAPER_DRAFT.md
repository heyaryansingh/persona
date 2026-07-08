# On constructing a persistent, continuously-learning synthetic researcher
*Draft — compiles the results as they land (BUILD_PLAN Appendix B). Status: skeleton with the validated core.*

## Abstract (to firm up)
A persistent LLM researcher is less a prompt problem than a **memory, calibration, and
division-of-labor** problem. We separate a small durable **self** from a vast ephemeral
**swarm**, admit swarm output through a **membrane** (convergence + provenance +
calibration), and anchor human-confirmed beliefs. Our headline empirical result: in an
external-memory agent, identity-anchoring is **unnecessary under benign noise but decisive
under correlated poisoning** — a quantified crossover — and, refined here, a membrane does
most of the general anti-poison work while anchoring *guarantees the human-confirmed core*.

## 1. The bottleneck
Science's bottleneck is increasingly synthesis and prioritization, not data generation.
A synthetic researcher that maintains the living state of a field and points at the
highest-leverage next experiment attacks that directly.

## 2. The self/swarm architecture
Separation is the load-bearing commitment (best-evidenced choice per the 2024–26
literature: orchestrator-worker read swarms help *breadth-first reading*; reasoning stays
single-agent — Data-Processing-Inequality). Belief-store is bi-temporal and
provenance-typed; the self is human-readable living-docs, two-tier.

## 3. The membrane + anchoring result (headline)
- Benign independent noise: naive continuous update ties/wins (protection = latency).
  *Reproduced bit-identically.*
- Correlated sustained poisoning: human-anchored retains **1.000 vs 0.762** of verified
  beliefs during attack; quorum membrane 0.950. *Reproduced to the digit.*
- **Refinement (this work):** the "all-poisoned recovery" advantage is an artifact of most
  victims being human-confirmed; the honest claim is *anchoring guarantees the confirmed
  core; the membrane does the general work* (results/REPRODUCTION.md).
- **Escape hatch (E9, GO):** independent contrary evidence re-escalates a *wrong* anchor to
  a human (recovery from human error) without reopening the poisoning vulnerability.
- **Adaptive switch (E10, GO)** and **independence-as-convergence (E14, GO):** the membrane
  detects correlated poisoning online and refuses to count citation echo as independent
  corroboration — the exact failure mode the science-of-science literature documents.

## 4. The acting loop
Flagged contradiction → falsifiable hypothesis → located public dataset (live GEO) →
first-pass reanalysis → **human-gated** write-back. Ignition is human-gated because
deployed contradiction detection has ~30% wild false-positive and a ~75% inter-expert
ceiling; the AI does the superhuman part and escalates the call.

## 5. The intellectual instruments (Part 3) & their gates
Trajectory (E5), dependency/load-bearing (E6), experiment-value (E7), silence (3.5),
cross-field (3.6). Built with honest gates: forecasts render *descriptive* until E5;
dependency edges *candidate* until E6; VoI *experimental* (baseline = Open Targets genetic
prior, not citations) until E7. **Taste is functional (E13, GO):** changing disposition
measurably changes the agenda.

## 6. Human-as-resolver as compounding infrastructure
Expert judgment, once trapped in one lab's heads, becomes a durable shared belief node
others inherit. This is the safety story and the science story at once.

## 7. Limitations & threats to validity
- The membrane/anchor results rest on a boolean-channel simulation; **E8** (real Claude
  extraction + a MINJA-style injection) is the promotion gate to "validated on the real
  regime" and needs an API key.
- E6 inferential-dependency extraction likely can't hit per-edge precision (no dataset
  exists); we judge on rank-correlation and expect the human-in-the-loop downgrade.
- Calibration (5.3) is a hypothesis until E11 selects an estimator + conformal threshold.
- Cross-field translation is a lexical baseline pending embeddings/LLM.

## Reproducibility
Everything seeded; `results/*.json` + `results/REPRODUCTION.md`; the whole backend runs on
stdlib + numpy/scipy with no API key. See `README.md`.
