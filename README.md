# Document Search Platform — Agentic RAG Backend + OpenWebUI

A document search platform built around an **agentic, contextual RAG
backend** (FastAPI + LlamaIndex + CrewAI + PostgreSQL/pgvector + Ollama),
fully traced with **Arize Phoenix**, evaluated with **RAGAs**, and fronted
by **OpenWebUI** as the chat interface. Built to satisfy a technical
assessment that mandates this exact toolset — see
[Requirements traceability](#requirements-traceability) below for how each
mandated piece is used.

```
User <-> OpenWebUI <-> FastAPI backend <-> CrewAI agent crew <-> LlamaIndex retriever <-> PostgreSQL/pgvector
                              |                                                                |
                              +--> Ollama (LLM + embeddings)                    Docling ingestion pipeline
                              +--> Arize Phoenix (tracing)
                              +--> RAGAs (evaluation)
```

Full architecture diagrams and design rationale: [`doc/architecture/`](doc/architecture/).

## Table of contents

- [Requirements traceability](#requirements-traceability)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick start (Docker Compose)](#quick-start-docker-compose)
- [Configuration](#configuration)
- [Using the platform](#using-the-platform)
- [REST API](#rest-api)
- [Prompt management](#prompt-management)
- [Tracing & observability](#tracing--observability)
- [Evaluation (RAGAs)](#evaluation-ragas)
- [Running without Docker (local dev)](#running-without-docker-local-dev)
- [Supporting documents](#supporting-documents)
- [Known limitations of this build](#known-limitations-of-this-build)
- [Troubleshooting](#troubleshooting)

## Requirements traceability

| Mandated tool | Role in this repo |
|---|---|
| **Docling** | PDF/DOCX/PPTX/HTML preprocessing — layout analysis, table structure recognition, Markdown export. `backend/app/ingestion/docling_loader.py` |
| **PostgreSQL + PGVector** | Sole vector store, HNSW/cosine index over `document_chunks`. `backend/app/retrieval/vector_store.py`, `docker/postgres/init.sql` |
| **LlamaIndex** | Node parsing/splitting, embedding + retrieval orchestration, `VectorStoreIndex` over PGVector. `backend/app/ingestion/pipeline.py`, `backend/app/retrieval/` |
| **CrewAI** | 4-agent contextual RAG crew: Query Analyzer → Retriever → Synthesizer → Verifier, with a verify/retry loop. `backend/app/agents/` |
| **Ollama** | Sole LLM + embedding provider (local or remote), used by LlamaIndex, CrewAI, and the RAGAs judge — no OpenAI key required anywhere. |
| **Arize Phoenix** | Trace collector + UI for every LLM/agent/tool call, instrumented once at startup via OpenInference. `backend/app/tracing/phoenix_setup.py` |
| **RAGAs** | Evaluation harness (faithfulness, answer relevancy, context precision/recall) over the real agentic pipeline. `backend/app/evaluation/` |
| **OpenWebUI** | Chat frontend, connected to the backend's OpenAI-compatible `/v1/chat/completions` surface. |

Also delivered: prompts externalized to YAML (`backend/app/prompts/library/`,
independently hot-reloadable), full REST API with generated Swagger/OpenAPI
docs (`doc/api/`), architecture diagrams, a design-rationale ADR, and a
presentation deck (all under `doc/`).

## Repository layout

```
.
├── backend/                    FastAPI application (the actual deliverable)
│   ├── app/
│   │   ├── main.py             App wiring: routers, CORS, startup tracing init
│   │   ├── config.py           Centralized env-var settings (pydantic-settings)
│   │   ├── ingestion/          Docling loading + Markdown-aware splitting + indexing
│   │   ├── retrieval/          PGVector/LlamaIndex vector store + retriever
│   │   ├── agents/             CrewAI crew (query analysis/retrieval/synthesis/verification) + tools
│   │   ├── prompts/            PromptManager + externalized prompt YAML library
│   │   ├── tracing/            Arize Phoenix / OpenInference bootstrap
│   │   ├── evaluation/         RAGAs harness + curated Q&A dataset
│   │   └── api/                FastAPI routers + Pydantic schemas
│   ├── tests/                   Pytest suite (config, prompts, agent JSON parsing)
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── Dockerfile
├── docker-compose.yml          Full stack: postgres, ollama, phoenix, backend, openwebui
├── docker/postgres/init.sql    Enables the pgvector extension
├── sample_docs/                Placeholder knowledge base (see note below)
├── scripts/                    generate_sample_pdfs.py, ingest.sh, run_eval.sh, export_openapi.py
├── doc/
│   ├── architecture/           System diagrams (.mmd source + rendered .png/.svg) + architecture.md (ADR)
│   ├── api/                    Exported openapi.json / openapi.yaml (Swagger)
│   ├── evaluation/             RAGAs methodology + results report
│   └── presentation/           Slide deck (.pptx)
├── .env.example
└── README.md                   You are here
```

> **About `sample_docs/`.** The assessment references a shared Google Drive
> folder of source PDFs that wasn't accessible from the environment this
> repo was built in. `scripts/generate_sample_pdfs.py` generates 4 realistic
> placeholder policy/reference PDFs (cloud architecture standards, a data
> privacy policy, an API reference guide, an HR leave policy) so the full
> ingestion → retrieval → generation → evaluation pipeline is demonstrable
> end-to-end. **To use the real corpus:** drop the real PDFs into
> `sample_docs/` (or any directory and set `SOURCE_DOCUMENTS_DIR`/pass
> `source_dir` to `POST /api/v1/ingest`) — no code changes needed.

## Prerequisites

- Docker + Docker Compose v2 (`docker compose version`)
- ~10 GB free disk (Ollama model + Postgres + Phoenix + OpenWebUI images/volumes)
- 8 GB+ RAM recommended. A GPU is optional — see the commented-out `deploy.resources`
  block in `docker-compose.yml`'s `ollama` service to enable NVIDIA GPU acceleration.

## Quick start (Docker Compose)

```bash
git clone <this-repo-url>
cd doc-search-platform
cp .env.example .env               # adjust model names / ports if needed

# 1. Bring up the full stack (Postgres+pgvector, Ollama, Phoenix, backend, OpenWebUI)
docker compose up -d --build

# 2. Pull the Ollama models (the `ollama-pull` one-shot service does this
#    automatically on first `up`, but you can re-run it any time):
docker compose run --rm ollama-pull

# 3. Ingest the knowledge base (sample_docs/ by default)
./scripts/ingest.sh
#   -> {"status": "completed", "documents_processed": 4, "chunks_indexed": NN, ...}

# 4. Ask a question directly against the API
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How many days of PTO do full-time employees accrue per year?"}' | python3 -m json.tool
```

Then open:
- **OpenWebUI** (chat): http://localhost:3000 — the `agentic-rag` model is
  pre-wired to this backend (see [OpenWebUI setup](#3-openwebui-chat-ui)).
- **Swagger / OpenAPI UI**: http://localhost:8000/docs
- **Arize Phoenix** (traces): http://localhost:6006

## Configuration

All configuration is environment-variable driven — see [`.env.example`](.env.example)
for the full list (Postgres connection, Ollama model names/URL, chunking
parameters, retriever `top_k`/similarity cutoff, CrewAI iteration cap,
Phoenix endpoint, eval dataset path). `docker-compose.yml` overrides the
inter-service hostnames (`postgres`, `ollama`, `phoenix`) automatically —
you generally only need to edit `OLLAMA_LLM_MODEL` / `OLLAMA_EMBEDDING_MODEL`
if you want a different model than the small default
(`qwen2.5:3b-instruct` + `nomic-embed-text`, chosen to run reasonably on
CPU-only hosts; swap in a larger model for better answer quality if you have
more compute).

**If you change `OLLAMA_EMBEDDING_MODEL`,** also update `PGVECTOR_EMBED_DIM`
to match its output dimension (`nomic-embed-text` = 768), and re-ingest —
the pgvector column dimension is fixed at table-creation time.

## Using the platform

### 1. Ingest documents

```bash
# Synchronous (waits for completion, good for demos):
curl -X POST http://localhost:8000/api/v1/ingest -d '{"run_async": false}' -H "Content-Type: application/json"

# Asynchronous (returns immediately; poll status):
curl -X POST http://localhost:8000/api/v1/ingest -d '{"run_async": true}' -H "Content-Type: application/json"
curl http://localhost:8000/api/v1/ingest/status
```

Re-running ingestion re-embeds and upserts every document currently in the
source directory (see [Known limitations](#known-limitations-of-this-build)
re: no incremental/delta ingestion yet).

### 2. Query via REST

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is our incident reporting SLA for a suspected data breach?", "include_trace": true}'
```

Response includes the answer, cited sources, whether the Verifier agent
approved it, how many retrieve/verify iterations it took, and (optionally)
the full multi-agent execution trace.

### 3. OpenWebUI (chat UI)

`docker-compose.yml` already points OpenWebUI at this backend
(`OPENAI_API_BASE_URL=http://backend:8000/v1`). On first login to
http://localhost:3000:

1. Create the initial admin account (local to your OpenWebUI instance).
2. Go to **Settings → Connections** and confirm an OpenAI connection exists
   at `http://backend:8000/v1` (any non-empty API key value works — the
   backend doesn't validate it unless you set `API_KEY` in `.env`).
3. Start a new chat and select the **agentic-rag** model.

Every message is answered by the same `/v1/chat/completions` → CrewAI crew
path as the native `/api/v1/query` endpoint; citations are appended as a
Markdown "Sources" list in the assistant's reply.

### 4. Evaluate the pipeline

```bash
./scripts/run_eval.sh
```

See [Evaluation (RAGAs)](#evaluation-ragas) below.

## REST API

Full interactive docs: `http://localhost:8000/docs` (Swagger UI) and
`http://localhost:8000/redoc`. A static export lives at
[`doc/api/openapi.json`](doc/api/openapi.json) /
[`doc/api/openapi.yaml`](doc/api/openapi.yaml) — 11 paths, 23 component
schemas, every `$ref` resolved (verified programmatically).

**Two ways to (re)generate it**, depending on whether the full backend deps
are installed:

```bash
# Preferred: imports the live FastAPI app, so it's byte-for-byte what
# /openapi.json actually serves. Needs `pip install -r requirements.txt`.
cd backend && python ../scripts/export_openapi.py

# Fallback: hand-assembles an equivalent OpenAPI 3.1 doc directly from the
# Pydantic models in app/api/schemas.py + the routes in app/api/routes_*.py
# -- only needs `pydantic` (no FastAPI/uvicorn/etc). This is what generated
# the checked-in doc/api/openapi.json in this build (see "Known limitations").
cd backend && python ../scripts/build_openapi_static.py
```

| Method & path | Purpose |
|---|---|
| `GET /api/v1/health` | Liveness + dependency checks (Postgres, Ollama, Phoenix) |
| `POST /api/v1/ingest` | Run the Docling → split → embed → PGVector ingestion pipeline |
| `GET /api/v1/ingest/status` | Poll the last background ingestion run |
| `POST /api/v1/query` | Native rich RAG query (answer, sources, approval status, optional trace) |
| `POST /api/v1/search` | Raw retrieval only (no generation) — useful for debugging the index |
| `GET /api/v1/prompts` | Introspect the externalized prompt library (name, version, variables) |
| `POST /api/v1/prompts/reload` | Hot-reload prompts from disk, no restart |
| `POST /api/v1/eval/run` | Run the RAGAs evaluation harness |
| `GET /api/v1/eval/status` | Poll the last background evaluation run |
| `POST /v1/chat/completions` | OpenAI-compatible surface consumed by OpenWebUI |
| `GET /v1/models` | OpenAI-compatible model list (`agentic-rag`) |

## Prompt management

All agent personas and task prompts live in
[`backend/app/prompts/library/*.yaml`](backend/app/prompts/library/) —
completely independent of application code. Each file carries a semantic
`version`, a human `summary`, and either a plain `template` or structured
CrewAI fields (`role`/`goal`/`backstory`/`description`/`expected_output`).
Edit a YAML file, then either restart the backend or call
`POST /api/v1/prompts/reload` to pick up the change with zero downtime.
`GET /api/v1/prompts` lists every loaded prompt and its version for audit.

Optional: sync a prompt's `template`/`description` into Arize Phoenix's
Prompt Hub for UI-based iteration — Phoenix's client SDK
(`phoenix.client.Client().prompts.create(...)`) accepts the same string;
this repo treats the YAML files as the source of truth and Phoenix as an
optional downstream mirror, see `doc/architecture/architecture.md` §2.3.

## Tracing & observability

`app/tracing/phoenix_setup.py::init_tracing()` runs once at FastAPI startup
and instruments **LlamaIndex**, **CrewAI**, and **LiteLLM** (the layer CrewAI
uses to call Ollama) via OpenInference, exporting OTLP spans to the `phoenix`
container. Open http://localhost:6006 to see, per request:

- The full query-analysis → retrieve → synthesize → verify span tree, including
  every retry iteration.
- Each LLM call's prompt, completion, latency, and token usage.
- The exact `search_knowledge_base` tool calls and their arguments/results.

Set `PHOENIX_ENABLED=false` to disable tracing entirely (e.g. for a minimal
local dev loop).

## Evaluation (RAGAs)

`backend/app/evaluation/qa_dataset.json` is a curated set of question/
ground-truth pairs written against the placeholder `sample_docs/` corpus
(swap in your own set once you ingest the real documents — see
`backend/app/prompts/library/ragas_testset_seed.yaml` for an LLM-assisted
seed-generation prompt to bootstrap that). `app/evaluation/run_ragas.py`
runs every question through the **real** `run_agentic_rag()` pipeline (not a
retrieval-only shortcut), then scores the results with RAGAs:

- **Faithfulness** — is the answer supported by the retrieved context?
- **Answer relevancy** — does the answer address the actual question?
- **Context precision** — how much of the retrieved context is relevant?
- **Context recall** — did retrieval surface what's needed for the reference answer?

The RAGAs judge LLM/embeddings are the same Ollama-backed models used in
production (no OpenAI key required). Run it with `./scripts/run_eval.sh` or
`POST /api/v1/eval/run`; a timestamped JSON report is written to
`EVAL_REPORT_DIR` (`/data/eval_reports` in the container, a named Docker
volume). See [`doc/evaluation/evaluation_report.md`](doc/evaluation/evaluation_report.md)
for methodology and the latest recorded results.

## Running without Docker (local dev)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Point at your own Postgres+pgvector and Ollama instances:
export POSTGRES_HOST=localhost OLLAMA_BASE_URL=http://localhost:11434 \
       PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces

uvicorn app.main:app --reload --port 8000
```

Run ingestion directly (no HTTP round-trip):

```bash
python -m app.ingestion.pipeline --source-dir ../sample_docs
python -m app.evaluation.run_ragas
```

### Running the test suite

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

`tests/test_config.py` and `tests/test_prompts.py` and
`tests/test_agent_json_parsing.py` cover configuration loading, the
externalized-prompt rendering engine, and the small-model-tolerant JSON
extraction the agent crew relies on — all pure-logic, no Postgres/Ollama/
Phoenix required. (Full integration tests against the live stack are a
natural next addition once the real corpus is ingested — see
`doc/architecture/architecture.md` §4.)

## Supporting documents

- **Architecture & design rationale (ADR):** [`doc/architecture/architecture.md`](doc/architecture/architecture.md)
- **Diagrams:** [`doc/architecture/system_architecture.png`](doc/architecture/system_architecture.png),
  [`agentic_rag_sequence.png`](doc/architecture/agentic_rag_sequence.png),
  [`ingestion_flow.png`](doc/architecture/ingestion_flow.png)
  (Mermaid `.mmd` sources alongside each, editable/re-renderable with `mmdc`)
- **REST API spec:** [`doc/api/openapi.json`](doc/api/openapi.json) / [`doc/api/openapi.yaml`](doc/api/openapi.yaml)
- **Evaluation methodology & results:** [`doc/evaluation/evaluation_report.md`](doc/evaluation/evaluation_report.md)
- **Presentation deck:** [`doc/presentation/`](doc/presentation/)

## Known limitations of this build

- **This build was authored and validated in a network-restricted sandbox.**
  The development environment this repo was produced in had no outbound
  access to PyPI, Docker Hub, HuggingFace, or the Ollama model registry (all
  returned `host_not_allowed` at its egress gateway), and no GitHub
  repository connected for pushing. Concretely, this means: the backend's
  Python dependencies were never `pip install`-ed here, `docker compose up`
  was never actually run, and the RAGAs evaluation and Phoenix traces were
  never executed against a live Ollama model. What *was* possible and *was*
  done instead: every module byte-compiles cleanly; the dependency-light
  logic (config loading, prompt rendering, agent JSON-parsing) is covered by
  `backend/tests/` and was manually verified against the actual installed
  `pydantic`/`PyYAML`; `docker-compose.yml` was validated with
  `docker compose config`; the Mermaid diagrams were rendered to PNG/SVG;
  and `doc/api/openapi.json` was generated from the real Pydantic models via
  `scripts/build_openapi_static.py` (a FastAPI-free fallback -- see
  [REST API](#rest-api)). **Action for whoever runs this next:** `docker
  compose up -d --build`, `./scripts/ingest.sh`, `./scripts/run_eval.sh`,
  and `cd backend && python ../scripts/export_openapi.py` to get a live-
  verified OpenAPI export and real RAGAs numbers in
  `doc/evaluation/evaluation_report.md`.
- **Placeholder corpus.** See the `sample_docs/` note above — swap in the
  real Google Drive documents by dropping them into that directory (or any
  directory + `SOURCE_DOCUMENTS_DIR`).
- **No token streaming.** `/v1/chat/completions` rejects `stream=true`
  explicitly rather than degrading silently — the crew produces one final,
  verified answer per turn rather than incremental tokens.
- **Citations are Markdown, not OpenWebUI's native citation cards** — see
  `doc/architecture/architecture.md` §2.5 for the trade-off and the
  Pipelines-plugin alternative if that UX is required later.
- **Full re-embed on every ingestion run** — no content-hash-based delta
  ingestion yet; fine at this document volume, worth adding for a large,
  frequently-updated corpus.
- **Single-tenant** — an optional bearer `API_KEY` gate exists
  (`app/config.py`) but there's no per-user document ACL; out of scope per
  the assessment brief.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `ingest` returns 0 chunks | `SOURCE_DOCUMENTS_DIR` empty or wrong extension (`.pdf/.docx/.pptx/.html/.md` supported) |
| `/api/v1/health` shows `ollama: false` | Model not pulled yet — run `docker compose run --rm ollama-pull`, or check `docker compose logs ollama` |
| Answers are slow (30s+) | Expected on CPU-only hosts with the default small model — each turn makes 4+ sequential LLM calls (analyze → retrieve → synthesize → verify, times up to `CREW_MAX_ITERATIONS`). Reduce `CREW_MAX_ITERATIONS` or use a smaller/faster model for a snappier demo. |
| PGVector dimension mismatch error on ingest | You changed `OLLAMA_EMBEDDING_MODEL` after the table was created — drop the `document_chunks` table (or the `pgdata` volume) and re-ingest, keeping `PGVECTOR_EMBED_DIM` in sync with the new model's output dimension. |
| OpenWebUI shows no models | Confirm `OPENAI_API_BASE_URL=http://backend:8000/v1` in its environment and that the backend container is healthy (`docker compose ps`). |
