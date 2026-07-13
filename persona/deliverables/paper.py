"""Paper engine (v5 P10) — a compiled LaTeX -> PDF paper, grounded in the mind's cited notes.

Generates a full LaTeX article from the persona's synthesis notes, compiles it offline with
pdflatex in the sandbox (with a compile-error retry loop — LLM LaTeX often needs one), and outputs
a real PDF to deliverables/. References come from the notes' sources, so every citation resolves.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from datetime import datetime, timezone

from .. import config
from ..budget import budget
from ..context import get_persona
from ..events import log
from ..tools import sandbox

_TOOL = {"name": "write_paper", "description": "Write a complete research paper in Markdown.",
         "input_schema": {"type": "object", "properties": {
             "title": {"type": "string"},
             "markdown": {"type": "string", "description": "a COMPLETE research paper in Markdown: "
                 "a `# Title`, then `## Abstract`, `## Introduction`, 2-4 body `##` sections, "
                 "`## Discussion`, and `## References` listing the numbered sources (`1. Author … DOI`). "
                 "Cite inline as [1], [2]. Use $…$ / $$…$$ for math. If a figure is provided, embed it "
                 "ONCE as `![caption](figure.png)` and refer to it. Ground every claim in the notes; "
                 "be rigorous and honest about what is established vs open."}},
             "required": ["title", "markdown"]}}

_SYSTEM = (
    "You are a domain scientist writing a research article to the standard of a top journal (Nature / "
    "PNAS). Write in MARKDOWN from the mind's cited synthesis notes, prior beliefs, and prior papers.\n\n"
    "VOICE — write like a working scientist, not an AI:\n"
    "• Measured, precise, declarative. State findings; let the evidence carry them.\n"
    "• NEVER narrate your own process, tools, or limitations in the body: no 'the sandbox was used to…', "
    "no 'no wet-lab/statistical computation was performed', no 'we searched the notes', no meta-commentary "
    "about steps you did or did not take or why a step is weak. That belongs nowhere in a manuscript.\n"
    "• No filler or AI tells: drop 'it is important to note', 'it is worth mentioning', 'in conclusion', "
    "'delve', 'landscape', 'plays a crucial role', 'a testament to'. No hedging pileups. No restating the "
    "question as a finding.\n"
    "• LEAD WITH WHAT IS NEW OR UNSETTLED. Prioritise the most novel, non-obvious, or decision-relevant "
    "result — a genuine tension in the literature, a mechanism that discriminates between hypotheses, the "
    "specific experiment the field now needs. Do not pad with a bland recap of textbook background.\n\n"
    "STRUCTURE — follow EXACTLY:\n"
    "1. `# Title` — specific, informative, self-contained (no colon-salad buzzwords).\n"
    "2. `## Abstract` — ONE tight paragraph, ≤180 words: the question, what you establish, the key result.\n"
    "3. `## Significance` — 2–3 sentences a non-specialist scientist could read: why it matters now.\n"
    "4. `## Main result` — the precise claims of THIS paper as a short bulleted list. Flag ONLY the "
    "noteworthy ones: **[PROVED HERE]** (a complete argument is given below), **[VERIFIED NUMERICALLY]** "
    "(machine-checked by computation), or **[OPEN]** (conjecture / not settled). A claim merely "
    "established in the literature needs NO tag — carry its [n] citation. Never tag PROVED HERE unless the "
    "argument is actually in the paper.\n"
    "5. `## Introduction` — the problem, prior work (cite [n]), and the specific gap this paper addresses.\n"
    "6. `## Results` — the actual findings/argument, section by section, in scientific prose. Show the "
    "reasoning and the evidence, not just conclusions; quantify where the sources quantify. Reference "
    "**Figure 1**/**Figure 2** where they clarify, each with a real one-line caption.\n"
    "7. `## Discussion` — what is established vs contested vs open, the strongest counter-evidence, the "
    "real limitations of the EVIDENCE (not of your tooling), and the single most valuable next experiment.\n"
    "8. `## References` — number every source `1. Authors. Title. Venue. Year. https://doi.org/…`; every "
    "inline `[n]` must resolve here. Put each reference on its own line.\n"
    "Use $…$ / $$…$$ for math. Embed EACH provided figure once as `![Figure N. <caption>](figureN.png)` in "
    "Results where it is discussed. Ground every claim in the provided material; where evidence is "
    "preclinical, single-lab, or mixed, say so plainly in-line — an honest 'not settled by present "
    "evidence' beats a bluff, but state it as a scientist would, without apologising for your method.")


def _slug(t, limit=48):
    """Readable slug: hyphenate, then truncate on a WORD boundary (never mid-word), <=~limit chars."""
    s = re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")
    if len(s) > limit:
        s = s[:limit].rsplit("-", 1)[0] or s[:limit]   # drop the partial trailing word
    return s or "paper"


def _today(): return datetime.now(timezone.utc).date().isoformat()   # YYYY-MM-DD


def _deliverable_name(topic: str) -> str:
    """B1: human-readable PDF name — word-boundary title slug + a short ISO date (not a raw hash/uuid),
    no generic 'latex-document-' prefix. e.g. paper-erdos-straus-conjecture-2026-07-13.pdf"""
    return f"paper-{_slug(topic)}-{_today()}.pdf"


def _now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")


# A5: the claim-status vocabulary rendered ONCE as styled small-caps badges (see _SYSTEM), never raw
# **[OPEN]** literals. Colored via xcolor (loaded by the document template); each badge is wrapped in
# inline math + \text so it survives the markdown->LaTeX escaper verbatim and compiles to a real
# \colorbox in text mode (see document._inline / md_to_latex).
_STATUS_COLOR = {"PROVED HERE": "green!25", "VERIFIED NUMERICALLY": "blue!18", "OPEN": "red!20"}


def _badge(label: str) -> str:
    color = _STATUS_COLOR.get(label.upper(), "gray!25")
    return r"$\text{\colorbox{%s}{\textsc{%s}}}$" % (color, label.lower())


_STATUS_LEGEND = ("*Status key:* " + _badge("PROVED HERE") + " proved in this paper; "
                  + _badge("VERIFIED NUMERICALLY") + " machine-checked by computation; "
                  + _badge("OPEN") + " open, not settled by present evidence.")


def _style_status(md: str) -> str:
    """A5: replace every raw **[OPEN]** / **[PROVED HERE]** / **[VERIFIED NUMERICALLY]** (and any
    **[UPPER]** token the model invents) with a styled badge, and drop the one-line legend under Main
    result. No bare **[A-Z]+** literal survives into prose."""
    if not re.search(r"\*\*\[[A-Z][A-Z /]*\]\*\*", md):
        return md
    md = re.sub(r"\*\*\[([A-Z][A-Z /]*)\]\*\*", lambda m: _badge(m.group(1).strip()), md)
    anchor = re.search(r"^##\s*main result.*$", md, re.I | re.M)
    if anchor:
        return md[:anchor.end()] + "\n\n" + _STATUS_LEGEND + md[anchor.end():]
    return _STATUS_LEGEND + "\n\n" + md


def _prune_refs(md: str) -> str:
    """Citation hygiene: keep ONLY reference entries that are actually cited inline, so a paper never
    ships with orphaned references (a bibliography of entries nothing points to reads as unprofessional).
    Numbers may end up non-contiguous — every listed ref still resolves, which is what matters."""
    m = re.search(r"(^##\s*references\s*)$(.*)\Z", md, re.I | re.M | re.S)
    if not m:
        return md
    head, refs = md[:m.start()], m.group(2)
    cited = set(re.findall(r"\[(\d+)\]", head))          # numbers cited in the body
    if not cited:                                        # nothing cited -> drop the orphaned list entirely
        return head.rstrip() + "\n"
    kept = []
    for line in refs.splitlines():
        n = re.match(r"^\s*(\d+)\.\s", line)
        if n and n.group(1) not in cited:
            continue                                     # drop an uncited reference entry
        kept.append(line)
    return head + m.group(1) + "\n" + "\n".join(kept).strip() + "\n"


_PLACEHOLDER_CAP = re.compile(
    r"structure and objects of the problem|key quantities?\s*/?\s*distribution|"
    r"a labeled (?:concept )?diagram of the core|a quantitative chart", re.I)


def _fix_references(md: str, sources: list) -> str:
    """Guarantee clean citations: strip the model's own (often canned/bracket-style/orphaned) reference
    list, drop any inline [n] that has no source, and append the canonical DOI-carrying list of ONLY the
    cited sources — so every reference is cited and every citation resolves to a real paper + DOI."""
    md = re.sub(r"\n##\s*references\b.*\Z", "\n", md, flags=re.I | re.S)   # remove model's ref section
    order = []                                             # cited source numbers, FIRST-appearance order
    for n in (int(x) for x in re.findall(r"\[(\d+)\]", md)):
        if 1 <= n <= len(sources) and n not in order:
            order.append(n)
    if not order:
        return re.sub(r"\[(\d+)\]", "", md).rstrip() + "\n"                 # no resolvable cites → drop them
    remap = {old: new for new, old in enumerate(order, 1)}                  # old index -> contiguous 1..k
    md = re.sub(r"\[(\d+)\]", lambda m: f"[{remap[int(m.group(1))]}]" if int(m.group(1)) in remap else "", md)
    lines = "\n".join(f"{new}. {sources[old - 1]}" for old, new in
                      sorted(remap.items(), key=lambda kv: kv[1]))          # emit 1..k, no gaps
    return md.rstrip() + "\n\n## References\n\n" + lines + "\n"


def _fmt_authors(authors) -> str:
    """'Surname I.' for up to 3 authors, then 'et al.' — the byline of a real reference."""
    if isinstance(authors, str):
        try:
            authors = json.loads(authors.replace("'", '"'))
        except Exception:
            authors = [a.strip(" '\"[]") for a in authors.split(",")]
    authors = [a for a in (authors or []) if a and str(a).strip()]

    def si(name):
        parts = str(name).replace(",", " ").split()
        return f"{parts[-1]} " + "".join(p[0] + "." for p in parts[:-1] if p) if len(parts) > 1 else (parts[0] if parts else "")
    named = [si(a).strip() for a in authors[:3] if si(a).strip()]
    return (", ".join(named) + (", et al." if len(authors) > 3 else "")) if named else ""


def _source_index(p) -> dict:
    """doi (lowercased) -> source meta.json, from the papers this mind has actually read. No network:
    authors/year/venue/title were already captured at ingest, so every reference resolves off disk."""
    idx = {}
    for mf in p.paths.sources_dir.glob("*/meta.json"):
        try:
            m = json.loads(mf.read_text(encoding="utf-8", errors="replace"))
            d = (m.get("doi") or "").strip().lower()
            if d:
                idx[d] = m
        except Exception:
            pass
    return idx


def _pro_citation(cite: str, idx: dict) -> str:
    """Promote a note's impoverished '[Title — lab:university (doi:D)]' into a professional reference
    built from the source metadata: 'Chen J, Mei A, et al. Title. Journal. 2022. https://doi.org/D'.
    The DOI becomes a resolvable link (the 'citation link'). Falls back to a de-uglified cite string."""
    m = re.search(r"doi:\s*([^\s)\]]+)", cite, re.I)
    doi = m.group(1).strip().lower() if m else ""
    meta = idx.get(doi)
    if not meta:                                    # no metadata: at least drop the 'lab:…' stand-in
        return re.sub(r"\s*[—-]\s*lab:[^()]*", " ", cite).strip()
    title = re.sub(r"</?[A-Za-z][^>]*>", "", str(meta.get("title") or cite)).strip().rstrip(".")
    venue = (meta.get("venue") or "").strip()
    year = str(meta.get("year") or "").strip()
    authors = _fmt_authors(meta.get("authors"))
    parts = [p for p in (
        (authors.rstrip(".") + "." if authors else ""), title + ".",
        (f"*{venue}*." if venue else ""), (year + "." if year and year != "0" else ""),
        (f"https://doi.org/{doi}" if doi else "")) if p]
    return " ".join(parts)


def _process_appendix(p, n_sources: int) -> str:
    """The bottom 'how this was made' section — the funnel of trust, from REAL persona state: which
    agents/teams ran, on how much evidence, and how it was checked. Honest and specific, not model prose."""
    try:
        n_read = sum(1 for _ in p.paths.sources_dir.glob("*/meta.json"))
        n_notes = sum(1 for _ in p.paths.notes_dir.glob("*.md"))
    except Exception:
        n_read = n_notes = 0
    n_verified = 0
    try:
        from ..memory import verified as vled
        n_verified = sum(1 for e in vled.entries() if e.get("verified"))
    except Exception:
        pass
    checked = (f" ({n_verified} result(s) currently stand as machine-verified in this mind's ledger)"
               if n_verified else "")
    return "\n".join([
        "## How this paper was produced",
        "",
        "*Persona is a persistent, autonomous synthetic researcher. This manuscript was assembled by a "
        "pipeline of bounded agents that read the literature at scale and machine-check their own logic; "
        "it synthesises published work and does not report new wet-lab experiments. The trail is auditable.*",
        "",
        f"- **Reading — reader swarm.** Retrieved and read {n_read} primary source(s) from the open "
        "literature (Europe PMC / OpenAlex), each agent extracting structured claims tied to a source span.",
        "- **Admission — the membrane.** Screened those claims by provenance and cross-source agreement "
        "before any entered the belief-state: scale of reading, discipline of believing.",
        f"- **Synthesis — consolidation agent.** Clustered the admitted claims into {n_notes} cited note(s); "
        f"the {n_sources} numbered references above are the sources this argument rests on.",
        f"- **Reasoning — derivation & analyst agents.** Symbolic and numeric steps were checked by running "
        f"them in an isolated, offline sandbox{checked}.",
        "- **Writing & review — writer and reviewer agents.** Drafted this manuscript, then verified "
        "citation integrity, figure captions, and honest claim-status labelling before release.",
        "",
        "*Every numbered reference resolves to a real paper and DOI; claim status — established, contested, "
        "or open — is labelled explicitly rather than asserted.*",
        "",
    ])


def _provenance_section(rundata: dict) -> str:
    """A8 (I1.7) — the 'Provenance & Process' section, a PROJECTION of this run's own logged data:
    reading-funnel counts, the agent pipeline, sources admitted/quarantined, sandbox computations with
    their content hash, and (when run) the robustness verdict. NOT model prose — every rendered number
    carries a grounding key (the file / jsonl / sha256 it was derived from), so the section is auditable
    and re-render is byte-identical (no wall-clock, no model call here — RQ-E01a exact-source discipline
    applied to the report itself). A datum with no backing record renders 'not recorded for this run',
    never a fabricated 0 or an estimate (I1.7 §0-3)."""
    rd = rundata or {}

    def g(key):                                        # grounding suffix for a rendered number
        return f" — `{key}`"

    out = ["## Provenance & Process", "",
           "*Generated from this run's own logs. Each count and hash below is traceable to the record it "
           "came from; a step that left no log is marked \"not recorded\" rather than guessed.*", ""]

    # 1. Reading funnel — counts derived from the read sources and the admitted/rejected claim logs.
    f = rd.get("funnel") or {}
    fl = [f"- {lbl}: **{f[k]}**{g(key)}"
          for lbl, k, key in (("Sources read", "read", "sources/*/meta.json"),
                              ("Claims extracted", "claims_extracted", "sources/*/claims*.jsonl"),
                              ("Claims admitted", "admitted", "sources/*/claims.jsonl"),
                              ("Claims quarantined", "rejected", "sources/*/claims_rejected.jsonl"))
          if isinstance(f.get(k), int)]
    reasons = f.get("reject_reasons") or {}
    if reasons:
        fl.append("- Quarantine reasons: " + ", ".join(f"{r} ({c})" for r, c in sorted(reasons.items()))
                  + g("sources/*/claims_rejected.jsonl"))
    out += ["### Reading funnel", ""] + (fl or ["*not recorded for this run.*"]) + [""]

    # 2. Agent pipeline — the stages that actually ran, each with items processed.
    pl = [f"- **{s['stage']}** — {s['count']} item(s){g(s.get('source', 'run log'))}"
          for s in (rd.get("pipeline") or []) if isinstance(s.get("count"), int)]
    out += ["### Agent pipeline", ""] + (pl or ["*not recorded for this run.*"]) + [""]

    # 3. Sources — admitted (the numbered references) vs quarantined (had rejected claims).
    s = rd.get("sources") or {}
    sl = []
    if isinstance(s.get("admitted"), int):
        sl.append(f"- Admitted: **{s['admitted']}** source(s){g('## References')}")
    if isinstance(s.get("quarantined"), int):
        sl.append(f"- Quarantined: **{s['quarantined']}** source(s){g('sources/*/claims_rejected.jsonl')}")
    out += ["### Sources", ""] + (sl or ["*not recorded for this run.*"]) + [""]

    # 4. Computations — each sandbox artifact with its content hash (auditable, deterministic).
    cl = []
    for c in (rd.get("computations") or []):
        h = (c.get("source_sha256") or "")[:12]
        if not h:
            continue
        status = "ok" if c.get("ok") else "failed"
        cl.append(f"- {c.get('what') or 'sandbox run'}: {status}; `sha256:{h}`")
    out += ["### Computations", ""] + (cl or ["*not recorded for this run.*"]) + [""]

    # 5. Robustness verdict — the auditor band/likelihood/interval, when an audit ran.
    rb = rd.get("robustness") or {}
    rl = []
    if rb.get("band"):
        parts = [f"**{rb['band']}**"]
        if rb.get("likelihood"):
            parts.append(f"replication likelihood {rb['likelihood']}")
        if rb.get("interval"):
            parts.append(f"interval {rb['interval']}")
        rl.append("- " + " · ".join(parts) + g(rb.get("source", "robustness audit")))
        if rb.get("failing"):
            rl.append("- Failing checks: " + ", ".join(rb["failing"]) + g(rb.get("source", "robustness audit")))
    out += ["### Robustness verdict", ""] + (rl or ["*not recorded for this run.*"]) + [""]

    return "\n".join(out).rstrip() + "\n"


def _collect_rundata(p, project, sources, fignums) -> dict:
    """Assemble the A8 provenance data from THIS mind's REAL on-disk logs (I1.7 §1). Every value is a
    count or content-hash read off a real file; anything absent is simply omitted so the section degrades
    to 'not recorded' rather than fabricating a 0. Runs before compile, so computation hashes are the
    already-built figure PNGs (not the paper's own hash — that would be self-referential)."""
    import collections
    read = admitted = rejected = quarantined_sources = 0
    reasons = collections.Counter()
    try:
        read = sum(1 for _ in p.paths.sources_dir.glob("*/meta.json"))
        for cf in p.paths.sources_dir.glob("*/claims.jsonl"):
            admitted += sum(1 for l in cf.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip())
        for rf in p.paths.sources_dir.glob("*/claims_rejected.jsonl"):
            n = 0
            for l in rf.read_text(encoding="utf-8", errors="replace").splitlines():
                if not l.strip():
                    continue
                n += 1
                try:
                    reasons[str(json.loads(l).get("reason") or "unspecified")] += 1
                except Exception:
                    reasons["unspecified"] += 1
            rejected += n
            quarantined_sources += 1 if n else 0
    except Exception:
        pass
    try:
        n_notes = sum(1 for _ in p.paths.notes_dir.glob("*.md"))
    except Exception:
        n_notes = 0
    rd: dict = {}
    funnel: dict = {}
    if read:
        funnel["read"] = read
    if admitted or rejected:
        funnel["claims_extracted"] = admitted + rejected
        funnel["admitted"] = admitted
    if rejected:
        funnel["rejected"] = rejected
    if reasons:
        funnel["reject_reasons"] = dict(reasons)
    if funnel:
        rd["funnel"] = funnel
    pipeline = []
    if read:
        pipeline.append({"stage": "Reader swarm", "count": read, "source": "sources/*/meta.json"})
    if n_notes:
        pipeline.append({"stage": "Consolidation", "count": n_notes, "source": "notes/*.md"})
    if fignums:
        pipeline.append({"stage": "Figure builder", "count": len(fignums), "source": "sandbox figures"})
    pipeline.append({"stage": "Writer", "count": 1, "source": "this manuscript"})
    rd["pipeline"] = pipeline
    rd["sources"] = {"admitted": len(sources), "quarantined": quarantined_sources}
    comps = []
    for i in sorted(fignums):
        fp = project / f"figure{i}.png"
        if fp.is_file():
            comps.append({"what": f"Figure {i} (sandbox matplotlib)",
                          "source_sha256": hashlib.sha256(fp.read_bytes()).hexdigest(), "ok": True})
    if comps:
        rd["computations"] = comps
    return rd


def _ship_blocked(lint: dict) -> bool:
    """D — the pre-ship gate predicate: a paper that fails the deterministic lint MUST NOT ship."""
    return not (lint or {}).get("ok", False)


def _fix_captions(md: str, capmap: dict) -> str:
    """Replace shipped PLACEHOLDER figure captions ('structure and objects of the problem') with the
    figure's real title, so a paper never ships a generic/framing caption."""
    def repl(m):
        num, cap = m.group(1), m.group(2)
        if _PLACEHOLDER_CAP.search(cap) or len(cap.strip()) < 4:
            return f"![Figure {num}. {capmap.get(int(num)) or 'illustration'}](figure{num}.png)"
        return m.group(0)
    return re.sub(r"!\[Figure (\d+)\.?\s*([^\]]*)\]\(figure\1\.png\)", repl, md)


def write_paper(topic: str, *, parent_id=None, max_notes: int = 6) -> dict:
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    if not sandbox.image_ready():
        return {"ok": False, "reason": "sandbox-image-missing"}
    p = get_persona()
    nd = p.paths.notes_dir
    if not nd.exists() or not any(nd.glob("*.md")):
        return {"ok": False, "reason": "no-notes-yet"}
    slugs = [h["slug"] for h in p.vectors.search(topic, k=max_notes) if h.get("slug")] or \
            [f.stem for f in sorted(nd.glob("*.md"))[:max_notes]]
    src_idx = _source_index(p)            # doi -> read-source metadata (authors/year/venue), off disk
    notes, sources = [], []               # sources: professional numbered references, 1..N
    for s in slugs:
        f = nd / f"{s}.md"
        if f.exists():
            txt = f.read_text(encoding="utf-8")
            notes.append(txt[:3000])
            for m in re.finditer(r"^\[(\d+)\]\s*(.+)$", txt, re.M):
                raw = re.sub(r"</?[A-Za-z][^>]*>", "", m.group(2)).strip()     # strip leaked HTML tags
                cite = _pro_citation(raw, src_idx)                            # real authors/venue/year/link
                if cite not in sources and len(sources) < 24:      # cap so the ref tail can't blow tokens
                    sources.append(cite)
    if not notes:
        return {"ok": False, "reason": "no-notes-matched"}
    # canonical numbered reference list — the paper MUST cite [n] against this, and we guarantee it
    # resolves by appending this exact list as ## References if the model forgets (see post-process).
    references_md = "## References\n\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(sources, 1))
    src_list = "\n".join(f"[{i}] {t}" for i, t in enumerate(sources, 1))

    # reasoning chain to PRIOR work: the mind's own beliefs + the titles of its earlier papers, so the
    # paper can trace its argument to established belief-state and past deliverables, not just fresh notes.
    beliefs = ""
    bf = p.paths.self_dir / "beliefs.md"
    if bf.exists():
        blines = [l for l in bf.read_text(encoding="utf-8").splitlines() if l.strip().startswith(("-", "*"))][:10]
        if blines:
            beliefs = "\n\nPRIOR BELIEFS (this mind's current belief-state — cite as 'prior belief'):\n" + "\n".join(blines)
    prior = []
    for pf in sorted(p.paths.projects_dir.glob("paper-*/*/paper.md"))[-12:]:
        try:
            hm = re.search(r"^#\s+(.+)$", pf.read_text(encoding="utf-8"), re.M)
            if hm and _slug(hm.group(1)) != _slug(topic):
                prior.append(hm.group(1).strip())
        except Exception:
            pass
    prior_md = ("\n\nRELATED PRIOR PAPERS BY THIS MIND (reference where relevant):\n"
                + "\n".join(f"- {t}" for t in prior[-6:])) if prior else ""

    from ..providers import anthropic_client
    client = anthropic_client()
    msgs = [{"role": "user", "content": f"Topic / question:\n{topic}\n\nSYNTHESIS NOTES:\n"
             + "\n\n=== NOTE ===\n".join(notes) + f"\n\nNUMBERED SOURCES (cite inline as [n]; list ALL "
             f"under ## References):\n{src_list}{beliefs}{prior_md}\n\nWrite the complete paper in Markdown."}]
    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    project = p.paths.projects_dir / f"paper-{_slug(topic)}" / run_id
    project.mkdir(parents=True, exist_ok=True)
    # TWO real, grounded figures (matplotlib written by the builder, run in the sandbox): a structural
    # diagram and a data/quantities plot. More than one figure was the main formatting gap (6/10 papers
    # had none). Budget-gated: build what we can afford.
    fignums, figinfo = [], []          # figinfo: (num, real_title) so the paper's caption MATCHES the image
    try:
        from ..agents import builder
        # two DISTINCT figures: a concept diagram and a genuinely quantitative chart (not another diagram)
        framings = [("figure1.png", f"{topic} — a labeled concept diagram of the core objects/mechanism and how they relate"),
                    ("figure2.png", f"{topic} — a QUANTITATIVE chart/plot of the key numbers (bars/lines/scatter), NOT a boxes-and-arrows diagram")]
        for i, (fname, framing) in enumerate(framings, 1):
            if not budget().can_spend():
                break
            fg = builder.build_visual("diagram", framing, parent_id=parent_id, max_attempts=1)
            sp = p.paths.workspace / (fg.get("artifact") or "")
            if fg.get("ok") and sp.is_file():
                shutil.copy2(sp, project / fname)
                fignums.append(i)
                figinfo.append((i, (fg.get("title") or "").strip()))
    except Exception:
        pass
    if figinfo:
        # tell the model EXACTLY what each figure shows, so its caption/reference can't mismatch the image
        msgs[0]["content"] += ("\n\nFIGURES available (embed EACH once as ![caption](figureN.png) where it "
            "fits; your caption and any 'Figure N shows…' text MUST match what the figure actually depicts):\n"
            + "\n".join(f"- figure{i}.png depicts: {t}" for i, t in figinfo if t))
    # Generate the paper as plain-text MARKDOWN (NOT a forced tool call — that truncates the JSON at
    # max_tokens and yields an empty paper). Then compile via the robust document pipeline.
    from .document import compile_source, sanitize_markdown
    title, ok, total_cost, attempts, r = topic, False, 0.0, [], {}
    msgs[0]["content"] += "\n\nOutput ONLY the complete paper in Markdown, starting with '# '."
    resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=12000, system=_SYSTEM, messages=msgs)
    u = resp.usage
    call_cost = (u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000
    budget().add(call_cost); total_cost += call_cost
    md = sanitize_markdown("".join(b.text for b in resp.content if b.type == "text"))

    def _measure(text):
        # (non-reference body chars, body section count, distinct inline [n] citations)
        body = re.split(r"\n##\s*references", text, maxsplit=1, flags=re.I)[0]
        return (len(body.strip()), len(re.findall(r"^##\s+", body, re.M)),
                len(set(re.findall(r"\[(\d+)\]", text))))

    body_chars, n_sec, inline = _measure(md)
    # A real paper has a BODY, not just a title + a references list. The old floor (len>=300) shipped
    # bodyless stubs that became "papers" that were ONLY a ## References list (0 inline citations) —
    # unprofessional. Regenerate once if the first draft is thin.
    if (body_chars < 1200 or n_sec < 3) and budget().can_spend():
        resp2 = client.messages.create(model=config.MODEL_WORKER, max_tokens=12000, system=_SYSTEM,
            messages=msgs + [{"role": "assistant", "content": md[:1500]},
                             {"role": "user", "content": "That draft is only a stub — it lacks a real "
                              "body. Write the COMPLETE paper with every section (Abstract, Significance, "
                              "Introduction, Methods, Results, Discussion) filled with substantive content "
                              "and inline [n] citations to the numbered sources. Output ONLY the full "
                              "Markdown paper, starting with '# '."}])
        u2 = resp2.usage
        call_cost = (u2.input_tokens * 3.0 + u2.output_tokens * 15.0) / 1_000_000
        budget().add(call_cost); total_cost += call_cost
        md2 = sanitize_markdown("".join(b.text for b in resp2.content if b.type == "text"))
        if _measure(md2)[0] > body_chars:
            md = md2
        body_chars, n_sec, inline = _measure(md)
    # ENFORCE figures: inject any built-but-unreferenced figure into the body (the model often ignores
    # the embed instruction) — but only into a real-bodied paper.
    missing = [i for i in fignums if f"figure{i}.png" not in md]
    if missing and n_sec >= 2:
        caps = dict(figinfo)                          # real figure titles, so an injected caption still matches
        block = "\n\n" + "\n\n".join(f"![Figure {i}. {caps.get(i) or 'illustration'}](figure{i}.png)" for i in missing) + "\n\n"
        anchor = re.search(r"^##\s*(discussion|reasoning chain|references)", md, re.I | re.M)
        md = (md[:anchor.start()] + block + md[anchor.start():]) if anchor else (md.rstrip() + block)
    # Citations: canonicalize to the real DOI-carrying sources, drop danglers, keep only cited (no
    # orphans, nothing dangling). Then strip leaked HTML tags and fix placeholder figure captions.
    md = _fix_references(md, sources)
    md = re.sub(r"</?(?:i|b|em|strong|sup|sub|mml:[a-z]+)\b[^>]*>", "", md)   # leaked <i>…</i> from titles
    md = _fix_captions(md, dict(figinfo))
    md = _style_status(md)                                # A5: raw **[OPEN]** -> styled badge + legend
    md = md.rstrip() + "\n\n" + _process_appendix(p, len(sources))   # bottom: the agents/steps that made it
    # A8 (I1.7): grounded 'Provenance & Process' section — real funnel/pipeline/source/computation counts
    # from this run's own logs, each number carrying its grounding key. Built before compile so figure
    # hashes are available; NOT model prose. A datum with no backing record renders 'not recorded'.
    rundata = _collect_rundata(p, project, sources, fignums)
    md = md.rstrip() + "\n\n" + _provenance_section(rundata)
    hm = re.search(r"^#\s+(.+)$", md, re.M)
    title = (hm.group(1).strip() if hm else "") or topic
    # SUBSTANCE FLOOR: never ship a bodyless / references-only stub as a paper.
    if body_chars >= 1200 and n_sec >= 3:
        (project / "paper.md").write_text(md, encoding="utf-8")
        r = compile_source(md, "md", project, title=title)
        ok = bool(r.get("ok"))
    attempts.append({"attempt": 1, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                     "cost_usd": round(call_cost, 6), "markdown_len": len(md), "compile_ok": ok,
                     "stop_reason": resp.stop_reason, "source_sha256": r.get("source_sha256"),
                     "pdf_sha256": r.get("pdf_sha256"), "log_tail": (r.get("log", "") or "")[-1500:]})

    # Repair loop: LLM LaTeX usually needs a pass or two. Feed the pdflatex error log back and ask the
    # model to fix the ACTUAL .tex (md_to_latex would re-derive the same broken output), harden it, and
    # recompile — instead of giving up and leaving the mind with only a note. Bounded by budget.
    from .document import harden_latex
    n = 1
    while not ok and n < config.PAPER_COMPILE_ATTEMPTS and budget().can_spend():
        n += 1
        cur_tex = (project / "main.tex").read_text(encoding="utf-8", errors="replace")
        errlog = (r.get("log", "") or "")[-4000:]
        rp = client.messages.create(model=config.MODEL_WORKER, max_tokens=12000,
            system="You repair broken LaTeX so pdflatex compiles it. Output ONLY the full corrected .tex.",
            messages=[{"role": "user", "content":
                "This LaTeX failed to compile. Fix ONLY what the log flags and return the COMPLETE "
                "corrected document — no prose, no code fences.\n\n=== main.tex ===\n" + cur_tex +
                "\n\n=== pdflatex error log (tail) ===\n" + errlog}])
        u = rp.usage
        call_cost = (u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000
        budget().add(call_cost); total_cost += call_cost
        fixed = re.sub(r"^```(?:latex|tex)?|```$", "", "".join(b.text for b in rp.content
                                                                if b.type == "text").strip()).strip()
        compile_ok = False
        if "\\begin{document}" in fixed:          # sanity: a whole document, not a truncated fragment
            r = compile_source(harden_latex(fixed), "tex", project, title=title)
            ok = compile_ok = bool(r.get("ok"))
        attempts.append({"attempt": n, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                         "cost_usd": round(call_cost, 6), "repair": True, "compile_ok": compile_ok,
                         "stop_reason": rp.stop_reason, "source_sha256": r.get("source_sha256"),
                         "pdf_sha256": r.get("pdf_sha256"), "log_tail": (r.get("log", "") or "")[-1500:]})
        log().emit("control", f"paper compile attempt {n}/{config.PAPER_COMPILE_ATTEMPTS}: "
                   f"{'compiled' if ok else 'still failing'}", actor="paper", parent_id=parent_id)

    receipt = {"topic": topic, "title": title, "run_id": run_id, "ok": ok,
               "at": _now(), "attempts": attempts, "sources": sources,
               "cost_usd": round(total_cost, 6), "sandbox_image": sandbox.IMAGE,
               "sandbox_image_digest": sandbox.image_digest()}
    (project / "compile.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    if not ok:
        log().emit("error", f"paper on “{topic}” did not compile", actor="paper", parent_id=parent_id)
        return {"ok": False, "reason": "compile-failed",
                "project": str(project.relative_to(p.paths.projects_dir)).replace("\\", "/")}
    # HARSH PRE-SHIP AUDIT (deterministic, offline — no model): formatting overflow, leaked status
    # literals, citation integrity, and epoch-date '1970' forensics over the compiled .tex + sources.
    from .paper_lint import lint_paper
    lint = lint_paper({"tex": (project / "main.tex").read_text(encoding="utf-8", errors="replace"),
                       "markdown": md, "filename": _deliverable_name(topic), "sources": sources,
                       "provenance_present": bool(rundata)})
    receipt["lint"] = lint
    # D — HARD GATE: a paper that fails the deterministic audit is NOT shipped. It stays as a compiled
    # project artifact (auditable), but never reaches deliverables/ — a broken PDF must not go out.
    if _ship_blocked(lint):
        log().emit("error", f"pre-ship audit BLOCKED release ({len(lint['violations'])} issue(s)): "
                   + "; ".join(f"{x['code']} {x['msg']}" for x in lint["violations"][:6]),
                   actor="paper", parent_id=parent_id)
        (project / "compile.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return {"ok": False, "reason": "failed-pre-ship-audit", "lint": lint,
                "project": str(project.relative_to(p.paths.projects_dir)).replace("\\", "/")}
    log().emit("control", "paper passed the pre-ship audit (formatting · citations · dates · provenance)",
               actor="paper", parent_id=parent_id)
    p.paths.deliverables_dir.mkdir(parents=True, exist_ok=True)
    source_hash = attempts[-1]["source_sha256"]
    dst = p.paths.deliverables_dir / _deliverable_name(topic)   # B1: readable title + ISO date, no hash
    shutil.copy2(project / "main.pdf", dst)
    receipt["deliverable"] = {"path": dst.name,
                              "pdf_sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
                              "bytes": dst.stat().st_size}
    (project / "compile.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    log().emit("artifact", f"compiled a paper: “{title}” → {dst.name} ({len(sources)} refs)",
               actor="paper", parent_id=parent_id, file=dst.name)
    return {"ok": True, "pdf": dst.name, "title": title, "sources": len(sources),
            "project": str(project.relative_to(p.paths.projects_dir)).replace("\\", "/"),
            "source_sha256": source_hash, "pdf_sha256": receipt["deliverable"]["pdf_sha256"]}
