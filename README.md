# Persona

Persona is a persistent synthetic researcher for scientific work: disposable agents read and test, while a small durable self preserves only typed, evidence-linked state. Its core loop is:

`candidate conflict -> exact evidence -> falsifiable question -> executable test -> replayable artifact -> human review or bounded belief update`

The product is deliberately not a chat/search dashboard. It exposes the evidence, code, outputs, uncertainty, and corrections behind each conclusion.

## What is working now

- Exact-span claim admission and correction overlays prevent non-verbatim evidence from entering active claims.
- A content-addressed research-session substrate records code, artifacts, evidence IDs, costs, and a tamper-evident event-log digest.
- Research UI surfaces show session trace integrity separately from scientific-review status.
- Candidate conflicts open exact-evidence dossiers and write non-mutating human-review records; direct anchoring remains disabled pending human-gold RQ-E02.
- One cached public-data GEO analysis is replayable offline (20/20 core numeric reruns) and honestly marked `contested`/`inconclusive` after sensitivity review.
- The app has a domain-general OpenAlex literature tool alongside biomedical tools.

## Verified evidence and limits

- `RQ-E01a`: exact-span validation removed non-verbatim evidence in the Curie replay while retaining 76% of claims.
- `RQ-E03a`: dense/hybrid retrieval did **not** meet its deployment gate; simple retrieval remains the production path.
- `RQ-E07a/b`: source partitioning and selective verification won in replay; this is not evidence that huge live-agent teams reason better.
- `RQ-E10`: a frozen-evaluator policy-optimization harness passes, but its exact-span proxy is not human contradiction gold and no learned policy is wired into runtime.
- `RQ-E12b`: transcriptomic result is same-donor, FTL-sensitive, and not causal; it must not be called a biological discovery.

Read [the active continuation contract](docs/CONTINUATION_HANDOFF.md), [research-quality program](docs/RESEARCH_QUALITY_PROGRAM.md), and [findings](results/FINDINGS.md) before extending the system.

## Run and verify

```powershell
python -m pytest -q
python -m compileall -q persona experiments
$env:PERSONA_WORKERS='0'
python -m persona --port 8137
```

The normal capped default is three workers. For an explicitly uncapped BYOK run, set
`PERSONA_UNLIMITED_SPEND=1`; it uses eight workers unless `PERSONA_WORKERS` is set.
An explicit `PERSONA_DAILY_BUDGET_USD` always keeps the run capped.

For the browser smoke, use the bundled runtime as documented in [the handoff](docs/CONTINUATION_HANDOFF.md#8-verification-commands-and-runtime-recipe). The smoke launches no autonomous workers and makes no paid model calls.

## Safety boundary

Candidate sign collisions are not verified contradictions. A result can be computationally replayable and still be scientifically contested. Persona keeps those states separate, preserves rejected/invalidated work for audit, and routes biological or methodological judgment to humans.

## Hackathon handoff

The three-minute cached demo is in [docs/HACKATHON_DEMO.md](docs/HACKATHON_DEMO.md).
Use [docs/HACKATHON_SUBMISSION.md](docs/HACKATHON_SUBMISSION.md) for the written pitch and
[docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) for the local and public-launch gates.
