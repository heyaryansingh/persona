# S2 CRITIQUE — paper/PDF quality, legibility, naming, interaction (2026-07-13)

> **For the DIRECTOR (S0), the IDEAS agents (S1), and ALL implementers (S3/S4/S5/S6).** User-reported,
> S2-verified against code. Each item: symptom → evidence (file:line) → root cause → fix → owner.
> These are recurring output-quality defects that make finished papers read as unprofessional. Treat as a
> standing quality bar, not a one-off — add the pre-ship lint (§D) so they can't regress.

## A. LaTeX / PDF paper quality

### A1 — Code blocks run off the page (unstyled, no wrap) · **[S6 deliverables/document.py]**
Symptom: code blocks aren't professionally styled and overflow the right margin.
Evidence: `md_to_latex` emits `\begin{verbatim}` … `\end{verbatim}` (document.py:138-143, 172); `verbatim`
does **not** wrap long lines → they overflow/clip. Template loads no code package (document.py:17-27).
Fix: use `listings` — add `\usepackage{listings}\usepackage{xcolor}` + a `\lstset{basicstyle=\small\ttfamily,
breaklines=true, breakatwhitespace=false, columns=fullflexible, frame=single, backgroundcolor=\color{gray!8},
keepspaces=true, showstringspaces=false}`; render fences as `\begin{lstlisting}` (with `language=` when known).
Keeps offline compile (listings is in texlive-base). Add a lint: no source line in a code block may exceed
the text width once broken.

### A2 — Titles / headings / long tokens cut off · **[S6 document.py]**
Symptom: titles and headings clipped at the margin.
Evidence: headings `\section*{…}` (document.py:149-150) and inline `\texttt{}` (line 101) don't hyphenate
long unbreakable tokens (URLs, `long_snake_case_ids`, filenames) → overflow. 1-inch margins + `parskip`.
Fix: add `\usepackage{microtype}`, `\usepackage[hyphens]{url}`, and allow breaking in `\texttt` /headings
(`\usepackage{seqsplit}` for long ids, or a global `\sloppy` + `\emergencystretch=3em`). Wrap long inline
code with `\allowbreak`. Directly tied to B1 (long ugly filenames appearing in headings).

### A3 — Diagrams / large flowcharts: text too small to read · **[S4 figure-gen + S6 embed]**
Symptom: big flowcharts/diagrams have unreadably small text.
Evidence: every image embeds at a fixed `width=0.85\linewidth` (document.py:105) — a large/wide flowchart
scaled to 0.85·(6.5in) shrinks its internal text below legibility. No full-width/landscape/rotate path.
Fix: (a) generators (matplotlib/graphviz) must render with a **minimum on-figure font size** (≥9pt at final
size) and target the final print width, not a huge canvas; (b) embed large/wide figures full text-width or
in a `figure*`/`\rotatebox`/`landscape` for very wide ones; (c) cap aspect so a tall figure doesn't force
tiny width. Add a lint: warn if a figure's pixel width ÷ embed width implies effective font < ~8pt.

### A4 — Always single-column · **[S6 document.py]**
Evidence: `\documentclass[11pt]{article}` (document.py:18) — never `twocolumn`.
Fix: parameterize the class options; pick 2-column for dense empirical papers (heuristic: has ≥N figures /
is a "paper" deliverable), keep 1-column for math derivations with wide display equations. Expose a
`layout: one|two` field on the deliverable request so the ideas/director layer can choose per paper.

### A5 — `[OPEN]` (and status tags) render as raw bold literals · **[S6 paper.py + document.py]**
Symptom: "random **[OPEN]** in bold and other messages" scattered in the text.
Evidence: paper.py:44 defines the claim-status vocabulary rendered inline as `**[OPEN]**` (also PROVED/
machine-checked tags). To a reader these read as leaked placeholders, not typesetting.
Fix: render status as a **styled label** — a small colored badge / `\fbox`/`\colorbox` or smallcaps
`\textsc{}` with a color key, defined once and explained in a legend — instead of raw bracketed bold.
Ensure no bare `[OPEN]`/`[TODO]`/`[TESTED]`-style tokens survive into prose without the styled treatment.
Add a lint: flag any `**[A-Z]+**` literal remaining in the compiled body.

### A6 — Citations messed up (non-contiguous numbers) · **[S6 paper.py]**
Evidence: `_fix_references` (paper.py:92-103) keeps only cited refs but **preserves original indices**:
`enumerate(sources,1) if i in valid` → the reference list shows gaps (e.g. `2.`, `5.`, `7.`) while dropping
1,3,4,6. Inline `[n]` are kept at their old numbers. A reader sees `[5]` with a refs list that skips 1,3,4.
Fix: renumber **contiguously** — build `old→new` map over the cited set in first-appearance order, rewrite
every inline `[old]`→`[new]`, and emit `1..k` with no gaps. Add a test: every inline cite resolves and the
reference list is exactly `1..k` contiguous.

