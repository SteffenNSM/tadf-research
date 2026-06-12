"""Workflow implementation for archetype G: Strategic and Adaptive Planning.

Two-stage canonical workflow in the IT-014 fetch-then-act form: the read
stage gathers the ids, transfer counts, owners, and addresses the plan
needs; the planning stage produces the full action plan against the
observed values in a single structured-output call. Nothing is executed —
the plan is the deliverable and is scored by the simulator.

Graph topology:
    [plan_reads] -> [execute_reads] -> [generate_plan] -> END

Two LLM calls in total. The agent paradigm may instead interleave reads
and reasoning across ReAct turns; that flexibility (and its token cost) is
the paradigm contrast under measurement.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.g_strategic_planning.config import (
    ACTION_SET_DOC,
    GENERATE_PLAN_PROMPT,
    PLAN_READS_PROMPT,
    TEMPERATURE,
)
from src.archetypes.g_strategic_planning.schemas import GReadPlan, Plan
from src.core.llm import get_llm
from src.core.tools.database import db_read, db_search

_READ_DISPATCH = {"db_read": db_read, "db_search": db_search}


def plan_reads(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 1: produce the GReadPlan (LLM call 1)."""
    llm = get_llm(TEMPERATURE).with_structured_output(GReadPlan, method="function_calling")
    plan: GReadPlan = llm.invoke(
        PLAN_READS_PROMPT.format(action_doc=ACTION_SET_DOC, instruction=state["instruction"])
    )
    return {**state, "read_plan": plan.model_dump()}


def execute_reads(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 2: dispatch each planned read deterministically."""
    plan = GReadPlan(**state["read_plan"])
    results: list[dict] = []
    for read in plan.reads:
        tool = _READ_DISPATCH.get(read.tool)
        if tool is None:
            results.append({"tool": read.tool, "args": read.args, "error": "unknown tool"})
            continue
        try:
            rows = tool.invoke(read.args, config=config)
            results.append({"tool": read.tool, "args": read.args, "result": rows})
        except Exception as exc:  # noqa: BLE001
            results.append({"tool": read.tool, "args": read.args, "error": str(exc)[:200]})
    return {**state, "read_results": results}


def _format_read_results(results: list[dict]) -> str:
    if not results:
        return "(no reads were executed)"
    blocks = []
    for r in results:
        body = r.get("result", r.get("error", ""))
        blocks.append(f"[{r['tool']}({r['args']})]\n{body}")
    return "\n\n".join(blocks)


def generate_plan(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 3: produce the Plan informed by the read results (LLM call 2)."""
    llm = get_llm(TEMPERATURE).with_structured_output(Plan, method="function_calling")
    plan: Plan = llm.invoke(
        GENERATE_PLAN_PROMPT.format(
            action_doc=ACTION_SET_DOC,
            instruction=state["instruction"],
            read_results=_format_read_results(state.get("read_results", [])),
        )
    )
    return {**state, "output": plan.model_dump(), "completed": True}


def build_workflow():
    """Construct and compile the archetype G workflow."""
    graph = StateGraph(dict)
    graph.add_node("plan_reads", plan_reads)
    graph.add_node("execute_reads", execute_reads)
    graph.add_node("generate_plan", generate_plan)
    graph.set_entry_point("plan_reads")
    graph.add_edge("plan_reads", "execute_reads")
    graph.add_edge("execute_reads", "generate_plan")
    graph.add_edge("generate_plan", END)
    return graph.compile()


workflow = build_workflow()
