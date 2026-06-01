"""SQLite-backed session persistence."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.models.schemas import ChatMessage
from app.models.state import SessionState


class SessionStore:
    def __init__(self) -> None:
        self._path: Path | None = None

    def initialize(self) -> None:
        self._path = settings.session_db_file
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        if self._path is None:
            raise RuntimeError("SessionStore not initialized")
        return sqlite3.connect(str(self._path))

    def create_session(self) -> SessionState:
        session_id = str(uuid.uuid4())
        state = SessionState(session_id=session_id, discovery_phase="welcome")
        self.save(state)
        return state

    def get(self, session_id: str) -> SessionState | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT state_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if not row:
            return None
        data = json.loads(row[0])
        return SessionState.model_validate(data)

    def save(self, state: SessionState) -> None:
        state.updated_at = datetime.utcnow()
        payload = state.model_dump(mode="json")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (state.session_id, json.dumps(payload), state.updated_at.isoformat()),
            )
            conn.commit()

    def append_message(self, state: SessionState, role: str, content: str) -> None:
        state.messages.append(ChatMessage(role=role, content=content))
        self.save(state)


session_store = SessionStore()
