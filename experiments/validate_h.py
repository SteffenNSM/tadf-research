"""End-to-end validation for archetype H with the real LLM.

Runs the fixed-pipeline workflow and the self-revision agent on each
drafting instance, then scores each artefact twice: the deterministic
compliance layer (objective anchor) and the frozen-prompt LLM judge (OQS,
the protocol success metric). Persists a per-run telemetry record plus both
scores to a results JSON, and writes a human-rating template (CSV) for the
20% kappa validation the protocol mandates for OQS archetypes.

Per-run fields:
    compliance_all_pass / compliance_rate / compliance_breakdown
    oqs (judge mean 1-5) / judge_scores (per criterion)
    judge_disagreement  — judge rated completeness/responsiveness high (>=4)
                          while the deterministic layer found a missing
                          required point or missing feedback (a built-in
                          judge-reliability flag beyond kappa)
    iteration_overflow / agent_turns
    No DB is touched (H is pure generation): no reset between runs.

Run:
    python experiments/seed_drafting.py     # generate instances
    python experiments/validate_h.py         # one instance per difficulty
    python experiments/validate_h.py --all   # all 15 instances
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from src.archetypes.h_content_drafting.agent import run_agent
from src.archetypes.h_content_drafting.ground_truth import check_compliance
from src.archetypes.h_content_drafting.judge import judge_artifact
from src.archetypes.h_content_drafting.workflow import run_workflow
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "h_content_drafting"
RESULTS = REPO / "data" / "results"


def load_instances(all_: bool) -> list[dict]:
    if all_:
        picks = [f"{lvl}/h-{lvl}-{n}" for lvl in ("low", "med", "high") for n in range(1, 6)]
    else:
        picks = ["low/h-low-1", "med/h-med-1", "high/h-high-1"]
    return [json.loads((IN / f"{p}.json").read_text()) for p in picks]


def _disagreement(judge_scores, breakdown: dict) -> bool:
    """Judge says complete/responsive (>=4) but deterministic layer found gaps."""
    missing = bool(breakdown.get("missing_points")) or bool(breakdown.get("missing_feedback"))
    high_soft = judge_scores.completeness >= 4 or judge_scores.responsiveness >= 4
    return missing and high_soft


def run_one(inst: dict, paradigm: str) -> dict:
    logger = ExecutionLogger()
    logger.start()
    overflow = False
    turns = None
    if paradigm == "workflow":
        out = run_workflow(inst, config={"callbacks": [logger]})
    else:
        state = run_agent(inst, config={"callbacks": [logger]})
        out = state.get("draft", {})
        overflow = bool(state.get("iteration_overflow"))
        turns = state.get("turns")
    logger.stop()
    title = out.get("title", "") if isinstance(out, dict) else ""
    body = out.get("body", "") if isinstance(out, dict) else str(out)

    all_pass, rate, breakdown = check_compliance(inst, title, body)
    scores = judge_artifact(inst, title, body)
    rec = logger.to_record()
    return {
        "instance": inst["id"], "difficulty": inst["difficulty"],
        "sub_class": inst.get("sub_class"), "format": inst["format"], "paradigm": paradigm,
        "compliance_all_pass": all_pass, "compliance_rate": round(rate, 3),
        "compliance_breakdown": breakdown,
        "oqs": round(scores.mean(), 3), "judge_scores": scores.model_dump(),
        "judge_disagreement": _disagreement(scores, breakdown),
        "iteration_overflow": overflow, "agent_turns": turns,
        "title": title, "body": body, **rec,
    }


def main() -> None:
    all_ = "--all" in sys.argv
    instances = load_instances(all_)
    rows: list[dict] = []
    print(f"{'instance':11} {'paradigm':9} {'compl':6} {'rate':>5} {'oqs':>4} "
          f"{'tok':>7} {'turns':>5} {'ovf':>4}  flags")
    print("-" * 92)
    for inst in instances:
        for paradigm in ("workflow", "agent"):
            try:
                row = run_one(inst, paradigm)
                flags = []
                if row["judge_disagreement"]:
                    flags.append("JUDGE_DISAGREE")
                if row["iteration_overflow"]:
                    flags.append("OVERFLOW")
                print(f"{inst['id']:11} {paradigm:9} {str(row['compliance_all_pass']):6} "
                      f"{row['compliance_rate']:>5} {row['oqs']:>4} {row['total_tokens']:>7} "
                      f"{str(row['agent_turns'] or ''):>5} {str(row['iteration_overflow']):>4}  {','.join(flags)}")
            except Exception as e:  # noqa: BLE001
                row = {"instance": inst["id"], "paradigm": paradigm, "error": str(e)[:200]}
                print(f"{inst['id']:11} {paradigm:9} ERROR  {str(e)[:70]}")
            rows.append(row)

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"h_validation_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")

    # Human-rating template for the 20% kappa validation (protocol A.7):
    # one instance per difficulty, both paradigms = 6 artefacts.
    sample_ids = {"h-low-1", "h-med-1", "h-high-1"}
    kappa_rows = [r for r in rows if r.get("instance") in sample_ids and "error" not in r]
    if kappa_rows:
        kpath = RESULTS / f"h_kappa_template_{stamp}.csv"
        with kpath.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["instance", "paradigm", "criterion", "judge_score", "human_score (fill 1-5)"])
            for r in kappa_rows:
                for crit in ("completeness", "responsiveness", "coherence", "tone_audience", "conciseness"):
                    w.writerow([r["instance"], r["paradigm"], crit, r["judge_scores"][crit], ""])
        print(f"Kappa human-rating template: {kpath.relative_to(REPO)}")
        print("  (rate each artefact 1-5 per criterion, then compute Cohen's weighted kappa vs judge_score)")


if __name__ == "__main__":
    main()
