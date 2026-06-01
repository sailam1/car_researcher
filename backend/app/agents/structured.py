"""Helpers for structured and streaming LLM outputs via OpenRouter."""

from __future__ import annotations

import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel

from app.agents.llm_factory import chat_complete, chat_stream

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    arr_start = text.find("[")
    if start == -1 and arr_start != -1:
        end = text.rfind("]")
        return json.loads(text[arr_start : end + 1])
    if start != -1:
        end = text.rfind("}")
        return json.loads(text[start : end + 1])
    return json.loads(text)


def invoke_structured(
    prompt: str,
    schema: type[T],
    *,
    fast: bool = False,
    temperature: float | None = None,
) -> T:
    sys = (
        f"You must respond with valid JSON matching this schema: {schema.model_json_schema()}. "
        "No markdown, no explanation outside JSON."
    )
    try:
        content = chat_complete(
            prompt,
            fast=fast,
            temperature=temperature,
            system=sys,
        )
    except Exception as exc:
        logger.exception("invoke_structured LLM call failed")
        raise
    if not content.strip():
        raise ValueError("OpenRouter returned empty structured response")
    data = _extract_json(content)
    if isinstance(data, list) and schema.__name__ == "SessionManagerOutput":
        data = data[0] if data else {}
    return schema.model_validate(data)


def invoke_text(
    prompt: str,
    *,
    fast: bool = False,
    temperature: float | None = None,
    max_tokens: int = 256,
) -> str:
    return "".join(
        invoke_text_stream(
            prompt, fast=fast, temperature=temperature, max_tokens=max_tokens
        )
    )


def invoke_text_stream(
    prompt: str,
    *,
    fast: bool = False,
    temperature: float | None = None,
    max_tokens: int = 256,
):
    """Yield text tokens from OpenRouter (content only, no reasoning field)."""
    yield from chat_stream(
        prompt,
        fast=fast,
        temperature=temperature,
        max_tokens=max_tokens,
        user_facing=True,
    )
