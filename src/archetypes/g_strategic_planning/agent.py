"""Agent implementation for archetype G: Strategic and Adaptive Planning.

LangGraph ReAct loop with the read-only CRM tools. The agent interleaves
reads and reasoning at its own discretion, then reports the plan as JSON
in a ``FINAL_PLAN:`` block. No state-changing tools are exposed to either
paradigm — the deliverable is the plan, and actions exist only as
plan-step vocabulary (see ``config.ACTION_SET_DOC``).

Step limits (protocol A.6; resolves deviation D-007 for G): the validation
runner invokes the agent with a LangGraph ``recursion_limit`` derived from
the per-difficulty maximum step count in ``config.MAX_AGENT_STEPS``; a
``GraphRecursionError`` is recorded as an ``iteration_overflow`` failure.
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from src.archetypes.g_strategic_planning.config import (
    ACTION_SET_DOC,
    AGENT_SYSTEM_PROMPT,
    TEMPERATURE,
    TOOLS,
)
from src.core.llm import get_llm


def build_agent():
    """Construct a ReAct agent for archetype G with read-only tools."""
    llm = get_llm(TEMPERATURE)
    system_message = SystemMessage(content=AGENT_SYSTEM_PROMPT.format(action_doc=ACTION_SET_DOC))
    return create_react_agent(model=llm, tools=TOOLS, prompt=system_message)


def run_agent(instruction: str, config: dict | None = None) -> dict:
    """Execute the agent on a single planning instance.

    Args:
        instruction: The natural-language planning scenario.
        config: LangGraph config; the runner passes the ExecutionLogger
            callback and the per-difficulty ``recursion_limit`` here.

    Returns:
        The agent result dict; the final message carries the FINAL_PLAN
        JSON, parsed by ``ground_truth.extract_plan``.
    """
    agent = build_agent()
    return agent.invoke({"messages": [("human", instruction)]}, config=config or {})
