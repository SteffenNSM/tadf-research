"""Ground-truth scoring for archetype D: deterministic label matching.

Both paradigms emit a decision label. The workflow returns the
DecisionResult schema with the label already constrained to the Literal
enum; the agent returns free text that should end with a
``FINAL_ANSWER:`` line. The extractor below normalises both into a single
Literal value and the scorer compares it to the curated gold for the
instance.

D's labels are uppercase identifiers with underscores
(``ESCALATE_DIRECTOR``, ``ESCALATE_REGIONAL_VP``). The fallback path
matches whole-token instances of the label; ``re.IGNORECASE`` is on so a
lowercase ``decline`` in agent prose is also resolvable.
"""

from __future__ import annotations

import re

#: Valid decision labels, mirroring the DECISION Literal in schemas.py.
#: Order is significant for the fallback path: longest first so that
#: ``ESCALATE_REGIONAL_VP`` wins over the substring ``ESCALATE_VP``.
VALID_LABELS = [
    "ESCALATE_REGIONAL_VP",
    "ESCALATE_DIRECTOR",
    "ESCALATE_VP",
    "APPROVE",
    "DECLINE",
]


def extract_label(text: str) -> str | None:
    """Extract a decision label from a free-text response.

    Strategy:
        1. Look for an explicit ``FINAL_ANSWER: <label>`` line (agent
           system prompt instructs this format).
        2. Otherwise scan the response for a valid label and return the
           LAST occurrence — the convention (IT-005) is that LLMs state the
           final answer at the end of the response.

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
