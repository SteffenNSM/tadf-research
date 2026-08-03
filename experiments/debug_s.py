"""Trace capture for family-S state-machine runs (diagnostics, not evidence).

Runs the state-machine form on one instance and dumps the FULL intermediate
state -- read plan, read results, the verbatim StagedActionPlan, every
executed action with its tool response, and the predicate verdict -- to
``data/results/phase2b/diagnostics/``. Follows the ``debug_m_agent.py``
precedent: summaries are unreliable (IT-052); traces settle diagnoses.

Run (any instance id from families S/X/P that validate_s.py knows):
    PYTHONPATH=. python experiments/debug_s.py p-b-1
    PYTHONPATH=. python experiments/debug_s.py s3-1
    PYTHONPATH=. python experiments/debug_s.py x1-1
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from experiments.load_db import load as reset_database
from experiments.validate_s import PREDICATES, VARIANTS
from src.archetypes.f_action_execution.ground_truth import score
from src.archetypes.f_action_execution.state_machine import state_machine
from src.core.llm import MODEL_NAME
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "data" / "results" / "phase2b" / "diagnostics"


def find_instance(iid: str) -> dict:
    for _variant, (ids, src, _forms) in VARIANTS.items():
        if iid in ids:
            return json.loads((src / f"{iid}.json").read_text())
    raise SystemExit(f"unknown instance id: {iid}")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: PYTHONPATH=. python experiments/debug_s.py <instance-id>")
    iid = sys.argv[1]
    inst = find_instance(iid)

    reset_database()
    logger = ExecutionLogger()
    logger.start()
    state = state_machine.invoke(
        {"input_id": iid, "instruction": inst["instruction"]},
        config={"callbacks": [logger]},
    )
    logger.stop()
    s, rationale = score(iid, PREDICATES)

    dump = {
        "instance": iid,
        "model": MODEL_NAME,
        "correct": s >= 1.0,
        "predicate_rationale": rationale,
        "read_plan": state.get("read_plan"),
        "read_results": state.get("read_results"),
        "staged_plan": state.get("staged_plan"),
        "executed_actions": (state.get("output") or {}).get("executed_actions"),
        "summary": (state.get("output") or {}).get("summary"),
        "record": logger.to_record(),
        "expected_post_state": inst.get("expected_post_state"),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"s_debug_{iid}_{MODEL_NAME}_{stamp}.json"
    out.write_text(json.dumps(dump, indent=2, default=str))

    print(f"correct: {s >= 1.0}  ({rationale})")
    print("\n== StagedActionPlan ==")
    print(json.dumps(state.get("staged_plan"), indent=2, default=str)[:4000])
    print("\n== Executed actions ==")
    for a in (state.get("output") or {}).get("executed_actions", []):
        print(json.dumps(a, default=str)[:300])
    print(f"\nFull trace written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
