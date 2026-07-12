# Persona Build Notes

Append-only working record for the research-quality program. Durable numeric conclusions and reversals also go to `results/FINDINGS.md`.

## 2026-07-11 — Step 1 audit

### Scope

Read the frozen architecture plan, live source paths, existing Curie data, current API, research agents, extraction/synthesis code, sandbox/paper paths, and current browser-facing implementation. Reviewed current primary/official work on autoresearch, scientific agents, multi-agent scaling, memory, agent learning, and reproducible research artifacts.

### Reproduced failures

1. `personas/curie-3c33/self/open_questions.md` has 315 bullet items. The shared setter iterates its input without a runtime type check, so a malformed string becomes one question per character.
2. At least one displayed microglia/tau conflict is a sign-extraction failure: both stored quotes describe exacerbation, but one claim is stored with negative polarity.
3. `GET /api/persona/{pid}/topic/digest` calls the worker model when claims and budget exist. Two read-only audit requests spent $0.0887. The docstring incorrectly calls the operation read-only.
4. A completed Curie analysis reports uncited scientific numbers and conclusions because the analyst receives notes rather than the underlying evidence packet and its `finish` result has no evidence-ID requirement.
5. Live data on `curie-3c33`: 5,368 claims, 5,037 entities, 63 sign-collision candidates, 18 synthesis notes, 12 projects. Of the first 200 beliefs, 47 have one lab/source despite a “converged” UI label.
6. Recent 500 events contain 217 spawn, 197 lease, 65 thought, and 21 schedule events. The notebook primarily shows orchestration telemetry, not scientific moves.
7. Current UI adds an ambient fake reader, treats all claims as admitted, uses ingest edges as “Evolution,” and computes load-bearing/VoI/silence heuristics in the browser.
8. Persona selection does not clear all persona-scoped caches. Brain file loading also uses a fixed 300 ms wait even though the observed file request took about 590 ms.
9. `/fieldmap` returns 40 subtopics but is not used by the current UI. `/kg` and `/files` return hundreds of KB in one request.
10. `runs/` has no session records. There is no durable lineage from question through sources, claims, code, outputs, figures, and final conclusions.
11. Unscoped `pytest` collects the archived v3 suite and fails on 32 imports for modules intentionally absent from the live package. Current test discovery was not configured, so the prior “52 tests green” claim was not reproducible against this checkout.

### Decisions frozen from evidence

- Repair trust boundaries before adding autonomy.
- A raw opposite-sign pair is a candidate conflict, not a scientific contradiction.
- Use a hybrid memory: immutable session/artifact record as truth; text/vector and temporal graph as derived retrieval projections.
- Use one strong agent for coupled/sequential tasks; use small heterogeneous cells for decomposable breadth until equal-budget experiments justify more.
- Optimize hosted Claude through harness, tools, prompts, memory, and evaluation. Restrict weight training to open models.
- Do not duplicate Claude Science's generic workbench. Persona owns persistent epistemology, idea genealogy, value-of-information routing, and human-resolution dossiers.

### Next action

Implement and verify four integrity fixes: self-output validation and safe migration; read-only digest GET; honest candidate-conflict status; and server-owned epistemic labels. Preregister and run the real Curie extraction/contradiction experiments before replacing the extraction and conflict mechanisms.

## 2026-07-11 — Step 1 implementation checkpoint

- Added complete reflection-payload validation before any durable self mutation and matching validation in shared self setters.
- Preserved the malformed Curie file byte-for-byte at `personas/curie-3c33/quarantine/open_questions-malformed-2026-07-11.md` (SHA-256 `A43EB9D42CED6E62DA8CC656AD12B6C1CBEA46CBBC88C4F3BE68B0F523663F1F`). Recovered eight scientific questions from the latest interests and changelog; recorded the recovery in Curie's changelog.
- Split topic digest into a read-only GET evidence bundle and explicit model-generating POST.
- User-facing sign collisions are now `candidate_conflict / unverified`; direct binary anchoring requires explicit verification and rationale.
- Beliefs now carry a server-owned `epistemic_state`: observed, corroborated, tested, or anchored.
- Removed fake idle swarm activity, hid scheduler noise from the scientific stream, cleared persona-scoped UI caches, and relabeled unvalidated client metrics honestly.
- Added three integrity regression checks and scoped pytest to the live `tests/` tree; archived suites remain unchanged.

