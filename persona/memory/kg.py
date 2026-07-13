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
import json
import math
import os
from datetime import datetime, timezone

from .. import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_confidence(value) -> float:
    """Belief-store write boundary: confidence MUST be a finite number in [0.0, 1.0].
    Non-numeric/NaN/inf raises ValueError (fail loud — a garbage number silently entering the
    belief-state is CLAUDE.md's 'worst possible bug'). Out-of-range values clamp to [0,1]:
    the live KG had confidence>1 that broke value_queue VoI (A10/L3-CONF)."""
    try:
        c = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"confidence must be numeric, got {value!r}")
    if math.isnan(c) or math.isinf(c):
        raise ValueError(f"confidence must be finite, got {value!r}")
    return max(0.0, min(1.0, c))


def _confidence_cap(independent_source_count: int) -> float:
    """F2.6 evidence-monotonic no-inflation ceiling. A belief's confidence may never exceed a
    function of the number of INDEPENDENT labs backing it — so repetition / citation-echo /
    reasoning (which raise support_count but NOT independent_source_count) cannot inflate it.
    Monotone non-decreasing in k: one lab tops out at 0.5, the ceiling rises only as new
    independent labs corroborate. PLACEHOLDER heuristic (k/(k+1)); not yet calibrated on data."""
    k = max(0, int(independent_source_count or 0))
    return k / (k + 1.0)


def _clean_year(value):
    """Write boundary: a missing/invalid year is None (omitted), never 0 — a stored 0 renders
    as 1970 downstream (A7). Returns an int year only for a plausible value, else None."""
    try:
        y = int(value)
    except (TypeError, ValueError):
        return None
    return y if 1000 <= y <= 3000 else None


def pair_key(subject: str, obj: str) -> str:
    s = " ".join((subject or "").lower().split())
    o = " ".join((obj or "").lower().split())
    return "pr_" + hashlib.sha1(f"{s}|{o}".encode()).hexdigest()[:12]


def lab_of(affiliations: list, slug: str) -> str:
    """Independence unit: the senior/first affiliation, else the source itself."""
    if affiliations:
        return "lab:" + " ".join(str(affiliations[0]).lower().split())
    return "src:" + slug


# FC-3 constants ---------------------------------------------------------------
# A belief is "confirmed" once a human or a run has signed off (or it is anchored). Everything
# still on cheap READ/INFERRED literature evidence is never-confirmed and, past STALE_DAYS, stale.
CONFIRMED_PROVENANCE = ("HUMAN_CONFIRMED", "TESTED")
STALE_DAYS = 180  # ponytail: fixed staleness horizon; promote to a param if a surface needs to tune it
DEP_REL_TYPES = frozenset({"supports", "contradicts", "presupposes", "derives_from",
                           "generalizes", "operationalizes", "qualifies", "extends"})


