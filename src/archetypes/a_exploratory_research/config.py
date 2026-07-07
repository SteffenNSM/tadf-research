"""Configuration for archetype A: Exploratory Research and Synthesis.

Single source of truth for archetype A: its dimensional profile, source
benchmarks, tool whitelist, output schema, and the prompt templates for both
paradigms.

Source: AssistantBench (Yoran et al., 2024) for low- and medium-difficulty
research tasks, with BrowseComp (Wei et al., 2025) for high-difficulty
deep-browsing instances. The task TYPES are taken from those benchmarks; the
specific instances are curated to have stable verifiable gold answers, since
live web facts can shift over time. See ``experiments/seed_research.py`` for
the per-instance provenance.
"""

from src.archetypes.a_exploratory_research.schemas import ResearchAnswer, SearchPlan
from src.core.llm import DEFAULT_TEMPERATURE
from src.core.tools.search import tavily_search

# ── TADF metadata ──

DIMENSIONAL_PROFILE = {
    # "mid": the kind of step (a search) is known; the number of searches and
    # their queries depend on intermediate results (Table-3 level anchors).
    "step_predictability": "mid",
    "information_availability": "low",
    # "low": short, closed-form answers verifiable against the curated gold.
    "output_ambiguity": "low",
    "error_consequence": "low_moderate",
}

SOURCE_BENCHMARK = "AssistantBench (Yoran et al., 2024); BrowseComp (Wei et al., 2025)"
TEMPERATURE = DEFAULT_TEMPERATURE
TOOLS = [tavily_search]

__all__ = [
    "DIMENSIONAL_PROFILE",
    "SOURCE_BENCHMARK",
    "TEMPERATURE",
    "TOOLS",
    "SearchPlan",
    "ResearchAnswer",
    "PLAN_PROMPT",
    "SYNTHESIZE_PROMPT",
    "AGENT_SYSTEM_PROMPT",
]


# ── Prompts ──

PLAN_PROMPT = """You are planning a web research task.

Decide which web search queries to run to gather the facts needed to answer the question. Up to 10 queries are available. All queries are issued together, before any results come back, so plan the full set now; you cannot revise it based on what the searches return. Do not answer the question yet. Return only a SearchPlan with the queries and a brief rationale.

Each query should target a specific piece of information rather than restate the question.

Question: {question}"""


SYNTHESIZE_PROMPT = """You are answering a research question based on web search results.

Use only the information in the results below. Give a concise final answer: a number, a name, a year, or a short phrase. Do not explain your reasoning. List the URLs you actually used as sources.

Question: {question}

Search results (grouped by the query that produced them):
{snippets}"""


AGENT_SYSTEM_PROMPT = """You are a research analyst. Answer the user's question by searching the web with the tavily_search tool.

Call tavily_search with focused queries to retrieve snippets, read what comes back, and search further if you do not yet have enough information. When you can answer, give the final answer as a single concise value: a number, name, year, or short phrase. State only the value."""