### Live browser evidence

- Active Curie rendered exactly eight recovered questions; no character fragments remained.
- The claims rail read `observed claims`; a 10-lab item rendered `corroborated`, not globally “converged.”
- Instruments rendered explicit headings `Epistemic status`, `Connectivity triage · unvalidated heuristic`, `Candidate review order · unvalidated heuristic`, `Sparse-evidence candidates`, and `Candidate-conflict inbox`; no raises/lowers resolution buttons remained.
- The microglia/tau candidate displayed both exact spans. Both say activation can **exacerbate tau pathology**, proving the stored negative sign is an extraction error rather than a scientific contradiction.
- The scientific stream omitted spawn/lease/schedule telemetry and fake idle readers. It still exposed repeated OpenAlex 400 fallback events and repeated reflection-status messages; that daemon/source-loop defect remains open.
- Verification: `python -m pytest -q` -> 3 passed; Python compilation passed; inline UI JavaScript parsed; GET and POST digest routes both registered.

### Runtime-loop root cause

- App startup resumed every persona marked running. Each daemon had six workers and a five-second scheduler.
- Whenever queue depth fell below four, the scheduler immediately enqueued a reflection; reflection fanned out five broad searches plus bulk/harvest work. A drained queue therefore caused a new correlated research pulse every five seconds.
- One interest is phrased as a question. OpenAlex interprets `?` as a wildcard and returns HTTP 400 for default stemmed search, so the same pulse repeatedly failed over to Crossref.
- Fix: broad pulses now have a 15-minute minimum cooldown; expensive self evolution defaults to 30 minutes; the calibration knobs remain environment-overridable. OpenAlex queries strip wildcard punctuation before request. This is an operational safety correction; RQ-E07/E09 will determine the eventual learned routing/cadence.
- A no-worker live run held Curie's queue exactly constant for 12 seconds (`pending=1`) and spend exactly constant at `$0.7538`; workers reported zero. The earlier full-worker audit had already raised the day's Curie spend from roughly `$0.09` to `$0.7538`, which is direct evidence that auto-resuming five six-worker minds during inspection was unsafe. Further runtime validation defaults to zero workers until explicitly testing execution.
- Restart behavior was tightened further: only a genuinely new, empty queue receives an immediate pulse. Existing minds start on cooldown, preventing every API restart from multiplying work across all Curie instances.

## 2026-07-11 — RQ-E01a claim-integrity experiment

- Ran `experiments/exp_rq_e01_claim_integrity.py` over 5,704 real Curie claims with 30 seeded bootstrap resamples of 500 claims each.
- Current admission accepted 24.0% ± 0.7% quotes not found in normalized source text.
- Exact schema/span validation retained 76.0% ± 0.7% and reduced non-verbatim evidence admission to zero.
- A lexical direction proxy alarmed on 27.6% ± 1.4% of checkable accepted claims and identified three of seventeen sign-conflict pairs where both sides expressed the same direction. Inspection also found false positives from composite/multi-clause sentences, so the proxy is diagnostic only.
- Reversal: do **not** ship simple polarity lexicons as a belief gate. Ship exact-span/schema validation; keep polarity correction gated on a structured verifier and human-labeled RQ-E01b/RQ-E02.
- Implemented the exact gate once in `reading.extract.validate_claims()` and reused it for interactive and batch readers. Rejected outputs are retained beside the source in `claims_rejected.jsonl` and logged; they cannot reach the membrane.
- Outputs: `results/rq_e01_claim_integrity.json` and `results/rq_e01_claim_integrity.png`. Verification: 5 tests passed; updated modules compiled.

## 2026-07-11 — RQ-E07a preregistration correction

