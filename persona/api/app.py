"""FastAPI app (v5 P3) — multi-persona: a gallery of fully-isolated researcher minds.

Every persona has its own workspace, graph, events, budget, and daemon. Endpoints are routed by
persona_id and set the current-persona context so the shared code (log/get_kg/budget/selfmind)
resolves to the right mind. `GET /` serves the gallery UI.

Run: python -m persona   (or: uvicorn persona.api.app:app --port 8137)
"""
from __future__ import annotations

import asyncio
import json
import mimetypes
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse

from .. import config, context, selfmind
from ..manager import manager

app = FastAPI(title="Persona v5", version="5.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_STATIC = Path(__file__).resolve().parent / "static"


@app.on_event("startup")
async def _startup():
    asyncio.create_task(_supervisor())    # start/resume seeded personas' daemons in the loop


async def _supervisor():
    """Ensure every SEEDED persona has a running daemon (resume on boot + start newly-seeded)."""
    while True:
        try:
            for p in manager().list():
                if p.is_seeded() and not p.is_halted():   # HALTED personas stay down until resumed
                    manager().start(p)      # no-op if already running
        except Exception:
            pass
        await asyncio.sleep(3)


@app.on_event("shutdown")
async def _shutdown():
    manager().stop_all()


def _p(pid: str):
    p = manager().get(pid)
    if p is None:
        raise HTTPException(status_code=404, detail=f"no persona {pid!r}")
    return p


# --------------------------------------------------------------- gallery
@app.get("/api/personas")
def personas():
    return {"personas": [p.to_card() for p in manager().list()]}


@app.post("/api/personas")
def create_persona(payload: dict):
    interests = payload.get("interests") or []
    if isinstance(interests, str):
        interests = [s.strip() for s in interests.split(",") if s.strip()]
    p = manager().create(payload["name"], interests=interests,
                         budget_usd=payload.get("budget_usd"))
    # create() already seeds when interests are given; the startup _supervisor() loop starts the
    # daemon from WITHIN the event loop. Don't call manager().start() here — this is a sync request
    # thread with no running loop, so asyncio.create_task() would raise (a 500 with no UI feedback).
    return p.to_card()


@app.post("/api/persona/{pid}/seed")
def seed(pid: str, payload: dict):
    interests = payload.get("interests") or []
    if isinstance(interests, str):
        interests = [s.strip() for s in interests.split(",") if s.strip()]
    fresh = manager().seed(pid, interests)
    with context.use(_p(pid)):
        from ..events import log
        log().emit("seed", f"{'born' if fresh else 're-seeded'}: {', '.join(interests)}", actor="human")
    return {"applied": True, "fresh_birth": fresh}


@app.post("/api/persona/{pid}/reset")
def reset(pid: str):
    with context.use(_p(pid)):
        selfmind.reset()
    return {"reset": True}


# --------------------------------------------------------------- control plane (v6 P0)
@app.post("/api/persona/{pid}/pause")
def pause(pid: str):
    p = _p(pid)
    p.set_run_state("PAUSED")
    with context.use(p):
        from ..events import log
        log().emit("control", "paused by human — no new work or spend until resumed", actor="human")
    return {"run_state": "PAUSED"}


@app.post("/api/persona/{pid}/resume")
def resume(pid: str):
    p = _p(pid)
    p.set_run_state("RUNNING")   # the startup supervisor restarts a halted daemon within ~3s
    with context.use(p):
        from ..events import log
        log().emit("control", "resumed by human", actor="human")
    return {"run_state": "RUNNING"}


@app.post("/api/persona/{pid}/halt")
def halt(pid: str):
    p = _p(pid)
    p.set_run_state("HALTED")
    manager().stop(pid)          # stop the daemon; supervisor won't restart while HALTED
    with context.use(p):
        from ..events import log
        log().emit("control", "halted by human — daemon stopped", actor="human")
    return {"run_state": "HALTED"}


@app.get("/api/persona/{pid}/spend")
def spend(pid: str):
    p = _p(pid)
    b = p.budget
    with context.use(p):
        from ..events import log
        recent = [e for e in log().since(max(0, log().latest_id() - 400))
                  if e.get("type") == "cost"][-12:]
    return {"spent_today": round(b.spent_today(), 4), "cap_usd": round(p.cap_usd, 2),
            "remaining": round(b.remaining(), 4), "run_state": p.run_state(),
            "recent_costs": [{"task": e["data"].get("task_type"), "usd": e["data"].get("cost"),
                              "at": e["ts"]} for e in recent]}


@app.post("/api/persona/{pid}/budget")
def set_budget(pid: str, payload: dict):
    p = _p(pid)
    p.set_cap(float(payload["cap_usd"]))
    return {"cap_usd": round(p.cap_usd, 2), "remaining": round(p.budget.remaining(), 4)}


@app.post("/api/persona/{pid}/delete")
def delete(pid: str, payload: dict = None):
    return {"deleted": manager().delete(pid, wipe=(payload or {}).get("wipe", False))}


# --------------------------------------------------------------- per-persona views
@app.get("/api/persona/{pid}/status")
def status(pid: str):
    p = _p(pid)
    d = manager()._daemons.get(pid)
    with context.use(p):
        from ..events import log
        return {**p.to_card(), "workers": (d.n_workers if d else 0),
                "queue": (d.queue.counts() if d else {}), "latest_event": log().latest_id(),
                "have_key": config.have_key()}


@app.get("/api/persona/{pid}/events")
def events(pid: str, after: int = 0, limit: int = 500):
    with context.use(_p(pid)):
        from ..events import log
        return {"events": log().since(after, limit), "latest": log().latest_id()}


@app.get("/api/persona/{pid}/self")
def get_self(pid: str):
    with context.use(_p(pid)):
        return {"seeded": selfmind.is_seeded(), "interests": selfmind.interests(),
                "open_questions": selfmind.open_questions(), "files": selfmind.read_self()}


@app.get("/api/persona/{pid}/kg")
def kg(pid: str):
    p = _p(pid)
    with context.use(p):
        from ..memory.membrane import get_kg
        g = get_kg()
        if g is None:
            return {"available": False}
        return {"available": True, "stats": g.stats(), "beliefs": g.beliefs(min_independent=1),
                "contradictions": g.contradictions(), "graph": g.graph_snapshot()}


# --------------------------------------------------------------- navigable graph (v6 P3)
@app.get("/api/persona/{pid}/graph/overview")
def graph_overview(pid: str, limit: int = 60):
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        return g.overview(limit) if g else {"nodes": [], "edges": []}


@app.get("/api/persona/{pid}/graph/neighbors")
def graph_neighbors(pid: str, node: str, limit: int = 40):
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        return g.neighbors(node, limit) if g else {"nodes": [], "edges": []}


@app.get("/api/persona/{pid}/graph/node")
def graph_node(pid: str, node: str):
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        return g.node(node) if g else {}


@app.get("/api/persona/{pid}/graph/search")
def graph_search(pid: str, q: str):
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        return {"results": g.search(q) if g else []}


@app.get("/api/persona/{pid}/provenance/{claim_id}")
def provenance(pid: str, claim_id: str):
    """The defensible chain: belief → claim → every supporting source + verbatim quote + DOI/URL."""
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        return g.provenance(claim_id) if g else {}


@app.get("/api/persona/{pid}/history/{claim_id}")
def history(pid: str, claim_id: str):
    p = _p(pid)
    return {"series": p.history.series(claim_id)}


@app.get("/api/persona/{pid}/inbox")
def inbox(pid: str):
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        return {"available": g is not None, "items": (g.contradictions(limit=50) if g else [])}


@app.post("/api/persona/{pid}/inbox/resolve")
def inbox_resolve(pid: str, payload: dict):
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        from ..events import log
        g = get_kg()
        if g is None:
            return {"ok": False}
        res = g.human_resolve(payload["claim_id"], bool(payload.get("truth", True)))
        if res.get("ok"):
            log().emit("escalate", f"human anchored {res['subject']} → {res['object']}", actor="human")
        return res


@app.get("/api/persona/{pid}/synthesis")
def synthesis(pid: str):
    """The persona's cited synthesis notes — what it has UNDERSTOOD per subtopic."""
    p = _p(pid)
    nd = p.paths.notes_dir
    notes = []
    if nd.exists():
        for f in sorted(nd.glob("*.md"), key=lambda x: -x.stat().st_mtime):
            first = f.read_text(encoding="utf-8").splitlines()
            title = next((l[2:] for l in first if l.startswith("# ")), f.stem)
            notes.append({"slug": f.stem, "title": title})
    return {"notes": notes}


@app.post("/api/persona/{pid}/deliver")
def deliver(pid: str, payload: dict):
    """Ask a persona to produce a deliverable now: a cited review or a LaTeX->PDF paper on a topic."""
    p = _p(pid)
    d = manager()._daemons.get(pid)
    kind = payload.get("kind", "review")
    topic = payload.get("topic", "")
    if d is None:
        return {"ok": False, "reason": "daemon not running (seed the persona first)"}
    tid = d.queue.enqueue("paper" if kind == "paper" else "review", priority=2,
                          params={"topic": topic})
    return {"ok": True, "queued": kind, "task": tid}


# --------------------------------------------------------------- knowledge transfer (v6 P5)
@app.get("/api/persona/{pid}/topic/digest")
def topic_digest(pid: str, q: str):
    """A digestible, cited briefing of everything the persona knows on a topic + a subgraph +
    an evolution timeline — the 'transfer the knowledge, not just next steps' surface."""
    p = _p(pid)
    with context.use(p):
        from ..memory.membrane import get_kg
        from ..agents.knowledge import topic_digest as _td
        return _td(q, get_kg(), p.history)


@app.get("/api/persona/{pid}/topic/evolution")
def topic_evolution(pid: str, q: str):
    """How belief/consensus on a topic moved over time (per-claim confidence + support series)."""
    p = _p(pid)
    with context.use(p):
        from ..memory.membrane import get_kg
        g = get_kg()
        if g is None:
            return {"series": []}
        ents = [n["label"] for n in g.search(q, 25) if n["type"] == "entity"]
        claims = g.claims_about(ents, 12) if ents else []
        out = []
        for c in claims:
            s = p.history.series(c["claim_id"])
            if len(s) >= 2:
                out.append({"claim_id": c["claim_id"],
                            "text": f"{c['subject']} [{c['effect_sign']}] {c['object']}", "series": s})
        return {"topic": q, "series": out}


@app.get("/api/persona/{pid}/graph/subgraph")
def graph_subgraph(pid: str, q: str):
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        if g is None:
            return {"nodes": [], "edges": []}
        ents = [n["label"] for n in g.search(q, 40) if n["type"] == "entity"]
        return g.subgraph(ents)


@app.post("/api/persona/{pid}/goal")
def goal(pid: str, payload: dict):
    """Directed mode: hand the persona a real problem/question. It pursues it (reads + a real
    computational investigation) as high-priority work and returns a cited deliverable — without
    stopping its own research, and without rewriting its durable self."""
    p = _p(pid)
    d = manager()._daemons.get(pid)
    g = (payload.get("goal") or payload.get("text") or "").strip()
    if not g:
        return {"ok": False, "reason": "empty"}
    if d is None:
        return {"ok": False, "reason": "daemon not running (seed/resume the persona)"}
    with context.use(p):
        from ..events import log
        log().emit("say", f"[goal] {g}", actor="human")
    d.queue.enqueue("scout", priority=1, params={"interest": g})
    tid = d.queue.enqueue("investigate", priority=1, params={"question": g})
    return {"ok": True, "task": tid, "goal": g}


@app.post("/api/persona/{pid}/mywork")
async def mywork(pid: str, file: UploadFile = File(...), kind: str = "draft"):
    """Upload YOUR paper/draft/notes -> the persona extracts your claims and cross-checks each against
    everything it has read (what supports it, what contradicts it, with quotes+DOIs)."""
    p = _p(pid)
    up = p.paths.uploads_dir
    up.mkdir(parents=True, exist_ok=True)
    name = "".join(c for c in (file.filename or "doc") if c.isalnum() or c in "._- ")[:120] or "doc"
    (up / name).write_bytes(await file.read())
    with context.use(p):
        from ..memory.membrane import get_kg
        from ..agents.mywork import ingest
        return ingest(f"uploads/{name}", kind, get_kg())


@app.post("/api/persona/{pid}/ask")
def ask(pid: str, payload: dict):
    """Ask the persona's knowledge graph a question in plain English — answered with citations."""
    p = _p(pid)
    q = (payload.get("q") or payload.get("question") or "").strip()
    if not q:
        return {"ok": False, "reason": "empty"}
    with context.use(p):
        from ..memory.membrane import get_kg
        from ..agents.knowledge import ask_graph
        return ask_graph(q, get_kg())


# --------------------------------------------------------------- builders + free mind (v6 P4)
@app.post("/api/persona/{pid}/build")
def build_ep(pid: str, payload: dict):
    """Ask the persona to build a real artifact now: a diagram, generative art, an interactive page,
    or a small code tool — grounded in its knowledge, browsable in files/deliverables when done."""
    p = _p(pid)
    d = manager()._daemons.get(pid)
    kind = (payload.get("kind") or "diagram").strip()
    topic = (payload.get("topic") or "").strip()
    if not topic:
        return {"ok": False, "reason": "empty topic"}
    if kind not in ("diagram", "art", "page", "code"):
        return {"ok": False, "reason": f"unknown kind {kind}"}
    if d is None:
        return {"ok": False, "reason": "daemon not running (seed/resume the persona)"}
    tid = d.queue.enqueue("build", priority=3, params={"kind": kind, "topic": topic})
    return {"ok": True, "queued": kind, "task": tid}


@app.post("/api/persona/{pid}/freemove")
def freemove_ep(pid: str):
    """Let the persona choose its own next move (the free mind), one step, budget-gated."""
    d = manager()._daemons.get(pid)
    if d is None:
        return {"ok": False, "reason": "daemon not running (seed/resume the persona)"}
    tid = d.queue.enqueue("free_move", priority=2)
    return {"ok": True, "task": tid}


@app.get("/api/persona/{pid}/fieldmap")
def fieldmap(pid: str):
    """A navigable map through the field: subtopics → beliefs → contradictions → open-questions → papers."""
    p = _p(pid)
    with context.use(p):
        from ..memory.membrane import get_kg
        from ..synthesis import fieldmap as fm
        g = get_kg()
        if g is None:
            return {"n_subtopics": 0, "subtopics": []}
        return fm.build(g, p.paths.notes_dir)


@app.get("/api/persona/{pid}/note/{slug}")
def note(pid: str, slug: str):
    if "/" in slug or "\\" in slug:
        raise HTTPException(400, "bad slug")
    f = _p(pid).paths.notes_dir / f"{slug}.md"
    if not f.exists():
        raise HTTPException(404, "not found")
    return {"slug": slug, "content": f.read_text(encoding="utf-8")}


# --------------------------------------------------------------- conversation / steer (v6 P2)
@app.post("/api/persona/{pid}/say")
def say(pid: str, payload: dict):
    """Talk to the persona while it works. It replies (grounded in its self+graph), remembers a
    standing directive if you steer it, and starts reading any topics you point it at — without
    stopping. Runs synchronously so it replies immediately in any run-state."""
    p = _p(pid)
    text = (payload.get("text") or "").strip()
    if not text:
        return {"ok": False, "reason": "empty"}
    with context.use(p):
        from ..events import log
        from ..memory.membrane import get_kg
        from ..agents.converse import converse
        log().emit("say", text, actor="human")
        res = converse(text, get_kg())
    if res.get("ok") and res.get("focus_now"):     # act on steering: priority reads, but keep working
        q = p.queue()
        for topic in res["focus_now"]:
            q.enqueue("scout", priority=1, params={"interest": topic})
    return res


# --------------------------------------------------------------- file & artifact browser (v6 P1)
_TEXT_EXT = {".py", ".md", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".tex", ".log", ".yaml",
             ".yml", ".toml", ".ini", ".cfg", ".ipynb", ".r", ".sh", ".js", ".ts", ".html", ".css"}


@app.get("/api/persona/{pid}/files")
def files(pid: str):
    """The persona's workspace as a jailed recursive tree (dirs + files, sizes) — so every
    experiment, script, figure, dataset, and compiled deliverable it made is browsable."""
    p = _p(pid)
    root = p.paths.workspace.resolve()
    budget = [4000]

    def walk(d, depth):
        out = []
        try:
            entries = sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except Exception:
            return out
        for e in entries:
            if e.name.startswith(".") or budget[0] <= 0:
                continue
            budget[0] -= 1
            rel = str(e.relative_to(root)).replace("\\", "/")
            if e.is_dir():
                out.append({"name": e.name, "path": rel, "type": "dir",
                            "children": walk(e, depth + 1) if depth < 7 else []})
            else:
                try:
                    sz = e.stat().st_size
                except Exception:
                    sz = 0
                out.append({"name": e.name, "path": rel, "type": "file",
                            "ext": e.suffix.lower().lstrip("."), "size": sz})
        return out

    return {"root": p.name, "tree": walk(root, 0)}


@app.get("/api/persona/{pid}/file")
def get_file(pid: str, path: str):
    """Serve ONE workspace file inline with the right media type — PDF, code, image, CSV, md.
    Path-jailed to the persona workspace (traversal/symlink escape -> 400)."""
    p = _p(pid)
    try:
        target = p.paths.safe(path)
    except ValueError:
        raise HTTPException(400, "bad path")
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "not found")
    mt = mimetypes.guess_type(str(target))[0]
    if target.suffix.lower() in _TEXT_EXT:      # show code/notes in-browser, don't force download
        mt = "text/plain; charset=utf-8"
    return FileResponse(str(target), media_type=(mt or "application/octet-stream"))  # inline (no filename)


