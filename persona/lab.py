"""A lab, not a loner (BUILD_PLAN 7.1): spawn several researchers with different
dispositions; let their DISAGREEMENT be a signal. Different taste/strictness -> different
bodies of belief; where two synthetic researchers disagree (or one believes what the
other hasn't committed) is exactly where a human PI should look.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .researcher import Researcher


@dataclass
class Disagreement:
    claim_key: str
    statement: str
    kind: str                 # 'sign' (opposite conclusions) | 'coverage' (one committed, one hasn't)
    a_name: str
    a_p: float | None
    b_name: str
    b_p: float | None


class Lab:
    def __init__(self, researchers: list[Researcher]):
        assert len(researchers) >= 2, "a lab needs at least two researchers"
        self.researchers = researchers

    def run(self, queries: list[str] | None = None) -> None:
        for r in self.researchers:
            r.tick(queries)

    def _beliefs(self, r: Researcher) -> dict:
        return {c.claim_id: c for c in r.me.store.core_claims()}

    def disagreements(self) -> list[Disagreement]:
        a, b = self.researchers[0], self.researchers[1]
        ba, bb = self._beliefs(a), self._beliefs(b)
        keys = set(ba) | set(bb)
        out: list[Disagreement] = []
        for k in keys:
            ca, cb = ba.get(k), bb.get(k)
            if ca and cb:
                if ca.predicted != cb.predicted:      # opposite conclusions
                    out.append(Disagreement(k, ca.statement, "sign", a.name,
                                            round(ca.calibrated_p, 3), b.name, round(cb.calibrated_p, 3)))
            else:                                      # one committed it, the other hasn't
                held_by = ca or cb
                out.append(Disagreement(k, held_by.statement, "coverage",
                                        a.name, round(ca.calibrated_p, 3) if ca else None,
                                        b.name, round(cb.calibrated_p, 3) if cb else None))
        # sign disagreements first (the sharper signal)
        out.sort(key=lambda d: 0 if d.kind == "sign" else 1)
        return out

    def close(self) -> None:
        for r in self.researchers:
            r.close()


def build_default_lab(root: str | Path = "runs/lab", adapter=None) -> Lab:
    """Two personas with different dispositions on the same seed program."""
    root = Path(root)
    ada = Researcher(root / "ada", name="Ada", disposition="skeptical",
                     seed_interests=["neuroinflammation", "microglia", "tau"], adapter=adapter)
    bo = Researcher(root / "bo", name="Bo", disposition="exploratory",
                    seed_interests=["neuroinflammation", "microglia", "tau"], adapter=adapter)
    return Lab([ada, bo])
