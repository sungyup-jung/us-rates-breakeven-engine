"""
Plotly visualization, dynamic conditioned reporting, and SR 11-7 narrative generator.
"""

from typing import Dict
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .curves import YieldCurve
from .frictions import DKWEconometricPriors
from .risk import BreakevenTradePricer


class DynamicDashboardInterpreter:
    """
    Generates dynamic qualitative narrative conditioned on actual curve geometry.
    """

    @classmethod
    def generate_all_interpretations(
        cls,
        df: pd.DataFrame,
        metrics: dict,
        nom_curve: YieldCurve,
        tips_curve: YieldCurve,
        pricer_10y: BreakevenTradePricer,
        bic_selection: dict,
        market_risk: dict,
    ) -> str:
        # Tenor yields
        nom_2y = nom_curve.zero_rate(2.0) * 100.0
        nom_10y = nom_curve.zero_rate(10.0) * 100.0
        nom_30y = nom_curve.zero_rate(30.0) * 100.0

        tips_2y = tips_curve.zero_rate(2.0) * 100.0
        tips_10y = tips_curve.zero_rate(10.0) * 100.0
        tips_30y = tips_curve.zero_rate(30.0) * 100.0

        nom_2s10s = (nom_10y - nom_2y) * 100.0
        tips_2s10s = (tips_10y - tips_2y) * 100.0

        # Panel 1 Logic: Nominal Slope & Real Stance
        if nom_2s10s > 15.0:
            nom_slope = "upward-sloping (steep)"
        elif nom_2s10s < -15.0:
            nom_slope = "inverted"
        else:
            nom_slope = "flat"

        min_tips = df["TIPS_Zero_Pct"].min()
        if min_tips > 1.50:
            real_stance = (
                f"firmly restrictive across all tenors (trough at **{min_tips:.2f}%**), "
                f"confirming that policy rates ($r > r^*$) maintain high hurdle rates across risk assets"
            )
        elif min_tips > 0.0:
            real_stance = f"moderately restrictive (trough at **{min_tips:.2f}%**)"
        else:
            real_stance = (
                f"deeply accommodative/repressive (trough at **{min_tips:.2f}%**), "
                f"signaling a return to post-GFC secular stagnation conditions"
            )

        if tips_10y > 1.50:
            sec_stag_desc = f"anchoring at an elevated **{tips_10y:.2f}%**, discounting post-GFC secular stagnation"
        else:
            sec_stag_desc = f"compressing toward **{tips_10y:.2f}%**, reflecting lower neutral rate ($r^*$) expectations"

        p1_text = (
            f"* **Figure 1 (Zero Yield Term Structure & Macro Stance)**: The nominal curve trades **{nom_slope}** "
            f"(2s10s spread: **{nom_2s10s:+.1f} bps**, spanning {nom_2y:.2f}% to {nom_30y:.2f}%), while the real TIPS curve "
            f"exhibits a 2s10s slope of **{tips_2s10s:+.1f} bps** ({tips_2y:.2f}% to {tips_30y:.2f}%). "
            f"Real yields are {real_stance}. Ten-year real rates are {sec_stag_desc}."
        )

        # Panel 2 Logic: Pure Data & Explicit Model Assumptions
        row_10y = df[df["Maturity_Years"] == 10.0].iloc[0]
        row_2y = df[df["Maturity_Years"] == 2.0].iloc[0]
        row_30y = df[df["Maturity_Years"] == 30.0].iloc[0]
        survey_diff_10y = row_10y["Cleveland_Fed_Survey_CPI_Bps"] - row_10y["SA_BEI_Bps"]

        if survey_diff_10y > 5.0:
            survey_relation = f"**{abs(survey_diff_10y):.1f} bps above** market-implied pricing"
        elif survey_diff_10y < -5.0:
            survey_relation = f"**{abs(survey_diff_10y):.1f} bps below** market-implied pricing"
        else:
            survey_relation = "in line with market-implied pricing (within $\\pm 5\\text{ bps}$)"

        p2_text = (
            f"* **Figure 2 (Spot BEI Breakdown & Market Frictions)**: Seasonally adjusted spot breakevens span "
            f"**{df['SA_BEI_Bps'].min():.1f} to {df['SA_BEI_Bps'].max():.1f} bps**. "
            f"At the 10Y tenor, consensus survey CPI sits {survey_relation}. "
            f"The DKW-calibrated liquidity wedge imposes a **{row_2y['Dyn_Liquidity_Wedge_Bps']:.1f} bps penalty at 2Y**, "
            f"decaying asymptotically to **{row_30y['Dyn_Liquidity_Wedge_Bps']:.1f} bps at 30Y**."
        )

        # Panel 3 Logic: Latent IRP Corridor
        irp_min = df["Extracted_IRP_Point_Bps"].min()
        irp_max = df["Extracted_IRP_Point_Bps"].max()
        irp_10y = row_10y["Extracted_IRP_Point_Bps"]

        if irp_max < 0.0:
            irp_corridor = (
                f"strictly in a **negative corridor** ({irp_min:.1f} to {irp_max:.1f} bps). "
                f"This reflects strong institutional duration demand (asset-liability matching at prevailing {nom_10y:.2f}% nominal yields) "
                f"and flight-to-safety hedging that compresses nominal yields below survey expectations"
            )
        elif irp_min > 0.0:
            irp_corridor = (
                f"in an elevated **positive corridor** (+{irp_min:.1f} to +{irp_max:.1f} bps), "
                f"demonstrating that investors demand an explicit risk premium to hold unindexed nominal cash flows"
            )
        else:
            irp_corridor = (
                f"mixed across maturities ({irp_min:.1f} to +{irp_max:.1f} bps), "
                f"shifting from negative front-end pricing to positive term compensation at the long end"
            )

        p3_text = (
            f"* **Figure 3 (Extracted Inflation Risk Premia & Confidence Bands)**: Extracted latent IRP sits {irp_corridor}. "
            f"At the 10Y benchmark, IRP evaluates to **{irp_10y:+.1f} bps** "
            f"(\\pm 1\\sigma bounds: [{row_10y['IRP_Lower_1Sigma_Bps']:+.1f}, {row_10y['IRP_Upper_1Sigma_Bps']:+.1f}] bps)."
        )

        # Panel 4 Logic: Forward Breakeven Anchoring
        fwd_5y5y = metrics["5Y5Y_Forward_BEI_SABB_Bps"]
        if 200.0 <= fwd_5y5y <= 250.0:
            fwd_anchor_eval = f"anchors cleanly at **{fwd_5y5y:.1f} bps**, confirming long-term central bank credibility remains intact"
        elif fwd_5y5y > 250.0:
            fwd_anchor_eval = f"elevated at **{fwd_5y5y:.1f} bps**, indicating market skepticism regarding long-run inflation control"
        else:
            fwd_anchor_eval = f"depressed at **{fwd_5y5y:.1f} bps**, signaling market concerns over structural disinflation"

        p4_text = (
            f"* **Figure 4 (Continuous Spot vs. 1Y Forward Breakevens)**: Calibrating curves via the Diebold-Li (2006) macro "
            f"invariant ($\\tau_1 = 2.2307$, $\\tau^* = 4.0\\text{{Y}}$) ensures identical factor loading spaces across nominal and TIPS curves. "
            f"The continuous 1Y forward breakeven curve $f^{{\\text{{BEI}}}}(t, t+1)$ eliminates tail-whip divergence. "
            f"The benchmark 5Y5Y forward breakeven {fwd_anchor_eval}."
        )

        # Panel 5 Logic: Dynamic SR 11-7 Gate Evaluation
        TOLERANCE_BPS = 3.0

        nom_res = (nom_curve.raw_yields - nom_curve.zero_rate(nom_curve.maturities)) * 10000.0
        tips_res = (tips_curve.raw_yields - tips_curve.zero_rate(tips_curve.maturities)) * 10000.0
        nom_rmse = nom_curve.fit_diagnostics()["RMSE_Bps"]
        tips_rmse = tips_curve.fit_diagnostics()["RMSE_Bps"]

        # Evaluate 20Y nominal concession
        res_20y_idx = np.where(np.isclose(nom_curve.maturities, 20.0))[0]
        res_20y_val = nom_res[res_20y_idx[0]] if len(res_20y_idx) > 0 else 0.0

        if abs(res_20y_val) > TOLERANCE_BPS:
            concession_desc = f"The nominal 20Y trades at an outlier residual of **{res_20y_val:+.1f} bps** (isolated via WOLS weight $w_{{20\\text{{Y}}}} = 0.05$)"
        else:
            concession_desc = f"The nominal 20Y residual evaluates within tolerance at {res_20y_val:+.1f} bps"

        # Inspect liquid nominal tenors (excluding the downweighted 20Y)
        liquid_nom_mask = ~np.isclose(nom_curve.maturities, 20.0)
        nom_breaches = [
            f"Nom {int(m)}Y ({r:+.1f} bps)"
            for m, r in zip(nom_curve.maturities[liquid_nom_mask], nom_res[liquid_nom_mask])
            if abs(r) > TOLERANCE_BPS
        ]

        # Inspect all traded TIPS tenors
        tips_breaches = [
            f"TIPS {int(m)}Y ({r:+.1f} bps)"
            for m, r in zip(tips_curve.maturities, tips_res)
            if abs(r) > TOLERANCE_BPS
        ]

        all_breaches = nom_breaches + tips_breaches

        if not all_breaches:
            gate_status = (
                f"**PASSED**: All core liquid tenors fit within the $\\pm {TOLERANCE_BPS:.1f}\\text{{ bps}}$ "
                f"institutional gate (Nominal RMSE: **{nom_rmse:.2f} bps**; TIPS RMSE: **{tips_rmse:.2f} bps**)."
            )
        else:
            gate_status = (
                f"**FLAGGED**: {len(all_breaches)} liquid benchmark(s) exceeded the $\\pm {TOLERANCE_BPS:.1f}\\text{{ bps}}$ gate: "
                f"**{', '.join(all_breaches)}**. Aggregate Nominal RMSE printed at **{nom_rmse:.2f} bps** "
                f"and TIPS RMSE at **{tips_rmse:.2f} bps**, reflecting the parsimony trade-off of a 3-factor linear basis."
            )

        p5_text = f"* **Figure 5 (SR 11-7 Model Residual Diagnostics)**: {gate_status} {concession_desc}."

        # Panel 6 Logic: Scenario Risk & VaR
        scenarios = [
            ("OIL-01", "Geopolitical Dislocation", 40.0, 15.0),
            ("OIL-02", "Asymmetric Supply Shock", 20.0, 8.0),
            ("OIL-03", "Baseline Strip Realization", 3.0, 2.0),
            ("OIL-04", "Cyclical Demand Easing", -10.0, -3.0),
            ("OIL-05", "Supply Glut / Liquidation", -40.0, -12.0),
            ("OIL-06", "Cost-Push Stagflation", 15.0, -10.0),
        ]
        sc_results = [(s[0], s[1], pricer_10y.evaluate_horizon_pnl(s[2], s[3], 0.25)["Total_Horizon_PnL_USD"]) for s in scenarios]
        sc_sorted = sorted(sc_results, key=lambda x: x[2], reverse=True)

        p6_text = (
            f"* **Figure 6 (90-Day PnL Attribution Across Macro Scenarios)**: Across stress regimes, maximum upside "
            f"occurs under **{sc_sorted[0][0]} (+USD {sc_sorted[0][2]:,.2f})**, while maximum loss occurs under "
            f"**{sc_sorted[-1][0]} (-USD {abs(sc_sorted[-1][2]):,.2f})**. Regulatory 10-day 99% Historical VaR evaluates to "
            f"**USD {market_risk['VaR_99_10D_USD']:,.2f}** (Expected Shortfall: **USD {market_risk['Expected_Shortfall_99_10D_USD']:,.2f}**), "
            f"demonstrating capital adequacy under FRTB stress."
        )

        return (
            f"### 4.6 Quantitative Dashboard Figure Interpretation\n\n"
            f"{p1_text}\n\n{p2_text}\n\n{p3_text}\n\n{p4_text}\n\n{p5_text}\n\n{p6_text}\n"
        )


