"""Mechanical tests for archetype E's deterministic verdict engine.

Two layers, mirroring the D test strategy (test_d_policy.py):

1. Engine unit tests: the count rule's boundaries (0 / 1 / 2 / 3 / 5
   failures), the fail-closed validation (unknown and duplicate ids), and
   the assessment-set invariant (exactly one assessment per criterion).
2. Gold self-test: for every seeded E instance, the engine applied to the
   instance's ``criterion_failures`` gold must reproduce the instance's
   ``expected_label``. This machine-verifies the golds through the same
   code path the workflow uses, before any LLM run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.archetypes.e_output_verification.ground_truth import score_criteria
from src.archetypes.e_output_verification.verdict_engine import (
    CRITERIA,
    derive_verdict,
    validate_assessments,
)

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "e_output_verification"


# ── 1. Engine unit tests ──


def test_zero_failures_is_pass():
    label, rationale = derive_verdict([])
    assert label == "PASS"
    assert "met" in rationale


@pytest.mark.parametrize("failed", [["C1"], ["C2", "C5"]])
def test_one_or_two_failures_is_needs_revision(failed):
    label, _ = derive_verdict(failed)
    assert label == "NEEDS_REVISION"


@pytest.mark.parametrize(
    "failed",
    [["C1", "C2", "C3"], ["C1", "C2", "C3", "C4"], ["C1", "C2", "C3", "C4", "C5"]],
)
def test_three_or_more_failures_is_fail(failed):
    label, _ = derive_verdict(failed)
    assert label == "FAIL"


def test_boundary_two_vs_three_is_the_verdict_edge():
    assert derive_verdict(["C1", "C2"])[0] == "NEEDS_REVISION"
    assert derive_verdict(["C1", "C2", "C3"])[0] == "FAIL"


def test_rationale_names_failed_criteria_in_rubric_order():
    _, rationale = derive_verdict(["C4", "C1"])
    assert "C1, C4" in rationale


def test_unknown_id_raises():
    with pytest.raises(ValueError, match="unknown criterion"):
        derive_verdict(["C9"])


def test_duplicate_id_raises():
    with pytest.raises(ValueError, match="duplicate"):
        derive_verdict(["C1", "C1"])


# ── validate_assessments: the decide node's input invariant ──


def _assessments(failed: list[str]) -> list[dict]:
    return [
        {"criterion_id": c, "passed": c not in failed, "evidence": "x"}
        for c in CRITERIA
    ]


def test_validate_assessments_returns_failed_ids_in_order():
    assert validate_assessments(_assessments(["C5", "C2"])) == ["C2", "C5"]


def test_validate_assessments_all_pass():
    assert validate_assessments(_assessments([])) == []


def test_validate_assessments_missing_criterion_raises():
    broken = _assessments([])[:4]
    with pytest.raises(ValueError, match="exactly"):
        validate_assessments(broken)


def test_validate_assessments_duplicate_criterion_raises():
    broken = _assessments([])[:4] + [_assessments([])[0]]
    with pytest.raises(ValueError, match="exactly"):
        validate_assessments(broken)


def test_validate_assessments_unknown_id_raises():
    broken = _assessments([])
    broken[0]["criterion_id"] = "C7"
    with pytest.raises(ValueError, match="exactly"):
        validate_assessments(broken)


# ── score_criteria ──


def test_score_criteria_perfect_match():
    acc, false_fails, missed = score_criteria(["C1", "C3"], ["C1", "C3"])
    assert acc == 1.0 and false_fails == [] and missed == []


def test_score_criteria_attribution():
    acc, false_fails, missed = score_criteria(["C1", "C2"], ["C2", "C4"])
    assert acc == 3 / 5
    assert false_fails == ["C1"]
    assert missed == ["C4"]


# ── 2. Gold self-test over the seeded instances ──


def _instances() -> list[dict]:
    files = sorted(IN.glob("*/e-*.json"))
    assert files, f"no E instances found under {IN}"
    return [json.loads(f.read_text()) for f in files]


@pytest.mark.parametrize("inst", _instances(), ids=lambda i: i["id"])
def test_gold_self_test_engine_reproduces_expected_label(inst):
    label, _ = derive_verdict(inst["criterion_failures"])
    assert label == inst["expected_label"], (
        f"{inst['id']}: engine derives {label!r} from gold criterion_failures "
        f"{inst['criterion_failures']!r} but expected_label is {inst['expected_label']!r}"
    )
