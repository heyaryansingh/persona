# PRD-33 — Reviewer confidence report card

> **Owner lane:** 4 (Legibility) · **Status:** DRAFT · **Autonomy:** Balanced · **Depends on:** FC-3 (`kg.provenance`, `kg.provenance_breakdown` — Lane 2, live), FC-5 (`calibrate.admit_decision` — Lane 2, live), FC-6 (`retraction.contamination` — Lane 3, live but dead-code until first consumer), FC-10 (`kg.causal_tier` — Lane 2, **pending PRD-12**), FC-2 (`kg.contradictions` — Lane 2, live). Backlog #98.

---

## 0. Summary + capability

A single per-conclusion **"should I trust this"** card. A reviewer opening any belief/conclusion sees one compact panel that answers the trust question at a glance by *collecting already-computed server signals* — nothing is recomputed, nothing is invented client-side:

| Field | Meaning | Source (already computed) |
|---|---|---|
| `tier` | provenance state | FC-3 `kg.provenance(claim_id).provenance` (+ `anchored`) |
| `independent_labs` | distinct-lab support | FC-3 `kg.provenance(claim_id).independent_sources` |
| `calibrated_p` | routing probability | FC-5 `calibrate.admit_decision(candidate).calibrated_p` |
| `calibration_bin` | which PRD-15 reliability decile | deterministic decile of `calibrated_p` |
| `causal_tier` | strongest grounded causal cue | FC-10 `kg.causal_tier(claim_id).tier` (pending) |
| `contaminated` | rests on a retracted source | FC-6 `retraction.contamination(claim_id).contaminated` |
| `open_contradictions` | unresolved sign collisions on this claim | FC-2 `kg.contradictions()` filtered to `claim_id` |
| `overall_band` | documented deterministic rollup | worst-wins over the fields above (no model) |

