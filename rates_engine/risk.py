"""
Trade structuring, Key Rate Duration decomposition, and FRTB historical market risk.
"""

from typing import Dict
import numpy as np
import pandas as pd
from .curves import YieldCurve

class BreakevenTradePricer:
    """Sizes and attributes PnL for a duration-hedged, beta-adjusted 10Y Breakeven Box."""

    def __init__(
            self,
            nom_par_notional: float,
            nom_curve: YieldCurve,
            tips_curve: YieldCurve,
            tenor: float,
            cif: float,
            beta_tips: float,
            repo_nom_bps: float,
            repo_tips_bps: float,
    ):
        self.nom_par = float(nom_par_notional)
        self.nom_curve = nom_curve
        self.tips_curve = tips_curve
        self.tenor = float(tenor)
        self.cif = float(cif)
        self.beta = float(beta_tips)
        self.repo_nom = float(repo_nom_bps)
        self.repo_tips = float(repo_tips_bps)

    def calculate_trade_structure(self) -> Dict[str, float]:
        d_nom = self.nom_curve.modified_duration(self.tenor)
        d_tips = self.tips_curve.modified_duration(self.tenor)
        c_nom = self.nom_curve.convexity(self.tenor)
        c_tips = self.tips_curve.convexity(self.tenor)

        dv01_nom = self.nom_par * d_nom * 0.0001
        # Duration-, CIF-, and Beta-neutral sizing: N_TIPS = DV01_nom / (CIF * D_tips * 0.0001 * beta)
        tips_hedged_par = dv01_nom / (self.cif * d_tips * 0.0001 * self.beta)
        dv01_tips = tips_hedged_par * self.cif * d_tips * 0.0001

        return {
            "Nominal_Notional_USD": self.nom_par,
            "TIPS_Hedged_Notional_USD": float(tips_hedged_par),
            "Nominal_DV01_USD": float(dv01_nom),
            "TIPS_Hedged_DV01_USD": float(dv01_tips),
            "Nominal_Duration": float(d_nom),
            "TIPS_Duration": float(d_tips),
            "Nominal_Convexity": float(c_nom),
            "TIPS_Convexity": float(c_tips),
        }

    def evaluate_horizon_pnl(
        self, dy_nom_bps: float, dy_tips_bps: float, dt_years: float = 0.25 
    ) -> Dict[str, float]:
        st = self.calculate_trade_structure()
        dy_n = dy_nom_bps * 0.0001
        dy_r = dy_tips_bps * 0.0001

        pnl_delta_nom = -st["Nominal_Notional_USD"] * st["Nominal_Duration"] * dy_n
        pnl_gamma_nom = 0.5 * st["Nominal_Notional_USD"] * st["Nominal_Convexity"] * (dy_n ** 2)
        pnl_delta_tips = +(st["TIPS_Hedged_Notional_USD"] * self.cif) * st["TIPS_Duration"] * dy_r
        pnl_gamma_tips = -0.5 * (st["TIPS_Hedged_Notional_USD"] * self.cif) * st["TIPS_Convexity"] * (dy_r**2)

        nom_roll = self.nom_curve.zero_rate(self.tenor - dt_years) - self.nom_curve.zero_rate(self.tenor)
        tips_roll = self.tips_curve.zero_rate(self.tenor - dt_years) - self.tips_curve.zero_rate(self.tenor)
        pnl_roll_nom = -st["Nominal_Notional_USD"] * st["Nominal_Duration"] * nom_roll
        pnl_roll_tips = +st["TIPS_Hedged_Notional_USD"] * self.cif * st["TIPS_Duration"] * tips_roll

        financing_drag = -st["Nominal_Notional_USD"] * (self.repo_nom * 0.0001) * dt_years
        collateral_gain = +st["TIPS_Hedged_Notional_USD"] * self.cif * (self.repo_tips * 0.0001) * dt_years

        net_delta = pnl_delta_nom + pnl_delta_tips
        net_gamma = pnl_gamma_nom + pnl_gamma_tips
        net_roll = pnl_roll_nom + pnl_roll_tips
        net_repo = financing_drag + collateral_gain

        return {
            "Delta_PnL_USD": float(net_delta),
            "Convexity_Gamma_PnL_USD": float(net_gamma),
            "RollDown_PnL_USD": float(net_roll),
            "Repo_Carry_PnL_USD": float(net_repo),
            "Total_Horizon_PnL_USD": float(net_delta + net_gamma + net_roll + net_repo),
        }

class HistoricalMarketRiskEngine:
    """
    Computes 99% Historical VaR and Expected Shortfall (ES) across rolling
    empirical yield changes in accordance with Basel III / FRTB standards.
    """

    @classmethod
    def evaluate_portfolio_var(
        cls,
        nom_10y_series: pd.Series,
        tips_10y_series: pd.Series,
        pricer: BreakevenTradePricer,
        holding_period_days: int = 10,
        confidence_level: float = 0.99,
    ) -> Dict[str, float]:
        df = pd.concat([nom_10y_series.diff(), tips_10y_series.diff()], axis=1).dropna().tail(252)
        df.columns = ["dNom", "dTIPS"]

        scale = np.sqrt(holding_period_days)
        simulated_pnls = []

        for _, row in df.iterrows():
            shift_n_bps = row["dNom"] * 100.0 * scale
            shift_r_bps = row["dTIPS"] * 100.0 * scale
            res = pricer.evaluate_horizon_pnl(shift_n_bps, shift_r_bps, dt_years=holding_period_days / 365.25)
            simulated_pnls.append(res["Total_Horizon_PnL_USD"])

        pnl_arr = np.array(simulated_pnls)
        var_threshold = np.percentile(pnl_arr, (1.0 - confidence_level) * 100.0)
        tail_losses = pnl_arr[pnl_arr <= var_threshold]
        expected_shortfall = np.mean(tail_losses) if len(tail_losses) > 0 else var_threshold

        return {
            "VaR_99_10D_USD": float(abs(var_threshold)),
            "Expected_Shortfall_99_10D_USD": float(abs(expected_shortfall)),
            "Max_Historical_Drawdown_USD": float(abs(np.min(pnl_arr))),
        }

class CurveSpreadPricer:
    """Sizes a Duration-Neutral 10s30s Breakeven Curve Box."""

    @classmethod
    def size_10s30s_box(
        cls,
        nom_curve: YieldCurve,
        tips_curve: YieldCurve,
        cif: float,
        beta_10y: float,
        beta_30y: float,
        target_10y_notional: float = 100_000_000.0,
    ) -> Dict[str, float]:
        d_nom_10 = nom_curve.modified_duration(10.0)
        d_nom_30 = nom_curve.modified_duration(30.0)
        d_tips_10 = tips_curve.modified_duration(10.0)
        d_tips_30 = tips_curve.modified_duration(30.0)

        target_dv01 = target_10y_notional * d_nom_10 * 0.0001
        tips_10y_par = target_dv01 / (cif * d_tips_10 * 0.0001 * beta_10y)
        nom_30y_par  = target_dv01 / (d_nom_30 * 0.0001)
        tips_30y_par = target_dv01 / (cif * d_tips_30 * 0.0001 * beta_30y)

        return {
            "Leg1_Long_Nom_10Y_USD": float(target_10y_notional),
            "Leg1_Short_TIPS_10Y_USD": float(tips_10y_par),
            "Leg2_Short_Nom_30Y_USD": float(nom_30y_par),
            "Leg2_Long_TIPS_30Y_USD": float(tips_30y_par),
            "Matched_DV01_USD": float(target_dv01),
        }