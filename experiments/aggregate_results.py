"""Aggregate the final-grid results into one master CSV plus console pivots.

Walks ``data/results/final/<model>/<run_label>/*.json`` (the run_final_grid
output), normalizes the per-archetype success fields, and writes
``data/results/final/master_results.csv`` with one row per (archetype,
instance, paradigm, model, run_label, kind). The console prints the two
pivots the thesis tables are built from: success per archetype x model x
paradigm, and average tokens per archetype x model x paradigm.

Success-field normalization (the harnesses differ deliberately):
    C            -> all_correct        (per-email batch, all labels right)
    H            -> compliance_all_pass (deterministic compliance layer)
    A/B/D/E/F/G  -> correct

Usage:
    PYTHONPATH=. python experiments/aggregate_results.py
    PYTHONPATH=. python experiments/aggregate_results.py --include-dev
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FINAL_DIR = REPO / "data" / "results" / "final"
DEV_DIR = REPO / "data" / "results" / "dev"
OUT_CSV = FINAL_DIR / "master_results.csv"

COLUMNS = [
    "archetype", "kind", "instance", "base_instance", "difficulty", "sub_class",
    "perturbation_type", "paradigm", "model", "run_label", "success",
    "total_tokens", "input_tokens", "output_tokens", "tool_call_count",
    "latency_s", "iteration_overflow", "error", "source_file",
]


def _archetype(fname: str) -> str:
    return fname.split("_")[0].upper()


def _kind(fname: str) -> str:
    return "robustness" if "robustness" in fname else "clean"


def _success(archetype: str, run: dict) -> bool | None:
    if archetype == "C":
        v = run.get("all_correct")
        if v is None and run.get("accuracy") is not None:
            # validate_c_robustness records per-item accuracy without the
            # all_correct flag; a batch counts as solved at accuracy 1.0.
            v = float(run["accuracy"]) >= 1.0
    elif archetype == "H":
        v = run.get("compliance_all_pass")
    else:
        v = run.get("correct")
    return bool(v) if v is not None else None


def _rows_from_file(path: Path, run_label: str, model_dir: str) -> list[dict]:
    data = json.loads(path.read_text())
    runs = data.get("runs", [])
    model = data.get("model", model_dir)
    archetype = _archetype(path.name)
    kind = _kind(path.name)
    rows = []
    for r in runs:
        rows.append({
            "archetype": archetype, "kind": kind,
            "instance": r.get("instance"), "base_instance": r.get("base_instance"),
            "difficulty": r.get("difficulty"), "sub_class": r.get("sub_class"),
            "perturbation_type": r.get("perturbation_type"),
            "paradigm": r.get("paradigm"), "model": model, "run_label": run_label,
            "success": _success(archetype, r),
            "total_tokens": r.get("total_tokens"),
            "input_tokens": r.get("input_tokens"),
            "output_tokens": r.get("output_tokens"),
            "tool_call_count": r.get("tool_call_count"),
            "latency_s": r.get("latency_s"),
            "iteration_overflow": r.get("iteration_overflow"),
            "error": (r.get("error") or "")[:80],
            "source_file": str(path.relative_to(REPO)),
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-dev", action="store_true",
                    help="also aggregate unlabeled dev runs (run_label='dev')")
    args = ap.parse_args()

    rows: list[dict] = []
    if FINAL_DIR.exists():
        for model_dir in sorted(p for p in FINAL_DIR.iterdir() if p.is_dir()):
            for label_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
                for f in sorted(label_dir.glob("*.json")):
                    rows.extend(_rows_from_file(f, label_dir.name, model_dir.name))
    if args.include_dev and DEV_DIR.exists():
        for f in sorted(DEV_DIR.glob("*.json")):
            rows.extend(_rows_from_file(f, "dev", "dev"))

    if not rows:
        print("No grid results found under", FINAL_DIR)
        return

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} rows written to {OUT_CSV.relative_to(REPO)}\n")

    # Pivot 1: success per archetype x model x paradigm (clean runs, per run_label)
    agg = defaultdict(lambda: [0, 0])
    tok = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["kind"] != "clean" or r["success"] is None:
            continue
        key = (r["archetype"], r["model"], r["run_label"], r["paradigm"])
        agg[key][0] += int(r["success"]); agg[key][1] += 1
        if r["total_tokens"]:
            tok[key][0] += r["total_tokens"]; tok[key][1] += 1

    print(f"{'arch':4} {'model':28} {'run':6} {'paradigm':9} {'success':>8} {'avg_tok':>8}")
    print("-" * 70)
    for key in sorted(agg):
        s, n = agg[key]
        t, tn = tok.get(key, (0, 0))
        avg = t // tn if tn else 0
        print(f"{key[0]:4} {key[1]:28} {key[2]:6} {key[3]:9} {f'{s}/{n}':>8} {avg:>8}")


if __name__ == "__main__":
    main()
