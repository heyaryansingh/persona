# PRD-25 — Claims-must-not-make blocklist guardrail

> **Owner lane:** 2 + 4 · **Status:** DRAFT-for-implementation · **Autonomy:** Balanced · **Depends-on:** none (self-contained new module; consumers are additive one-liners). Coordinates a one-line hook in a Lane-3 file (`agents/audit.py`) via CCP-25a.
>
> **Read first:** `PRD-00-overview.md` §4/§6/§8 (govern), `results/FINDINGS.md` (the reversal ledger this PRD reifies), `docs/CONTINUATION_HANDOFF.md` §10 ("Claims the next agent must not make"), `docs/prd/IDEAS_BACKLOG.md` #9. Per PRD-00 §8, §4/§6 win on any id disagreement.

---

## 0. Summary + capability unlocked

Persona has already earned, and written down, a set of **debunked or over-reached claims** — reversals discovered by its own experiments and preserved in `results/FINDINGS.md` and `CONTINUATION_HANDOFF.md` §10:

- *"stop citing '88% vs 68% of all poisoned' as an anchoring win"* (`FINDINGS.md:81` — the anchoring advantage was an artifact of the human-confirmed subset).
- *"E7 as originally framed is not a valid test"* (`FINDINGS.md:288` — VoI-vs-genetic-prior is ill-posed).
- *"Do not say the GEO result validates the biological hypothesis"* / *"not as a biological discovery"* (`FINDINGS.md:523`, `CONTINUATION_HANDOFF.md:261` — `inconclusive`, same-donor, FTL-sensitive, `contested`).
- *"Do not claim the paper system is generally reproducible yet"* (`FINDINGS.md:432`).
- *"Do not ship the lexical direction checker as an admission gate"* (`FINDINGS.md:337`).
- plus the six standing don'ts in `CONTINUATION_HANDOFF.md` §257–265 (contradiction "solved", dense memory "better", "pretrained/RL-trained", "fully redesigned", etc.).

**The gap:** nothing stops a future generation from *silently re-asserting* one of these. `paper.py`, `review.py`, `agents/audit.py`, and `agents/knowledge.py` each call an LLM whose only guardrail is a generic "ground every claim / don't invent" instruction (e.g. `paper.py:33 _SYSTEM`, `review.py:29`, `audit.py:68 _ADJ_SYS`, `knowledge.py:120`). None of them knows about the specific claims the project has already *retired*. A drafted paper can happily print "88% vs 68%" again; the reversal lives in a Markdown file no prompt reads.

**This PRD** reifies those human-written reversals into a **machine-readable, human-curated blocklist** and wires it into every generation/LLM-judge seam so a debunked claim (a) is discouraged in the prompt and (b) is **conservatively screened out of the output and surfaced** — never silently edited, never model-invented.

**Capability unlocked:** the reversal ledger stops being passive documentation and becomes an **active guardrail with memory across sessions** — Persona cannot quietly walk back a reversal it already paid (in experiments) to learn. This is the anti-slop counterpart to anchoring: anchoring protects *confirmed* beliefs from poisoning; the blocklist protects *disconfirmed* claims from resurrection.

---

## 1. File ownership (disjoint)

| File | New? | Owner | Notes |
|---|---|---|---|
| `persona/memory/blocklist.py` | **new** | Lane 2 | FC-17 provider. `memory/` is Lane 2 (§3). |
| `persona/memory/claims_blocklist.jsonl` | **new** | Lane 2 | The curated data file (human-authored from FINDINGS reversals). Package data, ships in-tree. |
| `persona/deliverables/paper.py` | edit | **this PRD (2+4)** | `deliverables/` is unassigned in §3 → owned here for the additive guard. **Boundary flag ↓** |
| `persona/deliverables/review.py` | edit | **this PRD (2+4)** | as above. |
| `persona/agents/knowledge.py` | edit | **this PRD (2+4)** | `agents/knowledge.py` is unassigned in §3 (Lane 1 owns a named subset that excludes it). Owned here for the additive guard. **Boundary flag ↓** |
| `persona/agents/audit.py` | edit (1 line) | **Lane 3** | `agents/audit.py` is **Lane 3** (§3, §53). Hook added by Lane 3 as **CCP-25a** — mirrors the CCP-10 sleep-consolidation one-liner pattern. |
| `persona/api/app.py` | edit (new route only) | Lane 4 | `GET /api/blocklist`. |
| `persona/api/static/index.html` | edit (new surface only) | Lane 4 | Small read-only legibility panel. |
| `experiments/exp_rq_e41_blocklist.py` | **new** | Lane 4 | RQ-E41 fault-injection. |
| `results/rq_e41_blocklist.json` | **new** | Lane 4 | RQ-E41 result. |
| `tests/test_blocklist.py` | **new** | Lane 4 | Unit + regression. |

