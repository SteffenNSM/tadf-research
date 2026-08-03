"""Map-form workflow (B1 confirmation) for the v2.x Decision Sheet — IT-069.

Pre-registered confirmation sweep for build rule B1 / task-fit criterion T4
("heterogeneous item-specific arguments"). The final grid measured the
SINGLE-PLAN two-stage workflow at 2/5 on f-med-3 (nine updates, each with its
own owner and note) versus the agent's 5/5, while sixteen IDENTICAL updates
(f-med-4) scored 5/5 for both — the ceiling is per-item argument variety in
ONE combined plan object, not volume. Build rule B1 claims a workflow escape:
bind each item's arguments in its OWN small LLM call (a map step) and dispatch
deterministically. That escape is so far DERIVED (analogous per-item batch
triage measured 15/15); this module makes it measurable on exactly the
failing instances.

Paradigm definition of the form. Still an LLM workflow by thesis §2.2: the
graph is fixed at build time, every LLM call sits at a predetermined position
in a bounded, data-driven fan-out (the map), and no LLM decides control flow.
The read stage is imported UNCHANGED from the canonical workflow; both
canonical forms remain untouched (frozen artifact state, family-S precedent).

Graph topology (2 + N LLM calls, N = number of items, capped):
    [plan_reads] -> [execute_reads] -> [plan_items] -> [map_execute] -> END
where map_execute deterministically iterates the item list and, per item,
makes ONE small structured call (an ActionPlan for that item alone — tiny
schema load, per build rule B3) and dispatches its actions immediately.

Pre-registered hypotheses and decision rule (IT-069):
- H1: the map form recovers f-med-3 at the reference tier (>= 4/5 across the
  two reference runs).
- H2: the control f-med-4 stays perfect (no regression from mapping).
- Decision rule for criterion T4 (fixed BEFORE the sweep): reference-tier map
  parity with the agent -> drop T4 from the scoring, keep B1 as a build rule;
  partial recovery (2-3/5) -> T4 stays with Workflow 2 / Agent 3;
  still weak (<= 1/5) -> T4 stays with Workflow 1 / Agent 3.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.archetypes.f_action_execution.config import (
    CRM_SCHEMA_DOC,
    TEMPERATURE,
    TOOL_DISPATCH,
)
from src.archetypes.f_action_execution.schemas import ActionPlan, ActionResult
from src.archetypes.f_action_execution.workflow import (
    _format_read_results,
    execute_reads,
    plan_reads,
)
from src.core.llm import get_llm

#: Bound on the data-driven fan-out (build rule B5 territory; the tested
#: batches hold at most 16 items — the cap only guards degenerate item lists).
MAX_ITEMS = 40


class ItemList(BaseModel):
    """The homogeneous item inventory of a bulk task (map keys only).

    Deliberately flat (build rule B3): one short string per item, no nested
    arguments — per-item argument binding happens in the per-item calls.
    """

    rationale: str = Field(description="One sentence stating what the items are")
    items: list[str] = Field(
        description=(
            "One entry per item of the bulk operation, each the item's key "
            "exactly as the task names it (e.g. an account name or case id). "
            "No argument values here — only the keys."
        )
    )


PLAN_ITEMS_PROMPT = """You are inventorying the items of a bulk workplace task. A deterministic runner will later handle each item separately; you only list WHICH items exist.

{schema}

You have already run a set of read-only lookups. Their results are shown below.

Read results:
{read_results}

Produce an ItemList: one entry per item that the task operates on, using the item's key exactly as the task or the read results name it (account name, case id, ...). Do not include argument values, owners, notes, or wording — only the item keys, in the task's order. If the task operates on a single item, return that single key.

Task: {instruction}"""


PLAN_ITEM_ACTIONS_PROMPT = """You are planning the actions for exactly ONE item of a bulk workplace task. Other items are handled separately; plan ONLY this item's actions.

{schema}

You have already run a set of read-only lookups. Their results are shown below. Use the concrete ids and field values from those results.

Read results:
{read_results}

Current item: {item}

Produce an ActionPlan containing ONLY the state-changing actions for this one item, with the exact tool names and argument keys documented above. Take this item's specific values (owner, note, fields, wording) from the task text. db_update updates one row at a time by record_id (args: table, record_id, updates); it does not accept filters. Do not plan actions for any other item.

Task: {instruction}"""


def plan_items(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 3: produce the ItemList (LLM call 2 — homogeneous keys only)."""
    llm = get_llm(TEMPERATURE).with_structured_output(ItemList, method="function_calling")
    inventory: ItemList = llm.invoke(
        PLAN_ITEMS_PROMPT.format(
            schema=CRM_SCHEMA_DOC,
            instruction=state["instruction"],
            read_results=_format_read_results(state.get("read_results", [])),
        ),
        config=config,
    )
    return {**state, "item_list": inventory.model_dump()}


def map_execute(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 4: per item, ONE small plan call, then deterministic dispatch."""
    inventory = ItemList(**state["item_list"])
    read_results = _format_read_results(state.get("read_results", []))
    llm = get_llm(TEMPERATURE).with_structured_output(ActionPlan, method="function_calling")
    executed: list[dict] = []
    for item in inventory.items[:MAX_ITEMS]:
        try:
            plan: ActionPlan = llm.invoke(
                PLAN_ITEM_ACTIONS_PROMPT.format(
                    schema=CRM_SCHEMA_DOC,
                    instruction=state["instruction"],
                    read_results=read_results,
                    item=item,
                ),
                config=config,
            )
        except Exception as exc:  # noqa: BLE001
            executed.append({"item": item, "error": f"plan: {str(exc)[:200]}"})
            continue
        for action in plan.actions:
            tool = TOOL_DISPATCH.get(action.tool)
            if tool is None:
                executed.append({"item": item, "tool": action.tool, "error": "unknown tool"})
                continue
            try:
                result = tool.invoke(action.args, config=config)
                executed.append(
                    {"item": item, "tool": action.tool, "args": action.args, "result": result}
                )
            except Exception as exc:  # noqa: BLE001
                executed.append(
                    {"item": item, "tool": action.tool, "args": action.args,
                     "error": str(exc)[:200]}
                )

    any_failed = any("error" in r for r in executed)
    summary = (
        f"Map workflow processed {len(inventory.items[:MAX_ITEMS])} items, "
        f"{len(executed)} actions" + (" with failures" if any_failed else "")
    )
    result = ActionResult(success=not any_failed, summary=summary, executed_actions=executed)
    return {**state, "output": result.model_dump(), "completed": True}


def build_map_workflow():
    """Construct and compile the B1 map-form workflow."""
    graph = StateGraph(dict)
    graph.add_node("plan_reads", plan_reads)
    graph.add_node("execute_reads", execute_reads)
    graph.add_node("plan_items", plan_items)
    graph.add_node("map_execute", map_execute)
    graph.set_entry_point("plan_reads")
    graph.add_edge("plan_reads", "execute_reads")
    graph.add_edge("execute_reads", "plan_items")
    graph.add_edge("plan_items", "map_execute")
    graph.add_edge("map_execute", END)
    return graph.compile()


map_workflow = build_map_workflow()