- Initial density floor (at least 60 packets and 30 exact spans per entity) left only three Curie topics, so the run aborted before results.
- Correction: construct each of 30 seeded research tasks from the union of three entities drawn from 58 entities with at least 10 packets and five exact spans. Team sizes, topologies, per-agent budget, seed count, metrics, and stop rule remain unchanged.
- Pre-promotion verifier correction: dense sharing initially permitted within-agent copying at N=1 and topology arms used different random streams. Corrected to copy only prior agents, use paired streams, and assign zero coordination overhead at N=1. The preliminary output was overwritten and is not a finding.

## 2026-07-11 — RQ-E07a swarm-physics result

- Completed 30 paired seeded Curie replays across N=1 through N=1,000 with 5,704 real evidence packets.
- At N=30, dense sharing: 50.2% ± 5.5% coverage, 80.8% duplicates, efficiency 0.127. Central source partitions: 88.8% ± 3.7% coverage, zero duplicates by construction, efficiency 0.305.
- Central partition efficiency peaked at N=3 (0.786 versus single 0.772). By N=100, non-dense arms had 97–99% coverage but only ~14 effective agents. N=1,000 remained ~14–15 effective agents.
- Decision: default workers 6 -> 3; no dense all-to-all debate; partition sources and stop when marginal verified evidence falls below cost. Sequential/live-model claims remain unproven.
- Outputs: `results/rq_e07a_swarm_physics.json` and `.png`.

## 2026-07-11 — Step 2 evidence-session forward test and reversal

### Mechanism implemented

- Added append-only research sessions under each persona's `runs/` directory. `events.jsonl` records the public execution trace; `session.json` records contract, status, artifacts, conclusions, model, cost, and verifier state. Artifacts are content-addressed by SHA-256, and each completed session emits dependency-free RO-Crate 1.3 JSON-LD.
- The analyst now stores the evidence packet, model/tool blocks, code, stdout/stderr, tool receipts, and generated project files. A session cannot finish an established `SUPPORTED` or `INFERRED` conclusion without known claim/artifact IDs; `UNSUPPORTED_HYPOTHESIS` remains available for explicitly unproven ideas.
- Investigations launched from a candidate conflict now pin both triggering claim IDs. Retrieval may add context, but it cannot silently omit the disputed evidence.
- Added session list/read/artifact APIs and append-only verifier verdicts. Invalid sessions remain visible rather than being overwritten.

### Failed first forward test

Session `20260711T181704Z-do-the-two-stored-claims-that-microglia--9d69547b` passed the initial technical gate because it executed code and cited evidence IDs. On review, the general retriever had omitted the two claims that actually triggered the investigation, so the report answered a nearby question from an incomplete packet. This is a **failed scientific session despite valid-looking citations**.

The session was marked `invalidated`; its trace remains intact. Reversal: “has citations” is insufficient. The task contract must name required evidence, and finalization must prove those IDs were present.

### Corrected forward test

Session `20260711T182050Z-do-the-opposite-stored-signs-for-microgl-8774b70a` pinned:

- positive claim `clm_33711b72f30d`, DOI `10.1016/j.trci.2018.06.014`, exact text says microglial activation can “exacerbate both amyloid and tau pathology”;
- negative-stored claim `clm_9272dc679319`, DOI `10.1083/jcb.201709069`, exact text says microglia can “also exacerbate tau pathology.”

The session executed code, preserved its evidence and outputs, and concluded that this pair is an extraction-sign error, not a true refutation or context divergence. The primary conclusion cites both claim IDs and was independently marked `verified` at confidence 0.88. Broader literature commentary remains `INFERRED` and is not promoted.

The membrane correction is append-only:

- the old graph node remains with `provenance=REJECTED_EXTRACTION`, `valid_to`, reason, and correction-session ID;
- the raw source `claims.jsonl` remains unchanged;
- `claim_corrections.jsonl` stores the source-level old/new sign overlay;
- the source evidence transfers to active positive claim `clm_33711b72f30d`, which now has two independent DOI-backed sources;
- the microglia activation → tau pathology pair no longer appears among active candidate conflicts.

