"""
Retriever construction on top of the shared PGVector-backed VectorStoreIndex.
Kept separate from `vector_store.py` (index/storage plumbing) so retrieval
tuning (top_k, similarity cutoff, reranking) lives in one place and is reused
identically by the CrewAI tool (app/agents/tools.py) and any direct
`/search` API calls.
"""
from __future__ import annotations

from typing import List, TypedDict

from app.config import Settings, get_settings
from app.retrieval.vector_store import get_cached_index


class RetrievedChunk(TypedDict):
    text: str
    score: float
    source_file: str
    section_path: str
    node_id: str


def get_retriever(settings: Settings | None = None, top_k: int | None = None):
    settings = settings or get_settings()
    index = get_cached_index()
    return index.as_retriever(similarity_top_k=top_k or settings.retriever_top_k)


def retrieve(query: str, settings: Settings | None = None, top_k: int | None = None) -> List[RetrievedChunk]:
    """Runs similarity search + a minimum-score cutoff and returns plain
    dicts (not LlamaIndex objects) so this is trivially usable from the
    CrewAI tool, the `/search` endpoint, and the RAGAs evaluation harness
    without any of them depending on LlamaIndex internals.
    """
    settings = settings or get_settings()
    retriever = get_retriever(settings, top_k=top_k)
    nodes = retriever.retrieve(query)

    results: List[RetrievedChunk] = []
    for n in nodes:
        if n.score is not None and n.score < settings.similarity_cutoff:
            continue
        results.append(
            RetrievedChunk(
                text=n.node.get_content(),
                score=float(n.score) if n.score is not None else 0.0,
                source_file=n.node.metadata.get("source_file", "unknown"),
                section_path=n.node.metadata.get("section_path", ""),
                node_id=n.node.node_id,
            )
        )
    return results
