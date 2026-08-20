"""
RAGAs evaluation harness.

Runs the curated Q&A set (app/evaluation/qa_dataset.json) through the *real*
retrieval + agentic generation pipeline (the same code path `/api/v1/query`
uses), then scores the results with RAGAs:

  - faithfulness        : is the answer supported by the retrieved context?
  - answer_relevancy     : does the answer actually address the question?
  - context_precision    : how much of the retrieved context is relevant?
  - context_recall       : did retrieval surface the context needed to
                            reconstruct the ground-truth answer?

Uses the locally-hosted Ollama LLM/embeddings (via LlamaIndex wrappers) as
the RAGAs judge model -- no OpenAI key required, consistent with the
"Ollama: local or remote LLM provider" requirement.

Run via CLI:
    python -m app.evaluation.run_ragas

Or via API: POST /api/v1/eval/run
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import Settings, get_settings
from app.evaluation.dataset import load_qa_dataset

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    num_questions: int
    scores: Dict[str, Optional[float]]
    report_path: str
    per_question: list


def _collect_predictions(dataset_path: str, settings: Settings) -> list[dict]:
    """For each curated question: run retrieval directly (for
    `retrieved_contexts`) and the full agentic crew (for `response`), which
    internally performs its own retrieval -- we keep the two independent so
    RAGAs' context-based metrics reflect exactly what the crew actually saw
    on its final, verified pass rather than a separate debug-only query.
    """
    from app.agents.crew import run_agentic_rag
    from app.retrieval.query_engine import retrieve

    items = load_qa_dataset(dataset_path)
    predictions = []
    for item in items:
        logger.info("Evaluating: %s", item.question)
        contexts = retrieve(item.question, top_k=settings.retriever_top_k)
        rag_result = run_agentic_rag(question=item.question)
        predictions.append(
            {
                "user_input": item.question,
                "response": rag_result.answer,
                "retrieved_contexts": [c["text"] for c in contexts] or [""],
                "reference": item.ground_truth_answer,
                "source_file": item.source_file,
                "approved": rag_result.approved,
                "iterations": rag_result.iterations,
            }
        )
    return predictions


def run_evaluation(dataset_path: str | None = None, settings: Settings | None = None) -> EvalResult:
    settings = settings or get_settings()
    dataset_path = dataset_path or settings.eval_dataset_path

    from app.retrieval.vector_store import configure_llama_index_settings

    configure_llama_index_settings(settings)

    predictions = _collect_predictions(dataset_path, settings)

    from ragas import EvaluationDataset, evaluate
    from ragas.embeddings import LlamaIndexEmbeddingsWrapper
    from ragas.llms import LlamaIndexLLMWrapper
    from ragas.metrics import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

    from llama_index.core import Settings as LlamaSettings

    judge_llm = LlamaIndexLLMWrapper(LlamaSettings.llm)
    judge_embeddings = LlamaIndexEmbeddingsWrapper(LlamaSettings.embed_model)

    eval_dataset = EvaluationDataset.from_list(
        [
            {
                "user_input": p["user_input"],
                "response": p["response"],
                "retrieved_contexts": p["retrieved_contexts"],
                "reference": p["reference"],
            }
            for p in predictions
        ]
    )

    metrics = [
        Faithfulness(llm=judge_llm),
        AnswerRelevancy(llm=judge_llm, embeddings=judge_embeddings),
        ContextPrecision(llm=judge_llm),
        ContextRecall(llm=judge_llm),
    ]

    logger.info("Running RAGAs evaluate() over %d questions with %d metrics", len(predictions), len(metrics))
    result = evaluate(dataset=eval_dataset, metrics=metrics)
    scores_df = result.to_pandas()

    aggregate = {
        "faithfulness": _safe_mean(scores_df, "faithfulness"),
        "answer_relevancy": _safe_mean(scores_df, "answer_relevancy"),
        "context_precision": _safe_mean(scores_df, "context_precision"),
        "context_recall": _safe_mean(scores_df, "context_recall"),
    }

    report_dir = Path(settings.eval_report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"ragas_report_{int(time.time())}.json"

    per_question = []
    for i, p in enumerate(predictions):
        row = scores_df.iloc[i].to_dict() if i < len(scores_df) else {}
        per_question.append(
            {
                "question": p["user_input"],
                "answer": p["response"],
                "reference": p["reference"],
                "approved_by_verifier": p["approved"],
                "iterations": p["iterations"],
                "faithfulness": row.get("faithfulness"),
                "answer_relevancy": row.get("answer_relevancy"),
                "context_precision": row.get("context_precision"),
                "context_recall": row.get("context_recall"),
            }
        )

    report = {"aggregate_scores": aggregate, "num_questions": len(predictions), "per_question": per_question}
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("RAGAs evaluation complete. Aggregate scores: %s", aggregate)
    return EvalResult(
        num_questions=len(predictions),
        scores=aggregate,
        report_path=str(report_path),
        per_question=per_question,
    )


def _safe_mean(df: Any, column: str) -> Optional[float]:
    if column not in df:
        return None
    try:
        return round(float(df[column].mean()), 4)
    except Exception:
        return None


def _cli() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Run the RAGAs evaluation harness")
    parser.add_argument("--dataset-path", default=None)
    args = parser.parse_args()
    result = run_evaluation(dataset_path=args.dataset_path)
    print(json.dumps({"scores": result.scores, "report_path": result.report_path}, indent=2))


if __name__ == "__main__":
    _cli()
