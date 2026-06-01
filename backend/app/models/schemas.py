from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DiscoveryPhase = Literal[
    "welcome", "broad", "narrow", "refining", "shortlisted", "done"
]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QuestionOutput(BaseModel):
    question_text: str
    dimension_targeted: str = ""
    expected_answer_type: str = "open"


class UserPreferences(BaseModel):
    use_case: str | None = None
    body_style: str | None = None
    fuel_preference: str | None = None
    transmission_preference: str | None = None
    drivetrain_preference: str | None = None
    budget_notes: str | None = None
    family_size_notes: str | None = None
    must_have_features: list[str] = Field(default_factory=list)
    avoid_notes: str | None = None
    soft_notes: str | None = None


class ActiveFilters(BaseModel):
    makes: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    engine_fuel_types: list[str] = Field(default_factory=list)
    gearbox_types: list[str] = Field(default_factory=list)
    drivetrains: list[str] = Field(default_factory=list)
    year_from_min: float | None = None
    year_from_max: float | None = None
    power_bhp_min: float | None = None
    power_bhp_max: float | None = None
    boot_litres_min: float | None = None
    fuel_economy_l100_max: float | None = None


class VehicleCardState(BaseModel):
    vehicle_id: str
    make: str
    model: str
    variant: str
    image_url: str
    fuel_type: str | None = None
    gearbox: str | None = None
    power_bhp: float | None = None
    boot_litres: float | None = None
    fuel_economy_l100: float | None = None
    year_from: float | None = None
    drivetrain: str | None = None
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    reason: str = ""
    avg_rating: float | None = None


class UIState(BaseModel):
    filters: ActiveFilters = Field(default_factory=ActiveFilters)
    vehicles: list[VehicleCardState] = Field(default_factory=list)
    filter_options: "FilterOptions | None" = None
    catalog_total: int = 0
    catalog_showing: int = 0
    candidate_count: int = 0
    shortlist_label: str = ""


class FilterOptions(BaseModel):
    makes: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    engine_fuel_types: list[str] = Field(default_factory=list)
    gearbox_types: list[str] = Field(default_factory=list)
    drivetrains: list[str] = Field(default_factory=list)
    year_from_min: float = 1968
    year_from_max: float = 2025
    power_bhp_min: float = 0
    power_bhp_max: float = 1000
    boot_litres_max: float = 2000
    fuel_economy_l100_max: float = 30


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    messages: list[ChatMessage]
    ui_state: UIState
    discovery_phase: DiscoveryPhase


class SessionCreateResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]
    ui_state: UIState
    discovery_phase: DiscoveryPhase
    narrative_summary: str = ""


class SessionResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]
    ui_state: UIState
    discovery_phase: DiscoveryPhase
    narrative_summary: str
    candidate_count: int = 0


class VehicleDetail(BaseModel):
    vehicle_id: str
    make: str
    model: str
    variant: str
    specs: dict
    avg_rating: float | None = None
    review_snippets: list[str] = Field(default_factory=list)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)


class CompareVehicle(BaseModel):
    vehicle_id: str
    make: str
    model: str
    variant: str
    specs: dict
    avg_rating: float | None = None
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)


UIState.model_rebuild()
