"""Human-delegation loop (BUILD_PLAN 2.4 / 3.7): the human is the adjudication step
INSIDE the loop, not a reader of outputs. The AI does the superhuman part — surface the
tension, pre-assemble the dossier, generate candidate explanations — the human makes the
call, and their answer becomes a durable, anchored belief node others inherit.

Ignition is human-gated (§2.7): a typed contradiction becomes a dossier in the inbox; the
human's resolution anchors the belief (provenance HUMAN_CONFIRMED). The AI never fabricates
a resolution — it escalates and records provenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..membrane import ContradictionEvent

# candidate explanations, biased by contradiction type (BioDivergence: most apparent
# contradictions are context-conditioned divergence, planning/LITERATURE.md §D)
_EXPLANATIONS = {
    "context-divergence": [
        "context effect-modifier (cohort / dose / assay / subtype / geography) — both locally valid",
        "population difference between the two studies",
        "methodological / measurement difference",
    ],
    "true-refutation": [
        "one side is underpowered or methodologically weaker",
        "a genuine reversal — the earlier claim does not replicate",
        "publication/citation amplification inflated the weaker side",
    ],
    "no-evidence": [
        "insufficient independent evidence on either side yet",
        "the apparent conflict is terminological, not empirical",
    ],
}


@dataclass
class Dossier:
    claim_key: str
    kind: str                         # contradiction type
    question: str
    support: list = field(default_factory=list)   # source refs favoring the claim
    refute: list = field(default_factory=list)
    candidate_explanations: list = field(default_factory=list)
    status: str = "open"              # open | resolved
    resolution: str | None = None


def assemble_dossier(store, event: ContradictionEvent) -> Dossier:
    """Pre-assemble everything a human needs to make the call in one glance."""
    srcs = store.sources(event.claim_key)
    support = [s["ref"] for s in srcs]              # (directional attribution refined later)
    return Dossier(
        claim_key=event.claim_key,
        kind=event.kind,
        question=(f"On \"{event.statement[:120]}\": which explanation holds for the "
                  f"{event.support_groups}-vs-{event.refute_groups}-group disagreement, "
                  f"or is it a fourth?"),
        support=support,
        refute=[],
        candidate_explanations=list(_EXPLANATIONS.get(event.kind, _EXPLANATIONS["no-evidence"])),
    )


class HandoffInbox:
    """The human-handoff inbox. Resolving a dossier ANCHORS the belief (durable, shared)."""

    def __init__(self, store):
        self.store = store
        self._items: dict[str, Dossier] = {}

    def add(self, dossier: Dossier) -> None:
        self._items[dossier.claim_key] = dossier

    def add_event(self, event: ContradictionEvent) -> Dossier:
        d = assemble_dossier(self.store, event)
        self.add(d)
        return d

    def open_items(self) -> list[Dossier]:
        return [d for d in self._items.values() if d.status == "open"]

    def resolve(self, claim_key: str, chosen_explanation: str, truth: int, *, tested: bool = False):
        """The human's call. Anchors the belief -> it now resists swarm overwrite forever
        (until a human/test escapes it — E9). Returns the anchored Claim."""
        d = self._items.get(claim_key)
        if d is None:
            raise KeyError(claim_key)
        if self.store.get_claim(claim_key) is None:
            from ..store import Claim
            self.store.add_claim(Claim(claim_key, d.question, tier="core"))
        anchored = self.store.human_confirm(claim_key, truth, tested=tested)
        d.status = "resolved"
        d.resolution = chosen_explanation
        return anchored
