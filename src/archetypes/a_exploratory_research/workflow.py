"""Workflow implementation for archetype A: Exploratory Research and Synthesis.

LangGraph StateGraph in DAG mode. The workflow commits to a search plan
upfront and synthesizes the answer from the retrieved snippets in a single
final LLM call. It cannot adapt the search strategy based on intermediate
observations; that flexibility is the defining property of the agent paradigm
for this archetype.

Graph topology:
    [plan_searches] -> [execute_searches] -> [synthesize] -> END

Canonical minimal form: two LLM calls (plan and synthesize). The intermediate
search execution is deterministic, calling the ``tavily_search`` tool for each
planned query. No optional refinement or quality-gate node is included.
"""

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.a_exploratory_research.config import (
    PLAN_PROMPT,
    SYNTHESIZE_PROMPT,
    TEMPERATURE,
)
from src.archetypes.a_exploratory_research.schemas import ResearchAnswer, SearchPlan
from src.core.llm import get_llm
from src.core.tools.search import tavily_search


def plan_searches(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 1: produce the SearchPlan (the first LLM call)."""
    llm = get_llm(TEMPERATURE).with_structured_output(SearchPlan)
    plan: SearchPlan = llm.invoke(PLAN_PROMPT.format(question=state["instruction"]))
    return {**state, "search_plan": plan.model_dump()}


#: Hard ceiling on the number of upfront queries the workflow may issue,
#: symmetric with the agent's tool-call safety limit (see agent.py). The
#: workflow plans all queries before seeing any results, so the cap bounds the
#: planned batch; the agent's cap bounds its sequential tool calls.
MAX_QUERIES = 10


def execute_searches(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 2: run each planned query via the tavily_search tool.

    The reads are issued through the ``tavily_search`` LangChain tool so the
    workflow's tool calls are counted on equal footing with the agent's. The
    planned batch is capped at ``MAX_QUERIES``. Results are kept grouped by the
    query that produced them (the merge), with URLs deduplicated globally so a
    source is attributed to the first query that returned it.
    """
    plan = SearchPlan(**state["search_plan"])
    merged: list[dict] = []
    seen_urls: set[str] = set()
    for query in plan.queries[:MAX_QUERIES]:
        results = tavily_search.invoke({"query": query}, config=config)
        group: list[dict] = []
        for snippet in results:
            url = snippet.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                group.append(snippet)
        merged.append({"query": query, "results": group})
    return {**state, "merged": merged}


def _format_merge(merged: list[dict]) -> str:
    """Render the query-grouped snippet merge for the synthesize prompt."""
    blocks = []
    for group in merged:
        lines = [f"Query: {group['query']}"]
        if group["results"]:
            for snippet in group["results"]:
                content = (snippet.get("content", "") or "")[:800]
                lines.append(f"  [{snippet.get('url', '')}]\n  {content}")
        else:
            lines.append("  (no new results)")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) if blocks else "(no snippets retrieved)"


def synthesize(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 3: produce the ResearchAnswer from the query-grouped merge (LLM call 2)."""
    llm = get_llm(TEMPERATURE).with_structured_output(ResearchAnswer)
    snippets_text = _format_merge(state["merged"])
    answer: ResearchAnswer = llm.invoke(
        SYNTHESIZE_PROMPT.format(
            question=state["instruction"], snippets=snippets_text
        )
    )
    return {**state, "output": answer.model_dump(), "completed": True}


def build_workflow():
    """Construct and compile the archetype A workflow."""
    graph = StateGraph(dict)
    graph.add_node("plan_searches", plan_searches)
    graph.add_node("execute_searches", execute_searches)
    graph.add_node("synthesize", synthesize)
    graph.set_entry_point("plan_searches")
    graph.add_edge("plan_searches", "execute_searches")
    graph.add_edge("execute_searches", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


workflow = build_workflow()
