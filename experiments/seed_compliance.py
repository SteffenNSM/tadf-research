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


def _render_request_text(qr: dict) -> str:
    """Render a structured quote request as a natural-language email.

    The D redesign lowers information availability to mid: the workflow and
    agent receive the request as free text (the policy is fetched separately
    from the Policy Registry). This renderer embeds all six policy-relevant
    facts — lead status, region, existing/new, overdue invoices, amount, base
    discount — unambiguously in prose, so the only linguistic work is
    extraction, not disambiguation (the latter is archetype C's axis).
    """
    lead = qr["lead"]
    cust = qr["customer"]
    quote = qr["quote"]
    existing_phrase = (
        "an existing customer" if cust["is_existing"] else "a new (non-existing) customer"
    )
    new_logo_phrase = (
        " This deal is a new-logo acquisition." if cust.get("is_new_logo") else ""
    )
    overdue_phrase = (
        "has overdue invoices outstanding"
        if cust["has_overdue_invoices"]
        else "has no overdue invoices on file"
    )
    credit_phrase = (
        "is on a credit hold"
        if cust.get("has_credit_hold")
        else "is not on any credit hold"
    )
    return (
        f"Subject: Quote approval request — lead {lead['id']}\n\n"
        f"Hi Compliance team,\n\n"
        f"Could you run our quote approval policy on the request below and let "
        f"me know the decision?\n\n"
        f"The lead (ID {lead['id']}) is currently marked \"{lead['status']}\" in "
        f"the CRM. The customer is in the {cust['region']} region, is "
        f"{existing_phrase}, sits in the {cust['segment']} segment, "
        f"{overdue_phrase}, and {credit_phrase}. The deal is for "
        f"${quote['amount']:,} over a {quote['term_months']}-month term, with a "
        f"requested base discount of {quote['base_discount_pct']}%.{new_logo_phrase}\n\n"
        f"Thanks,\nSales Operations"
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
    # ── HIGH: full-ruleset reconciliation. Each requires evaluating ~10 rules --
    #    four gates (G1 lead, G2 overdue, G3 segment, G4 credit hold), up to three
    #    of the five bonuses (B1 EMEA, B2 loyalty, B3 term, B4 APAC, B5 new-logo),
    #    and precedence across P1 cap / P2 high-value / P2s strategic / P3 small /
    #    P4 brackets -- plus two distractor policies that must be ignored. ──
    {
        "id": "d-high-1",
        "difficulty": "high",
        "sub_class": "boundary_inclusive_triple_bonus",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5011, "status": "qualified", "account_id": 1},
            "customer": {"region": "EMEA", "is_existing": True, "has_overdue_invoices": False, "has_credit_hold": False, "is_new_logo": False, "segment": "Commercial"},
            "quote": {"amount": 80000, "base_discount_pct": 18, "term_months": 24},
        },
        "expected_label": "ESCALATE_VP",
        "rationale_hint": (
            "All four gates pass. Of the five bonuses, B1 (EMEA +5), B2 (loyalty +3), B3 (24-month +4) "
            "fire while B4/B5 do not: effective = 18 + 12 = exactly 30 %. P1 fires only above 30, so the "
            "(20,30] bracket applies inclusively → ESCALATE_VP."
        ),
    },
    {
        "id": "d-high-2",
        "difficulty": "high",
        "sub_class": "no_action_over_limit_via_three_bonuses",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5012, "status": "qualified", "account_id": 5},
            "customer": {"region": "EMEA", "is_existing": True, "has_overdue_invoices": False, "has_credit_hold": False, "is_new_logo": False, "segment": "Commercial"},
            "quote": {"amount": 80000, "base_discount_pct": 20, "term_months": 24},
        },
        "expected_label": "DECLINE",
        "rationale_hint": (
            "All four gates pass; B1 +5, B2 +3, B3 +4 add 12 to base 20 % → effective 32 % > 30 %. P1 "
            "(over-limit cap) fires → DECLINE. The base alone (20 %) would have been ESCALATE_VP; the "
            "three stacking bonuses push it over the cap."
        ),
    },
    {
        "id": "d-high-3",
        "difficulty": "high",
        "sub_class": "new_bonuses_apac_newlogo_strategic_regional_vp",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5013, "status": "qualified", "account_id": 10},
            "customer": {"region": "APAC", "is_existing": False, "has_overdue_invoices": False, "has_credit_hold": False, "is_new_logo": True, "segment": "Strategic"},
            "quote": {"amount": 150000, "base_discount_pct": 8, "term_months": 24},
        },
        "expected_label": "ESCALATE_REGIONAL_VP",
        "rationale_hint": (
            "All four gates pass; B4 (APAC +2), B5 (new-logo +3), B3 (24-month +4) fire → effective 17 %. "
            "The deal is $150,000: below the $200,000 high-value threshold (P2) but Strategic and above "
            "$100,000, so P2s (precedence 2.5) fires → ESCALATE_REGIONAL_VP, overriding the (10,20] "
            "bracket. Exercises the two new bonuses B4/B5."
        ),
    },
    {
        "id": "d-high-4",
        "difficulty": "high",
        "sub_class": "no_action_credit_hold_gate_dominates_full_chain",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5014, "status": "qualified", "account_id": 17},
            "customer": {"region": "EMEA", "is_existing": True, "has_overdue_invoices": False, "has_credit_hold": True, "is_new_logo": False, "segment": "Commercial"},
            "quote": {"amount": 80000, "base_discount_pct": 15, "term_months": 24},
        },
        "expected_label": "DECLINE",
        "rationale_hint": (
            "Gate G4 fires: the customer is on a credit hold → DECLINE before any discount logic. The "
            "complete trail (B1 +5, B2 +3, B3 +4 → effective 27 %, P4 (20,30] → ESCALATE_VP) is a "
            "distractor; a compliance gate dominates everything that follows. Exercises the new G4 gate."
        ),
    },
    {
        "id": "d-high-5",
        "difficulty": "high",
        "sub_class": "precedence_P2_high_value_over_bracket",
        "instruction": "Apply the approval policy to this quote request and return the required decision.",
        "quote_request": {
            "lead": {"id": 5015, "status": "qualified", "account_id": 18},
            "customer": {"region": "EMEA", "is_existing": True, "has_overdue_invoices": False, "has_credit_hold": False, "is_new_logo": False, "segment": "Commercial"},
            "quote": {"amount": 250000, "base_discount_pct": 5, "term_months": 24},
        },
        "expected_label": "ESCALATE_REGIONAL_VP",
        "rationale_hint": (
            "All four gates pass; B1 +5, B2 +3, B3 +4 → effective 17 %. The deal is $250,000 > $200,000, "
            "so P2 (high-value, precedence 2) fires → ESCALATE_REGIONAL_VP, overriding the (10,20] "
            "bracket P4 would otherwise choose. Precedence of P2 over P4 on top of three-bonus stacking."
        ),
    },
]


def main() -> None:
    written = 0
    for inst in INSTANCES:
        # Neutral defaults for the segment/term fields added in the
        # rule-depth extension: Low/Med instances carry segment="Commercial"
        # (neither the Restricted gate G3 nor the Strategic routing P2s fires)
        # and term_months=12 (the 24-month bonus B3 does not fire), so their
        # gold labels are unchanged. High instances set these explicitly.
        inst["quote_request"]["customer"].setdefault("segment", "Commercial")
        inst["quote_request"]["customer"].setdefault("has_credit_hold", False)
        inst["quote_request"]["customer"].setdefault("is_new_logo", False)
        inst["quote_request"]["quote"].setdefault("term_months", 12)
        directory = INPUT_DIR / inst["difficulty"]
        directory.mkdir(parents=True, exist_ok=True)
        record = {
            "id": inst["id"],
            "archetype": "D",
            "difficulty": inst["difficulty"],
            "sub_class": inst.get("sub_class"),
            "instruction": inst["instruction"],
            "quote_request": inst["quote_request"],
            "request_text": _render_request_text(inst["quote_request"]),
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
