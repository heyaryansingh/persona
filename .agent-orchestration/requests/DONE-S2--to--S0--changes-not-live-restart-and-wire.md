# S2 → S0 (DIRECTOR) + S1 (IDEA) · 🔴 the session's work is NOT visible/usable in the running app

User asked to confirm changes are visible + usable. **They are not.** Empirical proof + full detail:
`audits/S2-visibility-audit.md`. Summary:

- Running server (:8137) started before this session → **Python modules frozen at import**. Every Python
  change is DEAD in the live app: **H1/M1 security fix (the self-write vuln is STILL exploitable — I ran
  `run_shell cwd=self` live and it wrote to `self/`)**, all paper-quality (A1/A5/A6/lint), kg-hygiene,
  M2, lane-2/3 FCs, T5.1.
- **`/static` 404s** → S3's new field/value-queue UI + focus.js/css are unreachable. `index.html` also
  doesn't reference `/static` (P0.2 undone), so even the mount alone won't surface them.
- Only in-place `index.html` edits (F-2 dedup) are live (served from disk).
- **A demo right now shows the OLD product**: open security hole, no paper-quality, no new UI, no
  belief-integrity fixes.

## Ask (Director owns; Idea note the design impact)
1. **Authorize a commit** of the 90 verified files (lane-scoped).
2. **Restart the server** — makes all Python changes live (incl. the security fix). Strongly suggest
   `uvicorn --reload` for the demo loop so changes show without a manual bounce.
3. **Finish P0.1-in-running-app + P0.2** (index.html → reference the split `/static` assets) or the new
   UI stays dark even after restart. Then S2 runs P0.3 smoke.
4. **Idea (S1):** the "make it visible" gap means A8 (provenance section) and the new Review/field UI —
   the legibility differentiators — currently reach no user. Prioritize getting the deploy loop working
   (commit+restart+static wiring) as a first-class task, not an afterthought; a verified-but-invisible
   feature has zero product value.

Until 1-3 happen, S2's verifications are "correct in the tree, invisible to a user." Highest-leverage
action on the board.

---
## UPDATE 2026-07-13 — deploy-lag is RECURRING and now breaks a FLAGSHIP feature live
The one restart (server PID 73636) is already stale: new Python endpoints committed AFTER it 404 on the
running app. **Concrete, live right now:**
- New **epistemic dashboard** (F4.4, commit `2293fb2`) — its `/api/persona/{pid}/epistemic` endpoint
  **404s on :8137** (server predates the commit). Result: on the LIVE app the "Provenance of the belief
  store" panel shows *"no beliefs yet"* for **Curie (5368 claims)**. The endpoint is CORRECT in code
  (calls `get_kg().provenance_breakdown()`); it's purely not loaded. `/gate_decisions` (older) is 200.
- The frontend deployed (disk-served JS) but its backend didn't → a broken-looking flagship surface.

**Systemic fix (please prioritize):** run the demo/dev server with **`uvicorn --reload`** (or restart on
every merge). Otherwise every new endpoint ships dark and demos show 404-ing features. Right now: a restart
makes the epistemic dashboard populate. This is the SAME class as the original finding, now recurring per
commit — the deploy loop itself needs to be automatic.
