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

_TOOL = {"name": "write_latex", "description": "Write a complete, compilable LaTeX article.",
         "input_schema": {"type": "object", "properties": {
             "title": {"type": "string"},
             "latex": {"type": "string", "description": "a COMPLETE LaTeX document (\\documentclass "
                 "{article} ... \\end{document}). Use base packages amsmath, graphicx, hyperref, url. "
                 "Abstract, sections, and a \\begin{thebibliography} built from the numbered sources. "
                 "Cite with \\cite{sN}. If a figure file is provided, embed it ONCE with a "
                 "\\begin{figure} ... \\includegraphics ... \\end{figure} and reference it. Must "
                 "compile offline with pdflatex (only the provided figure.png may be included)."}},
             "required": ["title", "latex"]}}

_SYSTEM = ("You write a concise, compilable LaTeX research paper from cited synthesis notes. Use "
           "\\documentclass{article} with amsmath, graphicx, hyperref, url. Ground every claim in the "
           "notes; build \\begin{thebibliography} from the numbered sources with \\bibitem{sN}, and "
           "where a source line contains a DOI render it as \\url{https://doi.org/<doi>}. If a figure "
           "file is provided, include it exactly once in a figure environment with a caption and "
           "reference it in the text. Do not \\includegraphics any other file. Prefer "
           "correctness/compilability over length.")


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
            msgs[0]["content"] += ("\n\nA FIGURE is available as figure.png. Embed it ONCE with "
                "\\begin{figure}[h]\\centering\\includegraphics[width=0.85\\linewidth]{figure.png}"
                "\\caption{<one line>}\\label{fig:main}\\end{figure} and reference \\ref{fig:main} "
                "in the text.")
    except Exception:
        pass
    title, ok, total_cost, attempts = topic, False, 0.0, []
    for attempt in range(2):                         # generate, compile, fix-on-error once
        resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=4096, system=_SYSTEM,
            tools=[_TOOL], tool_choice={"type": "tool", "name": "write_latex"}, messages=msgs)
        u = resp.usage
        call_cost = (u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000
        budget().add(call_cost)
        total_cost += call_cost
        out = {}
        for b in resp.content:
            if b.type == "tool_use":
                out = b.input
        if not out:
            break
        title = out.get("title", topic)
        (project / "main.tex").write_text(out.get("latex", ""), encoding="utf-8")
        r = sandbox.compile_latex(project, "main.tex")
        attempts.append({"attempt": attempt + 1, "input_tokens": u.input_tokens,
                         "output_tokens": u.output_tokens, "cost_usd": round(call_cost, 6),
                         "compile_ok": r["ok"], "exit_code": r.get("exit_code"),
                         "source_sha256": r.get("source_sha256"),
                         "pdf_sha256": r.get("pdf_sha256"), "log_tail": r.get("log", "")[-2000:]})
        if r["ok"]:
            ok = True
            break
        # feed the compile error back for one fix
        msgs.append({"role": "assistant", "content": resp.content})
        msgs.append({"role": "user", "content": [{"type": "tool_result",
            "tool_use_id": next(b.id for b in resp.content if b.type == "tool_use"),
            "content": f"pdflatex FAILED. Fix the LaTeX so it compiles. Error tail:\n{r['log'][-1500:]}"}]})

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