@app.post("/api/persona/{pid}/upload")
async def upload(pid: str, file: UploadFile = File(...)):
    """Upload a file into the persona's workspace (uploads/). P5 reads these into the 'my work' corpus."""
    p = _p(pid)
    up = p.paths.uploads_dir
    up.mkdir(parents=True, exist_ok=True)
    name = "".join(c for c in (file.filename or "upload.bin") if c.isalnum() or c in "._- ")[:120]
    dest = up / (name or "upload.bin")
    data = await file.read()
    dest.write_bytes(data)
    return {"ok": True, "path": f"uploads/{dest.name}", "bytes": len(data)}


@app.get("/api/persona/{pid}/workspace")
def workspace(pid: str):
    p = _p(pid)
    pa = p.paths
    drafts = sorted(x.name for x in pa.drafts_dir.glob("*.md")) if pa.drafts_dir.exists() else []
    deliv = sorted(x.name for x in pa.deliverables_dir.glob("*")) if pa.deliverables_dir.exists() else []
    projects = sorted(x.name for x in pa.projects_dir.glob("*") if x.is_dir()) if pa.projects_dir.exists() else []
    n_sources = len(list(pa.sources_dir.glob("*/meta.json"))) if pa.sources_dir.exists() else 0
    with context.use(p):
        return {"self": selfmind.read_self(), "drafts": drafts, "deliverables": deliv,
                "projects": projects, "n_sources": n_sources}


