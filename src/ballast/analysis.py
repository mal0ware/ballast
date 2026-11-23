"""The tables behind every number in the README.

Each function takes :class:`ballast.data.FactorData` and a sample window and
returns a ``DataFrame`` with one row per factor. Nothing here reads files or
draws; ``scripts/reproduce.py`` does that.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ballast.data import FACTORS, FactorData
from ballast.managed import ManagedFactor, VarianceMethod, build_managed, realized_variance
from ballast.perf import (
    cer_difference_test,
    certainty_equivalent,
    jobson_korkie,
    sharpe_ratio,
)
from ballast.realtime import Window, ex_post_combination, real_time_combination
from ballast.regress import CovType, spanning_regression

FF3 = ["MKT", "SMB", "HML"]


def managed_factor(
    data: FactorData,
    name: str,
    method: VarianceMethod,
    start: str | None = None,
    end: str | None = None,
) -> ManagedFactor:
    """Managed version of one factor over ``[start, end]``."""
    rv = realized_variance(data.daily[name], method)
    return build_managed(data.monthly[name], rv, start=start, end=end)


def spanning_table(
    data: FactorData,
    start: str | None = None,
    end: str | None = None,
    method: VarianceMethod = "mm",
    cov_type: CovType = "HC0",
) -> pd.DataFrame:
    """Moreira and Muir's Table 1: managed on unmanaged, factor by factor.

    Columns ending in ``_ff3`` come from the regression that adds the three
    Fama-French factors (their Panel B).
    """
    rows = {}
    for name in FACTORS:
        m = managed_factor(data, name, method, start, end)
        fit = spanning_regression(m.managed, m.original, cov_type=cov_type)
        fit_ff3 = spanning_regression(
            m.managed, m.original, controls=data.monthly[FF3], cov_type=cov_type
        )
        rows[name] = {
            "first_month": str(m.original.index[0]),
            "last_month": str(m.original.index[-1]),
            "nobs": fit.nobs,
            "alpha": fit.alpha,
            "alpha_se": fit.alpha_se,
            "alpha_t": fit.alpha_t,
            "beta": fit.beta,
            "beta_se": fit.beta_se,
            "r2": fit.r2,
            "r2_adj": fit.r2_adj,
            "rmse": fit.rmse,
            "appraisal_ratio": fit.appraisal_ratio,
            "alpha_ff3": fit_ff3.alpha,
            "alpha_ff3_se": fit_ff3.alpha_se,
            "alpha_ff3_t": fit_ff3.alpha_t,
            "c_star": 1e4 * m.c,
            "weight_p01": float(m.weight.quantile(0.01)),
            "weight_p50": float(m.weight.quantile(0.50)),
            "weight_p99": float(m.weight.quantile(0.99)),
            # Average size of the monthly change in the position, in units of
            # the factor's own notional. A rough gauge of the extra trading.
            "mean_abs_weight_change": float(m.weight.diff().abs().mean()),
        }
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("factor")


def direct_table(
    data: FactorData,
    start: str | None = None,
    end: str | None = None,
    method: VarianceMethod = "cowy",
) -> pd.DataFrame:
    """Cederburg et al.'s Table 1: Sharpe ratio of managed against unmanaged.

    The Sharpe ratio of the managed factor does not depend on ``c``, so this
    comparison is the same in sample and in real time.
    """
    rows = {}
    for name in FACTORS:
        m = managed_factor(data, name, method, start, end)
        original = m.original.to_numpy()
        managed = m.managed.to_numpy()
        test = jobson_korkie(managed, original)
        rows[name] = {
            "first_month": str(m.original.index[0]),
            "last_month": str(m.original.index[-1]),
            "nobs": len(original),
            "sr_original": sharpe_ratio(original),
            "sr_managed": sharpe_ratio(managed),
            "sr_diff": test.difference,
            "sr_z": test.z,
            "sr_p": test.p_value,
            "correlation": float(np.corrcoef(managed, original)[0, 1]),
        }
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("factor")


def real_time_table(
    data: FactorData,
    end: str | None = None,
    evaluate_from: str | None = None,
    method: VarianceMethod = "cowy",
    training_months: int = 120,
    gamma: float = 5.0,
    leverage_cap: float | None = 5.0,
    window: Window = "expanding",
) -> pd.DataFrame:
    """Cederburg et al.'s Table 5, Panel A: the real-time combination strategy.

    Args:
        data: Factor returns.
        end: Last month of the sample.
        evaluate_from: Score only months from this one on. Training still
            starts at the beginning of each factor's history.
        method: Realized-variance definition.
        training_months: Initial training period ``K``.
        gamma: Risk aversion.
        leverage_cap: Bound on the absolute factor position.
        window: Expanding or rolling estimation window.
    """
    rows = {}
    for name in FACTORS:
        m = managed_factor(data, name, method, None, end)
        result = real_time_combination(
            m.original, m.inverse_variance, training_months, gamma, leverage_cap, window
        )
        frame = result.frame
        if evaluate_from is not None:
            frame = frame.loc[frame.index >= pd.Period(evaluate_from, "M")]
        combo = frame["return_combo"].to_numpy()
        original = frame["return_original"].to_numpy()
        expost = ex_post_combination(
            m.original.loc[frame.index].to_numpy(),
            m.inverse_variance.loc[frame.index].to_numpy(),
            gamma,
        )
        sr = jobson_korkie(combo, original)
        cer = cer_difference_test(combo, original, gamma)
        sr_x = jobson_korkie(combo, expost)
        cer_x = cer_difference_test(combo, expost, gamma)
        rows[name] = {
            "first_month": str(frame.index[0]),
            "last_month": str(frame.index[-1]),
            "nobs": len(frame),
            "sr_combo": sharpe_ratio(combo),
            "sr_original": sharpe_ratio(original),
            "sr_diff": sr.difference,
            "sr_z": sr.z,
            "sr_p": sr.p_value,
            "sr_expost": sharpe_ratio(expost),
            "sr_diff_expost": sr_x.difference,
            "sr_p_expost": sr_x.p_value,
            "cer_combo": certainty_equivalent(combo, gamma),
            "cer_original": certainty_equivalent(original, gamma),
            "cer_diff": cer.difference,
            "cer_z": cer.z,
            "cer_p": cer.p_value,
            "cer_expost": certainty_equivalent(expost, gamma),
            "cer_diff_expost": cer_x.difference,
            "cer_p_expost": cer_x.p_value,
            "mean_abs_position": float(frame["position_combo"].abs().mean()),
            "share_at_cap": float(
                (frame["position_combo"].abs() >= leverage_cap - 1e-12).mean()
                if leverage_cap is not None
                else 0.0
            ),
        }
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("factor")


def compare_cells(
    ours: pd.DataFrame, paper: dict[str, dict[str, float]], table: str
) -> pd.DataFrame:
    """Line up our figures with a paper's, one row per printed cell.

    ``differs`` is true when our figure, rounded as the paper rounds (two
    decimals, or a whole number for ``nobs``), is not the printed figure.
    """
    records = []
    for factor, cells in paper.items():
        for statistic, printed in cells.items():
            value = float(ours.loc[factor, statistic])
            digits = 0 if statistic == "nobs" else 2
            records.append(
                {
                    "table": table,
                    "factor": factor,
                    "statistic": statistic,
                    "paper": printed,
                    "ours": round(value, 4),
                    "difference": round(value - printed, 4),
                    "differs": round(value, digits) != round(printed, digits),
                }
            )
    return pd.DataFrame.from_records(records)


def drawdown(returns: pd.Series) -> float:
    """Largest peak-to-trough loss of the compounded series, as a negative decimal."""
    wealth = (1.0 + returns).cumprod()
    peak = wealth.cummax().clip(lower=1.0)
    return float((wealth / peak - 1.0).min())


def momentum_crash(
    data: FactorData,
    end: str | None = None,
    window: tuple[str, str] = ("2008-01", "2010-12"),
    crash: tuple[str, str] = ("2009-03", "2009-05"),
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Momentum through the 2009 crash, managed and unmanaged.

    The managed series uses Moreira and Muir's construction with ``c`` from the
    whole sample to ``end``. The real-time columns use Cederburg et al.'s
    strategy, whose positions use only earlier months.

    Returns:
        ``(monthly, summary, worst)``: the month-by-month path over ``window``;
        compounded returns and drawdowns over ``crash`` and ``window``; and the
        ten worst months of the unmanaged factor with the managed return beside
        each.
    """
    m = managed_factor(data, "MOM", "mm", None, end)
    m_rt = managed_factor(data, "MOM", "cowy", None, end)
    rt = real_time_combination(m_rt.original, m_rt.inverse_variance).frame
    full = pd.DataFrame(
        {
            "mom": m.original,
            "prior_month_vol_annual": np.sqrt(12.0 / m.inverse_variance),
            "weight": m.weight,
            "managed": m.managed,
            "rt_position": rt["position_combo"],
            "rt_return": rt["return_combo"],
            "rt_benchmark_position": rt["position_original"],
            "rt_benchmark_return": rt["return_original"],
        }
    )
    lo, hi = pd.Period(window[0], "M"), pd.Period(window[1], "M")
    monthly = full.loc[(full.index >= lo) & (full.index <= hi)]
    c_lo, c_hi = pd.Period(crash[0], "M"), pd.Period(crash[1], "M")
    in_crash = monthly.loc[(monthly.index >= c_lo) & (monthly.index <= c_hi)]

    labels = {
        "mom": "unmanaged",
        "managed": "managed (full-sample c)",
        "rt_return": "real-time combination",
        "rt_benchmark_return": "real-time unmanaged benchmark",
    }
    summary_rows = {}
    for column, label in labels.items():
        summary_rows[label] = {
            "crash_return": float((1.0 + in_crash[column]).prod() - 1.0),
            "worst_month": float(monthly[column].min()),
            "window_return": float((1.0 + monthly[column]).prod() - 1.0),
            "window_max_drawdown": drawdown(monthly[column]),
            "full_sample_skewness": float(full[column].dropna().skew()),
            "full_sample_worst_month": float(full[column].min()),
        }
    summary = pd.DataFrame.from_dict(summary_rows, orient="index").rename_axis("series")

    worst = full.nsmallest(10, "mom")[["mom", "prior_month_vol_annual", "weight", "managed"]]
    return monthly, summary, worst
