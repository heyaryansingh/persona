"""The analyst (v4 P5) — the agent that does REAL WORK: plans, fetches real data, writes and RUNS
code in the sandbox, interprets results, and writes a real artifact (a report + a project).

A bounded tool-use loop (Sonnet). Tools: write_file (into its project), fetch_dataset (allowlisted
open-data hosts), run_python (sandboxed, no-network compute), finish (emit the report). Everything
is confined to persona-workspace/; the only outputs are files it writes and a draft report — no
irreversible outward actions. This is "do real research, write real things", closing the loop from
a question to a computed, written result.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .. import config
from ..context import get_persona
from ..budget import budget
from ..events import log
from ..tools import sandbox, datasets


def _slug(q: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")[:48]
    return s or "investigation"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


TOOLS = [
    {"name": "write_file", "description": "Write a text file inside the project (e.g. a script, notes).",
     "input_schema": {"type": "object", "properties": {
         "path": {"type": "string", "description": "relative path within the project, e.g. analysis/step1.py"},
         "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "fetch_dataset", "description": "Download a real dataset from an open-data host into "
     "the project's data/ folder (available to run_python at /work/data/). Allowlisted hosts only.",
     "input_schema": {"type": "object", "properties": {
         "url": {"type": "string"}, "filename": {"type": "string"}}, "required": ["url"]}},
    {"name": "run_python", "description": "Run Python in a sandbox (numpy/pandas/scipy/sklearn/"
     "matplotlib/statsmodels available; NO network). The project is mounted at /work; datasets at "
     "/work/data. Write outputs to /work/results/. Returns stdout/stderr.",
     "input_schema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}},
    {"name": "finish", "description": "Finish the investigation with a written report.",
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"}, "report_markdown": {"type": "string",
         "description": "the finding as a concise report: question, what you did, result, caveats"}},
         "required": ["title", "report_markdown"]}},
]

_SYSTEM = ("You are a rigorous research analyst. Given a question, do REAL work: plan briefly, fetch "
           "real data if useful (open-data hosts only), write and RUN Python in the sandbox to "
           "actually compute an answer (don't just reason — verify numerically), then finish with a "
           "concise, honest report including caveats. Prefer a small, decisive analysis over a sprawling "
           "one. Keep code self-contained and print results. You have at most ~7 tool calls, so be "
           "efficient. If data can't be found, do a rigorous self-contained computational demonstration "
           "instead. Always call run_python at least once before finish.")


def _safe_join(project: Path, rel: str) -> Path | None:
    p = (project / rel).resolve()
    return p if str(p).startswith(str(project.resolve())) else None


def investigate(question: str, *, parent_id=None, max_turns: int = 8) -> dict:
    if not config.have_key():
        return {"ok": False, "reason": "no-key"}
    if not budget().can_spend():
        return {"ok": False, "reason": "budget"}
    if not sandbox.image_ready():
        return {"ok": False, "reason": "sandbox-image-missing"}
    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    project = get_persona().paths.projects_dir / _slug(question)
    (project / "results").mkdir(parents=True, exist_ok=True)
    (project / "data").mkdir(parents=True, exist_ok=True)
    (project / "plan.md").write_text(f"# {question}\n\n_started {_now()}_\n", encoding="utf-8")
    logf = project / "log.md"
    logf.write_text(f"# log — {question}\n\n", encoding="utf-8")

    def _tool(name, inp) -> dict:
        try:
            if name == "write_file":
                p = _safe_join(project, inp["path"])
                if p is None:
                    return {"ok": False, "error": "path escapes project"}
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(inp["content"], encoding="utf-8")
                return {"ok": True, "wrote": inp["path"]}
            if name == "fetch_dataset":
                r = datasets.fetch(inp["url"], project / "data", inp.get("filename"))
                log().emit("tool", f"fetch dataset {inp['url'][:70]} → "
                           f"{'ok '+str(r.get('bytes',0))+'B' if r.get('ok') else 'FAIL: '+r.get('error','')}",
                           actor="analyst", parent_id=parent_id)
                return r
            if name == "run_python":
                r = sandbox.run_python(inp["code"], project, timeout=90)
                log().emit("tool", f"ran code in sandbox → exit {r['exit_code']}"
                           + (" (timeout)" if r.get("timeout") else ""), actor="analyst",
                           parent_id=parent_id)
                return r
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}
        return {"ok": False, "error": "unknown tool"}

    messages = [{"role": "user", "content": f"Question to investigate:\n\n{question}\n\n"
                 f"Project dir is /work (mounted); write outputs to /work/results/."}]
    ran_code, finished = False, None
    for turn in range(max_turns):
        if not budget().can_spend():
            break
        resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=4096, system=_SYSTEM,
                                      tools=TOOLS, messages=messages)
        u = resp.usage
        budget().add((u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000)   # Sonnet $/Mtok
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                if b.name == "finish":
                    finished = b.input
                    break
                out = _tool(b.name, b.input)
                if b.name == "run_python":
                    ran_code = True
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": json.dumps(out)[:6000]})
        if finished:
            break
        if not results:
            break
        messages.append({"role": "user", "content": results})

    if not finished:
        return {"ok": False, "reason": "no-finish", "project": _slug(question), "ran_code": ran_code}
    title = finished.get("title", question)[:120]
    report = finished.get("report_markdown", "")
    draft = get_persona().paths.drafts_dir / f"{_slug(question)}.md"
    get_persona().paths.drafts_dir.mkdir(parents=True, exist_ok=True)
    draft.write_text(f"# {title}\n\n_{_now()} · question: {question}_\n\n{report}\n", encoding="utf-8")
    (project / "REPORT.md").write_text(f"# {title}\n\n{report}\n", encoding="utf-8")
    log().emit("artifact", f"wrote a report: “{title}” (real analysis{' with code' if ran_code else ''})",
               actor="analyst", parent_id=parent_id, draft=str(draft.name), ran_code=ran_code)
    return {"ok": True, "title": title, "draft": str(draft), "project": _slug(question),
            "ran_code": ran_code}
