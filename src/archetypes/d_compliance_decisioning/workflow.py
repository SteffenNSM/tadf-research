"""Workflow implementation for archetype D: Compliance and Rule-Based Decisioning.

Canonical-minimal form for a rule-application decision task: a single LLM
call with ``with_structured_output(DecisionResult, ...)`` against the quote
request provided in state. No plan stage, no tool dispatch; the policy
application is the entire task and structured output constrains the label
to the documented Literal enum so the workflow cannot emit an invented
decision.

Graph topology:
    [decide] -> END

The architecture parallels archetype C deliberately: both archetypes share
the high Step Predictability / high Information Availability / low Output
Ambiguity profile, so the canonical-minimal forms collapse to the same
structural pattern (one LLM call, structured output, no information
gathering). The empirical difference between C and D shows in the failure
distribution rather than in the workflow's graph: C tests input-ambiguity
resolution, D tests rule-depth application, and the difficulty axes are
operationalized accordingly.
"""

from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.d_compliance_decisioning.config import (
    CLASSIFY_PROMPT,
    POLICY_RULES,
    TEMPERATURE,
)
from src.archetypes.d_compliance_decisioning.schemas import DecisionResult
from src.core.llm import get_llm


def decide(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 1: produce the DecisionResult (single LLM call)."""
    llm = get_llm(TEMPERATURE).with_structured_output(
        DecisionResult, method="function_calling"
    )
    qr_json = json.dumps(state["quote_request"], indent=2, ensure_ascii=False)
    result: DecisionResult = llm.invoke(
        CLASSIFY_PROMPT.format(
            rules=POLICY_RULES,
            quote_request=qr_json,
            instruction=state["instruction"],
        )
    )
    return {**state, "output": result.model_dump(), "completed": True}


def build_workflow():
    """Construct and compile the archetype D workflow."""
    graph = StateGraph(dict)
    graph.add_node("decide", decide)
    graph.set_entry_point("decide")
    graph.add_edge("decide", END)
    return graph.compile()


workflow = build_workflow()
