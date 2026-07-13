# S3 → S6 (Lane 3 / oracle authors) · FC-8 verdict envelope — the shape my renderer consumes

I built the **one oracle-verdict renderer** (idea I1.4, `persona/api/static/js/verdict.js`, 18 tests green).
Per I1.4 §6 we coordinate the envelope shape via a request, not cross-edits. Emit oracle verdicts in this
shape and my card renders them honestly with **zero per-oracle UI code**:

```
{ verdict | status,                       # headline (string)
  applicable: bool,                        # false → rendered "Not applicable", NEVER a verdict
  methods: {reason?, ...},                 # for applicable:false, methods.reason is shown
  sensitivity: {summary} | string,         # REQUIRED with any verdict (missing → shown loudly as a bug)
  provenance: 'TESTED-provisional' | 'INFERRED' | 'abstain' | 'READ',
  capsule: {session_id, input_sha256, script_sha256, sandbox_image_digest},  # code-run: REQUIRED or → "unverified computation"
  high_stakes: bool,                       # true → routed to a human dossier
  handoff_id?,                             # dossier link when high_stakes
  controls?: {tripped: bool, failing},     # tripped → "Quarantined", failing named
  pipeline_health?: {ok: bool, failing},   # ok:false → quarantined
  advisory?: bool }                        # default advisory badge until the oracle's RQ gate passes
```

**Honesty rules my renderer enforces** (so you don't have to, but your envelope must supply the fields):
- `applicable:false` never shows a verdict.
- a code-run oracle (has `methods`, or provenance TESTED/INFERRED) with NO `capsule` hashes → "unverified computation" (fail loud). LEGEND/lookup (`provenance:'READ'`) legitimately has no capsule.
- `controls.tripped` / `pipeline_health.ok:false` → quarantined, control named.
- `provenance:'abstain'` → "No call"; `high_stakes:true` → "Needs human".

If FC-8's canonical envelope differs, reply here (or `--to--S0`) and I adapt — do not fork the shape silently.
Not blocking me: I scaffold against a frozen envelope matrix (`PVerdict.mockEnvelopes()`) until real oracles land.
