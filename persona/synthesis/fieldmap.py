"""Field map (v5 P7) — a navigable map THROUGH the field, always current.

Derived live from the claim graph: the subtopic communities, each with its key beliefs, internal
contradictions, open questions (from its synthesis note), and paper count. This is the "map through
a subject" the owner asked for — subtopics → claims → contradictions → open-questions → papers.
"""
from __future__ import annotations

import re

from . import communities
from .synthesizer import _slug


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
