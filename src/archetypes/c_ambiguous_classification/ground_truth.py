"""Ground-truth scoring for archetype C: deterministic label matching.

Both paradigms emit a category label. The workflow returns the
``ClassificationResult`` schema with the label already constrained to the
Literal enum; the agent returns free text that should end with a
``FINAL_ANSWER:`` line. The extractor below normalizes both into a single
Literal value and the scorer compares it to the curated gold for the
instance.

The extractor is robust to two common LLM output deviations: the label may
be wrapped in markdown emphasis (``**Technical**``) or punctuated with a
trailing period. It is intentionally NOT robust to invented labels: if the
LLM emits something outside the five-label enum, the extractor returns
``None`` and the run is marked incorrect, which is the desired behaviour for
a strict classification metric.

Known limitation of the last-mention fallback (audited per run via the
``final_answer_line_present`` field in the validation record): when the
agent omits the ``FINAL_ANSWER:`` line AND discusses several labels in its
prose (e.g. "this is Billing, not an Account change"), the fallback can pick
the wrong label. Runs scored through the fallback path are therefore flagged
in the results so extraction-induced errors can be separated from genuine
classification errors in the analysis.
"""

from __future__ import annotations

import re

#: Valid labels, mirroring the EMAIL_CATEGORY Literal in schemas.py and the
#: ``cases.issue_category`` column in the seed CRM (see seed_crm.py).
VALID_LABELS = ["Billing", "Technical", "Shipping", "Account", "Product"]


def extract_label(text: str) -> str | None:
    """Extract a category label from a free-text response.

    Strategy:
        1. Look for an explicit ``FINAL_ANSWER: <label>`` line first (the
           agent's system prompt instructs this format).
        2. Otherwise scan the response for valid labels and return the LAST
           one mentioned in the text. The convention (verified for archetype
           B in IT-005) is that LLMs state the final answer at the end of
           the response; an earlier mention of the incorrect label being
           rejected should not be misread as the answer.

    Tie-break inside the fallback: when two valid labels match at the same
    text position, the longer one wins. (No label in the current five-value
    enum is a prefix of another, so this guard is currently dormant; it is
    kept so the extractor stays correct if the label set ever changes.)

    Returns the normalized label string, or ``None`` if no valid label is
    found.
    """
    if not text:
        return None
    m = re.search(
        r"FINAL_ANSWER\s*:\s*\**\s*([A-Za-z][A-Za-z ]+?)\s*\**\s*(?:[\.\n]|$)",
        text,
        re.IGNORECASE,
    )
    if m:
        candidate = m.group(1).strip()
        for label in VALID_LABELS:
            if label.lower() == candidate.lower():
                return label
    # Fallback: collect all (position, label) hits and return the latest
    # occurrence; on equal positions prefer the longer label.
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
