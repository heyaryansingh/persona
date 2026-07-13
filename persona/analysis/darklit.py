"""F3.5: the dark-literature / dead-science meter, read-only over the FC-3 KG.

`dead_science(topic)` surfaces claims the field once leaned on but has stopped touching: **high
past support** (many corroborating reads) yet **no recent activity** (no fresh read/test has
re-observed the claim in a long time). These are the dormant, "dark" beliefs — plausibly true,
plausibly forgotten — that a researcher should periodically re-examine.

Signals, all read straight off the Claim node (no mutation, no model, no network):
  - support: `support_count` — total observations backing the claim (its past weight).
  - last_activity: `ingest_time` — set/refreshed every time a source re-observes the claim
    (`add_claim`), so it is the KG's best deterministic proxy for "last read/test that touched it".
  - dormant_days: age of `last_activity` relative to `now`.
  - revived: the claim has since been re-touched by a test or a human (provenance TESTED /
    HUMAN_CONFIRMED, or anchored) — dark literature being pulled back into the light.

The thresholds below are PLACEHOLDER heuristics (not yet validated against a labelled
dormancy/revival set): high-support cutoff and the dormancy horizon are structural guesses,
not calibrated. Do NOT present the meter as a validated "dead-science" classifier until then.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..memory.membrane import get_kg


def _age_days(iso: str, now: datetime) -> int | None:
    """Whole days between an ISO timestamp and `now`; None if unparseable/missing."""
    try:
        t = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return int((now - t).total_seconds() // 86400)

# PLACEHOLDER: "high past support" = observed by at least this many sources. A claim below this
# was never load-bearing, so its dormancy isn't "dead science", just an untested aside.
MIN_SUPPORT = 3
# PLACEHOLDER: dormancy horizon. No read/test in this many days -> the claim has gone dark.
DORMANT_DAYS = 365


def dead_science(topic: str = None, kg=None, now: datetime = None) -> list:
    """[{claim_id, last_activity, dormant_days, revived}] for high-support, dormant claims on
    `topic`, most-dormant first. Read-only. `kg`/`now` injectable for tests; kg defaults to the
    current persona's KG (None/falsy -> [] if FalkorDB is down)."""
    kg = kg if kg is not None else get_kg()
    if not kg:
        return []
    now = now or datetime.now(timezone.utc)

    where = ""
    params = {"k": MIN_SUPPORT}
    if topic:
        params["t"] = " ".join(str(topic).lower().split())
        where = "AND (toLower(c.subject) CONTAINS $t OR toLower(c.object) CONTAINS $t) "
    rows = kg._q(
        "MATCH (c:Claim) "
        "WHERE c.support_count >= $k AND c.valid_to IS NULL " + where +
        "RETURN c.claim_id, c.ingest_time, c.provenance, c.anchored, c.support_count",
        params).result_set

    out = []
    for cid, ingest, prov, anchored, _support in rows:
        dormant_days = _age_days(ingest, now)
        if dormant_days is None or dormant_days < DORMANT_DAYS:
            continue  # missing timestamp or still active -> not dark
        revived = bool(anchored) or str(prov or "").upper() in {"TESTED", "HUMAN_CONFIRMED"}
        out.append({"claim_id": cid, "last_activity": ingest,
                    "dormant_days": dormant_days, "revived": revived})

    # deterministic: most-dormant first, claim_id breaks ties.
    out.sort(key=lambda d: (-d["dormant_days"], d["claim_id"]))
    return out
