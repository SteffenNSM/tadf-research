"""Generate a blind human-rating sheet for the H judge kappa validation (A.7).

Produces, from the saved H sweep, a self-contained Markdown rating sheet for
the 20% stratified sample (one instance per difficulty x both paradigms = 6
artefacts), anonymized so the rater sees neither the paradigm nor the judge
score (both would anchor the rating and invalidate the kappa). The human
fills one 1-5 score per criterion per artefact; kappa vs the saved judge
scores is computed afterwards by joining on the hidden key.

Outputs (under data/results/):
    h_kappa_rating_sheet.md   — read this, rate each artefact
    h_kappa_scores_blank.csv  — enter your scores here (or in the .md)
    h_kappa_key.csv           — hidden artefact -> (instance, paradigm) map
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "h_content_drafting"
RESULTS = REPO / "data" / "results"
SWEEP = RESULTS / "h_validation_20260616_111547.json"

SAMPLE = [("h-low-1", "low"), ("h-med-1", "med"), ("h-high-1", "high")]

CRITERIA = [
    ("completeness", "Conveys the substance the brief asks for, using the table's data.",
     "1 = misses most required content; 3 = covers the main points, minor gaps; 5 = fully covers everything the brief asks for."),
    ("responsiveness", "Reflects the reviewer feedback that was given (if no feedback was given, score 5).",
     "1 = ignores the feedback; 3 = partially incorporates it; 5 = fully incorporates every requested change (or no feedback was given)."),
    ("coherence", "Logical organization and structure appropriate to the format.",
     "1 = disorganized/hard to follow; 3 = readable, some flow issues; 5 = clear, well-structured for the format."),
    ("tone_audience", "Matches the required tonality and suits the stated audience.",
     "1 = wrong tone/register for the audience; 3 = acceptable but uneven; 5 = pitch-perfect for tone and audience."),
    ("conciseness", "Free of padding and redundancy; tight for its purpose. Do NOT reward length.",
     "1 = padded/repetitive; 3 = mostly tight, some filler; 5 = no wasted words."),
]


def _load_instances() -> dict:
    out = {}
    for iid, lvl in SAMPLE:
        out[iid] = json.loads((IN / lvl / f"{iid}.json").read_text())
    return out


def _load_bodies() -> dict:
    d = json.loads(SWEEP.read_text())
    bodies = {}
    for r in d["runs"]:
        if "error" in r:
            continue
        bodies[(r["instance"], r["paradigm"])] = {"title": r.get("title", ""), "body": r.get("body", "")}
    return bodies


def _render_brief(inst: dict) -> str:
    c = inst["constraints"]
    t = inst["table"]
    cols = " | ".join(t["columns"])
    sep = " | ".join("---" for _ in t["columns"])
    rows = "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in t["rows"])
    lines = [
        f"**Task:** {inst['instruction']}",
        f"**Format:** {inst['format']}  |  **Audience:** {c['audience']}  |  **Tonality:** {c['tonality']}  |  **Length window:** {c['min_words']}–{c['max_words']} words",
    ]
    if c.get("framing"):
        lines.append(f"**Framing requested:** {c['framing']}")
    if c.get("required_sections"):
        lines.append("**Required sections:** " + "; ".join(c["required_sections"]))
    if c.get("required_points"):
        lines.append("**Required data points:** " + "; ".join(p["desc"] for p in c["required_points"]))
    lines.append("")
    lines.append(f"**Data table — _{t.get('caption','')}_**")
    lines.append("")
    lines.append(f"| {cols} |")
    lines.append(f"| {sep} |")
    lines.append(rows)
    if inst.get("feedback_rounds"):
        lines.append("")
        lines.append("**Reviewer feedback given during drafting:**")
        for i, fb in enumerate(inst["feedback_rounds"], 1):
            lines.append(f"  {i}. {fb}")
    return "\n".join(lines)


def main() -> None:
    instances = _load_instances()
    bodies = _load_bodies()

    artefacts = [(iid, par) for iid, _ in SAMPLE for par in ("workflow", "agent")]
    random.Random(42).shuffle(artefacts)
    labels = [f"Artefact {chr(65 + i)}" for i in range(len(artefacts))]  # A..F

    md: list[str] = []
    md.append("# H Judge Validation — Blind Human Rating Sheet\n")
    md.append("Rate each of the six artefacts on the five criteria below, **1 to 5** "
              "(integers). Rate each artefact **on its own**, against its brief. "
              "Do **not** try to guess which system wrote it, and rate before looking "
              "at any model score — the whole point is an independent second opinion "
              "to validate the automated judge (Cohen's weighted kappa, threshold "
              "kappa >= 0.6).\n")
    md.append("## Criteria (same five the automated judge uses)\n")
    for name, desc, anchors in CRITERIA:
        md.append(f"- **{name}** — {desc}\n  _{anchors}_")
    md.append("\n> Scoring tip: 3 is \"adequate / acceptable\", 4 is \"good\", 5 is "
              "\"excellent\". Reserve 1–2 for real problems. Conciseness is NOT about "
              "length alone — a short artefact can still be padded, a longer one tight.\n")
    md.append("---\n")

    for label, (iid, par) in zip(labels, artefacts):
        art = bodies[(iid, par)]
        md.append(f"## {label}\n")
        md.append(_render_brief(instances[iid]))
        md.append("\n**Artefact under review:**\n")
        if art["title"]:
            md.append(f"> _Subject/Title:_ {art['title']}\n")
        md.append("```")
        md.append(art["body"])
        md.append("```\n")
        md.append("**Your scores (1–5):**\n")
        for name, _, _ in CRITERIA:
            md.append(f"- {name}: ____")
        md.append("\n---\n")

    (RESULTS / "h_kappa_rating_sheet.md").write_text("\n".join(md))

    with (RESULTS / "h_kappa_scores_blank.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["artefact", "criterion", "human_score (1-5)"])
        for label in labels:
            for name, _, _ in CRITERIA:
                w.writerow([label, name, ""])

    with (RESULTS / "h_kappa_key.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["artefact", "instance", "paradigm"])
        for label, (iid, par) in zip(labels, artefacts):
            w.writerow([label, iid, par])

    print("Wrote h_kappa_rating_sheet.md, h_kappa_scores_blank.csv, h_kappa_key.csv")


if __name__ == "__main__":
    main()
