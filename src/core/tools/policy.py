"""Simulated Policy Registry service for archetype D.

Exposes the company approval policy as an EXTERNAL service reached only
through its API, mirroring how a production compliance flow loads its rules
from a policy store rather than hard-coding them. Two read tools are offered:

    list_policies()      -> the catalogue of available policy documents
    get_policy(topic)    -> the rule clauses + human text for one document

Both add the protocol's synthetic latency (Appendix A.5) so the wall-clock
latency reflects the order of magnitude of a real rules-service round trip,
exactly as the Mail/Calendar tools do for archetype B/F. The document data
lives in ``policy_data.py`` (framework-free) so the deterministic rule engine
and the tests can read the same source of truth without importing LangChain.

Both paradigms share these two tools (Phase-2 tool-symmetry invariant A.3).
The workflow calls them in a fixed order (survey the catalogue, then fetch
every document) and applies the assembled clauses with a deterministic engine.
The agent calls them at runtime, deciding which documents it needs, and applies
the rules in-context.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from src.core.tools._latency import synthetic_delay
from src.core.tools.policy_data import get_doc, list_topics


@tool
def list_policies() -> list[dict[str, str]]:
    """List the policy documents available in the compliance Policy Registry.

    Returns:
        A list of catalogue entries, one per document, each with:
        ``topic`` (the identifier passed to ``get_policy``), ``title``, and a
        one-line ``summary`` of what the document governs.
    """
    synthetic_delay("list_policies", {})
    return list_topics()


@tool
def get_policy(topic: str) -> dict[str, Any]:
    """Fetch one policy document from the Policy Registry by its topic id.

    Args:
        topic: The document identifier from ``list_policies`` (e.g.
            ``"escalation_matrix"``).

    Returns:
        The document: ``{topic, title, summary, rules_text, clauses}``.
        ``rules_text`` is the human-readable policy; ``clauses`` is the
        machine-readable rule set (gate / bonus / decision records). Returns
        ``{"error": ...}`` if the topic is unknown.
    """
    synthetic_delay("get_policy", {"topic": topic})
    doc = get_doc(topic)
    if doc is None:
        return {"error": f"unknown policy topic {topic!r}"}
    return doc
