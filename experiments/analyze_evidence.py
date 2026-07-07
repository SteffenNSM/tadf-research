"""Compute the numbered gate-evidence statistics from the final grid.

Reproduces every number in ``docs/evidence_summary.md`` directly from the
raw results under ``data/results/final/`` (not from the master CSV), so the
summary is verifiable with one command:

    PYTHONPATH=. python experiments/analyze_evidence.py

Sections: G1-G4 gate evidence, saturation cells, the E-high capability
switch, and the deep-pattern census (temperature-0 flip rate, tokens per
SOLVED task, error-direction census for D, E criterion census, G constraint
census, H turns-vs-compliance decay, structural crash counts).
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / "data" / "results" / "final"

RUNTIME_F = {"f-high-1", "f-high-2", "f-high-5"}
SEV = {"APPROVE": 0, "ESCALATE_DIRECTOR": 1, "ESCALATE_VP": 2,
       "ESCALATE_REGIONAL_VP": 3, "DECLINE": 4}


def load():
    data = defaultdict(list)
    for f in BASE.rglob("*.json"):
        if "kappa" in f.name:
            continue
        rel = f.relative_to(BASE)
        arch = f.name.split("_")[0].upper()
        kind = "rob" if "robustness" in f.name else "clean"
        for r in json.load(open(f)).get("runs", []):
            r["_model"], r["_run"] = rel.parts[0], rel.parts[1]
            data[(arch, kind)].append(r)
    return data


def ok(arch, r):
    if arch == "H":
        return bool(r.get("compliance_all_pass"))
    if arch == "C":
        v = r.get("all_correct")
        if v is None and r.get("accuracy") is not None:
            return float(r["accuracy"]) >= 1.0
        return bool(v)
    return bool(r.get("correct"))


def count(rows, arch):
    return sum(1 for r in rows if ok(arch, r)), len(rows)


def main() -> None:
    D = load()
    F = D[("F", "clean")]

    print("G1 runtime feedback (f-high-1/2/5):")
    for p in ("workflow", "agent"):
        s, n = count([r for r in F if r["instance"] in RUNTIME_F and r["paradigm"] == p], "F")
        print(f"  {p}: {s}/{n}")
    print("G1 correction, read-conditional f-med-2:")
    for p in ("workflow", "agent"):
        s, n = count([r for r in F if r["instance"] == "f-med-2" and r["paradigm"] == p], "F")
        print(f"  {p}: {s}/{n}")

    print("G2 rule application (D):")
    Dr = D[("D", "clean")]
    for p in ("workflow", "agent"):
        rows = [r for r in Dr if r["paradigm"] == p]
        s, n = count(rows, "D")
        t = [r["total_tokens"] for r in rows]
        print(f"  {p}: {s}/{n}, tokens {statistics.mean(t):.0f} +/- {statistics.pstdev(t):.0f}")
    errs = [r for r in Dr if r["paradigm"] == "agent" and not ok("D", r)]
    perm = sum(1 for r in errs if SEV.get(r.get("predicted"), 9) < SEV.get(r.get("expected"), -1))
    print(f"  agent errors {len(errs)}, permissive {perm}")

    print("G3 chained search (A high, provider errors excluded):")
    Ar = [r for r in D[("A", "clean")] if r["difficulty"] == "high" and not r.get("error")]
    for p in ("workflow", "agent"):
        s, n = count([r for r in Ar if r["paradigm"] == p], "A")
        print(f"  {p}: {s}/{n}")

    print("G4 enumeration (heterogeneous vs identical):")
    for iid in ("f-med-3", "f-med-5", "f-med-4"):
        for p in ("workflow", "agent"):
            s, n = count([r for r in F if r["instance"] == iid and r["paradigm"] == p], "F")
            print(f"  {iid} {p}: {s}/{n}")

    print("Saturation (H-high, B-high):")
    for arch in ("H", "B"):
        for p in ("workflow", "agent"):
            rows = [r for r in D[(arch, "clean")] if r["difficulty"] == "high" and r["paradigm"] == p]
            s, n = count(rows, arch)
            print(f"  {arch}-high {p}: {s}/{n}")

    print("E-high capability switch:")
    for m in sorted({r["_model"] for r in D[("E", "clean")]}):
        for p in ("workflow", "agent"):
            rows = [r for r in D[("E", "clean")] if r["difficulty"] == "high"
                    and r["_model"] == m and r["paradigm"] == p]
            s, n = count(rows, "E")
            print(f"  {m} {p}: {s}/{n}")

    print("Deep patterns:")
    flips = tot = 0
    for (arch, kind), rows in D.items():
        if kind != "clean":
            continue
        per = defaultdict(dict)
        for r in rows:
            if r["_model"].startswith("gpt-5.2"):
                continue
            per[(r["instance"], r["paradigm"], r["_model"])][r["_run"]] = ok(arch, r)
        for v in per.values():
            if "run1" in v and "run2" in v:
                tot += 1
                flips += v["run1"] != v["run2"]
    print(f"  temp-0 flip rate: {flips}/{tot} = {100*flips/tot:.1f}%")

    print("  tokens per SOLVED task:")
    for arch in "ABCDEFGH":
        line = f"    {arch}:"
        for p in ("workflow", "agent"):
            rows = [r for r in D[(arch, "clean")] if r["paradigm"] == p and not r.get("error")]
            solved = sum(1 for r in rows if ok(arch, r))
            tk = sum(r.get("total_tokens") or 0 for r in rows)
            line += f" {p[0].upper()}={tk/solved:.0f}" if solved else f" {p[0].upper()}=n/a"
        print(line)

    ff = mf = arts = 0
    for r in D[("E", "clean")] + D[("E", "rob")]:
        if r["paradigm"] == "workflow" and r.get("false_fails") is not None:
            ff += len(r["false_fails"]); mf += len(r["missed_fails"]); arts += 1
    print(f"  E criterion census ({arts} workflow artefacts): false_fails={ff}, missed_fails={mf}")

    cens = defaultdict(lambda: defaultdict(int))
    for r in D[("G", "clean")] + D[("G", "rob")]:
        for k, v in ((r.get("score_rationale") or {}).get("goal_breakdown") or {}).items():
            if v is False:
                cens[r["paradigm"]][k] += 1
    for p in ("workflow", "agent"):
        print(f"  G constraint fails {p}: {dict(cens[p])}")

    turns = defaultdict(lambda: [0, 0])
    for r in D[("H", "clean")]:
        if r["paradigm"] == "agent" and r.get("agent_turns"):
            t = min(r["agent_turns"], 4)
            turns[t][0] += bool(r.get("compliance_all_pass")); turns[t][1] += 1
    print("  H agent compliance by turns:", {k: f"{v[0]}/{v[1]}" for k, v in sorted(turns.items())})
    jd = sum(1 for r in D[("H", "clean")] if r.get("judge_disagreement"))
    print(f"  H judge-disagreement flags: {jd}/150")


if __name__ == "__main__":
    main()
