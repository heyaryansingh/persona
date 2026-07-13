# PRD-07 — DepMap functional-genomics knockout oracle

> Owner: implementer lane **3** (Engine / forensics / data acting-loop) · Status: **DRAFT-for-implementation** · Autonomy: **Balanced** · Depends on: PRD-00 file-ownership map + epistemic contract; consumes FC-3 (`kg` read paths, optional); provides new **FC-8 (proposed)**. Reuses the existing `IngestService` cache, `datasets.fetch` allowlist, and the `agents/audit.py` forensics-verdict pattern.

---

## 0. Summary + how it advances the vision

Persona today can re-check the *arithmetic* of a paper (`analysis/forensics.py` — statcheck/GRIM/GRIMMER/power/p-curve, run in code, line 155 `run_all`) and can pull structured biology from literature-adjacent APIs (`tools/science.py` — Open Targets, UniProt, ClinicalTrials, OpenAlex). **Every one of those signals is still a claim *about the literature*: an association score, a citation count, a stated p-value.** None of them is an independent, orthogonal, *functional* measurement of whether the biology is actually true.

This PRD adds exactly that missing axis. For a belief of the form **"gene X is essential / a driver in cancer type Y"**, it fires an applicability-gated code check against **DepMap** — the Broad Institute's genome-wide CRISPR-knockout dependency map (Chronos gene-effect scores across ~1,100 cancer cell lines) — and returns a **TESTED-tier verdict**:

- **`confirmed_selective`** — median Chronos ≤ −0.5 in lineage Y **and** the dependency is selective (lineage Y meaningfully more dependent than the pan-cancer background), i.e. a genuine lineage driver.
- **`confirmed_pan_essential`** — median ≤ −0.5 in Y but the gene is essential *everywhere* (pan-essential): the "essential" half of the claim holds, the "*driver in Y specifically*" half does **not**. This distinction is invisible to a literature score and is the check's sharpest contribution.
- **`contradicted`** — knockout is tolerated in lineage Y (median Chronos > −0.5): the essentiality claim is functionally unsupported.
- **`abstain`** — gene or lineage absent from DepMap, or the data source is unreachable. (The applicability gate — distinct from a "pass".)

**New capability nothing else in the stack has:** an *orthogonal, non-literature, wet-lab-derived* falsification signal wired into the acting loop. Persona can now take a belief it read in a paper and ask an independent functional-genomics screen "*is this gene actually required for these cancer cells to survive?*" — then write a replayable artifact (per-cell-line Chronos scores + the exact threshold + the seed/version) and, under Balanced autonomy, append a **TESTED-provisional** belief (never an anchor). This is the acting-loop closure the build plan calls for — *candidate belief → exact functional evidence → typed verdict → replayable artifact → provisional belief or human handoff* — realised for the one evidence type Persona was blind to.

---

## 1. File ownership (disjoint set)

All primary files are **Lane 3-owned** (PRD-00 §3: Lane 3 owns `persona/tools/{science.py, datasets.py}`, `persona/analysis/*`, `persona/agents/audit.py`).

