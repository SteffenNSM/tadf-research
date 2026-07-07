"""Workflow for archetype D: rule-retrieval + deterministic decision engine.

A realistic compliance sub-flow with **mid information availability**: the
approval policy is not in the prompt; it is fetched from the external Policy
Registry and applied by a deterministic rule engine. The single LLM call
extracts the request fields — it never applies the policy. This is the same
division of labour as B's ETL workflow (LLM plans/extracts, engine computes),
and it is what makes D a genuine workflow-vs-agent paradigm test instead of a
single in-context call.

Graph topology:
    [survey] -> [fetch_rules] -> [extract] -> [decide] -> END
      det.        det.+latency     LLM         det. engine

- survey (deterministic): call list_policies() to read the policy catalogue.
- fetch_rules (deterministic): call get_policy(topic) for every catalogued
  document (Policy-Registry API, payload realism + synthetic latency) and
  assemble the complete clause set. The workflow loads the whole governing
  policy; the engine's precedence logic selects what actually applies.
- extract (LLM): read the natural-language request and emit QuoteFacts.
- decide (deterministic): the rule engine evaluates the fetched clauses
  against the extracted facts and returns the DecisionResult. The label is
  constrained to the documented enum by the engine's own decision space.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.d_compliance_decisioning.config import (
    EXTRACT_PROMPT,
    TEMPERATURE,
)
from src.archetypes.d_compliance_decisioning.rule_engine import evaluate
from src.archetypes.d_compliance_decisioning.schemas import (
    DecisionResult,
    QuoteFacts,
)
from src.core.llm import get_llm
from src.core.tools.policy import get_policy, list_policies


def survey(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 1 (deterministic): read the policy catalogue from the registry."""
    catalogue = list_policies.invoke({}, config=config)
    return {**state, "policy_catalogue": catalogue}


def fetch_rules(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 2 (deterministic): fetch every policy document and assemble clauses."""
    clauses: list[dict] = []
    docs: list[dict] = []
    for entry in state["policy_catalogue"]:
        doc = get_policy.invoke({"topic": entry["topic"]}, config=config)
        if isinstance(doc, dict) and "clauses" in doc:
            docs.append(doc)
            clauses.extend(doc["clauses"])
    return {**state, "policy_docs": docs, "clauses": clauses}


def extract(state: dict) -> dict:
    """Node 3 (LLM): extract structured QuoteFacts from the free-text request."""
    llm = get_llm(TEMPERATURE).with_structured_output(
        QuoteFacts, method="function_calling"
    )
    facts: QuoteFacts = llm.invoke(
        EXTRACT_PROMPT.format(request_text=state["request_text"])
    )
    return {**state, "facts": facts.model_dump()}


def decide(state: dict) -> dict:
    """Node 4 (deterministic): apply the rule engine to facts + clauses."""
    label, rationale = evaluate(state["clauses"], state["facts"])
    result = DecisionResult(label=label, rationale=rationale)
    return {**state, "output": result.model_dump(), "completed": True}


def build_workflow():
    """Construct and compile the archetype D rule-retrieval workflow."""
    graph = StateGraph(dict)
    graph.add_node("survey", survey)
    graph.add_node("fetch_rules", fetch_rules)
    graph.add_node("extract", extract)
    graph.add_node("decide", decide)
    graph.set_entry_point("survey")
    graph.add_edge("survey", "fetch_rules")
    graph.add_edge("fetch_rules", "extract")
    graph.add_edge("extract", "decide")
    graph.add_edge("decide", END)
    return graph.compile()


workflow = build_workflow()
