"""Metrics collection for experiment runs.

Captures per-run metrics required for the Aggregate Performance Score (APS):
- Token Cost (TC): prompt + completion tokens, converted to USD
- Latency (L): wall-clock time from invocation to final output
- Error tracking: exceptions, schema violations, timeouts

Uses LangChain's callback system to intercept all LLM calls transparently.
Both workflow and agent implementations are measured identically.

Pricing source: https://openai.com/api/pricing/ (pinned at experiment start)
"""

import time
from dataclasses import dataclass, field
from langchain_community.callbacks.openai_info import OpenAICallbackHandler


# ── Pricing (USD per token, pinned for experiment consistency) ──
PRICING = {
    "gpt-4o-2024-11-20": {
        "input": 2.50 / 1_000_000,   # $2.50 per 1M input tokens
        "output": 10.00 / 1_000_000,  # $10.00 per 1M output tokens
    },
}


@dataclass
class RunMetrics:
    """Metrics captured for a single experiment run."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    token_cost_usd: float = 0.0
    latency_ms: int = 0
    llm_calls: int = 0
    tool_calls: list = field(default_factory=list)
    error: str | None = None


class MetricsCollector:
    """Context manager that captures LLM metrics for one experiment run.

    Usage:
        collector = MetricsCollector()
        with collector:
            result = workflow.invoke(input, config=collector.config)
        metrics = collector.get_metrics()
    """

    def __init__(self, model_name: str = "gpt-4o-2024-11-20"):
        self.model_name = model_name
        self._callback = OpenAICallbackHandler()
        self._start_time: float = 0
        self._end_time: float = 0
        self._error: str | None = None

    @property
    def config(self) -> dict:
        """LangGraph config dict with callback handler attached."""
        return {"callbacks": [self._callback]}

    def __enter__(self):
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._end_time = time.perf_counter()
        if exc_type is not None:
            self._error = f"{exc_type.__name__}: {exc_val}"
        return False  # Do not suppress exceptions

    def get_metrics(self) -> RunMetrics:
        """Return collected metrics after the run completes."""
        pricing = PRICING.get(self.model_name, {"input": 0, "output": 0})
        prompt_tokens = self._callback.prompt_tokens
        completion_tokens = self._callback.completion_tokens

        return RunMetrics(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=self._callback.total_tokens,
            token_cost_usd=(
                prompt_tokens * pricing["input"]
                + completion_tokens * pricing["output"]
            ),
            latency_ms=int((self._end_time - self._start_time) * 1000),
            llm_calls=self._callback.successful_requests,
            error=self._error,
        )
