"""Cross-field mechanism translation tests (assert-based, stdlib only).
Run: python tests/test_cross_field.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.engine.cross_field import mechanism_tokens, similarity, align  # noqa: E402


def test_mechanism_tokens_strips_stopwords_and_short_words():
    toks = mechanism_tokens("The activation of a cell is in the synapse")
    assert "the" not in toks and "of" not in toks and "is" not in toks
    assert "activation" in toks and "synapse" in toks and "cell" in toks


def test_similarity_identity_and_disjoint():
    assert similarity("microglial activation drives synapse loss",
                       "microglial activation drives synapse loss") == 1.0
    assert similarity("microglial activation drives synapse", "unrelated ocean salinity trends") == 0.0


def test_align_recovers_cross_field_mechanistic_match():
    a_field = ["microglial activation drives synapse loss"]
    b_field = [
        "immune activation triggers synapse elimination",  # same mechanism, different field vocab
        "unrelated ocean salinity trends",
    ]
    pairs = align(a_field, b_field, threshold=0.2)
    assert len(pairs) == 1
    assert pairs[0]["a"] == a_field[0]
    assert pairs[0]["b"] == b_field[0]
    assert pairs[0]["score"] >= 0.2


def test_align_excludes_exact_equal_strings():
    same = "microglial activation drives synapse loss"
    assert align([same], [same], threshold=0.0) == []


if __name__ == "__main__":
    test_mechanism_tokens_strips_stopwords_and_short_words()
    print("PASS test_mechanism_tokens_strips_stopwords_and_short_words")
    test_similarity_identity_and_disjoint()
    print("PASS test_similarity_identity_and_disjoint")
    test_align_recovers_cross_field_mechanistic_match()
    print("PASS test_align_recovers_cross_field_mechanistic_match")
    test_align_excludes_exact_equal_strings()
    print("PASS test_align_excludes_exact_equal_strings")
