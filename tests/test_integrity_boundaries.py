import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from persona import selfmind
from persona.agents import deliberate, knowledge


def test_malformed_reflection_cannot_mutate_questions():
    with TemporaryDirectory() as td:
        self_dir = Path(td)
        questions = self_dir / "open_questions.md"
        questions.write_text("sentinel", encoding="utf-8")
        persona = SimpleNamespace(paths=SimpleNamespace(self_dir=self_dir))
        with patch.object(selfmind, "get_persona", return_value=persona):
            try:
                selfmind.set_open_questions('<parameter name="strategy_note">bad')
                raise AssertionError("a string must not be accepted as a question list")
            except TypeError:
                pass
        assert questions.read_text(encoding="utf-8") == "sentinel"

    bad = {"interests": [], "open_questions": "not-a-list", "priority_reads": [],
           "changelog": "x"}
    try:
        deliberate._validated_output(bad)
        raise AssertionError("malformed reflection output must be rejected")
    except ValueError:
        pass


def test_topic_digest_read_never_checks_budget_or_model_key():
    class KG:
        def search(self, q, limit):
            return [{"type": "entity", "label": "microglia"}]

        def claims_about(self, entities, limit):
            return [{"claim_id": "c1", "subject": "microglia", "effect_sign": "+",
                     "object": "tau", "independent_sources": 1, "confidence": 0.7,
                     "anchored": False, "sources": [{"slug": "s1", "doi": "10/x"}]}]

        def contradictions(self, limit):
            return []

        def subgraph(self, entities):
            return {"nodes": [], "edges": []}

    with patch.object(knowledge.config, "have_key", side_effect=AssertionError("GET checked key")):
        result = knowledge.topic_digest("microglia", KG())
    assert result["ok"] and result["generated"] is False and result["digest"] is None


def test_candidate_conflicts_are_not_verified_contradictions():
    from persona.memory.kg import KG

    fake = SimpleNamespace(contradictions=lambda limit: [{"subject": "a", "object": "b"}])
    items = KG.candidate_conflicts(fake, 10)
    assert items == [{"subject": "a", "object": "b", "status": "candidate_conflict",
                      "conflict_type": "unverified", "needs_human_review": True}]


def test_scheduler_cooldown_and_openalex_query_sanitization():
    from persona import config
    from persona.daemon.supervisor import _should_reflect
    from persona.ingest import sources

    assert not _should_reflect(0, 5.0, 0.0)
    assert _should_reflect(0, config.SCOUT_INTERVAL_S, 0.0)
    captured = {}

    class Service:
        def get_json(self, url, params):
            captured.update(params)
            return {"results": []}

    with patch.object(sources, "service", return_value=Service()):
        sources.openalex_search("Do AI models outperform clinicians?", 1)
    assert captured["search"] == "Do AI models outperform clinicians"


def test_claims_require_schema_and_verbatim_evidence():
    from persona.reading.extract import validate_claims

    good = {"subject": "microglia", "relation": "exacerbates", "object": "tau pathology",
            "effect_sign": "+", "quote": "Microglia exacerbate tau pathology.", "confidence": .9}
    paraphrase = {**good, "quote": "Microglia worsen tau."}
    accepted, rejected = validate_claims([good, paraphrase, "bad"],
                                         "Results:  Microglia exacerbate tau pathology.\n")
    assert accepted == [good]
    assert [r["reason"] for r in rejected] == ["quote-not-verbatim", "claim-not-an-object"]


def test_source_corrections_are_append_only_overlays():
    from persona.memory.membrane import _source_corrections

    with TemporaryDirectory() as td:
        source_dir = Path(td)
        original = {"claim_id": "source-c1", "effect_sign": "-"}
        (source_dir / "claims.jsonl").write_text(json.dumps(original) + "\n", encoding="utf-8")
        (source_dir / "claim_corrections.jsonl").write_text(json.dumps({
            "source_claim_id": "source-c1", "old_effect_sign": "-",
            "new_effect_sign": "+", "reason": "exact quote says exacerbate",
            "session_id": "session-1",
        }) + "\n", encoding="utf-8")

        corrections = _source_corrections(source_dir)
        assert corrections["source-c1"]["new_effect_sign"] == "+"
        assert json.loads((source_dir / "claims.jsonl").read_text(encoding="utf-8"))["effect_sign"] == "-"


