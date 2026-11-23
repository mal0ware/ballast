"""Sharpe ratio, CER and the two difference tests."""

from __future__ import annotations

import numpy as np
import pytest

from ballast.perf import (
    cer_difference_test,
    certainty_equivalent,
    jobson_korkie,
    sharpe_ratio,
)


def _pair(seed: int, n: int = 600, rho: float = 0.6) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    a = rng.normal(0.006, 0.04, n)
    b = rho * a + np.sqrt(1 - rho**2) * rng.normal(0.006, 0.04, n)
    return a, b


def test_sharpe_and_cer_by_hand() -> None:
    r = np.array([0.02, -0.01, 0.03, 0.00])
    mean, var = 0.01, (0.01**2 + 0.02**2 + 0.02**2 + 0.01**2) / 3
    assert sharpe_ratio(r) == pytest.approx(np.sqrt(12) * mean / np.sqrt(var))
    assert certainty_equivalent(r, 5.0) == pytest.approx(1200 * (mean - 2.5 * var))


def test_jobson_korkie_is_antisymmetric_and_scale_free() -> None:
    a, b = _pair(1)
    ab, ba = jobson_korkie(a, b), jobson_korkie(b, a)
    assert ab.difference == pytest.approx(sharpe_ratio(a) - sharpe_ratio(b))
    assert ba.z == pytest.approx(-ab.z)
    assert ba.p_value == pytest.approx(ab.p_value)
    scaled = jobson_korkie(3.0 * a, 0.2 * b)  # leverage does not change a Sharpe ratio
    assert scaled.z == pytest.approx(ab.z)


def test_jobson_korkie_matches_the_formula_written_out() -> None:
    a, b = _pair(2)
    n = len(a)
    mi, mj, si, sj = a.mean(), b.mean(), a.std(ddof=1), b.std(ddof=1)
    sij = np.cov(a, b, ddof=1)[0, 1]
    theta = (
        2 * si**2 * sj**2
        - 2 * si * sj * sij
        + 0.5 * mi**2 * sj**2
        + 0.5 * mj**2 * si**2
        - mi * mj / (si * sj) * sij**2
    ) / n
    assert jobson_korkie(a, b).z == pytest.approx((sj * mi - si * mj) / np.sqrt(theta))


def test_cer_test_matches_the_matrix_form_in_the_paper() -> None:
    """Footnote 19 of Cederburg et al.: gradient times covariance times gradient."""
    a, b = _pair(3)
    gamma = 5.0
    vi, vj = a.var(ddof=1), b.var(ddof=1)
    sij = np.cov(a, b, ddof=1)[0, 1]
    big = np.array(
        [
            [vi, sij, 0, 0],
            [sij, vj, 0, 0],
            [0, 0, 2 * vi**2, 2 * sij**2],
            [0, 0, 2 * sij**2, 2 * vj**2],
        ]
    )
    g = np.array([1, -1, -gamma / 2, gamma / 2])
    theta = g @ big @ g / len(a)
    diff = (a.mean() - gamma / 2 * vi) - (b.mean() - gamma / 2 * vj)
    result = cer_difference_test(a, b, gamma)
    assert result.z == pytest.approx(diff / np.sqrt(theta))
    assert result.difference == pytest.approx(
        certainty_equivalent(a, gamma) - certainty_equivalent(b, gamma)
    )


def test_identical_series_give_no_statistic() -> None:
    a, _ = _pair(4)
    result = jobson_korkie(a, a)
    assert result.difference == pytest.approx(0.0)
    assert np.isnan(result.z)


@pytest.mark.parametrize("which", ["sharpe", "cer"])
def test_tests_have_about_the_right_size_under_the_null(which: str) -> None:
    """With equal true Sharpe ratios and CERs, z should be close to standard normal."""
    rng = np.random.default_rng(99)
    cov = 0.04**2 * np.array([[1.0, 0.5], [0.5, 1.0]])
    z = []
    for _ in range(2000):
        draw = rng.multivariate_normal([0.005, 0.005], cov, size=480)
        if which == "sharpe":
            z.append(jobson_korkie(draw[:, 0], draw[:, 1]).z)
        else:
            z.append(cer_difference_test(draw[:, 0], draw[:, 1], 5.0).z)
    z_arr = np.array(z)
    assert abs(z_arr.mean()) < 0.08
    assert z_arr.std() == pytest.approx(1.0, abs=0.06)
    assert np.mean(np.abs(z_arr) > 1.96) == pytest.approx(0.05, abs=0.02)


def test_length_mismatch() -> None:
    with pytest.raises(ValueError, match="same length"):
        jobson_korkie(np.zeros(3), np.zeros(4))
    with pytest.raises(ValueError, match="same length"):
        cer_difference_test(np.zeros(3), np.zeros(4), 5.0)
