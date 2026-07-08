"""Retrieval test — real semantic matching. Run: python tests/test_retrieval.py
(Loads MiniLM on first use; cached after.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.retrieval import Retriever                 # noqa: E402
from persona.ingest.base import Document                # noqa: E402


def _doc(i, title, text, group="J"):
    return Document(f"d{i}", title, text, source="t", group=group)


def test_dense_beats_keywords_on_paraphrase():
    docs = [
        _doc(1, "Microglia in Alzheimer's",
             "Brain-resident immune cells promote inflammatory responses and neuronal loss."),
        _doc(2, "Ocean salinity trends",
             "Sea surface salt concentration varies with latitude and season."),
        _doc(3, "Cardiac hypertrophy",
             "Pressure overload thickens the ventricular wall in the heart."),
    ]
    r = Retriever().index(docs)
    # a paraphrase that shares MEANING but not the exact words of doc 1
    hits = r.retrieve("neuroinflammation driven by microglial activation", k=1, mode="dense")
    assert hits and hits[0].doc_id == "d1", [h.doc_id for h in hits]
    # hybrid should also surface it first
    hits_h = r.retrieve("neuroinflammation driven by microglial activation", k=1, mode="hybrid")
    assert hits_h and hits_h[0].doc_id == "d1"


def test_retrieve_ranks_relevant_over_distractors():
    docs = [_doc(i, f"paper {i}", txt) for i, txt in enumerate([
        "Tau hyperphosphorylation forms neurofibrillary tangles.",
        "Photosynthesis converts light to chemical energy in plants.",
        "NLRP3 inflammasome activation drives neuroinflammation.",
        "Stock market volatility and interest rates.",
    ])]
    r = Retriever().index(docs)
    hits = r.retrieve("inflammasome and brain inflammation", k=2, mode="hybrid")
    ids = [h.doc_id for h in hits]
    assert "d2" in ids, ids   # the NLRP3/neuroinflammation doc must be retrieved


if __name__ == "__main__":
    test_dense_beats_keywords_on_paraphrase()
    print("PASS test_dense_beats_keywords_on_paraphrase")
    test_retrieve_ranks_relevant_over_distractors()
    print("PASS test_retrieve_ranks_relevant_over_distractors")
    print("\nretrieval tests passed.")
