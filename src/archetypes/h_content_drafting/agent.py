"""Agent implementation for archetype H: Content Drafting and Refinement.

A runtime-controlled self-revision loop, implemented as a LangGraph
StateGraph with a single conditional edge resolved by the LLM (protocol
A.3). Each turn rewrites the full artefact and emits a decision
('revise' / 'submit'); the router loops back for another self-revision,
injects the next scripted feedback round at a submit point, or terminates.
Unlike the workflow's fixed revise-per-feedback pipeline, the number of
self-revisions is chosen by the model at execution time — the
Step-Predictability contrast that defines the paradigm difference for H.

H exposes no tools to either paradigm (high Information Availability, all
content inline), so the loop is tool-free; the "agentic" property is the
runtime revise-vs-submit control and termination.

Step limit (protocol A.6): turns are capped at config.MAX_AGENT_STEPS per
difficulty. Reaching the cap before all feedback rounds are incorporated,
or while still wanting to revise, is recorded as ``iteration_overflow``.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.h_content_drafting.config import (
    AGENT_SYSTEM_PROMPT,
    BRIEF_PREAMBLE,
    MAX_AGENT_STEPS,
    REVISE_PROMPT,
    TEMPERATURE,
    render_constraints,
    render_table,
)
from src.archetypes.h_content_drafting.schemas import AgentTurn
from src.core.llm import get_llm

_DRAFT_USER = """Data table:
{table}

Writing constraints:
{constraints}

Task: {instruction}

Write the first draft. If it already satisfies every constraint and is well written, you may set decision to 'submit'; otherwise set 'revise' and note what to improve."""

_SELF_REVISE_USER = """Your current draft:
Title: {title}
Body:
{body}

Your own note for improvement: {critique}

Produce an improved draft. Set decision to 'submit' once every constraint is met and the writing is tight; otherwise 'revise'."""

_FEEDBACK_USER = """Your current draft:
Title: {title}
Body:
{body}

Reviewer feedback to incorporate now:
{feedback}

Revise to incorporate this feedback while keeping every original constraint satisfied. Set decision to 'submit' when the revised draft is ready, or 'revise' to keep improving it."""


def _turn(state: dict, config: RunnableConfig | None = None) -> dict:
    inst = state["instance"]
    llm = get_llm(TEMPERATURE).with_structured_output(AgentTurn, method="function_calling")
    system = AGENT_SYSTEM_PROMPT.format(preamble=BRIEF_PREAMBLE)

    if state.get("draft") is None:
        user = _DRAFT_USER.format(
            table=render_table(inst["table"]),
            constraints=render_constraints(inst),
            instruction=inst["instruction"],
        )
    elif state.get("active_feedback"):
        d = state["draft"]
        user = _FEEDBACK_USER.format(title=d["title"], body=d["body"], feedback=state["active_feedback"])
    else:
        d = state["draft"]
        user = _SELF_REVISE_USER.format(title=d["title"], body=d["body"], critique=state.get("critique", ""))

    turn: AgentTurn = llm.invoke([("system", system), ("human", user)])
    return {
        **state,
        "draft": {"title": turn.title, "body": turn.body},
        "decision": turn.decision,
        "critique": turn.critique,
        "active_feedback": None,
        "turns": state.get("turns", 0) + 1,
    }


def _route(state: dict) -> str:
    inst = state["instance"]
    limit = MAX_AGENT_STEPS[inst["difficulty"]]
    rounds = inst.get("feedback_rounds", [])
    round_idx = state.get("round_idx", 0)
    decision = (state.get("decision") or "submit").lower()

    if decision == "submit":
        if round_idx < len(rounds):
            return "inject"  # deliver next feedback round
        return END
    # decision == revise
    if state.get("turns", 0) >= limit:
        return "overflow"
    return "turn"


def _inject(state: dict, config: RunnableConfig | None = None) -> dict:
    inst = state["instance"]
    round_idx = state.get("round_idx", 0)
    feedback = inst["feedback_rounds"][round_idx]
    return {**state, "active_feedback": feedback, "round_idx": round_idx + 1}


def _overflow(state: dict, config: RunnableConfig | None = None) -> dict:
    # Reached the self-revision cap while still wanting to revise; if feedback
    # rounds remain undelivered the run did not complete the task.
    inst = state["instance"]
    incomplete = state.get("round_idx", 0) < len(inst.get("feedback_rounds", []))
    return {**state, "iteration_overflow": True, "incomplete": incomplete}


def build_agent_graph():
    graph = StateGraph(dict)
    graph.add_node("turn", _turn)
    graph.add_node("inject", _inject)
    graph.add_node("overflow", _overflow)
    graph.set_entry_point("turn")
    graph.add_conditional_edges("turn", _route, {"turn": "turn", "inject": "inject", "overflow": "overflow", END: END})
    graph.add_edge("inject", "turn")
    graph.add_edge("overflow", END)
    return graph.compile()


_AGENT_GRAPH = build_agent_graph()


def run_agent(inst: dict, config: dict | None = None) -> dict:
    """Run the self-revision loop for one instance.

    Returns the final state dict, including ``draft``, ``turns``, and
    ``iteration_overflow``. The recursion limit is a safety net above the
    per-difficulty turn cap, which is the binding limit enforced in _route.
    """
    limit = MAX_AGENT_STEPS[inst["difficulty"]]
    cfg = dict(config or {})
    cfg["recursion_limit"] = 3 * limit + 5
    return _AGENT_GRAPH.invoke(
        {"instance": inst, "draft": None, "round_idx": 0, "turns": 0, "active_feedback": None},
        config=cfg,
    )
