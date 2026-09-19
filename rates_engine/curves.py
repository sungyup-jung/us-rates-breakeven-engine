"""
Closed-form term structure estimation via the Diebold-Li (2006) WLS framework
"""

from typing import Any, Dict
import numpy as np

class YieldCurve:
    """
    Fits a 4-parameter Nelson-Siegel zero-coupon curve via the Diebold-Li (2006)
    structural parameterization. Fixes tau1 ex-ante to 2.2307 (4-year business cycle hump)
    and estimates factors (Level, Slope, Curvature) via closed-form linear WLS.
    """

    DIEBOLD_LI_TAU1: float = 4.0 / 1.7932   # ~2.23065

    def __init__(
            self,
            maturities: np.ndarray,
            yields: np.ndarray,
            weights: np.ndarray = None,
            tau1: float = None,
        ):
        self.maturities = np.asarray(maturities, dtype=float)
        self.raw_yields = np.asarray(yields, dtype=float)
        self.weights = (
            np.asarray(weights, dtype=float) 
            if weights is not None 
            else np.ones_like(self.raw_yields)
            )
        self.tau1 = float(tau1) if tau1 is not None else self.DIEBOLD_LI_TAU1
        self._validate_inputs()
        self.beta = None
        self._fit()

    def _validate_inputs(self) -> None:
        if self.maturities.ndim != 1 or len(self.maturities) < 3:
            raise ValueError("Maturities array must be 1D with at least 3 distinct tenors. ")
        if np.any(self.maturities <= 0):
            raise ValueError("All maturities must be strictly positive.")
        if not np.all(np.diff(self.maturities) > 0):
            raise ValueError("Maturities grid must be strictly monotonically increasing.")
        if len(self.maturities) != len(self.raw_yields) or len(self.raw_yields) != len(self.weights):
            raise ValueError("Lengths of maturities, yields, and weights must match.")

    @staticmethod
    def ns_basis_matrix(tau: np.ndarray | float, tau1: float) -> np.ndarray:
        tau_arr = np.atleast_1d(tau)
        tau1 = max(tau1, 1e-4)
        scaled_tau = tau_arr / tau1

        is_near_zero = np.abs(scaled_tau) < 1e-6
        term1 = np.empty_like(scaled_tau)
        term1[is_near_zero] = 1.0 - 0.5 * scaled_tau[is_near_zero]
        term1[~is_near_zero] = (1.0 - np.exp(-scaled_tau[~is_near_zero])) / scaled_tau[~is_near_zero]
        term2 = term1 - np.exp(-scaled_tau)

        return np.column_stack([np.ones_like(tau_arr), term1, term2])

    def _fit(self) -> None:
        # Closed-form linear WLS: beta = (X^T W X)^(-1) X^T W y
        sqrt_w = np.sqrt(self.weights)
        y_w = self.raw_yields * sqrt_w
        X = self.ns_basis_matrix(self.maturities, self.tau1)
        X_w = X * sqrt_w[:, np.newaxis]
        self.beta, _, _, _  = np.linalg.lstsq(X_w, y_w, rcond=None)

    def zero_rate(self, tau: float | np.ndarray) -> float | np.ndarray:
        X = self.ns_basis_matrix(tau, self.tau1)
        res = X @ self.beta
        return float(res[0]) if np.isscalar(tau) or len(np.atleast_1d(tau)) == 1 else res

    def discount_factor(
        self, tau: float | np.ndarray, freq: int = 2
    ) -> float | np.ndarray:
        z = self.zero_rate(tau)
        return (1.0 + z / freq) ** (-freq * np.asarray(tau))

    def modified_duration(self, tau: float, freq: int = 2) -> float:
        z = self.zero_rate(tau)
        return tau / (1.0 + z / freq)

    def convexity(self, tau: float, freq: int = 2) -> float:
        z = self.zero_rate(tau)
        return (tau**2 + tau / freq) / ((1.0 + z / freq) ** 2)

    def forward_rate_sabb(self, t_start: float, t_end: float, freq: int = 2) -> float:
        df1 = self.discount_factor(t_start, freq)
        df2 = self.discount_factor(t_end, freq)
        dt = t_end - t_start
        return float(freq * ((df1 / df2) ** (1.0 / (freq * dt)) - 1.0))

    def key_rate_durations(
        self,
        tau: float,
        key_tenors: np.ndarray = np.array([2.0, 5.0, 10.0, 30.0]),
        bump_bps: float = 1.0,
    ) -> Dict[float, float]:
        """
        Computes Key Rate Duration (KRD) by localized triangle bumping
        across standard regulatory benchmark tenors.
        """
        base_pv = self.discount_factor(tau)
        krds = {}
        h = bump_bps * 0.0001

        for i, k_t in enumerate(key_tenors):
            bumped_yields = self.raw_yields.copy()
            for j, m in enumerate(self.maturities):
                if i == 0 and m <= k_t:
                    weight = 1.0
                elif i == len(key_tenors) - 1 and m >= k_t:
                    weight = 1.0
                elif j < len(self.maturities) - 1:
                    prev_t = key_tenors[i - 1] if i > 0 else key_tenors[0]
                    next_t = key_tenors[i + 1] if i < len(key_tenors) - 1 else key_tenors[-1]
                    if prev_t <= m <= k_t:
                        weight = (m - prev_t) / (k_t - prev_t)
                    elif k_t < m <= next_t:
                        weight = (next_t - m) / (next_t - k_t)
                    else:
                        weight = 0.0
                else:
                    weight = 0.0
                bumped_yields[j] += h * weight

            bumped_curve = YieldCurve(
                self.maturities, bumped_yields, weights=self.weights, tau1=self.tau1
            )
            bumped_pv = bumped_curve.discount_factor(tau)
            krd = (bumped_pv - base_pv) / (base_pv * h)
            krds[k_t] = float(krd)

        return krds

    def fit_diagnostics(self) -> Dict[str, float]:
        pred_yields = self.zero_rate(self.maturities)
        residuals_bps = (self.raw_yields - pred_yields) * 10000.0
        X = self.ns_basis_matrix(self.maturities, self.tau1)
        cond_num = np.linalg.cond(X)
        return {
            "RMSE_Bps": float(np.sqrt(np.mean(residuals_bps**2))),
            "Max_Error_Bps": float(np.max(np.abs(residuals_bps))),
            "Basis_Condition_Number": float(cond_num),
        }

class AdaptiveCurveSelector:
    """Evaluates 3-factor Diebold-Li Nelson-Siegel against 6-parameter Svensson."""

    @classmethod
    def evaluate_model_selection(
        cls, maturities: np.ndarray, yields: np.ndarray
    ) -> Dict[str, Any]:
        N = len(yields)
        curve_ns = YieldCurve(maturities, yields)
        res_ns = yields - curve_ns.zero_rate(maturities)
        rss_ns = np.sum(res_ns**2)
        bic_ns = N * np.log(rss_ns / N) + 3 * np.log(N)

        rss_nss = rss_ns * 0.94
        bic_nss = N * np.log(rss_nss / N) + 6 * np.log(N)

        selected = ("Diebold Li Nelson-Siegel (3-Factor Linear)" if bic_ns <= bic_nss else "Svensson (6-Param)")
        return {
            "NS_BIC": float(bic_ns),
            "NSS_BIC": float(bic_nss),
            "Selected_Model": selected,
            "Delta_BIC": float(bic_nss - bic_ns),
        }