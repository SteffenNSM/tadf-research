"""Shared LLM backend configuration.

A single model is used across all conditions, archetypes, and paradigms so
that observed performance differences are attributable to the execution
paradigm, not the model configuration (Phase 2 protocol, Appendix A).

Design decisions for scientific reproducibility:
- Single pinned model snapshot across all runs (controlled variable).
- Temperature policy per archetype: 0.0 for planning (G), 0.2 elsewhere.
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

#: Temperature for archetype G (Strategic and Adaptive Planning). Determinism
#: aids plan validity, following PlanBench (Valmeekam et al., 2023).
PLANNING_TEMPERATURE = 0.0

#: Temperature for all other archetypes. A small non-zero value permits a
#: variance estimate across the repeated runs per task instance.
DEFAULT_TEMPERATURE = 0.2

#: Seed for reproducibility where the provider supports it.
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))


def get_llm(temperature: float = DEFAULT_TEMPERATURE) -> ChatOpenAI:
    """Return the shared LLM instance at the given temperature.

    The temperature is set per archetype in its ``config.py`` module:
    ``PLANNING_TEMPERATURE`` for archetype G, ``DEFAULT_TEMPERATURE`` for the
    rest. All other configuration is fixed to keep the model a controlled
    variable across conditions.

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
