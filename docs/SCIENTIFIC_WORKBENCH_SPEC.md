# Persona Scientific Workbench

Status: implementation/Figma specification, grounded in the 2026-07-11 live audit and corrected research-session forward test.

## Product rule

Persona is not a dashboard of agent activity. It is a legible research state: what question is active, what exact evidence supports each conclusion, what remains contested, what computation ran, what changed, and which next action has the highest expected information value.

Every visible scientific status comes from the server. The client may sort and filter; it may not invent convergence, contradiction truth, load-bearing importance, value of information, or confidence.

## Four destinations

The current six destinations collapse into four questions a researcher actually asks:

1. **Focus — what is Persona doing and why?**
   - active research question and compact public notebook;
   - next action, its reason, expected evidence gain, cost ceiling, and stop rule;
   - real state changes only: evidence retrieved, claim proposed/rejected, code run, result produced, belief updated, human needed;
   - orchestration telemetry lives in a collapsed diagnostics drawer.
2. **Map — what does the field rest on and how is it changing?**
   - claim/evidence dependency graph;
   - time scrubber changes claim validity/confidence, not merely ingestion order;
   - true refutations, contextual divergence, insufficient evidence, and extraction errors have distinct reviewed states;
   - one source is `observed`, independent support is `corroborated`, executable confirmation is `tested`, explicit human judgment is `anchored`.
3. **Work — what research can I inspect or continue?**
   - research threads/sessions first, then reports, figures, code, data, LaTeX/PDF, and projects;
   - every conclusion opens its evidence tree;
   - trace-integrity status is separate from scientific-review status;
   - failed and invalidated sessions remain visible and explain the failure;
   - code, environment, inputs, stdout/stderr, artifacts, hashes, costs, and verifier verdict are replayable.
4. **Review — what needs judgment or another experiment?**
   - human-resolution dossiers, not binary raises/lowers prompts;
   - candidate conflicts with exact spans, qualifiers, source independence, and current classification;
   - cheapest discriminating search/computation/wet-lab experiment;
   - expected belief changes for each possible result;
   - explicit `defer`, `request missing context`, `contest`, and `confirm` actions.

One global question/command bar remains available across destinations. `Ask` is read-only by default. `Investigate`, `Build`, and `Publish` show their intended model/tool budget before starting.

## Desktop workbench frame

Target: 1440 × 960, calm editorial dark theme.

```text
┌ Persona / researcher ─ Focus  Map  Work  Review ─ budget / run state ┐
├ threads / field map ┬ active argument and evidence ┬ inspector       ┤
│ saved questions     │ question + contract           │ exact source    │
│ active sessions     │ strongest conclusion          │ qualifiers      │
│ field communities   │ evidence tree                 │ provenance      │
│ unresolved loops    │ counterevidence / test        │ artifact/code   │
│                     │ next action + stop rule        │ human dossier   │
├─────────────────────┴───────────────────────────────┴─────────────────┤
│ expandable notebook · code / stdout · orchestration diagnostics       │
└───────────────────────────────────────────────────────────────────────┘
```

The side panes collapse independently. The center remains usable at 900 px. Below 760 px, panes become a single stack with a persistent segmented control; no fixed-width overflow.

## Work/session anatomy

### Session list

Each keyboard-operable card shows:

- question or reviewed title;
- `running`, `completed`, `failed`, or `invalidated` execution state;
- separate `unverified`, `verified`, `contested`, or `invalidated` scientific review;
- conclusions, content-addressed artifacts, required claims, duration, and cost;
- one sentence explaining why a session failed or changed state.

List responses are paginated summaries. Opening one session fetches the complete trace. Hash verification is explicit, never polled.

### Session detail

Order is fixed:

1. question and frozen task contract;
2. scientific-review verdict and scope;
3. trace-integrity result with a warning that lineage is not truth;
4. required evidence packet;
5. conclusions, each with status, calibrated confidence, and evidence IDs;
6. primary figure/table where present;
7. content-addressed artifacts and source paths;
8. compact public chronology;
9. raw public model/tool payloads in a collapsed disclosure.

