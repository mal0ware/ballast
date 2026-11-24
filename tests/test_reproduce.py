"""The reproduce pipeline: it runs, and it gives the same files twice."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ballast.analysis import compare_cells, drawdown
from ballast.data import FACTORS
from ballast.report import build_results
from ballast.synthetic import synthetic_factors

#: Small bootstrap and size study, so the pipeline tests run quickly.
FAST = {"draws": 49, "size_sims": 4}


def test_two_runs_give_identical_tables(tmp_path: Path) -> None:
    first = build_results(synthetic_factors(), tmp_path / "a", figures=False, **FAST)
    second = build_results(synthetic_factors(), tmp_path / "b", figures=False, **FAST)
    assert first.keys() == second.keys()
    assert len(first) >= 19
    for name in first:
        assert first[name].read_bytes() == second[name].read_bytes(), name


def test_figures_are_written_and_identical(tmp_path: Path) -> None:
    data = synthetic_factors()
    first = build_results(data, tmp_path / "a", **FAST)
    second = build_results(data, tmp_path / "b", **FAST)
    for name in ("headline_png", "costs_png", "momentum_png"):
        assert first[name].stat().st_size > 10_000
        assert first[name].read_bytes() == second[name].read_bytes()


def test_tables_cover_all_six_factors(tmp_path: Path) -> None:
    written = build_results(synthetic_factors(), tmp_path, figures=False, **FAST)
    for name in ("table1_paper_sample", "realtime_paper_sample", "direct_extended"):
        table = pd.read_csv(written[name], index_col=0)
        assert list(table.index) == list(FACTORS)
        assert not table.isna().any().any()
    for name in ("costs_in_sample", "costs_real_time"):
        table = pd.read_csv(written[name])
        assert set(table["sample"]) == {"paper", "extended", "new_months"}
        assert len(table) == 3 * len(FACTORS) * 4
    headline = written["headline"].read_text(encoding="utf-8")
    assert headline.count("<table>") == 3


def test_synthetic_data_is_seeded() -> None:
    a, b = synthetic_factors(end="1930-12-31"), synthetic_factors(end="1930-12-31")
    pd.testing.assert_frame_equal(a.daily, b.daily)
    pd.testing.assert_frame_equal(a.monthly, b.monthly)
    c = synthetic_factors(seed=1, end="1930-12-31")
    assert not a.daily["MKT"].equals(c.daily["MKT"])


def test_compare_cells_flags_only_printed_differences() -> None:
    ours = pd.DataFrame({"alpha": [4.864, 1.20], "nobs": [1065, 620]}, index=["MKT", "SMB"])
    paper = {"MKT": {"alpha": 4.86, "nobs": 1065}, "SMB": {"alpha": 1.25, "nobs": 621}}
    cells = compare_cells(ours, paper, "t").set_index(["factor", "statistic"])
    assert not cells.loc[("MKT", "alpha"), "differs"]
    assert not cells.loc[("MKT", "nobs"), "differs"]
    assert cells.loc[("SMB", "alpha"), "differs"]
    assert cells.loc[("SMB", "nobs"), "differs"]


def test_drawdown_by_hand() -> None:
    returns = pd.Series([0.10, -0.50, 0.20, -0.10])
    # Wealth: 1.10, 0.55, 0.66, 0.594. Peak 1.10, trough 0.55.
    assert drawdown(returns) == pytest.approx(-0.5)
    assert drawdown(pd.Series([-0.2, 0.1])) == pytest.approx(-0.2)  # from the first dollar
