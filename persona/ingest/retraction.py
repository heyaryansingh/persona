"""FC-6: retraction / contamination check (offline, deterministic).

Two grounded, model-free reads used by the audit adjudication (audit.py already consumes
`meta.get('retracted')`):

- `is_retracted(doi=, pmid=)` — checks a LOCAL seeded retractions store (a jsonl file under the
  workspace). No network. The real Retraction-Watch / Crossref `/works?filter=is-retracted:true`
  wiring is a later paid/online step — see the TODO seam in `_lookup`.
- `contamination(claim_id)` — walks the FC-3 claim-dependency graph out from a claim and reports
  the first path reaching a claim backed by a retracted source. Pure read; never writes the KG.
"""
from __future__ import annotations

import json
import os
from collections import deque
from pathlib import Path

from .. import config


def _doi_norm(doi: str | None) -> str | None:
    """Match kg's Source.doi form: lowercase, scheme/`doi:` prefix stripped."""
    if not doi:
        return None
    d = str(doi).strip().lower()
    for pre in ("https://doi.org/", "http://doi.org/", "http://dx.doi.org/", "doi:"):
        if d.startswith(pre):
            d = d[len(pre):]
            break
    return d or None


def _store_path() -> Path:
    """Local retractions store. Override with PERSONA_RETRACTIONS_FILE (tests seed a temp file)."""
    env = os.environ.get("PERSONA_RETRACTIONS_FILE")
    return Path(env) if env else (config.WORKSPACE / "retractions.jsonl")


def _load_store() -> list[dict]:
    # ponytail: re-read the (tiny) jsonl per call — no cache to invalidate after a seed/edit.
    p = _store_path()
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _lookup(doi: str | None, pmid: str | None) -> dict | None:
    """First matching local record, or None. TODO(online): fall through to a live Retraction-Watch /
    Crossref is-retracted lookup here (paid/rate-limited) via ingest.service — the store stays the cache."""
    dn = _doi_norm(doi)
    pm = str(pmid).strip() if pmid not in (None, "") else None
    for rec in _load_store():
        if dn and _doi_norm(rec.get("doi")) == dn:
            return rec
        if pm and rec.get("pmid") is not None and str(rec["pmid"]).strip() == pm:
            return rec
    return None


def is_retracted(doi: str | None = None, pmid: str | None = None) -> dict:
    """{retracted, date, reason, source} — offline check against the seeded local store."""
    rec = _lookup(doi, pmid)
    if not rec:
        return {"retracted": False, "date": None, "reason": None, "source": None}
    return {"retracted": True, "date": rec.get("date"), "reason": rec.get("reason"),
            "source": rec.get("source")}


def _pmid_from_slug(slug: str | None) -> str | None:
    """Europe PMC MED records carry the PMID as the slug tail (see grounding: epmc_MED_<pmid>)."""
    if slug and slug.startswith("epmc_MED_"):
        return slug.rsplit("_", 1)[-1]
    return None


def _sources_retracted(kg, claim_id: str) -> bool:
    """True if any source backing this claim is in the retractions store."""
    for s in (kg.provenance(claim_id) or {}).get("sources", []):
        if is_retracted(doi=s.get("doi"), pmid=_pmid_from_slug(s.get("slug")))["retracted"]:
            return True
    return False


def contamination(claim_id: str, kg=None) -> dict:
    """{contaminated, path:[claim_id...]} — BFS along DEPENDS_ON from `claim_id` to the first claim
    whose source is retracted. `kg` injectable for tests; defaults to the current persona's KG."""
    if kg is None:
        from ..memory.membrane import get_kg
        kg = get_kg()
    if kg is None:
        return {"contaminated": False, "path": []}

    # adjacency: a depends-on b (a -> b); contamination flows from a retracted b up its dependents,
    # so from claim_id we follow the edges it (transitively) depends on.
    adj: dict[str, list[str]] = {}
    for e in kg.dependency_edges():
        adj.setdefault(e["src"], []).append(e["dst"])

    parent: dict[str, str | None] = {claim_id: None}
    q = deque([claim_id])
    while q:
        node = q.popleft()
        if _sources_retracted(kg, node):
            path = []
            cur: str | None = node
            while cur is not None:
                path.append(cur)
                cur = parent[cur]
            path.reverse()
            return {"contaminated": True, "path": path}
        for nxt in adj.get(node, []):
            if nxt not in parent:
                parent[nxt] = node
                q.append(nxt)
    return {"contaminated": False, "path": []}
