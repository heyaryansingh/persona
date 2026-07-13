# PRD-05 — Second researcher / a lab

> Owner: implementer lane **1+2** · Status: **DRAFT-for-implementation** · Autonomy: **Balanced** · Depends on: **FC-2** (consumed, `persona/inbox.py`), `manager.py` multi-persona substrate (exists), `memory/kg.py` read APIs + `pair_key` (exists). Provides candidate **FC-8** (cross-persona diff — see §2). Registers **RQ-E20**.

---

## 0. Summary + how it advances the vision

Persona already runs **multiple fully-isolated personas** in one process: `PersonaManager.create(name, interests, budget_usd)` mints a persona with its own workspace, its own FalkorDB graph `persona_{id}`, its own daemon, queue, budget, and canonicalizer (`persona/manager.py:54-68`, `persona/persona_obj.py:17-135`). What does **not** yet exist is any reason to run two at once: today two personas seeded on the same field are two copies of the same reader that will read near-identical papers and converge to near-identical beliefs. The substrate is a *lab with one bench occupied twice*.

This PRD makes the second bench matter. It adds:

1. A **disposition** — a small, durable, git-diffable part of the Self (BUILD_PLAN §1.1: *"its stance — skeptical vs. exploratory — risk appetite for speculation"*) that is **functional, not a personality prompt** (BUILD_PLAN §0.3, §1.4): two scalar traits (`skepticism`, `novelty_seeking`) that measurably change (a) **which papers a persona reads** from the same candidate pool and (b) **what stance it takes when adjudicating a contradiction**. If it doesn't change behavior it is anthropomorphic theater — so it ships gated behind **RQ-E20**, which *is the E4 test from BUILD_PLAN §1.4* applied to disposition.
2. A **cross-persona belief-diff**: given two personas that read the same field, compute where their converged beliefs **agree, diverge in confidence, oppose in sign, or where one covered a claim the other never saw** — keyed on the *shared claim shape* (`pair_key(subject,object)` + `effect_sign`) that `memory/kg.py` already computes.
3. A **reconciliation dossier**: for each material disagreement, compare the two personas' *evidence* (their supporting sources + verbatim spans), **type the disagreement**, and route it to the human via **`inbox.file_handoff` (FC-2)** — never auto-resolved, never auto-anchored.

**New capability nothing else in the stack has.** Every incumbent (scite, Open Targets, PaperQA2, MedKGent) reads a field once, from one implicit stance. Persona's differentiator so far is the *acting loop* and the *persistent self*; this adds the piece none of them and none of Persona's own subsystems have: **cross-agent epistemic disagreement as a first-class, provenance-typed signal and dataset.** A skeptic and an explorer reading the same literature and *disagreeing in a located, auditable way* is a stronger tension detector than any single mind's internal contradiction graph — it surfaces "your reading of this field is stance-dependent, and here is exactly where," which is precisely the legibility thesis (CLAUDE.md §5) turned on the researcher itself. The disagreement stream is also a reusable **dataset** (append-only handoffs) for studying where automated reading is fragile.

**Why it's cheap to build:** the isolation, the per-persona graph, and the claim-identity shape already exist. The belief-diff is a **pure function over two `kg.beliefs()` results** — it needs **zero edits to Lane 2's `kg.py`**. The only shared-core edits are two lines (a `disposition=` kwarg on `manager.create`, one entry in `config.SELF_FILES`).

---

## 1. File ownership (disjoint)

