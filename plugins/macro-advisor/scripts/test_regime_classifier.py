#!/usr/bin/env python3
"""
Tests for regime_core.py and regime_classifier.py.

Run: python test_regime_classifier.py
"""

import json
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Import from regime_core
from regime_core import (
    build_monthly_df, compute_growth_score, compute_growth_direction,
    compute_inflation_score, compute_inflation_direction,
    compute_liquidity_score, classify_liquidity,
    assign_regime_family, assign_regime_8, apply_confirmation_filter,
    DIRECTION_WINDOW,
)


def make_monthly_index(n_months=48, end_date=None):
    """Create a monthly DatetimeIndex ending at end_date."""
    if end_date is None:
        end_date = pd.Timestamp("2026-03-31")
    dates = pd.date_range(end=end_date, periods=n_months, freq="ME")
    return dates


def make_series(values, index):
    """Create a pd.Series from values with the given index."""
    return pd.Series(values, index=index, dtype=float)


class TestGrowthScoring(unittest.TestCase):

    def test_all_rising(self):
        """All indicators improving should produce positive growth score."""
        idx = make_monthly_index(24)
        # Create a DataFrame with rising indicators
        monthly = pd.DataFrame(index=idx)
        # INDPRO YoY rising over 6 months: values increase
        monthly["indpro_yoy"] = np.linspace(1.0, 3.0, 24)
        # UNRATE falling (good): values decrease
        monthly["unrate"] = np.linspace(5.0, 3.5, 24)
        # Retail YoY rising
        monthly["retail_yoy"] = np.linspace(2.0, 4.0, 24)
        # Payrolls YoY rising
        monthly["payrolls_yoy"] = np.linspace(1.5, 3.0, 24)

        score, signals = compute_growth_score(monthly)
        last_score = score.iloc[-1]
        self.assertGreater(last_score, 0, "All rising indicators should give positive growth")

    def test_all_falling(self):
        """All indicators deteriorating should produce negative growth score."""
        idx = make_monthly_index(24)
        monthly = pd.DataFrame(index=idx)
        monthly["indpro_yoy"] = np.linspace(3.0, 1.0, 24)
        monthly["unrate"] = np.linspace(3.5, 5.0, 24)
        monthly["retail_yoy"] = np.linspace(4.0, 2.0, 24)
        monthly["payrolls_yoy"] = np.linspace(3.0, 1.5, 24)

        score, _ = compute_growth_score(monthly)
        last_score = score.iloc[-1]
        self.assertLess(last_score, 0, "All falling indicators should give negative growth")

    def test_tied_score_maps_to_falling(self):
        """Documented bias: growth_score == 0.0 maps to 'falling'."""
        idx = make_monthly_index(24)
        monthly = pd.DataFrame(index=idx)
        # Two rising, two falling → score = 0.0
        monthly["indpro_yoy"] = np.linspace(1.0, 3.0, 24)  # rising
        monthly["unrate"] = np.linspace(3.5, 5.0, 24)       # rising (bad) → -1
        monthly["retail_yoy"] = np.linspace(4.0, 2.0, 24)   # falling → -1
        monthly["payrolls_yoy"] = np.linspace(1.5, 3.0, 24) # rising → +1

        score, _ = compute_growth_score(monthly)
        direction = compute_growth_direction(score)
        # With exact tie, direction should be "falling"
        # (This may not produce exact 0 due to linspace, so we test the boundary directly)
        zero_score = pd.Series([0.0])
        zero_dir = compute_growth_direction(zero_score)
        self.assertEqual(zero_dir.iloc[0], "falling", "Score of exactly 0.0 should map to 'falling'")

    def test_nan_indicator_excluded(self):
        """NaN indicators should be excluded from the vote, not counted as 0."""
        idx = make_monthly_index(24)
        monthly = pd.DataFrame(index=idx)
        monthly["indpro_yoy"] = np.linspace(1.0, 3.0, 24)  # rising
        monthly["payrolls_yoy"] = np.linspace(1.5, 3.0, 24) # rising
        # No unrate, no retail → only 2 signals, both positive

        score, signals = compute_growth_score(monthly)
        last_score = score.iloc[-1]
        self.assertGreater(last_score, 0, "With only 2 positive signals, score should be positive")
        self.assertEqual(len(signals.columns), 2, "Should only have 2 signal columns")


