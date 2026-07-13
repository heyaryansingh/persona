# S4 → S5 — exact shape the extractor now emits for `Claim.qualifiers` (§B)

**Context:** RQ-E06 S4 slice done. `persona/reading/extract.py::validate_claims` now attaches an
**optional** `qualifiers` dict to accepted claims (additive; absent on most claims). Your on-deck
`Claim.qualifiers` storage in `memory/kg.py` should persist exactly this shape. **No action needed
from me on your side — this is the contract so you don't have to reverse-engineer it.**

## What an accepted claim looks like now
```python
{ "subject": ..., "relation": ..., "object": ..., "effect_sign": "+|-|0|na",
  "quote": "<verbatim>", "confidence": 0.0-1.0,
  # OPTIONAL — present only when the model grounded qualifiers in an exact span:
  "qualifiers": {
     "qual_source": "<verbatim sentence, guaranteed in source text>",  # always present if block exists
     "population":   "<str>",              # optional
     "model_system": "in_vivo|in_vitro|post_mortem|cohort",  # optional, enum-validated
     "direction":    "+|-|na",             # optional, enum-validated
     "magnitude":    "<str>",              # optional
     "timepoint":    "<str>",              # optional
     "n":            <int>,                # optional, ints only (bools/floats already stripped)
  }}
```

## Guarantees my side already enforces (you can trust these, no re-validation needed)
- `qualifiers` is **absent** unless at least one substantive field + a **verbatim** `qual_source` survived.
- `qual_source` is guaranteed to be an exact span in the source text (RQ-E01a discipline).
- `model_system`/`direction` are already restricted to the frozen enums; unknown fields already dropped.
- Ungrounded / empty qualifier blocks are stripped **without** rejecting the claim (identity `subject|object|sign` untouched).

## The one thing I need from you
Confirm `kg.py` **preserves `qualifiers` verbatim** (additive column/field) and that claim **identity/convergence stays `subject|object|sign`** — qualifiers must NOT enter the merge key (§B: "identity stays subject|object|sign, convergence preserved"). If your store drops unknown keys today, that's the wire-up.

Incompatible qualifiers on same-identity claims = `context_divergence` (ties to §A labels). My
`exp_rq_e06_evidence_tree.py::qualifiers_compatible` has the compat rule if useful as a reference.

_Not blocking me. Ack in `status/S5` when kg.py persists this, so the end-to-end qualifier path is live._
