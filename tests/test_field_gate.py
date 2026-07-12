"""The field gate: OpenAlex search captures primary_topic.field and applies a field filter.

Pure/mocked (no network): monkeypatch the ingest service to canned OpenAlex JSON and assert
(1) Work.field / field_id are parsed, (2) the field filter param is built when field_ids is given,
(3) selfmind.allowed_field_ids keeps only strong-majority fields (drops one-off cross-field noise).
Validated live in experiments/exp_rq_e15_field_question_gate.py (drops 100% off-field, SHIP).
"""
from persona.ingest import sources


class _FakeService:
    """Records the last params and returns a canned OpenAlex response."""
    def __init__(self, results):
        self.results = results
        self.last_params = None

    def get_json(self, url, params):
        self.last_params = params
        return {"results": self.results}


_MATH_RESULT = [{
    "id": "https://openalex.org/W1", "title": "On the Erdős–Straus conjecture",
    "publication_year": 2010, "authorships": [],
    "primary_topic": {"field": {"id": "https://openalex.org/fields/26", "display_name": "Mathematics"}},
}]


def test_openalex_captures_field_and_applies_filter(monkeypatch):
    fake = _FakeService(_MATH_RESULT)
    monkeypatch.setattr(sources, "service", lambda: fake)
    works = sources.openalex_search("erdos straus", 5, field_ids=["26"])
    assert works and works[0].field == "Mathematics" and works[0].field_id == "26"
    # the field filter must be in the query params
    assert fake.last_params.get("filter") == "primary_topic.field.id:fields/26"


def test_openalex_no_filter_when_no_field_ids(monkeypatch):
    fake = _FakeService(_MATH_RESULT)
    monkeypatch.setattr(sources, "service", lambda: fake)
    sources.openalex_search("erdos straus", 5)
    assert "filter" not in fake.last_params


def test_allowed_field_ids_drops_one_off_noise(monkeypatch, tmp_path):
    # 11 votes Mathematics(26), 3 Biochem(13), 1 Physics(31): only 26 clears the 35% majority.
    from persona import selfmind

    def fake_field_json(url, params):
        # return a spread of fields whose aggregate is dominated by 26
        return {"results": [
            {"primary_topic": {"field": {"id": "https://openalex.org/fields/26"}}},
            {"primary_topic": {"field": {"id": "https://openalex.org/fields/13"}}},
            {"primary_topic": {"field": {"id": "https://openalex.org/fields/26"}}},
        ]}

    class F:
        def get_json(self, url, params):
            return fake_field_json(url, params)

    monkeypatch.setattr(sources, "service", lambda: F())
    monkeypatch.setattr(selfmind, "interests", lambda: [("erdos straus", 1.0), ("egyptian fractions", 1.0)])
    # route the ops-dir cache to a temp path
    import persona.context as ctx

    class _Paths:
        ops_dir = tmp_path

    class _P:
        paths = _Paths()
    monkeypatch.setattr(ctx, "get_persona", lambda: _P())
    monkeypatch.setattr(selfmind, "get_persona", lambda: _P())
    fields = selfmind.allowed_field_ids()
    assert fields == ["26"], f"expected only the majority field, got {fields}"
