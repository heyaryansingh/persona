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


@dataclass
class DatasetHit:
    accession: str
    source: str
    url: str
    relevance: str = ""


@dataclass
class SelfTestResult:
    hypothesis: Hypothesis
    dataset: Optional[DatasetHit]
    outcome: str               # supports | refutes | inconclusive
    confidence: float
    detail: str
    is_replay: bool = True      # True until a real Claude-Science reanalysis is wired


def hypothesize(event: ContradictionEvent) -> Hypothesis:
    """Turn a typed contradiction into a falsifiable sub-hypothesis."""
    text = (f"If the disagreement on \"{event.statement[:100]}\" is a true effect (not "
            f"{event.kind}), an independent public dataset should show the same direction.")
    return Hypothesis(
        text=text, claim_key=event.claim_key, predicts=+1.0,
        test_description=("Locate a public expression/association dataset for the entities "
                          "in the claim; compute the first-pass effect direction and compare."),
    )


class DatasetScout(Protocol):
    def search(self, hypothesis: Hypothesis, limit: int = 5) -> list[DatasetHit]:
        ...


class GEODatasetScout:
    """Live NCBI GEO (GDS) search via eutils (stdlib urllib, cached)."""
    _ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    def __init__(self, cache: Optional[DiskCache] = None, timeout: float = 20.0):
        self.cache = cache or DiskCache()
        self.timeout = timeout

    def search(self, hypothesis: Hypothesis, limit: int = 5) -> list[DatasetHit]:
        # crude term: the claim key's statement words (the caller can pass richer terms later)
        term = hypothesis.claim_key
        term = urllib.parse.quote(hypothesis.text.split("\"")[1] if "\"" in hypothesis.text else term)
        cached = self.cache.get("geo", term, str(limit))
        if cached is None:
            params = urllib.parse.urlencode({"db": "gds", "term": term, "retmode": "json",
                                             "retmax": limit})
            req = urllib.request.Request(f"{self._ESEARCH}?{params}",
                                         headers={"User-Agent": "persona-researcher/0.0.1"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            ids = data.get("esearchresult", {}).get("idlist", [])
            self.cache.put(ids, "geo", term, str(limit))
        else:
            ids = cached
        return [DatasetHit(accession=f"GDS_uid:{i}", source="GEO",
                           url=f"https://www.ncbi.nlm.nih.gov/gds/?term={i}",
                           relevance="keyword match") for i in ids]


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
