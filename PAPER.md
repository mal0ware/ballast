# Sources, formulas and comparison

Every number here comes from `results/`, built by `scripts/reproduce.py` from French library files downloaded on 2026-11-23. Sections marked as added here go beyond the two papers. In the comparison tables each cell is "ours / paper", and a star marks a cell that differs from the printed figure after rounding the way the paper rounds.

## Citations and the versions read

1. Alan Moreira and Tyler Muir, "Volatility-Managed Portfolios", Journal of Finance 72(4), 2017, 1611-1644. I read NBER working paper 22208 (April 2016), which is public. I did not read the journal version, so its table and equation numbers may differ from the ones cited below. Short name: MM.
2. Scott Cederburg, Michael S. O'Doherty, Feifei Wang and Xuemin (Sterling) Yan, "On the performance of volatility-managed portfolios", Journal of Financial Economics 138(1), 2020, 95-117. I read the published article from an author's university page. I did not read its Internet Appendix. Short name: COWY.
3. Kent Daniel and Tobias J. Moskowitz, "Momentum crashes", Journal of Financial Economics 122(2), 2016, 221-247. I read NBER working paper 20439 (August 2014). Short name: DM.
4. Olivier Ledoit and Michael Wolf, "Robust performance hypothesis testing with the Sharpe ratio", Journal of Empirical Finance 15(5), 2008, 850-859. I did not read it. The bootstrap test below was written from the published description of their method, and its size was checked by simulation. Short name: LW.
5. Whitney Newey and Kenneth West (1987) for the HAC standard error, and Sture Holm (1979) for the step-down multiple-testing adjustment. Both are textbook methods; I did not read the originals.

## Formulas implemented

### The managed factor (MM equations 1 and 2, COWY equations 3 and 4)

MM equation (1): the managed return is `f_sigma[t+1] = c / sigma2[t] * f[t+1]`, where `f` is the factor's excess return and `sigma2[t]` is a proxy for its conditional variance. The text below it says "we choose c so that the managed portfolio has the same unconditional standard deviation as the buy-and-hold portfolio", and footnote 5 notes that `c` comes from the full sample.

MM equation (2): the proxy is the previous month's realized variance, the sum over the month's trading days of squared deviations of the daily return from its mean for the month. Code: `realized_variance(..., "mm")`.

COWY equation (3) is the same managed return. COWY equation (4) defines the variance differently: `sigma2[t] = 22 / J[t] * sum of f[t,j]^2` over the `J[t]` trading days of month `t`, with no demeaning. Code: `realized_variance(..., "cowy")`.

Each paper's tables are reproduced with that paper's own definition. Any constant multiple of the variance is absorbed by `c`, so the two definitions differ only in the demeaning.

In code, `c = sd(f) / sd(f / sigma2_lagged)` over the sample in use (`scale_constant`).

### The spanning regression (MM equation 3, COWY equation 5)

`f_sigma[t] = alpha + beta * f[t] + e[t]`, monthly.

MM Table 1's caption: "Standard errors are in parentheses and adjust for heteroscedasticity. All factors are annualized in percent per year by multiplying monthly factors by 12." So alpha and RMSE are the monthly figures times 1200. MM Section 2.4 gives the appraisal ratio as `sqrt(12) * alpha / sigma_e` on monthly figures. COWY equation (12) is the same ratio, and COWY Table 3 states White (1980) standard errors.

Panel B of MM Table 1 adds the three Fama-French factors as regressors. For the market, SMB and HML rows the factor is already one of the three, so it enters once.

### The portfolio reading of the regression (COWY equations 6 to 14)

A mean-variance investor with risk aversion `gamma` who can hold both series chooses `[x_sigma, x] = inverse(Sigma) mu / gamma` (equation 7). The position in the factor is `y[t] = x_sigma * c / sigma2[t-1] + x` (equation 11). Three identities follow and are used as tests:

- Equation (10): `x_sigma = alpha / (gamma * var(f) * (1 - rho^2))`.
- Equation (13): `AR^2 = SR(y)^2 - SR(f)^2`.
- Equation (14): the CER gain is `(SR(y)^2 - SR(f)^2) / (2 gamma)`.

