"""Pure data models for archetype H: Content and Document Drafting and Refinement.

The deliverable of an H task is an open-form text artefact (a short post, an
email, or a multi-section report) generated from an inline data table and a
set of writing constraints (format, length window, tonality, audience,
framing). Output Ambiguity is high by construction: many distinct artefacts
satisfy the same constraint set, so there is no single gold output. Scoring
is therefore dual (see ``ground_truth.py`` and ``judge.py``):

1. a deterministic COMPLIANCE layer over the mechanically checkable
   constraints (required data points present, no fabricated figures, length
   window, required sections, feedback incorporation), and
2. a frozen-prompt LLM-judge OQS over the soft constraints (tonality,
   audience fit, coherence, conciseness) — the protocol-specified success
   metric for H (Appendix A.7), validated against a human sample by
   Cohen's weighted kappa (>= 0.6).

Information Availability is HIGH: the data table is inline in the brief, not
in the database. This keeps H distinct from B (structured retrieval over the
DB) and G (planning over DB state) — no read stage exists for either
paradigm, and the paradigm contrast is purely the refinement structure
(fixed pipeline vs runtime-controlled self-revision).

Source: WONDERBREAD SOP Generation / SOP Improvement (Wornow et al., 2024);
TheAgentCompany report drafting (Xu et al., 2024). Briefs, tables, and
constraints are author-constructed (IT-017 honesty rule).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Draft(BaseModel):
    """A single drafting artefact produced by the workflow or the agent."""

    title: str = Field(
        default="",
        description="Optional title or subject line for the artefact (e.g. an email subject).",
    )
    body: str = Field(
        description="The full text of the artefact: the post, email, or report body."
    )


class AgentTurn(BaseModel):
    """One agent turn: a (re)written draft plus a runtime control decision.

    Each turn rewrites the full artefact and decides whether to keep
    refining it or submit it for the current round. The ``decision`` field
    is the runtime-resolved conditional edge that makes the agent paradigm
    an agent (protocol A.3): the number of self-revisions is chosen by the
    LLM at execution time, not fixed by the graph as in the workflow.
    """

    title: str = Field(default="", description="Title or subject line for the artefact.")
    body: str = Field(description="The full current text of the artefact.")
    decision: str = Field(
        description="Either 'revise' (this draft can still be improved) or 'submit' (it satisfies every constraint and is ready)."
    )
    critique: str = Field(
        default="",
        description="If revising, one sentence on what to improve next; empty when submitting.",
    )
