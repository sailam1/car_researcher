"""Optional deep-agent fetch path (not used by main discovery graph)."""

from __future__ import annotations

# Main graph uses OpenRouter via llm_factory + tools directly in nodes.py.
build_fetch_agent = None  # type: ignore
