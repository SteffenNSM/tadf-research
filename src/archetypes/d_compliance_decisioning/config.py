"""Configuration for archetype D: Compliance and Rule-Based Decisioning.

Single source of truth for archetype D: its dimensional profile, source
benchmark, tool whitelist, output schema, and the prompt templates for both
paradigms.

Redesign (D rebuild, "mid information availability" — see iteration log).
Earlier, the full approval policy was pasted into the prompt, so D had high
information availability and its canonical-minimal workflow collapsed to a
single in-context LLM call — structurally identical to archetype C. The
redesign lowers information availability to **mid**: the rules are no longer
in the prompt. They live in an external Policy Registry (``policy.py``,
five documents) and must be retrieved through its API — with synthetic
latency, like the Mail/Calendar services in archetype B/F — before the
decision can be made. This is how a production compliance flow works: it
loads its rules from a policy store, then runs them through a rules engine.

The two paradigms now genuinely diverge in locus of control:
- Workflow: a fixed pipeline. (1) ``survey`` lists the policy catalogue;
  (2) ``fetch_rules`` deterministically pulls every policy document and
  assembles the clause set; (3) ``extract`` (the single LLM call) reads the
  natural-language request and emits the structured ``QuoteFacts``;
  (4) ``decide`` applies the clauses with a deterministic rule engine
  (``rule_engine.py``) — the LLM never applies the policy. This parallels
  B's ETL pattern (LLM plans/extracts, engine computes).
- Agent: the same two registry tools, called at runtime. The agent decides
  which documents to read, reads the rules, and applies them in-context.

What is held fixed is D's *identity*: the difficulty axis remains **rule
depth / decision criticality** (Low: one gate or bracket settles it; Medium:
bonuses + a bracket combine; High: precedence reconciliation across the full
clause set with gate-dominated and boundary paths), and the
high-error-consequence ``DECLINE`` no-action label is unchanged. The number
of policy documents a request touches is a *consequence* of rule depth, not
the difficulty driver — so D does not collapse into B's source-count axis.
Which paradigm routes better under high error consequence is left to the
experiment, not assumed a priori.

Sources: CRMArena-Pro Workflow Execution (Huang et al., 2025); World of
Workflows Constraint Understanding (Skyfall Research, 2025); WorkBench
no-action subset (Styles et al., 2024); FlowBench rule-following (Xiao et
al., 2024). Quote requests are author-constructed; the rule set is original
work that captures the structural pattern used across the four benchmarks.
"""

from src.archetypes.d_compliance_decisioning.schemas import (
    DECISION,
    DecisionResult,
    QuoteFacts,
)
from src.core.llm import DEFAULT_TEMPERATURE
from src.core.tools.database import db_read, db_search
from src.core.tools.policy import get_policy, list_policies

# ── TADF metadata ──

DIMENSIONAL_PROFILE = {
    "step_predictability": "high",
    "information_availability": "mid",
    "output_ambiguity": "low",
    "error_consequence": "high",
}

SOURCE_BENCHMARK = (
    "CRMArena-Pro Workflow Execution (Huang et al., 2025); "
    "World of Workflows Constraint Understanding (Skyfall Research, 2025); "
    "WorkBench no-action subset (Styles et al., 2024); "
    "FlowBench rule-following (Xiao et al., 2024)"
)

#: Protocol A.6 (IT-030): temperature 0 for all archetypes — deterministic
#: single-run evaluation following WorkBench and PlanBench.
TEMPERATURE = DEFAULT_TEMPERATURE

#: Tool whitelist exposed to both paradigms (Phase-2 tool-symmetry invariant
#: A.3). Both paradigms reach the policy only through the Policy Registry API;
#: the rules are not in the prompt. The workflow calls these in a fixed order
#: (survey, then fetch all); the agent calls them adaptively at runtime.
#: db_read/db_search are exposed but NOT needed (the decision is determined by
#: the request facts plus the fetched policy); they are distractor tools that
#: let us observe whether the agent wastes calls on irrelevant CRM lookups.
TOOLS = [list_policies, get_policy, db_read, db_search]


# ── Prompts ──

#: Workflow extraction step. The LLM's ONLY job in the workflow: turn the
#: free-text request into structured QuoteFacts. It does not see or apply the
#: policy — the deterministic engine does that over the fetched clauses.
EXTRACT_PROMPT = """You are a sales-operations assistant. Read the quote request below and extract the structured facts needed to evaluate it. Do not make any approval decision; only extract what is stated.

Quote request:
{request_text}

Extract a QuoteFacts object:
- lead_status: the lead's status word as written (e.g. "qualified", "unqualified").
- region: the customer's region (e.g. "EMEA", "AMER", "APAC").
- is_existing: true if it is described as an existing customer, false if new / non-existing.
- has_overdue_invoices: true if the customer is said to have overdue invoices, false if it has none.
- has_credit_hold: true if the customer is said to be on a credit hold / credit block, false otherwise.
- is_new_logo: true if the deal is described as a new-logo acquisition (a brand-new customer win), false otherwise.
- segment: the customer segment as written (e.g. "Commercial", "Strategic", "Restricted").
- amount: the deal amount in dollars as a plain number (drop the $ and any commas).
- base_discount_pct: the requested base discount as a plain percentage number.
- term_months: the contract term length in months as a plain number.
Report only what the request states; do not infer eligibility or apply any rule."""


#: Agent system prompt. The agent must retrieve the policy from the registry
#: itself and apply it in-context.
AGENT_SYSTEM_PROMPT = """You are a compliance officer in the sales operations team. A quote request arrives as a natural-language message. You must decide it under the company's approval policy and return exactly one decision label.

The approval policy is NOT included in this prompt. It lives in an external Policy Registry that you read with tools:
- list_policies(): returns the catalogue of available policy documents (topic, title, summary). Some documents are unrelated to quote approval (e.g. travel or data-retention policies) and can be ignored.
- get_policy(topic): returns one document's rules, including a human-readable `rules_text` and a machine-readable `clauses` list.
- db_read / db_search are also available for CRM lookups but are rarely needed: the decision is determined by the request facts plus the fetched approval policy.

Procedure:
1. Read the request and note the relevant facts (lead status, region, existing customer, overdue invoices, credit hold, new-logo, segment, amount, base discount, term).
2. Use list_policies to see what policy documents exist, then get_policy to read the ones relevant to quote approval.
3. Apply the rules exactly as written — evaluate gates first (a failed gate forces DECLINE), then add any discount bonuses to the base discount, then apply the decision rules in precedence order (the lowest-precedence rule that fires decides).
4. Apply the rules mechanically; do not invent exceptions.

End your response with a single line in the exact format:
FINAL_ANSWER: <one of: APPROVE | ESCALATE_DIRECTOR | ESCALATE_VP | ESCALATE_REGIONAL_VP | DECLINE>"""