def test_latex_compile_rejects_stale_output_and_unsafe_filename():
    from persona.tools import sandbox

    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "main.tex").write_text("invalid", encoding="utf-8")
        (root / "main.pdf").write_bytes(b"stale-pdf")
        failed = SimpleNamespace(returncode=1, stdout="Fatal error: no output PDF", stderr="")
        with patch.object(sandbox.subprocess, "run", return_value=failed) as run:
            result = sandbox.compile_latex(root, "main.tex")
        assert result["ok"] is False and not (root / "main.pdf").exists()
        assert result["exit_code"] == 1 and "Fatal error" in result["log"]
        compile_args = run.call_args_list[0].args[0]
        assert "sh" not in compile_args and "--read-only" in compile_args
        assert compile_args[-1] == "main.tex"

        with patch.object(sandbox.subprocess, "run") as run:
            unsafe = sandbox.compile_latex(root, "main.tex;touch-INJECTED.tex")
        assert unsafe["ok"] is False and unsafe["log"] == "invalid LaTeX filename"
        run.assert_not_called()


def test_research_session_is_append_only_and_content_addressed():
    from persona.sessions import (ResearchSession, append_session_artifact, audit_session,
                                  read_session, verify_session)

    with TemporaryDirectory() as td:
        session = ResearchSession(Path(td), "Does the result reproduce?", model="test-model")
        a = session.store_text("analysis.py", "print(42)", media_type="text/x-python")
        b = session.store_text("copy.py", "print(42)", media_type="text/x-python")
        assert a["id"] == b["id"] and len(session.artifact_ids) == 1
        session.record("tool_result", {"stdout": "42"})
        session.finalize("completed", title="Reproduction", conclusions=[
            {"claim": "It prints 42", "status": "SUPPORTED", "evidence_ids": [a["id"]]}])
        loaded = read_session(Path(td), session.id)
        assert loaded["session"]["status"] == "completed"
        assert [e["event_id"] for e in loaded["events"]] == list(range(1, len(loaded["events"]) + 1))
        crate = json.loads((session.root / "ro-crate-metadata.json").read_text(encoding="utf-8"))
        assert crate["@context"] == "https://w3id.org/ro/crate/1.3/context"
        assert audit_session(Path(td), session.id, "invalidated", "required evidence was omitted")
        audited = read_session(Path(td), session.id)
        assert audited["session"]["status"] == "invalidated"
        assert audited["events"][-1]["kind"] == "verifier_verdict"
        extra = append_session_artifact(Path(td), session.id, "figures/check.svg", b"<svg/>",
                                        media_type="image/svg+xml",
                                        parent_event_id=audited["events"][-1]["event_id"])
        assert extra["source_path"] == "figures/check.svg"
        replay = verify_session(Path(td), session.id)
        assert replay["ok"] and replay["checks"]["artifacts"] == 2
        with session.events_path.open("a", encoding="utf-8") as handle:
            handle.write("{malformed event}\n")
        corrupted = verify_session(Path(td), session.id)
        assert not corrupted["ok"] and "event-json-invalid" in corrupted["errors"][0]


def test_session_event_digest_rejects_valid_json_tampering():
    from persona.sessions import ResearchSession, verify_session

    with TemporaryDirectory() as td:
        session = ResearchSession(Path(td), "Can a trace be altered?")
        session.finalize("completed", title="Trace test")
        assert verify_session(Path(td), session.id)["ok"]
        events = [json.loads(line) for line in session.events_path.read_text(encoding="utf-8").splitlines()]
        events[0]["payload"]["question"] = "tampered but valid JSON"
        session.events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n",
                                       encoding="utf-8")
        audit = verify_session(Path(td), session.id)
        assert not audit["ok"] and "event-log-sha256-mismatch" in audit["errors"]


def test_analyst_cannot_finish_with_uncited_findings():
    from persona.agents import analyst
    from persona.agents.analyst import _finish_error

    finding = {"report_markdown": "A result", "conclusions": [
        {"claim": "Drug X works", "status": "SUPPORTED", "evidence_ids": [], "confidence": .9}]}
    assert "require evidence" in _finish_error(finding, ran_code=True, allowed_ids=set())
    finding["conclusions"][0]["evidence_ids"] = ["artifact:abc"]
    assert "unknown evidence" in _finish_error(finding, ran_code=True, allowed_ids=set())
    assert _finish_error(finding, ran_code=True, allowed_ids={"artifact:abc"}) is None
    assert "required evidence" in _finish_error(
        finding, ran_code=True, allowed_ids={"artifact:abc", "claim:required"},
        required_ids={"claim:required"})
    finding["conclusions"][0]["evidence_ids"].append("claim:required")
    assert _finish_error(finding, ran_code=True,
                         allowed_ids={"artifact:abc", "claim:required"},
                         required_ids={"claim:required"}) is None

    class KG:
        def provenance(self, claim_id):
            return {"claim_id": claim_id, "subject": "microglia", "effect_sign": "+",
                    "object": "tau", "sources": []}

        def search(self, q, limit):
            return []

    with patch.object(analyst, "get_persona", return_value=SimpleNamespace(kg=KG())):
        packet = analyst._evidence_packet("question", required_claim_ids=["must-include"])
    assert packet[0]["claim_id"] == "must-include"


