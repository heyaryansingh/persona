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
    "You are writing a research article to the standard of a top journal (Nature / PNAS): precise, "
    "structured, figure-rich, every claim traceable. Write in MARKDOWN from the mind's cited synthesis "
    "notes, prior beliefs, and prior papers. Follow this journal structure EXACTLY:\n"
    "1. `# Title` — specific, informative, and self-contained.\n"
    "2. `## Abstract` — ONE tight paragraph, ≤180 words: background, the question, what you establish, "
    "and the key result. No walls of text.\n"
    "3. `## Significance` — 2–3 sentences a non-specialist scientist could read: why this matters "
    "(Nature/PNAS-style significance statement).\n"
    "4. `## Main result` — the precise claims of THIS paper as a short bulleted list. Flag ONLY the "
    "noteworthy ones: **[PROVED HERE]** (a complete argument is given below), **[VERIFIED NUMERICALLY]** "
    "(machine-checked by computation), or **[OPEN]** (conjecture / not settled). A claim merely "
    "established in the literature needs NO tag — just carry its [n] citation (the citation is its "
    "evidence; do NOT write '[CITED]'). Never tag PROVED HERE unless the argument is actually in the paper.\n"
    "5. `## Introduction` — the problem, prior work (cite [n]), and the gap.\n"
    "6. `## Methods` — how the result is obtained: the reduction/derivation strategy, and any "
    "computation (state that code was run in a sandbox and what it checked).\n"
    "7. `## Results` — the actual argument/derivation/computation, section by section. Show the "
    "reasoning, not just conclusions. Reference **Figure 1**, **Figure 2** where they clarify, and give "
    "each a real one-line caption.\n"
    "8. `## Reasoning chain` — a numbered chain tracing each Main-result item to its support: a cited "
    "source `[n]`, a prior belief, or a step proved above. A reader must walk evidence → conclusion.\n"
    "9. `## Discussion` — established vs contested vs open, limitations, and the next question.\n"
    "10. `## References` — number every source `1. Authors/title — venue (doi:…)`; every inline `[n]` "
    "must resolve here.\n"
    "Use $…$ / $$…$$ for math. Embed EACH provided figure once as `![Figure N. <caption>](figureN.png)` "
    "in Results where it is discussed. Ground every claim in the provided material; never claim a proof "
    "you do not have — an honest 'not settled by the present evidence' beats a bluff.")


def _slug(t): return (re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:50] or "paper")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _prune_refs(md: str) -> str:
    """Citation hygiene: keep ONLY reference entries that are actually cited inline, so a paper never
    ships with orphaned references (a bibliography of entries nothing points to reads as unprofessional).
    Numbers may end up non-contiguous — every listed ref still resolves, which is what matters."""
    m = re.search(r"(^##\s*references\s*)$(.*)\Z", md, re.I | re.M | re.S)
    if not m:
        return md
    head, refs = md[:m.start()], m.group(2)
    cited = set(re.findall(r"\[(\d+)\]", head))          # numbers cited in the body
    if not cited:                                        # nothing cited -> drop the orphaned list entirely
        return head.rstrip() + "\n"
    kept = []
    for line in refs.splitlines():
        n = re.match(r"^\s*(\d+)\.\s", line)
        if n and n.group(1) not in cited:
            continue                                     # drop an uncited reference entry
        kept.append(line)
    return head + m.group(1) + "\n" + "\n".join(kept).strip() + "\n"


_PLACEHOLDER_CAP = re.compile(
    r"structure and objects of the problem|key quantities?\s*/?\s*distribution|"
    r"a labeled (?:concept )?diagram of the core|a quantitative chart", re.I)


def _fix_references(md: str, sources: list) -> str:
    """Guarantee clean citations: strip the model's own (often canned/bracket-style/orphaned) reference
    list, drop any inline [n] that has no source, and append the canonical DOI-carrying list of ONLY the
    cited sources — so every reference is cited and every citation resolves to a real paper + DOI."""
    md = re.sub(r"\n##\s*references\b.*\Z", "\n", md, flags=re.I | re.S)   # remove model's ref section
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", md)}
    valid = {n for n in cited if 1 <= n <= len(sources)}
    if not valid or not sources:
        return re.sub(r"\[(\d+)\]", "", md).rstrip() + "\n"                 # no resolvable cites → drop them
    md = re.sub(r"\[(\d+)\]", lambda m: m.group(0) if int(m.group(1)) in valid else "", md)  # kill danglers
    lines = "\n".join(f"{i}. {t}" for i, t in enumerate(sources, 1) if i in valid)
    return md.rstrip() + "\n\n## References\n\n" + lines + "\n"


