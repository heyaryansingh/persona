"""FC-4 (part 2): the value-of-information queue — Persona's advisory "what should I resolve next?".

Ranks unconfirmed, live beliefs on a topic by *value of information ÷ cost*: a claim is worth
resolving when it is **load-bearing** (many downstream beliefs depend on it) and **contested**
(the literature disagrees / it is thinly supported), and it is *not* worth re-resolving once a human
or a test has already anchored it. Read-only over the FC-3 KG: no mutation, no model, no network.

This queue is ADVISORY (human-click) until RQ-E17 validates the VoI estimator — so `voi` is a
deterministic PLACEHOLDER, not a calibrated expected-information-gain. I1.3 (ideas/I1.3) says the
real load-bearing weight must integrate *downstream calibrated replication-p*, degrading gracefully
if RQ-E17 fails; here we degrade all the way to the graceful floor: downstream dependent-count.
"""
from __future__ import annotations

# cost -> how much a resolution "costs"; VoI is divided by this to rank. Public re-analysis of an
# already-available dataset is cheapest; a de-novo expensive assay is dearest.
_COST_WEIGHT = {"public_data": 1.0, "cheap_assay": 3.0, "expensive": 10.0}
_CONFIRMED_PROV = {"HUMAN_CONFIRMED", "TESTED"}


def _tokens(*fields: str) -> set:
    out = set()
    for f in fields:
        for w in str(f or "").lower().replace("-", " ").split():
            if len(w) > 3:
                out.add(w)
    return out


def _dataset_available(tokens: set) -> bool:
    """True iff a locally-fetched dataset (see tools/datasets.fetch) names one of the claim's tokens.
    Guarded: no persona context / no datasets dir -> False. ponytail: filename-token match, not a
    semantic dataset index — upgrade to a manifest lookup when datasets carry topic metadata."""
    if not tokens:
        return False
    try:
        from ..context import get_persona
        ddir = get_persona().paths.datasets_dir
        if not ddir.exists():
            return False
        for p in ddir.iterdir():
            name = p.name.lower()
            if any(t in name for t in tokens):
                return True
    except Exception:
        return False
    return False


def value_queue(topic: str, kg=None, dataset_available=None) -> list:
    """Rank candidate next-experiments for `topic` by VoI ÷ cost. Returns a list of
    {question, resolves_claim_id, voi, cost_tier, dataset_available, de_risks_n, run_action},
    highest value first. `kg`/`dataset_available` are injectable for testing (default: the current
    persona's KG via get_kg(), and a local datasets-dir scan)."""
    if kg is None:
        from ..memory.membrane import get_kg
        kg = get_kg()
    if not kg:
        return []
    ds_fn = dataset_available if callable(dataset_available) else _dataset_available

    t = " ".join(str(topic or "").lower().split())

    # Downstream dependents: for edge (src)-[DEPENDS_ON]->(dst), src relies on dst, so resolving dst
    # de-risks every distinct src. de_risks_n(cid) = # distinct srcs of edges whose dst == cid.
    downstream: dict = {}
    for e in kg.dependency_edges() or []:
        downstream.setdefault(e["dst"], set()).add(e["src"])

    # Candidate pool: every live claim (min_independent=1 so single-lab claims — often the most
    # fragile — are included), topic-filtered on subject/object, excluding already-confirmed beliefs.
    rows = []
    for c in kg.beliefs(min_independent=1, min_conf=0.0, limit=500) or []:
        subj, obj = c.get("subject") or "", c.get("object") or ""
        if t and t not in subj.lower() and t not in obj.lower():
            continue
        confirmed = bool(c.get("anchored")) or c.get("provenance") in _CONFIRMED_PROV
        if confirmed:
            continue
        rows.append(c)

    out = []
    for c in rows:
        cid = c["claim_id"]
        subj, obj, sign = c.get("subject") or "", c.get("object") or "", c.get("effect_sign") or "na"
        de_risks_n = len(downstream.get(cid, ()))
        indep = int(c.get("independent_sources") or 0)
        # clamp to [0,1] at the boundary: extraction has been seen to emit confidence > 1, which
        # would make uncertainty (and thus voi) go negative. VoI is never negative.
        conf = min(1.0, max(0.0, float(c.get("confidence") or 0.0)))
        ratio = min(1.0, max(0.0, float((kg.citation_support_ratio(cid) or {}).get("ratio", 0.0))))
        contested = 1.0 - ratio          # 1.0 = fully disputed / uncorroborated
        uncertainty = 1.0 - conf         # 1.0 = no confidence in the current belief

        # VoI PLACEHOLDER (pending RQ-E17): load-bearing (downstream count) amplified by how contested
        # and how uncertain the belief is. Floors at 0.5 so a load-bearing-but-settled claim still
        # ranks above nothing, and so voi is strictly increasing in de_risks_n.
        voi = round((1 + de_risks_n) * (0.5 + contested) * (0.5 + uncertainty), 4)

        toks = _tokens(subj, obj)
        has_data = bool(ds_fn(toks))
        if has_data:
            cost_tier = "public_data"                    # reanalyze the dataset already on disk
        elif indep >= 2:
            cost_tier = "cheap_assay"                    # corroborated enough for a small confirmatory run
        else:
            cost_tier = "expensive"                      # thin evidence -> de-novo work to resolve

        # run_action = CCP-19a prefix dispatch. With data in hand, re-derive via a science oracle
        # (-> science.call); otherwise actively hunt disconfirming evidence (-> queue.enqueue).
        if has_data:
            run_action = f"literature_search:{subj} {obj}".strip()
        else:
            run_action = f"null_hunt:{subj}|{obj}"

        verb = {"+": "raise", "-": "lower", "0": "not affect", "na": "affect"}.get(sign, "affect")
        question = (f"Does {subj} {verb} {obj}? "
                    f"(resolving de-risks {de_risks_n} downstream belief"
                    f"{'s' if de_risks_n != 1 else ''})")

        out.append({
            "question": question,
            "resolves_claim_id": cid,
            "voi": voi,
            "cost_tier": cost_tier,
            "dataset_available": has_data,
            "de_risks_n": de_risks_n,
            "run_action": run_action,
        })

    # value ÷ cost, then most-downstream, then stable by claim_id.
    out.sort(key=lambda r: (-(r["voi"] / _COST_WEIGHT[r["cost_tier"]]), -r["de_risks_n"],
                            r["resolves_claim_id"]))
    return out