**Boundary decoupling.** Every consumer touches the blocklist through **FC-17 only** — two additive lines (`prompt_block()` inject before the call, `screen()` after). No consumer imports blocklist internals or the data file. `deliverables/` and `agents/knowledge.py` are unassigned in §3, so this PRD editing them collides with no lane. `agents/audit.py` is Lane-3-owned, so its two-line hook is a **CONTRACT CHANGE PROPOSAL (CCP-25a)** that Lane 3 lands in its own file — decoupled by the FC, not by shared editing.

---

## 2. FCs provided / consumed + CONTRACT CHANGE PROPOSAL

### Provided — **FC-17** (Lane 2, new `persona/memory/blocklist.py`)

Copy verbatim:

```python
def entries() -> list[dict]:
    """Curated blocklist rows, loaded once (lru_cache) from claims_blocklist.jsonl.
    Row: {id:str, patterns:[str], reason:str, findings_ref:str, severity:'hard'|'soft'}.
    Returns [] if the file is absent/empty (fail-open: a blank blocklist blocks nothing)."""

def prompt_block() -> str:
    """A ready-to-inject 'CLAIMS YOU MUST NOT MAKE' instruction built from entries().
    Returns '' when there are no entries (so the append is a guaranteed no-op)."""

def screen(text: str) -> list[dict]:
    """CONSERVATIVE, code-only screen of generated text against every entry's patterns.
    Returns hits [{id, matched:str, reason:str, findings_ref:str, span:str}] (empty == clean).
    NEVER mutates text. Deterministic (regex/normalized-substring); no model call."""

def quarantine(kind: str, ref: str, hits: list[dict], *, parent_id=None) -> None:
    """Record a blocklist hit to the legibility stream (events.log) so a flagged claim is
    SURFACED, not silently dropped. No-op when hits is empty. Pure side-effect (logging)."""
```

- Data file `persona/memory/claims_blocklist.jsonl` is **human-curated** (never written by a model). Each row carries a `findings_ref` (e.g. `"FINDINGS.md:81"` or `"CONTINUATION_HANDOFF.md:261"`) so every blocked claim is provenance-linked to the reversal that earned it.
- **Fail-open by construction:** empty/absent file → `entries()==[]` → `prompt_block()==""` → `screen()==[]`. A missing blocklist never blocks a legitimate generation (same failure posture as `_relevance_filter` fail-open in RQ-E14).

### Consumed
- `events.log().emit(kind, msg, actor=, parent_id=, file=)` (existing legibility stream) — used by `quarantine()`.
- No FC-1..FC-16 consumed. No signature of any existing FC changes.

