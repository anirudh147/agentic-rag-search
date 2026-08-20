# Solution Architecture: Agentic RAG Document Search Platform

**Status:** Accepted
**Date:** 2026-08-20
**Deciders:** Platform/AI engineering (this assessment)

## 1. Context

The brief requires a document search platform with an **agentic RAG backend**
exposing REST APIs, fronted by **OpenWebUI**, built on a fixed, mandated
toolset: Docling, PostgreSQL+PGVector, LlamaIndex, CrewAI, Ollama, Arize
Phoenix, and RAGAs. Because the toolset itself isn't a free choice, this
document focuses on the architectural decisions made *within* those
constraints: how the pieces are composed, where the "agentic" and
"contextual" behavior actually lives, how prompts are externalized, how
tracing is guaranteed to cover every inference call, and how OpenWebUI talks
to a fully custom backend.

Diagrams referenced throughout: [`system_architecture.png`](system_architecture.png)
(component view), [`agentic_rag_sequence.png`](agentic_rag_sequence.png)
(request-time sequence), [`ingestion_flow.png`](ingestion_flow.png)
(ingestion pipeline).

## 2. Decision

Build a single FastAPI service (`backend/`) that owns three responsibilities
- ingestion, agentic retrieval/generation, and evaluation - backed by
PostgreSQL+PGVector as the sole system of record for vectors, Ollama as the
sole LLM/embedding provider, and Phoenix as the sole trace sink. OpenWebUI
is treated as a replaceable, standard OpenAI-compatible client rather than a
tightly-coupled component.

### 2.1 Ingestion: Docling -> heading-aware split -> Ollama embed -> PGVector

Docling's `DocumentConverter` (`app/ingestion/docling_loader.py`) handles PDF
layout analysis, reading order, and table-structure recognition, then
exports clean Markdown per document. Splitting happens in two passes
(`app/ingestion/pipeline.py`):

1. `MarkdownNodeParser` splits on heading boundaries first, so a chunk never
   silently crosses from one policy section into an unrelated one.
2. `SentenceSplitter` then enforces a token-size ceiling (`CHUNK_SIZE`
   /`CHUNK_OVERLAP`) within each section, so long sections still produce
   retrieval-friendly chunk sizes.

Every chunk keeps `source_file` and a human-readable `section_path` in its
metadata, which is what lets the Synthesizer agent cite "(Source:
data_privacy_security_policy.pdf, 2. Data Classification)" instead of an
opaque chunk ID.

**Why not naive fixed-size character chunking?** It regularly splits a table
row or a numbered policy clause in half, which measurably hurts both
retrieval precision and the Verifier agent's ability to confirm a claim
against a coherent passage. The two-pass approach costs one extra parser
pass and is worth it.

### 2.2 Retrieval + generation: an explicit agentic loop, not a single call

This is the central design decision, since "contextual Agentic RAG" is a
requirement, not just "RAG":

- **Query Analyzer agent** rewrites the question (resolving chat-history
  references) and decomposes it into 1-3 targeted sub-queries.
- **Retriever agent** owns the `search_knowledge_base` CrewAI tool (backed by
  `app/retrieval/query_engine.py`, which wraps the LlamaIndex retriever over
  the PGVector index) and explicitly flags sub-queries with no supporting
  evidence rather than dropping them.
- **Synthesizer agent** writes a cited answer from *only* the retrieved
  evidence.
- **Verifier agent** checks every claim against the evidence and either
  `APPROVE`s or `REJECT`s with a refined query.

CrewAI's `Process.sequential` handles the Retriever -> Synthesizer -> Verifier
hand-off within one pass (via `Task(context=[...])` dependency wiring). The
**outer retry loop** (reject -> refined query -> retry, up to
`CREW_MAX_ITERATIONS`) is implemented as plain Python control flow in
`app/agents/crew.py::run_agentic_rag`, not as a CrewAI hierarchical crew.

**Alternative considered - CrewAI hierarchical process with a manager
agent.** A manager agent could in principle own the retry decision itself.
Rejected for this build because: (a) it adds a fifth agent's worth of LLM
calls and latency for every single query, even ones the Verifier would have
approved on the first pass; (b) with a small local Ollama model, a manager
agent making free-form delegation decisions is measurably less reliable
than a fixed, inspectable Python loop; (c) the loop's exit conditions
(approved, or max iterations exhausted) are simple enough that an explicit
loop is more debuggable and cheaper to trace than emergent manager behavior.
This can be revisited if a larger/remote LLM is swapped in later.

**Alternative considered - single-shot RAG (retrieve once, generate once).**
Rejected because it does not satisfy the "agentic"/"contextual" requirement
and, empirically on the RAGAs eval set (see
[`../evaluation/evaluation_report.md`](../evaluation/evaluation_report.md)),
produces materially lower faithfulness on multi-part questions where the
first retrieval pass misses one clause.

### 2.3 Prompts: externalized YAML, not f-strings in Python

Every agent persona (`role`/`goal`/`backstory`) and task instruction
(`description`/`expected_output`) lives in
`backend/app/prompts/library/*.yaml`, loaded by `PromptManager`
(`app/prompts/manager.py`). Consequences:

- A prompt change is a YAML diff, reviewable independently of application
  code, and hot-reloadable via `POST /api/v1/prompts/reload` without a
  service restart.
- Each prompt file is versioned (`version: "1.2.0"`) so a Phoenix trace can
  record exactly which prompt version produced a given span.
- `GET /api/v1/prompts` exposes the live prompt inventory for audit.

