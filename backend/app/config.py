import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str = ""
    openrouter_chat_model: str = "qwen/qwen3-8b"
    openrouter_fast_model: str = "qwen/qwen3-coder-next"
    openrouter_embed_model: str = "openai/text-embedding-3-small"

    llm_temp_session_manager: float = 0.5
    llm_temp_question_generator: float = 0.7
    llm_temp_welcome: float = 0.6
    llm_temp_router: float = 0.1
    llm_temp_sql: float = 0.1

    checkpoint_db_path: str = "./runtime/checkpoints.db"
    session_db_path: str = "./runtime/sessions.db"
    duckdb_path: str = "./runtime/cardeko.duckdb"
    # Use :memory: to avoid file lock issues (recommended on Windows / uvicorn --reload).
    duckdb_in_memory: bool = sys.platform == "win32"
    # If the .duckdb file is locked, load CSV into memory instead.
    duckdb_fallback_memory: bool = True
    # Max vehicle cards shown in the UI grid per update.
    ui_cards_limit: int = 30
    # Legacy alias used for initial catalog size.
    initial_catalog_limit: int = 30
    cardata_dir: str = "../cardata"
    cors_origins: str = "http://localhost:5173"

    @property
    def cardata_path(self) -> Path:
        p = Path(self.cardata_dir)
        if not p.is_absolute():
            p = (_BACKEND_ROOT / p).resolve()
        return p

    @property
    def duckdb_file(self) -> Path:
        p = Path(self.duckdb_path)
        if not p.is_absolute():
            p = (_BACKEND_ROOT / p).resolve()
        return p

    @property
    def checkpoint_file(self) -> Path:
        p = Path(self.checkpoint_db_path)
        if not p.is_absolute():
            p = (_BACKEND_ROOT / p).resolve()
        return p

    @property
    def session_db_file(self) -> Path:
        p = Path(self.session_db_path)
        if not p.is_absolute():
            p = (_BACKEND_ROOT / p).resolve()
        return p

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
