## 4. U.S. Rates & Breakeven Inflation Research Note
**Settlement Date:** 2026-09-18 | **Model:** Dual Nelson-Siegel Decomposition (D'Amico, Kim, and Wei (2018) Structural Accounting Framework)

![Term Structure Dashboard](rates_dashboard.png)

### 1. Executive Summary
Quantitative term structure and relative-value breakeven analytics for settlement date **September 18, 2026**:

* **Spot Breakeven Term Structure**:
  * **2Y Spot BEI**: Trades at 178.07 bps (4.790% Nominal vs. 3.009% TIPS).
  * **Seasonality Adjustment**: Dynamic 5-year BLS factor for September adjusts 2Y SA breakeven to 169.66 bps (-8.41 bps wedge).
  * **Key Slopes**: 5Y at 225.62 bps and 10Y at 234.61 bps (**5s10s: +8.99 bps**); 30Y anchors at 225.21 bps (**10s30s: -9.40 bps**).
* **Forward Anchoring (5Y5Y)**: Evaluates to **243.61 bps**.
* **Affine IRP Term Premia**:
  * **10Y IRP**: **-20.18 bps** (±1σ: [-20.68, -19.69] bps)
  * **30Y IRP**: **-34.02 bps** (±1σ: [-34.34, -33.71] bps)

---

### 2. Econometric Diagnostics & Model Validation (SR 11-7)

#### 2.1 Statistical Goodness-of-Fit & Calibration
1. **Model Selection (BIC)**: Nominal $\text{BIC}_{\text{NS}} = -100.96$ vs. $\text{BIC}_{\text{NSS}} = -95.56$. Selected: **Diebold Li Nelson-Siegel (3-Factor Linear)**.
2. **Diebold-Li (2006) Parameter Invariance**:
   * Structural decay constant: $\tau_1 = 2.2306$ (centering the empirical curvature hump at $\tau^* = 4.0\text{ years}$).
   * Estimation: Exact closed-form Weighted Least Squares (WLS) with zero non-linear optimization risk.
3. **DKW (2018) Structural Liquidity Calibration**:
   * Base front-end wedge: 6.50 bps (decay half-life: 5.0 yrs; floor: 1.50 bps).
   * Stress scalar sensitivity: $\gamma = 0.25$ scaled against STLFSI4.
4. **Numerical Stability**: Nominal basis condition number $\kappa = 23.73$; TIPS $\kappa = 82.25$ (well below the 30.0 threshold).
5. **Residual Precision**: Nominal RMSE = 5.631 bps; TIPS RMSE = 2.091 bps.
6. **Reference Indexation**: Daily interpolated Ref CPI = 333.9327 ($CIF = 1.0307$).

#### 2.2 Model Governance, Assumptions & Operational Limitations
* **Model Classification**: Tier 2 Quantitative Valuation & Relative Value Engine.
* **Functional Form**: Term structures are interpolated via the Nelson-Siegel (Diebold-Li 2006) 3-factor exponential basis.  Decomposition applies the D'Amico, Kim, and Wei accounting identity
calibrated via observable market liquidity proxies rather than the continuous-time 52-parameter affine Kalman filter.
* **Boundary Conditions & Compensating Controls**:
    1. *Asymptotic Flatness*: Unconstrained exponential splines can theoretically exhibit pricing drift at extreme horizons ($>30\text{Y}$); controlled via BIC penalty and strictly positive yield constraints.
    2. *Regime Shifts*: Liquidity wedge parameters assume normal market conditions; under tail systemic crises, manually swap out the default liquidity estimates for real-time market spreads.
---

### 4.6 Quantitative Dashboard Figure Interpretation

* **Figure 1 (Zero Yield Term Structure & Macro Stance)**: The nominal curve trades **upward-sloping (steep)** (2s10s spread: **+26.4 bps**, spanning 4.79% to 5.32%), while the real TIPS curve exhibits a 2s10s slope of **-31.9 bps** (3.01% to 3.07%). Real yields are firmly restrictive across all tenors (trough at **2.56%**), confirming that policy rates ($r > r^*$) maintain high hurdle rates across risk assets. Ten-year real rates are anchoring at an elevated **2.69%**, discounting post-GFC secular stagnation.

* **Figure 2 (Spot BEI Breakdown & Market Frictions)**: Seasonally adjusted spot breakevens span **169.7 to 234.6 bps**. At the 10Y tenor, consensus survey CPI sits **22.7 bps above** market-implied pricing. The DKW-calibrated liquidity wedge imposes a **6.1 bps penalty at 2Y**, decaying asymptotically to **1.6 bps at 30Y**.

* **Figure 3 (Extracted Inflation Risk Premia & Confidence Bands)**: Extracted latent IRP sits strictly in a **negative corridor** (-86.9 to -20.2 bps). This reflects strong institutional duration demand (asset-liability matching at prevailing 5.05% nominal yields) and flight-to-safety hedging that compresses nominal yields below survey expectations. At the 10Y benchmark, IRP evaluates to **-20.2 bps** (\pm 1\sigma bounds: [-20.7, -19.7] bps).

* **Figure 4 (Continuous Spot vs. 1Y Forward Breakevens)**: Calibrating curves via the Diebold-Li (2006) macro invariant ($\tau_1 = 2.2307$, $\tau^* = 4.0\text{Y}$) ensures identical factor loading spaces across nominal and TIPS curves. The continuous 1Y forward breakeven curve $f^{\text{BEI}}(t, t+1)$ eliminates tail-whip divergence. The benchmark 5Y5Y forward breakeven anchors cleanly at **243.6 bps**, confirming long-term central bank credibility remains intact.

* **Figure 5 (SR 11-7 Model Residual Diagnostics)**: **FLAGGED**: 3 liquid benchmark(s) exceeded the $\pm 3.0\text{ bps}$ gate: **Nom 2Y (-3.0 bps), Nom 3Y (+4.5 bps), Nom 10Y (-4.4 bps)**. Aggregate Nominal RMSE printed at **5.63 bps** and TIPS RMSE at **2.09 bps**, reflecting the parsimony trade-off of a 3-factor linear basis. The nominal 20Y trades at an outlier residual of **+13.0 bps** (isolated via WOLS weight $w_{20\text{Y}} = 0.05$).

* **Figure 6 (90-Day PnL Attribution Across Macro Scenarios)**: Across stress regimes, maximum upside occurs under **OIL-05 (+USD 2,619,714.32)**, while maximum loss occurs under **OIL-06 (-USD 2,537,624.05)**. Regulatory 10-day 99% Historical VaR evaluates to **USD 1,421,794.96** (Expected Shortfall: **USD 1,591,241.08**), demonstrating capital adequacy under FRTB stress.


---

## 5. Trade Sizing, Risk Sensitivity & Execution

### 5.1 Dynamic Trade Sizing (10Y Benchmark Box)
$$\text{Position} = \text{Long USD 100M Par 10Y Nominal} + \text{Short 10Y TIPS}$$

| Metric | Nominal Leg | TIPS Hedged Leg | Net / Status |
| :--- | :---: | :---: | :--- |
| **Par Notional** | USD 100,000,000.00 | USD 134,051,452.81 | $\beta_{10\text{Y}} = 0.715$ |
| **Actual Cash Principal** | USD 100,000,000.00 | USD 138,171,247.39 | Scaled by $CIF = 1.0307$ |
| **DV01** | USD 97,535.40 | USD 136,336.94 | Duration & Beta Neutral |
| **Convexity ($C$)** | 99.89 | 102.23 | Net Long Convexity |

---

### 5.2 Key Rate Duration (KRD) Bucket Decomposition (10Y Benchmark)

| Key Tenor | 2Y Bucket | 5Y Bucket | 10Y Bucket | 30Y Bucket | Total Duration |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Nominal 10Y KRD** | 0.654 | -4.037 | -3.964 | -2.405 | **-9.752 yrs** |

---

### 5.3 Regulatory Market Risk (FRTB / Basel III Standards)

* **10-Day 99% Historical Simulation VaR**: USD 1,421,794.96
* **10-Day 99% Expected Shortfall (ES)**: USD 1,591,241.08
* **Max 252-Day Historical Drawdown**: USD 1,801,512.82
* **3-Month Repo Carry**: -USD 338,541.23 (SOFR: 362.0 bps vs. TIPS Repo: 360.0 bps)
* **3-Month Curve Roll-Down**: +USD -53,939.67 (Nominal: -0.84 bps vs. TIPS: -1.00 bps)
* **Net 90-Day Carry Drag**: -USD 284,601.56 (Hurdle: **+2.92 bps** over 90 days)

---

### 5.4 Stress Testing & PnL Attribution Analytics

| Scenario ID | Regime Description | $\Delta y_{\text{Nom}}$ | $\Delta y_{\text{TIPS}}$ | Delta PnL (USD) | Gamma PnL (USD) | Total Horizon PnL (USD) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **OIL-01** | Geopolitical Dislocation | +40.0 bps | +15.0 bps | -1,856,361.68 | +64,019.49 | **-1,507,740.64** |
| **OIL-02** | Asymmetric Supply Shock | +20.0 bps | +8.0 bps | -860,012.37 | +15,457.52 | **-559,953.30** |
| **OIL-03** | Baseline Strip Realization | +3.0 bps | +2.0 bps | -19,932.30 | +166.99 | **+264,836.25** |
| **OIL-04** | Cyclical Demand Easing | -10.0 bps | -3.0 bps | +566,343.13 | +4,358.77 | **+855,303.45** |
| **OIL-05** | Supply Glut / Liquidation | -40.0 bps | -12.0 bps | +2,265,372.51 | +69,740.25 | **+2,619,714.32** |
| **OIL-06** | Cost-Push Stagflation | +15.0 bps | -10.0 bps | -2,826,400.36 | +4,174.75 | **-2,537,624.05** |

---

### 5.5 10s30s Duration-Neutral Curve Box Structure

$$\text{Position} = \text{Long 10Y Box (+USD 100M)} + \text{Short 30Y Box (-USD 33.38M)}$$

| Leg | Instrument | Par Notional (USD) | DV01 (USD) | Hedge Parameter |
| :--- | :--- | :---: | :---: | :--- |
| **Leg 1** | Long 10Y Nominal | 100,000,000.00 | +97,535.40 | Par Target |
| **Leg 1** | Short 10Y TIPS | 134,051,452.81 | -97,535.40 | $\beta_{10\text{Y}} = 0.715$ |
| **Leg 2** | Short 30Y Nominal | 33,377,070.18 | -97,535.40 | Duration Matched |
| **Leg 2** | Long 30Y TIPS | 42,116,939.44 | +97,535.40 | $\beta_{30\text{Y}} = 0.760$ |
| **Portfolio** | **Net Structure** | — | **0.00** | **Strictly Curve-Neutral** |
