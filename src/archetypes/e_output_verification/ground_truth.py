"""Ground-truth scoring for archetype E: deterministic label matching.

Both paradigms emit a verdict label. The workflow returns the
QualityVerdict schema with the label already constrained to the Literal
enum; the agent returns free text that should end with a
``FINAL_ANSWER:`` line. The extractor below normalises both into a single
Literal value and the scorer compares it to the curated gold for the
instance.

E's labels are short uppercase identifiers with one underscore
(``NEEDS_REVISION``). The fallback path matches whole-token instances of
the label; ``re.IGNORECASE`` is on so a lowercase ``needs_revision`` in
agent prose is also resolvable.
"""

from __future__ import annotations

import re

#: Valid verdict labels, mirroring the QUALITY_VERDICT Literal in
#: schemas.py. Order is significant for the fallback path: the longer
#: ``NEEDS_REVISION`` is matched before the substring ``REVISION`` could
#: trip a partial match (it can't here, but the convention is preserved).
VALID_LABELS = ["NEEDS_REVISION", "PASS", "FAIL"]


def extract_label(text: str) -> str | None:
    """Extract a verdict label from a free-text response.

    Strategy:
        1. Look for an explicit ``FINAL_ANSWER: <label>`` line first
           (the agent system prompt instructs this format).
        2. Otherwise scan the response for a valid label and return the
           LAST occurrence — the convention (IT-005) is that LLMs state
           the final answer at the end of the response.

    Returns the normalised label string, or ``None`` if no valid label is
    found.
    """
    if not text:
        return None
    m = re.search(
        r"FINAL_ANSWER\s*:\s*\**\s*([A-Za-z_]+)\s*\**\s*(?:[\.\n]|$)",
        text,
        re.IGNORECASE,
    )
    if m:
        candidate = m.group(1).strip()
        for label in VALID_LABELS:
            if label.lower() == candidate.lower():
                return label
    # Fallback: collect all hits ordered by position; return the latest.
    hits: list[tuple[int, str]] = []
    for label in VALID_LABELS:
        for match in re.finditer(r"\b" + re.escape(label) + r"\b", text, re.IGNORECASE):
            hits.append((match.start(), label))
    if not hits:
        return None
    hits.sort(key=lambda h: (h[0], -len(h[1])))
    return hits[-1][1]


def score(predicted_label: str | None, expected_label: str) -> tuple[float, str]:
    """Return (score, rationale). 1.0 on exact label match else 0.0."""
    if predicted_label is None:
        return 0.0, "no label extracted from response"
    if predicted_label == expected_label:
        return 1.0, "match"
    return 0.0, f"predicted {predicted_label!r}, expected {expected_label!r}"


# ── Per-criterion scoring (workflow path only) ──

#: The rubric's criterion ids, mirroring verdict_engine.CRITERIA.
CRITERIA = ["C1", "C2", "C3", "C4", "C5"]


def score_criteria(
    predicted_failed: list[str], gold_failed: list[str]
) -> tuple[float, list[str], list[str]]:
    """Score the workflow's per-criterion judgments against the gold.

    Compares the predicted failed-criteria set with the instance's
    ``criterion_failures`` gold. Returns ``(criterion_accuracy,
    false_fails, missed_fails)`` where criterion_accuracy is the fraction
    of the five criteria judged correctly, false_fails are criteria the
    workflow failed but the gold passes, and missed_fails are gold
    failures the workflow judged as passing.

    This attribution exists only for the workflow path by design: the
    agent's holistic free text carries no reliable per-criterion structure,
    and that asymmetry is itself an auditability observable of the
    paradigm comparison (see the iteration log).
    """
    pred, gold = set(predicted_failed), set(gold_failed)
    correct = sum(1 for c in CRITERIA if (c in pred) == (c in gold))
    false_fails = sorted(pred - gold, key=CRITERIA.index)
    missed_fails = sorted(gold - pred, key=CRITERIA.index)
    return correct / len(CRITERIA), false_fails, missed_fails
