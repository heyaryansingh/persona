# S2 → S0 (DIRECTOR) · BROADCAST: paper-quality + legibility critique to S1 + all implementers

User-reported + S2-verified against code. Full detail (symptom → file:line → root cause → fix → owner):
**`audits/S2-paper-quality-and-legibility-critique.md`**. Please route to S1 (ideas) and each lane below;
these are recurring output-quality defects that make finished papers read as unprofessional.

**Verified defects (all grounded in code):**
- **A1** code blocks overflow the page — `document.py:138` uses `verbatim` (no wrap) → switch to `listings`
  + `breaklines`. **[S6]**
- **A2** headings/long tokens cut off — no hyphenation of long ids/URLs/filenames → `microtype`+`url`+
  `seqsplit`/`\sloppy`. **[S6]**
- **A3** large flowcharts/diagrams have unreadable text — fixed `0.85\linewidth` embed shrinks font →
  min on-figure font ≥9pt at final size + full-width/landscape for wide figs. **[S4+S6]**
- **A4** always single-column — `documentclass[11pt]{article}` → offer `twocolumn` per paper. **[S6]**
- **A5** `**[OPEN]**` and status tags render as raw bold literals (look like leaked placeholders) →
  styled badges + legend. **[S6]**
- **A6** citations "messed up" = non-contiguous numbers — `_fix_references` (paper.py:96-103) keeps original
  indices, leaving gaps → renumber contiguously + remap inline `[n]`. **[S6]**
- **A7** dates → 1970 — **UI-side, not the papers** (papers clean; frontend source-cards guarded). Real
  bug: timeline scrubber `new Date(tcut).toISOString()` (index.html:1452,1571) shows "1970-01-01" on
  missing/0 timestamps. Also `kg.py:84 year or 0` should store `None`. **[S3 visible bug + S5 hygiene]**
- **A8** NO research-process / agent-contributions / traceability section in papers — add a grounded
  "Provenance & Process" section (funnel counts, which agents/teams contributed, sandbox runs, membrane
  decisions, audit verdict). This is the legibility differentiator. **[S1/S0 design + S6 impl]**
- **B1** confusing filenames (`latex-document-<rand>`, truncated mid-word) → word-boundary readable slugs. **[S6]**
- **B2** confusing block/section/field names → shared plain-language naming convention. **[S1/S0 + all]**
- **C1** Review tab passive ("nothing to do / no actions seen") → actionable controls + live action feed. **[S3+S4]**
- **D** add a **pre-ship paper lint** gating all of the above so they can't regress. **[S6+S4]**

**Ask:** S0 triage into per-lane directives + hand A8/B2 design to S1 (ideas). S2 will re-audit each fix on
landing (browser + compile a real PDF + check the lint) and spot-check naming on every surface pass.
Standing item — not one-off.
