# RAG Pipeline Evaluation — Methodology & Results

## Methodology

**What's being evaluated.** The RAGAs harness (`backend/app/evaluation/run_ragas.py`)
runs every question in the curated set (`backend/app/evaluation/qa_dataset.json`)
through the **production code path** — `run_agentic_rag()`, the exact
function `/api/v1/query` and OpenWebUI's `/v1/chat/completions` call — not a
simplified retrieval-only shortcut. This means the reported scores reflect
whatever the Verifier agent's retry loop actually converges on, including
cases where the first retrieval pass missed something and a later iteration
corrected it.

**Dataset.** 12 question/ground-truth pairs (`qa_dataset.json`), each
written against one of the 4 placeholder documents in `sample_docs/`
(`cloud_architecture_standards.pdf`, `data_privacy_security_policy.pdf`,
`product_api_reference_guide.pdf`, `employee_handbook_leave_policy.pdf`).
Each question targets a specific, checkable fact (a percentage, a time
window, a retry count) rather than an open-ended summary, so faithfulness
and context-recall scores are meaningfully interpretable rather than
inflated by vague phrasing. **When the real Google Drive corpus is
substituted, replace this file** — `backend/app/prompts/library/ragas_testset_seed.yaml`
is an externalized prompt for LLM-assisted candidate question generation
from a chunk, meant to be reviewed by a human before being added here (RAGAs-
generated questions are a starting point, not a final eval set).

**Metrics** (all computed by RAGAs, judged by the same Ollama-backed
LlamaIndex LLM/embeddings used in production — no OpenAI key involved):

| Metric | What it measures | Computed from |
|---|---|---|
| Faithfulness | Fraction of claims in the answer that are directly supported by the retrieved context | `response`, `retrieved_contexts` |
| Answer relevancy | How well the answer addresses the actual question asked (penalizes off-topic or evasive answers) | `user_input`, `response` |
| Context precision | How much of what was retrieved is actually relevant to the reference answer | `retrieved_contexts`, `reference` |
| Context recall | Whether retrieval surfaced everything needed to reconstruct the reference answer | `retrieved_contexts`, `reference` |

**Per-question metadata also recorded** (not RAGAs metrics, but useful
context): whether the Verifier agent ultimately `approved` the answer, and
how many retrieve/synthesize/verify iterations it took — a high iteration
count on an otherwise-high-scoring question is a signal the Verifier is
doing useful work catching a bad first draft; a high iteration count *and* a
low final score is a signal the retry loop isn't enough and the retriever/
chunking needs attention for that document.

**How to reproduce:**

```bash
docker compose up -d --build
docker compose run --rm ollama-pull
./scripts/ingest.sh
./scripts/run_eval.sh
```

The full per-question report (including each answer, its citations, and its
four scores) is written as timestamped JSON to `EVAL_REPORT_DIR`
(`/data/eval_reports` in the container). Copy it out with:

```bash
docker compose cp backend:/data/eval_reports/. ./doc/evaluation/runs/
```

## Results

> **Status: pending a live run.** This build was authored in a sandboxed
> development environment without outbound access to PyPI/Docker Hub/Ollama's
> model registry (see the root [README §Known limitations](../../README.md#known-limitations-of-this-build)
> and the architecture doc's action item #7), so the pipeline has been
> validated by static checks (byte-compilation of every module, unit tests
> of the prompt-loading and JSON-parsing logic, `docker compose config`
> validation) but not yet executed end-to-end against a live Ollama model.
> Run `./scripts/run_eval.sh` after `docker compose up`, then replace this
> section with the actual `aggregate_scores` output — a filled-in example of
> the target shape:

```json
{
  "aggregate_scores": {
    "faithfulness": 0.0,
    "answer_relevancy": 0.0,
    "context_precision": 0.0,
    "context_recall": 0.0
  },
  "num_questions": 12
}
```

### Reading the numbers once populated

- **Faithfulness below ~0.8** usually means the Synthesizer is drawing on
  the LLM's general knowledge instead of the retrieved passage, or the
  Verifier's approval bar is too lenient for the model in use — check
  `backend/app/prompts/library/verifier_agent.yaml` first.
- **Context recall below ~0.7** usually means chunking or `RETRIEVER_TOP_K`
  needs tuning, not the generation prompts — check whether the relevant
  passage is being retrieved at all via `POST /api/v1/search` before
  touching the agent prompts.
- **Low answer relevancy with high faithfulness** typically means the Query
  Analyzer's sub-query decomposition is drifting from the original
  question's intent — inspect the `query_analysis` stage in a Phoenix trace
  for the affected question.
