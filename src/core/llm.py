"""Shared LLM backend configuration.

A single model is used across all conditions, archetypes, and paradigms so
that observed performance differences are attributable to the execution
paradigm, not the model configuration (Phase 2 protocol, Appendix A).

Design decisions for scientific reproducibility:
- Single pinned model snapshot across all runs (controlled variable).
- Temperature 0 for all archetypes (deterministic single-run evaluation,
  following WorkBench and PlanBench; see iteration log IT-030). Under
  deterministic decoding a single run per instance is the appropriate design,
  so no within-instance variance is estimated by repeated runs.
- ``reasoning_effort`` is set to ``"none"`` explicitly, so the GPT-5 family is
  used in its standard chat-completion mode. Reasoning-mode tokens are billed
  separately and would not be cleanly comparable across paradigms; the
  controlled experiments therefore disable internal reasoning.
- Fixed seed for the instance-ordering and sampling where the provider honors it.
- Token usage is captured per call by the ExecutionLogger callback (logging.py),
  not here, so this module stays a thin configuration surface.
"""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# ── Controlled model configuration ──

#: Pinned model snapshot. Changing this invalidates cross-run comparability.
MODEL_NAME = "gpt-5.2-2025-12-11"

#: GPT-5 family supports an internal reasoning mode. For controlled experiments
#: it is disabled so token accounting compares cleanly across paradigms.
REASONING_EFFORT = "none"

#: Temperature for all archetypes. Set to 0 for deterministic single-run
#: evaluation (WorkBench, PlanBench convention; IT-030). Changing this
#: invalidates the deterministic-single-run rationale of the Phase 2 design.
DEFAULT_TEMPERATURE = 0.0

#: Retained alias for archetype G's explicit reference; identical to the
#: default now that all archetypes run deterministically.
PLANNING_TEMPERATURE = 0.0

#: Seed for reproducibility where the provider supports it.
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))


def get_llm(temperature: float = DEFAULT_TEMPERATURE) -> ChatOpenAI:
    """Return the shared LLM instance at the given temperature.

    The temperature is taken from each archetype's ``config.py`` module; all
    archetypes use ``DEFAULT_TEMPERATURE`` (0) for deterministic single-run
    evaluation. All other configuration is fixed to keep the model a
    controlled variable across conditions.

    Args:
        temperature: Sampling temperature for this archetype.

    Returns:
        A configured ``ChatOpenAI`` instance pinned to ``MODEL_NAME`` with
        ``reasoning_effort`` set to ``"none"``.

    Raises:
        ValueError: If no valid ``OPENAI_API_KEY`` is configured.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-key-here":
        raise ValueError("Set a valid OPENAI_API_KEY in .env")

    return ChatOpenAI(
        model=MODEL_NAME,
        temperature=temperature,
        seed=RANDOM_SEED,
        api_key=api_key,
        model_kwargs={"reasoning_effort": REASONING_EFFORT},
    )
