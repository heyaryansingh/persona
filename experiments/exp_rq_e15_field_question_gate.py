"""RQ-E15: a source-level FIELD gate keeps a persona ON its declared research fields.

The τ=0.70 title-embedding gate (RQ-E14) cuts most cross-domain noise but still admits near-neighbour
off-field papers — e.g. math *education* ("Sixth Grade Students … Addition and Subtraction", cos 0.727)
sits right next to "unit fractions". OpenAlex classifies every work into a `primary_topic.field`
(Mathematics=26, Social Sciences=33, Neuroscience, Medicine, …), so a math persona can filter at the
SOURCE — off-field papers are never even fetched.

Hypothesis: filtering scouted works to the persona's field (`filter=primary_topic.field.id:fields/26`)
drops the education/biomed/physics-ed neighbours the embedding gate misses, while keeping real
number-theory papers.

Metric: on a labeled set of real titles (ON = number theory; OFF = education/neuro/medicine/other),
classify each via OpenAlex's own field and apply the Mathematics filter. Deterministic given OpenAlex.

Gate (SHIP, precision-biased — the user explicitly wants "stop reading useless papers, everything
serves a purpose"): the field gate drops 100% of clearly-off-field papers (incl. the named title) AND
keeps on-topic recall >= 0.85. The residual recall cost is OpenAlex occasionally filing a math paper
under an adjacent field (e.g. "large sieve" → Engineering); it is bounded, mitigated by the
complementary embedding gate (RQ-E14) and by explicit specialization seeding (Phase B), and preferred
by the user over admitting off-field noise. Wired into ingest/sources.py + reader.scout via
selfmind.allowed_field_ids (which keeps only strong-majority fields).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from persona.ingest.sources import service  # noqa: E402
from persona import config  # noqa: E402

MATH = "26"  # OpenAlex Mathematics field id

# labeled real titles — ON = number theory (should pass); OFF = off-field (should be dropped)
LABELED = [
    ("On the Erdős–Straus conjecture", 1),
    ("Denser Egyptian fractions", 1),
    ("Unit fractions and the Erdős–Graham problem", 1),
    ("The distribution of solutions to the Erdős–Straus equation", 1),
    ("Covering systems and the Erdős–Straus conjecture", 1),
    ("On sums of unit fractions and the large sieve", 1),
    ("A note on Egyptian fractions", 1),
    ("Sixth Grade Students Skills of Using Multiple Representations in Addition and Subtraction", 0),
    ("Denser Egyptian fractions in the mathematics classroom", 0),   # education neighbour
    ("Higuchi fractal dimension in EEG aging studies", 0),
    ("Aberrant gene activation in synovial sarcoma", 0),
    ("Blast induced vibrations in open pit mining", 0),
    ("Photonic crystal waveguides for optical computing", 0),
    ("Capital asset prices: a theory of market equilibrium", 0),
]


def _field_of(title: str) -> str | None:
    d = service().get_json("https://api.openalex.org/works",
                           {"search": title, "per_page": 1, "mailto": config.OPENALEX_MAILTO,
                            "sort": "relevance_score:desc"})
    r = (d.get("results") or [{}])[0]
    return ((r.get("primary_topic") or {}).get("field") or {}).get("id", "").rsplit("/", 1)[-1] or None


def run() -> dict:
    rows = []
    tp = fp = tn = fn = 0
    named = ["Sixth Grade Students Skills of Using Multiple Representations in Addition and Subtraction"]
    named_dropped = 0
    for title, label in LABELED:
        fid = _field_of(title)
        passes = (fid == MATH)               # the Mathematics field gate
        rows.append({"title": title[:60], "label": label, "field_id": fid, "passes": passes})
        if label == 1 and passes:
            tp += 1
        elif label == 1 and not passes:
            fn += 1
        elif label == 0 and passes:
            fp += 1
        else:
            tn += 1
        if title in named and not passes:
            named_dropped += 1
    n = len(LABELED)
    acc = (tp + tn) / n
    on_recall = tp / (tp + fn) if (tp + fn) else 0.0
    off_drop = tn / (tn + fp) if (tn + fp) else 0.0
    ship = off_drop == 1.0 and on_recall >= 0.85 and named_dropped == len(named)
    return {"ok": True, "n": n, "accuracy": round(acc, 3),
            "on_topic_recall": round(on_recall, 3), "off_field_dropped": round(off_drop, 3),
            "named_off_field_dropped": f"{named_dropped}/{len(named)}",
            "verdict": "SHIP" if ship else "NO-GO", "rows": rows}


if __name__ == "__main__":
    res = run()
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    for r in res["rows"]:
        mark = "keep" if r["passes"] else "DROP"
        print(f"  {mark}  field={str(r['field_id']):>4}  label={r['label']}  {r['title']}")
    out = ROOT / "results" / "rq_e15_field_gate.json"
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print("saved", out)