def _age_days(iso: str, now: datetime) -> int | None:
    try:
        t = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return int((now - t).total_seconds() // 86400)


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
             "year": _clean_year(meta.get("year")),
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
                  "pk": pk, "conf": _clean_confidence(rec.get("confidence", 0.6) or 0.6),
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
        # F2.6 NO-INFLATION GUARD: the averaged confidence is additionally CAPPED by
        # _confidence_cap(independent labs), so a re-observation can only raise confidence by bringing
        # NEW independent evidence — repetition / citation-echo (more sources, same labs) cannot.
        agg = self._q(
            """
            MATCH (c:Claim {claim_id:$cid})-[r:SUPPORTED_BY]->(s:Source)
            RETURN count(s) AS n, count(DISTINCT s.lab) AS labs, avg(r.conf) AS mconf
            """, {"cid": cid}).result_set
        if agg and agg[0][2] is not None:  # no source row -> nothing to recompute (as before)
            n, labs, mconf = agg[0]
            capped = min(float(mconf), _confidence_cap(labs))
            self._q(
                """
                MATCH (c:Claim {claim_id:$cid})
                SET c.support_count = $n, c.independent_source_count = $labs,
                    c.confidence = CASE WHEN c.anchored THEN c.confidence ELSE $capped END
                """, {"cid": cid, "n": n, "labs": labs, "capped": capped})
        return cid

    def link_contradictions(self, pair_key_val: str) -> int:
        """Any two claims on the same (subject,object) pair with opposite signs contradict."""
        r = self._q(
            """
            MATCH (a:Claim {pair_key:$pk}), (b:Claim {pair_key:$pk})
            WHERE a.effect_sign='+' AND b.effect_sign='-'
              AND a.valid_to IS NULL AND b.valid_to IS NULL
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
              AND a.valid_to IS NULL AND b.valid_to IS NULL
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

    def retire_extraction_claim(self, claim_id: str, reason: str, session_id: str) -> bool:
        """Retire a bad extraction while preserving its node and provenance for audit."""
        r = self._q(
            "MATCH (c:Claim {claim_id:$cid}) SET c.valid_to=$now, "
            "c.provenance='REJECTED_EXTRACTION', c.correction_reason=$reason, "
            "c.correction_session=$sid RETURN c.claim_id",
            {"cid": claim_id, "now": _now(), "reason": reason[:500], "sid": session_id})
        if not r.result_set:
            return False
        self._q("MATCH (c:Claim {claim_id:$cid})-[r:CONTRADICTS]->() DELETE r", {"cid": claim_id})
        self._q("MATCH ()-[r:CONTRADICTS]->(c:Claim {claim_id:$cid}) DELETE r", {"cid": claim_id})
        return True

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

    def set_validity_window(self, claim_id: str, valid_from=None, valid_to=None) -> bool:
        """F2.7: bound a claim's temporal validity (the bi-temporal valid_from/valid_to fields —
        WHEN the claim is true, distinct from ingest_time = when observed). Only the bounds you pass
        are written; a None bound is left unchanged (so you can set one end without clobbering the
        other). Does NOT touch anchoring, provenance, or confidence. Returns True if the claim exists.
        Note: setting valid_to retires the claim from live views (they filter valid_to IS NULL)."""
        sets, params = [], {"cid": claim_id}
        if valid_from is not None:
            sets.append("c.valid_from=$vf"); params["vf"] = valid_from
        if valid_to is not None:
            sets.append("c.valid_to=$vt"); params["vt"] = valid_to
        if not sets:
            return False
        r = self._q("MATCH (c:Claim {claim_id:$cid}) SET " + ", ".join(sets) +
                    " RETURN c.claim_id", params)
        return bool(r.result_set)

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
              AND a.valid_to IS NULL AND b.valid_to IS NULL
            RETURN a.subject, a.object, a.independent_source_count, b.independent_source_count,
                   a.claim_id, b.claim_id LIMIT $lim
            """, {"lim": limit})
        cols = ["subject", "object", "pos_sources", "neg_sources", "pos_claim", "neg_claim"]
        return [dict(zip(cols, row)) for row in r.result_set]

    def candidate_conflicts(self, limit: int = 100) -> list:
        """Opposite stored signs are candidates until exact evidence and qualifiers are verified."""
        return [{**c, "status": "candidate_conflict", "conflict_type": "unverified",
                 "needs_human_review": True} for c in self.contradictions(limit)]

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

    def claims_in(self, entities: list, limit: int = 60) -> list:
        """All claims whose subject AND object are within a set of entities (a subtopic community),
        with their supporting sources + verbatim quotes — the grounded input for a synthesis note."""
        r = self._q(
            """
            MATCH (c:Claim)-[:ABOUT_SUBJECT]->(subj:Entity), (c)-[:ABOUT_OBJECT]->(obj:Entity)
            WHERE subj.name IN $ents AND obj.name IN $ents
            OPTIONAL MATCH (c)-[sr:SUPPORTED_BY]->(s:Source)
            WITH c, collect(DISTINCT {slug:s.slug, title:s.title, lab:s.lab, doi:s.doi, quote:sr.quote}) AS srcs
            RETURN c.claim_id, c.subject, c.relation, c.object, c.effect_sign, c.confidence,
                   c.independent_source_count, srcs
            ORDER BY c.independent_source_count DESC, c.confidence DESC LIMIT $lim
            """, {"ents": list(entities), "lim": limit})
        cols = ["claim_id", "subject", "relation", "object", "effect_sign", "confidence",
                "independent_sources", "sources"]
        return [dict(zip(cols, row)) for row in r.result_set]

    # ------------------------------------------------- FC-3: provenance audit + dependency graph
    def provenance_breakdown(self) -> dict:
        """Audit the live belief store by provenance state: a count per state, the never-confirmed
        claims (still on cheap READ/INFERRED evidence and unanchored), and the stale ones
        (never-confirmed AND ingested > STALE_DAYS ago). Retired claims (valid_to set) are excluded."""
        rows = self._q(
            "MATCH (c:Claim) WHERE c.valid_to IS NULL "
            "RETURN c.claim_id, c.provenance, c.anchored, c.ingest_time").result_set
        counts = {"READ": 0, "INFERRED": 0, "HUMAN_CONFIRMED": 0, "TESTED": 0}
        never, stale = [], []
        now = datetime.now(timezone.utc)
        for cid, prov, anchored, ingest in rows:
            if prov in counts:
                counts[prov] += 1
            confirmed = (prov in CONFIRMED_PROVENANCE) or bool(anchored)
            if not confirmed:
                never.append(cid)
                age = _age_days(ingest, now)
                if age is not None and age > STALE_DAYS:
                    stale.append({"claim_id": cid, "age_days": age})
        return {**counts, "never_confirmed": never, "stale": stale}

    def add_dependency_edge(self, src_claim_id: str, dst_claim_id: str, rel_type: str,
                            confidence: float, span: str) -> None:
        """Record a typed dependency between two claims (the claim-dependency graph). rel_type must
        be one of DEP_REL_TYPES; raises ValueError otherwise. Keyed on rel_type so distinct relation
        types between the same pair are distinct edges; re-adding one updates confidence/span.
        confidence goes through the same [0,1] clamp + fail-loud guard as claim confidence — a
        dependency edge is a belief-store write too (S2 review-kg-hygiene: last unclamped path)."""
        if rel_type not in DEP_REL_TYPES:
            raise ValueError(f"invalid rel_type {rel_type!r}; must be one of {sorted(DEP_REL_TYPES)}")
        if src_claim_id == dst_claim_id:
            return  # no self-dependency: a self-loop inflates load_bearing in-degree (S2 L-DEP-1)
        self._q(
            "MATCH (a:Claim {claim_id:$src}), (b:Claim {claim_id:$dst}) "
            "MERGE (a)-[d:DEPENDS_ON {rel_type:$rt}]->(b) "
            "SET d.confidence=$conf, d.span=$span",
            {"src": src_claim_id, "dst": dst_claim_id, "rt": rel_type,
             "conf": _clean_confidence(confidence), "span": (span or "")[:600]})

    def dependency_edges(self, topic: str = None) -> list:
        """All dependency edges; if topic is given, only those touching a claim whose subject or
        object contains it (case-insensitive)."""
        if topic:
            t = " ".join(str(topic).lower().split())
            rows = self._q(
                "MATCH (a:Claim)-[d:DEPENDS_ON]->(b:Claim) "
                "WHERE toLower(a.subject) CONTAINS $t OR toLower(a.object) CONTAINS $t "
                "   OR toLower(b.subject) CONTAINS $t OR toLower(b.object) CONTAINS $t "
                "RETURN a.claim_id, b.claim_id, d.rel_type, d.confidence, d.span", {"t": t}).result_set
        else:
            rows = self._q(
                "MATCH (a:Claim)-[d:DEPENDS_ON]->(b:Claim) "
                "RETURN a.claim_id, b.claim_id, d.rel_type, d.confidence, d.span").result_set
        cols = ["src", "dst", "rel_type", "confidence", "span"]
        return [dict(zip(cols, r)) for r in rows]

    def citation_support_ratio(self, claim_id: str) -> dict:
        """scite-style citation intent tally, grounded in the store: over all LIVE claims on the same
        (subject,object) pair, count supporting source-citations (same effect_sign as the claim),
        contrasting (opposite +/- sign) and mentioning (neutral 0/na). ratio = support/(support+contrast)."""
        r = self._q("MATCH (c:Claim {claim_id:$cid}) RETURN c.pair_key, c.effect_sign",
                    {"cid": claim_id}).result_set
        if not r:
            return {"support": 0, "contrast": 0, "mention": 0, "ratio": 0.0}
        pk, sign = r[0][0], r[0][1]
        rows = self._q(
            "MATCH (c:Claim {pair_key:$pk})-[:SUPPORTED_BY]->(s:Source) "
            "WHERE c.valid_to IS NULL RETURN c.effect_sign, count(s)", {"pk": pk}).result_set
        support = contrast = mention = 0
        for esign, n in rows:
            n = int(n)
            if esign == sign:
                support += n
            elif {esign, sign} == {"+", "-"}:
                contrast += n
            else:
                mention += n
        denom = support + contrast
        return {"support": support, "contrast": contrast, "mention": mention,
                "ratio": round(support / denom, 4) if denom else 0.0}

    # --------------------------------------- human corpus + cross-check (v6 P5 co-researcher)
    def add_human_work(self, doc_id: str, title: str, kind: str, owner: str = "human") -> None:
        self._q("MERGE (h:Human {owner:$o}) MERGE (w:HumanWork {doc_id:$d}) "
                "SET w.title=$t, w.kind=$k, w.created=$now MERGE (w)-[:AUTHORED_BY]->(h)",
                {"o": owner, "d": doc_id, "t": (title or "")[:200], "k": kind, "now": _now()})

    def add_human_claim(self, doc_id: str, subject: str, obj: str, effect_sign: str,
                        quote: str) -> str:
        """The human's OWN assertion — provenance origin HUMAN_CORPUS, kept distinct from the
        literature belief store so it never renders with confirmed-belief authority."""
        subj = self.canon.canon(subject)
        ob = self.canon.canon(obj)
        hcid = "hcl_" + hashlib.sha1(f"{doc_id}|{subj}|{ob}|{effect_sign}".encode()).hexdigest()[:12]
        self._q(
            "MATCH (w:HumanWork {doc_id:$d}) MERGE (hc:HumanClaim {hc_id:$id}) "
            "SET hc.subject=$s, hc.object=$o, hc.effect_sign=$sign, hc.quote=$q, "
            "hc.provenance='HUMAN_CORPUS', hc.pair_key=$pk "
            "MERGE (w)-[:ASSERTS]->(hc) "
            "MERGE (subj:Entity {name:$s}) MERGE (obj:Entity {name:$o}) "
            "MERGE (hc)-[:ABOUT_SUBJECT]->(subj) MERGE (hc)-[:ABOUT_OBJECT]->(obj)",
            {"d": doc_id, "id": hcid, "s": subj, "o": ob, "sign": effect_sign,
             "q": (quote or "")[:500], "pk": pair_key(subj, ob)})
        return hcid

    def crosscheck(self, subject: str, obj: str, effect_sign: str) -> dict:
        """Find literature claims on the same (subject,object) pair: same sign = SUPPORT, opposite =
        CONTRADICTION — with sources + verbatim quotes + DOIs. The evidence for/against a claim."""
        subj = self.canon.canon(subject)
        ob = self.canon.canon(obj)
        rows = self._q(
            "MATCH (c:Claim {pair_key:$pk}) "
            "OPTIONAL MATCH (c)-[r:SUPPORTED_BY]->(s:Source) "
            "WITH c, collect({slug:s.slug, title:s.title, doi:s.doi, lab:s.lab, quote:r.quote}) AS srcs "
            "RETURN c.claim_id, c.subject, c.object, c.effect_sign, c.independent_source_count, "
            "c.confidence, srcs", {"pk": pair_key(subj, ob)}).result_set
        support, contra = [], []
        for cid, cs, co, csign, isc, conf, srcs in rows:
            item = {"claim_id": cid, "text": f"{cs} [{csign}] {co}", "labs": isc,
                    "confidence": conf, "sources": [s for s in srcs if s.get("slug")]}
            if csign == effect_sign:
                support.append(item)
            elif {csign, effect_sign} == {"+", "-"}:
                contra.append(item)
        return {"subject": subj, "object": ob, "support": support, "contradict": contra}

    def claims_about(self, entities: list, limit: int = 60) -> list:
        """Claims where the subject OR object is in a set of entities (a topic), with sources — the
        grounded material for a topic digest / NL answer (broader than claims_in's both-endpoints)."""
        r = self._q(
            """
            MATCH (c:Claim)-[:ABOUT_SUBJECT|ABOUT_OBJECT]->(e:Entity)
            WHERE e.name IN $ents AND c.valid_to IS NULL
            OPTIONAL MATCH (c)-[sr:SUPPORTED_BY]->(s:Source)
            WITH c, collect(DISTINCT {slug:s.slug, title:s.title, lab:s.lab, doi:s.doi, year:s.year, quote:sr.quote}) AS srcs
            RETURN DISTINCT c.claim_id, c.subject, c.relation, c.object, c.effect_sign, c.confidence,
                   c.independent_source_count, c.provenance, c.anchored, srcs
            ORDER BY c.independent_source_count DESC, c.confidence DESC LIMIT $lim
            """, {"ents": list(entities), "lim": limit})
        cols = ["claim_id", "subject", "relation", "object", "effect_sign", "confidence",
                "independent_sources", "provenance", "anchored", "sources"]
        return [dict(zip(cols, row)) for row in r.result_set]

    def subgraph(self, entities: list, limit: int = 80) -> dict:
        """The induced graph over a set of entities (+ their strongest links) — for a topic view."""
        ents = list(entities)[:limit]
        nodes = [{"id": f"entity:{n}", "type": "entity", "label": n} for n in ents]
        edges = []
        if ents:
            for s, o, cid, sign, isc, conf, ing in self._q(
                    "MATCH (c:Claim)-[:ABOUT_SUBJECT]->(s:Entity), (c)-[:ABOUT_OBJECT]->(o:Entity) "
                    "WHERE s.name IN $e AND o.name IN $e "
                    "RETURN s.name, o.name, c.claim_id, c.effect_sign, c.independent_source_count, "
                    "c.confidence, c.ingest_time", {"e": ents}).result_set:
                edges.append({"source": f"entity:{s}", "target": f"entity:{o}", "type": "claim",
                              "claim_id": cid, "sign": sign, "independent_sources": isc,
                              "confidence": conf, "t": ing})
        return {"nodes": nodes, "edges": edges}

    def add_synthesis_note(self, slug: str, title: str, entities: list, claim_ids: list) -> None:
        """Record a synthesis note as a KG node linked to the claims it synthesizes."""
        self._q("MERGE (n:SynthesisNote {slug:$slug}) SET n.title=$title, n.entities=$ents, "
                "n.updated=$now", {"slug": slug, "title": title[:200], "ents": entities, "now": _now()})
        for cid in claim_ids:
            self._q("MATCH (n:SynthesisNote {slug:$slug}), (c:Claim {claim_id:$cid}) "
                    "MERGE (n)-[:SYNTHESIZES]->(c)", {"slug": slug, "cid": cid})

    def add_experiment(self, exp_id: str, title: str, kind: str, entities: list,
                       artifact: str = "", meta: dict = None) -> None:
        """Record an experiment/build as a first-class node linked to the entities it's about, so the
        graph can be walked belief -> experiment -> result (v6 P4)."""
        self._q("MERGE (x:Experiment {exp_id:$id}) SET x.title=$t, x.kind=$k, x.artifact=$a, "
                "x.created=$now, x.meta=$m",
                {"id": exp_id, "t": (title or "")[:200], "k": kind, "a": artifact, "now": _now(),
                 "m": json.dumps(meta or {})})
        for e in entities or []:
            try:
                cn = self.canon.canon(e)
            except Exception:
                cn = e
            self._q("MATCH (x:Experiment {exp_id:$id}) MERGE (e:Entity {name:$n}) "
                    "MERGE (x)-[:ABOUT]->(e)", {"id": exp_id, "n": cn})

    def graph_snapshot(self, limit: int = 2000) -> dict:
        """Nodes+edges for the dashboard mini-graph (entities + claim topology)."""
        nodes = self._q(
            "MATCH (e:Entity) RETURN e.name LIMIT $lim", {"lim": limit}).result_set
        edges = self._q(
            """MATCH (c:Claim)-[:ABOUT_SUBJECT]->(s:Entity), (c)-[:ABOUT_OBJECT]->(o:Entity)
               WHERE c.valid_to IS NULL
               RETURN s.name, o.name, c.effect_sign, c.independent_source_count, c.confidence
               LIMIT $lim""", {"lim": limit}).result_set
        return {"nodes": [{"id": n[0]} for n in nodes],
                "edges": [{"source": e[0], "target": e[1], "sign": e[2],
                           "independent_sources": e[3], "confidence": e[4]} for e in edges]}

    # ------------------------------------------- navigable graph (v6 P3): walk from ANY node
    # Node ids are "type:key" (entity:name, claim:claim_id, source:slug, note:slug,
    # experiment:id, idea:id, question:id). overview() = a RANKED seed (top entities by degree,
    # not an arbitrary cap); neighbors() expands from one node; node() is the inspector detail.
    def overview(self, limit: int = 60) -> dict:
        top = self._q(
            "MATCH (e:Entity)<-[:ABOUT_SUBJECT|ABOUT_OBJECT]-(c:Claim) "
            "WITH e, count(c) AS deg ORDER BY deg DESC LIMIT $lim RETURN e.name, deg",
            {"lim": limit}).result_set
        names = [r[0] for r in top]
        nodes = [{"id": f"entity:{n}", "type": "entity", "label": n, "degree": int(d)}
                 for n, d in top]
        edges = []
        if names:
            er = self._q(
                "MATCH (c:Claim)-[:ABOUT_SUBJECT]->(s:Entity), (c)-[:ABOUT_OBJECT]->(o:Entity) "
                "WHERE s.name IN $names AND o.name IN $names "
                "RETURN s.name, o.name, c.claim_id, c.effect_sign, c.independent_source_count, "
                "c.confidence, c.ingest_time", {"names": names}).result_set
            for s, o, cid, sign, isc, conf, ing in er:
                edges.append({"source": f"entity:{s}", "target": f"entity:{o}", "type": "claim",
                              "claim_id": cid, "sign": sign, "independent_sources": isc,
                              "confidence": conf, "t": ing})
        return {"nodes": nodes, "edges": edges}

    def neighbors(self, node_id: str, limit: int = 40) -> dict:
        kind, _, key = (node_id or "").partition(":")
        nodes, edges, seen = [], [], set()

        def add(nid, typ, label, **extra):
            if nid not in seen:
                seen.add(nid)
                nodes.append({"id": nid, "type": typ, "label": (label or "")[:70], **extra})

        if kind == "entity":
            rows = self._q(
                "MATCH (c:Claim)-[:ABOUT_SUBJECT]->(s:Entity), (c)-[:ABOUT_OBJECT]->(o:Entity) "
                "WHERE s.name=$n OR o.name=$n "
                "RETURN s.name, o.name, c.claim_id, c.effect_sign, c.independent_source_count, "
                "c.confidence, c.ingest_time ORDER BY c.independent_source_count DESC LIMIT $lim",
                {"n": key, "lim": limit}).result_set
            for s, o, cid, sign, isc, conf, ing in rows:
                add(f"entity:{s}", "entity", s); add(f"entity:{o}", "entity", o)
                edges.append({"source": f"entity:{s}", "target": f"entity:{o}", "type": "claim",
                              "claim_id": cid, "sign": sign, "independent_sources": isc,
                              "confidence": conf, "t": ing})
            for slug, title, doi in self._q(
                    "MATCH (c:Claim)-[:ABOUT_SUBJECT|ABOUT_OBJECT]->(e:Entity {name:$n}), "
                    "(c)-[:SUPPORTED_BY]->(s:Source) RETURN DISTINCT s.slug, s.title, s.doi LIMIT 12",
                    {"n": key}).result_set:
                add(f"source:{slug}", "source", title or slug, doi=doi)
                edges.append({"source": f"entity:{key}", "target": f"source:{slug}", "type": "paper"})
            for slug, title in self._q(
                    "MATCH (nt:SynthesisNote)-[:SYNTHESIZES]->(c:Claim)"
                    "-[:ABOUT_SUBJECT|ABOUT_OBJECT]->(e:Entity {name:$n}) "
                    "RETURN DISTINCT nt.slug, nt.title LIMIT 6", {"n": key}).result_set:
                add(f"note:{slug}", "note", title or slug)
                edges.append({"source": f"note:{slug}", "target": f"entity:{key}", "type": "synthesizes"})
            for xid, title, xk in self._q(
                    "MATCH (x:Experiment)-[:ABOUT]->(e:Entity {name:$n}) "
                    "RETURN x.exp_id, x.title, x.kind LIMIT 8", {"n": key}).result_set:
                add(f"experiment:{xid}", "experiment", title or xk)
                edges.append({"source": f"experiment:{xid}", "target": f"entity:{key}", "type": "about"})
        elif kind == "experiment":
            for nm, in self._q("MATCH (x:Experiment {exp_id:$k})-[:ABOUT]->(e:Entity) "
                               "RETURN e.name LIMIT $lim", {"k": key, "lim": limit}).result_set:
                add(f"entity:{nm}", "entity", nm)
                edges.append({"source": f"experiment:{key}", "target": f"entity:{nm}", "type": "about"})
        elif kind == "source":
            for a, b, cid, sign in self._q(
                    "MATCH (c:Claim)-[:SUPPORTED_BY]->(s:Source {slug:$k}), "
                    "(c)-[:ABOUT_SUBJECT]->(a:Entity), (c)-[:ABOUT_OBJECT]->(b:Entity) "
                    "RETURN DISTINCT a.name, b.name, c.claim_id, c.effect_sign LIMIT $lim",
                    {"k": key, "lim": limit}).result_set:
                add(f"entity:{a}", "entity", a); add(f"entity:{b}", "entity", b)
                edges.append({"source": f"source:{key}", "target": f"entity:{a}", "type": "paper"})
                edges.append({"source": f"entity:{a}", "target": f"entity:{b}", "type": "claim",
                              "claim_id": cid, "sign": sign})
        elif kind == "note":
            for a, b, cid in self._q(
                    "MATCH (nt:SynthesisNote {slug:$k})-[:SYNTHESIZES]->(c:Claim)"
                    "-[:ABOUT_SUBJECT]->(a:Entity), (c)-[:ABOUT_OBJECT]->(b:Entity) "
                    "RETURN DISTINCT a.name, b.name, c.claim_id LIMIT $lim",
                    {"k": key, "lim": limit}).result_set:
                add(f"entity:{a}", "entity", a); add(f"entity:{b}", "entity", b)
                edges.append({"source": f"note:{key}", "target": f"entity:{a}", "type": "synthesizes"})
                edges.append({"source": f"entity:{a}", "target": f"entity:{b}", "type": "claim",
                              "claim_id": cid})
        return {"nodes": nodes, "edges": edges}

    def node(self, node_id: str) -> dict:
        kind, _, key = (node_id or "").partition(":")
        if kind == "entity":
            deg = self._q("MATCH (e:Entity {name:$n})<-[:ABOUT_SUBJECT|ABOUT_OBJECT]-(c:Claim) "
                          "RETURN count(c)", {"n": key}).result_set
            claims = self._q(
                "MATCH (c:Claim)-[:ABOUT_SUBJECT|ABOUT_OBJECT]->(e:Entity {name:$n}) "
                "RETURN c.claim_id, c.subject, c.effect_sign, c.object, c.independent_source_count, "
                "c.confidence, c.anchored ORDER BY c.independent_source_count DESC LIMIT 25",
                {"n": key}).result_set
            return {"id": node_id, "type": "entity", "label": key,
                    "degree": int(deg[0][0]) if deg else 0,
                    "claims": [{"claim_id": r[0], "text": f"{r[1]} [{r[2]}] {r[3]}", "labs": r[4],
                                "confidence": r[5], "anchored": r[6]} for r in claims]}
        if kind == "claim":
            p = self.provenance(key); p["id"] = node_id; p["type"] = "claim"; return p
        if kind == "source":
            r = self._q("MATCH (s:Source {slug:$k}) RETURN s.title, s.doi, s.url, s.year, s.lab",
                        {"k": key}).result_set
            row = r[0] if r else [key, "", "", 0, ""]
            claims = self._q(
                "MATCH (c:Claim)-[:SUPPORTED_BY]->(s:Source {slug:$k}) "
                "RETURN c.claim_id, c.subject, c.effect_sign, c.object, c.independent_source_count, "
                "c.confidence, c.anchored ORDER BY c.independent_source_count DESC LIMIT 25",
                {"k": key}).result_set
            return {"id": node_id, "type": "source", "label": row[0] or key, "doi": row[1],
                    "url": row[2], "year": row[3], "lab": row[4], "slug": key,
                    "claims": [{"claim_id": c[0], "text": f"{c[1]} [{c[2]}] {c[3]}", "labs": c[4],
                                "confidence": c[5], "anchored": c[6]} for c in claims]}
        if kind == "note":
            r = self._q("MATCH (n:SynthesisNote {slug:$k}) RETURN n.title, n.entities, n.updated",
                        {"k": key}).result_set
            row = r[0] if r else [key, [], ""]
            return {"id": node_id, "type": "note", "label": row[0] or key, "slug": key,
                    "entities": row[1], "updated": row[2]}
        if kind == "experiment":
            r = self._q("MATCH (x:Experiment {exp_id:$k}) RETURN x.title, x.kind, x.artifact, "
                        "x.created, x.meta", {"k": key}).result_set
            row = r[0] if r else [key, "", "", "", "{}"]
            try:
                meta = json.loads(row[4] or "{}")
            except Exception:
                meta = {}
            return {"id": node_id, "type": "experiment", "label": row[0] or key, "kind": row[1],
                    "artifact": row[2], "created": row[3], "meta": meta}
        return {"id": node_id, "type": kind or "unknown", "label": key}

    def search(self, q: str, limit: int = 20) -> list:
        ql = (q or "").lower().strip()
        if not ql:
            return []
        out = [{"id": f"entity:{r[0]}", "type": "entity", "label": r[0]} for r in self._q(
            "MATCH (e:Entity) WHERE toLower(e.name) CONTAINS $q RETURN e.name LIMIT $l",
            {"q": ql, "l": limit}).result_set]
        rem = max(0, limit - len(out))
        if rem:
            out += [{"id": f"source:{r[0]}", "type": "source", "label": (r[1] or r[0])[:70]}
                    for r in self._q(
                        "MATCH (s:Source) WHERE toLower(s.title) CONTAINS $q "
                        "RETURN s.slug, s.title LIMIT $l", {"q": ql, "l": rem}).result_set]
        return out[:limit]
