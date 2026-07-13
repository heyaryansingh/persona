# PRD-36 — Contradiction-independence pre-check

> **Owner lane:** 2 (Membrane & belief core) · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced (annotate + type autonomously; *suppress* a contradiction from the human queue only after RQ-E50 clears its gate — until then advisory-only, the tension still escalates) · **Depends on:** existing `memory/kg.py` independence-by-lab machinery (`lab_of` `kg.py:64-68`; `count(DISTINCT s.lab)` `kg.py:172-173`) — Lane 2 self; `memory/membrane.py` contradiction-announce loop (`membrane.py:101-116`) — Lane 2 self; the shared append-only `ops_dir/gate_decisions.jsonl` ledger (FC-8). **Consumed by** Lane 4 (renders the suppressed/annotated candidate + override view) via new **FC-28**. · **Backlog #37.**
>
> Governed by PRD-00 §4/§6 and §8 reconciliation. Where this body disagrees with §4/§6, §4/§6 win.

---

## 0. Summary + capability unlocked

Persona fires a contradiction on a **pure sign-collision**: any two live claims that share a `pair_key` (same canonical subject→object) and carry opposite `effect_sign` get a reciprocal `CONTRADICTS` edge (`kg.link_all_contradictions` `kg.py:191-202`; `link_contradictions` `kg.py:178-189`), which `kg.contradictions()` (`kg.py:261-271`) wraps into `candidate_conflicts()` (`kg.py:273-276`) and routes to the human — the membrane announces each one (`membrane.py:106-115`) and both `/epistemic` (`app.py:569`) and `/inbox` (`app.py:630`) surface them for review. **Nothing checks whether the two disagreeing sides trace to the same lab, author-group, dataset, or preprint/published pair of a single origin.** So a lab that reports `+` in a preprint and `−` in the published version, or two papers from one group that revise a number, register as a *contradiction* in the human's queue with the same weight as a genuine cross-lab tension. That is noise: a disagreement one origin has *with itself* is not an independent tension, and the whole discipline of the store is that **independence is by lab, not by copy** (`kg.py:8`, `kg.py:172-173`) — the same principle `poisoning_signals` already leans on (a low-independence signature is suspect, `kg.py:297-309`).

PRD-36 adds a **pre-escalation independence check** that reuses the existing independence-by-lab unit (`lab_of`) rather than reinventing it:

1. **Trace origins.** `kg.shared_origin(a, b)` (FC-28) fetches both claims' `SUPPORTED_BY` sources with their `lab`/`slug`/`doi`/`title`, forms every **cross-side source pair** (one supporter of A × one supporter of B), and asks per pair: do these two sources share a **primary origin** (same lab; or a preprint↔published pair; or — deferred, O-2 — same dataset)?
2. **Conservative suppression rule.** A contradiction is a *shared-origin false tension* **only when ALL cross-side pairs share an origin** (`independent_pairs == 0 AND total_pairs > 0`). **Any single independent pair ⇒ the tension is genuine and stands** — the strictest possible rule, favouring keeping contradictions.
3. **Suppress at the queue, not the graph.** The structural `CONTRADICTS` edge stays (it is structurally true; `poisoning_signals` and the trajectory readers still see it). The pre-check only decides whether the tension **escalates to the human contradiction queue** — it annotates every candidate with its origin trace, and (once gated) filters shared-origin ones out of `candidate_conflicts()` / the announce loop, logging each suppression append-only to `gate_decisions.jsonl` (`gate:'independence'`), auditable and human-overridable.

**Capability unlocked:** the human's contradiction queue shows only **genuinely independent** tensions — two different origins actually disagreeing — instead of one origin's internal revisions masquerading as refutations. It is `poisoning_signals`' complement: that flags low-independence claims *attacking* an anchor; this flags low-independence *tensions* not worth a human's escalation, using the same lab-independence unit, in **code not model self-report**, **conservatively** (suppress only when the entire disagreement is one origin talking to itself), and **advisory-until-validated** (RQ-E50 gates the suppression; until it passes the tension still reaches the human, merely badged).

