"""
Market frictions, liquidity wedges, empirical betas, and reference indexation.
"""

from dataclasses import dataclass
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class DKWEconometricPriors:
    """
    Literature-grounded baseline calibration from D'Amico, Kim, and Wei (DKW 2018, Table 3)
    and Pflueger & Viceira (2011) for U.S. TIPS liquidity premia.
    """

    BASE_FRONT_END_BPS: float = 6.50
    TERMINAL_FLOOR_BPS: float = 1.50
    DECAY_HORIZON_YEARS: float = 5.00
    STRESS_SENSITIVITY: float = 0.25
    RESIDUAL_VOLATILITY: float = 0.20

class DynamicMarketFrictions:
    """
    Computes dynamic liquidity penalities, empirical OLS betas, and reference indexation.
    Enforces SR 11-7 fail-fast data governance: refuses to inject arbitrary fallbacks if inputs fail.
    """

    MIN_OBSERVATIONS: int = 30
    MIN_VARIANCE_TOL: float = 1e-8

    @classmethod
    def compute_dynamic_liquidity_wedge(
        cls,
        maturities: np.ndarray,
        financial_stress_idx: float,
        priors: DKWEconometricPriors = DKWEconometricPriors(),
    ) -> Tuple[np.ndarray, np.ndarray]:
        tau = np.asarray(maturities, dtype=float)
        stress_scaled = max(0.0, financial_stress_idx + 1.0)

        # DKW (2018) Affine Decay Specification
        base_term = (priors.BASE_FRONT_END_BPS * np.exp(-tau / priors.DECAY_HORIZON_YEARS) + priors.TERMINAL_FLOOR_BPS)
        stress_multiplier = 1.0 + priors.STRESS_SENSITIVITY * stress_scaled
        lambda_bps = base_term * stress_multiplier
        sigma_bps = lambda_bps * priors.RESIDUAL_VOLATILITY

        return lambda_bps, sigma_bps

    @classmethod
    def compute_all_parameters(
        cls,
        nom_10y_series: pd.Series,
        tips_10y_series: pd.Series,
        nom_30y_series: pd.Series,
        tips_30y_series: pd.Series,
        cpi_nsa_series: pd.Series,
        sofr_rate: float,
        tgcr_rate: float,
        settlement_date: str,
    ) -> Dict[str, Any]:
        # 1. 10Y Empirical OLS Beta Estimation
        aligned_10y = pd.concat([nom_10y_series, tips_10y_series], axis=1, join="inner").dropna()
        diffs_10y = aligned_10y.diff().dropna().tail(60)

        if len(diffs_10y) < cls.MIN_OBSERVATIONS:
            raise ValueError(
                f"[SR 11-7 MODEL ERROR] Insufficient 10Y time-series observations ({len(diffs_10y)} < {cls.MIN_OBSERVATIONS}). "
                "Refusing silent fallback injection."
            )
        cov_10y = np.cov(diffs_10y.iloc[:, 0], diffs_10y.iloc[:, 1])
        if cov_10y[0, 0] <= cls.MIN_VARIANCE_TOL or np.isnan(cov_10y[0, 1]):
            raise ValueError(
                f"[SR 11-7 MODEL ERROR] Degenerate variance ({cov_10y[0, 0]:.2e}) detected in 10Y nominal series. "
                "Cannot evaluate empirical hedge beta."
            )
        beta_10y = float(cov_10y[0, 1] / cov_10y[0, 0])

        # 2. 30Y Empirical OLS Beta Estimation
        aligned_30y = pd.concat([nom_30y_series, tips_30y_series], axis=1, join="inner").dropna()
        diffs_30y = aligned_30y.diff().dropna().tail(60)

        if len(diffs_30y) < cls.MIN_OBSERVATIONS:
            raise ValueError(
                f"[SR 11-7 MODEL ERROR] Insufficient 30Y time-series observations ({len(diffs_30y)} < {cls.MIN_OBSERVATIONS}). "
                "Refusing silent fallback injection."
            )
        cov_30y = np.cov(diffs_30y.iloc[:, 0], diffs_30y.iloc[:, 1])
        if cov_30y[0, 0] <= cls.MIN_VARIANCE_TOL or np.isnan(cov_30y[0, 1]):
            raise ValueError(
                f"[SR 11-7 MODEL ERROR] Degenerate variance ({cov_30y[0, 0]:.2e}) detected in 30Y nominal series. "
                "Cannot evaluate empirical hedge beta."
            )
        beta_30y = float(cov_30y[0, 1] / cov_30y[0, 0])

        # 3. Daily Reference CPI Calculation
        settle_dt = pd.to_datetime(settlement_date)
        d = settle_dt.day
        dim = pd.Period(settle_dt, freq="D").days_in_month

        cpi_sorted = cpi_nsa_series.dropna().sort_index()
        cpi_m3 = float(cpi_sorted.iloc[-3])
        cpi_m2 = float(cpi_sorted.iloc[-2])
        ref_cpi = cpi_m3 + ((d - 1) / dim) * (cpi_m2 - cpi_m3)
        base_cpi = float(cpi_sorted.iloc[-12])
        cif = ref_cpi / base_cpi

        return {
            "Beta_TIPS_10Y": beta_10y,
            "Beta_TIPS_30Y": beta_30y,
            "Current_Ref_CPI": float(ref_cpi),
            "Base_Ref_CPI": float(base_cpi),
            "CIF": float(cif),
            "Repo_Nominal_Bps": float(sofr_rate * 100.0),
            "Repo_TIPS_Bps": float(tgcr_rate * 100.0),
        }
