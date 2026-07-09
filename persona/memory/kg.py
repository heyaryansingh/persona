"""Temporal knowledge graph over FalkorDB (v4 P2).

The authoritative structured belief store. Direct Cypher (not Graphiti's LLM-extraction path —
we extract ourselves, cheaply; see the v4 plan's experiment #1). Implements the epistemic ideas
the rebuild keeps:
- **Claim identity = (subject, relation, object, effect_sign).** Opposing signs on the same
  (subject, object) pair do NOT merge — they get a CONTRADICTS edge.
- **Independence by lab** (senior affiliation), not raw source count — citation echo can't inflate.
- **Provenance-typed** (READ/INFERRED/TESTED/HUMAN_CONFIRMED) with an anchor flag so cheap
  evidence can't overwrite verified knowledge.
- **Bi-temporal**: `ingest_time` (when observed) + `valid_from/valid_to` (when true).

Nodes: Entity{name}, Claim{claim_id, subject, object, relation, effect_sign, pair_key,
support_count, independent_source_count, confidence, provenance, anchored, ingest_time,
valid_from, valid_to}, Source{slug, lab, title, year}.
Edges: (Claim)-[:ABOUT_SUBJECT|ABOUT_OBJECT]->(Entity), (Claim)-[:SUPPORTED_BY]->(Source),
(Claim)-[:CONTRADICTS]->(Claim).
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

from .. import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def pair_key(subject: str, obj: str) -> str:
    s = " ".join((subject or "").lower().split())
    o = " ".join((obj or "").lower().split())
    return "pr_" + hashlib.sha1(f"{s}|{o}".encode()).hexdigest()[:12]


def lab_of(affiliations: list, slug: str) -> str:
    """Independence unit: the senior/first affiliation, else the source itself."""
    if affiliations:
        return "lab:" + " ".join(str(affiliations[0]).lower().split())
    return "src:" + slug


class KG:
    def __init__(self, host: str = None, port: int = None, name: str = None, ops_dir=None):
        from falkordb import FalkorDB
        self.host = host or os.environ.get("PERSONA_FALKOR_HOST", "127.0.0.1")
        self.port = int(port or os.environ.get("PERSONA_FALKOR_PORT", "6379"))
        self.name = name or os.environ.get("PERSONA_KG_NAME", "persona")
        self.ops_dir = ops_dir
        self.db = FalkorDB(host=self.host, port=self.port)
        self.g = self.db.select_graph(self.name)
        self._canon = None
        self._init()

    @property
    def canon(self):
        """Lazy entity canonicalizer (embeddings) — so the same concept converges to one node."""
        if self._canon is None:
            from .canon import Canonicalizer
            self._canon = Canonicalizer(ops_dir=self.ops_dir)
        return self._canon

    def _q(self, cypher: str, params: dict = None):
        return self.g.query(cypher, params or {})

    def _init(self):
        for label, prop in (("Entity", "name"), ("Claim", "claim_id"), ("Source", "slug"),
                            ("Claim", "pair_key")):
            try:
                self._q(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")
            except Exception:
                pass   # already exists

    # ---------------------------------------------------------------- writes
    def upsert_source(self, meta: dict) -> None:
        self._q(
            "MERGE (s:Source {slug:$slug}) "
            "ON CREATE SET s.title=$title, s.year=$year, s.lab=$lab, s.affiliations=$affs, "
            "s.doi=$doi, s.url=$url",
            {"slug": meta["slug"], "title": (meta.get("title") or "")[:200],
             "year": meta.get("year") or 0,
             "lab": lab_of(meta.get("affiliations") or [], meta["slug"]),
             "affs": meta.get("affiliations") or [],
             "doi": meta.get("doi") or "", "url": meta.get("url") or ""})

    def add_claim(self, rec: dict, source_slug: str) -> str:
        """Add one observation of a claim from one source; (re)compute support + independence.
        Entities are CANONICALIZED here (not at read time) so the same concept from different
        papers converges, and the claim_id is derived from the canonical form. Returns claim_id."""
        subj = self.canon.canon(rec["subject"])
        obj = self.canon.canon(rec["object"])
        sign = rec.get("effect_sign", "na")
        # claim identity = (subject, object, effect_sign) — the DIRECTIONAL belief. The relation verb
        # ("exhibits"/"shows"/"increases") is descriptive and varies across papers; keying on it would
        # fragment synonymous claims and kill convergence. Opposite signs still contradict via pair_key.
        cid = "clm_" + hashlib.sha1(f"{subj}|{obj}|{sign}".encode()).hexdigest()[:12]
        pk = pair_key(subj, obj)
        params = {"cid": cid, "subj": subj, "obj": obj,
                  "rel": rec.get("relation", ""), "sign": rec.get("effect_sign", "na"),
                  "pk": pk, "conf": float(rec.get("confidence", 0.6) or 0.6),
                  "prov": rec.get("provenance", "READ"), "now": _now(), "slug": source_slug,
                  "quote": (rec.get("quote", "") or "")[:600]}
        self._q(
            """
            MERGE (subj:Entity {name:$subj})
            MERGE (obj:Entity {name:$obj})
            MERGE (c:Claim {claim_id:$cid})
              ON CREATE SET c.subject=$subj, c.object=$obj, c.relation=$rel, c.effect_sign=$sign,
                            c.pair_key=$pk, c.provenance=$prov, c.anchored=false,
                            c.ingest_time=$now, c.valid_from=$now, c.valid_to=null,
                            c.support_count=0, c.independent_source_count=0, c.confidence=$conf
            MERGE (c)-[:ABOUT_SUBJECT]->(subj)
            MERGE (c)-[:ABOUT_OBJECT]->(obj)
            WITH c
            MATCH (s:Source {slug:$slug})
            MERGE (c)-[r:SUPPORTED_BY]->(s)
              ON CREATE SET r.quote=$quote, r.conf=$conf
            """, params)
        # recompute support + independence (distinct labs) + confidence = AVG per-source confidence
        # (bounded [0,1]; one source can't inflate it). ANCHOR WRITE-POLICY: an anchored belief's
        # confidence is PINNED — cheap READ evidence updates counts but cannot move verified belief.
        self._q(
            """
            MATCH (c:Claim {claim_id:$cid})-[r:SUPPORTED_BY]->(s:Source)
            WITH c, count(s) AS n, count(DISTINCT s.lab) AS labs, avg(r.conf) AS mconf
            SET c.support_count = n, c.independent_source_count = labs,
                c.confidence = CASE WHEN c.anchored THEN c.confidence ELSE mconf END
            """, {"cid": cid})
        return cid

    def link_contradictions(self, pair_key_val: str) -> int:
        """Any two claims on the same (subject,object) pair with opposite signs contradict."""
        r = self._q(
            """
            MATCH (a:Claim {pair_key:$pk}), (b:Claim {pair_key:$pk})
            WHERE a.effect_sign='+' AND b.effect_sign='-'
            MERGE (a)-[:CONTRADICTS]->(b)
            MERGE (b)-[:CONTRADICTS]->(a)
            RETURN count(*) AS n
            """, {"pk": pair_key_val})
        return int(r.result_set[0][0]) if r.result_set else 0

    def link_all_contradictions(self) -> int:
        """Link every (subject,object) pair that has both a + and a - claim. pair_key is indexed."""
        r = self._q(
            """
            MATCH (a:Claim), (b:Claim)
            WHERE a.pair_key = b.pair_key AND a.effect_sign='+' AND b.effect_sign='-'
            MERGE (a)-[:CONTRADICTS]->(b)
            MERGE (b)-[:CONTRADICTS]->(a)
            RETURN count(*) AS n
            """)
        return int(r.result_set[0][0]) if r.result_set else 0

    def anchor(self, claim_id: str, provenance: str, truth: bool) -> None:
        """Human/tested sign-off pins a belief (anchor write-policy). truth=False retires it."""
        self._q(
            "MATCH (c:Claim {claim_id:$cid}) SET c.anchored=true, c.provenance=$prov, "
            "c.confidence = CASE WHEN $truth THEN 0.99 ELSE 0.01 END, "
            "c.valid_to = CASE WHEN $truth THEN null ELSE $now END",
            {"cid": claim_id, "prov": provenance, "truth": truth, "now": _now()})

    def human_resolve(self, claim_id: str, truth: bool, provenance: str = "HUMAN_CONFIRMED") -> dict:
        """A human resolves an escalated contradiction: anchor the chosen side (protected henceforth)."""
        self.anchor(claim_id, provenance, truth)
        r = self._q("MATCH (c:Claim {claim_id:$cid}) RETURN c.subject, c.relation, c.object, "
                    "c.effect_sign, c.provenance, c.anchored", {"cid": claim_id})
        if not r.result_set:
            return {"ok": False}
        row = r.result_set[0]
        return {"ok": True, "claim_id": claim_id, "subject": row[0], "object": row[2],
                "effect_sign": row[3], "provenance": row[4], "anchored": row[5], "truth": truth}

    def is_anchored(self, claim_id: str) -> bool:
        r = self._q("MATCH (c:Claim {claim_id:$cid}) RETURN c.anchored", {"cid": claim_id})
        return bool(r.result_set and r.result_set[0][0])

    # ---------------------------------------------------------------- reads
    def stats(self) -> dict:
        r = self._q("MATCH (c:Claim) RETURN count(c)")
        e = self._q("MATCH (n:Entity) RETURN count(n)")
        x = self._q("MATCH (:Claim)-[r:CONTRADICTS]->(:Claim) RETURN count(r)")
        return {"claims": r.result_set[0][0], "entities": e.result_set[0][0],
                "contradiction_edges": x.result_set[0][0]}

    def beliefs(self, min_independent: int = 2, min_conf: float = 0.5, limit: int = 200) -> list:
        r = self._q(
            """
            MATCH (c:Claim)
            WHERE c.independent_source_count >= $k AND c.confidence >= $mc AND c.valid_to IS NULL
            RETURN c.claim_id, c.subject, c.relation, c.object, c.effect_sign,
                   c.independent_source_count, c.confidence, c.provenance, c.anchored
            ORDER BY c.independent_source_count DESC, c.confidence DESC LIMIT $lim
            """, {"k": min_independent, "mc": min_conf, "lim": limit})
        cols = ["claim_id", "subject", "relation", "object", "effect_sign",
                "independent_sources", "confidence", "provenance", "anchored"]
        return [dict(zip(cols, row)) for row in r.result_set]

    def contradictions(self, limit: int = 100) -> list:
        r = self._q(
            """
            MATCH (a:Claim)-[:CONTRADICTS]->(b:Claim)
            WHERE a.effect_sign='+' AND b.effect_sign='-'
            RETURN a.subject, a.object, a.independent_source_count, b.independent_source_count,
                   a.claim_id, b.claim_id LIMIT $lim
            """, {"lim": limit})
        cols = ["subject", "object", "pos_sources", "neg_sources", "pos_claim", "neg_claim"]
        return [dict(zip(cols, row)) for row in r.result_set]

    def provenance(self, claim_id: str) -> dict:
        """The full defensible chain for a belief: claim → every supporting source + verbatim quote."""
        r = self._q(
            """
            MATCH (c:Claim {claim_id:$cid})
            OPTIONAL MATCH (c)-[r:SUPPORTED_BY]->(s:Source)
            RETURN c.subject, c.relation, c.object, c.effect_sign, c.confidence, c.provenance,
                   c.anchored, c.independent_source_count,
                   collect({slug:s.slug, title:s.title, lab:s.lab, doi:s.doi, url:s.url,
                            year:s.year, quote:r.quote})
            """, {"cid": claim_id})
        if not r.result_set:
            return {}
        row = r.result_set[0]
        srcs = [s for s in (row[8] or []) if s.get("slug")]
        return {"claim_id": claim_id, "subject": row[0], "relation": row[1], "object": row[2],
                "effect_sign": row[3], "confidence": row[4], "provenance": row[5],
                "anchored": row[6], "independent_sources": row[7], "sources": srcs}

    def poisoning_signals(self, min_volume: int = 8, max_indep_ratio: float = 0.4) -> list:
        """Correlated-poisoning signature: a high-volume, LOW-independence claim that contradicts
        an anchored belief (many copies from few labs trying to overturn verified knowledge)."""
        r = self._q(
            """
            MATCH (attacker:Claim)-[:CONTRADICTS]->(anchored:Claim {anchored:true})
            WHERE attacker.support_count >= $vol
              AND (toFloat(attacker.independent_source_count) / attacker.support_count) <= $ratio
            RETURN attacker.subject, attacker.object, attacker.support_count,
                   attacker.independent_source_count, anchored.claim_id
            """, {"vol": min_volume, "ratio": max_indep_ratio})
        cols = ["subject", "object", "volume", "independent_labs", "anchored_claim"]
        return [dict(zip(cols, row)) for row in r.result_set]

    def graph_snapshot(self, limit: int = 2000) -> dict:
        """Nodes+edges for the UI (entities + claim topology)."""
        nodes = self._q(
            "MATCH (e:Entity) RETURN e.name LIMIT $lim", {"lim": limit}).result_set
        edges = self._q(
            """MATCH (c:Claim)-[:ABOUT_SUBJECT]->(s:Entity), (c)-[:ABOUT_OBJECT]->(o:Entity)
               RETURN s.name, o.name, c.effect_sign, c.independent_source_count, c.confidence
               LIMIT $lim""", {"lim": limit}).result_set
        return {"nodes": [{"id": n[0]} for n in nodes],
                "edges": [{"source": e[0], "target": e[1], "sign": e[2],
                           "independent_sources": e[3], "confidence": e[4]} for e in edges]}
