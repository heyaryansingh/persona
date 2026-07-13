# S0 → review — independently verify Paper-quality M0 (coordinator-workflow code)

Built by workflow `wpmntkc2i`, not a terminal → same review gate before commit-ready counts.

**Files ($0, deterministic):**
- `persona/deliverables/document.py` — A1 listings code-wrap, A2 microtype/`[hyphens]{url}`/`\sloppy\emergencystretch`, A3 full-width/landscape figures (+ stdlib PNG/JPEG size parse), A4 `layout` one|two|auto. Refactored a pure `render_latex`.
- `persona/deliverables/paper.py` — A5 styled status badges (`\colorbox`+`\textsc`+legend), A6 contiguous citation renumber (first-appearance map), B1 word-boundary + ISO-date filenames.
- `persona/deliverables/paper_lint.py` (new) — pre-ship `lint_paper()` (A1/A2/A5/A6/A7/B1; A3/A8 best-effort).
- Tests: `tests/test_deliv_{document_quality,paper_quality,paper_lint}.py` (26 pass self-reported).

**Check specifically:** (1) offline texlive-base compile still works — actually compile a sample paper end-to-end in Docker if feasible (listings/microtype/url/xcolor all base; `url` before `hyperref`); (2) the A5 badge survives `md_to_latex`'s escaper and renders in text mode; (3) A6 renumbering never breaks an inline `[n]` (every cite resolves, 1..k contiguous); (4) B1 filenames can't collide-silently (two same-topic same-day papers share a name — hash still in the receipt; acceptable?); (5) the lint's A6 contiguity is now consistent with `paper.py`'s new renumbering (agent flagged it was stricter than the OLD pipeline). **Note: lint is NOT yet wired into the compile path (imp4 follow-up).** File `audits/review-paper-quality-m0.md`.
