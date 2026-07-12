# Persona research-quality continuation handoff

Last updated: 2026-07-11 after the final integrity, replay, archive, and browser checks in this slice. This is a living continuation contract, not a retrospective. Re-read the live checkout before editing because Persona's append-only state may evolve after this handoff.

## 1. Mission and non-negotiable product thesis

Persona must become a persistent, scientifically legible researcher that helps human teams move work forward. It must read broadly with disposable agents, preserve a small durable self, distinguish stored claims from truth, expose exact evidence and derivations, run code and public-data experiments, produce publication-grade figures/papers, and route wet-lab or judgment-heavy decisions to humans. Its differentiator is the closed longitudinal loop:

`candidate tension → exact evidence tree → typed uncertainty → falsifiable hypothesis → executable test → verified artifact → append-only belief update or human handoff`.

Do not turn it into another chat/search dashboard. The product is a mind at work whose reasoning, failures, costs, and corrections are inspectable.

## 2. Read-first contract

Before changing code, read in this order:

1. `AGENTS.md` — scientific workflow and repository rules.
2. `Initial Planning Docs/BUILD_PLAN.md` — source of truth for architecture and sequenced build.
3. `docs/RESEARCH_QUALITY_PROGRAM.md` — frozen experiments, baselines, metrics, gates, and implementation sequence.
4. `docs/BUILD_NOTES.md` — append-only observations, failed assumptions, and reversals.
5. `results/FINDINGS.md` — only claims that have earned evidence.
6. `docs/SCIENTIFIC_WORKBENCH_SPEC.md` — minimal Focus / Map / Work / Review UI contract.
7. This file and `.agent-orchestration/HANDOFF.md`.

Use `token-smart-orchestration` for non-trivial work. Keep the main agent as planner/judge and delegate bounded scouting, implementation, and independent verification when capacity permits. The user explicitly requested persistent execution, real experiments, and living documentation.

## 3. Repository safety and ownership

- Workspace: `C:\Aryan\GitHub Projects\Persona` on Windows/PowerShell.
- Do not stage, commit, push, reset, or discard changes unless the user explicitly asks.
- The tree was already dirty. Treat untracked `AGENTS.md` and `persona/api/static/index_v6_backup.html` as user-owned. Preserve all pre-existing `persona/api/static/index.html` work and inspect overlap before editing.
- Use `apply_patch` for file edits. Preserve raw Curie records; corrections are append-only overlays.
- Never print or copy API keys. A key appeared in an old project log URL; do not repeat it.
- Figma mutation is blocked because the connector reports that the app connection requires reauthentication. Do not repeatedly retry. The code-native design contract is in `docs/SCIENTIFIC_WORKBENCH_SPEC.md`.

## 4. Current verified baseline

### Step 1 — trust-boundary and epistemic-integrity repair

- Runtime-generated self fields are type/shape/length validated in `persona/selfmind.py` and `persona/agents/deliberate.py`; malformed tool markers and string-as-list corruption cannot mutate the self.
- The original 315-character corrupted Curie question list remains quarantined byte-for-byte under `personas/curie-3c33/quarantine/`; the live list was restored to eight questions.
- Read-only topic endpoints no longer spend model budget; generation is explicit POST.
- Opposite signs are called `candidate_conflict / unverified`, never verified contradictions. The UI no longer presents sign labels as scientific “raises/lowers” conclusions on the repaired surfaces.
- Scheduler defaults changed from six workers to three, with restart-safe cooldowns and no immediate broad pulse.
- OpenAlex questions are sanitized rather than sent with wildcard punctuation.
- Remaining risk: configured hosted-model names are only defaults and must be probed against the live provider before any paid call. Never assume a name in `persona/config.py` exists.

### RQ-E01a — claim extraction integrity

- `persona/reading/extract.py` owns shared exact-schema and exact-span validation used by reader and batch paths; rejected objects are retained with reasons.
- Real Curie data: 5,704 extracted claims, 30 seeded resamples.
- Exact-span admission reduced non-verbatim evidence from 24.0% ±0.7% to zero while retaining 76.0%.
- A lexical polarity checker was explicitly rejected as an admission gate because it produced false positives.
- Artifacts: `experiments/exp_rq_e01_claim_integrity.py`, `results/rq_e01_claim_integrity.json`, `.png`.

