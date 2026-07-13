"""Persona v4 — an always-on, blank-slate autonomous researcher.

Rebuilt ground-up (see planning/ + the approved v4 plan). The design: a small durable SELF on
disk (persona-workspace/self/*.md), a never-idle daemon that continuously spawns fresh-context
sub-agents to read at scale and do real work, a membrane that admits only convergent independent
evidence into a bi-temporal knowledge graph, and a live-thought UI you can watch it think in.
"""
try:
    from importlib.metadata import version
    __version__ = version("persona")
except Exception:  # editable/source checkout before installation
    __version__ = "0.3.0"