---

## 1. File ownership (disjoint)

| File | New? | Role |
|---|---|---|
| `persona/memory/kg.py` | edit | Add `shared_origin(claim_a_id, claim_b_id)` read (FC-28) — one Cypher fetching both claims' `SUPPORTED_BY` sources' `lab`/`slug`/`doi`/`title`, the cross-pair origin computation. Extend `candidate_conflicts(...)` (`kg.py:273-276`) with an additive `*, include_suppressed=False` kwarg: annotate every candidate with its `shared_origin` trace; when `ops_dir/rq_e50.passed` exists, omit shared-origin candidates unless `include_suppressed=True`. New private `_origin_share(src_i, src_j)` helper (reuses the `lab` field `lab_of` set at `kg.py:129`). |
| `persona/memory/membrane.py` | edit | In `_harvest`'s announce loop (`membrane.py:106-115`): consult `kg.shared_origin` per contradiction; annotate the log event; once gated, skip *announcing* a shared-origin tension and append its `gate:'independence'` row to `gate_decisions.jsonl`. No new public membrane signature (reuses the existing loop; `admit_candidate`/`harvest` signatures unchanged). |
| `experiments/exp_contradiction_independence.py` | **new** | RQ-E50 sandbox (Lane-2-owns-its-RQ, per the PRD-05/06/12 precedent — flagged O-5). |
| `persona/tests/test_shared_origin.py` | **new** | Unit + gate tests (see §5). |

**Boundary files another lane owns — decoupled by FC-28, NOT edited here:**
- `persona/api/app.py`, `persona/api/static/*` — **Lane 4 owns.** They already call `g.candidate_conflicts()` (`app.py:569`, `app.py:630`) and `g.gate_decisions` (`app.py:1450-1464`); with FC-28 they render the origin trace + a "suppressed: shared origin" badge, and add a human-override view that calls `candidate_conflicts(include_suppressed=True)`. Read-side only; PRD-36 provides, Lane 4 renders.
- `persona/memory/conflicts.py` — **Lane 2 self, but out of scope here.** `type_conflict` (`conflicts.py:27-43`) answers *why* two independent claims disagree; its `CONFLICT_TYPES` enum `{temporal, semantic, misinformation, insufficient}` (`conflicts.py:14`) is **FC-2-frozen and NOT extended** — shared-origin is an *independence* flag orthogonal to conflict type, carried as its own `shared_origin` field on the candidate, never as a fifth `conflict_type`. (Order of operations: independence pre-check runs *before* typing — a suppressed tension is never typed.)
- `ops_dir/gate_decisions.jsonl` — **shared FC-8 ledger** (Lane 2 appends `drift`/`membrane` rows today). This PRD appends `gate:'independence'` rows — an **additive enum extension** (see §2 CCP-36a).

---

## 2. FCs provided / consumed

### PROVIDES — **FC-28 (Lane 2), new `kg.shared_origin`** — additive to FC-3 (kg independence reads); no new membrane signature

