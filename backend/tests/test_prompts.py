"""
PromptManager tests -- pure YAML loading + string.Template rendering, no
LLM/network dependency. Run: pytest backend/tests/test_prompts.py
"""
import pytest

from app.prompts.manager import PromptFieldNotFoundError, PromptManager, PromptNotFoundError


@pytest.fixture(scope="module")
def pm():
    return PromptManager()  # defaults to app/prompts/library


def test_all_library_prompts_load(pm):
    names = pm.list_prompts()
    expected = {
        "query_analyzer",
        "retriever_agent",
        "synthesizer_agent",
        "verifier_agent",
        "openwebui_system",
        "ragas_testset_seed",
    }
    assert expected.issubset(names.keys())


def test_agent_prompts_expose_crewai_fields(pm):
    for name in ("query_analyzer", "retriever_agent", "synthesizer_agent", "verifier_agent"):
        prompt = pm.get(name)
        for field in ("role", "goal", "backstory", "description", "expected_output"):
            assert field in prompt.fields, f"{name} missing field {field}"


def test_render_field_substitutes_variables(pm):
    text = pm.render_field(
        "query_analyzer", "description", question="What is the PTO policy?", chat_history="(none)"
    )
    assert "What is the PTO policy?" in text
    assert "$question" not in text and "$chat_history" not in text


def test_render_field_missing_variable_raises_on_primary_fields(pm):
    with pytest.raises(ValueError):
        pm.get("query_analyzer").render_field("description", question="only one var")


def test_render_field_does_not_require_vars_for_role(pm):
    # `role` doesn't reference $question/$chat_history, so it renders fine
    # even without those kwargs -- this is what lets Agent(role=..., ...)
    # construction stay decoupled from the task's input variables.
    role = pm.get("query_analyzer").render_field("role")
    assert "Query Analyst" in role


def test_unknown_prompt_raises(pm):
    with pytest.raises(PromptNotFoundError):
        pm.get("does_not_exist")


def test_unknown_field_raises(pm):
    with pytest.raises(PromptFieldNotFoundError):
        pm.get("openwebui_system").render_field("role")


def test_plain_template_prompt_renders_with_no_variables(pm):
    text = pm.render("openwebui_system")
    assert "Document Search Assistant" in text


def test_reload_picks_up_disk_changes(tmp_path, pm):
    # Point a fresh manager at an isolated directory to verify reload()
    # re-reads from disk without mutating the shared library fixture.
    d = tmp_path / "library"
    d.mkdir()
    (d / "greeting.yaml").write_text(
        'name: greeting\nversion: "1.0.0"\ninput_variables: []\ntemplate: "hello v1"\n'
    )
    local_pm = PromptManager(str(d))
    assert local_pm.render("greeting") == "hello v1"

    (d / "greeting.yaml").write_text(
        'name: greeting\nversion: "1.0.1"\ninput_variables: []\ntemplate: "hello v2"\n'
    )
    local_pm.reload()
    assert local_pm.render("greeting") == "hello v2"
