"""Workflow for archetype C: batch email triage via deterministic map-reduce.

The task is to route a BATCH of customer emails into support categories: one
input batch plus the category document, one output list of per-email labels
(Section 2.2.3, a single task). The workflow's structure is a deterministic
map-reduce: the batch is split into fixed-size chunks (CHUNK_SIZE = 5), each
chunk is classified by one structured LLM call, and the per-email results are
merged into the output. With the current batch sizes this yields Low (3 emails)
-> 1 call, Med (5) -> 1 call, High (8) -> 2 calls; the LLM only disambiguates
each email against the category definitions, while the split-and-merge is
deterministic code.

Graph topology:
    [triage] -> END

The agent, by contrast, receives the whole batch in one context. Empirically
(gpt-5.4-nano) both paradigms score 100 % on the current batches, and the
chunking is net OVERHEAD, not an advantage: at High the workflow re-sends the
category document once per chunk and so costs ~1.5x the agent's tokens (~2.5k
vs ~1.6k), while the agent carries all 8 emails in a single call without loss.
The map-reduce advantage would only materialise once a single call genuinely
degrades (attention dilution or context overflow at far larger load), which the
current batch sizes do not reach. The context-management/chunking angle is thus
a system-level orchestration concern, not exercised in C's normal regime.
"""

from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.c_ambiguous_classification.config import (
    BATCH_CLASSIFY_PROMPT,
    CATEGORY_DEFINITIONS,
    CHUNK_SIZE,
    TEMPERATURE,
)
from src.archetypes.c_ambiguous_classification.schemas import BatchClassification
from src.core.llm import get_llm


def triage(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 1: classify the batch by mapping one LLM call over each chunk."""
    llm = get_llm(TEMPERATURE).with_structured_output(
        BatchClassification, method="function_calling"
    )
    emails = state["emails"]
    labels: dict[str, str] = {}
    rationales: dict[str, str] = {}
    n_chunks = 0
    for i in range(0, len(emails), CHUNK_SIZE):
        chunk = emails[i : i + CHUNK_SIZE]
        n_chunks += 1
        emails_json = json.dumps(chunk, indent=2, ensure_ascii=False)
        result: BatchClassification = llm.invoke(
            BATCH_CLASSIFY_PROMPT.format(
                definitions=CATEGORY_DEFINITIONS, emails=emails_json
            )
        )
        for c in result.classifications:
            labels[c.email_id] = c.label
            rationales[c.email_id] = c.rationale
    output = {"labels": labels, "rationales": rationales, "n_chunks": n_chunks}
    return {**state, "output": output, "completed": True}


def build_workflow():
    """Construct and compile the archetype C batch-triage workflow."""
    graph = StateGraph(dict)
    graph.add_node("triage", triage)
    graph.set_entry_point("triage")
    graph.add_edge("triage", END)
    return graph.compile()


workflow = build_workflow()
