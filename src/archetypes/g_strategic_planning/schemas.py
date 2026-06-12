"""Pure data models for archetype G: Strategic and Adaptive Planning.

The deliverable of a G task is a **plan**: an ordered sequence of concrete,
argument-complete action steps that, if executed against the current CRM
state, would reach the stated goal. Nothing is executed — the plan is scored
by the deterministic simulator (``simulator.py``), which checks every step's
preconditions and then evaluates the instance's declarative goal spec
against the simulated final state. This operationalizes the F/G boundary of
Sections 4.2.2/4.2.5: tasks whose output is a state change belong to F;
tasks whose output is a plan consumed downstream belong to G.

The plannable action set is the state-changing subset of the F tool
inventory. Read tools (``db_read``, ``db_search``) are NOT plan steps; reads
happen before planning (workflow: ``plan_reads`` stage; agent: ReAct turns).

Source: PlanBench (Valmeekam et al., 2023) — mechanical plan validation,
plan-length difficulty axis, temperature 0; FlowBench plan-generation
variant (Xiao et al., 2024); WorkArena L2 compositional tasks (Drouin et
al., 2024). Scenarios are author-constructed over the local CRM seed
(IT-017 honesty rule); the validator replaces PlanBench's VAL because the
domain is the CRM workspace rather than PDDL (deviation D-012).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

#: Actions a plan step may use. State-changing subset of the F inventory.
PLAN_ACTION = Literal[
    "db_update",
    "attempt_close_case",
    "send_email",
    "create_event",
]

#: Read tools available before planning (identical for both paradigms).
G_READ_TOOL = Literal["db_read", "db_search"]


class GRead(BaseModel):
    """One read-only lookup planned before the action plan is produced."""

    tool: G_READ_TOOL = Field(description="The read tool to invoke")
    args: dict[str, Any] = Field(
        description=(
            "Arguments for the read tool, e.g. "
            "{'table': 'cases', 'filters': {'status': 'Open', 'agent_id': 5}}"
        )
    )


class GReadPlan(BaseModel):
    """Ordered list of reads that gather the state the plan needs."""

    reads: list[GRead] = Field(
        description=(
            "Read-only lookups, in order. Empty if the task statement "
            "already contains every value needed to plan."
        )
    )


class PlanStep(BaseModel):
    """One concrete, argument-complete action in the plan."""

    tool: PLAN_ACTION = Field(description="The action to perform at this step")
    args: dict[str, Any] = Field(
        description=(
            "Exact arguments for the action with concrete ids and values "
            "taken from the read results — no placeholders. Argument keys "
            "must match the action documentation exactly."
        )
    )


class Plan(BaseModel):
    """The final deliverable: an ordered action sequence plus rationale."""

    steps: list[PlanStep] = Field(
        description="The ordered action sequence that reaches the goal when executed"
    )
    rationale: str = Field(
        description=(
            "Two or three sentences: which preconditions and ordering "
            "constraints shaped the plan"
        )
    )