Verification: Python compilation passed; `python -m pytest -q` reports **8 passed**; a live FalkorDB read confirmed the retired node, one overlay record, zero active matches for this candidate pair, and two exact-source records on the corrected claim.

### Session replay, figure, and workbench proof

- Added a no-model replay audit: `python -m persona.sessions <runs-dir> <session-id>`. It verifies ordered event IDs and parent references, every artifact hash/size, required-evidence recall, reconstructed model cost, RO-Crate context, and verifier presence. It explicitly reports lineage integrity separately from scientific truth.
- The corrected session passes with 34 events, 20 hash-valid artifacts, 2/2 required claims cited, reconstructed model cost `$0.226482`, and scientific verdict `verified`. The final verifier event also records visual review of the figure and its code/CSV lineage.
- Added and executed `analysis/figure_sign_consistency.py` inside the credential-free sandbox. It emitted a source CSV and the publication-ready `microglia_tau_sign_consistency.png`; code, CSV, PNG, sandbox receipt, and image digest are appended to the same content-addressed session lineage. Visual QA confirmed both stored markers remain visible and the mismatched negative sign is unambiguous.
- Future analyst calls now record model/tool latency, causal event parents, aggregate session cost, source paths, and all model requests; finalization rejects any session whose conclusions omit a task's required claim IDs. The preserved historical session predates causal-parent instrumentation, so its chronology remains flat rather than fabricating links.
- The top-level `Studios` surface is now `Research`, without adding another navigation button. It leads with keyboard-operable session cards, visibly separates invalidated and verified work, distinguishes trace-integrity from scientific review, and exposes required packets, conclusion → evidence links, content-addressed artifacts, figures, and a collapsed raw public trace. The list endpoint returns paginated summaries rather than complete session payloads.
- Headless Chromium smoke with `PERSONA_WORKERS=0` passed: two session cards; corrected session shows `Trace integrity · passes`, `2/2 required claims cited`, conclusions, primary figure, and public execution trace; no application console errors or failing API requests. Screenshots: `results/ui_research_sessions.png` and `results/ui_research_session_detail.png`.

## 2026-07-11 — RQ-E03a memory-retrieval screening preregistration

The RQ-E03 contract calls for 200 human-checked questions. Those labels do not yet exist, so no run may claim semantic answer accuracy. E03 is split before execution:

- **E03a, now:** auto-labeled structural evidence retrieval over real `curie-3c33` claims, exact quotes, sources, belief history, synthesis notes, candidate conflicts, and session traces. This can falsify retrieval architectures and quantify forensic access.
- **E03b, later:** the original 200 human-checked questions and answer/provenance grading. Only E03b can justify claims about research-answer quality.

E03a freezes exactly 200 questions: 40 exact-provenance, 30 temporal-change, 40 two-hop connection, 30 candidate-conflict, 30 field-note, and 30 session-reconstruction queries. If the live data cannot supply a category, the run aborts rather than silently changing the mixture.

Arms under the same top-k contract:

1. unindexed raw lexical scan over all evidence documents;
2. summary-only BM25;
3. all-document BM25;
4. dense vectors over the same documents when the existing local embedder is available;
5. temporal/relationship graph retrieval;
6. reciprocal-rank hybrid of BM25, vectors, and graph.

Primary metric is macro evidence-set F1@10 across the six categories, with Recall@5/10, MRR, exact-provenance recall, temporal recall, session-forensic recall, p95 latency, estimated retrieved tokens, and index write amplification. Report 30 seeded bootstrap resamples with mean ±95% CI. The original deployment gate remains: hybrid must beat the best single projection by at least five macro-F1 points and must not lose session-forensic recall. If it does not, keep the simpler winner. Auto-labels and any embedding fallback must be explicit in the result.

### Pre-run data sufficiency correction

The live audit found 62 active candidate conflicts, but only 18 claim histories with at least two snapshots, 23 synthesis notes, and 2 real research sessions. Therefore 200 generated questions are **not 200 independent scientific cases**. E03a may create distinct question/facet variants to preserve the frozen category mixture, but every row must retain a `base_item_id`; uncertainty is grouped by base item where possible; unique base counts are reported; and the 30 session facets are explicitly a two-session forensic diagnostic. The no-loss session gate is provisional until Persona accumulates more independently generated sessions. E03b still requires 200 human-checked questions and cannot inherit E03a's confidence intervals.

