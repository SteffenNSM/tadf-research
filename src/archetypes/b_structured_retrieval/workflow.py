"""Workflow for archetype B: tool-router retrieval with a deterministic core.

A realistic enterprise sub-flow. Two LLM calls bracket deterministic steps:

    [plan] -> [fetch] -> [execute] -> [aggregate] -> END
     LLM #1    det.+lat   det.+lat     LLM #2

- plan (LLM #1): given the question and the tool catalogue, emit a RetrievalSpec
  -- the Mail/Calendar searches to issue and one read-only SQL SELECT per answer
  field over the CRM plus the staged Mail/Calendar rows.
- fetch (deterministic): dispatch the searches to the simulated Gmail/Calendar
  APIs (payload realism + synthetic latency) and stage the results; tools the
  planner did not select stage empty.
- execute (deterministic): create the staging temp tables and run each field's
  SQL (with synthetic DB latency); the database engine performs the joins and
  aggregations. The LLM never computes here.
- aggregate (LLM #2): given the original question and the computed field values,
  compose the final answer. Heavy aggregation is deterministic; where the
  computation does not fit the SQL structure the aggregator combines the
  retrieved values, so the workflow's accuracy advantage is conditional on the
  aggregation being SQL-expressible.

The CRM, Mail, and Calendar are all reached only through their tool/API boundary
and all carry synthetic latency.
"""

import json
from datetime import datetime, timezone

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.archetypes.b_structured_retrieval.config import (
    AGGREGATE_PROMPT,
    PLAN_PROMPT,
    QUERY_SCHEMA_DOC,
    TEMPERATURE,
)
from src.archetypes.b_structured_retrieval.schemas import QueryAnswer, RetrievalSpec
from src.archetypes.b_structured_retrieval.sql_executor import is_read_only
from src.core.db import get_connection
from src.core.llm import get_llm
from src.core.tools._latency import synthetic_delay
from src.core.tools.calendar import search_events
from src.core.tools.mail import search_emails


def _email_from_gmail(msg: dict) -> dict:
    """Parse a Gmail-shaped message resource into a staging row."""
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    sent_at = ""
    ms = msg.get("internalDate")
    if ms:
        sent_at = datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "sender": headers.get("From", ""),
        "recipient": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "body": msg.get("snippet", ""),
        "sent_at": sent_at,
    }


def _event_from_calendar(ev: dict) -> dict:
    """Parse a Google-Calendar-shaped event resource into a staging row."""
    emails = [a.get("email", "") for a in ev.get("attendees", []) if a.get("email")]
    def _dt(block: dict) -> str:
        s = (block or {}).get("dateTime", "") or ""
        return s[:19].replace("T", " ")
    return {
        "name": ev.get("summary", ""),
        "attendees": ",".join(emails),
        "start_time": _dt(ev.get("start")),
        "end_time": _dt(ev.get("end")),
    }


def plan(state: dict) -> dict:
    """Node 1 (LLM #1): emit the RetrievalSpec (Mail/Calendar searches + SQL).

    Uses function-calling structured output: SQL fields carry quotes, CASE
    expressions and semicolons that break free-text JSON parsing, so the
    tool-schema path is required to keep the spec valid.
    """
    llm = get_llm(TEMPERATURE).with_structured_output(RetrievalSpec, method="function_calling")
    prompt = PLAN_PROMPT.format(schema=QUERY_SCHEMA_DOC, question=state["instruction"])
    spec: RetrievalSpec = llm.invoke(prompt)
    return {**state, "spec": spec.model_dump()}


def _norm_query(q: str) -> str:
    """Normalize a search query. A query consisting only of quote characters
    (the planner sometimes emits the literal string ``''`` instead of an empty
    string when told to 'use []') is treated as the empty query = fetch all."""
    return "" if q.strip().strip("'\"").strip() == "" else q


def fetch(state: dict, config: RunnableConfig | None = None) -> dict:
    """Node 2 (deterministic): dispatch the searches and stage the results."""
    spec = RetrievalSpec(**state["spec"])
    emails: dict[tuple, dict] = {}
    for q in spec.mail_queries:
        for msg in search_emails.invoke({"query": _norm_query(q)}, config=config):
            row = _email_from_gmail(msg)
            emails[(row["sender"], row["subject"], row["sent_at"])] = row
    events: dict[tuple, dict] = {}
    for q in spec.calendar_queries:
        for ev in search_events.invoke({"query": _norm_query(q)}, config=config):
            row = _event_from_calendar(ev)
            events[(row["name"], row["start_time"])] = row
    return {**state, "fetched_emails": list(emails.values()), "fetched_events": list(events.values())}


def execute(state: dict) -> dict:
    """Node 3 (deterministic): stage the fetched rows and run each field's SQL."""
    spec = RetrievalSpec(**state["spec"])
    conn = get_connection()
    results: dict = {}
    try:
        conn.execute("CREATE TEMP TABLE fetched_emails (sender TEXT, recipient TEXT, subject TEXT, body TEXT, sent_at TEXT)")
        conn.executemany(
            "INSERT INTO fetched_emails VALUES (:sender, :recipient, :subject, :body, :sent_at)",
            state.get("fetched_emails", []),
        )
        conn.execute("CREATE TEMP TABLE fetched_events (name TEXT, attendees TEXT, start_time TEXT, end_time TEXT)")
        conn.executemany(
            "INSERT INTO fetched_events VALUES (:name, :attendees, :start_time, :end_time)",
            state.get("fetched_events", []),
        )
        for f in spec.fields:
            synthetic_delay("db_query", {"sql": f.sql})  # DB round-trip latency
            if not is_read_only(f.sql):
                results[f.name] = None
                continue
            try:
                row = conn.execute(f.sql).fetchone()
                results[f.name] = row[0] if row is not None else None
            except Exception:
                results[f.name] = None
    finally:
        conn.close()
    return {**state, "field_results": results}


def aggregate(state: dict) -> dict:
    """Node 4 (LLM #2): compose the final answer from the computed field values."""
    llm = get_llm(TEMPERATURE).with_structured_output(QueryAnswer, method="function_calling")
    results_text = json.dumps(state.get("field_results", {}), default=str, ensure_ascii=False)
    answer: QueryAnswer = llm.invoke(
        AGGREGATE_PROMPT.format(question=state["instruction"], results=results_text)
    )
    return {**state, "output": answer.model_dump(), "completed": True}


def build_workflow():
    """Construct and compile the archetype B tool-router workflow."""
    graph = StateGraph(dict)
    graph.add_node("plan", plan)
    graph.add_node("fetch", fetch)
    graph.add_node("execute", execute)
    graph.add_node("aggregate", aggregate)
    graph.set_entry_point("plan")
    graph.add_edge("plan", "fetch")
    graph.add_edge("fetch", "execute")
    graph.add_edge("execute", "aggregate")
    graph.add_edge("aggregate", END)
    return graph.compile()


workflow = build_workflow()
