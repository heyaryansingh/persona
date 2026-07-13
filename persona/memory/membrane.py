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


# ---------------------------------------------------------------- dual-signal admission (F2.1)
# The "discipline of believing" gate: a candidate claim is committed to belief ONLY when TWO
# independent signals agree — an exact-span entailment AND independent KG support. Anything less
# abstains to a human. This never anchors (anchoring stays a human/tested act — kg.anchor); it
# only ROUTES. Deterministic + offline: reads candidate fields + the KG, no model, no network.
# PLACEHOLDER: min-labs threshold not yet calibrated against a labelled admit/reject set.
_KG_SUPPORT_MIN_LABS = 2


def _nli_span_signal(candidate: dict) -> bool:
    """Exact-span entailment signal — PLUGGABLE SEAM, offline stub for now.

    Deterministic proxy (no model): the candidate must carry a verbatim source span
    (`span`/`quote`/`evidence_span`) that literally contains BOTH the subject and object
    surface forms — a cheap stand-in for "the source text entails this claim at a locatable
    span". An ungrounded assertion (no span) can never satisfy it.
    TODO(nli-model): replace the body with a real span-grounded NLI entailment call behind
    THIS signature. PLACEHOLDER: the contains-both heuristic is unvalidated vs a labelled set.
    """
    span = (candidate.get("span") or candidate.get("quote")
            or candidate.get("evidence_span") or "").lower()
    subj = " ".join((candidate.get("subject") or "").lower().split())
    obj = " ".join((candidate.get("object") or "").lower().split())
    if not span or not subj or not obj:
        return False
    return subj in span and obj in span


def _kg_support_signal(candidate: dict, kg) -> bool:
    """KG-support signal: independent literature already agrees on this directional claim.

    Same-sign claims on the (subject, object) pair must be backed by >= _KG_SUPPORT_MIN_LABS
    DISTINCT labs. Uses independence-by-lab (kg.crosscheck's `labs` = independent_source_count),
    so raw copy count — citation echo / correlated poisoning — can't satisfy the gate.
    """
    if kg is None:
        return False
    try:
        cc = kg.crosscheck(candidate.get("subject", ""), candidate.get("object", ""),
                           candidate.get("effect_sign", "na"))
    except Exception:
        return False
    labs = max((int(s.get("labs") or 0) for s in cc.get("support", [])), default=0)
    return labs >= _KG_SUPPORT_MIN_LABS


def admit_candidate(candidate: dict, kg=None) -> dict:
    """Dual-signal atomic admission gate (PRD F2.1) — the 'discipline of believing'.

    Commit a candidate to belief ONLY when BOTH signals agree:
      1. nli_span   — an exact, locatable source span entails the claim (offline stub; NLI seam).
      2. kg_support — independent literature in the KG already agrees (>= N distinct labs).
    Exactly one signal -> abstain to a human. Neither -> reject (nothing to believe). Cheap
    evidence alone (volume without independence, or an assertion with no span) can never reach
    'commit' — that is the poisoning defence. NEVER auto-anchors; this only routes.

    Returns {admit, route:'commit'|'human'|'reject', reasons[], signals:{nli_span, kg_support}}.
    """
    kg = kg if kg is not None else get_kg()
    nli = _nli_span_signal(candidate)
    kgs = _kg_support_signal(candidate, kg)
    reasons = []
    if nli and kgs:
        route, admit = "commit", True
        reasons.append("exact-span entailment AND independent KG support agree")
    elif nli or kgs:
        route, admit = "human", False
        reasons.append("only one signal present (%s) — abstain to human"
                       % ("nli_span" if nli else "kg_support"))
    else:
        route, admit = "reject", False
        reasons.append("neither exact-span entailment nor independent KG support")
    if not nli:
        reasons.append("no exact source span entailing the claim (nli_span=false)")
    if not kgs:
        reasons.append("no independent KG support (>=%d distinct labs) (kg_support=false)"
                       % _KG_SUPPORT_MIN_LABS)
    return {"admit": admit, "route": route, "reasons": reasons,
            "signals": {"nli_span": nli, "kg_support": kgs}}


# ------------------------------------------------------------ recomposition / feasibility (F2.4)
# A second, cheaper gate than admit_candidate: before believing (or even crediting a signal), ask
# whether the candidate is even *physically/logically possible*. Two deterministic, offline checks
# — no model, no network:
#   1. sign-vs-anchor: the candidate's effect_sign directly opposes an ANCHORED (human/tested)
#      belief on the same (subject,object) pair. Overturning verified knowledge is a human's call,
#      not the gate's — so an implausible sign-flip is routed out, never silently committed.
#   2. magnitude-range: a numeric effect size parsed from the free-text `magnitude` field falls
#      outside a sane range for a ratio/fold (must be > 0; absurdly large = extraction/typo).
# PLACEHOLDER: the magnitude bounds below are unvalidated heuristics, not calibrated against a
# labelled set of real vs implausible effect sizes.
_MAGNITUDE_RATIO_CEILING = 1000.0   # PLACEHOLDER: fold/HR/OR/RR above this ~never real in-vivo
_RATIO_WORDS = ("fold", "hr", "or", "rr", "ratio")


def _magnitude_flag(candidate: dict):
    """Return a flag string if the free-text `magnitude` names an impossible ratio, else None.

    Deterministic parse (no model): pull the first number out of e.g. '2.1-fold' / 'HR 1.4'. If
    the magnitude reads as a ratio/fold (the only kind with a hard floor) it must be > 0 and below
    a sane ceiling — a non-positive or absurdly large fold-change is a physical impossibility /
    extraction error. Percentages and bare numbers are left alone (no universal sane range).
    """
    import re
    mag = str(candidate.get("magnitude") or "").strip().lower()
    if not mag or "%" in mag or not any(w in mag for w in _RATIO_WORDS):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", mag)
    if not m:
        return None
    val = float(m.group())
    if val <= 0:
        return "magnitude-range: ratio/fold '%s' is non-positive (physically impossible)" % mag
    if val > _MAGNITUDE_RATIO_CEILING:
        return ("magnitude-range: ratio/fold %g exceeds sane ceiling %g (likely extraction error)"
                % (val, _MAGNITUDE_RATIO_CEILING))
    return None


def feasibility_flags(candidate: dict, kg=None) -> dict:
    """Recomposition/feasibility gate (PRD F2.4) — is this candidate even possible? Offline.

    Flags a candidate claim as physically/logically implausible so the membrane can route it to a
    human instead of crediting it. Deterministic, no model/network. Two checks (see module notes):
      * sign-vs-anchor — effect_sign contradicts an ANCHORED belief on the same (subject,object).
      * magnitude-range — a ratio/fold effect size out of a sane range.

    Returns {feasible: bool, flags: [str]}. feasible=False means "do not admit; hand to a human".
    """
    kg = kg if kg is not None else get_kg()
    flags = []
    mag = _magnitude_flag(candidate)
    if mag:
        flags.append(mag)
    if kg is not None:
        try:
            cc = kg.crosscheck(candidate.get("subject", ""), candidate.get("object", ""),
                               candidate.get("effect_sign", "na"))
            for opp in cc.get("contradict", []):
                prov = kg.provenance(opp.get("claim_id", ""))
                if prov and prov.get("anchored"):
                    flags.append("sign-vs-anchor: effect_sign contradicts anchored belief %s (%s)"
                                 % (opp.get("claim_id"), opp.get("text", "")))
                    break
        except Exception:
            pass
    return {"feasible": not flags, "flags": flags}


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
