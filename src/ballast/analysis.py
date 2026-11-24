"""The tables behind every number in the README.

Each function takes :class:`ballast.data.FactorData` and a sample window and
returns a ``DataFrame`` with one row per factor. Nothing here reads files or
draws; ``scripts/reproduce.py`` does that.
"""

from __future__ import annotations

from functools import partial

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from ballast._types import Array
from ballast.bootstrap import BLOCK, DRAWS, sharpe_difference_bootstrap
from ballast.costs import COST_LEVELS_BPS, net_of_costs, turnover
from ballast.data import FACTORS, FactorData
from ballast.managed import ManagedFactor, VarianceMethod, build_managed, realized_variance
from ballast.perf import (
    cer_difference_test,
    certainty_equivalent,
    holm,
    jobson_korkie,
    sharpe_ratio,
    two_sided_p,
)
from ballast.realtime import Window, ex_post_combination, real_time_combination
from ballast.regress import CovType, newey_west_lags, spanning_regression

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
        fit_nw = spanning_regression(m.managed, m.original, cov_type="HAC")
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
            "nw_lags": newey_west_lags(fit.nobs),
            "alpha_se_nw": fit_nw.alpha_se,
            "alpha_t_nw": fit_nw.alpha_t,
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
    table = pd.DataFrame.from_dict(rows, orient="index").rename_axis("factor")
    table["alpha_p_nw"] = two_sided_p(table["alpha_t_nw"].to_numpy())
    table["alpha_p_nw_holm"] = holm(table["alpha_p_nw"].to_numpy())
    return table


def _holm_by_cost(table: pd.DataFrame, column: str) -> pd.Series:
    """Holm-adjust ``column`` across factors within each cost level."""
    adjusted = pd.Series(np.nan, index=table.index)
    for _, group in table.groupby("cost_bps"):
        adjusted.loc[group.index] = holm(group[column].to_numpy())
    return adjusted


def spanning_costs_table(
    data: FactorData,
    start: str | None = None,
    end: str | None = None,
    method: VarianceMethod = "mm",
    costs: tuple[float, ...] = COST_LEVELS_BPS,
) -> pd.DataFrame:
    """In-sample alpha after charging for the trading that scaling causes.

    The managed return is charged ``cost`` bps per unit change in its weight
    ``c / RV[t-1]`` and regressed on the gross unmanaged factor, with
    Newey-West standard errors. The regression is linear in the dependent
    variable, so the net alpha falls in a straight line as the cost rises;
    ``break_even_bps`` is where it reaches zero (NaN without a positive gross
    alpha). ``significant_up_to_bps`` is the highest cost at which the
    Newey-West t-statistic is still at least 1.96 (NaN if it is below 1.96
    gross). Holm adjustments are across the six factors at each cost level.
    """
    rows = []
    for name in FACTORS:
        m = managed_factor(data, name, method, start, end)
        trade = turnover(m.weight)
        gross = spanning_regression(m.managed, m.original, cov_type="HAC")
        drag = spanning_regression(trade, m.original, cov_type="HAC")
        if gross.alpha > 0.0 and drag.alpha > 0.0:
            break_even = 1e4 * gross.alpha / drag.alpha
        else:
            break_even = float("nan")
        if gross.alpha_t >= 1.96 and np.isfinite(break_even):
            gap = partial(_alpha_t_gap, m)
            significant_up_to = float(brentq(gap, 0.0, break_even, xtol=1e-6))
        else:
            significant_up_to = float("nan")
        for bps in costs:
            fit = spanning_regression(
                net_of_costs(m.managed, m.weight, bps), m.original, cov_type="HAC"
            )
            rows.append(
                {
                    "factor": name,
                    "cost_bps": bps,
                    "first_month": str(m.original.index[0]),
                    "last_month": str(m.original.index[-1]),
                    "nobs": fit.nobs,
                    "turnover_per_month": float(trade.mean()),
                    "alpha": fit.alpha,
                    "alpha_se_nw": fit.alpha_se,
                    "alpha_t_nw": fit.alpha_t,
                    "appraisal_ratio": fit.appraisal_ratio,
                    "break_even_bps": break_even,
                    "significant_up_to_bps": significant_up_to,
                }
            )
    table = pd.DataFrame.from_records(rows)
    table["alpha_p_nw"] = two_sided_p(table["alpha_t_nw"].to_numpy())
    table["alpha_p_nw_holm"] = _holm_by_cost(table, "alpha_p_nw")
    return table.set_index(["factor", "cost_bps"])


