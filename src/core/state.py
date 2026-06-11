"""Typed state shared across archetype graphs.

Both the workflow and the agent implementation of every archetype read from
and write to the same state structure, so that data flow is comparable across
paradigms. Archetype-specific data is carried in ``payload``, ``scratch``, and
``output`` to keep the shared schema stable across all eight archetypes, while
the fixed fields capture the elements required by the task definition
(Section 2.2.3): an input, a delimitable output, and the execution mode.
"""

from typing import Any

from pydantic import BaseModel, Field


class TaskState(BaseModel):
    """Generic task state for a single archetype execution."""

    # ── Input: from a preceding step or external source ──
    input_id: str = Field(description="Identifier of the input record or task instance")
    instruction: str = Field(default="", description="Natural-language task instruction")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Archetype-specific input data"
    )

    # ── Processing: intermediate working memory ──
    scratch: dict[str, Any] = Field(
        default_factory=dict, description="Intermediate working data between steps"
    )

    # ── Output: passed to a subsequent step or the coordination layer ──
    output: dict[str, Any] = Field(
        default_factory=dict, description="Archetype-specific structured output"
    )
    completed: bool = Field(
        default=False, description="Whether the task reached its terminal state"
    )

    # ── Execution metadata ──
    run_id: str | None = Field(default=None, description="Experiment run identifier")
    paradigm: str | None = Field(
        default=None, description="Execution paradigm: 'workflow' or 'agent'"
    )
    error: str | None = Field(
        default=None, description="Terminal error message, if the task failed"
    )