### RQ-E07a — swarm physics

- Real-data replay through N=1,000 with 30 paired seeds.
- Central source partitioning peaked in useful efficiency at N=3. Effective team size saturated near 14–15 by N=100–1,000; dense all-to-all sharing was harmful.
- Production default workers changed 6 → 3. Scale breadth through explicit source partitions and a reducer; stop when marginal validated evidence is below cost.
- This does not prove live-model reasoning quality or sequential task performance.
- Artifacts: `experiments/exp_rq_e07a_swarm_physics.py`, `results/rq_e07a_swarm_physics.json`, `.png`.

### Evidence-first sessions and correction loop

- `persona/sessions.py` implements append-only `events.jsonl`, atomic `session.json`, content-addressed artifacts, RO-Crate 1.3 metadata, replay verification, append-only artifacts/verdicts, and CLI audit.
- `persona/agents/analyst.py` creates a real session for investigations; stores evidence, prompts/responses, tool calls, code, stdout/stderr, projects, cost and latency; and refuses established conclusions without valid evidence IDs or omitted task-required IDs.
- The first microglia/tau forward session was invalidated because generic retrieval omitted the triggering claims despite citations. The corrected contract pins required claim IDs.
- Corrected session `20260711T182050Z-do-the-opposite-stored-signs-for-microgl-8774b70a` verifies with 34 events, 20 hash-valid artifacts, 2/2 required claims, cost $0.226482, a reviewed figure, and scientific verdict `verified`.
- Bad claim `clm_9272dc679319` is preserved as `REJECTED_EXTRACTION`; its source-level correction is appended in `claim_corrections.jsonl`; active positive claim `clm_33711b72f30d` now has two DOI sources. Raw `claims.jsonl` is unchanged.
- Research UI/API lists and opens real sessions, separates trace integrity from scientific review, exposes claim/artifact links and figures, and keeps invalidated work visible.
- Browser artifacts: `results/ui_research_sessions.png`, `results/ui_research_session_detail.png`.

### Reusable skill forward test

- Skill: `C:\Users\aryan\.codex\skills\evidence-first-research-session`.
- `quick_validate.py` passed. Its verifier passes the real corrected session.
- Independent local-only forward bundle: `results/skill-forward-test/`; 14 ordered events, six hash-valid artifacts, 2/2 required claims, zero warnings, fresh scoped scientific verdict.
- It found another likely sign-label error for α-synuclein aggregation → ferroptosis, but correctly left wider literature unsupported and did not mutate the graph.

### RQ-E12a — LaTeX compiler integrity

- Reproduced severe old behavior: failed TeX could return success by reusing a stale PDF; filenames were shell-injectable; identical builds were nondeterministic; truncated slugs collided.
- `persona/tools/sandbox.py` now uses direct Docker arguments, validates filenames, clears stale outputs, requires two successful passes and a nonempty PDF, disables network, uses a read-only root and caps, freezes time variables, and returns source/PDF/environment hashes.
- `persona/deliverables/paper.py` uses unique run directories and source-hash-versioned outputs with compile manifests.
- Real Docker regression passed: valid read-only build; byte-identical fresh builds; broken recompile cannot reuse old PDF; unsafe filename rejected.
- Artifacts: `experiments/exp_rq_e12_latex_integrity.py`, `results/rq_e12_latex_integrity.json`, `.png`.

### Current automated checks

- `python -m pytest -q` most recently passed 20 tests.
- `python -m compileall -q persona experiments` passed.
- `git diff --check` has only LF/CRLF warnings, no whitespace errors.
- `tests/ui_research_smoke.cjs` passed against a local no-worker server and Chrome/Playwright.
- Integration audit additionally checked the new OpenAlex tool path, E07b/E10 artifacts, safe experiment `--help` handling, and active session replay. RQ-E10 is a deterministic frozen-evaluator harness only; no evolved policy is connected to runtime escalation.
- Active legacy sessions were compatibility-sealed with an exact event-log SHA-256; valid JSON edits now fail replay. This is workspace tamper evidence, not protection against a writer able to replace both the log and metadata.

