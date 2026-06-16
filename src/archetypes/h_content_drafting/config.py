"""Configuration for archetype H: Content and Document Drafting and Refinement.

Single source of truth for archetype H: its dimensional profile, source
benchmarks, tool whitelist, output schema, and the prompt templates for
both paradigms plus the frozen judge template.

H is the canonical high-Output-Ambiguity archetype and the second archetype
(after G) whose Table-3 a-priori routing is agent-or-hybrid rather than
workflow. Its difficulty axis is operationalized as CONSTRAINT LOAD plus
feedback rounds (deviation D-014): the number of simultaneous writing
constraints (format, length window, tonality, audience, framing, required
data points) rises across tiers, and the High tier adds a tension revision
(e.g. "shorten it but add the regional breakdown") that forces genuine
re-prioritization. This ties H's difficulty to the same constraint-dropping
mechanism observed in F (enumeration), D (bonus accumulation), and G
(argument completeness), and tests whether the agent's runtime self-revision
catches dropped constraints the fixed workflow pipeline does not.

Tool whitelist: EMPTY for both paradigms. H is pure text generation with
high Information Availability (the data table is inline); CRM tools are
irrelevant, and protocol Section 5 forbids exposing irrelevant tools to the
agent. Symmetry is preserved by giving both paradigms the same empty tool
set. The agent's "loop" is runtime-controlled self-revision and termination
(RevisionDecision), not tool use.

Source: WONDERBREAD SOP Generation / SOP Improvement (Wornow et al., 2024);
TheAgentCompany report drafting (Xu et al., 2024). Author-constructed
briefs, tables, and constraints (IT-017 rule).
"""

from src.core.llm import DEFAULT_TEMPERATURE

# ── TADF metadata ──

DIMENSIONAL_PROFILE = {
    "step_predictability": "moderate_low",
    "information_availability": "high",
    "output_ambiguity": "high",
    "error_consequence": "low_moderate",
}

SOURCE_BENCHMARK = (
    "WONDERBREAD SOP Generation / SOP Improvement (Wornow et al., 2024); "
    "TheAgentCompany report drafting (Xu et al., 2024)"
)

#: H runs at DEFAULT_TEMPERATURE (0.2), consistent with every archetype
#: except G. Drafting benefits from limited stochasticity and the variance
#: estimate; the judge runs separately at temperature 0 (see judge.py).
TEMPERATURE = DEFAULT_TEMPERATURE

#: Per-difficulty maximum agent self-revision turns (protocol A.6 step-limit
#: principle, applied to H's tool-free loop). One turn = one draft/critique
#: LLM call. Exceeding the limit is recorded as iteration_overflow.
MAX_AGENT_STEPS = {"low": 4, "med": 8, "high": 14}

#: Tool whitelist: intentionally empty for both paradigms (see module docstring).
TOOLS: list = []

#: Shared writing-brief preamble exposed verbatim to both paradigms.
BRIEF_PREAMBLE = """You are a business communications writer. You will be given a small data table and a set of writing constraints, and you must produce one text artefact (a post, an email, or a report) that uses the data and satisfies every constraint.

Hard rules that always apply:
- Use ONLY figures that appear in or follow arithmetically from the provided table. Do not invent numbers, names, dates, or facts that are not supported by the table.
- Every required data point listed in the constraints must appear in the artefact.
- Stay within the specified word window.
- Honour the specified format, tonality, audience, and framing.
- Do not leave placeholders (no "[TODO]", "[insert X]", "XXX")."""


def render_constraints(inst: dict) -> str:
    """Render an instance's constraint block as the shared brief text."""
    c = inst["constraints"]
    lines = [
        f"Format: {inst['format']}",
        f"Audience: {c['audience']}",
        f"Tonality: {c['tonality']}",
        f"Length window: {c['min_words']}–{c['max_words']} words",
    ]
    if c.get("framing"):
        lines.append(f"Framing/emphasis: {c['framing']}")
    if c.get("required_sections"):
        lines.append("Required sections (use these as headers): " + "; ".join(c["required_sections"]))
    if c.get("required_points"):
        lines.append("Required data points to include: " + "; ".join(p["desc"] for p in c["required_points"]))
    return "\n".join(lines)


def render_table(table: dict) -> str:
    """Render the inline data table as a compact text block."""
    cols = table["columns"]
    rows = table["rows"]
    header = " | ".join(cols)
    sep = " | ".join("---" for _ in cols)
    body = "\n".join(" | ".join(str(v) for v in row) for row in rows)
    caption = table.get("caption", "")
    return (f"{caption}\n" if caption else "") + f"{header}\n{sep}\n{body}"


# ── Prompts ──

DRAFT_PROMPT = """{preamble}

Data table:
{table}

Writing constraints:
{constraints}

Task: {instruction}

Write the artefact now. Output a Draft with an optional title/subject and the full body."""


REVISE_PROMPT = """{preamble}

Data table:
{table}

Writing constraints:
{constraints}

Current draft:
Title: {title}
Body:
{body}

Reviewer feedback to incorporate:
{feedback}

Revise the draft so that it incorporates the feedback while still satisfying every original constraint. Output the revised Draft."""


AGENT_SYSTEM_PROMPT = """{preamble}

You write the artefact through a self-controlled revision loop. After each draft you decide whether to revise it further or submit it. Revise when a constraint is not yet fully met or the writing can be improved; submit when the draft satisfies every constraint and is well written. Do not pad the text to look thorough — conciseness is valued.

When reviewer feedback is provided to you, incorporate it in your next revision while preserving all original constraints.

The data table and constraints are in the user message."""


# ── Frozen judge rubric template (filled with per-instance parameters; the
#    TEMPLATE is frozen, only the bracketed instance parameters vary) ──

JUDGE_PROMPT = """You are a senior communications editor scoring a single text artefact against its brief. You score the artefact as written; you do not rewrite it. You are NOT told which system produced it.

The artefact was written from a data table for this brief:
- Format: {format}
- Audience: {audience}
- Required tonality: {tonality}
- Framing/emphasis requested: {framing}
- Word window: {min_words}–{max_words}

Data table the artefact must stay faithful to:
{table}
{feedback_block}
Artefact under review:
Title: {title}
Body:
{body}

Score each criterion on an integer scale 1 (poor) to 5 (excellent). Judge only what is in the artefact; do not reward length — a longer artefact is not better, and padding should lower the conciseness score.

- completeness: Does it convey the substance the brief asks for, using the table's data?
- responsiveness: Does it reflect the reviewer feedback shown above? (If no feedback was given, score 5.)
- coherence: Is it logically organized and well structured for its format?
- tone_audience: Does it match the required tonality and suit the stated audience?
- conciseness: Is it free of padding and redundancy, tight for its purpose?

Return a JudgeScores object with the five integer scores and a one-sentence justification."""
