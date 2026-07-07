"""Configuration for archetype B: Structured Data Retrieval and Transformation.

v4 retrieval operationalization (IT-037). Difficulty axis = number of distinct
sources to combine (1/2/3), sweep-all. Tasks are natural-language information-
retrieval questions about named customers (mostly single-fact retrieval, a few
customer-360 multi-field, a few aggregates).

Paradigm operationalization (tool-router workflow that respects the real
service boundary):
- Workflow: a two-LLM pipeline bracketing deterministic steps. (1) a planner
  node, given the question and the tool catalogue, emits a RetrievalSpec: the
  Mail/Calendar searches to issue and one read-only SQL SELECT per answer field
  over the CRM plus the staged Mail/Calendar rows. (2) a deterministic dispatch/
  fetch node calls the simulated Gmail/Calendar APIs (payload realism + synthetic
  latency) and stages the results; unselected tools stage empty. (3) a
  deterministic execute node runs each field's SQL (with synthetic DB latency) so
  the database engine performs the joins and aggregations. (4) an aggregator LLM,
  given the original question and the computed field values, composes the final
  answer. The heavy aggregation is deterministic; where a question does not fit
  the SQL structure the aggregator combines the retrieved values, so the
  workflow's accuracy advantage is conditional on the computation being
  SQL-expressible. All four tools carry synthetic latency; the DB, Mail and
  Calendar are reached only through their tool/API boundary.
- Agent: the same question answered with the read tools (db_read/db_search for
  CRM, search_emails for the mailbox, search_events for the calendar); the LLM
  locates, combines, and computes in-context.

Source: CRMArena (Huang et al., 2025) for CRM; WorkBench (Styles et al., 2024)
for the Mail/Calendar APIs. Coherent named customers seeded by
experiments/seed_b_retrieval.py.
"""

from src.archetypes.b_structured_retrieval.schemas import (
    FetchPlan,
    QueryAnswer,
    RetrievalField,
    RetrievalPlan,
    RetrievalSpec,
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
    "QUERY_SCHEMA_DOC",
    "AGENT_SCHEMA_DOC",
    "QueryAnswer",
    "RetrievalField",
    "RetrievalPlan",
    "RetrievalSpec",
    "FetchPlan",
    "PLAN_PROMPT",
    "AGGREGATE_PROMPT",
    "AGENT_SYSTEM_PROMPT",
]

DIMENSIONAL_PROFILE = {
    # "mid": the shape of the pipeline (plan, fetch, aggregate) is fixed, but
    # which stores to query and the queries themselves depend on the input.
    "step_predictability": "mid",
    # "mid": the source records live in known external stores (CRM/Mail/
    # Calendar) reached through their query APIs; access is guaranteed, so
    # retrieval is deterministic, but the information is not in the input.
    # Aligned with the Table-3 level anchors (thesis Section 4.2.7).
    "information_availability": "mid",
    "output_ambiguity": "low",
    "error_consequence": "moderate",
}

SOURCE_BENCHMARK = "CRMArena (Huang et al., 2025) + WorkBench (Styles et al., 2024)"
TEMPERATURE = DEFAULT_TEMPERATURE
TOOLS = [db_read, db_search, search_emails, search_events]

QUERY_SCHEMA_DOC = """The CRM is a local SQLite database (case-sensitive string comparison) with:
- accounts(id, name, region, industry, type)
- contacts(id, account_id, name, email)
- agents(id, name, team, region, email)
- cases(id, account_id, agent_id, subject, issue_category, status, priority, created_at, closed_at, transfer_count)
- opportunities(id, account_id, owner_agent_id, name, amount, stage, created_at, close_date, is_won)

Mail and Calendar are EXTERNAL services. Their data is NOT in the CRM database; it has already been fetched
through their APIs into two staging tables you can join against:
- fetched_emails(sender, recipient, subject, body, sent_at)
- fetched_events(name, attendees, start_time, end_time)

Value conventions (use these exact values):
- accounts.type is one of 'Key Account', 'Customer', 'Partner'; key accounts are exactly type='Key Account'.
- Account and contact names are exact strings: use the name exactly as written in the question (e.g. 'Mayer & Co').
- opportunities.is_won is 1 (won) or 0 (open/not won); an offer's recency is its created_at.
- cases.status is 'Open' or 'Closed'; cases.priority is 'Low','Medium','High'.
- fetched_events.attendees is a single COMMA-SEPARATED string of email addresses; match an attendee with
  fetched_events.attendees LIKE '%' || contacts.email || '%'. Do not use json_each.
- IMPORTANT: the calendar search matches the event NAME only, so a customer's meeting may not be found by
  searching the customer name. Whenever the question involves a meeting, fetch ALL events (calendar_queries=[''])
  and identify the customer's meeting by the ATTENDEE join above, not by the event title.
- A customer's emails are rows in fetched_emails whose sender or recipient is one of that account's contact emails.
- A meeting "with" a customer is a fetched_events row whose attendees include one of the account's contact emails;
  the "next" meeting is the earliest such row (ORDER BY start_time ASC LIMIT 1).
- An 'offer' or 'deal' is an opportunities row REGARDLESS of is_won; the 'most recent' offer is the one with the latest created_at. Do NOT add is_won unless the question explicitly says 'won'. Only filter is_won=1 for 'won' and is_won=0 for 'open/still-open'.
- When the question asks WHICH account/customer (who), return accounts.name (not accounts.id and not an opportunity name). When it asks HOW MUCH / HOW LARGE / the value / the amount, return the numeric amount.
- To find an account that a colleague flagged or named in an INTERNAL email (both sender and recipient @atlas.com), match the account name against the email text: join accounts to fetched_emails on (fetched_emails.subject LIKE '%' || accounts.name || '%' OR fetched_emails.body LIKE '%' || accounts.name || '%').
- Dates are 'YYYY-MM-DD HH:MM:SS'; wrap a date answer in date(...) to return 'YYYY-MM-DD'."""

