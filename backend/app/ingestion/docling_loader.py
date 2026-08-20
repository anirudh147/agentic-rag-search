"""
Document preprocessing with Docling.

Docling handles PDF layout analysis, reading order, table structure
recognition, and (optionally) OCR for scanned pages, then exports a clean
Markdown representation that preserves heading structure. We chunk on that
Markdown structure (see `pipeline.py`) rather than raw character windows, so
each chunk stays within a coherent section instead of splitting mid-table or
mid-paragraph -- this is what "document preprocessing" + "splitting" means
for this pipeline, ahead of the LlamaIndex vectorization/indexing stage.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".md"}


@dataclass
class LoadedDocument:
    source_path: str
    file_name: str
    markdown: str
    num_pages: int | None
    metadata: dict


def _build_converter(ocr_enabled: bool):
    """Constructs a Docling DocumentConverter.

    Import is deferred so the rest of the codebase (config, prompts, API
    schemas) can be imported/tested without the (heavy, torch-based) Docling
    dependency installed.
    """
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = ocr_enabled
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )


def iter_source_files(source_dir: str) -> Iterable[Path]:
    root = Path(source_dir)
    if not root.exists():
        raise FileNotFoundError(f"Source documents directory not found: {source_dir}")
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def load_documents(source_dir: str, ocr_enabled: bool = False) -> List[LoadedDocument]:
    """Runs Docling conversion over every supported file in `source_dir`
    and returns their Markdown export plus lightweight metadata.
    """
    converter = _build_converter(ocr_enabled)
    results: List[LoadedDocument] = []

    for path in iter_source_files(source_dir):
        logger.info("Docling: converting %s", path)
        try:
            conv_result = converter.convert(str(path))
        except Exception:
            logger.exception("Docling failed to convert %s -- skipping", path)
            continue

        doc = conv_result.document
        markdown = doc.export_to_markdown()
        try:
            num_pages = len(doc.pages) if getattr(doc, "pages", None) else None
        except Exception:
            num_pages = None

        results.append(
            LoadedDocument(
                source_path=str(path),
                file_name=path.name,
                markdown=markdown,
                num_pages=num_pages,
                metadata={
                    "source_file": path.name,
                    "source_path": str(path),
                    "converter": "docling",
                },
            )
        )
        logger.info("Docling: converted %s (%d chars markdown)", path.name, len(markdown))

    return results
