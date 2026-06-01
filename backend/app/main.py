import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings
from app.services.duckdb_service import duckdb_service
from app.services.feedback_join import feedback_join
from app.services.session_store import session_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    duckdb_service.initialize()
    logger.info("DuckDB storage: %s", duckdb_service.storage_mode)
    feedback_join.initialize()
    session_store.initialize()
    _ensure_placeholders()
    yield
    duckdb_service.close()


def _ensure_placeholders():
    base = Path(__file__).resolve().parent / "data" / "placeholders"
    base.mkdir(parents=True, exist_ok=True)
    default = base / "default.png"
    if not default.exists():
        # Minimal 1x1 PNG
        default.write_bytes(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                "1f15c4890000000a49444154789c63000100000500010d0a2db400000000"
                "49454e44ae426082"
            )
        )


app = FastAPI(title="Cardeko API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

placeholders_dir = Path(__file__).resolve().parent / "data" / "placeholders"
placeholders_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/placeholders", StaticFiles(directory=str(placeholders_dir)), name="placeholders")


@app.get("/health")
def health():
    from app.agents.llm_factory import openrouter_health_ok

    return {
        "status": "ok",
        "duckdb": duckdb_service.health_ok(),
        "duckdb_storage": duckdb_service.storage_mode,
        "openrouter": openrouter_health_ok(),
        "openrouter_api_key_set": bool((settings.openrouter_api_key or "").strip()),
        "openrouter_chat_model": settings.openrouter_chat_model,
        "openrouter_fast_model": settings.openrouter_fast_model,
    }
