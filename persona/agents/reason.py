"""Reasoning / proof agent (v7) — real logic & math, not just code.

`prove(question)` makes the model produce a RIGOROUS structured derivation (claim → premises →
numbered steps → conclusion) and, crucially, embed a `sympy` assertion for every step that is a
symbolic/numeric identity. Each assertion is then RUN in the offline sandbox, so the derivation is
machine-CHECKED, not merely asserted — the honest difference between "the model says so" and "this
step is verified". The output is a legible derivation document (markdown, compiled to PDF) with each
checkable step marked ✓ verified / ✗ failed, and an honest count of how much was machine-checked.

This is the thinking surface the numeric analyst lacked: exact/symbolic math, algebra, and logic.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from .. import config
from ..budget import budget
from ..context import get_persona
from ..events import log
from ..tools import sandbox

_SYSTEM = (
    "You are a rigorous mathematician/logician. Given a question or claim, produce a STRUCTURED "
    "DERIVATION in Markdown: a `# Derivation: <title>`, a one-line **Claim**, a **Premises** list, "
    "then numbered `## Step k` sections each stating one deductive move in prose. For EVERY step that "
    "is a symbolic or numeric identity/inequality, immediately follow it with a fenced ```python code "
    "block that uses sympy (or mpmath) to ASSERT exactly that step — the block must `raise` (e.g. via "
    "`assert`) if the step is false, and print a one-line confirmation if true. Keep each check "
    "self-contained (its own imports). End with a `## Conclusion`. Be honest: only claim what the "
    "steps establish; if a step is heuristic or unproven, say so and omit its check. Never fabricate a "
    "check that doesn't actually test the step.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(t: str) -> str:
    return (re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")[:48]) or "derivation"


def prove(question: str, *, parent_id=None) -> dict:
    """Produce and machine-check a derivation for `question`. Returns {ok, doc, verified, checks}."""
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    if not sandbox.image_ready():
        return {"ok": False, "reason": "sandbox-image-missing"}
    p = get_persona()

    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    # This model emits a server-side thinking block, so a tight max_tokens can truncate the derivation
    # text away entirely (esp. on a broad question); 10000 leaves headroom without the latency of a
    # huge cap. Retry once, MORE FOCUSED, if the first reply still comes back empty.
    md = ""
    for attempt in range(2):
        if not budget().can_spend():
            break
        prompt = f"Question / claim to derive rigorously:\n{question}"
        if attempt == 1:
            prompt += ("\n\nKeep it focused: state the single most important derivable identity/step "
                       "for this question, give its sympy check, and conclude. Do not exceed ~1200 words.")
        resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=10000, system=_SYSTEM,
                                      messages=[{"role": "user", "content": prompt}])
        u = resp.usage
        budget().add((u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000)
        md = "".join(b.text for b in resp.content if b.type == "text").strip()
        if len(md) >= 120:
            break
    if len(md) < 120:
        return {"ok": False, "reason": "empty-derivation"}

    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    project = p.paths.projects_dir / f"derivation-{_slug(question)}" / run_id
    project.mkdir(parents=True, exist_ok=True)

    # extract every sympy check block and RUN it in the sandbox — this is the machine verification
    blocks = re.findall(r"```python\s*(.*?)```", md, re.S)
    results = []
    for i, code in enumerate(blocks):
        wrapped = code.strip() + '\nprint("__STEP_OK__")\n'
        r = sandbox.run_python(wrapped, project / f"check_{i}", timeout=30)
        ok = r.get("exit_code") == 0 and "__STEP_OK__" in (r.get("stdout") or "")
        results.append({"idx": i, "ok": ok, "stderr": (r.get("stderr") or "")[-300:]})

    verified = sum(1 for r in results if r["ok"])
    total = len(results)
    # annotate the document with the verification outcome (honest: checked vs argued)
    banner = (f"_derivation · {verified}/{total} step-checks machine-verified in the sandbox · {_now()}_"
              if total else f"_derivation · no machine-checkable steps · {_now()}_")
    body = re.sub(r"^#\s+.*$", lambda m: m.group(0) + "\n\n" + banner, md, count=1, flags=re.M)
    if banner not in body:                          # no H1 to anchor under
        body = f"# Derivation\n\n{banner}\n\n" + md
    if total:
        body += "\n\n## verification\n" + "\n".join(
            f"- check {r['idx']+1}: {'✓ verified' if r['ok'] else '✗ failed — ' + (r['stderr'] or 'no output')}"
            for r in results) + "\n"
    (project / "derivation.md").write_text(body, encoding="utf-8")

    # compile to a real PDF deliverable (best-effort; the .md stands on its own if compile fails)
    doc = None
    try:
        from ..deliverables.document import compile_source
        cr = compile_source(body, "md", project, title=f"Derivation: {question[:60]}")
        if cr.get("ok"):
            p.paths.deliverables_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            dst = p.paths.deliverables_dir / f"derivation-{_slug(question)}-{run_id[-8:]}.pdf"
            shutil.copy2(project / "main.pdf", dst)
            doc = dst.name
    except Exception:
        pass

    # FORMAL PROOF (async, strongest tier): for a MATH persona, also submit the statement to Harmonic
    # Aristotle for a kernel-verified Lean 4 proof. Proving takes minutes, so it runs in the background;
    # collect_proofs records the lean-verified result to the ledger when it lands. sympy is the
    # immediate machine-check; a later Lean proof is the formal seal on top.
    try:
        from ..tools import aristotle
        from .. import selfmind
        if aristotle.available() and "26" in (selfmind.allowed_field_ids() or []):
            from ..memory import proofs
            proofs.submit_and_track(question)
    except Exception:
        pass

    # THE VERIFIED LOOP: a machine-checked result becomes a durable TESTED belief — the mind now KNOWS
    # it proved this, not just that it read it. Recorded only when a check actually passed (honest) AND
    # the statement is a PROPOSITION — an interrogative ("Is X …?") is a question, not a proven fact, so
    # it must never enter the ledger as "verified".
    is_question = question.rstrip().endswith("?")
    if total > 0 and not is_question:
        from ..memory import verified as vled
        status = "verified" if verified == total else ("weakened" if verified > 0 else "refuted")
        vled.record(question, "sympy", status, evidence=(doc or "derivation.md"), checks=total,
                    source="prove")

    log().emit("artifact", f"derived “{question[:56]}” — {verified}/{total} steps machine-verified"
               + (f" → {doc}" if doc else ""), actor="reason", parent_id=parent_id, file=doc)
    return {"ok": True, "doc": doc, "verified": verified, "checks": total,
            "project": str(project.relative_to(p.paths.projects_dir)).replace("\\", "/")}
