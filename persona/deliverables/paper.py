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

_SYSTEM = (
    "You write a rigorous research paper in MARKDOWN from the mind's cited synthesis notes, prior "
    "beliefs, and prior papers. Follow this structure EXACTLY:\n"
    "1. `# Title` — specific and informative.\n"
    "2. `## Abstract` — ONE tight paragraph, ≤180 words: the question, what you actually establish, "
    "and the single most important takeaway. No walls of text.\n"
    "3. `## Main result` — state precisely what THIS paper establishes as a short bulleted list, and "
    "TAG each item with its status: **[PROVED HERE]** (a complete argument given below), "
    "**[VERIFIED NUMERICALLY]** (checked by computation), **[CITED]** (established elsewhere, with "
    "[n]), or **[OPEN]** (conjecture / not settled). Be scrupulously honest — do not tag something "
    "PROVED HERE unless the argument is actually in the paper.\n"
    "4. `## Introduction` — the problem and why it matters.\n"
    "5. 2–4 body `##` sections carrying the actual argument/derivation/computation. Show the reasoning, "
    "not just conclusions. Refer to Figure 1 / Figure 2 where they clarify.\n"
    "6. `## Reasoning chain` — a short numbered chain that traces each Main-result item to its support: "
    "either a cited source `[n]`, a prior belief, or a step proved above. A reader must be able to walk "
    "the logic from evidence to conclusion.\n"
    "7. `## Discussion` — what is established vs contested vs open, and the next question.\n"
    "8. `## References` — number every source `1. Authors/title — venue (doi:…)` and make sure every "
    "inline `[n]` resolves to an entry here.\n"
    "Use $…$ / $$…$$ for math. Embed EACH provided figure once as `![caption](figureN.png)` at the "
    "point it is discussed. Ground every claim in the provided material; never claim a proof you do "
    "not have — an honest 'this is not settled by the present evidence' is worth more than a bluff.")


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
    notes, sources = [], []               # sources: unique "[n] Title — venue (doi:…)" strings, numbered 1..N
    for s in slugs:
        f = nd / f"{s}.md"
        if f.exists():
            txt = f.read_text(encoding="utf-8")
            notes.append(txt[:3000])
            for m in re.finditer(r"^\[(\d+)\]\s*(.+)$", txt, re.M):
                cite = m.group(2).strip()
                if cite not in sources and len(sources) < 24:      # cap so the ref tail can't blow tokens
                    sources.append(cite)
    if not notes:
        return {"ok": False, "reason": "no-notes-matched"}
    # canonical numbered reference list — the paper MUST cite [n] against this, and we guarantee it
    # resolves by appending this exact list as ## References if the model forgets (see post-process).
    references_md = "## References\n\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(sources, 1))
    src_list = "\n".join(f"[{i}] {t}" for i, t in enumerate(sources, 1))

    # reasoning chain to PRIOR work: the mind's own beliefs + the titles of its earlier papers, so the
    # paper can trace its argument to established belief-state and past deliverables, not just fresh notes.
    beliefs = ""
    bf = p.paths.self_dir / "beliefs.md"
    if bf.exists():
        blines = [l for l in bf.read_text(encoding="utf-8").splitlines() if l.strip().startswith(("-", "*"))][:10]
        if blines:
            beliefs = "\n\nPRIOR BELIEFS (this mind's current belief-state — cite as 'prior belief'):\n" + "\n".join(blines)
    prior = []
    for pf in sorted(p.paths.projects_dir.glob("paper-*/*/paper.md"))[-12:]:
        try:
            hm = re.search(r"^#\s+(.+)$", pf.read_text(encoding="utf-8"), re.M)
            if hm and _slug(hm.group(1)) != _slug(topic):
                prior.append(hm.group(1).strip())
        except Exception:
            pass
    prior_md = ("\n\nRELATED PRIOR PAPERS BY THIS MIND (reference where relevant):\n"
                + "\n".join(f"- {t}" for t in prior[-6:])) if prior else ""

    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msgs = [{"role": "user", "content": f"Topic / question:\n{topic}\n\nSYNTHESIS NOTES:\n"
             + "\n\n=== NOTE ===\n".join(notes) + f"\n\nNUMBERED SOURCES (cite inline as [n]; list ALL "
             f"under ## References):\n{src_list}{beliefs}{prior_md}\n\nWrite the complete paper in Markdown."}]
    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    project = p.paths.projects_dir / f"paper-{_slug(topic)}" / run_id
    project.mkdir(parents=True, exist_ok=True)
    # TWO real, grounded figures (matplotlib written by the builder, run in the sandbox): a structural
    # diagram and a data/quantities plot. More than one figure was the main formatting gap (6/10 papers
    # had none). Budget-gated: build what we can afford.
    fignums = []
    try:
        from ..agents import builder
        framings = [("figure1.png", f"{topic} — a labeled diagram of the core objects/mechanism and how they relate"),
                    ("figure2.png", f"{topic} — the key quantities, distribution, or structure plotted as a clean data figure")]
        for i, (fname, framing) in enumerate(framings, 1):
            if not budget().can_spend():
                break
            fg = builder.build_visual("diagram", framing, parent_id=parent_id, max_attempts=1)
            sp = p.paths.workspace / (fg.get("artifact") or "")
            if fg.get("ok") and sp.is_file():
                shutil.copy2(sp, project / fname)
                fignums.append(i)
    except Exception:
        pass
    if fignums:
        msgs[0]["content"] += ("\n\nFIGURES available: " + ", ".join(f"figure{i}.png" for i in fignums)
            + ". Embed EACH once as ![caption](figureN.png) at the point it is discussed; refer to it as Figure N.")
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
    # ENFORCE figures: the model often ignores the embed instruction, so inject any built-but-unreferenced
    # figure into the body (before Discussion/References) — a paper with no diagrams was the main gap.
    missing = [i for i in fignums if f"figure{i}.png" not in md]
    if missing:
        caps = {1: "structure and objects of the problem", 2: "key quantities / distribution"}
        block = "\n\n" + "\n\n".join(f"![Figure {i}. {caps.get(i,'')}](figure{i}.png)" for i in missing) + "\n\n"
        anchor = re.search(r"^##\s*(discussion|reasoning chain|references)", md, re.I | re.M)
        md = (md[:anchor.start()] + block + md[anchor.start():]) if anchor else (md.rstrip() + block)
    # guarantee citations resolve: if the model omitted (or truncated) the References section, append
    # the canonical numbered list so every inline [n] traces to a real source with its DOI.
    if sources and not re.search(r"^##\s*references", md, re.I | re.M):
        md = md.rstrip() + "\n\n" + references_md + "\n"
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