```python
# persona/memory/kg.py  (KG method)
def shared_origin(self, claim_a_id: str, claim_b_id: str) -> dict:
    """Do BOTH sides of a candidate contradiction trace to a single shared primary origin?
    Reuses the independence-by-lab unit (Source.lab, set by lab_of at kg.py:129). A tension is a
    shared-origin FALSE tension ONLY when EVERY cross-side source pair shares an origin
    (independent_pairs == 0 and total_pairs > 0); any independent pair => genuine tension.
    Read-only; never mutates a belief; conservative on absent evidence (no sources => shared=False)."""
    # returns:
    # {
    #   "shared": bool,                    # True iff independent_pairs == 0 and total_pairs > 0
    #   "group_id": str | None,            # the shared origin key when shared (e.g. 'lab:broad institute'), else None
    #   "basis": str | None,               # 'same_lab' | 'preprint_published_pair' | 'same_dataset' (O-2) | None
    #   "independent_pairs": int,          # # of cross-side (src_a, src_b) pairs sharing NO origin
    #   "total_pairs": int,                # |sources(a)| * |sources(b)|
    #   "origins_a": list[str],            # distinct origin keys on side A  (legibility; additive)
    #   "origins_b": list[str],            # distinct origin keys on side B  (legibility; additive)
    # }

# persona/memory/kg.py  (additive kwarg on the existing read — NOT a signature break)
def candidate_conflicts(self, limit: int = 100, *, include_suppressed: bool = False) -> list:
    # each row additionally carries:
    #   "shared_origin": {shared, group_id, basis, independent_pairs, total_pairs}   # the FC-28 trace
    #   "suppressed": bool           # shared AND ops_dir/rq_e50.passed exists (else False — advisory)
    # Behaviour: gate PRESENT + suppressed rows are OMITTED unless include_suppressed=True.
    #            gate ABSENT  -> nothing omitted (advisory); every row annotated, suppressed=False.
```

**Frozen return shape = the six-key `shared_origin` dict** (`shared, group_id, basis, independent_pairs, total_pairs` + the two legibility lists). Origin equivalence is evaluated **pairwise** (`_origin_share(src_i, src_j)`), not by a single hashed key, so a preprint↔published pair with differing lab strings can still share an origin.

### CONSUMES
- **FC-3** (`kg.py` independence reads, PRD-00 §4) — specifically the `Source.lab` independence unit (`lab_of` `kg.py:64-68`, set at `kg.py:129`) and `crosscheck`/`provenance` source-fetch pattern (`kg.py:432-451`, `kg.py:278-295`). No new consumption contract; `shared_origin` is a sibling read in the same file.
- **FC-8 shared ledger** `ops_dir/gate_decisions.jsonl` (PRD-00 §4 line 68) — append-only, one row per suppression.
- Existing `membrane._harvest` announce loop (`membrane.py:101-116`) — Lane 2 self.

### CONTRACT CHANGE PROPOSAL — CCP-36a (additive, minimal; needs master ratify)
The FC-8 ledger `gate` enum is `'relevance'|'drift'|'membrane'|'redteam'` (PRD-00 §4). This PRD needs `gate:'independence'`. **Extend the enum additively** (exactly as `'redteam'` was added 2026-07-13): `gate += 'independence'`. No field/shape change; every consumer reads the enum as an opaque string (`app.py:1450-1464`, `epistemic.js:91`). Surfaced also as **O-1** for the master to ratify. *No other contract change is required; I do not mint a new FC/RQ id.*

---

## 3. Features

---

### F36.1 — Origin-tracing read `kg.shared_origin` (`memory/kg.py`)

**Problem & evidence.** Contradictions fire on `pair_key` + opposite `effect_sign` with **zero origin check**: `link_all_contradictions` (`kg.py:191-202`) matches `a.effect_sign='+' AND b.effect_sign='-'` on a shared `pair_key` and merges `CONTRADICTS` — it never looks at `Source.lab`. The store *has* the independence unit already (`lab_of` `kg.py:64-68`; `independent_source_count = count(DISTINCT s.lab)` `kg.py:172-173`; and `poisoning_signals` `kg.py:297-309` already treats a low `independent/support` ratio as suspect) — but the contradiction path is blind to it. Research/source: this is the *echo-chamber / non-independence* problem the store's design memo names ("citation echo can't inflate", `kg.py:8`); the standard framing is that agreement **and disagreement** are only informative between *independent* sources (independence-of-evidence, e.g. the meta-analytic unit-of-analysis rule — one lab's preprint+paper is one unit, not two).