These hold exactly in sample when every moment uses the same degrees of freedom. The regression RMSE divides by `n - 2` and the sample variance by `n - 1`, so the test for (13) carries a factor of `(n - 1) / (n - 2)`.

### The real-time strategy (COWY Section 4.3.1, equations 15 to 18)

The first `K = 120` months are training. At the start of each later month `t`, from the months before `t` only:

1. `c[t]` is "the constant that allows the original and volatility-managed factors to have the same variance over the training period preceding month t".
2. `mu[t]` and `Sigma[t]` are the mean vector and covariance matrix of the managed and original factor over the training period, and equation (15) gives `[x_sigma[t], x[t]] = inverse(Sigma[t]) mu[t] / gamma`.
3. Equation (16): `y[t] = x_sigma[t] * c[t] / sigma2[t-1] + x[t]`. The return is `y[t] * f[t]`.

The base case is an expanding window, `gamma = 5`, and `|y[t]| <= 5`. The benchmark, "original factor (real time)", holds `mean / (gamma * variance)` of the factor from the same training months, capped the same way.

Equation (17) is the Sharpe-ratio difference and equation (18) the CER difference, with `CER = mean - gamma / 2 * variance`. Sharpe ratios are annualized by `sqrt(12)` and CERs are in percent per year.

One thing the paper's emphasis on `c` can hide: `y[t]` does not depend on `c[t]`. Multiplying the managed series by `k` divides `x_sigma` by `k`. The Sharpe ratio of the managed factor alone does not depend on `c` either. What the real-time investor lacks is the pair of weights, and those come from an estimated alpha. A test checks the invariance.

### The two tests

Jobson and Korkie (1981) with Memmel's (2003) correction, as written in COWY footnote 8: `z = (s_j m_i - s_i m_j) / sqrt(theta)`, with `theta = (2 s_i^2 s_j^2 - 2 s_i s_j s_ij + m_i^2 s_j^2 / 2 + m_j^2 s_i^2 / 2 - m_i m_j s_ij^2 / (s_i s_j)) / T`.

DeMiguel, Garlappi and Uppal (2009), as written in COWY footnote 19: the delta method on `(m_i, m_j, s_i^2, s_j^2)` with gradient `(1, -1, -gamma/2, gamma/2)`. Multiplied out, the variance of the CER difference is `(s_i^2 + s_j^2 - 2 s_ij + gamma^2 / 2 * (s_i^4 + s_j^4 - 2 s_ij^2)) / T`.

I took both statistics from COWY's footnotes and did not read the three original papers. P-values are two-sided from the standard normal.

### Newey-West standard errors (added here)

The papers use White (HC0) errors. Alongside them the code reports Newey-West errors: the meat of the sandwich is `sum_t s_t s_t' + sum_{l=1}^{L} (1 - l / (L + 1)) (G_l + G_l')`, with `s_t` the regressor row times the residual and `G_l = sum_t s_t s_{t-l}'`. The lag length is `L = floor(4 (T / 100)^(2/9))`, which is 6 for the full samples and 4 for the post-sample windows. There is no small-sample correction. Code: `ols(..., "HAC")`, checked against statsmodels.

### Trading costs (added here)

The managed factor's position in month `t` is `w[t] = c / sigma2[t-1]`. Moving from `w[t-1]` to `w[t]` trades `|w[t] - w[t-1]|` units of the factor. At a cost of `k` basis points per unit, the net managed return is `f_sigma[t] - k / 10000 * |w[t] - w[t-1]|`. The plain factor holds one unit throughout and pays nothing. The first month of each sample is charged nothing.

The net managed return is regressed on the gross plain factor. OLS is linear in the dependent variable, so net alpha is `alpha - k * a_turn`, where `a_turn` is the alpha from regressing the turnover series on the factor. The break-even cost is `alpha / a_turn`. The code also finds, by root search, the highest cost at which the Newey-West t-statistic is still 1.96.

In real time, both the combination and the plain benchmark pay `k` per unit change in their own position `y[t]`. The break-even is the cost at which their Sharpe ratios are equal, found by root search between 0 and 1,000 bps.

### The block-bootstrap Sharpe test (added here, after LW)

