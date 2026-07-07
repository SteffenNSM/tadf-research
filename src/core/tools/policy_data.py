"""Policy registry contents for archetype D (framework-free).

This module holds the *data* served by the simulated Policy Registry service
(``src/core/tools/policy.py``): the catalogue of policy documents and, for
each document, its machine-readable rule clauses plus a human-readable text.
It carries no LangChain/LangGraph dependency so the rule engine, the
ground-truth verifier, and the unit tests can import it directly.

Design rationale (IT-04x, D rebuild — "mid information availability"). In the
canonical-minimal D the full approval policy was pasted into the prompt
(information availability = high). The redesign lowers information
availability to *mid*: the rules are NOT in the prompt; they live in an
external Policy Registry and must be retrieved through its API before the
decision can be made — exactly as a production compliance flow loads its
policy from a rules service (e.g. a decision-table store or a policy-doc
repository) rather than hard-coding it.

The policy is partitioned into eight documents by topic: six that govern quote
approval plus two DISTRACTORS (travel-expense and data-retention policies)
whose clauses reference fields absent from QuoteFacts and therefore can never
fire. The partition is the realistic envelope, not the difficulty axis: the
difficulty axis of D is **rule depth** — the number of rules that must be
combined and correctly ordered to reach the decision (Low ~2, Med ~5, High
~10) at a fixed document count, so it does not collapse into B's source-count
axis. A Low instance is settled by ~2 rules (a gate, or gates-pass plus one
bracket); a High instance reconciles ~10 — up to four gates, several stacking
bonuses (B1 EMEA, B2 loyalty, B3 term, B4 APAC, B5 new-logo), and precedence
across the over-limit cap, high-value/strategic escalation, small-deal, and
bracket rules, with boundary and gate-dominated paths. The distractors let us
observe agent selectivity (does it read irrelevant policy?) against the
workflow's fetch-all cost.

Each clause is a small, engine-interpretable record:

    gate     {id, kind:'gate',     field, op, value, decision}
    bonus    {id, kind:'bonus',    field, op, value, add_pct}
    decision {id, kind:'decision', precedence, conditions[{field,op,value}], decision}

Field names are the flat fact keys produced by the workflow's extraction step
(see ``schemas.QuoteFacts``): ``lead_status``, ``region``, ``is_existing``,
``has_overdue_invoices``, ``amount``, ``base_discount_pct``, and the derived
``effective_discount``. The clause set is the same policy that the
canonical-minimal D expressed in prose; expressing it as data is what lets a
deterministic engine — rather than the LLM — apply it in the workflow.

Source: the policy is original author work capturing the structural pattern of
CRMArena-Pro Workflow Execution (Huang et al., 2025), World of Workflows
Constraint Understanding (Skyfall Research, 2025), the WorkBench no-action
subset (Styles et al., 2024), and FlowBench rule-following (Xiao et al., 2024).
"""

from __future__ import annotations

import copy
from typing import Any

