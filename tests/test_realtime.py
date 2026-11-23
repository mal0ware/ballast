"""The real-time strategy: no look-ahead, the cap, and the closed forms it should obey."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from ballast.analysis import managed_factor, real_time_table
from ballast.data import FactorData
from ballast.perf import certainty_equivalent, sharpe_ratio
from ballast.realtime import ex_post_combination, mean_variance_weights, real_time_combination
from ballast.regress import spanning_regression

CUT = pd.Period("1960-06", "M")


def _perturbed(data: FactorData, after: pd.Period, seed: int = 5) -> FactorData:
    """Replace every daily and monthly return after ``after`` with noise."""
    rng = np.random.default_rng(seed)
    daily = data.daily.copy()
    monthly = data.monthly.copy()
    late_days = daily.index.to_period("M") > after
    late_months = monthly.index > after
    daily.loc[late_days] = rng.normal(0.0, 0.03, size=(int(late_days.sum()), daily.shape[1]))
    monthly.loc[late_months] = rng.normal(
        0.0, 0.10, size=(int(late_months.sum()), monthly.shape[1])
    )
    return replace(data, daily=daily, monthly=monthly)


@pytest.mark.parametrize("window", ["expanding", "rolling"])
def test_future_data_does_not_move_earlier_outputs(synthetic: FactorData, window: str) -> None:
    """Change everything after June 1960; nothing up to June 1960 may change."""
    changed = _perturbed(synthetic, CUT)
    for name in ("MKT", "MOM"):
        frames = []
        for data in (synthetic, changed):
            m = managed_factor(data, name, "cowy")
            frames.append(
                real_time_combination(
                    m.original,
                    m.inverse_variance,
                    window=window,  # type: ignore[arg-type]
                ).frame
            )
        before, after = (frame.loc[frame.index <= CUT] for frame in frames)
        assert len(before) > 100
        pd.testing.assert_frame_equal(before, after, check_exact=True)

        # The position for July 1960 is set at the end of June, so it must not move either,
        # while the July return does.
        july = CUT + 1
        positions = ["c", "x_sigma", "x", "position_combo", "position_original"]
        pd.testing.assert_series_equal(
            frames[0].loc[july, positions], frames[1].loc[july, positions], check_exact=True
        )
        assert frames[0].loc[july, "return_combo"] != frames[1].loc[july, "return_combo"]
        later = frames[0].index > july
        assert not np.allclose(
            frames[0].loc[later, "position_combo"], frames[1].loc[later, "position_combo"]
        )


def test_full_sample_c_does_use_the_future(synthetic: FactorData) -> None:
    """The contrast: Moreira and Muir's managed series moves when later data change."""
    changed = _perturbed(synthetic, CUT)
    a = managed_factor(synthetic, "MKT", "mm")
    b = managed_factor(changed, "MKT", "mm")
    early = a.managed.index <= CUT
    assert a.c != b.c
    assert not np.allclose(a.managed[early], b.managed[early])
    # Only the constant moved: the two early series are proportional.
    ratio = (a.managed[early] / b.managed[early]).to_numpy()
    np.testing.assert_allclose(ratio, ratio[0], rtol=1e-10)


def test_first_out_of_sample_month_is_k_plus_one(synthetic: FactorData) -> None:
    m = managed_factor(synthetic, "MKT", "cowy")
    frame = real_time_combination(m.original, m.inverse_variance, training_months=120).frame
    assert frame.index[0] == m.original.index[120]
    assert len(frame) == len(m.original) - 120


def test_first_position_by_hand(synthetic: FactorData) -> None:
    m = managed_factor(synthetic, "HML", "cowy")
    gamma, k = 5.0, 120
    frame = real_time_combination(m.original, m.inverse_variance, k, gamma, leverage_cap=None).frame
    f = m.original.to_numpy()[:k]
    iv = m.inverse_variance.to_numpy()
    c = f.std(ddof=1) / (f * iv[:k]).std(ddof=1)
    managed = c * iv[:k] * f
    weights = np.linalg.inv(np.cov(managed, f, ddof=1)) @ [managed.mean(), f.mean()] / gamma
    assert frame["c"].iloc[0] == pytest.approx(c)
    assert frame["position_combo"].iloc[0] == pytest.approx(weights[0] * c * iv[k] + weights[1])
    assert frame["position_original"].iloc[0] == pytest.approx(f.mean() / (gamma * f.var(ddof=1)))
    assert frame["return_combo"].iloc[0] == pytest.approx(
        frame["position_combo"].iloc[0] * m.original.iloc[k]
    )


