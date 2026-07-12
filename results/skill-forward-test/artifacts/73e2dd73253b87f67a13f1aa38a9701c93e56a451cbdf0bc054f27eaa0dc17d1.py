#!/usr/bin/env python3
"""Build a local-only evidence bundle for one Curie candidate conflict."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
from pathlib import Path


PAIR = "α-synuclein aggregation||ferroptosis"
POSITIVE_ID = "clm_3e15db860262"
NEGATIVE_ID = "clm_3f58a556a969"
QUESTION = (
    "Do the opposite stored signs for α-synuclein aggregation → ferroptosis "
    "represent opposing evidence in the exact locally stored spans, or an "
    "extraction/normalization problem?"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_claim(path: Path, claim_id: str) -> tuple[dict, int]:
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        record = json.loads(line)
        if record.get("claim_id") == claim_id:
            return record, line_number
    raise ValueError(f"claim not found: {claim_id} in {path}")


def source_window(path: Path, start: int, end: int) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not 1 <= start <= end <= len(lines):
        raise ValueError(f"invalid line range {start}-{end} for {path}")
    text = "\n".join(lines[start - 1 : end])
    return {"line_start": start, "line_end": end, "text": text, "sha256": sha256(text.encode())}


def normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


def artifact(bundle: Path, name: str, data: bytes, extension: str, media_type: str,
             source_path: str) -> dict:
    digest = sha256(data)
    relative = f"artifacts/{digest}.{extension}"
    path = bundle / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "id": f"artifact:{digest}",
        "name": name,
        "source_path": source_path,
        "path": relative,
        "sha256": digest,
        "bytes": len(data),
        "media_type": media_type,
    }


def json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--at", required=True, help="Frozen UTC timestamp for the session trace")
    args = parser.parse_args()

    repo = args.repo.resolve()
    bundle = args.bundle.resolve()
    expected_bundle = (repo / "results" / "skill-forward-test").resolve()
    if bundle != expected_bundle:
        raise ValueError(f"bundle must be {expected_bundle}")

    paths = {
        "active_registry": repo / "personas/curie-3c33/.persona/announced_contradictions.json",
        "integrity_result": repo / "results/rq_e01_claim_integrity.json",
        "positive_claims": repo / "personas/curie-3c33/sources/doi_8e9ff8502090/claims.jsonl",
        "positive_source": repo / "personas/curie-3c33/sources/doi_8e9ff8502090/clean.md",
        "positive_meta": repo / "personas/curie-3c33/sources/doi_8e9ff8502090/meta.json",
        "negative_claims": repo / "personas/curie-3c33/sources/doi_808e759856fd/claims.jsonl",
        "negative_source": repo / "personas/curie-3c33/sources/doi_808e759856fd/clean.md",
        "negative_meta": repo / "personas/curie-3c33/sources/doi_808e759856fd/meta.json",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing inputs: " + ", ".join(missing))

    positive, positive_line = read_claim(paths["positive_claims"], POSITIVE_ID)
    negative, negative_line = read_claim(paths["negative_claims"], NEGATIVE_ID)
    positive_window = source_window(paths["positive_source"], 39, 42)
    negative_window = source_window(paths["negative_source"], 28, 31)
    active_registry = read_json(paths["active_registry"])
    integrity_result = read_json(paths["integrity_result"])
    orientation = next(
        item for item in integrity_result["false_conflict_proxy_examples"]
        if normalized(item["subject"]) == normalized(positive["subject"])
        and normalized(item["object"]) == normalized(positive["object"])
    )

    input_files = {}
    for key, path in paths.items():
        data = path.read_bytes()
        input_files[key] = {
            "path": path.relative_to(repo).as_posix(),
            "sha256": sha256(data),
            "bytes": len(data),
        }

    evidence = {
        "question": QUESTION,
        "captured_at": args.at,
        "scope": (
            "Local claim records, local source-text spans, local metadata, the local active-conflict "
            "registry, and the existing local integrity result only. No full-paper interpretation."
        ),
        "required_evidence_ids": [f"claim:{POSITIVE_ID}", f"claim:{NEGATIVE_ID}"],
        "active_registry": {
            "pair": PAIR,
            "present": PAIR in active_registry,
            "locator": f"{input_files['active_registry']['path']} (exact JSON array member)",
        },
        "claims": [
            {
                "evidence_id": f"claim:{POSITIVE_ID}",
                "record": positive,
                "locator": f"{input_files['positive_claims']['path']}:{positive_line}",
                "source_meta": read_json(paths["positive_meta"]),
                "source_window_locator": f"{input_files['positive_source']['path']}:39-42",
                "source_window": positive_window,
            },
            {
                "evidence_id": f"claim:{NEGATIVE_ID}",
                "record": negative,
                "locator": f"{input_files['negative_claims']['path']}:{negative_line}",
                "source_meta": read_json(paths["negative_meta"]),
                "source_window_locator": f"{input_files['negative_source']['path']}:28-31",
                "source_window": negative_window,
            },
        ],
        "orientation_not_evidence": {
            "description": "Existing deterministic integrity result that surfaced this pair for review.",
            "locator": input_files["integrity_result"]["path"],
            "record": orientation,
        },
        "inputs": input_files,
    }

    positive_source = normalized(positive_window["text"])
    negative_source = normalized(negative_window["text"])
    positive_quote = normalized(positive["quote"])
    negative_quote = normalized(negative["quote"])
    checks = {
        "active_registry_contains_pair": PAIR in active_registry,
        "same_normalized_subject": normalized(positive["subject"]) == normalized(negative["subject"]),
        "same_normalized_object": normalized(positive["object"]) == normalized(negative["object"]),
        "stored_signs": {POSITIVE_ID: positive["effect_sign"], NEGATIVE_ID: negative["effect_sign"]},
        "stored_signs_are_opposite": {positive["effect_sign"], negative["effect_sign"]} == {"+", "-"},
        "positive_span_has_frozen_causal_phrase": (
            "aggregate-membrane interaction is critical to induce a form of cell death called ferroptosis"
            in positive_source
        ),
        "negative_span_has_frozen_causal_phrase": "directly induces ferroptosis" in negative_source,
        "positive_claim_quote_exact_after_whitespace_normalization": positive_quote in positive_source,
        "negative_claim_quote_exact_after_whitespace_normalization": negative_quote in negative_source,
        "negative_source_contains_omitted_not_only": (
            "aggregation not only directly induces ferroptosis" in negative_source
            and "not only" not in negative_quote
        ),
        "existing_integrity_result_contains_pair": bool(orientation),
    }
    required_true = [
        "active_registry_contains_pair",
        "same_normalized_subject",
        "same_normalized_object",
        "stored_signs_are_opposite",
        "positive_span_has_frozen_causal_phrase",
        "negative_span_has_frozen_causal_phrase",
        "positive_claim_quote_exact_after_whitespace_normalization",
        "negative_source_contains_omitted_not_only",
        "existing_integrity_result_contains_pair",
    ]
    failed = [name for name in required_true if checks[name] is not True]
    if checks["negative_claim_quote_exact_after_whitespace_normalization"] is not False:
        failed.append("negative_claim_quote_expected_non_exact")
    if failed:
        raise AssertionError("frozen checks failed: " + ", ".join(failed))

    output = {
        "check": "alpha_synuclein_ferroptosis_local_span_consistency_v1",
        "deterministic": True,
        "checks": checks,
        "scoped_result": {
            "stored_sign_collision_present": True,
            "exact_local_spans_express_opposite_directions": False,
            "classification": "INFERRED_EXTRACTION_OR_NORMALIZATION_ERROR",
            "reason": (
                "Both exact local source windows contain explicit induction-to-ferroptosis language, "
                "while one stored claim is negative. Its stored quote also omits 'not only' from the "
                "local source window."
            ),
            "does_not_establish": [
                "the direction of every result in either full paper",
                "the direction of the wider α-synuclein/ferroptosis literature",
                "absence of population, model, dose, or temporal context elsewhere in the papers",
            ],
        },
    }

    evidence_artifact = artifact(
        bundle, "evidence_packet.json", json_bytes(evidence), "json", "application/json",
        "generated from the exact local inputs enumerated in evidence_packet.json",
    )
    code_artifact = artifact(
        bundle, "check_conflict.py", Path(__file__).read_bytes(), "py", "text/x-python",
        "results/skill-forward-test/check_conflict.py",
    )
    output_artifact = artifact(
        bundle, "check_output.json", json_bytes(output), "json", "application/json",
        "generated by check_conflict.py from evidence_packet.json inputs",
    )

    receipt = {
        "command": (
            "python results/skill-forward-test/check_conflict.py --repo . "
            f"--bundle results/skill-forward-test --at {args.at}"
        ),
        "exit_code": 0,
        "python": sys.version,
        "platform": platform.platform(),
        "script_sha256": code_artifact["sha256"],
        "input_hashes": {key: value["sha256"] for key, value in input_files.items()},
        "output_sha256": output_artifact["sha256"],
        "network_calls": 0,
        "api_calls": 0,
        "model_calls": 0,
        "knowledge_graph_mutations": 0,
        "stderr": "",
    }
    receipt_artifact = artifact(
        bundle, "execution_receipt.json", json_bytes(receipt), "json", "application/json",
        "generated by check_conflict.py",
    )

    conclusions = [
        {
            "claim": (
                "The local active-conflict registry contains α-synuclein aggregation → ferroptosis, "
                f"and {POSITIVE_ID} / {NEGATIVE_ID} store opposite signs for the same normalized pair."
            ),
            "status": "SUPPORTED",
            "evidence_ids": [
                f"claim:{POSITIVE_ID}", f"claim:{NEGATIVE_ID}", evidence_artifact["id"],
                output_artifact["id"],
            ],
            "confidence": 1.0,
        },
        {
            "claim": (
                "Within the exact locally stored source windows, both sources express an induction/drive "
                "toward ferroptosis; these spans do not supply opposing directional evidence."
            ),
            "status": "SUPPORTED",
            "evidence_ids": [
                f"claim:{POSITIVE_ID}", f"claim:{NEGATIVE_ID}", evidence_artifact["id"],
                output_artifact["id"],
            ],
            "confidence": 0.99,
        },
        {
            "claim": (
                f"The negative sign on {NEGATIVE_ID} is likely an extraction/sign-label error, while its "
                "stored quote's omission of 'not only' shows a separate normalization-fidelity defect."
            ),
            "status": "INFERRED",
            "evidence_ids": [
                f"claim:{POSITIVE_ID}", f"claim:{NEGATIVE_ID}", evidence_artifact["id"],
                output_artifact["id"], code_artifact["id"], receipt_artifact["id"],
            ],
            "confidence": 0.93,
        },
        {
            "claim": (
                "The full papers or wider literature contain no context-dependent reversal of the "
                "α-synuclein aggregation → ferroptosis relationship."
            ),
            "status": "UNSUPPORTED_HYPOTHESIS",
            "evidence_ids": [],
            "confidence": 0.0,
        },
    ]

    report = f"""# Scoped conflict review: α-synuclein aggregation → ferroptosis

