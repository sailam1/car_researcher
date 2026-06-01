"""Streaming chat pipeline with step progress and token streaming."""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

from app.agents.nodes import (
    build_question_prompt,
    finalize_question_reply,
    node_enough_data,
    node_general_router,
    node_message_info_analyzer,
    node_preference_extractor,
    node_session_manager,
    node_ui_finalize,
    node_vehicle_search,
    node_why_recommend,
    route_after_enough_data,
    route_after_router,
)
from app.agents.structured import invoke_text_stream
from app.config import settings
from app.models.schemas import ChatMessage
from app.models.state import GraphState, SessionState
from app.prompts.prompt_loader import load_prompt
from app.services.duckdb_service import duckdb_service
from app.services.agent_session_log import log_agent_step, log_chat_turn_start
from app.services.ui_sync import build_ui_payload

STEP_LABELS: dict[str, str] = {
    "router": "Understanding your message…",
    "general_qa": "Writing answer…",
    "preference_extractor": "Learning your preferences…",
    "session_manager": "Updating your research profile…",
    "vehicle_search": "Searching the vehicle catalog…",
    "message_info_analyzer": "Reviewing your last answer…",
    "enough_data": "Checking if we can shortlist…",
    "question_generator": "Formulating the next question…",
    "why_recommend": "Explaining recommendations…",
    "ui_finalize": "Updating your shortlist…",
}


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


def _stream_reply_text(text: str, chunk_size: int = 12) -> Generator[str, None, None]:
    for i in range(0, len(text), chunk_size):
        yield _sse({"type": "token", "content": text[i : i + chunk_size]})


def _log_discovery_step(
    session_id: str, step_key: str, state: GraphState, turn_id: str
) -> None:
    outputs: dict = {
        "discovery_phase": state.session.discovery_phase,
        "candidate_count": state.session.candidate_count,
        "vehicles_on_screen": len(state.session.vehicles),
    }
    if step_key == "preference_extractor" and state.preference_delta:
        outputs["preferences"] = state.preference_delta.model_dump()
    if step_key == "session_manager" and state.session_manager_output:
        outputs["session_manager"] = state.session_manager_output.model_dump()
    if state.fetch_result:
        outputs["sql"] = state.fetch_result.sql
        outputs["fetch_error"] = state.fetch_result.error
    if step_key in ("question_generator", "ui_finalize", "general_qa"):
        outputs["reply_preview"] = (state.reply or "")[:500]
    log_agent_step(
        session_id,
        agent=step_key,
        inputs={"user_message": state.user_message},
        outputs=outputs,
        turn_id=turn_id,
    )


def _emit_ui_update(state: GraphState) -> Generator[str, None, None]:
    ui = build_ui_payload(state)
    yield _sse(
        {
            "type": "ui_update",
            "ui_state": ui,
            "discovery_phase": state.session.discovery_phase,
            "shortlist_label": ui.get("shortlist_label", ""),
            "candidate_count": ui.get("candidate_count", 0),
        }
    )


def stream_chat_turn(
    session: SessionState, user_message: str
) -> Generator[str, None, None]:
    """Yield SSE lines: step, token, done, or error events."""
    state = GraphState(session=session, user_message=user_message)
    turn_id = log_chat_turn_start(session.session_id, user_message)

    try:
        yield _sse({"type": "step", "step": "router", "label": STEP_LABELS["router"]})
        state = node_general_router(state)
        log_agent_step(
            session.session_id,
            agent="general_router",
            inputs={"user_message": user_message},
            outputs={"is_general_query": state.is_general_query},
            turn_id=turn_id,
        )

        if route_after_router(state) == "general_qa":
            yield _sse(
                {
                    "type": "step",
                    "step": "general_qa",
                    "label": STEP_LABELS["general_qa"],
                }
            )
            prompt = load_prompt(
                "general_qa",
                narrative_summary=state.session.narrative_summary,
                user_message=state.user_message,
            )
            state.session.messages.append(
                ChatMessage(role="user", content=state.user_message)
            )
            reply_parts: list[str] = []
            for token in invoke_text_stream(
                prompt, fast=False, temperature=settings.llm_temp_question_generator
            ):
                reply_parts.append(token)
                yield _sse({"type": "token", "content": token})
            state.reply = "".join(reply_parts)
            state.session.messages.append(
                ChatMessage(role="assistant", content=state.reply)
            )
            yield from _emit_ui_update(state)
        else:
            for step_key, node_fn in [
                ("preference_extractor", node_preference_extractor),
                ("session_manager", node_session_manager),
                ("vehicle_search", node_vehicle_search),
                ("message_info_analyzer", node_message_info_analyzer),
                ("enough_data", node_enough_data),
            ]:
                yield _sse(
                    {
                        "type": "step",
                        "step": step_key,
                        "label": STEP_LABELS[step_key],
                    }
                )
                state = node_fn(state)
                _log_discovery_step(session.session_id, step_key, state, turn_id)
                if step_key == "vehicle_search":
                    ui = build_ui_payload(state)
                    yield _sse(
                        {
                            "type": "step",
                            "step": "vehicle_search",
                            "label": ui.get("shortlist_label")
                            or f"Found {state.session.candidate_count} matches…",
                        }
                    )
                    yield from _emit_ui_update(state)

            branch = route_after_enough_data(state)
            if branch == "question":
                yield _sse(
                    {
                        "type": "step",
                        "step": "question_generator",
                        "label": STEP_LABELS["question_generator"],
                    }
                )
                q_prompt = build_question_prompt(state)
                reply_parts: list[str] = []
                try:
                    for token in invoke_text_stream(
                        q_prompt,
                        fast=False,
                        temperature=settings.llm_temp_question_generator,
                    ):
                        reply_parts.append(token)
                        yield _sse({"type": "token", "content": token})
                except Exception as stream_exc:
                    logger = __import__("logging").getLogger(__name__)
                    logger.warning("Question stream failed: %s", stream_exc)
                state = finalize_question_reply(state, "".join(reply_parts))
                _log_discovery_step(session.session_id, "question_generator", state, turn_id)
                yield from _emit_ui_update(state)
            else:
                yield _sse(
                    {
                        "type": "step",
                        "step": "why_recommend",
                        "label": STEP_LABELS["why_recommend"],
                    }
                )
                state = node_why_recommend(state)
                yield _sse(
                    {
                        "type": "step",
                        "step": "ui_finalize",
                        "label": STEP_LABELS["ui_finalize"],
                    }
                )
                state = node_ui_finalize(state)
                _log_discovery_step(session.session_id, "ui_finalize", state, turn_id)
                yield from _emit_ui_update(state)
                if state.reply:
                    yield from _stream_reply_text(state.reply)

        ui = build_ui_payload(state)
        yield _sse(
            {
                "type": "done",
                "reply": state.reply,
                "messages": [m.model_dump(mode="json") for m in state.session.messages],
                "ui_state": ui,
                "discovery_phase": state.session.discovery_phase,
                "shortlist_label": ui.get("shortlist_label", ""),
                "candidate_count": ui.get("candidate_count", 0),
            }
        )
    except Exception as exc:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("Stream chat failed")
        detail = str(exc)
        if "RuntimeError" in type(exc).__name__ or any(
            k in detail.lower()
            for k in ("openrouter", "api_key", "user not found", "401", "403", "placeholder")
        ):
            pass  # detail already user-friendly from llm_factory
        elif any(k in detail.lower() for k in ("connection", "timeout")):
            detail = f"{detail} — check network and OpenRouter status."
        yield _sse({"type": "error", "detail": detail})