def _fix_captions(md: str, capmap: dict) -> str:
    """Replace shipped PLACEHOLDER figure captions ('structure and objects of the problem') with the
    figure's real title, so a paper never ships a generic/framing caption."""
    def repl(m):
        num, cap = m.group(1), m.group(2)
        if _PLACEHOLDER_CAP.search(cap) or len(cap.strip()) < 4:
            return f"![Figure {num}. {capmap.get(int(num)) or 'illustration'}](figure{num}.png)"
        return m.group(0)
    return re.sub(r"!\[Figure (\d+)\.?\s*([^\]]*)\]\(figure\1\.png\)", repl, md)


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
                cite = re.sub(r"</?[A-Za-z][^>]*>", "", m.group(2)).strip()   # strip leaked HTML tags
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
    fignums, figinfo = [], []          # figinfo: (num, real_title) so the paper's caption MATCHES the image
    try:
        from ..agents import builder
        # two DISTINCT figures: a concept diagram and a genuinely quantitative chart (not another diagram)
        framings = [("figure1.png", f"{topic} — a labeled concept diagram of the core objects/mechanism and how they relate"),
                    ("figure2.png", f"{topic} — a QUANTITATIVE chart/plot of the key numbers (bars/lines/scatter), NOT a boxes-and-arrows diagram")]
        for i, (fname, framing) in enumerate(framings, 1):
            if not budget().can_spend():
                break
            fg = builder.build_visual("diagram", framing, parent_id=parent_id, max_attempts=1)
            sp = p.paths.workspace / (fg.get("artifact") or "")
            if fg.get("ok") and sp.is_file():
                shutil.copy2(sp, project / fname)
                fignums.append(i)
                figinfo.append((i, (fg.get("title") or "").strip()))
    except Exception:
        pass
    if figinfo:
        # tell the model EXACTLY what each figure shows, so its caption/reference can't mismatch the image
        msgs[0]["content"] += ("\n\nFIGURES available (embed EACH once as ![caption](figureN.png) where it "
            "fits; your caption and any 'Figure N shows…' text MUST match what the figure actually depicts):\n"
            + "\n".join(f"- figure{i}.png depicts: {t}" for i, t in figinfo if t))
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

    def _measure(text):
        # (non-reference body chars, body section count, distinct inline [n] citations)
        body = re.split(r"\n##\s*references", text, maxsplit=1, flags=re.I)[0]
        return (len(body.strip()), len(re.findall(r"^##\s+", body, re.M)),
                len(set(re.findall(r"\[(\d+)\]", text))))

    body_chars, n_sec, inline = _measure(md)
    # A real paper has a BODY, not just a title + a references list. The old floor (len>=300) shipped
    # bodyless stubs that became "papers" that were ONLY a ## References list (0 inline citations) —
    # unprofessional. Regenerate once if the first draft is thin.
    if (body_chars < 1200 or n_sec < 3) and budget().can_spend():
        resp2 = client.messages.create(model=config.MODEL_WORKER, max_tokens=12000, system=_SYSTEM,
            messages=msgs + [{"role": "assistant", "content": md[:1500]},
                             {"role": "user", "content": "That draft is only a stub — it lacks a real "
                              "body. Write the COMPLETE paper with every section (Abstract, Significance, "
                              "Introduction, Methods, Results, Discussion) filled with substantive content "
                              "and inline [n] citations to the numbered sources. Output ONLY the full "
                              "Markdown paper, starting with '# '."}])
        u2 = resp2.usage
        call_cost = (u2.input_tokens * 3.0 + u2.output_tokens * 15.0) / 1_000_000
        budget().add(call_cost); total_cost += call_cost
        md2 = sanitize_markdown("".join(b.text for b in resp2.content if b.type == "text"))
        if _measure(md2)[0] > body_chars:
            md = md2
        body_chars, n_sec, inline = _measure(md)
    # ENFORCE figures: inject any built-but-unreferenced figure into the body (the model often ignores
    # the embed instruction) — but only into a real-bodied paper.
    missing = [i for i in fignums if f"figure{i}.png" not in md]
    if missing and n_sec >= 2:
        caps = dict(figinfo)                          # real figure titles, so an injected caption still matches
        block = "\n\n" + "\n\n".join(f"![Figure {i}. {caps.get(i) or 'illustration'}](figure{i}.png)" for i in missing) + "\n\n"
        anchor = re.search(r"^##\s*(discussion|reasoning chain|references)", md, re.I | re.M)
        md = (md[:anchor.start()] + block + md[anchor.start():]) if anchor else (md.rstrip() + block)
    # Citations: canonicalize to the real DOI-carrying sources, drop danglers, keep only cited (no
    # orphans, nothing dangling). Then strip leaked HTML tags and fix placeholder figure captions.
    md = _fix_references(md, sources)
    md = re.sub(r"</?(?:i|b|em|strong|sup|sub|mml:[a-z]+)\b[^>]*>", "", md)   # leaked <i>…</i> from titles
    md = _fix_captions(md, dict(figinfo))
    hm = re.search(r"^#\s+(.+)$", md, re.M)
    title = (hm.group(1).strip() if hm else "") or topic
    # SUBSTANCE FLOOR: never ship a bodyless / references-only stub as a paper.
    if body_chars >= 1200 and n_sec >= 3:
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
