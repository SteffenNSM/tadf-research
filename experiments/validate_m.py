"""End-to-end validation for Phase 2b family M (state drift) with the real LLM.

Runs the workflow and the agent on the 15 family-M instances. Before each run
the database is reset to the shared seed and the instance's deterministic
drift TRIGGER is installed (``seed_m.apply_drift``): the environment state
changes when the run performs its own first state-changing write -- the
identical causal position for both paradigms. Both paradigm implementations
are imported UNCHANGED from archetype F (frozen artifact state, IT-055/
IT-063). Results are routed to ``data/results/phase2b/<model>/<run_label>/``.

Run:
    PYTHONPATH=. python experiments/seed_m.py       # write instances + triggers
    PYTHONPATH=. python experiments/load_db.py      # build crm.db from seed
    PYTHONPATH=. python experiments/validate_m.py         # smoke: one per variant
    PYTHONPATH=. python experiments/validate_m.py --all   # all 15
    PYTHONPATH=. python experiments/validate_m.py --only m3-2
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from experiments.load_db import load as reset_database
from experiments.seed_m import PREDICATES, VARIANT_DIRS, apply_drift
from src.archetypes.f_action_execution.agent import run_agent
from src.archetypes.f_action_execution.ground_truth import score
from src.archetypes.f_action_execution.workflow import workflow
from src.core.db import get_connection
from src.core.llm import MODEL_NAME, RUN_LABEL
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "m_state_drift"
RESULTS = REPO / "data" / "results" / "phase2b"

VARIANTS = ["m1_observable_drift", "m2_silent_drift", "m3_guarded_drift"]


def phase2b_results_dir() -> Path:
    target = RESULTS / MODEL_NAME / (RUN_LABEL or "adhoc")
    target.mkdir(parents=True, exist_ok=True)
    return target


def load_instances(all_: bool, only: list[str] | None = None) -> list[dict]:
    if only:
        ids = only
    elif all_:
        ids = [f"m{v}-{n}" for v in (1, 2, 3) for n in range(1, 6)]
    else:
        ids = ["m1-1", "m2-1", "m3-1"]
    picks = []
    for iid in ids:
        variant = VARIANTS[int(iid[1]) - 1]
        picks.append(IN / VARIANT_DIRS[variant] / f"{iid}.json")
    return [json.loads(p.read_text()) for p in picks]


def prepare_db(iid: str) -> None:
    """Reset to the shared seed, then install the instance's drift trigger."""
    reset_database()
    conn = get_connection()
    try:
        apply_drift(conn, iid)
    finally:
        conn.close()


def run_workflow_instance(inst: dict) -> tuple[dict, dict]:
    logger = ExecutionLogger()
    logger.start()
    state = workflow.invoke(
        {"input_id": inst["id"], "instruction": inst["instruction"]},
        config={"callbacks": [logger]},
    )
    logger.stop()
    return state.get("output", {}), logger.to_record()


def run_agent_instance(inst: dict) -> tuple[str, dict]:
    logger = ExecutionLogger()
    logger.start()
    result = run_agent(inst["instruction"], config={"callbacks": [logger]})
    logger.stop()
    summary = result["messages"][-1].content if result.get("messages") else ""
    return summary, logger.to_record()


def main() -> None:
    all_ = "--all" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    instances = load_instances(all_, only)
    rows: list[dict] = []
    print(f"{'instance':8} {'variant':20} {'paradigm':9} {'correct':7} {'tokens':>8} {'tools':>5} {'lat_s':>6}  summary")
    print("-" * 112)
    for inst in instances:
        for name, runner in (("workflow", run_workflow_instance), ("agent", run_agent_instance)):
            row: dict = {
                "instance": inst["id"],
                "family": "M",
                "variant": inst["variant"],
                "difficulty": inst["difficulty"],
                "sub_class": inst.get("sub_class"),
                "paradigm": name,
            }
            try:
                prepare_db(inst["id"])
                output, rec = runner(inst)
                s, rationale = score(inst["id"], PREDICATES)
                ok = s >= 1.0
                summary = output.get("summary", "") if isinstance(output, dict) else str(output)
                row.update({"correct": ok, "summary": summary[:120], "predicate_rationale": rationale, **rec})
                print(
                    f"{inst['id']:8} {inst['variant']:20} {name:9} {str(ok):7} {rec['total_tokens']:>8} "
                    f"{rec['tool_call_count']:>5} {rec['latency_s']:>6.1f}  {str(summary)[:44]!r}"
                )
            except Exception as e:  # noqa: BLE001
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{inst['id']:8} {inst['variant']:20} {name:9} ERROR  {str(e)[:60]}")
            rows.append(row)

    out_dir = phase2b_results_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"m_validation_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "model": MODEL_NAME, "run_label": RUN_LABEL or "adhoc", "family": "M", "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
