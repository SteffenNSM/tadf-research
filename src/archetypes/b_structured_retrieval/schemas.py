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


# ── Multi-source plan (difficulty axis = number of sources to combine) ──


class CrmSource(BaseModel):
    """The CRM structured input to a multi-source plan."""

    table: Literal["accounts", "contacts", "agents", "cases", "opportunities"] = Field(
        description="CRM table holding the rows to filter/aggregate"
    )
    filters: list[FilterSpec] = Field(
        default_factory=list, description="Exact/comparison filters, combined with AND"
    )
    key_column: str | None = Field(
        default=None,
        description="Join key used to intersect with Mail/Calendar, e.g. 'name' for opportunities. Required when mail or calendar is set.",
    )
    value_column: str | None = Field(
        default=None, description="Column to sum when operation == 'sum', e.g. 'amount'"
    )


class MailSource(BaseModel):
    """A Mail-derived key set: opportunities named in matching emails."""

    query: str = Field(description="Subject/body substring identifying the emails, e.g. 'Contract countersigned'")
    extract: Literal["opportunity"] = Field(
        default="opportunity", description="Entity to extract from the email text ('Opportunity NNN')"
    )


class CalendarSource(BaseModel):
    """A Calendar-derived key set: opportunities named in matching events."""

    query: str = Field(description="Event-name substring identifying the events, e.g. 'Closing call'")
    extract: Literal["opportunity"] = Field(
        default="opportunity", description="Entity to extract from the event name ('Opportunity NNN')"
    )


class MultiSourcePlan(BaseModel):
    """A declarative multi-source retrieval plan produced by the plan node.

    When only ``crm`` is set, the operation is applied to the filtered CRM rows
    directly (single source). When ``mail`` and/or ``calendar`` are also set,
    the answer is computed over the INTERSECTION of the per-source key sets
    (sweep-all), keyed by ``crm.key_column``.
    """

    crm: CrmSource = Field(description="The CRM source (always present)")
    mail: MailSource | None = Field(default=None, description="Optional Mail source to intersect")
    calendar: CalendarSource | None = Field(default=None, description="Optional Calendar source to intersect")
    operation: Literal["count", "sum"] = Field(description="Final aggregation over the combined set")
