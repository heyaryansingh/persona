"""Knowledge transfer (v6 P5) — hand the human what the persona KNOWS, not just next steps.

- topic_digest(q): a digestible, cited, layered briefing of everything the persona has learned on a
  topic (TL;DR -> what's settled -> what's contested -> open questions -> narrative), grounded ONLY
  in its own claims (each citable to source+DOI), plus a navigable subgraph and an evolution timeline
  (how belief/support changed over time).
- ask_graph(q): a plain-English question answered from the graph, WITH citations — never invented.

Both are read-only over the KG + notes + belief history; the human sees, reviews, and assesses the
connections/changes for themselves.
"""
from __future__ import annotations

import re

from .. import config, selfmind
from ..budget import budget
from ..context import get_persona

_STOP = {"what", "which", "whats", "is", "are", "the", "of", "a", "an", "and", "or", "in", "on", "to",
         "for", "how", "does", "do", "did", "was", "were", "between", "with", "about", "currently",
         "known", "relationship", "role", "effect", "cause", "causes", "why", "when", "where", "that",
         "this", "these", "those", "from", "into", "vs", "versus", "tell", "me", "your", "you"}


def _entities_for(kg, q: str, cap: int = 25) -> list:
    """Find topic entities by the WHOLE phrase AND each significant keyword (NL questions don't
    match any entity name as a whole substring)."""
    seen = {}
    for n in kg.search(q, cap):
        if n["type"] == "entity":
            seen[n["label"]] = 1
    for tok in {w for w in re.findall(r"[a-z0-9\-]{4,}", q.lower()) if w not in _STOP}:
        for n in kg.search(tok, 8):
            if n["type"] == "entity":
                seen[n["label"]] = 1
    return list(seen)[:cap]


def _numbered(claims: list) -> str:
    out = []
    for i, c in enumerate(claims):
        tag = " (anchored)" if c.get("anchored") else ""
        out.append(f"[{i+1}] {c['subject']} [{c['effect_sign']}] {c['object']} — "
                   f"{c['independent_sources']} independent labs, p={c['confidence']:.2f}{tag}")
    return "\n".join(out) or "(no claims yet on this topic)"


def _notes_for(q: str, k: int = 3) -> str:
    p = get_persona()
    texts = []
    try:
        for h in p.vectors.search(q, k=k):
            f = p.paths.notes_dir / f"{h.get('slug', '')}.md"
            if f.exists():
                texts.append(f.read_text(encoding="utf-8")[:1400])
    except Exception:
        pass
    return "\n\n---\n\n".join(texts)


def _claim_cite(c: dict) -> dict:
    doi = next((s.get("doi") for s in (c.get("sources") or []) if s.get("doi")), None)
    return {"claim_id": c["claim_id"], "n": None,
            "text": f"{c['subject']} [{c['effect_sign']}] {c['object']}",
            "labs": c["independent_sources"], "confidence": c["confidence"], "doi": doi}


