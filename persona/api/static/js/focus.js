/* =========================================================================
   focus.js — Focus view (T3.1) + blinded review card (T3.2)   (S3-owned)
   ---------------------------------------------------------------------------
   Standalone + mock-driven so it is drop-in-ready the moment Wave 0 (P0.3)
   clears. Pure string builders (node-testable) + a thin DOM mount. Uses PUI
   (ui.js). Exposed as `PFocus` in the browser, module.exports under node.

   Contracts: docs/SCIENTIFIC_WORKBENCH_SPEC.md (Focus + Review), S0 board §A(v2)
   blinded conflict-review record, S0 board §B qualifier fields.

   Epistemic-debt rules (S3 inventory of the old app.js — do NOT reproduce):
   - No client-side verdict mapping. A sign collision stays "candidate ·
     unverified"; it never gets a rising/collapsing colour-as-conclusion.
   - Effect signs appear ONLY inside a packet as that source's own stated
     direction, always tagged unverified — never a standalone verified ↑/↓.
   - No client-invented metric. Missing server fields render "—", not a number.
   - side_order is the server's sealed randomisation: packets are rendered in
     SERVED order; the UI never reorders them and never implies A = "positive".
   ========================================================================= */
(function (root) {
  "use strict";
  const UI = root.PUI || (typeof require !== "undefined" ? require("./ui.js") : null);
  if (!UI) throw new Error("focus.js requires ui.js (PUI)");
  const { esc, fmtTime, orDash, stateBadge, dualBadge, motionOK } = UI;

  // Event glyphs mirror the existing notebook vocabulary for continuity.
  const EGLYPH = {
    thought: "∴", read: "▤", observe: "◎", claim: "◆", belief_update: "⟳",
    contradiction: "◈", artifact: "✦", synthesis: "❋", tool: "⌥", say: "›",
    reply: "‹", escalate: "!", boot: "●", error: "✕", seed: "✧", coherence: "~",
  };
  // Orchestration/telemetry noise — belongs in the collapsed diagnostics drawer,
  // NOT in the notebook of real scientific moves (spec Focus §1).
  const NOISE = new Set(["spawn", "lease", "schedule", "cost", "control"]);
  const MAX_MSG = 240;

  const isRealMove = (e) => e && !NOISE.has(e.type);
  // Dedup key: real event id if present, else a stable composite (S2 stream-dedup report).
  const eventKey = (e) => (e && (e.id || `${e.ts}|${e.type}|${e.actor}|${e.message}`)) || "";
  const _seen = new Set();

  // ---- Focus: living notebook (real state changes only) ------------------
  function notebookRow(e) {
    const full = String(e.message || "");
    const short = full.length > MAX_MSG ? full.slice(0, MAX_MSG - 2) + "…" : full;
    const expand = full.length > MAX_MSG
      ? ` data-full="${esc(full)}" onclick="this.textContent=this.getAttribute('data-full')" style="cursor:zoom-in"`
      : "";
    return (
      `<div class="frow ev-${esc(e.type || "thought")}${e.parent_id ? " child" : ""}">` +
      `<span class="ft">${esc(fmtTime(e.ts))}</span>` +
      `<span class="fg" aria-hidden="true">${EGLYPH[e.type] || "·"}</span>` +
      `<span class="fmsg"${expand}>${esc(short)}</span>` +
      `<span class="fwho">${e.actor ? "· " + esc(e.actor) : ""}</span>` +
      `</div>`
    );
  }

  function renderNotebook(events) {
    const rows = (events || []).filter(isRealMove).map(notebookRow).join("");
    return rows || `<div class="fempty">no moves yet — Persona is reading.</div>`;
  }

  // ---- Focus: next action (server-owned; nothing invented) ---------------
  function renderNextAction(a) {
    a = a || {};
    return (
      `<div class="nextact">` +
      `<div class="na-h">Next action</div>` +
      `<div class="na-what">${esc(orDash(a.what || a.label))}</div>` +
      `<dl class="na-grid">` +
      `<dt>why</dt><dd>${esc(orDash(a.reason))}</dd>` +
      `<dt>expected evidence gain</dt><dd>${esc(orDash(a.expected_gain))}</dd>` +
      `<dt>cost ceiling</dt><dd class="mono">${esc(orDash(a.cost_ceiling))}</dd>` +
      `<dt>stop rule</dt><dd>${esc(orDash(a.stop_rule))}</dd>` +
      `</dl>` +
      (a.mode ? `<div class="na-mode">mode: ${esc(a.mode)} · budget shown before start</div>` : "") +
      `</div>`
    );
  }

  // ---- Review: blinded candidate-conflict card (§A v2) -------------------
  function qualifierRow(q) {
    q = q || {};
    const cell = (k, v) => `<div class="ql"><span class="ql-k">${k}</span><span class="ql-v">${esc(orDash(v))}</span></div>`;
    return (
      `<div class="quals">` +
      cell("population", q.population) +
      cell("model", q.model_system) +
      // this source's OWN stated direction — intrinsic evidence, tagged unverified.
      cell("stated direction", q.direction) +
      cell("magnitude", q.magnitude) +
      cell("timepoint", q.timepoint) +
      cell("n", q.n) +
      `</div>`
    );
  }

  // Rendered in SERVED order. "Source A/B" is the sealed randomisation; the card
  // never says which is the KG's canonical positive.
  function packet(label, p) {
    p = p || {};
    const src = p.source || {};
    return (
      `<div class="packet">` +
      `<div class="pk-h">Source ${esc(label)}</div>` +
      `<blockquote class="pk-span">${esc(orDash(p.exact_span))}</blockquote>` +
      `<div class="pk-src mono">${esc(orDash(src.title))}${src.doi ? " · " + esc(src.doi) : ""}` +
      `${src.hash ? ` <span class="pk-hash">${esc(String(src.hash).slice(0, 12))}</span>` : ""}</div>` +
      qualifierRow(p.qualifiers) +
      `</div>`
    );
  }

  const LABELS = [
    ["extraction_error", "Extraction error", "a stored quote or its sign does not match the source"],
    ["true_refutation", "True refutation", "matched qualifiers, directions genuinely disagree"],
    ["context_divergence", "Context divergence", "different population/tissue/stage explains the difference"],
    ["insufficient_evidence", "Insufficient evidence", "not enough to classify yet"],
  ];

  function renderReviewCard(asg) {
    asg = asg || {};
    const why = asg.why_raised || {};
    const gaps = (asg.missing_context_fields || []).map((g) => `<span class="gap">${esc(g)}</span>`).join("");
    const checks = (asg.discriminating_checks || asg.next_checks || [])
      .map((c) => `<li>${esc(c)}</li>`).join("");
    const buttons = LABELS.map(([id, name, help]) =>
      `<button type="button" class="lbl" data-label="${id}" title="${esc(help)}">${esc(name)}</button>`
    ).join("");
    return (
      `<div class="review" data-assignment="${esc(orDash(asg.assignment_id))}">` +
      `<div class="rv-top"><span class="rv-tag">candidate conflict · unverified</span>` +
      dualBadge("passed", "unverified") + `</div>` +
      `<p class="rv-note">Labeling this never changes a belief. The system's canonical sign is hidden; sources are shown in a random order.</p>` +
      `<div class="rv-why"><b>Why raised:</b> ${esc(orDash(why.trigger))}` +
      (why.what_it_does_not_mean ? `<div class="rv-caveat">${esc(why.what_it_does_not_mean)}</div>` : "") +
      `</div>` +
      `<div class="packets">${packet("A", asg.packet_A)}${packet("B", asg.packet_B)}</div>` +
      (gaps ? `<div class="rv-gaps"><span class="rv-lab">missing context</span>${gaps}</div>` : "") +
      (checks ? `<div class="rv-checks"><span class="rv-lab">cheapest discriminating checks</span><ol>${checks}</ol></div>` : "") +
      `<div class="rv-actions">${buttons}</div>` +
      `<textarea class="rv-rationale" placeholder="rationale (required with a label)"></textarea>` +
      `</div>`
    );
  }

  // Build the §A(v2) ReviewLabel POST body. Pure — no KG mutation, no network
  // here; the caller (or live wiring) does the POST to /api/review/label.
  function buildLabelBody(asg, label, rationale, now) {
    return {
      assignment_id: asg.assignment_id,
      reviewer_id: asg.reviewer_id,
      batch_id: asg.batch_id,
      conflict_id: asg.conflict_id,
      schema_version: asg.schema_version,
      label,
      rationale: rationale || "",
      ts: now || null, // wall-clock stamped by caller/live wiring, not here
    };
  }

  // ---- browser mount (demo / drop-in) ------------------------------------
  function resetStream() { _seen.clear(); }   // call on persona switch

  function appendEvent(streamEl, e) {
    if (!streamEl || !isRealMove(e)) return;
    const k = eventKey(e); if (_seen.has(k)) return; _seen.add(k);   // dedup backfill/live overlap
    const wrap = root.document.createElement("div");
    wrap.innerHTML = notebookRow(e);
    const node = wrap.firstChild;
    // Motion ONLY here — a real state change just arrived — and only if allowed.
    if (motionOK()) node.classList.add("fresh");
    streamEl.appendChild(node);
    streamEl.scrollTop = streamEl.scrollHeight;
  }

  function mount(rootEl, data) {
    if (!rootEl) return;
    data = data || mockData();
    rootEl.innerHTML =
      `<section class="focus-col"><div class="col-h">Focus</div>` +
      renderNextAction(data.next_action) +
      `<div class="notebook" id="fnotebook">${renderNotebook(data.events)}</div></section>` +
      `<section class="review-col"><div class="col-h">Review</div>${renderReviewCard(data.assignment)}</section>`;
    // wire label buttons in the demo: log the POST body, never mutate anything.
    rootEl.querySelectorAll(".lbl").forEach((b) =>
      b.addEventListener("click", () => {
        const card = b.closest(".review");
        const rationale = card.querySelector(".rv-rationale").value;
        const body = buildLabelBody(data.assignment, b.dataset.label, rationale, new Date().toISOString());
        (root.console || console).log("[review label — would POST /api/review/label]", body);
      })
    );
    return rootEl;
  }

  // ---- mock fixtures (shapes mirror the real endpoints) ------------------
  function mockData() {
    return {
      events: [
        { ts: "2026-07-12T22:40:01Z", type: "read", actor: "reader-3", message: "Europe PMC: 'Nrf2 activation attenuates ferroptotic neuronal death' (2023)" },
        { ts: "2026-07-12T22:40:07Z", type: "claim", actor: "extractor", message: "proposed: SLC7A11 expression ↑ under NRF2 activation (exact span pinned)" },
        { ts: "2026-07-12T22:40:09Z", type: "observe", actor: "membrane", message: "admitted 1 claim (verbatim span OK); rejected 1 (non-exact quote)" },
        { ts: "2026-07-12T22:40:44Z", type: "contradiction", actor: "membrane", message: "candidate conflict: microglia/tau — opposite stored signs (UNVERIFIED)" },
        { ts: "2026-07-12T22:41:15Z", type: "tool", actor: "analyst", message: "ran OLS score~severity+age+sex on GSE1297 (offline Docker, $0)" },
        { ts: "2026-07-12T22:41:31Z", type: "artifact", actor: "analyst", message: "figure: adjusted β by severity + residual diagnostics (hash 7fe93d1e…)" },
        { ts: "2026-07-12T22:41:40Z", type: "belief_update", actor: "membrane", message: "computation marked TESTED (transcriptomic association only, not causal)" },
        { ts: "2026-07-12T22:42:02Z", type: "escalate", actor: "self", message: "needs human: cheapest discriminating step is a matched-qualifier re-extraction" },
      ],
      next_action: {
        what: "Re-extract population/tissue/stage for the microglia–tau candidate pair",
        reason: "Direction differs, but qualifiers are unmatched; a matched re-extraction may dissolve the conflict without any wet-lab work.",
        expected_gain: "resolves 1 candidate conflict → either extraction_error or a matched true_refutation",
        cost_ceiling: "$0 (cached sources, no paid model call)",
        stop_rule: "stop once both packets carry population + tissue + stage, or after 2 reader passes",
        mode: "Investigate",
      },
      assignment: {
        assignment_id: "a_9f3c1b7e",
        batch_id: "batch_2026-07-12_pilot",
        conflict_id: "cf_microglia_tau_0001",
        reviewer_id: "rv_opaque_7b21",
        schema_version: "A.v2",
        why_raised: {
          trigger: "same canonical subject/object pair with opposite stored effect signs",
          what_it_does_not_mean: "This sign collision is not evidence of a true scientific contradiction.",
        },
        packet_A: {
          exact_span: "microglial activation exacerbated tau pathology in the hippocampus of P301S mice",
          source: { title: "J. Neuroinflammation 2022", doi: "10.1186/s12974-022-xxxx", hash: "b8eadf94d9721c0a" },
          qualifiers: { population: "P301S mice", model_system: "in_vivo", direction: "+", magnitude: "large", timepoint: "9 mo", n: 12 },
        },
        packet_B: {
          exact_span: "depletion of microglia reduced tau seeding, indicating microglia drive tau spread",
          source: { title: "Neuron 2021", doi: "10.1016/j.neuron.2021.yyyy", hash: "6cdefce3d24409f1" },
          qualifiers: { population: "PS19 mice", model_system: "in_vivo", direction: "-", magnitude: "moderate", timepoint: "6 mo", n: 9 },
        },
        missing_context_fields: ["disease stage", "outcome definition", "comparator"],
        discriminating_checks: [
          "Confirm each stored quote is verbatim and its sign matches the source sentence.",
          "Compare population, tissue, stage, perturbation, dose, timepoint, outcome across both.",
          "Check source independence (shared cohort? corrections/retractions?).",
        ],
        review_options: ["extraction_error", "true_refutation", "context_divergence", "insufficient_evidence"],
      },
    };
  }

  const API = {
    renderNotebook, renderNextAction, renderReviewCard, buildLabelBody,
    appendEvent, resetStream, eventKey, mount, mockData, isRealMove, EGLYPH, NOISE,
  };
  root.PFocus = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
})(typeof window !== "undefined" ? window : globalThis);
