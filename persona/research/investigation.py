"""Investigation (v7) — the unit of work: a persistent, multistep research PROGRAM on one question.

An investigation replaces the old one-shot task as the thing a persona actually works on. It commits
to ONE open question inside a specialization (the master line of thought) and drives a team of
specialized agent-steps through it — gather evidence → admit to the belief graph → synthesize →
compute/prove → write a compiled report → finalize. Each step is a real queue task; the steps are
chained by the queue's dependency engine (`depends_on`), so they run in order across the worker pool
while other investigations run in parallel. The whole thing is a legible folder of documents.

Durable record: `investigations/<slug>/investigation.json` (+ question.md, plan.md, worklog.md, and,
as steps complete, findings.md). Nothing here calls a model — it only defines and launches the plan;
the paid work happens in the step handlers, budget-gated as always.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone

from ..context import get_persona


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(text: str) -> str:
    return (re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:48]) or "investigation"


# The default research pipeline: a linear chain of specialized roles. Each step is (role, task_type,
# param keys). Steps run strictly in order (each depends on the previous), but a step may itself fan
# out a team (gather reads many papers). Kept linear on purpose — a DAG is gold-plating until a
# question needs branching. `question` is threaded into whichever param key each handler reads.
DEFAULT_PLAN = [
    ("gather",      "gather",      "read the literature for this question"),
    ("harvest",     "harvest",     "admit new evidence at the membrane"),
    ("synthesize",  "consolidate", "synthesize what was found into cited notes"),
    ("analyze",     "investigate", "compute with real sandboxed Python / data"),
    ("reason",      "prove",       "derive & machine-check the core claim (sympy)"),
    ("write",       "paper",       "write & compile the report"),
    ("critique",    "critique",    "peer-review the report & revise it if weak"),
    ("finalize",    "finalize_investigation", "record findings and close the loop"),
]


# F1.1 — branching/DAG plan. When a question decomposes into ≥2 independent sub-hypotheses, run one
# `investigate` branch PER sub-hypothesis in PARALLEL (all depending on the shared harvest), then a
# single synthesize step that joins ALL the branches (the DAG join the queue's lease() already
# supports, queue.py:111-129). Fewer serial paid steps on decomposable questions; each branch stays a
# normal grounded investigate run. Falls back to the linear DEFAULT_PLAN when <2 sub-hypotheses —
# "DAG is gold-plating until a question needs branching." Plan steps are (role, type, detail, deps,
# q_override?) where `deps` = list of earlier step indices (None → chain after previous step).
def _branch_plan(sub_hypotheses) -> list:
    subs = [s.strip() for s in (sub_hypotheses or []) if isinstance(s, str) and s.strip()]
    if len(subs) < 2:
        return DEFAULT_PLAN
    plan = [("gather", "gather", "read the literature for this question", None),
            ("harvest", "harvest", "admit new evidence at the membrane", [0])]
    harvest_idx = 1
    analyze_idxs = []
    for sub in subs:
        analyze_idxs.append(len(plan))
        plan.append((f"analyze: {sub[:48]}", "investigate",
                     f"compute/test the sub-hypothesis: {sub}", [harvest_idx], sub))
    plan.append(("synthesize", "consolidate",
                 "synthesize the parallel sub-analyses into cited notes", list(analyze_idxs)))
    prev = len(plan) - 1                                   # the synthesize join
    for role, ttype, detail in (("write", "paper", "write & compile the report"),
                                ("critique", "critique", "peer-review the report & revise it if weak"),
                                ("finalize", "finalize_investigation", "record findings and close the loop")):
        plan.append((role, ttype, detail, [prev]))
        prev = len(plan) - 1
    return plan


def _plan_md(steps: list) -> str:
    """Render the plan as a legible list; branch steps annotate the DAG join they wait on."""
    out = "# plan\n\n"
    for s in steps:
        deps = s.get("deps")
        note = (f"  ↳ after {', '.join('step ' + str(d + 1) for d in deps)}" if deps else "")
        out += f"{s['idx']+1}. **{s['role']}** — {s['detail']}{note}\n"
    return out


class Investigation:
    def __init__(self, meta: dict):
        self.meta = meta

    # --------------------------------------------------------------- identity
    @property
    def id(self) -> str: return self.meta["id"]
    @property
    def slug(self) -> str: return self.meta["slug"]
    @property
    def question(self) -> str: return self.meta["question"]
    @property
    def status(self) -> str: return self.meta.get("status", "open")

    @property
    def folder(self):
        return get_persona().paths.investigations_dir / self.slug

    # --------------------------------------------------------------- create / load / save
    @classmethod
    def create(cls, question: str, *, specialization: str = "", plan=None,
               sub_hypotheses=None) -> "Investigation":
        p = get_persona()
        p.paths.ensure()
        slug = f"{_slug(question)}-{uuid.uuid4().hex[:6]}"
        # F1.1: ≥2 sub-hypotheses → a branching/DAG plan; else the linear default (backward-compatible).
        if plan is None and sub_hypotheses:
            plan = _branch_plan(sub_hypotheses)
        steps = []
        for i, step in enumerate(plan or DEFAULT_PLAN):
            role, ttype, detail = step[0], step[1], step[2]
            deps = step[3] if len(step) > 3 else None
            q_override = step[4] if len(step) > 4 else None
            sd = {"idx": i, "role": role, "type": ttype, "detail": detail,
                  "status": "pending", "task_id": None, "result_ref": None}
            if deps is not None:
                sd["deps"] = deps
            if q_override:
                sd["q"] = q_override
            steps.append(sd)
        meta = {"id": slug, "slug": slug, "question": question.strip(),
                "specialization": specialization, "status": "open", "created": _now(),
                "updated": _now(), "steps": steps, "findings": None}
        inv = cls(meta)
        inv.folder.mkdir(parents=True, exist_ok=True)
        (inv.folder / "question.md").write_text(
            f"# {question.strip()}\n\n_investigation · {specialization or 'general'} · opened {_now()}_\n\n"
            f"The master question this program is pursuing. Every step below serves it.\n", encoding="utf-8")
        (inv.folder / "plan.md").write_text(_plan_md(steps), encoding="utf-8")
        (inv.folder / "worklog.md").write_text(f"# worklog\n\n- {_now()} — opened\n", encoding="utf-8")
        inv.save()
        return inv

    @classmethod
    def open_from_conflict(cls, conflict_id: str, evidence_claim_ids=None) -> "Investigation":
        """FC-1 (loop-closing entry): open an investigation FROM a flagged candidate conflict —
        contradiction → falsifiable investigation. The pinned `evidence_claim_ids` are the exact
        claims whose stored signs collide; they are threaded into the analyze steps so the analyst's
        evidence packet is grounded in them (never generic retrieval — the RQ-E02 discipline).

        Full (F1.10): resolves the conflict → a directional question + two opposing stances via the
        belief graph (import-guarded), fans them into a branch plan (F1.1), dedups against an already-
        open investigation (idempotent), and auto-launches the team (balanced-autonomy: auto-open;
        the enqueued steps are budget-gated at execution). It opens WORK, never a belief — a conflict
        is only a 'true refutation' once the caller (a human/verifier) has judged it so upstream."""
        evidence_claim_ids = list(evidence_claim_ids or [])
        question, sub_hyps = _resolve_conflict(conflict_id, evidence_claim_ids)
        existing = _find_open(question)                       # idempotent: don't reopen live work
        if existing is not None:
            return existing
        inv = cls.create(question, specialization="conflict-resolution", sub_hypotheses=sub_hyps)
        inv.meta["origin"] = {"kind": "conflict", "conflict_id": str(conflict_id),
                              "evidence_claim_ids": evidence_claim_ids}
        inv.meta["evidence_claim_ids"] = evidence_claim_ids   # threaded into analyze steps at launch
        inv.save()
        inv.log(f"opened from conflict {conflict_id} · pinned {len(evidence_claim_ids)} evidence claim id(s)"
                + (f" · {len(sub_hyps)}-way branch" if sub_hyps else " · linear"))
        try:                                                  # auto-launch; guarded so a queue-less caller still gets the object
            inv.launch(get_persona().queue())
        except Exception:
            pass
        return inv

    @classmethod
    def load(cls, slug: str):
        f = get_persona().paths.investigations_dir / slug / "investigation.json"
        if not f.exists():
            return None
        try:
            return cls(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            return None

    @classmethod
    def list_all(cls) -> list["Investigation"]:
        d = get_persona().paths.investigations_dir
        out = []
        if d.exists():
            for f in sorted(d.glob("*/investigation.json")):
                try:
                    out.append(cls(json.loads(f.read_text(encoding="utf-8"))))
                except Exception:
                    pass
        return out

    def save(self) -> None:
        self.meta["updated"] = _now()
        (self.folder / "investigation.json").write_text(
            json.dumps(self.meta, indent=2, ensure_ascii=False), encoding="utf-8")

    def log(self, line: str) -> None:
        wl = self.folder / "worklog.md"
        prev = wl.read_text(encoding="utf-8") if wl.exists() else "# worklog\n\n"
        wl.write_text(prev + f"- {_now()} — {line}\n", encoding="utf-8")

    # --------------------------------------------------------------- launch the team
    def launch(self, queue) -> list[int]:
        """Enqueue the whole step chain, each step depending on the previous, so the queue's
        dependency engine runs the team in order across the worker pool. Returns the task ids."""
        q = self.question
        prev_id = None
        ids = []
        idx_to_tid: dict[int, int] = {}          # F1.1: resolve per-step deps (indices) → task-ids
        for s in self.meta["steps"]:
            params = {"investigation_id": self.id, "step": s["idx"]}
            # thread the question into whatever key each handler reads; a branch analyze step carries
            # its own sub-hypothesis (s["q"]) so each parallel branch investigates its own claim.
            if s["type"] in ("gather",):
                params["interest"] = q
            elif s["type"] == "investigate":
                params["question"] = s.get("q") or q
                if self.meta.get("evidence_claim_ids"):      # F1.10: pin the conflict's exact claims
                    params["evidence_claim_ids"] = self.meta["evidence_claim_ids"]
            elif s["type"] in ("prove", "critique"):
                params["question"] = q
            elif s["type"] in ("paper", "review", "build"):
                params["topic"] = q
            # honor an explicit DAG dependency set (branch plans); else chain after the previous step.
            if s.get("deps"):
                depends_on = [idx_to_tid[d] for d in s["deps"] if d in idx_to_tid] or None
            else:
                depends_on = [prev_id] if prev_id is not None else None
            tid = queue.enqueue(s["type"], prompt=q, priority=2, params=params,
                                investigation_id=self.id, step_idx=s["idx"],
                                depends_on=depends_on)
            s["task_id"] = tid
            idx_to_tid[s["idx"]] = tid
            s["status"] = "running" if depends_on is None else "queued"
            ids.append(tid)
            prev_id = tid
        self.meta["status"] = "running"
        self.save()
        self.log(f"launched a team of {len(ids)} agents across {len(ids)} steps")
        try:
            refresh_now(queue)
        except Exception:
            pass
        return ids

    # --------------------------------------------------------------- finalize
    def finalize(self, queue) -> None:
        """Aggregate the step outcomes into findings.md, gather the produced documents INTO the
        investigation folder (so it's a self-contained research directory), and close it."""
        steps = {s["step_idx"]: s for s in queue.investigation_steps(self.id)}
        done = sum(1 for s in steps.values() if s["status"] == "done")
        lines = []
        for s in self.meta["steps"]:
            qs = steps.get(s["idx"], {})
            s["status"] = qs.get("status", s["status"])
            s["result_ref"] = qs.get("result_ref")
            lines.append(f"- **{s['role']}** ({s['type']}): {s['status']}"
                         + (f" — {s['result_ref']}" if s.get("result_ref") else ""))
        report = self._gather_docs()          # copies report/derivation PDFs into the folder
        self.meta["findings"] = {"report": report, "steps_done": done, "at": _now()}
        self.meta["status"] = "done"
        self.save()
        (self.folder / "findings.md").write_text(
            f"# findings — {self.question}\n\n_closed {_now()} · {done}/{len(self.meta['steps'])} steps completed_\n\n"
            + (f"A compiled report is in this folder: [`report.pdf`](report.pdf).\n\n" if report else "")
            + "## step outcomes\n" + "\n".join(lines) + "\n", encoding="utf-8")
        self.log(f"finalized — {done}/{len(self.meta['steps'])} steps done"
                 + (", report.pdf gathered" if report else ""))
        try:
            refresh_now(queue)
        except Exception:
            pass

    def _gather_docs(self):
        """Copy the compiled report (and any machine-checked derivation) INTO this investigation's
        folder, so the folder is the self-contained document set for the question. Returns the report
        filename if one was produced."""
        import shutil
        dd = get_persona().paths.deliverables_dir
        slug = _slug(self.question)
        report = None
        papers = sorted(dd.glob(f"paper-{slug}*.pdf"), key=lambda f: f.stat().st_mtime, reverse=True)
        if papers:
            shutil.copy2(papers[0], self.folder / "report.pdf")
            report = "report.pdf"
        derivs = sorted(dd.glob(f"derivation-{slug}*.pdf"), key=lambda f: f.stat().st_mtime, reverse=True)
        if derivs:
            shutil.copy2(derivs[0], self.folder / "derivation.pdf")
        return report


def _resolve_conflict(conflict_id: str, evidence_claim_ids: list) -> tuple[str, list | None]:
    """Build the research question + opposing sub-hypotheses for a conflict. If the belief graph can
    resolve a pinned claim to (subject, object), branch into the two directional stances (F1.1); else
    fall back to a generic linear investigation. Import-guarded — never hard-blocks on the membrane."""
    subject = obj = ""
    try:
        kg = get_persona().kg
        for cid in evidence_claim_ids:
            c = kg.provenance(cid)
            if isinstance(c, dict) and c.get("subject") and c.get("object"):
                subject, obj = str(c["subject"]), str(c["object"])
                break
    except Exception:
        pass
    if subject and obj:
        q = (f"Does {subject} raise or lower {obj}? Stored evidence signs collide "
             f"(conflict {conflict_id}) — resolve whether it is a true refutation, context divergence, "
             f"or extraction error.")
        return q, [f"{subject} raises {obj}", f"{subject} lowers {obj}"]
    return (f"Is candidate conflict {conflict_id} a true refutation, a context divergence, "
            f"or an extraction error?"), None


def _find_open(question: str):
    """An already-open investigation covering this question (idempotency guard), else None."""
    try:
        from ..agents import director
        want = director._norm(question)
        for i in Investigation.list_all():
            if director._norm(i.question) == want and i.meta.get("status") != "done":
                return i
    except Exception:
        pass
    return None


def refresh_now(queue) -> None:
    """Regenerate self/now.md — the human-readable 'what I'm working on right now' document: the
    master line of thought made legible (active investigations with live progress + open questions),
    so a reader sees the mind's current focus at a glance and it shows up in the file browser."""
    from .. import selfmind
    p = get_persona()
    invs = Investigation.list_all()
    active = [i for i in invs if i.meta.get("status") == "running"]
    done = [i for i in invs if i.meta.get("status") == "done"]
    out = ["# now — what I'm working on", "", f"_updated {_now()}_", ""]
    try:
        ints = selfmind.interests()
        if ints:
            out += ["## specializations (deepest focus)"]
            out += [f"- {n} · weight {w:.2f}" for n, w in sorted(ints, key=lambda x: -x[1])[:5]] + [""]
    except Exception:
        pass
    out.append("## active investigations")
    if active:
        for i in active:
            steps = {s["step_idx"]: s for s in queue.investigation_steps(i.id)}
            nd = sum(1 for s in steps.values() if s["status"] == "done")
            cur = next((s["role"] for s in i.meta["steps"]
                        if steps.get(s["idx"], {}).get("status") in ("leased", "pending")), "…")
            out.append(f"- **{i.question}** — step {min(nd + 1, len(i.meta['steps']))}/"
                       f"{len(i.meta['steps'])} ({cur})")
    else:
        out.append("- (none active right now)")
    out.append("")
    if done:
        out += ["## recently completed"]
        for i in sorted(done, key=lambda x: x.meta.get("updated", ""), reverse=True)[:5]:
            rep = (i.meta.get("findings") or {}).get("report")
            out.append(f"- {i.question}" + (f" → `{rep}`" if rep else ""))
        out.append("")
    try:
        qs = selfmind.open_questions()
        if qs:
            out += ["## open questions"] + [f"- {q}" for q in qs[:10]] + [""]
    except Exception:
        pass
    p.paths.self_dir.mkdir(parents=True, exist_ok=True)
    (p.paths.self_dir / "now.md").write_text("\n".join(out) + "\n", encoding="utf-8")
