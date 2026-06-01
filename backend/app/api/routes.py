import json
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

logger = logging.getLogger(__name__)

from app.graphs.main_graph import run_chat_turn, run_manual_filter
from app.models.schemas import (
    ActiveFilters,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CompareVehicle,
    SessionCreateResponse,
    SessionResponse,
    VehicleDetail,
)
from app.agents.nodes import run_welcome
from app.config import settings
from app.services.catalog import build_initial_catalog
from app.services.duckdb_service import duckdb_service
from app.services.chat_stream import stream_chat_turn
from app.services.feedback_join import feedback_join
from app.services.session_store import session_store
from app.services.ui_sync import build_ui_payload
from app.models.state import GraphState

router = APIRouter(prefix="/api")


@router.get("/health")
def api_health():
    """Lightweight health for frontend wake-up polling (Render cold start)."""
    return {
        "status": "ok",
        "duckdb": duckdb_service.health_ok(),
    }


@router.post("/sessions", response_model=SessionCreateResponse)
def create_session():
    state = session_store.create_session()
    welcome_text, summary = run_welcome()
    state.messages.append(ChatMessage(role="assistant", content=welcome_text))
    state.narrative_summary = summary
    state.discovery_phase = "welcome"
    vehicles, showing, total = build_initial_catalog()
    state.vehicles = vehicles
    state.catalog_total = total
    state.catalog_showing = showing
    state.candidate_count = total
    session_store.save(state)
    opts = duckdb_service.get_filter_options()
    return SessionCreateResponse(
        session_id=state.session_id,
        messages=state.messages,
        ui_state=state.to_ui_state(opts),
        discovery_phase=state.discovery_phase,
        narrative_summary=state.narrative_summary,
    )


@router.get("/catalog")
def get_catalog(limit: int = 500, offset: int = 0):
    from app.services.catalog import catalog_total_count, fetch_catalog_rows, rows_to_cards

    lim = min(max(limit, 1), 2000)
    rows = fetch_catalog_rows(limit=lim, offset=offset)
    total = catalog_total_count()
    return {
        "vehicles": rows_to_cards(rows),
        "catalog_total": total,
        "catalog_showing": len(rows),
        "offset": offset,
    }


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    state = session_store.get(session_id)
    if not state:
        raise HTTPException(404, "Session not found")
    if not state.vehicles:
        vehicles, showing, total = build_initial_catalog()
        state.vehicles = vehicles
        state.catalog_total = total
        state.catalog_showing = showing
        session_store.save(state)
    opts = duckdb_service.get_filter_options(state.filters)
    return SessionResponse(
        session_id=state.session_id,
        messages=state.messages,
        ui_state=state.to_ui_state(opts),
        discovery_phase=state.discovery_phase,
        narrative_summary=state.narrative_summary,
        candidate_count=state.candidate_count,
    )


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    state = session_store.get(req.session_id)
    if not state:
        raise HTTPException(404, "Session not found")

    def event_gen():
        for line in stream_chat_turn(state, req.message):
            yield line
        session_store.save(state)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    state = session_store.get(req.session_id)
    if not state:
        raise HTTPException(404, "Session not found")
    try:
        result = run_chat_turn(state, req.message)
    except Exception as exc:
        logger.exception("Chat pipeline failed for session %s", req.session_id)
        detail = str(exc)
        lower = detail.lower()
        if any(
            k in lower
            for k in ("openrouter", "api_key", "401", "403", "connection", "connect")
        ):
            raise HTTPException(
                status_code=503,
                detail=(
                    f"LLM service error: {detail}. "
                    "Check OPENROUTER_API_KEY in backend/.env and model "
                    f"{settings.openrouter_chat_model}."
                ),
            ) from exc
        raise HTTPException(status_code=500, detail=detail) from exc
    session_store.save(result.session)
    ui = build_ui_payload(
        GraphState(session=result.session, user_message=req.message, reply=result.reply)
    )
    from app.models.schemas import UIState

    return ChatResponse(
        reply=result.reply,
        messages=result.session.messages,
        ui_state=UIState.model_validate(ui),
        discovery_phase=result.session.discovery_phase,
    )


@router.patch("/sessions/{session_id}/filters")
def update_filters(session_id: str, filters: ActiveFilters):
    state = session_store.get(session_id)
    if not state:
        raise HTTPException(404, "Session not found")
    state.ui_manual_filters = filters
    state.filters = filters
    result = run_manual_filter(state)
    session_store.save(result.session)
    ui = build_ui_payload(result)
    return {
        "reply": result.reply,
        "ui_state": ui,
        "discovery_phase": result.session.discovery_phase,
        "candidate_count": result.session.candidate_count,
        "shortlist_label": ui.get("shortlist_label", ""),
    }


@router.get("/vehicles/{vehicle_id}", response_model=VehicleDetail)
def get_vehicle(vehicle_id: str):
    row = duckdb_service.get_vehicle_by_id(vehicle_id)
    if not row:
        raise HTTPException(404, "Vehicle not found")
    fb = feedback_join.get_summary(vehicle_id)
    specs = {k: v for k, v in row.items() if k != "vehicle_id"}
    snippets = fb.get("snippets", []) or []
    return VehicleDetail(
        vehicle_id=vehicle_id,
        make=str(row.get("make", "")),
        model=str(row.get("model", "")),
        variant=str(row.get("variant", "")),
        specs=specs,
        avg_rating=fb.get("avg_rating"),
        review_snippets=snippets,
        pros=[str(s)[:200] for s in snippets[:3]],
    )


@router.get("/compare")
def compare(ids: str = Query(..., description="Comma-separated vehicle IDs")):
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    rows = duckdb_service.get_vehicles_by_ids(id_list)
    out = []
    for row in rows:
        vid = str(row.get("vehicle_id", ""))
        fb = feedback_join.get_summary(vid)
        specs = {
            "yearFrom": row.get("yearFrom"),
            "engineFuelType": row.get("engineFuelType"),
            "gearboxType": row.get("gearboxType"),
            "enginePowerBhp": row.get("enginePowerBhp"),
            "bootLitres": row.get("bootLitres"),
            "fuelEconomyCombinedL100": row.get("fuelEconomyCombinedL100"),
            "drivetrain": row.get("drivetrain"),
            "weightKg": row.get("weightKg"),
        }
        out.append(
            CompareVehicle(
                vehicle_id=vid,
                make=str(row.get("make", "")),
                model=str(row.get("model", "")),
                variant=str(row.get("variant", "")),
                specs=specs,
                avg_rating=fb.get("avg_rating"),
            )
        )
    return {"vehicles": out}


@router.get("/sessions/{session_id}/agent-log")
def get_session_agent_log(session_id: str, tail: int = Query(80, ge=1, le=500)):
    """Return recent agent I/O log lines for this chat session (JSONL on disk)."""
    from app.services.agent_session_log import _log_path

    path = _log_path(session_id)
    if not path.exists():
        return {"session_id": session_id, "path": str(path), "entries": []}
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    import json

    entries = []
    for line in lines[-tail:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"session_id": session_id, "path": str(path), "entries": entries}


@router.get("/placeholders/{name}")
def placeholder_image(name: str):
    from pathlib import Path

    base = Path(__file__).resolve().parent.parent / "data" / "placeholders"
    path = base / name
    if not path.exists():
        path = base / "default.png"
    if not path.exists():
        raise HTTPException(404, "Placeholder not found")
    return FileResponse(path)
