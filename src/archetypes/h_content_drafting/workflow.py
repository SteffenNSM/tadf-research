"""Workflow implementation for archetype H: Content Drafting and Refinement.

Fixed-pipeline canonical form: one draft node followed by exactly one
revise node per scripted feedback round. The topology is determined at
compile time by the instance's feedback-round count — no LLM-controlled
edges, no self-initiated extra revisions. This is the deliberate foil to
the agent's runtime-controlled self-revision loop (the Step-Predictability
contrast of Section 2.2.2): the workflow revises exactly as many times as
there are feedback rounds, no more, no less.

Topology (built per instance):
    [draft] -> [revise_1] -> ... -> [revise_k] -> END      (k = #feedback rounds)
    [draft] -> END                                          (k = 0)

Each node is one LLM call with structured output (Draft). No tools (H has
an empty tool set for both paradigms).
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.h_content_drafting.config import (
    BRIEF_PREAMBLE,
    DRAFT_PROMPT,
    REVISE_PROMPT,
    TEMPERATURE,
    render_constraints,
    render_table,
)
from src.archetypes.h_content_drafting.schemas import Draft
from src.core.llm import get_llm


def _draft_node(state: dict, config: RunnableConfig | None = None) -> dict:
    inst = state["instance"]
    llm = get_llm(TEMPERATURE).with_structured_output(Draft, method="function_calling")
    draft: Draft = llm.invoke(
        DRAFT_PROMPT.format(
            preamble=BRIEF_PREAMBLE,
            table=render_table(inst["table"]),
            constraints=render_constraints(inst),
            instruction=inst["instruction"],
        )
    )
    return {**state, "draft": draft.model_dump()}


def _make_revise_node(round_index: int):
    def _revise(state: dict, config: RunnableConfig | None = None) -> dict:
        inst = state["instance"]
        feedback = inst["feedback_rounds"][round_index]
        cur = Draft(**state["draft"])
        llm = get_llm(TEMPERATURE).with_structured_output(Draft, method="function_calling")
        revised: Draft = llm.invoke(
            REVISE_PROMPT.format(
                preamble=BRIEF_PREAMBLE,
                table=render_table(inst["table"]),
                constraints=render_constraints(inst),
                title=cur.title,
                body=cur.body,
                feedback=feedback,
            )
        )
        return {**state, "draft": revised.model_dump()}

    return _revise


def _finalize(state: dict, config: RunnableConfig | None = None) -> dict:
    return {**state, "output": state["draft"], "completed": True}


def build_workflow(n_feedback_rounds: int):
    """Compile a fixed pipeline with one revise node per feedback round."""
    graph = StateGraph(dict)
    graph.add_node("draft", _draft_node)
    graph.set_entry_point("draft")
    prev = "draft"
    for i in range(n_feedback_rounds):
        name = f"revise_{i + 1}"
        graph.add_node(name, _make_revise_node(i))
        graph.add_edge(prev, name)
        prev = name
    graph.add_node("finalize", _finalize)
    graph.add_edge(prev, "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def run_workflow(inst: dict, config: dict | None = None) -> dict:
    """Run the fixed pipeline for one instance; returns the final Draft dict."""
    wf = build_workflow(len(inst.get("feedback_rounds", [])))
    state = wf.invoke({"instance": inst}, config=config or {})
    return state.get("output", {})
