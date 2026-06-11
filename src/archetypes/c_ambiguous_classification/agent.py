"""Agent implementation for archetype C: Ambiguous Classification and Disambiguation.

LangGraph ReAct loop with the read-only CRM tools exposed (the same tools
the workflow has access to, per the Phase-2 tool-symmetry invariant). The
agent decides at runtime whether to fetch additional context — the C
instances are constructed to be solvable from the email text alone, so most
runs require no tool calls — and reports its classification in free text
terminated by a ``FINAL_ANSWER:`` line.

The canonical-minimal agent form for a classification task carries the same
information as the workflow's single LLM call but pays two structural costs
the workflow does not: the ReAct system-prompt overhead in every input, and
the absence of an output-format constraint (the label may appear anywhere
in the response and requires regex extraction).
"""

from __future__ import annotations

import json

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from src.archetypes.c_ambiguous_classification.config import (
    AGENT_SYSTEM_PROMPT,
    CATEGORY_DEFINITIONS,
    TEMPERATURE,
    TOOLS,
)
from src.core.llm import get_llm


def build_agent():
    """Construct a ReAct agent for archetype C with the read-only CRM toolset."""
    llm = get_llm(TEMPERATURE)
    system_message = SystemMessage(
        content=AGENT_SYSTEM_PROMPT.format(definitions=CATEGORY_DEFINITIONS)
    )
    return create_react_agent(model=llm, tools=TOOLS, prompt=system_message)


def run_agent(instruction: str, email: dict, config: dict | None = None) -> dict:
    """Execute the agent on a single classification instance.

    Args:
        instruction: The natural-language routing task.
        email: The email record (a dict with sender, subject, body).
        config: LangGraph config, e.g. with the ExecutionLogger callback.

    Returns:
        The agent result dict. The final message content carries the
        classification text including the ``FINAL_ANSWER:`` line.
    """
    agent = build_agent()
    email_json = json.dumps(email, indent=2, ensure_ascii=False)
    user_msg = f"{instruction}\n\nCustomer email:\n{email_json}"
    return agent.invoke(
        {"messages": [("human", user_msg)]},
        config=config or {},
    )