AGENT_SCHEMA_DOC = """Data you can read:
- CRM tables via db_read/db_search: accounts(name, region, industry, type),
  contacts(account_id, name, email), agents(name, team, email),
  cases(account_id, status, priority, ...), opportunities(account_id, name, amount, stage, created_at, close_date, is_won).
- The mailbox via search_emails(query): emails have sender, recipient, subject, body, sent_at, status.
- The calendar via search_events(query): events have a name, attendees (email addresses), and start_time.

Value conventions (use these exact values):
- accounts.type is one of 'Key Account', 'Customer', 'Partner'; key accounts are exactly type='Key Account'.
- Account and contact names are exact strings: use the name exactly as written in the question (e.g. 'Mayer & Co').
- opportunities.is_won is true (won) or false (open/not won); an offer's recency is its created_at.
- cases.status is 'Open' or 'Closed'; priority is 'Low','Medium','High'. emails.status is 'inbox','outbox','deleted'.

Semantic conventions:
- A deal/offer = an opportunity, regardless of won status; the "most recent" offer is the one with the latest created_at. Only restrict to won or open if the question says so ("won" = is_won true; "open/still-open" = is_won false).
- When the question asks WHICH account/customer (who), answer with the account's name. When it asks how much / how large / the value / the amount, answer with the number.
- A customer's emails are those to/from one of that account's contact emails; colleague notes are agent-to-agent emails (both @atlas.com) that name the account. To find the account a colleague flagged in an internal email, read the internal email and match the account name it mentions.
- A meeting "with" a customer is an event whose attendees include one of the account's contact emails; the "next" meeting is the earliest such event."""


PLAN_PROMPT = """You plan the retrieval for a CRM data question. Four tools are available:
- the CRM database (accounts, contacts, agents, cases, opportunities), queried with read-only SQL;
- Mail and Calendar, external services reached only through their search APIs; their data is staged into the tables fetched_emails / fetched_events so your SQL can join against it.

{schema}

Emit a RetrievalSpec:
- mail_queries: substrings to search the mailbox (subject/body/sender). Use a customer's email domain (e.g. 'mayer.example') or a subject keyword; use '' to fetch all emails. Empty list if the question needs no mail.
- calendar_queries: the calendar search matches the event NAME only, not the attendees. Because a customer's meeting may not carry the customer name in its title, use [''] to fetch ALL events whenever the question involves a meeting, and let the SQL filter by attendee. Empty list only if the question needs no calendar.
- fields: one read-only SQL SELECT per answer field over the CRM tables plus fetched_emails/fetched_events. Let the DATABASE do the joins and aggregations (SUM, COUNT, AVG, MIN, MAX, ORDER BY ... LIMIT 1) — do not compute in prose. Return each field's value as the first column of the first row. Use one field named 'answer' for a single-fact question; descriptive field names for a multi-part question. If an aggregation truly cannot be expressed in SQL, return the underlying values as fields and they will be combined afterwards.
- Read Mail/Calendar only from fetched_emails / fetched_events. Scope to key accounts (type='Key Account') when the question says "key account". Use account/contact names exactly as written. SELECT only, one statement per field.

Question: {question}"""

AGGREGATE_PROMPT = """You write the final answer to a CRM data question. A deterministic retrieval step has already dispatched the tools and run the SQL; the field results below were computed by the database engine.

Question: {question}

Retrieved field results (field name -> value, already computed):
{results}

Give the final answer as a QueryAnswer: `value` is the concise answer the question asks for (a number, a name, a region, or a date; for a multi-part question state each requested value clearly). Do not re-derive or second-guess a value that is already computed; only select, combine, or format the retrieved values into the answer. If a value is missing (None), say so rather than inventing one."""

AGENT_SYSTEM_PROMPT = """You are a CRM data analyst. Answer the user's question by reading the available sources with the tools.

{schema}

Use db_read/db_search for the CRM tables, search_emails(query=...) for the mailbox, and search_events(query=...) for the calendar. Locate the relevant records, combine them across sources as the question requires, and answer. For a single-fact question, state only the value (a number, a name, a region, or a date). For a multi-part question, state each requested value clearly."""