## 2026-07-11 — RQ-E12a LaTeX compiler integrity reversal

### Reproduced failures

- A valid `main.tex` compiled to a 11,375-byte PDF. After the source was replaced with an undefined LaTeX command in the same directory, the old compiler returned `ok=true` even though the log contained `Undefined control sequence` and a fatal no-output error. The PDF hash, size, and modification time remained byte-identical: Persona would have copied an old paper as the new result.
- Root cause: the sandbox command ended with `true`, discarded Docker's exit code, and defined success only as “a PDF path exists.” Stable slug directories made stale artifacts likely.
- The `tex` filename was interpolated into a shell command. A benign probe wrote an injected marker into the mounted workspace.
- Identical source compiled seconds apart produced different PDF hashes because creation dates/trailer IDs were not frozen.
- Distinct long topics shared the same truncated 50-character slug directory, allowing concurrent source/log/output overwrites.

### Correction and deterministic result

- Removed the shell entirely. `pdflatex` receives a validated filename as a Docker argument; the root filesystem is read-only, network is disabled, `/tmp` is bounded, and `/work` is the only writable mount.
- Stale PDF/log/auxiliary files are removed before compilation. Both compiler passes must exit zero and produce a nonempty new PDF; failure removes any partial PDF.
- `SOURCE_DATE_EPOCH=0`, `FORCE_SOURCE_DATE=1`, and `TZ=UTC` make identical source plus environment byte-reproducible.
- Compiler receipts now return exit code, source/PDF SHA-256, and sandbox image digest. Paper runs use unique run directories, version PDF names by source hash, and retain a compile manifest with attempts, costs, logs, source list, and deliverable hash.
- `experiments/exp_rq_e12_latex_integrity.py` passed all four deterministic gates: valid compile in the read-only container; identical source produced the same PDF SHA-256 (`9afcd39a…`) in two fresh directories; invalid recompile returned exit 1 and left no PDF; unsafe filename was rejected before Docker. The image digest is `sha256:a6a829…76ecf9`.
- Outputs: `results/rq_e12_latex_integrity.json` and `.png`. This is a deterministic seam regression, not a multi-seed scientific benchmark. Full RQ-E12 clean-container, numeric, figure/data, citation, and AstaBench evaluation remains open.

## 2026-07-11 — reusable evidence-session skill forward test

The new user-level `evidence-first-research-session` skill was exercised by a fresh-context agent on a different live Curie conflict without network or model calls. The task was deliberately bounded to the two exact stored claim windows for α-synuclein aggregation → ferroptosis.

- The bundle contains 14 append-only events, six content-addressed artifacts, 2/2 required claim IDs, executable deterministic analysis, an explicit unsupported wider-literature hypothesis, and a separate verifier artifact.
- The integrity verifier returns `ok=true` with zero errors and zero warnings. A fresh scientific reviewer independently returned `verified`, scoped only to the two local windows.
- Both windows express induction of ferroptosis. The stored negative sign is therefore reasonably classified as an extraction/sign-label error for these spans; the negative record's shortened quote also omits “not only,” exposing an independent quotation-fidelity defect.
- The report initially mentioned a verifier file before that file existed. The correction was appended as events 13–14 rather than rewriting the earlier trace, making the process failure and its repair visible.
- The wider claim that no full-paper or context-dependent reversal exists remains `UNSUPPORTED_HYPOTHESIS` at confidence 0. This test does not authorize an automatic knowledge-graph correction or validate contradiction classification generally.

Forward-test bundle: `results/skill-forward-test/`. Reversal: a technically valid evidence bundle still needs a distinct scientific verdict artifact; references to future verification are not verification.

## 2026-07-11 — RQ-E03a structural memory retrieval result

