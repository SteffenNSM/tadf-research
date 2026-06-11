"""Configuration for archetype D: Compliance and Rule-Based Decisioning.

Single source of truth for archetype D: its dimensional profile, source
benchmark, tool whitelist, output schema, and the prompt templates for both
paradigms.

The C/D separation (Section 4.2.5 of the thesis, deviation D-010): C exposes
**category definitions** and tests input ambiguity over a fixed label set,
while D exposes **codified IF-THEN rules** and tests rule application over a
fixed decision space. The difficulty axis for D is rule depth — Low uses one
rule, Medium chains three rules, High applies five or more rules with
precedence conflicts and gate-dominated paths (Table A.1 row D).

The high-error-consequence dimension (the property that distinguishes D
from C in the four-dimensional profile of Table 3) is tested by the
``DECLINE`` label and the WorkBench no-action subset semantics: a non-
trivial fraction of D instances require refusal because the rules forbid
issuing a quote. Six of the fifteen D instances are no-action / DECLINE
cases, one of them in the High stratum behind a complete discount-logic
trail that the LLM must learn to skip because a gate dominates everything
that follows.

Sources: CRMArena-Pro Workflow Execution (Huang et al., 2025); World of
Workflows Constraint Understanding (Skyfall Research, 2025); WorkBench
no-action subset (Styles et al., 2024); FlowBench rule-following (Xiao et
al., 2024). Quote requests are author-constructed and inline in the
instance JSON; the rule set is original work that captures the structural
pattern used across the four cited benchmarks.
"""

from src.archetypes.d_compliance_decisioning.schemas import (
    DECISION,
    DecisionResult,
)
from src.core.llm import DEFAULT_TEMPERATURE
from src.core.tools.database import db_read, db_search

# ── TADF metadata ──

DIMENSIONAL_PROFILE = {
    "step_predictability": "high",
    "information_availability": "high",
    "output_ambiguity": "low",
    "error_consequence": "high",
}

SOURCE_BENCHMARK = (
    "CRMArena-Pro Workflow Execution (Huang et al., 2025); "
    "World of Workflows Constraint Understanding (Skyfall Research, 2025); "
    "WorkBench no-action subset (Styles et al., 2024); "
    "FlowBench rule-following (Xiao et al., 2024)"
)

#: Protocol A.6: temperature 0.0 applies ONLY to archetype G (the PlanBench
#: convention for planning); all other archetypes run at 0.2 so the
#: consolidated multi-run pass can estimate within-instance variance, and so
#: the C/D comparison is not confounded by a temperature difference (C ran
#: at 0.2).
TEMPERATURE = DEFAULT_TEMPERATURE

#: Tool whitelist exposed to both paradigms (Phase-2 tool-symmetry invariant
#: A.3). The canonical-minimal workflow never invokes a tool; the agent may.
#: The D instances are constructed so the quote request alone is sufficient
#: to apply the policy, mirroring the C exposed-but-unused tool pattern.
TOOLS = [db_read, db_search]


#: The full approval policy, expressed as codified IF-THEN rules in three
#: tiers (gates, computation, decision precedence). Exposed verbatim to both
#: paradigms. The order in which the rules are listed mirrors the
#: evaluation order; the inline "precedence" markers make the override
#: hierarchy explicit so that ambiguous-precedence instances reduce to
#: deterministic gold under the policy.
POLICY_RULES = """Quote approval policy. Apply the following rules to each incoming quote request and return one decision. Evaluate in the order below; the first applicable rule whose decision is final wins.

GATES — evaluated first. If any gate fails, the decision is DECLINE and no further evaluation is performed.
G1. Lead qualification: lead.status must equal "qualified". If not: DECLINE.
G2. Customer compliance: customer.has_overdue_invoices must be false. If true: DECLINE.

DISCOUNT COMPUTATION — only if both gates pass.
B1. Regional bonus: if customer.region == "EMEA", add 5 percentage points to quote.base_discount_pct.
B2. Loyalty bonus: if customer.is_existing == true, add 3 percentage points to quote.base_discount_pct.
The effective discount = base_discount_pct + (EMEA bonus if any) + (loyalty bonus if any).

DECISION RULES — applied in precedence order. Each rule has a precedence index; the rule with the lowest precedence index that fires determines the decision.
P1 (precedence 1, over-limit cap): if effective discount > 30, the decision is DECLINE — the discount exceeds the maximum authorized amount.
P2 (precedence 2, high-value escalation): if quote.amount > 200000, the decision is ESCALATE_REGIONAL_VP — high-value deals route to the regional VP regardless of the discount bracket.
P3 (precedence 3, small-deal constraint): if quote.amount < 5000 AND effective discount > 5, the decision is ESCALATE_DIRECTOR — small deals with non-trivial discounts require director sign-off even if the bracket would otherwise APPROVE.
P4 (precedence 4, discount brackets, applied only if P1–P3 do not fire):
    - effective discount in the inclusive range [0, 10]: APPROVE
    - effective discount in the half-open range (10, 20]: ESCALATE_DIRECTOR
    - effective discount in the half-open range (20, 30]: ESCALATE_VP

Valid decision labels are exactly: APPROVE | ESCALATE_DIRECTOR | ESCALATE_VP | ESCALATE_REGIONAL_VP | DECLINE."""


# ── Prompts ──

CLASSIFY_PROMPT = """You are a compliance officer in the sales operations team. You receive a quote request and must apply the company's approval policy below to return exactly one decision.

{rules}

Quote request:
{quote_request}

Task: {instruction}

Output your decision as a DecisionResult: pick the `label` mandated by the policy and give a one-sentence `rationale` naming the rule(s) that determined it. Apply the rules mechanically; do not invent exceptions."""


AGENT_SYSTEM_PROMPT = """You are a compliance officer in the sales operations team. You receive a quote request and must apply the company's approval policy below to return exactly one decision.

{rules}

The quote request is provided in the user message. The policy can be applied from the quote request alone; the read tools (db_read, db_search) are available if you decide a CRM lookup is useful, but the policy applies to the fields already present in the request and rarely requires additional context.

Apply the rules mechanically and do not invent exceptions. End your response with a single line in the exact format:
FINAL_ANSWER: <one of: APPROVE | ESCALATE_DIRECTOR | ESCALATE_VP | ESCALATE_REGIONAL_VP | DECLINE>"""
