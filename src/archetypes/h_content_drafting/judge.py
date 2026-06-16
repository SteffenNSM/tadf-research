"""Frozen-prompt LLM judge for archetype H (OQS, protocol A.7).

The judge scores a single artefact on five 1–5 criteria under a frozen
prompt template at temperature 0, using the same backbone model as the
experiment (gpt-5.2). It is blind to which paradigm produced the artefact
(no paradigm label appears in the input) and sees one artefact at a time
(absolute scoring, not pairwise), with the instance's tonality/audience/
framing parameters filled into the otherwise-frozen template.

Bias controls (documented in IT-025):
- No paradigm label in the judge input.
- The rubric explicitly instructs not to reward length and to penalize
  padding via the conciseness criterion, countering verbosity bias.
- Same model, frozen template, temperature 0 for every artefact.
- Self-preference (gpt-5.2 generates and judges) is symmetric across the
  workflow and agent outputs and therefore largely cancels in the W-vs-A
  contrast; it is recorded as a limitation.

The OQS is the mean of the five criteria, in [1, 5]. Protocol A.7 requires
validation against a 20% human-rated sample by Cohen's weighted kappa
(>= 0.6); the human-rating template is produced by
``experiments/validate_h.py`` for that pass.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.archetypes.h_content_drafting.config import JUDGE_PROMPT, render_table
from src.core.llm import get_llm


class JudgeScores(BaseModel):
    """Per-criterion 1–5 scores for one artefact."""

    completeness: int = Field(description="1–5: conveys the substance using the table data")
    responsiveness: int = Field(description="1–5: reflects the reviewer feedback (5 if none was given)")
    coherence: int = Field(description="1–5: logical organization and structure for the format")
    tone_audience: int = Field(description="1–5: matches required tonality and suits the audience")
    conciseness: int = Field(description="1–5: free of padding and redundancy")
    justification: str = Field(description="One sentence explaining the scores")

    def mean(self) -> float:
        """OQS: mean of the five criteria, in [1, 5]."""
        return (
            self.completeness
            + self.responsiveness
            + self.coherence
            + self.tone_audience
            + self.conciseness
        ) / 5.0


def judge_artifact(inst: dict, title: str, body: str) -> JudgeScores:
    """Score one artefact against its instance brief (frozen template, temp 0)."""
    c = inst["constraints"]
    feedback_block = ""
    rounds = inst.get("feedback_rounds", [])
    if rounds:
        joined = "\n".join(f"- {fb}" for fb in rounds)
        feedback_block = f"\nReviewer feedback that was given during drafting:\n{joined}\n"
    llm = get_llm(temperature=0.0).with_structured_output(JudgeScores)
    prompt = JUDGE_PROMPT.format(
        format=inst["format"],
        audience=c["audience"],
        tonality=c["tonality"],
        framing=c.get("framing", "(none specified)"),
        min_words=c["min_words"],
        max_words=c["max_words"],
        table=render_table(inst["table"]),
        feedback_block=feedback_block,
        title=title or "(none)",
        body=body,
    )
    return llm.invoke(prompt)