def direct_table(
    data: FactorData,
    start: str | None = None,
    end: str | None = None,
    method: VarianceMethod = "cowy",
    draws: int = DRAWS,
) -> pd.DataFrame:
    """Cederburg et al.'s Table 1: Sharpe ratio of managed against unmanaged.

    The Sharpe ratio of the managed factor does not depend on ``c``, so this
    comparison is the same in sample and in real time. ``sr_p_boot`` is the
    block-bootstrap p-value from :mod:`ballast.bootstrap` with ``draws`` draws.
    """
    rows = {}
    for name in FACTORS:
        m = managed_factor(data, name, method, start, end)
        original = m.original.to_numpy()
        managed = m.managed.to_numpy()
        test = jobson_korkie(managed, original)
        boot = sharpe_difference_bootstrap(managed, original, draws=draws)
        rows[name] = {
            "first_month": str(m.original.index[0]),
            "last_month": str(m.original.index[-1]),
            "nobs": len(original),
            "sr_original": sharpe_ratio(original),
            "sr_managed": sharpe_ratio(managed),
            "sr_diff": test.difference,
            "sr_z": test.z,
            "sr_p": test.p_value,
            "sr_p_boot": boot.p_value,
            "correlation": float(np.corrcoef(managed, original)[0, 1]),
        }
    table = pd.DataFrame.from_dict(rows, orient="index").rename_axis("factor")
    table["sr_p_boot_holm"] = holm(table["sr_p_boot"].to_numpy())
    return table


def real_time_table(
    data: FactorData,
    end: str | None = None,
    evaluate_from: str | None = None,
    method: VarianceMethod = "cowy",
    training_months: int = 120,
    gamma: float = 5.0,
    leverage_cap: float | None = 5.0,
    window: Window = "expanding",
    draws: int = DRAWS,
    block: int = BLOCK,
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
        draws: Bootstrap draws for ``sr_p_boot``.
        block: Bootstrap block length in months.

    Holm-adjusted p-values (``*_holm``) are across the six factors.
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
        boot = sharpe_difference_bootstrap(combo, original, block, draws)
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
            "sr_p_boot": boot.p_value,
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
            "turnover_combo": float(
                turnover(result.frame["position_combo"]).loc[frame.index].mean()
            ),
            "turnover_original": float(
                turnover(result.frame["position_original"]).loc[frame.index].mean()
            ),
            "share_at_cap": float(
                (frame["position_combo"].abs() >= leverage_cap - 1e-12).mean()
                if leverage_cap is not None
                else 0.0
            ),
        }
    table = pd.DataFrame.from_dict(rows, orient="index").rename_axis("factor")
    table["sr_p_holm"] = holm(table["sr_p"].to_numpy())
    table["sr_p_boot_holm"] = holm(table["sr_p_boot"].to_numpy())
    return table


def _real_time_net(full: pd.DataFrame, index: pd.Index, bps: float) -> tuple[Array, Array]:
    """Net returns of the combination and the benchmark over ``index``."""
    combo = net_of_costs(full["return_combo"], full["position_combo"], bps)
    original = net_of_costs(full["return_original"], full["position_original"], bps)
    return combo.loc[index].to_numpy(), original.loc[index].to_numpy()


def _real_time_gain(full: pd.DataFrame, index: pd.Index, bps: float) -> float:
    combo, original = _real_time_net(full, index, bps)
    return sharpe_ratio(combo) - sharpe_ratio(original)


