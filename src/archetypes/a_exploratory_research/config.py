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
    "step_predictability": "low",
    "information_availability": "low",
    "output_ambiguity": "high",
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

Given a research question, decide the minimal set of web search queries needed to gather the facts required to answer it. Do not answer the question now. Return only a SearchPlan with the queries and a brief rationale.

Guidelines:
- Plan the minimum number of focused queries needed to answer the question.
- Each query should target a specific piece of information, not be a paraphrase of the original question.
- Use as few queries as you can while still being likely to retrieve the necessary facts.
- Use more queries only when the question genuinely requires combining facts from multiple distinct sources.

Question: {question}"""


SYNTHESIZE_PROMPT = """You are answering a research question based on web search snippets.

Use only the information in the snippets below. Give a concise final answer: a number, a name, a year, or a short phrase. Do not explain your reasoning. List the URLs of the snippets you actually used as sources.

Question: {question}

Snippets:
{snippets}"""


AGENT_SYSTEM_PROMPT = """You are a research analyst. Answer the user's question by searching the web with the tavily_search tool.

Call tavily_search with focused queries to retrieve snippets, read what comes back, and search further if you do not yet have enough information. When you can answer, give the final answer as a single concise value: a number, name, year, or short phrase. State only the value."""
