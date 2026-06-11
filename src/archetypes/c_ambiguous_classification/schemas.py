"""Pure data models for archetype C: Ambiguous Classification and Disambiguation.

The classification target is the support-ticket category of an incoming
customer email, drawn from the five-value enum used in the seed CRM
``cases.issue_category`` column. The workflow emits the
``ClassificationResult`` via ``with_structured_output`` so the label is
constrained to the Literal; the agent reports its choice in free text and
the ground-truth extractor parses a ``FINAL_ANSWER:`` line.

The five categories deliberately mirror ``cases.issue_category`` from
``experiments/seed_crm.py`` (``Billing``, ``Technical``, ``Shipping``,
``Account``, ``Product``) so the CRM-routing semantics are visible in the
schema and the C archetype tasks can in principle be cross-validated against
real case data without a schema mapping step.

The ambiguity tested by archetype C lives in the **email text** rather than
in the routing rule set: under the category definitions documented in
``config.py``, exactly one category captures the requester's primary intent
even when the surface text touches several categories. This is the
operational distinction between archetype C (input-ambiguity, fixed labels)
and archetype D (rule-application with codified IF-THEN rules).

Source: CRMArena-Pro Case Routing / Activity Priority Understanding (Huang
et al., 2025) — task semantics; email texts are author-constructed and
inline in the instance JSON.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EMAIL_CATEGORY = Literal[
    "Billing",
    "Technical",
    "Shipping",
    "Account",
    "Product",
]


class ClassificationResult(BaseModel):
    """Final routing decision for a customer email."""

    label: EMAIL_CATEGORY = Field(
        description="The category that best captures the requester's primary intent"
    )
    rationale: str = Field(
        description="One short sentence describing what the requester is asking for and why that maps to the chosen category"
    )
