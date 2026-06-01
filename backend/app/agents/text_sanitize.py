"""Strip model reasoning and keep user-facing replies short."""

from __future__ import annotations

import re

_REASONING_MARKERS = (
    "the user said",
    "let's see",
    "let me check",
    "i need to",
    "the phase is",
    "missing dimensions",
    "candidate count",
    "critical rules",
    "alright, that should be it",
)


def sanitize_user_facing_text(text: str, *, max_chars: int = 400) -> str:
    """Remove chain-of-thought and keep a concise assistant reply."""
    t = (text or "").strip()
    if not t:
        return ""
    think_open, think_close = "<think>", "</think>"
    t = re.sub(
        re.escape(think_open) + r"[\s\S]*?" + re.escape(think_close),
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"<thinking>[\s\S]*?</thinking>", "", t, flags=re.IGNORECASE)
    t = t.strip()
    lower = t.lower()
    if any(m in lower for m in _REASONING_MARKERS):
        lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
        for ln in reversed(lines):
            if len(ln) <= 220 and not any(m in ln.lower() for m in _REASONING_MARKERS):
                return ln[:max_chars]
        sentences = re.split(r"(?<=[.?!])\s+", t)
        for ln in reversed(sentences):
            ln = ln.strip()
            if ln and len(ln) <= 220 and not any(m in ln.lower() for m in _REASONING_MARKERS):
                return ln[:max_chars]
    if len(t) > max_chars:
        cut = t[:max_chars]
        last_space = cut.rfind(" ")
        if last_space > max_chars // 2:
            cut = cut[:last_space]
        return cut.rstrip() + "…"
    return t
