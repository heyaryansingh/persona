"""
P4 retrieval eval (gates the RAG layer). Now IMPLEMENTED.

Known-item retrieval: index abstracts (text only), query with each paper's TITLE, and check
whether its own abstract is retrieved (title<->abstract is a semantic match — titles rarely
share verbatim wording with their abstract, so this rewards real semantic retrieval).

METRIC: MRR@10 and recall@1 for dense (MiniLM) / lexical (TF-IDF) / hybrid (RRF).
GO: hybrid MRR >= max(dense, lexical) (fusion shouldn't hurt) AND hybrid recall@1 >= lexical
    (semantic adds over keywords). Corpus fetched live from Europe PMC (free), cached.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from persona.retrieval import Retriever
from persona.ingest import EuropePMCAdapter
from persona.ingest.base import Document, DiskCache

QUERIES = ["neuroinflammation microglia alzheimer", "tau hyperphosphorylation tangles",
           "amyloid beta plaques", "NLRP3 inflammasome neurodegeneration"]


def build_corpus():
    pmc = EuropePMCAdapter(cache=DiskCache(root=str(Path(__file__).resolve().parent.parent
                                                    / "tests" / "fixtures" / "ingest")))
    seen, docs = set(), []
    for q in QUERIES:
        for d in pmc.search(q, limit=12):
            if d.doc_id not in seen and d.text and d.title:
                seen.add(d.doc_id)
                docs.append(d)
    return docs


def evaluate(docs, mode: str):
    corpus = [Document(d.doc_id, "", d.text, source=d.source, group=d.group) for d in docs]
    r = Retriever().index(corpus)
    mrr, hit1 = 0.0, 0
    for d in docs:
        ranked = r.retrieve(d.title, k=10, mode=mode)
        ids = [x.doc_id for x in ranked]
        if d.doc_id in ids:
            rank = ids.index(d.doc_id)
            mrr += 1.0 / (rank + 1)
            hit1 += 1 if rank == 0 else 0
    n = len(docs)
    return mrr / n, hit1 / n


def main():
    docs = build_corpus()
    print(f"=== P4 retrieval eval | corpus={len(docs)} abstracts (known-item: title->abstract) ===")
    res = {}
    for mode in ("lexical", "dense", "hybrid"):
        mrr, r1 = evaluate(docs, mode)
        res[mode] = (mrr, r1)
        print(f"  {mode:8}  MRR@10={mrr:.3f}  recall@1={r1:.3f}")
    ok = (res["hybrid"][0] >= max(res["dense"][0], res["lexical"][0]) - 1e-6
          and res["hybrid"][1] >= res["lexical"][1] - 1e-6)
    import json
    Path("results").mkdir(exist_ok=True)
    json.dump({k: {"mrr": v[0], "recall@1": v[1]} for k, v in res.items()},
              open("results/p4_retrieval.json", "w"), indent=2)
    print("\nGO — hybrid retrieval works (semantic + lexical fused)" if ok
          else "\nNO-GO — fusion did not help; revisit")


if __name__ == "__main__":
    main()
