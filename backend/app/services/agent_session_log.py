"""Append-only per-session log of agent steps, tools, inputs, and outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings

_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "runtime" / "session_logs"


def _log_path(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
    return _LOG_DIR / f"{safe}.jsonl"


def log_agent_step(
    session_id: str,
    *,
    agent: str,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    tools_used: list[str] | None = None,
    error: str | None = None,
    turn_id: str | None = None,
) -> None:
    if not session_id:
        return
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "turn_id": turn_id,
        "agent": agent,
        "tools_used": tools_used or [],
        "inputs": inputs or {},
        "outputs": outputs or {},
        "llm_provider": "openrouter",
    }
    if error:
        entry["error"] = error
    with _log_path(session_id).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def log_chat_turn_start(session_id: str, user_message: str) -> str:
    turn_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    log_agent_step(
        session_id,
        agent="chat_turn",
        inputs={"user_message": user_message},
        outputs={"status": "started"},
        turn_id=turn_id,
    )
    return turn_id
