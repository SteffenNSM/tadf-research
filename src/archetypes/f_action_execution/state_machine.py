"""State-machine workflow (third execution form) for Phase 2b family S.

Family S ("Staged Adaptivity", IT-066) tests how far adaptive behavior can be
moved into COMPILED control flow: branching on runtime tool outcomes without
an LLM in the control-flow loop. This module adds the third execution form
next to the canonical two-stage workflow (``workflow.py``) and the ReAct agent
(``agent.py``); both canonical forms remain UNTOUCHED (frozen artifact state).

Paradigm definition of the form. All LLM involvement stays at PLAN TIME: the
planner produces a ``StagedActionPlan`` that enumerates, for every
transactional step, a branch per enumerated outcome category of
``attempt_close_case`` (success / refused / already_closed) with the
follow-up actions of that branch fully specified in advance. At RUN TIME the
deterministic executor classifies each tool response on its STRUCTURED fields
and selects the pre-built branch -- no LLM call, no free interpretation.
Control flow is therefore resolved by a compiled finite-state machine whose
states are (step index, outcome) and whose transition table is the plan; this
is exactly equivalent to LangGraph conditional edges compiled per step, and is
implemented -- like the canonical ``execute_actions`` loop -- inside a single
deterministic node so the run-record format stays identical across forms.

Two deliberately bounded runtime capabilities, documented as the form's
integration contract (IT-066 design decisions):

1. **Template substitution.** Branch-action string arguments may carry the
   placeholders ``{case_id}`` and ``{reason}``; the executor substitutes them
   deterministically from the CURRENT step's structured tool response. No
   other runtime value enters an action. (Extending the placeholder
   vocabulary is possible per deployment, but every aggregate placeholder is
   bespoke executor logic; the family measures the ceiling of the bounded
   vocabulary, mirroring the bounded/unbounded variety split of row 3.1.)
2. **Default stop.** If a runtime outcome has no planned branch, the executor
   records it and STOPS the batch (no improvised action). Uncovered outcomes
   are the agent's domain; a state machine must fail safely.

Graph topology (two LLM calls, identical count to the canonical workflow):
    [plan_reads] -> [execute_reads] -> [plan_staged_actions]
        -> [execute_state_machine] -> END

The read stage is imported unchanged from the canonical workflow so the two
workflow forms differ only in the action stage.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.archetypes.f_action_execution.config import (
    CRM_SCHEMA_DOC,
    TEMPERATURE,
    TOOL_DISPATCH,
)
from src.archetypes.f_action_execution.schemas import ACTION_TOOLS, ActionResult
from src.archetypes.f_action_execution.workflow import (
    _format_read_results,
    execute_reads,
    plan_reads,
)
from src.core.llm import get_llm

#: Hard iteration cap for the step loop (bounded depth is the property that
#: separates the compiled state machine from the open agent loop). Family-S
#: batches hold at most 5 steps; the cap only guards against degenerate plans.
MAX_STEPS = 12

#: The enumerated outcome categories of ``attempt_close_case``, classified
#: from the tool's structured response fields (see ``classify_close_response``).
SM_OUTCOMES = Literal["success", "refused", "already_closed"]


# ── Plan schema (state-machine form) ──


class BranchAction(BaseModel):
    """A single pre-planned tool invocation inside a branch or action list."""

    tool: ACTION_TOOLS = Field(description="Name of the tool to invoke")
    args: dict[
        str,
        str | int | float | bool | list[str] | dict[str, str | int | float | bool],
    ] = Field(
        description=(
            "Keyword arguments for the tool. String values may contain the "
            "placeholders {case_id} and {reason}; they are replaced at run "
            "time with the current step's case id and the back-end's stated "
            "reason. Use only the documented arguments for that tool."
        )
    )
    rationale: str = Field(
        description="One short sentence describing what this action accomplishes"
    )


class OutcomeBranch(BaseModel):
    """The pre-planned response to ONE outcome category of a close step."""

    outcome: SM_OUTCOMES = Field(
        description="Which outcome of attempt_close_case this branch handles"
    )
    actions: list[BranchAction] = Field(
        description=(
            "Actions executed only when this outcome occurs, in order. May be "
            "empty when the runbook requires no follow-up for this outcome."
        )
    )
    then: Literal["continue", "stop_batch"] = Field(
        description=(
            "'continue' proceeds to the next step; 'stop_batch' ends the step "
            "loop after this branch's actions (remaining steps are skipped)."
        )
    )


class CloseStep(BaseModel):
    """One transactional close attempt with its full branch table."""

    case_id: int = Field(description="The case to attempt to close in this step")
    resolution_summary: str = Field(
        description="Resolution text passed to attempt_close_case"
    )
    branches: list[OutcomeBranch] = Field(
        description=(
            "One branch per outcome category that the runbook covers. An "
            "outcome without a branch stops the batch (default stop)."
        )
    )


class StagedActionPlan(BaseModel):
    """The complete compiled control-flow plan of the state-machine form."""

    rationale: str = Field(
        description="One sentence stating how this plan answers the request"
    )
    pre_actions: list[BranchAction] = Field(
        description="Unconditional actions executed before the step loop (often empty)"
    )
    steps: list[CloseStep] = Field(
        description="Ordered transactional steps; the executor runs them first to last"
    )
    post_actions: list[BranchAction] = Field(
        description=(
            "Unconditional actions executed after the step loop ends (whether "
            "it completed or stopped). Placeholders are NOT substituted here; "
            "post-action arguments must be fully specified at plan time."
        )
    )


# ── Prompt ──

PLAN_STAGED_PROMPT = """You are planning the complete, branch-aware action program for a workplace task. A deterministic runner will execute it; you will NOT see any tool result and you cannot revise the plan at run time.

