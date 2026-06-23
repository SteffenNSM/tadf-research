"""Configuration for archetype B: Structured Data Retrieval and Transformation.

Multi-source operationalization (difficulty axis = number of distinct sources
that must be combined, sweep-all / plan-time-decidable):
    Low  = 1 source  (CRM only)
    Med  = 2 sources (CRM + Mail, or CRM + Calendar)
    High = 3 sources (CRM + Mail + Calendar)

The workflow keeps the LLM confined to translation (NL -> MultiSourcePlan); the
deterministic executor performs retrieval, the cross-source intersection, and
the aggregation. The agent receives the same read tools and integrates the
sources in-context. Tool inventory is identical across paradigms (protocol A.3).

Source: CRMArena structured querying (Huang et al., 2025) for the CRM source;
WorkBench mailbox/calendar (Styles et al., 2024) for the Mail/Calendar sources.
Records are synthesized locally (experiments/seed_crm.py, seed_b_multisource.py).
"""

from src.archetypes.b_structured_retrieval.schemas import (
    CalendarSource,
    CrmSource,
    FilterSpec,
    MailSource,
    MultiSourcePlan,
    QueryAnswer,
)
from src.core.llm import DEFAULT_TEMPERATURE
from src.core.tools.calendar import search_events
from src.core.tools.database import db_read, db_search
from src.core.tools.mail import search_emails

__all__ = [
    "DIMENSIONAL_PROFILE",
    "SOURCE_BENCHMARK",
    "TEMPERATURE",
    "TOOLS",
    "SOURCE_SCHEMA_DOC",
    "QueryAnswer",
    "FilterSpec",
    "CrmSource",
    "MailSource",
    "CalendarSource",
    "MultiSourcePlan",
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

SOURCE_BENCHMARK = "CRMArena (Huang et al., 2025) + WorkBench (Styles et al., 2024)"
TEMPERATURE = DEFAULT_TEMPERATURE
# Identical read-tool inventory for both paradigms (A.3). CRM via db_read/db_search;
# Mail via search_emails; Calendar via search_events.
TOOLS = [db_read, db_search, search_emails, search_events]

SOURCE_SCHEMA_DOC = """Data sources:

CRM tables (read via db_read / db_search):
- accounts(id, name, region, industry, type)
- contacts(id, account_id, name, email)
- agents(id, name, team, region, email)
- cases(id, account_id, agent_id, subject, issue_category, status, priority, created_at, closed_at, transfer_count)
- opportunities(id, account_id, owner_agent_id, name, amount, stage, created_at, close_date, is_won)

Mail (read via search_emails(query)): emails carry cross-references in their body.
- An email with subject 'Contract countersigned' names the opportunity its contract was signed for ('Opportunity NNN').
- An email with subject 'Payment received' names the opportunity a payment was received for ('Opportunity NNN').

Calendar (read via search_events(query)): events carry the reference in the event name.
- An event named 'Closing call: Opportunity NNN' marks a closing call for that opportunity.
- An event named 'Kickoff scheduled: Opportunity NNN' marks a kickoff for that opportunity.

Notes: handle time of a case = closed_at minus created_at (status 'Closed'). Dates are ISO strings.
Opportunities are referenced across sources by their name in the form 'Opportunity NNN'."""


# ── Prompts ──

PLAN_PROMPT = """You translate a natural-language question into a structured MultiSourcePlan.
Do not compute the answer. Only describe which sources to read and how to combine them.

{schema}

Rules (about the MultiSourcePlan format, not the domain):
- Always set `crm` to the CRM source: its `table`, any `filters` (e.g. is_won = 1), and `value_column` = 'amount' when the operation is 'sum'.
- If the question requires a fact from the mailbox, set `mail.query` to the subject that identifies those emails (e.g. 'Contract countersigned' or 'Payment received').
- If the question requires a fact from the calendar, set `calendar.query` to the event-name prefix that identifies those events (e.g. 'Closing call' or 'Kickoff scheduled').
- When `mail` or `calendar` is set, the answer is the INTERSECTION of the sources keyed on opportunities; set `crm.key_column` = 'name' so CRM opportunities match the 'Opportunity NNN' references in Mail/Calendar.
- Set `operation` to 'count' for "how many" questions and 'sum' for total-amount questions.

Question: {question}"""

AGENT_SYSTEM_PROMPT = """You are a CRM data analyst. Answer the user's question by reading the available sources with the tools.

{schema}

Use db_read/db_search for the CRM tables, search_emails(query=...) for the mailbox, and search_events(query=...) for the calendar. When a question combines sources (for example, won opportunities that were also countersigned by email and have a closing-call event), read each source, extract the referenced opportunities ('Opportunity NNN'), intersect them, and compute the answer yourself. Give the final answer as a single value: a number (rounded as the question requests) or an entity name. State only the value."""