### CONTRACT CHANGE PROPOSAL — **CCP-25a** (→ Lane 3)
`agents/audit.py` gains a two-line hook at its **adjudicator** seam (NOT the extractor — the extractor transcribes untrusted paper text; the blocklist governs *Persona's own* generated verdict prose):
1. append `blocklist.prompt_block()` to `_ADJ_SYS` (line 68) or the `adj_prompt` (line 236);
2. after `adj` is parsed (line 247), `hits = blocklist.screen(adj.get("executive_summary","") + " ".join(per-claim reasoning))`; on hits call `blocklist.quarantine("audit", result_title, hits, parent_id=parent_id)` and attach `result["blocklist_hits"]=hits`.
Additive, backward-compatible, no signature change to `audit()`. Acked by master + Lane 3 before it lands.

**Next-free registry (per PRD-00 §4/§6):** this PRD claims **FC-17** and **RQ-E41** (both pre-assigned to PRD-25 in IDEAS_BACKLOG iter-19). No collision.

---

## 3. Features

### F25.1 — Curated blocklist + FC-17 loader/screen (`memory/blocklist.py`)

**Problem & evidence.** The reversals exist only as prose. `FINDINGS.md:81` literally instructs "stop citing '88% vs 68%'"; `FINDINGS.md:288` "E7 as originally framed is not a valid test"; `CONTINUATION_HANDOFF.md:261` "Do not say the GEO result validates the biological hypothesis." No code path consults them. Research context: this is a *negative-constraint / claim-verification* guardrail. The defensible design is **deterministic matching in code**, not a semantic/LLM matcher — consistent with the program's rule that *forensics run in CODE, never a model* (PRD-00 §2) and its precision-biased gates (RQ-E14/E15). An LLM or embedding matcher would (a) let the model police itself, (b) add unsurfaceable false positives, and (c) be non-auditable. Considered and rejected; the RQ-E41 false-positive gate is the discriminator.

**Design.**
- **Data file** `claims_blocklist.jsonl`, one JSON object per line. Seed it from the reversals above; each row:
  ```json
  {"id":"anchoring-88-68","patterns":["88%\\s*vs\\.?\\s*68%","88 percent vs.* 68 percent","880*\\s*(?:vs|versus).*680*"],
   "reason":"Anchoring did NOT broadly rescue poisoned beliefs; the 0.880-vs-0.683 gap is an artifact of the human-confirmed subset. Cite non-human-victim recovery instead.",
   "findings_ref":"FINDINGS.md:81","severity":"hard"}
  ```
  Curator supplies **multiple surface patterns per claim** (favouring precision) — the human, not a model, decides what counts.
- **`entries()`** — `@lru_cache(maxsize=1)` read of the jsonl relative to `__file__` (no path plumbing, ships with the package). Malformed lines skipped (fail loud to a warning, never crash a generation).
- **`prompt_block()`** — joins each `severity=="hard"` (and optionally soft) row's `reason` into a bulleted "## CLAIMS YOU MUST NOT MAKE — these were tested and retired; do not assert or re-derive them" block. `""` when empty.
- **`screen(text)`** — for each entry, each pattern: `re.search(pattern, text, re.I)` over whitespace-normalized text; on match record `{id, matched, reason, findings_ref, span}` where `span` is ±80 chars of context (the exact-span discipline: surface *where* it fired). Conservative: literal/curated regex only, no fuzzy expansion.
- **`quarantine()`** — `log().emit("needs_human", f"blocklist: '{hit['matched']}' — {hit['reason']}", actor="blocklist", parent_id=...)` per hit. Uses the *existing* legibility stream (no new ledger file needed — ponytail: reuse the events log the UI already renders).

**Epistemic guardrails.** Blocklist is human-curated (rows never model-written); `screen()` never mutates text (returns hits, caller quarantines); `findings_ref` on every row keeps provenance to the reversal; fail-open when empty. Matching is precision-biased (paraphrases may slip — a known, curator-upgradable ceiling; see F25.1 test + Open Q).

**Required experiment.** RQ-E41 (see F25.5) covers this feature's core claim; the loader itself is otherwise a trivial jsonl read.

**Acceptance + one runnable check.** `tests/test_blocklist.py::test_screen_catches_seeded_and_passes_clean` — `screen("...we retain 88% vs 68% of poisoned...")` returns ≥1 hit with `id=="anchoring-88-68"`; `screen("neuroinflammation drives neurodegeneration across 7 independent labs")` returns `[]`. `prompt_block()` is non-empty and contains "88%". `entries()` on a temp empty file → `[]`, `prompt_block()==""`, `screen("88% vs 68%")==[]` (fail-open).

**Effort:** S. **Deps:** none.

---

### F25.2 — Inject + screen at the two deliverable seams (`paper.py`, `review.py`)

**Problem & evidence.** `paper.py::write_paper` generates a full paper at `paper.py:252` (main) and `:269` (regen) under `_SYSTEM` (`:33`), post-processes at `:293–296`, and ships to `deliverables/` at `:349–352` — with **zero** check against retired claims. `review.py::write_review` generates at `:71`, checks only *citation support* (`checker.check`, `:83`), and writes at `:87–93`. A paper asserting the GEO result is a "biological discovery" would compile and ship.

**Design (files, signatures, data flow, seams).**
- `paper.py`: after building `msgs`, append `blocklist.prompt_block()` to `_SYSTEM` (pass a combined system string to `client.messages.create`, `:252` and `:269`). After final post-processing (`:296`, before the substance-floor write at `:300`): `hits = blocklist.screen(md)`. If `hits`: `blocklist.quarantine("paper", title, hits, parent_id=parent_id)`, and **quarantine the deliverable** — write it to `project/` and record `receipt["blocklist_hits"]=hits`, but return `{"ok": False, "reason": "blocklist-quarantine", "blocklist_hits": hits, "project": ...}` so a flagged paper is **held for human review, not published to `deliverables/`**. (Never auto-edit the prose — surface the hit and stop.)
- `review.py`: append `prompt_block()` to `_SYSTEM` (`:71`). After `out` is parsed (`:82`): `hits = blocklist.screen(out.get("review_markdown","") + " " + out.get("abstract",""))`. On hits → `quarantine("review", title, hits)` + return `{"ok": False, "reason": "blocklist-quarantine", "blocklist_hits": hits}` (do not write the file).
- Both: `from ..memory import blocklist` (import-light; `entries()` is cached).

**Epistemic guardrails.** Preventive (prompt) + detective (screen) — the screen is authoritative because the model may ignore the prompt. Quarantine = hold + surface, never silent deletion (a blocked paper is visible to the human with the exact matched span and reason). Fail-open: empty blocklist → both hooks are no-ops, existing behaviour unchanged.

**Required experiment.** Covered by RQ-E41 (F25.5) via fault-injection into the real `write_paper` path (seed a debunked claim into the notes/prompt, assert quarantine fires).

**Acceptance + one runnable check.** `tests/test_blocklist.py::test_paper_quarantines_debunked` — monkeypatch the Anthropic client to return markdown containing "the GEO result is a biological discovery"; assert `write_paper(...)["ok"] is False` and `reason=="blocklist-quarantine"` and no new file in `deliverables/`. Clean markdown ships normally (`ok True`).

**Effort:** S. **Deps:** F25.1.

---

### F25.3 — Inject + screen at the two knowledge/answer seams (`knowledge.py`)

**Problem & evidence.** `knowledge.py::topic_digest` generates a layered briefing at `:120` and `ask_graph` answers at `:150` — both grounded in the KG but with **no reversal guardrail**. A digest could state "Persona has solved contradiction detection" (`CONTINUATION_HANDOFF.md:259` forbids exactly this) if a stale claim implied it.

**Design.**
- `topic_digest`: append `blocklist.prompt_block()` to the brief `system` (`:120`). After `digest` is parsed (`:128`): screen the concatenation of `digest["tldr"], digest["narrative"]` and the `settled`/`contested` lists; on hits, `quarantine("digest", q, hits)` and attach `base["blocklist_hits"]=hits` — but **still return the digest** (this is a read-only briefing to a human who is *reviewing*, per the module docstring; here we surface+annotate rather than withhold, because there is no artifact being published). Downgrade: mark `digest["blocklist_flagged"]=True` so Lane 4 renders the warning inline.
- `ask_graph`: append `prompt_block()` to the answer `system` (`:150`). Screen `out.get("answer","")`; on hits → `quarantine("answer", q, hits)` + `result["blocklist_hits"]=hits` (answer still returned, flagged).

**Epistemic guardrails.** For non-published, human-in-the-loop read surfaces (digest/answer), the conservative action is **surface + annotate**, not withhold (the human is already the reviewer). For *published artifacts* (paper/review, F25.2), the action is **hold**. This split is deliberate and matches PRD-00 §5 "honest uncertainty in the UI" vs the higher bar for a shipped deliverable. Never a silent edit either way.

**Required experiment.** Covered by RQ-E41 false-positive arm (digest/answer over real clean claims must not flag).

**Acceptance + one runnable check.** `tests/test_blocklist.py::test_digest_flags_but_returns` — patched digest containing a §10-forbidden phrase → returned dict has `blocklist_hits` non-empty and `digest["blocklist_flagged"] is True`, `ok True` (not withheld).

**Effort:** S. **Deps:** F25.1.

---

### F25.4 — Legibility surface (`api/app.py`, `index.html`) — Lane 4

**Problem & evidence.** PRD-00 §5: "the product is legibility." A guardrail the user can't see is untrustworthy. The blocklist and its firings must be inspectable.

**Design.**
- `GET /api/blocklist` → `{"entries": blocklist.entries(), "recent_hits": [...] }` where `recent_hits` is scanned from the persona's event log for `actor=="blocklist"` events (reuse existing event storage; no new persistence). Route style matches `app.py:84+`.
- `index.html`: a small read-only panel (fits the existing robustness/trust tab, not a new top-level tab — PRD-00 §5 "if a screen doesn't answer a real question, cut it") listing each blocked claim with its `reason` + `findings_ref` link, and a short "quarantine log" of recent firings (what was caught, where). Monospace, one accent for a live firing (PRD-00 §6 aesthetic).

**Epistemic guardrails.** Read-only; renders provenance (`findings_ref`) so a user can verify every blocked claim traces to a real reversal. No control to *add* entries from the UI (curation is a human editing the jsonl + committing — deliberate friction, keeps "never model-invented").

**Required experiment.** trivial (rendering).

**Acceptance + one runnable check.** `PERSONA_WORKERS=0` browser smoke: `GET /api/blocklist` returns ≥1 entry with a `findings_ref`; the panel shows the "88% vs 68%" row. Plus `tests/test_blocklist.py::test_route_shape`.

**Effort:** S. **Deps:** F25.1.

---

### F25.5 — Required experiment RQ-E41 (fault-injection)

**Hypothesis.** *A curated blocklist screen catches a seeded debunked claim injected into a real generation, at high detection, while its false-positive rate on legitimate Persona-generated text is bounded.*

**Metric + gate (pre-registered).**
- **Detection:** over ≥20 seeds, each injecting a randomly-chosen blocklist claim (in ≥3 surface forms per claim: verbatim, whitespace-varied, and a curator-listed paraphrase) into a `write_paper`/`write_review`/`topic_digest` output, `screen()` (and hence quarantine) fires. **Gate: detection ≥ 0.95** on the seeded set (target 1.0 for verbatim/whitespace forms; paraphrase forms measured separately and reported — see Open Q).
- **False positive:** run `screen()` over a legitimate corpus = the persona's own real shipped notes/papers/audit summaries (`deliverables/`, `notes/`) that are known-clean. **Gate: false-positive rate 95%-CI upper bound ≤ 0.05** (precision-biased, matching RQ-E15/E36). A single false quarantine of legitimate text is the correctness boundary (blocking a true claim is worse than the guardrail's value).
- Both computed with mean ± 95% CI over ≥20 seeds; result JSON to `results/rq_e41_blocklist.json`; **no model calls** (deterministic screen over fixed corpora → free + reproducible, seeded).

