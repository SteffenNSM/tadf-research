"""Pure data models for archetype F: Transactional Action Execution.

Separated from ``config.py`` so the structured outputs carry no framework
dependencies and can be unit-tested with pydantic alone. The workflow's
``plan_actions`` node emits an ``ActionPlan``; the deterministic
``execute_actions`` node consumes it and returns an ``ActionResult``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

#: Tools the workflow's read-planner may select. Read-only operations.
READ_TOOLS = Literal[
    "db_read",
    "db_search",
    "search_emails",
    "search_events",
]

#: Tools the workflow's action-planner may select. Full toolset; reads are
#: also allowed in case a confirmation lookup is needed after the read stage.
ACTION_TOOLS = Literal[
    "send_email",
    "search_emails",
    "forward_email",
    "delete_email",
    "create_event",
    "search_events",
    "update_event",
    "delete_event",
    "db_read",
    "db_search",
    "db_update",
    "attempt_close_case",
]


class ReadAction(BaseModel):
    """A single read-only tool invocation in the read stage."""

    tool: READ_TOOLS = Field(description="Name of the read-only tool to invoke")
    args: dict[
        str,
        str | int | float | bool | list[str] | dict[str, str | int | float | bool],
    ] = Field(
        description="Keyword arguments for the tool. Use only the documented arguments for that tool."
    )
    rationale: str = Field(
        description="One short sentence describing what this read fetches"
    )


class ReadPlan(BaseModel):
    """The set of read-only calls the workflow runs in stage one.

    The reads gather the identifiers and fields the action planner needs to
    produce a correct ActionPlan in stage two. The read planner does not yet
    see any tool results; the action planner sees the read outputs.
    """

    rationale: str = Field(description="One sentence stating what these reads will reveal")
    reads: list[ReadAction] = Field(
        description="Ordered list of read-only tool invocations to run before the action planner is called"
    )


class Action(BaseModel):
    """A single tool invocation in the planned action sequence."""

    tool: ACTION_TOOLS = Field(description="Name of the tool to invoke")
    args: dict[
        str,
        str | int | float | bool | list[str] | dict[str, str | int | float | bool],
    ] = Field(
        description="Keyword arguments for the tool. Use only the documented arguments for that tool. Some tools take a nested dict (for example db_update.updates and db_read.filters); for those, pass the inner mapping with primitive values."
    )
    rationale: str = Field(
        description="One short sentence describing what this action accomplishes (use an empty string if not applicable)"
    )


class ActionPlan(BaseModel):
    """The full sequence of actions the workflow will execute, in order."""

    rationale: str = Field(
        description="One sentence stating how this plan answers the request"
    )
    actions: list[Action] = Field(
        description="Ordered list of tool invocations. Read actions (db_read, db_search, search_emails, search_events) appear before any state-changing actions that depend on what they return."
    )


class ActionResult(BaseModel):
    """The final outcome reported by the workflow or agent."""

    success: bool = Field(description="True if the task is reported as completed")
    summary: str = Field(description="One-sentence human-readable summary of what was done")
    executed_actions: list[dict] = Field(
        default_factory=list,
        description="Per-action records: tool, args, and the tool's return value or error",
    )
