"""Join customer feedback to vehicle variants."""

from __future__ import annotations

import re
from collections import defaultdict

import pandas as pd

from app.config import settings
from app.services.duckdb_service import duckdb_service


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


class FeedbackJoinService:
    def __init__(self) -> None:
        self._by_vehicle: dict[str, dict] = {}
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        cardata = settings.cardata_path
        feedback_csv = cardata / "feedbacks.csv"
        if not feedback_csv.exists():
            self._initialized = True
            return

        feedbacks = pd.read_csv(
            feedback_csv, engine="python", on_bad_lines="skip"
        )
        vehicles_df = duckdb_service.conn.execute(
            "SELECT vehicle_id, make, model, yearFrom, engineFuelType, engineDisplacement FROM cars_details"
        ).fetchdf()

        make_model_index: dict[str, list[dict]] = defaultdict(list)
        for _, v in vehicles_df.iterrows():
            key = f"{_normalize(str(v['make']))}|{_normalize(str(v['model']))}"
            make_model_index[key].append(v.to_dict())

        agg: dict[str, list] = defaultdict(lambda: {"ratings": [], "snippets": []})

        for _, fb in feedbacks.iterrows():
            title = str(fb.get("Vehicle_Title", ""))
            rating = fb.get("Rating")
            review = str(fb.get("Review", ""))[:300]
            matched_id = self._match_title(title, make_model_index)
            if not matched_id:
                continue
            if pd.notna(rating):
                try:
                    agg[matched_id]["ratings"].append(float(rating))
                except (TypeError, ValueError):
                    pass
            if review.strip():
                if len(agg[matched_id]["snippets"]) < 5:
                    agg[matched_id]["snippets"].append(review.strip())

        for vid, data in agg.items():
            ratings = data["ratings"]
            self._by_vehicle[vid] = {
                "avg_rating": sum(ratings) / len(ratings) if ratings else None,
                "review_count": len(ratings),
                "snippets": data["snippets"],
            }
        self._initialized = True

    def _match_title(
        self, title: str, index: dict[str, list[dict]]
    ) -> str | None:
        year_match = re.search(r"\b(19|20)\d{2}\b", title)
        year = int(year_match.group()) if year_match else None
        title_lower = title.lower()
        tokens = set(re.findall(r"[a-z0-9]+", title_lower))
        best_id = None
        best_score = 0
        for key, vehicles in index.items():
            make, model = key.split("|", 1)
            if not make or make not in title_lower:
                continue
            model_match = model in title_lower or any(
                t in model for t in tokens if len(t) > 2
            )
            if not model_match:
                continue
            for v in vehicles:
                score = 3
                if year and v.get("yearFrom"):
                    try:
                        ydiff = abs(float(v["yearFrom"]) - year)
                        if ydiff <= 1:
                            score += 3
                        elif ydiff <= 3:
                            score += 1
                    except (TypeError, ValueError):
                        pass
                fuel = str(v.get("engineFuelType", "")).lower()
                if fuel and fuel in title_lower:
                    score += 1
                if score > best_score:
                    best_score = score
                    best_id = str(v["vehicle_id"])
        return best_id

    def get_summary(self, vehicle_id: str) -> dict:
        return self._by_vehicle.get(
            vehicle_id,
            {"avg_rating": None, "review_count": 0, "snippets": []},
        )

    def summarize_for_prompt(self, vehicle_id: str) -> str:
        s = self.get_summary(vehicle_id)
        parts = []
        if s.get("avg_rating"):
            parts.append(f"Avg rating: {s['avg_rating']:.1f}/5 ({s['review_count']} reviews)")
        for snip in s.get("snippets", [])[:3]:
            parts.append(f"- {snip[:200]}")
        return "\n".join(parts) if parts else "No customer reviews matched."


feedback_join = FeedbackJoinService()
