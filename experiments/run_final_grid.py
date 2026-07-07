"""Orchestrate the final Phase 2 evaluation grid across the capability tiers.

Grid design (deviation D-032): all eight archetypes on the FROZEN artifact
state, three capability tiers --

    gpt-5.4-nano   2x clean sweep + 1x robustness   (capability tier 1)
    gpt-5.4-mini   2x clean sweep + 1x robustness   (capability tier 2)
    gpt-5.2        1x clean sweep + 1x robustness   (reference tier, judge model)

The two runs on the weaker tiers provide the run-to-run variance estimate
(IT-042 discipline); the single gpt-5.2 clean run is read conservatively
against that estimate (cost decision, documented in the deviation). The
judge stays frozen on gpt-5.2 for every backbone tier.

Results are routed to ``data/results/final/<model>/<run_label>/`` via the
TADF_RUN_LABEL mechanism in ``src/core/llm.py``, so path, file stamp, and
aggregation key all carry the model and run assignment.

Usage:
    PYTHONPATH=. python experiments/run_final_grid.py --dry-run
    PYTHONPATH=. python experiments/run_final_grid.py --phase clean
    PYTHONPATH=. python experiments/run_final_grid.py --phase robustness
    PYTHONPATH=. python experiments/run_final_grid.py --model gpt-5.4-mini-2026-03-17
    PYTHONPATH=. python experiments/run_final_grid.py --archetype f g h
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

NANO = "gpt-5.4-nano-2026-03-17"
MINI = "gpt-5.4-mini-2026-03-17"
REF = "gpt-5.2-2025-12-11"

ARCHETYPES = ["a", "b", "c", "d", "e", "f", "g", "h"]

#: (model, run_label) cells of the grid, per phase.
CLEAN_CELLS = [
    (NANO, "run1"), (NANO, "run2"),
    (MINI, "run1"), (MINI, "run2"),
    (REF, "run1"),
]
ROBUSTNESS_CELLS = [
    (NANO, "robustness"), (MINI, "robustness"), (REF, "robustness"),
]


def _cmd(script: str, all_flag: bool) -> list[str]:
    cmd = [sys.executable, f"experiments/{script}.py"]
    if all_flag:
        cmd.append("--all")
    return cmd


def run_cell(model: str, label: str, script: str, all_flag: bool, dry: bool) -> bool:
    env = {**os.environ, "TADF_MODEL": model, "TADF_RUN_LABEL": label}
    cmd = _cmd(script, all_flag)
    tag = f"[{model} | {label}] {' '.join(cmd[1:])}"
    if dry:
        print("DRY ", tag)
        return True
    print("RUN ", tag, flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=REPO, env=env)
    ok = proc.returncode == 0
    print(f"{'OK  ' if ok else 'FAIL'} {tag} ({time.time() - t0:.0f}s)", flush=True)
    return ok


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the final evaluation grid.")
    ap.add_argument("--phase", choices=["clean", "robustness", "all"], default="all")
    ap.add_argument("--model", nargs="*", help="restrict to these model names")
    ap.add_argument("--run", nargs="*", help="restrict to these run labels (run1, run2, robustness)")
    ap.add_argument("--archetype", nargs="*", help="restrict to these archetypes (a..h)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    archetypes = [a.lower() for a in (args.archetype or ARCHETYPES)]
    failures: list[str] = []

    def _filter(cells):
        return [
            (m, l) for (m, l) in cells
            if (not args.model or m in args.model) and (not args.run or l in args.run)
        ]

    if args.phase in ("clean", "all"):
        for model, label in _filter(CLEAN_CELLS):
            for arch in archetypes:
                if not run_cell(model, label, f"validate_{arch}", True, args.dry_run):
                    failures.append(f"{model}/{label}/validate_{arch}")
    if args.phase in ("robustness", "all"):
        for model, label in _filter(ROBUSTNESS_CELLS):
            for arch in archetypes:
                if not run_cell(model, label, f"validate_{arch}_robustness", False, args.dry_run):
                    failures.append(f"{model}/{label}/validate_{arch}_robustness")

    print("\n" + "=" * 60)
    if failures:
        print(f"{len(failures)} cell(s) FAILED:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("Grid complete. Aggregate with: PYTHONPATH=. python experiments/aggregate_results.py")


if __name__ == "__main__":
    main()
