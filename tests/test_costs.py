"""Trading costs, break-even costs, and the Holm adjustment."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.multitest import multipletests

from ballast.analysis import (
    _real_time_gain,
    managed_factor,
    real_time_costs_table,
    real_time_table,
    spanning_costs_table,
    spanning_table,
)
from ballast.costs import net_of_costs, turnover
from ballast.data import FactorData
from ballast.perf import holm
from ballast.realtime import real_time_combination
from ballast.regress import spanning_regression


def test_turnover_and_net_return_by_hand() -> None:
    months = pd.period_range("2000-01", periods=4, freq="M")
    position = pd.Series([1.0, 1.5, 0.5, 0.5], index=months)
    gross = pd.Series([0.01, 0.02, -0.01, 0.00], index=months)
    np.testing.assert_allclose(turnover(position), [0.0, 0.5, 1.0, 0.0])
    np.testing.assert_allclose(
        net_of_costs(gross, position, 50.0), [0.01, 0.02 - 0.0025, -0.01 - 0.005, 0.0]
    )


def test_holm_matches_statsmodels() -> None:
    p = np.array([0.01, 0.04, 0.03, 0.20, 0.005, 0.6])
    expected = multipletests(p, method="holm")[1]
    np.testing.assert_allclose(holm(p), expected)
    with_nan = holm(np.array([0.01, np.nan, 0.04]))
    assert np.isnan(with_nan[1])
    np.testing.assert_allclose(with_nan[[0, 2]], multipletests([0.01, 0.04], method="holm")[1])


@pytest.fixture(scope="module")
def in_sample(synthetic: FactorData) -> pd.DataFrame:
    return spanning_costs_table(synthetic, end="1990-12")


def test_gross_row_matches_the_spanning_table(
    synthetic: FactorData, in_sample: pd.DataFrame
) -> None:
    table = spanning_table(synthetic, end="1990-12")
    gross = in_sample.xs(0.0, level="cost_bps")
    np.testing.assert_allclose(gross["alpha"], table["alpha"], rtol=1e-12)
    np.testing.assert_allclose(gross["alpha_t_nw"], table["alpha_t_nw"], rtol=1e-12)


def test_net_alpha_falls_in_a_straight_line_to_the_break_even(
    synthetic: FactorData, in_sample: pd.DataFrame
) -> None:
    for factor in in_sample.index.get_level_values("factor").unique():
        rows = in_sample.loc[factor]
        alphas = rows["alpha"].to_numpy()
        costs = rows.index.to_numpy()
        slope = np.polyfit(costs, alphas, 1)
        np.testing.assert_allclose(np.polyval(slope, costs), alphas, atol=1e-9)
        break_even = rows["break_even_bps"].iloc[0]
        if np.isfinite(break_even):
            m = managed_factor(synthetic, factor, "mm", end="1990-12")
            net = net_of_costs(m.managed, m.weight, break_even)
            assert spanning_regression(net, m.original, cov_type="HAC").alpha == pytest.approx(
                0.0, abs=1e-9
            )


def test_significance_threshold_sits_at_t_of_1_96(
    synthetic: FactorData, in_sample: pd.DataFrame
) -> None:
    for factor in in_sample.index.get_level_values("factor").unique():
        limit = in_sample.loc[factor, "significant_up_to_bps"].iloc[0]
        if np.isfinite(limit):
            m = managed_factor(synthetic, factor, "mm", end="1990-12")
            net = net_of_costs(m.managed, m.weight, limit)
            fit = spanning_regression(net, m.original, cov_type="HAC")
            assert fit.alpha_t == pytest.approx(1.96, abs=1e-4)


def test_real_time_costs_gross_row_and_break_even(synthetic: FactorData) -> None:
    costs = real_time_costs_table(synthetic, end="1980-12", draws=99)
    plain = real_time_table(synthetic, end="1980-12", draws=99)
    gross = costs.xs(0.0, level="cost_bps")
    np.testing.assert_allclose(gross["sr_diff"], plain["sr_diff"], rtol=1e-12)
    np.testing.assert_allclose(gross["turnover_combo"], plain["turnover_combo"], rtol=1e-12)
    for factor in gross.index:
        diffs = costs.loc[factor, "sr_diff"].to_numpy()
        assert np.all(np.diff(diffs) < 0) or plain.loc[factor, "turnover_combo"] < 1e-12
        break_even = gross.loc[factor, "break_even_bps"]
        if np.isnan(break_even):
            assert gross.loc[factor, "sr_diff"] <= 0
        elif np.isfinite(break_even):
            m = managed_factor(synthetic, factor, "cowy", end="1980-12")
            full = real_time_combination(m.original, m.inverse_variance).frame
            gap = _real_time_gain(full, full.index, float(break_even))
            assert gap == pytest.approx(0.0, abs=1e-6)
