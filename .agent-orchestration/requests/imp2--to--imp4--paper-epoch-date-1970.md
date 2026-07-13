# imp2 → imp4 — A7 root: compiled papers show "Jan 1 1970" / "(0)" for undated sources (user-reported)

**User asked for this fix directly. Traced it — the root is in YOUR lane (`deliverables/`/`synthesis/`), not mine.**

## What I verified (imp2 lane is clean)
- `reading/reader.py` + `batch.py` store the **real** `work.year` (or `None` when OpenAlex has none) in `meta.json`; `claims.jsonl` has **no** date field. Sampled real data: years 1999/2019/2016 — correct.
- Frontend (`index.html`) already guards every paper/source render: `${s.year||''}`, `${d.year?…}` → blank when missing (imp1's A7 frontend part is in). The only full-date renders (L1487 `gxScrub`, L1606 `evtime`) are single timeline labels, not per-paper.
- So no epoch leaks from reading/ or the UI paper cards.

## The remaining leak (yours to fix)
`deliverables/paper_lint.py:110-133` already **detects** `\b1970\b` and `(0)` in the compiled paper body + source-cards — so the compiled paper IS rendering a missing source year as `1970`/`(0)`. The **source-card / bibliography year render** in the paper builder (`deliverables/paper.py` or `synthesis/synthesizer.py`) is emitting `year or 0` → `(0)`, or formatting a 0/None as a date → `1970`. `kg.py::_year` (already yours) returns `None` for implausible years — **use it and render `None`/`0`/missing as the real year or `n.d.`, never `0`/`1970`.**

## Fix
Wherever a source's year is written into the paper (card, bibliography, or the model prompt that builds them): `year_str = str(y) if isinstance(y, int) and 1500 <= y <= <current+1> else "n.d."` — never `0`, never a date-format of a 0/None. Then `paper_lint`'s A7 check will pass on real output (right now it detects the leak but nothing upstream prevents it). Add the guard at the render, plus a test that a source with `year=None`/`0` renders `n.d.` (not `1970`).

_Not my file to edit (deliverables = imp4 sole-writer + your active workflow). Flagging with the exact locus so you can fix cleanly. If S0/human wants me to cross-edit, say so._
