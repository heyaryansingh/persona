/* =========================================================================
   epistemic.js — Epistemic-status dashboard (F4.4)            (S3 / Lane 4)
   ---------------------------------------------------------------------------
   Provenance breakdown (FC-3, real KG audit) + calibration bound (FC-5) + the
   RQ-gate status table. Exposed as `PEpistemic` (browser) + module.exports.

   Honesty: every count is the server's live KG audit — the bar segments are a
   faithful proportional view of those counts, never an invented score. Each
   segment carries its label + count (not colour alone). Calibration is shown as
   "not yet calibrated" when a validated global bound doesn't exist (RQ-E16).
   ========================================================================= */
(function (root) {
  "use strict";
  const UI = root.PUI || (typeof require !== "undefined" ? require("./ui.js") : null);
  if (!UI) throw new Error("epistemic.js requires ui.js (PUI)");
  const { esc, orDash } = UI;

  const PROV = [
    ["READ", "read", "pv-read"],
    ["INFERRED", "inferred", "pv-inferred"],
    ["HUMAN_CONFIRMED", "human-confirmed", "pv-anchor"],
    ["TESTED", "tested", "pv-tested"],
  ];

  function renderProvenance(prov) {
    prov = prov || {};
    const total = PROV.reduce((a, [k]) => a + (Number(prov[k]) || 0), 0);
    if (!total) return `<div class="fempty">no beliefs yet — provenance breakdown will populate as it reads</div>`;
    const bar = PROV.map(([k, , cls]) => {
      const c = Number(prov[k]) || 0;
      const pct = ((c / total) * 100).toFixed(1);
      return c ? `<span class="pv-seg ${cls}" style="width:${pct}%" title="${esc(k)}: ${c}"></span>` : "";
    }).join("");
    const legend = PROV.map(([k, label, cls]) =>
      `<span class="pv-key"><span class="pv-dot ${cls}"></span>${esc(label)} <b>${Number(prov[k]) || 0}</b></span>`
    ).join("");
    const flags = [];
    if (prov.never_confirmed) flags.push(`<span class="pv-flag">${prov.never_confirmed} never-confirmed</span>`);
    if (prov.stale) flags.push(`<span class="pv-flag pv-flag-stale">${prov.stale} stale</span>`);
    return `<div class="pv"><div class="pv-bar">${bar}</div><div class="pv-legend">${legend}</div>` +
      (flags.length ? `<div class="pv-flags">${flags.join("")}</div>` : "") + `</div>`;
  }

  function renderCalibration(bound, available) {
    if (available && bound != null) {
      return `<div class="calib">admitted-set error bound: <b class="mono">${esc(orDash(bound))}</b></div>`;
    }
    return `<div class="calib calib-none">calibration bound not yet validated (a global conformal bound is RQ-E16 — pending)</div>`;
  }

  const GATE_LABEL = { passed: "passed", partial: "partial", in_progress: "in progress",
    pending: "pending", contested: "contested", gated: "resource-gated" };

  function renderGates(gates) {
    const rows = (gates || []).map((g) =>
      `<div class="gate gate-${esc(g.status)}"><span class="gate-id mono">${esc(g.id)}</span>` +
      `<span class="gate-t">${esc(orDash(g.title))}</span>` +
      `<span class="gate-s">${esc(GATE_LABEL[g.status] || g.status)}</span></div>`
    ).join("");
    return `<div class="gates">${rows || '<div class="fempty">no RQ gates found</div>'}</div>`;
  }

  // F4.6 — read-only view of the append-only gate-decisions ledger (Lanes 1/2 write). Empty if absent.
  function renderGateDecisions(gd) {
    gd = gd || {};
    if (!gd.available || !(gd.decisions || []).length) {
      return `<div class="fempty">no gate decisions recorded yet — Lanes 1/2 append; this view is read-only</div>`;
    }
    const rows = gd.decisions.slice().reverse().map((d) => {
      const dec = d.decision || "—";
      return `<div class="gd gd-${esc(dec)}"><span class="gd-dec">${esc(dec)}</span>` +
        `<span class="gd-gate mono">${esc(orDash(d.gate))}</span>` +
        `<span class="gd-t">${esc(orDash(d.title || d.candidate_id))}</span>` +
        `<span class="gd-reason">${esc(orDash(d.reason))}</span>` +
        (d.score != null ? `<span class="gd-score mono">${esc(d.score)}</span>` : "") + `</div>`;
    }).join("");
    return `<div class="gdlist">${rows}</div>`;
  }

  function mount(rootEl, data) {
    if (!rootEl) return;
    data = data || mockData();
    rootEl.innerHTML =
      `<div class="epi-sec"><div class="epi-h">Provenance of the belief store</div>` +
      renderProvenance(data.provenance) + renderCalibration(data.calibration_bound, data.calibration_available) + `</div>` +
      `<div class="epi-sec"><div class="epi-h">Research-quality gates</div>` +
      `<p class="col-sub">a gate is a claim's licence to drive autonomy — advisory until it passes</p>` +
      renderGates(data.gates) + `</div>` +
      `<div class="epi-sec"><div class="epi-h">Gate decisions · admitted / skipped</div>` +
      `<p class="col-sub">what the relevance / drift / membrane gates admitted or skipped, and why</p>` +
      renderGateDecisions(data.gate_decisions) + `</div>`;
    return rootEl;
  }

  async function loadEpistemic(pid, rootEl) {
    const base = `/api/persona/${encodeURIComponent(pid)}`;
    let epi = null, gd = null;
    try {
      [epi, gd] = await Promise.all([
        root.fetch(`${base}/epistemic`).then((r) => r.json()),
        root.fetch(`${base}/gate_decisions?limit=100`).then((r) => r.json()),
      ]);
    } catch (e) { epi = { provenance: {}, gates: [] }; gd = { decisions: [], available: false }; }
    const data = Object.assign({ provenance: {}, gates: [] }, epi || {}, { gate_decisions: gd || { decisions: [], available: false } });
    mount(rootEl, data);
    return data;
  }

  function mockData() {
    return {
      provenance: { READ: 4200, INFERRED: 820, HUMAN_CONFIRMED: 41, TESTED: 12, never_confirmed: 380, stale: 90 },
      calibration_bound: null, calibration_available: false,
      gates: [
        { id: "RQ-E01", title: "extraction integrity", status: "partial" },
        { id: "RQ-E02", title: "contradiction typing", status: "pending" },
        { id: "RQ-E12", title: "executable science", status: "contested" },
        { id: "RQ-E13", title: "SFT vs RL", status: "gated" },
      ],
      gate_decisions: { available: true, decisions: [
        { candidate_id: "clm_x", title: "SLC7A11 ↑ under NRF2", gate: "membrane", decision: "admit", reason: "verbatim span + KG support agree", score: 0.86, at: "2026-07-12T22:40Z" },
        { candidate_id: "clm_y", title: "vague claim", gate: "relevance", decision: "skip", reason: "off-topic for active question", score: 0.12, at: "2026-07-12T22:41Z" },
      ] },
    };
  }

  const API = { renderProvenance, renderGates, renderCalibration, renderGateDecisions, mount, loadEpistemic, mockData };
  root.PEpistemic = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
})(typeof window !== "undefined" ? window : globalThis);
