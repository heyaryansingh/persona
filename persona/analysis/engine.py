"""FC-4 engine facade — the intellectual-engine API under its contract namespace.

PRD-00 §4 FC-4 specifies `engine.dependency_graph(topic)` and `engine.value_queue(topic)`.
The implementations live in sibling modules (dependency.py, value_queue.py); this facade
re-exports them so consumers (imp1's Lane-4 routes) can `from persona.analysis import engine`
and call the contract names directly. Add fragility_cascade / trajectory here as they land.
"""
from .dependency import dependency_graph
from .value_queue import value_queue

__all__ = ["dependency_graph", "value_queue"]
