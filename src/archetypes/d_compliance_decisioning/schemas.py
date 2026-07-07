"""Pure data models for archetype D: Compliance and Rule-Based Decisioning.

The decision target is the routing of a sales-operations quote request
against a codified approval policy. The five decision labels span the
typical compliance decision space:

    APPROVE              — auto-issue the quote
    ESCALATE_DIRECTOR    — quote needs director sign-off
    ESCALATE_VP          — quote needs VP sign-off
    ESCALATE_REGIONAL_VP — quote needs regional VP sign-off
    DECLINE              — quote cannot be issued under the current policy

DECLINE is the canonical **no-action** label following the WorkBench
no-action subset (Styles et al., 2024): the requested action is non-
permissible under the rules, and the correct behaviour is to refuse rather
than to invent an alternative. This is the high-error-consequence test that
separates D from C — in C the label set is taxonomic (route to a category),
in D the label set includes a refusal that must be issued when the rules
forbid action.

Source: CRMArena-Pro Workflow Execution + World of Workflows Constraint
Understanding + WorkBench no-action subset + FlowBench rule-following.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DECISION = Literal[
    "APPROVE",
    "ESCALATE_DIRECTOR",
    "ESCALATE_VP",
    "ESCALATE_REGIONAL_VP",
    "DECLINE",
]


class QuoteFacts(BaseModel):
    """Structured facts extracted from a natural-language quote request.

    The redesigned D workflow (mid information availability) receives the
    request as free text rather than as a structured record. The single LLM
    call in the workflow is an *extraction* step: it reads the email-style
    request and emits these flat fields, which the deterministic rule engine
    then evaluates against the policy clauses fetched from the Policy Registry.
    The field names match the clause field names in ``policy_data.py``.
    """

    lead_status: str = Field(
        description="The lead's status as stated in the request, e.g. 'qualified' or 'unqualified'"
    )
    region: str = Field(
        description="The customer's region, e.g. 'EMEA', 'AMER', 'APAC'"
    )
    is_existing: bool = Field(
        description="True if an existing customer, False if a new/non-existing customer"
    )
    has_overdue_invoices: bool = Field(
        description="True if the customer has overdue invoices outstanding, else False"
    )
    has_credit_hold: bool = Field(
        description="True if the customer is on a credit hold / credit block, else False"
    )
    is_new_logo: bool = Field(
        description="True if the deal is a new-logo acquisition (a brand-new customer win), else False"
    )
    segment: str = Field(
        description="The customer segment as written, e.g. 'Commercial', 'Strategic', 'Restricted'"
    )
    amount: float = Field(
        description="The quote/deal amount in dollars (digits only, no currency symbol or thousands separators)"
    )
    base_discount_pct: float = Field(
        description="The requested base discount as a percentage number (e.g. 8 for 8%)"
    )
    term_months: float = Field(
        description="The contract term length in months as a plain number (e.g. 24)"
    )


class DecisionResult(BaseModel):
    """Final decision after applying the approval policy."""

    label: DECISION = Field(
        description="The decision mandated by the approval policy"
    )
    rationale: str = Field(
        description="One short sentence naming the rule(s) that determined the decision"
    )