**Design.** `experiments/exp_rq_e41_blocklist.py`: build a fixed clean corpus from real repo text; for each seed, splice one blocklist claim (random surface form) into a random clean document → assert a hit; count false hits on the untouched clean corpus. Mirrors the E30/E36 fault-injection template (detection ≥0.95 AND false-quarantine bounded).

**Gate consequence.** Until `results/rq_e41_blocklist.json` shows PASS, the paper/review **quarantine-hold** in F25.2 ships as **advisory** (flag + surface + still write, like the digest path) rather than **block** (withhold). The hard *block* action for published artifacts turns on only behind `ops_dir/rq_e41.passed` — same "advisory until the RQ passes" discipline as FC-4/FC-13. Prompt-injection + screen-and-surface are safe to ship immediately (they cannot suppress a true claim).

**Effort:** M. **Deps:** F25.1–F25.3.

---

## 4. Sequencing

1. **F25.1** (loader + curated jsonl + FC-17) — land first; it is the only thing every other feature imports. Seed the jsonl from the six FINDINGS/§10 reversals in §0.
2. **F25.2 + F25.3** (the four generation seams) — parallel after F25.1; each is two additive lines behind FC-17. `agents/audit.py` hook is **CCP-25a** (Lane 3, coordinated).
3. **F25.5** (RQ-E41) — as soon as F25.1–F25.3 exist; its PASS flips the paper/review block from advisory to hard.
4. **F25.4** (legibility) — Lane 4, any time after F25.1 (renders `entries()`; `recent_hits` needs at least the quarantine emitter from F25.1).

