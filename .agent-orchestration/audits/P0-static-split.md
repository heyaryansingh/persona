# P0.3 — `index.html` static-split byte-check (S2 gate)  ·  IN PROGRESS

**Gate owner:** S2. **Only S2 clears Wave 0.** Verdict pending the "AFTER" (needs S3 `✅ P0.2`).

---

## BEFORE — captured pre-split, 2026-07-12 (index.html frozen at current 2087-line monolith)

Ran the real gate harness against the **current, pre-split** `index.html` on a clean no-worker server — both to establish the before-reference and to de-risk the gate launch itself.

- **Server:** `PERSONA_WORKERS=0 python -m persona --port 8138` — ready in 1s (HTTP 200). Killed cleanly after (verified by cmdline `*persona*8138*`; :8138 → HTTP 000 after). Idle :8137 orphan left untouched.
- **Smoke:** `PERSONA_SMOKE_BASE=http://127.0.0.1:8138 node tests/ui_research_smoke.cjs`
- **Result:** `{"cards":3,"researchLabel":"Research","geoSession":"passed","conflictDossier":"passed"}` · exit 0 · **zero console errors** (the script throws on any; exit 0 ⇒ none, favicon 404 already filtered).
- **Before renders preserved:** `results/p03_before_ui_research_sessions.png`, `…_session_detail.png`, `…_geo_session.png`, `…_conflict_dossier.png` (so P0.2's "after" run can't overwrite them).

**De-risk conclusions:** (1) the :8138 launch + `PERSONA_SMOKE_BASE` path works end-to-end; (2) current frozen `index.html` is a clean baseline (all assertions pass, no console errors); (3) the before-console set is empty → at the gate I assert the after-set is **also** empty (zero NEW errors is trivially satisfied unless the split introduces one, e.g. a 404 on `/static/css/app.css`).

---

## BEFORE — REFRESHED 2026-07-13 (P0.1 mount landed; baseline re-captured at 2091)

- **P0.1 verified:** `app.py` L20 `from fastapi.staticfiles import StaticFiles`, L30 `app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")`, root `/` (L1388) still serves `index.html`. Suite 144 passed. (No `health.txt` self-asset, but the smoke's live asset-load at P0.3 is the real check.)
- **Why re-captured:** the earlier before-shots were on the 2087 monolith; `index.html` is now **2091** (my F-2 dedup fix merged in) and is the *exact content P0.2 will extract*. Critically, the 2091 pre-split version is **uncommitted (HEAD `0a6f923`)** — it exists only in the working tree and S3's P0.2 shell edit will overwrite it. So I preserved it before it's lost:
  - Bytes: `scratchpad/p03_before_index_2091.html`.
  - Render: fresh `PERSONA_WORKERS=0` :8138 smoke → `{cards:3, Research, geo:passed, dossier:passed}`, exit 0, **zero console errors**. Shots → `results/p03_before_*.png` (now the 2091 baseline). :8138 killed clean.

## AFTER — 2026-07-13 · ✅ P0.3 PASS — Wave 0 CLEARED

S3 shipped a *partial* split (css → `/static/css/app.css`, JS kept inline + new Lane-4 modules; the original clean full-extraction was deprioritized and superseded). What matters for the gate — **behavior preserved** — holds:
- Clean `PERSONA_WORKERS=0` :8138 server; `GET /static/css/app.css` → **200** via the mount.
- Smoke (after): `{cards:3, Research, geo:passed, dossier:passed}`, exit 0, **zero console errors** — identical to the BEFORE result.
- `js/app.js → 404` on a **direct** curl is a NON-issue: the page does not reference it (S3 deleted the vestigial file); if it did, the smoke's response-≥400 hook would have flagged it → it didn't.
- fe unit tests on the current state: field **19**, focus **38**, verdict **18** assertions; eval **11**. Python suite **256** green; compileall 0.

**Verdict: ✅ P0.3 clears Wave 0.** Render identical + zero new console errors + assets load. The frontend was committed on this verification (`8279168` + `a39218c`).