**Design.**
- `shared_origin(a, b)`: one Cypher fetches both claims' supporters —
  `MATCH (c:Claim {claim_id:$cid})-[r:SUPPORTED_BY]->(s:Source) RETURN s.lab, s.slug, s.doi, s.title` for each of A and B. Build `sources_a`, `sources_b`.
- **Pairwise origin relation** `_origin_share(si, sj) -> (bool, basis)`:
  - `same_lab` — `si.lab == sj.lab` and non-empty (the primary, live basis; `lab` is the existing independence unit).
  - `preprint_published_pair` — exact normalized-title match (`_norm(si.title) == _norm(sj.title)`, both non-empty) **or** a linked preprint/journal DOI pair (e.g. `10.1101/...` biorxiv DOI ↔ its published DOI when the store records the link). Conservative: title match must be exact after normalize (casefold + whitespace-collapse), never fuzzy.
  - `same_dataset` — **deferred (O-2):** `Source` carries no dataset accession today; the hook exists in `_origin_share` but returns `False` until a dataset signal lands. Naming it in `basis` is forward-compatible only.
- Count `total_pairs = len(sources_a) * len(sources_b)`; `independent_pairs = #{(si,sj) : not _origin_share(si,sj)[0]}`. `shared = (total_pairs > 0 and independent_pairs == 0)`. When `shared`, `group_id` = the common origin key (the shared `lab`, or the normalized-title hash for a preprint pair) and `basis` = the relation that held for all pairs (`same_lab` dominates when mixed).
- Pure read, no belief mutation, offline, no model, no budget — a `forensics.py`-class deterministic check.

**Epistemic guardrails.** **Conservative by construction:** suppression requires *every* cross-pair to share an origin; one independent pair keeps the tension. **Never suppresses on absent evidence** — `total_pairs == 0` (a side with no live source) ⇒ `shared=False`. Reuses the *validated* independence unit (`lab`) — it does not invent a second notion of independence that could drift from `independent_source_count`. Never touches anchored/HUMAN_CONFIRMED beliefs' edges; it only reads. No model self-report of "these are the same lab" — it is string/DOI identity over stored `Source` fields.

**Required experiment.** **RQ-E50** (F36.3) — this read *drives* whether a contradiction is withheld from a human, so it is load-bearing and gets the full loop *before* it suppresses anything.

**Acceptance + ONE runnable check.** (a) two claims each supported only by sources with `lab == 'lab:x'` → `shared=True, basis='same_lab', independent_pairs==0`; (b) claim A from `lab:x`, claim B from `lab:x` **and** `lab:y` → `shared=False, independent_pairs>=1` (the y×x pair is independent); (c) A/B sources sharing an exact normalized title but different `lab` strings → `shared=True, basis='preprint_published_pair'`; (d) a side with zero sources → `shared=False, total_pairs==0`. Runnable: `pytest persona/tests/test_shared_origin.py::test_shared_origin_all_pairs_rule` (stubbed `_q`, mirroring existing kg tests).

**Effort** M · **Deps** existing `kg`, FC-3.

---

### F36.2 — Pre-check wiring: annotate → gate-suppress → log (`memory/kg.py` `candidate_conflicts`, `memory/membrane.py` announce loop)

**Problem & evidence.** The tension reaches the human through two chokepoints, both origin-blind: `kg.candidate_conflicts()` (`kg.py:273-276`, consumed at `app.py:569` `/epistemic` and `app.py:630` `/inbox`), and the membrane announce loop (`membrane.py:106-115`) that logs a `contradiction` event per pair. Suppression must sit at *these* queue/announce points — **not** at edge creation (`link_all_contradictions`), because the structural `CONTRADICTS` edge is legitimately read by `poisoning_signals` (`kg.py:297-309`), `stats` (`kg.py:244`), and trajectory surfaces; deleting it would blind them.

