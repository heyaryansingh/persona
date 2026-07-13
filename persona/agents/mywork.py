"""Ingest the HUMAN's own work + cross-check it against the literature (v6 P5 co-researcher).

The flagship "works for you" move: upload your paper/draft/notes, and the persona reads it, extracts
YOUR claims (kept distinct as HUMAN_CORPUS — never rendered with confirmed-belief authority), and
checks each against everything it has read: what SUPPORTS it, what CONTRADICTS it, with quotes+DOIs.
Adversarial self-check against your own unpublished claims — evidence, not generic feedback.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .. import config
from ..budget import budget
from ..context import get_persona
from ..events import log


def _read_text(f: Path) -> str:
    if f.suffix.lower() == ".pdf":
        try:
            import fitz
            doc = fitz.open(str(f))
            return "\n".join(pg.get_text() for pg in doc)[:40000]
        except Exception:
            return ""
    try:
        return f.read_text(encoding="utf-8", errors="replace")[:40000]
    except Exception:
        return ""


def ingest(path_rel: str, kind: str = "draft", kg=None) -> dict:
    p = get_persona()
    try:
        f = p.paths.safe(path_rel)
    except ValueError:
        return {"ok": False, "reason": "bad-path"}
    if not f.exists() or not f.is_file():
        return {"ok": False, "reason": "not-found"}
    if kg is None:
        return {"ok": False, "reason": "no-kg"}
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    text = _read_text(f)
    if len(text.strip()) < 40:
        return {"ok": False, "reason": "no-text"}
    from ..reading.extract import extract_claims
    claims, usage = extract_claims(text, f.name)
    budget().add(usage.get("cost", 0.0))
    if not claims:
        return {"ok": False, "reason": "no-claims"}
    doc_id = "hw_" + hashlib.sha1(path_rel.encode()).hexdigest()[:12]
    kg.add_human_work(doc_id, f.name, kind)
    results, n_sup, n_con = [], 0, 0
    for c in claims:
        subj, obj = c.get("subject", ""), c.get("object", "")
        sign = c.get("effect_sign", "na")
        if not subj or not obj:
            continue
        kg.add_human_claim(doc_id, subj, obj, sign, c.get("quote", ""))
        cc = kg.crosscheck(subj, obj, sign)
        status = ("mixed" if cc["support"] and cc["contradict"]
                  else "contradicted" if cc["contradict"]
                  else "supported" if cc["support"] else "novel")
        if cc["support"]:
            n_sup += 1
        if cc["contradict"]:
            n_con += 1
        results.append({"your_claim": f"{subj} [{sign}] {obj}", "quote": c.get("quote", ""),
                        "status": status, "support": cc["support"], "contradict": cc["contradict"]})
    # RAG: embed the uploaded work so it INFORMS the mind's generation (reports/answers), not just the
    # one-shot cross-check — your paper becomes retrievable context alongside the literature notes.
    try:
        vecs = get_persona().vectors
        for j, i in enumerate(range(0, min(len(text), 18000), 1500)):
            vecs.upsert(f"upload:{doc_id}:{j}", text[i:i + 1500],
                        {"title": f.name, "kind": "upload", "doc_id": doc_id})
    except Exception:
        pass
    log().emit("artifact", f"cross-checked your work “{f.name}”: {len(results)} claims — "
               f"{n_sup} with literature support, {n_con} contradicted", actor="co-researcher",
               file=path_rel)
    # AUTO-AUDIT: an uploaded paper is untrusted input — run the robustness auditor on it automatically
    # (forensics + calibrated replication likelihood) and register it on the living re-audit watchlist.
    audit_res = None
    if len(text.strip()) >= 200 and budget().can_spend():
        try:
            from ..agents import audit as auditor
            a = auditor.audit(text=text, title=f.name, upload_ref=path_rel)
            if a.get("ok"):
                audit_res = {"likelihood": a["likelihood"], "band": a["band"], "interval": a["interval"],
                             "checks": a["checks"], "file": a.get("file")}
        except Exception:
            pass
    return {"ok": True, "doc_id": doc_id, "title": f.name, "n_claims": len(results),
            "n_supported": n_sup, "n_contradicted": n_con, "results": results, "audit": audit_res}
