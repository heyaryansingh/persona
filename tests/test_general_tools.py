"""The analyst is field-general: a domain-agnostic literature tool is registered and exposed, so a
non-biomedical persona (physics, economics, materials, CS) has a real structured-evidence tool.
Offline — no network call.
"""
from persona.agents import analyst
from persona.tools import science


def test_domain_general_literature_tool_registered_and_exposed():
    assert "literature_search" in science.REGISTRY, "OpenAlex (all-fields) tool must be registered"
    # unknown api is safely rejected (dispatch guard)
    assert science.call("not_a_tool", {})["ok"] is False
    # the analyst's science_query tool advertises the general tool in its enum
    sq = next(t for t in analyst.TOOLS if t["name"] == "science_query")
    enum = sq["input_schema"]["properties"]["api"]["enum"]
    assert "literature_search" in enum
    # biomedical tools remain available too
    assert "uniprot" in enum and "open_targets" in enum


def test_literature_search_dispatches_the_requested_limit(monkeypatch):
    seen = {}

    class FakeService:
        def get_json(self, _url, **kwargs):
            seen.update(kwargs["params"])
            return {"results": []}

    monkeypatch.setattr(science, "service", lambda: FakeService())
    assert science.call("literature_search", {"query": "graphs", "size": 1})["ok"]
    assert seen["search"] == "graphs" and seen["per_page"] == 1
