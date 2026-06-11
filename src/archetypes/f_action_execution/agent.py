"""Agent implementation for archetype F: Transactional Action Execution.

LangGraph ReAct loop with the full action toolset. The LLM decides at runtime
which tool to invoke next, with which arguments, in which order, and when the
task is complete. It can re-read state between actions to confirm an id, react
to a tool failure by retrying with different arguments, and stop once the goal
is achieved.

Canonical minimal form: the system prompt states the task goal and the schema;
tool selection, argument choice, sequencing, and termination are delegated to
the LLM, per the agent definition in Section 2.2.
"""

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from src.archetypes.f_action_execution.config import (
    AGENT_SYSTEM_PROMPT,
    CRM_SCHEMA_DOC,
    TEMPERATURE,
    TOOLS,
)
from src.core.llm import get_llm


def build_agent():
    """Construct a ReAct agent for archetype F with the full action toolset."""
    llm = get_llm(TEMPERATURE)
    system_message = SystemMessage(content=AGENT_SYSTEM_PROMPT.format(schema=CRM_SCHEMA_DOC))
    return create_react_agent(model=llm, tools=TOOLS, prompt=system_message)


def run_agent(instruction: str, config: dict | None = None) -> dict:
    """Execute the agent on a single action task.

    Args:
        instruction: The natural-language workplace task.
        config: LangGraph config, e.g. with the ExecutionLogger callback.

    Returns:
        The agent result dict. The final summary is the content of the last
        message; the runner reads the post-execution database state to score.
    """
    agent = build_agent()
    return agent.invoke(
        {"messages": [("human", instruction)]},
        config=config or {},
    )
