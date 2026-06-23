"""No-tool memorization check for archetype A instances.

For each A instance, asks the backbone model the question with NO tools and NO
web access, then scores the answer with the same frozen-prompt judge used in
the sweep. An instance is flagged 'memorized' if the model answers it correctly
without any retrieval (at temperature 0 or in any stochastic sample) -- such an
instance does not exercise archetype A's research construct and should be
hardened or replaced.

Run:
    PYTHONPATH=. python experiments/check_memorization_a.py            # temp 0 + 2 samples
    PYTHONPATH=. python experiments/check_memorization_a.py --samples 0  # temp 0 only
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from src.core.llm import get_llm
from src.archetypes.a_exploratory_research.ground_truth import score

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "a_exploratory_research"

PROMPT = """Answer the following question from your own internal knowledge only.
You have NO web access and NO tools. If you are not certain of the exact answer, reply exactly: I don't know.

Question: {q}

Answer with the value only."""


def load() -> list[dict]:
    picks = [f"{l}/a-{l}-{n}" for l in ("low", "med", "high") for n in range(1, 6)]
    return [json.loads((IN / f"{p}.json").read_text()) for p in picks]


def main() -> None:
    samples = 2
    if "--samples" in sys.argv:
        samples = int(sys.argv[sys.argv.index("--samples") + 1])
    rows = []
    print(f"{'instance':10} {'memorized':10} {'verdicts':16} gold | no-tool answer")
    print("-" * 100)
    for inst in load():
        gt = inst["ground_truth"]; q = inst["instruction"]
        verdicts = []; first = ""
        for i, temp in enumerate([0.0] + [0.7] * samples):
            ans = get_llm(temperature=temp).invoke(PROMPT.format(q=q)).content
            if i == 0:
                first = ans
            s, _ = score(ans, gt, q)
            verdicts.append(int(s >= 1.0))
        memo = any(verdicts)
        rows.append({"instance": inst["id"], "memorized": memo, "verdicts": verdicts,
                     "gold": gt["value"], "no_tool_answer": str(first)[:200]})
        print(f"{inst['id']:10} {str(memo):10} {str(verdicts):16} {gt['value']!r} | {str(first)[:55]!r}")
    out = REPO / "data" / "results" / "a_memorization_check.json"
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=str))
    n = sum(r["memorized"] for r in rows)
    print(f"\nMemorized (correct without tools): {n}/15  -> these do NOT exercise the research construct; harden/replace.")
    print(f"Written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
