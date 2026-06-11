"""Configuration for archetype B: Structured Data Retrieval and Transformation.

Single source of truth for archetype B: its dimensional profile, source
benchmark, tool whitelist, output schema, the structured query specification
used by the workflow, and the prompt templates for both paradigms.

Source: CRMArena structured querying (Huang et al., 2025). Task types adapted:
Handle Time Understanding, Transfer Count Understanding, Top Issue
Identification, Monthly Trend Analysis, Best Region Identification, Sales Volume
Understanding. Records are synthesized locally for reproducibility
(see experiments/seed_crm.py).
"""

from src.archetypes.b_structured_retrieval.schemas import (
    FilterSpec,
    JoinSpec,
    QueryAnswer,
    QuerySpec,
)
from src.core.llm import DEFAULT_TEMPERATURE
from src.core.tools.database import db_read, db_search

__all__ = [
    "DIMENSIONAL_PROFILE",
    "SOURCE_BENCHMARK",
    "TEMPERATURE",
    "TOOLS",
    "CRM_SCHEMA_DOC",
    "QueryAnswer",
    "FilterSpec",
    "JoinSpec",
    "QuerySpec",
    "PLAN_PROMPT",
    "AGENT_SYSTEM_PROMPT",
]

# ── TADF metadata ──

DIMENSIONAL_PROFILE = {
    "step_predictability": "high",
    "information_availability": "high",
    "output_ambiguity": "low",
    "error_consequence": "moderate",
}

SOURCE_BENCHMARK = "CRMArena (Huang et al., 2025)"
TEMPERATURE = DEFAULT_TEMPERATURE
TOOLS = [db_read, db_search]

CRM_SCHEMA_DOC = """CRM tables and columns:
- accounts(id, name, region, industry, type)
- contacts(id, account_id, name, email)
- agents(id, name, team, region)
- cases(id, account_id, agent_id, subject, issue_category, status, priority, created_at, closed_at, transfer_count)
- opportunities(id, account_id, owner_agent_id, name, amount, stage, created_at, close_date, is_won)
Notes: handle time of a case = closed_at minus created_at (only for status 'Closed'). Dates are ISO strings."""


# ── Prompts ──

PLAN_PROMPT = """You translate a natural-language CRM question into a structured QuerySpec.
Do not compute the answer. Only describe how to retrieve and aggregate the data.

{schema}

Rules (about how to use the QuerySpec format, not about the domain):
- Choose base_table as the table that holds the rows to aggregate.
- Use joins to bring in parent attributes needed for filtering or grouping. Joined columns are referenced with the prefix, e.g. join agents with prefix 'agent_' then filter 'agent_team'.
- Use derive for computed columns: handle_time_hours (cases), created_year/created_month, close_year/close_quarter/close_month (opportunities), closed_year (cases).
- For "which X has the highest/most Y" questions, use operation 'argmax_group' with group_by = X and group_metric over target_column (count for "most", sum/avg for totals/averages).

Question: {question}"""

AGENT_SYSTEM_PROMPT = """You are a CRM data analyst. Answer the user's question by querying the CRM database with the available tools.

{schema}

Use db_read to fetch rows (optionally with exact-match filters) and db_search for substring matches. Read the tables you need, compute the answer yourself from the returned rows, and give the final answer as a single value: a number (rounded as the question requests) or an entity name (region, team, issue_category, or month number). State only the value."""
