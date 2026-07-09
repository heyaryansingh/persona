"""Current-persona context (v5 P2) — the de-globalization mechanism.

A `contextvars.ContextVar` holds the persona the current async task / thread is acting for.
Workers set it before dispatching a task; API requests set it per persona_id; `asyncio.to_thread`
copies the context so blocking reads see the right persona. Concurrent tasks for different
personas each get their own context → isolation with NO singleton and NO arg threaded through
every call site. `log()`, `get_kg()`, `budget()`, and `selfmind` all resolve through here.

Falls back to a lazily-built DEFAULT persona (the v4 single-workspace) when nothing is set, so
existing single-persona behavior is unchanged.
"""
from __future__ import annotations

import contextvars

_current: contextvars.ContextVar = contextvars.ContextVar("persona", default=None)
_DEFAULT = None


def set_persona(p):
    return _current.set(p)


def reset_persona(token):
    try:
        _current.reset(token)
    except Exception:
        pass


def get_persona():
    p = _current.get()
    if p is not None:
        return p
    global _DEFAULT
    if _DEFAULT is None:
        from . import config
        from .persona_obj import Persona
        _DEFAULT = Persona(id="default", name="Persona", workspace=config.WORKSPACE,
                           graph_name=config.KG_NAME)
    return _DEFAULT


def use(persona):
    """Context manager: `with use(p): ...` binds p as current for the block."""
    class _Ctx:
        def __enter__(self_):
            self_.tok = _current.set(persona)
            return persona
        def __exit__(self_, *a):
            reset_persona(self_.tok)
    return _Ctx()
