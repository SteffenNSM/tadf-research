"""Workflow implementation for archetype B: Structured Data Retrieval.

LangGraph StateGraph in DAG mode. External orchestration fixes the step
sequence; the LLM does not decide which step follows, which tools to call, or
when to terminate.

Graph topology:
    [plan] -> [execute] -> [format] -> END

Canonical minimal form: one LLM call (the plan node), which translates the
question into a structured QuerySpec. The execute node performs the retrieval
and aggregation deterministically via the query executor, and the format node
builds the structured answer. The aggregation is never delegated to the LLM,
which is the defining property of the workflow paradigm for this archetype.
Removing the plan node would prevent generic question handling; removing the
execute node would force the LLM to compute the aggregation, changing the
paradigm. No optional nodes are included.
"""

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.b_structured_retrieval.config import (
    CRM_SCHEMA_DOC,
    PLAN_PROMPT,
    TEMPERATURE,
)
from src.archetypes.b_structured_retrieval.query_executor import run_query
from src.archetypes.b_structured_retrieval.schemas import QueryAnswer, QuerySpec
from src.core.llm import get_llm
from src.core.tools.database import db_read


def plan(state: dict) -> dict:
    """Node 1: translate the question into a QuerySpec (the single LLM call)."""
    llm = get_llm(TEMPERATURE).with_structured_output(QuerySpec)
    prompt = PLAN_PROMPT.format(schema=CRM_SCHEMA_DOC, question=state["instruction"])
    spec: QuerySpec = llm.invoke(prompt)
    return {**state, "spec": spec.model_dump()}


def execute(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 2: run the query deterministically against the database.

    The reads are issued through the ``db_read`` LangChain tool so that the
    workflow's database accesses are counted by the ExecutionLogger callback
    on equal footing with the agent's tool calls. The aggregation itself
    remains deterministic and is performed in the query executor, never by
    the LLM.
    """

    def load(table: str) -> list[dict]:
        return db_read.invoke({"table": table, "filters": None}, config=config)

    spec = QuerySpec(**state["spec"])
    value = run_query(spec, load)
    return {**state, "raw_value": value}


def format_answer(state: dict) -> dict:
    """Node 3: build the structured answer (deterministic)."""
    answer = QueryAnswer(value=str(state["raw_value"]))
    return {**state, "output": answer.model_dump(), "completed": True}


def build_workflow():
    """Construct and compile the archetype B workflow."""
    graph = StateGraph(dict)
    graph.add_node("plan", plan)
    graph.add_node("execute", execute)
    graph.add_node("format", format_answer)
    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "format")
    graph.add_edge("format", END)
    return graph.compile()


workflow = build_workflow()