def test_position_does_not_depend_on_the_scale_of_the_variance_proxy(
    synthetic: FactorData,
) -> None:
    """Rescaling 1/RV rescales c the other way, so the position is unchanged."""
    m = managed_factor(synthetic, "SMB", "cowy")
    a = real_time_combination(m.original, m.inverse_variance).frame
    b = real_time_combination(m.original, 37.0 * m.inverse_variance).frame
    np.testing.assert_allclose(a["position_combo"], b["position_combo"], rtol=1e-8)
    np.testing.assert_allclose(b["c"], a["c"] / 37.0, rtol=1e-10)


def test_leverage_cap_binds(synthetic: FactorData) -> None:
    m = managed_factor(synthetic, "MKT", "cowy")
    free = real_time_combination(m.original, m.inverse_variance, leverage_cap=None).frame
    capped = real_time_combination(m.original, m.inverse_variance, leverage_cap=1.0).frame
    assert free["position_combo"].abs().max() > 1.0
    assert capped["position_combo"].abs().max() <= 1.0
    np.testing.assert_allclose(capped["position_combo"], free["position_combo"].clip(-1.0, 1.0))


def test_rolling_window_uses_only_the_last_k_months(synthetic: FactorData) -> None:
    m = managed_factor(synthetic, "MKT", "cowy")
    frame = real_time_combination(m.original, m.inverse_variance, 60, window="rolling").frame
    t = 200
    f = m.original.to_numpy()[t - 60 : t]
    assert frame["position_original"].iloc[t - 60] == pytest.approx(
        np.clip(f.mean() / (5.0 * f.var(ddof=1)), -5, 5)
    )


def test_ex_post_combination_obeys_the_spanning_identities(synthetic: FactorData) -> None:
    """Cederburg et al., equations (10), (13) and (14), with monthly moments."""
    gamma = 5.0
    m = managed_factor(synthetic, "MOM", "cowy")
    f, iv = m.original.to_numpy(), m.inverse_variance.to_numpy()
    combo = ex_post_combination(f, iv, gamma)
    fit = spanning_regression(m.managed, m.original)

    sr_combo, sr_f = sharpe_ratio(combo), sharpe_ratio(f)
    n = len(f)
    appraisal_squared = fit.appraisal_ratio**2 * (n - 1) / (n - 2)  # rmse divides by n - 2
    assert sr_combo**2 - sr_f**2 == pytest.approx(appraisal_squared, rel=1e-8)

    best_alone = f * f.mean() / (gamma * f.var(ddof=1))
    cer_gain = certainty_equivalent(combo, gamma) - certainty_equivalent(best_alone, gamma)
    assert cer_gain == pytest.approx(100 * (sr_combo**2 - sr_f**2) / (2 * gamma), rel=1e-8)

    x_sigma = mean_variance_weights(np.column_stack([m.managed, f]), gamma)[0]
    rho = np.corrcoef(m.managed, f)[0, 1]
    alpha_monthly = fit.alpha / 1200
    assert x_sigma == pytest.approx(alpha_monthly / (gamma * f.var(ddof=1) * (1 - rho**2)))


def test_real_time_never_beats_ex_post_on_cer(synthetic: FactorData) -> None:
    """The ex post weights maximize in-sample CER, so nothing uncapped can beat them."""
    table = real_time_table(synthetic, leverage_cap=None)
    assert (table["cer_combo"] <= table["cer_expost"] + 1e-9).all()


def test_evaluate_from_only_changes_the_scoring_window(synthetic: FactorData) -> None:
    table = real_time_table(synthetic, evaluate_from="1960-01")
    assert (table.loc[["MKT", "SMB", "HML", "MOM"], "first_month"] == "1960-01").all()
    m = managed_factor(synthetic, "MKT", "cowy")
    frame = real_time_combination(m.original, m.inverse_variance).frame
    late = frame.loc[frame.index >= pd.Period("1960-01", "M")]
    assert table.loc["MKT", "sr_combo"] == pytest.approx(sharpe_ratio(late["return_combo"]))


def test_short_sample_is_rejected() -> None:
    months = pd.period_range("2000-01", periods=100, freq="M")
    series = pd.Series(0.01, index=months)
    with pytest.raises(ValueError, match="not longer"):
        real_time_combination(series, series, training_months=120)
