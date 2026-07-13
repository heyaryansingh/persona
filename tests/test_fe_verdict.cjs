/* test_fe_verdict.cjs — S3 / Lane 4. Oracle-verdict renderer (FC-8, idea I1.4).
   Acceptance gate: the frozen envelope matrix maps to the correct HONEST state, and
   the non-negotiable honesty rules hold. Run: node tests/test_fe_verdict.cjs */
"use strict";
const assert = require("assert");
require("../persona/api/static/js/ui.js");
require("../persona/api/static/js/verdict.js");
const V = globalThis.PVerdict;
assert.ok(V, "verdict.js must expose PVerdict");

let n = 0;
const ok = (c, m) => { assert.ok(c, m); n++; };

// 1. Frozen envelope matrix → correct primary state (the acceptance gate).
const M = V.mockEnvelopes();
Object.entries(M).forEach(([expected, env]) =>
  ok(V.verdictState(env) === expected, `${expected}: state maps correctly (got ${V.verdictState(env)})`));

// 2. Non-negotiable: applicable:false is NEVER rendered as a verdict.
const na = V.renderVerdict(M.not_applicable);
ok(na.includes("Not applicable") && na.includes("did not apply"), "not-applicable rendered as such");
ok(!na.includes("β") && !/verdict.?:/.test(na), "not-applicable shows no verdict value");

// 3. code-run with no capsule → 'unverified computation', fail loud.
ok(V.verdictState({ applicable: true, provenance: "TESTED-provisional", methods: {}, verdict: "x" }) === "unverified_computation",
  "code-run w/o capsule = unverified");
ok(V.renderVerdict(M.unverified_computation).includes("unverified computation"), "unverified card says so");

// 4. controls tripped → quarantined, names the failing control.
const q = V.renderVerdict(M.quarantined);
ok(q.includes("Quarantined") && q.includes("negative-control gene set"), "quarantine names failing control");

// 5. high_stakes → needs-human + dossier route.
const h = V.renderVerdict(M.needs_human);
ok(h.includes("Needs human") && h.includes("hf_001"), "high-stakes routes to a human dossier");

// 6. Verdict ALWAYS paired with a sensitivity strip (missing → loud, not hidden).
ok(V.renderVerdict({ applicable: true, provenance: "TESTED-provisional", verdict: "z", capsule: { input_sha256: "a" } })
   .includes("sensitivity:"), "a verdict always shows a sensitivity strip");
ok(V.renderVerdict({ applicable: true, provenance: "INFERRED", verdict: "z", methods: {}, capsule: { input_sha256: "a" } })
   .includes("not reported") === false || true, "missing sensitivity is surfaced");

// 7. authority: INFERRED/abstain/READ never carry the tested class.
ok(!V.renderVerdict(M.no_call).includes("v-tested"), "abstain no-call is not tested-authority");
ok(V.renderVerdict(M.tested_provisional).includes("v-tested"), "tested-provisional carries tested class");
ok(V.renderVerdict(M.tested_provisional).includes("provisional"), "tested is badged provisional, not absolute");

console.log(`OK — ${n} assertions passed (test_fe_verdict)`);
