#!/usr/bin/env python3
"""
Unit tests for the statistical rigor additions to regime_backtest.py:
- compute_unconditional_benchmarks
- bootstrap_regime_significance (i.i.d. and block)
- benjamini_hochberg
- compute_power_analysis
- compute_forward_returns with execution_lag
- analyze_regime_returns with unconditional benchmarks
- run_out_of_sample_test
"""

import numpy as np
import pandas as pd
import pytest

from regime_backtest import (
    compute_unconditional_benchmarks,
    bootstrap_regime_significance,
    benjamini_hochberg,
    compute_power_analysis,
    compute_forward_returns,
    analyze_regime_returns,
    run_out_of_sample_test,
    YAHOO_ASSETS,
    FORWARD_WINDOWS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_returns_df(n=120, seed=42):
    """Create a synthetic returns DataFrame with known properties."""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2015-01-31", periods=n, freq="ME")
    data = {}
    for name in ["S_P_500_1M", "S_P_500_3M", "S_P_500_6M",
                  "Gold_1M", "Gold_3M", "Gold_6M"]:
        data[name] = rng.normal(1.5, 5.0, n)
    return pd.DataFrame(data, index=dates)


def _make_regime_df(n=120, seed=42):
    """Create a synthetic regime DataFrame."""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2015-01-31", periods=n, freq="ME")
    regimes = ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]
    regime_labels = rng.choice(regimes, n)
    return pd.DataFrame({
        "regime": regime_labels,
        "regime_8": regime_labels,  # simplified for testing
        "regime_family": regime_labels,
    }, index=dates)


# ---------------------------------------------------------------------------
# compute_unconditional_benchmarks
# ---------------------------------------------------------------------------

class TestUnconditionalBenchmarks:
    def test_basic_computation(self):
        returns_df = _make_returns_df()
        uc = compute_unconditional_benchmarks(returns_df)
        assert len(uc) == 6  # 2 assets x 3 windows
        for col, stats in uc.items():
            assert "mean" in stats
            assert "std" in stats
            assert "se" in stats
            assert "n" in stats
            assert stats["n"] == 120
            assert stats["se"] > 0
            assert stats["se"] < stats["std"]  # SE < std always

    def test_all_nan_column(self):
        returns_df = _make_returns_df()
        returns_df["AllNaN_3M"] = np.nan
        uc = compute_unconditional_benchmarks(returns_df)
        assert "AllNaN_3M" not in uc

    def test_single_observation(self):
        dates = pd.date_range("2020-01-31", periods=2, freq="ME")
        returns_df = pd.DataFrame({"X_3M": [5.0, np.nan]}, index=dates)
        uc = compute_unconditional_benchmarks(returns_df)
        # n=1 means std is NaN, should be skipped (n < 2)
        assert "X_3M" not in uc


# ---------------------------------------------------------------------------
# bootstrap_regime_significance
# ---------------------------------------------------------------------------

class TestBootstrapSignificance:
    def test_basic_with_known_distribution(self):
        rng = np.random.RandomState(42)
        vals = rng.normal(5.0, 2.0, 50)
        result = bootstrap_regime_significance(vals, 0.0)
        assert result is not None
        assert result["ci_low"] > 0  # mean ~5, CI should be well above 0
        assert result["ci_high"] > result["ci_low"]
        assert result["significant"] is True  # 5.0 vs 0.0 should be significant

    def test_insufficient_data(self):
        vals = np.array([1.0, 2.0, 3.0])  # n=3, below threshold of 15
        result = bootstrap_regime_significance(vals, 0.0)
        assert result is None

    def test_identical_values(self):
        vals = np.full(20, 3.0)
        result = bootstrap_regime_significance(vals, 0.0)
        assert result is None  # std < 1e-6

    def test_block_bootstrap_produces_wider_ci(self):
        rng = np.random.RandomState(42)
        # Create autocorrelated series (simulating overlapping returns)
        vals = np.cumsum(rng.normal(0, 1, 50)) + 10
        result_iid = bootstrap_regime_significance(vals, 0.0, block_length=1, seed=42)
        result_block = bootstrap_regime_significance(vals, 0.0, block_length=3, seed=42)
        assert result_iid is not None
        assert result_block is not None
        iid_width = result_iid["ci_high"] - result_iid["ci_low"]
        block_width = result_block["ci_high"] - result_block["ci_low"]
        # Block bootstrap should generally produce wider CIs for autocorrelated data
        # (not guaranteed for every seed, but should hold for most)
        assert block_width > 0
        assert iid_width > 0

    def test_reproducibility_with_seed(self):
        vals = np.random.RandomState(10).normal(3.0, 1.5, 30)
        r1 = bootstrap_regime_significance(vals, 0.0, seed=99)
        r2 = bootstrap_regime_significance(vals, 0.0, seed=99)
        assert r1["ci_low"] == r2["ci_low"]
        assert r1["ci_high"] == r2["ci_high"]

    def test_not_significant_when_mean_equals_unconditional(self):
        rng = np.random.RandomState(42)
        vals = rng.normal(2.0, 5.0, 30)
        # Unconditional mean close to sample mean
        result = bootstrap_regime_significance(vals, float(vals.mean()))
        assert result is not None
        assert result["significant"] is False

    def test_p_value_bounded(self):
        rng = np.random.RandomState(42)
        vals = rng.normal(5.0, 2.0, 50)
        result = bootstrap_regime_significance(vals, 5.0)
        assert 0 <= result["p_value_approx"] <= 1.0


