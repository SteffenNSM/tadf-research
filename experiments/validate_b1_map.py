"""B1 confirmation sweep (IT-069): map-form workflow on the frozen f-med instances.

Runs ONLY the new map-form workflow (``map_workflow.py``) on the two
pre-registered instances; the canonical workflow and agent numbers for the
identical instances JOIN from the final F grid (family-S join discipline,
zero duplicate spend):

- **f-med-3** (target): nine account updates, each with its own owner and
  note — the cell where the single-plan workflow measured 2/5 vs the agent's
  5/5.
- **f-med-4** (control): sixteen identical updates — 5/5 for both paradigms;
  the map form must not regress it.

Database reset before each run; scoring via the registered outcome-centric
post-state predicates of the F seed. Results are routed to
``data/results/phase2b/<model>/<run_label>/`` (``adhoc`` unlabeled), family
tag "B1".

Run (grid discipline as in the other families):
    PYTHONPATH=. python experiments/validate_b1_map.py            # both instances
    PYTHONPATH=. python experiments/validate_b1_map.py --only f-med-3
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from experiments.load_db import load as reset_database
from experiments.seed_actions import PREDICATES
from src.archetypes.f_action_execution.ground_truth import score
from src.archetypes.f_action_execution.map_workflow import map_workflow
from src.core.llm import MODEL_NAME, RUN_LABEL
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "f_action_execution" / "med"
RESULTS = REPO / "data" / "results" / "phase2b"

#: Pre-registered sweep scope (IT-069): target + control. Widening the scope
#: after seeing results would break the pre-registration — do not add ids here.
INSTANCE_IDS = ["f-med-3", "f-med-4"]


def phase2b_results_dir() -> Path:
    target = RESULTS / MODEL_NAME / (RUN_LABEL or "adhoc")
    target.mkdir(parents=True, exist_ok=True)
    return target


def run_map_instance(inst: dict) -> tuple[dict, dict]:
    logger = ExecutionLogger()
    logger.start()
    state = map_workflow.invoke(
        {"input_id": inst["id"], "instruction": inst["instruction"]},
        config={"callbacks": [logger]},
    )
    logger.stop()
    return state.get("output", {}), logger.to_record()


def main() -> None:
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    ids = [i for i in INSTANCE_IDS if (only is None or i in only)]
    rows: list[dict] = []
    print(f"{'instance':10} {'paradigm':13} {'correct':7} {'tokens':>8} {'tools':>5} {'lat_s':>6}  summary")
    print("-" * 110)
    for iid in ids:
        inst = json.loads((IN / f"{iid}.json").read_text())
        row: dict = {
            "instance": inst["id"],
            "family": "B1",
            "variant": "map_form_confirmation",
            "difficulty": inst.get("difficulty", "med"),
            "sub_class": inst.get("sub_class"),
            "paradigm": "map_workflow",
        }
        try:
            reset_database()
            output, rec = run_map_instance(inst)
            s, rationale = score(inst["id"], PREDICATES)
            ok = s >= 1.0
            summary = output.get("summary", "") if isinstance(output, dict) else str(output)
            row.update({"correct": ok, "summary": summary[:120],
                        "predicate_rationale": rationale, **rec})
            print(
                f"{inst['id']:10} {'map_workflow':13} {str(ok):7} {rec['total_tokens']:>8} "
                f"{rec['tool_call_count']:>5} {rec['latency_s']:>6.1f}  {str(summary)[:45]!r}"
            )
        except Exception as e:  # noqa: BLE001
            row.update({"correct": False, "error": str(e)[:200]})
            print(f"{inst['id']:10} {'map_workflow':13} ERROR  {str(e)[:60]}")
        rows.append(row)

    out_dir = phase2b_results_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"b1_validation_{stamp}.json"
    out.write_text(json.dumps({
        "timestamp": stamp, "model": MODEL_NAME, "run_label": RUN_LABEL or "adhoc",
        "family": "B1", "runs": rows,
    }, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