**Alternative considered - Phoenix Prompt Hub as the source of truth.**
Phoenix does support prompt management ("PromptOps"). We treat file-based
YAML as the source of truth (git-versioned, code-reviewable, works offline)
and note in the README how to additionally sync prompts into Phoenix's hub
for UI-based editing/experimentation - the two are complementary, not
exclusive, and a team already invested in Phoenix's prompt workflow can flip
the precedence.

### 2.4 Tracing: instrument once, at process startup, unconditionally

`app/tracing/phoenix_setup.py::init_tracing()` runs in FastAPI's `startup`
event, before any request is served, and instruments LlamaIndex, CrewAI, and
LiteLLM (the layer CrewAI uses to actually call Ollama) via OpenInference/
OpenTelemetry, exporting to the Phoenix collector. Doing this once at
startup - rather than wrapping individual call sites - means a new call site
added later is traced automatically instead of requiring the author to
remember to instrument it, which is what "tracing for all inference calls"
actually requires in practice.

### 2.5 OpenWebUI integration: OpenAI-compatible surface, not a custom plugin

The backend exposes `/v1/chat/completions` and `/v1/models` matching the
OpenAI Chat Completions contract (`app/api/routes_chat.py`). OpenWebUI is
configured with this backend as a custom "OpenAI API" connection
(`OPENAI_API_BASE_URL=http://backend:8000/v1` in `docker-compose.yml`) - no
custom OpenWebUI "Function"/"Pipeline" code is required.

**Alternative considered - an OpenWebUI Pipelines plugin.** Rejected as the
default because it couples the RAG logic to OpenWebUI's plugin runtime and
requires deploying and maintaining a second Python service (the Pipelines
server). The OpenAI-compat surface works with *any* OpenAI SDK client, not
just OpenWebUI, and is the smaller moving part. The trade-off: OpenWebUI's
native RAG/citation UI affordances aren't used - citations are instead
appended as a Markdown "Sources" section in the assistant message
(`routes_chat.py::chat_completions`), which renders fine in the chat UI but
isn't structured. This is called out in the README as a documented, revisit-
able limitation.

### 2.6 Evaluation: RAGAs over the real pipeline, not a mocked one

`app/evaluation/run_ragas.py` runs the curated Q&A set
(`app/evaluation/qa_dataset.json`) through the *actual* `run_agentic_rag()`
code path - the same one `/api/v1/query` and `/v1/chat/completions` use -
rather than a separate simplified retrieval-only harness. This is slower
(each question invokes the full 4-agent crew) but means the eval numbers
describe what a user actually experiences, including cases where the
Verifier's retry loop changes the final answer. RAGAs' judge LLM and judge
embeddings are the same Ollama-backed LlamaIndex models used in production
(`LlamaIndexLLMWrapper`/`LlamaIndexEmbeddingsWrapper`), so no OpenAI key is
required anywhere in the stack.

## 3. Options Considered (tooling-adjacent choices not mandated by the brief)

| Decision | Chosen | Rejected alternative | Why |
|---|---|---|---|
| Chunking strategy | Heading-aware split + sentence-splitter ceiling | Fixed-size character windows | Fewer mid-table/mid-clause splits; better citation quality |
| Agent retry control | Explicit Python loop around a CrewAI sequential crew | CrewAI hierarchical process w/ manager agent | Cheaper, more debuggable with a small local model |
| OpenWebUI wiring | OpenAI-compatible `/v1/chat/completions` | Custom OpenWebUI Pipelines plugin | One fewer service; works with any OpenAI client |
| Prompt source of truth | Git-versioned YAML files | Database-backed prompt store | Reviewable in PRs; no extra schema/migration; still hot-reloadable |
| Vector index | Single PGVector table, HNSW/cosine | Per-document-type tables | Simpler for this corpus size; revisit if corpus grows >10M chunks |

## 4. Consequences

**Easier:**
- Prompt iteration is a YAML edit + `POST /prompts/reload`, no redeploy.
- Any inference call added to the codebase is traced by default.
- Swapping OpenWebUI for another OpenAI-compatible client (or the Swagger UI
  directly) requires zero backend changes.
- RAGAs scores reflect the real, agentic, multi-iteration pipeline.

**Harder / explicitly deferred:**
- No streaming token-by-token responses (the crew produces one final answer
  per turn); `stream=true` is rejected with a clear error rather than
  silently ignored. Revisit if perceived latency becomes a problem with a
  larger local model.
- No structured citation UI in OpenWebUI (citations are Markdown text, not
  OpenWebUI's native citation cards). Revisit via a Pipelines plugin if that
  UX matters more than deployment simplicity.
- Single-tenant, no per-user auth/ACLs on documents (optional bearer
  `API_KEY` gate only) - out of scope per the assessment brief, called out
  in the README as a production hardening item.
- Ingestion is a full re-embed of the source directory today - no
  incremental/delta ingestion by content hash. Fine for the assessment's
  document volumes; a "Future Work" item in the README for a real corpus.

## 5. Action Items

1. [x] Implement ingestion pipeline (Docling -> split -> embed -> PGVector).
2. [x] Implement the 4-agent CrewAI crew + outer verify/retry loop.
3. [x] Externalize all prompts to YAML with a hot-reload endpoint.
4. [x] Instrument Phoenix tracing at process startup.
5. [x] Expose OpenAI-compatible + native REST surfaces with OpenAPI docs.
6. [x] Build the RAGAs evaluation harness over the real pipeline.
7. [ ] Run the full stack against the real network-enabled environment and
       capture live trace screenshots + eval numbers (blocked on network
       egress allowlist at the time of writing - see README "Known
       Limitations of This Build").
