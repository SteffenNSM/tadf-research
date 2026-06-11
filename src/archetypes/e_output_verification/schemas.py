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
    """Verdict on a candidate support response under the rubric."""

    label: QUALITY_VERDICT = Field(
        description="Overall quality verdict on the candidate response"
    )
    rationale: str = Field(
        description="One short sentence naming which rubric criteria are violated (or confirming compliance)"
    )