| File | New? | Lane | Notes |
|---|---|---|---|
| `persona/disposition.py` | **new** | 1+2 (this PRD) | The disposition Self-fragment + its two functional levers (read re-rank, adjudication stance). Pure, no side effects except writing `disposition.md`. Unassigned in PRD-00's map → this PRD claims it. |
| `persona/agents/reconcile.py` | **new** | 1 (this PRD; `agents/*` is Lane 1's set) | Cross-persona belief-diff, disagreement typing, dossier builder/filer. |
| `persona/reading/reader.py` | edit | **1** (Lane 1 owns `reading/reader.py` per PRD-00 §3) | Add a disposition re-rank hook inside `scout()` after the relevance gate. |
| `experiments/exp_rq_e20_disposition_functional.py` | **new** | 4 owns `experiments/*` — **boundary**, see below | The RQ-E20 sandbox. Additive new file; no collision. |
| `tests/test_disposition.py`, `tests/test_reconcile.py` | **new** | 4 owns `tests/*` — **boundary**, see below | Runnable checks. Additive new files. |

**Boundary files another lane owns (+ the FC / mechanism that decouples them):**

- `persona/manager.py`, `persona/config.py`, `persona/selfmind.py` — **core, unassigned to any lane in PRD-00 §3.** This PRD needs **two one-line additions** (`create(... disposition=None)`; `SELF_FILES += ("disposition.md",)`). These are additive and touch no other lane's logic. Flagged for the master in §6-Q1; treat as owned by this PRD unless the master reassigns.
- `persona/inbox.py` (**FC-2, Lane 2 provides**) — **consumed, not edited.** `reconcile.py` calls `inbox.file_handoff(kind, dossier)` exactly as frozen. Until Lane 2 lands it, `reconcile` imports lazily and falls back to writing the dossier JSON under `ops_dir/handoffs/` (see §3.F3).
- `experiments/*`, `tests/*` — **Lane 4's set**, but only *new* files. PRD-00 §3 already scopes Lane 4 to "new" files there; new files by another lane don't collide (append-only directory, same rule as the shared ledger). Flagged in §6-Q2; if the master prefers, these move under a `lane1/` subdir.
- `persona/memory/kg.py` (**Lane 2**) — **read-only.** We call the existing `pair_key()`, `beliefs()`, `provenance()`, `crosscheck()`, `is_anchored()`. **No edit requested.**

---

## 2. Frozen contracts provided / consumed

### Consumed verbatim

**FC-2 (Lane 2 provides, `persona/inbox.py`):**
```
inbox.file_handoff(kind:str, dossier:dict) -> handoff_id:str
```
Dossier schema `{decision_requested, why_unresolvable, disagreeing:[{claim_id,span,qualifiers}], conflict_type:'temporal'|'semantic'|'misinformation'|'insufficient', cheapest_test:{action,cost_tier,dataset}, expected_updates:[{outcome,belief_change}], uncertainty, authority_boundary}`.

`reconcile.reconciliation_dossier(...)` produces a dict that **conforms exactly** to this schema (field-by-field mapping in §3.F3). `kind = "cross_persona_disagreement"`.

**FC-3 read APIs (Lane 2, `persona/memory/kg.py`)** — used read-only if present, but the diff's core path depends **only** on the already-shipped `beliefs()` / `provenance()` / module-level `pair_key()`, so it works today against the current `kg.py`.

### Provided — CONTRACT CHANGE PROPOSAL (candidate FC-8)

This PRD introduces the first cross-persona interface. Lane 4 (legibility) will want to render the diff and the dossier. Rather than have Lane 4 reach into `reconcile.py` internals, propose a frozen read contract:

> **FC-8 (Lane 1 provides, new `persona/agents/reconcile.py`) — PROPOSED, needs master ratification:**
> ```
> reconcile.belief_diff(persona_a, persona_b, *, min_independent:int=2, conf_tol:float=0.2)
>     -> [{pair_key, subject, object,
>          type:'sign_conflict'|'confidence_divergence'|'coverage_gap',
>          a:{claim_id, effect_sign, confidence, provenance, independent_sources, sources}|None,
>          b:{...}|None}]
> reconcile.reconciliation_dossier(persona_a, persona_b, *, max_rows:int=25)
>     -> {handoff_id:str|None, dossier:dict, n_disagreements:int, filed:bool}
> ```

Flagged in §6-Q3. Until ratified, Lane 4 consumes it at its own risk; the signature above is the one this PRD will hold stable.

---

## 3. Features

### F1 — Disposition as a functional Self-fragment

**Problem & evidence.** BUILD_PLAN §1.1 lists *disposition ("skeptical vs. exploratory")* as a first-class part of the Self, and §0.3/§1.4 make the hard rule explicit: it is real **iff it changes which papers get read and which tensions get prioritized** — otherwise it is theater the judge will call out. Today the Self has interests/beliefs/strategies/taste/directives (`config.py:35-36`, `selfmind.py`) but **no disposition** and nothing stance-dependent in the reading path: `reader.scout()` ranks purely by objective-relevance (`reading/reader.py:80-112`), identical for every persona. `manager.create()` takes only `interests` (`manager.py:54`).

**Design.**
- **Storage — new Self file `disposition.md`** (same markdown-on-disk, git-diffable pattern as every other Self file; `paths.self_dir`). Add `"disposition.md"` to `config.SELF_FILES` (one line) so `selfmind.read_self()` surfaces it into agent prompts for free.
- **New module `persona/disposition.py`** (pure; only side effect is writing `disposition.md`):
  ```python
  # two scalar traits + a human-readable stance/reason. Presets are a convenience, not a taxonomy.
  DISPOSITIONS = {
      "skeptic":  {"skepticism": 0.85, "novelty_seeking": 0.25, "stance": "skeptic",
                   "reason": "demands independent replication; reads into contested findings"},
      "explorer": {"skepticism": 0.30, "novelty_seeking": 0.85, "stance": "explorer",
                   "reason": "reads the frontier; provisionally weights the newest results"},
      "balanced": {"skepticism": 0.5,  "novelty_seeking": 0.5,  "stance": "balanced", "reason": "default"},
  }

  def seed(spec: str | dict | None) -> dict:
      """Resolve spec (preset name | explicit dict | None->balanced) to a full disposition dict and
      write disposition.md ONCE. Idempotent like selfmind.seed: never overwrite an evolved disposition."""

  def load() -> dict:
      """Read disposition.md for the current persona (via get_persona()); balanced default if absent.
      Clamps both traits to [0,1]; fails to 'balanced' on any parse error (fail-safe, never crash reading)."""

  def read_rank(works: list, kg, disp: dict) -> list:
      """Stable, DETERMINISTIC re-rank of scouted works by a disposition score (see F2). Pure."""

  def adjudicate_stance(conflict: dict, disp: dict) -> dict:
      """Map a candidate conflict + disposition -> {stance, route, reason}. Pure. NO KG write (see F4)."""
  ```
- **Wiring `manager.create` (one kwarg + one call):**
  ```python
  def create(self, name, interests=None, budget_usd=None, disposition=None):   # +disposition
      ...
      if interests:
          with context.use(p):
              selfmind.seed(...)
      with context.use(p):
          disposition.seed(disposition)     # writes disposition.md; balanced if None
      return p
  ```
  Existing callers pass nothing → every current persona is `balanced` → **zero behavior change** for single-persona use. `disposition.load()` resolves through the `get_persona()` contextvar exactly like `selfmind` (`context.py:31-41`), so it is correct inside a persona's own worker/daemon with no arg threading.

**Epistemic guardrails.** Disposition changes *reading selection* and *adjudication stance recommendation* only. It **never** touches extraction (`reading/extract.py` stays domain-general and stance-free — a skeptic and an explorer extract the *same* claims with the *same* verbatim spans; only which papers reach the extractor differs), never sets belief confidence, never anchors. Provenance typing is untouched. Disposition is itself provenance-neutral metadata on the Self.

**Required experiment:** RQ-E20 (see F2/F4 — one experiment covers both levers).

**Acceptance + runnable check.** `disposition.seed("skeptic")` then `load()` returns `skepticism≈0.85`; re-seeding with `"explorer"` on an already-seeded persona does **not** overwrite (idempotent); `load()` on an unseeded workspace returns `balanced`.
`pytest tests/test_disposition.py::test_seed_load_idempotent`.

**Effort:** S. **Deps:** none.

---

### F2 — Disposition changes *which papers get read* (reading lever)

**Problem & evidence.** This is half of the anti-theater bar (BUILD_PLAN §0.3, §1.4 "which papers get read"). `reader.scout()` currently returns the first `want` unread works after a relevance filter (`reading/reader.py:102-108`) — pool order is source-order, stance-independent. Two personas on the same interest get the same reads.

**Design — `read_rank` hook inside `scout()` (Lane 1 owns `reader.py`).** After the objective-relevance gate (`reader.py:97-101`) and **before** the `want` cap (`:102-108`), re-rank the surviving `works` by a disposition score, then take the top `want`. Both dispositions read *on-objective* papers (the relevance gate is untouched — no off-field pollution); they differ in *which* on-objective papers they prioritize when the pool exceeds `want`.

Deterministic score per work (all signals already available on the `Work` dict / the persona's KG — no new fetch):
```
score(w, disp) =  disp.skepticism      * contested_signal(w, kg)      # into tensions / replication
               +  disp.novelty_seeking * novelty_signal(w, kg)        # frontier / unseen entities
               +  base_relevance(w)                                    # tie-break = existing order
```
- `contested_signal`: +1 if the title matches a small contested-lexicon (`replicat|fail(s|ed) to|no (significant )?effect|contradic|revisit|controvers|irreproducib|retract`); **+1 more** if the work's entities already sit on a `CONTRADICTS` pair in the persona's KG (`kg.contradictions()` / `kg.crosscheck()`) — a skeptic reads *into* live tensions.
- `novelty_signal`: +1 for recent year (`w.year >= current_year-2`); **+1 more** if neither endpoint entity is yet in the KG (`kg.search()` miss) — an explorer reads the unseen frontier.
- Ties preserve source order (stable sort), so `balanced` ≈ today's behavior.

`read_rank` is a pure function of `(works, kg, disp)`; the sandbox in RQ-E20 exercises it with synthetic works and a fake KG (no network).

**Epistemic guardrails.** Re-rank only reorders *within the relevance-passed set*; it cannot admit an off-objective paper (the gate at `reader.py:97-101` still runs first). No claim, confidence, or provenance is touched by reading order. `ponytail:` the re-rank is the whole lever — a tau offset per disposition was considered and dropped as gold-plating (the re-rank already produces divergence; a second knob adds tuning surface for no measured gain — revisit only if RQ-E20 fails the divergence gate on re-rank alone).

**Required experiment: RQ-E20 (reading half).** *Hypothesis:* over one shared candidate pool of on-field works, a skeptic and an explorer select measurably different read-sets, while both stay on-field. *Metric + gate:* mean Jaccard(read-set_skeptic, read-set_explorer) over ≥20 seeds (seed = shuffled pool order + jittered trait scalars) with 95% CI, **gate: mean Jaccard ≤ 0.7** (they diverge) **AND** on-field ratio of both read-sets ≥ the `balanced` baseline (they don't diverge by going off-topic). *Null:* disposition ignored → Jaccard = 1.0. Sandbox: `experiments/exp_rq_e20_disposition_functional.py`, fully offline (synthetic works tagged contested/novel/plain + a synthetic KG stub), deterministic → seedable. Results → `results/`. Cited in the `read_rank` docstring per CLAUDE.md §2.6.

**Acceptance + runnable check.** With a fixed 40-work synthetic pool (mix of contested/novel/plain) and `want=10`, `read_rank` under `skeptic` puts ≥N contested works in the top-10 that `explorer` does not, and vice-versa for novel; Jaccard(top-10) < 0.7. `pytest tests/test_disposition.py::test_read_rank_diverges`.

**Effort:** M. **Deps:** F1.

---

### F3 — Cross-persona belief-diff + reconciliation dossier

**Problem & evidence.** The claim-identity shape is already shared and pure: `kg.pair_key(subject, object)` (`memory/kg.py:33-36`) plus `effect_sign` is *the* directional-belief key (`kg.py:97-99` comment: "claim identity = (subject, object, effect_sign)"). `kg.beliefs()` returns exactly `{claim_id, subject, object, effect_sign, independent_sources, confidence, provenance, anchored}` (`kg.py:204-215`) and `kg.provenance(cid)` returns supporting sources with verbatim quotes (`kg.py:234-251`). Two personas' graphs are independent objects (`persona.kg`, `persona_obj.py:89-94`) reachable without any contextvar juggling. **Everything the diff needs already exists as a read API — no `kg.py` edit.**

**Design — `persona/agents/reconcile.py` (Lane 1).**
```python
def belief_diff(persona_a, persona_b, *, min_independent=2, conf_tol=0.2) -> list[dict]:
    # a = {(pair_key(s,o), sign): belief} from persona_a.kg.beliefs(min_independent=min_independent)
    # b = likewise from persona_b.kg.beliefs(...)
    # emit one row per material disagreement, typed:
    #   'sign_conflict'          same pair_key present in BOTH, opposite effect_sign
    #   'confidence_divergence'  same (pair_key,sign) in both, |conf_a-conf_b|>=conf_tol OR provenance rank differs
    #   'coverage_gap'           pair_key held (>=min_independent labs) by exactly ONE persona
    # each side carries claim_id, effect_sign, confidence, provenance, independent_sources,
    #   and sources (from kg.provenance(cid) -> slug/doi/quote) for the evidence compare.
```
- **Identity across canonicalizers.** Each persona canonicalizes entities independently (`kg.py:59-64`), so exact `claim_id` match would miss synonyms. The diff keys on **`pair_key(subject, object)` recomputed from the stored (already-canonical) subject/object strings** — the same pure hash for both personas — which matches whenever both converged to the same canonical surface form (the common case for a shared field). Cross-canonicalizer *synonym* matching (embedding-based) is deliberately **out of scope** (see §6-Q4); the honest failure mode is a *false coverage_gap* (A and B named the same thing differently), which is safe — it over-reports "you two may have missed each other," never fabricates a conflict. Documented in the docstring.

```python
def type_disagreement(row: dict) -> str:
    # map a diff row -> FC-2 conflict_type vocabulary {temporal|semantic|misinformation|insufficient}:
    #   coverage_gap                         -> 'insufficient'   (one side has no evidence at all)
    #   sign_conflict w/ differing valid_to  -> 'temporal'       (belief changed over time)
    #   sign_conflict, one side low-independence high-volume (kg.poisoning_signals shape) -> 'misinformation'
    #   sign_conflict / confidence_divergence with differing qualifiers -> 'semantic'  (context divergence)

def reconciliation_dossier(persona_a, persona_b, *, max_rows=25) -> dict:
    rows = belief_diff(persona_a, persona_b)[:max_rows]
    dossier = {                                    # conforms VERBATIM to FC-2 schema
      "decision_requested": "For each pair below, which lab's reading should we hold — or is this an open tension needing data?",
      "why_unresolvable": "two dispositions read the same field and diverged; neither side is anchored.",
      "disagreeing": [{"claim_id": side["claim_id"], "span": top_quote(side), "qualifiers": ...}
                       for row in rows for side in (row["a"], row["b"]) if side],
      "conflict_type": <the modal type_disagreement over rows>,       # dossier-level; per-row type kept in body
      "cheapest_test": {"action": "cross-read: each persona reads the other's top uncited source on the pair",
                        "cost_tier": "public_data", "dataset": None},
      "expected_updates": [{"outcome": "coverage_gap closes on re-read", "belief_change": "convergence, no human needed"},
                           {"outcome": "sign persists after cross-read", "belief_change": "escalate as a real tension"}],
      "uncertainty": <fraction of rows that are sign_conflict>,
      "authority_boundary": "Persona may recommend a stance; it may NOT anchor either side. Human decides.",
    }
    handoff_id = _file(kind="cross_persona_disagreement", dossier=dossier)
    return {"handoff_id": handoff_id, "dossier": dossier, "n_disagreements": len(rows), "filed": handoff_id is not None}
```
- **Filing (FC-2 consume + fallback).** `_file()` does `from ..inbox import file_handoff` lazily; if Lane 2 hasn't landed `inbox.py` yet, it writes the dossier to `get_persona().paths.ops_dir / "handoffs" / f"{ts}.json"`, logs an `escalate` event, and returns `None` (so `filed=False` is honest). When `inbox.py` lands, the lazy import wins with **no code change** here. This keeps the two lanes decoupled through M0.
- **Who runs it, and when.** Balanced autonomy: the diff/dossier is **advisory**. A CLI entry (`python -m persona.agents.reconcile <persona_a_id> <persona_b_id>`) and a callable for a future Lane-4 route/daemon step. It does **not** auto-run in the scheduler in this PRD (a periodic reconcile step is a trivial later add — `supervisor.py:130-164` is the hook — but is Lane 1's scheduler surface and gated on the master wanting it; §6-Q5). No auto-anchor, ever.

**Epistemic guardrails (the load-bearing ones).** (1) Each persona's beliefs stay exactly as their own graph typed them — the diff **reads**, never writes either graph. (2) A disagreement is a **candidate signal, not truth** — mirrors `kg.candidate_conflicts()` framing (`kg.py:229-232`): the dossier says "needs human," `conflict_type` is provisional, nothing is a verified contradiction. (3) **Nothing auto-anchors** — `authority_boundary` states it and `reconcile` has no path to `kg.anchor()`/`human_resolve()`. (4) The dossier's `disagreeing[].span` is a **real verbatim quote** pulled from `kg.provenance()` (already exact-span-gated at extraction, `extract.py:115-148`) — if a side has no quoted source, that side is omitted rather than fabricated (abstain-not-fabricate, CLAUDE.md §0).

**Required experiment.** F3 is **"trivial" in the RQ sense** — it is deterministic set arithmetic over two graphs with an established identity key (`pair_key`), not a load-bearing modeling choice. Its correctness is covered by unit tests (below), not a seeded sandbox. (The *disposition* that produces divergent graphs is what RQ-E20 validates; the diff over them is plumbing.)

**Acceptance + runnable check.** Build two in-memory belief lists: shared pair with opposite signs → exactly one `sign_conflict` row; a pair only A holds → one `coverage_gap`; a shared pair+sign with Δconf > `conf_tol` → one `confidence_divergence`; identical high-conf pair+sign → **no** row. `reconciliation_dossier` returns a dict whose keys are exactly the FC-2 set and whose `authority_boundary` forbids anchoring; with no `inbox.py` present it writes a fallback JSON and returns `filed=False`. `pytest tests/test_reconcile.py::test_belief_diff_types` and `::test_dossier_conforms_fc2`.

**Effort:** M. **Deps:** F1 (personas carry dispositions so the two graphs actually diverge); FC-2 (consumed, with fallback).

---

### F4 — Disposition changes *how a contradiction is adjudicated* (adjudication lever)

**Problem & evidence.** The second half of the anti-theater bar (BUILD_PLAN §0.3 "which tensions get prioritized"; §1.4). Persona has adjudication vocabulary already — `conflict_reviews.ConflictVerdict = {extraction_error, true_refutation, context_divergence, insufficient_evidence}` (`conflict_reviews.py:23-27`) and a skeptic-framed paper adjudicator (`agents/audit.py:69`) — but the *stance* is hard-coded; nothing lets two dispositions weigh the same conflict differently.

**Design — `disposition.adjudicate_stance(conflict, disp)` (pure, in `disposition.py`).** Given a candidate conflict (the `kg.candidate_conflicts()` shape: `{subject, object, pos_sources, neg_sources, pos_claim, neg_claim, ...}`, `kg.py:217-232`) and a disposition, return a **recommended stance + route**, never a mutation:
```python
def adjudicate_stance(conflict, disp) -> {"stance": str, "route": str, "reason": str}:
    # skepticism raises the evidence bar to believe EITHER side:
    #   high skepticism + neither side anchored/TESTED + low independent-lab count
    #        -> stance="hold_insufficient", route="human"        (map: insufficient_evidence)
    # novelty_seeking is willing to provisionally weight the newer/positive finding:
    #   high novelty_seeking + one side notably higher independent support
    #        -> stance="provisional_context_divergence", route="commit_provisional"  (map: context_divergence)
    #   both traits low/balanced -> stance="needs_review", route="human"
    # An ANCHORED side always wins regardless of disposition (anchor write-policy, kg.py:160-166) -> route="human" (confirm).
```
- `route ∈ {human, commit_provisional}` aligns with Balanced autonomy: `commit_provisional` is a *recommendation to open a narrow reanalysis* (TESTED-provisional lane per PRD-00 autonomy), still gated; `human` escalates. **No route anchors.**
- The stance feeds F3's dossier (`type_disagreement` uses it to pick `context_divergence` vs `insufficient`) and is where a skeptic-lab and an explorer-lab visibly diverge on the *same* tension.

**Epistemic guardrails.** Recommendation only — the return value is inert data. No call to `kg.anchor`, `kg.human_resolve`, or `conflict_reviews.append_conflict_review` from here. An anchored belief is disposition-proof (the branch forces `route="human"` to *confirm*, never overturn) — preserves the anchoring result that retained 100% of verified beliefs under poisoning (`results/FINDINGS.md`).

**Required experiment: RQ-E20 (adjudication half).** *Hypothesis:* over a fixed set of candidate conflicts spanning the evidence spectrum (anchored/unanchored × few/many labs × sign-symmetry), skeptic and explorer produce measurably different stance distributions. *Metric + gate:* **stance-flip rate** = fraction of conflicts where `adjudicate_stance(c, skeptic).stance != adjudicate_stance(c, explorer).stance`, over ≥20 seeds (seed = sampled conflict set + jittered trait scalars), 95% CI; **gate: mean flip-rate ≥ 0.30** while **anchored conflicts never flip** (both route them to `human`). *Null:* disposition ignored → flip-rate 0. Same sandbox file as F2 (`exp_rq_e20_disposition_functional.py`), offline, deterministic. This *is* BUILD_PLAN's E4 realized for disposition — register RQ-E20 in `docs/RESEARCH_QUALITY_PROGRAM.md` and cite it in the `adjudicate_stance` docstring.

**Acceptance + runnable check.** On a fixed 12-conflict fixture, flip-rate between skeptic and explorer ≥ 0.30, and every anchored-side conflict yields `route="human"` for both. `pytest tests/test_disposition.py::test_adjudicate_stance_diverges_and_respects_anchor`.

**Effort:** S. **Deps:** F1.

---

## 4. Sequencing (interface-first, then fill)

**M0 (land stubs, commit-in-place so parallel work can build):**
1. `persona/disposition.py` with `DISPOSITIONS`, `seed`, `load`, and typed-empty `read_rank`/`adjudicate_stance` stubs. Add `"disposition.md"` to `config.SELF_FILES`. Add `disposition=None` kwarg to `manager.create`. → F1 usable immediately; unblocks F2/F4.
2. `persona/agents/reconcile.py` with `belief_diff`/`reconciliation_dossier` signatures returning typed empties, and the lazy-FC-2 `_file` fallback. → freezes candidate FC-8 for Lane 4.

**Then fill in this order:**
- **F1** (real `seed`/`load`) — smallest, unblocks everything.
- **F2** (`read_rank` + `scout` hook) and **F4** (`adjudicate_stance`) in parallel — both pure, both feed RQ-E20; write `exp_rq_e20` once, it validates both.
- **F3** (`belief_diff` real + dossier + FC-2 wire) last — depends on F1 so two personas actually diverge, and consumes F4's stance for typing.

Rationale: the two *pure* levers (F2/F4) carry the anti-theater risk, so they get their experiment first; the diff (F3) is deterministic plumbing that only becomes interesting once dispositions make graphs differ.

---

## 5. Test & verification plan

- **RQ-E20 sandbox** (`experiments/exp_rq_e20_disposition_functional.py`, ≥20 seeds, offline, seeded): reading-half Jaccard ≤ 0.7 gate + adjudication-half flip-rate ≥ 0.30 gate, both with 95% CI; anchored conflicts never flip; results → `results/` and a line in `results/FINDINGS.md`. This is the go/no-go for shipping disposition as *functional*; if either gate fails, disposition is theater and the reading/adjudication levers do not merge (log the reversal per CLAUDE.md §2.5).
- **Unit (reuse real oracles, no mocks of the thing under test):**
  - `test_disposition.py`: idempotent seed/load; `read_rank` divergence on a synthetic pool; `adjudicate_stance` divergence + anchor-respect.
  - `test_reconcile.py`: `belief_diff` emits the correct row type for each of the four cases (sign_conflict / confidence_divergence / coverage_gap / no-row); `reconciliation_dossier` output key-set == FC-2 schema and `authority_boundary` forbids anchoring; FC-2 fallback path (`filed=False`, JSON written) when `inbox.py` absent. These use **real `KG` objects** against the test FalkorDB (the suite already stands one up) so the `pair_key`/`beliefs`/`provenance` seam is exercised for real, not stubbed — a regression in claim identity actually fails the test.
- **Integration smoke (manual/CLI, no new UI in this PRD):** `manager.create("Skeptic Lab", interests=[...], disposition="skeptic")` and `"Explorer Lab"` on the same interests; let both read a few papers with `PERSONA_WORKERS` small; run `python -m persona.agents.reconcile skeptic-lab explorer-lab`; assert a dossier is produced with ≥1 typed disagreement and `authority_boundary` present. (Rendering the dossier is Lane 4 via the FC-2 inbox — out of scope here.)

---

## 6. Open questions for the master / user

- **Q1 (ownership).** `manager.py`, `config.py`, `manager.create` are unassigned in PRD-00 §3 but need two additive one-line edits. Confirm this PRD may make them, or name the owning lane. (No other lane's logic is touched.)
- **Q2 (experiments/tests ownership).** PRD-00 §3 scopes `experiments/*` and `tests/*` to Lane 4. New files by this lane don't collide, but confirm the master is fine with Lane-1 authors adding `exp_rq_e20_*` and `test_disposition/reconcile` there, or prefer a `lane1/` subdir.
- **Q3 (CONTRACT CHANGE PROPOSAL — candidate FC-8).** Ratify `reconcile.belief_diff` / `reconcile.reconciliation_dossier` as a frozen read contract so **Lane 4** can render the diff + dossier without reaching into internals. Blocks nothing until Lane 4 builds that surface, but the signature should be frozen before then.
- **Q4 (identity across canonicalizers).** The diff keys on `pair_key` over each persona's canonical surface forms; synonym drift (A: "amyloid-beta", B: "Aβ") shows up as a false `coverage_gap`, never a false conflict. Ship the safe exact-key version now and defer embedding-based synonym matching to a follow-up? (Recommended: yes — the over-report is epistemically safe and cheap to fix later.)
- **Q5 (autonomy of reconcile).** Should a periodic `reconcile` step run in the daemon scheduler (`supervisor.py:130-164`) when two seeded personas share a field, or stay CLI/advisory-only in this PRD? Balanced autonomy permits the *diff* to auto-run (it only files a human handoff, never anchors), but that touches Lane 1's scheduler surface — confirm before wiring.
- **Q6 (disposition evolution).** `disposition.seed` is idempotent (won't overwrite), matching `selfmind.seed`. Should the reflection loop (`agents/deliberate.py`) be *allowed* to evolve disposition over time (a persona that keeps finding true refutations grows more skeptical), or is disposition a fixed birth-trait for now? Recommend fixed-at-birth for this PRD; evolution is a clean follow-up once RQ-E20 proves the trait is functional at all.

---

### Compact summary

- **File:** `docs/prd/PRD-05-second-researcher-lab.md`
- **Features:** F1 disposition Self-fragment · F2 reading lever · F3 cross-persona belief-diff + FC-2 dossier · F4 adjudication lever.
- **New public signatures (for FC coherence):**
  - `disposition.seed(spec: str|dict|None) -> dict`
  - `disposition.load() -> dict`  *(→ {stance, skepticism, novelty_seeking, reason})*
  - `disposition.read_rank(works: list, kg, disp: dict) -> list`
  - `disposition.adjudicate_stance(conflict: dict, disp: dict) -> {stance, route, reason}`
  - `reconcile.belief_diff(persona_a, persona_b, *, min_independent=2, conf_tol=0.2) -> list[dict]`  **(candidate FC-8)**
  - `reconcile.type_disagreement(row: dict) -> str`
  - `reconcile.reconciliation_dossier(persona_a, persona_b, *, max_rows=25) -> {handoff_id, dossier, n_disagreements, filed}`  **(candidate FC-8)**
  - `manager.create(name, interests=None, budget_usd=None, disposition=None)`  *(+disposition kwarg)*
- **Consumes:** FC-2 `inbox.file_handoff(kind, dossier)` (with fallback until Lane 2 lands `inbox.py`); `kg.pair_key/beliefs/provenance` (read-only, no edit).
- **Blocking another lane:** Q3 (ratify candidate **FC-8**) so Lane 4 can render the diff/dossier; Q1 (approve two-line edits to `manager.py`/`config.py`).
- **Experiment:** **RQ-E20** (BUILD_PLAN E4 for disposition) — reading Jaccard ≤ 0.7 AND adjudication flip-rate ≥ 0.30, ≥20 seeds, anchored conflicts never flip.
