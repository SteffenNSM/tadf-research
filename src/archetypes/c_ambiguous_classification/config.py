"""Configuration for archetype C: Ambiguous Classification and Disambiguation.

Single source of truth for archetype C: its dimensional profile, source
benchmark, tool whitelist, output schema, and the prompt templates for both
paradigms.

Source: CRMArena-Pro Case Routing / Activity Priority Understanding (Huang
et al., 2025) — semantics; email texts are author-constructed and inline in
the instance JSON.

Operational note on the C versus D distinction (Iteration Log IT-018, see
also Section 4.2.5 of the thesis): C presents category **definitions** (what
a category covers) rather than IF-THEN routing rules (what keyword triggers
which label). The difficulty axis varies **input ambiguity** — single-cluster
signal, dominant-with-distractor, confusable near-duplicates plus paraphrase
— rather than rule complexity. This keeps archetype C empirically separable
from archetype D (Compliance and Rule-Based Decisioning), whose difficulty
axis is the depth of the rule chain to apply.

The C task is solvable from the email text alone (Information Availability
= HIGH). Both paradigms expose ``db_read`` and ``db_search`` to preserve the
Phase-2 tool-symmetry invariant; the canonical-minimal workflow never calls
them, the agent may. Token cost of unnecessary agent lookups is therefore an
observable comparison signal, analogous to the IT-010 floor finding for A.
"""

from src.archetypes.c_ambiguous_classification.schemas import (
    ClassificationResult,
    EMAIL_CATEGORY,
)
from src.core.llm import DEFAULT_TEMPERATURE
from src.core.tools.database import db_read, db_search

# ── TADF metadata ──

DIMENSIONAL_PROFILE = {
    "step_predictability": "high",
    "information_availability": "high",
    "output_ambiguity": "low",
    "error_consequence": "moderate_high",
}

SOURCE_BENCHMARK = "CRMArena-Pro Case Routing / Activity Priority Understanding (Huang et al., 2025)"
TEMPERATURE = DEFAULT_TEMPERATURE

#: Tool whitelist exposed to both paradigms. Required by the Phase-2
#: tool-symmetry invariant: differences in observed behaviour must be
#: attributable to the paradigm, not to a difference in available tools. The
#: canonical-minimal workflow never invokes a tool (classification is a
#: single LLM call with structured output). The agent may call db_read or
#: db_search if it decides additional CRM context is useful, but the C
#: instances are constructed so the email text alone determines the label.
TOOLS = [db_read, db_search]

#: Category definitions exposed verbatim to both paradigms. These are
#: descriptive (what kind of request the category covers) rather than
#: prescriptive (which keyword triggers which label). The "primary intent"
#: clause at the end of the block is the disambiguation rule when several
#: categories touch the same email; it is not an IF-THEN routing rule.
CATEGORY_DEFINITIONS = """Support-ticket categories. Every incoming customer email is routed to exactly one of these five categories.

- Billing: requests concerning invoices, payments, refunds, billing discrepancies, contract charges, and pricing on existing or about-to-be-issued services. The requester is asking about a monetary amount, a charge that should or should not have happened, or how a price was applied. Mentions of contracts, renewals, or seat changes do not by themselves qualify; the request must be about money.
- Technical: requests reporting that something is broken or degraded — system errors, crashes, broken pages, performance issues, integration or API failures, and login failures caused by the service being unavailable. The requester is reporting a defect they expect to be fixed.
- Shipping: requests concerning physical delivery — delivery status, tracking, address corrections, lost or damaged packages, missed delivery windows, and carrier coordination. The requester wants information about or remediation of the movement of a physical item.
- Account: requests for account-level changes — adding or removing seats, permissions, roles, team membership, profile changes, regional or organisational structure, and password resets where the login system itself is working. The requester wants a change made to who can access the account or to how the account is structured.
- Product: requests for product help — feature how-to questions, documentation questions, "is this supported?" questions, feature requests, and feedback on product behaviour. The requester is asking how to use the product, whether something is supported, or wishing it worked differently.

Routing principle: when an email touches more than one category, route to the category that captures the requester's **primary intent** — the resolution they want delivered. Side mentions, context, and keywords that merely appear in the text do not change the routing target."""


# ── Prompts ──

CLASSIFY_PROMPT = """You are a support-desk router. You receive a customer email and assign it to exactly one of the support-ticket categories defined below.

{definitions}

Customer email:
{email}

Task: {instruction}

Output your routing decision as a ClassificationResult: pick the `label` that captures the requester's primary intent, and give a one-sentence `rationale` describing what the requester is asking for."""


AGENT_SYSTEM_PROMPT = """You are a support-desk router. You receive a customer email and assign it to exactly one of the support-ticket categories defined below.

{definitions}

The customer email is included in the user message. The email text alone is sufficient to determine the routing target in nearly every case; the read tools (db_read, db_search) are available if you decide a CRM lookup is useful, but the routing decision is about the email's stated intent and rarely requires additional context.

End your response with a single line in the exact format:
FINAL_ANSWER: <one of: Billing | Technical | Shipping | Account | Product>"""
