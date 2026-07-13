# PRD-31 — Evidence-tier upgrade pathway

> **Owner lane:** 4 · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (read-only; suggests actions, never upgrades a tier or writes the KG) · **Depends-on:** FC-3 (`kg.provenance`, provenance/independence/anchor fields — PRD-02), the codified admission thresholds in `persona/memory/calibrate.py` (FC-5, PRD-02), the cost vocabulary in `persona/analysis/value_queue.py` (FC-4, PRD-03). Provides **FC-23**.

---

## 0. Summary + capability unlocked

Backlog **#125**. Persona already *derives* a per-belief epistemic state on the server — `app.py:565–567` maps every belief to `anchored | tested | corroborated | observed` from its provenance, independent-lab count, and anchor flag, and the UI renders that state (`index.html:2001,2010`) and the raw provenance chain (`prov()` modal, `index.html:1393–1410`). What a user **cannot** see is the *forward* question every working scientist asks about a belief: **"what exactly would it take to trust this more?"** The state is shown; the **path off it** is not.

FC-23 answers that deterministically. For any claim, `upgrade_pathway(claim_id)` reports its current tier on the codified ladder **READ/INFERRED → corroborated → TESTED → anchored**, the next rung up, and the *exact* evidence that rung requires — e.g. *"one independent replication + a public-data test away from TESTED"* — plus the single cheapest concrete action that moves it. Every number is read straight from the rules the membrane and anchor policy **already enforce** (`calibrate._MIN_INDEP_COMMIT`, `kg.CONFIRMED_PROVENANCE`, `kg.anchor`), so the pathway can never invent a requirement the system doesn't actually impose.

**Capability unlocked:** the belief-detail panel stops being a static verdict and becomes a *to-do list against the epistemic ladder*. And because a cheap upgrade action (a public-data code-run test) is expressed in the same `run_action` vocabulary as the FC-4 value-of-information queue, "the cheapest way to trust belief X more" becomes a first-class, dispatchable VoI item — closing the loop from *what do I believe* → *what should I do next* on a per-belief basis.

---

## 1. File ownership (disjoint)

| File | New? | Lane | Role |
|---|---|---|---|
| `persona/analysis/tiers.py` | **new** | **4** (new-file rule, §4 of PRD-00: a new non-colliding file is owned by the lane whose PRD creates it, regardless of directory) | the pure derivation — tier ladder + `current_tier` + `upgrade_pathway` (FC-23) |
| `persona/api/app.py` | edit (additive) | 4 | one new read route `GET /upgrade_pathway/{claim_id}`; optional 3-line refactor of the inline tier map at `app.py:565–567` to call `tiers.current_tier` (same lane — removes the duplicate) |
| `persona/api/static/index.html` | edit (additive) | 4 | render the pathway inside the existing `prov()` belief-detail modal (`index.html:1393–1410`) |
| `tests/test_upgrade_pathway.py` | **new** | 4 | the property test (RQ = trivial; §5) |

**Boundary flag — `persona/analysis/tiers.py` sits in Lane 3's directory** (`analysis/`, owned by PRD-03) but is a **new, non-colliding file owned by Lane 4** per PRD-00 §4's new-file rule. It does not edit any Lane-3 file. It *imports* two read-only constants from sibling modules (see §2). It could be re-exported from `analysis/engine.py` (FC-4 facade) for symmetry, but `engine.py` is Lane-3-owned, so this PRD does **not** touch it — the route imports `from ..analysis.tiers import upgrade_pathway` directly. Flag for Lane 3 awareness only; no coordinated edit required.

**No source file is edited by two lanes.** Everything this PRD edits (`app.py`, `index.html`) and creates (`tiers.py`, the test) is Lane 4.

---

## 2. FCs provided / consumed

### Provided — **FC-23** (Lane 4, new `persona/analysis/tiers.py`)

