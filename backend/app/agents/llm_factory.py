"""OpenRouter LLM client (replaces local Ollama)."""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any

from openrouter import OpenRouter

from app.agents.text_sanitize import sanitize_user_facing_text
from app.config import settings

logger = logging.getLogger(__name__)

_USER_FACING_SYSTEM = (
    "You are Cardeko. Reply to the user only. "
    "No reasoning, planning, meta commentary, or analysis. "
    "Maximum 2 short sentences."
)


_PLACEHOLDER_KEY_MARKERS = (
    "your-key-here",
    "your_key_here",
    "changeme",
    "replace-me",
    "xxx",
)


def _api_key() -> str:
    key = (settings.openrouter_api_key or "").strip().strip('"').strip("'")
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and add your key from https://openrouter.ai/keys"
        )
    lower = key.lower()
    if any(m in lower for m in _PLACEHOLDER_KEY_MARKERS) or key == "sk-or-v1-":
        raise RuntimeError(
            "OPENROUTER_API_KEY is still a placeholder. Paste a real key from "
            "https://openrouter.ai/keys into backend/.env and restart the server."
        )
    return key


def _friendly_openrouter_error(exc: Exception) -> str:
    text = str(exc).strip()
    lower = text.lower()
    if "unauthorized" in lower or "user not found" in lower:
        return (
            "OpenRouter rejected the API key (User not found). "
            "Create a key at https://openrouter.ai/keys and set OPENROUTER_API_KEY "
            "in backend/.env — not the placeholder from .env.example."
        )
    if "insufficient" in lower or "credit" in lower or "balance" in lower:
        return f"OpenRouter billing/credits issue: {text}"
    return text


def resolve_model(*, fast: bool = False) -> str:
    return settings.openrouter_fast_model if fast else settings.openrouter_chat_model


def build_messages(
    prompt: str, *, system: str | None = None
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def _content_from_piece(obj: Any) -> str:
    """Message/delta content only — never expose model reasoning to the UI."""
    if obj is None:
        return ""
    content = getattr(obj, "content", None)
    if content is None and isinstance(obj, dict):
        content = obj.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(str(block["text"]))
                elif block.get("text"):
                    parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
        if parts:
            return "".join(parts)
    if content is not None and not isinstance(content, (list, dict)):
        return str(content)
    return ""


def chat_complete(
    prompt: str,
    *,
    fast: bool = False,
    temperature: float | None = None,
    system: str | None = None,
    max_tokens: int = 1024,
    user_facing: bool = False,
) -> str:
    temp = temperature if temperature is not None else 0.2
    model = resolve_model(fast=fast)
    if user_facing and system is None:
        system = _USER_FACING_SYSTEM
    logger.info("OpenRouter chat_complete model=%s", model)
    try:
        with OpenRouter(api_key=_api_key(), timeout_ms=120_000) as client:
            response = client.chat.send(
                model=model,
                messages=build_messages(prompt, system=system),
                temperature=temp,
                max_completion_tokens=max_tokens,
            )
    except Exception as exc:
        raise RuntimeError(_friendly_openrouter_error(exc)) from exc
    if not response.choices:
        logger.warning("OpenRouter returned no choices for model=%s", model)
        return ""
    text = _content_from_piece(response.choices[0].message)
    if user_facing:
        text = sanitize_user_facing_text(text)
    if not text.strip():
        logger.warning("OpenRouter empty content for model=%s", model)
    return text


def chat_stream(
    prompt: str,
    *,
    fast: bool = False,
    temperature: float | None = None,
    system: str | None = None,
    max_tokens: int = 256,
    user_facing: bool = True,
) -> Generator[str, None, None]:
    temp = temperature if temperature is not None else 0.2
    model = resolve_model(fast=fast)
    if user_facing and system is None:
        system = _USER_FACING_SYSTEM
    logger.info("OpenRouter chat_stream model=%s", model)
    try:
        client_ctx = OpenRouter(api_key=_api_key(), timeout_ms=120_000)
    except Exception as exc:
        raise RuntimeError(_friendly_openrouter_error(exc)) from exc
    with client_ctx as client:
        try:
            stream = client.chat.send(
                model=model,
                messages=build_messages(prompt, system=system),
                temperature=temp,
                stream=True,
                max_completion_tokens=max_tokens,
            )
        except Exception as exc:
            raise RuntimeError(_friendly_openrouter_error(exc)) from exc
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue
            piece = _content_from_piece(delta)
            if piece:
                yield piece


def embed_query(text: str) -> list[float]:
    """Embedding via OpenRouter (used by category matcher)."""
    with OpenRouter(api_key=_api_key(), timeout_ms=60_000) as client:
        response = client.embeddings.generate(
            input=text,
            model=settings.openrouter_embed_model,
        )
    if not response.data:
        return []
    item = response.data[0]
    embedding = getattr(item, "embedding", None)
    if embedding is None:
        return []
    return list(embedding)


def openrouter_health_ok() -> bool:
    if not (settings.openrouter_api_key or "").strip():
        return False
    try:
        with OpenRouter(api_key=_api_key(), timeout_ms=10_000) as client:
            client.models.list()
        return True
    except Exception as exc:
        logger.debug("OpenRouter health check failed: %s", exc)
        return False
