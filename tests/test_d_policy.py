"""Mechanical gold validation for archetype D (PlanBench principle, protocol A.2).

A deterministic Python implementation of the POLICY_RULES decision tree
(config.py) recomputes the expected decision for every D instance and
compares it to the curated gold label. This guards the instance set against
hand-assignment errors, exactly as the B query-executor regression test
guards the B golds.

The engine is a TEST ARTIFACT only. It must never be wired into the
workflow implementation: archetype D measures whether the LLM applies the
codified rules correctly, so the canonical-minimal workflow is a single LLM
call and the deterministic engine exists solely to verify the ground truth.

Run:
    pytest tests/test_d_policy.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
INSTANCE_DIR = REPO / "data" / "test_inputs" / "d_compliance_decisioning"


def apply_policy(quote_request: dict) -> str:
    """Deterministic reference implementation of POLICY_RULES (config.py)."""
    lead = quote_request["lead"]
    customer = quote_request["customer"]
    quote = quote_request["quote"]

    # GATES — evaluated first; a gate failure is final.
    if lead["status"] != "qualified":  # G1
        return "DECLINE"
    if customer["has_overdue_invoices"]:  # G2
        return "DECLINE"

    # DISCOUNT COMPUTATION
    effective = quote["base_discount_pct"]
    if customer["region"] == "EMEA":  # B1
        effective += 5
    if customer["is_existing"]:  # B2
        effective += 3

    # DECISION RULES — precedence order P1 < P2 < P3 < P4.
    if effective > 30:  # P1
        return "DECLINE"
    if quote["amount"] > 200000:  # P2
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
    files = sorted(INSTANCE_DIR.glob("*/*.json"))
    assert files, f"no D instances found under {INSTANCE_DIR}"
    return [json.loads(f.read_text()) for f in files]


@pytest.mark.parametrize("inst", _instances(), ids=lambda i: i["id"])
def test_gold_matches_policy_engine(inst: dict) -> None:
    """Every curated gold label must equal the engine-computed decision."""
    assert apply_policy(inst["quote_request"]) == inst["expected_label"], (
        f"{inst['id']}: curated gold {inst['expected_label']!r} disagrees with "
        f"the deterministic policy engine — fix the instance or the policy text"
    )


def test_instance_set_shape() -> None:
    """15 instances, 5 per difficulty, exactly 6 DECLINE (no-action) cases."""
    instances = _instances()
    assert len(instances) == 15
    by_difficulty: dict[str, int] = {}
    for inst in instances:
        by_difficulty[inst["difficulty"]] = by_difficulty.get(inst["difficulty"], 0) + 1
    assert by_difficulty == {"low": 5, "med": 5, "high": 5}
    declines = sum(1 for i in instances if i["expected_label"] == "DECLINE")
    assert declines == 6
