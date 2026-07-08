"""Inferential-dependency tagger (v3 T0.5) — builds the flagship graph the audit found missing.

BUILD_PLAN 3.2: the differentiator vs a literature-search tool is an *inferential*-dependency
graph — which beliefs structurally depend on which — so we can compute what's LOAD-BEARING and
where the highest-value experiment is. Extraction emitted none of these edges, so
`load_bearing` returned {} on real data and VoI was 0 for everything (finding #5).

This pass proposes CANDIDATE edges between committed claims:
  - `derives-from` / `presupposes`: claim A's validity depends on claim B (B is more foundational)
  - `generalizes`: A is a general form of the more specific B
Edges are INFERRED candidates (never auto-anchored). Two backends behind one `tag()` interface:
a real Claude classifier (constrained tool-use) and a deterministic heuristic (offline / no key).
The heuristic's foundational-ness score is validated in experiments/exp_e6_dependency.py (E6).
"""
from __future__ import annotations

from itertools import combinations
from typing import Optional, Protocol

from .. import config
from ..store import _PROV_RANK
from ..engine.cross_field import mechanism_tokens

_RELN_WORDS = {"increase", "increases", "increased", "decrease", "decreases", "cause", "causes",
               "caused", "associated", "association", "drive", "drives", "driven", "inhibit",
               "inhibits", "requires", "require", "reduces", "reduced", "promotes", "promote",
               "effect", "with", "and", "the", "via", "through", "levels", "no"}

# heuristic foundational-ness weights — a claim is more FOUNDATIONAL when it is better
# established (provenance, independent replication) and more GENERAL (fewer distinct entities).
# Validated in experiments/exp_e6_dependency.py.
_W_PROV, _W_SUPPORT, _W_GENERALITY = 1.5, 0.4, 0.6
_MARGIN = 0.5          # foundational-score gap required before we assert a dependency
_MAX_PAIRS = 80        # cost/again cap on how many co-mention pairs we classify per pass


def _entities(store, claim) -> set:
    if claim.entities:
        return {str(e).lower() for e in claim.entities}
    return mechanism_tokens(claim.statement) - _RELN_WORDS


def _foundational(store, claim, n_entities: int) -> float:
    prov = _PROV_RANK.get(claim.provenance_state, 0)
    support = store.independent_source_count(claim.claim_id)
    return _W_PROV * prov + _W_SUPPORT * support - _W_GENERALITY * n_entities


def candidate_pairs(store, max_pairs: int = _MAX_PAIRS) -> list:
    """Ordered claim pairs that share >=1 entity (co-mention) — the only pairs worth classifying."""
    claims = store.core_claims()
    ents = {c.claim_id: _entities(store, c) for c in claims}
    pairs = []
    for a, b in combinations(claims, 2):
        if ents[a.claim_id] & ents[b.claim_id]:
            pairs.append((a, b))
    # prefer pairs touching better-established claims first (more informative structure)
    pairs.sort(key=lambda ab: max(_PROV_RANK.get(ab[0].provenance_state, 0),
                                  _PROV_RANK.get(ab[1].provenance_state, 0)), reverse=True)
    return pairs[:max_pairs]


class DependencyTagger(Protocol):
    def tag(self, store, a, b) -> Optional[dict]:
        """Return {'src','dst','relation','confidence'} or None for a pair (a, b)."""
        ...


class HeuristicDependencyTagger:
    """Deterministic, offline. Asserts A derives-from B when B is clearly more foundational
    (better established + more general) and they co-mention an entity. Order-independent."""

    def tag(self, store, a, b) -> Optional[dict]:
        ea, eb = _entities(store, a), _entities(store, b)
        if not (ea & eb):
            return None
        fa, fb = _foundational(store, a, len(ea)), _foundational(store, b, len(eb))
        if abs(fa - fb) < _MARGIN:
            return None
        src, dst, gap = (a, b, fb - fa) if fb > fa else (b, a, fa - fb)
        conf = min(0.6, 0.3 + 0.05 * gap)     # candidate-grade; never high-confidence
        return {"src": src.claim_id, "dst": dst.claim_id, "relation": "derives-from",
                "confidence": round(conf, 3)}


