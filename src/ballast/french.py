"""Parser for the CSV files of the Kenneth R. French Data Library.

A file is a few lines of free text, a blank line, a header row that starts
with a comma, then one row per period. Monthly files carry a second block of
annual figures after another blank line; only the first block is read. Returns
are quoted in percent and are converted to decimals here. Missing values are
coded as ``-99.99`` or ``-999``.
"""

from __future__ import annotations

import re
from typing import Literal

import numpy as np
import pandas as pd

Frequency = Literal["daily", "monthly"]

_MISSING_CODES = (-99.99, -999.0)
_DATE_DIGITS = {"daily": 8, "monthly": 6}


def parse_french_csv(text: str, frequency: Frequency) -> pd.DataFrame:
    """Parse the first data block of a French library CSV.

    Args:
        text: Full contents of the CSV file.
        frequency: ``"daily"`` for ``YYYYMMDD`` rows, ``"monthly"`` for ``YYYYMM``.

    Returns:
        Returns as decimals (``0.01`` is one percent). The index is a
        ``DatetimeIndex`` for daily files and a monthly ``PeriodIndex`` for
        monthly files. Column names are stripped of surrounding blanks.

    Raises:
        ValueError: If no header row is found, the block is empty, a row has
            the wrong number of fields, or the dates are not strictly increasing.
    """
    digits = _DATE_DIGITS[frequency]
    row_pattern = re.compile(rf"^\s*(\d{{{digits}}})\s*,(.*)$")
    lines = text.splitlines()

    header_at = next((i for i, line in enumerate(lines) if line.startswith(",")), None)
    if header_at is None:
        raise ValueError("no header row (a line starting with a comma) found")
    columns = [name.strip() for name in lines[header_at].split(",")[1:]]
    if not columns or any(not name for name in columns):
        raise ValueError(f"malformed header row: {lines[header_at]!r}")

    dates: list[str] = []
    rows: list[list[float]] = []
    for line in lines[header_at + 1 :]:
        match = row_pattern.match(line)
        if match is None:
            break  # blank line, annual block or copyright notice
        fields = match.group(2).split(",")
        if len(fields) != len(columns):
            raise ValueError(f"expected {len(columns)} values, got {len(fields)}: {line!r}")
        dates.append(match.group(1))
        rows.append([float(field) for field in fields])
    if not rows:
        raise ValueError("no data rows found after the header")

    values = np.asarray(rows, dtype=float)
    for code in _MISSING_CODES:
        values[np.isclose(values, code)] = np.nan
    values = values / 100.0

    index: pd.Index
    if frequency == "daily":
        index = pd.DatetimeIndex(pd.to_datetime(dates, format="%Y%m%d"), name="date")
    else:
        index = pd.PeriodIndex(pd.to_datetime(dates, format="%Y%m"), freq="M", name="month")
    if not index.is_monotonic_increasing or not index.is_unique:
        raise ValueError("dates are not strictly increasing")
    return pd.DataFrame(values, index=index, columns=columns)
