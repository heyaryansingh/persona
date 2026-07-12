"""The membrane + harvester (v4 P2): candidate claims on disk -> gated beliefs in the KG.

Reads each source's `claims.jsonl`, writes observations into the temporal KG, links contradictions
(opposite effect-signs on the same subject-object pair), and projects high-confidence beliefs back
into the legible `self/beliefs.md`. A "belief" = a claim converged from >= K INDEPENDENT labs
(citation echo can't inflate). Idempotent: a source with a `.ingested` marker is skipped.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone

from .. import config
from ..events import log
from .kg import KG

def get_kg():
    """The CURRENT persona's KG (v5); None if FalkorDB is unreachable."""
    from ..context import get_persona
    try:
        return get_persona().kg
    except Exception as e:
        log().emit("error", f"knowledge graph unavailable (FalkorDB): {str(e)[:140]}",
                   actor="membrane")
        return None


def _ops_dir():
    from ..context import get_persona
    return get_persona().paths.ops_dir


def _announced() -> set:
    p = _ops_dir() / "announced_contradictions.json"
    if p.exists():
        try:
            return set(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def _save_announced(s: set) -> None:
    (_ops_dir() / "announced_contradictions.json").write_text(
        json.dumps(sorted(s)), encoding="utf-8")


def _source_corrections(src_dir) -> dict:
    path = src_dir / "claim_corrections.jsonl"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
            out[item["source_claim_id"]] = item
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def harvest(min_independent: int = 2, parent_id=None) -> dict:
    """Ingest all not-yet-ingested sources into the KG; fire contradictions; project beliefs."""
    from ..context import get_persona
    lock = get_persona().harvest_lock
    if not lock.acquire(blocking=False):
        return {"ok": True, "ingested": 0, "reason": "harvest-already-running"}
    try:
        return _harvest(min_independent, parent_id)
    finally:
        lock.release()


def _harvest(min_independent: int, parent_id) -> dict:
    kg = get_kg()
    if kg is None:
        return {"ok": False, "reason": "no-kg"}
    from ..context import get_persona
    ingested, n_claims = 0, 0
    for src_dir in sorted(get_persona().paths.sources_dir.glob("*")):
        claims_f = src_dir / "claims.jsonl"
        marker = src_dir / ".ingested"
        if not claims_f.exists() or marker.exists():
            continue
        meta = json.loads((src_dir / "meta.json").read_text(encoding="utf-8"))
        kg.upsert_source(meta)
        corrections = _source_corrections(src_dir)
        for line in claims_f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("claim_id") in corrections:
                rec = {**rec, "effect_sign": corrections[rec["claim_id"]]["new_effect_sign"],
                       "provenance": "CORRECTED_EXTRACTION"}
            kg.add_claim(rec, meta["slug"])          # canonicalizes entities inside
            n_claims += 1
        marker.write_text("", encoding="utf-8")
        ingested += 1

    # link + announce contradictions (on canonical pairs)
    announced = _announced()
    new_contra = 0
    if ingested:
        kg.link_all_contradictions()
    for c in kg.contradictions():
        key = f"{c['subject']}||{c['object']}"
        if key not in announced:
            announced.add(key)
            new_contra += 1
            log().emit("contradiction",
                       f"CONTRADICTION on {c['subject']} → {c['object']}: "
                       f"+{c['pos_sources']} lab(s) vs −{c['neg_sources']} lab(s)",
                       actor="membrane", parent_id=parent_id,
                       subject=c["subject"], object=c["object"])
    _save_announced(announced)

    beliefs = kg.beliefs(min_independent=min_independent)
    try:
        get_persona().history.snapshot(kg.beliefs(min_independent=1, limit=400))   # confidence-over-time
    except Exception:
        pass
    if ingested:
        log().emit("belief_update",
                   f"harvested {ingested} source(s), {n_claims} claim(s) → "
                   f"{len(beliefs)} converged belief(s) (≥{min_independent} independent labs), "
                   f"{len(kg.contradictions())} contradiction(s)", actor="membrane",
                   parent_id=parent_id, beliefs=len(beliefs))
        project_beliefs(kg, min_independent)
    return {"ok": True, "ingested": ingested, "claims": n_claims,
            "beliefs": len(beliefs), "new_contradictions": new_contra}


def correct_extraction_sign(claim_id: str, new_effect_sign: str, reason: str,
                            session_id: str) -> dict:
    """Append a source correction, transfer its evidence, and retire the bad KG claim."""
    if new_effect_sign not in {"+", "-", "0", "na"} or not reason.strip() or not session_id:
        return {"ok": False, "reason": "invalid-correction"}
    kg = get_kg()
    if kg is None:
        return {"ok": False, "reason": "no-kg"}
    old = kg.provenance(claim_id)
    if not old or old.get("anchored"):
        return {"ok": False, "reason": "claim-not-correctable"}
    if old["effect_sign"] == new_effect_sign:
        return {"ok": True, "reason": "already-correct", "corrected_claim": claim_id}
    from ..context import get_persona
    corrected_ids, written = [], 0
    for source in old.get("sources") or []:
        src_dir = get_persona().paths.sources_dir / source["slug"]
        claims_path = src_dir / "claims.jsonl"
        if not claims_path.exists():
            continue
        match = None
        for line in claims_path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if (rec.get("effect_sign") == old["effect_sign"] and
                    rec.get("quote") == source.get("quote")):
                match = rec
                break
        if match is None:
            continue
        correction = {"source_claim_id": match["claim_id"], "kg_claim_id": claim_id,
                      "old_effect_sign": old["effect_sign"], "new_effect_sign": new_effect_sign,
                      "reason": reason, "session_id": session_id,
                      "corrected_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        path = src_dir / "claim_corrections.jsonl"
        existing = _source_corrections(src_dir)
        if match["claim_id"] not in existing:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(correction, ensure_ascii=False) + "\n")
            written += 1
        corrected_ids.append(kg.add_claim({**match, "effect_sign": new_effect_sign,
                                           "provenance": "CORRECTED_EXTRACTION"}, source["slug"]))
    if not corrected_ids or not kg.retire_extraction_claim(claim_id, reason, session_id):
        return {"ok": False, "reason": "source-evidence-not-found"}
    announced = _announced()
    announced.discard(f"{old['subject']}||{old['object']}")
    _save_announced(announced)
    project_beliefs(kg)
    target = corrected_ids[0]
    log().emit("correction", f"retired bad sign on {old['subject']} → {old['object']}; "
               f"moved {written} source(s) to {new_effect_sign}", actor="membrane",
               claim_id=claim_id, corrected_claim=target, session_id=session_id)
    return {"ok": True, "retired_claim": claim_id, "corrected_claim": target,
            "source_corrections": written}


def project_beliefs(kg=None, min_independent: int = 2) -> None:
    """Render the KG's high-confidence beliefs into legible self/beliefs.md (git-diffable mind)."""
    kg = kg or get_kg()
    if kg is None:
        return
    beliefs = kg.beliefs(min_independent=min_independent, limit=200)
    arrow = {"+": "↑", "-": "↓", "0": "∅"}
    lines = ["# beliefs\n",
             f"_projected from the knowledge graph — claims converged from ≥{min_independent} "
             f"independent labs. Auto-generated; edited by the membrane, not by hand._\n"]
    for b in beliefs:
        a = arrow.get(b["effect_sign"], "·")
        anchor = " ⚓" if b["anchored"] else ""
        lines.append(f"- **{b['subject']}** {a} **{b['object']}** ({b['relation']}) "
                     f"· {b['independent_sources']} labs · p={b['confidence']:.2f} "
                     f"· {b['provenance']}{anchor}")
    from ..context import get_persona
    (get_persona().paths.self_dir / "beliefs.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
