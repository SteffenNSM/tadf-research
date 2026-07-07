"""Agent implementation for archetype C: Ambiguous Classification and Disambiguation.

LangGraph ReAct loop with the read-only CRM tools exposed (the same tools
the workflow has access to, per the Phase-2 tool-symmetry invariant). The
agent triages the whole batch in a single context and reports one
``FINAL_ANSWER <email_id>: <label>`` line per email. The C instances are
solvable from the email text alone, and in every run the agent made zero tool
calls.

Cost note (batch-triage design): the agent pays the ReAct system-prompt
overhead and a free-text output that needs regex extraction, but it processes
the batch in ONE call. The workflow, by contrast, re-sends the category
document once per chunk, so on the larger High batches the AGENT is the cheaper
paradigm (both remain at ceiling accuracy on gpt-5.4-nano). The single-item
framing in which the agent was the more expensive paradigm no longer holds once
the task is a batch that the workflow chunks.
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


#: Safety ceiling on the agent's tool calls (not in the prompt): the batch
#: needs no tools in the common case, so this only bounds a runaway loop.
MAX_TOOL_CALLS = 10
_RECURSION_LIMIT = 2 * MAX_TOOL_CALLS + 1


def run_agent(instruction: str, emails: list[dict], config: dict | None = None) -> dict:
    """Execute the agent on a batch-triage instance.

    Args:
        instruction: The natural-language triage task.
        emails: The batch of email records (each a dict with id, sender,
            subject, body).
        config: LangGraph config, e.g. with the ExecutionLogger callback.

    Returns:
        The agent result dict. The final message content carries one
        ``FINAL_ANSWER <email_id>: <label>`` line per email. The agent receives
        the whole batch in one context and manages it at runtime; it may spawn
        no sub-agents in this minimal form (a design-knowledge extension noted
        in the iteration log).
    """
    agent = build_agent()
    emails_json = json.dumps(emails, indent=2, ensure_ascii=False)
    user_msg = f"{instruction}\n\nEmails to classify:\n{emails_json}"
    run_config = {"recursion_limit": _RECURSION_LIMIT, **(config or {})}
    return agent.invoke(
        {"messages": [("human", user_msg)]},
        config=run_config,
    )
