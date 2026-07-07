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
Phase-2 tool-symmetry invariant; the workflow never calls them, and the agent
too made ZERO tool calls in every run. The a-priori expectation that the
agent's unnecessary lookups would be the observable cost signal did NOT
materialise. In the batch-triage design the observed cost signal is instead the
workflow's chunk overhead at High (the category document is re-sent per chunk),
so the agent's single-context call is actually the cheaper paradigm there.
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

#: Chunk size for the workflow's deterministic map-reduce over a batch. A batch
#: of N emails is split into ceil(N / CHUNK_SIZE) LLM calls: Low (3) -> 1, Med
#: (5) -> 1, High (8) -> 2. It is the internal conditional branching that keeps
#: this a single task (one batch input -> one labelled output; Section 2.2.3).
#: NOTE: at these batch sizes chunking is net OVERHEAD, not an advantage --
#: each chunk re-sends the full category document, so at High the workflow costs
#: ~1.5x the agent's tokens (~2.5k vs ~1.6k) with no accuracy gain, and the
#: agent carries all 8 emails in one call. The threshold was raised from 3 to 5
#: only to remove the even larger premature-chunking overhead the first nano run
#: showed at Med. Chunking would pay off (on accuracy/feasibility, not tokens)
#: only once a single call degrades under far larger load, which C's regime does
#: not reach; see the iteration log for the batch-load discussion.
CHUNK_SIZE = 5

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


#: Workflow batch prompt. One call classifies one CHUNK of the batch; the
#: deterministic node loops over chunks and merges the results.
BATCH_CLASSIFY_PROMPT = """You are a support-desk router. Classify EACH email in the batch below into exactly one of the support-ticket categories defined below.

{definitions}

Emails to classify (each has an `id`):
{emails}

For every email, output an EmailClassification carrying its `email_id` (copied exactly from the input), the `label` capturing that requester's primary intent, and a one-sentence `rationale`. Return exactly one classification per email in the batch above."""


AGENT_SYSTEM_PROMPT = """You are a support-desk router. You receive a BATCH of customer emails and must assign EACH to exactly one of the support-ticket categories defined below.

{definitions}

The batch of emails (each with an `id`) is in the user message. Classify every email by its stated primary intent. The email text alone is sufficient in nearly every case; the read tools (db_read, db_search) are available if you decide a CRM lookup is useful, but the routing decision is about each email's stated intent.

End your response with ONE line per email, in the exact format (one line each):
FINAL_ANSWER <email_id>: <one of: Billing | Technical | Shipping | Account | Product>"""
