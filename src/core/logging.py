"""Unified execution logging.

Captures the raw signals required to compute the six evaluation metrics
(see ``evaluation/metrics.py``) at execution time: token usage per LLM call,
tool-call count, latency, and errors. The same logger is attached to both the
workflow and the agent run of an archetype so that the captured signals are
directly comparable across paradigms.

Usage:
    logger = ExecutionLogger()
    logger.start()
    result = graph.invoke(state, config={"callbacks": [logger]})
    logger.stop()
    record = logger.to_record()
"""

import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


class ExecutionLogger(BaseCallbackHandler):
    """Callback handler that records per-execution telemetry.

    Token accounting reads the provider usage block first and falls back to
    the message ``usage_metadata`` so that the logger works regardless of
    which convention the installed LangChain version emits.
    """

    def __init__(self) -> None:
        self.llm_calls: int = 0
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.tool_calls: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self._start_time: float | None = None
        self._end_time: float | None = None

    # ── Latency lifecycle ──

    def start(self) -> None:
        """Mark the start of the execution for latency measurement."""
        self._start_time = time.perf_counter()

    def stop(self) -> None:
        """Mark the end of the execution for latency measurement."""
        self._end_time = time.perf_counter()

    @property
    def latency_s(self) -> float:
        """Wall-clock latency in seconds, or 0.0 if not measured."""
        if self._start_time is None or self._end_time is None:
            return 0.0
        return self._end_time - self._start_time

    @property
    def total_tokens(self) -> int:
        """Sum of input and output tokens across all LLM calls."""
        return self.input_tokens + self.output_tokens

    @property
    def tool_call_count(self) -> int:
        """Number of tool invocations during the execution."""
        return len(self.tool_calls)

    # ── LangChain callbacks ──

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Accumulate the LLM call count and token usage."""
        self.llm_calls += 1
        usage = self._extract_usage(response)
        if usage:
            self.input_tokens += int(
                usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
            )
            self.output_tokens += int(
                usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
            )

    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Record a tool invocation with its name and timestamp."""
        name = (serialized or {}).get("name", "unknown")
        self.tool_calls.append({"tool": name, "t": time.perf_counter()})

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """Record an LLM error."""
        self.errors.append(f"llm_error: {error}")

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        """Record a tool error."""
        self.errors.append(f"tool_error: {error}")

    # ── Helpers ──

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, Any] | None:
        """Extract a token-usage dict from an LLM response, or None."""
        llm_output = getattr(response, "llm_output", None)
        if llm_output:
            usage = llm_output.get("token_usage") or llm_output.get("usage")
            if usage:
                return usage
        try:
            message = response.generations[0][0].message
            return getattr(message, "usage_metadata", None)
        except (AttributeError, IndexError, TypeError):
            return None

    def to_record(self) -> dict[str, Any]:
        """Return the captured telemetry as a flat dict for persistence."""
        return {
            "llm_calls": self.llm_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "tool_call_count": self.tool_call_count,
            "tool_calls": self.tool_calls,
            "latency_s": self.latency_s,
            "errors": self.errors,
        }