Ship order is safe at every step: with only F25.1 landed, nothing changes behaviour (no consumer wired). Each seam added is fail-open.

---

## 5. Test plan

- **Unit** (`tests/test_blocklist.py`): `screen` catches each seeded reversal in ≥3 surface forms; `screen` passes a known-clean paragraph; `prompt_block` non-empty and contains a blocked phrase; empty-file fail-open (entries `[]`, prompt `""`, screen `[]`); malformed jsonl line skipped without crashing.
- **Integration:** `write_paper` / `write_review` quarantine a patched debunked output (no file written, `ok False`, `reason=="blocklist-quarantine"`); clean output ships. `topic_digest` / `ask_graph` flag-but-return.
- **Experiment gate:** `exp_rq_e41_blocklist.py` → detection ≥0.95 ∧ FP 95%-CI ≤0.05, ≥20 seeds, `results/rq_e41_blocklist.json`.
- **Route + UI:** `GET /api/blocklist` shape test; `PERSONA_WORKERS=0` browser smoke showing the panel with `findings_ref` links.
- **Regression oracle:** the blocklist jsonl itself is the regression suite — every future reversal added to `FINDINGS.md` should add a row (enforced by review habit, noted in the panel copy), so a debunked claim can never silently return.

---

## 6. Open questions

