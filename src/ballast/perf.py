"""Performance measures and the two tests Cederburg et al. (2020) use.

Sharpe ratios are annualized by ``sqrt(12)``. The certainty-equivalent return
(CER) of a mean-variance investor with risk aversion ``gamma`` is
``mean - gamma / 2 * variance`` on monthly decimal returns, reported in percent
per year (times 1200).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from ballast._types import Array

#: Relative floor below which a test variance is treated as zero (identical series).
_TINY = 1e-12


def sharpe_ratio(returns: Array) -> float:
    """Annualized Sharpe ratio of monthly excess returns."""
    return float(np.sqrt(12.0) * np.mean(returns) / np.std(returns, ddof=1))


def certainty_equivalent(returns: Array, gamma: float) -> float:
    """CER in percent per year for monthly decimal excess returns."""
    return float(1200.0 * (np.mean(returns) - 0.5 * gamma * np.var(returns, ddof=1)))


@dataclass(frozen=True)
class DifferenceTest:
    """A difference ``i - j``, its z-statistic and two-sided normal p-value."""

    difference: float
    z: float
    p_value: float


def _two_sided(z: float) -> float:
    return float(2.0 * norm.sf(abs(z)))


def jobson_korkie(returns_i: Array, returns_j: Array) -> DifferenceTest:
    """Test of equal Sharpe ratios, Jobson and Korkie (1981) with Memmel's (2003) correction.

    This is the statistic in footnote 8 of Cederburg et al. (2020):
    ``z = (s_j m_i - s_i m_j) / sqrt(theta)`` with
    ``theta = (2 s_i^2 s_j^2 - 2 s_i s_j s_ij + m_i^2 s_j^2 / 2 + m_j^2 s_i^2 / 2
    - m_i m_j s_ij^2 / (s_i s_j)) / T``.

    The reported difference is in annualized Sharpe ratios.
    """
    n = len(returns_i)
    if len(returns_j) != n:
        raise ValueError("series must have the same length")
    m_i, m_j = float(np.mean(returns_i)), float(np.mean(returns_j))
    s_i, s_j = float(np.std(returns_i, ddof=1)), float(np.std(returns_j, ddof=1))
    s_ij = float(np.cov(returns_i, returns_j, ddof=1)[0, 1])
    theta = (
        2.0 * s_i**2 * s_j**2
        - 2.0 * s_i * s_j * s_ij
        + 0.5 * m_i**2 * s_j**2
        + 0.5 * m_j**2 * s_i**2
        - m_i * m_j * s_ij**2 / (s_i * s_j)
    ) / n
    difference = float(np.sqrt(12.0) * (m_i / s_i - m_j / s_j))
    if theta <= _TINY * s_i**2 * s_j**2 / n:
        return DifferenceTest(difference, float("nan"), float("nan"))
    z = (s_j * m_i - s_i * m_j) / float(np.sqrt(theta))
    return DifferenceTest(difference, z, _two_sided(z))


def cer_difference_test(returns_i: Array, returns_j: Array, gamma: float) -> DifferenceTest:
    """Test of equal CERs, DeMiguel, Garlappi and Uppal (2009).

    This is the statistic in footnote 19 of Cederburg et al. (2020): the delta
    method applied to ``(m_i, m_j, s_i^2, s_j^2)`` with gradient
    ``(1, -1, -gamma/2, gamma/2)``, which gives the variance
    ``(s_i^2 + s_j^2 - 2 s_ij + gamma^2 / 2 * (s_i^4 + s_j^4 - 2 s_ij^2)) / T``.

    The reported difference is in percent per year.
    """
    n = len(returns_i)
    if len(returns_j) != n:
        raise ValueError("series must have the same length")
    v_i, v_j = float(np.var(returns_i, ddof=1)), float(np.var(returns_j, ddof=1))
    s_ij = float(np.cov(returns_i, returns_j, ddof=1)[0, 1])
    monthly = (float(np.mean(returns_i)) - 0.5 * gamma * v_i) - (
        float(np.mean(returns_j)) - 0.5 * gamma * v_j
    )
    theta = (v_i + v_j - 2.0 * s_ij + 0.5 * gamma**2 * (v_i**2 + v_j**2 - 2.0 * s_ij**2)) / n
    difference = 1200.0 * monthly
    if theta <= _TINY * (v_i + v_j) / n:
        return DifferenceTest(difference, float("nan"), float("nan"))
    z = monthly / float(np.sqrt(theta))
    return DifferenceTest(difference, z, _two_sided(z))