### Integration-audit follow-ups that remain deliberately blocked

- `conflict_reviews.py` currently has a process-local lock. It is safe for the present single-process, empty-ledger pilot, but must gain a cross-process lock or single-writer service before two reviewers or horizontal API workers collect labels.
- `analyst.investigate` still needs a failure finalizer around its post-session work so an unexpected model/filesystem exception becomes an invalidated session rather than a permanently `running` one. Do not present it as crash-complete until that seam has a regression test.

## 5. RQ-E03a memory-retrieval experiment — complete

Purpose: structural evidence-record retrieval only. It does not evaluate biomedical truth, answer correctness, or real-user generalization.

Frozen ledger: exactly 200 auto-generated queries — 40 provenance, 30 temporal, 40 two-hop, 30 candidate-conflict, 30 field-note, 30 session-reconstruction. Every row has `base_item_id`; distinct bases are 40 / 18 / 40 / 30 / 23 / 2. Thirty seeded category-stratified base-cluster bootstraps use percentile intervals.

Arms: raw lexical scan, summary BM25, all-document BM25, local BGE dense vectors if operational, temporal graph, RRF hybrid. Metrics include Recall@5/10, evidence-set precision/F1@10, all-evidence@10, MRR@10, p95 query latency, retrieved-token estimate, and index write amplification. Query↔gold token containment/Jaccard is reported because synthetic queries retain lexical cues.

Important dense-embedding reversals:

1. Default FastEmbed full-corpus attempt was stopped after 229.45 wall-s, 3,073.56 CPU-s, 9,078,595,584 B parent working set, and no output.
2. A later probe appeared to use only ~84 MB, but that measured only the parent. `parallel=0` means automatic multiprocessing in FastEmbed 0.8.0; it spawned 22 Python children using roughly 0.6–1.2 GB each. The entire experiment-owned tree was stopped.
3. The script now uses `parallel=None`, `threads=2`, local-files-only, batch size 32, and a new cache fingerprint. A process-tree-aware 128-long-record probe had zero children, 1,328,390,144 B total RSS, and 4.34 records/s.
4. The bounded full dense run completed with `parallel=None`; never use `parallel=0`.

Final six-arm result: RRF Recall@10 0.891 and macro evidence F1@10 0.210; best single-arm F1 was 0.200, so the +0.010 hybrid gain failed the +0.050 deployment gate. Session recall was only ~0.524 and is a two-session diagnostic. Dense F1 was 0.182 with 2.373× estimated index writes. Mean query-token containment in gold is 0.604 (p95 0.867), so do not generalize these values to human questions.

Files: `experiments/exp_rq_e03a_memory_retrieval.py`, `results/rq_e03a_memory_retrieval.json`, and `.png`. The old `_embeddings.npz` was deliberately removed after E12b changed the corpus: it was a rebuildable pre-E12b cache whose fingerprint no longer matched the live snapshot. A future dense run may create a new cache, but the JSON result is the immutable record of this completed run.

Decision: reject dense/hybrid deployment and retain the simple retrieval path pending E03b human gold. Visual QA passed. A cache determinism rerun was deliberately stopped because creation of the E12b session changed the live Curie corpus and invalidated the snapshot fingerprint; do not compare rankings across snapshots.

## 6. RQ-E12b executable GEO session — complete

This is now the hackathon money-shot and a demonstration of self-correction. Session: `20260711T194501Z-does-a-prespecified-nrf2-associated-tran-08c6fd9b`; primary computation passed 20/20 clean numeric reruns. After independent review and append-only sensitivity it has 58 ordered events, 30 hash-valid artifacts, 2/2 canonical claims, zero model cost, zero replay errors/warnings, and latest scientific verdict `contested` while computation integrity remains verified. Events 56–58 are a redundant verifier/audit append caused by a handoff auditor probing the then-unsafe sensitivity CLI with `--help`; they are preserved, not treated as new scientific evidence. Both E12b scripts now implement real help parsing, and the sensitivity script refuses a repeat append unless `--allow-repeat` is explicit.

