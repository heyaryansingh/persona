/* =========================================================================
   verdict.js — The one Oracle-Verdict renderer (FC-8)         (S3 / Lane 4)
   ---------------------------------------------------------------------------
   Renders EVERY oracle's verdict (code-run: MR/DepMap/meta-analysis; lookup:
   LEGEND) with ONE honest card, per idea I1.4. The honesty rules live here, once.

   Non-negotiable rules (I1.4 §3 + §7), enforced by verdictState():
   - `applicable:false` → "not applicable" (NEVER a verdict — the skipped≠passed rule).
   - controls tripped / pipeline unhealthy → "quarantined" (name the failing control).
   - a code-run oracle with NO capsule hashes → "unverified computation" (fail loud).
   - `provenance:'abstain'` → "no call"; `high_stakes:true` → routes to a human.
   - a verdict is ALWAYS shown paired with its sensitivity (E12b lesson) — a headline
     with no sensitivity strip is a bug, so we render "sensitivity: —" loudly.
   - provenance drives authority: INFERRED/READ/abstain never get TESTED weight.
   Exposed as `PVerdict` (browser) + module.exports (node). Uses PUI (ui.js).
   ========================================================================= */
(function (root) {
  "use strict";
  const UI = root.PUI || (typeof require !== "undefined" ? require("./ui.js") : null);
  if (!UI) throw new Error("verdict.js requires ui.js (PUI)");
  const { esc, orDash } = UI;

  const _controlsTripped = (env) =>
    !!(env.controls && env.controls.tripped) ||
    !!(env.pipeline_health && env.pipeline_health.ok === false);

  const _isCodeRun = (env) =>
    env.provenance === "TESTED-provisional" || env.provenance === "INFERRED" || !!env.methods;

  const _hasCapsule = (env) =>
    !!(env.capsule && (env.capsule.input_sha256 || env.capsule.script_sha256 || env.capsule.sandbox_image_digest));

  // Primary honest state. Priority matters — not-applicable and quarantine must win
  // over any verdict; a missing capsule on a computed result must fail loud.
  function verdictState(env) {
    env = env || {};
    if (env.applicable === false) return "not_applicable";
    if (_controlsTripped(env)) return "quarantined";
    if (env.provenance === "abstain") return "no_call";
    if (_isCodeRun(env) && env.provenance !== "READ" && !_hasCapsule(env)) return "unverified_computation";
    if (env.high_stakes === true) return "needs_human";
    if (env.provenance === "READ") return "looked_up";
    if (env.provenance === "TESTED-provisional") return "tested_provisional";
    if (env.provenance === "INFERRED") return "inferred";
    return "unknown";
  }

  const STATE_LABEL = {
    not_applicable: "Not applicable",
    quarantined: "Quarantined",
    unverified_computation: "Unverified computation",
    no_call: "No call",
    needs_human: "Needs human",
    looked_up: "Looked up (not computed)",
    tested_provisional: "Tested · provisional",
    inferred: "Inferred",
    unknown: "Unknown",
  };
  // authority class — INFERRED/abstain/READ never get the strong (tested) treatment.
  const STATE_CLASS = {
    not_applicable: "v-na", quarantined: "v-bad", unverified_computation: "v-bad",
    no_call: "v-weak", needs_human: "v-human", looked_up: "v-read",
    tested_provisional: "v-tested", inferred: "v-weak", unknown: "v-weak",
  };

  function _sensitivityStrip(env) {
    const s = env.sensitivity;
    if (s && (s.summary || s.text)) return `<div class="v-sens">sensitivity: ${esc(s.summary || s.text)}</div>`;
    if (s && typeof s === "string") return `<div class="v-sens">sensitivity: ${esc(s)}</div>`;
    // A verdict with no sensitivity is a bug — say so loudly, don't hide it.
    return `<div class="v-sens v-sens-missing">sensitivity: — (not reported)</div>`;
  }

  function _capsule(env) {
    const c = env.capsule || {};
    const has = _hasCapsule(env);
    if (!has) {
      // code-run with no hashes = unverified; lookup oracles legitimately have none.
      return _isCodeRun(env) && env.provenance !== "READ"
        ? `<div class="v-cap v-cap-missing">no reproduction capsule — unverified computation</div>` : "";
    }
    const h = (x) => esc(String(x || "").slice(0, 12));
    return (
      `<div class="v-cap"><span class="v-cap-h">reproduce</span>` +
      `<span class="mono">in ${h(c.input_sha256)}</span>` +
      `<span class="mono">code ${h(c.script_sha256)}</span>` +
      `<span class="mono">img ${h(c.sandbox_image_digest)}</span>` +
      (c.session_id ? `<a class="v-replay" data-session="${esc(c.session_id)}">open session ↦</a>` : "") +
      `</div>`
    );
  }

  function renderVerdict(env) {
    env = env || {};
    const st = verdictState(env);
    const headline = st === "not_applicable"
      ? esc(orDash((env.methods && env.methods.reason) || env.reason))
      : esc(orDash(env.verdict || env.status));
    const parts = [];
    parts.push(`<div class="verdict ${STATE_CLASS[st]}" data-state="${st}">`);
    parts.push(`<div class="v-top"><span class="v-state">${esc(STATE_LABEL[st])}</span>` +
      (env.advisory !== false && env.advisory !== undefined
        ? `<span class="v-adv" title="advisory until this oracle's RQ gate passes">advisory</span>` : "") +
      `</div>`);
    if (st === "not_applicable") {
      parts.push(`<div class="v-na-body">this oracle did not apply${headline && headline !== "—" ? ` — ${headline}` : ""}</div>`);
    } else {
      parts.push(`<div class="v-headline">${headline}</div>`);
      parts.push(_sensitivityStrip(env));
      if (st === "quarantined") {
        const ctl = (env.controls && env.controls.failing) || (env.pipeline_health && env.pipeline_health.failing) || "a control";
        parts.push(`<div class="v-quar">⚠ control tripped: ${esc(ctl)} — verdict held inconclusive</div>`);
      }
      if (st === "needs_human") {
        parts.push(`<div class="v-needs">high-stakes — routed to a human${env.handoff_id ? `` : ""}` +
          `${env.handoff_id ? ` <button class="v-handoff" data-handoff="${esc(env.handoff_id)}">open dossier</button>` : ""}</div>`);
      }
      parts.push(_capsule(env));
    }
    parts.push(`</div>`);
    return parts.join("");
  }

  // Frozen envelope matrix — the acceptance fixture (I1.4 §5). One per honest state.
  function mockEnvelopes() {
    return {
      not_applicable: { applicable: false, methods: { reason: "no eligible instruments for MR" }, provenance: "abstain" },
      quarantined: { applicable: true, verdict: "β = -0.11", sensitivity: { summary: "flips under HC3" }, provenance: "TESTED-provisional", capsule: { input_sha256: "aa11", script_sha256: "bb22" }, controls: { tripped: true, failing: "negative-control gene set" } },
      unverified_computation: { applicable: true, verdict: "β = +0.07", sensitivity: { summary: "n/a" }, provenance: "TESTED-provisional", methods: { model: "OLS" } },
      no_call: { applicable: true, provenance: "abstain", verdict: "insufficient overlap" },
      needs_human: { applicable: true, verdict: "compensatory activation likely", sensitivity: { summary: "holds 3/3" }, provenance: "TESTED-provisional", high_stakes: true, handoff_id: "hf_001", capsule: { input_sha256: "cc33", script_sha256: "dd44", sandbox_image_digest: "ee55", session_id: "sess_1" } },
      looked_up: { applicable: true, provenance: "READ", verdict: "GPX4 is a known ferroptosis regulator", source_doi: "10.1000/x", sensitivity: { summary: "curated lookup" } },
      tested_provisional: { applicable: true, verdict: "score declines with severity", sensitivity: { summary: "holds under 3/3 checks" }, provenance: "TESTED-provisional", capsule: { input_sha256: "ff66", script_sha256: "0077", sandbox_image_digest: "8899", session_id: "sess_2" } },
    };
  }

  const API = { verdictState, renderVerdict, mockEnvelopes, STATE_LABEL };
  root.PVerdict = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
})(typeof window !== "undefined" ? window : globalThis);
