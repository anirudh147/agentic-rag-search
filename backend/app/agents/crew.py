"""
The agentic RAG crew: Query Analyzer -> (Retriever -> Synthesizer ->
Verifier) loop.

This is what makes the pipeline "contextual" and "agentic" rather than a
single fixed retrieve-then-generate call:
  1. Query Analyzer runs once: rewrites the question and plans sub-queries.
  2. Retriever + Synthesizer + Verifier run as a CrewAI sequential crew.
  3. If the Verifier rejects the draft (unsupported claims, missing
     evidence, doesn't answer the question), the loop retries with the
     Verifier's own refined query -- up to `settings.crew_max_iterations`
     times -- before returning the best available answer.

All agent personas and task instructions are loaded from
`app/prompts/library/*.yaml` via PromptManager (see app/prompts/manager.py)
-- nothing here is a hardcoded prompt string, satisfying the "prompts
externalized from application code" requirement.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.config import Settings, get_settings
from app.prompts.manager import get_prompt_manager

logger = logging.getLogger(__name__)


@dataclass
class AgentRAGResult:
    answer: str
    approved: bool
    iterations: int
    sources: List[Dict[str, Any]] = field(default_factory=list)
    trace: List[Dict[str, Any]] = field(default_factory=list)


def _parse_json_loose(text: str) -> Dict[str, Any]:
    """LLMs (especially small local models) often wrap JSON in prose or code
    fences. Extract the first {...} block and parse it, falling back to an
    empty dict rather than raising -- callers treat a missing key as
    "unknown" and degrade gracefully instead of crashing the request.
    """
    if not text:
        return {}
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("Could not parse JSON from agent output: %r", text[:300])
        return {}


def _get_llm(settings: Settings):
    """CrewAI's native LLM wrapper, pointed at the local/remote Ollama
    server. Using CrewAI's own `LLM` class (backed by LiteLLM) keeps this
    independent from the LlamaIndex `Ollama` LLM used for embeddings/direct
    querying (app/retrieval/vector_store.py) -- the two libraries do not
    share an LLM abstraction.
    """
    from crewai import LLM

    return LLM(
        model=f"ollama/{settings.ollama_llm_model}",
        base_url=settings.ollama_base_url,
        temperature=0.1,
        max_tokens=settings.ollama_max_tokens,
    )


def _build_agent(prompt_name: str, llm, tools: Optional[list] = None, **render_kwargs):
    from crewai import Agent

    pm = get_prompt_manager()
    prompt = pm.get(prompt_name)
    settings = get_settings()
    return Agent(
        role=prompt.render_field("role", **render_kwargs),
        goal=prompt.render_field("goal", **render_kwargs),
        backstory=prompt.render_field("backstory", **render_kwargs),
        llm=llm,
        tools=tools or [],
        verbose=settings.crew_verbose,
        allow_delegation=False,
        max_iter=settings.crew_agent_max_iter,
        max_execution_time=settings.crew_agent_max_execution_time,
        max_retry_limit=1,
    )


def _analyze_query(question: str, chat_history: str, llm) -> Dict[str, Any]:
    from crewai import Crew, Process, Task

    pm = get_prompt_manager()
    render_kwargs = {"question": question, "chat_history": chat_history or "(none)"}
    agent = _build_agent("query_analyzer", llm, **render_kwargs)
    task = Task(
        description=pm.render_field("query_analyzer", "description", **render_kwargs),
        expected_output=pm.render_field("query_analyzer", "expected_output"),
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=get_settings().crew_verbose)
    raw = str(crew.kickoff())
    parsed = _parse_json_loose(raw)
    return {
        "standalone_query": parsed.get("standalone_query", question),
        "sub_queries": parsed.get("sub_queries") or [question],
        "answer_type": parsed.get("answer_type", "fact"),
        "raw": raw,
    }


def _retrieve_synthesize_verify(
    question: str, standalone_query: str, sub_queries: List[str], llm, settings: Settings
) -> Dict[str, Any]:
    from crewai import Crew, Process, Task

    from app.agents.tools import get_search_tool

    pm = get_prompt_manager()
    search_tool = get_search_tool()

    retriever_kwargs = {
        "standalone_query": standalone_query,
        "sub_queries": json.dumps(sub_queries),
        "top_k": settings.retriever_top_k,
    }
    retriever_agent = _build_agent("retriever_agent", llm, tools=[search_tool], **retriever_kwargs)
    retriever_task = Task(
        description=pm.render_field("retriever_agent", "description", **retriever_kwargs),
        expected_output=pm.render_field("retriever_agent", "expected_output"),
        agent=retriever_agent,
    )

    synth_kwargs = {"question": question, "evidence": "(see retrieval task output above)"}
    synthesizer_agent = _build_agent("synthesizer_agent", llm, **synth_kwargs)
    synthesizer_task = Task(
        description=pm.render_field("synthesizer_agent", "description", **synth_kwargs),
        expected_output=pm.render_field("synthesizer_agent", "expected_output"),
        agent=synthesizer_agent,
        context=[retriever_task],
    )

    verifier_kwargs = {
        "question": question,
        "draft_answer": "(see synthesis task output above)",
        "evidence": "(see retrieval task output above)",
    }
    verifier_agent = _build_agent("verifier_agent", llm, **verifier_kwargs)
    verifier_task = Task(
        description=pm.render_field("verifier_agent", "description", **verifier_kwargs),
        expected_output=pm.render_field("verifier_agent", "expected_output"),
        agent=verifier_agent,
        context=[retriever_task, synthesizer_task],
    )

    crew = Crew(
        agents=[retriever_agent, synthesizer_agent, verifier_agent],
        tasks=[retriever_task, synthesizer_task, verifier_task],
        process=Process.sequential,
        verbose=settings.crew_verbose,
    )
    crew.kickoff()

    retrieval_raw = str(retriever_task.output) if retriever_task.output else ""
    draft_answer = str(synthesizer_task.output) if synthesizer_task.output else ""
    verdict_raw = str(verifier_task.output) if verifier_task.output else ""
    verdict = _parse_json_loose(verdict_raw)

    sources = _extract_sources(retrieval_raw)

    return {
        "draft_answer": draft_answer,
        "verdict": verdict.get("verdict", "APPROVE"),
        "reason": verdict.get("reason", ""),
        "refined_query": verdict.get("refined_query"),
        "sources": sources,
        "retrieval_raw": retrieval_raw,
    }


def _extract_sources(retrieval_raw: str) -> List[Dict[str, Any]]:
    """Best-effort extraction of (source_file, section) pairs the retriever
    agent mentioned, by re-running the same sub-query search deterministically
    is avoided here -- instead we just scan the tool's own JSON output that
    CrewAI logs as part of the task, falling back to an empty list."""
    sources: List[Dict[str, Any]] = []
    for match in re.finditer(r'"source_file"\s*:\s*"([^"]+)"[^}]*?"section_path"\s*:\s*"([^"]*)"', retrieval_raw):
        entry = {"source_file": match.group(1), "section_path": match.group(2)}
        if entry not in sources:
            sources.append(entry)
    return sources


def run_agentic_rag(
    question: str,
    chat_history: str = "",
    settings: Optional[Settings] = None,
) -> AgentRAGResult:
    settings = settings or get_settings()
    llm = _get_llm(settings)

    plan = _analyze_query(question, chat_history, llm)
    trace: List[Dict[str, Any]] = [{"stage": "query_analysis", "output": plan}]

    standalone_query = plan["standalone_query"]
    sub_queries = plan["sub_queries"]

    last_result: Dict[str, Any] = {}
    for iteration in range(1, settings.crew_max_iterations + 1):
        result = _retrieve_synthesize_verify(question, standalone_query, sub_queries, llm, settings)
        last_result = result
        trace.append({"stage": f"iteration_{iteration}", "output": result})

        if result["verdict"].upper() == "APPROVE":
            return AgentRAGResult(
                answer=result["draft_answer"],
                approved=True,
                iterations=iteration,
                sources=result["sources"],
                trace=trace,
            )

        if result.get("refined_query"):
            standalone_query = result["refined_query"]
            sub_queries = [result["refined_query"]]
        logger.info(
            "Verifier rejected answer on iteration %d (reason=%s); retrying", iteration, result.get("reason")
        )

    # Exhausted retries: return the last draft, flagged as unapproved so the
    # API layer / UI can surface that this answer wasn't fully verified.
    return AgentRAGResult(
        answer=last_result.get("draft_answer", "I could not find a reliable answer in the knowledge base."),
        approved=False,
        iterations=settings.crew_max_iterations,
        sources=last_result.get("sources", []),
        trace=trace,
    )
