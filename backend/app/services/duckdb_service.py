"""DuckDB data layer: ingest CSVs and run queries."""

from __future__ import annotations

import hashlib
import logging
import math
import re
import time
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

from app.config import settings
from app.models.schemas import ActiveFilters, FilterOptions

CARS_TABLE = "cars_details"
FEEDBACK_TABLE = "feedbacks"

def _safe_float(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


ALLOWED_COLUMNS = {
    "vehicle_id",
    "make",
    "model",
    "variant",
    "yearFrom",
    "engineDisplacement",
    "engineCylinders",
    "engineFuelType",
    "enginePowerBhp",
    "enginePowerKw",
    "engineTorqueNm",
    "gearboxType",
    "gears",
    "drivetrain",
    "acceleration0100",
    "topSpeedKph",
    "fuelEconomyCombinedL100",
    "fuelEconomyCombinedMpg",
    "fuelTankLitres",
    "lengthMm",
    "widthMm",
    "heightMm",
    "wheelbaseMm",
    "weightKg",
    "bootLitres",
}


class DuckDBService:
    def __init__(self) -> None:
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._read_only: bool = False
        self.storage_mode: str = "uninitialized"

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            raise RuntimeError("DuckDB not initialized")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        self._read_only = False

    def initialize(self) -> None:
        if self._conn is not None:
            return

        cardata = settings.cardata_path
        cars_csv = cardata / "cars_details.csv"
        feedback_csv = cardata / "feedbacks.csv"

        if not cars_csv.exists():
            raise FileNotFoundError(f"Missing {cars_csv}")

        if settings.duckdb_in_memory:
            self._open_memory_and_load(cars_csv, feedback_csv)
            return

        db_path = settings.duckdb_file
        db_path.parent.mkdir(parents=True, exist_ok=True)

        if db_path.exists():
            if self._try_open_file_db(
                db_path,
                read_only=True,
                cars_csv=cars_csv,
                feedback_csv=feedback_csv,
            ):
                return

        try:
            self._conn = self._connect_file_with_retry(db_path, read_only=False)
            self._read_only = False
            self.storage_mode = f"file:read_write:{db_path.name}"
        except duckdb.IOException as exc:
            if self._fallback_to_memory(exc, db_path, cars_csv, feedback_csv):
                return
            raise

        if self._table_exists(CARS_TABLE):
            return

        self._ingest_csv(cars_csv, feedback_csv)

    def _connect_file_with_retry(
        self, db_path: Path, *, read_only: bool, attempts: int = 4, delay_s: float = 0.4
    ) -> duckdb.DuckDBPyConnection:
        """Retry file open — uvicorn --reload can hold the file briefly after restart."""
        last_exc: duckdb.IOException | None = None
        for attempt in range(attempts):
            try:
                return duckdb.connect(str(db_path), read_only=read_only)
            except duckdb.IOException as exc:
                last_exc = exc
                if attempt < attempts - 1:
                    time.sleep(delay_s)
        assert last_exc is not None
        raise last_exc

    def _fallback_to_memory(
        self,
        exc: Exception,
        db_path: Path,
        cars_csv: Path,
        feedback_csv: Path,
    ) -> bool:
        if not settings.duckdb_fallback_memory:
            return False
        logger.warning(
            "DuckDB file %s is not available (%s). Using in-memory catalog instead. "
            "This is normal after uvicorn --reload or a crashed server; any PID in the "
            "message may already be gone. Set DUCKDB_IN_MEMORY=true to skip file mode.",
            db_path.name,
            _short_duckdb_error(exc),
        )
        self._open_memory_and_load(cars_csv, feedback_csv)
        return True

    def _try_open_file_db(
        self,
        db_path: Path,
        *,
        read_only: bool,
        cars_csv: Path,
        feedback_csv: Path,
    ) -> bool:
        try:
            self._conn = self._connect_file_with_retry(db_path, read_only=read_only)
            self._read_only = read_only
            if self._table_exists(CARS_TABLE):
                mode = "read_only" if read_only else "read_write"
                self.storage_mode = f"file:{mode}:{db_path.name}"
                logger.info("DuckDB ready: %s", self.storage_mode)
                return True
            self.close()
            return False
        except duckdb.IOException as exc:
            if self._fallback_to_memory(exc, db_path, cars_csv, feedback_csv):
                return True
            raise RuntimeError(
                f"Cannot open {db_path}. Set DUCKDB_IN_MEMORY=true in backend/.env. "
                f"Original error: {exc}"
            ) from exc

    def _open_memory_and_load(
        self, cars_csv: Path, feedback_csv: Path
    ) -> None:
        self._conn = duckdb.connect(":memory:")
        self._read_only = False
        self.storage_mode = "memory"
        logger.info("DuckDB ready: in-memory (loaded from CSV)")
        self._ingest_csv(cars_csv, feedback_csv)

    def _ingest_csv(self, cars_csv: Path, feedback_csv: Path) -> None:
        cars = pd.read_csv(cars_csv)
        for col in ("make", "model", "variant", "engineFuelType", "gearboxType", "drivetrain"):
            if col in cars.columns:
                cars[col] = (
                    cars[col]
                    .astype(str)
                    .replace({"nan": "", "None": "", "<NA>": ""})
                    .str.strip()
                )
        cars["vehicle_id"] = cars.apply(self._make_vehicle_id, axis=1)
        self.conn.execute(f"CREATE TABLE {CARS_TABLE} AS SELECT * FROM cars")
        self.conn.execute(f"CREATE INDEX idx_cars_make ON {CARS_TABLE}(make)")
        self.conn.execute(
            f"CREATE INDEX idx_cars_fuel ON {CARS_TABLE}(engineFuelType)"
        )

        if feedback_csv.exists():
            try:
                feedbacks = pd.read_csv(
                    feedback_csv,
                    engine="python",
                    on_bad_lines="skip",
                )
                self.conn.execute(
                    f"CREATE TABLE {FEEDBACK_TABLE} AS SELECT * FROM feedbacks"
                )
            except Exception:
                pass

    def _table_exists(self, name: str) -> bool:
        rows = self.conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [name],
        ).fetchone()
        return bool(rows and rows[0] > 0)

    @staticmethod
    def _make_vehicle_id(row: pd.Series) -> str:
        key = "|".join(
            str(row.get(c, ""))
            for c in ["make", "model", "variant", "yearFrom", "engineFuelType"]
        )
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def get_schema_info(self) -> dict[str, Any]:
        cols = self.conn.execute(f"DESCRIBE {CARS_TABLE}").fetchdf()
        sample = self.conn.execute(
            f"SELECT * FROM {CARS_TABLE} LIMIT 3"
        ).fetchdf()
        distincts: dict[str, list] = {}
        for col in ["make", "engineFuelType", "gearboxType", "drivetrain"]:
            try:
                vals = self.conn.execute(
                    f"SELECT DISTINCT {col} FROM {CARS_TABLE} "
                    f"WHERE {col} IS NOT NULL ORDER BY {col} LIMIT 50"
                ).fetchall()
                distincts[col] = [v[0] for v in vals]
            except Exception:
                distincts[col] = []
        return {
            "columns": cols.to_dict(orient="records"),
            "sample_rows": sample.to_dict(orient="records"),
            "distinct_values": distincts,
        }

    def get_filter_options(self, filters: ActiveFilters | None = None) -> FilterOptions:
        makes = self._distinct_list("make")
        model_sql = (
            f"SELECT DISTINCT CAST(model AS VARCHAR) AS model FROM {CARS_TABLE} "
            f"WHERE model IS NOT NULL AND TRIM(CAST(model AS VARCHAR)) != ''"
        )
        params: list[Any] = []
        if filters and filters.makes:
            placeholders = ",".join("?" * len(filters.makes))
            model_sql += f" AND make IN ({placeholders})"
            params.extend(filters.makes)
        models = self._rows_to_str_list(
            self.conn.execute(model_sql + " ORDER BY model LIMIT 200", params).fetchall()
        )
        year_min, year_max = self._aggregate_pair(
            f"SELECT MIN(yearFrom), MAX(yearFrom) FROM {CARS_TABLE}",
            default=(1968.0, 2025.0),
        )
        power_min, power_max = self._aggregate_pair(
            f"SELECT MIN(enginePowerBhp), MAX(enginePowerBhp) FROM {CARS_TABLE}",
            default=(0.0, 1000.0),
        )
        boot_max = self._aggregate_scalar(
            f"SELECT MAX(bootLitres) FROM {CARS_TABLE}",
            default=2000.0,
        )
        return FilterOptions(
            makes=makes[:100],
            models=models,
            engine_fuel_types=self._distinct_list("engineFuelType"),
            gearbox_types=self._distinct_list("gearboxType"),
            drivetrains=self._distinct_list("drivetrain"),
            year_from_min=year_min,
            year_from_max=year_max,
            power_bhp_min=power_min,
            power_bhp_max=power_max,
            boot_litres_max=boot_max,
            fuel_economy_l100_max=30,
        )

    def _aggregate_pair(
        self, sql: str, *, default: tuple[float, float]
    ) -> tuple[float, float]:
        row = self._fetchone_safe(sql)
        if row is None:
            return default
        a = _safe_float(row[0] if len(row) > 0 else None, default[0])
        b = _safe_float(row[1] if len(row) > 1 else None, default[1])
        return a, b

    def _aggregate_scalar(self, sql: str, *, default: float) -> float:
        row = self._fetchone_safe(sql)
        if row is None or not row:
            return default
        return _safe_float(row[0], default)

    def _fetchone_safe(self, sql: str) -> tuple | None:
        try:
            if not self._table_exists(CARS_TABLE):
                return None
            return self.conn.execute(sql).fetchone()
        except Exception as exc:
            logger.warning("DuckDB aggregate query failed: %s — %s", sql[:80], exc)
            return None

    @staticmethod
    def _rows_to_str_list(rows: list[tuple]) -> list[str]:
        out: list[str] = []
        for r in rows:
            if not r or r[0] is None:
                continue
            s = str(r[0]).strip()
            if not s or s.lower() in ("nan", "none"):
                continue
            if s.endswith(".0") and s[:-2].isdigit():
                continue
            out.append(s)
        return out

    def _distinct_list(self, column: str, limit: int = 50) -> list[str]:
        rows = self.conn.execute(
            f"SELECT DISTINCT CAST({column} AS VARCHAR) AS v FROM {CARS_TABLE} "
            f"WHERE {column} IS NOT NULL AND TRIM(CAST({column} AS VARCHAR)) != '' "
            f"ORDER BY v LIMIT {limit}"
        ).fetchall()
        return self._rows_to_str_list(rows)

    def _build_where_clause(self, filters: ActiveFilters) -> str:
        clauses = ["1=1"]
        if filters.makes:
            vals = ",".join(f"'{m.replace(chr(39), '')}'" for m in filters.makes)
            clauses.append(f"make IN ({vals})")
        if filters.models:
            vals = ",".join(f"'{m.replace(chr(39), '')}'" for m in filters.models)
            clauses.append(f"CAST(model AS VARCHAR) IN ({vals})")
        if filters.engine_fuel_types:
            vals = ",".join(f"'{v}'" for v in filters.engine_fuel_types)
            clauses.append(f"engineFuelType IN ({vals})")
        if filters.gearbox_types:
            vals = ",".join(f"'{v}'" for v in filters.gearbox_types)
            clauses.append(f"gearboxType IN ({vals})")
        if filters.drivetrains:
            vals = ",".join(f"'{v}'" for v in filters.drivetrains)
            clauses.append(f"drivetrain IN ({vals})")
        if filters.year_from_min is not None:
            clauses.append(f"yearFrom >= {filters.year_from_min}")
        if filters.year_from_max is not None:
            clauses.append(f"yearFrom <= {filters.year_from_max}")
        if filters.power_bhp_min is not None:
            clauses.append(f"enginePowerBhp >= {filters.power_bhp_min}")
        if filters.power_bhp_max is not None:
            clauses.append(f"enginePowerBhp <= {filters.power_bhp_max}")
        if filters.boot_litres_min is not None:
            clauses.append(f"bootLitres >= {filters.boot_litres_min}")
        if filters.fuel_economy_l100_max is not None:
            clauses.append(
                f"(fuelEconomyCombinedL100 IS NULL OR fuelEconomyCombinedL100 <= {filters.fuel_economy_l100_max})"
            )
        return " AND ".join(clauses)

    _CARD_COLUMNS = (
        "vehicle_id, make, model, variant, yearFrom, engineFuelType, "
        "gearboxType, enginePowerBhp, bootLitres, fuelEconomyCombinedL100, drivetrain"
    )

    def build_filter_sql(self, filters: ActiveFilters, limit: int = 50) -> str:
        where = self._build_where_clause(filters)
        return (
            f"SELECT {self._CARD_COLUMNS} "
            f"FROM {CARS_TABLE} WHERE {where} ORDER BY yearFrom DESC LIMIT {int(limit)}"
        )

    def build_count_sql(self, filters: ActiveFilters) -> str:
        where = self._build_where_clause(filters)
        return f"SELECT COUNT(*) FROM {CARS_TABLE} WHERE {where}"

    def execute_readonly_sql(self, sql: str) -> tuple[list[dict], int, str | None]:
        sql_stripped = sql.strip().rstrip(";")
        upper = sql_stripped.upper()
        if not upper.startswith("SELECT"):
            return [], 0, "Only SELECT queries are allowed"
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "ATTACH"]
        for word in forbidden:
            if word in upper:
                return [], 0, f"Forbidden keyword: {word}"
        try:
            df = self.conn.execute(sql_stripped).fetchdf()
            rows = df.to_dict(orient="records")
            for row in rows:
                for k, v in row.items():
                    if hasattr(v, "item"):
                        row[k] = v.item()
                    elif pd.isna(v):
                        row[k] = None
                    elif k in ("make", "model", "variant", "engineFuelType", "gearboxType", "drivetrain"):
                        row[k] = str(v).strip() if v is not None else None
            return rows, len(rows), None
        except Exception as e:
            return [], 0, str(e)

    def get_vehicle_by_id(self, vehicle_id: str) -> dict | None:
        row = self.conn.execute(
            f"SELECT * FROM {CARS_TABLE} WHERE vehicle_id = ?",
            [vehicle_id],
        ).fetchdf()
        if row.empty:
            return None
        d = row.iloc[0].to_dict()
        return {k: (None if pd.isna(v) else v) for k, v in d.items()}

    def get_vehicles_by_ids(self, ids: list[str]) -> list[dict]:
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        df = self.conn.execute(
            f"SELECT * FROM {CARS_TABLE} WHERE vehicle_id IN ({placeholders})",
            ids,
        ).fetchdf()
        results = []
        for _, r in df.iterrows():
            d = r.to_dict()
            results.append({k: (None if pd.isna(v) else v) for k, v in d.items()})
        return results

    def count_with_filters(self, filters: ActiveFilters) -> int:
        try:
            row = self.conn.execute(self.build_count_sql(filters)).fetchone()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    def search_filtered(
        self, filters: ActiveFilters, *, display_limit: int | None = None
    ) -> tuple[list[dict], int, str | None, str]:
        """Return (display_rows, total_match_count, error, sql_used)."""
        from app.config import settings

        lim = display_limit if display_limit is not None else settings.ui_cards_limit
        sql = self.build_filter_sql(filters, limit=lim)
        rows, _, err = self.execute_readonly_sql(sql)
        total = self.count_with_filters(filters)
        return rows, total, err, sql

    def health_ok(self) -> bool:
        try:
            self.conn.execute(f"SELECT 1 FROM {CARS_TABLE} LIMIT 1").fetchone()
            return True
        except Exception:
            return False


def _short_duckdb_error(exc: Exception) -> str:
    text = str(exc).strip()
    text = re.sub(r"\(PID\s+\d+\)", "(stale lock — process may already be exited)", text)
    return text[:240]


duckdb_service = DuckDBService()
