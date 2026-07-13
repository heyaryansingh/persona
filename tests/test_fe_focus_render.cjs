/* test_fe_focus_render.cjs — S3 lane. Node self-check for focus.js/ui.js pure
   render functions (no DOM). Guards the spec's epistemic-integrity acceptance
   checks. Run: node tests/test_fe_focus_render.cjs  (exit 0 = pass). */
"use strict";
const assert = require("assert");
// The modules are browser classic scripts (loaded via <script src> → window
// globals). Require for side-effects, then read the globals the IIFE sets —
// this matches production and is robust whether node treats .js as CJS or ESM.
require("../persona/api/static/js/ui.js");
require("../persona/api/static/js/focus.js");
const UI = globalThis.PUI;
const F = globalThis.PFocus;
assert.ok(UI && F, "ui.js/focus.js must expose PUI/PFocus globals");

let n = 0;
const ok = (c, m) => { assert.ok(c, m); n++; };

// 1. Notebook drops orchestration noise, keeps real moves.
const evs = [
  { ts: "2026-07-12T10:00:00Z", type: "read", message: "read a paper", actor: "r1" },
  { ts: "2026-07-12T10:00:01Z", type: "spawn", message: "spawned worker", actor: "sched" },
  { ts: "2026-07-12T10:00:02Z", type: "cost", message: "$0.01", actor: "meter" },
  { ts: "2026-07-12T10:00:03Z", type: "belief_update", message: "updated belief", actor: "membrane" },
];
const nb = F.renderNotebook(evs);
ok(nb.includes("read a paper"), "keeps real 'read' move");
ok(nb.includes("updated belief"), "keeps 'belief_update'");
ok(!nb.includes("spawned worker"), "drops 'spawn' noise");
ok(!nb.includes("$0.01"), "drops 'cost' noise");

// 2. XSS: message HTML is escaped, never injected.
const evil = F.renderNotebook([{ ts: "2026-07-12T10:00:00Z", type: "read", message: "<script>alert(1)</script>", actor: "x" }]);
ok(!evil.includes("<script>alert(1)</script>"), "raw script tag not present");
ok(evil.includes("&lt;script&gt;"), "script tag is escaped");

// 3. Next action: missing server field → em dash, never a fabricated value.
const na = F.renderNextAction({ what: "do X", reason: "because", cost_ceiling: "$0" });
ok(na.includes("do X") && na.includes("because"), "renders present fields");
ok((na.match(/—/g) || []).length >= 2, "missing expected_gain + stop_rule render as —");

// 4. Blinded review card invariants.
const asg = F.mockData().assignment;
const rc = F.renderReviewCard(asg);
["extraction_error", "true_refutation", "context_divergence", "insufficient_evidence"].forEach((l) =>
  ok(rc.includes(l), `review card exposes label ${l}`));
ok(rc.includes("unverified"), "card marks status unverified");
ok(/never changes a belief/i.test(rc), "card states labeling never mutates a belief");
ok(!/\braises\b/i.test(rc) && !/\blowers\b/i.test(rc), "no verified raises/lowers debt wording");
ok(rc.indexOf("Source A") < rc.indexOf("Source B"), "packets rendered in served order A then B");
// no canonical pos/neg mapping leaks into served HTML
["pos_claim", "neg_claim", "canonical_positive", "is_positive"].forEach((k) =>
  ok(!rc.includes(k), `no sign-map leak: ${k} absent`));

// 5. State badge pairs colour-class WITH text + shape (never colour alone).
const b = UI.stateBadge("candidate");
ok(b.includes("st-candidate"), "badge has colour class");
ok(b.includes("candidate · unverified"), "badge has text label");
ok(b.includes("pbadge-g"), "badge has glyph/shape");

// 6. Dual badge = TWO separate chips (lineage never conflated with truth).
const db = UI.dualBadge("passed", "contested");
ok((db.match(/class="chip/g) || []).length === 2, "dual badge renders two chips");
ok(db.includes("trace:") && db.includes("review:"), "trace + review shown separately");

// 7. §A v2 label body carries all keys; ts is caller-stamped (null by default).
const body = F.buildLabelBody(asg, "true_refutation", "matched qualifiers", null);
["assignment_id", "reviewer_id", "batch_id", "conflict_id", "schema_version", "label", "rationale", "ts"].forEach((k) =>
  ok(k in body, `label body has ${k}`));
ok(body.ts === null, "ts defaults null (wall-clock stamped by caller, per §A v2 F6)");
ok(body.label === "true_refutation" && body.rationale === "matched qualifiers", "label + rationale carried");

// 8. Event dedup key (S2 stream-dedup): stable, distinguishing, prefers real id.
ok(F.eventKey({ ts: "t", type: "read", actor: "a", message: "m" }) ===
   F.eventKey({ ts: "t", type: "read", actor: "a", message: "m" }), "eventKey stable for identical events");
ok(F.eventKey({ ts: "t", type: "read", actor: "a", message: "m" }) !==
   F.eventKey({ ts: "t", type: "read", actor: "a", message: "n" }), "eventKey differs when a field differs");
ok(F.eventKey({ id: "x1", ts: "t", type: "read" }) === "x1", "eventKey prefers a real event id");

console.log(`OK — ${n} assertions passed (test_fe_focus_render)`);
