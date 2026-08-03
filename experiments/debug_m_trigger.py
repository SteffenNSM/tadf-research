"""Diagnostic 2 for family M: machine-level trigger check + parallel-call check.

Separates the two remaining hypotheses for the non-firing drift (IT-063/064):

  (A) machine issue -- the trigger does not exist or does not fire on this
      machine's SQLite even on a sequential tool-SQL path;
  (B) parallel tool calls -- the model emits BOTH attempt_close_case calls in
      one assistant turn; LangGraph's ToolNode executes them concurrently, so
      the second close reads its status BEFORE the first close's transaction
      (and its drift trigger) commits, then overwrites the sentinel (a TOCTOU
      race that the tool's SELECT-then-UPDATE shape permits).

Part 1 needs no LLM. Part 2 runs the agent once on m1-1 and prints how many
tool calls each assistant turn carried.

Run (author machine):
    TADF_MODEL=gpt-5.2-2025-12-11 PYTHONPATH=. python experiments/debug_m_trigger.py
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from experiments.seed_m import SENTINEL
from experiments.validate_m import prepare_db
from src.core.db import get_connection
from src.core.llm import MODEL_NAME

REPO = Path(__file__).resolve().parents[1]

print(f"sqlite version: {sqlite3.sqlite_version} | model: {MODEL_NAME}\n")

# ── Part 1: sequential tool-SQL replication (no LLM) ──
prepare_db("m1-1")
conn = get_connection()
trigs = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()]
print("PART 1 — sequential path")
print("  triggers installed:", trigs)
conn.close()

conn = get_connection()
row = conn.execute("SELECT id, status, transfer_count FROM cases WHERE id = ?", (62,)).fetchone()
print("  case 62 pre-close:", dict(row))
conn.execute("UPDATE cases SET status = 'Closed', closed_at = datetime('now') WHERE id = ?", (62,))
conn.commit()
conn.close()

conn = get_connection()
b = dict(conn.execute("SELECT id, status, closed_at FROM cases WHERE id = 40").fetchone())
fired = b["closed_at"] == SENTINEL
print(f"  case 40 post: {b}")
print(f"  -> drift fired on sequential path: {fired}  ({'machine OK' if fired else 'MACHINE ISSUE'})\n")

# ── Part 2: one agent run, inspect turn structure ──
from experiments.seed_m import PREDICATES  # noqa: E402
from src.archetypes.f_action_execution.agent import run_agent  # noqa: E402

inst = json.loads((REPO / "data/test_inputs/m_state_drift/m1_observable_drift/m1-1.json").read_text())
prepare_db("m1-1")
result = run_agent(inst["instruction"])
print("PART 2 — agent turn structure (tool calls per assistant turn)")
parallel_close_turn = False
for i, msg in enumerate(result.get("messages", [])):
    tcs = getattr(msg, "tool_calls", None) or []
    if tcs:
        names = [tc["name"] for tc in tcs]
        closes = names.count("attempt_close_case")
        parallel_close_turn |= closes >= 2
        print(f"  turn {i}: {len(tcs)} tool call(s): {names}")
conn = get_connection()
b = dict(conn.execute("SELECT id, status, closed_at FROM cases WHERE id = 40").fetchone())
ok = bool(PREDICATES["m1-1"](conn))
conn.close()
print(f"  case 40 post-agent: {b} | sentinel intact: {b['closed_at'] == SENTINEL} | predicate: {ok}")
print(f"\nVERDICT: sequential drift fired={fired}; parallel close-calls in one turn={parallel_close_turn}")
print("  -> both True  = hypothesis (B): parallel-call race (TOCTOU in attempt_close_case)")
print("  -> fired False = hypothesis (A): machine-level trigger issue")
