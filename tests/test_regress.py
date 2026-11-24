"""Regression code against statsmodels."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from ballast.analysis import managed_factor
from ballast.data import FactorData
from ballast.regress import CovType, newey_west_lags, ols, spanning_regression


def _data(seed: int, n: int = 400, p: int = 3) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, p))
    noise = rng.normal(size=n) * (0.5 + np.abs(x[:, 0]))  # heteroskedastic
    y = 0.3 + x @ np.array([1.0, -0.5, 0.25])[:p] + noise
    return y, x


@pytest.mark.parametrize("cov_type", ["nonrobust", "HC0", "HC1"])
@pytest.mark.parametrize("p", [1, 3])
def test_ols_matches_statsmodels(cov_type: CovType, p: int) -> None:
    y, x = _data(7, p=p)
    ours = ols(y, x, cov_type)
    ref = sm.OLS(y, sm.add_constant(x)).fit(cov_type=cov_type)
    np.testing.assert_allclose(ours.params, ref.params, rtol=1e-10)
    np.testing.assert_allclose(ours.se, ref.bse, rtol=1e-10)
    np.testing.assert_allclose(ours.tstats, ref.tvalues, rtol=1e-9)
    assert ours.r2 == pytest.approx(ref.rsquared, rel=1e-10)
    assert ours.r2_adj == pytest.approx(ref.rsquared_adj, rel=1e-10)
    assert ours.rmse == pytest.approx(np.sqrt(ref.mse_resid), rel=1e-10)
    assert ours.nobs == int(ref.nobs)


@pytest.mark.parametrize("lags", [0, 1, 6])
def test_newey_west_matches_statsmodels(lags: int) -> None:
    y, x = _data(11, p=2)
    ours = ols(y, x, "HAC", lags=lags)
    ref = sm.OLS(y, sm.add_constant(x)).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags, "use_correction": False}
    )
    np.testing.assert_allclose(ours.se, ref.bse, rtol=1e-10)
    if lags == 0:
        np.testing.assert_allclose(ours.se, ols(y, x, "HC0").se, rtol=1e-12)


def test_newey_west_default_lags() -> None:
    assert newey_west_lags(100) == 4
    assert newey_west_lags(1065) == 6
    assert newey_west_lags(117) == 4
    y, x = _data(12, n=300, p=1)
    np.testing.assert_allclose(ols(y, x, "HAC").se, ols(y, x, "HAC", lags=5).se)


def test_one_dimensional_regressor_is_accepted() -> None:
    y, x = _data(3, p=1)
    np.testing.assert_allclose(ols(y, x[:, 0]).params, ols(y, x).params)


def test_spanning_regression_matches_statsmodels_in_paper_units(synthetic: FactorData) -> None:
    m = managed_factor(synthetic, "MOM", "mm")
    ours = spanning_regression(m.managed, m.original)
    ref = sm.OLS(m.managed.to_numpy(), sm.add_constant(m.original.to_numpy())).fit(cov_type="HC0")
    assert ours.alpha == pytest.approx(1200 * ref.params[0], rel=1e-9)
    assert ours.alpha_se == pytest.approx(1200 * ref.bse[0], rel=1e-9)
    assert ours.alpha_t == pytest.approx(ref.tvalues[0], rel=1e-9)
    assert ours.beta == pytest.approx(ref.params[1], rel=1e-9)
    assert ours.rmse == pytest.approx(1200 * np.sqrt(ref.mse_resid), rel=1e-9)
    assert ours.appraisal_ratio == pytest.approx(
        np.sqrt(12) * ref.params[0] / np.sqrt(ref.mse_resid), rel=1e-9
    )


def test_controls_match_statsmodels_and_drop_the_duplicate(synthetic: FactorData) -> None:
    ff3 = synthetic.monthly[["MKT", "SMB", "HML"]]
    m = managed_factor(synthetic, "MKT", "mm")
    ours = spanning_regression(m.managed, m.original, controls=ff3)
    x = ff3.loc[m.managed.index].to_numpy()  # MKT once, not twice
    ref = sm.OLS(m.managed.to_numpy(), sm.add_constant(x)).fit(cov_type="HC0")
    assert ours.alpha == pytest.approx(1200 * ref.params[0], rel=1e-8)
    assert ours.alpha_se == pytest.approx(1200 * ref.bse[0], rel=1e-8)


def test_beta_equals_correlation_when_variances_match(synthetic: FactorData) -> None:
    """Cederburg et al., footnote 13: equal variances make the slope the correlation."""
    m = managed_factor(synthetic, "HML", "cowy")
    fit = spanning_regression(m.managed, m.original)
    assert fit.beta == pytest.approx(np.corrcoef(m.managed, m.original)[0, 1], rel=1e-10)


def test_too_few_observations() -> None:
    with pytest.raises(ValueError, match="more observations"):
        ols(np.array([1.0, 2.0]), np.array([1.0, 2.0]))


def test_exact_line_is_recovered_in_paper_units() -> None:
    months = pd.period_range("2000-01", periods=50, freq="M")
    rng = np.random.default_rng(0)
    original = pd.Series(rng.normal(size=50), index=months)
    managed = 0.01 + 0.5 * original
    fit = spanning_regression(managed, original)
    assert fit.alpha == pytest.approx(12.0)
    assert fit.beta == pytest.approx(0.5)
