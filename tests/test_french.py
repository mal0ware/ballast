"""The parser, checked against two small files written by hand."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ballast.french import parse_french_csv

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_monthly_block_is_read_and_annual_block_is_ignored() -> None:
    table = parse_french_csv(_read("monthly_fixture.csv"), "monthly")
    assert list(table.columns) == ["Mkt-RF", "SMB", "HML", "RF"]
    assert list(table.index) == list(pd.period_range("2000-01", "2000-04", freq="M"))
    january = table.loc[pd.Period("2000-01", "M")]
    np.testing.assert_allclose(january.to_numpy(), [0.0125, -0.005, 0.0075, 0.001])
    assert table.loc[pd.Period("2000-02", "M"), "Mkt-RF"] == pytest.approx(-0.02)


def test_missing_codes_become_nan() -> None:
    table = parse_french_csv(_read("monthly_fixture.csv"), "monthly")
    last = table.loc[pd.Period("2000-04", "M")]
    assert np.isnan(last["Mkt-RF"])
    assert np.isnan(last["HML"])
    assert last["SMB"] == 0.0
    assert last["RF"] == pytest.approx(0.0013)


def test_daily_file_with_padded_header() -> None:
    table = parse_french_csv(_read("daily_fixture.csv"), "daily")
    assert list(table.columns) == ["Mom"]
    assert isinstance(table.index, pd.DatetimeIndex)
    assert table.index[0] == pd.Timestamp("2000-01-03")
    assert len(table) == 4
    np.testing.assert_allclose(table["Mom"].to_numpy()[:3], [0.0056, -0.005, 0.0117])
    assert np.isnan(table["Mom"].iloc[3])


def test_windows_line_endings_parse_the_same() -> None:
    """The real files use CRLF."""
    text = _read("monthly_fixture.csv")
    crlf = text.replace("\n", "\r\n")
    pd.testing.assert_frame_equal(
        parse_french_csv(crlf, "monthly"), parse_french_csv(text, "monthly")
    )


def test_wrong_frequency_finds_no_rows() -> None:
    with pytest.raises(ValueError, match="no data rows"):
        parse_french_csv(_read("monthly_fixture.csv"), "daily")


def test_no_header_is_an_error() -> None:
    with pytest.raises(ValueError, match="no header"):
        parse_french_csv("just text\n200001, 1.0\n", "monthly")


def test_ragged_row_is_an_error() -> None:
    with pytest.raises(ValueError, match="expected 2 values"):
        parse_french_csv(",A,B\n200001, 1.0\n", "monthly")


def test_dates_out_of_order_are_an_error() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        parse_french_csv(",A\n200002, 1.0\n200001, 2.0\n", "monthly")
