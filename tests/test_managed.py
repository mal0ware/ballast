"""Realized variance and the managed factor."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ballast.analysis import managed_factor
from ballast.data import FACTORS, FactorData
from ballast.managed import VarianceMethod, build_managed, realized_variance, scale_constant


def _daily() -> pd.Series:
    days = pd.to_datetime(["2000-01-03", "2000-01-04", "2000-01-05", "2000-02-01", "2000-02-02"])
    return pd.Series([0.01, -0.02, 0.04, 0.03, -0.01], index=days)


def test_realized_variance_mm_is_sum_of_squared_deviations() -> None:
    rv = realized_variance(_daily(), "mm")
    jan = np.array([0.01, -0.02, 0.04])
    assert rv[pd.Period("2000-01", "M")] == pytest.approx(((jan - jan.mean()) ** 2).sum())
    assert rv[pd.Period("2000-02", "M")] == pytest.approx(2 * 0.02**2)


def test_realized_variance_cowy_is_scaled_sum_of_squares() -> None:
    rv = realized_variance(_daily(), "cowy")
    assert rv[pd.Period("2000-01", "M")] == pytest.approx(22 / 3 * (0.01**2 + 0.02**2 + 0.04**2))
    assert rv[pd.Period("2000-02", "M")] == pytest.approx(22 / 2 * (0.03**2 + 0.01**2))


def test_months_with_one_day_are_dropped() -> None:
    days = pd.to_datetime(["2000-01-03", "2000-01-04", "2000-02-01"])
    rv = realized_variance(pd.Series([0.01, 0.02, 0.03], index=days), "mm")
    assert list(rv.index) == [pd.Period("2000-01", "M")]


def test_managed_return_uses_previous_month_variance() -> None:
    months = pd.period_range("2000-01", "2000-05", freq="M")
    monthly = pd.Series([0.01, 0.02, -0.03, 0.04, 0.01], index=months)
    rv = pd.Series([0.001, 0.002, 0.004, 0.008, 0.016], index=months)
    m = build_managed(monthly, rv)
    assert list(m.original.index) == list(months[1:])  # no variance before the first month
    np.testing.assert_allclose(m.inverse_variance.to_numpy(), [1000.0, 500.0, 250.0, 125.0])
    np.testing.assert_allclose(m.managed.to_numpy(), m.c * np.array([20.0, -15.0, 10.0, 1.25]))
    np.testing.assert_allclose(m.weight.to_numpy(), m.c * m.inverse_variance.to_numpy())


@pytest.mark.parametrize("method", ["mm", "cowy"])
@pytest.mark.parametrize("name", FACTORS)
def test_managed_and_unmanaged_have_equal_variance(
    synthetic: FactorData, name: str, method: VarianceMethod
) -> None:
    m = managed_factor(synthetic, name, method)
    assert m.managed.var(ddof=1) == pytest.approx(m.original.var(ddof=1), rel=1e-12)


def test_equal_variance_holds_on_a_subsample(synthetic: FactorData) -> None:
    m = managed_factor(synthetic, "MKT", "mm", start="1950-01", end="1969-12")
    assert len(m.original) == 240
    assert m.managed.std(ddof=1) == pytest.approx(m.original.std(ddof=1), rel=1e-12)


def test_scale_constant_is_positive_and_scales_inversely() -> None:
    rng = np.random.default_rng(1)
    f = rng.normal(0.005, 0.04, 300)
    iv = 1.0 / rng.uniform(0.0005, 0.005, 300)
    c = scale_constant(f, iv)
    assert c > 0
    assert scale_constant(f, 10.0 * iv) == pytest.approx(c / 10.0)


def test_zero_variance_is_rejected() -> None:
    months = pd.period_range("2000-01", "2000-06", freq="M")
    monthly = pd.Series(0.01, index=months)
    rv = pd.Series([0.001, 0.0, 0.002, 0.001, 0.003, 0.002], index=months)
    with pytest.raises(ValueError, match="positive"):
        build_managed(monthly, rv)