**Design.**
- **`candidate_conflicts(limit, *, include_suppressed=False)`** (single chokepoint — both API routes already funnel through it): for each candidate call `so = shared_origin(pos_claim, neg_claim)`; attach `"shared_origin": so`. Compute `suppressed = so["shared"] and _gate_passed()` where `_gate_passed()` ⇔ `ops_dir/rq_e50.passed` exists. When the gate is present, omit `suppressed` rows unless `include_suppressed=True`; when absent, omit nothing (advisory — annotate only). This is additive (new keyword-only kwarg; all existing calls — `()`, `(limit=50)`, `(100)` — behave identically until the gate flag lands).
- **Announce loop** (`membrane.py:106-115`): before `log().emit("contradiction", ...)`, call `kg.shared_origin(c["pos_claim"], c["neg_claim"])`. Always attach the trace to the event (legibility). When the gate is present *and* `shared`, **skip the announce** and append one row to `ops_dir/gate_decisions.jsonl`:
  `{"candidate_id": conflict_id(pos,neg), "title": f"{subject} → {object}", "gate": "independence", "decision": "skip", "reason": f"all {total_pairs} cross-source pairs share origin {basis}:{group_id}", "score": independent_pairs/total_pairs, "at": <iso>}` (append-only, never edits another lane's rows — the FC-8 discipline).
- **Human override.** A suppressed candidate is *never destroyed* — it is (i) always retrievable via `candidate_conflicts(include_suppressed=True)` (Lane-4 override view), and (ii) fully recorded in the append-only ledger with its reason. A human forcing re-escalation is out-of-band (Lane-4 renders the override list); PRD-36 guarantees the data is present and the decision auditable.

**Epistemic guardrails.** **Advisory until RQ-E50 passes:** with no `rq_e50.passed` flag, the pre-check changes *nothing* that reaches the human — it only badges — so a wrong origin trace can never silently bury a real contradiction before the check is validated (matches how PRD-12/-20 hold load-bearing autonomy behind their RQ gate flags). **The structural edge is untouched** — suppression is a *routing* decision, reversible by deleting the flag. **Every suppression is append-only + auditable + overridable** (`gate_decisions.jsonl`, the FC-8 pattern; a human can always see and re-open it). Order: independence pre-check precedes `type_conflict` — a suppressed tension is never typed or escalated.

**Required experiment.** Inherits **RQ-E50** (the suppression it performs is exactly what E50 gates). The annotate/omit plumbing itself is deterministic and unit-tested (§5), not seeded.

**Acceptance + ONE runnable check.** With `rq_e50.passed` absent, a shared-origin candidate is returned with `shared_origin.shared == True` and `suppressed == False` (still escalates). With the flag present, the same candidate is omitted from `candidate_conflicts()` but present in `candidate_conflicts(include_suppressed=True)`, and one `gate:'independence'` row is appended to `gate_decisions.jsonl`; a genuinely-independent candidate is returned in both cases. Runnable: `pytest persona/tests/test_shared_origin.py::test_precheck_advisory_then_suppresses_behind_gate`.

**Effort** M · **Deps** F36.1; existing `candidate_conflicts`, `_harvest` announce loop.

---

### F36.3 — Precision of the independence pre-check (RQ-E50)

**Problem & evidence.** The pre-check *withholds a contradiction from a human*. The dangerous error is a **false suppression** — burying a genuinely independent tension — which is exactly the "silent wrong number that propagates into the belief-state … the worst possible bug" (`CLAUDE.md §4`) applied to *non-escalation*. So the suppression is a pre-registered go/no-go: it must remove shared-origin false tensions **without** losing genuine ones, and stay advisory (annotate-only) until it clears.

### Required experiment — RQ-E50 (register in `docs/RESEARCH_QUALITY_PROGRAM.md`)

- **Sandbox.** `experiments/exp_contradiction_independence.py`; results → `results/FINDINGS.md#RQ-E50`. Offline, deterministic classifier + bootstrap seeds.
- **Oracle / labeled set.** A fixture of contradiction pairs, each labeled `shared_origin_false_tension` **or** `genuinely_independent`, built from real `sources/*/meta.json` affiliations so `lab_of` is exercised on real strings. Positive (false-tension) cases: two sides whose supporters all resolve to one lab, plus a preprint↔published pair of one paper. Negative (genuine) cases: cross-lab disagreements, including a **near-miss** where one side has a single extra independent lab (must stay genuine — tests the all-pairs rule). **Independence labels are human/curated, never model-emitted** (`CLAUDE.md §7`); if no human-labeled slice is available at build time, RQ-E50 **blocks** the gate (the pre-check ships advisory-only). See O-3.
- **Hypothesis.** *The all-cross-pairs origin rule (reusing `lab_of`) removes shared-origin false contradictions from the human queue without materially reducing recall of genuine independent contradictions.*
- **Metric (two numbers).**
  - `false_tension_precision` = P(label = shared-origin false tension | pre-check suppresses) — of what we bury, how much was truly one origin talking to itself.
  - `genuine_recall_loss` = P(pre-check suppresses | label = genuinely independent) — the fraction of real tensions wrongly buried (the safety metric; should be ~0 by the strict rule, non-zero only from dirty `lab`/DOI data).
- **Seeds ≥ 20.** Bootstrap-resample the labeled fixture 20× (stratified by label); report both metrics as **mean ± 95% CI**. Deterministic classifier ⇒ the seed varies the resample (the real small-set uncertainty).
- **Gate (pre-registered).** `false_tension_precision ≥ 0.85` **AND** `genuine_recall_loss ≤ 0.05` (upper 95% CI bound). **Pass** ⇒ write `ops_dir/rq_e50.passed`; the pre-check suppresses autonomously. **Fail** ⇒ no flag; the pre-check stays advisory (annotate the origin trace, never omit), a logged reversal (`CLAUDE.md §2`), and the fallback is to tighten `_origin_share` (e.g. drop the title-match basis) and re-gate.

**Epistemic guardrails.** Pre-registered gate, stated before results; no tuning-to-pass. Recall loss is the *hard* safety bound (asymmetric like PRD-12: burying a real tension is worse than showing a redundant one). Labels are human; the experiment never grades itself against Persona's own output.

**Acceptance + ONE runnable check.** The script runs offline on the committed fixture, prints the mean±CI table + the gate boolean, and appends to `results/FINDINGS.md#RQ-E50`. Runnable: `pytest persona/tests/test_shared_origin.py::test_rq_e50_recall_loss_under_gate` (asserts `genuine_recall_loss` upper-CI ≤ 0.05 and `false_tension_precision` ≥ 0.85 on the fixture, ≥20 resamples, offline).

**Effort** M · **Deps** F36.1; human-labeled fixture (O-3).

---

## 4. Sequencing

**Milestone 0 (hour 1 — land the FC-28 stub so Lane 4 builds against it):** ship `kg.shared_origin(a, b)` returning `{shared:False, group_id:None, basis:None, independent_pairs:0, total_pairs:0, origins_a:[], origins_b:[]}` and the additive `candidate_conflicts(..., *, include_suppressed=False)` kwarg (annotates `shared_origin` from the stub, `suppressed=False`). File **CCP-36a** (ledger enum `+= 'independence'`) in the HANDOFF dispatch log. Repo stays runnable — the stub suppresses nothing.

Then: **F36.1** (real `shared_origin` + the all-pairs rule, with its unit tests) → **F36.3 / RQ-E50** (validate F36.1 on the human-labeled fixture; the gate flag is *not* written until it passes) → **F36.2** (wire `candidate_conflicts` + the announce loop + the ledger append; ships advisory, becomes suppressive only once `rq_e50.passed` exists).

Rationale: nothing is withheld from a human until the origin trace clears RQ-E50; annotation and the structural edge are safe from hour 1.

---

## 5. Test plan

| Check | File / name | Asserts |
|---|---|---|
| All-pairs rule | `test_shared_origin.py::test_shared_origin_all_pairs_rule` | same-lab both sides ⇒ `shared`; one extra independent lab on a side ⇒ not shared (`independent_pairs≥1`); zero sources ⇒ `shared=False`, `total_pairs==0` |
| Preprint pair basis | `test_shared_origin.py::test_preprint_published_pair_basis` | exact normalized-title match across differing `lab` strings ⇒ `shared=True, basis='preprint_published_pair'`; fuzzy/partial title ⇒ not shared |
| Advisory → gated | `test_shared_origin.py::test_precheck_advisory_then_suppresses_behind_gate` | no flag ⇒ shared-origin candidate returned with `suppressed=False`; flag present ⇒ omitted from default `candidate_conflicts()`, present with `include_suppressed=True`, one `gate:'independence'` ledger row appended |
| Genuine tension never buried | `test_shared_origin.py::test_independent_pair_keeps_contradiction` | a candidate with ≥1 cross-lab independent pair is returned even with the gate flag present |
| Enum orthogonality | `test_shared_origin.py::test_shared_origin_is_not_a_conflict_type` | `conflicts.CONFLICT_TYPES` unchanged; the shared-origin flag rides as its own field, not a 5th type |
| RQ-E50 gate | `test_shared_origin.py::test_rq_e50_recall_loss_under_gate` | on the committed fixture, `genuine_recall_loss` upper-CI ≤ 0.05 AND `false_tension_precision` ≥ 0.85, ≥20 resamples, offline |
| Experiment oracle | `experiments/exp_contradiction_independence.py` | prints mean±95%CI for both metrics + the gate boolean; appends to `results/FINDINGS.md#RQ-E50` |

---

## 6. Open questions

- **O-1 (CCP-36a / FC-8 ledger enum — needs master ratify).** Add `'independence'` to the frozen `gate` enum (`'relevance'|'drift'|'membrane'|'redteam'` → `+ 'independence'`), exactly as `'redteam'` was added. Purely additive; every reader treats `gate` as an opaque string. **Recommended default: ratify** — the suppression is un-auditable without a ledger row, and the enum has been extended additively before. Blocks the F36.2 suppression ledger append until acked.
- **O-2 (`same_dataset` basis — deferred).** `Source` stores no dataset accession, so `_origin_share` cannot detect two sources reanalysing one GEO/dataset today. **Recommended default: ship `same_lab` + `preprint_published_pair` only**; name `same_dataset` in `basis` as a forward-compatible hook that returns `False` until a dataset-accession signal lands on `Source` (a later, additive PRD). Do not block on it.
- **O-3 (RQ-E50 human dependency — the oracle).** The labeled fixture needs a human to mark each contradiction pair `shared_origin_false_tension` vs `genuinely_independent` (independence labels are never model-synthesized, `CLAUDE.md §7`). **Recommended default:** build the fixture from real `sources/*/meta.json` affiliations + a small hand-labeled slice; **until a human-labeled slice exists, RQ-E50 blocks the gate** and the pre-check ships advisory-only (annotate, never suppress). Surface to the master: who provides the independence labels?
- **O-4 (preprint↔published DOI linkage).** The `preprint_published_pair` basis currently leans on exact normalized-title identity; a DOI-link basis (biorxiv `10.1101/...` ↔ published DOI) is stronger but needs the store to record the pairing. **Recommended default: title-identity only for v1**, gated by RQ-E50; if E50 shows title-match drives false suppressions, drop it (fallback in F36.3) and revisit DOI linkage.
- **O-5 (experiment/test file ownership).** PRD-00 §3 files `experiments/*`/`tests/*` under Lane 4, but PRD-05/06/12 have each lane ship its own RQ experiment + unit test. PRD-36 follows that precedent (`experiments/exp_contradiction_independence.py`, `persona/tests/test_shared_origin.py`). **Recommended default: confirm the precedent**, or route the experiment file through Lane 4.
