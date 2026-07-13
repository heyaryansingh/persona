/* =========================================================================
   field.js — Flagship 4.1 "Field-rests-on-this + value queue"   (S3 / Lane 4)
   ---------------------------------------------------------------------------
   The flagship legibility surface: what the field rests on (dependency /
   load-bearing map) beside the highest-value experiments to run (VoI ÷ cost).
   Contract-first against FC-4 fixtures (Lane 3/S6 provides the real
   `engine.dependency_graph` / `engine.value_queue`; parked → build vs fixtures).

   Exposed as `PField` (browser) + module.exports (node). Uses PUI (ui.js).

   Epistemic rules (PRD-04 §4, RQP §8) — enforced here:
   - EVERY surfaced number (load_bearing, voi, support_ratio, independent_labs,
     de_risks_n) is a SERVER field rendered verbatim. This module performs NO
     arithmetic that yields a labelled score. The only client computation is
     COUNTING returned edges ("N downstream"), which is counting server data.
   - `fragile` is marked with a distinct SHAPE + text (◇ fragile), never colour alone.
   - Missing server fields render "—", never a fabricated value.
   ========================================================================= */
(function (root) {
  "use strict";
  const UI = root.PUI || (typeof require !== "undefined" ? require("./ui.js") : null);
  if (!UI) throw new Error("field.js requires ui.js (PUI)");
  const { esc, orDash, stateBadge } = UI;

  // Count downstream dependents of a claim = edges whose src is this claim.
  // Counting server-returned edges is allowed (acceptance: N matches hand-count).
  function downstreamCount(claimId, edges) {
    return (edges || []).filter((e) => e && e.src === claimId).length;
  }

  function fragileMark(fragile) {
    // Shape (◇) + text, never colour alone (PRD-04 §4).
    return fragile ? `<span class="frag" title="thinly supported — may not hold">◇ fragile</span>` : "";
  }

  function depNode(node, edges) {
    node = node || {};
    const down = downstreamCount(node.claim_id, edges);
    return (
      `<div class="dep" data-claim="${esc(orDash(node.claim_id))}" tabindex="0">` +
      `<div class="dep-top">${stateBadge(node.provenance)}${fragileMark(node.fragile)}</div>` +
      `<div class="dep-stmt">${esc(orDash(node.statement))}</div>` +
      `<dl class="dep-m">` +
      `<div><dt>load-bearing</dt><dd class="mono">${esc(orDash(node.load_bearing))}</dd></div>` +
      `<div><dt>independent labs</dt><dd class="mono">${esc(orDash(node.independent_labs))}</dd></div>` +
      `<div><dt>support ratio</dt><dd class="mono">${esc(orDash(node.support_ratio))}</dd></div>` +
      `<div><dt>downstream</dt><dd class="mono">${down} weaken if this falls</dd></div>` +
      `</dl></div>`
    );
  }

  function renderDependency(graph) {
    graph = graph || {};
    const edges = graph.edges || [];
    // Order by server load_bearing desc; ties keep input order. No score is invented.
    const nodes = (graph.nodes || []).slice().sort(
      (a, b) => (Number(b.load_bearing) || 0) - (Number(a.load_bearing) || 0));
    const body = nodes.map((n) => depNode(n, edges)).join("");
    return `<div class="deplist">${body || '<div class="fempty">no dependency graph yet</div>'}</div>`;
  }

  const COST_LABEL = { public_data: "public data", cheap_assay: "cheap assay", expensive: "expensive" };

  function vqRow(item) {
    item = item || {};
    const cost = COST_LABEL[item.cost_tier] || orDash(item.cost_tier);
    const ds = item.dataset_available === true ? "✓ dataset" :
               item.dataset_available === false ? "no dataset" : "—";
    return (
      `<div class="vq" data-resolves="${esc(orDash(item.resolves_claim_id))}">` +
      `<div class="vq-q">${esc(orDash(item.question))}</div>` +
      `<div class="vq-m"><span class="vq-voi mono" title="value of information (server)">VoI ${esc(orDash(item.voi))}</span>` +
      `<span class="cost cost-${esc(item.cost_tier || "unknown")}">${esc(cost)}</span>` +
      `<span class="ds">${esc(ds)}</span>` +
      // R-1: hide "de-risks 0" (uniform when the dep-graph is empty) — reads as a broken metric.
      (item.de_risks_n ? `<span class="mono">de-risks ${esc(item.de_risks_n)}</span>` : "") + `</div>` +
      `<div class="vq-act">` +
      `<button type="button" class="run" data-action="${esc(orDash(item.run_action))}">${esc(orDash(item.run_action))}</button>` +
      `<button type="button" class="dossier" data-resolves="${esc(orDash(item.resolves_claim_id))}">open dossier</button>` +
      `</div></div>`
    );
  }

  function renderValueQueue(queue) {
    // Order by server voi desc; ties keep input order. VoI is displayed, never computed.
    const rows = (queue || []).slice()
      .sort((a, b) => (Number(b.voi) || 0) - (Number(a.voi) || 0))
      .map(vqRow).join("");
    return `<div class="vqlist">${rows || '<div class="fempty">value queue empty</div>'}</div>`;
  }

  function mount(rootEl, data) {
    if (!rootEl) return;
    data = data || mockData();
    const depEmpty = !(((data.dependency || {}).nodes) || []).length;
    if (rootEl.classList) rootEl.classList.toggle("fieldwrap-single", depEmpty);
    // R-1: an empty dependency graph must not render a dead ~40% column — collapse to a single
    // full-width value queue with a hint that the map builds as claims accumulate links.
    const fieldCol = depEmpty ? "" :
      `<section class="field-col"><div class="col-h">Field rests on</div>` +
      `<p class="col-sub">node = a claim others depend on · ◇ = thinly supported · numbers are server-computed</p>` +
      renderDependency(data.dependency) + `</section>`;
    const vqSub = depEmpty
      ? "ranked by value-of-information ÷ cost · advisory until RQ-E17 · the dependency map builds as claims link"
      : "ranked by value-of-information ÷ cost · advisory until RQ-E17 passes";
    rootEl.innerHTML = fieldCol +
      `<section class="vq-col"><div class="col-h">Highest-value experiments</div>` +
      `<p class="col-sub">${vqSub}</p>` +
      renderValueQueue(data.value_queue) + `</section>`;
    return rootEl;
  }

  // Adapt the two route responses to what renderDependency/renderValueQueue expect.
  // /engine/dependency → {nodes,edges[,available]} ; /engine/value_queue → {queue[,available]}.
  // Degrades to EMPTY (honest) on absence — never falls back to mock data on a live surface.
  function normalizeField(depResp, vqResp) {
    const dep = depResp && Array.isArray(depResp.nodes)
      ? { nodes: depResp.nodes, edges: depResp.edges || [] } : { nodes: [], edges: [] };
    const vq = vqResp && Array.isArray(vqResp.queue) ? vqResp.queue
      : Array.isArray(vqResp) ? vqResp : [];
    return { dependency: dep, value_queue: vq };
  }

  // Live wiring: fetch FC-4 from the Lane-4 routes and render. Empty on error.
  async function loadField(pid, topic, rootEl) {
    const base = `/api/persona/${encodeURIComponent(pid)}`;
    const q = topic ? `?topic=${encodeURIComponent(topic)}` : "";
    let dr = null, vr = null;
    try {
      [dr, vr] = await Promise.all([
        root.fetch(`${base}/engine/dependency${q}`).then((r) => r.json()),
        root.fetch(`${base}/engine/value_queue${q}`).then((r) => r.json()),
      ]);
    } catch (e) { /* degrade to empty — honest uncertainty, not fabricated data */ }
    const data = normalizeField(dr, vr);
    mount(rootEl, data);
    return data;
  }

  // FC-4-shaped fixtures (standalone demo only; the live surface uses loadField).
  function mockData() {
    return {
      dependency: {
        nodes: [
          { claim_id: "clm_a1", statement: "Oxidative stress contributes to AD progression", load_bearing: 0.91, independent_labs: 6, support_ratio: 0.83, provenance: "corroborated", fragile: false },
          { claim_id: "clm_b2", statement: "NRF2 signaling regulates ferroptosis-pathway enzymes", load_bearing: 0.74, independent_labs: 3, support_ratio: 0.66, provenance: "tested", fragile: false },
          { claim_id: "clm_c3", statement: "A 7-gene NRF2 score declines with AD severity", load_bearing: 0.55, independent_labs: 1, support_ratio: 0.40, provenance: "candidate", fragile: true },
          { claim_id: "clm_d4", statement: "Microglial activation exacerbates tau pathology", load_bearing: 0.38, independent_labs: 2, support_ratio: 0.52, provenance: "observed", fragile: true },
        ],
        edges: [
          { src: "clm_a1", dst: "clm_b2", rel_type: "supports", confidence: 0.8, span: "…" },
          { src: "clm_a1", dst: "clm_c3", rel_type: "presupposes", confidence: 0.6, span: "…" },
          { src: "clm_b2", dst: "clm_c3", rel_type: "operationalizes", confidence: 0.7, span: "…" },
        ],
      },
      value_queue: [
        { question: "Re-extract matched qualifiers for the microglia–tau candidate pair", resolves_claim_id: "clm_d4", voi: 0.72, cost_tier: "public_data", dataset_available: true, de_risks_n: 3, run_action: "Investigate" },
        { question: "Replicate the 7-gene NRF2 score in an independent AD cohort", resolves_claim_id: "clm_c3", voi: 0.61, cost_tier: "public_data", dataset_available: true, de_risks_n: 2, run_action: "Investigate" },
        { question: "Assay GPX4 activity under NRF2 knockdown", resolves_claim_id: "clm_b2", voi: 0.44, cost_tier: "cheap_assay", dataset_available: false, de_risks_n: 1, run_action: "Handoff" },
      ],
    };
  }

  const API = { renderDependency, renderValueQueue, downstreamCount, normalizeField, loadField, mount, mockData };
  root.PField = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
})(typeof window !== "undefined" ? window : globalThis);