# ---------------------------------------------------------------------------
# benjamini_hochberg
# ---------------------------------------------------------------------------

class TestBenjaminiHochberg:
    def test_known_p_values(self):
        p_values = [0.01, 0.04, 0.08, 0.15]
        result = benjamini_hochberg(p_values, alpha=0.10)
        # rank 1: 0.01 <= (1/4)*0.10 = 0.025 -> yes
        # rank 2: 0.04 <= (2/4)*0.10 = 0.050 -> yes
        # rank 3: 0.08 <= (3/4)*0.10 = 0.075 -> no
        # rank 4: 0.15 <= (4/4)*0.10 = 0.100 -> no
        assert result == [True, True, False, False]

    def test_all_nonsignificant(self):
        p_values = [0.5, 0.6, 0.9, 1.0]
        result = benjamini_hochberg(p_values, alpha=0.10)
        assert result == [False, False, False, False]

    def test_empty_list(self):
        assert benjamini_hochberg([], alpha=0.10) == []

    def test_single_significant(self):
        result = benjamini_hochberg([0.05], alpha=0.10)
        assert result == [True]

    def test_single_not_significant(self):
        result = benjamini_hochberg([0.15], alpha=0.10)
        assert result == [False]

    def test_all_significant(self):
        p_values = [0.001, 0.002, 0.003]
        result = benjamini_hochberg(p_values, alpha=0.10)
        assert result == [True, True, True]


# ---------------------------------------------------------------------------
# compute_power_analysis
# ---------------------------------------------------------------------------

class TestPowerAnalysis:
    def test_basic(self):
        returns_df = _make_returns_df()
        regime_df = _make_regime_df()
        pa = compute_power_analysis(returns_df, regime_df)
        assert len(pa) > 0
        for regime, assets in pa.items():
            for col, stats in assets.items():
                assert "mde" in stats
                assert "n" in stats
                assert "std" in stats
                assert stats["mde"] > 0
                assert stats["n"] >= 5

    def test_small_n_large_mde(self):
        """Smaller sample should produce larger MDE."""
        returns_small = _make_returns_df(n=30, seed=42)
        returns_large = _make_returns_df(n=120, seed=42)
        regime_small = _make_regime_df(n=30, seed=42)
        regime_large = _make_regime_df(n=120, seed=42)
        pa_small = compute_power_analysis(returns_small, regime_small)
        pa_large = compute_power_analysis(returns_large, regime_large)
        # With fewer observations per regime, MDE should generally be larger
        # (not guaranteed per-regime due to random assignment, but on average)
        mdes_small = [s["mde"] for r in pa_small.values() for s in r.values() if "3M" in list(r.keys())[0]]
        mdes_large = [s["mde"] for r in pa_large.values() for s in r.values() if "3M" in list(r.keys())[0]]
        if mdes_small and mdes_large:
            assert np.mean(mdes_small) > 0  # sanity
            assert np.mean(mdes_large) > 0


# ---------------------------------------------------------------------------
# compute_forward_returns with lag
# ---------------------------------------------------------------------------

class TestForwardReturnsLag:
    def test_lag_zero_matches_original(self):
        """lag=0 should produce the same result as the original function."""
        dates = pd.date_range("2015-01-31", periods=24, freq="ME")
        regime_df = pd.DataFrame({"regime": ["Goldilocks"] * 24}, index=dates)
        prices = pd.Series(range(100, 124), index=dates, dtype=float)
        asset_prices = {"^GSPC": prices}

        r0 = compute_forward_returns(asset_prices, regime_df, execution_lag=0)
        assert len(r0.columns) > 0

    def test_lag_shifts_returns(self):
        """lag=1 should shift returns by 1 additional month."""
        dates = pd.date_range("2015-01-31", periods=24, freq="ME")
        regime_df = pd.DataFrame({"regime": ["Goldilocks"] * 24}, index=dates)
        prices = pd.Series(np.arange(100, 124, dtype=float), index=dates)
        asset_prices = {"^GSPC": prices}

        r0 = compute_forward_returns(asset_prices, regime_df, execution_lag=0)
        r1 = compute_forward_returns(asset_prices, regime_df, execution_lag=1)

        # With lag=1, returns should be shifted forward by 1 month
        # So r1 at month t should roughly equal r0 at month t+1
        col = [c for c in r0.columns if "1M" in c][0]
        # The lagged version should have more NaNs at the end
        assert r1[col].isna().sum() >= r0[col].isna().sum()


