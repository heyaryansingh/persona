"""
P1 de-risking test: does Claude actually extract real STRUCTURED claims from a real
abstract? (The core assumption of v2 — v1's extractor is keyword matching.)

Calls Claude Haiku 4.5 with forced tool-use (constrained structured output) on a real
cached Europe PMC abstract and prints the extracted claims + token usage + est. cost.
Portable (tool-use works across SDK versions); auditable (we see the exact prompt).

Run: python experiments/exp_p1_claude_extraction.py   (needs ANTHROPIC_API_KEY in .env; ~$0.001)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from persona import config
from persona.ingest import EuropePMCAdapter
from persona.ingest.base import DiskCache

EXTRACT_TOOL = {
    "name": "record_claims",
    "description": "Record the falsifiable scientific claims asserted or tested in this abstract.",
    "input_schema": {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string", "description": "entity/intervention"},
                        "relation": {"type": "string",
                                     "enum": ["increases", "decreases", "no_effect",
                                              "associated_with", "causes", "inhibits", "requires"]},
                        "object": {"type": "string", "description": "outcome/entity affected"},
                        "population": {"type": "string", "description": "model/cohort, if stated"},
                        "confidence": {"type": "number",
                                       "description": "0-1, how strongly the abstract asserts this"},
                    },
                    "required": ["subject", "relation", "object"],
                },
            }
        },
        "required": ["claims"],
    },
}


def main():
    if not config.have_key():
        print("SKIP: ANTHROPIC_API_KEY not set (.env). Cannot run the real-extraction test.")
        return
    pmc = EuropePMCAdapter(cache=DiskCache(root=str(Path(__file__).resolve().parent.parent
                                                    / "tests" / "fixtures" / "ingest")))
    docs = pmc.search("neuroinflammation AND alzheimer AND microglia", limit=8)
    doc = next((d for d in docs if d.text), docs[0])
    print(f"ABSTRACT: {doc.title[:80]}\n  {doc.text[:220]}...\n")

    client = config.anthropic_client()
    resp = client.messages.create(
        model=config.MODEL_READER,
        max_tokens=4096,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "record_claims"},
        messages=[{"role": "user",
                   "content": f"Abstract title: {doc.title}\n\nAbstract: {doc.text}\n\n"
                              f"Extract the falsifiable scientific claims as structured tuples "
                              f"(aim for the 3-8 most important; do not pad)."}],
    )
    print(f"stop_reason: {resp.stop_reason} | blocks: {[b.type for b in resp.content]}")
    claims = None
    for block in resp.content:
        if block.type == "tool_use":
            claims = block.input.get("claims", [])
    print(f"MODEL: {config.MODEL_READER}")
    print(f"EXTRACTED {len(claims or [])} structured claims:")
    for c in (claims or []):
        conf = c.get("confidence", "?")
        pop = f" [{c['population']}]" if c.get("population") else ""
        print(f"  - ({c['subject']}) --{c['relation']}--> ({c['object']}){pop}  conf={conf}")
    u = resp.usage
    cost = config.est_cost_usd(config.MODEL_READER, u.input_tokens, u.output_tokens)
    print(f"\nusage: in={u.input_tokens} out={u.output_tokens} tok  | est ${cost:.4f}/abstract "
          f"→ ~${cost*10000:.0f}/10k abstracts (before Batch 50% + cache 90%)")
    ok = claims and len(claims) >= 1
    print("\nGO — real structured extraction works" if ok else "\nNO-GO — no claims extracted")


if __name__ == "__main__":
    main()
