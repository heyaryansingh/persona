/* test_fe_field.cjs — S3 / Lane 4. Node self-check for field.js (flagship 4.1).
   Guards: verbatim server-value passthrough (no invented scores), fragile-as-shape,
   correct downstream edge counts, VoI/load-bearing ordering. Run: node tests/test_fe_field.cjs */
"use strict";
const assert = require("assert");
require("../persona/api/static/js/ui.js");
require("../persona/api/static/js/field.js");
const F = globalThis.PField;
assert.ok(F, "field.js must expose PField");

let n = 0;
const ok = (c, m) => { assert.ok(c, m); n++; };

const data = F.mockData();

// 1. downstreamCount is pure counting of returned edges (no fabrication).
ok(F.downstreamCount("clm_a1", data.dependency.edges) === 2, "clm_a1 has 2 downstream");
ok(F.downstreamCount("clm_b2", data.dependency.edges) === 1, "clm_b2 has 1 downstream");
ok(F.downstreamCount("clm_c3", data.dependency.edges) === 0, "clm_c3 is a leaf");

// 2. Dependency render: statements present, server numbers verbatim, downstream shown.
const dep = F.renderDependency(data.dependency);
ok(dep.includes("Oxidative stress contributes to AD progression"), "renders a statement");
ok(dep.includes("0.91"), "load_bearing rendered verbatim (server value, not computed)");
ok(dep.includes("2 weaken if this falls"), "downstream count surfaced for clm_a1");

// 3. Fragile node → distinct SHAPE + text, never colour alone.
ok(dep.includes("◇ fragile"), "fragile marked with a shape glyph + text");
// non-fragile node must NOT carry the fragile mark spuriously (count marks == fragile nodes)
const fragCount = (dep.match(/◇ fragile/g) || []).length;
ok(fragCount === data.dependency.nodes.filter((x) => x.fragile).length, "exactly the fragile nodes are marked");

// 4. Ordering by server load_bearing desc (0.91 before 0.55).
ok(dep.indexOf("0.91") < dep.indexOf("0.55"), "nodes ordered by load_bearing desc");

// 5. Missing server field → em dash, never fabricated.
const miss = F.renderDependency({ nodes: [{ claim_id: "x", provenance: "observed" }], edges: [] });
ok(miss.includes("—"), "missing statement/metrics render as —");

// 6. Value queue: rows, VoI verbatim, cost label, dataset flag, ordering by voi desc.
const vq = F.renderValueQueue(data.value_queue);
ok(vq.includes("VoI 0.72"), "VoI rendered verbatim (server value)");
ok(vq.includes("public data") && vq.includes("cheap assay"), "cost tiers labelled");
ok(vq.includes("✓ dataset") && vq.includes("no dataset"), "dataset availability shown as text");
ok(vq.includes("open dossier"), "each row can open a handoff dossier (FC-2)");
ok(vq.indexOf("0.72") < vq.indexOf("0.44"), "value queue ordered by VoI desc");

// 7. normalizeField adapts the two live route shapes; degrades to empty (honest, not mock).
const norm = F.normalizeField({ nodes: [{ claim_id: "z" }], edges: [{ src: "z", dst: "y" }] }, { queue: [{ question: "q", voi: 0.5 }] });
ok(norm.dependency.nodes.length === 1 && norm.dependency.edges.length === 1, "unwraps /engine/dependency");
ok(norm.value_queue.length === 1, "unwraps /engine/value_queue {queue:[...]}");
const empty = F.normalizeField({ available: false }, { available: false });
ok(empty.dependency.nodes.length === 0 && empty.value_queue.length === 0, "degrades to EMPTY, not mock, when backend absent");
const bare = F.normalizeField(null, [{ question: "q2" }]);
ok(bare.value_queue.length === 1 && bare.dependency.nodes.length === 0, "handles bare-array value_queue + null dependency");

// 8. R-1: value-queue hides "de-risks 0"; shows it when > 0.
ok(!F.renderValueQueue([{ question: "q", voi: 0.5, de_risks_n: 0 }]).includes("de-risks"), "de-risks 0 hidden");
ok(F.renderValueQueue([{ question: "q", voi: 0.5, de_risks_n: 3 }]).includes("de-risks 3"), "de-risks shown when > 0");

// 9. R-1: empty dependency graph → single-column mount (no dead 'Field rests on' col), with a hint.
const fake = { classList: { _c: {}, toggle(c, on) { this._c[c] = on; } }, innerHTML: "" };
F.mount(fake, { dependency: { nodes: [], edges: [] }, value_queue: [{ question: "q", voi: 0.4 }] });
ok(fake.classList._c["fieldwrap-single"] === true, "empty dep → single-col class toggled on");
ok(!fake.innerHTML.includes("field-col"), "empty dep → no dead Field-rests-on column");
ok(/dependency map builds/i.test(fake.innerHTML), "empty dep → shows a build hint");
const fake2 = { classList: { _c: {}, toggle(c, on) { this._c[c] = on; } }, innerHTML: "" };
F.mount(fake2, F.mockData());
ok(fake2.classList._c["fieldwrap-single"] === false && fake2.innerHTML.includes("field-col"), "non-empty dep → two columns");

console.log(`OK — ${n} assertions passed (test_fe_field)`);
