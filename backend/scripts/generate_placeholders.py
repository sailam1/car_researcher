"""Generate placeholder PNG files per make from cars_details."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python scripts/generate_placeholders.py` without PYTHONPATH=.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import pandas as pd  # noqa: E402

from app.config import settings  # noqa: E402


def main() -> None:
    cars_csv = settings.cardata_path / "cars_details.csv"
    if not cars_csv.exists():
        raise FileNotFoundError(f"Missing {cars_csv}")

    makes = (
        pd.read_csv(cars_csv, usecols=["make"])["make"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    out = _BACKEND_ROOT / "app" / "data" / "placeholders"
    out.mkdir(parents=True, exist_ok=True)
    default = out / "default.png"
    if not default.exists():
        default.write_bytes(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d4948445200000064000000640806000000"
                "7e9a5a1a0000000a49444154789c63000100000500010d0a2db400000000"
                "49454e44ae426082"
            )
        )
    created = 0
    for make in makes:
        name = f"{make.upper().replace(' ', '_')}.png"
        target = out / name
        if not target.exists():
            target.write_bytes(default.read_bytes())
            created += 1
    print(f"Placeholders: {created} new, {len(makes)} makes total -> {out}")


if __name__ == "__main__":
    main()