The canonical working session lives under git-ignored `personas/`. A portable full-session archive is therefore stored as `results/rq_e12b_geo_session_bundle.zip` (10,774,379 B; SHA-256 `f90263b1bbc65809ab06d62f2568ac0bbf42b8cdde187200b4bc508e937f42df`) with a standard `.sha256` sidecar. Verify the archive and then run `persona.sessions` against the extracted parent directory before treating a fresh clone as reproducible.

Two audit-created non-results are preserved outside active runs under `personas/curie-3c33/quarantine/incomplete-sessions/`: `...9a665916` is a terminated setup-only invocation, and `...d7c1ffd4` is an invalidated 0/20 run caused by the first misplaced CLI-guard patch. Neither may be loaded as scientific evidence or returned by Research/session retrieval.

Result: GSE1297 adjusted β `+0.1071`; GSE28146 β `+0.0619`. The frozen branch is `inconclusive`, so the predicted decline was not supported. Independent 10,000-draw/HC3 intervals include zero in both. Removing cross-hybridizing FTL probes reduces magnitude 47.6%/67.2% and leaves both intervals null-compatible. The original 30-draw output remains preserved, as do its classifier/figure limitations. Revised code fixes the positive-branch rule; appended gene scores, 40,000 sensitivity rows, residual/influence diagnostics, and adjusted figure are in-session. No positive, compensatory, or causal inference is supported.

### Preregistered hypothesis and branches

Primary proxy hypothesis: a prespecified seven-gene NRF2-associated expression score declines with Alzheimer’s severity in both cached preparations after age/sex adjustment.

- Negative, CI excluding zero in both datasets plus ≥6/7 leave-one-gene-out sign retention: symmetric decline branch.
- Positive, CI excluding zero in both: compensatory activation branch.
- Opposite reliable signs: tissue/context divergence branch.
- Otherwise: inconclusive branch.

The computation may be marked `TESTED`. It is transcriptomic association, not proof of oxidative damage, NRF2 activity, causality, disease modification, or ferroptosis. Keep those claims `INFERRED` or unsupported. Never auto-anchor the KG.

### Frozen local data

Project root: `personas/curie-3c33/projects/the-converged-belief-oxidative-stress-lowers-neu/`.

- `data/GSE1297_series_matrix.txt.gz`: 1,622,090 B; SHA-256 `7fe93d1e78ea1567625a066a267e28a62de2d421d517f3dd7a12576628d89009`.
- `data/GSE28146_series_matrix.txt.gz`: 3,858,604 B; SHA-256 `10416f47a2f531d344b07a366f11d5c1df83665e55b00c84588770caa4791a09`.
- `data/GPL96.annot.gz`: 4,522,748 B; SHA-256 `88e0b22362bac779eb220b3b185c80faa6510a92b9358eaad159a561ab4351c4`.
- Planner reported 31 GSE1297 samples, 30 GSE28146 samples, 30 matched donors, 22,277 shared probe IDs. Re-derive and assert every count; do not trust the report without checking raw headers.
- Frozen genes: `SLC7A11, GPX4, GCLC, HMOX1, FTH1, FTL, TFRC`; planner reported 13 measured probes. Derive mappings from GPL96 and assert the final mapping table.
- The two planner-provided IDs (`clm_6cdefce3d244`, `clm_b8eadf94d972`) are source-record IDs, not live canonical KG IDs; direct provenance lookup returns empty. The verified canonical required evidence IDs are `claim:clm_f4c5e47c1470` (NRF2 signaling regulates ferroptosis-pathway enzymes; one exact DOI source) and `claim:clm_cf8d869026bb` (oxidative stress contributes to AD progression; one exact DOI source). Pin these canonical IDs and preserve the source-record IDs inside the evidence packet for cross-reference.

### Frozen analysis

