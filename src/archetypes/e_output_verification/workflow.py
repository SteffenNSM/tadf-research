"""Workflow implementation for archetype E: Output Verification and Quality Control.

Canonical-minimal form for an LLM-as-Judge task: a single LLM call with
``with_structured_output(QualityVerdict, ...)`` over the inquiry, the
candidate response, and the rubric. No plan stage, no tool dispatch; the
judge call is the entire task and structured output constrains the verdict
to the documented Literal enum so the workflow cannot emit an invented
label.

Graph topology:
    [judge] -> END

This is the third single-stage workflow archetype in the TADF (after C and
D). The shared architectural pattern reflects the shared dimensional
signature: high Step Predictability, high Information Availability, low
Output Ambiguity. The empirical differences across C / D / E show up in
the failure distribution rather than in the workflow's graph — C tests
input ambiguity, D tests rule depth, E tests judgment quality against a
rubric.
"""

from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.e_output_verification.config import (
    CLASSIFY_PROMPT,
    EVALUATION_RUBRIC,
    TEMPERATURE,
)
from src.archetypes.e_output_verification.schemas import QualityVerdict
from src.core.llm import get_llm


def judge(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 1: produce the QualityVerdict (single LLM call)."""
    llm = get_llm(TEMPERATURE).with_structured_output(
        QualityVerdict, method="function_calling"
    )
    inquiry_json = json.dumps(state["inquiry"], indent=2, ensure_ascii=False)
    candidate_json = json.dumps(state["candidate_response"], indent=2, ensure_ascii=False)
    result: QualityVerdict = llm.invoke(
        CLASSIFY_PROMPT.format(
            rubric=EVALUATION_RUBRIC,
            inquiry=inquiry_json,
            candidate_response=candidate_json,
            instruction=state["instruction"],
        )
    )
    return {**state, "output": result.model_dump(), "completed": True}


def build_workflow():
    """Construct and compile the archetype E workflow."""
    graph = StateGraph(dict)
    graph.add_node("judge", judge)
    graph.set_entry_point("judge")
    graph.add_edge("judge", END)
    return graph.compile()


workflow = build_workflow()