#: The policy documents served by the registry (six governing + two distractor).
#: Order is the catalogue
#: order returned by ``list_policies``; it also mirrors the natural evaluation
#: order (gates, then computation, then decision precedence) but the engine
#: does not rely on document order — it sorts gates and decisions explicitly.
POLICY_DOCS: dict[str, dict[str, Any]] = {
    "lead_eligibility": {
        "topic": "lead_eligibility",
        "title": "Lead Eligibility Gate",
        "summary": "Whether the lead is eligible for a quote at all.",
        "rules_text": (
            "Lead eligibility gate (evaluated before any discount logic). "
            "The lead status must be \"qualified\". If the lead is not "
            "qualified, the quote is DECLINED and no further rules are "
            "evaluated."
        ),
        "clauses": [
            {
                "id": "G1",
                "kind": "gate",
                "field": "lead_status",
                "op": "ne",
                "value": "qualified",
                "decision": "DECLINE",
            }
        ],
    },
    "customer_compliance": {
        "topic": "customer_compliance",
        "title": "Customer Compliance Gate",
        "summary": "Whether the customer's account standing permits a quote.",
        "rules_text": (
            "Customer compliance gates (evaluated before any discount logic). "
            "G2: the customer must not have overdue invoices; if it does, the "
            "quote is DECLINED. G4: the customer must not be on credit hold; if "
            "it is, the quote is DECLINED. Either failing gate forces DECLINE "
            "with no further evaluation."
        ),
        "clauses": [
            {
                "id": "G2",
                "kind": "gate",
                "field": "has_overdue_invoices",
                "op": "eq",
                "value": True,
                "decision": "DECLINE",
            },
            {
                "id": "G4",
                "kind": "gate",
                "field": "has_credit_hold",
                "op": "eq",
                "value": True,
                "decision": "DECLINE",
            },
        ],
    },
    "customer_segment": {
        "topic": "customer_segment",
        "title": "Customer Segment Rules",
        "summary": "Restricted-segment refusal and strategic-account escalation.",
        "rules_text": (
            "Customer segment rules.\n"
            "Restricted segment (gate — evaluated before any discount logic, "
            "alongside the other gates): if the customer segment is "
            "\"Restricted\", the quote is DECLINED and no further rules are "
            "evaluated.\n"
            "Strategic routing (precedence 2.5 — evaluated after the "
            "high-value rule and before the small-deal rule): if the customer "
            "segment is \"Strategic\" and the deal amount exceeds 100,000, "
            "route to the REGIONAL VP, regardless of the discount bracket."
        ),
        "clauses": [
            {
                "id": "G3",
                "kind": "gate",
                "field": "segment",
                "op": "eq",
                "value": "Restricted",
                "decision": "DECLINE",
            },
            {
                "id": "P2s",
                "kind": "decision",
                "precedence": 2.5,
                "conditions": [
                    {"field": "segment", "op": "eq", "value": "Strategic"},
                    {"field": "amount", "op": "gt", "value": 100000},
                ],
                "decision": "ESCALATE_REGIONAL_VP",
            },
        ],
    },
    "discount_bonuses": {
        "topic": "discount_bonuses",
        "title": "Discount Bonus Schedule",
        "summary": "Bonus percentage points added to the requested base discount.",
        "rules_text": (
            "Discount bonus schedule (applied only after all gates pass); "
            "bonuses stack, and the effective discount is the base discount plus "
            "every bonus that applies. B1: +5 points if the customer region is "
            "EMEA. B2: +3 points if the customer is an existing customer. B3: +4 "
            "points if the contract term is 24 months or longer. B4: +2 points "
            "if the customer region is APAC. B5: +3 points if the deal is a "
            "new-logo acquisition."
        ),
        "clauses": [
            {
                "id": "B1",
                "kind": "bonus",
                "field": "region",
                "op": "eq",
                "value": "EMEA",
                "add_pct": 5,
            },
            {
                "id": "B2",
                "kind": "bonus",
                "field": "is_existing",
                "op": "eq",
                "value": True,
                "add_pct": 3,
            },
            {
                "id": "B3",
                "kind": "bonus",
                "field": "term_months",
                "op": "ge",
                "value": 24,
                "add_pct": 4,
            },
            {
                "id": "B4",
                "kind": "bonus",
                "field": "region",
                "op": "eq",
                "value": "APAC",
                "add_pct": 2,
            },
            {
                "id": "B5",
                "kind": "bonus",
                "field": "is_new_logo",
                "op": "eq",
                "value": True,
                "add_pct": 3,
            },
        ],
    },
    "discount_limits": {
        "topic": "discount_limits",
        "title": "Discount Authorization Limit",
        "summary": "Maximum authorized effective discount before a quote must be declined.",
        "rules_text": (
            "Discount authorization limit (precedence 1 — overrides every "
            "escalation rule). If the effective discount exceeds 30 percent, "
            "the quote is DECLINED: it is above the maximum authorized "
            "discount."
        ),
        "clauses": [
            {
                "id": "P1",
                "kind": "decision",
                "precedence": 1,
                "conditions": [
                    {"field": "effective_discount", "op": "gt", "value": 30}
                ],
                "decision": "DECLINE",
            }
        ],
    },
    "escalation_matrix": {
        "topic": "escalation_matrix",
        "title": "Quote Escalation Matrix",
        "summary": "Sign-off routing by deal value and effective discount bracket.",
        "rules_text": (
            "Quote escalation matrix (applied after the authorization limit). "
            "Rules are evaluated in precedence order; the lowest-precedence "
            "rule that fires decides.\n"
            "P2 (precedence 2, high-value): if the deal amount exceeds "
            "200,000, route to the REGIONAL VP regardless of discount "
            "bracket.\n"
            "P3 (precedence 3, small-deal): if the deal amount is below 5,000 "
            "and the effective discount exceeds 5 percent, route to the "
            "DIRECTOR.\n"
            "P4 (precedence 4, discount brackets): effective discount in "
            "[0,10] is APPROVED; in (10,20] routes to the DIRECTOR; in "
            "(20,30] routes to the VP."
        ),
        "clauses": [
            {
                "id": "P2",
                "kind": "decision",
                "precedence": 2,
                "conditions": [{"field": "amount", "op": "gt", "value": 200000}],
                "decision": "ESCALATE_REGIONAL_VP",
            },
            {
                "id": "P3",
                "kind": "decision",
                "precedence": 3,
                "conditions": [
                    {"field": "amount", "op": "lt", "value": 5000},
                    {"field": "effective_discount", "op": "gt", "value": 5},
                ],
                "decision": "ESCALATE_DIRECTOR",
            },
            {
                "id": "P4a",
                "kind": "decision",
                "precedence": 4,
                "conditions": [
                    {"field": "effective_discount", "op": "ge", "value": 0},
                    {"field": "effective_discount", "op": "le", "value": 10},
                ],
                "decision": "APPROVE",
            },
            {
                "id": "P4b",
                "kind": "decision",
                "precedence": 4,
                "conditions": [
                    {"field": "effective_discount", "op": "gt", "value": 10},
                    {"field": "effective_discount", "op": "le", "value": 20},
                ],
                "decision": "ESCALATE_DIRECTOR",
            },
            {
                "id": "P4c",
                "kind": "decision",
                "precedence": 4,
                "conditions": [
                    {"field": "effective_discount", "op": "gt", "value": 20},
                    {"field": "effective_discount", "op": "le", "value": 30},
                ],
                "decision": "ESCALATE_VP",
            },
        ],
    },
    # ── Distractor documents: plausible corporate policies that are IRRELEVANT
    #    to quote approval. Their clauses reference fields that do not exist in
    #    QuoteFacts (trip_cost, record_age_days, ...), so they can never fire in
    #    the engine. They exist to (a) enlarge the catalogue the workflow fetches
    #    and (b) test whether the agent wastes calls reading irrelevant policy.
    "travel_expense_policy": {
        "topic": "travel_expense_policy",
        "title": "Travel & Expense Reimbursement Policy",
        "summary": "Rules for reimbursing employee travel expenses (not related to quote approval).",
        "rules_text": (
            "Travel and expense policy. Trips over 5,000 in cost require prior "
            "manager approval; expenses filed more than 60 days after the trip "
            "are not reimbursed. This document does not govern customer quotes."
        ),
        "clauses": [
            {"id": "T1", "kind": "gate", "field": "trip_cost", "op": "gt", "value": 5000, "decision": "DECLINE"},
        ],
    },
    "data_retention_policy": {
        "topic": "data_retention_policy",
        "title": "Data Retention & Deletion Policy",
        "summary": "How long records are retained before deletion (not related to quote approval).",
        "rules_text": (
            "Data retention policy. Customer interaction records older than 730 "
            "days are archived; personal data older than 1,095 days is deleted "
            "unless under legal hold. This document does not govern customer quotes."
        ),
        "clauses": [
            {"id": "R1", "kind": "gate", "field": "record_age_days", "op": "gt", "value": 1095, "decision": "DECLINE"},
        ],
    },
}


def list_topics() -> list[dict[str, str]]:
    """Return the catalogue: one ``{topic, title, summary}`` entry per document."""
    return [
        {"topic": d["topic"], "title": d["title"], "summary": d["summary"]}
        for d in POLICY_DOCS.values()
    ]


def get_doc(topic: str) -> dict[str, Any] | None:
    """Return a deep copy of the policy document for ``topic`` (or None)."""
    doc = POLICY_DOCS.get(topic)
    return copy.deepcopy(doc) if doc is not None else None


def all_clauses() -> list[dict[str, Any]]:
    """Return every clause across all documents (deep-copied)."""
    out: list[dict[str, Any]] = []
    for doc in POLICY_DOCS.values():
        out.extend(copy.deepcopy(doc["clauses"]))
    return out
