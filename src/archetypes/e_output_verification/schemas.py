"""Pure data models for archetype E: Output Verification and Quality Control.

The verdict target is the quality of a candidate customer-support response
evaluated against a five-criterion rubric. The workflow emits the
QualityVerdict via ``with_structured_output`` so the label is constrained
to the Literal; the agent reports its verdict in free text and the
ground-truth extractor parses a ``FINAL_ANSWER:`` line.

E is the canonical LLM-as-Judge archetype in the TADF (Table 3, expected
routing: LLM workflow with structured output as the judge). The judge
reads (i) the customer inquiry, (ii) the candidate response, and (iii) the
rubric, and renders one verdict drawn from a ternary scale:

    PASS            — all five rubric criteria are met
    NEEDS_REVISION  — one or two criteria are violated but the response
                      is recoverable with targeted edits
    FAIL            — three or more criteria are violated; the response
                      should not be sent in its current form

The ternary scale follows the WONDERBREAD SOP-Ranking convention of
distinguishing acceptable from recoverable from unacceptable artefacts,
adapted to the customer-support setting.

Source: WONDERBREAD SOP Ranking and Demo Validation (Wornow et al., 2024);
Kourani et al. (2025) self-improvement; TheAgentCompany feedback subtasks
(Xu et al., 2024). The five-criterion rubric is original work that
captures the structural pattern of judge-prompts used in those sources.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

QUALITY_VERDICT = Literal[
    "PASS",
    "NEEDS_REVISION",
    "FAIL",
]


class QualityVerdict(BaseModel):
    """Verdict on a candidate support response under the rubric.

    Retained for the agent path (label extraction target) and as the
    workflow's final output shape; since the per-criterion rebuild the
    workflow derives it deterministically in ``verdict_engine`` rather
    than asking the LLM for it directly.
    """

    label: QUALITY_VERDICT = Field(
        description="Overall quality verdict on the candidate response"
    )
    rationale: str = Field(
        description="One short sentence naming which rubric criteria are violated (or confirming compliance)"
    )


CRITERION_ID = Literal["C1", "C2", "C3", "C4", "C5"]


class CriterionAssessment(BaseModel):
    """The workflow's judgment on ONE rubric criterion, in isolation.

    The per-criterion decomposition is the workflow's structural difference
    from the agent's holistic in-context judgment: each criterion receives
    a dedicated pass/fail decision with cited evidence, and the verdict is
    computed downstream by deterministic code, never by the LLM.
    """

    criterion_id: CRITERION_ID = Field(
        description="The rubric criterion this assessment refers to (C1..C5)"
    )
    passed: bool = Field(
        description="True if the candidate response satisfies this criterion as written, false if it fails it"
    )
    evidence: str = Field(
        description="One sentence citing what in the candidate response satisfies or violates this criterion"
    )


class RubricAssessment(BaseModel):
    """The full per-criterion assessment of one candidate response.

    Must contain exactly one CriterionAssessment for each of C1..C5. The
    workflow's decide node validates this invariant and fails hard on a
    missing, duplicated, or unknown criterion id; the verdict itself is
    derived from the failure count by ``verdict_engine.derive_verdict``.
    """

    assessments: list[CriterionAssessment] = Field(
        description="Exactly five assessments, one per rubric criterion C1, C2, C3, C4, C5, in order"
    )