def topic_digest(q: str, kg=None, history=None, max_claims: int = 45, *, generate: bool = False) -> dict:
    if kg is None:
        return {"ok": False, "reason": "no-kg"}
    ents = _entities_for(kg, q)
    claims = kg.claims_about(ents, max_claims) if ents else []
    contra = [c for c in kg.contradictions(40)
              if c["subject"] in ents or c["object"] in ents][:12]
    subgraph = kg.subgraph(ents)
    citations = [{**_claim_cite(c), "n": i + 1} for i, c in enumerate(claims)]
    # evolution: how the top claims' confidence/support moved over time
    evolution = []
    if history is not None:
        for c in claims[:8]:
            try:
                series = history.series(c["claim_id"])
            except Exception:
                series = []
            if len(series) >= 2:
                evolution.append({"claim_id": c["claim_id"],
                                  "text": f"{c['subject']} [{c['effect_sign']}] {c['object']}",
                                  "series": series})
    base = {"ok": bool(claims), "topic": q, "reason": None if claims else "nothing-known-yet",
            "generated": False, "digest": None, "claims": citations, "subgraph": subgraph,
            "evolution": evolution, "contradictions": contra, "n_claims": len(claims),
            "n_sources": len({s.get("slug") for c in claims for s in (c.get("sources") or [])
                              if s.get("slug")})}
    if not generate or not claims:
        return base
    if not config.have_key() or not budget().can_spend():
        return {**base, "reason": "no-key-or-budget"}
    from ..providers import anthropic_client
    client = anthropic_client()
    tool = {"name": "brief", "description": "Produce the layered topic briefing.",
            "input_schema": {"type": "object", "properties": {
                "tldr": {"type": "string", "description": "2-3 sentence plain summary of what's known"},
                "settled": {"type": "array", "items": {"type": "string"},
                            "description": "what the evidence supports well; cite claims as [n]"},
                "contested": {"type": "array", "items": {"type": "string"},
                              "description": "what's contradictory or uncertain; cite [n]"},
                "open_questions": {"type": "array", "items": {"type": "string"}},
                "narrative": {"type": "string", "description": "a tight cited synthesis; cite [n]"}},
                "required": ["tldr", "settled", "contested", "open_questions", "narrative"]}}
    cl = _numbered(claims)
    contra_txt = "\n".join(f"- {c['subject']} -> {c['object']}: +{c['pos_sources']} vs "
                           f"-{c['neg_sources']} labs" for c in contra) or "(none)"
    prompt = (f"Topic: {q}\n\nMY CLAIMS (cite these by number as [n]):\n{cl}\n\n"
              f"KNOWN CONTRADICTIONS:\n{contra_txt}\n\n"
              f"MY SYNTHESIS NOTES:\n{_notes_for(q)}\n\n"
              f"Write a TIGHT, scannable briefing grounded ONLY in my claims (cite [n]): 4-6 settled "
              f"points, 3-5 contested points, 3-5 open questions, and a 5-6 sentence narrative. Be "
              f"honest about settled vs contested vs open. Do not invent.")
    resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=3000, system=(
        "You brief a researcher on what a synthetic colleague has learned about a topic, strictly "
        "from its own evidence-backed claims. Cite claims as [n]. Distinguish settled from contested "
        "from open. Never introduce facts not in the provided claims/notes."),
        tools=[tool], tool_choice={"type": "tool", "name": "brief"},
        messages=[{"role": "user", "content": prompt}])
    u = resp.usage
    budget().add((u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000)
    digest = next((b.input for b in resp.content if b.type == "tool_use"), None)
    return {**base, "ok": True, "generated": True, "digest": digest}


def ask_graph(q: str, kg=None) -> dict:
    """Answer a plain-English question from the graph, WITH citations (never invented)."""
    if kg is None:
        return {"ok": False, "reason": "no-kg"}
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    ents = _entities_for(kg, q)
    claims = kg.claims_about(ents, 40) if ents else []
    citations = [{**_claim_cite(c), "n": i + 1} for i, c in enumerate(claims)]
    from ..providers import anthropic_client
    client = anthropic_client()
    tool = {"name": "answer", "description": "Answer the question from the claims.",
            "input_schema": {"type": "object", "properties": {
                "answer": {"type": "string", "description": "a direct answer citing claims as [n]; if "
                           "the graph doesn't contain enough to answer, say so honestly"}},
                "required": ["answer"]}}
    prompt = (f"Question: {q}\n\nMY EVIDENCE-BACKED CLAIMS (cite as [n]):\n{_numbered(claims)}\n\n"
              f"MY NOTES:\n{_notes_for(q, 2)}\n\nAnswer only from these; cite [n]; if insufficient, say so.")
    resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=1000, system=(
        "You answer a researcher's question strictly from a synthetic colleague's evidence-backed "
        "claims. Cite [n]. If the claims don't cover it, say honestly what's missing — never invent."),
        tools=[tool], tool_choice={"type": "tool", "name": "answer"},
        messages=[{"role": "user", "content": prompt}])
    u = resp.usage
    budget().add((u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000)
    out = next((b.input for b in resp.content if b.type == "tool_use"), {})
    return {"ok": True, "question": q, "answer": out.get("answer", ""), "claims": citations,
            "subgraph": kg.subgraph(ents)}


def tree(max_topics: int = 16) -> dict:
    """The LAYERED knowledge ladder (v8): L1 topics known → L2 one-line summaries → L3 the in-depth
    synthesis → L4 the primary sources. Assembled from the mind's own notes + interests + sources, so
    a human can drill from 'what it knows' down to 'every source it stands on'."""
    p = get_persona()
    nd = p.paths.notes_dir
    topics = []
    files = sorted(nd.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True) if nd.exists() else []
    for f in files[:max_topics]:
        txt = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^#\s+(.+)$", txt, re.M)
        title = (m.group(1).strip() if m else f.stem)
        meta = re.search(r"^_.*_$", txt, re.M)
        l2meta = (meta.group(0).strip("_ ") if meta else "")
        parts = re.split(r"\n##\s*sources", txt, maxsplit=1)
        body = re.sub(r"^#.*$|^_.*_$", "", parts[0], flags=re.M).strip()
        first = (re.split(r"(?<=[.!?])\s", body, maxsplit=1)[0] if body else "")[:240]
        srcs = re.findall(r"^\[(\d+)\]\s*(.+)$", parts[1] if len(parts) > 1 else "", re.M)
        topics.append({"slug": f.stem, "title": title, "summary": first or l2meta, "meta": l2meta,
                       "depth_chars": len(body), "dossier": body[:8000],
                       "sources": [s[1][:90] for s in srcs[:16]], "n_sources": len(srcs)})
    noted = {t["title"].lower() for t in topics}
    l1_only = [n for n, _w in selfmind.interests() if n.lower() not in noted][:12]
    return {"topics": topics, "l1_only": l1_only,
            "n_known": len(topics) + len(l1_only), "n_deep": len(topics),
            "n_sources": sum(t["n_sources"] for t in topics)}
