"""Field map (v5 P7) — a navigable map THROUGH the field, always current.

Derived live from the claim graph: the subtopic communities, each with its key beliefs, internal
contradictions, open questions (from its synthesis note), and paper count. This is the "map through
a subject" the owner asked for — subtopics → claims → contradictions → open-questions → papers.
"""
from __future__ import annotations

import re

from . import communities
from .synthesizer import _slug


def _handoff_for_contradiction(cc: dict) -> str:
    """FC-2: a live sign-contradiction isn't only displayed — it's filed as a human-handoff dossier
    so it lands in the inbox queue for judgment. Built DETERMINISTICALLY from the contradiction's
    existing fields (no model, no network); file_handoff's content-hash id dedups identical dossiers.
    Best-effort — a schema mismatch must never break the field map render."""
    subj, obj = cc["subject"], cc["object"]
    pos, neg = cc.get("pos", 0), cc.get("neg", 0)
    total = (pos + neg) or 1
    dossier = {
        "decision_requested": f"Does {subj} increase or decrease {obj}?",
        "why_unresolvable": f"{pos} independent source(s) report an increase and {neg} report a "
                            f"decrease — a same-relation sign conflict the swarm can't settle by count.",
        "disagreeing": [
            {"claim_id": cc.get("pos_claim", ""), "span": f"{subj} increases {obj}"},
            {"claim_id": cc.get("neg_claim", ""), "span": f"{subj} decreases {obj}"},
        ],
        "conflict_type": "semantic",  # opposite signs on the same relation
        "cheapest_test": {"action": f"human review of the opposing spans on {subj} -> {obj}",
                          "cost_tier": "human", "dataset": ""},
        "expected_updates": [{"outcome": "resolved",
                              "belief_change": "keep the supported sign, retract the other"}],
        # PLACEHOLDER heuristic: uncertainty = balance of opposing sources (1.0 = evenly split / most
        # contested, -> 0 as one side dominates). Not validated; a defensible split metric would replace it.
        "uncertainty": round(2 * min(pos, neg) / total, 3),
        "authority_boundary": "human anchors any sign reversal; Persona cannot run the wet-lab test",
    }
    try:
        from .. import inbox
        return inbox.file_handoff("field_contradiction", dossier)
    except Exception:
        return ""


def _open_questions(note_path) -> list:
    if not note_path.exists():
        return []
    text = note_path.read_text(encoding="utf-8")
    m = re.search(r"## open questions\n(.*?)(\n##|\Z)", text, re.S)
    if not m:
        return []
    return [l.strip()[2:] for l in m.group(1).splitlines() if l.strip().startswith("- ")]


def build(kg, notes_dir) -> dict:
    comms = communities.detect(kg, min_size=3)
    arrow = {"+": "↑", "-": "↓", "0": "∅"}
    contra = kg.contradictions(limit=100)
    contra_pairs = {(c["subject"], c["object"]) for c in contra}
    subtopics = []
    for c in comms:
        ents = c["entities"]
        claims = kg.claims_in(ents, limit=40)
        beliefs = [{"claim_id": cl["claim_id"],
                    "text": f"{cl['subject']} {arrow.get(cl['effect_sign'],'~')} {cl['object']}",
                    "labs": cl["independent_sources"], "confidence": round(cl.get("confidence", 0), 2)}
                   for cl in claims if cl["independent_sources"] >= 2][:8]
        subc = [{"subject": cc["subject"], "object": cc["object"], "pos": cc["pos_sources"],
                 "neg": cc["neg_sources"], "pos_claim": cc["pos_claim"], "neg_claim": cc["neg_claim"]}
                for cc in contra if (cc["subject"], cc["object"]) in
                {(cl["subject"], cl["object"]) for cl in claims}]
        # FC-2: don't just show the contradiction — file it for human judgment. Deterministic + deduped
        # (content-hash id), so re-rendering the map doesn't create new asks. ponytail: appends one line
        # per build; move to file-if-new if the jsonl grows unwieldy.
        for cc in subc:
            cc["handoff_id"] = _handoff_for_contradiction(cc)
        slug = _slug(ents)
        note_p = notes_dir / f"{slug}.md"
        title = slug
        if note_p.exists():
            for l in note_p.read_text(encoding="utf-8").splitlines():
                if l.startswith("# "):
                    title = l[2:]; break
        src_count = len({s["slug"] for cl in claims for s in (cl.get("sources") or []) if s.get("slug")})
        subtopics.append({"slug": slug, "title": title, "entities": ents[:10],
                          "n_claims": len(claims), "n_sources": src_count, "has_note": note_p.exists(),
                          "beliefs": beliefs, "contradictions": subc,
                          "open_questions": _open_questions(note_p)[:6]})
    subtopics.sort(key=lambda s: -s["n_claims"])
    return {"n_subtopics": len(subtopics), "subtopics": subtopics,
            "total_contradictions": len(contra)}
