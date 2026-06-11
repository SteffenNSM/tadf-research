"""Configuration for archetype E: Output Verification and Quality Control.

Single source of truth for archetype E: its dimensional profile, source
benchmarks, tool whitelist, output schema, and the prompt templates for
both paradigms.

E is the canonical LLM-as-Judge archetype. The judge receives a customer
inquiry, a candidate support response, and a five-criterion rubric, and
renders one ternary verdict (PASS / NEEDS_REVISION / FAIL). The dimensional
profile (high Step Predictability, high Information Availability, low
Output Ambiguity, moderate Error Consequence) places E firmly in the
workflow-leaning region of Table 3; the canonical-minimal form is a single
LLM call with structured output, parallel to archetypes C and D.

The empirical question for E is whether the workflow's structured-output
verdict is more reliable than the agent's free-text verdict at the same
single-call cost. C showed a token efficiency advantage but no correctness
gap (Ceiling). D showed a 13-percentage-point correctness gap (the
schema-rationale-forces-visible-reasoning effect). E tests whether the
LLM-as-Judge setup shows the C pattern (efficient but tied) or the D
pattern (workflow strictly more reliable).

Sources: WONDERBREAD SOP Ranking and Demo Validation (Wornow et al.,
2024); Kourani et al. (2025) self-improvement; TheAgentCompany feedback
subtasks (Xu et al., 2024). The rubric is original work that captures the
structural pattern of the judge-prompts used in those sources; the
customer inquiries and candidate responses are author-constructed and
inline in the instance JSON.
"""

from src.archetypes.e_output_verification.schemas import (
    QUALITY_VERDICT,
    QualityVerdict,
)
from src.core.llm import DEFAULT_TEMPERATURE
from src.core.tools.database import db_read, db_search

# ── TADF metadata ──

DIMENSIONAL_PROFILE = {
    "step_predictability": "high",
    "information_availability": "high",
    "output_ambiguity": "low",
    "error_consequence": "moderate",
}

SOURCE_BENCHMARK = (
    "WONDERBREAD SOP Ranking and Demo Validation (Wornow et al., 2024); "
    "Kourani et al. (2025) self-improvement; "
    "TheAgentCompany feedback subtasks (Xu et al., 2024)"
)

#: D-style temperature note: E runs at DEFAULT_TEMPERATURE (0.2) so the
#: C/D/E ternary classification triad uses consistent decoding settings,
#: which keeps the within-archetype Token-Cost / correctness comparison
#: free of a temperature confound.
TEMPERATURE = DEFAULT_TEMPERATURE

#: Tool whitelist exposed to both paradigms (Phase-2 tool-symmetry
#: invariant A.3). The canonical-minimal workflow never invokes a tool;
#: the agent may. The E instances are constructed so the inquiry and the
#: candidate response alone carry every signal the rubric requires.
TOOLS = [db_read, db_search]

#: The full evaluation rubric, expressed as a list of criteria with
#: explicit pass/fail conditions and the verdict-decision rule. Exposed
#: verbatim to both paradigms. The rubric is intentionally definitional
#: (what each criterion requires) rather than rule-chained, so the test
#: stays separable from archetype D's codified IF-THEN rule application.
EVALUATION_RUBRIC = """Customer support response evaluation rubric. A candidate response is judged against five criteria. Each criterion is a pass/fail check. The verdict is derived by counting failures.

CRITERIA — each evaluated independently against the candidate response.
C1. Issue acknowledgment. The response addresses the specific issue, question, or request raised in the customer's inquiry. Generic openings ("Thanks for reaching out") do not satisfy this on their own; the response must reference what the customer actually asked about. FAIL if the response does not address the specific issue.
C2. Actionable next steps. The response provides either a concrete next step, a specific resolution, or a clear ETA (an actual date or a numeric time window). Vague placeholders such as "soon", "shortly", or "we'll get back to you" without specifics do not satisfy this. FAIL if no actionable element is present.
C3. Scope discipline. The response does not promise features, fixes, refunds, or actions that the customer did not ask for and that the support function would not normally commit to in a first reply (for example, promising a product change, a future feature, a financial credit not yet authorized, or a process exception). FAIL if such a commitment is made.
C4. Tone. The response is professional and respectful. FAIL on condescension ("you should have read the docs"), blame-shifting ("that's a user error"), or any dismissive language.
C5. Reference accuracy. Where the customer's inquiry references a case ID, order ID, account, or specific contact, the response identifies the same item correctly. FAIL if the response cites a different case/order/customer than the inquiry, or invents an identifier that does not appear in the inquiry.

VERDICT — derived from the failure count.
- PASS: zero criteria fail.
- NEEDS_REVISION: one or two criteria fail.
- FAIL: three or more criteria fail.

Valid verdict labels are exactly: PASS | NEEDS_REVISION | FAIL."""


# ── Prompts ──

CLASSIFY_PROMPT = """You are a senior support quality reviewer. You receive a customer inquiry and a candidate response drafted by a support agent, and you must apply the evaluation rubric below to return one verdict.

{rubric}

Customer inquiry:
{inquiry}

Candidate response (drafted by an agent):
{candidate_response}

Task: {instruction}

Output your verdict as a QualityVerdict: pick the `label` derived from the rubric and give a one-sentence `rationale` naming the criteria that failed (or confirming that all criteria are met). Evaluate the candidate as written; do not assume facts the response itself does not state."""


AGENT_SYSTEM_PROMPT = """You are a senior support quality reviewer. You receive a customer inquiry and a candidate response drafted by a support agent, and you must apply the evaluation rubric below to return one verdict.

{rubric}

The customer inquiry and the candidate response are provided in the user message. The rubric can be applied from those two artefacts alone; the read tools (db_read, db_search) are available if you decide a CRM lookup is useful, but the verdict is about the candidate response as written and rarely requires additional context.

Evaluate the candidate as written; do not assume facts the response itself does not state. End your response with a single line in the exact format:
FINAL_ANSWER: <one of: PASS | NEEDS_REVISION | FAIL>"""
