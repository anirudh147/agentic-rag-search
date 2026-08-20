"""
Full ingestion workflow: Docling preprocessing -> Markdown-aware splitting ->
Ollama embedding -> PGVector indexing.

Run via the CLI:
    python -m app.ingestion.pipeline --source-dir sample_docs

Or via the REST API: POST /api/v1/ingest (see app/api/routes_ingest.py),
which calls `run_ingestion()` in a background task.
"""
from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass
from typing import List

from app.config import Settings, get_settings
from app.ingestion.docling_loader import LoadedDocument, load_documents
from app.retrieval.vector_store import configure_llama_index_settings, get_vector_store

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    documents_processed: int
    chunks_indexed: int
    skipped_files: List[str]
    duration_seconds: float


def _split_into_nodes(documents: List[LoadedDocument], settings: Settings):
    """Markdown-structure-aware splitting: first split on heading boundaries
    (so a chunk never straddles two unrelated sections), then enforce a
    token-size ceiling within each section via SentenceSplitter so retrieval
    still gets tightly-scoped chunks even for very long sections.
    """
    from llama_index.core import Document
    from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

    llama_docs = [
        Document(text=d.markdown, metadata=d.metadata, doc_id=d.file_name)
        for d in documents
    ]

    heading_parser = MarkdownNodeParser()
    size_parser = SentenceSplitter(
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )

    section_nodes = heading_parser.get_nodes_from_documents(llama_docs)
    final_nodes = size_parser.get_nodes_from_documents(section_nodes)

    # Preserve provenance: file name + the heading path Docling/MarkdownNodeParser
    # attached, so citations in the synthesizer prompt are human-readable.
    for node in final_nodes:
        node.metadata.setdefault("source_file", node.metadata.get("source_file", "unknown"))
        headings = [
            v for k, v in sorted(node.metadata.items()) if k.startswith("Header")
        ]
        node.metadata["section_path"] = " > ".join(str(h) for h in headings) or "document root"

    return final_nodes


def run_ingestion(source_dir: str | None = None, settings: Settings | None = None) -> IngestionResult:
    settings = settings or get_settings()
    source_dir = source_dir or settings.source_documents_dir
    start = time.time()

    configure_llama_index_settings(settings)

    logger.info("Ingestion: loading + converting documents from %s via Docling", source_dir)
    documents = load_documents(source_dir, ocr_enabled=settings.docling_ocr_enabled)
    if not documents:
        logger.warning("No documents found/convertible in %s", source_dir)
        return IngestionResult(0, 0, [], time.time() - start)

    nodes = _split_into_nodes(documents, settings)
    logger.info("Ingestion: %d documents split into %d chunks", len(documents), len(nodes))

    from llama_index.core import StorageContext, VectorStoreIndex

    vector_store = get_vector_store(settings)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Building the index with `nodes=` embeds each node (via the globally
    # configured Ollama embed model) and upserts it into the pgvector table
    # in one call.
    VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        show_progress=True,
    )

    duration = time.time() - start
    logger.info("Ingestion complete: %d chunks indexed in %.1fs", len(nodes), duration)
    return IngestionResult(
        documents_processed=len(documents),
        chunks_indexed=len(nodes),
        skipped_files=[],
        duration_seconds=duration,
    )


def _cli() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Ingest documents into the PGVector knowledge base")
    parser.add_argument("--source-dir", default=None, help="Directory of PDFs/docs to ingest")
    args = parser.parse_args()
    result = run_ingestion(source_dir=args.source_dir)
    print(result)


if __name__ == "__main__":
    _cli()