class TestInflationScoring(unittest.TestCase):

    def test_rising_inflation(self):
        """CPI and Core both rising over 6 months → positive inflation score."""
        idx = make_monthly_index(24)
        monthly = pd.DataFrame(index=idx)
        monthly["cpi_yoy"] = np.linspace(2.0, 4.0, 24)
        monthly["core_cpi_yoy"] = np.linspace(2.5, 3.8, 24)

        score = compute_inflation_score(monthly)
        last = score.iloc[-1]
        self.assertGreater(last, 0, "Rising CPI/Core should give positive inflation score")

    def test_falling_inflation(self):
        """CPI and Core both falling → negative inflation score."""
        idx = make_monthly_index(24)
        monthly = pd.DataFrame(index=idx)
        monthly["cpi_yoy"] = np.linspace(4.0, 2.0, 24)
        monthly["core_cpi_yoy"] = np.linspace(3.8, 2.5, 24)

        score = compute_inflation_score(monthly)
        last = score.iloc[-1]
        self.assertLess(last, 0, "Falling CPI/Core should give negative inflation score")

    def test_zero_maps_to_falling(self):
        """Documented bias: inflation_score == 0.0 maps to 'falling'."""
        zero_score = pd.Series([0.0])
        direction = compute_inflation_direction(zero_score)
        self.assertEqual(direction.iloc[0], "falling")


class TestLiquidityScoring(unittest.TestCase):

    def test_all_above_median(self):
        """All 3 indicators above 36-month median → score > 0.5 → 'loose'."""
        idx = make_monthly_index(48)
        monthly = pd.DataFrame(index=idx)
        # M2 YoY: first 36 months low, last 12 months high
        monthly["m2_yoy"] = [3.0] * 36 + [8.0] * 12
        # NFCI: first 36 months high, last 12 months low (looser)
        monthly["nfci"] = [0.0] * 36 + [-1.0] * 12
        # Fed assets: first 36 months low, last 12 months high
        monthly["fed_assets_yoy"] = [2.0] * 36 + [10.0] * 12

        score, signals, medians = compute_liquidity_score(monthly)
        last_score = score.iloc[-1]
        condition = classify_liquidity(score).iloc[-1]
        self.assertGreater(last_score, 0.5, "All above median should give score > 0.5")
        self.assertEqual(condition, "loose")

    def test_all_missing(self):
        """No liquidity columns → NaN score."""
        idx = make_monthly_index(24)
        monthly = pd.DataFrame(index=idx)
        monthly["cpi_yoy"] = [2.0] * 24  # non-liquidity column

        score, signals, medians = compute_liquidity_score(monthly)
        self.assertTrue(score.isna().all(), "No liquidity data should give all NaN")

    def test_insufficient_history(self):
        """Less than min_periods months → NaN for early months."""
        idx = make_monthly_index(15)
        monthly = pd.DataFrame(index=idx)
        monthly["m2_yoy"] = [3.0] * 15
        monthly["nfci"] = [-0.5] * 15
        monthly["fed_assets_yoy"] = [5.0] * 15

        score, signals, _ = compute_liquidity_score(monthly)
        # First 11 months should be NaN (min_periods=12)
        self.assertTrue(score.iloc[:11].isna().all(),
                       "First 11 months should be NaN with only 15 months of data")


class TestRegimeAssignment(unittest.TestCase):

    def test_all_four_quadrants(self):
        """Test all 4 regime family assignments."""
        cases = [
            ("rising", "falling", "Goldilocks"),
            ("rising", "rising", "Overheating"),
            ("falling", "falling", "Disinflationary Slowdown"),
            ("falling", "rising", "Stagflation"),
        ]
        for growth, inflation, expected in cases:
            g = pd.Series([growth])
            i = pd.Series([inflation])
            result = assign_regime_family(g, i)
            self.assertEqual(result.iloc[0], expected,
                           f"growth={growth}, inflation={inflation} should be {expected}")

    def test_eight_regime_labels(self):
        """Test 8-regime label construction."""
        fam = pd.Series(["Goldilocks", "Stagflation"])
        liq = pd.Series(["loose", "tight"])
        result = assign_regime_8(fam, liq)
        self.assertEqual(result.iloc[0], "Goldilocks — Ample Liquidity")
        self.assertEqual(result.iloc[1], "Stagflation — Tight Liquidity")

    def test_missing_liquidity_falls_back(self):
        """Missing liquidity should fall back to 4-quadrant label."""
        fam = pd.Series(["Goldilocks"])
        liq = pd.Series([None])
        result = assign_regime_8(fam, liq)
        self.assertEqual(result.iloc[0], "Goldilocks")


