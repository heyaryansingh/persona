"""Inner loop (BUILD_PLAN 2.1): swarm reads new literature -> extract claims -> membrane
-> update belief-graph, narrating every move to the living notebook. Always-on substrate.

The swarm reads; the membrane commits; the self records. This is one tick over a set of
queries; the outer loop (later) decides *which* queries to run.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..membrane import Membrane
from ..self_state import Self
from ..swarm.reader import Extractor
from ..ingest.base import SourceAdapter


@dataclass
class LoopSummary:
    docs_read: int = 0
    candidates: int = 0
    committed: int = 0
    held: int = 0
    contradictions: int = 0
    strict: int = 0
    contradiction_events: list = field(default_factory=list)


def run_inner_loop(me: Self, adapter: SourceAdapter, extractor: Extractor,
                   membrane: Membrane, queries: list[str], limit: int = 8) -> LoopSummary:
    s = LoopSummary()
    for q in queries:
        docs = adapter.search(q, limit=limit)
        n_cand = 0
        for doc in docs:
            for cand in extractor.extract(doc):
                membrane.submit(cand)
                n_cand += 1
        rep = membrane.harvest()
        s.docs_read += len(docs)
        s.candidates += n_cand
        s.committed += len(rep.committed)
        s.held += len(rep.held)
        s.contradictions += len(rep.contradictions)
        s.strict += len(rep.strict_claims)
        s.contradiction_events.extend(rep.contradictions)
        me.notebook(
            f"read {len(docs)} on \"{q}\" → {n_cand} candidates → "
            f"committed {len(rep.committed)} / held {len(rep.held)}; "
            f"{len(rep.contradictions)} contradiction(s) flagged"
            + (f"; {len(rep.strict_claims)} claim(s) went strict (poisoning signature)"
               if rep.strict_claims else "")
        )
        for ev in rep.contradictions:
            me.notebook(f"  ⚠ [{ev.kind}] {ev.statement[:90]} "
                        f"(support {ev.support_groups} vs refute {ev.refute_groups} groups) "
                        f"→ needs-human")
    me.consolidate()   # refresh the readable core snapshot (sleep-time analogue)
    return s