The Sharpe-ratio difference is a function of `v = (m_i, m_j, E[r_i^2], E[r_j^2])`: `d = m_i / sqrt(g_i - m_i^2) - m_j / sqrt(g_j - m_j^2)`. The delta method gives `se(d) = sqrt(grad' Psi grad / T)`, where `Psi` is the long-run covariance of the four centred moment terms. On the data, `Psi` is estimated with Newey-West weights. LW use a prewhitened quadratic-spectral kernel instead.

The bootstrap draws circular blocks of `b = 6` months until it has at least `T` months. On each draw it computes `d*` and a block standard error: the gradient-weighted moment terms are summed within each block, divided by `sqrt(b)`, and `Psi*` is the mean square of those sums. The statistic is `|d* - d| / se*`. The two-sided p-value is `(1 + #{|d* - d| / se* >= |d| / se}) / (draws + 1)` with 4,999 draws. LW choose `b` by a calibration step; here it is fixed at six months, and `results/bootstrap_block_length.csv` shows the p-values for 1 to 24 months.

`results/bootstrap_size.csv` checks the size. Each design draws 1,000 samples of two series with equal Sharpe ratios and correlation 0.6. One design is independent normal. The other has Student-t(5) shocks and a shared GARCH(1,1) volatility (`omega = 0.05`, `alpha = 0.10`, `beta = 0.85`), so it has fat tails and volatility clusters.

| Design | Months | Jobson-Korkie rejects | Bootstrap rejects |
|---|---:|---:|---:|
| Independent normal | 120 | 5.3% | 4.3% |
| Independent normal | 480 | 4.2% | 3.9% |
| GARCH(1,1), t(5) shocks | 120 | 6.8% | 4.9% |
| GARCH(1,1), t(5) shocks | 480 | 5.0% | 4.3% |

The nominal level is 5%. With 1,000 samples each rate has a standard error of about 0.7 points. The bootstrap is slightly conservative. Jobson-Korkie over-rejects with fat tails in the short sample and is close to 5% otherwise.

### Multiple testing (added here)

Each table tests six factors. Holm's step-down adjustment sorts the six p-values, multiplies the `r`-th smallest by `7 - r`, and makes the sequence non-decreasing. It controls the chance of any false rejection among the six at the stated level, under any dependence between the tests. The adjustment is applied within one table and one cost level. It is not applied across samples, cost levels or tables.

### Momentum crashes (DM)

DM's dynamic weight is their equation (5), `w = mu / (2 lambda sigma2)`, with a forecast mean and a GJR-GARCH variance forecast (equations 6 and 7). That strategy is not implemented here. The worked example uses MM's simpler rule on the French momentum factor, and cites DM only for the facts of the crash: Table 2 lists April 2009 (-45.52%) and March 2009 (-42.28%) as the fourth and seventh worst months of their winners-minus-losers decile portfolio, and the introduction reports that from March to May 2009 the loser decile rose 163% while the winner decile gained 8%.

## Samples

| Exercise | Sample | Source of the dates |
|---|---|---|
| MM Table 1 | managed returns 1926-08 to 2015-04; MOM from 1927-01; RMW and CMA from 1963-08 | The caption says "1926-2015". April 2015 is inferred: it is the only end month that gives N = 1,065, 1,060 and 621. |
| COWY Tables 1, 3, 5 | same starts, ending 2016-12 | Table 1 caption. |
| Extension | to 2026-09 | The last month in the files downloaded on 2026-11-23. New. |
| Post-sample only | 2015-05 to 2026-09 for the regression (`c` set within that window); 2017-01 to 2026-09 for the real-time strategy (training from the start of the data) | New. |

## Claim by claim

### MM Table 1, Panel A: univariate spanning regressions, 1926-08 to 2015-04

