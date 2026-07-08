"""Bi-temporal graph views (v3 T4) — time-travel over the belief-graph.

The store is already bi-temporal (claims/edges carry valid_from/valid_to; every logit move is
appended to `history` with a timestamp), but nothing exposed an AS-OF view. This module
reconstructs the belief-graph as it existed at any past instant: which claims were valid, what
their logit/confidence was then, and which edges held — so the UI's time-scrubber shows the real
past, not just the current state with a timeline overlay.

Read-only queries over store._db (same access pattern as orchestrator/budget).
"""
from __future__ import annotations

from ..store import sigmoid


def _rows(store, sql, args=()):
    return store._db.execute(sql, args).fetchall()


def claims_valid_at(store, ts: str) -> list:
    """claim_ids whose validity interval contains ts (valid_from <= ts < valid_to|open)."""
    return [r["claim_id"] for r in _rows(
        store,
        "SELECT claim_id FROM claims WHERE valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)",
        (ts, ts))]


def logit_at(store, claim_id: str, ts: str) -> float:
    """The claim's logit as of ts: the last history entry at/before ts (0.0 if none yet)."""
    r = _rows(store,
              "SELECT logit_after FROM history WHERE claim_id=? AND ts <= ? "
              "ORDER BY ts DESC, history_id DESC LIMIT 1", (claim_id, ts))
    if r:
        return float(r[0]["logit_after"])
    # no history at/before ts -> fall back to the claim's creation logit if it existed then
    c = _rows(store, "SELECT logit, valid_from FROM claims WHERE claim_id=?", (claim_id,))
    return float(c[0]["logit"]) if (c and c[0]["valid_from"] <= ts) else 0.0


def edges_valid_at(store, ts: str) -> list:
    return [dict(r) for r in _rows(
        store,
        "SELECT src, dst, relation, confidence FROM edges "
        "WHERE valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)", (ts, ts))]


def graph_as_of(store, ts: str) -> dict:
    """The belief-graph as it existed at ts: nodes (with logit/calibrated_p at ts) + valid edges."""
    valid = set(claims_valid_at(store, ts))
    nodes = []
    for cid in valid:
        lg = logit_at(store, cid, ts)
        row = _rows(store, "SELECT statement FROM claims WHERE claim_id=?", (cid,))
        nodes.append({"id": cid, "statement": (row[0]["statement"][:120] if row else cid),
                      "logit": round(lg, 3), "calibrated_p": round(sigmoid(lg), 3)})
    edges = [e for e in edges_valid_at(store, ts) if e["src"] in valid and e["dst"] in valid]
    return {"as_of": ts, "n_nodes": len(nodes), "nodes": nodes, "edges": edges}


def change_points(store) -> list:
    """Distinct timestamps where anything changed — the scrubber's stops."""
    return [r["ts"] for r in _rows(store, "SELECT DISTINCT ts FROM history ORDER BY ts")]