- Parse both GEO matrices and sample metadata from the compressed raw files.
- Normalize expression as `log2(x + 1)` only after inspecting raw ranges and confirming the matrices are not already log-scaled. If already log-scaled, follow evidence and record the preregistered reversal instead of double logging.
- Within each dataset: probe z-score across samples; median probes per gene; equal-weight mean across seven genes.
- Severity ordinal: Control=0, Incipient=1, Moderate=2, Severe=3. Assert labels and donor matching.
- OLS score ~ severity + age + sex. Store coefficient, standard error, sample count, rank/condition diagnostics, residual checks, and exact design columns.
- Original preregistration used 30 paired donor-bootstrap seeds; those intervals are retained only as diagnostic. Independent sensitivity now uses 10,000 paired draws plus HC3 and no-FTL checks. Paired resampling keeps each donor’s two preparations together.
- Leave one gene out seven times; record coefficient sign/stability.
- Primary figure must be reconstructed from a stored tidy table, not hidden in-memory objects.

### Executable and replay gates

- One new self-checking experiment: `experiments/exp_rq_e12b_geo_self_test.py` unless a smaller reuse of existing code is clearly possible.
- Use a new `ResearchSession`; cost must be exactly zero.
- Store raw input hash manifest, required-claim packets, preregistration, analysis source, container/image digest, stdout/stderr, tidy score table, summary JSON, bootstrap table, leave-one-out table, figure source and PNG, report/dossier, and verifier verdict as content-addressed artifacts.
- Run in offline Docker with data mounted read-only and a pristine writable work directory.
- Twenty pristine reruns; require at least 18/20 clean. Successful runs must reproduce summary JSON/CSV hashes exactly and numeric error exactly zero. Record every failure rather than deleting it.
- `verify_session` must return zero errors/warnings and 2/2 required evidence IDs cited.
- Browser smoke must open the latest `contested` session projection, keep trace integrity visibly passing, show the adjusted review figure and evidence chips, and contain an explicit “expression proxy, not causality” caveat.
- Do not mutate the KG. Produce a human dossier recommending the next discriminating biological/replication step.

### Existing project warning

The old project is incomplete and replay-labelled. `_run.py` only parses GSE1297 into pickles. It hardcodes line numbers and uses pandas; do not treat `results/expr.pkl` or `meta.pkl` as verified outputs. Preserve them for audit but build the clean test from the compressed raw inputs.

## 7. Prioritized continuation after RQ-E12b

1. **Candidate-review substrate is safe for a single-process pilot; build real multi-rater acquisition before collecting gold.** The existing inbox now shows why a pair was raised, both exact evidence packets, missing PICO/context fields, discriminating checks, and four non-mutating labels. `persona/conflict_reviews.py` stores a verified append-only hash chain; the API/UI never anchors. Browser smoke passes and no fake label was written. However, records do not yet carry reviewer identity, blinded assignment, or randomized-side-order metadata, and the lock is process-local rather than cross-process. Add those fields and an OS-level file lock (or single-writer service), test concurrent appends, freeze a blinded 20-case stratified bundle, then have at least two real reviewers label it independently, measure agreement, adjudicate disagreements, and only then run RQ-E02.
2. **RQ-E01b/E02 qualifiers and contradiction typing:** only after at least 20 blinded labels and inter-rater agreement. Compare sign collision, one verifier, and two independent verifiers plus exact-span gate. Require ≥0.85 precision before escalation; otherwise remain “candidate conflict.”
3. **RQ-E05 real retrieval:** use human-checked LitQA2/ScholarQA/AstaBench plus Persona questions. Evaluate iterative retrieval, reranking, citation traversal, and exact-span verification with correctness, citation precision/recall, abstention, primariness, cost, and latency.
4. **Evidence trees / RQ-E06:** atomic claims with qualifiers and explicit premise→inference edges. Target ≥50% reduction in unsupported synthesis and ≥10-point qualifier recall improvement.
5. **Scientific workbench UI:** preserve minimal navigation. Focus = living notebook and next decisions; Map = argument/evidence/trajectory graph; Work = sessions/code/data/figures/TeX; Review = human dossiers. Remove legacy synthetic metrics, ambient fake agents, and residual “raises/lowers” wording. Use browser checks on every visible slice.
6. **Executable papers / full RQ-E12:** session-to-LaTeX synthesis with exact claim citations, figure/data consistency, numeric reproduction, clean rerun, and AstaBench evaluation. Use the repaired deterministic compiler.
7. **Learning loops:** hosted Claude models cannot be customer weight-trained. Optimize prompts/tools/memory with immutable evaluators and keep/revert logs. Reserve SFT + GRPO/RLER for open-weight workers only after trajectories have reliable rewards. Never reward persuasive prose; use citation, format, execution, calibration, and human-outcome rewards separately.
8. **Large-team physics:** add equal-token live trials for parallel breadth vs sequential reasoning, hierarchical cells, DAG handoffs, reducer bottlenecks, correlated errors, and marginal evidence/cost stopping. Do not celebrate agent count; effective team size and validated novelty are the metrics.
9. **Membrane/belief storage:** keep raw folder/session logs as canonical provenance, graph as a rebuildable projection, and vectors as a rebuildable retrieval index. Test poisoning, duplicates, qualifier mismatches, retractions, correction latency, and anchor retention before expanding write autonomy.
10. **Figma:** after user reauthenticates, translate `docs/SCIENTIFIC_WORKBENCH_SPEC.md` into the existing/new Figma file using the already-read `figma-generate-design` + `figma-use` prerequisites. Do not block code-native UI work on Figma.