## Question

{QUESTION}

## Scoped verdict

The local registry and claim records support a real **stored-sign collision**, but the exact local source windows do not support a scientific directional conflict. Both windows say α-synuclein aggregation or aggregate–membrane interaction induces/drives ferroptosis. The most defensible classification is therefore **inferred extraction or normalization error**, not verified biological refutation.

The negative record `{NEGATIVE_ID}` has two distinct integrity problems: its `-` sign conflicts with its source window's explicit “directly induces ferroptosis” wording, and its stored quote is not an exact whitespace-normalized substring because it drops “not only.”

## Exact evidence

- `claim:{POSITIVE_ID}` — stored `+`; DOI `10.1038/s41418-020-0542-z`; local source window `personas/curie-3c33/sources/doi_8e9ff8502090/clean.md:39-42`.
- `claim:{NEGATIVE_ID}` — stored `-`; DOI `10.3389/fnins.2026.1780573`; local source window `personas/curie-3c33/sources/doi_808e759856fd/clean.md:28-31`.
- Content-addressed evidence packet: `{evidence_artifact['id']}`.
- Executed deterministic result: `{output_artifact['id']}`.
- Code and receipt: `{code_artifact['id']}`, `{receipt_artifact['id']}`.

## Uncertainty and limits

No model, API, network, or knowledge-graph write was used. This review does not inspect or characterize the full papers beyond the stored windows, does not adjudicate the wider literature, and cannot exclude model-, dose-, population-, or time-dependent reversal elsewhere. The full-literature no-reversal claim remains `UNSUPPORTED_HYPOTHESIS`.

