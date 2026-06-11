"""Web-search tool with deterministic disk cache.

Exposes a single LangChain tool, ``tavily_search``, that wraps the Tavily Search
API. Each unique query is cached on disk under ``data/search_cache/`` so that
re-runs of the experiment return identical snippets, regardless of when the
live web changes. This protects the workflow-vs-agent comparison from
content-drift confounds and makes the experiment reproducible by a reviewer.

Cache contract:
- Cache key is a SHA-256 prefix of the query string. Same query produces the
  same key.
- First call for a query: hits the live Tavily API, persists the normalized
  snippet list as JSON, and returns it.
- Subsequent calls for the same query: read the JSON, no network call.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

#: Repository-local cache directory; created on first use.
CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "search_cache"

#: Default snippets per query.
DEFAULT_MAX_RESULTS = 5


def _cache_path(query: str, max_results: int) -> Path:
    """Stable file path for a cached query result."""
    key = f"{query.strip().lower()}|n={max_results}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{digest}.json"


def _normalize_results(raw: dict[str, Any]) -> list[dict[str, str]]:
    """Reduce the Tavily response to a stable {title, url, content} list."""
    out = []
    for item in raw.get("results", []) or []:
        out.append(
            {
                "title": item.get("title", "") or "",
                "url": item.get("url", "") or "",
                "content": item.get("content", "") or "",
            }
        )
    return out


def _live_search(query: str, max_results: int) -> list[dict[str, str]]:
    """Call the Tavily API and return normalized snippets."""
    from tavily import TavilyClient  # imported lazily so the module is importable without the dep

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("Set TAVILY_API_KEY in .env to use the web-search tool")
    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=max_results)
    return _normalize_results(response)


def web_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict[str, str]]:
    """Search the web for ``query`` and return up to ``max_results`` snippets.

    Direct (non-tool) function used by deterministic workflow nodes and tests.
    The result is cached on disk; identical queries return identical snippets.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(query, max_results)
    if path.exists():
        return json.loads(path.read_text())
    results = _live_search(query, max_results)
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    return results


@tool
def tavily_search(query: str) -> list[dict[str, str]]:
    """Search the web for the given query and return up to five snippets.

    Each snippet is a dict with ``title``, ``url``, and ``content``. The same
    query always returns the same snippets within an experiment run, because
    results are cached on disk on the first call.

    Args:
        query: The search query.

    Returns:
        A list of snippet dicts (up to five).
    """
    return web_search(query, DEFAULT_MAX_RESULTS)
