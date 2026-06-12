"""Ground-truth scoring for archetype G: simulator-based plan validation.

Both paradigms emit a ``Plan`` (ordered action steps with concrete args).
The workflow returns it as a Pydantic model via structured output; the
agent returns it as JSON after a ``FINAL_PLAN:`` marker, parsed by the
brace-depth extractor below and validated against the same Pydantic model,
so schema validation is identical across paradigms.

Scoring is mechanical (protocol A.2, PlanBench principle; deviation D-012):
``simulator.score_plan`` applies the steps against the seed state under the
live tools' preconditions and then evaluates the instance's declarative
goal spec. A plan is correct iff every step is applicable in order AND the
final state satisfies the goal, including side-effect discipline (exact
email/event sets, no off-target changes).
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from src.archetypes.g_strategic_planning.schemas import Plan
from src.archetypes.g_strategic_planning.simulator import score_plan

__all__ = ["extract_plan", "score_plan", "Plan"]


def extract_plan(text: str) -> Plan | None:
    """Extract and validate a Plan from agent free text.

    The agent system prompt instructs ``FINAL_PLAN: { ... }``. The
    extractor locates the marker, captures the JSON object via a
    brace-depth counter (string- and escape-aware), parses it, and
    validates it against the Plan schema. Returns ``None`` on any failure;
    the validation runner records this in the ``plan_parse_ok`` audit
    field so extraction failures are separable from planning failures.
    """
    if not text:
        return None
    m = re.search(r"FINAL_PLAN\s*:\s*", text, re.IGNORECASE)
    if m is None:
        return None
    start = text.find("{", m.end())
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    end = -1
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        return None
    try:
        data = json.loads(text[start:end])
    except json.JSONDecodeError:
        return None
    try:
        return Plan.model_validate(data)
    except ValidationError:
        return None
