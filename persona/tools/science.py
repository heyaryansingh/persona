"""Scientific tool clients (v6 P7) — typed access to public research databases, so the persona can
ground its work in real structured biology (not just prose it read). Every call goes through the
rate-limited + cached IngestService; fetching happens OUTSIDE the sandbox (which stays --network
none). This is the 'interface with research tools automatically' capability — wired into the
analyst's tool-use loop so an investigation can pull real evidence on demand.

No API keys required for these endpoints (NCBI uses the optional key if present for a higher rate).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .. import config
from ..ingest.service import service


# --- GEO / dataset resolution (PRD F3.9) --------------------------------------------------------
# The acting loop needs to resolve a GEO accession (GSEnnnnn) to on-disk metadata before it can
# stage a reanalysis. This is the OFFLINE half: parse a local cache dir if present, else return
# found:false with a seam for the (later) live NCBI/GEO fetch. NO network call here by design —
# science.py fetching goes through the rate-limited IngestService, and F3.9's online step is
# separate. Cache layout: one GEO SOFT file (or .soft/.txt) per series, named <GSE_ID>.soft.
# SOFT is GEO's canonical plain-text serialization, so a real `geo_online_fetch` can drop files
# here and geo_lookup/geo_search parse them unchanged.
GEO_CACHE_DIR = Path(os.environ.get("PERSONA_GEO_CACHE", str(config.DATASETS_DIR / "geo")))


def _geo_cache_file(gse_id: str) -> Path | None:
    """Locate a cached SOFT file for a GSE id, tolerating common extensions. None if absent."""
    if not GEO_CACHE_DIR.is_dir():
        return None
    for ext in (".soft", ".txt", ".soft.txt", ""):
        p = GEO_CACHE_DIR / f"{gse_id}{ext}"
        if p.is_file():
            return p
    return None


def _parse_geo_soft(path: Path, gse_id: str) -> dict:
    """Parse the handful of fields F3.9 needs from a GEO SOFT text file. Deterministic.
    n_samples is counted from !Series_sample_id lines (one per GSM) — GEO's own way of listing a
    series' samples, so it's a definition, not a heuristic."""
    title = platform = None
    n_samples = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if key == "!Series_sample_id":
            n_samples += 1
        elif key == "!Series_title" and title is None:
            title = val
        elif key in ("!Series_platform_id", "!Platform_geo_accession") and platform is None:
            platform = val
    return {"gse_id": gse_id, "title": title, "platform": platform,
            "n_samples": n_samples, "found": True, "source": f"cache:{path.name}"}


def geo_lookup(gse_id: str) -> dict:
    """Resolve a GEO series accession to on-disk metadata (F3.9). OFFLINE: reads the local SOFT
    cache. If nothing is cached, returns found:false with a network TODO seam — the live GEO fetch
    is a later online step, never triggered here."""
    gse_id = (gse_id or "").strip().upper()
    if not re.fullmatch(r"GSE\d+", gse_id):
        return {"gse_id": gse_id, "title": None, "platform": None, "n_samples": 0,
                "found": False, "source": "invalid_id"}
    path = _geo_cache_file(gse_id)
    if path is None:
        # TODO(F3.9-online): fetch SOFT from NCBI GEO via IngestService (e.g.
        # https://ftp.ncbi.nlm.nih.gov/geo/series/<GSExxx>nnn/<GSE>/soft/<GSE>_family.soft.gz),
        # write it into GEO_CACHE_DIR, then re-parse. Kept out of the offline path on purpose.
        return {"gse_id": gse_id, "title": None, "platform": None, "n_samples": 0,
                "found": False, "source": "not_cached"}
    return _parse_geo_soft(path, gse_id)


def geo_search(query: str, field: str | None = None) -> list[dict]:
    """Search the local GEO cache (F3.9), returning geo_lookup-shaped hits. OFFLINE substring match
    over cached series. `field` restricts matching to one of gse_id/title/platform; default matches
    any. Empty list when the cache is absent or nothing matches — no network."""
    q = (query or "").strip().lower()
    if not q or not GEO_CACHE_DIR.is_dir():
        return []
    fields = (field,) if field in ("gse_id", "title", "platform") else ("gse_id", "title", "platform")
    hits: list[dict] = []
    seen: set[str] = set()
    for path in sorted(GEO_CACHE_DIR.iterdir()):
        m = re.match(r"(GSE\d+)", path.name)
        if not path.is_file() or not m or m.group(1) in seen:
            continue
        rec = geo_lookup(m.group(1))
        if not rec.get("found"):
            continue
        if any(q in str(rec.get(f) or "").lower() for f in fields):
            seen.add(rec["gse_id"])
            hits.append(rec)
    return hits


def open_targets(disease_or_gene: str, size: int = 12) -> dict:
    """Open Targets (GraphQL): top gene<->disease associations for a search term."""
    q = ("query($q:String!){search(queryString:$q,entityNames:[\"disease\",\"target\"],"
         "page:{index:0,size:1}){hits{id entity name}}}")
    # resolve the entity id first, then pull associations
    try:
        r = service().post_json("https://api.platform.opentargets.org/api/v4/graphql",
                                {"query": q, "variables": {"q": disease_or_gene}}, retries=1, timeout=12)
        hits = (((r or {}).get("data") or {}).get("search") or {}).get("hits") or []
        if not hits:
            return {"ok": True, "query": disease_or_gene, "hits": [], "note": "no entity match"}
        top = hits[0]
        ent, eid, name = top.get("entity"), top.get("id"), top.get("name")
        if ent == "disease":
            aq = ("query($id:String!,$n:Int!){disease(efoId:$id){name associatedTargets(page:{index:0,"
                  "size:$n}){rows{target{approvedSymbol} score}}}}")
            ar = service().post_json("https://api.platform.opentargets.org/api/v4/graphql",
                                     {"query": aq, "variables": {"id": eid, "n": size}}, retries=1, timeout=12)
            rows = ((((ar.get("data") or {}).get("disease") or {}).get("associatedTargets") or {})
                    .get("rows") or [])
            assoc = [{"target": x["target"]["approvedSymbol"], "score": round(x["score"], 3)}
                     for x in rows]
            return {"ok": True, "entity": "disease", "name": name, "associations": assoc}
        else:
            aq = ("query($id:String!,$n:Int!){target(ensemblId:$id){approvedSymbol associatedDiseases("
                  "page:{index:0,size:$n}){rows{disease{name} score}}}}")
            ar = service().post_json("https://api.platform.opentargets.org/api/v4/graphql",
                                     {"query": aq, "variables": {"id": eid, "n": size}}, retries=1, timeout=12)
            rows = ((((ar.get("data") or {}).get("target") or {}).get("associatedDiseases") or {})
                    .get("rows") or [])
            assoc = [{"disease": x["disease"]["name"], "score": round(x["score"], 3)} for x in rows]
            return {"ok": True, "entity": "target", "name": name, "associations": assoc}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def pubchem(compound: str) -> dict:
    """PubChem: canonical properties of a compound by name."""
    try:
        url = (f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{compound}/property/"
               f"MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName/JSON")
        r = service().get_json(url, retries=1, timeout=12)
        props = (r.get("PropertyTable") or {}).get("Properties") or []
        return {"ok": bool(props), "compound": compound, "properties": props[0] if props else {}}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def uniprot(query: str, size: int = 5) -> dict:
    """UniProt: proteins matching a query (accession, name, function)."""
    try:
        url = "https://rest.uniprot.org/uniprotkb/search"
        r = service().get_json(url, retries=1, params={"query": query, "size": size, "format": "json",
                                     "fields": "accession,id,protein_name,gene_names,organism_name"})
        out = []
        for it in (r.get("results") or []):
            out.append({"accession": it.get("primaryAccession"),
                        "name": (((it.get("proteinDescription") or {}).get("recommendedName") or {})
                                 .get("fullName") or {}).get("value"),
                        "gene": next((g.get("geneName", {}).get("value")
                                      for g in (it.get("genes") or [])), None),
                        "organism": (it.get("organism") or {}).get("scientificName")})
        return {"ok": True, "query": query, "proteins": out}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def clinical_trials(condition: str, size: int = 8) -> dict:
    """ClinicalTrials.gov (API v2): recent trials for a condition."""
    try:
        url = "https://clinicaltrials.gov/api/v2/studies"
        r = service().get_json(url, retries=1, params={"query.cond": condition, "pageSize": size,
                                     "fields": "NCTId,BriefTitle,OverallStatus,Phase"})
        out = []
        for s in (r.get("studies") or []):
            p = (s.get("protocolSection") or {})
            idm = (p.get("identificationModule") or {})
            stm = (p.get("statusModule") or {})
            dm = (p.get("designModule") or {})
            out.append({"nct": idm.get("nctId"), "title": idm.get("briefTitle"),
                        "status": stm.get("overallStatus"), "phase": (dm.get("phases") or [None])[0]})
        return {"ok": True, "condition": condition, "trials": out}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def ncbi_search(term: str, db: str = "pubmed", size: int = 8) -> dict:
    """NCBI E-utilities: esearch a database (pubmed, gds/GEO, gene, protein...)."""
    try:
        params = {"db": db, "term": term, "retmax": size, "retmode": "json", "sort": "relevance"}
        if config.NCBI_API_KEY:
            params["api_key"] = config.NCBI_API_KEY
        r = service().get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params, retries=1, timeout=12)
        ids = ((r.get("esearchresult") or {}).get("idlist")) or []
        return {"ok": True, "db": db, "term": term,
                "count": (r.get("esearchresult") or {}).get("count"), "ids": ids}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def literature_search(query: str, size: int = 8) -> dict:
    """OpenAlex: scholarly works on ANY topic (physics, economics, CS, materials, biology…) —
    title, year, DOI, citation count, authors. Domain-general structured evidence for any field."""
    try:
        size = max(1, min(int(size), 25))
        r = service().get_json("https://api.openalex.org/works", retries=1, timeout=12,
                               params={"search": query, "per_page": size,
                                       "select": "title,doi,publication_year,cited_by_count,authorships"})
        out = []
        for w in (r.get("results") or []):
            out.append({"title": w.get("title"),
                        "year": w.get("publication_year"),
                        "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                        "cited_by": w.get("cited_by_count"),
                        "authors": [(a.get("author") or {}).get("display_name")
                                    for a in (w.get("authorships") or [])][:5]})
        return {"ok": True, "query": query, "papers": out}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


# registry for the analyst's tool-use loop: name -> (fn, required arg keys)
REGISTRY = {
    "literature_search": (literature_search, ["query"]),   # domain-general (all fields)
    "open_targets": (open_targets, ["query"]),
    "pubchem": (pubchem, ["compound"]),
    "uniprot": (uniprot, ["query"]),
    "clinical_trials": (clinical_trials, ["condition"]),
    "ncbi_search": (ncbi_search, ["term"]),
    "geo_lookup": (geo_lookup, ["gse_id"]),          # F3.9: resolve a GEO accession to disk metadata
    "geo_search": (geo_search, ["query"]),           # F3.9: search the local GEO cache
}


def call(api: str, params: dict) -> dict:
    """Dispatch a science-tool call by name (used by the analyst tool loop)."""
    entry = REGISTRY.get(api)
    if not entry:
        return {"ok": False, "error": f"unknown api {api}"}
    fn = entry[0]
    try:
        if api == "literature_search":
            return fn(params.get("query") or params.get("term", ""), params.get("size", 8))
        if api == "open_targets":
            return fn(params.get("query") or params.get("disease") or params.get("gene", ""))
        if api == "pubchem":
            return fn(params.get("compound", ""))
        if api == "uniprot":
            return fn(params.get("query", ""))
        if api == "clinical_trials":
            return fn(params.get("condition") or params.get("query", ""))
        if api == "ncbi_search":
            return fn(params.get("term") or params.get("query", ""), params.get("db", "pubmed"))
        if api == "geo_lookup":
            return {"ok": True, **fn(params.get("gse_id") or params.get("id") or params.get("accession", ""))}
        if api == "geo_search":
            return {"ok": True, "hits": fn(params.get("query") or params.get("term", ""), params.get("field"))}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
    return {"ok": False, "error": "bad dispatch"}