| Statistic | MKT | SMB | HML | MOM | RMW | CMA |
|---|---:|---:|---:|---:|---:|---:|
| Alpha (%/yr) | 4.93 / 4.86 \* | -0.59 / -0.58 \* | 1.73 / 1.97 \* | 12.83 / 12.51 \* | 2.80 / 2.44 \* | 0.36 / 0.38 \* |
| s.e. of alpha | 1.57 / 1.56 \* | 0.91 / 0.91 | 1.05 / 1.02 \* | 1.72 / 1.71 \* | 0.89 / 0.83 \* | 0.67 / 0.67 |
| Beta | 0.60 / 0.61 \* | 0.60 / 0.62 \* | 0.54 / 0.57 \* | 0.45 / 0.47 \* | 0.58 / 0.62 \* | 0.67 / 0.68 \* |
| s.e. of beta | 0.05 / 0.05 | 0.08 / 0.08 | 0.07 / 0.07 | 0.07 / 0.07 | 0.08 / 0.08 | 0.05 / 0.05 |
| N | 1065 / 1065 | 1065 / 1065 | 1065 / 1065 | 1060 / 1060 | 621 / 621 | 621 / 621 |
| R² | 0.36 / 0.37 \* | 0.37 / 0.38 \* | 0.29 / 0.32 \* | 0.20 / 0.22 \* | 0.34 / 0.38 \* | 0.45 / 0.46 \* |
| RMSE | 51.79 / 51.39 \* | 30.55 / 30.44 \* | 35.68 / 34.92 \* | 51.08 / 50.37 \* | 21.84 / 20.16 \* | 17.65 / 17.55 \* |

28 of 42 cells differ. The paper's claims hold: alpha is positive for every factor but SMB, and more than two standard errors from zero for the market, momentum and RMW. HML's alpha is 1.64 standard errors from zero here and 1.93 in the paper; neither clears 1.96.

The appraisal ratios MM quote in Section 2.4 are 0.34 for the market, 0.20 for HML and 0.41 for profitability. Ours are 0.33, 0.17 and 0.44. For momentum the text works through `sqrt(12) * 12.5 / 50 = 0.875`; ours is 0.87.

### MM Table 1, Panel B: alpha with the three Fama-French factors added

| Statistic | MKT | SMB | HML | MOM | RMW | CMA |
|---|---:|---:|---:|---:|---:|---:|
| Alpha (%/yr) | 5.63 / 5.45 \* | -0.26 / -0.33 \* | 2.45 / 2.66 \* | 10.73 / 10.52 \* | 3.62 / 3.18 \* | -0.06 / -0.01 \* |
| s.e. | 1.56 / 1.56 | 0.89 / 0.89 | 1.06 / 1.02 \* | 1.59 / 1.60 \* | 0.91 / 0.83 \* | 0.68 / 0.68 |

9 of 12 cells differ.

### COWY Table 1: managed against original, 1926-08 to 2016-12

| Statistic | MKT | SMB | HML | MOM | RMW | CMA |
|---|---:|---:|---:|---:|---:|---:|
| Sharpe, original | 0.42 / 0.42 | 0.23 / 0.23 | 0.40 / 0.40 | 0.48 / 0.48 | 0.41 / 0.38 \* | 0.53 / 0.53 |
| Sharpe, managed | 0.51 / 0.51 | 0.08 / 0.08 | 0.37 / 0.38 \* | 0.96 / 0.99 \* | 0.57 / 0.51 \* | 0.39 / 0.40 \* |
| Difference | 0.09 / 0.09 | -0.15 / -0.15 | -0.03 / -0.02 \* | 0.49 / 0.50 \* | 0.16 / 0.13 \* | -0.14 / -0.13 \* |
| p-value | 0.31 / 0.30 \* | 0.09 / 0.09 | 0.74 / 0.86 \* | 0.00 / 0.00 | 0.20 / 0.29 \* | 0.19 / 0.23 \* |
| Correlation | 0.63 / 0.63 | 0.64 / 0.63 \* | 0.56 / 0.57 \* | 0.47 / 0.48 \* | 0.58 / 0.59 \* | 0.69 / 0.68 \* |

18 of 30 cells differ. The paper's point holds: the managed factor has the higher Sharpe ratio for three of these six, the lower for the other three, and only momentum's difference is significant.

### COWY Table 3, Panel A: their rerun of the spanning regressions, to 2016-12

