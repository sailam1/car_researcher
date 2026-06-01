from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.schemas import (
    ActiveFilters,
    ChatMessage,
    DiscoveryPhase,
    QuestionOutput,
    UIState,
    UserPreferences,
    VehicleCardState,
)


class RoutingDecision(BaseModel):
    is_general_query: bool
    reasoning: str = ""


class FetchDataResult(BaseModel):
    sql: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    error: str | None = None


class ValidationResult(BaseModel):
    is_correct: bool
    should_debug: bool
    feedback: str = ""


class EnoughDataDecision(BaseModel):
    enough_data: bool
    reasoning: str = ""


class SessionManagerOutput(BaseModel):
    updated_preferences: UserPreferences = Field(default_factory=UserPreferences)
    updated_filters: ActiveFilters = Field(default_factory=ActiveFilters)
    discovery_phase: DiscoveryPhase = "broad"
    confidence_score: float = 0.0
    missing_dimensions: list[str] = Field(default_factory=list)
    narrative_summary: str = ""
    merge_notes: str = ""
    should_run_search: bool = True
    should_ask_question: bool = True
    should_finalize_shortlist: bool = False


class SessionState(BaseModel):
    session_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    filters: ActiveFilters = Field(default_factory=ActiveFilters)
    ui_manual_filters: ActiveFilters | None = None
    shortlist_ids: list[str] = Field(default_factory=list)
    vehicles: list[VehicleCardState] = Field(default_factory=list)
    discovery_phase: DiscoveryPhase = "welcome"
    narrative_summary: str = ""
    last_question: QuestionOutput | None = None
    asked_dimensions: list[str] = Field(default_factory=list)
    candidate_count: int = 0
    candidate_rows: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    catalog_total: int = 0
    catalog_showing: int = 0

    def to_ui_state(self, filter_options: Any = None) -> UIState:
        total = self.catalog_total
        matched = self.candidate_count
        shown = self.catalog_showing or len(self.vehicles)
        label = ""
        if total > 0:
            label = f"Shortlisted {matched:,} out of {total:,}"
            if shown > 0 and shown < matched:
                label += f" — showing top {shown:,} matches"
        return UIState(
            filters=self.filters,
            vehicles=self.vehicles,
            filter_options=filter_options,
            catalog_total=total,
            catalog_showing=shown,
            candidate_count=matched,
            shortlist_label=label,
        )


class GraphState(BaseModel):
    """LangGraph state passed between nodes."""

    session: SessionState
    user_message: str = ""
    reply: str = ""
    is_general_query: bool = False
    skip_discovery: bool = False
    manual_filter_only: bool = False
    preference_delta: UserPreferences | None = None
    session_manager_output: SessionManagerOutput | None = None
    enough_data: EnoughDataDecision | None = None
    question_output: QuestionOutput | None = None
    fetch_result: FetchDataResult | None = None
