"""Volatility-managed factors as in Moreira and Muir (2017), equations (1) and (2).

The managed return in month ``t`` is ``c / RV[t-1] * f[t]``: the factor return
scaled by the inverse of last month's realized variance. The constant ``c`` is
set so that the managed and unmanaged series have the same unconditional
variance over the sample in use. That makes ``c`` a full-sample quantity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from ballast._types import Array

VarianceMethod = Literal["mm", "cowy"]


def realized_variance(daily: pd.Series, method: VarianceMethod = "mm") -> pd.Series:
    """Monthly realized variance from daily returns.

    Args:
        daily: Daily returns with a ``DatetimeIndex``. Missing days are dropped.
        method: ``"mm"`` is Moreira and Muir's equation (2), the sum of squared
            deviations from the month's mean daily return. ``"cowy"`` is
            Cederburg et al.'s equation (4), ``22 / J`` times the sum of squared
            daily returns, where ``J`` is the number of trading days.

    Returns:
        One value per calendar month with at least two daily returns, indexed
        by monthly period.
    """
    clean = daily.dropna()
    if not isinstance(clean.index, pd.DatetimeIndex):
        raise TypeError("daily returns need a DatetimeIndex")
    groups = clean.groupby(clean.index.to_period("M"))
    counts = groups.count()
    if method == "mm":
        rv = groups.apply(lambda x: float(((x - x.mean()) ** 2).sum()))
    elif method == "cowy":
        rv = groups.apply(lambda x: float(22.0 / len(x) * (x**2).sum()))
    else:
        raise ValueError(f"unknown method {method!r}")
    rv = rv[counts >= 2]
    rv.index.name = "month"
    return rv.rename("rv")


def scale_constant(factor: Array, inverse_variance: Array) -> float:
    """The ``c`` that gives ``c * factor * inverse_variance`` the variance of ``factor``."""
    unscaled = factor * inverse_variance
    return float(np.std(factor, ddof=1) / np.std(unscaled, ddof=1))


@dataclass(frozen=True)
class ManagedFactor:
    """A factor, its lagged inverse variance, and the managed series.

    All series share one monthly index: the months in the sample for which both
    the factor return and the previous month's realized variance exist.
    """

    #: Unmanaged monthly excess return ``f[t]``.
    original: pd.Series
    #: ``1 / RV[t-1]``, known at the start of month ``t``.
    inverse_variance: pd.Series
    #: The constant ``c``, from the whole of this sample.
    c: float
    #: Managed monthly return ``c / RV[t-1] * f[t]``.
    managed: pd.Series

    @property
    def weight(self) -> pd.Series:
        """Position in the original factor, ``c / RV[t-1]``."""
        return (self.c * self.inverse_variance).rename("weight")


def build_managed(
    monthly: pd.Series,
    rv: pd.Series,
    start: pd.Period | str | None = None,
    end: pd.Period | str | None = None,
) -> ManagedFactor:
    """Build the managed factor over ``[start, end]`` (both inclusive).

    Args:
        monthly: Monthly factor returns indexed by monthly period.
        rv: Monthly realized variance from :func:`realized_variance`.
        start: First month of managed returns to keep, or ``None`` for the earliest.
        end: Last month to keep, or ``None`` for the latest.
    """
    lagged = rv.copy()
    lagged.index = lagged.index + 1  # RV of month t-1 lines up with month t
    frame = pd.DataFrame({"f": monthly, "rv_lag": lagged}).dropna()
    frame = frame.loc[
        (frame.index >= (pd.Period(start, "M") if start is not None else frame.index[0]))
        & (frame.index <= (pd.Period(end, "M") if end is not None else frame.index[-1]))
    ]
    if len(frame) < 3:
        raise ValueError("fewer than three months in the sample")
    if (frame["rv_lag"] <= 0).any():
        raise ValueError("realized variance must be positive")
    original = frame["f"].rename("original")
    inverse_variance = (1.0 / frame["rv_lag"]).rename("inverse_variance")
    c = scale_constant(original.to_numpy(), inverse_variance.to_numpy())
    managed = (c * inverse_variance * original).rename("managed")
    return ManagedFactor(original=original, inverse_variance=inverse_variance, c=c, managed=managed)
