"""Pure data models for archetype B.

Separated from ``config.py`` so the query specification and output schema carry
no framework dependencies and can be unit-tested with pydantic alone. The
deterministic executor and the ground-truth evaluator depend only on this
module; the workflow and agent depend on ``config.py``.
"""

from typing import Literal

from pydantic import BaseModel, Field


class QueryAnswer(BaseModel):
    """The structured answer to a CRM querying task."""

    value: str = Field(description="The computed answer as a string (a number or an entity name)")
    unit: str = Field(default="", description="Unit or entity type, e.g. 'count', 'currency', 'region'")


class FilterSpec(BaseModel):
    """A single filter condition on a base, joined, or derived column."""

    column: str = Field(description="Column to filter on (joined columns are prefixed, e.g. 'agent_team')")
    op: Literal["eq", "ne", "gt", "lt", "ge", "le"] = Field(description="Comparison operator")
    value: str | int | float | bool = Field(description="Value to compare against")


class JoinSpec(BaseModel):
    """An in-memory join that enriches base rows with parent attributes."""

    table: str = Field(description="Parent table to join, e.g. 'agents' or 'accounts'")
    local_key: str = Field(description="Foreign-key column on the base row, e.g. 'agent_id'")
    foreign_key: str = Field(default="id", description="Key column on the parent table")
    prefix: str = Field(description="Prefix for joined columns, e.g. 'agent_' or 'account_'")


class QuerySpec(BaseModel):
    """A declarative specification of a CRM query, produced by the plan node."""

    base_table: str = Field(description="The table to query over")
    joins: list[JoinSpec] = Field(default_factory=list, description="Parent joins for filtering or grouping")
    derive: list[str] = Field(
        default_factory=list,
        description="Computed columns: handle_time_hours, created_year, created_month, close_year, close_quarter, close_month, closed_year",
    )
    filters: list[FilterSpec] = Field(default_factory=list, description="Filter conditions, combined with AND")
    operation: Literal["count", "sum", "avg", "min", "max", "argmax_group"] = Field(
        description="Aggregation to apply over the filtered rows"
    )
    target_column: str | None = Field(
        default=None, description="Column to aggregate for sum/avg/min/max and within argmax_group"
    )
    group_by: str | None = Field(default=None, description="Grouping column for argmax_group")
    group_metric: Literal["count", "sum", "avg"] | None = Field(
        default=None, description="Per-group metric for argmax_group"
    )
