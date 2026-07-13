"""On-demand grounded report (v9) — the idea-genealogy tool's payload.

Select any region of the field (a search query / a set of entities picked on the graph) and get a
REAL, cited report built from exactly the claims in that region — every statement traces to a source
paper with its year + DOI, and a follow-up message refines it. This is the differentiator vs asking a
chatbot: nothing is invented, everything resolves. Reuses the KG's grounded claims+quotes+sources.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .. import config
from ..budget import budget
from ..context import get_persona
from ..events import log

_SYSTEM = (
    "You write a rigorous, CITED research briefing from a set of extracted claims (each with verbatim "
    "quotes + source papers). Structure: `# Title`, a 2-3 sentence **Overview**, `## What is "
    "established`, `## What is contested` (name the disagreeing sources), `## Open questions`, and "
    "`## References`. Cite EVERY statement inline as [n] against the numbered sources; never state "
    "anything the claims don't support — if the region is thin, say so. Use $…$ for math. Output ONLY "
    "Markdown starting with '# '.")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(t):
    return (re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")[:48]) or "report"


def _st(x):
    return re.sub(r"<[^>]+>", "", str(x or "")).strip()


def generate(query: str, *, entities: list | None = None, message: str = "", parent_id=None) -> dict:
    """Build a grounded, cited report for a region (a query or an explicit entity set). `message`
    is an optional user steer. Returns {ok, markdown, file, n_claims, n_sources, entities}."""
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    from ..memory.membrane import get_kg
    kg = get_kg()
    if kg is None:
        return {"ok": False, "reason": "no-graph"}
    ents = list(entities) if entities else []
    if not ents:
        seen = set()
        # match the whole phrase first, then each significant token (kg.search is a substring match, so
        # a multi-word query rarely hits an entity name — tokenizing finds the region reliably)
        for tok in [query] + [w for w in re.split(r"[\s,;]+", query) if len(w) > 3]:
            for n in kg.search(tok, 12):
                if n.get("type") == "entity" and n["label"] not in seen:
                    seen.add(n["label"])
                    ents.append(n["label"])
            if len(ents) >= 24:
                break
        ents = ents[:24]
    if not ents:
        return {"ok": False, "reason": "no-matching-region"}
    claims = kg.claims_about(ents, 45)
    if len(claims) < 2:
        return {"ok": False, "reason": "too-little-evidence"}

    # numbered, deduped source list carrying year + DOI (the citation targets)
    src_num, src_list = {}, []
    for c in claims:
        for s in (c.get("sources") or []):
            if s.get("slug") and s["slug"] not in src_num:
                src_num[s["slug"]] = len(src_list) + 1
                src_list.append(s)
    arrow = {"+": "increases", "-": "decreases", "0": "no effect"}
    claim_lines = []
    for c in claims:
        cites = sorted({src_num[s["slug"]] for s in (c.get("sources") or []) if s.get("slug") in src_num})
        q = next((s.get("quote") for s in (c.get("sources") or []) if s.get("quote")), "")
        claim_lines.append(f"- {c['subject']} {arrow.get(c['effect_sign'], '~')} {c['object']} "
                           f"({c['independent_sources']} labs) {['['+str(n)+']' for n in cites]}"
                           + (f'  quote: "{_st(q)[:180]}"' if q else ""))
    sources_md = "\n".join(f"{src_num[s['slug']]}. {_st(s.get('title')) or s['slug']} — {_st(s.get('lab'))}"
                           + (f" ({s['year']})" if s.get("year") else "")
                           + (f" doi:{s['doi']}" if s.get("doi") else "") for s in src_list)
    prompt = (f"Region: {query}\nEntities: {', '.join(ents[:12])}\n\n"
              f"CLAIMS (with independent-lab counts, [n]=source, and a quote):\n" + "\n".join(claim_lines)
              + f"\n\nNUMBERED SOURCES (cite as [n]):\n{sources_md}\n\n"
              + (f"The reader specifically wants: {message}\n\n" if message else "")
              + "Write the cited briefing.")

    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=4000, system=_SYSTEM,
                                  messages=[{"role": "user", "content": prompt}])
    u = resp.usage
    budget().add((u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000)
    md = "".join(b.text for b in resp.content if b.type == "text").strip()
    if len(md) < 200:
        return {"ok": False, "reason": "empty-report"}
    # guarantee references resolve: replace/append the canonical numbered list (DOIs) of cited sources
    from ..deliverables.paper import _fix_references
    src_strings = [f"{_st(s.get('title')) or s['slug']} — {_st(s.get('lab'))}"
                   + (f" ({s['year']})" if s.get("year") else "")
                   + (f" doi:{s['doi']}" if s.get("doi") else "") for s in src_list]
    md = _fix_references(md, src_strings)

    p = get_persona()
    (p.paths.deliverables_dir / "reports").mkdir(parents=True, exist_ok=True)
    dst = p.paths.deliverables_dir / "reports" / f"report-{_slug(query)}.md"
    dst.write_text(md, encoding="utf-8")
    log().emit("artifact", f"generated a grounded report on “{query[:50]}” "
               f"({len(claims)} claims · {len(src_list)} sources)", actor="report",
               parent_id=parent_id, file=f"reports/{dst.name}")
    return {"ok": True, "markdown": md, "file": f"reports/{dst.name}", "n_claims": len(claims),
            "n_sources": len(src_list), "entities": ents}
