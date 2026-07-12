"""Paper engine (v5 P10) — a compiled LaTeX -> PDF paper, grounded in the mind's cited notes.

Generates a full LaTeX article from the persona's synthesis notes, compiles it offline with
pdflatex in the sandbox (with a compile-error retry loop — LLM LaTeX often needs one), and outputs
a real PDF to deliverables/. References come from the notes' sources, so every citation resolves.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from datetime import datetime, timezone

from .. import config
from ..budget import budget
from ..context import get_persona
from ..events import log
from ..tools import sandbox

_TOOL = {"name": "write_paper", "description": "Write a complete research paper in Markdown.",
         "input_schema": {"type": "object", "properties": {
             "title": {"type": "string"},
             "markdown": {"type": "string", "description": "a COMPLETE research paper in Markdown: "
                 "a `# Title`, then `## Abstract`, `## Introduction`, 2-4 body `##` sections, "
                 "`## Discussion`, and `## References` listing the numbered sources (`1. Author … DOI`). "
                 "Cite inline as [1], [2]. Use $…$ / $$…$$ for math. If a figure is provided, embed it "
                 "ONCE as `![caption](figure.png)` and refer to it. Ground every claim in the notes; "
                 "be rigorous and honest about what is established vs open."}},
             "required": ["title", "markdown"]}}

_SYSTEM = ("You write a concise, rigorous research paper in MARKDOWN from the mind's cited synthesis "
           "notes. Structure: Title, Abstract, Introduction, 2-4 body sections, Discussion, References. "
           "Ground every claim in the provided notes/sources and cite inline as [n]; list the numbered "
           "sources with their DOIs under References. Use $…$ for math. If a figure file is provided, "
           "embed it once with ![caption](figure.png). Be honest — distinguish what is established, "
           "contested, and open; never claim a proof you do not have.")


def _slug(t): return (re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:50] or "paper")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_paper(topic: str, *, parent_id=None, max_notes: int = 6) -> dict:
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    if not sandbox.image_ready():
        return {"ok": False, "reason": "sandbox-image-missing"}
    p = get_persona()
    nd = p.paths.notes_dir
    if not nd.exists() or not any(nd.glob("*.md")):
        return {"ok": False, "reason": "no-notes-yet"}
    slugs = [h["slug"] for h in p.vectors.search(topic, k=max_notes) if h.get("slug")] or \
            [f.stem for f in sorted(nd.glob("*.md"))[:max_notes]]
    notes, sources, snum = [], [], {}
    for s in slugs:
        f = nd / f"{s}.md"
        if f.exists():
            txt = f.read_text(encoding="utf-8")
            notes.append(txt[:3000])
            for m in re.finditer(r"^\[(\d+)\]\s*(.+)$", txt, re.M):
                if m.group(2).strip() not in snum and len(sources) < 24:  # cap refs so the
                    snum[m.group(2).strip()] = f"s{len(sources)+1}"       # tail list can't blow the token budget
                    sources.append(m.group(2).strip())
    if not notes:
        return {"ok": False, "reason": "no-notes-matched"}
    src_list = "\n".join(f"{snum[k]}: {k}" for k in sources)

    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msgs = [{"role": "user", "content": f"Topic: {topic}\n\nSYNTHESIS NOTES:\n"
             + "\n\n=== NOTE ===\n".join(notes) + f"\n\nSOURCES (cite as [n], list under References):\n{src_list}\n\n"
             f"Write the complete paper in Markdown."}]
    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    project = p.paths.projects_dir / f"paper-{_slug(topic)}" / run_id
    project.mkdir(parents=True, exist_ok=True)
    # embed ONE real, grounded figure — matplotlib written by the builder and run in the sandbox
    try:
        from ..agents import builder
        fig = builder.build_visual("diagram", topic, parent_id=parent_id)
        src_png = p.paths.workspace / (fig.get("artifact") or "")
        if fig.get("ok") and src_png.is_file():
            shutil.copy2(src_png, project / "figure.png")
            msgs[0]["content"] += ("\n\nA FIGURE is available as figure.png. Embed it once as "
                "![<one-line caption>](figure.png) and refer to it in the text.")
    except Exception:
        pass
    # Generate the paper as plain-text MARKDOWN (NOT a forced tool call — that truncates the JSON at
    # max_tokens and yields an empty paper). Then compile via the robust document pipeline.
    from .document import compile_source, sanitize_markdown
    title, ok, total_cost, attempts, r = topic, False, 0.0, [], {}
    msgs[0]["content"] += "\n\nOutput ONLY the complete paper in Markdown, starting with '# '."
    resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=12000, system=_SYSTEM, messages=msgs)
    u = resp.usage
    call_cost = (u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000
    budget().add(call_cost); total_cost += call_cost
    md = sanitize_markdown("".join(b.text for b in resp.content if b.type == "text"))
    hm = re.search(r"^#\s+(.+)$", md, re.M)
    title = (hm.group(1).strip() if hm else "") or topic
    if len(md) >= 300:                                # require real substance, not an empty stub
        (project / "paper.md").write_text(md, encoding="utf-8")
        r = compile_source(md, "md", project, title=title)
        ok = bool(r.get("ok"))
    attempts.append({"attempt": 1, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                     "cost_usd": round(call_cost, 6), "markdown_len": len(md), "compile_ok": ok,
                     "stop_reason": resp.stop_reason, "source_sha256": r.get("source_sha256"),
                     "pdf_sha256": r.get("pdf_sha256"), "log_tail": (r.get("log", "") or "")[-1500:]})

    # Repair loop: LLM LaTeX usually needs a pass or two. Feed the pdflatex error log back and ask the
    # model to fix the ACTUAL .tex (md_to_latex would re-derive the same broken output), harden it, and
    # recompile — instead of giving up and leaving the mind with only a note. Bounded by budget.
    from .document import harden_latex
    n = 1
    while not ok and n < config.PAPER_COMPILE_ATTEMPTS and budget().can_spend():
        n += 1
        cur_tex = (project / "main.tex").read_text(encoding="utf-8", errors="replace")
        errlog = (r.get("log", "") or "")[-4000:]
        rp = client.messages.create(model=config.MODEL_WORKER, max_tokens=12000,
            system="You repair broken LaTeX so pdflatex compiles it. Output ONLY the full corrected .tex.",
            messages=[{"role": "user", "content":
                "This LaTeX failed to compile. Fix ONLY what the log flags and return the COMPLETE "
                "corrected document — no prose, no code fences.\n\n=== main.tex ===\n" + cur_tex +
                "\n\n=== pdflatex error log (tail) ===\n" + errlog}])
        u = rp.usage
        call_cost = (u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000
        budget().add(call_cost); total_cost += call_cost
        fixed = re.sub(r"^```(?:latex|tex)?|```$", "", "".join(b.text for b in rp.content
                                                                if b.type == "text").strip()).strip()
        compile_ok = False
        if "\\begin{document}" in fixed:          # sanity: a whole document, not a truncated fragment
            r = compile_source(harden_latex(fixed), "tex", project, title=title)
            ok = compile_ok = bool(r.get("ok"))
        attempts.append({"attempt": n, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                         "cost_usd": round(call_cost, 6), "repair": True, "compile_ok": compile_ok,
                         "stop_reason": rp.stop_reason, "source_sha256": r.get("source_sha256"),
                         "pdf_sha256": r.get("pdf_sha256"), "log_tail": (r.get("log", "") or "")[-1500:]})
        log().emit("control", f"paper compile attempt {n}/{config.PAPER_COMPILE_ATTEMPTS}: "
                   f"{'compiled' if ok else 'still failing'}", actor="paper", parent_id=parent_id)

    receipt = {"topic": topic, "title": title, "run_id": run_id, "ok": ok,
               "at": _now(), "attempts": attempts, "sources": sources,
               "cost_usd": round(total_cost, 6), "sandbox_image": sandbox.IMAGE,
               "sandbox_image_digest": sandbox.image_digest()}
    (project / "compile.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    if not ok:
        log().emit("error", f"paper on “{topic}” did not compile", actor="paper", parent_id=parent_id)
        return {"ok": False, "reason": "compile-failed",
                "project": str(project.relative_to(p.paths.projects_dir)).replace("\\", "/")}
    p.paths.deliverables_dir.mkdir(parents=True, exist_ok=True)
    source_hash = attempts[-1]["source_sha256"]
    dst = p.paths.deliverables_dir / f"paper-{_slug(topic)}-{source_hash[:10]}.pdf"
    shutil.copy2(project / "main.pdf", dst)
    receipt["deliverable"] = {"path": dst.name,
                              "pdf_sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
                              "bytes": dst.stat().st_size}
    (project / "compile.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    log().emit("artifact", f"compiled a paper: “{title}” → {dst.name} ({len(sources)} refs)",
               actor="paper", parent_id=parent_id, file=dst.name)
    return {"ok": True, "pdf": dst.name, "title": title, "sources": len(sources),
            "project": str(project.relative_to(p.paths.projects_dir)).replace("\\", "/"),
            "source_sha256": source_hash, "pdf_sha256": receipt["deliverable"]["pdf_sha256"]}
