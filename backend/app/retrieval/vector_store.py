"""
LlamaIndex + PGVector wiring: embedding model, vector store, and the
VectorStoreIndex used both for ingestion (writing nodes) and retrieval
(reading nodes back) so the two paths can never drift out of sync.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def get_embed_model(settings: Settings | None = None):
    """Ollama-hosted embedding model, shared by ingestion and retrieval.

    Kept as a thin factory (not imported at module scope) so importing this
    module doesn't require `llama-index-embeddings-ollama` to be installed
    unless it's actually used.
    """
    from llama_index.embeddings.ollama import OllamaEmbedding

    settings = settings or get_settings()
    return OllamaEmbedding(
        model_name=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
    )


def get_llm(settings: Settings | None = None, temperature: float = 0.1):
    from llama_index.llms.ollama import Ollama

    settings = settings or get_settings()
    return Ollama(
        model=settings.ollama_llm_model,
        base_url=settings.ollama_base_url,
        request_timeout=settings.ollama_request_timeout,
        temperature=temperature,
    )


def configure_llama_index_settings(settings: Settings | None = None) -> None:
    """Sets the process-global LlamaIndex `Settings` (embed_model + llm) once
    at startup so downstream code can just call VectorStoreIndex(...) etc.
    without threading models through every call site.
    """
    from llama_index.core import Settings as LlamaSettings

    settings = settings or get_settings()
    LlamaSettings.embed_model = get_embed_model(settings)
    LlamaSettings.llm = get_llm(settings)
    LlamaSettings.chunk_size = settings.chunk_size
    LlamaSettings.chunk_overlap = settings.chunk_overlap


def get_vector_store(settings: Settings | None = None):
    from llama_index.vector_stores.postgres import PGVectorStore

    settings = settings or get_settings()
    return PGVectorStore.from_params(
        database=settings.postgres_db,
        host=settings.postgres_host,
        password=settings.postgres_password,
        port=settings.postgres_port,
        user=settings.postgres_user,
        table_name=settings.pgvector_table_name,
        embed_dim=settings.pgvector_embed_dim,
        hybrid_search=False,
        hnsw_kwargs={
            "hnsw_m": 16,
            "hnsw_ef_construction": 64,
            "hnsw_ef_search": 40,
            "hnsw_dist_method": "vector_cosine_ops",
        },
    )


def get_index(settings: Settings | None = None):
    """Loads the existing PGVector-backed VectorStoreIndex (does not ingest
    anything -- see app/ingestion/pipeline.py for building/updating it)."""
    from llama_index.core import StorageContext, VectorStoreIndex

    settings = settings or get_settings()
    configure_llama_index_settings(settings)
    vector_store = get_vector_store(settings)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
    )


@lru_cache
def get_cached_index():
    """Process-wide singleton so every request reuses the same index/engine
    instead of reconnecting to Postgres per call."""
    return get_index()
