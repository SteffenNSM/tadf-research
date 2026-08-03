"""End-to-end validation for Phase 2b family P (plan uncertainty) with the real LLM.

Runs the workflow and the agent on the 20 family-P instances, captures the
execution telemetry, resets the database before each run, and scores the
outcome by querying the post-state of the database against the registered
predicate.

Both paradigm implementations are imported UNCHANGED from archetype F
(frozen artifact state, IT-055 build decision): the two-stage
plan_reads -> execute_reads -> plan_actions -> execute_actions workflow and
the ReAct agent with the identical toolset. Family P varies only the task
instances, so observed differences attribute to the plan-uncertainty axis of
the instance, not to implementation changes.

Results are routed to ``data/results/phase2b/<model>/<run_label>/`` (or
``.../adhoc/`` when no TADF_RUN_LABEL is set), keeping Phase 2b evidence
separate from the Phase 2a grid under ``data/results/final/``.

Run:
    PYTHONPATH=. python experiments/seed_crm.py     # if not yet generated
    PYTHONPATH=. python experiments/seed_p.py       # write the 20 instances
    PYTHONPATH=. python experiments/load_db.py      # build crm.db from seed
    PYTHONPATH=. python experiments/validate_p.py         # smoke: one instance per variant
    PYTHONPATH=. python experiments/validate_p.py --all   # all 20 instances
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from experiments.load_db import load as reset_database
from experiments.seed_p import PREDICATES, VARIANT_DIRS
from src.archetypes.f_action_execution.agent import run_agent
from src.archetypes.f_action_execution.ground_truth import score
from src.archetypes.f_action_execution.workflow import workflow
from src.core.llm import MODEL_NAME, RUN_LABEL
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "p_plan_uncertainty"
RESULTS = REPO / "data" / "results" / "phase2b"

VARIANTS = ["a_count_read", "b_count_outcome", "c_source_unknown", "d_derived_order"]


def phase2b_results_dir() -> Path:
    """Phase 2b routing: <results>/phase2b/<model>/<run_label or 'adhoc'>/."""
    target = RESULTS / MODEL_NAME / (RUN_LABEL or "adhoc")
    target.mkdir(parents=True, exist_ok=True)
    return target


def load_instances(all_: bool, only: list[str] | None = None) -> list[dict]:
    picks: list[Path] = []
    for variant in VARIANTS:
        letter = variant.split("_")[0]
        ns = range(1, 6) if all_ else (1,)
        picks += [IN / VARIANT_DIRS[variant] / f"p-{letter}-{n}.json" for n in ns]
    if only:
        picks = [
            IN / VARIANT_DIRS[v] / f"{iid}.json"
            for iid in only
            for v in VARIANTS
            if v.startswith(iid.split("-")[1] + "_")
        ]
    return [json.loads(p.read_text()) for p in picks]


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
    print(f"{'instance':9} {'variant':16} {'paradigm':9} {'correct':7} {'tokens':>8} {'tools':>5} {'lat_s':>6}  summary")
    print("-" * 110)
    for inst in instances:
        for name, runner in (("workflow", run_workflow_instance), ("agent", run_agent_instance)):
            row: dict = {
                "instance": inst["id"],
                "family": "P",
                "variant": inst["variant"],
                "difficulty": inst["difficulty"],
                "sub_class": inst.get("sub_class"),
                "paradigm": name,
            }
            try:
                reset_database()
                output, rec = runner(inst)
                s, rationale = score(inst["id"], PREDICATES)
                ok = s >= 1.0
                summary = output.get("summary", "") if isinstance(output, dict) else str(output)
                row.update({"correct": ok, "summary": summary[:120], "predicate_rationale": rationale, **rec})
                print(
                    f"{inst['id']:9} {inst['variant']:16} {name:9} {str(ok):7} {rec['total_tokens']:>8} "
                    f"{rec['tool_call_count']:>5} {rec['latency_s']:>6.1f}  {str(summary)[:50]!r}"
                )
            except Exception as e:  # noqa: BLE001
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{inst['id']:9} {inst['variant']:16} {name:9} ERROR  {str(e)[:70]}")
            rows.append(row)

    out_dir = phase2b_results_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"p_validation_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "model": MODEL_NAME, "run_label": RUN_LABEL or "adhoc", "family": "P", "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
