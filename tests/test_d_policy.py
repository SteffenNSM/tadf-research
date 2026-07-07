"""Mechanical gold validation for archetype D (PlanBench principle, protocol A.2).

This module holds an INDEPENDENT reference implementation of the approval
policy (``apply_policy`` below, a plain hand-written decision tree) and uses
it two ways:

1. It recomputes the expected decision for every D instance and compares it to
   the curated gold label — guarding the instance set against hand-assignment
   errors, exactly as the B query-executor regression test guards the B golds.
2. It cross-checks the PRODUCTION rule engine: after the D redesign (mid
   information availability, iteration log), the workflow no longer applies the
   policy with the LLM. The rules live as machine-readable clauses in the
   Policy Registry (``src/core/tools/policy_data.py``) and are applied by a
   deterministic engine (``rule_engine.evaluate``). The cross-check confirms
   that the clause encoding + engine agree with this independent reference and
   with the curated golds, so a future edit to the clause data cannot silently
   diverge from the intended policy.

The two implementations are deliberately separate code paths: the reference
here is an imperative if-tree; the production path is a generic interpreter
over declarative clauses. Agreement between them on all 15 instances is the
regression guard.

Run:
    pytest tests/test_d_policy.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.archetypes.d_compliance_decisioning.rule_engine import evaluate
from src.core.tools.policy_data import all_clauses

REPO = Path(__file__).resolve().parents[1]
INSTANCE_DIR = REPO / "data" / "test_inputs" / "d_compliance_decisioning"


def _facts(quote_request: dict) -> dict:
    """Flatten a quote_request into the engine's fact keys (mirrors the
    workflow's extract step output)."""
    lead = quote_request["lead"]
    customer = quote_request["customer"]
    quote = quote_request["quote"]
    return {
        "lead_status": lead["status"],
        "region": customer["region"],
        "is_existing": customer["is_existing"],
        "has_overdue_invoices": customer["has_overdue_invoices"],
        "has_credit_hold": customer.get("has_credit_hold", False),
        "is_new_logo": customer.get("is_new_logo", False),
        "segment": customer.get("segment", "Commercial"),
        "amount": quote["amount"],
        "base_discount_pct": quote["base_discount_pct"],
        "term_months": quote.get("term_months", 12),
    }


def apply_policy(quote_request: dict) -> str:
    """Independent reference implementation of the approval policy.

    Mirrors the Policy Registry clause set (``policy_data.py``) as a plain
    imperative decision tree, including the deepened ruleset: gates G3
    (Restricted segment) and G4 (credit hold); bonuses B3 (24-month term), B4
    (APAC region), B5 (new-logo); and the Strategic routing rule P2s at
    precedence 2.5 (between high-value P2 and small-deal P3).
    """
    lead = quote_request["lead"]
    customer = quote_request["customer"]
    quote = quote_request["quote"]
    segment = customer.get("segment", "Commercial")
    term_months = quote.get("term_months", 12)

    # GATES — evaluated first; a gate failure is final.
    if lead["status"] != "qualified":  # G1
        return "DECLINE"
    if customer["has_overdue_invoices"]:  # G2
        return "DECLINE"
    if customer.get("has_credit_hold", False):  # G4
        return "DECLINE"
    if segment == "Restricted":  # G3
        return "DECLINE"

    # DISCOUNT COMPUTATION — bonuses stack.
    effective = quote["base_discount_pct"]
    if customer["region"] == "EMEA":  # B1
        effective += 5
    if customer["is_existing"]:  # B2
        effective += 3
    if term_months >= 24:  # B3
        effective += 4
    if customer["region"] == "APAC":  # B4
        effective += 2
    if customer.get("is_new_logo", False):  # B5
        effective += 3

    # DECISION RULES — precedence P1 < P2 < P2s(2.5) < P3 < P4.
    if effective > 30:  # P1
        return "DECLINE"
    if quote["amount"] > 200000:  # P2
        return "ESCALATE_REGIONAL_VP"
    if segment == "Strategic" and quote["amount"] > 100000:  # P2s
        return "ESCALATE_REGIONAL_VP"
    if quote["amount"] < 5000 and effective > 5:  # P3
        return "ESCALATE_DIRECTOR"
    # P4 brackets: [0, 10] / (10, 20] / (20, 30]
    if effective <= 10:
        return "APPROVE"
    if effective <= 20:
        return "ESCALATE_DIRECTOR"
    return "ESCALATE_VP"


def _instances() -> list[dict]:
    # Only the three difficulty tiers; the robustness/ subdir is scored separately.
    files = sorted(
        f for lvl in ("low", "med", "high") for f in (INSTANCE_DIR / lvl).glob("*.json")
    )
    assert files, f"no D instances found under {INSTANCE_DIR}"
    return [json.loads(f.read_text()) for f in files]


@pytest.mark.parametrize("inst", _instances(), ids=lambda i: i["id"])
def test_gold_matches_policy_engine(inst: dict) -> None:
    """Every curated gold label must equal the reference engine's decision."""
    assert apply_policy(inst["quote_request"]) == inst["expected_label"], (
        f"{inst['id']}: curated gold {inst['expected_label']!r} disagrees with "
        f"the reference policy engine — fix the instance or the policy text"
    )


@pytest.mark.parametrize("inst", _instances(), ids=lambda i: i["id"])
def test_production_engine_matches_gold(inst: dict) -> None:
    """The production registry clauses + rule_engine must reproduce the gold.

    Guards against the Policy Registry clause data drifting from the intended
    policy: the generic interpreter over the fetched clauses must agree with
    both the curated gold and the independent reference implementation.
    """
    label, _ = evaluate(all_clauses(), _facts(inst["quote_request"]))
    assert label == inst["expected_label"], (
        f"{inst['id']}: production engine produced {label!r} but gold is "
        f"{inst['expected_label']!r} — the policy clause data and the curated "
        f"label disagree"
    )
    assert label == apply_policy(inst["quote_request"])


def test_instance_set_shape() -> None:
    """15 instances, 5 per difficulty, 7 DECLINE cases, all carry request_text."""
    instances = _instances()
    assert len(instances) == 15
    by_difficulty: dict[str, int] = {}
    for inst in instances:
        by_difficulty[inst["difficulty"]] = by_difficulty.get(inst["difficulty"], 0) + 1
    assert by_difficulty == {"low": 5, "med": 5, "high": 5}
    declines = sum(1 for i in instances if i["expected_label"] == "DECLINE")
    assert declines == 6
    # The redesign feeds a natural-language request to both paradigms.
    for inst in instances:
        assert inst.get("request_text"), f"{inst['id']} is missing request_text"
