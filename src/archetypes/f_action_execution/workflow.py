"""Workflow implementation for archetype F: Transactional Action Execution.

Two-stage canonical workflow: the read stage gathers the identifiers and
field values that the action stage needs, then the action stage plans and
executes the state-changing operations with concrete arguments. Both
LLM-driven stages are bracketed by deterministic executors so the LLM never
performs the aggregation or the dispatch.

Graph topology:
    [plan_reads] -> [execute_reads] -> [plan_actions] -> [execute_actions] -> END

The architecture mirrors archetype A (plan_searches -> execute_searches ->
synthesize) so both archetypes follow the same workflow-paradigm pattern of
"plan the lookups, see the data, plan the output". Two LLM calls in total.
The agent paradigm remains free to interleave reads and actions, observe each
tool result, and recover from a failed call by retrying with different
arguments.

Failed actions are recorded and the plan continues. The workflow cannot
re-plan after observing an action failure; that flexibility is the defining
property of the agent paradigm for this archetype.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.f_action_execution.config import (
    CRM_SCHEMA_DOC,
    PLAN_ACTIONS_PROMPT,
    PLAN_READS_PROMPT,
    TEMPERATURE,
    TOOL_DISPATCH,
)
from src.archetypes.f_action_execution.schemas import (
    ActionPlan,
    ActionResult,
    ReadPlan,
)
from src.core.llm import get_llm


def plan_reads(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 1: produce the ReadPlan (the first LLM call)."""
    llm = get_llm(TEMPERATURE).with_structured_output(
        ReadPlan, method="function_calling"
    )
    plan: ReadPlan = llm.invoke(
        PLAN_READS_PROMPT.format(schema=CRM_SCHEMA_DOC, instruction=state["instruction"])
    )
    return {**state, "read_plan": plan.model_dump()}


def execute_reads(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 2: dispatch each planned read to its tool, deterministically."""
    plan = ReadPlan(**state["read_plan"])
    results: list[dict] = []
    for read in plan.reads:
        tool = TOOL_DISPATCH.get(read.tool)
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
    """Compact textual rendering of read outputs for the action prompt."""
    if not results:
        return "(no reads were executed)"
    blocks: list[str] = []
    for r in results:
        header = f"[{r['tool']}({r['args']})]"
        body = r.get("result", r.get("error", ""))
        blocks.append(f"{header}\n{body}")
    return "\n\n".join(blocks)


def plan_actions(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 3: produce the ActionPlan informed by the read results (LLM call 2)."""
    llm = get_llm(TEMPERATURE).with_structured_output(
        ActionPlan, method="function_calling"
    )
    plan: ActionPlan = llm.invoke(
        PLAN_ACTIONS_PROMPT.format(
            schema=CRM_SCHEMA_DOC,
            instruction=state["instruction"],
            read_results=_format_read_results(state.get("read_results", [])),
        )
    )
    return {**state, "action_plan": plan.model_dump()}


def execute_actions(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 4: dispatch each planned action to its tool, deterministically."""
    plan = ActionPlan(**state["action_plan"])
    executed: list[dict] = []
    for action in plan.actions:
        tool = TOOL_DISPATCH.get(action.tool)
        if tool is None:
            executed.append({"tool": action.tool, "args": action.args, "error": "unknown tool"})
            continue
        try:
            result = tool.invoke(action.args, config=config)
            executed.append({"tool": action.tool, "args": action.args, "result": result})
        except Exception as exc:  # noqa: BLE001
            executed.append({"tool": action.tool, "args": action.args, "error": str(exc)[:200]})

    any_failed = any("error" in r for r in executed)
    summary = f"Executed {len(executed)} actions" + (" with failures" if any_failed else "")
    result = ActionResult(success=not any_failed, summary=summary, executed_actions=executed)
    return {**state, "output": result.model_dump(), "completed": True}


def build_workflow():
    """Construct and compile the archetype F workflow."""
    graph = StateGraph(dict)
    graph.add_node("plan_reads", plan_reads)
    graph.add_node("execute_reads", execute_reads)
    graph.add_node("plan_actions", plan_actions)
    graph.add_node("execute_actions", execute_actions)
    graph.set_entry_point("plan_reads")
    graph.add_edge("plan_reads", "execute_reads")
    graph.add_edge("execute_reads", "plan_actions")
    graph.add_edge("plan_actions", "execute_actions")
    graph.add_edge("execute_actions", END)
    return graph.compile()


workflow = build_workflow()
