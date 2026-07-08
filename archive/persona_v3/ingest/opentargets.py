"""Open Targets Platform client (v3 T0.4) — keyless GraphQL, cached.

Cross-checks a gene<->disease claim against Open Targets' REAL computed target-disease
association (esp. the genetic-association datatype: genetic evidence -> 2.6x clinical success,
Minikel Nature 2024). This is a first-pass reanalysis over REAL structured data, not LLM
reasoning over a string. Resolves free-text entities to Ensembl/EFO ids via the search API.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Optional

from .base import DiskCache

_URL = "https://api.platform.opentargets.org/api/v4/graphql"
_UA = "persona-researcher/0.0.1"

_SEARCH = """query S($q:String!,$e:[String!]){ search(queryString:$q, entityNames:$e){
  hits { id entity name } } }"""

_ASSOC = """query A($t:String!,$d:String!){ target(ensemblId:$t){
  associatedDiseases(Bs:[$d]){ rows { disease{id} score
    datatypeScores { id score } } } } }"""


class OpenTargetsClient:
    def __init__(self, cache: Optional[DiskCache] = None, timeout: float = 20.0):
        self.cache = cache or DiskCache(".cache/opentargets")
        self.timeout = timeout

    def _gql(self, query: str, variables: dict) -> dict:
        key = json.dumps(variables, sort_keys=True)
        cached = self.cache.get("ot", query[:20], key)
        if cached is not None:
            return cached
        body = json.dumps({"query": query, "variables": variables}).encode()
        req = urllib.request.Request(_URL, data=body,
                                     headers={"Content-Type": "application/json", "User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        self.cache.put(data, "ot", query[:20], key)
        return data

    def _resolve(self, text: str, entity: str) -> Optional[str]:
        try:
            d = self._gql(_SEARCH, {"q": text, "e": [entity]})
            hits = (d.get("data", {}).get("search", {}) or {}).get("hits", [])
            for h in hits:
                if h.get("entity") == entity:
                    return h["id"]
        except Exception:
            return None
        return None

    def associate(self, a: str, b: str) -> dict:
        """Try a=target,b=disease then swapped. Returns {found, overall, genetic, target, disease}."""
        for gene, disease in ((a, b), (b, a)):
            t = self._resolve(gene, "target")
            dz = self._resolve(disease, "disease")
            if not t or not dz:
                continue
            try:
                d = self._gql(_ASSOC, {"t": t, "d": dz})
                rows = (((d.get("data", {}).get("target") or {}).get("associatedDiseases") or {})
                        .get("rows") or [])
                if not rows:
                    continue
                row = rows[0]
                genetic = next((s["score"] for s in row.get("datatypeScores", [])
                                if s.get("id") == "genetic_association"), 0.0)
                return {"found": True, "overall": float(row.get("score", 0.0)),
                        "genetic": float(genetic), "target": gene, "disease": disease,
                        "ensembl": t, "efo": dz}
            except Exception:
                continue
        return {"found": False, "overall": 0.0, "genetic": 0.0}
