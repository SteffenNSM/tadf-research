"""Ground-truth evaluation for archetype B (outcome-centric, TCR).

Compares a predicted answer to the instance ground truth and returns a binary
Task Completion Rate score. The comparison is robust to prose around the
final value, because the agent paradigm sometimes embeds the answer in a short
sentence even when prompted for a bare value.

Rules:
- If the expected value is numeric, scan the predicted string for numbers and
  use the last one (LLMs typically place the final answer at the end of their
  response). Compare it to the expected value after rounding both sides to the
  decimal precision implied by the expected value.
- If the expected value is a non-numeric entity name (region, team, category,
  month label), first try an exact case-insensitive match. Failing that, treat
  the comparison as a whole-word membership check, so answers like
  "The region is EMEA." still match the expected value "EMEA".
"""

from __future__ import annotations

import re
from typing import Any

#: Matches integers and decimals, optionally signed, optionally with thousands
#: separators. Currency and percent symbols are stripped before matching.
_NUMBER_RE = re.compile(r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?")


def _to_number(value: Any) -> float | None:
    """Parse a value as a float, stripping currency symbols and thousands separators."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if value is None:
        return None
    text = re.sub(r"[€$%\s]", "", str(value))
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def _find_numbers(text: str) -> list[float]:
    """Return all numeric tokens found in the text, in left-to-right order."""
    return [float(m.replace(",", "")) for m in _NUMBER_RE.findall(text)]


def _decimals(expected: Any) -> int:
    """Decimal places in the expected value's string form (0 for integers)."""
    text = str(expected)
    return len(text.split(".")[1]) if "." in text else 0


def is_correct(predicted: Any, expected: Any) -> bool:
    """Return True if the predicted answer matches the expected ground truth."""
    pe = _to_number(expected)
    if pe is not None:
        nums = _find_numbers(str(predicted))
        if not nums:
            return False
        # The last number in the response is taken as the final answer.
        pp = nums[-1]
        dec = _decimals(expected)
        return round(pp, dec) == round(pe, dec)

    expected_str = str(expected).strip().lower()
    predicted_str = str(predicted).strip().lower()
    if predicted_str == expected_str:
        return True
    return bool(re.search(rf"\b{re.escape(expected_str)}\b", predicted_str))


def score(predicted: Any, ground_truth: dict) -> float:
    """Return the TCR score (1.0 correct, 0.0 incorrect) for one instance."""
    return 1.0 if is_correct(predicted, ground_truth["value"]) else 0.0
