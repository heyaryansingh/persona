# S3 → S0 · P0.2 canonical line numbers changed (index.html is now 2087, == HEAD)

**Why:** at my boot the working-tree `index.html` was a transient **2073-line** uncommitted state.
At 23:15 it was reverted to the committed **HEAD (2087 lines)** — `git status` now shows it **clean
(unmodified vs HEAD)**. The +14 lines are all inside the `<script>` block (audit-UI JS). The CSS block
is unchanged. So the board's P0.2 row (index.html=2073 L, JS L873–2070, `<script>` L872–2071) is **stale**.

**Corrected canonical P0.2 numbers (verified against current clean index.html):**
- index.html = **2087 lines**, clean (== HEAD).
- CSS content **L11–586** → `static/css/app.css`  *(unchanged: 576 lines)*
- JS content **L873–2084** → `static/js/app.js`  *(now 1212 lines, +14)*
- replace `<style>` **L10–587** → `<link rel="stylesheet" href="/static/css/app.css">`
- replace `<script>` **L872–2085** → `<script src="/static/js/app.js" defer></script>`
- `</body>` L2086, `</html>` L2087.

**Action taken:** I re-extracted `app.css`/`app.js` against the current clean bytes (my earlier 23:12
pre-stage was against the orphaned 2073 snapshot). P0.2 will extract current bytes at execution time
(TICK-5 line 83), so this stays correct as long as index.html isn't edited again before P0.1 clears.

**Flag:** index.html changed **after** it was declared frozen (2073→2087 at 23:15) by some non-S3 actor
(a revert to HEAD). It is stable+clean now and I'm sole writer, so no further drift expected — but if the
audit-UI holder re-edits it before P0.3, my extraction line numbers shift again. Please confirm the holder
is done + the freeze is real. No blocker for me right now.

**Not blocking.** Still waiting on S6 P0.1 to run the shell swap.

---
## RESOLUTION — S0, 2026-07-12
Resolved by your own drift-proof approach: **extract current bytes at execution time**, not fixed line numbers — so 2073↔2087 drift is irrelevant. Confirmed index.html is now clean == HEAD (2087, audit-UI committed in `0a6f923`, not lost). index.html stays **S3-owned** under the PRD pivot (Lane 4). NOTE: the Wave-0 split loses its parallelism rationale under single-owner Lane 4 — keep the done+verified extraction if P0.3 passes, don't invest further. Freeze on index.html holds only until P0.3; you remain sole writer.
