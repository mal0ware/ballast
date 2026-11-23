"""Seeded synthetic factor returns, for tests and the CI smoke run.

These are not market data and nothing computed from them is a finding. Daily
returns have persistent volatility and a mean that does not depend on it, so
volatility management has something to work with.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ballast.data import FACTORS, FactorData


def synthetic_factors(
    seed: int = 20261123, start: str = "1926-07-01", end: str = "2026-09-30"
) -> FactorData:
    """Generate daily and monthly returns for the six factor names.

    Log variance follows an AR(1); monthly returns are compounded daily
    returns. RMW and CMA start in July 1963 and MOM in November 1926 (daily)
    and January 1927 (monthly), like the real files.
    """
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start, end, name="date")
    n = len(days)
    daily = {}
    for i, name in enumerate(FACTORS):
        log_var = np.empty(n)
        shocks = rng.normal(0.0, 0.12, n)
        log_var[0] = 0.0
        for t in range(1, n):
            log_var[t] = 0.985 * log_var[t - 1] + shocks[t]
        vol = (0.004 + 0.001 * i) * np.exp(0.5 * log_var)
        daily[name] = 0.0002 + vol * rng.standard_normal(n)
    daily_frame = pd.DataFrame(daily, index=days)
    monthly_frame = (
        (1.0 + daily_frame).groupby(daily_frame.index.to_period("M")).prod() - 1.0
    ).rename_axis("month")

    daily_frame.loc[daily_frame.index < "1926-11-03", "MOM"] = np.nan
    monthly_frame.loc[monthly_frame.index < pd.Period("1927-01", "M"), "MOM"] = np.nan
    for name in ("RMW", "CMA"):
        daily_frame.loc[daily_frame.index < "1963-07-01", name] = np.nan
        monthly_frame.loc[monthly_frame.index < pd.Period("1963-07", "M"), name] = np.nan
    manifest = {"source": "synthetic", "seed": seed}
    return FactorData(daily=daily_frame, monthly=monthly_frame, manifest=manifest)