```python
upgrade_pathway(claim_id: str, kg=None) -> {
    "claim_id":     str,
    "current_tier": str,          # one of TIER_ORDER (below), the server-derived state
    "provenance":   str,          # the raw provenance label (READ|INFERRED|TESTED|HUMAN_CONFIRMED|CORRECTED_EXTRACTION)
    "next_tier":    str | None,   # next rung up, or None if already anchored (top)
    "needed": [ {"kind": str, "count": int, "cost_tier": str} ],   # unmet requirements for next_tier
    "cheapest_action": {"kind": str, "cost_tier": str, "run_action": str | None} | None,
    "full_path": [ {"tier": str, "needed": [ ... ]} ],   # ADDITIVE: remaining rungs to anchored, for the "N steps to TESTED" phrasing
}
```

Also exported (public, reused by the `app.py` route and the test):

```python
TIER_ORDER = ("READ", "INFERRED", "corroborated", "TESTED", "anchored")   # ascending
current_tier(belief: dict) -> str          # pure; mirrors app.py:565–567 exactly, extended to split READ/INFERRED
```

- The **4 frozen keys** `{current_tier, next_tier, needed, cheapest_action}` match the pre-assigned FC-23 contract verbatim. `claim_id`, `provenance`, and `full_path` are **additive** (extra keys, allowed — like the FC-8 oracle envelope carries extra fields); `full_path` exists only so the panel can render the cumulative "*one independent replication + a public-data test away from TESTED*" phrasing from the task without a second call.
- `kg=None` defaults to the current persona's KG via `membrane.get_kg()`, injectable for the property test (same pattern as `value_queue(topic, kg=None)`).
- Read-only. No KG write, no model, no network. If `claim_id` is unknown, returns `{}` (mirrors `kg.provenance`'s empty-on-miss contract, `kg.py:289`).

### Consumed (read-only, verbatim — no contract change requested)

- **FC-3** — `kg.provenance(claim_id) -> {..., provenance, anchored, independent_sources, ...}` (`kg.py:278`). The single input record; carries every field the ladder needs.
- **`kg.CONFIRMED_PROVENANCE = ("HUMAN_CONFIRMED", "TESTED")`** (`kg.py:74`, public) — defines the TESTED / human-confirmed rungs.
- **`calibrate._MIN_INDEP_COMMIT = 2`** (`calibrate.py:23`) — the corroboration threshold. This is the *same* `2` that gates `kg.beliefs(min_independent=2)` (`kg.py:248`), `membrane.harvest(min_independent=2)` (`membrane.py:63`), and the calibrator's auto-commit floor (`calibrate.py:69`). Importing it is deliberate: **one source of truth**, so if the membrane's corroboration bar ever moves, the pathway moves with it and the property test (§5) proves they still agree.
- **`value_queue._COST_WEIGHT = {"public_data":1.0,"cheap_assay":3.0,"expensive":10.0}`** (`value_queue.py:17`) — the cost vocabulary, reused so `cheapest_action` ranks by the *same* cost model the VoI queue uses and its `run_action` slots straight into that queue (CCP-19a / FC-8 prefix rule).

**Private-name coupling (flagged):** `_MIN_INDEP_COMMIT` and `_COST_WEIGHT` are underscore-private. Importing them directly gives fail-loud drift (an `ImportError` if renamed) and zero duplication, which is what "must match the real rules" requires. If Lane 2 / Lane 3 prefer a public alias, that is a trivial one-line additive CCP (`MIN_INDEPENDENT_COMMIT = _MIN_INDEP_COMMIT` in `calibrate.py`; `COST_WEIGHT = _COST_WEIGHT` in `value_queue.py`) — see §6 Q1. Not blocking: this PRD ships against the private names with the drift guard below.

**No CONTRACT CHANGE PROPOSAL is required for FC-23 to land.** It only reads existing public/near-public surfaces.

---

## 3. Features

### F31.1 — Per-belief evidence-tier upgrade pathway (FC-23)

**Problem & evidence.** The server derives a belief's epistemic state but discards *how to improve it*. The derivation is real and already load-bearing in the UI:

```python
# app.py:565–567  — the codified ladder, computed but "read-only" to the user
state = ("anchored"     if belief.get("anchored") else
         "tested"       if belief.get("provenance") == "TESTED" else
         "corroborated" if belief.get("independent_sources", 0) >= 2 else "observed")
```

The rungs above `observed` each correspond to a concrete, codified admission/anchor rule:
- **corroborated** ⇔ `independent_source_count >= _MIN_INDEP_COMMIT` (`calibrate.py:23,69`; the membrane's belief threshold `kg.py:248`).
- **TESTED** ⇔ `provenance ∈ CONFIRMED_PROVENANCE` via a code-run oracle producing `TESTED-provisional` (FC-8 envelope, PRD-00 §4).
- **anchored** ⇔ a human sign-off flips `anchored=true` (`kg.anchor`, `kg.py:204`; `human_resolve`, `kg.py:225`) — the top; nothing auto-anchors (PRD-00 §2).

So the pathway is a **deterministic read** of rules that already exist — no new epistemics, no invented number. Research posture: this is the "legibility of the funnel" thesis (CLAUDE.md §5, "show the funnel, not just the output") applied to a single belief — surface the *discipline of believing* as an actionable ladder, not just a badge.

**Design.**

*New module `persona/analysis/tiers.py`:*

```python
from ..memory.kg import CONFIRMED_PROVENANCE
from ..memory.calibrate import _MIN_INDEP_COMMIT as MIN_INDEPENDENT   # single source of truth
from .value_queue import _COST_WEIGHT as COST_WEIGHT

TIER_ORDER = ("READ", "INFERRED", "corroborated", "TESTED", "anchored")
_BASE = {"READ", "INFERRED"}          # lateral provenance labels at the base rung
_CONFIRMED_PROV = set(CONFIRMED_PROVENANCE)   # {"HUMAN_CONFIRMED","TESTED"}

def current_tier(belief: dict) -> str:
    """Highest rung whose codified predicate holds. Mirrors app.py:565–567, split at the base
    so READ/INFERRED are reported distinctly. HUMAN_CONFIRMED (with or without the anchor flag)
    is human-owned → 'anchored' rung."""
    if belief.get("anchored") or belief.get("provenance") == "HUMAN_CONFIRMED":
        return "anchored"
    if belief.get("provenance") == "TESTED":
        return "TESTED"
    if int(belief.get("independent_sources") or belief.get("independent_source_count") or 0) >= MIN_INDEPENDENT:
        return "corroborated"
    return "INFERRED" if belief.get("provenance") == "INFERRED" else "READ"

def upgrade_pathway(claim_id, kg=None) -> dict: ...
```

*Ladder-walk (the whole of `upgrade_pathway`, deterministic):* fetch the belief via `kg.provenance(claim_id)`; abstain (`return {}`) on miss. Compute `current_tier`. The **next rung** skips the lateral READ↔INFERRED step — from either base label the next *strengthening* rung is `corroborated` (see the epistemic note below). Per-rung requirements are fixed:

| From → to | `needed` item | `cost_tier` | rationale (code cite) |
|---|---|---|---|
| base (READ/INFERRED) → **corroborated** | `{"kind":"independent_replication","count": MIN_INDEPENDENT − independent_sources}` | `cheap_assay` | one more *independent lab* on the same (subj,rel,obj,sign); `independent_source_count` is lab-distinct (`kg.py:8`), citation echo can't inflate |
| corroborated → **TESTED** | `{"kind":"public_data_test","count":1}` | `public_data` | one code-run oracle → `TESTED-provisional` (FC-8); cheapest real verification |
| TESTED → **anchored** | `{"kind":"human_anchor","count":1}` | `expensive` | a human owns the anchor (`kg.anchor`); high-stakes, never automatable (PRD-00 §2) |
| anchored → — | `next_tier=None`, `needed=[]` | — | top of ladder; no action suggested to overturn an anchor (poisoning territory) |

`full_path` = the list of remaining rungs with their `needed`, so the panel can print "*one independent replication + a public-data test away from TESTED*". `cheapest_action` = the lowest-`COST_WEIGHT` item across `full_path` **up to the next confirmed rung** (corroborated is not "confirmed"; TESTED/anchored are — so the cheapest lever toward real confirmation is surfaced). Its `run_action` is filled **only when a concrete dispatchable string exists** — for `public_data_test`, iff a dataset is locally available (reuse `value_queue._dataset_available` tokens) emit `"<oracle>:<subj>|<obj>"` in the CCP-19a vocabulary; otherwise `run_action=None` (**abstain from fabricating a runnable action** rather than name an oracle we can't confirm applies). `independent_replication` / `human_anchor` are descriptive, `run_action=None`.

*Data flow:* `prov()` modal → new route `GET /api/persona/{pid}/upgrade_pathway/{claim_id}` → `tiers.upgrade_pathway(claim_id)` → JSON → rendered as a compact ladder strip under the existing provenance header (`index.html:1410`). The route mirrors `provenance()` (`app.py:608–614`) exactly:

```python
@app.get("/api/persona/{pid}/upgrade_pathway/{claim_id}")
def upgrade_pathway(pid: str, claim_id: str):
    with context.use(_p(pid)):
        from ..analysis.tiers import upgrade_pathway as _up
        return _up(claim_id)
```

**Seams.** (1) reads `kg.provenance` + the codified thresholds — nothing else; (2) renders in the existing belief-detail modal (no new tab); (3) `cheapest_action.run_action` is FC-4/CCP-19a-compatible so a cheap upgrade is a VoI item. The three seams are exactly the three the task names.

**Epistemic guardrails.**
- **No fabricated requirement.** Every rung threshold is imported from the module that enforces it; the pathway cannot ask for more (or less) than the membrane/anchor actually demand. The drift guard `assert _MIN_INDEP_COMMIT == MIN_INDEPENDENT`-style single-import + the property test (§5) make divergence impossible-to-ship.
- **Abstain over fabricate.** Unknown claim → `{}`. No concrete dispatchable action → `run_action=None`, not a guessed oracle name.
- **Read-only, no autonomy.** The pathway *describes* what would move a tier; it never moves one. Consistent with Balanced autonomy — anchors stay human-gated (PRD-00 §1), and the pathway never suggests overturning an anchor.
- **Honest ordering.** READ↔INFERRED is *not* an upgrade (INFERRED is the weaker, hollow-rendered provenance, `index.html:1421`); both are the base rung and both upgrade to `corroborated`. The lateral pair is reported (via `provenance` + `current_tier`) but never presented as a step. This ordering decision is the one genuinely underspecified point in the task's `READ→INFERRED→…` phrasing; resolved here to match the real code (§6 Q2).
- **Server-derived, not client-invented.** `current_tier` is the single authority; the client renders it and never recomputes a status (PRD-00 non-negotiable: server derives every scientific status).

**Required experiment.** **Trivial** (pre-assigned). The pathway is a pure deterministic function of codified constants — there is no uncertain modelling choice to gate. A **property test** stands in for an RQ: it asserts the pathway *is* the rules (§5). No `/experiments` sandbox, no seeds, no metric — per PRD-00 §2 / CLAUDE.md §2, trivial reversible derivations do not get the full loop.

**Acceptance + one runnable check.**
- *Acceptance:* for every belief in a synthetic KG spanning all five tiers, (a) `current_tier` equals the `app.py:565–567` derivation (extended for the READ/INFERRED split), and (b) applying each `needed` item to the belief's fields flips `current_tier` to `next_tier`; anchored beliefs return `next_tier=None`; `cheapest_action` is the min-`COST_WEIGHT` item on the confirmed path.
- *Runnable check:* `python -m pytest tests/test_upgrade_pathway.py` (uses a fake-KG stub exposing `.provenance(cid)` — no FalkorDB needed, same injection pattern as `value_queue` tests).

**Effort.** ~S. One ~90-line pure module, one 6-line route, one modal render block (~25 lines JS), one property test (~60 lines). No new dependency, no migration.

**Deps.** FC-3 `kg.provenance` (landed, `kg.py:278`); `calibrate._MIN_INDEP_COMMIT` (landed, `calibrate.py:23`); `value_queue._COST_WEIGHT` (landed, `value_queue.py:17`). All present today — F31.1 can start immediately with zero stubs.

---

## 4. Sequencing

Single feature, no internal ordering. Against PRD-00 §5: this is a Lane-4 leaf that consumes only **already-landed** reads, so it needs no milestone-0 stub wait — build `tiers.py` + test first (pure, offline), then the route, then the modal render, then a `PERSONA_WORKERS=0` browser smoke of the `prov()` modal (PRD-00 §7 requires Lane-4 surfaces prove out in-browser). No other lane blocks on FC-23 and FC-23 blocks no other lane (§6 lists the one optional downstream hook).

---

## 5. Test plan

`tests/test_upgrade_pathway.py` — the property test that *is* RQ-trivial's gate:

1. **`test_current_tier_matches_server_derivation`** — for beliefs hand-built at each tier (READ 0–1 lab; INFERRED; corroborated ≥2 labs; TESTED provenance; anchored flag; HUMAN_CONFIRMED), assert `current_tier` equals the inline `app.py:565–567` logic (kept as a local reference function in the test so the test fails if either drifts).
2. **`test_needed_upgrades_flip_the_tier`** (the core property) — for every non-anchored belief, mutate its fields by each `needed` item (`independent_replication` → `independent_sources += count`; `public_data_test` → `provenance="TESTED"`; `human_anchor` → `anchored=True`) and assert `current_tier(mutated) == next_tier`. This is the machine-checkable statement of "pathway matches the rules."
3. **`test_anchored_is_terminal`** — anchored belief ⇒ `next_tier is None`, `needed == []`, `cheapest_action is None`.
4. **`test_cheapest_action_is_min_cost`** — `cheapest_action.cost_tier` has the minimum `COST_WEIGHT` among the confirmed-path `needed` items; `run_action` is `None` unless a dataset token matches (inject a fake `dataset_available`).
5. **`test_unknown_claim_abstains`** — `upgrade_pathway("nope", kg=stub_empty) == {}`.
6. **`test_thresholds_are_imported_not_hardcoded`** — monkeypatch would break, so instead assert `MIN_INDEPENDENT is calibrate._MIN_INDEP_COMMIT` and `COST_WEIGHT is value_queue._COST_WEIGHT` (identity) — proves single-source, catches a future copy-paste.

Fake KG: a 15-line stub `class _KG: def provenance(self, cid): return self._rows.get(cid, {})`. No network, no FalkorDB, deterministic.

Browser smoke (PRD-00 §7): with `PERSONA_WORKERS=0`, open the app, click a belief in `#blist`, open `prov()`, assert the pathway strip renders the ladder + a "N steps to TESTED"-style line.

---

## 6. Open questions

- **Q1 (non-blocking, → Lane 2 & 3, optional CCP):** promote `calibrate._MIN_INDEP_COMMIT` and `value_queue._COST_WEIGHT` to public aliases so FC-23 imports a public name instead of a private one? Ships fine against the private names today (fail-loud on rename + property-test guard); the alias is pure hygiene. Default: skip unless Lane 2/3 want it.
- **Q2 (resolved here, surfaced for review):** the task ladder writes `READ→INFERRED→corroborated`. The real code treats READ and INFERRED as *lateral* base labels (both map to `observed` at `app.py:567`; INFERRED is the weaker, hollow-rendered provenance at `index.html:1421`), not a strengthening step. **Resolution:** the base rung is `{READ, INFERRED}` and both upgrade to `corroborated`; the lateral pair is reported but never presented as an "upgrade." If a reviewer wants READ→INFERRED shown as a literal rung, it would require inventing a non-existent admission rule — declined per "no fabricated requirement."
- **Q3 (non-blocking, → Lane 3, future):** should `cheapest_action` rows (the public-data upgrade tests) be *merged into* `engine.value_queue()` output so the VoI queue literally lists per-belief upgrade actions? Today the integration is vocabulary-compatibility (same `run_action` grammar) + the panel offering the action — no `value_queue.py` edit. Deeper merge is a Lane-3 change (additive rows keyed by `resolves_claim_id`) → a CCP if wanted. Not required for FC-23.
- **Q4 (minor):** `corroborated` is derived state, not a stored `provenance` value — a belief can be `corroborated` while its `provenance` is still `READ`. The pathway reports both (`current_tier="corroborated"`, `provenance="READ"`); confirm the panel copy makes that distinction legible ("2 independent labs, still literature-only") rather than implying corroboration changed the provenance string.
