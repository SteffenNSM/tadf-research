"""Agent implementation for archetype A: Exploratory Research and Synthesis.

LangGraph ReAct loop with the web-search tool. The LLM decides at runtime
which queries to issue, when it has enough information, and how to phrase the
final answer. Unlike the workflow, it can adapt subsequent searches based on
what previous searches returned.

Canonical minimal form: the system prompt states the task goal and the single
available tool. Tool selection, query phrasing, sequencing, and termination
are delegated to the LLM, per the agent definition in Section 2.2.
"""

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from src.archetypes.a_exploratory_research.config import (
    AGENT_SYSTEM_PROMPT,
    TEMPERATURE,
    TOOLS,
)
from src.core.llm import get_llm


def build_agent():
    """Construct a ReAct agent for archetype A with the web-search tool."""
    llm = get_llm(TEMPERATURE)
    system_message = SystemMessage(content=AGENT_SYSTEM_PROMPT)
    return create_react_agent(model=llm, tools=TOOLS, prompt=system_message)


def run_agent(instruction: str, config: dict | None = None) -> dict:
    """Execute the agent on a single research task.

    Args:
        instruction: The natural-language research question.
        config: LangGraph config, e.g. with the ExecutionLogger callback.

    Returns:
        The agent result dict. The final answer is the content of the last
        message; the runner extracts it for scoring.
    """
    agent = build_agent()
    return agent.invoke(
        {"messages": [("human", instruction)]},
        config=config or {},
    )
