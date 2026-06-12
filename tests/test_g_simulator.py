"""Mechanical validation for archetype G (PlanBench principle, protocol A.2).

Three guarantees, mirroring the B query-executor and D policy-engine tests:

1. **Solvability:** every instance's reference plan simulates successfully
   AND satisfies the instance's declarative goal spec — proof that each
   task is achievable within the documented action vocabulary.
2. **Optimum bookkeeping:** the reference plan's length equals the
   documented ``optimal_length`` (the secondary plan-efficiency metric is
   anchored to a real plan, not an estimate).
3. **Precondition discrimination:** representative violations (blocked
   close, unknown record, disallowed column, missing email args, spurious
   extra email) are rejected by the simulator or the goal checker.

Run:
    pytest tests/test_g_simulator.py -v
"""

from __future__ import annotations

import pytest

from experiments.seed_planning import INSTANCES, REFERENCE_PLANS
from src.archetypes.g_strategic_planning.schemas import Plan, PlanStep
from src.archetypes.g_strategic_planning.simulator import score_plan, simulate

_BY_ID = {i["id"]: i for i in INSTANCES}


def _plan(inst_id: str, extra: list[dict] | None = None) -> Plan:
    steps = REFERENCE_PLANS[inst_id] + (extra or [])
    return Plan(steps=[PlanStep(**s) for s in steps], rationale="reference")


@pytest.mark.parametrize("inst", INSTANCES, ids=lambda i: i["id"])
def test_reference_plan_satisfies_goal(inst: dict) -> None:
    score, rationale = score_plan(_plan(inst["id"]), inst["goal"])
    assert score == 1.0, f"{inst['id']}: reference plan fails — {rationale}"


@pytest.mark.parametrize("inst", INSTANCES, ids=lambda i: i["id"])
def test_reference_plan_length_is_documented_optimum(inst: dict) -> None:
    assert len(REFERENCE_PLANS[inst["id"]]) == inst["optimal_length"]


def test_instance_set_shape() -> None:
    assert len(INSTANCES) == 15
    by_diff: dict[str, list[int]] = {}
    for inst in INSTANCES:
        by_diff.setdefault(inst["difficulty"], []).append(inst["optimal_length"])
    assert {k: len(v) for k, v in by_diff.items()} == {"low": 5, "med": 5, "high": 5}
    assert all(n == 3 for n in by_diff["low"])
    assert all(5 <= n <= 7 for n in by_diff["med"])
    assert all(15 <= n <= 18 for n in by_diff["high"])


def test_blocked_close_is_rejected() -> None:
    """attempt_close_case on a transfer_count>3 case invalidates the plan."""
    plan = Plan(steps=[PlanStep(tool="attempt_close_case",
                                args={"case_id": 7, "resolution_summary": "x"})],
                rationale="t")
    sim = simulate(plan)
    assert not sim["valid"] and "escalation" in sim["reason"]


def test_unknown_record_and_bad_column_rejected() -> None:
    bad_id = Plan(steps=[PlanStep(tool="db_update",
                                  args={"table": "cases", "record_id": 99999,
                                        "updates": {"status": "Closed"}})], rationale="t")
    assert not simulate(bad_id)["valid"]
    bad_col = Plan(steps=[PlanStep(tool="db_update",
                                   args={"table": "cases", "record_id": 5,
                                         "updates": {"subject": "hacked"}})], rationale="t")
    assert not simulate(bad_col)["valid"]


def test_incomplete_email_rejected() -> None:
    plan = Plan(steps=[PlanStep(tool="send_email",
                                args={"recipient": "a@b.c", "subject": "s"})], rationale="t")
    assert not simulate(plan)["valid"]


def test_spurious_email_fails_goal() -> None:
    """Side-effect discipline: one extra off-target email flips the goal check."""
    inst = _BY_ID["g-low-1"]
    extra = [{"tool": "send_email",
              "args": {"recipient": "noone@example.com", "subject": "extra", "body": "x"}}]
    score, _ = score_plan(_plan("g-low-1", extra), inst["goal"])
    assert score == 0.0


def test_capacity_violation_fails_goal() -> None:
    """g-high-2: piling 3+ cases onto one target agent fails agent_capacity."""
    inst = _BY_ID["g-high-2"]
    steps = []
    from experiments.seed_planning import _CASES  # noqa: PLC0415
    for cid in (31, 32, 53, 78, 93, 98):
        steps.append({"tool": "db_update", "args": {"table": "cases", "record_id": cid,
                      "updates": {"agent_id": 2,
                                  "transfer_count": (_CASES[cid].get("transfer_count") or 0) + 1}}})
    ref = REFERENCE_PLANS["g-high-2"]
    rest = [s for s in ref if s["tool"] != "db_update"]
    # one owner email (only agent 2 received cases)
    rest = [s for s in rest if not (s["tool"] == "send_email"
                                    and s["args"]["subject"] == "Cases reassigned to you")]
    rest.append({"tool": "send_email", "args": {"recipient": "agent02@atlas.com",
                 "subject": "Cases reassigned to you", "body": "x"}})
    plan = Plan(steps=[PlanStep(**s) for s in steps + rest], rationale="t")
    score, rationale = score_plan(plan, inst["goal"])
    assert score == 0.0
    assert rationale["goal_breakdown"]["agent_capacity"] is False
