"""Workflow implementation for archetype B: multi-source Structured Retrieval.

LangGraph StateGraph in DAG mode. External orchestration fixes the step
sequence; the LLM does not decide which step follows, which tools to call, or
when to terminate.

Graph topology:
    [plan] -> [execute] -> [format] -> END

Canonical minimal form: one LLM call (the plan node), which translates the
question into a structured MultiSourcePlan (which sources, how to combine). The
execute node performs retrieval, the cross-source intersection, and the
aggregation deterministically via the multi-source executor; the format node
builds the structured answer. The aggregation and the intersection are never
delegated to the LLM, which is the defining property of the workflow paradigm
for this archetype. Reads are routed through the same LangChain tools the agent
uses (db_read / search_emails / search_events) so tool calls are counted on
equal footing (fair TCC).
"""

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.b_structured_retrieval.config import (
    PLAN_PROMPT,
    SOURCE_SCHEMA_DOC,
    TEMPERATURE,
)
from src.archetypes.b_structured_retrieval.multisource_executor import run_plan
from src.archetypes.b_structured_retrieval.schemas import MultiSourcePlan, QueryAnswer
from src.core.llm import get_llm
from src.core.tools.calendar import search_events
from src.core.tools.database import db_read
from src.core.tools.mail import search_emails


def plan(state: dict) -> dict:
    """Node 1: translate the question into a MultiSourcePlan (the single LLM call)."""
    llm = get_llm(TEMPERATURE).with_structured_output(MultiSourcePlan)
    prompt = PLAN_PROMPT.format(schema=SOURCE_SCHEMA_DOC, question=state["instruction"])
    plan_obj: MultiSourcePlan = llm.invoke(prompt)
    return {**state, "plan": plan_obj.model_dump()}


def execute(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 2: run the plan deterministically, routing reads through the tools."""

    def crm_loader(table: str) -> list[dict]:
        return db_read.invoke({"table": table, "filters": None}, config=config)

    def mail_loader(query: str) -> list[str]:
        msgs = search_emails.invoke({"query": query}, config=config)
        return [m.get("snippet", "") for m in msgs]

    def cal_loader(query: str) -> list[str]:
        events = search_events.invoke({"query": query}, config=config)
        return [e.get("summary", "") for e in events]

    plan_obj = MultiSourcePlan(**state["plan"])
    value = run_plan(plan_obj, crm_loader, mail_loader, cal_loader)
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