| Statistic | MKT | SMB | HML | MOM | RMW | CMA |
|---|---:|---:|---:|---:|---:|---:|
| Alpha (%/yr) | 4.61 / 4.63 \* | -0.75 / -0.76 \* | 1.75 / 1.87 \* | 12.17 / 12.39 \* | 2.54 / 2.23 \* | 0.17 / 0.26 \* |
| t | 3.07 / 3.08 \* | -0.87 / -0.87 | 1.72 / 1.88 \* | 7.10 / 7.31 \* | 2.90 / 2.57 \* | 0.27 / 0.39 \* |
| Beta | 0.63 / 0.63 | 0.64 / 0.63 \* | 0.56 / 0.57 \* | 0.47 / 0.48 \* | 0.58 / 0.59 \* | 0.69 / 0.68 \* |
| Adj. R² | 0.40 / 0.40 | 0.40 / 0.40 | 0.31 / 0.33 \* | 0.22 / 0.23 \* | 0.34 / 0.34 | 0.47 / 0.46 \* |
| Appraisal ratio | 0.32 / 0.32 | -0.09 / -0.09 | 0.17 / 0.19 \* | 0.84 / 0.86 \* | 0.41 / 0.36 \* | 0.03 / 0.05 \* |
| c\* (returns in percent) | 10.31 / 10.33 \* | 2.63 / 2.63 | 2.92 / 2.95 \* | 4.54 / 4.60 \* | 1.45 / 1.48 \* | 1.49 / 1.53 \* |

28 of 36 cells differ. This table is the tightest check on the construction, because `c*` depends on the variance definition and on every month in the sample. The market's `c*` is 10.31 against 10.33.

### COWY Table 5, Panel A: real-time combination strategies, out of sample to 2016-12

[S1] is the real-time combination, [S2] the real-time investor limited to the original factor, [S3] the ex post optimal combination over the same out-of-sample months.

| Statistic | MKT | SMB | HML | MOM | RMW | CMA |
|---|---:|---:|---:|---:|---:|---:|
| Sharpe [S1] | 0.42 / 0.42 | 0.13 / 0.14 \* | 0.37 / 0.38 \* | 0.89 / 0.92 \* | 0.51 / 0.44 \* | 0.53 / 0.52 \* |
| Sharpe [S2] | 0.46 / 0.46 | 0.19 / 0.19 | 0.44 / 0.43 \* | 0.48 / 0.49 \* | 0.33 / 0.31 \* | 0.56 / 0.56 |
| Difference [S1]-[S2] | -0.04 / -0.04 | -0.06 / -0.06 | -0.07 / -0.06 \* | 0.41 / 0.44 \* | 0.18 / 0.13 \* | -0.04 / -0.03 \* |
| p-value | 0.62 / 0.64 \* | 0.36 / 0.37 \* | 0.33 / 0.41 \* | 0.00 / 0.00 | 0.38 / 0.53 \* | 0.14 / 0.20 \* |
| Sharpe [S3] | 0.53 / 0.53 | 0.25 / 0.26 \* | 0.50 / 0.50 | 0.97 / 0.99 \* | 0.63 / 0.58 \* | 0.65 / 0.64 \* |
| CER [S1] (%/yr) | 1.54 / 1.56 \* | -0.03 / 0.00 \* | 1.38 / 1.41 \* | 7.88 / 8.47 \* | 2.59 / 1.96 \* | 2.76 / 2.74 \* |
| CER [S2] | 1.76 / 1.75 \* | 0.35 / 0.38 \* | 1.62 / 1.61 \* | 2.21 / 2.29 \* | 0.98 / 0.91 \* | 3.14 / 3.09 \* |
| Difference [S1]-[S2] | -0.22 / -0.19 \* | -0.38 / -0.37 \* | -0.24 / -0.20 \* | 5.67 / 6.18 \* | 1.61 / 1.04 \* | -0.38 / -0.35 \* |
| p-value | 0.81 / 0.83 \* | 0.26 / 0.27 \* | 0.68 / 0.73 \* | 0.00 / 0.00 | 0.39 / 0.57 \* | 0.14 / 0.21 \* |
| CER [S3] | 2.79 / 2.79 | 0.63 / 0.67 \* | 2.47 / 2.47 | 9.36 / 9.87 \* | 4.01 / 3.42 \* | 4.18 / 4.04 \* |

48 of 60 cells differ. The paper's claims hold for these six factors: the combination beats the original for momentum and RMW and loses for the market, SMB, HML and CMA; only momentum's gain is significant; and the real-time combination is below the ex post optimal one in every column, on both measures. The paper's summary counts ("five of the nine cases") include three factors not available here.

