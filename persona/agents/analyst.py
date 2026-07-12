"""The analyst (v4 P5) — the agent that does REAL WORK: plans, fetches real data, writes and RUNS
code in the sandbox, interprets results, and writes a real artifact (a report + a project).

A bounded tool-use loop (Sonnet). Tools: write_file (into its project), fetch_dataset (allowlisted
open-data hosts), run_python (sandboxed, no-network compute), finish (emit the report). Everything
is confined to persona-workspace/; the only outputs are files it writes and a draft report — no
irreversible outward actions. This is "do real research, write real things", closing the loop from
a question to a computed, written result.
"""
from __future__ import annotations

import json
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from .. import config
from ..context import get_persona
from ..budget import budget
from ..events import log
from ..sessions import ResearchSession
from ..tools import sandbox, datasets


def _slug(q: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")[:48]
    return s or "investigation"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


TOOLS = [
    {"name": "write_file", "description": "Write a text file inside the project (e.g. a script, notes).",
     "input_schema": {"type": "object", "properties": {
         "path": {"type": "string", "description": "relative path within the project, e.g. analysis/step1.py"},
         "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "fetch_dataset", "description": "Download a real dataset from an open-data host into "
     "the project's data/ folder (available to run_python at /work/data/). Allowlisted hosts only.",
     "input_schema": {"type": "object", "properties": {
         "url": {"type": "string"}, "filename": {"type": "string"}}, "required": ["url"]}},
    {"name": "run_python", "description": "Run Python in a sandbox (numpy/pandas/scipy/sklearn/"
     "matplotlib/statsmodels available; NO network). The project is mounted at /work; datasets at "
     "/work/data. Write outputs to /work/results/. Returns stdout/stderr.",
     "input_schema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}},
    {"name": "science_query", "description": "Query a real research database for structured evidence. "
     "literature_search (OpenAlex — scholarly works in ANY field: physics, economics, CS, materials, "
     "biology…) is domain-general; the rest are biomedical: open_targets (gene<->disease), uniprot "
     "(proteins), ncbi_search (PubMed/GEO/gene; db='gds' for GEO), pubchem (compounds), clinical_trials. "
     "Use literature_search for non-biomedical topics.",
     "input_schema": {"type": "object", "properties": {
         "api": {"type": "string", "enum": ["literature_search", "open_targets", "uniprot",
                                            "ncbi_search", "pubchem", "clinical_trials"]},
         "params": {"type": "object", "description": "e.g. {\"query\":\"gravitational wave detection\"} "
                    "or {\"query\":\"Alzheimer disease\"} or {\"compound\":\"donepezil\"}"}},
         "required": ["api", "params"]}},
    {"name": "finish", "description": "Finish the investigation with a written report.",
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"}, "report_markdown": {"type": "string",
         "description": "concise report with inline claim:/artifact: evidence IDs"},
         "conclusions": {"type": "array", "items": {"type": "object", "properties": {
             "claim": {"type": "string"},
             "status": {"type": "string", "enum": ["SUPPORTED", "INFERRED",
                                                         "UNSUPPORTED_HYPOTHESIS"]},
             "evidence_ids": {"type": "array", "items": {"type": "string"}},
             "confidence": {"type": "number"}},
             "required": ["claim", "status", "evidence_ids", "confidence"]}}},
         "required": ["title", "report_markdown", "conclusions"]}},
]

_SYSTEM = ("You are a rigorous research analyst in ANY field (physics, economics, materials, CS, "
           "biology…). Given a question, do REAL work: plan briefly, pull structured evidence with "
           "science_query (literature_search / OpenAlex for any field; the biomedical DBs when the "
           "topic is biomedical) when relevant, fetch "
           "real data if useful (open-data hosts only), write and RUN Python in the sandbox to "
           "actually compute an answer (don't just reason — verify numerically), then finish with a "
           "concise, honest report including caveats. Prefer a small, decisive analysis over a sprawling "
           "one. Keep code self-contained and print results. You have at most ~7 tool calls, so be "
           "efficient. If data can't be found, do a rigorous self-contained computational demonstration "
           "instead. Always call run_python at least once before finish. Every supported or inferred "
           "conclusion must cite the supplied claim: IDs or artifact: IDs returned by tools. If evidence "
           "is absent, label the item UNSUPPORTED_HYPOTHESIS; never promote it as a finding.")


def _evidence_packet(question: str, limit: int = 24, required_claim_ids: list[str] | None = None) -> list[dict]:
    """Retrieve exact claim/source packets from the persona graph; no model calls."""
    try:
        from .knowledge import _entities_for
        kg = get_persona().kg
        required = [kg.provenance(cid) for cid in (required_claim_ids or [])]
        required = [claim for claim in required if claim]
        entities = _entities_for(kg, question)
        general = kg.claims_about(entities, limit) if entities else []
        seen, packet = set(), []
        for claim in required + general:
            if claim["claim_id"] not in seen:
                seen.add(claim["claim_id"])
                packet.append(claim)
        return packet[:max(limit, len(required))]
    except Exception:
        return []


def _evidence_prompt(claims: list[dict]) -> str:
    lines = []
    for claim in claims:
        sources = claim.get("sources") or []
        source = next((s for s in sources if s.get("quote")), sources[0] if sources else {})
        lines.append(f"[claim:{claim['claim_id']}] {claim['subject']} [{claim['effect_sign']}] "
                     f"{claim['object']} | {source.get('doi') or source.get('slug') or 'source unknown'} "
                     f"| quote: {source.get('quote') or '(missing exact span)'}")
    return "\n".join(lines) or "(no relevant graph claims found; treat outside facts as hypotheses)"


def _finish_error(value: object, *, ran_code: bool, allowed_ids: set[str],
                  required_ids: set[str] | None = None, relax: bool = False) -> str | None:
    # relax=True on a FORCED finish (out of turns/budget): accept a reasoning-only report so a
    # document lands instead of the whole paid investigation being discarded as "no-finish".
    if not ran_code and not relax:
        return "run_python must succeed or fail visibly before finish"
    if not isinstance(value, dict) or not isinstance(value.get("report_markdown"), str):
        return "finish must contain report_markdown"
    conclusions = value.get("conclusions")
    if not isinstance(conclusions, list) or not conclusions:
        return "finish requires at least one structured conclusion"
    cited = set()
    for item in conclusions:
        if not isinstance(item, dict) or not isinstance(item.get("claim"), str):
            return "each conclusion needs a text claim"
        status = item.get("status")
        ids = item.get("evidence_ids")
        if status not in {"SUPPORTED", "INFERRED", "UNSUPPORTED_HYPOTHESIS"}:
            return "invalid conclusion status"
        if not isinstance(ids, list) or any(not isinstance(x, str) for x in ids):
            return "evidence_ids must be a list of IDs"
        cited.update(ids)
        if status != "UNSUPPORTED_HYPOTHESIS" and not ids:
            return f"{status} conclusions require evidence IDs"
        unknown = [x for x in ids if x not in allowed_ids]
        if unknown:
            return f"unknown evidence IDs: {', '.join(unknown[:3])}"
        confidence = item.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            return "conclusion confidence must be between 0 and 1"
    missing_required = sorted((required_ids or set()) - cited)
    if missing_required:
        return f"required evidence not cited: {', '.join(missing_required[:3])}"
    return None


def _safe_join(project: Path, rel: str) -> Path | None:
    p = (project / rel).resolve()
    return p if project.resolve() in p.parents else None


def investigate(question: str, *, parent_id=None, max_turns: int = 8,
                evidence_claim_ids: list[str] | None = None) -> dict:
    if not config.have_key():
        return {"ok": False, "reason": "no-key"}
    if not budget().can_spend():
        return {"ok": False, "reason": "budget"}
    if not sandbox.image_ready():
        return {"ok": False, "reason": "sandbox-image-missing"}
    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    session = ResearchSession(get_persona().paths.runs_dir, question, model=config.MODEL_WORKER,
                              metadata={"parent_event_id": parent_id,
                                        "required_claim_ids": evidence_claim_ids or [],
                                        "sandbox_image": sandbox.IMAGE,
                                        "sandbox_image_digest": sandbox.image_digest()})
    project = get_persona().paths.projects_dir / _slug(question) / session.id
    (project / "results").mkdir(parents=True, exist_ok=True)
    (project / "data").mkdir(parents=True, exist_ok=True)
    (project / "plan.md").write_text(f"# {question}\n\n_started {_now()}_\n", encoding="utf-8")
    logf = project / "log.md"
    logf.write_text(f"# log — {question}\n\n_started {_now()}_\n", encoding="utf-8")
    session.store_text("plan.md", f"# {question}\n\n_started {_now()}_\n",
                       media_type="text/markdown", parent_event_id=session.root_event_id)
    import hashlib as _hl
    steps = []

    def _logstep(kind, detail):
        steps.append({"kind": kind, "detail": detail, "at": _now()})
        with logf.open("a", encoding="utf-8") as f:
            f.write(f"\n**{_now()} · {kind}** — {detail}\n")

    def _tool(name, inp) -> dict:
        try:
            if name == "write_file":
                p = _safe_join(project, inp["path"])
                if p is None:
                    return {"ok": False, "error": "path escapes project"}
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(inp["content"], encoding="utf-8")
                return {"ok": True, "wrote": inp["path"]}
            if name == "fetch_dataset":
                r = datasets.fetch(inp["url"], project / "data", inp.get("filename"))
                if r.get("ok"):
                    sha = _hl.sha256(Path(r["path"]).read_bytes()).hexdigest()[:16]
                    _logstep("fetch_dataset", f"{inp['url']} → {r['rel']} ({r['bytes']}B, sha256:{sha})")
                    r["sha256"] = sha
                else:
                    _logstep("fetch_dataset", f"{inp['url']} → FAILED: {r.get('error','')}")
                log().emit("tool", f"fetch dataset {inp['url'][:70]} → "
                           f"{'ok '+str(r.get('bytes',0))+'B' if r.get('ok') else 'FAIL: '+r.get('error','')}",
                           actor="analyst", parent_id=parent_id)
                return r
            if name == "science_query":
                from ..tools import science
                res = science.call(inp.get("api", ""), inp.get("params", {}) or {})
                _logstep("science_query", f"{inp.get('api')} {json.dumps(inp.get('params', {}))[:80]} "
                         f"-> {'ok' if res.get('ok') else 'fail'}")
                log().emit("tool", f"queried {inp.get('api')} → "
                           f"{'ok' if res.get('ok') else 'fail: '+str(res.get('error',''))[:60]}",
                           actor="analyst", parent_id=parent_id)
                return res
            if name == "run_python":
                code = inp["code"]
                ch = _hl.sha256(code.encode()).hexdigest()[:12]
                (project / "analysis").mkdir(exist_ok=True)
                (project / "analysis" / f"step_{len(steps)}_{ch}.py").write_text(code, encoding="utf-8")
                r = sandbox.run_python(code, project, timeout=90)
                _logstep("run_python", f"code sha256:{ch} → exit {r['exit_code']}"
                         + (" (timeout)" if r.get("timeout") else ""))
                log().emit("tool", f"ran code in sandbox → exit {r['exit_code']}"
                           + (" (timeout)" if r.get("timeout") else ""), actor="analyst",
                           parent_id=parent_id)
                return r
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}
        return {"ok": False, "error": "unknown tool"}

    # Ground conclusions in exact claim/source packets; synthesis notes are orientation only.
    evidence = _evidence_packet(question, required_claim_ids=evidence_claim_ids)
    evidence_artifact = session.store_json("evidence.json", evidence,
                                           parent_event_id=session.root_event_id)
    claim_ids = {f"claim:{claim['claim_id']}" for claim in evidence}
    session.record("evidence_retrieved", {"claims": len(evidence),
                                          "artifact_id": evidence_artifact["id"]},
                   parent_event_id=session.root_event_id)
    known = ""
    try:
        hits = get_persona().vectors.search(question, k=3)
        notes = []
        for h in hits:
            f = get_persona().paths.notes_dir / f"{h.get('slug','')}.md"
            if f.exists():
                notes.append(f.read_text(encoding="utf-8")[:1500])
        if notes:
            known = "\n\nSYNTHESIS NOTES (orientation only; cite the claim IDs above, not these notes):\n\n" + "\n\n---\n\n".join(notes)
    except Exception:
        pass
    messages = [{"role": "user", "content": f"Question to investigate:\n\n{question}\n\n"
                 f"KNOWN EVIDENCE PACKET:\n{_evidence_prompt(evidence)}\n\n"
                 f"Project dir is /work (mounted); write outputs to /work/results/.{known}"}]
    required_ids = {f"claim:{claim_id}" for claim_id in (evidence_claim_ids or [])}
    ran_code, finished, finish_event_id = False, None, None
    assistant_texts = []          # collect the analyst's reasoning so exhausted runs can be salvaged
    total_cost, request_parent = 0.0, session.root_event_id
    for turn in range(max_turns):
        if not budget().can_spend():
            break
        # Wrap-up: once code has run and turns are almost out, FORCE the finish tool so a real report
        # lands instead of being discarded as "no-finish" (turn-exhaustion was the main cause of lost,
        # already-paid-for investigations). Two forced turns leave one retry if the first finish is rejected.
        force_finish = turn >= max_turns - 2      # near the end, force a report even if no code ran
        sys_prompt = _SYSTEM if not force_finish else (_SYSTEM +
            "\n\nYou are out of turns. Call finish NOW with your report and at least one conclusion. "
            "Cite ONLY evidence IDs shown to you; mark anything else UNSUPPORTED_HYPOTHESIS (needs no IDs).")
        message_json = json.dumps(messages, ensure_ascii=False, default=str)
        request_payload = {"turn": turn, "message_count": len(messages),
                           "messages_sha256": _hl.sha256(message_json.encode()).hexdigest(),
                           "allowed_claim_ids": sorted(claim_ids), "forced_finish": force_finish}
        if turn == 0:
            request_payload.update({"system": _SYSTEM, "messages": messages})
        request_id = session.record("model_request", request_payload,
                                    parent_event_id=request_parent)
        call_started = perf_counter()
        resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=4096, system=sys_prompt,
                                      tools=TOOLS, messages=messages,
                                      tool_choice=({"type": "tool", "name": "finish"} if force_finish
                                                   else {"type": "auto"}))
        model_latency_ms = round((perf_counter() - call_started) * 1000)
        u = resp.usage
        call_cost = (u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000
        budget().add(call_cost)   # Sonnet $/Mtok
        total_cost += call_cost
        blocks = []
        for block in resp.content:
            if block.type == "text":
                blocks.append({"type": "text", "text": block.text})
                if block.text.strip():
                    assistant_texts.append(block.text.strip())
            elif block.type == "tool_use":
                blocks.append({"type": "tool_use", "id": block.id, "name": block.name,
                               "input": block.input})
        response_id = session.record("model_response", {"turn": turn, "model": config.MODEL_WORKER,
                                                         "input_tokens": u.input_tokens,
                                                         "output_tokens": u.output_tokens,
                                                         "latency_ms": model_latency_ms,
                                                         "cost_usd": round(call_cost, 6),
                                                         "blocks": blocks},
                                     parent_event_id=request_id)
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                if b.name == "finish":
                    error = _finish_error(b.input, ran_code=ran_code,
                                          allowed_ids=claim_ids | session.artifact_ids,
                                          required_ids=required_ids, relax=force_finish)
                    if error:
                        session.record("finish_rejected", {"turn": turn, "reason": error,
                                                            "input": b.input},
                                       parent_event_id=response_id)
                        results.append({"type": "tool_result", "tool_use_id": b.id,
                                        "content": json.dumps({"ok": False, "error": error})})
                        continue
                    finished = b.input
                    finish_event_id = session.record("finish_accepted", {"turn": turn,
                                                                          "input": finished},
                                                     parent_event_id=response_id)
                    break
                tool_started = perf_counter()
                out = _tool(b.name, b.input)
                tool_latency_ms = round((perf_counter() - tool_started) * 1000)
                if b.name == "run_python":
                    ran_code = True
                evidence_ids = []
                if b.name == "write_file" and isinstance(b.input.get("content"), str):
                    evidence_ids.append(session.store_text(
                        b.input.get("path", "written.txt"), b.input["content"],
                        parent_event_id=response_id)["id"])
                if b.name == "run_python":
                    evidence_ids.append(session.store_text(
                        f"turn-{turn}-analysis.py", b.input.get("code", ""),
                        media_type="text/x-python", parent_event_id=response_id)["id"])
                    evidence_ids.append(session.store_text(
                        f"turn-{turn}-stdout.txt", out.get("stdout", ""),
                        parent_event_id=response_id)["id"])
                    if out.get("stderr"):
                        evidence_ids.append(session.store_text(
                            f"turn-{turn}-stderr.txt", out["stderr"],
                            parent_event_id=response_id)["id"])
                receipt = session.store_json(f"turn-{turn}-{b.name}.json",
                                             {"input": b.input, "output": out,
                                              "latency_ms": tool_latency_ms},
                                             parent_event_id=response_id)
                evidence_ids.append(receipt["id"])
                model_out = {"evidence_ids": evidence_ids, **out}
                tool_event_id = session.record("tool_call", {"turn": turn, "tool": b.name,
                                                               "latency_ms": tool_latency_ms,
                                                               "input": b.input,
                                                               "output": model_out},
                                               parent_event_id=response_id)
                request_parent = tool_event_id
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": json.dumps(model_out)[:6000]})
        if finished:
            break
        if not results:
            break
        messages.append({"role": "user", "content": results})

    if not finished:
        # SALVAGE: the loop ended without a formal finish (turns/budget exhausted). Do NOT discard the
        # paid work — assemble the analyst's actual reasoning into a REPORT.md document, honestly marked
        # exploratory/truncated. A real document beats a lost "no-finish" every time.
        reasoning = "\n\n".join(assistant_texts).strip()
        if reasoning or ran_code:
            title = (question[:117].rsplit(" ", 1)[0] + "…") if len(question) > 120 else question
            report = ("> **exploratory** — investigation truncated (turns/budget ran out); this is the "
                      "analyst's reasoning and any computed output so far, not a completed, "
                      "evidence-backed finding.\n\n" + (reasoning or "_(reasoning not captured; see the "
                      "session's code/stdout artifacts)_"))
            get_persona().paths.drafts_dir.mkdir(parents=True, exist_ok=True)
            draft = get_persona().paths.drafts_dir / f"{_slug(question)}-{session.id[-8:]}.md"
            draft.write_text(f"# {title}\n\n_{_now()} · question: {question} · truncated_\n\n{report}\n",
                             encoding="utf-8")
            (project / "REPORT.md").write_text(f"# {title}\n\n{report}\n", encoding="utf-8")
            session.update(cost_usd=round(total_cost, 6))
            session.finalize("completed", reason="salvaged-truncated")
            return {"ok": True, "reason": "salvaged", "draft": draft.name, "ran_code": ran_code,
                    "project": str(project), "session_id": session.id, "truncated": True}
        session.update(cost_usd=round(total_cost, 6))
        session.finalize("failed", reason="no-finish")
        return {"ok": False, "reason": "no-finish", "project": str(project),
                "session_id": session.id, "ran_code": ran_code}
    title = finished.get("title", question).strip()
    if len(title) > 120:
        title = title[:117].rsplit(" ", 1)[0] + "..."
    report = finished.get("report_markdown", "")
    conclusions = finished.get("conclusions", [])
    # substance banner: grade the whole report by whether any conclusion is actually evidence-backed,
    # so an all-hypotheses report reads as exploratory, not a finding (the substance gate for reports).
    statuses = {c.get("status") for c in conclusions}
    rtier = ("verified" if "SUPPORTED" in statuses else
             "provisional" if "INFERRED" in statuses else "exploratory")
    rbanner = {"verified": "> **verified** — at least one conclusion is backed by cited evidence.",
               "provisional": "> **provisional** — conclusions are inferred, not directly evidenced.",
               "exploratory": "> **exploratory** — hypotheses only; nothing here is evidence-backed yet."}[rtier]
    conclusion_lines = ["## Evidence-linked conclusions"] + [
        f"- **{item['status']} · confidence {float(item['confidence']):.2f}:** {item['claim']} "
        f"({' '.join(f'[{e}]' for e in item['evidence_ids']) or '[no evidence — hypothesis]'})"
        for item in conclusions]
    report = rbanner + "\n\n" + report.rstrip() + "\n\n" + "\n".join(conclusion_lines) + "\n"
    # THE VERIFIED LOOP: an evidence-backed (SUPPORTED) computational conclusion is a TESTED result.
    try:
        from ..memory import verified as vled
        for item in conclusions:
            if item.get("status") == "SUPPORTED" and item.get("evidence_ids"):
                vled.record(item["claim"], "analyst", "verified",
                            evidence=",".join(item["evidence_ids"][:3]), source="investigate")
    except Exception:
        pass
    draft = get_persona().paths.drafts_dir / f"{_slug(question)}-{session.id[-8:]}.md"
    get_persona().paths.drafts_dir.mkdir(parents=True, exist_ok=True)
    draft.write_text(f"# {title}\n\n_{_now()} · question: {question}_\n\n{report}\n", encoding="utf-8")
    (project / "REPORT.md").write_text(f"# {title}\n\n{report}\n", encoding="utf-8")
    # reproducibility manifest: env pin + hashed inputs/outputs + the full step trace
    def _hashes(d):
        out = {}
        if d.exists():
            for f in sorted(d.rglob("*")):
                if f.is_file():
                    out[str(f.relative_to(d)).replace("\\", "/")] = _hl.sha256(f.read_bytes()).hexdigest()
        return out
    manifest = {"question": question, "title": title, "at": _now(),
                "session_id": session.id, "conclusions": conclusions,
                "evidence_claim_ids": sorted(claim_ids),
                "sandbox_image": sandbox.IMAGE, "sandbox_image_digest": sandbox.image_digest(),
                "steps": steps, "code": _hashes(project / "analysis"),
                "datasets": _hashes(project / "data"), "results": _hashes(project / "results")}
    (project / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    # Store every bounded project artifact; large datasets remain in-place with a hash record.
    for path in sorted(project.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        rel = str(path.relative_to(project)).replace("\\", "/")
        if len(data) <= 25 * 1024 * 1024:
            session.store_bytes(rel, data, media_type=mimetypes.guess_type(path.name)[0] or
                                "application/octet-stream", parent_event_id=finish_event_id)
        else:
            session.record("external_artifact", {"path": rel, "bytes": len(data),
                                                  "sha256": _hl.sha256(data).hexdigest()})
    session.store_bytes(draft.name, draft.read_bytes(), media_type="text/markdown",
                        parent_event_id=finish_event_id)
    session.update(cost_usd=round(total_cost, 6))
    session.finalize("completed", title=title, conclusions=conclusions,
                     parent_event_id=finish_event_id)
    log().emit("artifact", f"wrote a report: “{title}” [{rtier}] (real analysis{' with code' if ran_code else ''})",
               actor="analyst", parent_id=parent_id, draft=str(draft.name), ran_code=ran_code,
               session_id=session.id, tier=rtier)
    return {"ok": True, "title": title, "draft": str(draft),
            "project": str(project.relative_to(get_persona().paths.projects_dir)).replace("\\", "/"),
            "session_id": session.id, "ran_code": ran_code}
