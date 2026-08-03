"""End-to-end validation for Phase 2b family S (staged adaptivity) with the real LLM.

Family S compares THREE execution forms (IT-066): the canonical two-stage
workflow, the ReAct agent (both imported UNCHANGED from archetype F), and the
new state-machine workflow (``state_machine.py`` -- compiled conditional
control flow, LLM at plan time only).

Sweep economics (join discipline):
- **s1_enumerated_switch** reuses the family-X x1 instances and
  **s2_bounded_until** reuses the family-P p-b instances VERBATIM. Only the
  state machine runs on them here; the canonical workflow/agent numbers for
  identical instances come from the family-X/P grids (join key: instance id).
- **s3_content_synthesis** is new, so ALL THREE forms run on it.

The database is reset before each run; scoring uses the registered
outcome-centric post-state predicates of the source families. Results are
routed to ``data/results/phase2b/<model>/<run_label>/`` (``adhoc`` unlabeled).

Run:
    PYTHONPATH=. python experiments/seed_s.py       # write the 5 s3 instances
    PYTHONPATH=. python experiments/load_db.py      # build crm.db from seed
    PYTHONPATH=. python experiments/validate_s.py         # smoke: one per variant
    PYTHONPATH=. python experiments/validate_s.py --all   # full family (25 runs)
    PYTHONPATH=. python experiments/validate_s.py --only s3-3,p-b-1
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from experiments.load_db import load as reset_database
from experiments.seed_p import PREDICATES as P_PREDICATES
from experiments.seed_s import PREDICATES as S_PREDICATES
from experiments.seed_s import S1_IDS, S2_IDS
from experiments.seed_x import PREDICATES as X_PREDICATES
from src.archetypes.f_action_execution.agent import run_agent
from src.archetypes.f_action_execution.ground_truth import score
from src.archetypes.f_action_execution.state_machine import state_machine
from src.archetypes.f_action_execution.workflow import workflow
from src.core.llm import MODEL_NAME, RUN_LABEL
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
IN_X = REPO / "data" / "test_inputs" / "x_crossed_gates" / "x1_rule_on_outcome"
IN_P = REPO / "data" / "test_inputs" / "p_plan_uncertainty" / "b_count_outcome"
IN_S = REPO / "data" / "test_inputs" / "s_staged_adaptivity" / "s3_content_synthesis"
RESULTS = REPO / "data" / "results" / "phase2b"

PREDICATES = {**X_PREDICATES, **P_PREDICATES, **S_PREDICATES}

S3_IDS = [f"s3-{n}" for n in range(1, 6)]

#: variant -> (instance ids, source dir, execution forms swept HERE).
#: s1/s2: state machine only -- canonical W/A rows join from families X/P.
VARIANTS: dict[str, tuple[list[str], Path, list[str]]] = {
    "s1_enumerated_switch": (S1_IDS, IN_X, ["state_machine"]),
    "s2_bounded_until": (S2_IDS, IN_P, ["state_machine"]),
    "s3_content_synthesis": (S3_IDS, IN_S, ["workflow", "agent", "state_machine"]),
}


def phase2b_results_dir() -> Path:
    target = RESULTS / MODEL_NAME / (RUN_LABEL or "adhoc")
    target.mkdir(parents=True, exist_ok=True)
    return target


def load_plan(all_: bool, only: list[str] | None = None) -> list[tuple[dict, str, list[str]]]:
    """Return (instance, variant, forms) triples for the requested sweep."""
    plan: list[tuple[dict, str, list[str]]] = []
    for variant, (ids, src, forms) in VARIANTS.items():
        picks = ids if all_ else ids[:1]
        if only:
            picks = [i for i in ids if i in only]
        for iid in picks:
            inst = json.loads((src / f"{iid}.json").read_text())
            plan.append((inst, variant, forms))
    return plan


def run_workflow_instance(inst: dict) -> tuple[dict, dict]:
    logger = ExecutionLogger()
    logger.start()
    state = workflow.invoke(
        {"input_id": inst["id"], "instruction": inst["instruction"]},
        config={"callbacks": [logger]},
    )
    logger.stop()
    return state.get("output", {}), logger.to_record()


def run_state_machine_instance(inst: dict) -> tuple[dict, dict]:
    logger = ExecutionLogger()
    logger.start()
    state = state_machine.invoke(
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


RUNNERS = {
    "workflow": run_workflow_instance,
    "agent": run_agent_instance,
    "state_machine": run_state_machine_instance,
}


def main() -> None:
    all_ = "--all" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    plan = load_plan(all_, only)
    rows: list[dict] = []
    print(f"{'instance':9} {'variant':22} {'paradigm':14} {'correct':7} {'tokens':>8} {'tools':>5} {'lat_s':>6}  summary")
    print("-" * 120)
    for inst, variant, forms in plan:
        for name in forms:
            row: dict = {
                "instance": inst["id"],
                "family": "S",
                "variant": variant,
                "difficulty": inst.get("difficulty", "na"),
                "sub_class": inst.get("sub_class"),
                "source_family": inst.get("archetype", "S"),
                "paradigm": name,
            }
            try:
                reset_database()
                output, rec = RUNNERS[name](inst)
                s, rationale = score(inst["id"], PREDICATES)
                ok = s >= 1.0
                summary = output.get("summary", "") if isinstance(output, dict) else str(output)
                row.update({"correct": ok, "summary": summary[:120], "predicate_rationale": rationale, **rec})
                print(
                    f"{inst['id']:9} {variant:22} {name:14} {str(ok):7} {rec['total_tokens']:>8} "
                    f"{rec['tool_call_count']:>5} {rec['latency_s']:>6.1f}  {str(summary)[:40]!r}"
                )
            except Exception as e:  # noqa: BLE001
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{inst['id']:9} {variant:22} {name:14} ERROR  {str(e)[:55]}")
            rows.append(row)

    out_dir = phase2b_results_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"s_validation_{stamp}.json"
    out.write_text(json.dumps({
        "timestamp": stamp, "model": MODEL_NAME, "run_label": RUN_LABEL or "adhoc",
        "family": "S", "runs": rows,
    }, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