{schema}

You have already run a set of read-only lookups. Their results are shown below. Use the concrete ids and field values from those results.

Read results:
{read_results}

Produce a StagedActionPlan:
- `steps`: the ordered attempt_close_case calls. For EACH step, provide `branches` covering the outcome categories the runbook addresses. attempt_close_case reports exactly one of: `success` (the close went through), `refused` (the back-end blocked the close and states a reason), `already_closed` (the case was already closed).
- Each branch lists the follow-up actions for that outcome, fully specified in advance. In string arguments you may use the placeholders {{case_id}} (the current step's case id) and {{reason}} (the back-end's stated reason); the runner substitutes them mechanically. No other runtime information is available to the plan.
- `then` per branch: 'continue' to move to the next step, 'stop_batch' to end the step loop.
- `pre_actions` / `post_actions`: unconditional actions before / after the step loop. Post-actions run whether the loop completed or stopped early, and no placeholders are substituted in them.

Guidelines:
- Plan only what the task needs; do not pad the plan.
- Use exact tool names and argument keys as documented in the schema above. db_update updates one row at a time by record_id (args: table, record_id, updates); it does not accept filters. If multiple records need the same change, plan one action per record with the concrete record id.
- Include EVERY transactional target as its own step, in the required order; do not skip or merge steps.
- Actions that must happen exactly once per outcome of a step belong in that step's branch. Actions that must happen exactly once for the whole task -- for example a single completion report after the batch -- belong in `post_actions`, never inside per-step branches.
- If an outcome category is irrelevant per the runbook, you may omit its branch; an uncovered outcome stops the batch without action.

