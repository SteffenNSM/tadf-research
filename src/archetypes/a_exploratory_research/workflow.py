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


def execute_searches(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 2: run each planned query via the tavily_search tool.

    The reads are issued through the ``tavily_search`` LangChain tool so the
    workflow's tool calls are counted on equal footing with the agent's.
    Snippets are accumulated, deduplicated by URL.
    """
    plan = SearchPlan(**state["search_plan"])
    snippets: list[dict] = []
    seen_urls: set[str] = set()
    for query in plan.queries:
        results = tavily_search.invoke({"query": query}, config=config)
        for snippet in results:
            url = snippet.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                snippets.append(snippet)
    return {**state, "snippets": snippets}


def _format_snippets(snippets: list[dict]) -> str:
    """Compact textual rendering of the snippet pool for the synthesize prompt."""
    blocks = []
    for snippet in snippets:
        content = (snippet.get("content", "") or "")[:800]
        blocks.append(f"[{snippet.get('url', '')}]\n{content}")
    return "\n\n".join(blocks) if blocks else "(no snippets retrieved)"


def synthesize(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 3: produce the ResearchAnswer from the snippet pool (LLM call 2)."""
    llm = get_llm(TEMPERATURE).with_structured_output(ResearchAnswer)
    snippets_text = _format_snippets(state["snippets"])
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