@app.get("/api/persona/{pid}/draft/{name}")
def draft(pid: str, name: str):
    if "/" in name or "\\" in name or not name.endswith(".md"):
        raise HTTPException(400, "bad name")
    p = _p(pid)
    f = p.paths.drafts_dir / name
    if not f.exists():
        f = p.paths.deliverables_dir / name
    if not f.exists():
        raise HTTPException(404, "not found")
    return {"name": name, "content": f.read_text(encoding="utf-8")}


@app.post("/api/persona/{pid}/read_url")
def read_url(pid: str, payload: dict):
    p = _p(pid)
    d = manager()._daemons.get(pid)
    if d is None:
        return {"ok": False, "reason": "daemon not running"}
    tid = d.queue.enqueue("read_url", priority=2,
                          params={"url": payload["url"], "interest": payload.get("interest", "web")})
    return {"ok": True, "task": tid}


@app.get("/api/persona/{pid}/stream")
async def stream(pid: str):
    p = _p(pid)

    async def gen():
        with context.use(p):
            from ..events import log
            seen = max(0, log().latest_id() - 80)
            while True:
                evs = log().since(seen)
                if evs:
                    for e in evs:
                        yield f"data: {json.dumps(e)}\n\n"
                    seen = evs[-1]["id"]
                else:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.4)
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/")
def root():
    idx = _STATIC / "index.html"
    return FileResponse(str(idx)) if idx.exists() else {"service": "Persona v5", "hint": "UI missing"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8137)
