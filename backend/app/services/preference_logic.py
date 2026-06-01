"""Deterministic preference merge, filter mapping, and question planning."""

from __future__ import annotations

from typing import Any

from app.models.schemas import ActiveFilters, UserPreferences
from app.services.duckdb_service import CARS_TABLE, duckdb_service

# Order we ask about — only if not already known or asked twice
QUESTION_PRIORITY = [
    "fuel_type",
    "budget",
    "transmission",
    "year_range",
    "drivetrain",
    "boot_space",
]

QUESTION_TEMPLATES: dict[str, str] = {
    "fuel_type": (
        "Given you want a {body_style} for {use_case}, do you prefer petrol, diesel, "
        "hybrid, or are you open to any fuel type?"
    ),
    "budget": (
        "Roughly what budget range are you considering (e.g. under ₹15L, ₹15–25L, or flexible)?"
    ),
    "transmission": "Do you prefer automatic or manual transmission?",
    "year_range": "Are you looking at newer models (e.g. 2018+) or open to older ones if the value is good?",
    "drivetrain": "Is front-wheel drive fine, or do you need AWD/4WD for your trips?",
    "boot_space": "How important is boot space — moderate is OK, or do you need a large boot for family gear?",
    "body_style": "Besides SUVs, would you also consider a large estate/wagon for comfort on long trips?",
    "use_case": "What will you mainly use the car for — daily commute, family, long trips, or a mix?",
}


def merge_preferences(
    base: UserPreferences, delta: UserPreferences | None
) -> UserPreferences:
    if delta is None:
        return base
    data = base.model_dump()
    for key, val in delta.model_dump().items():
        if val is None:
            continue
        if isinstance(val, list):
            if val:
                existing = data.get(key) or []
                merged = list(dict.fromkeys([*existing, *val]))
                data[key] = merged
            continue
        if isinstance(val, str) and val.strip():
            data[key] = val
    return UserPreferences.model_validate(data)


def preferences_summary(prefs: UserPreferences) -> str:
    parts: list[str] = []
    if prefs.use_case:
        parts.append(f"use: {prefs.use_case}")
    if prefs.body_style:
        parts.append(f"body: {prefs.body_style}")
    if prefs.fuel_preference:
        parts.append(f"fuel: {prefs.fuel_preference}")
    if prefs.transmission_preference:
        parts.append(f"gearbox: {prefs.transmission_preference}")
    if prefs.drivetrain_preference:
        parts.append(f"drivetrain: {prefs.drivetrain_preference}")
    if prefs.family_size_notes:
        parts.append(f"family: {prefs.family_size_notes}")
    if prefs.must_have_features:
        parts.append("must-have: " + ", ".join(prefs.must_have_features))
    if prefs.soft_notes:
        parts.append(f"notes: {prefs.soft_notes}")
    if prefs.budget_notes:
        parts.append(f"budget: {prefs.budget_notes}")
    return "; ".join(parts) if parts else "none yet"


def known_dimensions(prefs: UserPreferences) -> set[str]:
    known: set[str] = set()
    blob = preferences_summary(prefs).lower()
    if prefs.use_case:
        known.add("use_case")
    if prefs.body_style or any(
        w in blob for w in ("suv", "sedan", "hatch", "wagon", "estate", "crossover", "mpv")
    ):
        known.add("body_style")
    if prefs.fuel_preference or any(
        w in blob for w in ("petrol", "diesel", "electric", "hybrid")
    ):
        known.add("fuel_type")
    if prefs.transmission_preference:
        known.add("transmission")
    if prefs.drivetrain_preference:
        known.add("drivetrain")
    if prefs.budget_notes or "budget" in blob or "lakh" in blob or "$" in blob:
        known.add("budget")
    if prefs.family_size_notes or "family" in blob:
        known.add("family_size")
    if any(w in blob for w in ("stylish", "comfort", "comfortable", "style")):
        known.add("comfort_style")
    return known


def compute_missing_dimensions(
    prefs: UserPreferences, asked_dimensions: list[str]
) -> list[str]:
    known = known_dimensions(prefs)
    asked_counts: dict[str, int] = {}
    for d in asked_dimensions:
        asked_counts[d] = asked_counts.get(d, 0) + 1

    missing: list[str] = []
    for dim in QUESTION_PRIORITY:
        if dim in known:
            continue
        if asked_counts.get(dim, 0) >= 2:
            continue
        missing.append(dim)

    if "body_style" not in known and asked_counts.get("body_style", 0) < 2:
        if "body_style" not in missing:
            missing.append("body_style")
    return missing


def _models_matching_keywords(keywords: list[str], limit: int = 80) -> list[str]:
    if not keywords:
        return []
    clauses = " OR ".join(
        f"LOWER(model) LIKE '%{kw.replace(chr(39), '')}%'" for kw in keywords
    )
    sql = (
        f"SELECT DISTINCT model FROM {CARS_TABLE} WHERE ({clauses}) "
        f"ORDER BY model LIMIT {limit}"
    )
    rows, _, err = duckdb_service.execute_readonly_sql(sql)
    if err:
        return []
    return [str(r["model"]) for r in rows if r.get("model")]


