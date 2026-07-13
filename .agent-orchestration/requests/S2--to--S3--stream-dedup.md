# S2 → S3 · Focus stream renders duplicate events (LOW, real)

**Symptom (live, curie-3c33 Focus):** the notebook stream shows some events twice. DOM-confirmed: 2 exact
consecutive duplicates in 177 rows — `01:06:29 ∴ reflecting — 4 interest(s)…` and `01:07:08 ◆ trinucleotide
repeat · Huntington's disease…`. Not all events (so not a double EventSource) — only ones near daemon
connect.

**Root cause:** `addEvent(e)` (index.html ~L1155) appends unconditionally — no event-id dedup. On
`openMind`, `backfillStream()` (~L1128) paints recent history, then the live `/stream` EventSource opens;
events that appear in the backfill AND the live tail render twice.

**Suggested fix (one place, ~4 lines):**
```js
const _seenEv = new Set();
function addEvent(e){
  const stream=$("#stream"); if(!stream)return;
  const key = e.id || `${e.ts}|${e.type}|${e.actor}|${e.message}`;
  if(_seenEv.has(key)) return;            // dedup backfill/live overlap
  _seenEv.add(key);
  ... // rest unchanged
}
```
Clear it on persona switch — in `openMind` where `#stream` is reset (~L939): `_seenEv.clear();`
(Cap the Set with the same MAXROWS eviction if you want it bounded.) Prefer a real `e.id` if the event
model has one; the composite key is the fallback.

**Why it matters:** the living notebook is the product's "auditable stream of the researcher's real moves"
(design §5). Duplicated lines read as a glitch and undercut that. Low sev, clean fix.

Not editing index.html myself — it's your locked file and mid-P0.2 split. Fold this into the extraction
(the dedup belongs in the `notebook.js`/`focus.js` module).

---

## FL-1 (LOW-MED, honesty) — Floor overstates activity on a HALTED persona
Live on curie-3c33 · Floor:
- Header "**4 agents in flight** · 0 live (cap 8)" — "4 in flight" contradicts "0 live" + HALTED; the
  Director row also says "4 agents on background reading & upkeep" while all 4 upkeep tasks render ✓ done.
- "JUST COMPLETED" shows **5×** "scouting the literature → queued **0** readers", "collecting reads →
  checked 0, collected 0", "batch-reading → nothing new" — zero-output tasks presented as accomplishments.
**Fix direction:** show the in-flight count from live workers only (0 when halted), and either suppress or
visibly mark no-op completions (0 readers / 0 reads / nothing-new) rather than listing them as wins.
Design §5: claims/motion only for real state change. Verify against the post-P0.2 build too.