| File | Own/edit | Lane | Note |
|---|---|---|---|
| `persona/analysis/depmap_oracle.py` | **create (new)** | 3 | The oracle: applicability gate + deterministic verdict, run in code. |
| `persona/tools/science.py` | edit (additive) | 3 | New `depmap_lookup()` + REGISTRY/`call()` entry. |
| `persona/tools/datasets.py` | edit (additive) | 3 | Add `depmap.org` to the fetch allowlist (`figshare`/`ndownloader.figshare.com` already present, lines 14–15). |
| `experiments/exp_rq_e20_depmap_oracle.py` | create (new) | 3 (via 4's `experiments/*` note) | Required gating experiment. |
| `results/e20_depmap_oracle.json` + FINDINGS.md append | create/append | 3 | Seeded results. |
| `tests/test_depmap_oracle.py` | create (new) | 3 | Runnable acceptance check (offline, fixtured). |

**Boundary files another lane owns (flagged):**

- **`persona/daemon/worker.py`** — not exclusively owned by any lane; its handler registry is **append-only** (docstring line 4 "*Later phases register richer handlers here*"; PRD-00 §4 ledger note cites "*worker.py's handler registry — never edit another lane's rows*"). Adding one `@handler("depmap_check")` is an append of a new row, consistent with that pattern. **Flagged for master ack; no existing handler is edited.**
- **`persona/memory/verified.py`** — the TESTED ledger writer `record(statement, method, status, …)` (line 48) accepts `method ∈ {lean, sympy, analyst}` (`_METHOD_LABEL`, line 20). The oracle records its provisional belief via `method="analyst"` (computational analysis) — **no edit to verified.py required**, so no lane boundary is crossed. A dedicated `"depmap"` method label would be nicer but is a Lane-2/unowned edit → deferred; noted in Open Questions.
- **`persona/agents/discover.py`** (Lane 1) — the acting loop that proposes/routes hypotheses. This PRD does **not** edit it; the oracle is exposed as a callable + a worker handler so Lane 1's loop *may* route to it later via FC-8. No cross-lane edit.

---

## 2. Frozen contracts provided/consumed

### Consumed (verbatim, optional)
- **FC-3** (Lane 2, `persona/memory/kg.py`) — the oracle optionally reads candidate beliefs from the KG to auto-select `(gene, lineage)` targets, but the core verdict function takes plain args and does **not** require FC-3. Degrades to explicit-target mode if the KG is absent (mirrors `audit.py` line 229 `get_kg()` optional use).

### Provided — **CONTRACT CHANGE PROPOSAL: FC-8 (Lane 3 provides)**

PRD-00's FCs stop at FC-7. This PRD introduces one new cross-lane interface so Lane 1 (acting loop) and Lane 4 (legibility/render) can consume the oracle without importing its internals. **Flagged for master + consuming-lane ratification.**

```
# FC-8 (Lane 3 provides, new persona/analysis/depmap_oracle.py):
depmap_oracle.essentiality_verdict(
    gene: str,
    lineage: str | None = None,          # DepMap lineage / OncotreeLineage string, e.g. "Lung"; None => pan-cancer only
    *,
    threshold: float = -0.5,             # Chronos dependency cutoff (cited below)
    selective_delta: float = -0.3,       # lineage-median must beat pan-median by this to be "selective"
    parent_id=None,
) -> {
    "ok": bool,
    "gene": str, "lineage": str | None,
    "status": "confirmed_selective" | "confirmed_pan_essential" | "contradicted" | "abstain" | "skipped",
    "applicable": bool,                  # False => abstain/skipped (gate did not fire on real data)
    "median_chronos_lineage": float | None,
    "median_chronos_pan": float | None,
    "n_lines_lineage": int, "n_lines_total": int,
    "selective": bool,
    "threshold": float,
    "artifact": str | None,              # rel path to the replayable JSON artifact (scores + params)
    "detail": str,                       # one-line human-readable verdict, forensics-style
    "provenance": "TESTED-provisional",  # verdict tier; anchoring stays human-gated
    "source": {"dataset": str, "release": str, "endpoint": str},
}
```

Verdict-dict shape deliberately mirrors the forensics flag contract (`{check, status, severity, detail, span}`, `forensics.py` line 14) so Lane 4 can render it in the existing robustness/trust surface with no new renderer.

---

## 3. Features

### F7.1 — `depmap_lookup`: fetch a gene's Chronos dependency slice + lineage metadata

**Problem & evidence.** `tools/science.py` has six clients but none reaches functional-genomics data (REGISTRY, line 137). DepMap's full gene-effect matrix (`CRISPRGeneEffect.csv`) is ~200 MB — **it blows the 30 MB `datasets.fetch` cap** (`datasets.py` line 21 `_MAX_BYTES = 30 * 1024 * 1024`). So a full-matrix download is *not viable*; we must fetch a **single gene's slice** (a ~1,100-value vector) plus the small cell-line/model metadata table.

**Design.**
- **File:** `persona/tools/science.py` (additive).
- **Signature:** `def depmap_lookup(gene: str, dataset: str = "Chronos_Combined") -> dict` returning `{ok, gene, scores: {DepMap_ID: chronos_float}, note}`.
- **Data flow:** hits the DepMap portal API per-gene slice through the shared cached `IngestService` (`service().get_json(...)`, `ingest/service.py` line 167) — fetch happens **outside** any sandbox, cache-first (same gene within TTL = cache hit, not a refetch), rate-limited by the existing `_default` host limiter. Endpoint per the DepMap skill: `https://depmap.org/portal/api/gene` with `{gene_id, dataset}` (skill line 79–83), falling back to `.../api/data/gene_dependency` (skill line 92). On any non-200 / empty / network error → `{ok: False, error}` (never raises), so the oracle's gate can abstain cleanly.
- **Lineage metadata** (needed for selectivity): the small **`Model.csv`** (~1–2 MB, cell-line → `OncotreeLineage`) is pulled once per release via `datasets.fetch` from figshare (already allow-listed) and cached to `paths.workspace/data/depmap/`. `depmap_lookup` merges lineage onto each `DepMap_ID`. (If the portal API already returns lineage per line, the fetch is skipped — resolved empirically in F7.4.)
- **REGISTRY/`call()`:** add `"depmap": (depmap_lookup, ["gene"])` (line 137) and a `depmap` branch in `call()` (line 147) so the analyst's tool-use loop can invoke it on demand — same wiring as the other five clients.

**Epistemic guardrails.** Read-only GET; no keys; no sandbox needed for the fetch. All fetch stays behind the allowlist/egress boundary (`datasets.py` docstring). Empty/failed lookup returns `ok:False` → downstream **abstains**, never fabricates a score.

**Required experiment.** Covered by F7.4 (the live-endpoint reachability + control classification are one experiment).

**Acceptance + runnable check.** `depmap_lookup("RPL9")["ok"] is True and len(scores) > 500` when online; offline the unit test uses a fixtured JSON slice (no network). CLI: `python -c "from persona.tools.science import depmap_lookup as d; print(d('KRAS')['ok'])"`.

**Effort:** M. **Deps:** none.

---

### F7.2 — `datasets.py` allowlist: admit `depmap.org`

**Problem & evidence.** `datasets.fetch` blocks any host not in `_ALLOW` (`datasets.py` lines 13–26, `allowed()`). `figshare.com` / `ndownloader.figshare.com` are already present (lines 14–15) — DepMap release files are figshare-hosted, so **the metadata path already works**. The portal API host `depmap.org` is **not** listed, so any direct `datasets.fetch` of a portal URL is rejected.

**Design.** One-line additive change: append `"depmap.org"` to the `_ALLOW` tuple (line 13–20). `depmap_lookup` reaches the API via `IngestService` (not `datasets.fetch`), so this addition only matters if a future release-file URL is served from `depmap.org` directly; adding it now keeps both paths open and is a reversible, trivial change.

**Epistemic guardrails.** Host stays an open-data research host; the 30 MB cap and no-egress-from-sandbox invariants are untouched.

**Required experiment.** **Trivial** (allowlist membership; the F7.4 experiment exercises the real fetch path end-to-end).

**Acceptance + runnable check.** `from persona.tools.datasets import allowed; assert allowed("https://depmap.org/portal/api/gene")`.

**Effort:** S. **Deps:** none.

---

### F7.3 — `depmap_oracle.essentiality_verdict`: applicability-gated functional verdict (FC-8)

**Problem & evidence.** Persona's only "does this replicate?" machinery today is literature-derived (`audit.py`) or arithmetic (`forensics.py`). There is no functional falsifier. The oracle is the new organ. It must run **in code, deterministically** (same discipline as `forensics.py` docstring: "*checks that run in CODE, never in a model … impossible to argue with*") and must emit an explicit **not-applicable / abstain** state distinct from a pass (PRD-00 §2: "*each check declares an applicability gate and emits a skipped/not-applicable state distinct from passed*").

**Design.**
- **File:** `persona/analysis/depmap_oracle.py` (new). Pure functions; no LLM call; numpy/statistics only (the slice is ~1,100 floats — no Docker sandbox needed, unlike heavy reanalyses).
- **Signature:** FC-8 `essentiality_verdict(...)` above, plus internal helpers `_classify(median_lineage, median_pan, n_lineage, threshold, selective_delta)` and `_load_slice(gene, lineage)`.
- **Data flow:**
  1. `depmap_lookup(gene)` (F7.1) → per-line Chronos + lineage. **Applicability gate:** if `ok is False`, gene absent (`scores` empty), or `n_lines_lineage == 0` for the requested lineage → return `status="abstain", applicable=False` (the gate did not fire on real data).
  2. Compute `median_chronos_pan` (all lines) and `median_chronos_lineage` (lines whose `OncotreeLineage == lineage`).
  3. **Classify** (thresholds cited in a code comment):
     - `median_lineage > threshold` (i.e. > −0.5) → **`contradicted`** (LoF-tolerant in this lineage).
     - `median_lineage ≤ threshold` **and** `(median_lineage − median_pan) ≤ selective_delta` (lineage clearly more dependent than background) → **`confirmed_selective`**.
     - `median_lineage ≤ threshold` **and** `median_pan ≤ threshold` (gene essential everywhere) → **`confirmed_pan_essential`** (essential, *not* a selective driver).
     - lineage `None` → report pan-cancer only: `≤ threshold → confirmed_pan_essential` else `contradicted`.
  4. **Replayable artifact:** write `deliverables/depmap/verdict-<gene>-<lineage>.json` = `{gene, lineage, threshold, selective_delta, per_line_scores, median_lineage, median_pan, n_*, dataset, release, endpoint, generated}`. Anyone can re-derive the verdict from this file → reproducibility is a feature, not a chore (`CLAUDE.md` §4).
- **Plugs into existing seams:**
  - **Auditor surface (Lane 3-owned, `audit.py`):** when a paper's central claim is essentiality-shaped, `audit()` can call `essentiality_verdict` and fold the verdict into the existing `flags`/`external` block (the verdict dict already matches the flag shape). *Optional, additive; not required for F7.3 to ship.*
  - **Acting loop (F7.5):** a worker handler runs it over candidate KG beliefs.

**Epistemic guardrails.** (1) Applicability gate → explicit `abstain`/`skipped`, never a silent zero. (2) Thresholds (`−0.5`, `−0.3` selective delta, pan-essential `−1` reference) are **cited in a code comment** against the DepMap Chronos scale (skill "Key thresholds": Chronos ≤ −0.5 likely dependent, ≤ −1 common-essential) and the gating experiment. (3) Verdict tier is **TESTED-provisional** only — it never anchors the KG; a `confirmed`/`contradicted` on a high-stakes belief routes to the human inbox (FC-2), consistent with Balanced autonomy. (4) No model touches the arithmetic.

**Required experiment.** RQ-E20 (F7.4).

**Acceptance + runnable check.** `pytest tests/test_depmap_oracle.py::test_classification_on_fixtures` — feeds fixtured slices for a pan-essential gene (median ≈ −1.5 everywhere), a selective driver (lineage ≈ −1.2, pan ≈ −0.1), a non-essential gene (median ≈ 0.0), and an absent gene; asserts `confirmed_pan_essential`, `confirmed_selective`, `contradicted`, `abstain` respectively. Fully offline.

**Effort:** M. **Deps:** F7.1.

---

### F7.4 — RQ-E20: validate verdicts on known essential vs non-essential controls

**Problem & evidence.** The load-bearing uncertainties are real: (a) *does the live DepMap portal API actually return usable per-gene slices with lineage?* (the skill hedges — "*Recommended for large queries: download*"), and (b) *do the chosen thresholds correctly classify ground-truth controls?* Both must pass a seeded gate **before** the oracle drives any autonomous TESTED-provisional write (`CLAUDE.md` §2; PRD-00 §6).

**Hypothesis + metric + gate.** *The oracle correctly classifies known-essential and known-non-essential control genes and abstains when data is absent.*
- **Controls (ground truth):** pan-essential = {`RPL9`, `RPS19`, `POLR2A`, `EIF3B`} (Hart/DepMap common-essential reference sets) → expect `confirmed_pan_essential`; non-essential/LoF-tolerant = {`OR2T35` (olfactory receptor), a set of Hart non-essential genes} → expect `contradicted`; selective driver = {`KRAS`@Pancreas/Lung, `BRAF`@Skin/melanoma} → expect `confirmed_selective`; absent = a fabricated symbol / non-DepMap gene → expect `abstain`.
- **Metric:** classification accuracy on essential-vs-nonessential controls; abstention correctness on the absent set.
- **Gate:** **≥ 90% correct** on the essential/non-essential control panel **and** **100% abstain** on the absent set (never a false verdict on missing data). If the live API fails reachability, the experiment records the failure and the gate falls back to the cached-figshare-metadata path; if *that* also fails the feature ships **abstain-only** (honest) and the API path is deferred — reversal logged in FINDINGS.
- **Seeds:** the classification is deterministic given a data release, so "seeds" = **≥ 20 bootstrap resamples** of the cell-line set per gene to report median-Chronos stability (mean ± 95% CI on the median), pinning the DepMap release id for reproducibility. Live-API variability is controlled by pinning the release + caching.

**File:** `experiments/exp_rq_e20_depmap_oracle.py` → `results/e20_depmap_oracle.json` + FINDINGS.md `#RQ-E20` append.

**Acceptance + runnable check.** `python experiments/exp_rq_e20_depmap_oracle.py` prints `PASS` and writes the JSON when the gate is met (skips live section gracefully with `SKIPPED-offline` when no network, still running the fixtured classification).

**Effort:** M. **Deps:** F7.1, F7.3.

---

### F7.5 — Acting-loop wiring: `depmap_check` worker handler → TESTED-provisional belief

**Problem & evidence.** The verdict is only an *acting-loop* signal if it fires automatically on candidate beliefs and writes back. The worker registry is the append-only dispatch seam (`worker.py` line 15 `@handler`, e.g. `@handler("reaudit")` line 163 → `audit.reaudit`, which records movement to the watchlist ledger). We mirror that pattern exactly.

**Design.**
- **File:** `persona/daemon/worker.py` — **append** one handler (flagged boundary, §1):
  ```
  @handler("depmap_check")
  async def _depmap_check(task, queue) -> str:
      from ..analysis import depmap_oracle
      r = await asyncio.to_thread(depmap_oracle.run_on_candidate, parent_id=task.parent_id)
      ...
  ```
- **File:** `persona/analysis/depmap_oracle.py` — add `run_on_candidate(parent_id=None) -> dict`: selects the highest-value essentiality-shaped belief from the KG (crosscheck/`beliefs`, `kg.py` line 308), runs `essentiality_verdict`, emits a legible event (`log().emit("belief_update", …)` as `audit.reaudit` does, worker line 337-ish pattern), and — under **Balanced autonomy** — records a **TESTED-provisional** entry via `verified.record(statement, method="analyst", status=..., evidence="DepMap Chronos verdict …", papers=[…])`. A `contradicted` verdict on a belief already anchored/high-stakes does **not** overwrite it; it files an FC-2 handoff instead (human anchors high-stakes — `CLAUDE.md` §7).
- **Selecting essentiality-shaped beliefs:** cheap heuristic on the belief's relation/object (`relation ∈ {essential_in, driver_of, required_for}` or effect-sign + oncology object). Kept simple; the LLM is not in the verdict path.

**Epistemic guardrails.** Auto-write is **narrow** (single-gene single-lineage functional check → TESTED-provisional) exactly as the autonomy contract permits ("*auto-run narrow reanalyses into TESTED-provisional; anchors + high-stakes stay human-gated*"). Abstain never writes a belief. Every write carries the replayable artifact path as provenance.

**Required experiment.** Reuses RQ-E20's gate as the go/no-go: the handler is registered but **advisory-only until RQ-E20 passes** (same pattern as FC-4 "*Auto-dispatch gated on RQ-E17; advisory until it passes*"). No separate experiment.

**Acceptance + runnable check.** `pytest tests/test_depmap_oracle.py::test_run_on_candidate_records_provisional` — with a fixtured KG belief + fixtured slice, asserts a `verified` entry with `method="analyst"` and a `status ∈ {verified, refuted}` mapped from the verdict, and that an `abstain` verdict records **no** entry.

**Effort:** S. **Deps:** F7.3, F7.4 (gate).

---

## 4. Sequencing (interface-first)

1. **F7.2** (allowlist one-liner) + **FC-8 stub** in `depmap_oracle.py` returning a typed `abstain` fixture — commit-in-place so Lane 1/Lane 4 can build against FC-8 from hour 1.
2. **F7.1** `depmap_lookup` (fetch + cache + lineage merge) — the data source.
3. **F7.3** `essentiality_verdict` classification + artifact (against fixtures first).
4. **F7.4** RQ-E20 experiment → gate. **Nothing auto-writes before this passes.**
5. **F7.5** worker handler + `run_on_candidate` (advisory until F7.4 green, then Balanced auto-write).

---

## 5. Test & verification plan

- **Offline unit oracle (primary):** `tests/test_depmap_oracle.py` drives the classifier on fixtured slices covering all four verdict classes + abstain — deterministic, no network, catches any threshold/selectivity regression. This *is* the regression oracle for the check (analogue of reusing `exp_when_protection_matters.py` as a test oracle, PRD-00 §2 / `CLAUDE.md` §4).
- **Live smoke (gated, skippable):** the F7.4 experiment's live section validates the real API on the control panel; auto-`SKIPPED-offline` when no network so CI stays green.
- **Reuse existing oracles:** the verdict dict conforms to the `forensics.py` flag shape, so Lane 4's existing robustness/trust renderer verifies it with no new test surface. The worker-handler smoke reuses the `PERSONA_WORKERS=0` daemon pattern.
- **Reproducibility:** the JSON artifact + pinned DepMap release id let any verdict be re-derived offline — the acceptance check for "replayable artifact."

---

## 6. Open questions for the master/user

1. **CONTRACT CHANGE PROPOSAL — ratify FC-8?** New Lane-3 interface `depmap_oracle.essentiality_verdict(...)` (signature in §2). Needs master + Lane 1 (acting loop) + Lane 4 (render) ack before F7.5 wiring lands.
2. **RQ id collision.** `RQ-E20` chosen as the next free id after PRD-00's E16–E19, but `E28` already appears in `RESEARCH_QUALITY_PROGRAM.md`. Confirm `RQ-E20` (or assign an id) so the register stays clean.
3. **`worker.py` append.** Adding `@handler("depmap_check")` is an append to an unowned, append-only registry (§1). Confirm this is the sanctioned way to add a Lane-3-driven handler, vs. routing through Lane 1's `discover.py` acting loop instead.
4. **DepMap portal API stability.** The `/portal/api/gene` endpoint is used by the web app but is not formally documented as a stable public API. F7.4 gates on it empirically and abstains on failure; acceptable to ship **abstain-until-reachable** if the live gate fails, with the figshare-download path (subset only, ≤30 MB cap) as the fallback? Confirm the fallback posture.
5. **TESTED method label.** The oracle records provisional beliefs as `method="analyst"` to avoid editing Lane-2/unowned `verified.py`. Prefer a dedicated `"depmap"` label (a 1-line `_METHOD_LABEL` edit)? If yes, who owns that edit.

---

_Grounded against: `persona/tools/science.py` (REGISTRY L137, `call` L147), `persona/tools/datasets.py` (`_ALLOW` L13–20, `_MAX_BYTES` L21, `allowed` L24, `fetch` L29), `persona/analysis/forensics.py` (`run_all` L155, flag shape L14), `persona/agents/audit.py` (`forensics.run_all` L216, `get_kg` L229, applicability via `status="skipped"`), `persona/daemon/worker.py` (`@handler` L15, `reaudit` L163), `persona/memory/verified.py` (`record` L48, `_METHOD_LABEL` L20), `persona/memory/kg.py` (`crosscheck` L308), `persona/ingest/service.py` (`get_json` L167), `persona/tools/sandbox.py` (`run_python` L27); DepMap skill (`~/.claude/skills/depmap/SKILL.md`: API L67–92, Chronos thresholds, `Model.csv`/`sample_info.csv` metadata)._
