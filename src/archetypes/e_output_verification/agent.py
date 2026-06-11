"""Agent implementation for archetype E: Output Verification and Quality Control.

LangGraph ReAct loop with the read-only CRM tools exposed (the same tools
the workflow has access to, per the Phase-2 tool-symmetry invariant). The
agent decides at runtime whether to fetch additional context — the E
instances are constructed to be solvable from the inquiry and candidate
response alone, so most runs require no tool calls — and reports its
verdict in free text terminated by a ``FINAL_ANSWER:`` line.

The agent paradigm carries the same information as the workflow's single
LLM call but pays the ReAct system-prompt overhead and the absence of an
output-format constraint. The interesting empirical question for E,
following the D finding that the workflow's structured `rationale` field
forced visible reasoning that the agent's terse FINAL_ANSWER skipped, is
whether the LLM-as-Judge setup amplifies, dampens, or inverts that effect.
"""

from __future__ import annotations

import json

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from src.archetypes.e_output_verification.config import (
    AGENT_SYSTEM_PROMPT,
    EVALUATION_RUBRIC,
    TEMPERATURE,
    TOOLS,
)
from src.core.llm import get_llm


def build_agent():
    """Construct a ReAct agent for archetype E with the read-only CRM toolset."""
    llm = get_llm(TEMPERATURE)
    system_message = SystemMessage(
        content=AGENT_SYSTEM_PROMPT.format(rubric=EVALUATION_RUBRIC)
    )
    return create_react_agent(model=llm, tools=TOOLS, prompt=system_message)


def run_agent(
    instruction: str,
    inquiry: dict,
    candidate_response: dict,
    config: dict | None = None,
) -> dict:
    """Execute the agent on a single verification instance.

    Args:
        instruction: The natural-language quality-review task.
        inquiry: The customer inquiry (sender, subject, body, metadata).
        candidate_response: The agent-drafted response (subject, body).
        config: LangGraph config, e.g. with the ExecutionLogger callback.

    Returns:
        The agent result dict. The final message content carries the
        verdict text including the ``FINAL_ANSWER:`` line.
    """
    agent = build_agent()
    inquiry_json = json.dumps(inquiry, indent=2, ensure_ascii=False)
    candidate_json = json.dumps(candidate_response, indent=2, ensure_ascii=False)
    user_msg = (
        f"{instruction}\n\n"
        f"Customer inquiry:\n{inquiry_json}\n\n"
        f"Candidate response (drafted by an agent):\n{candidate_json}"
    )
    return agent.invoke(
        {"messages": [("human", user_msg)]},
        config=config or {},
    )