The tables COWY build on 103 strategies (Tables 2, 4, 6, 7, 8 and 9) and Table 5, Panel B are not reproduced.

## Why the cells differ

The cause is unexplained. The data vintage is the main candidate, and it is untested.

- The French library is rebuilt whenever CRSP and Compustat are updated, and past returns change. The files used here say they were created from the 202609 CRSP database. MM's files date from 2015 and COWY's from about 2017. Neither old vintage is published.
- The sample sizes match exactly in every column, so the samples and the lag alignment are right.
- Where the method can be checked without the data, it matches: the market's `c*`, the ex post [S3] cells for the market and HML, and all the Sharpe ratios of the original market, SMB, HML and momentum agree to the printed digit.
- The gaps are smallest for the market and largest for RMW, the factor that depends most on accounting data. RMW's own Sharpe ratio over COWY's sample is 0.41 here against 0.38 in the paper, before any managing is done. That difference can only come from the input returns. It shows the inputs differ; it does not show that the difference explains the other gaps, such as RMW's RMSE of 21.84 against 20.16.

Running this code on an archived copy of the French files from 2015 to 2017 would test the vintage explanation. If those files reproduced the printed cells, the code is right and the data moved. No archived copy was used here.

A second possible cause for MM is the standard-error formula. "Adjust for heteroscedasticity" could mean HC0 or HC1. With over 600 observations the two differ by less than 0.2%, which is too small to explain any starred cell.

## Choices the papers leave open

- MM's sample end (April 2015), inferred from the sample sizes.
- White (HC0) standard errors for every comparison with the papers. COWY say White (1980); MM do not say which. Newey-West errors are reported beside them and used for the cost tables and the Holm adjustment.
- Sample standard deviations and covariances divide by `n - 1`.
- The leverage cap is applied by clipping `y[t]` to `[-5, 5]`.
- The ex post optimal strategy [S3] is uncapped, with `c` and the weights taken from the out-of-sample months. COWY's caption can be read as capping it. The market and HML cells match the paper to the digit this way.
- P-values are two-sided.
- A month's realized variance needs at least two daily returns. This never binds in the real data.
- Costs are charged per unit of the factor's notional, at 0, 10, 25 and 50 bps, on the change in position only. The first month is free.
- The bootstrap uses six-month blocks and 4,999 draws, seeded so the p-values are reproducible.

## Variants tried

Nothing was tuned to move a result. The full list of things run more than one way:

1. Standard errors for MM Table 1: HC1 in a first exploratory run, then HC0 for everything. The alpha standard errors changed in the third decimal.
2. The Sharpe-ratio tolerance in `tests/test_paper_match.py` was 0.06, failed on RMW's [S1] Sharpe ratio (0.51 against 0.44), and was widened to 0.08. No code or parameter changed. The tolerances describe the match found; they were not set in advance.

The variance definition, the training length, the window type, the risk aversion and the cap were each run once, at the papers' values. The code supports a rolling window and other caps, and tests exercise them on synthetic data, but no real-data result was produced with them.

The cost levels (10, 25 and 50 bps per unit of turnover) were named in the brief for this pass and run once. The six-month block, the 4,999 draws, the Newey-West lag rule and the Holm adjustment were each run at one setting. The block-length table reports the other block lengths it covers; none was used for a headline number.

## New results

These are not in either paper.

### Before costs, extended and post-sample

| Factor | Alpha, 1926-2026 (%/yr) | t, White | t, NW | Alpha, 2015-05 to 2026-09 | t, NW | Real-time Sharpe gain to 2026-09 [JK p, bootstrap p] | Real-time Sharpe gain, 2017-01 to 2026-09 [JK p, bootstrap p] |
|---|---:|---:|---:|---:|---:|---:|---:|
| MKT | 4.51 | 3.09 | 2.82 | 1.22 | 0.28 | -0.06 [0.43, 0.53] | -0.12 [0.58, 0.67] |
| SMB | -0.54 | -0.64 | -0.50 | -1.42 | -0.91 | -0.05 [0.45, 0.53] | +0.05 [0.30, 0.37] |
| HML | 1.57 | 1.57 | 1.37 | -4.13 | -1.62 | -0.03 [0.69, 0.71] | -0.10 [0.017, 0.042] |
| MOM | 11.95 | 7.62 | 6.56 | 3.31 | 1.14 | +0.40 [0.000, 0.004] | +0.13 [0.56, 0.56] |
| RMW | 2.79 | 3.39 | 3.17 | 1.99 | 1.17 | +0.17 [0.34, 0.34] | +0.05 [0.70, 0.66] |
| CMA | 0.38 | 0.58 | 0.61 | -2.30 | -1.37 | -0.03 [0.07, 0.07] | -0.02 [0.045, 0.035] |