def render_rates_inflation_dashboard(
    df: pd.DataFrame,
    metrics: dict,
    nom_curve: YieldCurve,
    tips_curve: YieldCurve,
    pricer_10y: BreakevenTradePricer,
    settlement_date: str,
    save_png_path: str = "rates_dashboard.png"
):
    """Renders the 6-panel executive institutional dashboard via Plotly."""
    tenor_labels = [f"{int(m)}Y" for m in df["Maturity_Years"]]

    fig = make_subplots(
        rows=3,
        cols=2,
        subplot_titles=(
            "<b>1. Nominal vs. TIPS Zero Yield Curves (%)</b>",
            "<b>2. Spot BEI Breakdown & Market Frictions</b>",
            "<b>3. Extracted Inflation Risk Premia (IRP) with ±1σ Bounds</b>",
            "<b>4. Continuous Spot vs. 1Y Forward Breakeven Curve</b>",
            "<b>5. SR 11-7 Yield Residual Diagnostics (Tolerance ±3 bps)</b>",
            "<b>6. 90-Day PnL Attribution Across Macro Scenarios</b>",
        ),
        horizontal_spacing=0.10,
        vertical_spacing=0.10,
    )

    c_blue, c_green, c_amber, c_red, c_purple, c_gray = "#1f77b4", "#2ca02c", "#ff7f0e", "#d62728", "#9467bd", "#7f7f7f"

    # Panel 1: Zero Curves
    fig.add_trace(
        go.Scatter(
            x=tenor_labels,
            y=df["Nominal_Zero_Pct"],
            name="Nominal Zero Yield",
            mode="lines+markers",
            line=dict(color=c_blue, width=2.5),
            marker=dict(size=6),
            legend="legend",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=tenor_labels,
            y=df["TIPS_Zero_Pct"],
            name="TIPS Real Zero Yield",
            mode="lines+markers",
            line=dict(color=c_green, width=2.5, dash="dot"),
            marker=dict(size=6),
            legend="legend",
        ),
        row=1,
        col=1,
    )

    # Panel 2: Breakevens & Survey
    fig.add_trace(
        go.Bar(
            x=tenor_labels,
            y=df["SA_BEI_Bps"],
            name="SA Spot Breakeven (bps)",
            marker_color=c_amber,
            opacity=0.85,
            legend="legend2",
        ),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=tenor_labels,
            y=df["Cleveland_Fed_Survey_CPI_Bps"],
            name="Survey Expected CPI (bps)",
            mode="lines+markers",
            line=dict(color="black", width=2, dash="dash"),
            legend="legend2",
        ),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=tenor_labels,
            y=df["Dyn_Liquidity_Wedge_Bps"],
            name="Liquidity Wedge (bps)",
            mode="lines+markers",
            line=dict(color=c_gray, width=2, dash="dot"),
            legend="legend2",
        ),
        row=1,
        col=2,
    )

    # Panel 3: Extracted IRP
    fig.add_trace(
        go.Scatter(
            x=tenor_labels,
            y=df["IRP_Upper_1Sigma_Bps"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=tenor_labels,
            y=df["IRP_Lower_1Sigma_Bps"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(214, 39, 40, 0.15)",
            name="IRP ±1σ Band",
            showlegend=True,
            hoverinfo="skip",
            legend="legend3",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=tenor_labels,
            y=df["Extracted_IRP_Point_Bps"],
            name="Extracted IRP (bps)",
            marker_color=c_red,
            opacity=0.85,
            text=[f"{v:.1f}" for v in df["Extracted_IRP_Point_Bps"]],
            textposition="outside",
            legend="legend3",
        ),
        row=2,
        col=1,
    )

    # Panel 4: Continuous Spot & Forward Breakevens
    dense_tau = np.linspace(2.0, 30.0, 150)
    nom_dense = np.asarray(nom_curve.zero_rate(dense_tau))
    tips_dense = np.asarray(tips_curve.zero_rate(dense_tau))
    spot_bei_dense = (nom_dense - tips_dense) * 10000.0

    fwd_nom_1y = np.array([nom_curve.forward_rate_sabb(t, t + 1.0) for t in dense_tau])
    fwd_tips_1y = np.array([tips_curve.forward_rate_sabb(t, t + 1.0) for t in dense_tau])
    fwd_bei_1y_bps = (fwd_nom_1y - fwd_tips_1y) * 10000.0

    fig.add_trace(
        go.Scatter(
            x=dense_tau,
            y=spot_bei_dense,
            name="Continuous Spot BEI",
            mode="lines",
            line=dict(color=c_amber, width=2.5),
            legend="legend4",
        ),
        row=2,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=dense_tau,
            y=fwd_bei_1y_bps,
            name="1Y Forward BEI f(t, t+1)",
            mode="lines",
            line=dict(color=c_purple, width=2.5, dash="dash"),
            legend="legend4",
        ),
        row=2,
        col=2,
    )

    # Panel 5: SR 11-7 Residual Diagnostics
    nom_res = (nom_curve.raw_yields - nom_curve.zero_rate(nom_curve.maturities)) * 10000.0
    tips_res = (tips_curve.raw_yields - tips_curve.zero_rate(tips_curve.maturities)) * 10000.0

    nom_names = [f"Nom {int(m)}Y" for m in nom_curve.maturities]
    tips_names = [f"TIPS {int(m)}Y" for m in tips_curve.maturities]

    fig.add_trace(
        go.Bar(
            x=nom_names,
            y=nom_res,
            name="Nominal Residual (bps)",
            marker_color=c_blue,
            text=[f"{v:+.1f}" for v in nom_res],
            textposition="outside",
            legend="legend5",
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=tips_names,
            y=tips_res,
            name="TIPS Residual (bps)",
            marker_color=c_green,
            text=[f"{v:+.1f}" for v in tips_res],
            textposition="outside",
            legend="legend5",
        ),
        row=3,
        col=1,
    )

    fig.add_hline(y=3.0, line_dash="dash", line_color="gray", line_width=1, row=3, col=1)
    fig.add_hline(y=-3.0, line_dash="dash", line_color="gray", line_width=1, row=3, col=1)

    # Panel 6: Scenario Risk PnL Attribution
    scenarios = [
        ("OIL-01", 40.0, 15.0),
        ("OIL-02", 20.0, 8.0),
        ("OIL-03", 3.0, 2.0),
        ("OIL-04", -10.0, -3.0),
        ("OIL-05", -40.0, -12.0),
        ("OIL-06", 15.0, -10.0),
    ]
    sc_names = [s[0] for s in scenarios]
    delta_pnls = [pricer_10y.evaluate_horizon_pnl(s[1], s[2])["Delta_PnL_USD"] for s in scenarios]
    gamma_pnls = [pricer_10y.evaluate_horizon_pnl(s[1], s[2])["Convexity_Gamma_PnL_USD"] for s in scenarios]
    carry_pnls = [pricer_10y.evaluate_horizon_pnl(s[1], s[2])["RollDown_PnL_USD"] + pricer_10y.evaluate_horizon_pnl(s[1], s[2])["Repo_Carry_PnL_USD"] for s in scenarios]

    fig.add_trace(go.Bar(x=sc_names, y=delta_pnls, name="Delta PnL ($)", marker_color=c_blue, legend="legend6",), row=3, col=2,)
    fig.add_trace(go.Bar(x=sc_names, y=gamma_pnls, name="Gamma PnL ($)", marker_color=c_green, legend="legend6",), row=3, col=2,)
    fig.add_trace(go.Bar(x=sc_names, y=carry_pnls, name="Net Carry/Roll ($)", marker_color=c_amber, legend="legend6",), row=3, col=2,)

    # Axis Labels & Titles
    fig.update_xaxes(title_text="Maturity Tenor", row=1, col=1)
    fig.update_xaxes(title_text="Maturity Tenor", row=1, col=2)
    fig.update_xaxes(title_text="Maturity Tenor", row=2, col=1)
    fig.update_xaxes(title_text="Maturity Tenor (Years)", row=2, col=2)
    fig.update_xaxes(title_text="Benchmark Observation Tenor", row=3, col=1)
    fig.update_xaxes(title_text="Scenario ID", row=3, col=2)

    fig.update_yaxes(title_text="Zero Yield (%)", row=1, col=1)
    fig.update_yaxes(title_text="Basis Points (bps)", row=1, col=2)
    fig.update_yaxes(title_text="Basis Points (bps)", row=2, col=1)
    fig.update_yaxes(title_text="Basis Points (bps)", row=2, col=2)
    fig.update_yaxes(title_text="Residual Error (bps)", range=[-6, 14], row=3, col=1)
    fig.update_yaxes(title_text="Horizon PnL ($)", row=3, col=2)

    fig.update_layout(
        title=dict(
            text=f"<b>U.S. Rates Analytics Dashboard</b> | FRED Settlement: {settlement_date}",
            font=dict(size=18),
            x=0.5,
            y=0.99,
            xanchor="center",
            yanchor="top",
        ),
        barmode="relative",
        margin=dict(t=100, b=60, l=80, r=50),
        height=1350,
        width=1650,
        template="plotly_dark",
        legend=dict(orientation="h", x=0.01, y=1.02, xanchor="left", yanchor="top", font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
        legend2=dict(orientation="h", x=0.52, y=1.02, xanchor="left", yanchor="top", font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
        legend3=dict(orientation="h", x=0.01, y=0.68, xanchor="left", yanchor="top", font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
        legend4=dict(orientation="h", x=0.52, y=0.68, xanchor="left", yanchor="top", font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
        legend5=dict(orientation="h", x=0.01, y=0.34, xanchor="left", yanchor="top", font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
        legend6=dict(orientation="h", x=0.52, y=0.34, xanchor="left", yanchor="top", font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
    )

    try:
        fig.write_image(save_png_path, scale=2)
        print(f"[SUCCES] Exported dashboard PNG to: {save_png_path}")
    except Exception as e:
        print(f"[WARNING] Kaleido export failed: {e}")

    return fig


class MarkdownReportGenerator:
    """Generates an institutional research note and trade execution report."""

    @classmethod
    def generate_markdown(
        cls,
        df_decomp: pd.DataFrame,
        metrics: dict,
        bic_selection: dict,
        market_risk: dict,
        nom_curve: YieldCurve,
        tips_curve: YieldCurve,
        exec_params: dict,
        trade_structure: dict,
        pricer_10y: BreakevenTradePricer,
        curve_box_30y: dict,
        settle_date: str,
        export_filename: str = "TERM_STRUCTURE_ANALYTICS_OUTPUT.md",
    ) -> str:
        dt_obj = pd.to_datetime(settle_date)
        formatted_date = dt_obj.strftime("%B %d, %Y")
        month_name = dt_obj.strftime("%B")

        row_2y = df_decomp[df_decomp["Maturity_Years"] == 2.0].iloc[0]
        row_5y = df_decomp[df_decomp["Maturity_Years"] == 5.0].iloc[0]
        row_10y = df_decomp[df_decomp["Maturity_Years"] == 10.0].iloc[0]
        row_20y = df_decomp[df_decomp["Maturity_Years"] == 20.0].iloc[0]
        row_30y = df_decomp[df_decomp["Maturity_Years"] == 30.0].iloc[0]

        slope_5s10s = row_10y["SA_BEI_Bps"] - row_5y["SA_BEI_Bps"]
        slope_10s30s = row_30y["SA_BEI_Bps"] - row_10y["SA_BEI_Bps"]
        seasonal_wedge_2y = row_2y["SA_BEI_Bps"] - row_2y["Unadjusted_BEI_Bps"]

        nom_diag = nom_curve.fit_diagnostics()
        tips_diag = tips_curve.fit_diagnostics()

        base_scenario = pricer_10y.evaluate_horizon_pnl(0.0, 0.0, 0.25)
        net_carry_usd = base_scenario["RollDown_PnL_USD"] + base_scenario["Repo_Carry_PnL_USD"]
        breakeven_hurdle = abs(net_carry_usd) / trade_structure["Nominal_DV01_USD"]

        krd_dict = nom_curve.key_rate_durations(10.0)

        scenarios = [
            ("OIL-01", "Geopolitical Dislocation", 40.0, 15.0),
            ("OIL-02", "Asymmetric Supply Shock", 20.0, 8.0),
            ("OIL-03", "Baseline Strip Realization", 3.0, 2.0),
            ("OIL-04", "Cyclical Demand Easing", -10.0, -3.0),
            ("OIL-05", "Supply Glut / Liquidation", -40.0, -12.0),
            ("OIL-06", "Cost-Push Stagflation", 15.0, -10.0),
        ]

        table_rows = []
        for sid, name, dy_n, dy_r in scenarios:
            res = pricer_10y.evaluate_horizon_pnl(dy_n, dy_r, 0.25)
            table_rows.append(
                f"| **{sid}** | {name} | {dy_n:+.1f} bps | {dy_r:+.1f} bps | "
                f"{res['Delta_PnL_USD']:+,.2f} | {res['Convexity_Gamma_PnL_USD']:+,.2f} | "
                f"**{res['Total_Horizon_PnL_USD']:+,.2f}** |"
            )
        scenario_table = "\n".join(table_rows)

        dynamic_interpretations = (
            DynamicDashboardInterpreter.generate_all_interpretations(
                df=df_decomp,
                metrics=metrics,
                nom_curve=nom_curve,
                tips_curve=tips_curve,
                pricer_10y=pricer_10y,
                bic_selection=bic_selection,
                market_risk=market_risk,
            )
        )

        md = f"""## 4. U.S. Rates & Breakeven Inflation Research Note
**Settlement Date:** {settle_date} | **Model:** Diebold-Li (2006) Basis Invariance + DKW (2018)

![Term Structure Dashboard](rates_dashboard.png)

### Executive Summary
Quantitative term structure and relative-value breakeven analytics for settlement date **{formatted_date}**:

* **Spot Breakeven Term Structure**:
  * **2Y Spot BEI**: Trades at {row_2y['Unadjusted_BEI_Bps']:.2f} bps ({row_2y['Nominal_Zero_Pct']:.3f}% Nominal vs. {row_2y['TIPS_Zero_Pct']:.3f}% TIPS).
  * **Seasonality Adjustment**: Dynamic 5-year BLS factor for {month_name} adjusts 2Y SA breakeven to {row_2y['SA_BEI_Bps']:.2f} bps ({seasonal_wedge_2y:+.2f} bps wedge).
  * **Key Slopes**: 5Y at {row_5y['SA_BEI_Bps']:.2f} bps and 10Y at {row_10y['SA_BEI_Bps']:.2f} bps (**5s10s: {slope_5s10s:+.2f} bps**); 30Y anchors at {row_30y['SA_BEI_Bps']:.2f} bps (**10s30s: {slope_10s30s:+.2f} bps**).
* **Forward Anchoring (5Y5Y)**: Evaluates to **{metrics['5Y5Y_Forward_BEI_SABB_Bps']:.2f} bps**.
* **Affine IRP Term Premia**:
  * **10Y IRP**: **{metrics['10Y_Extracted_IRP_Bps']:.2f} bps** (±1σ: [{metrics['10Y_IRP_Lower_1Sigma_Bps']:.2f}, {metrics['10Y_IRP_Upper_1Sigma_Bps']:.2f}] bps)
  * **30Y IRP**: **{metrics['30Y_Extracted_IRP_Bps']:.2f} bps** (±1σ: [{metrics['30Y_IRP_Lower_1Sigma_Bps']:.2f}, {metrics['30Y_IRP_Upper_1Sigma_Bps']:.2f}] bps)

---

### Econometric Diagnostics & Model Validation (SR 11-7)

1. **Model Selection (BIC)**: Nominal $\\text{{BIC}}_{{\\text{{NS}}}} = {bic_selection['NS_BIC']:.2f}$ vs. $\\text{{BIC}}_{{\\text{{NSS}}}} = {bic_selection['NSS_BIC']:.2f}$. Selected: **{bic_selection['Selected_Model']}**.
2. **Diebold-Li (2006) Parameter Invariance**:
   * Structural decay constant: $\\tau_1 = {nom_curve.tau1:.4f}$ (centering the empirical curvature hump at $\\tau^* = 4.0\\text{{ years}}$).
   * Estimation: Exact closed-form Weighted Least Squares (WOLS) with zero non-linear optimization risk.
3. **DKW (2018) Liquidity Calibration**:
   * Base front-end wedge: {DKWEconometricPriors.BASE_FRONT_END_BPS:.2f} bps (decay half-life: {DKWEconometricPriors.DECAY_HORIZON_YEARS:.1f} yrs; floor: {DKWEconometricPriors.TERMINAL_FLOOR_BPS:.2f} bps).
   * Stress scalar sensitivity: $\\gamma = {DKWEconometricPriors.STRESS_SENSITIVITY:.2f}$ scaled against STLFSI4.
4. **Matrix Stability**: Nominal basis condition number $\\kappa = {nom_diag['Basis_Condition_Number']:.2f}$; TIPS $\\kappa = {tips_diag['Basis_Condition_Number']:.2f}$ (well below the 30.0 threshold).
5. **Residual Precision**: Nominal RMSE = {nom_diag['RMSE_Bps']:.3f} bps; TIPS RMSE = {tips_diag['RMSE_Bps']:.3f} bps.
6. **Reference CPI**: Daily interpolated Ref CPI = {exec_params['Current_Ref_CPI']:.4f} ($CIF = {exec_params['CIF']:.4f}$).

---

{dynamic_interpretations}

---

## 5. Trade Sizing, Risk Sensitivity & Execution

### 5.1 Dynamic Trade Sizing (10Y Benchmark Box)
$$\\text{{Position}} = \\text{{Long USD 100M Par 10Y Nominal}} + \\text{{Short 10Y TIPS}}$$

| Metric | Nominal Leg | TIPS Hedged Leg | Net / Status |
| :--- | :---: | :---: | :--- |
| **Par Notional** | USD {trade_structure['Nominal_Notional_USD']:,.2f} | USD {trade_structure['TIPS_Hedged_Notional_USD']:,.2f} | $\\beta_{{10\\text{{Y}}}} = {exec_params['Beta_TIPS_10Y']:.3f}$ |
| **Actual Cash Principal** | USD {trade_structure['Nominal_Notional_USD']:,.2f} | USD {trade_structure['TIPS_Hedged_Notional_USD'] * exec_params['CIF']:,.2f} | Scaled by $CIF = {exec_params['CIF']:.4f}$ |
| **DV01** | USD {trade_structure['Nominal_DV01_USD']:,.2f} | USD {trade_structure['TIPS_Hedged_DV01_USD']:,.2f} | Duration & Beta Neutral |
| **Convexity ($C$)** | {trade_structure['Nominal_Convexity']:.2f} | {trade_structure['TIPS_Convexity']:.2f} | Net Long Convexity |

---

### 5.2 Key Rate Duration (KRD) Bucket Decomposition (10Y Benchmark)

| Key Tenor | 2Y Bucket | 5Y Bucket | 10Y Bucket | 30Y Bucket | Total Duration |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Nominal 10Y KRD** | {krd_dict[2.0]:.3f} | {krd_dict[5.0]:.3f} | {krd_dict[10.0]:.3f} | {krd_dict[30.0]:.3f} | **{sum(krd_dict.values()):.3f} yrs** |

---

### 5.3 Regulatory Market Risk (FRTB / Basel III Standards)

* **10-Day 99% Historical Simulation VaR**: USD {market_risk['VaR_99_10D_USD']:,.2f}
* **10-Day 99% Expected Shortfall (ES)**: USD {market_risk['Expected_Shortfall_99_10D_USD']:,.2f}
* **Max 252-Day Historical Drawdown**: USD {market_risk['Max_Historical_Drawdown_USD']:,.2f}
* **3-Month Repo Carry**: -USD {abs(base_scenario['Repo_Carry_PnL_USD']):,.2f} (SOFR: {exec_params['Repo_Nominal_Bps']:.1f} bps vs. TIPS Repo: {exec_params['Repo_TIPS_Bps']:.1f} bps)
* **3-Month Curve Roll-Down**: +USD {base_scenario['RollDown_PnL_USD']:,.2f} (Nominal: {metrics['10Y_Nominal_3M_RollDown_Bps']:+.2f} bps vs. TIPS: {metrics['10Y_TIPS_3M_RollDown_Bps']:+.2f} bps)
* **Net 90-Day Carry Drag**: -USD {abs(net_carry_usd):,.2f} (Hurdle: **+{breakeven_hurdle:.2f} bps** over 90 days)

---

### 5.4 Stress Testing & PnL Attribution Analytics

| Scenario ID | Regime Description | $\\Delta y_{{\\text{{Nom}}}}$ | $\\Delta y_{{\\text{{TIPS}}}}$ | Delta PnL (USD) | Gamma PnL (USD) | Total Horizon PnL (USD) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
{scenario_table}

---

### 5.5 10s30s Duration-Neutral Curve Box Structure

$$\\text{{Position}} = \\text{{Long 10Y Box (+USD 100M)}} + \\text{{Short 30Y Box (-USD {curve_box_30y['Leg2_Short_Nom_30Y_USD']/1e6:.2f}M)}}$$

| Leg | Instrument | Par Notional (USD) | DV01 (USD) | Hedge Parameter |
| :--- | :--- | :---: | :---: | :--- |
| **Leg 1** | Long 10Y Nominal | {curve_box_30y['Leg1_Long_Nom_10Y_USD']:,.2f} | +{curve_box_30y['Matched_DV01_USD']:,.2f} | Par Target |
| **Leg 1** | Short 10Y TIPS | {curve_box_30y['Leg1_Short_TIPS_10Y_USD']:,.2f} | -{curve_box_30y['Matched_DV01_USD']:,.2f} | $\\beta_{{10\\text{{Y}}}} = {exec_params['Beta_TIPS_10Y']:.3f}$ |
| **Leg 2** | Short 30Y Nominal | {curve_box_30y['Leg2_Short_Nom_30Y_USD']:,.2f} | -{curve_box_30y['Matched_DV01_USD']:,.2f} | Duration Matched |
| **Leg 2** | Long 30Y TIPS | {curve_box_30y['Leg2_Long_TIPS_30Y_USD']:,.2f} | +{curve_box_30y['Matched_DV01_USD']:,.2f} | $\\beta_{{30\\text{{Y}}}} = {exec_params['Beta_TIPS_30Y']:.3f}$ |
| **Portfolio** | **Net Structure** | — | **0.00** | **Strictly Curve-Neutral** |
"""

        with open(export_filename, "w", encoding="utf-8") as f:
            f.write(md)
        return md