Task: {instruction}"""


# ── Deterministic runtime pieces ──


def classify_close_response(resp: object) -> str:
    """Deterministically classify an ``attempt_close_case`` response.

    Classification uses only the structured response fields, mirroring how a
    real integration would switch on a status code: ``closed=True`` maps to
    ``success``; the back-end's fixed already-closed message maps to
    ``already_closed``; every other non-success (manual-review escalation,
    unknown id) maps to ``refused``.
    """
    if isinstance(resp, dict):
        if resp.get("closed") is True:
            return "success"
        reason = str(resp.get("reason", ""))
    else:
        reason = str(resp)
    if reason.strip() == "case is already closed":
        return "already_closed"
    return "refused"


def _substitute(value: object, case_id: int, reason: str) -> object:
    """Recursively replace {case_id} / {reason} in string argument values."""
    if isinstance(value, str):
        return value.replace("{case_id}", str(case_id)).replace("{reason}", reason)
    if isinstance(value, dict):
        return {k: _substitute(v, case_id, reason) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, case_id, reason) for v in value]
    return value


def _dispatch(action: BranchAction, config: RunnableConfig | None) -> dict:
    """Invoke one planned action; never raises (records errors like the canonical executor)."""
    tool = TOOL_DISPATCH.get(action.tool)
    if tool is None:
        return {"tool": action.tool, "args": action.args, "error": "unknown tool"}
    try:
        result = tool.invoke(action.args, config=config)
        return {"tool": action.tool, "args": action.args, "result": result}
    except Exception as exc:  # noqa: BLE001
        return {"tool": action.tool, "args": action.args, "error": str(exc)[:200]}


# ── Graph nodes ──


def plan_staged_actions(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 3: produce the StagedActionPlan (LLM call 2)."""
    llm = get_llm(TEMPERATURE).with_structured_output(
        StagedActionPlan, method="function_calling"
    )
    plan: StagedActionPlan = llm.invoke(
        PLAN_STAGED_PROMPT.format(
            schema=CRM_SCHEMA_DOC,
            instruction=state["instruction"],
            read_results=_format_read_results(state.get("read_results", [])),
        )
    )
    return {**state, "staged_plan": plan.model_dump()}


def execute_state_machine(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 4: run the compiled finite-state machine, fully deterministically."""
    plan = StagedActionPlan(**state["staged_plan"])
    executed: list[dict] = []
    stopped_early = False
    uncovered: str | None = None

    for action in plan.pre_actions:
        executed.append(_dispatch(action, config))

    close_tool = TOOL_DISPATCH.get("attempt_close_case")
    for step in plan.steps[:MAX_STEPS]:
        resp = None
        try:
            resp = close_tool.invoke(
                {"case_id": step.case_id, "resolution_summary": step.resolution_summary},
                config=config,
            )
            executed.append({
                "tool": "attempt_close_case",
                "args": {"case_id": step.case_id},
                "result": resp,
            })
        except Exception as exc:  # noqa: BLE001
            executed.append({
                "tool": "attempt_close_case",
                "args": {"case_id": step.case_id},
                "error": str(exc)[:200],
            })
            stopped_early = True
            break

        outcome = classify_close_response(resp)
        reason = str(resp.get("reason", "")) if isinstance(resp, dict) else ""
        branch = next((b for b in step.branches if b.outcome == outcome), None)
        if branch is None:
            # Default stop (IT-066): an outcome the plan does not cover ends
            # the batch without improvised action -- fail-safe by design.
            uncovered = outcome
            executed.append({
                "state_machine": "uncovered_outcome",
                "step_case_id": step.case_id,
                "outcome": outcome,
            })
            stopped_early = True
            break

        for action in branch.actions:
            substituted = BranchAction(
                tool=action.tool,
                args=_substitute(action.args, step.case_id, reason),
                rationale=action.rationale,
            )
            executed.append(_dispatch(substituted, config))

        if branch.then == "stop_batch":
            stopped_early = True
            break

    for action in plan.post_actions:
        executed.append(_dispatch(action, config))

    any_failed = any("error" in r for r in executed)
    summary = (
        f"State machine executed {len(executed)} actions"
        + (" (batch stopped early)" if stopped_early else "")
        + (f" (uncovered outcome: {uncovered})" if uncovered else "")
        + (" with failures" if any_failed else "")
    )
    result = ActionResult(success=not any_failed, summary=summary, executed_actions=executed)
    return {**state, "output": result.model_dump(), "completed": True}


def build_state_machine():
    """Construct and compile the family-S state-machine workflow."""
    graph = StateGraph(dict)
    graph.add_node("plan_reads", plan_reads)
    graph.add_node("execute_reads", execute_reads)
    graph.add_node("plan_staged_actions", plan_staged_actions)
    graph.add_node("execute_state_machine", execute_state_machine)
    graph.set_entry_point("plan_reads")
    graph.add_edge("plan_reads", "execute_reads")
    graph.add_edge("execute_reads", "plan_staged_actions")
    graph.add_edge("plan_staged_actions", "execute_state_machine")
    graph.add_edge("execute_state_machine", END)
    return graph.compile()


state_machine = build_state_machine()