def _alpha_t_gap(m: ManagedFactor, bps: float) -> float:
    net = net_of_costs(m.managed, m.weight, bps)
    return spanning_regression(net, m.original, cov_type="HAC").alpha_t - 1.96


def real_time_costs_table(
    data: FactorData,
    end: str | None = None,
    evaluate_from: str | None = None,
    method: VarianceMethod = "cowy",
    costs: tuple[float, ...] = COST_LEVELS_BPS,
    gamma: float = 5.0,
    draws: int = DRAWS,
) -> pd.DataFrame:
    """The real-time strategy and its benchmark, both charged for trading.

    Each strategy pays ``cost`` bps per unit change in its own position. The
    benchmark's position moves only as its estimates move, so it pays little.
    ``break_even_bps`` is the cost at which the Sharpe-ratio gain reaches zero
    (NaN when there is no gross gain, infinite when the gain survives 1,000
    bps). P-values are Jobson-Korkie and the block bootstrap; Holm adjustments
    are across the six factors at each cost level.
    """
    rows = []
    for name in FACTORS:
        m = managed_factor(data, name, method, None, end)
        full = real_time_combination(m.original, m.inverse_variance, gamma=gamma).frame
        if evaluate_from is None:
            index = full.index
        else:
            index = full.index[full.index >= pd.Period(evaluate_from, "M")]
        trade_combo = turnover(full["position_combo"])
        trade_original = turnover(full["position_original"])
        gain = partial(_real_time_gain, full, index)
        if gain(0.0) <= 0.0:
            break_even = float("nan")
        elif gain(1000.0) > 0.0:
            break_even = float("inf")
        else:
            break_even = float(brentq(gain, 0.0, 1000.0, xtol=1e-6))
        for bps in costs:
            combo, original = _real_time_net(full, index, bps)
            sr = jobson_korkie(combo, original)
            boot = sharpe_difference_bootstrap(combo, original, draws=draws)
            rows.append(
                {
                    "factor": name,
                    "cost_bps": bps,
                    "first_month": str(index[0]),
                    "last_month": str(index[-1]),
                    "nobs": len(combo),
                    "turnover_combo": float(trade_combo.loc[index].mean()),
                    "turnover_original": float(trade_original.loc[index].mean()),
                    "sr_combo": sharpe_ratio(combo),
                    "sr_original": sharpe_ratio(original),
                    "sr_diff": sr.difference,
                    "sr_p": sr.p_value,
                    "sr_p_boot": boot.p_value,
                    "cer_diff": certainty_equivalent(combo, gamma)
                    - certainty_equivalent(original, gamma),
                    "break_even_bps": break_even,
                }
            )
    table = pd.DataFrame.from_records(rows)
    table["sr_p_holm"] = _holm_by_cost(table, "sr_p")
    table["sr_p_boot_holm"] = _holm_by_cost(table, "sr_p_boot")
    return table.set_index(["factor", "cost_bps"])


def block_length_table(
    data: FactorData,
    end: str | None = None,
    blocks: tuple[int, ...] = (1, 3, 6, 12, 24),
    draws: int = DRAWS,
    method: VarianceMethod = "cowy",
) -> pd.DataFrame:
    """Bootstrap p-values of the gross real-time Sharpe gain at several block lengths.

    A block of one month resamples single months, which ignores serial
    dependence. The reported results use :data:`ballast.bootstrap.BLOCK`.
    """
    rows = {}
    for name in FACTORS:
        m = managed_factor(data, name, method, None, end)
        result = real_time_combination(m.original, m.inverse_variance)
        row: dict[str, float | str] = {
            "first_month": str(result.frame.index[0]),
            "last_month": str(result.frame.index[-1]),
            "sr_p_jobson_korkie": jobson_korkie(result.combo, result.original).p_value,
        }
        for block in blocks:
            test = sharpe_difference_bootstrap(result.combo, result.original, block, draws)
            row[f"sr_p_boot_block_{block}"] = test.p_value
        rows[name] = row
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
