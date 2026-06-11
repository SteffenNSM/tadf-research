"""Curated compliance decision instances for archetype D: Quote Approval Policy.

Writes 15 instance JSON files under ``data/test_inputs/d_compliance_decisioning/``
at three difficulty levels (5 each). Each instance contains:
    id, archetype, difficulty, sub_class, instruction, quote_request,
    expected_label, rationale_hint, provenance

The quote requests are author-constructed and stored inline in the
instance JSON. They are NOT inserted into the shared CRM database, so the
D instance set cannot interact with B's ground truth or with F's
side-effect predicates. Both the workflow and the agent receive the same
quote_request JSON; the agent additionally has db_read / db_search exposed
(per the Phase-2 tool-symmetry invariant) but should not need them.

Difficulty axis (Section 4.4 of the protocol, Table A.1 row D):
    Low    — exactly one rule determines the decision: a gate fails, an
             over-limit cap triggers, a high-value override fires, or the
             default discount bracket selects directly.
    Medium — three rules combine: gates pass, a bonus (or both) modifies
             the effective discount, and a bracket or precedence rule
             selects the decision.
    High   — five or more rules with precedence conflicts and gate-
             dominated paths: bracket boundary at exactly 30 %, bonuses
             pushing into the over-limit cap, small-deal constraint
             overriding the discount bracket, high-value escalation
             overriding the bracket, and a no-action case where a gate
             dominates a complete discount-logic trail that the LLM must
             learn to skip.

No-action coverage (WorkBench no-action subset): six of the fifteen
instances require DECLINE. Two are gate-fail cases at Low (G1 unqualified
lead, G2 overdue invoices); one is a direct over-limit cap at Low (35 %
base discount); two are compound cases where the over-limit cap fires only
through the bonus computation (Medium: +EMEA; High: +EMEA +loyalty); one
is a High instance where customer non-compliance (overdue invoices)
dominates an otherwise-complete discount-logic trail.

The gold label for every instance is determinate under the POLICY_RULES in
config.py — the policy is a deterministic decision tree once the precedence
markers (P1 < P2 < P3 < P4) are read correctly. The rationale_hint field
documents the per-instance rule trace for reviewer transparency.

Source attribution: the policy itself is original work that captures the
structural pattern of CRMArena-Pro Workflow Execution (Huang et al., 2025),
World of Workflows Constraint Understanding (Skyfall Research, 2025), and
the WorkBench no-action subset (Styles et al., 2024). The quote request
records and the rule chain are author-constructed and not lifted from any
benchmark.

Run:
    python experiments/seed_compliance.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "d_compliance_decisioning"

BENCHMARK_REF = (
    "CRMArena-Pro Workflow Execution (Huang et al., 2025); "
    "World of Workflows Constraint Understanding (Skyfall Research, 2025); "
    "WorkBench no-action subset (Styles et al., 2024); "
    "FlowBench rule-following (Xiao et al., 2024)"
)


def _provenance(sub_class: str | None) -> dict:
    note = (
        "Author-constructed quote request and approval policy; task semantics "
        "follow the rule-application + no-action pattern of the cited "
        "benchmarks. No benchmark text or data is reproduced."
    )
    if sub_class:
        note += f" Sub-class: {sub_class}."
    return {
        "source_benchmark": BENCHMARK_REF,
        "adaptation": note,
        # IT-017 honesty rule: original author work; benchmark semantics
        # reference only, no text reuse.
        "license": "Original work by the author (rule set, quote requests, task design); benchmark semantics reference only",
    }


INSTANCES: list[dict] = [
    # ── LOW: exactly one rule determines the decision ──
    {
        "id": "d-low-1",
        "difficulty": "low",
        "sub_class": "no_action_gate_G1",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5001, "status": "unqualified", "account_id": 12},
            "customer": {"region": "AMER", "is_existing": False, "has_overdue_invoices": False},
            "quote": {"amount": 50000, "base_discount_pct": 5},
        },
        "expected_label": "DECLINE",
        "rationale_hint": (
            "Gate G1 (lead.status must be 'qualified') fails — lead is 'unqualified'. "
            "Per the policy, gates evaluate first and a gate failure forces DECLINE with no further evaluation."
        ),
    },
    {
        "id": "d-low-2",
        "difficulty": "low",
        "sub_class": "no_action_gate_G2",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5002, "status": "qualified", "account_id": 7},
            "customer": {"region": "AMER", "is_existing": True, "has_overdue_invoices": True},
            "quote": {"amount": 80000, "base_discount_pct": 8},
        },
        "expected_label": "DECLINE",
        "rationale_hint": (
            "Gate G2 (customer.has_overdue_invoices must be false) fails. DECLINE before any "
            "discount computation."
        ),
    },
    {
        "id": "d-low-3",
        "difficulty": "low",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5003, "status": "qualified", "account_id": 4},
            "customer": {"region": "AMER", "is_existing": False, "has_overdue_invoices": False},
            "quote": {"amount": 50000, "base_discount_pct": 5},
        },
        "expected_label": "APPROVE",
        "rationale_hint": (
            "Gates pass; no EMEA or loyalty bonus applies; effective discount 5 %; falls in P4's [0,10] "
            "bracket → APPROVE."
        ),
    },
    {
        "id": "d-low-4",
        "difficulty": "low",
        "sub_class": "no_action_over_limit",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5004, "status": "qualified", "account_id": 9},
            "customer": {"region": "AMER", "is_existing": False, "has_overdue_invoices": False},
            "quote": {"amount": 100000, "base_discount_pct": 35},
        },
        "expected_label": "DECLINE",
        "rationale_hint": (
            "Gates pass; effective discount 35 % > 30 %. P1 (over-limit cap) fires → DECLINE."
        ),
    },
    {
        "id": "d-low-5",
        "difficulty": "low",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5005, "status": "qualified", "account_id": 14},
            "customer": {"region": "AMER", "is_existing": False, "has_overdue_invoices": False},
            "quote": {"amount": 250000, "base_discount_pct": 0},
        },
        "expected_label": "ESCALATE_REGIONAL_VP",
        "rationale_hint": (
            "Gates pass; effective discount 0 %; quote amount $250,000 > $200,000. P2 (high-value "
            "escalation) fires → ESCALATE_REGIONAL_VP regardless of bracket."
        ),
    },
    # ── MEDIUM: three rules combine ──
    {
        "id": "d-med-1",
        "difficulty": "med",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5006, "status": "qualified", "account_id": 3},
            "customer": {"region": "EMEA", "is_existing": False, "has_overdue_invoices": False},
            "quote": {"amount": 50000, "base_discount_pct": 8},
        },
        "expected_label": "ESCALATE_DIRECTOR",
        "rationale_hint": (
            "Gates pass; B1 (EMEA) adds 5 %; effective 13 %; P4 bracket (10,20] → ESCALATE_DIRECTOR. "
            "Without the EMEA bonus, 8 % would have stayed in [0,10] and APPROVE."
        ),
    },
    {
        "id": "d-med-2",
        "difficulty": "med",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5007, "status": "qualified", "account_id": 8},
            "customer": {"region": "AMER", "is_existing": True, "has_overdue_invoices": False},
            "quote": {"amount": 80000, "base_discount_pct": 18},
        },
        "expected_label": "ESCALATE_VP",
        "rationale_hint": (
            "Gates pass; B2 (loyalty) adds 3 %; effective 21 %; P4 bracket (20,30] → ESCALATE_VP."
        ),
    },
    {
        "id": "d-med-3",
        "difficulty": "med",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5008, "status": "qualified", "account_id": 11},
            "customer": {"region": "AMER", "is_existing": False, "has_overdue_invoices": False},
            "quote": {"amount": 4000, "base_discount_pct": 6},
        },
        "expected_label": "ESCALATE_DIRECTOR",
        "rationale_hint": (
            "Gates pass; no bonuses; effective 6 %; quote amount $4,000 < $5,000 AND effective > 5 %. "
            "P3 (small-deal constraint) fires → ESCALATE_DIRECTOR. Without P3, the 6 % would APPROVE."
        ),
    },
    {
        "id": "d-med-4",
        "difficulty": "med",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5009, "status": "qualified", "account_id": 2},
            "customer": {"region": "EMEA", "is_existing": True, "has_overdue_invoices": False},
            "quote": {"amount": 40000, "base_discount_pct": 0},
        },
        "expected_label": "APPROVE",
        "rationale_hint": (
            "Gates pass; B1 (EMEA) +5 % and B2 (loyalty) +3 %; effective 8 %; P4 bracket [0,10] → APPROVE."
        ),
    },
    {
        "id": "d-med-5",
        "difficulty": "med",
        "sub_class": "no_action_over_limit_via_bonus",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5010, "status": "qualified", "account_id": 6},
            "customer": {"region": "EMEA", "is_existing": False, "has_overdue_invoices": False},
            "quote": {"amount": 60000, "base_discount_pct": 28},
        },
        "expected_label": "DECLINE",
        "rationale_hint": (
            "Gates pass; B1 (EMEA) adds 5 %; effective 33 % > 30 %. P1 (over-limit cap) fires → "
            "DECLINE. Note that the base discount alone (28 %) would have been ESCALATE_VP."
        ),
    },
    # ── HIGH: five or more rules with precedence conflicts ──
    {
        "id": "d-high-1",
        "difficulty": "high",
        "sub_class": "boundary_inclusive",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5011, "status": "qualified", "account_id": 1},
            "customer": {"region": "EMEA", "is_existing": True, "has_overdue_invoices": False},
            "quote": {"amount": 80000, "base_discount_pct": 22},
        },
        "expected_label": "ESCALATE_VP",
        "rationale_hint": (
            "Gates pass; B1 +5 %, B2 +3 %; effective exactly 30 %. P4's (20,30] bracket is inclusive at "
            "the upper bound — 30 % falls in ESCALATE_VP, not DECLINE. P1 fires only at > 30, so it does "
            "not apply at the boundary."
        ),
    },
    {
        "id": "d-high-2",
        "difficulty": "high",
        "sub_class": "no_action_over_limit_via_bonuses",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5012, "status": "qualified", "account_id": 5},
            "customer": {"region": "EMEA", "is_existing": True, "has_overdue_invoices": False},
            "quote": {"amount": 100000, "base_discount_pct": 25},
        },
        "expected_label": "DECLINE",
        "rationale_hint": (
            "Gates pass; B1 +5 %, B2 +3 %; effective 33 % > 30 %. P1 fires → DECLINE. The base "
            "discount alone (25 %) would have been ESCALATE_VP; both bonuses together push it over the cap."
        ),
    },
    {
        "id": "d-high-3",
        "difficulty": "high",
        "sub_class": "precedence_P3_over_P4",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5013, "status": "qualified", "account_id": 10},
            "customer": {"region": "AMER", "is_existing": False, "has_overdue_invoices": False},
            "quote": {"amount": 4500, "base_discount_pct": 8},
        },
        "expected_label": "ESCALATE_DIRECTOR",
        "rationale_hint": (
            "Gates pass; no bonuses; effective 8 %; quote amount $4,500 < $5,000 AND effective > 5 %. "
            "P3 fires → ESCALATE_DIRECTOR. P3 takes precedence over P4's bracket, which would have "
            "selected APPROVE for an 8 % discount."
        ),
    },
    {
        "id": "d-high-4",
        "difficulty": "high",
        "sub_class": "precedence_P2_over_P4",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5014, "status": "qualified", "account_id": 17},
            "customer": {"region": "EMEA", "is_existing": True, "has_overdue_invoices": False},
            "quote": {"amount": 250000, "base_discount_pct": 5},
        },
        "expected_label": "ESCALATE_REGIONAL_VP",
        "rationale_hint": (
            "Gates pass; B1 +5 %, B2 +3 %; effective 13 %; quote amount $250,000 > $200,000. P2 fires "
            "→ ESCALATE_REGIONAL_VP. P2 takes precedence over P4, which would have selected "
            "ESCALATE_DIRECTOR for the 13 % bracket."
        ),
    },
    {
        "id": "d-high-5",
        "difficulty": "high",
        "sub_class": "no_action_gate_dominates_full_chain",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5015, "status": "qualified", "account_id": 18},
            "customer": {"region": "EMEA", "is_existing": True, "has_overdue_invoices": True},
            "quote": {"amount": 80000, "base_discount_pct": 5},
        },
        "expected_label": "DECLINE",
        "rationale_hint": (
            "Gate G2 (customer.has_overdue_invoices must be false) fails. The complete discount logic "
            "trail (B1, B2, effective 13 %, P4 bracket → ESCALATE_DIRECTOR) is a distractor — gates "
            "evaluate first and dominate everything that follows. DECLINE."
        ),
    },
]


def main() -> None:
    written = 0
    for inst in INSTANCES:
        directory = INPUT_DIR / inst["difficulty"]
        directory.mkdir(parents=True, exist_ok=True)
        record = {
            "id": inst["id"],
            "archetype": "D",
            "difficulty": inst["difficulty"],
            "sub_class": inst.get("sub_class"),
            "instruction": inst["instruction"],
            "quote_request": inst["quote_request"],
            "expected_label": inst["expected_label"],
            "rationale_hint": inst["rationale_hint"],
            "provenance": _provenance(inst.get("sub_class")),
        }
        (directory / f"{inst['id']}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False)
        )
        written += 1
    print(f"Wrote {written} instances under {INPUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
