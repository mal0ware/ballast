"""Trading costs charged on changes in the position.

A position is measured in units of the factor's own notional: 1.0 means the
plain factor, 0.5 half of it. Moving the position from ``w[t-1]`` to ``w[t]``
trades ``|w[t] - w[t-1]|`` units, and a cost of ``k`` basis points per unit
takes ``k / 10000 * |w[t] - w[t-1]|`` off that month's return.

For a long-short factor one unit is one dollar long and one dollar short, so
10 bps per unit is 5 bps on each dollar traded on each side. For the market
factor one unit is one dollar of the market.

Only the trading that scaling causes is charged. The plain factor holds a
constant position and pays nothing here. Both pay the factor's own rebalancing
costs, which the French returns already ignore and which this module does not
add. The first month of any series is charged nothing, because both strategies
open a position then.
"""

from __future__ import annotations

import pandas as pd

#: Cost levels reported, in basis points per unit of turnover.
COST_LEVELS_BPS: tuple[float, ...] = (0.0, 10.0, 25.0, 50.0)


def turnover(position: pd.Series) -> pd.Series:
    """``|w[t] - w[t-1]|`` with zero in the first month."""
    return position.diff().abs().fillna(0.0).rename("turnover")


def net_of_costs(gross: pd.Series, position: pd.Series, bps: float) -> pd.Series:
    """Monthly return after charging ``bps`` per unit of turnover."""
    return (gross - bps / 1e4 * turnover(position)).rename(gross.name)
