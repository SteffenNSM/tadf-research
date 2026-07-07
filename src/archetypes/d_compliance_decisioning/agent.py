"""Agent implementation for archetype D: Compliance and Rule-Based Decisioning.

LangGraph ReAct loop with the Policy Registry tools exposed (the same tools
the workflow uses, per the Phase-2 tool-symmetry invariant A.3). Unlike the
workflow — which loads the whole policy in a fixed order and applies it with a
deterministic engine — the agent decides at runtime which policy documents to
read, reads them, and applies the rules in-context before committing to a
decision terminated by a ``FINAL_ANSWER:`` line.

This is the locus-of-control contrast the experiment measures: under high
error consequence, does the agent's runtime retrieval-and-reasoning match the
workflow's deterministic engine, or does in-context rule application drift on
the deeper precedence chains? The answer is left to the data.
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from src.archetypes.d_compliance_decisioning.config import (
    AGENT_SYSTEM_PROMPT,
    TEMPERATURE,
    TOOLS,
)
from src.core.llm import get_llm


def build_agent():
    """Construct a ReAct agent for archetype D with the Policy Registry toolset."""
    llm = get_llm(TEMPERATURE)
    system_message = SystemMessage(content=AGENT_SYSTEM_PROMPT)
    return create_react_agent(model=llm, tools=TOOLS, prompt=system_message)


def run_agent(instruction: str, request_text: str, config: dict | None = None) -> dict:
    """Execute the agent on a single compliance instance.

    Args:
        instruction: The natural-language compliance task line.
        request_text: The free-text quote request (email-style).
        config: LangGraph config, e.g. with the ExecutionLogger callback.

    Returns:
        The agent result dict. The final message content carries the decision
        text including the ``FINAL_ANSWER:`` line.
    """
    agent = build_agent()
    user_msg = f"{instruction}\n\nQuote request:\n{request_text}"
    return agent.invoke(
        {"messages": [("human", user_msg)]},
        config=config or {},
    )
