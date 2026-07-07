"""Generate the thesis figures from the final-grid master CSV.

Produces, under ``docs/figures/`` (PNG for drafts, PDF for the thesis):

1. ``fig_<x>_<archetype>.pdf`` -- one combined per-archetype figure:
   two stacked panels (success rate; mean total tokens, log scale) x three
   model columns (nano, mini, gpt-5.2). Bars are workflow vs agent, paired
   per run (run2 drawn lighter). Half-page size, muted two-tone palette.
2. ``fig_overview_success.pdf`` -- the money figure: 2x4 grid, one panel per
   archetype, success rate across the capability tiers with the run range
   drawn as a vertical span.
3. ``fig_robustness.pdf`` -- robustness pass rate per archetype x model x
   paradigm (single pass per model).

Run:
    PYTHONPATH=. python experiments/make_figures.py
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
CSV = REPO / "data" / "results" / "final" / "master_results.csv"
OUT = REPO / "docs" / "figures"

MODELS = [
    ("gpt-5.4-nano-2026-03-17", "gpt-5.4-nano"),
    ("gpt-5.4-mini-2026-03-17", "gpt-5.4-mini"),
    ("gpt-5.2-2025-12-11", "gpt-5.2"),
]
ARCHETYPES = ["A", "B", "C", "D", "E", "F", "G", "H"]
ARCH_TITLES = {
    "A": "A — Exploratory Research", "B": "B — Structured Retrieval",
    "C": "C — Ambiguous Classification", "D": "D — Compliance Decisioning",
    "E": "E — Output Verification", "F": "F — Action Execution",
    "G": "G — Strategic Planning", "H": "H — Content Drafting",
}
ARCH_SHORT = {
    "A": "A — Research", "B": "B — Retrieval", "C": "C — Classification",
    "D": "D — Compliance", "E": "E — Verification", "F": "F — Actions",
    "G": "G — Planning", "H": "H — Drafting",
}

C_WF = "#39516b"   # muted slate blue  (workflow)
C_AG = "#a8763e"   # muted ochre       (agent)

plt.rcParams.update({
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.alpha": 0.25,
    "grid.linewidth": 0.5, "figure.dpi": 200, "savefig.bbox": "tight",
})


def load():
    rows = []
    with CSV.open() as fh:
        for r in csv.DictReader(fh):
            r["success"] = None if r["success"] == "" else (r["success"] == "True")
            r["total_tokens"] = float(r["total_tokens"]) if r["total_tokens"] else None
            rows.append(r)
    return rows


def cell_stats(rows, arch, model, run, paradigm, kind="clean"):
    sel = [r for r in rows if r["archetype"] == arch and r["model"] == model
           and r["run_label"] == run and r["paradigm"] == paradigm
           and r["kind"] == kind and r["success"] is not None]
    if not sel:
        return None
    n = len(sel)
    succ = 100.0 * sum(r["success"] for r in sel) / n
    toks = [r["total_tokens"] for r in sel if r["total_tokens"]]
    return {"n": n, "success": succ, "tokens": (sum(toks) / len(toks)) if toks else None}


def per_archetype_figure(rows, arch):
    fig, axes = plt.subplots(2, 3, figsize=(6.8, 4.0), sharey="row")
    runs_by_model = {m: (["run1", "run2"] if m != MODELS[2][0] else ["run1"]) for m, _ in MODELS}

    for col, (model, mlabel) in enumerate(MODELS):
        ax_s, ax_t = axes[0][col], axes[1][col]
        runs = runs_by_model[model]
        xticks, xlabels = [], []
        x = 0.0
        for run in runs:
            for paradigm, color in (("workflow", C_WF), ("agent", C_AG)):
                st = cell_stats(rows, arch, model, run, paradigm)
                if st is None:
                    x += 1
                    continue
                alpha = 1.0 if run == "run1" else 0.55
                ax_s.bar(x, st["success"], width=0.8, color=color, alpha=alpha,
                         edgecolor="white", linewidth=0.4)
                ax_s.text(x, st["success"] + 2, f"{st['success']:.0f}",
                          ha="center", va="bottom", fontsize=7, color="#333333")
                if st["tokens"]:
                    ax_t.bar(x, st["tokens"], width=0.8, color=color, alpha=alpha,
                             edgecolor="white", linewidth=0.4)
                    val = st["tokens"]
                    lab = f"{val/1000:.1f}k" if val >= 1000 else f"{val:.0f}"
                    ax_t.text(x, val * 1.08, lab, ha="center", va="bottom",
                              fontsize=6.5, color="#333333")
                x += 1
            xticks.append(x - 1.5)
            xlabels.append(run)
            x += 0.6
        ax_s.set_title(mlabel)
        ax_s.set_ylim(0, 112)
        ax_s.set_xticks(xticks)
        ax_s.set_xticklabels(xlabels)
        ax_t.set_yscale("log")
        ax_t.set_xticks(xticks)
        ax_t.set_xticklabels(xlabels)
        if col == 0:
            ax_s.set_ylabel("Success rate (%)")
            ax_t.set_ylabel("Mean tokens (log)")

    handles = [plt.Rectangle((0, 0), 1, 1, color=C_WF),
               plt.Rectangle((0, 0), 1, 1, color=C_AG)]
    fig.legend(handles, ["Workflow", "Agent"], ncol=2, loc="lower center",
               frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(f"Archetype {ARCH_TITLES[arch]} — success and token cost across the capability grid",
                 fontsize=9.5, y=1.0)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"fig_{arch.lower()}_{ARCH_TITLES[arch].split(' — ')[1].lower().replace(' ', '_')}.{ext}")
    plt.close(fig)


def overview_figure(rows):
    fig, axes = plt.subplots(2, 4, figsize=(7.0, 4.4), sharey=True)
    xs = [0, 1, 2]
    for i, arch in enumerate(ARCHETYPES):
        ax = axes[i // 4][i % 4]
        for paradigm, color, marker in (("workflow", C_WF, "o"), ("agent", C_AG, "s")):
            means, los, his = [], [], []
            for model, _ in MODELS:
                runs = ["run1", "run2"] if model != MODELS[2][0] else ["run1"]
                vals = [cell_stats(rows, arch, model, r, paradigm)["success"]
                        for r in runs if cell_stats(rows, arch, model, r, paradigm)]
                means.append(sum(vals) / len(vals))
                los.append(min(vals)); his.append(max(vals))
            ax.plot(xs, means, marker=marker, markersize=4, linewidth=1.3, color=color)
            for x, lo, hi in zip(xs, los, his):
                if hi > lo:
                    ax.vlines(x, lo, hi, color=color, linewidth=3, alpha=0.3)
        ax.set_title(ARCH_SHORT[arch], fontsize=8.5)
        ax.set_ylim(0, 105)
        ax.set_xticks(xs)
        ax.set_xticklabels(["nano", "mini", "5.2"])
        if i % 4 == 0:
            ax.set_ylabel("Success rate (%)")
    handles = [plt.Line2D([0], [0], color=C_WF, marker="o", markersize=4, linewidth=1.3),
               plt.Line2D([0], [0], color=C_AG, marker="s", markersize=4, linewidth=1.3)]
    fig.legend(handles, ["Workflow", "Agent"], ncol=2, loc="lower center",
               frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Success rate across the capability grid (mean of runs; band = run range)",
                 fontsize=9.5, y=1.0)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"fig_overview_success.{ext}")
    plt.close(fig)


def difficulty_figure(rows, arch):
    """Combined per-archetype chart: difficulty on X, success (left axis,
    solid) and mean tokens (right axis, log, dashed) for both paradigms,
    pooled over all clean grid cells (5 sweeps x 5 instances per tier)."""
    tiers = ["low", "med", "high"]
    fig, ax_s = plt.subplots(figsize=(6.2, 3.8))
    ax_t = ax_s.twinx()
    ax_t.grid(False)
    xs = [0, 1, 2]

    for paradigm, color, marker in (("workflow", C_WF, "o"), ("agent", C_AG, "s")):
        succ, toks = [], []
        for tier in tiers:
            sel = [r for r in rows if r["archetype"] == arch and r["kind"] == "clean"
                   and r["paradigm"] == paradigm and r["difficulty"] == tier
                   and r["success"] is not None]
            succ.append(100.0 * sum(r["success"] for r in sel) / len(sel))
            tv = [r["total_tokens"] for r in sel if r["total_tokens"]]
            toks.append(sum(tv) / len(tv))
        ax_s.plot(xs, succ, color=color, marker=marker, markersize=5,
                  linewidth=1.6, label=f"{paradigm.capitalize()} — success")
        for x, v in zip(xs, succ):
            ax_s.annotate(f"{v:.0f}", (x, v), textcoords="offset points",
                          xytext=(0, 6), ha="center", fontsize=7.5, color=color)
        ax_t.plot(xs, toks, color=color, marker=marker, markersize=4,
                  linewidth=1.2, linestyle="--", alpha=0.65,
                  label=f"{paradigm.capitalize()} — tokens")

    ax_s.set_ylim(0, 112)
    ax_s.set_ylabel("Success rate (%)")
    ax_t.set_yscale("log")
    ax_t.set_ylabel("Mean tokens per task (log)")
    ax_s.set_xticks(xs)
    ax_s.set_xticklabels(["Low", "Medium", "High"])
    ax_s.set_xlabel("Task difficulty")
    ax_s.set_xlim(-0.25, 2.25)
    h1, l1 = ax_s.get_legend_handles_labels()
    h2, l2 = ax_t.get_legend_handles_labels()
    ax_s.legend(h1 + h2, l1 + l2, ncol=2, frameon=False, loc="lower left",
                bbox_to_anchor=(0, -0.38), fontsize=8)
    ax_s.set_title(f"Archetype {ARCH_TITLES[arch]} — success and token cost by difficulty "
                   f"(pooled over all grid runs)", fontsize=9.5)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"fig_diff_{arch.lower()}.{ext}")
    plt.close(fig)


def overview_tokens_figure(rows):
    fig, axes = plt.subplots(2, 4, figsize=(7.0, 4.4))
    xs = [0, 1, 2]
    for i, arch in enumerate(ARCHETYPES):
        ax = axes[i // 4][i % 4]
        for paradigm, color, marker in (("workflow", C_WF, "o"), ("agent", C_AG, "s")):
            means, los, his = [], [], []
            for model, _ in MODELS:
                runs = ["run1", "run2"] if model != MODELS[2][0] else ["run1"]
                vals = [cell_stats(rows, arch, model, r, paradigm)["tokens"]
                        for r in runs if cell_stats(rows, arch, model, r, paradigm)]
                vals = [v for v in vals if v]
                means.append(sum(vals) / len(vals))
                los.append(min(vals)); his.append(max(vals))
            ax.plot(xs, means, marker=marker, markersize=4, linewidth=1.3, color=color)
            for x, lo, hi in zip(xs, los, his):
                if hi > lo:
                    ax.vlines(x, lo, hi, color=color, linewidth=3, alpha=0.3)
        ax.set_yscale("log")
        ax.set_title(ARCH_SHORT[arch], fontsize=8.5)
        ax.set_xticks(xs)
        ax.set_xticklabels(["nano", "mini", "5.2"])
        ax.set_xlim(-0.4, 2.4)
        if i % 4 == 0:
            ax.set_ylabel("Mean tokens (log)")
    handles = [plt.Line2D([0], [0], color=C_WF, marker="o", markersize=4, linewidth=1.3),
               plt.Line2D([0], [0], color=C_AG, marker="s", markersize=4, linewidth=1.3)]
    fig.legend(handles, ["Workflow", "Agent"], ncol=2, loc="lower center",
               frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Token cost per task across the capability grid (mean of runs; band = run range)",
                 fontsize=9.5, y=1.0)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"fig_overview_tokens.{ext}")
    plt.close(fig)


def robustness_figure(rows):
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.6), sharey=True)
    width = 0.38
    for col, (model, mlabel) in enumerate(MODELS):
        ax = axes[col]
        for j, (paradigm, color) in enumerate((("workflow", C_WF), ("agent", C_AG))):
            vals = []
            for arch in ARCHETYPES:
                st = cell_stats(rows, arch, model, "robustness", paradigm, kind="robustness")
                vals.append(st["success"] if st else 0)
            pos = [k + (j - 0.5) * width for k in range(len(ARCHETYPES))]
            ax.bar(pos, vals, width=width, color=color, edgecolor="white", linewidth=0.4)
        ax.set_title(mlabel)
        ax.set_xticks(range(len(ARCHETYPES)))
        ax.set_xticklabels(ARCHETYPES)
        ax.set_ylim(0, 105)
        if col == 0:
            ax.set_ylabel("Robustness pass (%)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=C_WF),
               plt.Rectangle((0, 0), 1, 1, color=C_AG)]
    fig.legend(handles, ["Workflow", "Agent"], ncol=2, loc="lower center",
               frameon=False, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("Robustness checks (perturbed inputs, both-solved anchors)", fontsize=9.5, y=1.04)
    fig.tight_layout(rect=(0, 0.02, 1, 0.98))
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"fig_robustness.{ext}")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load()
    for arch in ARCHETYPES:
        per_archetype_figure(rows, arch)
        difficulty_figure(rows, arch)
    overview_figure(rows)
    overview_tokens_figure(rows)
    robustness_figure(rows)
    print(f"Figures written to {OUT.relative_to(REPO)} ({len(list(OUT.glob('*.pdf')))} PDFs)")


if __name__ == "__main__":
    main()
