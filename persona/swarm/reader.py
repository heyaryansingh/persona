"""Reader/extractor swarm agents: Document -> candidate claims.

A Candidate is what the swarm hands the membrane. It is NOT a belief until the membrane
admits it. `group` is the evidential-independence key. `direction` is the EFFECT SIGN of the
relation (+1 = up/positive, -1 = down/negative-or-null), NOT an assert/refute flag — so two
papers claiming OPPOSITE directions about the same (subject, object) pair land on the same
claim node with opposite signs and the membrane fires a contradiction (v3 T0.1). All backends
build candidates through the single `build_candidate` function so their semantics can't diverge.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional, Protocol

from ..ingest.base import Document

# heuristic cue stems (offline extractor only)
_UP = ("increas", "elevat", "rais", "promot", "driv", "upregulat", "associat",
       "link", "exacerbat", "higher", "aggravat", "worsen", "activat")
_DOWN = ("decreas", "reduc", "lower", "protect", "attenuat", "downregulat",
         "inhibit", "suppress", "amelior", "rescu")
_NEG = ("no association", "not associat", "no effect", "fail", "no significant",
        "did not", "no difference")

# relation -> EFFECT SIGN. +1 = the entity RAISES/positively-relates the target;
# -1 = LOWERS/negatively-relates, or a null result. The membrane treats opposite signs on the
# same (subject, object) node as a CONTRADICTION (up-vs-down no longer merges as agreement).
RELATION_SIGN = {
    "increases": +1.0, "causes": +1.0, "promotes": +1.0, "drives": +1.0, "activates": +1.0,
    "associated_with": +1.0, "requires": +1.0, "upregulates": +1.0, "exacerbates": +1.0,
    "decreases": -1.0, "inhibits": -1.0, "reduces": -1.0, "suppresses": -1.0,
    "protects": -1.0, "downregulates": -1.0, "attenuates": -1.0, "rescues": -1.0,
    "no_effect": -1.0,
}


def _norm_rel(relation: str) -> str:
    return re.sub(r"\s+", "_", (relation or "associated_with").strip().lower())


def effect_sign(relation: str) -> float:
    return RELATION_SIGN.get(_norm_rel(relation), +1.0)


def claim_key(subject: str, obj: str) -> str:
    """Direction-agnostic identity of a claim: the (subject, object) pair. Opposite effect
    signs share this key so they collide into one node and contradict."""
    s = re.sub(r"\s+", " ", subject.strip().lower())
    o = re.sub(r"\s+", " ", obj.strip().lower())
    return "clm_" + hashlib.sha1(f"{s}|{o}".encode()).hexdigest()[:12]


@dataclass
class Candidate:
    claim_key: str
    statement: str
    direction: float           # EFFECT SIGN: +1 up/positive, -1 down/negative-or-null
    group: str                 # independence group (journal/lab/dataset)
    doc_id: str
    provenance: str = "READ"
    confidence: float = 0.5
    is_contradiction: bool = False
    meta: dict = field(default_factory=dict)


def build_candidate(subject: str, obj: str, relation: str, group: str, doc_id: str,
                    confidence: float = 0.6, canon=None, provenance: str = "READ",
                    population: Optional[str] = None) -> Optional[Candidate]:
    """The ONE place a (subject, relation, object) tuple becomes a Candidate — shared by every
    extractor so effect-sign + canonicalization semantics are identical everywhere."""
    subj = str(subject or "").strip()
    ob = str(obj or "").strip()
    if not subj or not ob:
        return None
    if canon is not None:
        subj, ob = canon.canon(subj), canon.canon(ob)
    reln = _norm_rel(relation)
    return Candidate(
        claim_key=claim_key(subj, ob),
        statement=f"{subj} {reln.replace('_', ' ')} {ob}",
        direction=RELATION_SIGN.get(reln, +1.0),
        group=group, doc_id=doc_id, provenance=provenance,
        confidence=float(confidence),
        meta={"subject": subj, "object": ob, "relation": reln, "population": population},
    )


class Extractor(Protocol):
    def extract(self, doc: Document) -> list[Candidate]:
        ...


class HeuristicExtractor:
    """Deterministic, offline extractor. Crude on purpose (extraction QUALITY is the real
    ClaudeExtractor's job). Scans sentences for an entity pair + a directional cue, then maps
    the cue to a relation and routes through build_candidate — so its effect-sign semantics
    match the Claude path exactly (fixes the v2 heuristic-vs-Claude direction split)."""

    def __init__(self, entities: Optional[list[str]] = None):
        self.entities = [e.lower() for e in (entities or [
            "microglia", "neuroinflammation", "amyloid", "tau", "apoe", "tnf",
            "il-1", "il-6", "nlrp3", "complement", "astrocyte", "cognition",
            "neurodegeneration", "synapse", "alzheimer",
        ])]

    def extract(self, doc: Document) -> list[Candidate]:
        from ..ingest.independence import independence_group
        text = f"{doc.title}. {doc.text}"
        group = independence_group(doc)
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
            relation = "no_effect" if neg else ("decreases" if (down and not up) else "increases")
            c = build_candidate(present[0], present[1], relation, group, doc.doc_id, confidence=0.55)
            if c:
                c.statement = sent.strip()[:300]      # keep the real sentence for legibility
                c.meta["year"] = doc.year
                out.append(c)
        return out
