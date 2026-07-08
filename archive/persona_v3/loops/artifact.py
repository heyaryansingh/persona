"""Artifact loop (BUILD_PLAN 2.6 / 6.7): the researcher's body of work — auto-written
mini-reviews (with an explicit 'unresolved dissents' section), and a first-class error
log ('times I was wrong'). The error log is the credibility signal: a researcher that
UPDATES, not a crank (BUILD_PLAN 5.7).
"""
from __future__ import annotations

from pathlib import Path

from ..engine import state_of_argument


def mini_review(store, claim_ids: list[str], title: str = "Mini-review") -> str:
    """Serif-ready markdown synthesizing a set of claims, honest about dissent."""
    lines = [f"# {title}", ""]
    dissents = []
    for cid in claim_ids:
        c = store.get_claim(cid)
        if c is None:
            continue
        n = store.independent_source_count(cid)
        state = state_of_argument(store, cid)
        lines.append(f"- **{c.statement[:160]}** — p={c.calibrated_p:.2f} "
                     f"[{c.provenance_state}], {n} independent source(s); *{state}*")
        if n < 2 or state == "contested":
            dissents.append((cid, c, n, state))
    lines += ["", "## Unresolved dissents", ""]
    if dissents:
        for cid, c, n, state in dissents:
            reason = "single-source / unreplicated" if n < 2 else "contested (sign has flipped)"
            lines.append(f"- {c.statement[:120]} — {reason}")
    else:
        lines.append("- none flagged in this set")
    lines += ["", "_Auto-written by Persona; provenance-typed, uncertainty stated._"]
    return "\n".join(lines)


def save_mini_review(me, store, claim_ids: list[str], title: str = "Mini-review") -> Path:
    """Write a mini-review into the self's artifacts shelf (me.root/reviews/)."""
    md = mini_review(store, claim_ids, title)
    reviews = Path(me.root) / "reviews"
    reviews.mkdir(exist_ok=True)
    slug = "".join(ch if ch.isalnum() else "_" for ch in title.lower())[:40]
    path = reviews / f"{slug}.md"
    path.write_text(md, encoding="utf-8")
    return path


def note_reversal(me, store, claim_id: str, note: str = "") -> None:
    """Record a time a belief was overturned — the error log as a first-class artifact."""
    hist = store.history(claim_id)
    detail = ""
    if hist:
        h = hist[-1]
        detail = f" (logit {h['logit_before']:.2f} → {h['logit_after']:.2f}, cause={h['cause']})"
    me.log_error(f"reversed belief {claim_id}: {note}{detail}")
