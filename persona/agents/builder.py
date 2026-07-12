"""Builders (v6 P4) — the swarm doesn't only READ, it BUILDS.

Real, browsable artifacts, each grounded in the persona's own knowledge (its beliefs + synthesis
notes) and provenance-pinned (a manifest with the sandbox image digest + input hashes + cost):
  - build_visual(kind): a figure/diagram or generative data-art — matplotlib code RUN in the
    offline sandbox → results/*.png.
  - build_page: a self-contained interactive HTML page explaining/visualizing a topic.
  - build_code: a small runnable Python tool/script (optionally executed to verify it runs).

Everything is confined to persona-workspace/ (workspace-jailed), no network inside the sandbox, no
irreversible outward action. Outputs surface in the file browser and the live stream.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .. import config
from ..budget import budget
from ..context import get_persona
from ..events import log
from ..tools import sandbox


def _slug(q: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (q or "").lower()).strip("-")[:48] or "artifact"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _grounding(topic: str, kg=None, k: int = 3) -> tuple[str, list]:
    """Pull the persona's relevant beliefs + notes so the artifact is grounded, not invented."""
    p = get_persona()
    beliefs, ents = [], []
    if kg is not None:
        try:
            for b in kg.beliefs(min_independent=1, limit=40):
                beliefs.append(f"- {b['subject']} [{b['effect_sign']}] {b['object']} "
                               f"({b['independent_sources']} labs, p={b['confidence']:.2f})")
                ents += [b["subject"], b["object"]]
        except Exception:
            pass
    notes = []
    try:
        for h in p.vectors.search(topic, k=k):
            f = p.paths.notes_dir / f"{h.get('slug', '')}.md"
            if f.exists():
                notes.append(f.read_text(encoding="utf-8")[:1400])
    except Exception:
        pass
    ctx = ""
    if beliefs:
        ctx += "MY BELIEFS (grounded in evidence):\n" + "\n".join(beliefs[:30]) + "\n\n"
    if notes:
        ctx += "MY SYNTHESIS NOTES:\n" + "\n\n---\n\n".join(notes)
    return (ctx or "(no grounding yet — keep it schematic and honest)"), list(dict.fromkeys(ents))[:12]


def _record_experiment(kind: str, title: str, ents: list, artifact: str, meta: dict, kg=None) -> None:
    """Make the artifact a first-class node in the graph (walk belief -> experiment -> result)."""
    if kg is None:
        return
    try:
        exp_id = "exp_" + hashlib.sha1(f"{kind}|{title}|{artifact}".encode()).hexdigest()[:12]
        kg.add_experiment(exp_id, title, kind, ents, artifact=artifact, meta=meta)
    except Exception:
        pass