class TestConfirmationFilter(unittest.TestCase):

    def test_stable_regime(self):
        """Same regime throughout → all confirmed as that regime."""
        raw = ["Goldilocks"] * 10
        confirmed = apply_confirmation_filter(raw)
        self.assertTrue(all(c == "Goldilocks" for c in confirmed))

    def test_single_month_noise(self):
        """Single-month deviation should not change the confirmed regime."""
        raw = ["Goldilocks"] * 5 + ["Stagflation"] + ["Goldilocks"] * 4
        confirmed = apply_confirmation_filter(raw)
        self.assertTrue(all(c == "Goldilocks" for c in confirmed),
                       "Single-month noise should not change regime")

    def test_two_month_confirmation(self):
        """Two consecutive months of new regime should trigger change."""
        raw = ["Goldilocks"] * 5 + ["Stagflation", "Stagflation"] + ["Stagflation"] * 3
        confirmed = apply_confirmation_filter(raw)
        # First 5: Goldilocks confirmed
        # Month 6: Stagflation pending (count=1)
        # Month 7: Stagflation confirmed (count=2 >= CONFIRMATION_MONTHS)
        self.assertEqual(confirmed[5], "Goldilocks", "First month of new regime still pending")
        self.assertEqual(confirmed[6], "Stagflation", "Second month should confirm")
        self.assertEqual(confirmed[7], "Stagflation", "Should stay confirmed")

    def test_initial_confirmed(self):
        """initial_confirmed parameter should set starting state."""
        raw = ["Goldilocks"] * 3
        confirmed = apply_confirmation_filter(raw, initial_confirmed="Stagflation")
        # Goldilocks needs 2 months to confirm over initial Stagflation
        self.assertEqual(confirmed[0], "Stagflation", "First month pending, still initial")
        self.assertEqual(confirmed[1], "Goldilocks", "Second month confirms")

    def test_alternating_never_confirms(self):
        """Alternating raw regimes should never trigger confirmation."""
        raw = ["Goldilocks", "Stagflation"] * 5
        confirmed = apply_confirmation_filter(raw)
        # Only the first observation gets confirmed
        self.assertTrue(all(c == "Goldilocks" for c in confirmed),
                       "Alternating regimes should never confirm a change")


class TestScoreConsistency(unittest.TestCase):

    def test_growth_direction_matches_score_sign(self):
        """Growth direction should match the sign of the growth score."""
        idx = make_monthly_index(24)
        monthly = pd.DataFrame(index=idx)
        monthly["indpro_yoy"] = np.linspace(1.0, 3.0, 24)
        monthly["payrolls_yoy"] = np.linspace(1.5, 3.0, 24)

        score, _ = compute_growth_score(monthly)
        direction = compute_growth_direction(score)

        for s, d in zip(score.dropna(), direction.dropna()):
            if s > 0:
                self.assertEqual(d, "rising")
            else:
                self.assertEqual(d, "falling")

    def test_inflation_monotonicity(self):
        """Larger CPI increase should produce larger (or equal) inflation score."""
        idx = make_monthly_index(24)

        # Small increase
        monthly1 = pd.DataFrame(index=idx)
        monthly1["cpi_yoy"] = np.linspace(2.0, 2.5, 24)
        monthly1["core_cpi_yoy"] = np.linspace(2.0, 2.5, 24)
        score1 = compute_inflation_score(monthly1).iloc[-1]

        # Larger increase
        monthly2 = pd.DataFrame(index=idx)
        monthly2["cpi_yoy"] = np.linspace(2.0, 4.0, 24)
        monthly2["core_cpi_yoy"] = np.linspace(2.0, 4.0, 24)
        score2 = compute_inflation_score(monthly2).iloc[-1]

        self.assertGreater(score2, score1,
                          "Larger CPI increase should produce larger inflation score")


class TestBuildMonthlyDf(unittest.TestCase):

    def test_basic_construction(self):
        """build_monthly_df should produce correct columns from FRED-style input."""
        idx = pd.date_range("2023-01-01", periods=24, freq="ME")
        fred_data = {
            "INDPRO": pd.Series(np.linspace(100, 110, 24), index=idx),
            "CPIAUCSL": pd.Series(np.linspace(300, 320, 24), index=idx),
        }
        monthly = build_monthly_df(fred_data)
        self.assertIn("indpro_yoy", monthly.columns)
        self.assertIn("cpi_yoy", monthly.columns)
        self.assertGreater(len(monthly), 0)


class TestParseRegimeHistory(unittest.TestCase):

    def test_real_json_schema(self):
        """Verify parse_regime_history reads the actual data_collector JSON structure."""
        from regime_classifier import parse_regime_history
        data_full = {
            "fred": {
                "data": {
                    "INDPRO": {
                        "regime_history": [
                            {"date": "2024-01-31", "value": 100.0},
                            {"date": "2024-02-29", "value": 101.0},
                        ]
                    }
                },
                "errors": []
            }
        }
        result = parse_regime_history(data_full)
        self.assertIn("INDPRO", result)
        self.assertEqual(len(result["INDPRO"]), 2)
        self.assertAlmostEqual(result["INDPRO"].iloc[0], 100.0)
        self.assertAlmostEqual(result["INDPRO"].iloc[1], 101.0)


if __name__ == "__main__":
    unittest.main()