def test_analyst_write_file_cannot_escape_project_root():
    from persona.agents.analyst import _safe_join

    with TemporaryDirectory() as td:
        root = Path(td)
        project = root / "project"
        project.mkdir()
        assert _safe_join(project, "analysis.py") == (project / "analysis.py").resolve()
        assert _safe_join(project, "../project-escape/owned.py") is None


def test_conflict_reviews_are_append_only_hash_chained_and_non_mutating():
    import hashlib

    from persona.conflict_reviews import (ConflictVerdict, append_conflict_review,
                                          conflict_id, read_conflict_reviews,
                                          summarize_conflict_reviews,
                                          verify_conflict_reviews)

    with TemporaryDirectory() as td:
        ops_dir = Path(td) / ".persona"
        untouched_kg = {"claims": ["positive", "negative"]}
        first = append_conflict_review(
            ops_dir, pos_claim_id="claim-positive", neg_claim_id="claim-negative",
            verdict=ConflictVerdict.INSUFFICIENT_EVIDENCE,
            rationale="The evidence packets do not resolve the population mismatch.",
            confidence=0.4, qualifier="Different disease stages",
            next_check="Compare matched-stage cohorts.")
        first_line = (ops_dir / "conflict_reviews.jsonl").read_bytes()
        second = append_conflict_review(
            ops_dir, pos_claim_id="claim-positive", neg_claim_id="claim-negative",
            verdict="context_divergence",
            rationale="The exact evidence supports effects in distinct disease stages.",
            confidence=0.85)

        records = read_conflict_reviews(ops_dir)
        assert records == [first, second]
        first_payload = {key: value for key, value in first.items() if key != "record_id"}
        canonical = json.dumps(first_payload, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode()
        assert first["record_id"] == hashlib.sha256(canonical).hexdigest()
        assert first["conflict_id"] == second["conflict_id"] == conflict_id(
            "claim-positive", "claim-negative")
        assert second["prev_sha256"] == first["record_id"]
        assert (ops_dir / "conflict_reviews.jsonl").read_bytes().startswith(first_line)
        assert verify_conflict_reviews(ops_dir)["ok"]
        summary = summarize_conflict_reviews(ops_dir)[first["conflict_id"]]
        assert summary["review_count"] == 2 and summary["latest"] == second
        assert untouched_kg == {"claims": ["positive", "negative"]}


def test_conflict_review_validation_and_tamper_detection_preserve_history():
    from persona.conflict_reviews import (MAX_OPTIONAL_CHARS, LedgerIntegrityError,
                                          append_conflict_review, verify_conflict_reviews)

    valid = {
        "pos_claim_id": "claim-positive", "neg_claim_id": "claim-negative",
        "verdict": "true_refutation",
        "rationale": "The matched evidence directly tests and reverses the same outcome.",
        "confidence": 0.9,
    }
    with TemporaryDirectory() as td:
        ops_dir = Path(td) / ".persona"
        for change in (
            {"verdict": "verified"},
            {"rationale": "too short"},
            {"confidence": float("nan")},
            {"confidence": 1.01},
            {"neg_claim_id": "claim-positive"},
            {"qualifier": "x" * (MAX_OPTIONAL_CHARS + 1)},
            {"next_check": None},
        ):
            try:
                append_conflict_review(ops_dir, **{**valid, **change})
                raise AssertionError(f"invalid review was accepted: {change}")
            except ValueError:
                pass
        assert not (ops_dir / "conflict_reviews.jsonl").exists()

        append_conflict_review(ops_dir, **valid)
        ledger = ops_dir / "conflict_reviews.jsonl"
        original = ledger.read_bytes()
        tampered = json.loads(original)
        tampered["rationale"] = "A tampered rationale that is still long enough to pass schema checks."
        ledger.write_text(json.dumps(tampered, sort_keys=True, separators=(",", ":")) + "\n",
                          encoding="utf-8")
        audit = verify_conflict_reviews(ops_dir)
        assert not audit["ok"] and "record-hash-mismatch:1" in audit["errors"]
        before_failed_append = ledger.read_bytes()
        try:
            append_conflict_review(ops_dir, **valid)
            raise AssertionError("append must reject a corrupted prior history")
        except LedgerIntegrityError:
            pass
        assert ledger.read_bytes() == before_failed_append and original != before_failed_append
