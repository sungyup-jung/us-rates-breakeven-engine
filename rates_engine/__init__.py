"""
Institutional U.S. Rates and Breakeven Inflation Term Structure Engine.
"""

from .curves import AdaptiveCurveSelector, YieldCurve
from .data import FREDMarketDataLoader
from .decompositor import CashBondDiscountEngine, InflationDecompositor
from .frictions import DKWEconometricPriors, DynamicMarketFrictions
from .risk import BreakevenTradePricer, CurveSpreadPricer, HistoricalMarketRiskEngine
from .visualizer import (
    DynamicDashboardInterpreter,
    MarkdownReportGenerator,
    render_rates_inflation_dashboard,
)

__all__ = [
    "FREDMarketDataLoader",
    "YieldCurve",
    "AdaptiveCurveSelector",
    "DKWEconometricPriors",
    "DynamicMarketFrictions",
    "CashBondDiscountEngine",
    "InflationDecompositor",
    "BreakevenTradePricer",
    "HistoricalMarketRiskEngine",
    "CurveSpreadPricer",
    "DynamicDashboardInterpreter",
    "MarkdownReportGenerator",
    "render_rates_inflation_dashboard",
]