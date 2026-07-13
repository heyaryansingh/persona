"""Batch-API bulk reader (v4 P3) — the real thousands/day lever (~50% cost, async).

Submit-then-collect-later (never blocks a worker on a slow batch): `submit()` fetches texts,
writes clean.md/meta.json, submits one Anthropic Batch of extraction requests, and records a
manifest under .persona/batches/. `collect()` polls a manifest; when the batch has ended it writes
claims.jsonl per source (then harvest ingests them). A periodic `collect_pending()` drains all
open manifests. Interactive AsyncSwarm-style reading stays for the live loop; this is the
background bulk sweep.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .. import config
from ..context import get_persona
from ..budget import budget
from ..events import log
from ..ingest import openalex, fetch
from .extract import EXTRACT_TOOL, _SYSTEM, validate_claims
from .reader import _claim_id, _already_read

def _batch_dir():
    from ..context import get_persona
    d = get_persona().paths.ops_dir / "batches"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _client():
    from ..providers import anthropic_client
    return anthropic_client()


def submit(works: list[dict], interest: str = "") -> dict:
    """Fetch texts + submit a batch of claim-extractions. Returns {batch_id, n}."""
    if not config.have_key():
        return {"ok": False, "reason": "no-key"}
    _batch_dir().mkdir(parents=True, exist_ok=True)
    requests, id_map = [], {}
    for i, wd in enumerate(works):
        work = openalex.Work.from_dict(wd)
        if not work.slug or _already_read(work.slug):
            continue
        text, kind = fetch.fulltext(work)
        src = get_persona().paths.sources_dir / work.slug
        src.mkdir(parents=True, exist_ok=True)
        (src / "clean.md").write_text(f"# {work.title}\n\n_{kind}_\n\n{text}\n", encoding="utf-8")
        (src / "meta.json").write_text(json.dumps(
            {"id": work.id, "slug": work.slug, "title": work.title, "year": work.year,
             "doi": work.doi, "authors": work.authors, "affiliations": work.affiliations,
             "venue": work.venue, "url": work.landing_url or work.pdf_url, "text_kind": kind,
             "interest": interest, "read_at": _now()}, ensure_ascii=False, indent=2), encoding="utf-8")
        cid = f"w{i}"
        id_map[cid] = work.slug
        requests.append({"custom_id": cid, "params": {
            "model": config.MODEL_READER, "max_tokens": 2048, "system": _SYSTEM,
            "tools": [EXTRACT_TOOL], "tool_choice": {"type": "tool", "name": "record_claims"},
            "messages": [{"role": "user", "content": f"Title: {work.title}\n\nText:\n{text[:40000]}\n\nExtract the claims."}]}})
    if not requests:
        return {"ok": True, "n": 0, "reason": "nothing-new"}
    batch = _client().messages.batches.create(requests=requests)
    (_batch_dir() / f"{batch.id}.json").write_text(json.dumps(
        {"batch_id": batch.id, "id_map": id_map, "interest": interest, "submitted_at": _now(),
         "status": "in_progress"}), encoding="utf-8")
    log().emit("tool", f"submitted a batch of {len(requests)} extraction(s) on “{interest}” "
               f"(Batch API, ~50% cost)", actor="bulk", batch=batch.id, n=len(requests))
    return {"ok": True, "batch_id": batch.id, "n": len(requests)}


def collect(batch_id: str) -> dict:
    """Poll one manifest; if ended, write claims.jsonl per source. Returns {status, written}."""
    man_p = _batch_dir() / f"{batch_id}.json"
    if not man_p.exists():
        return {"ok": False, "reason": "no-manifest"}
    man = json.loads(man_p.read_text(encoding="utf-8"))
    if man.get("status") == "done":
        return {"ok": True, "status": "done", "written": 0}
    client = _client()
    status = client.messages.batches.retrieve(batch_id).processing_status
    if status != "ended":
        return {"ok": True, "status": status, "written": 0}
    written = rejected_total = 0
    for res in client.messages.batches.results(batch_id):
        slug = man["id_map"].get(res.custom_id)
        if not slug or res.result.type != "succeeded":
            continue
        raw = []
        for b in res.result.message.content:
            if b.type == "tool_use":
                raw = b.input.get("claims", []) or []
        u = res.result.message.usage
        budget().add((u.input_tokens * 1.0 + u.output_tokens * 5.0) / 1_000_000 * 0.5)  # batch = 0.5x
        source_dir = get_persona().paths.sources_dir / slug
        meta = json.loads((source_dir / "meta.json").read_text(encoding="utf-8"))
        source_text = (source_dir / "clean.md").read_text(encoding="utf-8")
        raw, rejected = validate_claims(raw, source_text)
        if rejected:
            (source_dir / "claims_rejected.jsonl").write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in rejected) + "\n", encoding="utf-8")
            rejected_total += len(rejected)
        lines = []
        for c in raw:
            if not isinstance(c, dict):
                continue
            cid = _claim_id(c.get("subject", ""), c.get("relation", ""), c.get("object", ""),
                            c.get("effect_sign", "na"))
            lines.append(json.dumps({"claim_id": cid, "source_id": slug,
                "subject": c.get("subject", ""), "relation": c.get("relation", ""),
                "object": c.get("object", ""), "effect_sign": c.get("effect_sign", "na"),
                "quote": c.get("quote", ""), "confidence": c.get("confidence", 0.6),
                "provenance": "READ", "affiliations": meta.get("affiliations", []),
                "extracted_at": _now()}, ensure_ascii=False))
        (source_dir / "claims.jsonl").write_text(
            "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        written += 1
    man["status"] = "done"
    man_p.write_text(json.dumps(man), encoding="utf-8")
    log().emit("tool", f"collected batch {batch_id[:12]} → wrote claims for {written} paper(s), "
               f"rejected {rejected_total} ungrounded claim(s)", actor="bulk", batch=batch_id,
               written=written, rejected=rejected_total)
    return {"ok": True, "status": "ended", "written": written, "rejected": rejected_total}


def collect_pending() -> dict:
    """Drain all open batch manifests (periodic task)."""
    if not _batch_dir().exists():
        return {"ok": True, "checked": 0}
    checked, done = 0, 0
    for p in _batch_dir().glob("*.json"):
        man = json.loads(p.read_text(encoding="utf-8"))
        if man.get("status") == "done":
            continue
        checked += 1
        r = collect(man["batch_id"])
        if r.get("status") == "ended":
            done += 1
    return {"ok": True, "checked": checked, "collected": done}
