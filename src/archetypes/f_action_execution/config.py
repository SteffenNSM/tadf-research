"""Configuration for archetype F: Transactional Action Execution.

Single source of truth for archetype F: its dimensional profile, source
benchmarks, tool whitelist, output schema, and the prompt templates for both
paradigms.

Source: WorkBench (Styles et al., 2024) for the canonical CRUD action patterns
across mail, calendar, and CRM; WorkArena L1/L2 (Drouin et al., 2024) for the
multi-step compositional patterns used at the high difficulty level.

F is the bipolar archetype from Table 3: canonical inputs (familiar action
sequences) favor the workflow paradigm; novel inputs (uncommon combinations or
unusual orderings) favor the agent paradigm. The high difficulty stratum
includes both sub-classes (3 canonical, 2 novel) so the bipolarity is
empirically observable.
"""

from src.archetypes.f_action_execution.schemas import (
    Action,
    ActionPlan,
    ActionResult,
    ReadAction,
    ReadPlan,
)
from src.core.llm import DEFAULT_TEMPERATURE
from src.core.tools.calendar import (
    create_event,
    delete_event,
    search_events,
    update_event,
)
from src.core.tools.database import (
    attempt_close_case,
    db_read,
    db_search,
    db_update,
)
from src.core.tools.mail import (
    delete_email,
    forward_email,
    search_emails,
    send_email,
)

# ── TADF metadata ──

DIMENSIONAL_PROFILE = {
    "step_predictability": "high_for_canonical_low_for_novel",
    "information_availability": "high",
    "output_ambiguity": "low",
    "error_consequence": "high",
}

SOURCE_BENCHMARK = "WorkBench (Styles et al., 2024); WorkArena L1/L2 (Drouin et al., 2024)"
TEMPERATURE = DEFAULT_TEMPERATURE

#: Tool whitelist shared between workflow and agent. Both paradigms have
#: identical access; what differs is who decides when to use which.
TOOLS = [
    send_email,
    search_emails,
    forward_email,
    delete_email,
    create_event,
    search_events,
    update_event,
    delete_event,
    db_read,
    db_search,
    db_update,
    attempt_close_case,
]

#: Map from action name to the @tool runnable. Used by the workflow's
#: deterministic execute_actions node to dispatch planned actions.
TOOL_DISPATCH = {t.name: t for t in TOOLS}

CRM_SCHEMA_DOC = """Workspace data domains and the operations available on them.

CRM data (read-only via db_read / db_search; some columns updatable via db_update):
- accounts(id, name, region, industry, type)
- contacts(id, account_id, name, email)
- agents(id, name, team, region, email)
- cases(id, account_id, agent_id, subject, issue_category, status, priority, created_at, closed_at, transfer_count)
- opportunities(id, account_id, owner_agent_id, name, amount, stage, created_at, close_date, is_won)

Mail domain — accessed exclusively via the mail tools (not via db_read).
- send_email(recipient, subject, body, sender) → sends a message and returns a Gmail-shaped message resource: {{id, threadId, labelIds=['SENT'], snippet, historyId, internalDate, payload{{headers[5 items: From/To/Subject/Date/Message-ID], body{{size, data (base64url)}}, mimeType, partId, filename}}, sizeEstimate}}.
- search_emails(query, date_min, date_max, status) → list of Gmail message resources (same shape). status filter values: 'inbox' | 'outbox' | 'deleted' (internal storage). To find a recipient or subject, read payload.headers; to read body content prefer the snippet (first 200 chars, plaintext) over payload.body.data (base64url).
- forward_email(email_id, recipient, sender) → returns the Gmail resource for the new forwarded copy.
- delete_email(email_id) → minimal acknowledgement {{id, labelIds=['TRASH']}}.

Calendar domain — accessed exclusively via the calendar tools (not via db_read).
- create_event(name, start_time, end_time, attendees, organizer_email) → returns a Google Calendar event resource: {{kind, etag, id, status, htmlLink, created, updated, summary, creator{{email, self}}, organizer{{email, self}}, start{{dateTime, timeZone}}, end{{dateTime, timeZone}}, iCalUID, sequence, attendees[{{email, responseStatus}}], recurringEventId, eventType}}.
- search_events(query, date_min, date_max, attendee, status) → list of Calendar event resources (same shape). To find the title use summary; to find participants iterate attendees[].email.
- update_event(event_id, name?, start_time?, end_time?, attendees?) → returns the updated Calendar event resource.
- delete_event(event_id) → minimal acknowledgement {{id, status='cancelled'}}.

Case-specific transactional tool:
- attempt_close_case(case_id, resolution_summary): tries to close a case. The close is subject to internal business rules enforced by the back-end (escalation policies, transfer history, etc.); these rules are NOT exposed via the read tools and cannot be reliably checked in advance. The tool returns {{"closed": true, "id": ...}} on success, or {{"closed": false, "reason": "..."}} if the close was blocked by an internal rule. State changes only on success.

Notes:
- CRM date/time fields use 'YYYY-MM-DD HH:MM:SS' for db_read/db_update arguments; the calendar tools accept the same SQL-style format and return RFC3339 timestamps in start.dateTime / end.dateTime.
- The current user's email is 'user@atlas.com' (default sender/organizer).
- Mail and calendar tool responses are sized to match real Gmail and Google Calendar API payloads (multiple nested fields per item) rather than minimal acknowledgements."""


# ── Prompts ──

PLAN_READS_PROMPT = """You are planning the read-only database lookups needed to gather information for a workplace task.

{schema}

Produce a ReadPlan: an ordered list of read-only tool invocations whose results will let a separate action planner produce concrete actions with real ids and field values.

Read-only tools you may use:
- db_read(table, filters): fetches rows matching exact-match filters. Use this when you need a structured filter, for example {{"agent_id": 3, "status": "Open"}}.
- db_search(table, column, query): substring match on a single column. Use only for free-text columns.
- search_emails(query, date_min, date_max, status): search mailbox.
- search_events(query, date_min, date_max, attendee, status): search calendar.

Guidelines:
- Plan only the reads that the action planner will actually need.
- If the task statement already contains every value needed to act (recipient address, subject, body, dates, ids), produce an empty `reads` list and let the action planner act directly. Reading defensively when nothing is unknown wastes tokens.
- Prefer db_read with structured filters over db_search for exact filtering.
- Do not plan any state-changing actions in this stage. Those come later.

Task: {instruction}"""


PLAN_ACTIONS_PROMPT = """You are planning the actions needed to fulfill a workplace task.

{schema}

You have already run a set of read-only lookups. Their results are shown below. Use the concrete ids and field values from those results to plan the state-changing actions.

Read results:
{read_results}

Produce an ActionPlan: an ordered list of tool invocations that, when executed in sequence by a deterministic runner, will accomplish the task. Do not execute anything yourself.

Guidelines:
- Plan only the actions actually needed; do not pad the plan.
- For each action, fill in the exact tool name and argument keys as documented in the schema above.
- If the task involves multiple records, expand to one action per record with the concrete record id from the read results. db_update updates one row at a time by record_id; it does not accept filters.
- It is acceptable to include an additional read if it is needed for a value the first stage did not fetch.

Task: {instruction}"""


AGENT_SYSTEM_PROMPT = """You are an autonomous workplace assistant. Use the available tools to complete the user's task.

{schema}

Call the read tools (db_read, db_search, search_emails, search_events) to discover ids and fields you need. Call the state-changing tools (send_email, create_event, update_event, db_update, etc.) to perform actions. When the task is complete, reply with a one-sentence summary of what you did. Do not state things you did not do."""
