"""Coherence / anti-degradation (v5 P6).

Long-horizon agents degrade by self-conditioning on their own accumulated errors and by letting
the "self" balloon into incoherence. Persona's defenses:
1. RE-GROUND EVERY CYCLE: the deliberate/synthesize loops build prompts from the KG + quotes each
   time, never from their own prior free-text (this is inherent in the fresh-context design).
2. BOUNDED MEMORY-BLOCKS: the self files are capped (Letta-style) so identity/strategies/taste
   can't grow unbounded — `enforce_caps()` keeps the newest content within a char budget.
3. ANCHOR POLICY: verified beliefs are immovable by cheap evidence (enforced in the KG).
This module owns (2) and a cheap drift signal over the interest set.
"""
from __future__ import annotations

from . import config
from .context import get_persona

# per-file soft caps (chars) — keep the self small and legible (memory-blocks, not documents)
_CAPS = {"identity.md": 4000, "strategies.md": 6000, "taste.md": 6000, "CHANGELOG.md": 20000}


def enforce_caps() -> dict:
    """Trim accreting self files to their caps, keeping the header + the most recent entries."""
    sd = get_persona().paths.self_dir
    trimmed = {}
    for fname, cap in _CAPS.items():
        p = sd / fname
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if len(text) <= cap:
            continue
        lines = text.splitlines()
        header = [l for l in lines[:3] if l.startswith("#")]
        # keep newest bullet lines from the end until under cap
        kept, size = [], sum(len(h) + 1 for h in header)
        for l in reversed(lines):
            if l.startswith("#"):
                continue
            if size + len(l) + 1 > cap:
                break
            kept.append(l); size += len(l) + 1
        new = "\n".join(header + ["", "_(older entries pruned to keep the self bounded)_"] + list(reversed(kept)))
        p.write_text(new + "\n", encoding="utf-8")
        trimmed[fname] = len(text) - len(new)
    return trimmed


def interest_signature() -> set:
    """A cheap fingerprint of current interests (token set) for drift detection."""
    from . import selfmind
    toks = set()
    for n, _ in selfmind.interests():
        toks |= {w for w in n.lower().split() if len(w) > 3}
    return toks


def drift(prev: set, cur: set) -> float:
    """Jaccard DISTANCE between two interest signatures (0 = identical, 1 = totally different).
    A sudden jump flags a possible spiral; gradual change is healthy evolution."""
    if not prev and not cur:
        return 0.0
    inter = len(prev & cur)
    union = len(prev | cur) or 1
    return 1.0 - inter / union
