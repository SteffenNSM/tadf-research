"""Ground-truth evaluation for archetype A (LLM-as-judge, OQS).

Because A's outputs are short free-form research answers, exact string matching
is too brittle (a candidate like "Mount Everest, 8849 metres" should match the
gold "8849"). A frozen-prompt LLM judge compares the candidate to the gold
answer and returns a binary verdict. The judge uses the same backbone model as
the experiment, with temperature 0 for reproducibility.

The protocol (Appendix A.7) requires the judge to be validated against a 20%
human-reviewed sample using Cohen's weighted kappa, with kappa >= 0.6 as the
acceptance threshold. That validation pass is performed once the full A sweep
is complete and is recorded in the iteration log.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.core.llm import get_llm

JUDGE_PROMPT = """You evaluate a candidate answer against the gold answer to a research question.

A candidate is CORRECT if it expresses the same factual content as the gold answer. The following normalizations are accepted:
- Different wording, capitalization, or formatting of the same fact.
- Different units, after sensible conversion to the same physical quantity.
- Different numeric precision for the SAME measurement. Examples: 8849, 8848.86, and 8848 all refer to the same Mount Everest elevation; 100 °C and 100.0 °C are equivalent.
- Surrounding prose, as long as the core answer is present and unambiguous.
- For list answers (for example "A, B, C"), the candidate is correct if it includes all of the listed entities. If the question specifies an ordering (chronological, descending by some quantity, in the order they happened), the candidate's order must match the gold; otherwise any order is acceptable.
- For compound answers that contain two facts (for example "Argentina, Buenos Aires"), the candidate is correct if it gives both facts correctly.

A candidate is INCORRECT if any of the following holds:
- It states a different fact, names a different entity, or gives a different categorical value. In particular, different YEARS (for example 2002 vs 2003) and different DISCRETE IDENTIFIERS (different names, different chemical symbols, different city names) are NOT precision variants and count as different facts.
- For list answers, it misses any of the required entities, gives a wrong entity, or violates a required ordering.
- For compound answers, it gives only one of the required facts.
- It expresses uncertainty (for example "I don't know" or "I could not determine").
- It omits the core answer.

Question: {question}
Gold answer: {gold}
Candidate answer: {candidate}

Return a JudgeVerdict with the boolean field `correct` and a one-sentence rationale."""


class JudgeVerdict(BaseModel):
    """The judge's binary verdict on a candidate answer."""

    correct: bool = Field(description="True if the candidate matches the gold in substance")
    rationale: str = Field(description="One sentence explaining the verdict")


def judge(question: str, gold: str, candidate: str) -> JudgeVerdict:
    """Ask the LLM judge to compare a candidate answer to the gold answer."""
    llm = get_llm(temperature=0.0).with_structured_output(JudgeVerdict)
    return llm.invoke(
        JUDGE_PROMPT.format(question=question, gold=gold, candidate=candidate)
    )


def score(predicted: str, ground_truth: dict, question: str) -> tuple[float, str]:
    """Return the OQS score (1.0 correct, 0.0 incorrect) and the judge rationale.

    Args:
        predicted: The model's answer (workflow output's value or agent message).
        ground_truth: The instance ground-truth dict with at least a ``value`` key.
        question: The original research question, needed for the judge.
    """
    gold = str(ground_truth["value"])
    verdict = judge(question=question, gold=gold, candidate=str(predicted))
    return (1.0 if verdict.correct else 0.0), verdict.rationale
