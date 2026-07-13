# Persona — submission copy

## One-line pitch

Persona is a persistent synthetic researcher that turns a literature tension into an auditable public-data test, while keeping human judgment—not model confidence—as the authority for belief anchors.

## Problem

Biomedical teams can retrieve papers, but still struggle to see which claims are exact, independent, contested, computationally testable, or worth a human’s scarce experimental attention. A fluent summary hides those distinctions and makes unsupported certainty easy.

## What we built

- A durable researcher self—interests, notebook, beliefs, strategies, budget, and provenance—not a stateless chat session.
- A disposable reading swarm whose outputs enter through exact-span, provenance, independence, calibration, and human-gate boundaries.
- A closed acting loop: candidate conflict → falsifiable question → public GEO dataset → replayable analysis/code/artifacts → review-aware conclusion.
- Evidence dossiers that place competing exact packets, missing qualifiers, and discriminating checks in front of an independent human reviewer.
- A legibility layer: Focus notebook, Map/Field value queue, Work session artifacts, and Review inbox.

## Why it is novel

Existing literature tools mainly retrieve, classify citations, or summarize. Persona’s contribution is the **acting loop plus persistent self**: it preserves what a researcher believes and why, tries a bounded computational test when possible, and records what remains unresolved instead of converting it into an answer.

## Research-quality philosophy

- Evidence is not belief: all claims carry provenance and exact source spans.
- A computational result is not a biological or causal conclusion.
- A sign collision is a candidate conflict, not a refutation.
- Human-confirmed anchors resist swarm overwrite; unreviewed model output cannot create them.
- Every session has a replayable event trace and content-addressed artifacts.
- The system exposes abstention and uncertainty rather than turning them into dashboard theater.

## Demo proof points

The included three-minute demo shows the replayable matched-donor GEO session, its explicit non-causality caveat, the exact-evidence conflict dossier, and the human review boundary. Run [HACKATHON_DEMO.md](HACKATHON_DEMO.md) before recording.

## Technical proof

`350` Python tests, frontend renderer checks, a no-worker browser smoke, Compose validation, and a built `persona:0.3.0` image cover the local submission artifact. Production OAuth, DNS/TLS, and provider credentials remain deliberately external launch gates.
