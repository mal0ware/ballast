"""A Sharpe-ratio difference test that allows fat tails and serial dependence.

The Jobson-Korkie-Memmel test in :mod:`ballast.perf` assumes returns are
independent and normal. Monthly factor returns are neither: they have fat
tails and volatility clusters. This module implements the studentised circular
block bootstrap of Ledoit and Wolf (2008), "Robust performance hypothesis
testing with the Sharpe ratio", Journal of Empirical Finance 15(5), 850-859.
It was written from the published description of the method, not from the
authors' code.

The difference ``SR_i - SR_j`` is a function of
``v = (mean_i, mean_j, E[r_i^2], E[r_j^2])``. Its standard error comes from the
delta method with a long-run covariance of the moment terms. Two things differ
from the paper, and both are deliberate simplifications:

* The original-sample standard error uses Newey-West (Bartlett) weights with
  the usual automatic lag length. Ledoit and Wolf use a prewhitened
  quadratic-spectral kernel.
* The block length is fixed by the caller. Ledoit and Wolf choose it by a
  calibration step. :func:`size_study` checks how the fixed choice behaves.

The bootstrap samples are scored with the block standard error from the paper:
the moment terms are summed within each resampled block and the long-run
covariance is the average outer product of those block sums.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ballast._types import Array
from ballast.perf import jobson_korkie
from ballast.regress import newey_west_lags

#: Default block length in months.
BLOCK = 6
#: Default number of bootstrap draws.
DRAWS = 4999
_CHUNK = 500


@dataclass(frozen=True)
class BootstrapTest:
    """A Sharpe-ratio difference with its robust standard error and p-value.

    ``difference`` and ``se`` are annualized (times ``sqrt(12)``). The
    difference uses moments that divide by ``n``, so it can differ in the third
    decimal from :func:`ballast.perf.sharpe_ratio`, which divides by ``n - 1``.
    """

    difference: float
    se: float
    p_value: float
    block: int
    draws: int


def _difference_and_gradient(r_i: Array, r_j: Array) -> tuple[Array, Array, Array, Array]:
    """Monthly Sharpe difference and its gradient, along the last axis.

    Works on 1-d series or on ``(draws, n)`` stacks. Returns
    ``(difference, gradient, moment_terms, valid)`` where ``moment_terms`` has a
    trailing axis of length 4.
    """
    m_i, m_j = r_i.mean(axis=-1), r_j.mean(axis=-1)
    g_i, g_j = (r_i**2).mean(axis=-1), (r_j**2).mean(axis=-1)
    v_i, v_j = g_i - m_i**2, g_j - m_j**2
    valid = (v_i > 0) & (v_j > 0)
    v_i = np.where(valid, v_i, 1.0)
    v_j = np.where(valid, v_j, 1.0)
    diff = m_i / np.sqrt(v_i) - m_j / np.sqrt(v_j)
    grad = np.stack(
        [g_i / v_i**1.5, -g_j / v_j**1.5, -0.5 * m_i / v_i**1.5, 0.5 * m_j / v_j**1.5], axis=-1
    )
    terms = np.stack(
        [
            r_i - m_i[..., None],
            r_j - m_j[..., None],
            r_i**2 - g_i[..., None],
            r_j**2 - g_j[..., None],
        ],
        axis=-1,
    )
    return diff, grad, terms, valid


def hac_sharpe_se(r_i: Array, r_j: Array, lags: int | None = None) -> float:
    """Newey-West standard error of the monthly Sharpe-ratio difference."""
    r_i, r_j = np.asarray(r_i, dtype=float), np.asarray(r_j, dtype=float)
    n = len(r_i)
    max_lag = newey_west_lags(n) if lags is None else lags
    _, grad, terms, _ = _difference_and_gradient(r_i, r_j)
    u = terms @ grad  # gradient times moment terms, one value per month
    long_run = float(u @ u) / n
    for lag in range(1, max_lag + 1):
        long_run += 2.0 * (1.0 - lag / (max_lag + 1.0)) * float(u[lag:] @ u[:-lag]) / n
    return float(np.sqrt(max(long_run, 0.0) / n))


def _block_indices(rng: np.random.Generator, n: int, block: int, draws: int) -> Array:
    """Circular block resampling: ``ceil(n / block)`` blocks per draw."""
    blocks = -(-n // block)
    starts = rng.integers(0, n, size=(draws, blocks))
    idx: Array = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    return idx.reshape(draws, blocks * block)


def sharpe_difference_bootstrap(
    r_i: Array,
    r_j: Array,
    block: int = BLOCK,
    draws: int = DRAWS,
    seed: int = 0,
    lags: int | None = None,
) -> BootstrapTest:
    """Two-sided test of equal Sharpe ratios, Ledoit and Wolf (2008), Section 3.2.

    The p-value is ``(1 + #{d* >= d}) / (draws + 1)``, where
    ``d = |diff| / se`` on the data and ``d* = |diff* - diff| / se*`` on each
    bootstrap sample.
    """
    r_i, r_j = np.asarray(r_i, dtype=float), np.asarray(r_j, dtype=float)
    n = len(r_i)
    if len(r_j) != n:
        raise ValueError("series must have the same length")
    if block < 1 or block > n:
        raise ValueError("block length must be between 1 and the sample size")
    diff, _, _, valid = _difference_and_gradient(r_i, r_j)
    se = hac_sharpe_se(r_i, r_j, lags)
    annual = float(np.sqrt(12.0))
    if not bool(valid) or se <= 0.0:
        return BootstrapTest(annual * float(diff), annual * se, float("nan"), block, draws)
    observed = abs(float(diff)) / se

    rng = np.random.default_rng(seed)
    exceed = 0
    done = 0
    while done < draws:
        size = min(_CHUNK, draws - done)
        idx = _block_indices(rng, n, block, size)
        b_i, b_j = r_i[idx], r_j[idx]
        d_star, grad, terms, ok = _difference_and_gradient(b_i, b_j)
        length = idx.shape[1]
        u = np.einsum("dtk,dk->dt", terms, grad)
        block_sums = u.reshape(size, length // block, block).sum(axis=2) / np.sqrt(block)
        se_star = np.sqrt((block_sums**2).mean(axis=1) / length)
        usable = np.logical_and(ok, se_star > 0)
        stat = np.abs(d_star - float(diff)) / np.where(usable, se_star, 1.0)
        exceed += int(np.sum(usable & (stat >= observed)))
        done += size
    p_value = (1.0 + exceed) / (draws + 1.0)
    return BootstrapTest(annual * float(diff), annual * se, p_value, block, draws)


def _garch_t_pair(
    rng: np.random.Generator, n: int, rho: float, burn: int = 200
) -> tuple[Array, Array]:
    """Two series with equal Sharpe ratios, Student-t(5) shocks and GARCH(1,1) volatility.

    Both share one volatility process, so they have volatility clusters at the
    same times, as a factor and its managed version do.
    """
    total = n + burn
    shocks = rng.standard_t(5, size=(total, 2)) / np.sqrt(5.0 / 3.0)
    shocks[:, 1] = rho * shocks[:, 0] + np.sqrt(1.0 - rho**2) * shocks[:, 1]
    omega, alpha, beta = 0.05, 0.10, 0.85
    var = np.empty(total)
    var[0] = omega / (1.0 - alpha - beta)
    for t in range(1, total):
        var[t] = omega + alpha * var[t - 1] * shocks[t - 1, 0] ** 2 + beta * var[t - 1]
    vol = np.sqrt(var[burn:])
    sharpe = 0.15  # monthly, about 0.5 a year
    base = 0.04 * vol / np.sqrt(omega / (1.0 - alpha - beta))
    r_i = base * (sharpe + shocks[burn:, 0])
    r_j = 2.0 * base * (sharpe + shocks[burn:, 1])  # twice the risk, same Sharpe ratio
    return r_i, r_j


def _normal_pair(rng: np.random.Generator, n: int, rho: float) -> tuple[Array, Array]:
    cov = 0.04**2 * np.array([[1.0, 2.0 * rho], [2.0 * rho, 4.0]])
    draw = rng.multivariate_normal([0.006, 0.012], cov, size=n)
    return draw[:, 0], draw[:, 1]


def size_study(
    sims: int = 1000,
    lengths: tuple[int, ...] = (120, 480),
    block: int = BLOCK,
    draws: int = 499,
    rho: float = 0.6,
    seed: int = 20261124,
) -> pd.DataFrame:
    """Rejection rates at 5% when the two true Sharpe ratios are equal.

    Two designs: independent normal returns, and Student-t(5) shocks with
    GARCH(1,1) volatility. Each row gives the share of ``sims`` simulated
    samples in which the Jobson-Korkie test and the bootstrap reject.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for design in ("iid normal", "GARCH(1,1), t(5) shocks"):
        for n in lengths:
            jk_reject = 0
            boot_reject = 0
            for k in range(sims):
                if design == "iid normal":
                    r_i, r_j = _normal_pair(rng, n, rho)
                else:
                    r_i, r_j = _garch_t_pair(rng, n, rho)
                jk_reject += int(jobson_korkie(r_i, r_j).p_value < 0.05)
                test = sharpe_difference_bootstrap(r_i, r_j, block, draws, seed=k)
                boot_reject += int(test.p_value < 0.05)
            rows.append(
                {
                    "design": design,
                    "months": n,
                    "simulations": sims,
                    "block": block,
                    "draws": draws,
                    "reject_jobson_korkie": jk_reject / sims,
                    "reject_bootstrap": boot_reject / sims,
                }
            )
    return pd.DataFrame.from_records(rows)
