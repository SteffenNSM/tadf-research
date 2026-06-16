"""Configuration for archetype G: Strategic and Adaptive Planning.

Single source of truth for archetype G: its dimensional profile, source
benchmarks, tool whitelist, output schema, and the prompt templates for
both paradigms.

G's deliverable is a plan over the CRM action inventory; nothing is
executed. Scoring is mechanical: the deterministic simulator
(``simulator.py``) applies the plan against the seed state under the same
preconditions the live F tools enforce, then evaluates the instance's
declarative goal spec (deviation D-012: simulator replaces PlanBench's VAL
because the domain is the CRM workspace, not PDDL).

Information Availability is operationalized as **moderate**: the scenarios
reference accounts, agents, and constraints, but the concrete ids, owners,
transfer counts, and contact addresses live in the database and must be
read before a concrete plan can be produced. This gives the paradigm
contrast a real mechanism — the workflow plans its reads once
(``plan_reads → execute_reads → generate_plan``, the IT-014 fetch-then-act
pattern), while the agent may interleave reads and reasoning across turns.

A planner-relevant note on ``attempt_close_case``: in archetype F the
escalation rule (transfer_count > 3 blocks the close) is intentionally
hidden, because F tests runtime recovery after observing a rejection. In G
the rule is DOCUMENTED in the action-set doc below: a plan is produced
before anything runs, so an undocumented failure mode would make blocked
cases unplannable rather than harder to plan. The G test is whether the
planner reads the transfer counts and routes blocked cases through
``db_update`` instead.

Source: PlanBench (Valmeekam et al., 2023); FlowBench plan-generation
variant (Xiao et al., 2024); WorkArena L2 compositional (Boisvert et al.,
2024). Scenarios are author-constructed over the local CRM seed (IT-017).
"""

from src.archetypes.g_strategic_planning.schemas import (
    GReadPlan,
    Plan,
    PlanStep,
)
from src.core.tools.database import db_read, db_search

# ── TADF metadata ──

DIMENSIONAL_PROFILE = {
    "step_predictability": "low",
    "information_availability": "moderate",
    "output_ambiguity": "moderate",
    "error_consequence": "moderate",
}

SOURCE_BENCHMARK = (
    "PlanBench (Valmeekam et al., 2023); "
    "FlowBench plan-generation variant (Xiao et al., 2024); "
    "WorkArena L2 compositional (Boisvert et al., 2024)"
)

#: Protocol A.6 (IT-030): temperature 0 for all archetypes; for G this is also
#: the original PlanBench convention (determinism of the step sequence is the
#: correctness target). Set explicitly here as G's correctness depends on it.
TEMPERATURE = 0.0

#: Per-difficulty maximum agent step limit (protocol A.6; resolves D-007 for
#: G). One step = one agent LLM turn. Exceeding the limit is recorded as an
#: ``iteration_overflow`` failure, following OFFICEBENCH.
MAX_AGENT_STEPS = {"low": 5, "med": 12, "high": 25}

#: Read tools exposed to both paradigms (tool-symmetry invariant A.3).
#: G exposes no state-changing tools to either paradigm: the deliverable is
#: the plan, and actions exist only as plan-step vocabulary.
TOOLS = [db_read, db_search]

#: Action vocabulary for plan steps, with preconditions. Exposed verbatim
#: to both paradigms.
ACTION_SET_DOC = """Plannable actions. Your plan's steps may use exactly these four actions, with exactly these argument keys.

1. db_update(table, record_id, updates)
   - Updates ONE row, identified by record_id (integer). No filters.
   - Updatable columns: cases(status, priority, agent_id, transfer_count, closed_at);
     opportunities(stage, amount, is_won, owner_agent_id); contacts(email, name);
     agents(team, region); accounts(region, industry, type).
   - Setting several columns of the same row in ONE update is preferred over
     several single-column updates.

2. attempt_close_case(case_id, resolution_summary)
   - Closes the case and records the closure timestamp automatically.
   - PRECONDITIONS: the case must exist, must not already be 'Closed', and
     its transfer_count must be 3 or lower. Cases with transfer_count > 3
     are escalated and this action is REJECTED for them — close those via
     db_update(cases, id, {"status": "Closed", "closed_at": "<timestamp>"})
     instead, and remember to set closed_at explicitly on that path.

3. send_email(recipient, subject, body)
   - Sends one email. All three arguments are required.

4. create_event(name, start_time, end_time, attendees)
   - Creates one calendar event. Times use 'YYYY-MM-DD HH:MM:SS'.
   - attendees is a list of email addresses.

Read access (NOT plan steps — use before planning):
- db_read(table, filters): exact-match read over accounts, contacts, agents, cases, opportunities.
- db_search(table, column, query): substring search on one column.

Useful conventions in this workspace:
- The "primary contact" of an account is the contact with the LOWEST id among that account's contacts.
- Agent email addresses follow agent<two-digit-id>@atlas.com (e.g. agent05@atlas.com), and are also stored in the agents table.

Plan-quality requirements:
- Every step must carry concrete argument values (real ids, real email addresses) taken from the database — no placeholders.
- A plan whose step violates a precondition (wrong id, disallowed column, blocked close) is INVALID as a whole.
- Do not add actions the task does not ask for: unnecessary emails, events, or updates make the plan fail the outcome check."""


# ── Prompts ──

PLAN_READS_PROMPT = """You are preparing to write an action plan for a workplace scenario. First, plan the read-only lookups needed to gather the concrete ids and values the plan will reference.

{action_doc}

Produce a GReadPlan: an ordered list of read invocations whose results will let a separate planning stage produce concrete action steps with real ids and field values.

Guidelines:
- Plan only the reads the planner will actually need (case rows incl. transfer_count, contact rows for primary-contact resolution, agent rows, opportunity rows).
- If the task statement already contains every value needed, produce an empty reads list.

Task: {instruction}"""


GENERATE_PLAN_PROMPT = """You are a senior operations planner. Produce the action plan for the scenario below. The plan will be executed later by a deterministic runner — it must be complete, concrete, and precondition-safe as written.

{action_doc}

You have already run read-only lookups. Their results:
{read_results}

Task: {instruction}

Output the Plan: the ordered steps (each with tool and exact args) plus a short rationale naming the preconditions and ordering constraints that shaped the plan."""


AGENT_SYSTEM_PROMPT = """You are a senior operations planner. You will receive a workplace scenario and must produce an action plan. The plan will be executed later by a deterministic runner — it must be complete, concrete, and precondition-safe as written. You do NOT execute any action yourself.

{action_doc}

Use the read tools (db_read, db_search) to discover the concrete ids, transfer counts, owners, and email addresses your plan needs. When your plan is ready, end your response with a single line containing FINAL_PLAN followed by the JSON serialisation of the plan, in the exact format:
FINAL_PLAN: {{"steps": [{{"tool": "send_email", "args": {{"recipient": "...", "subject": "...", "body": "..."}}}}, ...], "rationale": "..."}}

Use valid JSON. Do not wrap the JSON in code fences. The first character after FINAL_PLAN: must be the opening brace."""
