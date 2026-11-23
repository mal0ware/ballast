"""Numbers printed in the source papers, typed in by hand for comparison.

Only the six factors available from the French library are kept. See
``PAPER.md`` for which version of each paper was read.
"""

from __future__ import annotations

#: Last month of managed returns in Moreira and Muir's sample. The paper says
#: "1926-2015"; April 2015 is the month that gives its N of 1,065 for the market.
MM_SAMPLE_END = "2015-04"

#: Cederburg et al.: "The sample periods end in December 2016" (Table 1 caption).
COWY_SAMPLE_END = "2016-12"

#: Moreira and Muir (NBER working paper 22208), Table 1, Panel A. Alpha, its
#: standard error and RMSE are in percent per year.
MM_TABLE1_PANEL_A: dict[str, dict[str, float]] = {
    "MKT": {"alpha": 4.86, "alpha_se": 1.56, "beta": 0.61, "beta_se": 0.05,
            "nobs": 1065, "r2": 0.37, "rmse": 51.39},
    "SMB": {"alpha": -0.58, "alpha_se": 0.91, "beta": 0.62, "beta_se": 0.08,
            "nobs": 1065, "r2": 0.38, "rmse": 30.44},
    "HML": {"alpha": 1.97, "alpha_se": 1.02, "beta": 0.57, "beta_se": 0.07,
            "nobs": 1065, "r2": 0.32, "rmse": 34.92},
    "MOM": {"alpha": 12.51, "alpha_se": 1.71, "beta": 0.47, "beta_se": 0.07,
            "nobs": 1060, "r2": 0.22, "rmse": 50.37},
    "RMW": {"alpha": 2.44, "alpha_se": 0.83, "beta": 0.62, "beta_se": 0.08,
            "nobs": 621, "r2": 0.38, "rmse": 20.16},
    "CMA": {"alpha": 0.38, "alpha_se": 0.67, "beta": 0.68, "beta_se": 0.05,
            "nobs": 621, "r2": 0.46, "rmse": 17.55},
}  # fmt: skip

#: Same table, Panel B: alpha when the three Fama-French factors are added.
MM_TABLE1_PANEL_B: dict[str, dict[str, float]] = {
    "MKT": {"alpha_ff3": 5.45, "alpha_ff3_se": 1.56},
    "SMB": {"alpha_ff3": -0.33, "alpha_ff3_se": 0.89},
    "HML": {"alpha_ff3": 2.66, "alpha_ff3_se": 1.02},
    "MOM": {"alpha_ff3": 10.52, "alpha_ff3_se": 1.60},
    "RMW": {"alpha_ff3": 3.18, "alpha_ff3_se": 0.83},
    "CMA": {"alpha_ff3": -0.01, "alpha_ff3_se": 0.68},
}

#: Cederburg et al. (2020), Table 1, Panels A to D: direct comparison.
COWY_TABLE1: dict[str, dict[str, float]] = {
    "MKT": {"sr_original": 0.42, "sr_managed": 0.51, "sr_diff": 0.09, "sr_p": 0.30,
            "correlation": 0.63},
    "SMB": {"sr_original": 0.23, "sr_managed": 0.08, "sr_diff": -0.15, "sr_p": 0.09,
            "correlation": 0.63},
    "HML": {"sr_original": 0.40, "sr_managed": 0.38, "sr_diff": -0.02, "sr_p": 0.86,
            "correlation": 0.57},
    "MOM": {"sr_original": 0.48, "sr_managed": 0.99, "sr_diff": 0.50, "sr_p": 0.00,
            "correlation": 0.48},
    "RMW": {"sr_original": 0.38, "sr_managed": 0.51, "sr_diff": 0.13, "sr_p": 0.29,
            "correlation": 0.59},
    "CMA": {"sr_original": 0.53, "sr_managed": 0.40, "sr_diff": -0.13, "sr_p": 0.23,
            "correlation": 0.68},
}  # fmt: skip

#: Cederburg et al. (2020), Table 3, Panels A.1 and A.2. ``c_star`` is for
#: returns in percent, so it is 10,000 times the constant for decimal returns.
COWY_TABLE3: dict[str, dict[str, float]] = {
    "MKT": {"alpha": 4.63, "alpha_t": 3.08, "beta": 0.63, "r2_adj": 0.40,
            "appraisal_ratio": 0.32, "c_star": 10.33},
    "SMB": {"alpha": -0.76, "alpha_t": -0.87, "beta": 0.63, "r2_adj": 0.40,
            "appraisal_ratio": -0.09, "c_star": 2.63},
    "HML": {"alpha": 1.87, "alpha_t": 1.88, "beta": 0.57, "r2_adj": 0.33,
            "appraisal_ratio": 0.19, "c_star": 2.95},
    "MOM": {"alpha": 12.39, "alpha_t": 7.31, "beta": 0.48, "r2_adj": 0.23,
            "appraisal_ratio": 0.86, "c_star": 4.60},
    "RMW": {"alpha": 2.23, "alpha_t": 2.57, "beta": 0.59, "r2_adj": 0.34,
            "appraisal_ratio": 0.36, "c_star": 1.48},
    "CMA": {"alpha": 0.26, "alpha_t": 0.39, "beta": 0.68, "r2_adj": 0.46,
            "appraisal_ratio": 0.05, "c_star": 1.53},
}  # fmt: skip

#: Cederburg et al. (2020), Table 5, Panel A: real-time combination strategies,
#: K = 120, expanding window, gamma = 5, leverage cap of 5. ``combo`` is their
#: [S1], ``original`` their [S2], ``expost`` their [S3]. CERs in percent per year.
COWY_TABLE5_PANEL_A: dict[str, dict[str, float]] = {
    "MKT": {"sr_combo": 0.42, "sr_original": 0.46, "sr_diff": -0.04, "sr_p": 0.64,
            "sr_expost": 0.53, "cer_combo": 1.56, "cer_original": 1.75,
            "cer_diff": -0.19, "cer_p": 0.83, "cer_expost": 2.79},
    "SMB": {"sr_combo": 0.14, "sr_original": 0.19, "sr_diff": -0.06, "sr_p": 0.37,
            "sr_expost": 0.26, "cer_combo": 0.00, "cer_original": 0.38,
            "cer_diff": -0.37, "cer_p": 0.27, "cer_expost": 0.67},
    "HML": {"sr_combo": 0.38, "sr_original": 0.43, "sr_diff": -0.06, "sr_p": 0.41,
            "sr_expost": 0.50, "cer_combo": 1.41, "cer_original": 1.61,
            "cer_diff": -0.20, "cer_p": 0.73, "cer_expost": 2.47},
    "MOM": {"sr_combo": 0.92, "sr_original": 0.49, "sr_diff": 0.44, "sr_p": 0.00,
            "sr_expost": 0.99, "cer_combo": 8.47, "cer_original": 2.29,
            "cer_diff": 6.18, "cer_p": 0.00, "cer_expost": 9.87},
    "RMW": {"sr_combo": 0.44, "sr_original": 0.31, "sr_diff": 0.13, "sr_p": 0.53,
            "sr_expost": 0.58, "cer_combo": 1.96, "cer_original": 0.91,
            "cer_diff": 1.04, "cer_p": 0.57, "cer_expost": 3.42},
    "CMA": {"sr_combo": 0.52, "sr_original": 0.56, "sr_diff": -0.03, "sr_p": 0.20,
            "sr_expost": 0.64, "cer_combo": 2.74, "cer_original": 3.09,
            "cer_diff": -0.35, "cer_p": 0.21, "cer_expost": 4.04},
}  # fmt: skip