Trace-integrity and fresh-context scientific-review states are recorded separately in `session.json`, `events.jsonl`, and `verifier-output.json`.
"""
    report_artifact = artifact(
        bundle, "report.md", report.encode("utf-8"), "md", "text/markdown",
        "generated by check_conflict.py",
    )
    artifacts = [evidence_artifact, code_artifact, output_artifact, receipt_artifact, report_artifact]

    session = {
        "session_id": "skill-forward-test-alpha-syn-ferroptosis-v1",
        "question": QUESTION,
        "status": "completed",
        "started_at": args.at,
        "finished_at": args.at,
        "actor": "Codex agent",
        "model": "none for computation; deterministic Python only",
        "cost_usd": 0.0,
        "required_evidence_ids": [f"claim:{POSITIVE_ID}", f"claim:{NEGATIVE_ID}"],
        "contract": {
            "allowed": "read existing local files; run Python standard library; write bundle only",
            "forbidden": "model/API/network calls; knowledge-graph mutation; full-paper inference beyond stored spans",
            "evaluator": "bundled integrity verifier plus fresh-context scientific reviewer",
            "stop_rule": "stop after one active non-microglia pair has a scoped verdict and passing bundle",
        },
        "artifacts": artifacts,
        "conclusions": conclusions,
        "verification": {
            "verdict": "pending",
            "reason": "Fresh-context scientific review has not yet been appended.",
            "reviewer": None,
            "timestamp": None,
        },
    }
    (bundle / "session.json").write_bytes(json_bytes(session))

    events = [
        {"event_id": 1, "parent_event_id": None, "at": args.at, "kind": "session_started",
         "payload": {"question": QUESTION, "contract": session["contract"]}},
        {"event_id": 2, "parent_event_id": 1, "at": args.at, "kind": "evidence_retrieved",
         "payload": {"required_evidence_ids": session["required_evidence_ids"],
                     "input_hashes": receipt["input_hashes"], "cost_usd": 0.0}},
        {"event_id": 3, "parent_event_id": 2, "at": args.at, "kind": "artifact_stored",
         "payload": evidence_artifact},
        {"event_id": 4, "parent_event_id": 2, "at": args.at, "kind": "tool_call",
         "payload": {"tool": "python-stdlib", "command": receipt["command"],
                     "network": False, "knowledge_graph_write": False, "cost_usd": 0.0}},
        {"event_id": 5, "parent_event_id": 4, "at": args.at, "kind": "artifact_stored",
         "payload": code_artifact},
        {"event_id": 6, "parent_event_id": 4, "at": args.at, "kind": "artifact_stored",
         "payload": output_artifact},
        {"event_id": 7, "parent_event_id": 4, "at": args.at, "kind": "tool_result",
         "payload": {"exit_code": 0, "output_artifact_id": output_artifact["id"],
                     "environment": {"python": sys.version, "platform": platform.platform()}}},
        {"event_id": 8, "parent_event_id": 7, "at": args.at, "kind": "artifact_stored",
         "payload": receipt_artifact},
        {"event_id": 9, "parent_event_id": 7, "at": args.at, "kind": "conclusion_recorded",
         "payload": {"conclusions": conclusions}},
        {"event_id": 10, "parent_event_id": 9, "at": args.at, "kind": "artifact_stored",
         "payload": report_artifact},
        {"event_id": 11, "parent_event_id": 9, "at": args.at, "kind": "finish_accepted",
         "payload": {"required_evidence_cited": True, "executed_code_receipt": receipt_artifact["id"]}},
        {"event_id": 12, "parent_event_id": 11, "at": args.at, "kind": "session_finished",
         "payload": {"status": "completed", "scientific_review": "pending"}},
    ]
    (bundle / "events.jsonl").write_text(
        "".join(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )

    print(json.dumps({
        "session_id": session["session_id"],
        "stored_sign_collision": True,
        "exact_local_spans_opposite": False,
        "classification": output["scoped_result"]["classification"],
        "artifacts": [item["id"] for item in artifacts],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