### A7 — Dates show 1970 (primarily in the UI, NOT the papers) · **[S3 frontend + S5 kg.py]**
Scope corrected after checking real output: compiled papers are basically clean (1 "1970" across all
shipped .tex, and it's a *legitimate* historical mention — "Hilbert's Tenth Problem settled in 1970"). The
frontend source-cards are also guarded (`${s.year||''}`, `${d.year?…}` at index.html:1406,1940,2034 → year=0
shows blank, not 1970). **The real 1970 locus is the timeline scrubber:** `new Date(GX.tcut).toISOString()
.slice(0,10)` (index.html:1452 gxScrub, 1571 evScrub) renders **"1970-01-01"** when the graph's
min/max timestamps are missing/zero (`new Date(0/NaN)`). Contributing data-hygiene cause: `kg.py:84`
`"year": meta.get("year") or 0` stores 0 for missing years (should be `None`).
Fix: (a) in the timeline scrubbers, guard `new Date(t)` — show "live"/"—" (not 1970) when `tcut`/`tmin`/`tmax`
is 0/NaN/absent; (b) store missing year as `None`, never 0 (kg.py); (c) any date formatter shows "n.d." for
missing. **[S3 owns the visible bug; S5 owns the year=0 hygiene.]**

### A8 — No documentation of the research process / agent contributions / traceability · **[S6 paper.py template + S1/S4 design]**
Symptom: papers never record how they were produced — which agent teams worked on it, their contributions,
the reading funnel, or a traceable chain from evidence to claim.
Evidence: paper.py section list (paper.py:44-63) = Main result / Intro / Methods / Results / Reasoning chain /
Discussion / References. No provenance/process/contributions section.
Fix: add a **"Provenance & Process"** section (or a structured appendix) auto-populated from real run data:
the swarm funnel (N works read → N admitted / N rejected by the membrane, with why), which agents/teams ran
(director → readers → extractor → membrane → synth → auditor) and their contribution, sources admitted vs
quarantined, computations run in the sandbox + what they checked, and the robustness-audit verdict. This is
the legibility differentiator — "scale of reading, discipline of believing" — and must be grounded in
logged events, not model prose. IDEAS/DIRECTOR: design the exact schema; it should be reproducible + audit-able.

## B. Legibility & naming

### B1 — Confusing deliverable filenames · **[S6 paper.py `_slug` / document.py `slug_for`]**
Symptom: names like `latex-document-4916814452.pdf`, `derivation-…-erd-s-straus-conje-e7010ab7.pdf`
(truncated mid-word, opaque hash, generic "latex-document").
Evidence: `slug_for` truncates to 48 chars mid-word (document.py:220-221); `_slug` to 50 (paper.py); run_id
appends `uuid4().hex[:8]`.
Fix: human-readable names — truncate on a **word boundary**, drop the generic `latex-document-<rand>` prefix
(use the title), use a short ISO date instead of a raw uuid, and keep a readable ≤~60-char slug
(`erdos-straus-conjecture-on-4-n-2026-07-13.pdf`). Never cut mid-word ("conje", "erd-s").

### B2 — Confusing block / section / field names & info · **[ALL lanes]**
Symptom: block names, labels, and info fields don't read clearly / don't make sense.
Fix: a shared naming convention — sections and UI labels in plain language; no internal codenames or
truncated tokens surfaced to the user; every user-facing field says what it is. IDEAS/DIRECTOR: publish the
convention; each lane conforms. (S2 will spot-check on every surface pass.)

## C. Interaction

### C1 — Review tab is passive: nothing to do, no actions seen being taken · **[S3 + S4]**
Symptom (user): "never anything to do or actions to take or seen being taken on the Review tab."
Evidence: the Review/"Instruments" surface is read-only panels (epistemic status, triage heuristics,
candidate-conflict inbox) — all display, no controls, and no live action feed.
Fix: make it actionable + live — per candidate-conflict: **buttons** (open evidence dossier, request human
review, mark label, launch investigation, escalate); show a **live action feed** of what the engine is
doing/decided (admitted X, flagged Y, queued test Z) so the user *sees* actions being taken; surface the
value-queue "highest-leverage next experiment" as a clickable item. (Anchoring stays gated per RQ-E02, but
the *review workflow* — label/dossier/investigate — is already wired and should be exposed.)

## D. Process — make paper checking SOUND (a pre-ship gate) · **[S6 + S4]**
Add a **pre-ship paper lint** that blocks/flags before a PDF is called done, covering exactly these classes:
1. no code line overflows text width (A1), 2. no heading/token overflow (A2), 3. every figure's effective
font ≥ ~8pt (A3), 4. no raw `**[A-Z]+**` status literal in the body (A5), 5. citations contiguous + every
`[n]` resolves (A6), 6. no `1970`/`(0)` dates (A7), 7. Provenance section present + grounded (A8), 8.
filename is word-boundary readable (B1). Run the existing robustness auditor on the paper's own claims too.
Wire it into the compile path so a failing paper never ships silently.

---
**Owners at a glance:** A1,A2,A4,A5,A6,A8,B1,D → **S6** (deliverables). A3 → **S4** (figure-gen) + S6.
A7 → **S5** (kg year) + S3 (frontend dates) + S6. C1 → **S3** + S4. B2, design of A8/B2 → **S1/S0**.
Broadcast filed: `requests/S2--to--S0--paper-quality-broadcast.md`.
