"""Agent implementation for archetype D: Compliance and Rule-Based Decisioning.

LangGraph ReAct loop with the read-only CRM tools exposed (the same tools
the workflow has access to, per the Phase-2 tool-symmetry invariant). The
agent decides at runtime whether to fetch additional context — the D
instances are constructed to be solvable from the quote request alone, so
most runs require no tool calls — and reports its decision in free text
terminated by a ``FINAL_ANSWER:`` line.

The agent paradigm carries the same information as the workflow's single
LLM call but pays the ReAct system-prompt overhead and the absence of an
output-format constraint. For rule-application tasks the agent has the
theoretical advantage of being able to "think out loud" in longer prose
before committing to a decision, which may help on deeply-nested rule
chains; the empirical question is whether that prose width compensates for
the system-prompt cost or not.
"""

from __future__ import annotations

import json

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from src.archetypes.d_compliance_decisioning.config import (
    AGENT_SYSTEM_PROMPT,
    POLICY_RULES,
    TEMPERATURE,
    TOOLS,
)
from src.core.llm import get_llm


def build_agent():
    """Construct a ReAct agent for archetype D with the read-only CRM toolset."""
    llm = get_llm(TEMPERATURE)
    system_message = SystemMessage(
        content=AGENT_SYSTEM_PROMPT.format(rules=POLICY_RULES)
    )
    return create_react_agent(model=llm, tools=TOOLS, prompt=system_message)


def run_agent(instruction: str, quote_request: dict, config: dict | None = None) -> dict:
    """Execute the agent on a single compliance instance.

    Args:
        instruction: The natural-language compliance task.
        quote_request: A dict with lead, customer, and quote sub-records.
        config: LangGraph config, e.g. with the ExecutionLogger callback.

    Returns:
        The agent result dict. The final message content carries the
        decision text including the ``FINAL_ANSWER:`` line.
    """
    agent = build_agent()
    qr_json = json.dumps(quote_request, indent=2, ensure_ascii=False)
    user_msg = f"{instruction}\n\nQuote request:\n{qr_json}"
    return agent.invoke(
        {"messages": [("human", user_msg)]},
        config=config or {},
    )
