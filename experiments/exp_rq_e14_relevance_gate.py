"""RQ-E14: does a free local-embedding relevance gate keep a persona's reading ON its objective?

Persona read with ZERO relevance filtering, so a math persona (erdos, on the Erdős–Straus conjecture)
pulled ~59% off-objective papers (biomed/physics: synovial sarcoma, EEG fractal dimension, microstrip
lines) that then polluted its belief graph and produced incoherent, empty-bodied syntheses.

Hypothesis: gating each scouted paper's TITLE on its max cosine similarity (bge-small, the embedder the
daemon already runs for canonicalization — free, local, no API) to the persona's DURABLE objective (its
top-weighted interests) separates on-topic from off-topic well enough to ship as a default gate.

Metric: balanced accuracy of the gate at threshold tau on a keyword-labeled subset of the persona's
own 646 real scouted titles (ON = clear number-theory signal; OFF = clear other-domain signal; the two
label sets use DISJOINT vocab from the embedding, so this measures whether embeddings recover the
topical split, not the keywords). Deterministic (bge-small is deterministic) — no seeds needed.

Gate (ship the default): balanced accuracy >= 0.90 AND on-topic recall >= 0.90 at the chosen tau.

Result (2026-07-12, erdos, 646 titles): tau=0.70 -> balanced_acc=0.939, keeps 94% on-topic, drops 94%
off-topic; ~44% of all titles filtered (matches the measured ~59% off-topic). SHIP. Wired into
persona/reading/reader.py::_relevance_filter with PERSONA_RELEVANCE_TAU=0.70.
"""
from __future__ import annotations

import glob
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
from persona.memory.embed import encode  # noqa: E402

ON = re.compile(r"erd[oő]s|straus|egyptian|unit fraction|diophantine|number theor|sieve|congruen|"
                r"modular|prime|elliptic curve|arithmetic|analytic number|residue|\bmod\b", re.I)
OFF = re.compile(r"\beeg\b|sarcoma|blast|vibration|microstrip|photonic|antimalarial|fibronectin|cardiac|"
                 r"heart|protein|cancer|\bcell\b|neural|brain|clinical|synovial|malaria|antenna|catalys|"
                 r"battery|drug|patient|tumou?r|molecul|conflict|news|fluid|flow|rotation|mining|social|"
                 r"innovation|knowledge creat|market", re.I)


def run(persona: str = "erdos", tau_grid=None) -> dict:
    tau_grid = tau_grid if tau_grid is not None else np.arange(0.50, 0.85, 0.01)
    pdir = ROOT / "personas" / persona
    # anchor = strongly-held interests (the durable objective)
    anchor = []
    ifile = pdir / "self" / "interests.md"
    if ifile.exists():
        for l in ifile.read_text(encoding="utf-8").splitlines():
            m = re.match(r"-\s*(.+?)\s*::\s*([\d.]+)", l.strip())
            if m and float(m.group(2)) >= 0.9:
                anchor.append(m.group(1))
    anchor = list(dict.fromkeys(anchor))[:10]
    titles = []
    for f in glob.glob(str(pdir / "sources" / "*" / "meta.json")):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("title"):
            titles.append(d["title"])
    if not anchor or len(titles) < 20:
        return {"ok": False, "reason": "insufficient real data", "anchor": len(anchor), "titles": len(titles)}

    av, tv = encode(anchor), encode(titles)
    sims = (tv @ av.T).max(axis=1)
    on = np.array([s for t, s in zip(titles, sims) if ON.search(t) and not OFF.search(t)])
    off = np.array([s for t, s in zip(titles, sims) if OFF.search(t) and not ON.search(t)])

    best = None
    for tau in tau_grid:
        tpr = float((on >= tau).mean()) if len(on) else 0.0
        tnr = float((off < tau).mean()) if len(off) else 0.0
        ba = (tpr + tnr) / 2
        if best is None or ba > best["balanced_acc"]:
            best = {"tau": round(float(tau), 2), "balanced_acc": round(ba, 3),
                    "on_topic_recall": round(tpr, 3), "off_topic_drop": round(tnr, 3),
                    "frac_all_pass": round(float((sims >= tau).mean()), 3)}
    ship = best["balanced_acc"] >= 0.90 and best["on_topic_recall"] >= 0.90
    return {"ok": True, "persona": persona, "n_titles": len(titles), "n_anchor": len(anchor),
            "labeled_on": len(on), "labeled_off": len(off),
            "on_mean_cos": round(float(on.mean()), 3), "off_mean_cos": round(float(off.mean()), 3),
            "best": best, "verdict": "SHIP" if ship else "NO-GO"}


if __name__ == "__main__":
    res = run()
    print(json.dumps(res, indent=2))
    out = ROOT / "results" / "rq_e14_relevance_gate.json"
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print("saved", out)
