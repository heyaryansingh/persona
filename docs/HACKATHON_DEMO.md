# Persona - three-minute demo

## Before the room

Start the existing, cached Curie workspace with all autonomous workers disabled. This demo is read-only: do not submit a review or start an investigation on the shared workspace.

```powershell
$env:PERSONA_WORKERS='0'
$env:PERSONA_START_SCHEDULER='0'
python -m persona --port 8137
```

Open `http://127.0.0.1:8137`, select **Curie**, then follow this sequence.

| Time | Screen | Say |
|---|---|---|
| 0:00 | Focus | "Biomedical teams can find papers but cannot easily tell what is exact, independent, contested, or worth the next experiment. Persona is a persistent researcher, not a chat box: a durable self directs bounded readers, while only provenance-backed evidence can change its belief state." |
| 0:30 | Focus notebook | "This is the researcher's legible memory: interests, recent moves, and the evidence trail that made each move. It keeps uncertainty separate from a conclusion instead of hiding it in a fluent summary." |
| 0:50 | Map -> Field | "This server-computed queue is useful because it ranks a discriminating next action by expected value and feasibility. It is advisory: it does not invent a scientific conclusion." |
| 1:10 | Work -> Research -> **Matched-donor GEO self-test** | "Here is the closed loop: a literature tension becomes a falsifiable question, a public GEO reanalysis, replayable code and artifacts, then an auditable conclusion. This result is an expression proxy, not causal biology." |
| 1:55 | Review -> open an evidence dossier | "Opposite signs are a candidate conflict, not a refutation. Persona puts both exact evidence packets, missing qualifiers, provenance, cost, and the next discriminating check in one dossier." |
| 2:25 | Human-review form | "A reviewer can record a scoped judgment. No unreviewed model output can anchor a belief; the system preserves the disagreement and asks for the judgment it cannot honestly make." |
| 2:45 | Focus | "That is the novelty: not retrieval or summarization, but an acting loop plus a persistent, auditable self: tension to test to replayable artifact to human judgment. Persona helps a lab decide what to investigate next without overstating what the evidence proves." |

## Claims to avoid

- Do not call the GEO result causal, a biological discovery, or a verified contradiction.
- Do not call a candidate conflict a refutation.
- Do not imply autonomous workers are enabled during the demo.
- Do not submit mutations against the shared Curie workspace.

## Smoke check

Run before recording or presenting:

```powershell
$base='C:\Users\aryan\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$env:NODE_PATH="$base;$base\.pnpm\node_modules"
& 'C:\Users\aryan\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests\ui_research_smoke.cjs
```

The smoke verifies the session trace, review-adjusted GEO artifact, explicit non-causality language, and the exact-evidence conflict dossier.

## Recording checklist

- Record this cached replay, not a paid or autonomous run.
- Keep browser zoom at 100%; use the labelled tabs above rather than searching.
- If a session takes longer than a few seconds to render, retry the page; do not improvise scientific claims.
- End on Focus and the sentence at 2:45. It states the problem, usefulness, novelty, and safety philosophy in one honest close.