**Capability:** legibility only — turns six existing gate outputs into one honest, auditable trust card. The `overall_band` is a **documented deterministic rollup** whose every threshold is *imported from the gate that owns it* (FC-5's `_P_COMMIT`/`_P_REJECT`/`_MIN_INDEP_COMMIT`), so the card introduces **no new metric and no new cut-point**. Every field on the card links back to the surface that produced it (provenance page, calibration panel, retraction watcher, contradiction inbox). This is the PRD-00 §5 "scale of reading, discipline of believing" story compressed to one glance.

---

## 1. File ownership (disjoint)

| File | Ownership | Change |
|---|---|---|
| `persona/api/report_card.py` | **Lane 4, NEW** | The pure aggregation function `report_card(claim_id, *, kg=None, contamination_fn=None)` + `overall_band(...)` + `calibration_bin(...)`. Offline, no network, injectable deps for tests. |
| `persona/api/app.py` | **Lane 4** (new route only) | One route `GET /api/persona/{pid}/report_card/{claim_id}` (mirrors the `provenance` route at `app.py:608`). |
| `persona/api/static/index.html` | **Lane 4** (new surface only) | One card component rendered on the existing conclusion/belief detail (the claim node inspector — see `graph_node` `app.py:592`, `kg.node` `kg.py:627` `kind=="claim"`). |
| `persona/api/static/js/*.js` | **Lane 4** (new render fn only) | Fetch + render the card; append to the existing claim-detail render path. |
| `tests/test_report_card.py` | **Lane 4, NEW** | Property test (RQ = trivial). |

**Boundary files owned by other lanes — READ-ONLY here, decoupled by FC:**
- `persona/memory/kg.py` (Lane 2) — consumed via **FC-3** (`provenance`, `contradictions`) and **FC-10** (`causal_tier`). Not edited.
- `persona/memory/calibrate.py` (Lane 2) — consumed via **FC-5** (`admit_decision`). Not edited.
- `persona/ingest/retraction.py` (Lane 3) — consumed via **FC-6** (`contamination`). Not edited.

No source file owned by another lane is modified. The card is a strict downstream reader.

---

## 2. FCs provided / consumed + CCP

### PROVIDES — **FC-25 (Lane 4), new `persona/api/report_card.py`** — CONTRACT CHANGE PROPOSAL **CCP-33a** (new FC; needs master ratify + Lane 4 self-ack)

```python
report_card.report_card(claim_id: str, *, kg=None, contamination_fn=None) -> dict
# -> {
#   claim_id: str,
#   tier: str,                    # provenance state: READ|INFERRED|HUMAN_CONFIRMED|TESTED (FC-3)
#   anchored: bool,               # FC-3 (a pinned belief)
#   independent_labs: int,        # FC-3 independent_source_count
#   calibrated_p: float,          # FC-5 admit_decision.calibrated_p (NOT recomputed here)
#   calibration_bin: int,         # 0..9 decile of calibrated_p (PRD-15 reliability bin index)
#   causal_tier: str | None,      # FC-10 kg.causal_tier(claim_id).tier; None until FC-10 lands
#   contaminated: bool,           # FC-6 retraction.contamination(claim_id).contaminated
#   open_contradictions: int,     # FC-2 count of live CONTRADICTS pairs touching claim_id
#   overall_band: str,            # 'trusted'|'provisional'|'caution'|'untrusted' — deterministic rollup
#   band_reason: str,             # human-readable "which floor set the band", for legibility
#   sources_available: {tier,calibration,causal,contamination,contradictions: bool}  # graceful degradation flags
# }

report_card.calibration_bin(calibrated_p: float) -> int         # int(p*10) clamped 0..9
report_card.overall_band(*, tier, anchored, independent_labs, calibrated_p,
                         contaminated, open_contradictions) -> tuple[str, str]  # (band, reason)
```

**Consumes:** FC-3, FC-5, FC-6, FC-10, FC-2 (all read-only). **No FC change to any consumed contract** — pure downstream aggregation.

**CCP-33a (frozen intent):** `overall_band` is a *documented deterministic rollup*, not a score. It reuses `calibrate._P_COMMIT` (0.70), `calibrate._P_REJECT` (0.40) and `calibrate._MIN_INDEP_COMMIT` (2) **by import**, never by re-declaration, so the card can never drift from the admission gate it summarizes. If those constants move, the card moves with them. No new numeric threshold is introduced by this PRD.

---

## 3. Features

### F33.1 — `report_card(claim_id)` pure aggregator (FC-25)

**Problem & evidence.** The trust signals a reviewer needs already exist but are scattered across five endpoints: provenance is at `app.py:608` (`kg.provenance`, `kg.py:278` returns `provenance`, `anchored`, `independent_sources`); calibration routing is `calibrate.admit_decision` (`calibrate.py:50`, returns `calibrated_p`); contamination is `retraction.contamination` (`retraction.py:93`, returns `{contaminated, path}`); contradictions are `kg.contradictions` (`kg.py:261`, returns pairs with `pos_claim`/`neg_claim`); causal tier will be `kg.causal_tier` (FC-10, PRD-12, `PRD-12 §FC-10`). A reviewer today must open five surfaces and hold the join in their head. Backlog #98 asks for the join, once, server-side.

**Design.**
- New file `persona/api/report_card.py`. `report_card(claim_id, *, kg=None, contamination_fn=None)`:
  1. `kg = kg or get_kg()` (`memory.membrane.get_kg`, `membrane.py:18`). If `kg is None`, return a card with all `sources_available=False` and `overall_band='untrusted'`, `band_reason="belief store unavailable"`.
  2. `prov = kg.provenance(claim_id)` (FC-3) → `tier=prov["provenance"]`, `anchored=prov["anchored"]`, `independent_labs=prov["independent_sources"]`. Empty dict ⇒ claim not found ⇒ `sources_available.tier=False`.
  3. Build the FC-5 candidate **from those same provenance fields** (no re-derivation of evidence): `candidate = {"provenance": tier, "anchored": anchored, "independent_source_count": independent_labs, "support_count": len(prov["sources"])}`; `dec = calibrate.admit_decision(candidate)` → `calibrated_p = dec["calibrated_p"]`. (We read the calibrator's own `calibrated_p`; we do not invent one.)
  4. `calibration_bin = calibration_bin(calibrated_p)` — deterministic decile, the PRD-15 reliability-panel bucket a claim lands in.
  5. `causal_tier`: `getattr(kg, "causal_tier", None)` — if present (FC-10 landed) call it, else `None` + `sources_available.causal=False`. (PRD-12 pending; renders against fixture until then.)
  6. `contaminated = (contamination_fn or retraction.contamination)(claim_id, kg=kg)["contaminated"]` (FC-6), import-guarded (`retraction.py` is dead-code until a consumer wires it — PRD-00 §FC-6 note — this PRD is a consumer; guard so an import failure degrades, never crashes).
  7. `open_contradictions = sum(1 for c in kg.contradictions(limit=500) if claim_id in (c["pos_claim"], c["neg_claim"]))` — live-only (the `contradictions` query already filters `valid_to IS NULL`, `kg.py:266`).
  8. `overall_band, band_reason = overall_band(...)`.
- Each block is individually try-guarded and sets its `sources_available.<x>` flag; a missing signal degrades the card, never 500s it (PRD-00 §5 honest uncertainty).

**`overall_band` — the documented deterministic rollup (worst-wins floors):**
```
1. contaminated                         -> 'untrusted'    ("rests on a retracted source")
2. anchored AND not contaminated        -> 'trusted'      ("human/tested anchor")   # FC-3 pin dominates
3. open_contradictions >= 1             -> 'caution'      ("N unresolved contradictions")  # cap, not floor-to-untrusted: a collision is a question, not a disproof (PRD-11)
4. calibrated_p >= _P_COMMIT (0.70)
      AND independent_labs >= _MIN_INDEP_COMMIT (2)  -> 'trusted'
5. calibrated_p <  _P_REJECT (0.40)     -> 'caution'
6. otherwise                            -> 'provisional'
```
Rules are evaluated top-to-bottom; the **first** matching rule sets the band and `band_reason`. Every constant is imported from `persona.memory.calibrate` — none is declared here. `causal_tier` is **displayed but does NOT enter the band** (it is a language-licensing signal per PRD-12, not a trust score — folding it in would double-count and conflate "is the phrasing licensed" with "should I trust the result"; kept as a separate honest badge). Documented in a module docstring so a skeptical reviewer can trace every band to its rule.

**Epistemic guardrails.**
- **No client invention.** The route returns the assembled dict; the browser only renders it. `calibrated_p` is the calibrator's own output, never recomputed in JS.
- **No new metric / no new cut-point.** Every threshold is an imported FC-5 constant; the band is a rollup, explicitly not a model judgment (CCP-33a).
- **Provenance authority preserved (PRD-00 §5).** An `INFERRED` or `READ` tier is never shown with the visual weight of `HUMAN_CONFIRMED`/`TESTED`; the card carries `tier` + `anchored` verbatim so the UI styles them distinctly (F33.2).
- **Graceful degradation, not fabrication.** A pending/absent signal (FC-10 today) yields `None` + `sources_available=False`, never a placeholder number.
- **Read-only.** No belief is mutated; mirrors the `provenance`/`inbox/dossier` read-only contract (`app.py:643` "reading this never mutates a belief").

**Required experiment.** **Trivial** (RQ = trivial, pre-assigned). Property test only (F33's acceptance) — the card is pure aggregation of already-validated signals; it introduces no modeled quantity to calibrate. No RQ-E id consumed.

**Acceptance + ONE runnable check.**
- Acceptance: for a fixture KG, every card field equals its source signal read independently; `overall_band` obeys the documented floors; a missing signal sets `sources_available.<x>=False` without raising.
- Runnable check: `python -m pytest tests/test_report_card.py -q` — asserts (a) `tier/independent_labs` match `kg.provenance` directly; (b) `calibrated_p` equals `calibrate.admit_decision(candidate)["calibrated_p"]`; (c) a contaminated fixture ⇒ `overall_band=='untrusted'`; (d) an anchored clean fixture ⇒ `'trusted'`; (e) a claim in a `contradictions` pair ⇒ `open_contradictions>=1` and band capped at `'caution'`; (f) `causal_tier is None` when the KG has no `causal_tier` attr, with `sources_available.causal is False`.

**Effort.** S (one pure module ~70 lines + one route + one property test).

**Deps.** FC-3, FC-5, FC-2 (live today → real immediately). FC-6 (live module, this PRD is first consumer → wire + guard). FC-10 (pending PRD-12 → fixture/`None` until it lands, then zero-change pickup via `getattr`).

---

### F33.2 — Route + UI card on the conclusion/belief detail

**Problem & evidence.** The claim detail surface (`kg.node` `kg.py:627` for `kind=="claim"`, served via `graph_node` `app.py:592`) shows provenance + sources but no consolidated trust verdict. Reviewers asked (backlog #98) for a one-glance answer beside the conclusion.

**Design.**
- **Route:** `GET /api/persona/{pid}/report_card/{claim_id}` in `app.py` — body identical in shape to the `provenance` route (`app.py:608`): `with context.use(_p(pid)): return report_card(claim_id)`. No new persona state.
- **UI:** a `report-card` component appended to the existing claim inspector (the panel that already renders `graph_node`/`provenance`). No new tab, no new screen (per instruction). Layout: `overall_band` as the headline chip (color: one accent for trusted, muted for provisional, warn for caution/untrusted — reuse the existing palette, PRD-00 §6), then a compact row of the six sub-signals, each linking to its owning surface (tier→provenance page, contradictions→inbox, contaminated→retraction watcher). Pending signals render as a greyed "—" with a "not yet computed" tooltip (honest uncertainty, PRD-00 §5). Motion: none (static panel; PRD-00 §5 "motion only for real state change").

**Epistemic guardrails.** UI renders server fields verbatim; no JS-side thresholding or number synthesis. `tier` badges keep the confirmed-vs-inferred visual distinction. `band_reason` is shown as the card's subtitle so the verdict is always self-explaining.

**Required experiment.** Trivial (covered by F33.1's property test; the route is a one-line pass-through and the card is presentational).

**Acceptance + ONE runnable check.**
- Acceptance: hitting the route for a seeded claim returns the F33.1 dict; the card renders on the claim detail with each sub-signal linked and pending signals greyed.
- Runnable check: `curl -s localhost:8000/api/persona/<pid>/report_card/<claim_id>` returns JSON whose keys equal the FC-25 contract (assert in the same `tests/test_report_card.py` via FastAPI `TestClient`).

**Effort.** S (one route + one component).

**Deps.** F33.1.

---

## 4. Sequencing

1. **F33.1** first — the pure `report_card.py` aggregator + property test, built against fixture KGs (contract-first, PRD-00 §7 "build every screen against fixtures first"). Green with FC-3/FC-5/FC-2 today; FC-6 wired-and-guarded; FC-10 stubbed via `getattr`.
2. **F33.2** — route + UI card, pass-through over F33.1.
3. **FC-10 pickup** — when PRD-12 lands `kg.causal_tier`, the `getattr` path activates with zero code change; flip the fixture test's causal branch to assert the real tier.

Repo stays runnable at every step (the card degrades, never blocks).

---

## 5. Test plan

`tests/test_report_card.py` (Lane 4, new; no framework beyond pytest + FastAPI `TestClient`):
- **Field fidelity:** each card field `==` its source read done independently on the same fixture KG (`tier`, `independent_labs` vs `kg.provenance`; `calibrated_p` vs `calibrate.admit_decision`).
- **Band floors:** one fixture per rule (contaminated→untrusted; anchored-clean→trusted; contradiction→caution cap; strong p+labs→trusted; p<0.40→caution; middle→provisional). Assert `band` and that `band_reason` names the firing rule.
- **Deterministic bin:** `calibration_bin(p)==min(9, int(p*10))` across `p∈{0.0,0.39,0.4,0.7,0.999,1.0}`.
- **Graceful degradation:** KG without `causal_tier` attr ⇒ `causal_tier is None`, `sources_available.causal is False`, no raise; `kg is None` ⇒ full `untrusted` card, no raise.
- **Threshold provenance:** assert the module imports `_P_COMMIT/_P_REJECT/_MIN_INDEP_COMMIT` from `persona.memory.calibrate` (guards against a re-declared constant drifting from the gate).
- **Read-only:** running `report_card` twice leaves `kg.stats()` unchanged.

Reuses the existing KG fixture harness in `tests/` (no new fixtures infrastructure).

---

## 6. Open questions

1. **CCP-33a ratify:** FC-25 is a new contract id (pre-assigned). Needs master ratify + Lane 4 self-ack. No other lane is impacted (strict downstream reader) — expected trivial approval.
2. **Band vocabulary:** `trusted/provisional/caution/untrusted` proposed. Confirm these four labels don't collide with existing UI status words (PRD-11 contradiction-gold, PRD-15 calibration panel). If a shared vocabulary exists, adopt it verbatim rather than mint new labels.
3. **`open_contradictions` cost:** `kg.contradictions(limit=500)` + client-side filter is O(edges); fine at demo scale. If the graph grows, a targeted `kg.open_contradiction_count(claim_id)` would be a one-line FC-3 addition (Lane 2) — flagged, not built (YAGNI until measured).
4. **Causal tier in the band?** Kept out deliberately (F33.1 rationale). If reviewers want an unlicensed-causal-verb claim visibly de-trusted, that is a PRD-12 language-gate concern, not a trust-band change — revisit only if a benchmark (PRD-04) shows reviewers conflate the two.
