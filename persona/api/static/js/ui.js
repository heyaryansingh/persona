/* =========================================================================
   ui.js — shared render primitives for the Persona workbench (S3-owned)
   ---------------------------------------------------------------------------
   Standalone, framework-free. Exposed as `PUI` in the browser and as
   module.exports under node (so tests/test_fe_*.cjs can import it without a DOM).

   Design contract: docs/SCIENTIFIC_WORKBENCH_SPEC.md + AGENTS.md §5.
   - Every visible scientific status comes from the server. This module renders
     what it is given; it NEVER invents convergence, contradiction-truth,
     importance, value-of-information, or confidence.
   - Color never carries state alone: every state pairs an accent with TEXT and
     a shape/glyph (spec "Visual language").
   - Trace-integrity and scientific-review are NEVER one badge (spec acceptance).
   - Motion only on real state change, gated by prefers-reduced-motion.

   Namespaced `PUI` (not bare globals) so it cannot collide with app.js while
   both load pre-P0.4; after the P0.4 split this file owns these helpers.
   ========================================================================= */
(function (root) {
  "use strict";

  // ---- pure helpers (safe under node; no DOM) ----------------------------
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  const fmtTime = (iso) => {
    try {
      const d = new Date(iso);
      if (isNaN(d)) return "";
      const p = (n) => String(n).padStart(2, "0");
      return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
    } catch { return ""; }
  };

  // A missing/unknown server value renders as an explicit em dash — NEVER a
  // fabricated number. Callers pass raw server fields straight through here.
  const orDash = (v) => (v === 0 ? "0" : v == null || v === "" ? "—" : String(v));

  // ---- epistemic state → {label, cls, glyph} -----------------------------
  // Colours are CSS classes (defined in app.css), so this stays theme-driven.
  // Shape (glyph) + label guarantee state is legible without colour.
  const STATE = {
    observed:     { label: "observed",     cls: "st-observed",     glyph: "◎" },
    read:         { label: "read",         cls: "st-observed",     glyph: "▤" },
    corroborated: { label: "corroborated", cls: "st-corroborated", glyph: "◉" },
    tested:       { label: "tested",       cls: "st-tested",       glyph: "✓" },
    anchored:     { label: "anchored",     cls: "st-anchored",     glyph: "⚓" },
    inferred:     { label: "inferred",     cls: "st-inferred",     glyph: "∴" },
    rejected:     { label: "rejected",     cls: "st-rejected",     glyph: "✕" },
    // A sign collision is a CANDIDATE until reviewed — never a verdict.
    candidate:    { label: "candidate · unverified", cls: "st-candidate", glyph: "◈" },
  };
  const stateMeta = (s) => STATE[s] || { label: esc(s || "unknown"), cls: "st-unknown", glyph: "·" };

  const stateBadge = (s) => {
    const m = stateMeta(s);
    // glyph (shape) + label (text) + class (colour) — three redundant channels.
    return `<span class="pbadge ${m.cls}"><span class="pbadge-g" aria-hidden="true">${m.glyph}</span>${esc(m.label)}</span>`;
  };

  // Two SEPARATE chips — the spec forbids one badge conflating lineage & truth.
  const dualBadge = (traceIntegrity, scientificReview) => {
    const trace = String(traceIntegrity || "unknown");
    const sci = String(scientificReview || "unverified");
    const traceCls = trace === "passed" || trace === "verified" ? "tr-ok" : trace === "failed" ? "tr-bad" : "tr-unknown";
    const sciCls = { verified: "sc-verified", contested: "sc-contested", invalidated: "sc-bad", unverified: "sc-unverified" }[sci] || "sc-unverified";
    return (
      `<span class="dual"><span class="chip ${traceCls}" title="trace integrity — lineage, not truth">trace: ${esc(trace)}</span>` +
      `<span class="chip ${sciCls}" title="scientific review — separate from lineage">review: ${esc(sci)}</span></span>`
    );
  };

  // ---- motion gate -------------------------------------------------------
  // Motion only on real state change AND only when the user allows it.
  const motionOK = () => {
    try {
      return !(root.matchMedia && root.matchMedia("(prefers-reduced-motion: reduce)").matches);
    } catch { return false; }
  };

  // ---- thin DOM helper (browser only) ------------------------------------
  const setHTML = (elOrId, html) => {
    const node = typeof elOrId === "string" ? (root.document && root.document.getElementById(elOrId)) : elOrId;
    if (node) node.innerHTML = html;
    return node;
  };

  const API = { esc, clamp, fmtTime, orDash, STATE, stateMeta, stateBadge, dualBadge, motionOK, setHTML };

  root.PUI = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
})(typeof window !== "undefined" ? window : globalThis);
