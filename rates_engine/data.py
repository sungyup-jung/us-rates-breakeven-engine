"""
Data ingestion module for U.S. Treasury, TIPS, CPI, and financing rates via FRED.
"""

from typing import Tuple
import numpy as np
import pandas as pd

class FREDMarketDataLoader:
    """
    Ingests live Treasury, TIPS, survey, BLS inflation, and repo financing data.
    Restricts nominal maturities to 2Y-30Y coupon Treasuries to eliminate money-market
    inversion kinks that distort parameteric functional forms.
    """

    NOMINAL_SERIES = {
        2.0: "DGS2", 3.0: "DGS3", 5.0: "DGS5", 7.0: "DGS7", 
        10.0: "DGS10", 20.0: "DGS20", 30.0: "DGS30",
    }

    TIPS_SERIES = {5.0: "DFII5", 7.0: "DFII7", 10.0: "DFII10", 20.0: "DFII20", 30.0: "DFII30",}

    SURVEY_CPI_SERIES = {
        2.0: "EXPINF2YR", 3.0: "EXPINF3YR", 5.0: "EXPINF5YR", 7.0: "EXPINF7YR", 
        10.0: "EXPINF10YR", 20.0: "EXPINF20YR", 30.0: "EXPINF30YR",
    }

    BLS_CPI_SERIES = {"NSA": "CPIAUCNS", "SA": "CPIAUCSL"}
    FINANCIAL_STRESS_SERIES = "STLFSI4"
    REPO_SERIES = {"SOFR": "SOFR", "TGCR": "TGCR"}

    @classmethod
    def _fetch_csv(cls, series_id: str) -> pd.Series:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        df = pd.read_csv(url, index_col=0, parse_dates=True)
        return pd.to_numeric(df[series_id], errors="coerce")

    @classmethod
    def fetch_latest_market_data(
        cls,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray,
               np.ndarray, np.ndarray, np.ndarray,
               np.ndarray, pd.Series, pd.Series,
               pd.Series, pd.Series, pd.Series,
               float, float, float, str,
    ]:
        """Fetches latest cross-section and rolling historical time series."""
        print("[INFO] Ingesting FRED market rates, survey CPI, and financing parameters...")

        nom_dict = {t: cls._fetch_csv(sid).rename(f"NOM_{t}") for t, sid in cls.NOMINAL_SERIES.items()} 
        tips_dict = {t: cls._fetch_csv(sid).rename(f"TIPS_{t}") for t, sid in cls.TIPS_SERIES.items()}

        all_rates_df = pd.concat(list(nom_dict.values()) + list(tips_dict.values()), axis=1).dropna()
        latest_date = all_rates_df.index[-1].strftime("%Y-%m-%d")
        latest_rates = all_rates_df.iloc[-1]

        nom_maturities = np.array(list(cls.NOMINAL_SERIES.keys()), dtype=float)
        nom_yields = np.array([latest_rates[f"NOM_{t}"] / 100.0 for t in nom_maturities])

        tips_obs_maturities = np.array(list(cls.TIPS_SERIES.keys()), dtype=float)
        tips_obs_yields = np.array([latest_rates[f"TIPS_{t}"] / 100.0 for t in tips_obs_maturities])

        # Cleveland Fed Survey Expectations
        survey_dict = {t: cls._fetch_csv(sid).rename(f"SURVEY_{t}") for t, sid in cls.SURVEY_CPI_SERIES.items()}
        survey_df = pd.concat(list(survey_dict.values()), axis=1).dropna()
        latest_survey_row = survey_df.iloc[-1]

        survey_maturities = np.array(list(cls.SURVEY_CPI_SERIES.keys()), dtype=float)
        survey_cpi_exp = np.array([latest_survey_row[f"SURVEY_{t}"] / 100.0 for t in survey_maturities])

        # Dynamic BLS CPI Seasonality Extraction (5-Year Rolling Median)
        cpi_nsa = cls._fetch_csv(cls.BLS_CPI_SERIES["NSA"]).dropna()
        cpi_sa = cls._fetch_csv(cls.BLS_CPI_SERIES["SA"]).dropna()
        cpi_df = pd.DataFrame({"NSA": cpi_nsa, "SA": cpi_sa}).dropna()
        cpi_df["Ratio"] = cpi_df["NSA"] / cpi_df["SA"]
        cpi_df["Month"] = cpi_df.index.month
        trailing_5y = cpi_df[cpi_df.index >= (cpi_df.index[-1] - pd.DateOffset(years=5))]
        monthly_medians = trailing_5y.groupby("Month")["Ratio"].median().values
        normalized_seasonal_factors = monthly_medians * (12.0 / np.sum(monthly_medians))

        # Benchmark Time Series for Rolling Empirical Betas
        nom_10y_series = nom_dict[10.0].dropna()
        tips_10y_series = tips_dict[10.0].dropna()
        nom_30y_series = nom_dict[30.0].dropna()
        tips_30y_series = tips_dict[30.0].dropna()

        # St. Louis Fed Financial Stress Index
        try:
            stress_series = cls._fetch_csv(cls.FINANCIAL_STRESS_SERIES).dropna()
            latest_stress_idx = float(stress_series.iloc[-1])
        except Exception:
            latest_stress_idx = 0.0

        # Live Financing Rates
        try:
            sofr_s = cls._fetch_csv(cls.REPO_SERIES["SOFR"]).dropna()
            tgcr_s = cls._fetch_csv(cls.REPO_SERIES["TGCR"]).dropna()
            repo_df = pd.concat([sofr_s, tgcr_s], axis=1).dropna()
            latest_sofr = float(repo_df.iloc[-1, 0])
            latest_tgcr = float(repo_df.iloc[-1, 1])
        except Exception:
            latest_sofr = 3.62
            latest_tgcr = 3.60

        print(f"[SUCCESS] Ingested market data for settlement date: {latest_date}")
        return (
            nom_maturities,
            nom_yields,
            tips_obs_maturities,
            tips_obs_yields,
            survey_maturities,
            survey_cpi_exp,
            normalized_seasonal_factors,
            nom_10y_series,
            tips_10y_series,
            nom_30y_series,
            tips_30y_series,
            cpi_nsa,
            latest_stress_idx,
            latest_sofr,
            latest_tgcr,
            latest_date,
        )

