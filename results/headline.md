## After trading costs, extended sample to 2026-09

Costs are basis points per unit change in the position, in units of the factor's notional. A star marks a Holm-adjusted p-value below 0.05 across the six factors at that cost.

In sample, Moreira and Muir's construction (1926-08 to 2026-09). Cells are alpha in % a year with the Newey-West t-statistic. Significant up to is the highest cost at which that t-statistic is still at least 1.96, for one factor on its own.

| Factor | Turnover a month | gross | 10 bps | 25 bps | 50 bps | Break-even (bps) | Significant up to (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|
| MKT | 0.74 | 4.51 (2.82)\* | 3.62 (2.28) | 2.28 (1.44) | 0.04 (0.03) | 50 | 16 |
| SMB | 0.53 | -0.54 (-0.50) | -1.17 (-1.08) | -2.12 (-1.91) | -3.71 (-3.21)\* | none | none |
| HML | 0.67 | 1.57 (1.37) | 0.77 (0.67) | -0.43 (-0.37) | -2.44 (-2.05) | 20 | none |
| MOM | 0.90 | 11.95 (6.56)\* | 10.89 (6.09)\* | 9.28 (5.32)\* | 6.61 (3.91)\* | 112 | 81 |
| RMW | 0.60 | 2.79 (3.17)\* | 2.07 (2.38) | 0.98 (1.14) | -0.82 (-0.96) | 39 | 15 |
| CMA | 0.56 | 0.38 (0.61) | -0.30 (-0.48) | -1.32 (-2.11) | -3.02 (-4.61)\* | 6 | none |

In real time, Cederburg et al.'s strategy (1936-08 to 2026-09). Cells are the Sharpe-ratio gain with the block-bootstrap p-value. Both the combination and the unmanaged benchmark pay for their own trading.

| Factor | Turnover a month | gross | 10 bps | 25 bps | 50 bps | Break-even (bps) |
|---|---:|---:|---:|---:|---:|---:|
| MKT | 0.33 | -0.06 [0.53] | -0.10 [0.32] | -0.15 [0.12] | -0.24 [0.01]\* | none |
| SMB | 0.15 | -0.05 [0.53] | -0.08 [0.30] | -0.13 [0.10] | -0.21 [0.01]\* | none |
| HML | 0.30 | -0.03 [0.71] | -0.07 [0.33] | -0.13 [0.06] | -0.24 [0.002]\* | none |
| MOM | 0.71 | +0.40 [0.004]\* | +0.34 [0.01] | +0.27 [0.05] | +0.14 [0.29] | 76 |
| RMW | 0.63 | +0.17 [0.34] | +0.09 [0.62] | -0.03 [0.88] | -0.23 [0.32] | 21 |
| CMA | 0.11 | -0.03 [0.07] | -0.04 [0.03] | -0.06 [0.01] | -0.09 [0.008]\* | none |

## Paper samples, before costs

<table>
<tr>
<th>In sample (1926-08 to 2015-04)</th>
<th>In real time (out of sample, 1936-08 to 2016-12)</th>
</tr>
<tr>
<td valign="top">

| Factor | Alpha (%/yr) | t, White | t, Newey-West | Holm p | Appraisal ratio |
|---|---:|---:|---:|---:|---:|
| MKT | 4.93 | 3.15 | 2.90 | 0.015 | 0.33 |
| SMB | -0.59 | -0.64 | -0.50 | 1.000 | -0.07 |
| HML | 1.73 | 1.64 | 1.41 | 0.472 | 0.17 |
| MOM | 12.83 | 7.47 | 6.49 | 0.000 | 0.87 |
| RMW | 2.80 | 3.14 | 2.96 | 0.015 | 0.44 |
| CMA | 0.36 | 0.53 | 0.57 | 1.000 | 0.07 |

</td>
<td valign="top">

| Factor | Sharpe, with managed | Sharpe, unmanaged | Difference | p, JK | p, bootstrap | Holm p | CER gain (%/yr) [p] |
|---|---:|---:|---:|---:|---:|---:|---:|
| MKT | 0.42 | 0.46 | -0.04 | 0.617 | 0.674 | 1.000 | -0.22 [0.81] |
| SMB | 0.13 | 0.19 | -0.06 | 0.362 | 0.448 | 1.000 | -0.38 [0.26] |
| HML | 0.37 | 0.44 | -0.07 | 0.333 | 0.362 | 1.000 | -0.24 [0.68] |
| MOM | 0.89 | 0.48 | +0.41 | 0.000 | 0.006 | 0.034 | +5.67 [0.000] |
| RMW | 0.51 | 0.33 | +0.18 | 0.383 | 0.420 | 1.000 | +1.61 [0.39] |
| CMA | 0.53 | 0.56 | -0.04 | 0.139 | 0.120 | 0.602 | -0.38 [0.14] |

</td>
</tr>
</table>

## Extended to 2026-09 (new), before costs

<table>
<tr>
<th>In sample (1926-08 to 2026-09)</th>
<th>In real time (out of sample, 1936-08 to 2026-09)</th>
</tr>
<tr>
<td valign="top">

| Factor | Alpha (%/yr) | t, White | t, Newey-West | Holm p | Appraisal ratio |
|---|---:|---:|---:|---:|---:|
| MKT | 4.51 | 3.09 | 2.82 | 0.019 | 0.31 |
| SMB | -0.54 | -0.64 | -0.50 | 1.000 | -0.06 |
| HML | 1.57 | 1.57 | 1.37 | 0.515 | 0.15 |
| MOM | 11.95 | 7.62 | 6.56 | 0.000 | 0.82 |
| RMW | 2.79 | 3.39 | 3.17 | 0.008 | 0.42 |
| CMA | 0.38 | 0.58 | 0.61 | 1.000 | 0.07 |

</td>
<td valign="top">

| Factor | Sharpe, with managed | Sharpe, unmanaged | Difference | p, JK | p, bootstrap | Holm p | CER gain (%/yr) [p] |
|---|---:|---:|---:|---:|---:|---:|---:|
| MKT | 0.44 | 0.50 | -0.06 | 0.431 | 0.526 | 1.000 | -0.24 [0.77] |
| SMB | 0.09 | 0.14 | -0.05 | 0.446 | 0.533 | 1.000 | -0.35 [0.25] |
| HML | 0.32 | 0.34 | -0.03 | 0.690 | 0.712 | 1.000 | -0.21 [0.69] |
| MOM | 0.85 | 0.45 | +0.40 | 0.000 | 0.004 | 0.024 | +5.14 [0.000] |
| RMW | 0.47 | 0.31 | +0.17 | 0.338 | 0.340 | 1.000 | +1.49 [0.34] |
| CMA | 0.39 | 0.42 | -0.03 | 0.075 | 0.069 | 0.343 | -0.31 [0.14] |

</td>
</tr>
</table>

## Only the months after each paper's sample (new), before costs

<table>
<tr>
<th>In sample (2015-05 to 2026-09)</th>
<th>In real time (out of sample, 2017-01 to 2026-09)</th>
</tr>
<tr>
<td valign="top">

| Factor | Alpha (%/yr) | t, White | t, Newey-West | Holm p | Appraisal ratio |
|---|---:|---:|---:|---:|---:|
| MKT | 1.22 | 0.29 | 0.28 | 0.969 | 0.10 |
| SMB | -1.42 | -0.89 | -0.91 | 0.969 | -0.26 |
| HML | -4.13 | -1.64 | -1.62 | 0.627 | -0.48 |
| MOM | 3.31 | 1.10 | 1.14 | 0.969 | 0.31 |
| RMW | 1.99 | 1.18 | 1.17 | 0.969 | 0.33 |
| CMA | -2.30 | -1.35 | -1.36 | 0.862 | -0.40 |

</td>
<td valign="top">

| Factor | Sharpe, with managed | Sharpe, unmanaged | Difference | p, JK | p, bootstrap | Holm p | CER gain (%/yr) [p] |
|---|---:|---:|---:|---:|---:|---:|---:|
| MKT | 0.68 | 0.79 | -0.12 | 0.577 | 0.666 | 1.000 | -0.45 [0.80] |
| SMB | -0.26 | -0.30 | +0.05 | 0.300 | 0.368 | 1.000 | -0.07 [0.79] |
| HML | -0.29 | -0.18 | -0.10 | 0.017 | 0.042 | 0.210 | +0.06 [0.91] |
| MOM | 0.37 | 0.24 | +0.13 | 0.557 | 0.559 | 1.000 | +1.02 [0.54] |
| RMW | 0.27 | 0.22 | +0.05 | 0.700 | 0.659 | 1.000 | +0.95 [0.53] |
| CMA | -0.14 | -0.12 | -0.02 | 0.045 | 0.035 | 0.210 | -0.02 [0.90] |

</td>
</tr>
</table>

Bootstrap: circular blocks of 6 months, 4999 draws.