- **Q1 (paraphrase recall — known ceiling).** Deterministic patterns catch verbatim + whitespace + *curator-listed* paraphrases, but not novel rephrasings ("the eight-eight versus sixty-eight retention gap"). Precision-biased by design (RQ-E15 posture). Upgrade path: curator adds surface forms as reversals recur; an optional semantic layer is deferred behind its **own** false-positive experiment (never shipped without one, because a semantic matcher that blocks a true claim violates PRD-00 §2). *Non-blocking* — bounds are measured and reported in RQ-E41.
- **Q2 (block vs surface policy).** F25.2 *holds* published artifacts; F25.3 *surfaces* read-only briefings. Confirm this split with the user — is a paper with a blocklist hit "held for review" (proposed) or "shipped with a visible warning banner"? Default = hold (higher bar for a published deliverable). *Non-blocking* — flip is a one-line change gated on `ops_dir/rq_e41.passed`.
- **Q3 (curation authority — does not block other lanes).** The jsonl is human-edited only. Should adding a row require a second reviewer (like the conflict-review multi-rater discipline, §11), or is a single committer fine for a *negative* constraint? Proposed: single committer + the `findings_ref` provenance requirement (a row with no resolvable `findings_ref` is rejected by `entries()`), since a blocklist is conservative-by-construction (it can only *withhold*, never assert). *Non-blocking.*
- **Q4 (CCP-25a ack).** The `agents/audit.py` two-line hook needs Lane 3 + master ack before landing. Until then, the auditor seam ships without the guard (the other three seams are unaffected). *Blocks only the audit.py hook, not the PRD.*
