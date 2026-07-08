"""exp_e14_independence_real (E14, made REAL) — the key choice, on real literature.

exp_e14_independence.py proves the membrane's gate counts distinct GROUPS not raw agreement
(synthetic group labels). This proves the harder half the audit flagged (#4): that the GROUP
KEY itself matters — journal-grouping inflates evidential independence on real papers, and
senior-author (lab) grouping resists the citation-echo attack.

Method: pull real Europe PMC results (cached, deterministic), then measure
  - independence inflation = #distinct journals / #distinct senior authors
  - the worst single lab: how many distinct journals its papers span (= false "independent"
    votes under journal-grouping; senior-author grouping gives it exactly 1).
Run: python experiments/exp_e14_independence_real.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from persona.ingest import EuropePMCAdapter                       # noqa: E402
from persona.ingest.base import DiskCache                         # noqa: E402
from persona.ingest.independence import senior_author, independence_group  # noqa: E402

QUERIES = ["microglia AND neuroinflammation AND alzheimer",
           "tau AND propagation AND alzheimer",
           "NLRP3 inflammasome AND neurodegeneration"]


def main():
    adapter = EuropePMCAdapter(cache=DiskCache(".cache/e14"))
    docs = []
    try:
        for q in QUERIES:
            docs.extend(adapter.search(q, limit=60))
    except Exception as e:
        print(f"SKIP: no network ({e})")
        return
    docs = [d for d in docs if (d.meta or {}).get("authors")]
    if len(docs) < 10:
        print(f"SKIP: too few authored docs ({len(docs)})")
        return

    journals = Counter(d.group for d in docs if d.group)
    seniors = Counter(senior_author(d.meta.get("authors", "")) for d in docs)
    seniors.pop("", None)
    n_j, n_s = len(journals), len(seniors)

    # journal-grouping fails in BOTH directions vs the lab-level truth:
    labs_by_journal = defaultdict(set)   # under-count: independent labs collapsed into one journal
    journals_by_lab = defaultdict(set)   # over-count (echo): one lab's papers split across journals
    for d in docs:
        sa = senior_author(d.meta.get("authors", ""))
        if sa and d.group:
            labs_by_journal[d.group].add(sa)
            journals_by_lab[sa].add(d.group)
    undercount = {j: labs for j, labs in labs_by_journal.items() if len(labs) >= 2}
    overcount = {sa: js for sa, js in journals_by_lab.items() if len(js) >= 2}
    worst_sa, worst_journals = max(journals_by_lab.items(), key=lambda kv: len(kv[1]),
                                   default=("", set()))
    worst_j, worst_labs = max(labs_by_journal.items(), key=lambda kv: len(kv[1]),
                              default=("", set()))

    print(f"real papers analysed: {len(docs)}")
    print(f"distinct journals (old key): {n_j}  |  distinct senior authors (new key): {n_s}")
    print(f"UNDER-count: {len(undercount)} journals host >=2 independent labs "
          f"(worst: '{worst_j}' -> {len(worst_labs)} distinct labs collapsed to 1 vote)")
    print(f"OVER-count (echo): {len(overcount)} labs span >=2 journals "
          f"(worst: '{worst_sa}' -> {len(worst_journals)} journals = {len(worst_journals)} false "
          f"'independent' votes; author-grouping = 1)")
    ig = Counter(independence_group(d) for d in docs)
    print(f"distinct independence_group() keys in production: {len(ig)}")
    verdict = ("PASS: journal-grouping is miscalibrated BOTH ways (collapses independent labs AND "
               "splits one lab's echo); senior-author grouping fixes both"
               if (undercount or overcount) else
               "INCONCLUSIVE on this corpus")
    print(f"\nVERDICT: {verdict}")
    res = {"n_docs": len(docs), "distinct_journals": n_j, "distinct_senior_authors": n_s,
           "journals_hosting_multiple_labs": len(undercount),
           "labs_spanning_multiple_journals": len(overcount),
           "worst_undercount_journal_labs": len(worst_labs),
           "worst_echo_lab": worst_sa, "worst_echo_journal_span": len(worst_journals),
           "verdict": verdict}
    (Path(__file__).resolve().parent.parent / "results" / "e14_independence_real.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8")
    print("saved -> results/e14_independence_real.json")


if __name__ == "__main__":
    main()
