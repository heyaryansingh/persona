/* test_fe_epistemic.cjs — S3 / Lane 4. Epistemic dashboard (F4.4) renderers.
   Guards: provenance counts verbatim + colour-with-text, honest calibration, gate states.
   Run: node tests/test_fe_epistemic.cjs */
"use strict";
const assert = require("assert");
require("../persona/api/static/js/ui.js");
require("../persona/api/static/js/epistemic.js");
const E = globalThis.PEpistemic;
assert.ok(E, "epistemic.js must expose PEpistemic");

let n = 0;
const ok = (c, m) => { assert.ok(c, m); n++; };

// 1. Provenance bar: server counts verbatim, labelled (colour never alone), flags surfaced.
const p = E.renderProvenance({ READ: 10, INFERRED: 5, HUMAN_CONFIRMED: 2, TESTED: 1, never_confirmed: 3, stale: 1 });
["read", "inferred", "human-confirmed", "tested"].forEach((l) => ok(p.includes(l), `legend labels ${l}`));
ok(p.includes(">10<") && p.includes(">5<") && p.includes(">2<") && p.includes(">1<"), "counts rendered verbatim");
ok(p.includes("pv-seg"), "bar has proportional segments");
ok(p.includes("3 never-confirmed") && p.includes("1 stale"), "never-confirmed/stale flags surfaced");

// 2. Empty provenance → honest empty, not a fabricated bar.
ok(E.renderProvenance({}).includes("no beliefs yet"), "empty provenance is honest");

// 3. Calibration: no validated global bound → says so, cites RQ-E16 (never a fake number).
const cal = E.renderCalibration(null, false);
ok(/not yet validated/i.test(cal) && cal.includes("RQ-E16"), "calibration honestly absent");
ok(!/[0-9]\.[0-9]/.test(cal), "no fabricated bound number when unavailable");

// 4. Gates: id + title + status label, status class.
const g = E.renderGates([{ id: "RQ-E02", title: "contradiction typing", status: "pending" },
                         { id: "RQ-E12", title: "executable science", status: "contested" }]);
ok(g.includes("RQ-E02") && g.includes("contradiction typing"), "gate row shows id + title");
ok(g.includes("gate-pending") && g.includes("gate-contested"), "gate status classes applied");
ok(g.includes("pending") && g.includes("contested"), "gate status shown as text");

// 5. Gate decisions (F4.6): rows with decision badge + reason; degrades empty; read-only.
const gd = E.renderGateDecisions({ available: true, decisions: [
  { candidate_id: "c1", title: "a claim", gate: "membrane", decision: "admit", reason: "spans agree", score: 0.9 },
  { candidate_id: "c2", gate: "relevance", decision: "skip", reason: "off-topic" }] });
ok(gd.includes("gd-admit") && gd.includes("gd-skip"), "decision classes applied");
ok(gd.includes("admit") && gd.includes("skip") && gd.includes("spans agree"), "decision + reason shown");
ok(gd.includes("membrane") && gd.includes("relevance"), "gate names shown");
ok(E.renderGateDecisions({ available: false, decisions: [] }).includes("no gate decisions"), "degrades empty (honest)");
ok(E.renderGateDecisions({}).includes("no gate decisions"), "missing ledger → honest empty");

console.log(`OK — ${n} assertions passed (test_fe_epistemic)`);