def apply_preferences_to_filters(
    prefs: UserPreferences, filters: ActiveFilters
) -> ActiveFilters:
    data = filters.model_dump()
    blob = " ".join(
        filter(
            None,
            [
                prefs.use_case or "",
                prefs.body_style or "",
                prefs.soft_notes or "",
                prefs.family_size_notes or "",
                " ".join(prefs.must_have_features),
            ],
        )
    ).lower()

    fuel_map = {
        "petrol": "PETROL",
        "gasoline": "PETROL",
        "diesel": "DIESEL",
        "electric": "ELECTRIC",
        "hybrid": "HYBRID",
    }
    fuels: list[str] = list(data.get("engine_fuel_types") or [])
    for token, col_val in fuel_map.items():
        if token in blob and col_val not in fuels:
            fuels.append(col_val)
    if prefs.fuel_preference:
        for token, col_val in fuel_map.items():
            if token in prefs.fuel_preference.lower() and col_val not in fuels:
                fuels.append(col_val)
    if fuels:
        data["engine_fuel_types"] = fuels

    if "automatic" in blob or (prefs.transmission_preference or "").lower().find("auto") >= 0:
        data["gearbox_types"] = list(
            dict.fromkeys([*(data.get("gearbox_types") or []), "AUTOMATIC"])
        )
    if "manual" in blob or (prefs.transmission_preference or "").lower().find("manual") >= 0:
        data["gearbox_types"] = list(
            dict.fromkeys([*(data.get("gearbox_types") or []), "MANUAL"])
        )

    if any(w in blob for w in ("awd", "4wd", "all wheel", "all-wheel")):
        data["drivetrains"] = list(
            dict.fromkeys([*(data.get("drivetrains") or []), "AWD", "4WD"])
        )

    body_keywords: list[str] = []
    if any(w in blob for w in ("suv", "crossover", "4x4")):
        body_keywords.extend(["suv", "crossover", "4x4"])
    if any(w in blob for w in ("family", "kids", "children")):
        data["boot_litres_min"] = data.get("boot_litres_min") or 400
    if "suv" in blob or (prefs.body_style or "").lower().find("suv") >= 0:
        models = _models_matching_keywords(["suv", "crossover", "4x4"])
        if not models:
            models = _models_matching_keywords(["sport", "tiguan", "qashqai", "x3", "x5"])
        if models:
            data["models"] = list(dict.fromkeys([*(data.get("models") or []), *models]))

    if any(w in blob for w in ("commute", "city", "daily")) and not data.get("fuel_economy_l100_max"):
        data["fuel_economy_l100_max"] = data.get("fuel_economy_l100_max") or 12

    return ActiveFilters.model_validate(data)


def build_next_question(
    prefs: UserPreferences,
    asked_dimensions: list[str],
    missing_dimensions: list[str],
    candidate_count: int,
    last_user_message: str,
) -> tuple[str, str]:
    """Return (question_text, dimension_targeted)."""
    if 5 <= candidate_count <= 7:
        return (
            f"I found {candidate_count} vehicles that match so far ({preferences_summary(prefs)}). "
            "Does this shortlist look right, or should we adjust fuel type, budget, or brand?",
            "shortlist_confirm",
        )

    known = known_dimensions(prefs)
    missing = missing_dimensions or compute_missing_dimensions(prefs, asked_dimensions)

    for dim in missing:
        if dim in QUESTION_TEMPLATES:
            tpl = QUESTION_TEMPLATES[dim]
            body = prefs.body_style or "vehicle"
            use = prefs.use_case or "your needs"
            text = tpl.format(body_style=body, use_case=use)
            ack = _acknowledge_user(last_user_message, prefs)
            return (f"{ack}{text}", dim)

    if "use_case" not in known:
        return (QUESTION_TEMPLATES["use_case"], "use_case")

    return (
        "What is the one thing we should prioritize next to narrow your shortlist — "
        "fuel type, budget, or transmission?",
        "priority",
    )


def _acknowledge_user(message: str, prefs: UserPreferences) -> str:
    msg = message.strip().lower()
    if len(msg) < 2 or msg in ("ok", "okay", "yes", "sure", "fine"):
        summary = preferences_summary(prefs)
        if summary != "none yet":
            return f"Got it — so far I have: {summary}. "
        return ""
    if msg.startswith("what do you mean") or msg.startswith("what does that mean"):
        return (
            "I was trying to learn one preference we do not have yet (e.g. fuel type or budget) "
            "so I can filter the catalog on the left. "
        )
    return f"Thanks — noted. "


def is_clarification_about_assistant(user_message: str, has_last_question: bool) -> bool:
    msg = user_message.strip().lower()
    if not has_last_question:
        return False
    return any(
        p in msg
        for p in (
            "what do you mean",
            "what does that mean",
            "don't understand",
            "do not understand",
            "confused",
            "clarify",
            "explain that",
        )
    )


def safe_count_query() -> int:
    """Robust vehicle count (avoids mis-parsed COUNT on bad schemas)."""
    try:
        row = duckdb_service.conn.execute(
            f"SELECT COUNT(vehicle_id) AS n FROM {CARS_TABLE}"
        ).fetchdf()
        if row.empty:
            return 0
        val = row.iloc[0]["n"]
        return int(val)
    except Exception:
        try:
            row = duckdb_service.conn.execute(
                f"SELECT COUNT(*) AS n FROM {CARS_TABLE}"
            ).fetchdf()
            if row.empty:
                return 0
            val = row.iloc[0]["n"]
            if isinstance(val, (int, float)):
                return int(val)
            if isinstance(val, str) and val.isdigit():
                return int(val)
        except Exception:
            pass
    return 0
