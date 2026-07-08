"""Bi-temporal, provenance-typed belief-graph over SQLite (stdlib only).

Design derived from BUILD_PLAN 5.3 + the literature sweep (planning/LITERATURE.md):
- Bi-temporal (Graphiti/Zep style): claims/edges carry valid_from/valid_to; superseding
  a belief *invalidates* (sets valid_to) rather than deleting, so history is queryable.
- Provenance-typed: READ / INFERRED / HUMAN_CONFIRMED / TESTED.
- Anchor write-policy (the tested core): READ/INFERRED evidence cannot move a
  HUMAN_CONFIRMED/TESTED anchor beyond `resist`; only human sign-off moves an anchor.
  Validated: under correlated poisoning, anchoring retained 1.000 vs 0.762 of the
  human-confirmed core (results/REPRODUCTION.md). The membrane (next milestone) decides
  *what* to commit; this store is the last-line anchor/provenance guard.
- Two-tier: `tier` in {core, archival}. hydrate() loads only the small core into the
  in-context self; archival stays queryable (Letta-style; planning/LITERATURE.md §A).

Independent-source convergence is counted by distinct `group` on sources (a lab / cohort
/ dataset), NOT by raw agreement count — evidential independence, per §2.4.
"""
from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# provenance ordering: higher = stronger protection
PROVENANCE = ("READ", "INFERRED", "HUMAN_CONFIRMED", "TESTED")
_PROV_RANK = {p: i for i, p in enumerate(PROVENANCE)}
PROTECTED = ("HUMAN_CONFIRMED", "TESTED")

RELATIONS = (
    "supports", "contradicts",
    "presupposes", "derives-from", "generalizes", "operationalizes",
)

LOGIT_CLIP = 8.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class Claim:
    claim_id: str
    statement: str
    logit: float = 0.0
    provenance_state: str = "READ"
    anchor: bool = False
    tier: str = "core"
    entities: list = field(default_factory=list)
    effect: Optional[str] = None
    direction: Optional[str] = None
    population: Optional[str] = None
    method: Optional[str] = None
    power_estimate: Optional[float] = None

    @property
    def calibrated_p(self) -> float:
        return sigmoid(self.logit)

    @property
    def predicted(self) -> int:
        return 1 if self.logit > 0 else 0


