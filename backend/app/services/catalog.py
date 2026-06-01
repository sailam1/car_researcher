"""Build vehicle card lists for the UI catalog."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.models.schemas import VehicleCardState
from app.services.duckdb_service import CARS_TABLE, duckdb_service
from app.services.feedback_join import feedback_join


def _float(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def row_to_card(
    row: dict[str, Any], *, include_feedback: bool = True
) -> VehicleCardState:
    vid = str(row.get("vehicle_id", ""))
    make = str(row.get("make", ""))
    fb = feedback_join.get_summary(vid) if include_feedback else {}
    model = str(row.get("model") or "").strip()
    if model.endswith(".0") and model[:-2].isdigit():
        model = model[:-2]
    return VehicleCardState(
        vehicle_id=vid,
        make=make,
        model=model,
        variant=str(row.get("variant") or "").strip(),
        image_url=f"/api/placeholders/{make.upper().replace(' ', '_')}.png",
        fuel_type=str(row.get("engineFuelType") or "") or None,
        gearbox=str(row.get("gearboxType") or "") or None,
        power_bhp=_float(row.get("enginePowerBhp")),
        boot_litres=_float(row.get("bootLitres")),
        fuel_economy_l100=_float(row.get("fuelEconomyCombinedL100")),
        year_from=_float(row.get("yearFrom")),
        drivetrain=str(row.get("drivetrain") or "") or None,
        avg_rating=fb.get("avg_rating"),
    )


def rows_to_cards(
    rows: list[dict[str, Any]], *, include_feedback: bool = True
) -> list[VehicleCardState]:
    return [row_to_card(r, include_feedback=include_feedback) for r in rows]


def catalog_total_count() -> int:
    from app.services.preference_logic import safe_count_query

    return safe_count_query()


def fetch_catalog_rows(limit: int | None = None, offset: int = 0) -> list[dict]:
    lim = limit if limit is not None else settings.ui_cards_limit
    sql = (
        f"SELECT vehicle_id, make, model, variant, yearFrom, engineFuelType, "
        f"gearboxType, enginePowerBhp, bootLitres, fuelEconomyCombinedL100, drivetrain "
        f"FROM {CARS_TABLE} ORDER BY yearFrom DESC, make, model "
        f"LIMIT {int(lim)} OFFSET {int(offset)}"
    )
    rows, _, err = duckdb_service.execute_readonly_sql(sql)
    if err:
        return []
    return rows


def build_initial_catalog() -> tuple[list[VehicleCardState], int, int]:
    """Return (cards, showing_count, total_count)."""
    total = catalog_total_count()
    limit = settings.ui_cards_limit
    rows = fetch_catalog_rows(limit=limit, offset=0)
    return rows_to_cards(rows, include_feedback=False), len(rows), total


def build_cards_from_filters(limit: int | None = None) -> list[VehicleCardState]:
    from app.models.schemas import ActiveFilters

    filters = ActiveFilters()
    sql = duckdb_service.build_filter_sql(filters, limit=limit or settings.initial_catalog_limit)
    rows, _, _ = duckdb_service.execute_readonly_sql(sql)
    return rows_to_cards(rows)
