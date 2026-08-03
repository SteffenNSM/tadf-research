"""Diagnostic for the family-M m1 agent failures (capability inversion check).

The m1 grid cell shows an inversion (mini 4/10 vs gpt-5.2 0/5) and agent
summaries claim both cases were closed, which the drift mechanism should
make impossible in oldest-first order. Per the IT-057 review rule this
requires a gold/mechanism review before interpretation.

Runs ONLY the agent on the five m1 instances and captures what the grid
telemetry cannot show: the full tool trajectory (call order, arguments,
tool responses), the post-state of both cases (status, closed_at vs the
drift sentinel), every new outbox mail, and the predicate verdict.

Diagnostic only: output goes to ``data/results/phase2b/diagnostics/``.

Run (author machine):
    TADF_MODEL=gpt-5.2-2025-12-11 PYTHONPATH=. python experiments/debug_m_agent.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from experiments.seed_actions import _seed_rows
from experiments.seed_m import PREDICATES, SENTINEL, _M1
from experiments.validate_m import prepare_db
from src.archetypes.f_action_execution.agent import run_agent
from src.core.db import get_connection
from src.core.llm import MODEL_NAME
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "data" / "results" / "phase2b" / "diagnostics"
IN = REPO / "data" / "test_inputs" / "m_state_drift" / "m1_observable_drift"

_SEED_EMAILS = _seed_rows("emails")


def trajectory(result: dict) -> list[dict]:
    """Extract (tool, args, response) triples from the agent's message log."""
    steps: list[dict] = []
    pending: dict[str, dict] = {}
    for msg in result.get("messages", []):
        for tc in getattr(msg, "tool_calls", None) or []:
            pending[tc["id"]] = {"tool": tc["name"], "args": tc["args"]}
        if getattr(msg, "type", "") == "tool":
            entry = pending.pop(getattr(msg, "tool_call_id", ""), {"tool": "?", "args": {}})
            entry["response"] = str(msg.content)[:200]
            steps.append(entry)
    return steps


def main() -> None:
    records = []
    print(f"model: {MODEL_NAME}\n")
    for iid, a, b in _M1:
        inst = json.loads((IN / f"{iid}.json").read_text())
        prepare_db(iid)
        logger = ExecutionLogger()
        logger.start()
        result = run_agent(inst["instruction"], config={"callbacks": [logger]})
        logger.stop()
        conn = get_connection()
        try:
            ra = dict(conn.execute("SELECT id, status, closed_at, priority FROM cases WHERE id=?", (a,)).fetchone())
            rb = dict(conn.execute("SELECT id, status, closed_at, priority FROM cases WHERE id=?", (b,)).fetchone())
            mails = [dict(r) for r in conn.execute(
                "SELECT id, recipient, subject FROM emails WHERE status='outbox'").fetchall()
                if r["id"] not in _SEED_EMAILS]
            ok = bool(PREDICATES[iid](conn))
        finally:
            conn.close()
        steps = trajectory(result)
        print(f"== {iid} (A={a}, B={b})  correct={ok}")
        for s in steps:
            print(f"   {s['tool']}({json.dumps(s['args'])[:90]}) -> {s['response'][:90]!r}")
        print(f"   post A: {ra['status']}, closed_at={ra['closed_at']}")
        print(f"   post B: {rb['status']}, closed_at={rb['closed_at']}  (sentinel={SENTINEL})")
        for m in mails:
            print(f"   mail -> {m['recipient']}: {m['subject']!r}")
        print()
        records.append({"instance": iid, "correct": ok, "steps": steps,
                        "post_a": ra, "post_b": rb, "mails": mails,
                        "telemetry": logger.to_record()})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"m_agent_debug_{MODEL_NAME}_{stamp}.json"
    out.write_text(json.dumps({"model": MODEL_NAME, "records": records}, indent=2, default=str))
    print(f"Diagnostic written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