class BeliefStore:
    """Versioned belief-graph. `path=":memory:"` for tests."""

    def __init__(self, path: str = ":memory:", resist: float = 0.05):
        self.resist = resist
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS claims (
                claim_id TEXT PRIMARY KEY,
                statement TEXT NOT NULL,
                logit REAL NOT NULL DEFAULT 0.0,
                provenance_state TEXT NOT NULL DEFAULT 'READ',
                anchor INTEGER NOT NULL DEFAULT 0,
                tier TEXT NOT NULL DEFAULT 'core',
                entities TEXT NOT NULL DEFAULT '[]',
                effect TEXT, direction TEXT, population TEXT, method TEXT,
                power_estimate REAL,
                trajectory TEXT,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT NOT NULL REFERENCES claims(claim_id),
                ref TEXT NOT NULL,
                grp TEXT NOT NULL,           -- independence group (lab/cohort/dataset)
                added_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS edges (
                edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                src TEXT NOT NULL REFERENCES claims(claim_id),
                dst TEXT NOT NULL REFERENCES claims(claim_id),
                relation TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.5,
                valid_from TEXT NOT NULL,
                valid_to TEXT
            );
            CREATE TABLE IF NOT EXISTS history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT NOT NULL REFERENCES claims(claim_id),
                ts TEXT NOT NULL,
                cause TEXT NOT NULL,
                logit_before REAL, logit_after REAL,
                provenance_before TEXT, provenance_after TEXT
            );
            CREATE INDEX IF NOT EXISTS ix_claims_tier ON claims(tier);
            CREATE INDEX IF NOT EXISTS ix_sources_claim ON sources(claim_id);
            CREATE INDEX IF NOT EXISTS ix_edges_src ON edges(src);
            """
        )
        self._db.commit()

    # ---------------------------------------------------------------- claims
    def add_claim(self, claim: Claim) -> Claim:
        if self._row(claim.claim_id) is not None:
            raise ValueError(f"claim {claim.claim_id!r} already exists")
        if claim.provenance_state not in _PROV_RANK:
            raise ValueError(f"bad provenance_state {claim.provenance_state!r}")
        now = _now()
        self._db.execute(
            """INSERT INTO claims (claim_id, statement, logit, provenance_state, anchor,
               tier, entities, effect, direction, population, method, power_estimate,
               valid_from, valid_to, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (claim.claim_id, claim.statement, claim.logit, claim.provenance_state,
             int(claim.anchor), claim.tier, json.dumps(claim.entities), claim.effect,
             claim.direction, claim.population, claim.method, claim.power_estimate,
             now, None, now, now),
        )
        self._db.commit()
        return claim

    def _row(self, claim_id: str):
        return self._db.execute(
            "SELECT * FROM claims WHERE claim_id=?", (claim_id,)
        ).fetchone()

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        r = self._row(claim_id)
        if r is None:
            return None
        return Claim(
            claim_id=r["claim_id"], statement=r["statement"], logit=r["logit"],
            provenance_state=r["provenance_state"], anchor=bool(r["anchor"]),
            tier=r["tier"], entities=json.loads(r["entities"]), effect=r["effect"],
            direction=r["direction"], population=r["population"], method=r["method"],
            power_estimate=r["power_estimate"],
        )

    def update_belief(self, claim_id: str, direction: float, *, strength: float = 0.6,
                      cause: str = "swarm", evidence_provenance: str = "READ") -> Claim:
        """Move a belief by `strength*direction`, applying the anchor write-policy.

        Anchor beliefs resist swarm (READ/INFERRED) evidence by `self.resist`; human/tested
        evidence moves them fully. This is the corruption-resistance guard validated in
        results/REPRODUCTION.md — it is the store's last line of defense even if the
        membrane admits a poisoned candidate.
        """
        r = self._row(claim_id)
        if r is None:
            raise KeyError(claim_id)
        if evidence_provenance not in _PROV_RANK:
            raise ValueError(f"bad evidence_provenance {evidence_provenance!r}")
        before = r["logit"]
        is_anchor = bool(r["anchor"])
        human_grade = _PROV_RANK[evidence_provenance] >= _PROV_RANK["HUMAN_CONFIRMED"]
        factor = 1.0 if (human_grade or not is_anchor) else self.resist
        after = max(-LOGIT_CLIP, min(LOGIT_CLIP, before + strength * direction * factor))
        prov_before = r["provenance_state"]
        # provenance can only be upgraded, and never silently by swarm evidence
        prov_after = prov_before
        if _PROV_RANK[evidence_provenance] > _PROV_RANK[prov_before] and human_grade:
            prov_after = evidence_provenance
        now = _now()
        self._db.execute(
            "UPDATE claims SET logit=?, provenance_state=?, updated_at=? WHERE claim_id=?",
            (after, prov_after, now, claim_id),
        )
        self._db.execute(
            """INSERT INTO history (claim_id, ts, cause, logit_before, logit_after,
               provenance_before, provenance_after) VALUES (?,?,?,?,?,?,?)""",
            (claim_id, now, cause, before, after, prov_before, prov_after),
        )
        self._db.commit()
        return self.get_claim(claim_id)

    def human_confirm(self, claim_id: str, truth: int, *, strong: float = 6.0,
                      tested: bool = False) -> Claim:
        """Human (or a TESTED reanalysis) pins a belief and anchors it. truth in {0,1}."""
        r = self._row(claim_id)
        if r is None:
            raise KeyError(claim_id)
        logit = strong if truth == 1 else -strong
        prov = "TESTED" if tested else "HUMAN_CONFIRMED"
        now = _now()
        self._db.execute(
            "UPDATE claims SET logit=?, provenance_state=?, anchor=1, updated_at=? WHERE claim_id=?",
            (logit, prov, now, claim_id),
        )
        self._db.execute(
            """INSERT INTO history (claim_id, ts, cause, logit_before, logit_after,
               provenance_before, provenance_after) VALUES (?,?,?,?,?,?,?)""",
            (claim_id, now, f"human_confirm({prov})", r["logit"], logit,
             r["provenance_state"], prov),
        )
        self._db.commit()
        return self.get_claim(claim_id)

    def invalidate(self, claim_id: str) -> None:
        """Bi-temporal retirement: set valid_to=now instead of deleting."""
        self._db.execute(
            "UPDATE claims SET valid_to=? WHERE claim_id=? AND valid_to IS NULL",
            (_now(), claim_id),
        )
        self._db.commit()

    # --------------------------------------------------------------- sources
    def add_source(self, claim_id: str, ref: str, group: str) -> None:
        if self._row(claim_id) is None:
            raise KeyError(claim_id)
        self._db.execute(
            "INSERT INTO sources (claim_id, ref, grp, added_at) VALUES (?,?,?,?)",
            (claim_id, ref, group, _now()),
        )
        self._db.commit()

    def independent_source_count(self, claim_id: str) -> int:
        """Distinct independence groups — evidential independence, not raw count."""
        return self._db.execute(
            "SELECT COUNT(DISTINCT grp) AS n FROM sources WHERE claim_id=?", (claim_id,)
        ).fetchone()["n"]

    def sources(self, claim_id: str) -> list:
        """All sources for a claim as dict(ref, group)."""
        return [{"ref": r["ref"], "group": r["grp"]} for r in self._db.execute(
            "SELECT ref, grp FROM sources WHERE claim_id=? ORDER BY source_id", (claim_id,)
        ).fetchall()]

    # ----------------------------------------------------------------- edges
    def add_edge(self, src: str, dst: str, relation: str, confidence: float = 0.5) -> None:
        if relation not in RELATIONS:
            raise ValueError(f"bad relation {relation!r}; expected one of {RELATIONS}")
        for cid in (src, dst):
            if self._row(cid) is None:
                raise KeyError(cid)
        self._db.execute(
            "INSERT INTO edges (src, dst, relation, confidence, valid_from) VALUES (?,?,?,?,?)",
            (src, dst, relation, confidence, _now()),
        )
        self._db.commit()

    def edges_from(self, src: str, relation: Optional[str] = None) -> list:
        q = "SELECT src, dst, relation, confidence FROM edges WHERE src=? AND valid_to IS NULL"
        args = [src]
        if relation:
            q += " AND relation=?"
            args.append(relation)
        return [dict(r) for r in self._db.execute(q, args).fetchall()]

    # ------------------------------------------------------------- history/query
    def history(self, claim_id: str) -> list:
        return [dict(r) for r in self._db.execute(
            "SELECT * FROM history WHERE claim_id=? ORDER BY history_id", (claim_id,)
        ).fetchall()]

    def claims(self, *, tier: Optional[str] = None, valid_only: bool = True) -> list:
        q = "SELECT claim_id FROM claims WHERE 1=1"
        args: list = []
        if tier:
            q += " AND tier=?"
            args.append(tier)
        if valid_only:
            q += " AND valid_to IS NULL"
        return [self.get_claim(r["claim_id"])
                for r in self._db.execute(q, args).fetchall()]

    def core_claims(self) -> list:
        """The small in-context tier loaded on hydrate() (two-tier memory)."""
        return self.claims(tier="core")

    def close(self) -> None:
        self._db.close()