def _manifest(project: Path, extra: dict) -> None:
    def _hashes(d):
        return {f.name: hashlib.sha256(f.read_bytes()).hexdigest()[:16]
                for f in sorted(d.glob("*")) if f.is_file()} if d.exists() else {}
    m = {"at": _now(), "sandbox_image": sandbox.IMAGE, "sandbox_image_digest": sandbox.image_digest(),
         "results": _hashes(project / "results"), **extra}
    (project / "manifest.json").write_text(json.dumps(m, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- visual (diagram / art)
_VIS_SYS = ("You write ONE self-contained Python matplotlib script that produces a single, clear, "
            "publication-quality figure. Save it to /work/results/figure.png at 150 dpi. "
            "LEGIBILITY IS MANDATORY and the figure will be rejected if text is unreadable: use fontsize "
            ">= 11 for every label/annotation, set constrained_layout=True (or call fig.tight_layout()), "
            "leave generous margins, and NEVER let text overlap other text, boxes, arrows, or run off the "
            "figure edge — if labels would collide, enlarge the figure (figsize) or shorten the text. Do "
            "not print a label on top of a box border or an arrow. Keep every box's text INSIDE the box. "
            "No network, no external files — synthesize any needed data in-code from the facts given. Use "
            "only numpy/pandas/matplotlib. Return ONLY the code via the tool.")


def build_visual(kind: str, topic: str, *, parent_id=None, kg=None, max_attempts: int = 2) -> dict:
    """kind='diagram' (an explanatory figure) or 'art' (a generative data-art piece from its mind).
    max_attempts>1 enables a render-retry (feed sandbox stderr back); callers that fan out many figures
    under a task lease pass max_attempts=1 to bound latency."""
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    if not sandbox.image_ready():
        return {"ok": False, "reason": "sandbox-image-missing"}
    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    ctx, ents = _grounding(topic, kg)
    intent = ("an explanatory scientific diagram (boxes/arrows/mechanism or a clean data plot) that "
              "makes the relationships legible" if kind == "diagram" else
              "a striking piece of GENERATIVE DATA-ART that renders the shape/structure of this "
              "knowledge aesthetically (still driven by the real relationships, but beautiful)")
    tool = {"name": "write_fig", "description": "Write the matplotlib script.",
            "input_schema": {"type": "object", "properties": {
                "title": {"type": "string"}, "code": {"type": "string"}}, "required": ["title", "code"]}}
    project = get_persona().paths.projects_dir / f"{kind}-{_slug(topic)}"
    (project / "results").mkdir(parents=True, exist_ok=True)
    png = project / "results" / "figure.png"
    messages = [{"role": "user", "content": f"Topic: {topic}\n\nMake {intent}.\n\n{ctx}\n\n"
                 f"Write the script; save the figure to /work/results/figure.png."}]
    # render-retry: LLM matplotlib for abstract topics errors ~half the time; feed the sandbox stderr
    # back and let it fix the code (one retry). This is why 6/10 papers had no figure.
    title, cost = topic[:120], 0.0
    for attempt in range(max(1, max_attempts)):
        if not budget().can_spend():
            break
        png.unlink(missing_ok=True)
        resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=8000, system=_VIS_SYS,
                                      tools=[tool], tool_choice={"type": "tool", "name": "write_fig"},
                                      messages=messages)
        u = resp.usage
        cost += (u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000
        budget().add((u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000)
        tu = next((b for b in resp.content if b.type == "tool_use"), None)
        if not tu or not tu.input.get("code"):
            continue
        title, code = tu.input.get("title", topic)[:120], tu.input["code"]
        (project / "figure.py").write_text(code, encoding="utf-8")
        r = sandbox.run_python(code, project, timeout=90)
        if png.exists():
            break
        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tu.id,
            "content": "figure.png was NOT created. Fix the script and call write_fig again.\nstderr:\n"
                       + (r.get("stderr") or "")[-1500:]}]})
    if not png.exists():
        log().emit("error", f"{kind} “{title}” did not render", actor="builder", parent_id=parent_id)
        return {"ok": False, "reason": "no-figure"}
    rel = f"projects/{project.name}/results/figure.png"
    _manifest(project, {"kind": kind, "title": title, "topic": topic, "cost_usd": round(cost, 4),
                        "code_sha256": hashlib.sha256(code.encode()).hexdigest()[:16]})
    _record_experiment(kind, title, ents, rel, {"cost_usd": round(cost, 4)}, kg)
    log().emit("artifact", f"built a {kind}: “{title}” → {rel}", actor="builder",
               parent_id=parent_id, file=rel, kind=kind)
    return {"ok": True, "kind": kind, "title": title, "artifact": rel}


# ---------------------------------------------------------------- interactive page (HTML)
_PAGE_SYS = ("You write ONE complete, self-contained HTML page (inline CSS + vanilla JS, NO external "
             "resources, no CDNs) that clearly explains and VISUALIZES a topic from the given research "
             "notes/beliefs. Make it genuinely interactive and legible (a small explorable explainer). "
             "Ground every claim in the provided material; do not invent findings. Return only the HTML.")


