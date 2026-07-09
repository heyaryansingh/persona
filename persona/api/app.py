"""FastAPI app (v4) — starts the always-on daemon and streams its live thought to the UI.

Run: python -m persona   (or: uvicorn persona.api.app:app --port 8137)
The daemon runs as a startup background task in the same process (shared SQLite files).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse

from .. import config, selfmind
from ..events import log
from ..daemon.supervisor import Daemon

app = FastAPI(title="Persona v4", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_STATIC = Path(__file__).resolve().parent / "static"
_daemon: Daemon | None = None


@app.on_event("startup")
async def _startup():
    global _daemon
    config.ensure_workspace()
    _daemon = Daemon()
    asyncio.create_task(_daemon.run())          # never-idle loop begins immediately


@app.on_event("shutdown")
async def _shutdown():
    if _daemon:
        _daemon.stop()


@app.get("/api/status")
def status():
    st = _daemon.status() if _daemon else {"workers": 0}
    return {**st, "latest_event": log().latest_id(), "have_key": config.have_key()}


@app.get("/api/events")
def events(after: int = 0, limit: int = 500):
    return {"events": log().since(after, limit), "latest": log().latest_id()}


@app.get("/api/kg")
def kg():
    """Knowledge-graph stats + beliefs + contradictions + a snapshot for the graph view."""
    from ..memory.membrane import get_kg
    g = get_kg()
    if g is None:
        return {"available": False}
    return {"available": True, "stats": g.stats(), "beliefs": g.beliefs(min_independent=1),
            "contradictions": g.contradictions(), "graph": g.graph_snapshot()}


@app.get("/api/inbox")
def inbox():
    """Human-escalation inbox: contradictions the researcher wants a human to adjudicate."""
    from ..memory.membrane import get_kg
    g = get_kg()
    if g is None:
        return {"available": False, "items": []}
    return {"available": True, "items": g.contradictions(limit=50)}


@app.post("/api/inbox/resolve")
def inbox_resolve(payload: dict):
    """Human adjudicates: anchor the chosen side (protected from cheap evidence henceforth)."""
    from ..memory.membrane import get_kg
    g = get_kg()
    if g is None:
        return {"ok": False, "reason": "no-kg"}
    res = g.human_resolve(payload["claim_id"], bool(payload.get("truth", True)),
                          payload.get("provenance", "HUMAN_CONFIRMED"))
    if res.get("ok"):
        log().emit("escalate", f"human anchored: {res['subject']} → {res['object']} "
                   f"({'holds' if payload.get('truth', True) else 'refuted'})", actor="human")
    return res


@app.get("/api/self")
def get_self():
    return {"seeded": selfmind.is_seeded(), "interests": selfmind.interests(),
            "open_questions": selfmind.open_questions(), "files": selfmind.read_self()}


@app.get("/api/workspace")
def workspace():
    """The mind on disk: self files, drafts (reports), and projects."""
    drafts = sorted(p.name for p in config.DRAFTS_DIR.glob("*.md")) if config.DRAFTS_DIR.exists() else []
    projects = sorted(p.name for p in config.PROJECTS_DIR.glob("*") if p.is_dir()) \
        if config.PROJECTS_DIR.exists() else []
    n_sources = len(list(config.SOURCES_DIR.glob("*/meta.json"))) if config.SOURCES_DIR.exists() else 0
    return {"self": selfmind.read_self(), "drafts": drafts, "projects": projects,
            "n_sources": n_sources}


@app.get("/api/draft/{name}")
def draft(name: str):
    p = config.DRAFTS_DIR / name
    if not p.exists() or p.suffix != ".md" or "/" in name or "\\" in name:
        return {"error": "not found"}
    return {"name": name, "content": p.read_text(encoding="utf-8")}


@app.post("/api/seed")
def seed(payload: dict):
    """Blank-slate spawn: give it interests and it starts on its own."""
    interests = payload.get("interests") or []
    if isinstance(interests, str):
        interests = [s.strip() for s in interests.split(",") if s.strip()]
    seeded = selfmind.seed(interests, name=payload.get("name", "Persona"))
    log().emit("seed", f"{'seeded' if seeded else 'already seeded'}: "
               f"{', '.join(interests)}", actor="human")
    return {"seeded": seeded, "interests": selfmind.interests()}


@app.post("/api/read_url")
def read_url(payload: dict):
    """Feed the researcher an arbitrary web/online source to read."""
    if _daemon is None:
        return {"ok": False, "reason": "daemon down"}
    tid = _daemon.queue.enqueue("read_url", priority=2,
                                params={"url": payload["url"], "interest": payload.get("interest", "web")})
    return {"ok": True, "task": tid}


@app.get("/api/stream")
async def stream():
    async def gen():
        seen = max(0, log().latest_id() - 80)     # replay a little recent context on connect
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
    if idx.exists():
        return FileResponse(str(idx))
    return {"service": "Persona v4", "hint": "UI missing; API under /api/*"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8137)