The final run indexed 6,274 real Curie records and evaluated the frozen 200-query mixture with 30 category-stratified base-cluster bootstraps. Source correction overlays were applied before claim/conflict reconstruction, so retired extraction claim `clm_9272dc679319` was not reintroduced. The result remains an auto-labeled structural diagnostic: mean query-token containment in its gold record was 0.604 (p95 0.867), so it does not estimate real-user question performance or scientific truth.

| arm | macro evidence F1@10 | Recall@10 | p95 query ms | index write amp. |
|---|---:|---:|---:|---:|
| summary BM25 | 0.199 | 0.842 | 25.83 | 0.302× |
| all-document BM25 | 0.188 | 0.806 | 30.33 | 0.720× |
| dense BGE | 0.182 | 0.782 | 1.12* | 2.373× |
| temporal graph | 0.200 | 0.856 | 40.37 | 0.743× |
| RRF hybrid | 0.210 | 0.891 | 62.64 | 3.418× |

`*` Dense query latency excludes the expensive index build. The first default full-corpus attempt reached 9.08 GB parent RSS and was stopped. A supposed 84 MB fix was invalidated because FastEmbed 0.8.0 interprets `parallel=0` as automatic multiprocessing and spawned 22 memory-heavy Python workers. The accepted run used `parallel=None`, two threads, local-files-only input, and batches of 32. The reversal is retained in the result metadata.

Hybrid F1 improved only 0.010 over the best single arm (temporal graph), far below the preregistered +0.05 gate. Session reconstruction remained weak even for hybrid (Recall@10 ≈0.524) and is based on only two sessions. Dense retrieval underperformed summary BM25 on this synthetic ledger while requiring much more index storage.

**Decision:** reject deployment of the hybrid/dense memory stack from E03a. Keep the existing simple retrieval path until E03b has human queries and judgments; use this run only to reject unjustified complexity and to prioritize session retrieval as a real gap. A planned cached determinism rerun was stopped when the newly created E12b session changed the live corpus and correctly invalidated the embedding fingerprint; do not compare across different corpus snapshots.

Artifacts: `experiments/exp_rq_e03a_memory_retrieval.py`, `results/rq_e03a_memory_retrieval.json`, and `.png`.

## 2026-07-11 — RQ-E12b real GEO executable-session result

Persona completed its first zero-model-cost, public-data acting loop in session `20260711T194501Z-does-a-prespecified-nrf2-associated-tran-08c6fd9b`. The session pins two canonical claim packets, the three original compressed GEO/annotation files, exact input hashes, preregistration, complete host/worker code, sandbox digest and constraints, output tables, bootstrap/leave-one-out results, figure, report, replay manifest, and method/session verifiers.

Independent raw-data audit confirmed:

- GSE1297: 31 samples, 22,283 unique probes; GSE28146: 30 samples, 54,675 probes; 30 exact matched donors and 22,277 shared probes;
- both matrices are positive linear-scale intensities, so the preregistered `log2(x+1)` transform is appropriate;
- all matched donors agree on severity, age, and sex; donor 1039 is the one GSE1297-only control;
- the frozen seven-gene panel maps to 13 shared probes; both FTL probes are `_x_at` cross-hybridizing probes, an interpretation caveat;
- planner-provided IDs were raw source-record IDs. The session correctly pins live canonical KG claims `clm_f4c5e47c1470` and `clm_cf8d869026bb` while retaining the source packets.

The preregistered “decline in both preparations” hypothesis did **not** pass:

| preparation | adjusted severity β | 30-draw paired-bootstrap 95% | LOO sign |
|---|---:|---:|---:|
| GSE1297 fresh-frozen CA1 block | +0.1071 | [+0.0245, +0.2817] | 7/7 |
| GSE28146 laser-captured CA1 gray matter | +0.0619 | [-0.0333, +0.2056] | 7/7 |

The frozen branch is `inconclusive`: both point estimates are positive, but only the bulk-preparation diagnostic interval excludes zero. These are two preparations from the same donors, not independent cohorts. The panel is an expression proxy and mixes context-dependent iron/HO-1 genes; it does not measure NRF2 activity, oxidative damage, ferroptosis, or causality.

