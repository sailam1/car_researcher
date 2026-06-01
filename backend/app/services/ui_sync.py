"""Build UI state payloads for API and SSE."""

from __future__ import annotations

from app.models.state import GraphState
from app.services.catalog import catalog_total_count
from app.services.duckdb_service import duckdb_service


def refresh_session_vehicles(state: GraphState) -> None:
    """Populate vehicle cards from latest search results."""
    from app.agents.nodes import _update_ui_from_candidates

    if state.session.candidate_rows:
        _update_ui_from_candidates(state)


def build_ui_payload(state: GraphState) -> dict:
    """Full ui_state dict including shortlist counts for the left panel."""
    refresh_session_vehicles(state)
    total = state.session.catalog_total or catalog_total_count()
    matched = int(state.session.candidate_count or 0)
    shown = len(state.session.vehicles)
    state.session.catalog_total = total
    state.session.catalog_showing = shown

    label = f"Shortlisted {matched:,} out of {total:,}"
    if shown > 0 and shown < matched:
        label += f" — showing top {shown:,} matches"

    opts = duckdb_service.get_filter_options(state.session.filters)
    payload = state.session.to_ui_state(opts).model_dump(mode="json")
    payload["candidate_count"] = matched
    payload["shortlist_label"] = label
    return payload
