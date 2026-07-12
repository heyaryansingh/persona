"""Self-critique + iterate (v7) — the persona checks its own work and revises it.

After a report is written, `critique()` reads it, judges it against the question (does it ANSWER the
question? is every claim grounded, not hand-waved? is it honest about established-vs-open? what are the
concrete gaps/errors?), writes a `critique.md` into the investigation folder — the self-check as a
DOCUMENT — and, if the report is weak and budget allows, REWRITES it to address the specific issues and
recompiles. This is the iterate loop: continually check the work, don't emit it once and move on.
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone

from .. import config
from ..budget import budget
from ..context import get_persona
from ..events import log

_CRIT_SYS = (
    "You are a rigorous, skeptical peer reviewer. Given a research QUESTION and a draft REPORT, judge "
    "the report honestly: (1) does it actually ANSWER the question, or dance around it? (2) is every "
    "substantive claim grounded in cited evidence, or hand-waved? (3) is it honest about what is "
    "established vs open (no overclaiming)? (4) what are the SPECIFIC weaknesses, errors, unsupported "
    "leaps, or missing pieces — cite sections. Write a concise structured review (Strengths, then "
    "Issues as a numbered list of concrete, actionable problems). End with EXACTLY one final line: "
    "'VERDICT: solid' if it is a defensible answer, or 'VERDICT: revise' if the issues are material.")

_REVISE_SYS = (
    "You revise a research report to address a peer review. Keep what is correct; fix each issue the "
    "review raises. Stay honest — do NOT fabricate evidence or a proof to paper over a gap; if the "
    "evidence isn't there, say so explicitly. Output ONLY the complete revised report in Markdown, "
    "starting with '# '. Preserve citations [n], $…$ math, and any ![caption](figure.png) image.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(t: str) -> str:
    return (re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")[:48]) or "report"


def _cost(u) -> float:
    return (u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000


def critique(question: str, *, investigation_id: str = "", parent_id=None) -> dict:
    """Review the latest report for `question`; write critique.md; revise once if weak. Returns
    {ok, verdict, revised, critique_doc}."""
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    p = get_persona()
    slug = _slug(question)
    # the report to check = the newest compiled paper.md for this question
    cands = sorted(p.paths.projects_dir.glob(f"paper-{slug}*/*/paper.md"),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    if not cands:
        return {"ok": False, "reason": "no-report-to-critique"}
    report_path = cands[0]
    report_md = report_path.read_text(encoding="utf-8")

    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=2000, system=_CRIT_SYS,
        messages=[{"role": "user", "content": f"QUESTION:\n{question}\n\nREPORT:\n{report_md[:12000]}"}])
    budget().add(_cost(resp.usage))
    review = "".join(b.text for b in resp.content if b.type == "text").strip()
    verdict = "revise" if re.search(r"VERDICT:\s*revise", review, re.I) else "solid"

    # write the self-check as a document, into the investigation folder if we know it
    from ..research.investigation import Investigation
    inv = Investigation.load(investigation_id) if investigation_id else None
    crit_dir = inv.folder if inv else report_path.parent
    crit_dir.mkdir(parents=True, exist_ok=True)
    (crit_dir / "critique.md").write_text(
        f"# self-critique — {question}\n\n_{_now()} · verdict: **{verdict}**_\n\n{review}\n",
        encoding="utf-8")

    revised = False
    if verdict == "revise" and budget().can_spend():
        r2 = client.messages.create(model=config.MODEL_WORKER, max_tokens=8000, system=_REVISE_SYS,
            messages=[{"role": "user", "content":
                       f"QUESTION:\n{question}\n\nPEER REVIEW:\n{review}\n\nCURRENT REPORT:\n{report_md}"}])
        budget().add(_cost(r2.usage))
        from ..deliverables.document import sanitize_markdown, compile_source
        new_md = sanitize_markdown("".join(b.text for b in r2.content if b.type == "text"))
        if len(new_md) >= 300 and new_md.lstrip().startswith("#"):
            report_path.write_text(new_md, encoding="utf-8")
            hm = re.search(r"^#\s+(.+)$", new_md, re.M)
            title = (hm.group(1).strip() if hm else question)[:80]
            cr = compile_source(new_md, "md", report_path.parent, title=title)
            if cr.get("ok"):
                # replace the shipped deliverable PDF with the revised one
                p.paths.deliverables_dir.mkdir(parents=True, exist_ok=True)
                for old in p.paths.deliverables_dir.glob(f"paper-{slug}*.pdf"):
                    dst = old
                    break
                else:
                    dst = p.paths.deliverables_dir / f"paper-{slug}-revised.pdf"
                shutil.copy2(report_path.parent / "main.pdf", dst)
                if inv:
                    shutil.copy2(report_path.parent / "main.pdf", inv.folder / "report.pdf")
                revised = True

    log().emit("artifact", f"self-critiqued “{question[:50]}” — {verdict}"
               + (" · revised the report" if revised else ""), actor="critic",
               parent_id=parent_id, file="critique.md")
    return {"ok": True, "verdict": verdict, "revised": revised, "critique_doc": "critique.md"}