Executable gate passed 20/20 pristine offline Docker reruns with exact summary/scores/bootstrap/leave-one-out hashes and zero numeric error. That establishes deterministic computation, not stable uncertainty or biological interpretation.

Important limitation: 30 paired bootstrap draws meet the frozen repository seed minimum but are too few for a high-resolution percentile interval. They remain a preregistered diagnostic and must not be promoted to population validation. A future sensitivity analysis should use ≥2,000 draws and HC3/independent-cohort replication without rewriting the original branch.

### Independent review and append-only sensitivity correction

A fresh reviewer reproduced all artifact hashes, core CSV/JSON hashes, and both coefficients, but contested the scientific presentation. A 10,000-draw paired bootstrap and HC3 t intervals included zero for both preparations:

| preparation | full-panel 10,000-draw 95% | HC3 t 95% | no-FTL β and 95% |
|---|---:|---:|---:|
| GSE1297 | [-0.0078, +0.2893] | [-0.0541, +0.2683] | +0.0561 [-0.0718, +0.2740] |
| GSE28146 | [-0.0682, +0.1811] | [-0.0808, +0.2046] | +0.0203 [-0.1159, +0.1400] |

Removing cross-hybridizing FTL probes reduced coefficient magnitude by 47.6% and 67.2%. Residual/leverage/Cook diagnostics, gene-level scores, 40,000 sensitivity draws, exact code, an age/sex-adjusted figure, report, receipt, and verifier were appended without rewriting the original artifacts. The original positive-branch classifier had also added a 6/7 LOO requirement not present in the preregistration; the future script is corrected, and the bug did not affect this already-inconclusive case. The original figure's unadjusted points/means with adjusted annotations and non-reproduced PNG bytes remain visible in the trace; the revised figure uses adjusted display scores.

Latest replay: 58 ordered events, 30 hash-valid artifacts, 2/2 required claims, `$0` model cost, zero errors/warnings. Events 56–58 are a redundant verifier/audit append produced when a handoff audit invoked the then-unguarded sensitivity script with `--help`; they repeat the same `contested` reason and are not new scientific evidence. They remain visible under the append-only contract. Both E12b host CLIs now parse help before execution, and sensitivity defaults to refusing a second append. Latest scientific verdict is `contested`; deterministic computation remains verified, and all primary/sensitivity branches remain `inconclusive`. No positive, compensatory, or causal claim is supported.

Artifacts: `experiments/exp_rq_e12b_geo_self_test.py`, `experiments/exp_rq_e12b_geo_sensitivity.py`, both `results/rq_e12b_geo_*` result/figure pairs, the live session above, and portable `results/rq_e12b_geo_session_bundle.zip` plus its SHA-256 sidecar. The archive is required because `personas/` is git-ignored.

## 2026-07-11 — candidate-conflict evidence dossiers and label ledger

The old inbox showed an opposite-sign pair and two quotes but supplied no scientific context, review taxonomy, durable rationale, or usable training/evaluation label. It also retained a nominal resolve endpoint that could anchor a candidate before the RQ-E02 typing gate had passed.

The repaired flow:

- opens a server-built dossier only for a currently active candidate pair;
- explains the mechanical trigger (same canonical pair, opposite stored signs) and explicitly says it is not a verified contradiction;
- shows both canonical relations, stored signs, source-group counts, exact quotes, labs, years, and DOI links;
- lists the missing population/species, tissue/cell, disease-stage, intervention/comparator, dose/time, outcome, and study-design fields rather than hallucinating them;
- proposes source-fidelity, qualifier, independence/retraction, and matched-context checks before an experiment;
- accepts only `extraction_error`, `true_refutation`, `context_divergence`, or `insufficient_evidence`, with confidence and a ≥20-character rationale;
- stores reviews in `.persona/conflict_reviews.jsonl` as canonical JSON with stable conflict IDs, content hashes, a previous-record hash chain, fsync, and a process-local lock;
- verifies the full ledger before every read/append and refuses to append after corruption;
- never imports or calls the KG from the ledger module. Review POSTs return `belief_mutated=false`; direct candidate anchoring is disabled until RQ-E02 passes.

