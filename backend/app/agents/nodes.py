"""LangGraph node implementations for all agents."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.structured import invoke_structured, invoke_text

logger = logging.getLogger(__name__)
from app.config import settings
from app.models.schemas import (
    ActiveFilters,
    ChatMessage,
    QuestionOutput,
    UserPreferences,
    VehicleCardState,
)
from app.models.state import (
    EnoughDataDecision,
    FetchDataResult,
    GraphState,
    RoutingDecision,
    SessionManagerOutput,
    ValidationResult,
)
from app.prompts.prompt_loader import load_prompt
from app.services.duckdb_service import duckdb_service
from app.services.feedback_join import feedback_join
from app.services.preference_logic import (
    apply_preferences_to_filters,
    build_next_question,
    compute_missing_dimensions,
    is_clarification_about_assistant,
    known_dimensions,
    merge_preferences,
    preferences_summary,
)
from app.services.agent_session_log import log_agent_step
from app.tools.dataframe_tools import dataframe_filter_tool, nearest_category_matcher_tool


def _format_messages(state: GraphState, limit: int = 10) -> str:
    msgs = state.session.messages[-limit:]
    return "\n".join(f"{m.role}: {m.content}" for m in msgs)


WELCOME_MESSAGE = (
    "Hi, I'm Cardeko — your vehicle research assistant. "
    "I help you explore our catalog, understand specs and owner feedback, "
    "and narrow down to a confident shortlist of 5–7 cars. "
    "Use the filters on the left or tell me: what will you mainly use the car for?"
)


def run_welcome() -> tuple[str, str]:
    """Instant welcome without blocking on LLM so the UI loads immediately."""
    return WELCOME_MESSAGE, "New session started. User has not stated preferences yet."


def run_welcome_llm() -> tuple[str, str]:
    """Optional slower LLM-personalized welcome."""
    prompt = load_prompt("welcome")
    text = invoke_text(prompt, temperature=settings.llm_temp_welcome)
    return text, "New session started. User has not stated preferences yet."


def _force_vehicle_discovery(state: GraphState) -> bool:
    """Discovery-first: only pure off-topic chit-chat goes to general_qa."""
    if state.session.last_question is not None:
        return True
    if state.session.discovery_phase not in ("welcome", "done"):
        return True
    if preferences_summary(state.session.preferences) != "none yet":
        return True
    msg = state.user_message.strip().lower()
    if msg in ("ok", "okay", "yes", "sure", "yep", "no", "nope"):
        return True
    vehicle_hints = (
        "car",
        "suv",
        "petrol",
        "diesel",
        "electric",
        "hybrid",
        "automatic",
        "manual",
        "budget",
        "family",
        "commute",
        "boot",
        "bhp",
        "fuel",
        "vehicle",
        "drive",
        "maintenance",
        "comfort",
    )
    if any(h in msg for h in vehicle_hints):
        return True
    return False


def node_general_router(state: GraphState) -> GraphState:
    if state.skip_discovery or not state.user_message.strip():
        return state
    if is_clarification_about_assistant(
        state.user_message, state.session.last_question is not None
    ):
        state.is_general_query = False
        return state
    if _force_vehicle_discovery(state):
        state.is_general_query = False
        return state
    msg = state.user_message.strip().lower()
    if msg in ("hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye"):
        state.is_general_query = True
        return state
    prompt = load_prompt(
        "general_query_router",
        narrative_summary=state.session.narrative_summary,
        messages=_format_messages(state),
        user_message=state.user_message,
    )
    try:
        decision = invoke_structured(
            prompt, RoutingDecision, fast=True, temperature=settings.llm_temp_router
        )
        state.is_general_query = decision.is_general_query
    except Exception as exc:
        logger.warning("Router LLM failed, defaulting to discovery: %s", exc)
        state.is_general_query = False
    return state


def node_general_qa(state: GraphState) -> GraphState:
    prompt = load_prompt(
        "general_qa",
        narrative_summary=state.session.narrative_summary,
        user_message=state.user_message,
    )
    state.reply = invoke_text(prompt, fast=True, temperature=0.5)
    state.session.messages.append(ChatMessage(role="user", content=state.user_message))
    state.session.messages.append(ChatMessage(role="assistant", content=state.reply))
    return state


def node_preference_extractor(state: GraphState) -> GraphState:
    prompt = load_prompt(
        "preference_extractor",
        narrative_summary=state.session.narrative_summary,
        messages=_format_messages(state),
        user_message=state.user_message,
        current_preferences=state.session.preferences.model_dump_json(),
    )
    try:
        prefs = invoke_structured(
            prompt, UserPreferences, temperature=settings.llm_temp_session_manager
        )
        state.preference_delta = prefs
    except Exception as exc:
        logger.warning("preference_extractor LLM failed: %s", exc)
        state.preference_delta = UserPreferences()
    return state


def node_session_manager(state: GraphState) -> GraphState:
    manual = state.session.ui_manual_filters
    merged_prefs = merge_preferences(
        state.session.preferences, state.preference_delta
    )
    prompt = load_prompt(
        "session_manager",
        narrative_summary=state.session.narrative_summary,
        messages=_format_messages(state),
        preferences=f"{preferences_summary(merged_prefs)} | {merged_prefs.model_dump_json()}",
        current_filters=state.session.filters.model_dump_json(),
        manual_filters=manual.model_dump_json() if manual else "none",
        candidate_count=str(state.session.candidate_count),
        user_message=state.user_message or "(manual filter update)",
    )
    try:
        out = invoke_structured(
            prompt,
            SessionManagerOutput,
            temperature=settings.llm_temp_session_manager,
        )
        out.updated_preferences = merge_preferences(merged_prefs, out.updated_preferences)
    except Exception as exc:
        logger.warning("session_manager LLM failed: %s", exc)
        out = SessionManagerOutput(
            updated_preferences=merged_prefs,
            updated_filters=state.session.filters,
            narrative_summary=state.session.narrative_summary,
            should_run_search=True,
            should_ask_question=True,
        )
    out.updated_filters = apply_preferences_to_filters(
        out.updated_preferences, out.updated_filters
    )
    if manual:
        out.updated_filters = _merge_filters(out.updated_filters, manual)

    known = known_dimensions(out.updated_preferences)
    out.missing_dimensions = compute_missing_dimensions(
        out.updated_preferences, state.session.asked_dimensions
    )

    count = state.session.candidate_count
    if 5 <= count <= 7 and {"fuel_type", "body_style", "use_case"} <= known:
        out.should_finalize_shortlist = True
        out.should_ask_question = False
    elif count > 7:
        out.should_ask_question = bool(out.missing_dimensions)
        out.should_finalize_shortlist = False

    if known and count > 0:
        out.discovery_phase = "refining" if count > 7 else out.discovery_phase
        if count <= 100:
            out.discovery_phase = "narrow"

    state.session_manager_output = out
    state.session.preferences = out.updated_preferences
    state.session.filters = out.updated_filters
    state.session.discovery_phase = out.discovery_phase
    state.session.narrative_summary = out.narrative_summary
    return state


def _merge_filters(base: ActiveFilters, override: ActiveFilters) -> ActiveFilters:
    data = base.model_dump()
    od = override.model_dump()
    for k, v in od.items():
        if v is None:
            continue
        if isinstance(v, list) and not v:
            continue
        if v not in (None, [], ""):
            data[k] = v
    return ActiveFilters.model_validate(data)


def node_vehicle_search(state: GraphState) -> GraphState:
    sm = state.session_manager_output
    if sm and not sm.should_run_search and not state.manual_filter_only:
        log_agent_step(
            state.session.session_id,
            agent="vehicle_search",
            inputs={"skipped": True, "reason": "should_run_search=false"},
            outputs={"candidate_count": state.session.candidate_count},
        )
        return state
    filters = state.session.filters
    tools_used: list[str] = ["dataframe_filter_tool"]
    tool_out = dataframe_filter_tool.invoke(
        {
            "filters_json": filters.model_dump_json(),
            "limit": settings.ui_cards_limit,
        }
    )
    import json as _json

    parsed = _json.loads(tool_out)
    rows = parsed.get("rows") or []
    sql = parsed.get("sql") or ""
    err = parsed.get("error")
    total = duckdb_service.count_with_filters(filters)
    if err or total == 0:
        tools_used.extend(["nearest_category_matcher_tool", "sql_executor_tool"])
        fetch = run_fetch_data_subgraph(
            state.session.narrative_summary + " " + state.user_message,
            filters,
        )
        rows = fetch.rows[: settings.ui_cards_limit]
        sql = fetch.sql
        err = fetch.error
        total = fetch.row_count
        filter_total = duckdb_service.count_with_filters(filters)
        if filter_total > total:
            total = filter_total
        elif total == 0 and rows:
            total = len(rows)
    state.session.candidate_rows = rows
    state.session.candidate_count = total
    state.fetch_result = FetchDataResult(sql=sql, rows=rows, row_count=total, error=err)
    log_agent_step(
        state.session.session_id,
        agent="vehicle_search",
        inputs={"filters": filters.model_dump(), "user_message": state.user_message},
        outputs={
            "candidate_count": total,
            "rows_returned": len(rows),
            "sql": sql,
            "error": err,
        },
        tools_used=tools_used,
    )
    if 5 <= total <= 7:
        state.session.discovery_phase = "shortlisted"
    elif total <= 100:
        state.session.discovery_phase = "narrow"
    elif total <= 500:
        state.session.discovery_phase = "refining"
    elif total > 0:
        state.session.discovery_phase = "broad"
    _update_ui_from_candidates(state)
    return state


def run_fetch_data_subgraph(query: str, filters: ActiveFilters) -> FetchDataResult:
    from app.tools.dataframe_tools import sql_executor_tool

    schema = json.dumps(duckdb_service.get_schema_info(), default=str)
    matched = []
    tools_used = ["dataframe_reader_tool"]
    for col in ["engineFuelType", "gearboxType", "drivetrain", "make"]:
        try:
            m = nearest_category_matcher_tool.invoke(
                {"user_phrase": query, "column": col}
            )
            matched.append(m)
            tools_used.append("nearest_category_matcher_tool")
        except Exception:
            pass
    matched_str = "\n".join(matched)
    retries = 0
    last_sql = ""
    while retries < 3:
        prompt = load_prompt(
            "sql_builder",
            schema=schema,
            query=query + " " + filters.model_dump_json(),
            matched_categories=matched_str,
        )
        sql = invoke_text(prompt, fast=True, temperature=settings.llm_temp_sql)
        sql = sql.strip().strip("`").replace("```sql", "").replace("```", "")
        last_sql = sql
        exec_out = sql_executor_tool.invoke({"sql": sql})
        import json as _json

        exec_data = _json.loads(exec_out)
        rows = exec_data.get("rows") or []
        count = int(exec_data.get("row_count") or 0)
        err = exec_data.get("error")
        tools_used.append("sql_executor_tool")
        if err:
            retries += 1
            continue
        if count == 0:
            debug_prompt = f"SQL returned 0 rows. SQL: {sql}. Intent: {query}. Regenerate."
            retries += 1
            query = debug_prompt
            continue
        val_prompt = load_prompt(
            "sql_validator",
            sql=sql,
            row_count=str(count),
            sample=json.dumps(rows[:3], default=str),
            query=query,
        )
        try:
            val = invoke_structured(
                val_prompt, ValidationResult, fast=True, temperature=settings.llm_temp_router
            )
        except Exception:
            val = ValidationResult(is_correct=True, should_debug=False)
        if val.is_correct:
            return FetchDataResult(
                sql=sql, rows=rows, row_count=count, error=None
            )
        if val.should_debug:
            retries += 1
            query = val.feedback
            continue
        return FetchDataResult(sql=sql, rows=rows, row_count=count)
    sql = duckdb_service.build_filter_sql(filters, limit=settings.ui_cards_limit)
    rows, count, err = duckdb_service.execute_readonly_sql(sql)
    total = duckdb_service.count_with_filters(filters) if rows else count
    return FetchDataResult(
        sql=last_sql or sql, rows=rows, row_count=total or count, error=err
    )


def node_message_info_analyzer(state: GraphState) -> GraphState:
    if not state.session.last_question:
        return state
    prompt = load_prompt(
        "message_info_analyzer",
        last_question=state.session.last_question.question_text,
        user_message=state.user_message,
    )
    try:
        invoke_text(prompt, fast=True, temperature=settings.llm_temp_router)
    except Exception:
        pass
    return state


def node_enough_data(state: GraphState) -> GraphState:
    sm = state.session_manager_output
    c = state.session.candidate_count
    known = known_dimensions(state.session.preferences)
    heuristic_enough = (
        5 <= c <= 7
        and "use_case" in known
        and ("body_style" in known or "family_size" in known)
        and "fuel_type" in known
    )
    if heuristic_enough:
        state.enough_data = EnoughDataDecision(
            enough_data=True, reasoning="heuristic: pool and prefs sufficient"
        )
        return state
    prompt = load_prompt(
        "enough_data",
        discovery_phase=state.session.discovery_phase,
        confidence_score=str(sm.confidence_score if sm else 0),
        candidate_count=str(c),
        missing_dimensions=json.dumps(sm.missing_dimensions if sm else []),
        narrative_summary=state.session.narrative_summary,
    )
    try:
        state.enough_data = invoke_structured(
            prompt, EnoughDataDecision, fast=True, temperature=settings.llm_temp_router
        )
    except Exception:
        state.enough_data = EnoughDataDecision(
            enough_data=5 <= c <= 7,
            reasoning="heuristic",
        )
    return state


def build_question_prompt(state: GraphState) -> str:
    """Prompt for the next discovery question (streamed in chat_stream)."""
    sm = state.session_manager_output
    prefs = state.session.preferences
    missing = (
        sm.missing_dimensions
        if sm
        else compute_missing_dimensions(prefs, state.session.asked_dimensions)
    )
    return load_prompt(
        "question_generator",
        discovery_phase=state.session.discovery_phase,
        known_preferences=preferences_summary(prefs),
        missing_dimensions=json.dumps(missing),
        asked_dimensions=json.dumps(state.session.asked_dimensions),
        candidate_count=str(state.session.candidate_count),
        last_question=(
            state.session.last_question.question_text
            if state.session.last_question
            else "none"
        ),
        user_message=state.user_message,
        narrative_summary=state.session.narrative_summary,
    )


def finalize_question_reply(state: GraphState, reply_text: str) -> GraphState:
    """Apply assistant reply after LLM (or template) question generation."""
    sm = state.session_manager_output
    prefs = state.session.preferences
    missing = (
        sm.missing_dimensions
        if sm
        else compute_missing_dimensions(prefs, state.session.asked_dimensions)
    )
    text = (reply_text or "").strip()
    if not text:
        text, dim = build_next_question(
            prefs,
            state.session.asked_dimensions,
            missing,
            state.session.candidate_count,
            state.user_message,
        )
    else:
        dim = missing[0] if missing else "priority"
    q = QuestionOutput(question_text=text, dimension_targeted=dim)
    state.question_output = q
    state.session.last_question = q
    state.session.asked_dimensions.append(q.dimension_targeted)
    state.reply = text
    state.session.messages.append(ChatMessage(role="user", content=state.user_message))
    state.session.messages.append(ChatMessage(role="assistant", content=state.reply))
    _update_ui_from_candidates(state)
    return state


def node_question_generator(state: GraphState) -> GraphState:
    sm = state.session_manager_output
    prefs = state.session.preferences
    missing = (
        sm.missing_dimensions
        if sm
        else compute_missing_dimensions(prefs, state.session.asked_dimensions)
    )
    known = known_dimensions(prefs)

    if is_clarification_about_assistant(
        state.user_message, state.session.last_question is not None
    ):
        next_text, next_dim = build_next_question(
            prefs,
            state.session.asked_dimensions,
            missing,
            state.session.candidate_count,
            state.user_message,
        )
        reply = "I was asking so we can filter the list on the left. " + next_text
        return finalize_question_reply(state, reply)

    try:
        reply = invoke_text(
            build_question_prompt(state),
            fast=False,
            temperature=settings.llm_temp_question_generator,
        )
    except Exception as exc:
        logger.warning("question_generator LLM failed: %s", exc)
        reply = ""
    return finalize_question_reply(state, reply)


def node_why_recommend(state: GraphState) -> GraphState:
    rows = state.session.candidate_rows
    if state.session.candidate_count > 7:
        rows = rows[:7]
    elif state.session.candidate_count < 5 and rows:
        rows = rows[: min(7, len(rows))]
    vehicles_payload = []
    for r in rows:
        vid = str(r.get("vehicle_id", ""))
        fb = feedback_join.get_summary(vid)
        vehicles_payload.append({**r, "feedback": fb})
    prompt = load_prompt(
        "why_recommend",
        narrative_summary=state.session.narrative_summary,
        vehicles_json=json.dumps(vehicles_payload, default=str),
    )
    try:
        raw = invoke_text(prompt, temperature=settings.llm_temp_session_manager)
        data = json.loads(
            raw[raw.find("[") : raw.rfind("]") + 1]
            if "[" in raw
            else raw[raw.find("{") : raw.rfind("}") + 1]
        )
        if isinstance(data, dict):
            data = [data]
    except Exception:
        data = []
    rec_map = {str(d.get("vehicle_id")): d for d in data if d.get("vehicle_id")}
    cards = []
    shortlist = []
    for r in rows[:7]:
        vid = str(r.get("vehicle_id", ""))
        rec = rec_map.get(vid, {})
        make = str(r.get("make", ""))
        fb = feedback_join.get_summary(vid)
        cards.append(
            VehicleCardState(
                vehicle_id=vid,
                make=make,
                model=str(r.get("model", "")),
                variant=str(r.get("variant", "")),
                image_url=f"/api/placeholders/{make.upper()}.png",
                fuel_type=str(r.get("engineFuelType") or ""),
                gearbox=str(r.get("gearboxType") or ""),
                power_bhp=_float(r.get("enginePowerBhp")),
                boot_litres=_float(r.get("bootLitres")),
                fuel_economy_l100=_float(r.get("fuelEconomyCombinedL100")),
                year_from=_float(r.get("yearFrom")),
                pros=rec.get("pros", ["Matches your stated preferences"]),
                cons=rec.get("cons", []),
                reason=rec.get("reason", "Recommended based on your criteria."),
                avg_rating=fb.get("avg_rating"),
            )
        )
        shortlist.append(vid)
    from app.services.catalog import catalog_total_count

    state.session.vehicles = cards
    state.session.shortlist_ids = shortlist
    state.session.discovery_phase = "shortlisted"
    state.session.catalog_total = catalog_total_count()
    state.session.catalog_showing = len(cards)
    return state


def _float(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def node_ui_finalize(state: GraphState) -> GraphState:
    if not state.session.vehicles and state.session.candidate_rows:
        node_why_recommend(state)
    count = len(state.session.vehicles)
    names = ", ".join(f"{v.make} {v.model}" for v in state.session.vehicles[:5])
    state.reply = (
        f"I've narrowed it down to {count} vehicles that fit what you've told me: {names}. "
        "Check the cards on the left for pros, cons, and details. Add any to compare or tell me what to adjust."
    )
    state.session.messages.append(ChatMessage(role="user", content=state.user_message))
    state.session.messages.append(ChatMessage(role="assistant", content=state.reply))
    if state.session.candidate_count <= 7:
        state.session.discovery_phase = "done"
    return state


def _update_ui_from_candidates(state: GraphState) -> None:
    from app.config import settings
    from app.services.catalog import catalog_total_count, rows_to_cards

    count = state.session.candidate_count or len(state.session.candidate_rows)
    cap = min(len(state.session.candidate_rows), settings.ui_cards_limit)
    if count <= 7:
        cap = max(cap, min(count, len(state.session.candidate_rows)))
    cap = max(cap, 1)
    cards = rows_to_cards(
        state.session.candidate_rows[:cap],
        include_feedback=cap <= 25,
    )
    state.session.vehicles = cards
    state.session.catalog_total = catalog_total_count()
    state.session.catalog_showing = len(cards)


def route_after_router(state: GraphState) -> str:
    if state.is_general_query:
        return "general_qa"
    return "discovery"


def route_after_enough_data(state: GraphState) -> str:
    sm = state.session_manager_output
    c = state.session.candidate_count
    enough = state.enough_data and state.enough_data.enough_data
    if sm and sm.should_finalize_shortlist and 5 <= c <= 7:
        return "finalize"
    if enough and 5 <= c <= 7:
        return "finalize"
    if c > 7:
        return "question"
    if sm and sm.should_ask_question and sm.missing_dimensions:
        return "question"
    if c > 0 and c < 5:
        return "question"
    if c > 0:
        return "finalize"
    return "question"
