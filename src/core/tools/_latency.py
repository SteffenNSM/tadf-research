"""Synthetic latency helper for Layer 2 simulated services (protocol A.5).

Adds a deterministic per-call latency to the simulated Mail and Calendar tools
so the wall-clock latency metric reflects the order of magnitude of real-API
round trips, rather than near-zero local execution. The latency is derived from
the call signature so that identical calls return identical delays, which keeps
the comparison between workflow and agent fair on identical task instances
across re-runs.

The latency layer is disabled if the environment variable
``TADF_DISABLE_SYNTHETIC_LATENCY`` is set to a non-empty value. This is for
unit tests where the executor logic is being checked and added wall-time would
just slow the test suite without informing correctness.
"""

from __future__ import annotations

import hashlib
import os
import random
import time
from typing import Any

#: Base latency target (seconds), per protocol Appendix A.5.
BASE_LATENCY_S = 0.300

#: Uniform jitter half-width (seconds), per protocol Appendix A.5.
JITTER_S = 0.050


def _signature(tool_name: str, args: dict[str, Any] | None) -> str:
    """Stable string for a tool call, used as latency seed."""
    payload = {"tool": tool_name, "args": args or {}}
    return repr(sorted(payload.items()))


def synthetic_delay(tool_name: str, args: dict[str, Any] | None = None) -> None:
    """Sleep for the deterministic synthetic latency of this call.

    No-op if ``TADF_DISABLE_SYNTHETIC_LATENCY`` is set.
    """
    if os.getenv("TADF_DISABLE_SYNTHETIC_LATENCY"):
        return
    seed = int(hashlib.sha256(_signature(tool_name, args).encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    offset = (rng.random() * 2 - 1) * JITTER_S
    time.sleep(BASE_LATENCY_S + offset)
