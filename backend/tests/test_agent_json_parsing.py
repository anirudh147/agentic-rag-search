"""
Tests for the small-model-tolerant JSON extraction helpers in
app/agents/crew.py. These have no CrewAI/LLM dependency (the module only
imports crewai lazily inside functions that need it), so they run in any
environment with just the project's stdlib + pydantic-settings deps.
Run: pytest backend/tests/test_agent_json_parsing.py
"""
from app.agents.crew import _extract_sources, _parse_json_loose


def test_parses_json_wrapped_in_prose():
    raw = 'Sure, here is the verdict: {"verdict": "APPROVE", "reason": "ok", "refined_query": null} — done.'
    parsed = _parse_json_loose(raw)
    assert parsed == {"verdict": "APPROVE", "reason": "ok", "refined_query": None}


def test_parses_json_in_code_fence():
    raw = '```json\n{"standalone_query": "q", "sub_queries": ["a", "b"], "answer_type": "fact"}\n```'
    parsed = _parse_json_loose(raw)
    assert parsed["standalone_query"] == "q"
    assert parsed["sub_queries"] == ["a", "b"]


def test_no_json_returns_empty_dict_not_exception():
    assert _parse_json_loose("The model just rambled without any JSON.") == {}


def test_empty_string_returns_empty_dict():
    assert _parse_json_loose("") == {}


def test_malformed_json_returns_empty_dict_not_exception():
    assert _parse_json_loose("{not: valid, json,}") == {}


def test_extract_sources_dedupes_repeated_chunks():
    raw = (
        '{"results": ['
        '{"source_file": "a.pdf", "score": 0.9, "section_path": "1. Intro"}, '
        '{"source_file": "a.pdf", "score": 0.81, "section_path": "1. Intro"}, '
        '{"source_file": "b.pdf", "score": 0.75, "section_path": "2. Setup"}'
        "]}"
    )
    sources = _extract_sources(raw)
    assert sources == [
        {"source_file": "a.pdf", "section_path": "1. Intro"},
        {"source_file": "b.pdf", "section_path": "2. Setup"},
    ]


def test_extract_sources_empty_on_no_matches():
    assert _extract_sources("no results here") == []
