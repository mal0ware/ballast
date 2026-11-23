"""The real-time combination strategy of Cederburg et al. (2020), Section 4.3.1.

At the start of each month ``t`` after an initial training period, the investor
uses only months before ``t`` to estimate

* ``c[t]``, the constant that equates the variances of the managed and
  unmanaged factor over the training months, and
* the mean vector and covariance matrix of the two series, which give the
  mean-variance weights of their equation (15),
  ``[x_sigma, x] = inverse(Sigma) @ mu / gamma``.

The position in the factor is their equation (16),
``y[t] = x_sigma[t] * c[t] / RV[t-1] + x[t]``, capped in absolute value. The
benchmark holds ``mean / (gamma * variance)`` of the factor, estimated on the
same training months and capped the same way.

``y[t]`` does not depend on ``c[t]``: rescaling the managed series by ``k``
divides ``x_sigma`` by ``k``. What the investor cannot know in advance is the
pair of weights, which the test suite checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from ballast._types import Array
from ballast.managed import scale_constant

Window = Literal["expanding", "rolling"]


def _clip(value: float, cap: float | None) -> float:
    return value if cap is None else float(np.clip(value, -cap, cap))


def mean_variance_weights(returns: Array, gamma: float) -> Array:
    """``inverse(Sigma) @ mu / gamma`` for the columns of ``returns``."""
    mu = returns.mean(axis=0)
    sigma = np.atleast_2d(np.cov(returns, rowvar=False, ddof=1))
    weights: Array = np.linalg.solve(sigma, mu) / gamma
    return weights


@dataclass(frozen=True)
class RealTimeResult:
    """Out-of-sample positions and returns, one row per month after training."""

    #: Columns: ``c``, ``x_sigma``, ``x``, ``position_combo``, ``position_original``,
    #: ``return_combo``, ``return_original``, ``factor``.
    frame: pd.DataFrame

    @property
    def combo(self) -> Array:
        """Returns of the strategy that can use the managed factor."""
        return np.asarray(self.frame["return_combo"], dtype=np.float64)

    @property
    def original(self) -> Array:
        """Returns of the strategy limited to the unmanaged factor."""
        return np.asarray(self.frame["return_original"], dtype=np.float64)


def real_time_combination(
    original: pd.Series,
    inverse_variance: pd.Series,
    training_months: int = 120,
    gamma: float = 5.0,
    leverage_cap: float | None = 5.0,
    window: Window = "expanding",
) -> RealTimeResult:
    """Run the real-time strategy and its unmanaged benchmark.

    Args:
        original: Monthly factor excess returns ``f[t]``.
        inverse_variance: ``1 / RV[t-1]`` on the same index; the entry for
            month ``t`` is known at the start of month ``t``.
        training_months: Length ``K`` of the initial training period. The
            first out-of-sample month is month ``K + 1`` of the sample.
        gamma: Risk aversion of the mean-variance investor.
        leverage_cap: Bound on the absolute position in the factor, or ``None``.
        window: ``"expanding"`` uses every earlier month; ``"rolling"`` uses the
            latest ``training_months``.

    Returns:
        Positions and returns for months ``K + 1`` to ``T``.
    """
    if not original.index.equals(inverse_variance.index):
        raise ValueError("series must share an index")
    f = original.to_numpy(dtype=float)
    iv = inverse_variance.to_numpy(dtype=float)
    total = len(f)
    if total <= training_months:
        raise ValueError("sample is not longer than the training period")

    rows = []
    for t in range(training_months, total):
        first = 0 if window == "expanding" else t - training_months
        f_train = f[first:t]
        iv_train = iv[first:t]
        c_t = scale_constant(f_train, iv_train)
        managed_train = c_t * iv_train * f_train
        x_sigma, x = mean_variance_weights(np.column_stack([managed_train, f_train]), gamma)
        position_combo = _clip(float(x_sigma * c_t * iv[t] + x), leverage_cap)
        position_original = _clip(
            float(f_train.mean() / (gamma * f_train.var(ddof=1))), leverage_cap
        )
        rows.append(
            (
                c_t,
                float(x_sigma),
                float(x),
                position_combo,
                position_original,
                position_combo * f[t],
                position_original * f[t],
                f[t],
            )
        )
    frame = pd.DataFrame(
        rows,
        index=original.index[training_months:],
        columns=[
            "c",
            "x_sigma",
            "x",
            "position_combo",
            "position_original",
            "return_combo",
            "return_original",
            "factor",
        ],
    )
    return RealTimeResult(frame=frame)


def ex_post_combination(original: Array, inverse_variance: Array, gamma: float = 5.0) -> Array:
    """Returns of the combination with ``c`` and weights fixed from the whole sample given.

    This is the strategy a spanning regression implies (Cederburg et al.,
    equations (7) and (11)). It is not available in real time and carries no
    leverage cap.
    """
    c = scale_constant(original, inverse_variance)
    managed = c * inverse_variance * original
    x_sigma, x = mean_variance_weights(np.column_stack([managed, original]), gamma)
    result: Array = (x_sigma * c * inverse_variance + x) * original
    return result
