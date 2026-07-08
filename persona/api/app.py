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


@app.get("/api/self")
def get_self():
    return {"seeded": selfmind.is_seeded(), "interests": selfmind.interests(),
            "open_questions": selfmind.open_questions(), "files": selfmind.read_self()}


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
