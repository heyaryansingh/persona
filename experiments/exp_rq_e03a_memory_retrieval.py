"""RQ-E03a: structural retrieval screening over the real Curie memory (no LLM calls).

This benchmark asks whether a retrieval method recovers the stored evidence records that were used
to auto-generate a query. It does *not* score biomedical truth, answer correctness, entailment, or
the scientific quality of a stored claim. Labels are structural document IDs, generated without a
model from claims, field notes, belief history, and immutable research-session traces.

The fixed ledger contains exactly 200 queries:
40 provenance, 30 temporal, 40 two-hop, 30 candidate-conflict, 30 field-note, and
30 session-reconstruction queries. Some categories necessarily reuse base records (only 18 claims
have multi-snapshot history, 23 field notes exist, and only two sessions exist). Thirty seeded
resamples therefore bootstrap *base_item_id clusters*, keeping all facets of a sampled base together.
The session category remains a two-session diagnostic even though it has 30 distinct event/artifact/
conclusion targets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import sqlite3
import statistics
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
CURIE = ROOT / "personas" / "curie-3c33"
SOURCES = CURIE / "sources"
NOTES = CURIE / "notes"
RUNS = CURIE / "runs"
HISTORY_DB = CURIE / ".persona" / "belief_history.db"
OUT_JSON = ROOT / "results" / "rq_e03a_memory_retrieval.json"
OUT_PNG = ROOT / "results" / "rq_e03a_memory_retrieval.png"
EMBED_CACHE = ROOT / "results" / "rq_e03a_memory_retrieval_embeddings.npz"

SEEDS = 30
TOP_K = 10
RRF_DEPTH = 100
RRF_K = 60
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
DENSE_RESOURCE_GATE = {
    "observed_at": "2026-07-11T14:21:28-05:00",
    "wall_seconds": 229.45,
    "cpu_seconds": 3073.56,
    "working_set_bytes": 9_078_595_584,
    "embedding_cache_written": False,
    "outcome": "terminated at workstation resource ceiling before retrieval output",
}
DENSE_SAFE_SETTINGS = {
    "threads": 2,
    "lazy_load": True,
    "local_files_only": True,
    "batch_size": 32,
    "parallel": None,
    "invalidated_parent_only_microprobe": {
        "documents": 256, "wall_seconds": 29.60, "documents_per_second": 8.65,
        "reported_parent_working_set_bytes": 84_000_000,
        "valid_process_tree_memory_measurement": False,
        "reason": "parallel=0 spawned child workers whose RSS was omitted from the parent-only measurement",
    },
    "parallel_zero_reversal": {
        "child_python_workers_observed": 22,
        "outcome": "terminated before output after process-tree inspection showed parallel=0 means automatic workers",
        "decision": "use parallel=None for a single-process bounded run",
    },
}
QUOTAS = {
    "provenance": 40,
    "temporal": 30,
    "multi_hop": 40,
    "candidate_conflict": 30,
    "field_note": 30,
    "session_reconstruction": 30,
}

TOKEN_RE = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:a-z0-9]+", re.I)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their", "this",
    "to", "was", "were", "which", "with", "record", "records", "retrieve", "stored",
    "evidence", "find", "locate", "show", "what", "where", "which",
}


@dataclass
class Document:
    doc_id: str
    kind: str
    text: str
    summary: str
    timestamp: str = ""
    entities: tuple[str, ...] = ()
    links: set[str] = field(default_factory=set)
    meta: dict = field(default_factory=dict)


@dataclass
class Query:
    query_id: str
    category: str
    base_item_id: str
    facet_target_id: str
    text: str
    gold_doc_ids: tuple[str, ...]


def norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text or "").casefold().split())


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(norm(text)) if t not in STOP and len(t) > 1]


def clipped(text: str, n: int = 1200) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + " …"


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def stable_order(items: list, key, salt: str) -> list:
    return sorted(items, key=lambda item: stable_hash(f"{salt}|{key(item)}"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8", errors="strict"))


def correction_records() -> list[dict]:
    records = []
    for path in sorted(SOURCES.glob("*/claim_corrections.jsonl")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid correction JSON: {path}:{line_no}: {exc}") from exc
    return records


def statement(claim: dict) -> str:
    relation = str(claim.get("relation", "relates to")).replace("_", " ")
    return f"{claim.get('subject', '')} {relation} {claim.get('object', '')}".strip()


def canon_key(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().strip()).strip(" .,:;")


def load_claim_documents() -> tuple[list[Document], dict[str, dict], dict[str, set[str]]]:
    docs, claims, doi_docs, docs_by_id = [], {}, defaultdict(set), {}
    canon_path = CURIE / ".persona" / "canon.json"
    if not canon_path.exists():
        raise RuntimeError(f"canonical claim reconstruction requires {canon_path}")
    canon_cache = read_json(canon_path).get("cache", {})
    for claims_path in sorted(SOURCES.glob("*/claims.jsonl")):
        meta_path = claims_path.with_name("meta.json")
        meta = read_json(meta_path) if meta_path.exists() else {}
        source_doi = norm(meta.get("doi", ""))
        corrections = {}
        correction_path = claims_path.with_name("claim_corrections.jsonl")
        if correction_path.exists():
            for correction_line in correction_path.read_text(encoding="utf-8").splitlines():
                correction = json.loads(correction_line)
                corrections[correction["source_claim_id"]] = correction
        for line_no, line in enumerate(claims_path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if not line.strip():
                continue
            try:
                claim = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid claim JSON: {claims_path}:{line_no}: {exc}") from exc
            source_claim_id = str(claim.get("claim_id", "")).strip()
            if not source_claim_id:
                raise RuntimeError(f"claim without claim_id: {claims_path}:{line_no}")
            correction = corrections.get(source_claim_id)
            if correction:
                claim = {**claim, "effect_sign": correction["new_effect_sign"],
                         "provenance": "CORRECTED_EXTRACTION", "correction": correction}
            canonical_subject = canon_cache.get(canon_key(claim.get("subject", "")),
                                                canon_key(claim.get("subject", "")))
            canonical_object = canon_cache.get(canon_key(claim.get("object", "")),
                                               canon_key(claim.get("object", "")))
            sign = claim.get("effect_sign", "na")
            claim_id = "clm_" + hashlib.sha1(
                f"{canonical_subject}|{canonical_object}|{sign}".encode()
            ).hexdigest()[:12]
            claim = {**claim, "claim_id": claim_id, "source_claim_id": source_claim_id,
                     "subject": canonical_subject, "object": canonical_object}
            doi = norm(meta.get("doi") or claim.get("doi") or "")
            doc_id = f"claim:{claim_id}"
            if claim_id in claims:
                existing = claims[claim_id]
                structural = (norm(claim.get("subject", "")), norm(claim.get("object", "")),
                              claim.get("effect_sign"))
                prior = (norm(existing.get("subject", "")), norm(existing.get("object", "")),
                         existing.get("effect_sign"))
                if structural != prior:
                    raise RuntimeError(f"claim_id collision has incompatible structure: {claim_id}")
                source_line = (f" Additional evidence source: {meta.get('title', '')}; DOI {doi}; "
                               f"quote {claim.get('quote', '')}; confidence {claim.get('confidence', '')}.")
                docs_by_id[doc_id].text += source_line
                docs_by_id[doc_id].summary += f"; additional DOI {doi}"
                existing.setdefault("source_records", []).append(
                    {"doi": doi, "title": meta.get("title", ""), "quote": claim.get("quote", ""),
                     "source_id": claim.get("source_id", meta.get("id", "")),
                     "source_claim_id": source_claim_id, "correction_applied": bool(correction)}
                )
                existing.setdefault("dois", set()).add(doi)
                if doi:
                    doi_docs[doi].add(doc_id)
                continue
            full = (
                f"Evidence claim {claim_id}. {statement(claim)}. Stored effect sign "
                f"{claim.get('effect_sign', 'na')}. Provenance {claim.get('provenance', 'READ')}. "
                f"Exact quote: {claim.get('quote', '')}. Source: {meta.get('title', '')}. "
                f"DOI {doi}. Source ID {claim.get('source_id', meta.get('id', ''))}. "
                f"Published {meta.get('year', '')}. Affiliations: "
                f"{', '.join(claim.get('affiliations') or meta.get('affiliations') or [])}."
            )
            summary = (
                f"{statement(claim)}; sign {claim.get('effect_sign', 'na')}; "
                f"source {meta.get('title', '')}; DOI {doi}; provenance {claim.get('provenance', 'READ')}"
            )
            entities = tuple(e for e in (norm(claim.get("subject", "")), norm(claim.get("object", ""))) if e)
            timestamp = str(claim.get("extracted_at") or meta.get("read_at") or meta.get("year") or "")
            enriched = {**claim, "doc_id": doc_id, "doi": doi, "dois": {doi} if doi else set(),
                        "source_meta": meta, "source_dir": claims_path.parent.name,
                        "source_records": [{"doi": doi, "title": meta.get("title", ""),
                                            "quote": claim.get("quote", ""),
                                            "source_id": claim.get("source_id", meta.get("id", "")),
                                            "source_claim_id": source_claim_id,
                                            "correction_applied": bool(correction)}]}
            claims[claim_id] = enriched
            doc = Document(doc_id, "claim", full, summary, timestamp, entities,
                           meta={"claim_id": claim_id, "doi": doi,
                                 "effect_sign": claim.get("effect_sign"),
                                 "relation": claim.get("relation", "")})
            docs.append(doc)
            docs_by_id[doc_id] = doc
            if doi:
                doi_docs[doi].add(doc_id)
        if source_doi and source_doi not in doi_docs:
            doi_docs[source_doi] = set()
    if len(claims) < QUOTAS["provenance"]:
        raise RuntimeError(f"provenance contract needs {QUOTAS['provenance']} claims; found {len(claims)}")
    return docs, claims, doi_docs


def note_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback.replace("-", " ")


def note_summary(text: str, heading: str) -> str:
    paragraphs = []
    for block in re.split(r"\n\s*\n", text):
        clean = " ".join(block.split())
        if clean and not clean.startswith("#") and not clean.startswith("## sources"):
            paragraphs.append(clean)
        if sum(map(len, paragraphs)) >= 900:
            break
    return clipped(f"{heading}. {' '.join(paragraphs)}", 1000)


def load_note_documents(doi_docs: dict[str, set[str]]) -> tuple[list[Document], list[dict]]:
    docs, notes = [], []
    for path in sorted(NOTES.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        heading = note_heading(text, path.stem)
        dois = sorted({norm(d.rstrip(".,;)]}")) for d in DOI_RE.findall(text)})
        links = {doc_id for doi in dois for doc_id in doi_docs.get(doi, ())}
        doc_id = f"note:{path.name}"
        doc = Document(doc_id, "field_note", text, note_summary(text, heading),
                       links=links, meta={"path": str(path.relative_to(ROOT)),
                                          "heading": heading, "dois": dois})
        docs.append(doc)
        notes.append({"doc": doc, "heading": heading, "dois": dois, "text": text})
    if not notes:
        raise RuntimeError("field-note category has no Curie notes")
    return docs, notes


def readonly_db(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise RuntimeError(f"required read-only database missing: {path}")
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_history_documents(claims: dict[str, dict]) -> tuple[list[Document], list[dict]]:
    grouped = defaultdict(list)
    with readonly_db(HISTORY_DB) as conn:
        rows = conn.execute(
            "SELECT id, claim_id, ts, confidence, support, independent, contra "
            "FROM belief_history ORDER BY claim_id, id"
        ).fetchall()
    for row in rows:
        grouped[row["claim_id"]].append(dict(row))
    docs, histories = [], []
    for claim_id, series in sorted(grouped.items()):
        claim = claims.get(claim_id)
        if claim is None:
            continue
        first, last = series[0], series[-1]
        doc_id = f"history:{claim_id}"
        series_text = "; ".join(
            f"{r['ts']}: confidence {r['confidence']:.6g}, independent sources {r['independent']}, "
            f"support {r['support']}, contra {r['contra']}" for r in series
        )
        full = f"Belief history for {statement(claim)} ({claim_id}). {series_text}."
        summary = (
            f"History of {statement(claim)}: {len(series)} snapshots; confidence "
            f"{first['confidence']:.6g} to {last['confidence']:.6g}; independent sources "
            f"{first['independent']} to {last['independent']}; {first['ts']} to {last['ts']}"
        )
        entities = tuple(e for e in (norm(claim.get("subject", "")), norm(claim.get("object", ""))) if e)
        doc = Document(doc_id, "belief_history", full, summary, str(last["ts"]), entities,
                       {f"claim:{claim_id}"}, {"claim_id": claim_id, "rows": len(series)})
        docs.append(doc)
        histories.append({"doc": doc, "claim": claim, "rows": series})
    multi = [h for h in histories if len(h["rows"]) >= 2]
    if not multi:
        raise RuntimeError("temporal category requires claims with at least two history snapshots")
    changelog = CURIE / "self" / "CHANGELOG.md"
    if changelog.exists():
        text = changelog.read_text(encoding="utf-8", errors="replace")
        docs.append(Document("history:self-changelog", "self_history", text, clipped(text, 1000)))
    return docs, histories


def payload_refs(value) -> set[str]:
    refs = set()
    if isinstance(value, dict):
        for child in value.values():
            refs |= payload_refs(child)
    elif isinstance(value, list):
        for child in value:
            refs |= payload_refs(child)
    elif isinstance(value, str):
        refs |= set(re.findall(r"(?:claim:clm_[a-z0-9]+|artifact:[0-9a-f]{64})", value, re.I))
    return refs


def event_summary(event: dict) -> str:
    kind, payload = event.get("kind", "event"), event.get("payload") or {}
    turn = payload.get("turn")
    if kind == "artifact_stored":
        detail = f"stored artifact {payload.get('name', '')} ({payload.get('media_type', '')})"
    elif kind == "evidence_retrieved":
        detail = f"retrieved {payload.get('claims', 0)} claims into {payload.get('artifact_id', '')}"
    elif kind == "model_request":
        detail = f"requested research turn {turn}; {len(payload.get('allowed_claim_ids') or [])} allowed claims"
    elif kind == "model_response":
        tools = [b.get("name") for b in payload.get("blocks") or [] if b.get("type") == "tool_use"]
        detail = (f"model response turn {turn}; {payload.get('model', '')}; "
                  f"{payload.get('input_tokens', 0)} input and {payload.get('output_tokens', 0)} output tokens; "
                  f"cost {payload.get('cost_usd', 0)}; tools {', '.join(t for t in tools if t)}")
    elif kind == "tool_call":
        detail = f"tool call {payload.get('tool', '')} on turn {turn}; {clipped(json.dumps(payload.get('input')), 500)}"
    elif kind in {"finish_rejected", "verifier_verdict"}:
        detail = f"{payload.get('verdict', '')} {payload.get('reason', '')}".strip()
    elif kind in {"finish_accepted", "session_finished"}:
        title = (payload.get("input") or {}).get("title") or payload.get("title", "")
        detail = f"{payload.get('status', '')} {title}".strip()
    elif kind == "session_started":
        detail = f"started question {payload.get('question', '')} with {payload.get('model', '')}"
    else:
        detail = clipped(json.dumps(payload, ensure_ascii=False, default=str), 700)
    return f"Trace event {event.get('event_id')}: {kind}. {detail}".strip()


def artifact_text(root: Path, artifact: dict) -> str:
    path = root / str(artifact.get("path", ""))
    if not path.is_file():
        return ""
    if path.suffix.lower() not in {".md", ".txt", ".json", ".jsonl", ".py", ".csv", ".tsv", ".tex", ".log"}:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:30_000]


def load_session_documents() -> tuple[list[Document], list[dict]]:
    docs, sessions = [], []
    for session_path in sorted(RUNS.glob("*/session.json")):
        session_root = session_path.parent
        events_path = session_root / "events.jsonl"
        if not events_path.exists():
            raise RuntimeError(f"session missing events.jsonl: {session_root.name}")
        meta = read_json(session_path)
        events = []
        for line_no, line in enumerate(events_path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid session event {events_path}:{line_no}: {exc}") from exc
        sid = str(meta.get("session_id") or session_root.name)
        session_doc_id = f"session:{sid}"
        session_children, artifact_lookup, candidate_facets = set(), {}, []
        title = meta.get("title") or meta.get("question") or sid
        summary = (f"Research session {title}. Question: {meta.get('question', '')}. Status "
                   f"{meta.get('status', '')}. Model {meta.get('model', '')}. Started "
                   f"{meta.get('started_at', '')}; finished {meta.get('finished_at', '')}; "
                   f"verification {(meta.get('verification') or {}).get('verdict', 'unverified')}.")
        session_doc = Document(session_doc_id, "session", summary, summary,
                               str(meta.get("started_at", "")), meta={"session_id": sid})

        for artifact in meta.get("artifacts") or []:
            sha = str(artifact.get("sha256", ""))
            if not re.fullmatch(r"[0-9a-f]{64}", sha):
                continue
            doc_id = f"session-artifact:{sid}:{sha}"
            content = artifact_text(session_root, artifact)
            artifact_summary = (f"Session artifact {artifact.get('name', '')}; media type "
                                f"{artifact.get('media_type', '')}; {artifact.get('bytes', 0)} bytes; "
                                f"sha256 {sha}; from research session {title}.")
            doc = Document(doc_id, "session_artifact", f"{artifact_summary}\n{content}",
                           f"{artifact_summary} {clipped(content, 500)}", meta={**artifact, "session_id": sid})
            docs.append(doc)
            session_children.add(doc_id)
            artifact_lookup[str(artifact.get("id", f"artifact:{sha}"))] = doc_id
            candidate_facets.append({
                "target": doc_id,
                "kind": "artifact",
                "description": (f"artifact file {artifact.get('name', '')} with media type "
                                f"{artifact.get('media_type', '')}").strip(),
            })

        for event in events:
            event_id = event.get("event_id")
            doc_id = f"session-event:{sid}:{event_id}"
            ev_summary = event_summary(event)
            payload = json.dumps(event.get("payload") or {}, ensure_ascii=False, default=str)
            links = {session_doc_id}
            for ref in payload_refs(event.get("payload") or {}):
                if ref.startswith("claim:"):
                    links.add(ref)
                elif ref in artifact_lookup:
                    links.add(artifact_lookup[ref])
            doc = Document(doc_id, "session_event", f"{ev_summary}. Payload: {clipped(payload, 6000)}",
                           ev_summary, str(event.get("at", "")), links,
                           {"session_id": sid, "event_id": event_id, "event_kind": event.get("kind")})
            docs.append(doc)
            session_children.add(doc_id)
            if event.get("kind") in {
                "evidence_retrieved", "tool_call", "finish_rejected", "finish_accepted",
                "session_finished", "verifier_verdict", "session_started",
            }:
                payload = event.get("payload") or {}
                descriptor = f"trace kind {event.get('kind')}"
                if payload.get("turn") is not None:
                    descriptor += f" on turn {payload.get('turn')}"
                if payload.get("tool"):
                    descriptor += f" using tool {payload.get('tool')}"
                if payload.get("verdict"):
                    descriptor += f" with verdict {payload.get('verdict')}"
                candidate_facets.append({"target": doc_id, "kind": "event", "description": descriptor})

        for index, conclusion in enumerate(meta.get("conclusions") or []):
            doc_id = f"session-conclusion:{sid}:{index}"
            evidence_ids = [str(e) for e in conclusion.get("evidence_ids") or []]
            links = {session_doc_id}
            for ref in evidence_ids:
                if ref.startswith("claim:"):
                    links.add(ref)
                elif ref in artifact_lookup:
                    links.add(artifact_lookup[ref])
            text = (f"Session conclusion {index + 1}: {conclusion.get('claim', '')}. Status "
                    f"{conclusion.get('status', '')}; confidence {conclusion.get('confidence', '')}; "
                    f"evidence IDs {', '.join(evidence_ids)}. Session {title}.")
            docs.append(Document(doc_id, "session_conclusion", text, clipped(text, 900),
                                 str(meta.get("finished_at", "")), links,
                                 {"session_id": sid, "conclusion_index": index}))
            session_children.add(doc_id)
            confidence = float(conclusion.get("confidence", 0) or 0)
            band = "high" if confidence >= .8 else "moderate" if confidence >= .5 else "low"
            candidate_facets.append({
                "target": doc_id, "kind": "conclusion",
                "description": f"conclusion slot {index + 1} with status {conclusion.get('status', '')} and {band} confidence",
            })

        session_doc.links = session_children
        docs.append(session_doc)
        candidate_facets.append({"target": session_doc_id, "kind": "session",
                                 "description": f"session summary for question {meta.get('question', '')}"})
        sessions.append({"session_id": sid, "title": title, "question": meta.get("question", ""),
                         "doc": session_doc, "facets": candidate_facets, "events": len(events),
                         "artifacts": len(meta.get("artifacts") or [])})
    if not sessions:
        raise RuntimeError("session-reconstruction category has no immutable Curie sessions")
    return docs, sessions


def provenance_queries(claims: dict[str, dict]) -> list[Query]:
    candidates = [c for c in claims.values() if c.get("doi") and c.get("quote") and
                  c.get("subject") and c.get("object")]
    candidates = stable_order(candidates, lambda c: c["claim_id"], "provenance")
    if len(candidates) < QUOTAS["provenance"]:
        raise RuntimeError(f"need {QUOTAS['provenance']} provenance bases, found {len(candidates)}")
    out = []
    for i, claim in enumerate(candidates[:QUOTAS["provenance"]]):
        relation = str(claim.get("relation", "relates to")).replace("_", " ")
        text = (f"Which evidence record says {claim.get('subject')} {relation} {claim.get('object')} "
                f"and attributes it to DOI {claim.get('doi')}?")
        out.append(Query(f"provenance-{i:03}", "provenance", claim["claim_id"],
                         f"claim:{claim['claim_id']}", text, (f"claim:{claim['claim_id']}",)))
    return out


def temporal_queries(histories: list[dict]) -> list[Query]:
    bases = stable_order([h for h in histories if len(h["rows"]) >= 2],
                         lambda h: h["claim"]["claim_id"], "temporal")
    facets = []
    for facet in ("earliest", "latest", "change", "independent"):
        for h in bases:
            rows, claim = h["rows"], h["claim"]
            first, last = rows[0], rows[-1]
            if facet == "earliest":
                detail = "its earliest recorded confidence snapshot"
            elif facet == "latest":
                detail = "its latest recorded confidence snapshot"
            elif facet == "change":
                detail = "the direction of confidence change from first to latest snapshot"
            else:
                detail = "the change in independent-source count across snapshots"
            facets.append((h, facet, detail))
    if len(facets) < QUOTAS["temporal"]:
        raise RuntimeError(f"need {QUOTAS['temporal']} distinct temporal facets, found {len(facets)}")
    out = []
    for i, (h, facet, detail) in enumerate(facets[:QUOTAS["temporal"]]):
        cid = h["claim"]["claim_id"]
        text = f"Retrieve the belief-history record for {statement(h['claim'])}, showing {detail}."
        out.append(Query(f"temporal-{i:03}", "temporal", cid, f"history:{cid}:{facet}",
                         text, (f"history:{cid}",)))
    return out


def multi_hop_queries(claims: dict[str, dict]) -> list[Query]:
    incoming, outgoing = defaultdict(list), defaultdict(list)
    for claim in claims.values():
        subject, obj = norm(claim.get("subject", "")), norm(claim.get("object", ""))
        if not subject or not obj or subject == obj:
            continue
        outgoing[subject].append(claim)
        incoming[obj].append(claim)
    candidates, seen = [], set()
    for bridge in sorted(set(incoming) & set(outgoing)):
        left = stable_order(incoming[bridge], lambda c: c["claim_id"], f"left:{bridge}")[:8]
        right = stable_order(outgoing[bridge], lambda c: c["claim_id"], f"right:{bridge}")[:8]
        for a in left:
            for b in right:
                start, end = norm(a.get("subject", "")), norm(b.get("object", ""))
                if a["claim_id"] == b["claim_id"] or start == end or not start or not end:
                    continue
                base = f"{a['claim_id']}|{b['claim_id']}"
                if base not in seen:
                    seen.add(base)
                    candidates.append((a, b, bridge, base))
    candidates = stable_order(candidates, lambda x: x[3], "multi-hop")
    if len(candidates) < QUOTAS["multi_hop"]:
        raise RuntimeError(f"need {QUOTAS['multi_hop']} two-hop paths, found {len(candidates)}")
    out = []
    for i, (a, b, bridge, base) in enumerate(candidates[:QUOTAS["multi_hop"]]):
        r1 = str(a.get("relation", "relates to")).replace("_", " ")
        r2 = str(b.get("relation", "relates to")).replace("_", " ")
        text = (f"Retrieve the two evidence records forming this path: {a.get('subject')} {r1} "
                f"{a.get('object')}, then {b.get('subject')} {r2} {b.get('object')}. "
                f"The bridge entity is {bridge}.")
        gold = (f"claim:{a['claim_id']}", f"claim:{b['claim_id']}")
        out.append(Query(f"multi-hop-{i:03}", "multi_hop", base,
                         f"path:{stable_hash(base)[:16]}", text, gold))
    return out


def conflict_queries(claims: dict[str, dict]) -> list[Query]:
    groups = defaultdict(lambda: {"+": [], "-": []})
    for claim in claims.values():
        sign = claim.get("effect_sign")
        if sign not in {"+", "-"}:
            continue
        key = (norm(claim.get("subject", "")), norm(claim.get("object", "")))
        if all(key):
            groups[key][sign].append(claim)
    candidates = []
    for (subject, obj), sides in groups.items():
        if not sides["+"] or not sides["-"]:
            continue
        gold = tuple(sorted(f"claim:{c['claim_id']}" for sign in ("+", "-") for c in sides[sign]))
        if len(gold) <= TOP_K:
            candidates.append((subject, obj, sides, gold))
    candidates = stable_order(candidates, lambda x: f"{x[0]}|{x[1]}", "conflict")
    if len(candidates) < QUOTAS["candidate_conflict"]:
        raise RuntimeError(
            f"need {QUOTAS['candidate_conflict']} conflict groups with <= top-k evidence, found {len(candidates)}"
        )
    out = []
    for i, (subject, obj, sides, gold) in enumerate(candidates[:QUOTAS["candidate_conflict"]]):
        base = f"{subject}|{obj}"
        text = (f"Retrieve every claim record that stores opposing positive and negative effect signs "
                f"for the same candidate-conflict relationship: {subject} to {obj}.")
        out.append(Query(f"conflict-{i:03}", "candidate_conflict", base,
                         f"conflict:{stable_hash(base)[:16]}", text, gold))
    return out


def distinctive_note_terms(notes: list[dict]) -> dict[str, list[str]]:
    doc_tokens = {n["doc"].doc_id: tokenize(n["text"]) for n in notes}
    df = Counter(t for toks in doc_tokens.values() for t in set(toks))
    total = len(notes)
    result = {}
    for doc_id, toks in doc_tokens.items():
        tf = Counter(toks)
        ranked = sorted(tf, key=lambda t: (-(1 + math.log(tf[t])) * math.log((total + 1) / (df[t] + 1)), t))
        result[doc_id] = [t for t in ranked if len(t) >= 4][:7]
    return result


def field_note_queries(notes: list[dict]) -> list[Query]:
    terms = distinctive_note_terms(notes)
    bases = stable_order(notes, lambda n: n["doc"].doc_id, "field-note")
    facets = []
    for n in bases:
        facets.append((n, "heading", f"the synthesis titled {n['heading']}"))
    for n in bases:
        keywords = ", ".join(terms[n["doc"].doc_id][:5])
        facets.append((n, "distinctive-terms", f"the distinctive topics {keywords}"))
    for n in bases:
        if n["dois"]:
            facets.append((n, "cited-doi", f"a field synthesis citing DOI {n['dois'][0]}"))
    if len(facets) < QUOTAS["field_note"]:
        raise RuntimeError(f"need {QUOTAS['field_note']} field-note facets, found {len(facets)}")
    out = []
    for i, (n, facet, detail) in enumerate(facets[:QUOTAS["field_note"]]):
        doc_id = n["doc"].doc_id
        text = f"Locate the Curie field note containing {detail}; return the note rather than a source paper."
        out.append(Query(f"field-note-{i:03}", "field_note", doc_id,
                         f"{doc_id}:{facet}", text, (doc_id,)))
    return out


def session_queries(sessions: list[dict]) -> list[Query]:
    ordered = []
    per_session = {}
    for session in sessions:
        facets = stable_order(session["facets"], lambda f: f["target"], f"session:{session['session_id']}")
        seen_descriptions, unique = set(), []
        for facet in facets:
            key = (facet["kind"], norm(facet["description"]))
            if key not in seen_descriptions:
                seen_descriptions.add(key)
                unique.append(facet)
        per_session[session["session_id"]] = unique
    positions = {s["session_id"]: 0 for s in sessions}
    while len(ordered) < QUOTAS["session_reconstruction"]:
        progressed = False
        for session in sessions:
            sid = session["session_id"]
            pos = positions[sid]
            if pos < len(per_session[sid]):
                ordered.append((session, per_session[sid][pos]))
                positions[sid] += 1
                progressed = True
                if len(ordered) == QUOTAS["session_reconstruction"]:
                    break
        if not progressed:
            break
    targets = {facet["target"] for _, facet in ordered}
    if len(ordered) < QUOTAS["session_reconstruction"] or len(targets) < QUOTAS["session_reconstruction"]:
        raise RuntimeError(
            f"session contract needs {QUOTAS['session_reconstruction']} distinct event/artifact/"
            f"conclusion targets; found {len(targets)} across {len(sessions)} sessions"
        )
    out = []
    for i, (session, facet) in enumerate(ordered):
        text = (f"Reconstruct the stored research trace for the question {session['question']}. "
                f"Retrieve the specific {facet['kind']} record: {facet['description']}.")
        out.append(Query(f"session-{i:03}", "session_reconstruction", session["session_id"],
                         facet["target"], text, (facet["target"],)))
    return out


class SparseIndex:
    def __init__(self, texts: list[str]):
        self.n = len(texts)
        self.lengths = np.zeros(self.n, dtype=np.float32)
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for index, text in enumerate(texts):
            counts = Counter(tokenize(text))
            self.lengths[index] = sum(counts.values())
            for term, count in counts.items():
                self.postings[term].append((index, count))
        self.avg_len = float(self.lengths.mean()) or 1.0
        self.estimated_index_bytes = int(
            self.lengths.nbytes + sum(len(term.encode("utf-8")) + 8 * len(rows)
                                     for term, rows in self.postings.items())
        )

    def raw_scores(self, query: str) -> np.ndarray:
        scores = np.zeros(self.n, dtype=np.float32)
        for term in set(tokenize(query)):
            for index, tf in self.postings.get(term, ()):
                scores[index] += min(tf, 3)
        return scores / np.sqrt(np.maximum(self.lengths, 1.0))

    def bm25_scores(self, query: str, k1: float = 1.5, b: float = 0.75) -> np.ndarray:
        scores = np.zeros(self.n, dtype=np.float32)
        for term in set(tokenize(query)):
            posting = self.postings.get(term, ())
            if not posting:
                continue
            df = len(posting)
            idf = math.log(1 + (self.n - df + 0.5) / (df + 0.5))
            for index, tf in posting:
                denom = tf + k1 * (1 - b + b * self.lengths[index] / self.avg_len)
                scores[index] += idf * tf * (k1 + 1) / denom
        return scores


def normalized(values: np.ndarray) -> np.ndarray:
    maximum = float(values.max(initial=0))
    return values / maximum if maximum > 0 else values.copy()


def build_graph(docs: list[Document]) -> tuple[list[set[int]], dict[str, list[int]], dict[str, tuple[str, ...]]]:
    index = {doc.doc_id: i for i, doc in enumerate(docs)}
    adjacency = [set() for _ in docs]
    entities = defaultdict(list)
    entity_tokens = {}
    for i, doc in enumerate(docs):
        for linked in doc.links:
            j = index.get(linked)
            if j is not None and i != j:
                adjacency[i].add(j)
                adjacency[j].add(i)
        for entity in set(doc.entities):
            et = tuple(tokenize(entity))
            if et and sum(map(len, et)) >= 4:
                entities[entity].append(i)
                entity_tokens[entity] = et
    return adjacency, entities, entity_tokens


def temporal_graph_scores(query: str, lexical: np.ndarray, docs: list[Document],
                          adjacency: list[set[int]], entities: dict[str, list[int]],
                          entity_tokens: dict[str, tuple[str, ...]]) -> np.ndarray:
    base = normalized(lexical)
    structural = np.zeros(len(docs), dtype=np.float32)
    qtokens = set(tokenize(query))
    for entity, indices in entities.items():
        et = entity_tokens[entity]
        if set(et).issubset(qtokens):
            boost = min(1.0, 0.25 + 0.12 * len(et))
            structural[indices] += boost
    seed_order = np.argsort(-base, kind="stable")[:8]
    for seed in seed_order:
        seed_weight = float(base[seed])
        for neighbor in adjacency[int(seed)]:
            structural[neighbor] += 0.55 * seed_weight
            for second in adjacency[neighbor]:
                structural[second] += 0.16 * seed_weight
    temporal = np.zeros(len(docs), dtype=np.float32)
    years = set(YEAR_RE.findall(query))
    if years:
        for i, doc in enumerate(docs):
            if any(year in doc.timestamp for year in years):
                temporal[i] = 1.0
    return 0.62 * base + 0.28 * normalized(structural) + 0.10 * temporal


def dense_embeddings(docs: list[Document], queries: list[Query]) -> tuple[np.ndarray | None, np.ndarray | None, dict]:
    dense_texts = [clipped(doc.text, 4000) for doc in docs]
    query_texts = [q.text for q in queries]
    digest = hashlib.sha256()
    digest.update(EMBED_MODEL.encode())
    digest.update(b"|fastembed-passage-query-v3|threads2|lazy|batch32|parallel-none|local-only")
    for doc, text in zip(docs, dense_texts):
        digest.update(doc.doc_id.encode()); digest.update(b"\0"); digest.update(text.encode()); digest.update(b"\0")
    for query, text in zip(queries, query_texts):
        digest.update(query.query_id.encode()); digest.update(b"\0"); digest.update(text.encode()); digest.update(b"\0")
    fingerprint = digest.hexdigest()
    if EMBED_CACHE.exists():
        try:
            cached = np.load(EMBED_CACHE, allow_pickle=False)
            if (str(cached["fingerprint"].item()) == fingerprint and
                    cached["documents"].shape[0] == len(docs) and
                    cached["queries"].shape[0] == len(queries)):
                return cached["documents"], cached["queries"], {
                    "available": True, "model": EMBED_MODEL, "cache_hit": True,
                    "cache": str(EMBED_CACHE.relative_to(ROOT)), "fingerprint": fingerprint,
                    "settings": DENSE_SAFE_SETTINGS, "failed_default_probe": DENSE_RESOURCE_GATE,
                }
        except Exception:
            pass
    if os.environ.get("PERSONA_E03A_SKIP_DENSE") == "1":
        return None, None, {
            "available": False, "model": EMBED_MODEL, "cache_hit": False,
            "settings": DENSE_SAFE_SETTINGS, "failed_default_probe": DENSE_RESOURCE_GATE,
            "reason": "Explicitly skipped by PERSONA_E03A_SKIP_DENSE=1.",
        }
    try:
        from fastembed import TextEmbedding
        model = TextEmbedding(EMBED_MODEL, threads=2, lazy_load=True, local_files_only=True)
        batch_size = int(os.environ.get("PERSONA_E03A_DENSE_BATCH_SIZE", "32"))
        doc_vecs = np.asarray(list(model.passage_embed(
            dense_texts, batch_size=batch_size, parallel=None)), dtype=np.float32)
        query_vecs = np.asarray(list(model.query_embed(
            query_texts, batch_size=batch_size, parallel=None)), dtype=np.float32)
        for matrix in (doc_vecs, query_vecs):
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1
            matrix /= norms
        np.savez_compressed(EMBED_CACHE, fingerprint=np.asarray(fingerprint),
                            documents=doc_vecs, queries=query_vecs)
        return doc_vecs, query_vecs, {
            "available": True, "model": EMBED_MODEL, "cache_hit": False,
            "cache": str(EMBED_CACHE.relative_to(ROOT)), "fingerprint": fingerprint,
            "settings": {**DENSE_SAFE_SETTINGS, "batch_size": batch_size},
            "failed_default_probe": DENSE_RESOURCE_GATE,
        }
    except Exception as exc:
        return None, None, {"available": False, "model": EMBED_MODEL,
                            "cache_hit": False, "settings": DENSE_SAFE_SETTINGS,
                            "failed_default_probe": DENSE_RESOURCE_GATE,
                            "reason": f"{type(exc).__name__}: {exc}"}


def rank(scores: np.ndarray) -> np.ndarray:
    return np.argsort(-scores, kind="stable")


def rrf_ranking(rankings: list[np.ndarray], n_docs: int) -> tuple[np.ndarray, np.ndarray]:
    scores = np.zeros(n_docs, dtype=np.float32)
    for ordering in rankings:
        for position, doc_index in enumerate(ordering[:RRF_DEPTH], 1):
            scores[int(doc_index)] += 1.0 / (RRF_K + position)
    return rank(scores), scores


def retrieval_metrics(ordering: np.ndarray, gold: tuple[str, ...], docs: list[Document],
                      latency_ms: float, doc_tokens: np.ndarray) -> dict:
    gold_set = set(gold)
    top = [docs[int(i)].doc_id for i in ordering[:TOP_K]]
    top5 = top[:5]
    found5 = gold_set.intersection(top5)
    found = gold_set.intersection(top)
    first = next((i + 1 for i, doc_id in enumerate(top) if doc_id in gold_set), None)
    precision = len(found) / len(top)
    recall = len(found) / len(gold_set)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "recall_at_5": len(found5) / len(gold_set),
        "recall_at_10": recall,
        "evidence_precision_at_10": precision,
        "evidence_f1_at_10": f1,
        "all_evidence_at_10": float(found == gold_set),
        "mrr_at_10": 1.0 / first if first else 0.0,
        "query_latency_ms": latency_ms,
        "estimated_retrieved_tokens_at_10": int(sum(doc_tokens[int(i)] for i in ordering[:TOP_K])),
        "top_doc_ids": top,
    }


def evaluate(docs: list[Document], queries: list[Query]) -> tuple[list[dict], dict, dict]:
    full = SparseIndex([d.text for d in docs])
    summaries = SparseIndex([d.summary for d in docs])
    adjacency, entities, entity_tokens = build_graph(docs)
    doc_vecs, query_vecs, dense_info = dense_embeddings(docs, queries)
    doc_tokens = np.asarray([len(tokenize(d.text)) for d in docs], dtype=np.int64)
    doc_index = {doc.doc_id: i for i, doc in enumerate(docs)}
    rows = []
    for q_index, query in enumerate(queries):
        started = time.perf_counter()
        raw_scores = full.raw_scores(query.text)
        raw_rank = rank(raw_scores)
        raw_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        summary_scores = summaries.bm25_scores(query.text)
        summary_rank = rank(summary_scores)
        summary_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        all_scores = full.bm25_scores(query.text)
        all_rank = rank(all_scores)
        all_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        graph_scores = temporal_graph_scores(query.text, all_scores, docs, adjacency, entities, entity_tokens)
        graph_rank = rank(graph_scores)
        graph_extra_ms = (time.perf_counter() - started) * 1000
        rank_map = {"raw_lexical_scan": raw_rank, "summary_only_bm25": summary_rank,
                    "all_document_bm25": all_rank, "temporal_graph": graph_rank}
        latency = {"raw_lexical_scan": raw_ms, "summary_only_bm25": summary_ms,
                   "all_document_bm25": all_ms, "temporal_graph": all_ms + graph_extra_ms}
        if doc_vecs is not None and query_vecs is not None:
            started = time.perf_counter()
            dense_scores = doc_vecs @ query_vecs[q_index]
            rank_map["dense_vectors"] = rank(dense_scores)
            latency["dense_vectors"] = (time.perf_counter() - started) * 1000
        components = [rank_map["summary_only_bm25"], rank_map["all_document_bm25"],
                      rank_map["temporal_graph"]]
        if "dense_vectors" in rank_map:
            components.append(rank_map["dense_vectors"])
        started = time.perf_counter()
        rank_map["rrf_hybrid"], _ = rrf_ranking(components, len(docs))
        fusion_ms = (time.perf_counter() - started) * 1000
        latency["rrf_hybrid"] = summary_ms + all_ms + graph_extra_ms + \
            latency.get("dense_vectors", 0.0) + fusion_ms
        methods = {name: retrieval_metrics(ordering, query.gold_doc_ids, docs,
                                            latency[name], doc_tokens)
                   for name, ordering in rank_map.items()}
        query_terms = set(tokenize(query.text))
        gold_terms = set().union(*(set(tokenize(docs[doc_index[doc_id]].text))
                                   for doc_id in query.gold_doc_ids))
        overlap = query_terms & gold_terms
        rows.append({
            "query_id": query.query_id, "category": query.category,
            "base_item_id": query.base_item_id, "facet_target_id": query.facet_target_id,
            "query": query.text, "gold_doc_ids": list(query.gold_doc_ids),
            "query_gold_token_overlap": {
                "query_unique_tokens": len(query_terms), "gold_unique_tokens": len(gold_terms),
                "shared_unique_tokens": len(overlap),
                "query_token_containment_in_gold": len(overlap) / max(1, len(query_terms)),
                "jaccard": len(overlap) / max(1, len(query_terms | gold_terms)),
            },
            "methods": methods,
        })
    raw_bytes = sum(len(d.text.encode("utf-8")) for d in docs)
    graph_extra = sum(len(neighbors) for neighbors in adjacency) * 4 + \
        sum(len(indices) for indices in entities.values()) * 4
    dense_bytes = int(doc_vecs.nbytes) if doc_vecs is not None else 0
    index_bytes = {
        "raw_lexical_scan": 0,
        "summary_only_bm25": summaries.estimated_index_bytes,
        "all_document_bm25": full.estimated_index_bytes,
        "temporal_graph": full.estimated_index_bytes + graph_extra,
        "rrf_hybrid": summaries.estimated_index_bytes + full.estimated_index_bytes + graph_extra + dense_bytes,
    }
    if doc_vecs is not None:
        index_bytes["dense_vectors"] = dense_bytes
    index_stats = {method: {"estimated_index_bytes_lower_bound": size,
                            "index_write_amplification_vs_corpus_bytes": size / max(1, raw_bytes)}
                   for method, size in index_bytes.items()}
    index_stats["corpus_utf8_bytes"] = raw_bytes
    return rows, dense_info, index_stats


METRICS = ("recall_at_5", "recall_at_10", "evidence_precision_at_10", "evidence_f1_at_10",
           "all_evidence_at_10", "mrr_at_10", "query_latency_ms",
           "estimated_retrieved_tokens_at_10")


def mean_metrics(rows: list[dict], method: str) -> dict:
    return {metric: statistics.fmean(r["methods"][method][metric] for r in rows) for metric in METRICS}


def cluster_bootstrap(rows: list[dict], methods: list[str]) -> list[dict]:
    by_category = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_category[row["category"]][row["base_item_id"]].append(row)
    seed_rows = []
    for seed in range(SEEDS):
        rng = random.Random(seed)
        category_metrics = defaultdict(dict)
        for category in QUOTAS:
            groups = by_category[category]
            base_ids = sorted(groups)
            sampled = rng.choices(base_ids, k=len(base_ids))
            sample_rows = [row for base in sampled for row in groups[base]]
            for method in methods:
                values = mean_metrics(sample_rows, method)
                category_metrics[method][category] = values
                seed_rows.append({"seed": seed, "category": category, "method": method,
                                  "sampled_base_clusters": len(sampled),
                                  "sampled_query_rows": len(sample_rows), **values})
        for method in methods:
            overall = {metric: statistics.fmean(category_metrics[method][cat][metric] for cat in QUOTAS)
                       for metric in METRICS}
            seed_rows.append({"seed": seed, "category": "overall", "method": method,
                              "sampled_base_clusters": sum(len(by_category[c]) for c in QUOTAS),
                              "sampled_query_rows": None, **overall})
    return seed_rows


def summarize_bootstrap(seed_rows: list[dict], methods: list[str]) -> dict:
    summary = {}
    for category in (*QUOTAS.keys(), "overall"):
        summary[category] = {}
        for method in methods:
            subset = [row for row in seed_rows if row["category"] == category and row["method"] == method]
            summary[category][method] = {}
            for metric in METRICS:
                values = [row[metric] for row in subset]
                mean = statistics.fmean(values)
                low, high = np.percentile(values, [2.5, 97.5]) if len(values) > 1 else (mean, mean)
                summary[category][method][metric] = {
                    "mean": mean, "bootstrap_percentile_95_low": float(low),
                    "bootstrap_percentile_95_high": float(high),
                }
    return summary


def fixed_metrics(rows: list[dict], methods: list[str]) -> dict:
    def block(items: list[dict], method: str) -> dict:
        values = mean_metrics(items, method)
        values["query_latency_p95_ms"] = float(np.percentile(
            [r["methods"][method]["query_latency_ms"] for r in items], 95))
        values["estimated_retrieved_tokens_p95_at_10"] = float(np.percentile(
            [r["methods"][method]["estimated_retrieved_tokens_at_10"] for r in items], 95))
        return values

    output = {"overall": {m: block(rows, m) for m in methods}}
    for category in QUOTAS:
        subset = [row for row in rows if row["category"] == category]
        output[category] = {m: block(subset, m) for m in methods}
    return output


def token_overlap_audit(rows: list[dict]) -> dict:
    output = {}
    for category in (*QUOTAS.keys(), "overall"):
        subset = rows if category == "overall" else [r for r in rows if r["category"] == category]
        output[category] = {}
        for metric in ("query_token_containment_in_gold", "jaccard"):
            values = [r["query_gold_token_overlap"][metric] for r in subset]
            output[category][metric] = {
                "mean": statistics.fmean(values), "median": float(np.median(values)),
                "p95": float(np.percentile(values, 95)), "max": max(values),
            }
    return output


def chart(summary: dict, methods: list[str]) -> None:
    import matplotlib.pyplot as plt

    labels = {
        "raw_lexical_scan": "raw lexical", "summary_only_bm25": "summary BM25",
        "all_document_bm25": "all-doc BM25", "dense_vectors": "dense",
        "temporal_graph": "temporal graph", "rrf_hybrid": "RRF hybrid",
    }
    colors = {
        "raw_lexical_scan": "#8a8f98", "summary_only_bm25": "#c29b4b",
        "all_document_bm25": "#4f79a7", "dense_vectors": "#8966a8",
        "temporal_graph": "#4c8b72", "rrf_hybrid": "#c65f4a",
    }
    fig, (ax_bar, ax_heat) = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={"width_ratios": [1, 1.45]})
    means = [summary["overall"][m]["recall_at_10"]["mean"] for m in methods]
    lows = [summary["overall"][m]["recall_at_10"]["bootstrap_percentile_95_low"] for m in methods]
    highs = [summary["overall"][m]["recall_at_10"]["bootstrap_percentile_95_high"] for m in methods]
    errors = np.asarray([[mean - low for mean, low in zip(means, lows)],
                         [high - mean for mean, high in zip(means, highs)]])
    x = np.arange(len(methods))
    ax_bar.bar(x, means, yerr=errors, color=[colors[m] for m in methods], capsize=3)
    ax_bar.set_xticks(x, [labels[m] for m in methods], rotation=30, ha="right")
    ax_bar.set_ylim(0, 1)
    ax_bar.set_ylabel(f"evidence recall@{TOP_K}")
    ax_bar.set_title("Category-balanced cluster bootstrap")
    ax_bar.grid(axis="y", alpha=.2)
    for i, value in enumerate(means):
        ax_bar.text(i, min(.97, value + .035), f"{value:.2f}", ha="center", fontsize=8)

    categories = list(QUOTAS)
    matrix = np.array([[summary[c][m]["recall_at_10"]["mean"] for m in methods] for c in categories])
    image = ax_heat.imshow(matrix, vmin=0, vmax=1, cmap="viridis", aspect="auto")
    ax_heat.set_xticks(range(len(methods)), [labels[m] for m in methods], rotation=30, ha="right")
    ax_heat.set_yticks(range(len(categories)), [c.replace("_", " ") for c in categories])
    ax_heat.set_title("Evidence recall by auto-labeled query category")
    for row in range(len(categories)):
        for col in range(len(methods)):
            value = matrix[row, col]
            ax_heat.text(col, row, f"{value:.2f}", ha="center", va="center",
                         color="white" if value < .35 or value > .72 else "black", fontsize=8)
    fig.colorbar(image, ax=ax_heat, fraction=.035, pad=.03, label=f"recall@{TOP_K}")
    fig.suptitle("Persona RQ-E03a — structural evidence retrieval, 30 seeded base-cluster bootstraps",
                 fontweight="bold")
    fig.text(.5, .01, "Auto-generated structural labels; this chart does not measure scientific answer truth.",
             ha="center", fontsize=9, color="#8b2f2f")
    fig.tight_layout(rect=(0, .045, 1, .94))
    fig.savefig(OUT_PNG, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def validate_contract(docs: list[Document], queries: list[Query], sessions: list[dict]) -> dict:
    doc_ids = {doc.doc_id for doc in docs}
    if len(doc_ids) != len(docs):
        raise RuntimeError("duplicate document IDs make structural labels ambiguous")
    if len(queries) != 200:
        raise RuntimeError(f"query contract requires exactly 200 queries; generated {len(queries)}")
    if len({q.query_id for q in queries}) != 200:
        raise RuntimeError("query IDs are not unique")
    counts = Counter(q.category for q in queries)
    if dict(counts) != QUOTAS:
        raise RuntimeError(f"query mixture mismatch: expected {QUOTAS}, got {dict(counts)}")
    for query in queries:
        missing = set(query.gold_doc_ids) - doc_ids
        if missing:
            raise RuntimeError(f"query {query.query_id} labels missing documents: {sorted(missing)}")
        if not query.text.strip() or not query.base_item_id or not query.facet_target_id:
            raise RuntimeError(f"query {query.query_id} has an empty contract field")
    session_queries_only = [q for q in queries if q.category == "session_reconstruction"]
    distinct_session_targets = len({q.facet_target_id for q in session_queries_only})
    if distinct_session_targets != QUOTAS["session_reconstruction"]:
        raise RuntimeError(f"session targets must be distinct; found {distinct_session_targets}")
    bases = {category: len({q.base_item_id for q in queries if q.category == category}) for category in QUOTAS}
    targets = {category: len({q.facet_target_id for q in queries if q.category == category}) for category in QUOTAS}
    return {"query_counts": dict(counts), "unique_base_items": bases,
            "distinct_facet_targets": targets, "base_sessions": len(sessions)}


def main() -> None:
    if not CURIE.is_dir():
        raise RuntimeError(f"required real Curie workspace missing: {CURIE}")
    claim_docs, claims, doi_docs = load_claim_documents()
    corrections = correction_records()
    retired_still_active = sorted({c.get("kg_claim_id") for c in corrections if c.get("kg_claim_id") in claims})
    if retired_still_active:
        raise RuntimeError(f"correction overlay failed; retired extraction claims remain active: {retired_still_active}")
    note_docs, notes = load_note_documents(doi_docs)
    history_docs, histories = load_history_documents(claims)
    session_docs, sessions = load_session_documents()
    docs = sorted(claim_docs + note_docs + history_docs + session_docs, key=lambda d: d.doc_id)
    queries = (
        provenance_queries(claims) + temporal_queries(histories) + multi_hop_queries(claims) +
        conflict_queries(claims) + field_note_queries(notes) + session_queries(sessions)
    )
    contract = validate_contract(docs, queries, sessions)
    rows, dense_info, index_stats = evaluate(docs, queries)
    methods = sorted(rows[0]["methods"], key=lambda m: (
        "raw_lexical_scan", "summary_only_bm25", "all_document_bm25", "dense_vectors",
        "temporal_graph", "rrf_hybrid",
    ).index(m))
    seed_rows = cluster_bootstrap(rows, methods)
    summary = summarize_bootstrap(seed_rows, methods)
    fixed = fixed_metrics(rows, methods)
    corpus_counts = Counter(doc.kind for doc in docs)
    snapshot = hashlib.sha256("\n".join(f"{d.doc_id}\t{stable_hash(d.text)}" for d in docs).encode()).hexdigest()
    result = {
        "experiment": "RQ-E03a structural memory retrieval screening",
        "scientific_truth_evaluated": False,
        "user_query_generalization_evaluated": False,
        "auto_generated_labels": True,
        "label_semantics": (
            "Gold labels are IDs of stored evidence records used to deterministically generate each query. "
            "Metrics measure evidence-record retrieval only; they do not validate claims, answer truth, "
            "entailment, or scientific quality."
        ),
        "seeds": SEEDS,
        "seed_semantics": (
            "Thirty deterministic category-stratified cluster-bootstrap resamples. base_item_id is the "
            "resampling unit, so repeated facets from one history/note/session remain grouped."
        ),
        "top_k_equal_for_all_methods": TOP_K,
        "query_contract": QUOTAS,
        "contract_audit": contract,
        "corpus": {"root": str(CURIE.relative_to(ROOT)), "documents": len(docs),
                   "by_kind": dict(corpus_counts), "snapshot_sha256": snapshot,
                   "claims": len(claims), "notes": len(notes), "history_records": len(histories),
                   "multi_snapshot_history_bases": sum(len(h["rows"]) >= 2 for h in histories),
                   "source_correction_overlays_applied": sum(
                       bool(source.get("correction_applied")) for claim in claims.values()
                       for source in claim.get("source_records", [])),
                   "retired_extraction_claims_excluded": sorted(
                       c.get("kg_claim_id") for c in corrections if c.get("kg_claim_id")),
                   "sessions": [{k: s[k] for k in ("session_id", "events", "artifacts")} for s in sessions]},
        "method_definitions": {
            "raw_lexical_scan": "Unweighted full-document token overlap normalized by document length.",
            "summary_only_bm25": "BM25 over deterministic, non-model per-record projections only.",
            "all_document_bm25": "BM25 over every indexed atomic record's full stored text.",
            "dense_vectors": "Frozen local-cache-only BGE-small passage/query vectors; included only if fastembed succeeds without download.",
            "temporal_graph": "All-document BM25 plus explicit stored links, entity overlap, two-hop propagation, and year match.",
            "rrf_hybrid": "RRF(k=60, depth=100) over summary BM25, all-document BM25, temporal graph, and dense when available.",
        },
        "dense": dense_info,
        "index_write_amplification": index_stats,
        "methods_compared": methods,
        "fixed_200_query_metrics": fixed,
        "synthetic_query_gold_token_overlap_audit": token_overlap_audit(rows),
        "cluster_bootstrap_summary": summary,
        "seed_rows": seed_rows,
        "queries_and_raw_rankings": rows,
        "limitations": [
            "All labels are auto-generated from storage structure, not human relevance judgments or scientific truth.",
            "Queries are synthetically generated from target records and retain measurable lexical cues; overlap is reported explicitly and results do not establish user-query generalization.",
            "Source-level correction overlays are applied before canonical claim IDs and conflicts are reconstructed; retired extraction signs are not reintroduced.",
            "Temporal queries reuse only 18 multi-snapshot claims; field-note queries reuse 23 notes.",
            "Session reconstruction has 30 distinct targets but only two base sessions; its confidence interval is diagnostic, not generalizable.",
            "Two-hop paths and sign conflicts are graph-structural labels; they need not express valid causal or scientific relationships.",
            "The temporal-graph scorer is a simple transparent screening heuristic, not a learned or validated memory architecture.",
            "The corpus indexes atomic claims rather than complete paper text, so this is a Persona-memory benchmark, not literature-search evaluation.",
            "Bootstrap intervals measure base-record sampling variation in this one Curie snapshot, not future-workspace or human-query variation.",
        ],
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    chart(summary, methods)
    print(f"documents={len(docs)} claims={len(claims)} notes={len(notes)} histories={len(histories)} sessions={len(sessions)}")
    print(f"queries={len(queries)} mixture={dict(Counter(q.category for q in queries))}")
    print(f"unique_bases={contract['unique_base_items']}")
    print(f"dense_available={dense_info['available']} cache_hit={dense_info.get('cache_hit', False)}")
    for method in methods:
        metrics = summary["overall"][method]
        fixed_method = fixed["overall"][method]
        print(f"{method:20} r@5={metrics['recall_at_5']['mean']:.3f} "
              f"r@10={metrics['recall_at_10']['mean']:.3f} "
              f"f1@10={metrics['evidence_f1_at_10']['mean']:.3f} "
              f"p95ms={fixed_method['query_latency_p95_ms']:.2f} "
              f"tokens={fixed_method['estimated_retrieved_tokens_at_10']:.0f}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    argparse.ArgumentParser(
        description="Run the structural Persona-memory retrieval benchmark."
    ).parse_args()
    main()
