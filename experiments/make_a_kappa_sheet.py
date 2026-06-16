"""Generate a blind human-rating sheet for the A judge kappa validation (A.7).

Archetype A's OQS judge renders a BINARY verdict (correct / incorrect) on a
short research answer against a gold answer. This builds a blind sheet for a
verdict-stratified sample: one instance per difficulty x paradigm, with the
single instance the judge marked INCORRECT (a-high-4 workflow) deliberately
included so the validation tests both the judge's positive and negative
calls — a sample of only "correct" verdicts could not distinguish a good
judge from one that always says correct. The rater sees the question, the
gold answer, and the candidate answer, anonymized (no paradigm, no judge
verdict), and marks each correct (1) or incorrect (0).

Outputs (under data/results/):
    a_kappa_rating_sheet.md   — read and rate
    a_kappa_scores_blank.csv  — enter verdicts here
    a_kappa_key.csv           — hidden artefact -> (instance, paradigm) map
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "a_exploratory_research"
RESULTS = REPO / "data" / "results"
SWEEP = RESULTS / "a_validation_20260527_093105.json"

# verdict-stratified sample: one per cell; the high/workflow cell uses
# a-high-4, the single instance the judge marked incorrect.
SAMPLE = [
    ("a-low-1", "low", "workflow"), ("a-low-1", "low", "agent"),
    ("a-med-1", "med", "workflow"), ("a-med-1", "med", "agent"),
    ("a-high-4", "high", "workflow"), ("a-high-4", "high", "agent"),
]

GUIDANCE = (
    "Mark each candidate answer **correct (1)** or **incorrect (0)** against the "
    "gold answer, using the same lenient standard the automated judge uses:\n"
    "- Accept different wording, capitalization, units (after sensible conversion), "
    "and numeric precision of the SAME measurement (e.g. 8848, 8848.86, 8849 are the "
    "same elevation).\n"
    "- For list answers, ALL required entities must be present; if the question "
    "specifies an order (chronological, descending by quantity, etc.), the order must match.\n"
    "- Mark incorrect if it states a different fact, names a different entity, gives a "
    "different year/identifier, misses a required list entity, violates a required order, "
    "expresses uncertainty, or omits the answer.\n"
    "Rate independently, before looking at any model verdict."
)


def main() -> None:
    instances = {}
    for iid, lvl, _ in SAMPLE:
        if iid not in instances:
            instances[iid] = json.loads((IN / lvl / f"{iid}.json").read_text())
    d = json.loads(SWEEP.read_text())
    ans = {(r["instance"], r["paradigm"]): r.get("answer", "") for r in d["runs"] if "error" not in r}

    artefacts = list(SAMPLE)
    random.Random(7).shuffle(artefacts)
    labels = [f"Answer {chr(65 + i)}" for i in range(len(artefacts))]

    md = ["# A Judge Validation — Blind Human Rating Sheet\n",
          "Decide, for each of the six candidate answers, whether it is **correct (1)** "
          "or **incorrect (0)** against the gold answer. Rate each on its own; do not try "
          "to guess which system produced it or look at any model verdict first "
          "(Cohen's kappa / Gwet's AC1, threshold 0.6).\n",
          "## Standard\n", GUIDANCE, "\n---\n"]
    for label, (iid, lvl, par) in zip(labels, artefacts):
        inst = instances[iid]
        gt = inst["ground_truth"]
        gold = gt.get("value", gt) if isinstance(gt, dict) else gt
        unit = gt.get("unit", "") if isinstance(gt, dict) else ""
        md.append(f"## {label}\n")
        md.append(f"**Question:** {inst['instruction']}\n")
        md.append(f"**Gold answer:** {gold}" + (f"  _(unit: {unit})_" if unit else "") + "\n")
        md.append(f"**Candidate answer:**\n\n> {ans.get((iid, par), '(missing)')}\n")
        md.append("**Your verdict (1 = correct, 0 = incorrect):** ____\n")
        md.append("---\n")
    (RESULTS / "a_kappa_rating_sheet.md").write_text("\n".join(md))

    with (RESULTS / "a_kappa_scores_blank.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["answer", "human_verdict (1=correct,0=incorrect)"])
        for label in labels:
            w.writerow([label, ""])
    with (RESULTS / "a_kappa_key.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["answer", "instance", "paradigm"])
        for label, (iid, lvl, par) in zip(labels, artefacts):
            w.writerow([label, iid, par])
    print("Wrote a_kappa_rating_sheet.md, a_kappa_scores_blank.csv, a_kappa_key.csv")


if __name__ == "__main__":
    main()