Validation: 11 Python tests pass, including append-only/hash-chain/tamper/validation cases. Live no-worker API rejected a short rationale with HTTP 422 and did not create a ledger. Chromium opened a real oxidative-stress/AD dossier and found the why/context/check/review surfaces without console/API errors. Screenshot: `results/ui_conflict_dossier.png`.

This creates a safe single-process pilot substrate; it does not itself validate contradiction typing or provide a labeled dataset. Multi-rater collection still requires pseudonymous reviewer/assignment/blinding metadata, duplicate-review prevention, and cross-process serialization.

## 2026-07-11 — accidental E12b invocation quarantined

A read-only handoff audit tried `experiments/exp_rq_e12b_geo_self_test.py --help`. The script did not yet implement a help-only path, so it began a new session before the auditor terminated it. The incomplete run had status `running`, eight setup/input artifacts, no analysis result, and did not alter the top-level E12b result files. It was moved intact from the active `runs/` directory to `personas/curie-3c33/quarantine/incomplete-sessions/20260711T201417Z-does-a-prespecified-nrf2-associated-tran-9a665916` so it remains auditable without appearing as research or contaminating session retrieval. No live process remained. This exposed the CLI-safety requirement addressed below.

The same audit also invoked the old sensitivity CLI, which appended a duplicate verifier, `contested` verdict, and session-audit artifact to the canonical run. Append-only events 56–58 are preserved and hash-valid but are not new scientific evidence. During the repair, an initial patch accidentally modified the embedded worker guard rather than the host entry point; a safety check therefore produced an invalidated 0/20 session. That entire trace is preserved under `personas/curie-3c33/quarantine/incomplete-sessions/20260711T201922Z-does-a-prespecified-nrf2-associated-tran-d7c1ffd4` and is absent from active runs. The final repair adds real host-side `argparse` help to both scripts and makes the sensitivity script refuse an existing append unless `--allow-repeat` is explicit. Verification observed 58 events before and after both help calls and after the default repeat refusal.

## 2026-07-11 — integration audit of later agent changes

- Verified 20 Python tests, full Python compilation, active-session replay, and the research browser smoke using the bundled Playwright module path.
- Added a byte-exact event-log digest to new sessions and sealed all three active legacy traces without changing event counts. A valid-JSON edit to an event now causes `event-log-sha256-mismatch` rather than a false trace-integrity pass. This is tamper evidence within the workspace, not a defense against an attacker able to rewrite both the log and its metadata.
- Repaired `analyst._safe_join` so a sibling path with a shared string prefix cannot escape the per-session project workspace.
- Added a real `--help` parser to E03a after an audit probe started a full retrieval benchmark; help now exits without creating work.
- E10 originally used Python's randomized `hash(arm)` for seeds and called exact-span eligibility a true conflict. Fixed deterministic arm offsets, reran under distinct hash seeds with identical JSON, and corrected the claim. The harness is not integrated into runtime human escalation.

## 2026-07-11 — RQ-E07b specialized/distributed swarm result
- Built `exp_rq_e07b_specialized_distributed_swarm.py` on the E07a loader, adding role specialization
  (extractor / exact-span verifier / reducer), correlated whole-source error injection, and the
  quality metrics E07a lacked (validated/token, false_admit_rate, false_conflict_rate).
- Honest reversal within the run: the first mechanism (verify EVERY proposed packet) hit 0% false
  conflicts but halved validated/token (0.5× partition) → failed the affordability gate (NO-GO).
- Added a smarter arm: verify only DECISION-RELEVANT evidence (sign-collision participants +
  convergent belief-candidates). It keeps 87% of partition throughput and still drives false
  conflicts to 0 → GO. Recorded both; kept verify-all as the documented contrast.
- Limitation: verifier assumed perfect; correlated error modelled as whole-source corruption; token
  costs are proxies. Live-model breadth-vs-sequential (E07b-live) and diversity/router (E08/E09)
  remain unrun. Do not claim differentiated live-agent science yet.
