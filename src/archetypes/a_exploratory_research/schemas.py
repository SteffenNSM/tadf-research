"""Pure data models for archetype A.

Separated from ``config.py`` so the structured outputs carry no framework
dependencies and can be unit-tested with pydantic alone.
"""

from pydantic import BaseModel, Field


class SearchPlan(BaseModel):
    """A list of search queries the workflow will execute upfront.

    Produced by the ``plan_searches`` node. The workflow commits to this plan
    before seeing any results, which is the defining constraint that
    differentiates this archetype's workflow from its agent.
    """

    rationale: str = Field(
        description="One sentence explaining what each query targets, for traceability"
    )
    queries: list[str] = Field(
        description="The search queries to run; choose 2-5 for simple questions, 5-8 for complex ones"
    )


class ResearchAnswer(BaseModel):
    """The structured answer to a research question."""

    answer: str = Field(
        description="The final, concise answer. A short string: a number, name, year, or short phrase."
    )
    sources: list[str] = Field(
        default_factory=list,
        description="URLs of the web sources that support the answer",
    )
