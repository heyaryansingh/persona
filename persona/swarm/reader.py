"""Reader/extractor swarm agents: Document -> candidate claims.

A Candidate is what the swarm hands the membrane. It is NOT a belief until the membrane
admits it. `group` is the evidential-independence key (journal/lab/dataset), so the
membrane counts independent corroboration rather than raw agreement (planning/LITERATURE.md §D).

Backends are pluggable: HeuristicExtractor is deterministic and offline (for tests + the
no-key demo); a ClaudeExtractor (real LLM) plugs in behind the same Protocol when a key is
available — that is what E8/E12 exercise (experiments/exp_e8_real_claude_poisoning.py).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional, Protocol

from ..ingest.base import Document

# directional cue STEMS -> sign of the asserted relation (stems catch verb inflections:
# promot/promote/promotes/promoting, increas/increase/increasing, ...).
_UP = ("increas", "elevat", "rais", "promot", "driv", "upregulat", "associat",
       "link", "exacerbat", "higher", "aggravat", "worsen")
_DOWN = ("decreas", "reduc", "lower", "protect", "attenuat", "downregulat",
         "inhibit", "suppress", "amelior", "rescu")
_NEG = ("no association", "not associat", "no effect", "fail", "no significant",
        "did not", "no difference")


def claim_key(subject: str, obj: str) -> str:
    """Stable key so candidates about the same relation land on the same belief node."""
    s = re.sub(r"\s+", " ", subject.strip().lower())
    o = re.sub(r"\s+", " ", obj.strip().lower())
    return "clm_" + hashlib.sha1(f"{s}|{o}".encode()).hexdigest()[:12]


@dataclass
class Candidate:
    claim_key: str
    statement: str
    direction: float           # +1 asserts the claim true, -1 refutes it
    group: str                 # independence group (journal/lab/dataset)
    doc_id: str
    provenance: str = "READ"
    confidence: float = 0.5
    is_contradiction: bool = False
    meta: dict = field(default_factory=dict)


class Extractor(Protocol):
    def extract(self, doc: Document) -> list[Candidate]:
        ...


class HeuristicExtractor:
    """Deterministic, offline extractor. Crude on purpose — extraction QUALITY is the job
    of the real ClaudeExtractor (tested by E6/E8); this exists to exercise the pipeline
    and run the no-key demo. It scans sentences for an entity pair + a directional cue.
    """

    def __init__(self, entities: Optional[list[str]] = None):
        # seed entities to look for (Alzheimer's neuroinflammation program by default)
        self.entities = [e.lower() for e in (entities or [
            "microglia", "neuroinflammation", "amyloid", "tau", "apoe", "tnf",
            "il-1", "il-6", "nlrp3", "complement", "astrocyte", "cognition",
            "neurodegeneration", "synapse", "alzheimer",
        ])]

    def extract(self, doc: Document) -> list[Candidate]:
        text = f"{doc.title}. {doc.text}"
        group = doc.group or doc.source
        out: list[Candidate] = []
        for sent in re.split(r"(?<=[.!?])\s+", text):
            low = sent.lower()
            present = [e for e in self.entities if e in low]
            if len(present) < 2:
                continue
            neg = any(n in low for n in _NEG)
            up = any(u in low for u in _UP)
            down = any(dn in low for dn in _DOWN)
            if not (up or down or neg):
                continue
            direction = -1.0 if (neg or (down and not up)) else 1.0
            subj, obj = present[0], present[1]
            out.append(Candidate(
                claim_key=claim_key(subj, obj),
                statement=sent.strip()[:300],
                direction=direction,
                group=group,
                doc_id=doc.doc_id,
                provenance="READ",
                confidence=0.55,
                meta={"subject": subj, "object": obj, "year": doc.year},
            ))
        return out