## 8. Verification commands and runtime recipe

Run from repository root:

```powershell
python -m pytest -q
python -m compileall -q persona experiments
git diff --check
python C:\Users\aryan\.codex\skills\evidence-first-research-session\scripts\verify_bundle.py results\skill-forward-test
python -c "from persona.conflict_reviews import verify_conflict_reviews; print(verify_conflict_reviews(r'personas/curie-3c33/.persona'))"
```

For UI smoke, launch with no autonomous workers. Do not run paid model work during browser tests. The desktop bundle contains Playwright but its package links require both module roots:

```powershell
$env:PERSONA_WORKERS='0'
python -m persona --port 8137
# In another PowerShell at the repository root:
$base='C:\Users\aryan\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$env:NODE_PATH="$base;$base\.pnpm\node_modules"
& 'C:\Users\aryan\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests\ui_research_smoke.cjs
```

Verify the exact server process and command line before stopping it. Do not kill a PID merely because an older note names it.

Do not probe historical copies of the E12b scripts with `--help`. Current source now has a safe help path, but the executed script preserved inside the session predates that repair. The sensitivity script targets the canonical session by ID and should never be rerun with `--allow-repeat` unless a new append-only replication is intentionally preregistered.

Session replay:

```powershell
python -m persona.sessions personas\curie-3c33\runs 20260711T182050Z-do-the-opposite-stored-signs-for-microgl-8774b70a
python -m persona.sessions personas\curie-3c33\runs 20260711T194501Z-does-a-prespecified-nrf2-associated-tran-08c6fd9b
```

Portable E12b replay:

```powershell
Get-FileHash results\rq_e12b_geo_session_bundle.zip -Algorithm SHA256
Expand-Archive results\rq_e12b_geo_session_bundle.zip results\rq_e12b_geo_session_bundle_unpacked
python -m persona.sessions results\rq_e12b_geo_session_bundle_unpacked 20260711T194501Z-does-a-prespecified-nrf2-associated-tran-08c6fd9b
```

Expected archive SHA-256 is `f90263b1bbc65809ab06d62f2568ac0bbf42b8cdde187200b4bc508e937f42df`; expected current replay is 58 events, 30 artifacts, 2/2 required claims, `$0`, and `contested`, with zero errors/warnings. Remove the unpacked verification directory only after resolving and confirming it is inside this workspace.

E03a attempts dense retrieval unless it is explicitly disabled. Use the safe five-arm mode by default:

```powershell
$env:PERSONA_E03A_SKIP_DENSE='1'
python experiments\exp_rq_e03a_memory_retrieval.py
```