def build_page(topic: str, *, parent_id=None, kg=None) -> dict:
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    ctx, ents = _grounding(topic, kg)
    tool = {"name": "write_page", "description": "Write the self-contained HTML page.",
            "input_schema": {"type": "object", "properties": {
                "title": {"type": "string"}, "html": {"type": "string"}}, "required": ["title", "html"]}}
    resp = client.messages.create(
        model=config.MODEL_WORKER, max_tokens=16000, system=_PAGE_SYS, tools=[tool],
        tool_choice={"type": "tool", "name": "write_page"},
        messages=[{"role": "user", "content": f"Topic: {topic}\n\n{ctx}\n\nWrite the interactive page."}])
    u = resp.usage
    cost = (u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000
    budget().add(cost)
    out = next((b.input for b in resp.content if b.type == "tool_use"), {})
    html = out.get("html", "")
    if "<" not in html:
        return {"ok": False, "reason": "no-html"}
    title = out.get("title", topic)[:120]
    dst = get_persona().paths.deliverables_dir / f"page-{_slug(topic)}.html"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(html, encoding="utf-8")
    rel = f"deliverables/{dst.name}"
    _record_experiment("page", title, ents, rel, {"cost_usd": round(cost, 4)}, kg)
    log().emit("artifact", f"built an interactive page: “{title}” → {rel}", actor="builder",
               parent_id=parent_id, file=rel, kind="page")
    return {"ok": True, "kind": "page", "title": title, "artifact": rel}


# ---------------------------------------------------------------- code / small tool
_CODE_SYS = ("You write ONE small, correct, self-contained Python script/tool related to the topic — "
             "something genuinely useful (a calculator, a simulation, a small analysis/util). It must "
             "run with the standard library + numpy/pandas if needed, print a clear demonstration when "
             "run, and include a one-line docstring. Return only the code.")


def build_code(topic: str, *, parent_id=None, kg=None) -> dict:
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    ctx, ents = _grounding(topic, kg)
    tool = {"name": "write_code", "description": "Write the script.",
            "input_schema": {"type": "object", "properties": {
                "name": {"type": "string", "description": "a short module name, e.g. gut_axis_sim"},
                "code": {"type": "string"}}, "required": ["name", "code"]}}
    resp = client.messages.create(
        model=config.MODEL_WORKER, max_tokens=8000, system=_CODE_SYS, tools=[tool],
        tool_choice={"type": "tool", "name": "write_code"},
        messages=[{"role": "user", "content": f"Topic: {topic}\n\n{ctx}\n\nWrite the tool."}])
    u = resp.usage
    cost = (u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000
    budget().add(cost)
    out = next((b.input for b in resp.content if b.type == "tool_use"), {})
    if not out.get("code"):
        return {"ok": False, "reason": "no-code"}
    name = _slug(out.get("name", topic))
    project = get_persona().paths.projects_dir / f"code-{_slug(topic)}"
    (project / "results").mkdir(parents=True, exist_ok=True)
    script = project / f"{name}.py"
    script.write_text(out["code"], encoding="utf-8")
    ran = None
    if sandbox.image_ready():                       # verify it actually runs
        r = sandbox.run_python(out["code"], project, timeout=60)
        ran = {"exit_code": r["exit_code"], "stdout": (r.get("stdout") or "")[-600:]}
        (project / "results" / "run.txt").write_text(
            (r.get("stdout") or "") + "\n---STDERR---\n" + (r.get("stderr") or ""), encoding="utf-8")
    (project / "README.md").write_text(f"# {name}\n\n_generated {_now()} on: {topic}_\n\n"
                                       f"Run: `python {name}.py`\n", encoding="utf-8")
    rel = f"projects/{project.name}/{name}.py"
    _manifest(project, {"kind": "code", "name": name, "topic": topic, "cost_usd": round(cost, 4),
                        "runs": bool(ran and ran["exit_code"] == 0)})
    _record_experiment("code", name, ents, rel, {"cost_usd": round(cost, 4)}, kg)
    log().emit("artifact", f"wrote code: {name}.py"
               + (" (runs ✓)" if ran and ran["exit_code"] == 0 else "") + f" → {rel}",
               actor="builder", parent_id=parent_id, file=rel, kind="code")
    return {"ok": True, "kind": "code", "title": name, "artifact": rel,
            "runs": bool(ran and ran["exit_code"] == 0)}
