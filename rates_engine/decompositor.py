"""
Cash flow discounting and inflation decomposition (spot breakeven, SABB forward, IRP).
"""

from typing import Dict, Tuple
import numpy as np
import pandas as pd
from .curves import YieldCurve


class CashBondDiscountEngine:
    """Discounts discrete cash flows from zero curve discount factors."""

    @classmethod
    def bond_price_from_zero_curve(
        cls, cash_flows: np.ndarray, cf_tenors: np.ndarray, curve: YieldCurve
) -> float:
        dfs = curve.discount_factor(cf_tenors, freq=2)
        return float(np.sum(cash_flows * dfs))

class InflationDecompositor:
    """Decomposes spot breakevens into survey CPI, liquidity wedges, and latent IRP."""

    def __init__(self, nom_curve: YieldCurve, tips_curve: YieldCurve):
        self.nom_curve = nom_curve
        self.tips_curve = tips_curve

    def decompose(
            self,
            eval_grid: np.ndarray,
            survey_mats: np.ndarray,
            survey_cpi_exp: np.ndarray,
            liquidity_wedge_bps: np.ndarray,
            sigma_wedge_bps: np.ndarray,
            seasonal_factors: np.ndarray,
            current_month: int,
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        nom_zeros = np.asarray(self.nom_curve.zero_rate(eval_grid))
        tips_zeros = np.asarray(self.tips_curve.zero_rate(eval_grid))
        unadj_bei_bps = (nom_zeros - tips_zeros) * 10000.0

        s_m = seasonal_factors[current_month - 1]
        sa_factor = (s_m - 1.0) * (1.0 / eval_grid)
        sa_bei_bps = unadj_bei_bps - (sa_factor * 10000.0)

        survey_interp = np.interp(eval_grid, survey_mats, survey_cpi_exp) * 10000.0

        irp_point_bps = sa_bei_bps - survey_interp + liquidity_wedge_bps
        irp_lower = irp_point_bps - sigma_wedge_bps
        irp_upper = irp_point_bps + sigma_wedge_bps

        df = pd.DataFrame(
            {
                "Maturity_Years": eval_grid,
                "Nominal_Zero_Pct": nom_zeros * 100.0,
                "TIPS_Zero_Pct": tips_zeros * 100.0,
                "Unadjusted_BEI_Bps": unadj_bei_bps,
                "SA_BEI_Bps": sa_bei_bps,
                "Cleveland_Fed_Survey_CPI_Bps": survey_interp,
                "Dyn_Liquidity_Wedge_Bps": liquidity_wedge_bps,
                "Extracted_IRP_Point_Bps": irp_point_bps,
                "IRP_Lower_1Sigma_Bps": irp_lower,
                "IRP_Upper_1Sigma_Bps": irp_upper,
            }
        )

        fwd_5y5y_nom = self.nom_curve.forward_rate_sabb(5.0, 10.0)
        fwd_5y5y_tips = self.tips_curve.forward_rate_sabb(5.0, 10.0)
        fwd_5y5y_bei_bps = (fwd_5y5y_nom - fwd_5y5y_tips) * 10000.0

        row_10y = df[df["Maturity_Years"] == 10.0].iloc[0]
        row_30y = df[df["Maturity_Years"] == 30.0].iloc[0]

        nom_roll_10y = (self.nom_curve.zero_rate(9.75) - self.nom_curve.zero_rate(10.0)) * 10000.0
        tips_roll_10y = (self.tips_curve.zero_rate(9.75) - self.tips_curve.zero_rate(10.0)) * 10000.0

        metrics = {
            "5Y5Y_Forward_BEI_SABB_Bps": float(fwd_5y5y_bei_bps),
            "10Y_Extracted_IRP_Bps": float(row_10y["Extracted_IRP_Point_Bps"]),
            "10Y_IRP_Lower_1Sigma_Bps": float(row_10y["IRP_Lower_1Sigma_Bps"]),
            "10Y_IRP_Upper_1Sigma_Bps": float(row_10y["IRP_Upper_1Sigma_Bps"]),
            "30Y_Extracted_IRP_Bps": float(row_30y["Extracted_IRP_Point_Bps"]),
            "30Y_IRP_Lower_1Sigma_Bps": float(row_30y["IRP_Lower_1Sigma_Bps"]),
            "30Y_IRP_Upper_1Sigma_Bps": float(row_30y["IRP_Upper_1Sigma_Bps"]),
            "10Y_Nominal_3M_RollDown_Bps": float(nom_roll_10y),
            "10Y_TIPS_3M_RollDown_Bps": float(tips_roll_10y),
        }

        return df, metrics
