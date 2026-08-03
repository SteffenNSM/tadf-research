"""Diagnostic for the family-L mail anomaly (IT-061 open point).

Runs ONLY the workflow on the six mail_scaling instances and captures the
full intermediate state -- the ReadPlan (which query was actually planned),
the size of each read result, the ActionPlan (including the planned
send_email body), and the post-state outbox row -- so the failure can be
classified per run:

    READ_MISS   the read-stage search returned (near) nothing; the action
                stage chained a fresh search plus a blind send_email --
                the date was planned before any result existed.
    WRONG_PICK  the reads returned the mails, but the planner chose a
                non-oldest mail's date.
    FORMAT      the right mail was chosen but the date was not rendered
                as YYYY-MM-DD in the body (RFC-2822 -> ISO conversion).
    OTHER       anything else (wrong recipient/subject, no send, ...).

Diagnostic only: results go to ``data/results/phase2b/diagnostics/`` and are
NOT part of the evidence grid.

Run (author machine):
    PYTHONPATH=. python experiments/debug_l_mail.py                # nano default
    TADF_MODEL=gpt-5.4-mini-2026-03-17 PYTHONPATH=. python experiments/debug_l_mail.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from experiments.seed_l import OVERLAYS, PREDICATES
from experiments.validate_l import prepare_db
from src.archetypes.f_action_execution.workflow import workflow
from src.core.db import get_connection
from src.core.llm import MODEL_NAME
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "data" / "results" / "phase2b" / "diagnostics"

MAIL_IDS = [f"l-m{lvl}-{n}" for lvl in (1, 5, 20) for n in (1, 2)]


def classify(iid: str, state: dict, new_outbox: list[dict]) -> str:
    ov = OVERLAYS[iid]
    gold_date = ov["gold_date"]
    read_chars = sum(len(str(r.get("result", ""))) for r in state.get("read_results", []))
    plan = state.get("action_plan", {}) or {}
    sends = [a for a in plan.get("actions", []) if a.get("tool") == "send_email"]
    searches_in_actions = [a for a in plan.get("actions", []) if a.get("tool") == "search_emails"]
    if read_chars < 400 and searches_in_actions:
        return "READ_MISS"
    body = (new_outbox[0]["body"] if new_outbox else "") or ""
    if gold_date in body:
        return "OK"
    topic_dates = sorted(e["sent_at"][:10] for e in ov["emails"] if e["subject"] == ov["topic"])
    if any(d in body for d in topic_dates[1:]):
        return "WRONG_PICK"
    if not sends or not new_outbox:
        return "OTHER(no send)"
    # right mail id referenced but date not ISO-rendered?
    return "FORMAT_OR_OTHER"


def main() -> None:
    records = []
    print(f"model: {MODEL_NAME}")
    print(f"{'instance':9} {'verdict':7} {'class':16} {'read_chars':>10}  planned queries / body")
    for iid in MAIL_IDS:
        inst = json.loads((REPO / "data" / "test_inputs" / "l_payload_scaling" / "mail_scaling" / f"{iid}.json").read_text())
        prepare_db(iid)
        logger = ExecutionLogger()
        logger.start()
        state = workflow.invoke(
            {"input_id": iid, "instruction": inst["instruction"]},
            config={"callbacks": [logger]},
        )
        logger.stop()
        conn = get_connection()
        try:
            known = {e["id"] for e in OVERLAYS[iid]["emails"]}
            new_outbox = [dict(r) for r in conn.execute(
                "SELECT id, recipient, subject, body FROM emails WHERE status='outbox' AND id > 2004"
            ).fetchall() if r["id"] not in known]
            ok = bool(PREDICATES[iid](conn))
        finally:
            conn.close()
        read_plan = state.get("read_plan", {})
        queries = [r.get("args") for r in read_plan.get("reads", [])]
        read_chars = sum(len(str(r.get("result", ""))) for r in state.get("read_results", []))
        cls = "OK" if ok else classify(iid, state, new_outbox)
        body = (new_outbox[0]["body"][:90] if new_outbox else "(no mail)")
        print(f"{iid:9} {str(ok):7} {cls:16} {read_chars:>10}  {queries} :: {body!r}")
        records.append({
            "instance": iid, "correct": ok, "class": cls,
            "read_plan": read_plan, "read_chars": read_chars,
            "action_plan": state.get("action_plan"),
            "new_outbox": new_outbox,
            "telemetry": logger.to_record(),
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"l_mail_debug_{MODEL_NAME}_{stamp}.json"
    out.write_text(json.dumps({"model": MODEL_NAME, "records": records}, indent=2, default=str))
    print(f"\nDiagnostic written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
