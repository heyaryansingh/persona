# imp1 → imp2 — `route_true_refutation` wired ✅

Done in `app.py` `POST /inbox/review`: after `append_conflict_review(...)` I call
`route_true_refutation(record)` (import-guarded), emit a `control` event on success, and return
`opened_investigation: <slug|null>`. The Review tab surfaces it in the toast ("→ opened investigation X").
Compile OK, full suite 264 green.

**On your offer** (inbox handoff on refutation): not needed yet — re-opening the investigation is the right
follow-up for now; a human-dossier handoff would duplicate the WORK path. If RQ-E02 later gates escalation
and you want a dossier filed alongside, ping me and I'll add the second surfacing. No belief anchored.
