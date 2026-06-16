"""Deterministic compliance scoring for archetype H (the objective anchor).

This layer scores the mechanically checkable constraints on a drafting
artefact, independent of and alongside the LLM-judge OQS (``judge.py``).
Together they implement H's dual evaluation: the judge grades soft quality
(tonality, audience fit, coherence), this layer verifies the hard,
reproducible requirements:

- required_points : each mandated data point appears (keyword/value match)
- length          : word count within the [min_words, max_words] window
- sections        : each required section header appears (multi-section tier)
- no_placeholder  : no "[TODO]"-style placeholders remain
- faithfulness    : every significant number in the artefact is supported by
                    the table (or its documented derived values) within a
                    rounding tolerance — the hallucination check
- feedback        : each feedback round's required change is reflected

``compliance_rate`` is the fraction of atomic checks passed; ``all_pass`` is
their conjunction. Both are fully deterministic and reproducible, and serve
as the objective floor against which the judge's OQS is read (and as the
cross-check for the judge-disagreement audit in validate_h.py).
"""

from __future__ import annotations

import re

#: Numbers at or below this magnitude, when written as bare integers without
#: a currency/percent/decimal marker, are treated as structural (counts,
#: quarter numbers, list positions) rather than data claims, and are exempt
#: from the faithfulness check.
_TRIVIAL_INT_MAX = 12

#: Relative + absolute tolerance for matching a number to an allowed value,
#: so legitimate rounding of derived figures (e.g. a YoY % of 11.8 vs 12) is
#: not flagged while fabricated figures are.
_REL_TOL = 0.01
_ABS_TOL = 0.5

_PLACEHOLDER_RE = re.compile(r"\[(?:todo|tbd|insert[^\]]*|placeholder|xxx)\]|x{3,}", re.IGNORECASE)
_NUM_RE = re.compile(r"[-+]?\$?€?£?\d[\d,]*(?:\.\d+)?\s*%?")


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text or ""))


def _normalize_number(token: str) -> tuple[float, bool] | None:
    """Parse a numeric token -> (value, is_significant) or None.

    is_significant is False for bare small integers (<= _TRIVIAL_INT_MAX with
    no %, currency, or decimal marker), which are exempt from faithfulness.
    """
    raw = token.strip()
    if not raw:
        return None
    has_pct = "%" in raw
    has_cur = any(s in raw for s in ("$", "€", "£"))
    cleaned = raw.replace("$", "").replace("€", "").replace("£", "").replace("%", "").replace(",", "").strip()
    has_dec = "." in cleaned
    try:
        value = float(cleaned)
    except ValueError:
        return None
    significant = has_pct or has_cur or has_dec or abs(value) > _TRIVIAL_INT_MAX
    return value, significant


def extract_numbers(text: str) -> list[tuple[float, bool]]:
    out: list[tuple[float, bool]] = []
    for m in _NUM_RE.findall(text or ""):
        parsed = _normalize_number(m)
        if parsed is not None:
            out.append(parsed)
    return out


def _matches_allowed(value: float, allowed: list[float]) -> bool:
    for a in allowed:
        if abs(value - a) <= max(_ABS_TOL, _REL_TOL * abs(a)):
            return True
    return False


def _contains_any(text: str, keywords: list[str]) -> bool:
    low = (text or "").lower()
    return any(k.lower() in low for k in keywords)


def check_compliance(inst: dict, title: str, body: str) -> tuple[bool, float, dict]:
    """Return (all_pass, compliance_rate, breakdown) for one artefact."""
    c = inst["constraints"]
    full = f"{title}\n{body}"
    checks: list[bool] = []
    breakdown: dict = {}

    # required data points
    missing_points = [p["desc"] for p in c.get("required_points", [])
                      if not _contains_any(full, p["keywords"])]
    breakdown["missing_points"] = missing_points
    checks.append(not missing_points)

    # length window
    wc = count_words(body)
    length_ok = c["min_words"] <= wc <= c["max_words"]
    breakdown["word_count"] = wc
    breakdown["length_ok"] = length_ok
    checks.append(length_ok)

    # required sections (multi-section tier)
    missing_sections = [s for s in c.get("required_sections", [])
                        if s.lower() not in full.lower()]
    breakdown["missing_sections"] = missing_sections
    if c.get("required_sections"):
        checks.append(not missing_sections)

    # no placeholders
    no_placeholder = _PLACEHOLDER_RE.search(full) is None
    breakdown["no_placeholder"] = no_placeholder
    checks.append(no_placeholder)

    # faithfulness: every significant number supported by the table/derived set
    allowed = list(inst.get("allowed_numbers", []))
    unsupported = [v for v, sig in extract_numbers(body) if sig and not _matches_allowed(v, allowed)]
    breakdown["unsupported_numbers"] = unsupported
    checks.append(not unsupported)

    # feedback incorporation (one atomic check per requirement)
    fb_missing = [req["desc"] for req in inst.get("feedback_requirements", [])
                  if not _contains_any(full, req["keywords"])]
    breakdown["missing_feedback"] = fb_missing
    for req in inst.get("feedback_requirements", []):
        checks.append(_contains_any(full, req["keywords"]))

    all_pass = all(checks)
    compliance_rate = sum(checks) / len(checks) if checks else 1.0
    breakdown["n_checks"] = len(checks)
    breakdown["n_passed"] = sum(checks)
    return all_pass, compliance_rate, breakdown
