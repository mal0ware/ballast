"""Write every table and figure into a results directory."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ballast import paper_values as pv
from ballast.analysis import (
    compare_cells,
    direct_table,
    momentum_crash,
    real_time_table,
    spanning_table,
)
from ballast.data import FactorData
from ballast.plots import headline_figure, momentum_figure


def _csv(table: pd.DataFrame, path: Path, index: bool = True) -> None:
    table.to_csv(path, float_format="%.6f", index=index, lineterminator="\n")


def _p(value: float) -> str:
    return f"[{value:.2f}]"


def _in_sample_md(table: pd.DataFrame) -> str:
    lines = ["| Factor | Alpha (%/yr) | t | Appraisal ratio |", "|---|---:|---:|---:|"]
    for factor, row in table.iterrows():
        lines.append(
            f"| {factor} | {row['alpha']:.2f} | {row['alpha_t']:.2f} "
            f"| {row['appraisal_ratio']:.2f} |"
        )
    return "\n".join(lines)


def _real_time_md(table: pd.DataFrame) -> str:
    lines = [
        "| Factor | Sharpe, with managed | Sharpe, unmanaged | Difference [p] "
        "| CER gain (%/yr) [p] |",
        "|---|---:|---:|---:|---:|",
    ]
    for factor, row in table.iterrows():
        lines.append(
            f"| {factor} | {row['sr_combo']:.2f} | {row['sr_original']:.2f} "
            f"| {row['sr_diff']:+.2f} {_p(row['sr_p'])} "
            f"| {row['cer_diff']:+.2f} {_p(row['cer_p'])} |"
        )
    return "\n".join(lines)


def _side_by_side(left_title: str, left: str, right_title: str, right: str) -> str:
    return (
        "<table>\n<tr>\n"
        f"<th>{left_title}</th>\n<th>{right_title}</th>\n"
        '</tr>\n<tr>\n<td valign="top">\n\n'
        f'{left}\n\n</td>\n<td valign="top">\n\n{right}\n\n</td>\n</tr>\n</table>\n'
    )


def _span(table: pd.DataFrame) -> str:
    return f"{table['first_month'].min()} to {table['last_month'].max()}"


def build_results(data: FactorData, out_dir: Path, figures: bool = True) -> dict[str, Path]:
    """Compute everything and write it to ``out_dir``.

    Returns:
        The files written, keyed by a short name.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    def save(name: str, table: pd.DataFrame, index: bool = True) -> None:
        path = out_dir / f"{name}.csv"
        _csv(table, path, index)
        written[name] = path

    last_month = str(data.monthly.index[-1])
    new_from_mm = str(pd.Period(pv.MM_SAMPLE_END, "M") + 1)
    new_from_cowy = str(pd.Period(pv.COWY_SAMPLE_END, "M") + 1)

    # Part 1: Moreira and Muir's Table 1.
    table1_paper = spanning_table(data, end=pv.MM_SAMPLE_END)
    table1_extended = spanning_table(data)
    table1_new = spanning_table(data, start=new_from_mm)
    save("table1_paper_sample", table1_paper)
    save("table1_extended", table1_extended)
    save("table1_new_months", table1_new)
    differences_mm = pd.concat(
        [
            compare_cells(table1_paper, pv.MM_TABLE1_PANEL_A, "MM Table 1 Panel A"),
            compare_cells(table1_paper, pv.MM_TABLE1_PANEL_B, "MM Table 1 Panel B"),
        ],
        ignore_index=True,
    )
    save("table1_differences", differences_mm, index=False)

    # Part 2: Cederburg et al.'s Tables 1, 3 and 5.
    direct_paper = direct_table(data, end=pv.COWY_SAMPLE_END)
    direct_extended = direct_table(data)
    spanning_cowy = spanning_table(data, end=pv.COWY_SAMPLE_END, method="cowy")
    realtime_paper = real_time_table(data, end=pv.COWY_SAMPLE_END)
    realtime_extended = real_time_table(data)
    realtime_new = real_time_table(data, evaluate_from=new_from_cowy)
    save("direct_paper_sample", direct_paper)
    save("direct_extended", direct_extended)
    save("spanning_cowy_sample", spanning_cowy)
    save("realtime_paper_sample", realtime_paper)
    save("realtime_extended", realtime_extended)
    save("realtime_new_months", realtime_new)
    differences_cowy = pd.concat(
        [
            compare_cells(direct_paper, pv.COWY_TABLE1, "COWY Table 1"),
            compare_cells(spanning_cowy, pv.COWY_TABLE3, "COWY Table 3 Panel A"),
            compare_cells(realtime_paper, pv.COWY_TABLE5_PANEL_A, "COWY Table 5 Panel A"),
        ],
        ignore_index=True,
    )
    save("cowy_differences", differences_cowy, index=False)

    # Part 3: momentum through 2009.
    monthly, summary, worst = momentum_crash(data)
    save("momentum_2009_monthly", monthly)
    save("momentum_2009_summary", summary)
    save("momentum_worst_months", worst)

    vintage = {
        "source": data.manifest.get("source", "unknown"),
        "downloaded_utc": data.manifest.get("downloaded_utc"),
        "last_month_in_data": last_month,
        "last_day_in_data": str(data.daily.index[-1].date()),
        "files": {
            name: {"last_period": entry.get("last_period"), "sha256_zip": entry.get("sha256_zip")}
            for name, entry in data.manifest.get("files", {}).items()
        },
    }
    vintage_path = out_dir / "data_vintage.json"
    vintage_text = json.dumps(vintage, indent=2) + "\n"
    vintage_path.write_text(vintage_text, encoding="utf-8", newline="\n")
    written["data_vintage"] = vintage_path

    headline = (
        "## Paper samples\n\n"
        + _side_by_side(
            f"In sample ({_span(table1_paper)})",
            _in_sample_md(table1_paper),
            f"In real time (out of sample, {_span(realtime_paper)})",
            _real_time_md(realtime_paper),
        )
        + f"\n## Extended to {last_month} (new)\n\n"
        + _side_by_side(
            f"In sample ({_span(table1_extended)})",
            _in_sample_md(table1_extended),
            f"In real time (out of sample, {_span(realtime_extended)})",
            _real_time_md(realtime_extended),
        )
        + "\n## Only the months after each paper's sample (new)\n\n"
        + _side_by_side(
            f"In sample ({_span(table1_new)})",
            _in_sample_md(table1_new),
            f"In real time (out of sample, {_span(realtime_new)})",
            _real_time_md(realtime_new),
        )
    )
    headline_path = out_dir / "headline.md"
    headline_path.write_text(headline, encoding="utf-8", newline="\n")
    written["headline"] = headline_path

    if figures:
        headline_png = out_dir / "headline.png"
        headline_figure(
            table1_paper,
            table1_extended,
            realtime_paper,
            realtime_extended,
            (
                f"Paper sample, to {pv.MM_SAMPLE_END}",
                f"Extended to {last_month} (new)",
                f"Paper sample, to {pv.COWY_SAMPLE_END}",
                f"Extended to {last_month} (new)",
            ),
            headline_png,
        )
        momentum_png = out_dir / "momentum_2009.png"
        momentum_figure(monthly, momentum_png)
        written["headline_png"] = headline_png
        written["momentum_png"] = momentum_png
    return written
