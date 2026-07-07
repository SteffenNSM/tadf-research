"""Deterministic verdict engine for archetype E (framework-free).

Derives the ternary quality verdict from the set of failed rubric criteria.
This is the component that gives the rebuilt E workflow a genuine
locus-of-control difference from the agent: the LLM judges each criterion
in isolation (the soft step), and *this engine* — not the LLM — applies the
rubric's count rule (the computation). The agent, by contrast, applies the
whole rubric in-context, including the counting.

Pattern precedent: archetype B's SQL executor (IT-043) and archetype D's
rule engine (IT-041/IT-045) — reserve the LLM for the judgment or
linguistic step, never the computation. IT-022's error analysis motivates
the split for E specifically: every observed verdict error was criterion
miscalibration followed by a correctly applied count rule on the wrong
count, so the count rule itself must be beyond error by construction.

Verdict rule (rubric, config.EVALUATION_RUBRIC):
    0 failed criteria      -> PASS
    1 or 2 failed criteria -> NEEDS_REVISION
    3 or more              -> FAIL

The engine fails closed: unknown or duplicated criterion ids raise
``ValueError`` rather than being silently ignored, the same stance as D's
engine (a malformed assessment set is a hard failure, not a default).
"""

from __future__ import annotations

#: The rubric's criterion identifiers. Mirrors CRITERION_ID in schemas.py
#: and the ``criterion_failures`` gold lists in the instance JSON.
CRITERIA = ["C1", "C2", "C3", "C4", "C5"]


def derive_verdict(failed_criteria: list[str]) -> tuple[str, str]:
    """Map the failed-criteria set to ``(label, rationale)``.

    Args:
        failed_criteria: The criterion ids judged as failed. May be empty.

    Returns:
        The verdict label (PASS / NEEDS_REVISION / FAIL) and a one-sentence
        rationale naming the failed criteria (or confirming compliance).

    Raises:
        ValueError: If an id is not one of C1..C5 or appears more than once.
    """
    unknown = [c for c in failed_criteria if c not in CRITERIA]
    if unknown:
        raise ValueError(f"unknown criterion id(s) {unknown!r}; expected {CRITERIA}")
    if len(set(failed_criteria)) != len(failed_criteria):
        raise ValueError(f"duplicate criterion id in {failed_criteria!r}")

    n = len(failed_criteria)
    if n == 0:
        return "PASS", "All five rubric criteria are met."
    ordered = sorted(failed_criteria, key=CRITERIA.index)
    if n <= 2:
        return (
            "NEEDS_REVISION",
            f"Criteria {', '.join(ordered)} failed ({n} failure{'s' if n > 1 else ''}); recoverable with targeted edits.",
        )
    return (
        "FAIL",
        f"Criteria {', '.join(ordered)} failed ({n} failures); the response should not be sent in its current form.",
    )


def validate_assessments(assessments: list[dict]) -> list[str]:
    """Validate a per-criterion assessment set and return the failed ids.

    Args:
        assessments: Dicts with ``criterion_id`` and ``passed`` keys (the
            dumped form of ``schemas.CriterionAssessment``).

    Returns:
        The list of criterion ids whose ``passed`` is false, in rubric order.

    Raises:
        ValueError: If the set is not exactly one assessment per criterion
            C1..C5 (missing, duplicated, or unknown ids).
    """
    ids = [a.get("criterion_id") for a in assessments]
    if sorted(ids, key=lambda x: (x is None, x)) != CRITERIA:
        raise ValueError(
            f"assessment set must cover exactly {CRITERIA}, got {ids!r}"
        )
    return [a["criterion_id"] for a in sorted(assessments, key=lambda a: a["criterion_id"]) if not a["passed"]]
