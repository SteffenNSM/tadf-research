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
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# ── Controlled model configuration ──

#: The strong reference model of the final evaluation grid (pre-registered in
#: the protocol) and the frozen judge model. NOTE (final-grid design): the
#: reported Phase 2 results come from a THREE-TIER capability grid on the
#: frozen artifact state -- gpt-5.4-nano (2x clean + 1x robustness),
#: gpt-5.4-mini (2x clean + 1x robustness), gpt-5.2 (1x clean + 1x
#: robustness). nano and mini are therefore RESULT models, not development-
#: only models; the earlier binary dev/final labeling applies only to
#: unlabeled ad-hoc runs (see ``results_dir``).
FINAL_MODEL = "gpt-5.2-2025-12-11"

#: Optional grid-run label (e.g. "run1", "run2", "robustness"). When set,
#: results are written to ``<results>/final/<model>/<label>/`` for every
#: model tier; when unset, the legacy dev/final routing applies.
RUN_LABEL = os.getenv("TADF_RUN_LABEL", "")

#: Active model. Defaults to gpt-5.4-nano (capability tier 1 of the final
#: grid; also the cheap pipeline-shake-out model during development);
#: override via the TADF_MODEL environment variable. The active model is
#: stamped into every results file so runs are never confused.
MODEL_NAME = os.getenv("TADF_MODEL", "gpt-5.4-nano-2026-03-17")

#: True while a non-reference model is active WITHOUT a grid label; routes
#: unlabeled ad-hoc runs to the dev folder (see ``results_dir``).
IS_DEV_MODEL = MODEL_NAME != FINAL_MODEL

#: GPT-5 family supports an internal reasoning mode. For controlled experiments
#: it is disabled so token accounting compares cleanly across paradigms. The
#: parameter is GPT-5-only; other families (e.g. gpt-4o-mini) reject it, so it
#: is passed conditionally in ``get_llm``.
REASONING_EFFORT = "none"


def _supports_reasoning_effort(model: str) -> bool:
    """Whether the model accepts the ``reasoning_effort`` parameter (GPT-5+)."""
    return model.startswith("gpt-5")


def results_dir(base_results: Path) -> Path:
    """Return the results directory for the active model and run label.

    Grid runs (TADF_RUN_LABEL set) are written to
    ``<results>/final/<model>/<label>/`` for every capability tier, so the
    model and run assignment is encoded in the path as well as in the file's
    ``model`` stamp. Unlabeled runs keep the legacy routing: non-reference
    models go to ``<results>/dev/`` (ad-hoc shake-out), the reference model
    to ``<results>/`` directly.
    """
    if RUN_LABEL:
        target = base_results / "final" / MODEL_NAME / RUN_LABEL
    else:
        target = base_results / "dev" if IS_DEV_MODEL else base_results
    target.mkdir(parents=True, exist_ok=True)
    return target

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

    kwargs: dict = {
        "model": MODEL_NAME,
        "temperature": temperature,
        "seed": RANDOM_SEED,
        "api_key": api_key,
        # Bound provider stalls: without an explicit timeout the OpenAI client
        # waits up to 600s PER ATTEMPT with retries, so a throttled call can
        # silently stall a grid cell for ~30 minutes (observed 2026-07-06:
        # 120s+ single-call latencies under rate limiting). 300s per attempt,
        # 3 retries keeps slow-but-legitimate calls alive and hangs bounded.
        "timeout": float(os.getenv("TADF_LLM_TIMEOUT", "300")),
        "max_retries": int(os.getenv("TADF_LLM_RETRIES", "3")),
    }
    # reasoning_effort is sent ONLY for the final reported model. Its purpose
    # is clean reasoning-token accounting on the reported run; development
    # models do not need it, and some GPT-5 small models (e.g. gpt-5.4-nano)
    # reject reasoning_effort when function tools are bound (agent paradigm),
    # returning a 400. Omitting it for dev models avoids that incompatibility
    # without affecting the reported sweep. (Non-GPT-5 finals would reject the
    # parameter outright, hence the family guard.)
    if not IS_DEV_MODEL and _supports_reasoning_effort(MODEL_NAME):
        kwargs["model_kwargs"] = {"reasoning_effort": REASONING_EFFORT}
    return ChatOpenAI(**kwargs)
