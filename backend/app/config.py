"""
Centralized application configuration.

All runtime configuration comes from environment variables (with sane local
defaults), following 12-factor practice. See `.env.example` at the repo root
for the full list of variables and `docker-compose.yml` for how each service
is wired together.
"""
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "doc-search-agentic-rag"
    api_prefix: str = "/api/v1"
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # --- Postgres / PGVector ---
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="ragdb")
    postgres_user: str = Field(default="raguser")
    postgres_password: str = Field(default="ragpassword")
    pgvector_table_name: str = Field(default="document_chunks")
    pgvector_embed_dim: int = Field(default=768)

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # --- Ollama ---
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_llm_model: str = Field(default="qwen2.5:3b-instruct")
    ollama_embedding_model: str = Field(default="nomic-embed-text")
    ollama_request_timeout: float = Field(default=180.0)
    # Hard cap on a single generation's length. Without this, a small model
    # that fails to emit a stop token keeps generating until it exhausts the
    # context window -- several minutes at CPU token rates -- instead of
    # failing fast.
    ollama_max_tokens: int = Field(default=1024)

    # --- Ingestion / chunking ---
    chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=64)
    docling_ocr_enabled: bool = Field(default=False)
    source_documents_dir: str = Field(default="/data/source_documents")

    # --- Retrieval ---
    retriever_top_k: int = Field(default=6)
    rerank_top_n: int = Field(default=4)
    similarity_cutoff: float = Field(default=0.2)

    # --- CrewAI agents ---
    crew_verbose: bool = Field(default=True)
    crew_max_iterations: int = Field(default=6)
    crew_process: str = Field(default="sequential")  # sequential | hierarchical
    # Per-agent hard caps: bound each Agent's *internal* ReAct tool-call loop,
    # which is independent of crew_max_iterations (that only bounds the outer
    # verify/retry loop across whole crew.kickoff() calls). Without these, a
    # small model producing malformed tool-call output can make a single
    # agent retry internally up to CrewAI's default max_iter=20 -- multiplied
    # across 3 agents per outer iteration -- before the outer loop ever sees it.
    crew_agent_max_iter: int = Field(default=5)
    crew_agent_max_execution_time: int = Field(default=90)

    # --- Prompts ---
    prompts_dir: str = Field(default="app/prompts/library")

    # --- Arize Phoenix tracing ---
    phoenix_enabled: bool = Field(default=True)
    phoenix_collector_endpoint: str = Field(default="http://localhost:6006/v1/traces")
    phoenix_project_name: str = Field(default="doc-search-agentic-rag")

    # --- OpenWebUI / OpenAI-compatible surface ---
    openai_compat_default_model_name: str = Field(default="agentic-rag")

    # --- RAGAs evaluation ---
    eval_dataset_path: str = Field(default="app/evaluation/qa_dataset.json")
    eval_report_dir: str = Field(default="/data/eval_reports")

    # --- Auth (optional simple API-key gate) ---
    api_key: Optional[str] = Field(default=None)


@lru_cache
def get_settings() -> "Settings":
    return Settings()