For an intentional dense rerun, remove `PERSONA_E03A_SKIP_DENSE`, optionally set `PERSONA_E03A_DENSE_BATCH_SIZE='32'`, confirm the code still uses `parallel=None`, and monitor the whole process tree rather than only the parent. There is no `PERSONA_E03A_FORCE_DENSE` switch.
Any rerun operates on the then-live corpus and must receive a new snapshot hash; do not compare it as a deterministic repeat of the frozen pre-E12b result.

## 9. Current file map

Core changed files: `persona/selfmind.py`, `persona/agents/deliberate.py`, `persona/reading/extract.py`, `persona/reading/reader.py`, `persona/reading/batch.py`, `persona/memory/kg.py`, `persona/memory/membrane.py`, `persona/sessions.py`, `persona/agents/analyst.py`, `persona/conflict_reviews.py`, `persona/tools/sandbox.py`, `persona/deliverables/paper.py`, `persona/api/app.py`, `persona/api/static/index.html`, scheduler/config/ingest files, `tests/test_integrity_boundaries.py`, and `tests/ui_research_smoke.cjs`.

Living artifacts: `docs/RESEARCH_QUALITY_PROGRAM.md`, `docs/BUILD_NOTES.md`, `docs/SCIENTIFIC_WORKBENCH_SPEC.md`, this handoff, `.agent-orchestration/HANDOFF.md`, and `results/FINDINGS.md`.

Do not infer completion from the old “all build steps done” paragraph in `.agent-orchestration/HANDOFF.md`; that refers to the earlier demo plan. The research-quality program is the active contract.

## 10. Claims the next agent must not make

- Do not say Persona has solved contradiction detection. It has a safe candidate-review substrate; RQ-E02 still needs blinded human labels and measured precision.
- Do not say dense or hybrid memory is better. The only completed structural benchmark failed its deployment gate, and its session slice had only two sessions.
- Do not say the GEO result validates the biological hypothesis. It is `inconclusive`, same-donor, transcriptomic, FTL-sensitive, and scientifically `contested` despite verified computation.
- Do not say figures are fully deterministic. The LaTeX compiler is byte-deterministic in E12a, but the original E12b matplotlib PNG did not reproduce byte-for-byte.
- Do not say Persona has been pretrained or RL-trained. Hosted Claude weights are not customer-trainable here; open-weight SFT/GRPO/RLER remains a future program gated on trustworthy trajectory rewards.
- Do not say the application is fully redesigned. The Research session and conflict-dossier slices are real; the broader Focus / Map / Work / Review migration and legacy-surface removal remain open.
- Do not run autonomous paid agents merely to demonstrate motion. Default browser verification uses `PERSONA_WORKERS=0`, and any paid model call requires a live model-name/cost probe plus explicit experimental purpose.

## 11. Best next bounded implementation slice

Build the missing multi-rater acquisition layer, then acquire a real blinded conflict gold set without contaminating the graph. Add pseudonymous reviewer IDs, assignment/batch IDs, fixed randomized side order, duplicate-review prevention per reviewer/conflict/batch, a single-writer or cross-process file lock, and a blinded export whose hashes are frozen before collection. Test concurrent appends and tamper refusal. Freeze 20 stratified candidate pairs; collect two independent human labels; verify the ledger hash chain; compute agreement and an adjudicated gold file; then run sign-collision vs one-verifier vs two-verifier-plus-exact-span under the RQ-E02 gate. The deliverable is not a nicer contradiction badge. It is a measured answer to whether Persona can escalate candidate conflicts at at least 0.85 precision while preserving false-negative and abstention visibility. If no real reviewers are available, stop after producing the blinded acquisition bundle and UI workflow--never synthesize labels.

## 12. Definition of genuinely finished

Persona is not finished when pages render or agents emit prose. It is finished for the hackathon slice when a skeptical reviewer can replay at least one complete public-data question from pinned evidence and immutable raw data through code, numeric results, figure, report, independent verification, and an honest next-human action; when a malformed model response cannot corrupt memory; when candidate conflicts remain unverified until exact evidence and context pass a measured gate; and when the UI exposes those facts without invented activity or scientific authority.
