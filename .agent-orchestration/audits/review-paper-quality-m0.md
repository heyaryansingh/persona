# S2 REVIEW — Paper-quality M0, 2026-07-13

Requested by `S0--to--review--verify-paper-quality-m0.md` (workflow `wpmntkc2i`). Most already verified
across my prior re-audit — full detail in `audits/S2-reaudit-paper-fixes.md`. Consolidated verdict here.

## Verdict: PASS (I caught + verified the fix of the one regression it had). 38 paper/lint/compile tests green.

- **Check #1 — offline compile still works → VERIFIED (real Docker).** I actually compiled sample docs
  end-to-end. Note: this pipeline SHIPPED a break I caught — **PQ-REG-1: `microtype` (default expansion)
  aborts every compile** ("auto expansion only w/ scalable fonts"). Fixed to `[expansion=false]`;
  re-compiled → ok=True, 42 KB PDF, lstlisting wraps. (The workflow's own verify ran pytest on LaTeX
  *strings*, so it missed the no-PDF break — exactly the risk S0 flagged. imp4: compile-smoke test now
  exists.)
- **Check #2 — A5 badge survives the escaper → VERIFIED.** `**[OPEN]**`→`$\text{\colorbox{}{\textsc{}}}$`
  is stashed as math by `document._inline` (unescaped) and renders in text mode. Compiled: ok=True, 31 KB.
- **Check #3 — A6 renumbering → VERIFIED CORRECT.** paper.py:143-153 first-appearance `old→new` map, 1..k
  contiguous, `sources[old-1]` index correct, out-of-range dropped. Lint independently flags non-contiguous.
- **Check #5 — lint A6 consistent with paper.py renumber → VERIFIED.** Fed a `1./3.` list w/ `[1],[3]` →
  lint flags "not contiguous" + dangling cite. Consistent.
- **Lint gate genuinely gates** — bad doc → `ok=False`, caught A1/A2/A5/A7. Would auto-catch a
  microtype-class regression.

## Findings / open
- **Check #4 (B1 silent collision):** two same-topic same-day papers share a slug — hash is in the run_id
  receipt, so no data loss, but the human-facing PDF *name* can collide. Acceptable per S0's framing; note
  it. **Also: lint does NOT flag ugly `…-conje-<hash>.pdf` mid-word/hash names** (LOW gap — belt-and-suspenders).
- **imp4 NOT done:** lint is not yet wired into the compile path → a paper can still ship unlinted. Until
  wired, the gate is advisory.
- **A8 (provenance/process/agent-contribution section) NOT built** — the biggest user-requested item is
  still absent from the paper template. A3 figure-font readability landed in code (size parse) but unverified
  on a real wide flowchart.
