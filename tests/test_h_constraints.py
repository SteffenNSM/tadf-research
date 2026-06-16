"""Mechanical validation for archetype H's deterministic compliance layer.

H's OQS is judge-scored and cannot be unit-tested deterministically, but the
compliance ANCHOR can and must be: these tests prove the constraint checks
fire correctly (length, required points, faithfulness/hallucination,
placeholders, sections, feedback incorporation), and that every instance is
satisfiable by a constructed compliant artefact and is failed by a
constructed non-compliant one. This guards the objective layer the same way
the B executor, D policy engine, and G simulator guard theirs.

Run:
    pytest tests/test_h_constraints.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.archetypes.h_content_drafting.ground_truth import (
    check_compliance,
    count_words,
    extract_numbers,
)

REPO = Path(__file__).resolve().parents[1]
INSTANCE_DIR = REPO / "data" / "test_inputs" / "h_content_drafting"


def _instances() -> list[dict]:
    files = sorted(INSTANCE_DIR.glob("*/*.json"))
    assert files, f"no H instances under {INSTANCE_DIR} (run seed_drafting.py)"
    return [json.loads(f.read_text()) for f in files]


def _compliant_body(inst: dict) -> str:
    """Construct a minimal artefact that satisfies every hard constraint."""
    c = inst["constraints"]
    parts: list[str] = []
    for s in c.get("required_sections", []):
        parts.append(f"{s}:")
    for p in c.get("required_points", []):
        parts.append(p["keywords"][0])
    for req in inst.get("feedback_requirements", []):
        parts.append(req["keywords"][0])
    body = " ".join(parts)
    # pad with neutral filler (no numbers) to reach the min word count
    while count_words(body) < c["min_words"]:
        body += " and the team reviewed the figures together carefully"
    # trim if we overshot the max
    words = body.split()
    if len(words) > c["max_words"]:
        # keep the constraint tokens at the front; truncate filler
        body = " ".join(words[: c["max_words"]])
    return body


def test_instance_set_shape() -> None:
    instances = _instances()
    assert len(instances) == 15
    by_diff: dict[str, int] = {}
    fb: dict[str, set] = {}
    for inst in instances:
        by_diff[inst["difficulty"]] = by_diff.get(inst["difficulty"], 0) + 1
        fb.setdefault(inst["difficulty"], set()).add(len(inst.get("feedback_rounds", [])))
    assert by_diff == {"low": 5, "med": 5, "high": 5}
    assert fb["low"] == {0} and fb["med"] == {1} and fb["high"] == {2}


@pytest.mark.parametrize("inst", _instances(), ids=lambda i: i["id"])
def test_compliant_artifact_passes(inst: dict) -> None:
    body = _compliant_body(inst)
    all_pass, rate, breakdown = check_compliance(inst, "", body)
    assert all_pass, f"{inst['id']}: constructed-compliant artefact failed: {breakdown}"


@pytest.mark.parametrize("inst", _instances(), ids=lambda i: i["id"])
def test_empty_artifact_fails(inst: dict) -> None:
    all_pass, rate, _ = check_compliance(inst, "", "")
    assert not all_pass and rate < 1.0


def test_hallucinated_number_flagged() -> None:
    inst = _instances()[0]  # h-low-1, allowed includes 1,240,000 etc.
    body = _compliant_body(inst) + " Our secret revenue was actually 7777777 euros."
    _, _, breakdown = check_compliance(inst, "", body)
    assert 7777777.0 in breakdown["unsupported_numbers"]


def test_placeholder_flagged() -> None:
    inst = _instances()[0]
    body = _compliant_body(inst) + " [TODO] add more here."
    all_pass, _, breakdown = check_compliance(inst, "", body)
    assert not all_pass and breakdown["no_placeholder"] is False


def test_length_window_enforced() -> None:
    inst = _instances()[0]
    _, _, breakdown = check_compliance(inst, "", "too short")
    assert breakdown["length_ok"] is False


def test_rounding_tolerance_accepts_derived_percent() -> None:
    """h-med-2 derived value 73% (from 35/48) must not be flagged though only
    72.9 / 73 are in allowed_numbers."""
    inst = {i["id"]: i for i in _instances()}["h-med-2"]
    nums = [v for v, sig in extract_numbers("The conversion was 73%.") if sig]
    assert nums == [73.0]
    # 73 is within tolerance of allowed 72.9
    _, _, breakdown = check_compliance(inst, "", _compliant_body(inst) + " 73%")
    assert 73.0 not in breakdown["unsupported_numbers"]


def test_missing_feedback_requirement_fails() -> None:
    """An otherwise-compliant artefact that omits the feedback change fails."""
    inst = {i["id"]: i for i in _instances()}["h-med-1"]
    c = inst["constraints"]
    parts = [p["keywords"][0] for p in c["required_points"]]
    body = " ".join(parts)
    while count_words(body) < c["min_words"]:
        body += " the figures were reviewed by the team in detail again"
    # deliberately omit the feedback requirement tokens (total / strongest / weakest)
    all_pass, _, breakdown = check_compliance(inst, "", body)
    assert not all_pass and breakdown["missing_feedback"]
