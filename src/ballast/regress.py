"""Least squares with robust standard errors, and the spanning regression.

The spanning regression is Moreira and Muir's equation (3):
``managed[t] = alpha + beta * original[t] + e[t]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from ballast._types import Array

CovType = Literal["nonrobust", "HC0", "HC1", "HAC"]


def newey_west_lags(n: int) -> int:
    """The usual automatic lag length, ``floor(4 * (n / 100) ** (2 / 9))``."""
    return int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))


@dataclass(frozen=True)
class OLSResult:
    """Coefficients and summary figures from one regression."""

    params: Array
    se: Array
    tstats: Array
    resid: Array
    nobs: int
    r2: float
    r2_adj: float
    #: ``sqrt(SSR / (n - k))``, the standard error of the regression.
    rmse: float


def ols(y: Array, x: Array, cov_type: CovType = "HC0", lags: int | None = None) -> OLSResult:
    """Regress ``y`` on ``x`` plus a constant.

    Args:
        y: Dependent variable, length ``n``.
        x: Regressors without the constant, shape ``(n,)`` or ``(n, p)``.
        cov_type: ``"HC0"`` is White (1980); ``"HC1"`` multiplies it by
            ``n / (n - k)``; ``"nonrobust"`` is the classical estimate;
            ``"HAC"`` is Newey and West (1987) with Bartlett weights and no
            small-sample correction.
        lags: Lag length for ``"HAC"``. ``None`` uses :func:`newey_west_lags`.

    Returns:
        Results with the constant first in ``params``.
    """
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    n = y.shape[0]
    design = np.column_stack([np.ones(n), x])
    k = design.shape[1]
    if n <= k:
        raise ValueError("need more observations than coefficients")
    xtx_inv = np.linalg.inv(design.T @ design)
    params = xtx_inv @ design.T @ y
    resid = y - design @ params
    ssr = float(resid @ resid)
    if cov_type == "nonrobust":
        cov = xtx_inv * ssr / (n - k)
    elif cov_type in ("HC0", "HC1"):
        meat = (design * resid[:, None] ** 2).T @ design
        cov = xtx_inv @ meat @ xtx_inv
        if cov_type == "HC1":
            cov = cov * n / (n - k)
    elif cov_type == "HAC":
        max_lag = newey_west_lags(n) if lags is None else lags
        scores = design * resid[:, None]
        meat = scores.T @ scores
        for lag in range(1, max_lag + 1):
            gamma = scores[lag:].T @ scores[:-lag]
            meat += (1.0 - lag / (max_lag + 1.0)) * (gamma + gamma.T)
        cov = xtx_inv @ meat @ xtx_inv
    else:
        raise ValueError(f"unknown cov_type {cov_type!r}")
    se = np.sqrt(np.diag(cov))
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ssr / sst
    return OLSResult(
        params=params,
        se=se,
        tstats=params / se,
        resid=resid,
        nobs=n,
        r2=r2,
        r2_adj=1.0 - (1.0 - r2) * (n - 1) / (n - k),
        rmse=float(np.sqrt(ssr / (n - k))),
    )


@dataclass(frozen=True)
class SpanningResult:
    """A spanning regression in the units the papers print.

    Alpha and RMSE are in percent per year (monthly figure times 1200). The
    appraisal ratio is ``sqrt(12) * alpha / rmse`` on monthly figures.
    """

    alpha: float
    alpha_se: float
    alpha_t: float
    beta: float
    beta_se: float
    beta_t: float
    nobs: int
    r2: float
    r2_adj: float
    rmse: float
    appraisal_ratio: float


def spanning_regression(
    managed: pd.Series,
    original: pd.Series,
    controls: pd.DataFrame | None = None,
    cov_type: CovType = "HC0",
    lags: int | None = None,
) -> SpanningResult:
    """Regress the managed factor on the original factor, with optional controls.

    Args:
        managed: Managed monthly returns as decimals.
        original: Unmanaged monthly returns on the same index.
        controls: Extra regressors on the same index, such as the three
            Fama-French factors. Columns equal to ``original`` are dropped.
        cov_type: Covariance estimator for the standard errors.
        lags: Lag length when ``cov_type`` is ``"HAC"``.
    """
    regressors = [original.to_numpy()]
    if controls is not None:
        aligned = controls.loc[managed.index]
        for name in aligned.columns:
            column = aligned[name].to_numpy()
            if not np.allclose(column, original.to_numpy()):
                regressors.append(column)
    fit = ols(managed.to_numpy(), np.column_stack(regressors), cov_type, lags)
    return SpanningResult(
        alpha=1200.0 * fit.params[0],
        alpha_se=1200.0 * fit.se[0],
        alpha_t=float(fit.tstats[0]),
        beta=float(fit.params[1]),
        beta_se=float(fit.se[1]),
        beta_t=float(fit.tstats[1]),
        nobs=fit.nobs,
        r2=fit.r2,
        r2_adj=fit.r2_adj,
        rmse=1200.0 * fit.rmse,
        appraisal_ratio=float(np.sqrt(12.0) * fit.params[0] / fit.rmse),
    )
