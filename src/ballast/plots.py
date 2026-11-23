"""The two figures. Colours are a validated two-series pair; text stays in ink."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ballast._types import Array

BLUE = "#2a78d6"
ORANGE = "#eb6834"
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"


def _style(ax: Axes) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _save(fig: Figure, path: Path) -> None:
    fig.savefig(path, dpi=160, facecolor=SURFACE, metadata={"Software": None})
    plt.close(fig)


def _interval_panel(
    ax: Axes,
    factors: list[str],
    series: list[tuple[str, str, Array, Array]],
    ylabel: str,
    title: str,
) -> None:
    """Point estimates with 95% intervals, one cluster per factor."""
    _style(ax)
    x = np.arange(len(factors))
    offsets = np.linspace(-0.14, 0.14, len(series)) if len(series) > 1 else np.zeros(1)
    for (label, colour, estimate, half_width), offset in zip(series, offsets, strict=True):
        ax.errorbar(
            x + offset,
            estimate,
            yerr=half_width,
            fmt="o",
            color=colour,
            markersize=6,
            linewidth=1.6,
            capsize=3,
            label=label,
        )
    ax.axhline(0.0, color=MUTED, linewidth=1.0)
    ax.set_xticks(x, factors)
    ax.set_ylabel(ylabel, color=INK, fontsize=10)
    ax.set_title(title, color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK, loc="upper left")


def headline_figure(
    spanning_paper: pd.DataFrame,
    spanning_extended: pd.DataFrame,
    realtime_paper: pd.DataFrame,
    realtime_extended: pd.DataFrame,
    labels: tuple[str, str, str, str],
    path: Path,
) -> None:
    """Left: in-sample alpha. Right: real-time Sharpe-ratio difference.

    Bars are 95% intervals: 1.96 robust standard errors on the left, and on the
    right the interval implied by the Jobson-Korkie z-statistic.
    """
    factors = list(spanning_paper.index)
    fig, (left, right) = plt.subplots(1, 2, figsize=(10.5, 4.2), facecolor=SURFACE)

    def alpha_series(table: pd.DataFrame) -> tuple[Array, Array]:
        return table["alpha"].to_numpy(), 1.96 * table["alpha_se"].to_numpy()

    def sharpe_series(table: pd.DataFrame) -> tuple[Array, Array]:
        diff = table["sr_diff"].to_numpy()
        return diff, 1.96 * np.abs(diff / table["sr_z"].to_numpy())

    _interval_panel(
        left,
        factors,
        [
            (labels[0], BLUE, *alpha_series(spanning_paper)),
            (labels[1], ORANGE, *alpha_series(spanning_extended)),
        ],
        "Alpha of managed on unmanaged (% per year)",
        "In sample: spanning-regression alpha",
    )
    _interval_panel(
        right,
        factors,
        [
            (labels[2], BLUE, *sharpe_series(realtime_paper)),
            (labels[3], ORANGE, *sharpe_series(realtime_extended)),
        ],
        "Sharpe ratio, combination minus unmanaged (annual)",
        "In real time: out-of-sample Sharpe-ratio gain",
    )
    fig.tight_layout()
    _save(fig, path)


def momentum_figure(monthly: pd.DataFrame, path: Path) -> None:
    """Momentum around 2009: growth of one dollar, and the managed weight."""
    dates = monthly.index.to_timestamp(how="end")
    start = monthly.index[0].to_timestamp(how="start")

    def growth(column: str) -> tuple[list[pd.Timestamp], list[float]]:
        return [start, *dates], [1.0, *(1.0 + monthly[column]).cumprod()]

    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(8.5, 6.0), sharex=True, height_ratios=[2, 1], facecolor=SURFACE
    )
    _style(top)
    _style(bottom)
    top.plot(*growth("mom"), color=BLUE, linewidth=2, label="Unmanaged")
    top.plot(
        *growth("managed"),
        color=ORANGE,
        linewidth=2,
        label="Volatility-managed (full-sample c)",
    )
    top.axhline(1.0, color=MUTED, linewidth=1.0)
    top.set_ylabel("Growth of $1 invested at the start", color=INK, fontsize=10)
    top.set_title("Momentum factor through the 2009 crash", color=INK, fontsize=11, loc="left")
    top.legend(frameon=False, fontsize=9, labelcolor=INK, loc=(0.6, 0.42))

    bottom.step(dates, monthly["weight"], where="mid", color=ORANGE, linewidth=2)
    bottom.axhline(1.0, color=MUTED, linewidth=1.0)
    bottom.set_ylabel("Managed position\n(multiple of the factor)", color=INK, fontsize=10)
    bottom.set_xlabel("Month", color=INK, fontsize=10)
    fig.tight_layout()
    _save(fig, path)
