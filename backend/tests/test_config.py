"""
Config tests -- pure pydantic-settings, no external services required.
Run: pytest backend/tests/test_config.py
"""
from app.config import Settings


def test_defaults_are_sane():
    s = Settings(_env_file=None)
    assert s.api_prefix == "/api/v1"
    assert s.chunk_size > s.chunk_overlap > 0
    assert s.retriever_top_k >= 1
    assert s.crew_max_iterations >= 1


def test_postgres_dsn_built_from_parts():
    s = Settings(
        _env_file=None,
        postgres_host="db.internal",
        postgres_port=5433,
        postgres_db="mydb",
        postgres_user="u",
        postgres_password="p",
    )
    assert s.postgres_dsn == "postgresql://u:p@db.internal:5433/mydb"


def test_env_override(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "1024")
    monkeypatch.setenv("OLLAMA_LLM_MODEL", "llama3.1:8b")
    s = Settings(_env_file=None)
    assert s.chunk_size == 1024
    assert s.ollama_llm_model == "llama3.1:8b"