The post-sample windows are 137 and 117 months. HML and CMA show Sharpe-ratio losses after 2016 that are significant on a single test, by both Jobson-Korkie and the bootstrap. After the Holm adjustment across six factors their p-values are 0.21. Both strategies have negative Sharpe ratios for these two factors in that window, with or without managing, and the CER differences are +0.06 and -0.02 with p-values of 0.91 and 0.90. I would not read much into either.

The block bootstrap changes no 5% verdict in COWY's Tables 1 and 5 for these six factors. It raises momentum's p-values, from 0.00001 to 0.008 in Table 1 and from 0.0001 to 0.006 in Table 5, and both stay significant after Holm (0.046 and 0.034).

### After costs

The tables in the README use the extended sample. The paper samples give break-even costs within five bps of those. Over the post-sample months, before costs, no factor has a significant alpha, so the cost tables there only lower numbers that were already insignificant. The break-even costs there are 15 bps for the market, 53 for momentum and 26 for RMW, and the real-time momentum gain breaks even at 27 bps. All are in `results/costs_in_sample.csv` and `results/costs_real_time.csv`.

## Questions a reader may ask

Why White (HC0) errors and not Newey-West? HC0 is what the papers state, so the replication uses it. Managed returns have volatility clusters, so serial correlation in the squared residuals is a fair worry. With six lags, Newey-West lowers the t-statistics of the significant alphas (over 1926 to 2015: market 3.15 to 2.90, momentum 7.47 to 6.49, RMW 3.14 to 2.96) and changes no verdict at 5%. Both are reported in `results/table1_*.csv`.

What about testing six factors at once? With six independent tests at 5% and all six nulls true, the chance of at least one false rejection is about 26%. After Holm's adjustment, the in-sample alphas of the market, momentum and RMW stay significant before costs (Holm p 0.015, under 0.001 and 0.015 over 1926 to 2015). In real time only momentum's gain does (0.034 over the paper sample, 0.024 to 2026). With costs of 10 bps per unit of turnover, only momentum's in-sample alpha survives the adjustment, and its real-time gain does not (Holm p 0.067 to 2026).

What happens after costs? See the README tables and `results/costs_*.csv`. The in-sample break-even costs are 50 bps for the market, 112 for momentum and 39 for RMW over 1926 to 2026. The real-time momentum gain breaks even at 76 bps and is no longer significant on its own at 50 bps (bootstrap p 0.29).

Does the Jobson-Korkie test's normality assumption matter here? Before costs it changes no verdict: the bootstrap gives larger p-values for momentum and the same 5% verdicts in every table. In the cost tables some single-test verdicts differ, including momentum's real-time gain at 25 bps over the paper sample (Jobson-Korkie p 0.008, bootstrap p 0.057). In the size simulation Jobson-Korkie rejects 6.8% of the time with fat tails over 120 months.

The momentum example is also new in its details. The numbers are in the README and in `results/momentum_2009_*.csv`.

## Not verified

- The journal versions of MM and DM, and COWY's Internet Appendix.
- The cause of the cell differences.
- MM's exact sample end and standard-error formula.
- The original statements of the Jobson-Korkie, Memmel and DeMiguel-Garlappi-Uppal statistics. The formulas are as COWY print them; the simulation test shows both reject about 5% of the time when the null is true.
- Ledoit and Wolf (2008) itself. The bootstrap follows the published description of their method, with the two simplifications listed above. Its size is checked by simulation, not against their code or their published examples.
- What trading these factors costs. The cost levels are round numbers, not estimates.
- Whether COWY cap the ex post strategy.
