"""The block-bootstrap Sharpe-ratio test."""

from __future__ import annotations

import numpy as np
import pytest

from ballast.bootstrap import (
    _difference_and_gradient,
    _garch_t_pair,
    hac_sharpe_se,
    sharpe_difference_bootstrap,
    size_study,
)
from ballast.perf import jobson_korkie


def _pair(seed: int, n: int = 600, rho: float = 0.6) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    a = rng.normal(0.006, 0.04, n)
    b = rho * a + np.sqrt(1 - rho**2) * rng.normal(0.006, 0.04, n)
    return a, b


def test_gradient_matches_finite_differences() -> None:
    a, b = _pair(1)

    def f(v: np.ndarray) -> float:
        return float(v[0] / np.sqrt(v[2] - v[0] ** 2) - v[1] / np.sqrt(v[3] - v[1] ** 2))

    v = np.array([a.mean(), b.mean(), (a**2).mean(), (b**2).mean()])
    diff, grad, _, valid = _difference_and_gradient(a, b)
    assert bool(valid)
    assert float(diff) == pytest.approx(f(v))
    h = 1e-7
    numeric = [(f(v + h * e) - f(v - h * e)) / (2 * h) for e in np.eye(4)]
    np.testing.assert_allclose(grad, numeric, rtol=1e-5)


def test_zero_lag_se_is_the_delta_method_by_hand() -> None:
    a, b = _pair(2)
    _, grad, terms, _ = _difference_and_gradient(a, b)
    psi = terms.T @ terms / len(a)
    by_hand = np.sqrt(grad @ psi @ grad / len(a))
    assert hac_sharpe_se(a, b, lags=0) == pytest.approx(by_hand)


def test_se_is_close_to_jobson_korkie_for_iid_normal_data() -> None:
    """Under iid normality both standard errors estimate the same thing."""
    a, b = _pair(3, n=5000)
    jk = jobson_korkie(a, b)
    jk_se = abs(jk.difference / np.sqrt(12.0) / jk.z)
    assert hac_sharpe_se(a, b) == pytest.approx(jk_se, rel=0.1)


def test_p_value_is_seeded_and_in_range() -> None:
    a, b = _pair(4, n=300)
    first = sharpe_difference_bootstrap(a, b, draws=199, seed=5)
    second = sharpe_difference_bootstrap(a, b, draws=199, seed=5)
    assert first == second
    assert 1 / 200 <= first.p_value <= 1.0
    assert first.difference == pytest.approx(
        np.sqrt(12) * (a.mean() / a.std() - b.mean() / b.std())
    )


def test_large_difference_is_rejected_and_none_is_not() -> None:
    rng = np.random.default_rng(6)
    noise = rng.normal(0.0, 0.04, (600, 2))
    good = 0.02 + noise[:, 0]
    bad = -0.01 + 0.6 * noise[:, 0] + 0.8 * noise[:, 1]
    assert sharpe_difference_bootstrap(good, bad, draws=499).p_value < 0.01
    a, b = _pair(8)
    assert jobson_korkie(a, b).p_value > 0.5
    assert sharpe_difference_bootstrap(a, b, draws=199).p_value > 0.2


def test_identical_series_give_no_p_value() -> None:
    a, _ = _pair(8)
    assert np.isnan(sharpe_difference_bootstrap(a, a, draws=99).p_value)


def test_bad_inputs() -> None:
    with pytest.raises(ValueError, match="same length"):
        sharpe_difference_bootstrap(np.zeros(5), np.zeros(6))
    with pytest.raises(ValueError, match="block length"):
        sharpe_difference_bootstrap(np.ones(5), np.ones(5), block=6)


def test_garch_pair_has_equal_sharpe_ratios_and_fat_tails() -> None:
    rng = np.random.default_rng(9)
    a, b = _garch_t_pair(rng, 200_000, 0.6)
    assert a.mean() / a.std() == pytest.approx(b.mean() / b.std(), abs=0.01)
    kurtosis = ((a - a.mean()) ** 4).mean() / a.var() ** 2
    assert kurtosis > 4.0


def test_size_is_near_five_percent_with_fat_tails() -> None:
    """A small run of the size study; the full one is in results/bootstrap_size.csv."""
    table = size_study(sims=200, lengths=(240,), draws=199, seed=11)
    for rate in table["reject_bootstrap"]:
        assert 0.01 <= rate <= 0.10
