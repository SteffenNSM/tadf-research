"""Workflow implementation for archetype C: Ambiguous Classification and Disambiguation.

Canonical-minimal form for a structured-output classification task: a single
LLM call with ``with_structured_output(ClassificationResult, ...)`` against
the email provided in state. No plan stage, no tool dispatch; the
classification is the entire task and structured output constrains the label
to the documented Literal enum, eliminating output-format ambiguity by
design.

Graph topology:
    [classify] -> END

This differs from archetypes A and F (two-stage and four-stage respectively)
because C does not require an information-gathering stage: the email text is
in the prompt and the category definitions are in the prompt, so the LLM
has everything it needs in one call. The agent paradigm has the same
information but pays the ReAct system-prompt overhead and the parsing cost
of free-text label extraction, which the structured workflow avoids by
construction.
"""

from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.c_ambiguous_classification.config import (
    CATEGORY_DEFINITIONS,
    CLASSIFY_PROMPT,
    TEMPERATURE,
)
from src.archetypes.c_ambiguous_classification.schemas import ClassificationResult
from src.core.llm import get_llm


def classify(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 1: produce the ClassificationResult (single LLM call)."""
    llm = get_llm(TEMPERATURE).with_structured_output(
        ClassificationResult, method="function_calling"
    )
    email_json = json.dumps(state["email"], indent=2, ensure_ascii=False)
    result: ClassificationResult = llm.invoke(
        CLASSIFY_PROMPT.format(
            definitions=CATEGORY_DEFINITIONS,
            email=email_json,
            instruction=state["instruction"],
        )
    )
    return {**state, "output": result.model_dump(), "completed": True}


def build_workflow():
    """Construct and compile the archetype C workflow."""
    graph = StateGraph(dict)
    graph.add_node("classify", classify)
    graph.set_entry_point("classify")
    graph.add_edge("classify", END)
    return graph.compile()


workflow = build_workflow()
