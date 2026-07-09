"""Paper engine (v5 P10) — a compiled LaTeX -> PDF paper, grounded in the mind's cited notes.

Generates a full LaTeX article from the persona's synthesis notes, compiles it offline with
pdflatex in the sandbox (with a compile-error retry loop — LLM LaTeX often needs one), and outputs
a real PDF to deliverables/. References come from the notes' sources, so every citation resolves.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .. import config
from ..budget import budget
from ..context import get_persona
from ..events import log
from ..tools import sandbox

_TOOL = {"name": "write_latex", "description": "Write a complete, compilable LaTeX article.",
         "input_schema": {"type": "object", "properties": {
             "title": {"type": "string"},
             "latex": {"type": "string", "description": "a COMPLETE LaTeX document (\\documentclass "
                 "{article} ... \\end{document}). Use only base packages (amsmath, graphicx, hyperref). "
                 "Abstract, sections, and a \\begin{thebibliography} built from the numbered sources. "
                 "Cite with \\cite{sN}. No external files/images. Must compile with pdflatex."}},
             "required": ["title", "latex"]}}

_SYSTEM = ("You write a concise, compilable LaTeX research paper from cited synthesis notes. Use "
           "\\documentclass{article} and only base packages. Ground every claim in the notes; build "
           "\\begin{thebibliography} from the numbered sources with \\bibitem{sN}. Keep it self-"
           "contained (no external images). Prefer correctness/compilability over length.")


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
                if m.group(2).strip() not in snum:
                    snum[m.group(2).strip()] = f"s{len(sources)+1}"
                    sources.append(m.group(2).strip())
    if not notes:
        return {"ok": False, "reason": "no-notes-matched"}
    src_list = "\n".join(f"{snum[k]}: {k}" for k in sources)

    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msgs = [{"role": "user", "content": f"Topic: {topic}\n\nSYNTHESIS NOTES:\n"
             + "\n\n=== NOTE ===\n".join(notes) + f"\n\nSOURCES (use as \\bibitem keys):\n{src_list}\n\n"
             f"Write the complete LaTeX paper."}]
    project = p.paths.projects_dir / f"paper-{_slug(topic)}"
    project.mkdir(parents=True, exist_ok=True)
    title, ok = topic, False
    for attempt in range(2):                         # generate, compile, fix-on-error once
        resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=4096, system=_SYSTEM,
            tools=[_TOOL], tool_choice={"type": "tool", "name": "write_latex"}, messages=msgs)
        u = resp.usage
        budget().add((u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000)
        out = {}
        for b in resp.content:
            if b.type == "tool_use":
                out = b.input
        if not out:
            break
        title = out.get("title", topic)
        (project / "main.tex").write_text(out.get("latex", ""), encoding="utf-8")
        r = sandbox.compile_latex(project, "main.tex")
        if r["ok"]:
            ok = True
            break
        # feed the compile error back for one fix
        msgs.append({"role": "assistant", "content": resp.content})
        msgs.append({"role": "user", "content": [{"type": "tool_result",
            "tool_use_id": next(b.id for b in resp.content if b.type == "tool_use"),
            "content": f"pdflatex FAILED. Fix the LaTeX so it compiles. Error tail:\n{r['log'][-1500:]}"}]})

    if not ok:
        log().emit("error", f"paper on “{topic}” did not compile", actor="paper", parent_id=parent_id)
        return {"ok": False, "reason": "compile-failed", "project": project.name}
    p.paths.deliverables_dir.mkdir(parents=True, exist_ok=True)
    dst = p.paths.deliverables_dir / f"paper-{_slug(topic)}.pdf"
    import shutil
    shutil.copy(project / "main.pdf", dst)
    log().emit("artifact", f"compiled a paper: “{title}” → {dst.name} ({len(sources)} refs)",
               actor="paper", parent_id=parent_id, file=dst.name)
    return {"ok": True, "pdf": dst.name, "title": title, "sources": len(sources)}