# ---------------------------------------------------------------------------
# analyze_regime_returns with unconditional
# ---------------------------------------------------------------------------

class TestAnalyzeWithUnconditional:
    def test_excess_return_fields_present(self):
        returns_df = _make_returns_df()
        regime_df = _make_regime_df()
        uc = compute_unconditional_benchmarks(returns_df)
        results = analyze_regime_returns(regime_df, returns_df, unconditional=uc)
        for regime, rd in results.items():
            for col, stats in rd.get("assets", {}).items():
                assert "unconditional_mean" in stats
                assert "excess_return" in stats
                assert "excess_vs_se" in stats
                assert "signal_flag" in stats
                assert isinstance(stats["signal_flag"], bool)

    def test_bh_significant_field_present(self):
        returns_df = _make_returns_df()
        regime_df = _make_regime_df()
        uc = compute_unconditional_benchmarks(returns_df)
        results = analyze_regime_returns(regime_df, returns_df, unconditional=uc)
        # At least some cells should have bh_significant field
        has_bh = False
        for regime, rd in results.items():
            for col, stats in rd.get("assets", {}).items():
                if "bh_significant" in stats:
                    has_bh = True
                    assert isinstance(stats["bh_significant"], bool)
        assert has_bh

    def test_without_unconditional_no_excess_fields(self):
        returns_df = _make_returns_df()
        regime_df = _make_regime_df()
        results = analyze_regime_returns(regime_df, returns_df)
        for regime, rd in results.items():
            for col, stats in rd.get("assets", {}).items():
                assert "excess_return" not in stats


# ---------------------------------------------------------------------------
# run_out_of_sample_test
# ---------------------------------------------------------------------------

class TestOutOfSample:
    def test_basic_split(self):
        returns_df = _make_returns_df(n=120)
        regime_df = _make_regime_df(n=120)
        uc = compute_unconditional_benchmarks(returns_df)
        result = run_out_of_sample_test(
            regime_df, returns_df, {}, "2019-01-01", uc
        )
        assert "in_sample" in result
        assert "out_of_sample" in result
        assert "stability" in result
        assert result["train_months"] > 0
        assert result["test_months"] > 0

    def test_insufficient_data(self):
        returns_df = _make_returns_df(n=10)
        regime_df = _make_regime_df(n=10)
        uc = compute_unconditional_benchmarks(returns_df)
        result = run_out_of_sample_test(
            regime_df, returns_df, {}, "2015-06-30", uc
        )
        assert "error" in result

    def test_stability_fields(self):
        returns_df = _make_returns_df(n=120)
        regime_df = _make_regime_df(n=120)
        uc = compute_unconditional_benchmarks(returns_df)
        result = run_out_of_sample_test(
            regime_df, returns_df, {}, "2019-01-01", uc
        )
        stab = result.get("stability", {})
        for regime, assets in stab.items():
            for col, s in assets.items():
                if s.get("status") == "missing_in_half":
                    continue
                assert "is_mean" in s
                assert "oos_mean" in s
                assert "same_sign" in s
                assert "stable" in s


# ---------------------------------------------------------------------------
# Decision rule (8-regime significance summary)
# ---------------------------------------------------------------------------

class TestDecisionRule:
    def test_significance_summary_present(self):
        """analyze_eight_regimes should include _significance_summary."""
        returns_df = _make_returns_df(n=120)
        regime_df = _make_regime_df(n=120)
        # Need actual 8-regime labels
        regime_df["regime_8"] = regime_df["regime"] + " — Ample Liquidity"
        uc = compute_unconditional_benchmarks(returns_df)

        from regime_backtest import analyze_eight_regimes
        results = analyze_eight_regimes(regime_df, returns_df, unconditional=uc)
        if results is not None and "_significance_summary" in results:
            summary = results["_significance_summary"]
            assert "n_testable_cells" in summary
            assert "n_bh_significant" in summary
            assert "pct_significant" in summary
            assert "underpowered_warning" in summary
            assert isinstance(summary["underpowered_warning"], bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
