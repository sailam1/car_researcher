"""LangGraph SqliteSaver for per-session graph checkpoints."""

from __future__ import annotations

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from app.config import settings

_checkpointer: SqliteSaver | None = None


def get_checkpointer() -> SqliteSaver:
    global _checkpointer
    if _checkpointer is None:
        path = settings.checkpoint_file
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), check_same_thread=False)
        _checkpointer = SqliteSaver(conn)
    return _checkpointer
