"""Load the six factors used here from files fetched by ``scripts/fetch_data.py``."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ballast.french import Frequency, parse_french_csv

MANIFEST_NAME = "manifest.json"

#: Factor names used throughout, in the column order of Moreira and Muir's Table 1.
FACTORS: tuple[str, ...] = ("MKT", "SMB", "HML", "MOM", "RMW", "CMA")


@dataclass(frozen=True)
class FileSpec:
    """One file in the French library and the columns taken from it."""

    archive: str
    csv_name: str
    frequency: Frequency
    #: Maps the column name in the file to the factor name used here.
    columns: dict[str, str]


FILES: tuple[FileSpec, ...] = (
    FileSpec(
        "F-F_Research_Data_Factors_CSV.zip",
        "F-F_Research_Data_Factors.csv",
        "monthly",
        {"Mkt-RF": "MKT", "SMB": "SMB", "HML": "HML"},
    ),
    FileSpec(
        "F-F_Research_Data_Factors_daily_CSV.zip",
        "F-F_Research_Data_Factors_daily.csv",
        "daily",
        {"Mkt-RF": "MKT", "SMB": "SMB", "HML": "HML"},
    ),
    FileSpec(
        "F-F_Momentum_Factor_CSV.zip",
        "F-F_Momentum_Factor.csv",
        "monthly",
        {"Mom": "MOM"},
    ),
    FileSpec(
        "F-F_Momentum_Factor_daily_CSV.zip",
        "F-F_Momentum_Factor_daily.csv",
        "daily",
        {"Mom": "MOM"},
    ),
    FileSpec(
        "F-F_Research_Data_5_Factors_2x3_CSV.zip",
        "F-F_Research_Data_5_Factors_2x3.csv",
        "monthly",
        {"RMW": "RMW", "CMA": "CMA"},
    ),
    FileSpec(
        "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip",
        "F-F_Research_Data_5_Factors_2x3_daily.csv",
        "daily",
        {"RMW": "RMW", "CMA": "CMA"},
    ),
)


@dataclass(frozen=True)
class FactorData:
    """Daily and monthly factor returns as decimals.

    ``daily`` has a ``DatetimeIndex``; ``monthly`` has a monthly ``PeriodIndex``.
    Both have one column per name in :data:`FACTORS`, with ``NaN`` before a
    factor starts. The market is in excess of the bill rate; the others are
    long-short portfolios, so every column is an excess return.
    """

    daily: pd.DataFrame
    monthly: pd.DataFrame
    manifest: dict[str, Any]


def _select(table: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Pick and rename columns, matching names without regard to case."""
    by_lower = {str(name).lower(): name for name in table.columns}
    picked = {}
    for source, target in mapping.items():
        if source.lower() not in by_lower:
            raise KeyError(f"column {source!r} not in {list(table.columns)}")
        picked[target] = table[by_lower[source.lower()]]
    return pd.DataFrame(picked)


def load_factors(data_dir: Path) -> FactorData:
    """Read the six French files in ``data_dir`` and align them by date."""
    frames: dict[str, list[pd.DataFrame]] = {"daily": [], "monthly": []}
    for spec in FILES:
        path = data_dir / spec.csv_name
        if not path.exists():
            raise FileNotFoundError(
                f"{path} is missing; run `uv run python scripts/fetch_data.py` first"
            )
        table = parse_french_csv(path.read_text(encoding="utf-8"), spec.frequency)
        frames[spec.frequency].append(_select(table, spec.columns))
    daily = pd.concat(frames["daily"], axis=1).sort_index()[list(FACTORS)]
    monthly = pd.concat(frames["monthly"], axis=1).sort_index()[list(FACTORS)]
    manifest_path = data_dir / MANIFEST_NAME
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return FactorData(daily=daily, monthly=monthly, manifest=manifest)
