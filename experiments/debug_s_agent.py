"""Trace capture for family-S AGENT runs (diagnostics, not evidence).

Runs the ReAct agent on one family-S/X/P instance and dumps the full message
trajectory, every tool call with its response, the post-state mail rows, and
the predicate verdict to ``data/results/phase2b/diagnostics/``. Companion to
``debug_s.py`` (state-machine traces); ``debug_m_agent.py`` precedent.

Run:
    PYTHONPATH=. python experiments/debug_s_agent.py s3-1
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from experiments.load_db import load as reset_database
from experiments.validate_s import PREDICATES, VARIANTS
from src.archetypes.f_action_execution.agent import run_agent
from src.archetypes.f_action_execution.ground_truth import score
from src.core.db import get_connection
from src.core.llm import MODEL_NAME
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "data" / "results" / "phase2b" / "diagnostics"


def find_instance(iid: str) -> dict:
    for _variant, (ids, src, _forms) in VARIANTS.items():
        if iid in ids:
            return json.loads((src / f"{iid}.json").read_text())
    raise SystemExit(f"unknown instance id: {iid}")


def _message_dump(result: dict) -> list[dict]:
    out = []
    for m in result.get("messages", []):
        entry: dict = {"type": m.__class__.__name__, "content": str(getattr(m, "content", ""))}
        calls = getattr(m, "tool_calls", None)
        if calls:
            entry["tool_calls"] = [
                {"name": c.get("name"), "args": c.get("args")} for c in calls
            ]
        out.append(entry)
    return out


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: PYTHONPATH=. python experiments/debug_s_agent.py <instance-id>")
    iid = sys.argv[1]
    inst = find_instance(iid)

    reset_database()
    logger = ExecutionLogger()
    logger.start()
    result = run_agent(inst["instruction"], config={"callbacks": [logger]})
    logger.stop()
    s, rationale = score(iid, PREDICATES)

    conn = get_connection()
    try:
        mails = [dict(r) for r in conn.execute(
            "SELECT id, recipient, subject, body FROM emails WHERE status='outbox' ORDER BY id DESC LIMIT 5"
        ).fetchall()]
        batch_cases = [dict(r) for r in conn.execute(
            "SELECT id, status, transfer_count, closed_at FROM cases ORDER BY id"
        ).fetchall() if dict(r)["closed_at"] is not None or True][:0]  # placeholder, full dump below
        cases = [dict(r) for r in conn.execute(
            "SELECT id, account_id, status, transfer_count FROM cases WHERE status='Closed' AND closed_at >= datetime('now','-1 hour')"
        ).fetchall()]
    finally:
        conn.close()

    dump = {
        "instance": iid,
        "model": MODEL_NAME,
        "correct": s >= 1.0,
        "predicate_rationale": rationale,
        "messages": _message_dump(result),
        "outbox_tail": mails,
        "cases_closed_this_run": cases,
        "record": logger.to_record(),
        "expected_post_state": inst.get("expected_post_state"),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"s_agent_debug_{iid}_{MODEL_NAME}_{stamp}.json"
    out.write_text(json.dumps(dump, indent=2, default=str))

    print(f"correct: {s >= 1.0}  ({rationale})")
    print("\n== Cases closed this run ==")
    print(cases)
    print("\n== Newest outbox mails ==")
    for m in mails:
        print(json.dumps(m, default=str)[:400])
    print("\n== Trajectory (tool calls only) ==")
    for m in dump["messages"]:
        if "tool_calls" in m:
            for c in m["tool_calls"]:
                print(c)
    print(f"\nFull trace written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