_TAG_TOOL = {
    "name": "classify_dependency",
    "description": "Classify the inferential dependency between two biomedical claims A and B.",
    "input_schema": {
        "type": "object",
        "properties": {
            "relation": {"type": "string",
                         "enum": ["A_derives_from_B", "B_derives_from_A", "A_presupposes_B",
                                  "B_presupposes_A", "A_generalizes_B", "B_generalizes_A", "none"]},
            "confidence": {"type": "number", "description": "0-1, how sure the dependency holds"},
            "reason": {"type": "string"},
        },
        "required": ["relation", "confidence"],
    },
}

_TAG_SYSTEM = ("You judge INFERENTIAL dependencies between scientific claims. 'A derives-from B' "
               "means A's truth logically or evidentially depends on B (B is the more foundational "
               "premise). 'A presupposes B' means A only makes sense if B holds. 'A generalizes B' "
               "means A is the broader statement B is a special case of. Answer 'none' unless there "
               "is a real structural dependency — most co-mentioning claim pairs are 'none'. Be "
               "conservative; these are candidate edges a human will audit.")

_REL_MAP = {"A_derives_from_B": ("a", "b", "derives-from"),
            "B_derives_from_A": ("b", "a", "derives-from"),
            "A_presupposes_B": ("a", "b", "presupposes"),
            "B_presupposes_A": ("b", "a", "presupposes"),
            "A_generalizes_B": ("b", "a", "generalizes"),   # B derives-from/under A's generalization
            "B_generalizes_A": ("a", "b", "generalizes")}


class ClaudeDependencyTagger:
    """Real classifier via the reasoning model. Falls back to the heuristic without a key."""

    def __init__(self, model: Optional[str] = None, client=None):
        self.model = model or config.MODEL_REASONER
        self._client = client
        self._fallback = HeuristicDependencyTagger()
        self.last_usage = {"in": 0, "out": 0, "cost": 0.0}

    def tag(self, store, a, b) -> Optional[dict]:
        client = self._client or (config.anthropic_client() if config.have_key() else None)
        if client is None:
            return self._fallback.tag(store, a, b)
        resp = client.messages.create(
            model=self.model, max_tokens=400, system=_TAG_SYSTEM, tools=[_TAG_TOOL],
            tool_choice={"type": "tool", "name": "classify_dependency"},
            messages=[{"role": "user", "content":
                       f"Claim A: {a.statement}\nClaim B: {b.statement}\n\nClassify the dependency."}])
        u = resp.usage
        self.last_usage = {"in": u.input_tokens, "out": u.output_tokens,
                           "cost": config.est_cost_usd(self.model, u.input_tokens, u.output_tokens)}
        out = {"relation": "none", "confidence": 0.0}
        for blk in resp.content:
            if blk.type == "tool_use":
                out.update(blk.input)
        rel = out.get("relation", "none")
        if rel == "none" or rel not in _REL_MAP:
            return None
        who_src, who_dst, relation = _REL_MAP[rel]
        src = a if who_src == "a" else b
        dst = a if who_dst == "a" else b
        return {"src": src.claim_id, "dst": dst.claim_id, "relation": relation,
                "confidence": float(out.get("confidence", 0.4))}


def tag_dependencies(store, tagger: Optional[DependencyTagger] = None,
                     max_pairs: int = _MAX_PAIRS) -> int:
    """Run the tagger over co-mentioning claim pairs; write NEW candidate edges. Returns the
    number of edges added. Idempotent: an edge already present (same src,dst,relation) is skipped."""
    tagger = tagger or (ClaudeDependencyTagger() if config.have_key() else HeuristicDependencyTagger())
    added = 0
    for a, b in candidate_pairs(store, max_pairs):
        res = tagger.tag(store, a, b)
        if not res:
            continue
        existing = {(e["dst"], e["relation"]) for e in store.edges_from(res["src"])}
        if (res["dst"], res["relation"]) in existing:
            continue
        try:
            store.add_edge(res["src"], res["dst"], res["relation"], res["confidence"])
            added += 1
        except (KeyError, ValueError):
            continue
    return added