`claim:*` opens exact provenance. `artifact:*` opens the hash-addressed file. Unknown IDs render as unresolved errors. Duplicate filenames never identify artifacts.

## Evidence tree

```text
Question
└─ Conclusion [SUPPORTED | INFERRED | UNSUPPORTED_HYPOTHESIS]
   ├─ Claim [observed | corroborated | tested | anchored | rejected]
   │  ├─ Exact span + locator
   │  ├─ Source metadata + source hash
   │  └─ Population / intervention / outcome / conditions
   ├─ Computation
   │  ├─ code + environment digest
   │  ├─ input dataset hashes
   │  └─ stdout/stderr + result hashes
   └─ Verifier verdict
```

Edges are typed `supports`, `refutes`, `qualifies`, `replicates`, `extends`, or `derived_from`. A sign collision is a candidate set until its exact spans and qualifiers are reviewed. Corrections retire active projections but never delete source records or prior nodes.

## Human-resolution dossier

Every dossier must answer:

- What exact decision is being requested?
- Why can Persona not resolve it from public evidence/computation?
- Which claims and sources disagree, and are their qualifiers compatible?
- Is this likely refutation, context divergence, insufficient evidence, or extraction error?
- What is the cheapest discriminating next action?
- What would Persona update under each possible result?
- What is the uncertainty, cost, elapsed time, and authority boundary?

No direct anchor control appears until contradiction precision passes RQ-E02 and the user supplies a rationale.

## Visual language

- Background `#07080B`; panels `#0E1015`; structural borders `#22262F`.
- Body text must meet WCAG AA; do not reuse the current `--faint` color for essential 9–11 px text.
- Monospace: public notebook, IDs, code, metrics, provenance.
- Serif: questions, synthesized conclusions, reports.
- Green: live/tested/verified; amber: needs human; red: rejected/invalidated; blue-violet: anchored; yellow: observed/read; gray-violet: inferred.
- Color never carries state alone: pair every accent with text and/or shape.
- Motion occurs only on state change and honors reduced-motion preferences.

## Figma construction plan

Create one design file, `Persona Epistemic Research Workbench`, with:

1. `00 Foundations`: imported/reconciled color, type, spacing, radius, and state tokens;
2. `01 Desktop`: Focus, Map, Work list, Work session, Review dossier;
3. `02 Responsive`: 760 px and 390 px Work/session states;
4. `03 State matrix`: running, completed/unverified, verified, contested, invalidated, empty, loading, offline;
5. `04 Prototype`: thread → session → conclusion → claim/source → artifact, plus candidate conflict → dossier.

Before building, search the target file/libraries for components, variables, and styles; reuse compatible assets. The current app is plain HTML/CSS with no Code Connect library, so code variables in `:root` are the source tokens unless the Figma file contains an authoritative system. Build with auto-layout; return every created node ID; verify screenshots after each major frame.

## Acceptance checks

- A new researcher can identify the active question, strongest conclusion, strongest counterevidence, and next action in under 30 seconds.
- A reviewer reaches an exact source span from a conclusion in at most two actions.
- A failed session cannot visually resemble verified work.
- Trace integrity and scientific truth are never represented by one badge.
- No client-created metric is presented as scientific fact.
- Keyboard users can open cards, evidence, artifacts, disclosures, and close/return from dialogs.
- Desktop, tablet, and mobile states have no horizontal overflow.
- Browser smoke covers thread → session → evidence → artifact and candidate → dossier flows.

## Current implementation bridge

The first Work slice is live in `persona/api/static/index.html`: the existing Studios destination is renamed Research, real sessions lead the surface, the invalidated and verified runs are visibly distinct, and the corrected session exposes required evidence, conclusions, primary figure, artifacts, and chronology. The remaining four-destination shell is intentionally deferred until browser tests and the memory/conflict experiments determine which Map and Review objects are scientifically valid.
