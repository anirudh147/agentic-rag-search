"""
Arize Phoenix tracing bootstrap.

Instruments every inference call made through LlamaIndex (embeddings +
direct LLM calls), CrewAI (agent/task execution), and LiteLLM (the layer
CrewAI uses to actually call Ollama), exporting OpenTelemetry/OpenInference
spans to a Phoenix collector. This satisfies "implement tracing for all
inference calls" -- instrumentation is applied once at process startup
(see app/main.py) rather than call-by-call, so nothing can be added later
and accidentally bypass tracing.

Phoenix UI (trace explorer, prompt playground, evals) is served by the
`phoenix` service in docker-compose.yml, independent of this backend
process -- this module only pushes spans to it.
"""
from __future__ import annotations

import logging

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

_tracer_provider = None


def init_tracing(settings: Settings | None = None):
    """Idempotent: safe to call multiple times (e.g. under uvicorn's
    reloader) -- returns the already-created provider on subsequent calls.
    """
    global _tracer_provider
    if _tracer_provider is not None:
        return _tracer_provider

    settings = settings or get_settings()
    if not settings.phoenix_enabled:
        logger.info("Phoenix tracing disabled via PHOENIX_ENABLED=false")
        return None

    try:
        from phoenix.otel import register
    except ImportError:
        logger.warning("arize-phoenix-otel not installed -- tracing disabled")
        return None

    tracer_provider = register(
        project_name=settings.phoenix_project_name,
        endpoint=settings.phoenix_collector_endpoint,
        batch=True,
    )

    _instrument_llama_index(tracer_provider)
    _instrument_crewai(tracer_provider)
    _instrument_litellm(tracer_provider)

    logger.info(
        "Phoenix tracing initialized (project=%s, endpoint=%s)",
        settings.phoenix_project_name,
        settings.phoenix_collector_endpoint,
    )
    _tracer_provider = tracer_provider
    return tracer_provider


def _instrument_llama_index(tracer_provider) -> None:
    try:
        from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

        LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)
    except ImportError:
        logger.warning("openinference-instrumentation-llama-index not installed -- skipping")


def _instrument_crewai(tracer_provider) -> None:
    try:
        from openinference.instrumentation.crewai import CrewAIInstrumentor

        CrewAIInstrumentor().instrument(tracer_provider=tracer_provider)
    except ImportError:
        logger.warning("openinference-instrumentation-crewai not installed -- skipping")


def _instrument_litellm(tracer_provider) -> None:
    """CrewAI agents call Ollama via LiteLLM under the hood; instrumenting
    LiteLLM captures those spans (prompt, completion, latency, token usage)
    even though the LlamaIndexInstrumentor/CrewAIInstrumentor cover the
    higher-level agent/task spans.
    """
    try:
        from openinference.instrumentation.litellm import LiteLLMInstrumentor

        LiteLLMInstrumentor().instrument(tracer_provider=tracer_provider)
    except ImportError:
        logger.warning("openinference-instrumentation-litellm not installed -- skipping")


def get_tracer_provider():
    return _tracer_provider
