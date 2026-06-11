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


class DecisionResult(BaseModel):
    """Final decision after applying the approval policy."""

    label: DECISION = Field(
        description="The decision mandated by the approval policy"
    )
    rationale: str = Field(
        description="One short sentence naming the rule(s) that determined the decision"
    )
