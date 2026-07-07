"""Workflow for archetype E: per-criterion judgment plus deterministic verdict engine.

Rebuilt from the canonical-minimal single judge call (IT-022 baseline). The
rubric's verdict rule (0 failures = PASS, 1-2 = NEEDS_REVISION, 3+ = FAIL)
is arithmetic, and the cross-archetype principle from B (IT-043) and D
(IT-041/IT-045) is to reserve the LLM for the soft step and give the
computation to code. The LLM therefore judges each of the five criteria in
isolation (pass/fail plus cited evidence) and never sees the count rule
applied; the deterministic engine derives the verdict.

Graph topology:
    [assess] -> [decide] -> END
      LLM        det. engine

- assess (LLM): one structured-output call (RubricAssessment via function
  calling — free-text JSON parsing is a known whole-run killer, IT-043)
  evaluating the five criteria independently over the inquiry and the
  candidate response.
- decide (deterministic): validates that exactly one assessment per
  criterion C1..C5 arrived (hard failure otherwise), collects the failed
  ids, and derives the verdict through ``verdict_engine.derive_verdict``.
  The per-criterion assessments are persisted in the output for forensic
  scoring against the gold ``criterion_failures``.

The agent, by contrast, applies the whole rubric holistically in one
context, including the counting. The paradigm contrast E measures is thus
decomposed judgment plus engine aggregation versus holistic in-context
judgment — a genuine locus-of-control difference, replacing the degenerate
single-call-vs-single-call comparison of the IT-022 design.
"""

from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.e_output_verification.config import (
    ASSESS_PROMPT,
    EVALUATION_RUBRIC,
    TEMPERATURE,
)
from src.archetypes.e_output_verification.schemas import (
    QualityVerdict,
    RubricAssessment,
)
from src.archetypes.e_output_verification.verdict_engine import (
    derive_verdict,
    validate_assessments,
)
from src.core.llm import get_llm


def assess(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 1 (LLM): judge each rubric criterion independently."""
    llm = get_llm(TEMPERATURE).with_structured_output(
        RubricAssessment, method="function_calling"
    )
    inquiry_json = json.dumps(state["inquiry"], indent=2, ensure_ascii=False)
    candidate_json = json.dumps(state["candidate_response"], indent=2, ensure_ascii=False)
    result: RubricAssessment = llm.invoke(
        ASSESS_PROMPT.format(
            rubric=EVALUATION_RUBRIC,
            inquiry=inquiry_json,
            candidate_response=candidate_json,
            instruction=state["instruction"],
        )
    )
    return {**state, "assessments": [a.model_dump() for a in result.assessments]}


def decide(state: dict) -> dict:
    """Node 2 (deterministic): count failures and derive the verdict."""
    failed = validate_assessments(state["assessments"])
    label, rationale = derive_verdict(failed)
    result = QualityVerdict(label=label, rationale=rationale)
    output = {
        **result.model_dump(),
        "failed_criteria": failed,
        "assessments": state["assessments"],
    }
    return {**state, "output": output, "completed": True}


def build_workflow():
    """Construct and compile the archetype E assess-then-decide workflow."""
    graph = StateGraph(dict)
    graph.add_node("assess", assess)
    graph.add_node("decide", decide)
    graph.set_entry_point("assess")
    graph.add_edge("assess", "decide")
    graph.add_edge("decide", END)
    return graph.compile()


workflow = build_workflow()
