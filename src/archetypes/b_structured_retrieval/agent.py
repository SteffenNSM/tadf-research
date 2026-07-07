"""Agent implementation for archetype B: Structured Data Retrieval.

LangGraph ReAct loop with conditional edges. The LLM directs the execution
path at runtime: it decides which tables to read, with which filters, in what
order, and when it has enough information to answer. It receives the same
read-only database tools as the workflow, but performs the aggregation itself
in its reasoning rather than via a deterministic executor.

Canonical minimal form: the system prompt states only the task goal and the
schema. Tool selection, sequencing, computation, and termination are delegated
to the LLM, per the agent definition in Section 2.2.
"""

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from src.archetypes.b_structured_retrieval.config import (
    AGENT_SCHEMA_DOC,
    AGENT_SYSTEM_PROMPT,
    TEMPERATURE,
    TOOLS,
)
from src.core.llm import get_llm


def build_agent():
    """Construct a ReAct agent for archetype B with read-only CRM/Mail/Calendar tools."""
    llm = get_llm(TEMPERATURE)
    system_message = SystemMessage(content=AGENT_SYSTEM_PROMPT.format(schema=AGENT_SCHEMA_DOC))
    return create_react_agent(model=llm, tools=TOOLS, prompt=system_message)


#: Safety ceiling on the agent's sequential tool calls. NOT stated in the
#: prompt: the agent decides adaptively when to stop; the limit only prevents a
#: pathological runaway loop (earlier B runs reached ~15 tool calls / 143k
#: tokens). B answers combine at most three sources, so 12 tool calls is
#: generous and does not bind normal behaviour. In LangGraph each tool call
#: spans two super-steps (agent node + tool node), so recursion_limit = 2*12+1.
MAX_TOOL_CALLS = 12
_RECURSION_LIMIT = 2 * MAX_TOOL_CALLS + 1


def run_agent(instruction: str, config: dict | None = None) -> dict:
    """Execute the agent on a single querying task.

    Args:
        instruction: The natural-language CRM question.
        config: LangGraph config, e.g. with the ExecutionLogger callback.

    Returns:
        The agent result dict. The final answer is the content of the last
        message; the runner extracts it for scoring.
    """
    agent = build_agent()
    run_config = {"recursion_limit": _RECURSION_LIMIT, **(config or {})}
    return agent.invoke(
        {"messages": [("human", instruction)]},
        config=run_config,
    )
