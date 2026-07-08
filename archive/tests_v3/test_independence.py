"""T1.1: evidential independence is keyed on the senior author (lab), not the journal.
Run: python tests/test_independence.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.ingest.base import Document                                  # noqa: E402
from persona.ingest.independence import (senior_author, author_list,     # noqa: E402
                                          independence_group)


def _doc(authors, journal):
    return Document(doc_id="d", title="t", text="x", source="europepmc", group=journal,
                    meta={"authors": authors})


def test_senior_author_is_last_author():
    assert senior_author("Smith AB, Jones CD, Brown EF.") == "brown e"
    assert senior_author("Solo X") == "solo x"
    assert senior_author("") == ""
    assert author_list("A B, C D, et al.") == ["A B", "C D"]   # 'et al' dropped


def test_one_lab_across_journals_is_ONE_group():
    # the echo attack: same senior author, different journals -> same independence group
    a = independence_group(_doc("Doe A, Roe B, Lab PI.", "Journal One"))
    b = independence_group(_doc("Kim S, Park J, Lab PI.", "Journal Two"))
    assert a == b, (a, b)


def test_different_labs_same_journal_are_DIFFERENT_groups():
    # journal-grouping would collapse these; senior-author keeps them independent
    a = independence_group(_doc("X Y, First PI.", "Big Journal"))
    b = independence_group(_doc("Z W, Second PI.", "Big Journal"))
    assert a != b, (a, b)


def test_fallback_to_journal_then_source_when_no_authors():
    assert independence_group(_doc("", "Some Journal")).startswith("jrnl:")
    d = Document(doc_id="d", title="t", text="x", source="europepmc")
    assert independence_group(d).startswith("src:")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} independence tests passed.")
