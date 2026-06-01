"""LangChain tools for data access."""

from __future__ import annotations

import json

import numpy as np
from langchain_core.tools import tool

from app.models.schemas import ActiveFilters
from app.services.duckdb_service import duckdb_service
from app.services.feedback_join import feedback_join


@tool
def dataframe_reader_tool() -> str:
    """Return schema, sample rows, and distinct values for cars_details."""
    info = duckdb_service.get_schema_info()
    return json.dumps(info, default=str)


@tool
def dataframe_filter_tool(filters_json: str, limit: int = 50) -> str:
    """Apply ActiveFilters JSON to cars_details and return matching rows."""
    data = json.loads(filters_json)
    filters = ActiveFilters.model_validate(data)
    sql = duckdb_service.build_filter_sql(filters, limit=limit)
    rows, count, err = duckdb_service.execute_readonly_sql(sql)
    return json.dumps({"rows": rows, "row_count": count, "error": err, "sql": sql})


@tool
def nearest_category_matcher_tool(
    user_phrase: str, column: str = "engineFuelType"
) -> str:
    """Match user phrase to nearest distinct value in a cars_details column using embeddings."""
    from app.agents.llm_factory import embed_query

    schema = duckdb_service.get_schema_info()
    distincts = schema.get("distinct_values", {}).get(column, [])
    if not distincts:
        distincts = duckdb_service._distinct_list(column)
    if not distincts:
        return json.dumps({"column": column, "value": None, "score": 0})

    try:
        phrase_vec = embed_query(user_phrase)
        best_val = None
        best_score = -1.0
        for val in distincts[:30]:
            val_vec = embed_query(str(val))
            score = float(np.dot(phrase_vec, val_vec) / (
                np.linalg.norm(phrase_vec) * np.linalg.norm(val_vec) + 1e-9
            ))
            if score > best_score:
                best_score = score
                best_val = val
        return json.dumps(
            {"column": column, "value": best_val, "score": best_score}
        )
    except Exception:
        phrase_l = user_phrase.lower()
        for val in distincts:
            if str(val).lower() in phrase_l or phrase_l in str(val).lower():
                return json.dumps({"column": column, "value": val, "score": 0.8})
        return json.dumps({"column": column, "value": distincts[0], "score": 0.5})


@tool
def sql_executor_tool(sql: str) -> str:
    """Execute read-only SELECT on DuckDB cars_details / feedbacks."""
    rows, count, err = duckdb_service.execute_readonly_sql(sql)
    return json.dumps({"rows": rows, "row_count": count, "error": err})


@tool
def feedback_summarizer_tool(vehicle_ids_json: str) -> str:
    """Summarize customer feedback for a list of vehicle_ids (JSON array)."""
    ids = json.loads(vehicle_ids_json)
    result = {}
    for vid in ids:
        result[vid] = feedback_join.get_summary(vid)
    return json.dumps(result, default=str)
