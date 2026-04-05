#!/usr/bin/env python3
"""
Macro Advisor — Regime Backtest
Tests whether the eight-regime model (Growth × Inflation × Liquidity) has predictive
power for forward asset class returns.

Layer 1: Four-quadrant regime family (Growth × Inflation) → forward 1/3/6M asset returns
Layer 2: Eight-regime model (Growth × Inflation × Liquidity) → forward asset returns
Layer 3: Liquidity value-added analysis (how much does the liquidity axis improve signal?)

Naming convention:
    "[Family] — [Ample/Tight] Liquidity"
    e.g. "Goldilocks — Ample Liquidity", "Stagflation — Tight Liquidity"

Usage:
    python regime_backtest.py --fred-key YOUR_KEY --output-dir ./outputs/backtest/
    python regime_backtest.py --fred-key YOUR_KEY --output-dir ./outputs/backtest/ --years 15
    python regime_backtest.py --fred-key YOUR_KEY --output-dir ./outputs/backtest/ --backfill --history outputs/regime-history.json
"""

import argparse
import json
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from regime_core import (
    build_monthly_df, compute_growth_score, compute_growth_direction,
    compute_inflation_score, compute_inflation_direction,
    compute_liquidity_score, classify_liquidity,
    assign_regime_family, assign_regime_8, apply_confirmation_filter,
)

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# FRED series needed for regime classification + liquidity overlay
FRED_REGIME_SERIES = {
    # Growth axis
    "INDPRO": "Industrial Production Index",
    "UNRATE": "Unemployment Rate",
    "RSAFS": "Retail Sales",
    "PAYEMS": "Nonfarm Payrolls",
    # Inflation axis
    "CPIAUCSL": "CPI All Urban Consumers",
    "CPILFESL": "Core CPI ex Food & Energy",
    # Liquidity overlay
    "M2SL": "M2 Money Stock",
    "NFCI": "Chicago Fed NFCI",
    "WALCL": "Fed Total Assets",
}

# Yahoo tickers for asset return measurement
YAHOO_ASSETS = {
    "^GSPC": "S&P 500",
    "^RUT": "Russell 2000",
    "TLT": "US 20Y+ Treasuries",
    "GC=F": "Gold",
    "CL=F": "Crude Oil WTI",
    "DX-Y.NYB": "US Dollar (DXY)",
    "EEM": "Emerging Markets",
    "HYG": "High Yield Credit",
    "^STOXX50E": "Euro Stoxx 50",
}

FORWARD_WINDOWS = [1, 3, 6]  # months


# ---------------------------------------------------------------------------
# DATA FETCHING
# ---------------------------------------------------------------------------

def fetch_fred_series(api_key, years=10):
    """Fetch all FRED series needed for regime classification."""
    from fredapi import Fred
    fred = Fred(api_key=api_key)

    end = datetime.now()
    # Extra buffer for YoY calculations
    start = end - timedelta(days=years * 365 + 400)

    data = {}
    errors = []
    for series_id, name in FRED_REGIME_SERIES.items():
        try:
            s = fred.get_series(series_id, observation_start=start, observation_end=end)
            if s is not None and len(s.dropna()) > 0:
                data[series_id] = s.dropna()
                print(f"  FRED {series_id}: {len(data[series_id])} obs")
            else:
                errors.append(f"{series_id}: empty")
        except Exception as e:
            errors.append(f"{series_id}: {str(e)[:80]}")

    return data, errors


def fetch_yahoo_assets(years=10):
    """Fetch Yahoo Finance price data for asset return calculation."""
    import yfinance as yf

    end = datetime.now()
    start = end - timedelta(days=years * 365 + 200)

    tickers = list(YAHOO_ASSETS.keys())
    print(f"  Downloading {len(tickers)} tickers from Yahoo Finance...")

    data = {}
    for ticker in tickers:
        try:
            df = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                             end=end.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
            if df is not None and len(df) > 0:
                close = df["Close"]
                if hasattr(close, "columns"):
                    close = close.iloc[:, 0]
                close = close.dropna()
                # Resample to monthly (end of month)
                monthly = close.resample("ME").last().dropna()
                data[ticker] = monthly
                print(f"  Yahoo {ticker}: {len(monthly)} monthly obs")
            else:
                print(f"  Yahoo {ticker}: no data")
        except Exception as e:
            print(f"  Yahoo {ticker}: ERROR {str(e)[:80]}")

    return data


# ---------------------------------------------------------------------------
# REGIME CLASSIFICATION
# ---------------------------------------------------------------------------

def classify_regimes(fred_data):
    """
    Classify each month into one of eight regimes based on growth, inflation,
    and liquidity direction. Uses shared regime_core module.

    Returns DataFrame with columns: growth_direction, inflation_direction, regime,
    regime_family, regime_8, liquidity_binary, plus component scores.
    """
    monthly = build_monthly_df(fred_data)

    # Growth scoring
    monthly["growth_score"], _ = compute_growth_score(monthly)
    monthly["growth_direction"] = compute_growth_direction(monthly["growth_score"])

    # Inflation scoring
    monthly["inflation_score"] = compute_inflation_score(monthly)
    monthly["inflation_direction"] = compute_inflation_direction(monthly["inflation_score"])

    # Raw regime assignment (before confirmation filter)
    monthly["regime_raw"] = assign_regime_family(
        monthly["growth_direction"], monthly["inflation_direction"]
    )

    # Confirmation filter: 2 consecutive months required
    monthly["regime"] = apply_confirmation_filter(monthly["regime_raw"].tolist())

    # Liquidity overlay (relative thresholds via rolling 36-month median)
    liq_score, liq_signals, _ = compute_liquidity_score(monthly)
    if len(liq_signals.columns) > 0:
        monthly["liquidity_score"] = liq_score
        monthly["liquidity_binary"] = classify_liquidity(liq_score)
        monthly["liquidity_condition"] = liq_score.apply(
            lambda x: "strong_loose" if x >= 0.8 else "loose" if x > 0.5
            else "tight" if x > 0.2 else "strong_tight"
        )
        # Preserve per-signal condition columns for backward compatibility
        if "m2" in liq_signals.columns:
            monthly["m2_condition"] = liq_signals["m2"].map(
                {1.0: "above_trend", 0.0: "below_trend"})
        if "nfci" in liq_signals.columns:
            monthly["nfci_condition"] = liq_signals["nfci"].map(
                {1.0: "looser_than_trend", 0.0: "tighter_than_trend"})

    # Eight-regime classification
    monthly["regime_family"] = monthly["regime"]
    if "liquidity_binary" in monthly.columns:
        monthly["regime_8"] = assign_regime_8(
            monthly["regime"], monthly["liquidity_binary"]
        )
    else:
        monthly["regime_8"] = monthly["regime"]

    monthly = monthly.dropna(subset=["regime"])
    return monthly


# ---------------------------------------------------------------------------
# FORWARD RETURN COMPUTATION
# ---------------------------------------------------------------------------

def compute_forward_returns(asset_prices, regime_df, execution_lag=0):
    """
    For each month in regime_df, compute forward 1/3/6M returns for each asset.
    Returns a DataFrame aligned to regime_df index.

    Args:
        execution_lag: months to delay return measurement (0 = concurrent, 1 = honest timing).
            With lag=1 and window=3: measures 3-month returns starting 1 month after classification.
    """
    returns = pd.DataFrame(index=regime_df.index)

    for ticker, name in YAHOO_ASSETS.items():
        if ticker not in asset_prices:
            continue
        prices = asset_prices[ticker]
        safe_name = name.replace(" ", "_").replace("+", "").replace("&", "and")

        for window in FORWARD_WINDOWS:
            col = f"{safe_name}_{window}M"
            fwd = prices.pct_change(window).shift(-(window + execution_lag)) * 100
            aligned = fwd.reindex(regime_df.index, method="nearest", tolerance=pd.Timedelta("5D"))
            returns[col] = aligned

    return returns


# ---------------------------------------------------------------------------
# STATISTICAL ANALYSIS
# ---------------------------------------------------------------------------

def compute_unconditional_benchmarks(returns_df):
    """
    Compute full-sample (unconditional) mean, std, SE for each asset/window column.
    Returns dict: {col: {"mean": float, "std": float, "se": float, "n": int}}
    """
    benchmarks = {}
    for col in returns_df.columns:
        vals = returns_df[col].dropna()
        n = len(vals)
        if n < 2:
            continue
        benchmarks[col] = {
            "mean": round(float(vals.mean()), 4),
            "std": round(float(vals.std()), 4),
            "se": round(float(vals.std() / np.sqrt(n)), 4),
            "n": int(n),
        }
    return benchmarks


def bootstrap_regime_significance(vals, unconditional_mean, n_boot=1000, ci=0.90,
                                  block_length=1, seed=42):
    """
    Bootstrap test: is the regime-conditioned mean significantly different from unconditional?

    Uses block bootstrap for overlapping returns (block_length > 1) to preserve
    autocorrelation structure. Standard i.i.d. bootstrap for 1M returns.

    Returns dict with CI bounds, approximate p-value, and significance flag,
    or None if data is insufficient.
    """
    vals = np.asarray(vals, dtype=float)
    vals = vals[~np.isnan(vals)]

    if len(vals) < 15 or np.std(vals) < 1e-6:
        return None

    rng = np.random.RandomState(seed)
    n = len(vals)
    boot_means = np.empty(n_boot)

    if block_length <= 1:
        # Standard i.i.d. bootstrap
        for i in range(n_boot):
            sample = rng.choice(vals, size=n, replace=True)
            boot_means[i] = sample.mean()
    else:
        # Block bootstrap for overlapping returns
        n_blocks = max(1, int(np.ceil(n / block_length)))
        for i in range(n_boot):
            blocks = []
            for _ in range(n_blocks):
                start = rng.randint(0, max(1, n - block_length + 1))
                blocks.append(vals[start:start + block_length])
            sample = np.concatenate(blocks)[:n]
            boot_means[i] = sample.mean()

    alpha = 1 - ci
    ci_low = float(np.percentile(boot_means, alpha / 2 * 100))
    ci_high = float(np.percentile(boot_means, (1 - alpha / 2) * 100))

    # Approximate two-sided p-value: fraction of bootstrap means on the other
    # side of unconditional_mean relative to the observed mean
    observed_mean = float(vals.mean())
    if observed_mean >= unconditional_mean:
        p_value = float(np.mean(boot_means <= unconditional_mean)) * 2
    else:
        p_value = float(np.mean(boot_means >= unconditional_mean)) * 2
    p_value = min(p_value, 1.0)

    significant = unconditional_mean < ci_low or unconditional_mean > ci_high

    return {
        "ci_low": round(ci_low, 2),
        "ci_high": round(ci_high, 2),
        "p_value_approx": round(p_value, 4),
        "significant": significant,
    }


def benjamini_hochberg(p_values, alpha=0.10):
    """
    Benjamini-Hochberg FDR correction.
    Returns list of booleans: True if significant after correction.
    """
    if not p_values:
        return []
    m = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    significant = [False] * m
    # Find largest k where p_(k) <= (k/m) * alpha
    max_k = -1
    for rank, (orig_idx, pval) in enumerate(indexed, start=1):
        threshold = (rank / m) * alpha
        if pval <= threshold:
            max_k = rank
    # All items with rank <= max_k are significant
    if max_k > 0:
        for rank, (orig_idx, pval) in enumerate(indexed, start=1):
            if rank <= max_k:
                significant[orig_idx] = True
    return significant


def compute_power_analysis(returns_df, regime_df, regime_col="regime"):
    """
    Compute minimum detectable effect (MDE) for each regime x asset x window cell.
    MDE at 80% power, 10% significance (one-sided) = 2.8 * (std / sqrt(n)).
    """
    combined = regime_df.join(returns_df, how="inner")
    regimes = combined[regime_col].unique()
    results = {}

    for regime in regimes:
        mask = combined[regime_col] == regime
        subset = combined[mask]
        regime_power = {}
        for col in returns_df.columns:
            vals = subset[col].dropna()
            n = len(vals)
            if n < 5:
                continue
            std = float(vals.std())
            mde = 2.8 * (std / np.sqrt(n)) if n > 0 else float("inf")
            regime_power[col] = {
                "mde": round(mde, 2),
                "n": int(n),
                "std": round(std, 2),
            }
        if regime_power:
            results[regime] = regime_power

    return results


# ---------------------------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------------------------

def analyze_regime_returns(regime_df, returns_df, unconditional=None):
    """
    Layer 1: Average/median/win-rate of forward returns by regime.
    If unconditional benchmarks provided, adds excess return and bootstrap significance.
    """
    combined = regime_df.join(returns_df, how="inner")
    results = {}
    all_p_values = []  # (regime, col, p_value) for BH correction
    all_p_refs = []    # parallel list of (regime, col) for indexing back

    for regime in ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]:
        mask = combined["regime"] == regime
        subset = combined[mask]
        n_months = int(mask.sum())

        regime_stats = {"n_months": n_months, "assets": {}}

        for col in returns_df.columns:
            vals = subset[col].dropna()
            if len(vals) < 10:
                continue
            cell_mean = float(vals.mean())
            cell_std = float(vals.std())
            cell_n = len(vals)
            cell_se = cell_std / np.sqrt(cell_n) if cell_n > 0 else 0

            cell_stats = {
                "mean": round(cell_mean, 2),
                "median": round(float(vals.median()), 2),
                "std": round(cell_std, 2),
                "win_rate": round(float((vals > 0).mean()) * 100, 1),
                "p25": round(float(vals.quantile(0.25)), 2),
                "p75": round(float(vals.quantile(0.75)), 2),
                "n": int(cell_n),
                "low_n_warning": cell_n < 20,
            }

            if unconditional and col in unconditional:
                uc = unconditional[col]
                excess = cell_mean - uc["mean"]
                excess_vs_se = excess / cell_se if cell_se > 0 else 0
                cell_stats["unconditional_mean"] = uc["mean"]
                cell_stats["excess_return"] = round(excess, 2)
                cell_stats["excess_vs_se"] = round(excess_vs_se, 2)
                cell_stats["signal_flag"] = bool(abs(excess_vs_se) > 1.0)

                # Extract window from column name for block bootstrap
                window = 1
                for w in FORWARD_WINDOWS:
                    if f"_{w}M" in col:
                        window = w
                        break
                boot = bootstrap_regime_significance(
                    vals.values, uc["mean"], block_length=window
                )
                if boot:
                    cell_stats["bootstrap_ci_90"] = [boot["ci_low"], boot["ci_high"]]
                    cell_stats["bootstrap_p"] = boot["p_value_approx"]
                    cell_stats["bootstrap_significant"] = boot["significant"]
                    all_p_values.append(boot["p_value_approx"])
                    all_p_refs.append((regime, col))

            regime_stats["assets"][col] = cell_stats

        results[regime] = regime_stats

    # Apply BH-FDR correction across all tested cells
    if all_p_values:
        bh_flags = benjamini_hochberg(all_p_values, alpha=0.10)
        for (regime, col), bh_sig in zip(all_p_refs, bh_flags):
            if col in results[regime]["assets"]:
                results[regime]["assets"][col]["bh_significant"] = bh_sig

    return results


def analyze_eight_regimes(regime_df, returns_df, unconditional=None):
    """
    Layer 2: Eight-regime model (Growth x Inflation x Liquidity).
    Returns stats keyed by the full 8-regime label.
    If unconditional provided, adds excess return and bootstrap significance with BH-FDR.
    """
    if "regime_8" not in regime_df.columns:
        return None

    combined = regime_df.join(returns_df, how="inner")
    results = {}
    all_p_values = []
    all_p_refs = []

    eight_regimes = [
        "Goldilocks — Ample Liquidity", "Goldilocks — Tight Liquidity",
        "Overheating — Ample Liquidity", "Overheating — Tight Liquidity",
        "Disinflationary Slowdown — Ample Liquidity", "Disinflationary Slowdown — Tight Liquidity",
        "Stagflation — Ample Liquidity", "Stagflation — Tight Liquidity",
    ]

    for regime_8 in eight_regimes:
        mask = combined["regime_8"] == regime_8
        subset = combined[mask]
        n_months = int(mask.sum())

        if n_months < 10:
            results[regime_8] = {"n_months": n_months, "assets": {}, "insufficient_data": True}
            continue

        stats = {"n_months": n_months, "assets": {}}
        for col in returns_df.columns:
            vals = subset[col].dropna()
            if len(vals) < 10:
                continue
            cell_mean = float(vals.mean())
            cell_std = float(vals.std())
            cell_n = len(vals)
            cell_se = cell_std / np.sqrt(cell_n) if cell_n > 0 else 0

            cell_stats = {
                "mean": round(cell_mean, 2),
                "median": round(float(vals.median()), 2),
                "std": round(cell_std, 2),
                "win_rate": round(float((vals > 0).mean()) * 100, 1),
                "p25": round(float(vals.quantile(0.25)), 2),
                "p75": round(float(vals.quantile(0.75)), 2),
                "n": int(cell_n),
                "low_n_warning": cell_n < 20,
            }

            if unconditional and col in unconditional:
                uc = unconditional[col]
                excess = cell_mean - uc["mean"]
                excess_vs_se = excess / cell_se if cell_se > 0 else 0
                cell_stats["unconditional_mean"] = uc["mean"]
                cell_stats["excess_return"] = round(excess, 2)
                cell_stats["excess_vs_se"] = round(excess_vs_se, 2)
                cell_stats["signal_flag"] = bool(abs(excess_vs_se) > 1.0)

                window = 1
                for w in FORWARD_WINDOWS:
                    if f"_{w}M" in col:
                        window = w
                        break
                boot = bootstrap_regime_significance(
                    vals.values, uc["mean"], block_length=window
                )
                if boot:
                    cell_stats["bootstrap_ci_90"] = [boot["ci_low"], boot["ci_high"]]
                    cell_stats["bootstrap_p"] = boot["p_value_approx"]
                    cell_stats["bootstrap_significant"] = boot["significant"]
                    all_p_values.append(boot["p_value_approx"])
                    all_p_refs.append((regime_8, col))

            stats["assets"][col] = cell_stats
        results[regime_8] = stats

    # BH-FDR correction across all 8-regime cells
    if all_p_values:
        bh_flags = benjamini_hochberg(all_p_values, alpha=0.10)
        for (regime_8, col), bh_sig in zip(all_p_refs, bh_flags):
            if col in results[regime_8]["assets"]:
                results[regime_8]["assets"][col]["bh_significant"] = bh_sig

    # Decision rule: if <25% of testable 8-regime cells pass BH, flag underpowered
    n_testable = len(all_p_values)
    n_significant = sum(1 for (r8, c), bh in zip(all_p_refs, benjamini_hochberg(all_p_values, 0.10))
                        if bh) if all_p_values else 0
    if n_testable > 0:
        pct_significant = n_significant / n_testable * 100
        results["_significance_summary"] = {
            "n_testable_cells": n_testable,
            "n_bh_significant": n_significant,
            "pct_significant": round(pct_significant, 1),
            "underpowered_warning": pct_significant < 25,
        }

    return results


def run_out_of_sample_test(regime_df, returns_df, asset_prices, split_date, unconditional):
    """
    Split data at split_date. Measure regime-conditioned returns on both halves.
    Returns dict with in-sample, out-of-sample analysis, and stability comparison.
    """
    split_ts = pd.Timestamp(split_date)
    train_mask = regime_df.index <= split_ts
    test_mask = regime_df.index > split_ts

    train_regime = regime_df[train_mask]
    test_regime = regime_df[test_mask]

    if len(train_regime) < 20 or len(test_regime) < 20:
        return {"error": "Insufficient data for OOS split", "train_n": len(train_regime), "test_n": len(test_regime)}

    # Compute forward returns for each half
    train_returns = returns_df[train_mask]
    test_returns = returns_df[test_mask]

    # Unconditional benchmarks for each half
    train_uc = compute_unconditional_benchmarks(train_returns)
    test_uc = compute_unconditional_benchmarks(test_returns)

    # Analyze each half
    is_results = analyze_regime_returns(train_regime, train_returns, unconditional=train_uc)
    oos_results = analyze_regime_returns(test_regime, test_returns, unconditional=test_uc)

    # Stability comparison: for each regime-asset cell, compare IS vs OOS
    stability = {}
    for regime in ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]:
        is_assets = is_results.get(regime, {}).get("assets", {})
        oos_assets = oos_results.get(regime, {}).get("assets", {})
        regime_stab = {}
        for col in set(list(is_assets.keys()) + list(oos_assets.keys())):
            is_data = is_assets.get(col)
            oos_data = oos_assets.get(col)
            if is_data is None or oos_data is None:
                regime_stab[col] = {"status": "missing_in_half"}
                continue
            is_mean = is_data["mean"]
            oos_mean = oos_data["mean"]
            diff = oos_mean - is_mean
            same_sign = (is_mean > 0 and oos_mean > 0) or (is_mean < 0 and oos_mean < 0) or (is_mean == 0 or oos_mean == 0)
            regime_stab[col] = {
                "is_mean": is_mean,
                "oos_mean": oos_mean,
                "diff": round(diff, 2),
                "same_sign": same_sign,
                "stable": same_sign and abs(diff) < is_data.get("std", 999),
            }
        if regime_stab:
            stability[regime] = regime_stab

    return {
        "split_date": split_date,
        "train_months": len(train_regime),
        "test_months": len(test_regime),
        "in_sample": is_results,
        "out_of_sample": oos_results,
        "stability": stability,
    }


def analyze_liquidity_overlay(regime_df, returns_df):
    """
    Legacy Layer 2 format: Same as Layer 1 but conditioned on liquidity (loose vs tight).
    Kept for backward compatibility with existing reports.
    """
    if "liquidity_binary" not in regime_df.columns:
        return None

    combined = regime_df.join(returns_df, how="inner")
    results = {}

    for regime in ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]:
        for liq in ["loose", "tight"]:
            key = f"{regime} + {liq} liquidity"
            mask = (combined["regime"] == regime) & (combined["liquidity_binary"] == liq)
            subset = combined[mask]
            n_months = int(mask.sum())

            if n_months < 10:
                results[key] = {"n_months": n_months, "assets": {}, "insufficient_data": True}
                continue

            stats = {"n_months": n_months, "assets": {}}
            for col in returns_df.columns:
                vals = subset[col].dropna()
                if len(vals) < 10:
                    continue
                stats["assets"][col] = {
                    "mean": round(float(vals.mean()), 2),
                    "median": round(float(vals.median()), 2),
                    "std": round(float(vals.std()), 2),
                    "win_rate": round(float((vals > 0).mean()) * 100, 1),
                    "p25": round(float(vals.quantile(0.25)), 2),
                    "p75": round(float(vals.quantile(0.75)), 2),
                    "n": int(len(vals)),
                    "low_n_warning": len(vals) < 20,
                }
            results[key] = stats

    return results


def analyze_transitions(regime_df, returns_df):
    """
    Compute returns in the 3 months following a regime change.
    """
    combined = regime_df.join(returns_df, how="inner")
    combined["prior_regime"] = combined["regime"].shift(1)
    combined["is_transition"] = combined["regime"] != combined["prior_regime"]

    transitions = combined[combined["is_transition"]].copy()
    if len(transitions) == 0:
        return None

    results = {"total_transitions": int(len(transitions)), "by_transition": {}}

    # Group by from → to
    for _, row in transitions.iterrows():
        key = f"{row['prior_regime']} → {row['regime']}"
        if key not in results["by_transition"]:
            results["by_transition"][key] = {"count": 0, "returns": {}}
        results["by_transition"][key]["count"] += 1

    # Compute average 3M returns for each transition type
    for key in results["by_transition"]:
        fr, to = key.split(" → ")
        mask = (transitions["prior_regime"] == fr) & (transitions["regime"] == to)
        subset = transitions[mask]
        for col in returns_df.columns:
            if "_3M" in col:
                vals = subset[col].dropna()
                if len(vals) >= 2:
                    results["by_transition"][key]["returns"][col] = {
                        "mean": round(float(vals.mean()), 2),
                        "n": int(len(vals)),
                    }

    return results


def compute_regime_timeline(regime_df):
    """Build a timeline of regime periods for visualization."""
    timeline = []
    current_regime = None
    start_date = None

    for date, row in regime_df.iterrows():
        if row["regime"] != current_regime:
            if current_regime is not None:
                timeline.append({
                    "regime": current_regime,
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": date.strftime("%Y-%m-%d"),
                })
            current_regime = row["regime"]
            start_date = date

    if current_regime is not None:
        timeline.append({
            "regime": current_regime,
            "start": start_date.strftime("%Y-%m-%d"),
            "end": regime_df.index[-1].strftime("%Y-%m-%d"),
        })

    return timeline


def compute_liquidity_value_added(layer1, layer2):
    """
    Compare Layer 1 (regime only) vs Layer 2 (regime + liquidity).
    For each regime, compute how much tighter the return distributions get
    when you condition on liquidity.
    """
    if layer2 is None:
        return None

    value_added = {}
    for regime in ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]:
        base = layer1.get(regime, {}).get("assets", {})
        loose_key = f"{regime} + loose liquidity"
        tight_key = f"{regime} + tight liquidity"
        loose = layer2.get(loose_key, {}).get("assets", {})
        tight = layer2.get(tight_key, {}).get("assets", {})

        regime_va = {}
        for col in base:
            if "_3M" not in col:
                continue
            b = base.get(col, {})
            l = loose.get(col, {})
            t = tight.get(col, {})

            if not b or not l or not t:
                continue

            # Does the spread between loose and tight returns exceed the base std?
            spread = abs(l.get("mean", 0) - t.get("mean", 0))
            base_std = b.get("std", 1)
            regime_va[col] = {
                "base_mean": b.get("mean", 0),
                "loose_mean": l.get("mean", 0),
                "tight_mean": t.get("mean", 0),
                "spread": round(spread, 2),
                "base_std": base_std,
                "information_ratio": round(spread / base_std, 2) if base_std > 0 else 0,
                "liquidity_matters": spread > base_std * 0.5,
            }
        if regime_va:
            value_added[regime] = regime_va

    return value_added


# ---------------------------------------------------------------------------
# HTML REPORT GENERATION
# ---------------------------------------------------------------------------

def generate_html_report(layer1, layer2, transitions, timeline, liquidity_va,
                         regime_df, returns_df, years, layer2_eight=None,
                         unconditional=None, power_analysis=None, oos_results=None,
                         lagged_layer1=None):
    """Generate a self-contained HTML report with tables and charts."""

    regime_colors = {
        "Goldilocks": "#22c55e",
        "Overheating": "#f97316",
        "Disinflationary Slowdown": "#3b82f6",
        "Stagflation": "#ef4444",
    }

    # Prepare data for charts
    regime_counts = regime_df["regime"].value_counts().to_dict()
    total_months = len(regime_df)

    # Timeline data for Chart.js
    timeline_js = json.dumps(timeline)

    # Regime distribution
    dist_labels = json.dumps(list(regime_counts.keys()))
    dist_values = json.dumps(list(regime_counts.values()))
    dist_colors = json.dumps([regime_colors.get(r, "#888") for r in regime_counts.keys()])

    # Extended color map for 8-regime labels
    eight_regime_colors = {
        "Goldilocks — Ample Liquidity": "#16a34a",
        "Goldilocks — Tight Liquidity": "#86efac",
        "Overheating — Ample Liquidity": "#ea580c",
        "Overheating — Tight Liquidity": "#fdba74",
        "Disinflationary Slowdown — Ample Liquidity": "#2563eb",
        "Disinflationary Slowdown — Tight Liquidity": "#93c5fd",
        "Stagflation — Ample Liquidity": "#dc2626",
        "Stagflation — Tight Liquidity": "#fca5a5",
    }

    def _regime_family_color(regime_name):
        """Get color for a regime name — works for both 4-regime and 8-regime labels."""
        if regime_name in regime_colors:
            return regime_colors[regime_name]
        if regime_name in eight_regime_colors:
            return eight_regime_colors[regime_name]
        # Fallback: extract family from "Family — Liquidity" pattern
        family = regime_name.split(" — ")[0].split(" + ")[0] if " — " in regime_name or " + " in regime_name else regime_name
        return regime_colors.get(family, "#888")

    # Build return tables (works for both 4-regime and 8-regime data)
    def build_return_table(data, window="3M", regime_names=None):
        assets_seen = set()
        for regime_data in data.values():
            if isinstance(regime_data, dict) and "assets" in regime_data:
                for col in regime_data["assets"]:
                    if f"_{window}" in col:
                        assets_seen.add(col)
        assets = sorted(assets_seen)

        if not assets:
            return "<p>No data available for this window.</p>"

        # Use provided regime names, or auto-detect from data keys
        if regime_names is None:
            regime_names = ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]

        rows = ""
        for regime in regime_names:
            rd = data.get(regime, {})
            n = rd.get("n_months", 0)
            color = _regime_family_color(regime)
            warn = " ⚠" if rd.get("insufficient_data") else (" *" if any(a.get("low_n_warning") for a in rd.get("assets", {}).values()) else "")
            row = f'<tr><td style="border-left: 4px solid {color}; padding-left: 8px; font-weight: 600;">{regime}{warn}</td><td>{n}</td>'
            for asset in assets:
                ad = rd.get("assets", {}).get(asset, {})
                mean = ad.get("mean", "—")
                win = ad.get("win_rate", "—")
                if isinstance(mean, (int, float)):
                    bh_sig = ad.get("bh_significant")
                    boot_sig = ad.get("bootstrap_significant")
                    # Bold border if BH-significant; dim if tested but not significant
                    border = "border: 2px solid #22c55e;" if bh_sig else ("opacity: 0.6;" if boot_sig is not None and not boot_sig else "")
                    bg = "#dcfce7" if mean > 0 else "#fee2e2" if mean < 0 else "#f3f4f6"
                    excess = ad.get("excess_return")
                    excess_str = f" ({excess:+.1f}pp)" if excess is not None else ""
                    sig_marker = " ✓" if bh_sig else ""
                    row += f'<td style="background:{bg}; text-align:center; {border}">{mean:+.1f}%{sig_marker}<br><small style="color:#6b7280;">{win}% win{excess_str}</small></td>'
                else:
                    row += f'<td style="text-align:center;">—</td>'
            row += "</tr>"
            rows += row

        header_labels = [a.replace(f"_{window}", "").replace("_", " ") for a in assets]
        headers = "".join(f'<th style="text-align:center; font-size:0.85em;">{h}</th>' for h in header_labels)

        return f"""
        <table class="data-table">
            <thead><tr><th>Regime</th><th>N</th>{headers}</tr></thead>
            <tbody>{rows}</tbody>
        </table>"""

    layer1_1m = build_return_table(layer1, "1M")
    layer1_3m = build_return_table(layer1, "3M")
    layer1_6m = build_return_table(layer1, "6M")

    # Build Layer 2 tables (liquidity overlay with correct regime names from data)
    layer2_html = ""
    if layer2:
        layer2_regime_names = [k for k in layer2.keys() if not k.startswith("_")]
        layer2_3m = build_return_table(layer2, "3M", regime_names=layer2_regime_names)
        layer2_html = f"""
        <div class="section">
            <h2>Layer 2: Regime × Liquidity (Legacy Overlay) — 3-Month Forward Returns</h2>
            <p class="subtitle">Does conditioning on liquidity (M2 growth + NFCI) improve the signal?</p>
            {layer2_3m}
        </div>"""

    # Build Layer 2 eight-regime tables
    layer2_eight_html = ""
    if layer2_eight:
        eight_regime_names = sorted([k for k in layer2_eight.keys() if not k.startswith("_")])
        l2e_3m = build_return_table(layer2_eight, "3M", regime_names=eight_regime_names)
        layer2_eight_html = f"""
        <div class="section">
            <h2>Layer 2: Full 8-Regime Model — 3-Month Forward Returns</h2>
            <p class="subtitle">Growth × Inflation × Liquidity: each of the 8 regimes independently. (* = low N warning, ⚠ = insufficient data)</p>
            {l2e_3m}
        </div>"""

    # Build liquidity value-added table
    lva_html = ""
    if liquidity_va:
        lva_rows = ""
        for regime, assets in liquidity_va.items():
            color = regime_colors.get(regime, "#888")
            for col, va in assets.items():
                asset_name = col.replace("_3M", "").replace("_", " ")
                matters = "✓" if va["liquidity_matters"] else "✗"
                matters_color = "#22c55e" if va["liquidity_matters"] else "#ef4444"
                lva_rows += f"""<tr>
                    <td style="border-left: 4px solid {color}; padding-left: 8px;">{regime}</td>
                    <td>{asset_name}</td>
                    <td style="text-align:center;">{va['base_mean']:+.1f}%</td>
                    <td style="text-align:center;">{va['loose_mean']:+.1f}%</td>
                    <td style="text-align:center;">{va['tight_mean']:+.1f}%</td>
                    <td style="text-align:center;">{va['spread']:.1f}pp</td>
                    <td style="text-align:center;">{va['information_ratio']:.2f}</td>
                    <td style="text-align:center; color:{matters_color}; font-weight:700;">{matters}</td>
                </tr>"""

        lva_html = f"""
        <div class="section">
            <h2>Liquidity Value-Added Analysis</h2>
            <p class="subtitle">For each regime × asset, does the loose/tight spread exceed half the base standard deviation?
            Information ratio = spread / base_std. Higher = liquidity conditioning adds more signal.</p>
            <table class="data-table">
                <thead><tr>
                    <th>Regime</th><th>Asset (3M)</th><th>Base Mean</th>
                    <th>Loose Mean</th><th>Tight Mean</th><th>Spread</th>
                    <th>Info Ratio</th><th>Matters?</th>
                </tr></thead>
                <tbody>{lva_rows}</tbody>
            </table>
        </div>"""

    # Build transition table
    trans_html = ""
    if transitions:
        trans_rows = ""
        for key, td in sorted(transitions["by_transition"].items(), key=lambda x: -x[1]["count"]):
            n = td["count"]
            returns_cells = ""
            # Show 3M returns for key assets
            for col in sorted(td.get("returns", {}).keys()):
                asset_name = col.replace("_3M", "").replace("_", " ")
                mean = td["returns"][col]["mean"]
                bg = "#dcfce7" if mean > 0 else "#fee2e2" if mean < 0 else "#f3f4f6"
                returns_cells += f'<span style="background:{bg}; padding: 2px 6px; border-radius: 4px; margin: 0 2px; font-size: 0.85em;">{asset_name}: {mean:+.1f}%</span> '

            trans_rows += f"""<tr>
                <td style="font-weight:600;">{key}</td>
                <td style="text-align:center;">{n}</td>
                <td>{returns_cells if returns_cells else '—'}</td>
            </tr>"""

        trans_html = f"""
        <div class="section">
            <h2>Regime Transitions — 3-Month Forward Returns</h2>
            <p class="subtitle">What happens to asset returns in the 3 months after a regime change?
            Total transitions: {transitions['total_transitions']}</p>
            <table class="data-table">
                <thead><tr><th>Transition</th><th>Count</th><th>3M Forward Returns (avg)</th></tr></thead>
                <tbody>{trans_rows}</tbody>
            </table>
        </div>"""

    # Build regime timeline data for chart
    # We need month-by-month data for the stacked area / bar chart
    combined = regime_df.join(returns_df, how="inner")
    chart_dates = [d.strftime("%Y-%m") for d in combined.index]
    chart_regimes = combined["regime"].tolist()
    chart_regime_nums = [
        {"Goldilocks": 0, "Overheating": 1, "Disinflationary Slowdown": 2, "Stagflation": 3}.get(r, -1)
        for r in chart_regimes
    ]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Regime Backtest — Macro Advisor</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: #0f172a; color: #e2e8f0; line-height: 1.6;
        padding: 20px; max-width: 1400px; margin: 0 auto;
    }}
    h1 {{ font-size: 1.8em; margin-bottom: 4px; color: #f8fafc; }}
    h2 {{ font-size: 1.3em; margin-bottom: 8px; color: #f1f5f9; }}
    .subtitle {{ color: #94a3b8; font-size: 0.9em; margin-bottom: 16px; }}
    .header {{ margin-bottom: 32px; padding-bottom: 16px; border-bottom: 1px solid #1e293b; }}
    .header .meta {{ color: #64748b; font-size: 0.9em; }}
    .section {{ background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 24px; }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    .data-table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
    .data-table th {{ background: #334155; padding: 10px 12px; text-align: left; font-weight: 600;
        border-bottom: 2px solid #475569; white-space: nowrap; }}
    .data-table td {{ padding: 10px 12px; border-bottom: 1px solid #334155; }}
    .data-table tbody tr:hover {{ background: #334155; }}
    .stat-card {{ background: #334155; border-radius: 8px; padding: 16px; text-align: center; }}
    .stat-card .number {{ font-size: 2em; font-weight: 700; color: #f8fafc; }}
    .stat-card .label {{ color: #94a3b8; font-size: 0.85em; }}
    .chart-container {{ position: relative; height: 300px; margin: 16px 0; }}
    .verdict {{ padding: 16px; border-radius: 8px; margin-top: 16px; }}
    .verdict.positive {{ background: #052e16; border: 1px solid #22c55e; }}
    .verdict.negative {{ background: #450a0a; border: 1px solid #ef4444; }}
    .verdict.neutral {{ background: #1c1917; border: 1px solid #a8a29e; }}
    .tabs {{ display: flex; gap: 4px; margin-bottom: 16px; }}
    .tab {{ padding: 8px 16px; border-radius: 8px 8px 0 0; cursor: pointer; background: #334155;
        color: #94a3b8; font-size: 0.9em; border: none; }}
    .tab.active {{ background: #1e293b; color: #f8fafc; }}
    .tab-content {{ display: none; }}
    .tab-content.active {{ display: block; }}
    .regime-dot {{
        display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 6px;
        vertical-align: middle;
    }}
    @media (max-width: 900px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>

<div class="header">
    <h1>Regime Backtest Report</h1>
    <p class="meta">Generated {datetime.now().strftime("%Y-%m-%d %H:%M")} · {years} years of data ·
    {total_months} monthly observations · Alpine Macro four-quadrant model</p>
</div>

<!-- Summary cards -->
<div class="grid-2" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 24px;">
    <div class="stat-card">
        <div class="number" style="color: #22c55e;">{regime_counts.get('Goldilocks', 0)}</div>
        <div class="label">Goldilocks months</div>
    </div>
    <div class="stat-card">
        <div class="number" style="color: #f97316;">{regime_counts.get('Overheating', 0)}</div>
        <div class="label">Overheating months</div>
    </div>
    <div class="stat-card">
        <div class="number" style="color: #3b82f6;">{regime_counts.get('Disinflationary Slowdown', 0)}</div>
        <div class="label">Disinfl. Slowdown months</div>
    </div>
    <div class="stat-card">
        <div class="number" style="color: #ef4444;">{regime_counts.get('Stagflation', 0)}</div>
        <div class="label">Stagflation months</div>
    </div>
</div>

<!-- Regime Distribution Chart -->
<div class="section">
    <h2>Regime Distribution</h2>
    <div class="grid-2">
        <div class="chart-container">
            <canvas id="regimePie"></canvas>
        </div>
        <div>
            <h3 style="margin-bottom: 12px; font-size: 1.1em;">Classification Logic</h3>
            <p style="color: #94a3b8; font-size: 0.9em; margin-bottom: 8px;">
                <strong>Growth axis:</strong> 6-month direction of Industrial Production YoY, Unemployment Rate (inverted),
                Retail Sales YoY, Nonfarm Payrolls YoY. Majority vote. 2-month confirmation filter.
            </p>
            <p style="color: #94a3b8; font-size: 0.9em; margin-bottom: 8px;">
                <strong>Inflation axis:</strong> 6-month direction of CPI YoY, with Core CPI as confirmation/tiebreaker.
            </p>
            <p style="color: #94a3b8; font-size: 0.9em; margin-bottom: 8px;">
                <strong>Liquidity overlay:</strong> M2 YoY, NFCI (inverted), Fed balance sheet YoY —
                each compared to its own 36-month rolling median. Majority vote determines loose/tight.
            </p>
            <table class="data-table" style="margin-top: 12px;">
                <thead><tr><th></th><th>Inflation Falling</th><th>Inflation Rising</th></tr></thead>
                <tbody>
                    <tr><td style="font-weight:600;">Growth Rising</td>
                        <td><span class="regime-dot" style="background:#22c55e;"></span>Goldilocks</td>
                        <td><span class="regime-dot" style="background:#f97316;"></span>Overheating</td></tr>
                    <tr><td style="font-weight:600;">Growth Falling</td>
                        <td><span class="regime-dot" style="background:#3b82f6;"></span>Disinfl. Slowdown</td>
                        <td><span class="regime-dot" style="background:#ef4444;"></span>Stagflation</td></tr>
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- Layer 1: Regime Returns -->
<div class="section">
    <h2>Layer 1: Regime → Forward Asset Returns</h2>
    <p class="subtitle">Average forward total return from each regime. Green = positive, red = negative. Win rate = % of months with positive return.</p>

    <div class="tabs">
        <button class="tab active" onclick="showTab('l1', '1m', event)">1-Month</button>
        <button class="tab" onclick="showTab('l1', '3m', event)">3-Month</button>
        <button class="tab" onclick="showTab('l1', '6m', event)">6-Month</button>
    </div>
    <div id="l1-1m" class="tab-content active">{layer1_1m}</div>
    <div id="l1-3m" class="tab-content">{layer1_3m}</div>
    <div id="l1-6m" class="tab-content">{layer1_6m}</div>
</div>

{layer2_html}
{layer2_eight_html}
{lva_html}
{trans_html}

<!-- Statistical Significance Legend -->
<div class="section">
    <h2>Statistical Significance</h2>
    <p class="subtitle">Return cells show excess return vs buy-and-hold in parentheses.
    ✓ = significant after Benjamini-Hochberg FDR correction (alpha=0.10).
    Green border = BH-significant. Dimmed = tested but not significant.
    Bootstrap uses block resampling for 3M/6M windows to handle overlapping returns.</p>
</div>

"""

    # Underpowered warning banner
    if layer2_eight:
        sig_summary = layer2_eight.get("_significance_summary", {})
        if sig_summary.get("underpowered_warning"):
            pct = sig_summary.get("pct_significant", 0)
            html += f"""
<div class="section" style="background: #422006; border: 1px solid #f97316;">
    <h2 style="color: #f97316;">⚠ 8-Regime Significance Warning</h2>
    <p>Only {pct:.0f}% of testable 8-regime cells show statistically significant signal after FDR correction.
    Consider using the 4-regime model for higher-confidence signals. The 8-regime granularity may exceed
    what the available data can support.</p>
</div>
"""

    # Power analysis section
    if power_analysis:
        pa_rows = ""
        for regime in ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]:
            rp = power_analysis.get(regime, {})
            color = regime_colors.get(regime, "#888")
            for col, pa in rp.items():
                if "_3M" in col:
                    asset_name = col.replace("_3M", "").replace("_", " ")
                    pa_rows += f"""<tr>
                        <td style="border-left: 4px solid {color}; padding-left: 8px;">{regime}</td>
                        <td>{asset_name}</td>
                        <td style="text-align:center;">{pa['n']}</td>
                        <td style="text-align:center;">{pa['std']:.1f}%</td>
                        <td style="text-align:center; font-weight:700;">{pa['mde']:.1f}pp</td>
                    </tr>"""
        if pa_rows:
            html += f"""
<div class="section">
    <h2>Power Analysis — Minimum Detectable Effect (3-Month Window)</h2>
    <p class="subtitle">MDE at 80% power, 10% significance. If the actual regime effect is smaller
    than the MDE, this backtest cannot reliably detect it. Larger MDE = less statistical power.</p>
    <table class="data-table">
        <thead><tr><th>Regime</th><th>Asset</th><th>N</th><th>Std</th><th>MDE</th></tr></thead>
        <tbody>{pa_rows}</tbody>
    </table>
</div>
"""

    # OOS results section
    if oos_results and "error" not in oos_results:
        oos_rows = ""
        for regime in ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]:
            stab = oos_results.get("stability", {}).get(regime, {})
            color = regime_colors.get(regime, "#888")
            for col, s in stab.items():
                if "_3M" not in col or s.get("status") == "missing_in_half":
                    continue
                asset_name = col.replace("_3M", "").replace("_", " ")
                stab_color = "#dcfce7" if s.get("stable") else ("#fee2e2" if not s.get("same_sign") else "#fef9c3")
                stab_label = "Stable" if s.get("stable") else ("Sign flip!" if not s.get("same_sign") else "Drift")
                oos_rows += f"""<tr>
                    <td style="border-left: 4px solid {color}; padding-left: 8px;">{regime}</td>
                    <td>{asset_name}</td>
                    <td style="text-align:center;">{s['is_mean']:+.1f}%</td>
                    <td style="text-align:center;">{s['oos_mean']:+.1f}%</td>
                    <td style="text-align:center;">{s['diff']:+.1f}pp</td>
                    <td style="background:{stab_color}; text-align:center; color:#1e293b;">{stab_label}</td>
                </tr>"""
        if oos_rows:
            html += f"""
<div class="section">
    <h2>Out-of-Sample Validation — 3-Month Returns</h2>
    <p class="subtitle">Split at {oos_results['split_date']}. In-sample: {oos_results['train_months']} months.
    Out-of-sample: {oos_results['test_months']} months. Green = stable (same sign, diff < 1 std).
    Red = sign flip. Yellow = same sign but drifted.</p>
    <table class="data-table">
        <thead><tr><th>Regime</th><th>Asset</th><th>In-Sample</th><th>Out-of-Sample</th><th>Diff</th><th>Stability</th></tr></thead>
        <tbody>{oos_rows}</tbody>
    </table>
</div>
"""

    # Lag comparison section
    if lagged_layer1:
        lag_rows = ""
        for regime in ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]:
            l0 = layer1.get(regime, {}).get("assets", {})
            l1 = lagged_layer1.get(regime, {}).get("assets", {})
            color = regime_colors.get(regime, "#888")
            for col in l0:
                if "_3M" not in col:
                    continue
                asset_name = col.replace("_3M", "").replace("_", " ")
                m0 = l0[col].get("mean", 0)
                m1 = l1.get(col, {}).get("mean", 0) if l1 else 0
                cost = m0 - m1
                lag_rows += f"""<tr>
                    <td style="border-left: 4px solid {color}; padding-left: 8px;">{regime}</td>
                    <td>{asset_name}</td>
                    <td style="text-align:center;">{m0:+.1f}%</td>
                    <td style="text-align:center;">{m1:+.1f}%</td>
                    <td style="text-align:center;">{cost:+.1f}pp</td>
                </tr>"""
        if lag_rows:
            html += f"""
<div class="section">
    <h2>Execution Lag Cost — 3-Month Returns</h2>
    <p class="subtitle">Concurrent (lag=0) vs honest timing (lag=1 month). The lag cost is the return
    you lose by waiting one month to act on the regime signal.</p>
    <table class="data-table">
        <thead><tr><th>Regime</th><th>Asset</th><th>Lag=0</th><th>Lag=1</th><th>Cost</th></tr></thead>
        <tbody>{lag_rows}</tbody>
    </table>
</div>
"""

    html += f"""
<!-- Regime Timeline -->
<div class="section">
    <h2>Regime Timeline</h2>
    <p class="subtitle">Historical regime classification month by month.</p>
    <div style="height: 120px; position: relative; overflow-x: auto;">
        <canvas id="timelineChart"></canvas>
    </div>
</div>

<script>
// Regime pie chart
new Chart(document.getElementById('regimePie'), {{
    type: 'doughnut',
    data: {{
        labels: {dist_labels},
        datasets: [{{ data: {dist_values}, backgroundColor: {dist_colors}, borderWidth: 0 }}]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{
            legend: {{ position: 'bottom', labels: {{ color: '#94a3b8', padding: 16 }} }}
        }}
    }}
}});

// Timeline chart
const timelineDates = {json.dumps(chart_dates)};
const timelineRegimes = {json.dumps(chart_regime_nums)};
const regimeNames = ['Goldilocks', 'Overheating', 'Disinfl. Slowdown', 'Stagflation'];
const regimeColors = ['#22c55e', '#f97316', '#3b82f6', '#ef4444'];

new Chart(document.getElementById('timelineChart'), {{
    type: 'bar',
    data: {{
        labels: timelineDates,
        datasets: [{{
            data: timelineRegimes.map(() => 1),
            backgroundColor: timelineRegimes.map(r => regimeColors[r] || '#666'),
            borderWidth: 0,
            barPercentage: 1.0,
            categoryPercentage: 1.0,
        }}]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        indexAxis: 'x',
        scales: {{
            x: {{
                display: true,
                ticks: {{ color: '#64748b', maxTicksLimit: 20, font: {{ size: 10 }} }},
                grid: {{ display: false }}
            }},
            y: {{ display: false, max: 1.2 }}
        }},
        plugins: {{
            legend: {{ display: false }},
            tooltip: {{
                callbacks: {{
                    label: function(ctx) {{
                        return regimeNames[timelineRegimes[ctx.dataIndex]] || 'Unknown';
                    }}
                }}
            }}
        }}
    }}
}});

// Tab switching
function showTab(group, tab, evt) {{
    document.querySelectorAll(`#${{group}}-1m, #${{group}}-3m, #${{group}}-6m`).forEach(el => el.classList.remove('active'));
    document.getElementById(`${{group}}-${{tab}}`).classList.add('active');
    // Update tab buttons
    const section = document.getElementById(`${{group}}-${{tab}}`).closest('.section');
    section.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    if (evt && evt.target) evt.target.classList.add('active');
}}
</script>

</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def backfill_regime_history(regime_df, history_path):
    """
    Backfill regime-history.json with 8-regime labels for all historical months.

    Uses the regime classification from the backtest to add regime_family,
    liquidity_condition, and regime_8 fields to each entry. Existing entries
    are updated; new entries are added for months not yet in the file.

    Args:
        regime_df: DataFrame from classify_regimes() with regime_8, regime_family,
                   liquidity_binary, growth_score, inflation_score, liquidity_score columns.
        history_path: Path to the regime-history.json file.
    """
    history_path = Path(history_path)

    # Load existing history if present
    existing = []
    if history_path.exists():
        with open(history_path) as f:
            existing = json.load(f)

    # Build a lookup of existing entries by week
    existing_by_week = {}
    for entry in existing:
        existing_by_week[entry.get("week", "")] = entry

    # Convert monthly regime data to weekly-like entries
    # The backtest produces monthly data; regime-history.json uses ISO weeks.
    # We'll create one entry per month, using the last ISO week of that month.
    for date, row in regime_df.iterrows():
        iso_year, iso_week, _ = date.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"

        entry = existing_by_week.get(week_key, {})
        entry["week"] = week_key

        # Core regime data
        entry["regime"] = row.get("regime_8", row.get("regime"))
        entry["regime_family"] = row.get("regime_family", row.get("regime"))

        # Liquidity condition
        liq_binary = row.get("liquidity_binary")
        if pd.notna(liq_binary):
            entry["liquidity_condition"] = "ample" if liq_binary == "loose" else "tight"
        else:
            entry["liquidity_condition"] = None

        # Continuous scores
        if "growth_score" in row and pd.notna(row["growth_score"]):
            entry["x"] = round(float(row["growth_score"]), 4)
        if "inflation_score" in row and pd.notna(row["inflation_score"]):
            entry["y"] = round(float(row["inflation_score"]), 4)
        if "liquidity_score" in row and pd.notna(row["liquidity_score"]):
            entry["liquidity_score"] = round(float(row["liquidity_score"]), 4)

        # Confidence (backfilled data gets "Backfilled" confidence)
        if "confidence" not in entry:
            entry["confidence"] = "Backfilled"

        existing_by_week[week_key] = entry

    # Sort by week and write
    all_entries = sorted(existing_by_week.values(), key=lambda e: e.get("week", ""))

    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "w") as f:
        json.dump(all_entries, f, indent=2, default=str)

    return len(all_entries)


def main():
    parser = argparse.ArgumentParser(description="Macro Advisor — Regime Backtest")
    parser.add_argument("--fred-key", required=True, help="FRED API key")
    parser.add_argument("--output-dir", required=True, help="Output directory for results")
    parser.add_argument("--years", type=int, default=10, help="Years of history (default: 10)")
    parser.add_argument("--backfill", action="store_true",
                        help="Backfill regime-history.json with 8-regime labels")
    parser.add_argument("--history", type=str, default=None,
                        help="Path to regime-history.json (required with --backfill)")
    parser.add_argument("--lag", type=int, default=0,
                        help="Execution lag in months (0=concurrent, 1=honest timing)")
    parser.add_argument("--oos", type=str, default=None,
                        help="Out-of-sample split date (e.g. 2019-12-31)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Regime Backtest — {args.years} years ===\n")

    # 1. Fetch data
    print("[1/6] Fetching FRED data...")
    fred_data, fred_errors = fetch_fred_series(args.fred_key, args.years)
    if fred_errors:
        print(f"  FRED errors: {fred_errors}")

    print("\n[2/6] Fetching Yahoo Finance data...")
    yahoo_data = fetch_yahoo_assets(args.years)

    # 2. Classify regimes
    print("\n[3/6] Classifying regimes...")
    regime_df = classify_regimes(fred_data)
    print(f"  Classified {len(regime_df)} months")
    print(f"  Regime distribution:")
    for regime, count in regime_df["regime"].value_counts().items():
        pct = count / len(regime_df) * 100
        print(f"    {regime}: {count} months ({pct:.1f}%)")

    if "liquidity_binary" in regime_df.columns:
        print(f"  Liquidity distribution:")
        for liq, count in regime_df["liquidity_binary"].value_counts().items():
            print(f"    {liq}: {count} months")

    if "regime_8" in regime_df.columns:
        print(f"  Eight-regime distribution:")
        for regime_8, count in regime_df["regime_8"].value_counts().sort_index().items():
            pct = count / len(regime_df) * 100
            sufficient = "✓" if count >= 10 else "⚠ <10"
            print(f"    {regime_8}: {count} months ({pct:.1f}%) {sufficient}")

    # Handle --backfill mode
    if args.backfill:
        if not args.history:
            print("\nERROR: --history path required with --backfill")
            return 1
        print(f"\n[BACKFILL] Writing 8-regime labels to {args.history}...")
        n_entries = backfill_regime_history(regime_df, args.history)
        print(f"  Backfilled {n_entries} entries")
        print("  Done. Exiting (backfill-only mode).")
        return 0

    # 3. Compute forward returns
    print("\n[4/8] Computing forward returns...")
    returns_df = compute_forward_returns(yahoo_data, regime_df, execution_lag=args.lag)
    print(f"  Return columns: {len(returns_df.columns)}")
    if args.lag > 0:
        print(f"  Execution lag: {args.lag} month(s)")

    # 3b. Unconditional benchmarks
    print("\n[5/8] Computing unconditional benchmarks...")
    unconditional = compute_unconditional_benchmarks(returns_df)
    print(f"  Benchmarks for {len(unconditional)} asset/window combos")

    # 4. Analyze (with unconditional benchmarks for significance testing)
    print("\n[6/8] Analyzing (with bootstrap significance + BH-FDR)...")
    layer1 = analyze_regime_returns(regime_df, returns_df, unconditional=unconditional)
    layer2_eight = analyze_eight_regimes(regime_df, returns_df, unconditional=unconditional)
    layer2_legacy = analyze_liquidity_overlay(regime_df, returns_df)
    transitions = analyze_transitions(regime_df, returns_df)
    timeline = compute_regime_timeline(regime_df)
    liquidity_va = compute_liquidity_value_added(layer1, layer2_legacy)

    # 4b. Power analysis
    power_analysis = compute_power_analysis(returns_df, regime_df, regime_col="regime")

    # 4c. Lagged returns comparison (always compute lag=1 for comparison)
    lagged_layer1 = None
    if args.lag == 0:
        lagged_returns = compute_forward_returns(yahoo_data, regime_df, execution_lag=1)
        lagged_uc = compute_unconditional_benchmarks(lagged_returns)
        lagged_layer1 = analyze_regime_returns(regime_df, lagged_returns, unconditional=lagged_uc)

    # 4d. Out-of-sample test
    oos_results = None
    if args.oos:
        print(f"\n[6b/8] Running out-of-sample test (split: {args.oos})...")
        oos_results = run_out_of_sample_test(regime_df, returns_df, yahoo_data, args.oos, unconditional)
        if "error" in oos_results:
            print(f"  OOS error: {oos_results['error']}")
        else:
            print(f"  Train: {oos_results['train_months']}mo, Test: {oos_results['test_months']}mo")

    # 5. Save results
    print("\n[7/8] Generating report...")
    regime_8_dist = regime_df["regime_8"].value_counts().to_dict() if "regime_8" in regime_df.columns else {}
    results = {
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "years": args.years,
        "total_months": len(regime_df),
        "execution_lag": args.lag,
        "regime_distribution": regime_df["regime"].value_counts().to_dict(),
        "regime_8_distribution": regime_8_dist,
        "unconditional_benchmarks": unconditional,
        "layer1_regime_family_returns": layer1,
        "layer2_eight_regime_returns": layer2_eight,
        "layer2_liquidity_overlay_legacy": layer2_legacy,
        "transitions": transitions,
        "timeline": timeline,
        "liquidity_value_added": liquidity_va,
        "power_analysis": power_analysis,
    }
    if oos_results:
        results["out_of_sample"] = oos_results

    json_path = output_dir / "regime-backtest-results.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Results JSON: {json_path}")

    html = generate_html_report(layer1, layer2_legacy, transitions, timeline, liquidity_va,
                                regime_df, returns_df, args.years, layer2_eight=layer2_eight,
                                unconditional=unconditional, power_analysis=power_analysis,
                                oos_results=oos_results, lagged_layer1=lagged_layer1)
    html_path = output_dir / "regime-backtest-report.html"
    with open(html_path, "w") as f:
        f.write(html)
    print(f"  HTML report: {html_path}")

    # Print key findings
    print("\n[8/8] Key findings...")
    print("\n=== Key Findings (Layer 1: Regime Only) ===")
    for regime in ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]:
        rd = layer1.get(regime, {})
        n = rd.get("n_months", 0)
        sp = rd.get("assets", {})
        sp_3m = None
        for col, vals in sp.items():
            if ("SandP" in col or "S_P" in col or "S&P" in col or "500" in col) and "3M" in col:
                sp_3m = vals
                break
        if sp_3m:
            excess = sp_3m.get("excess_return")
            bh = sp_3m.get("bh_significant")
            sig_str = ""
            if excess is not None:
                sig_str = f" ({excess:+.1f}pp vs buy-and-hold"
                if bh is not None:
                    sig_str += ", BH-significant" if bh else ", not significant"
                sig_str += ")"
            print(f"  {regime} ({n}mo): S&P 500 3M avg {sp_3m['mean']:+.1f}%, win rate {sp_3m['win_rate']:.0f}%{sig_str}")
        else:
            for col, vals in sp.items():
                if "3M" in col:
                    print(f"  {regime} ({n}mo): {col} avg {vals['mean']:+.1f}%, win rate {vals['win_rate']:.0f}%")
                    break

    # Power analysis summary
    print("\n=== Power Analysis (4-Regime, S&P 500 3M) ===")
    for regime in ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]:
        rp = power_analysis.get(regime, {})
        for col, pa in rp.items():
            if ("SandP" in col or "S_P" in col or "500" in col) and "3M" in col:
                print(f"  {regime}: MDE = {pa['mde']:.1f}pp (n={pa['n']}, std={pa['std']:.1f}%)")
                break

    # 8-regime significance summary
    if layer2_eight:
        sig_summary = layer2_eight.get("_significance_summary", {})
        if sig_summary:
            print(f"\n=== 8-Regime Significance Summary ===")
            print(f"  Testable cells: {sig_summary['n_testable_cells']}")
            print(f"  BH-significant: {sig_summary['n_bh_significant']} ({sig_summary['pct_significant']:.0f}%)")
            if sig_summary.get("underpowered_warning"):
                print(f"  ⚠ WARNING: <25% of cells significant — 8-regime model may exceed data capacity")

        print("\n=== Key Findings (Layer 2: Eight-Regime Model, 3M) ===")
        for regime_8, rd in sorted(layer2_eight.items()):
            if regime_8.startswith("_"):
                continue
            n = rd.get("n_months", 0)
            if rd.get("insufficient_data"):
                print(f"  {regime_8} ({n}mo): insufficient data")
                continue
            sp_3m = None
            for col, vals in rd.get("assets", {}).items():
                if ("SandP" in col or "S_P" in col or "S&P" in col or "500" in col) and "3M" in col:
                    sp_3m = vals
                    break
            if sp_3m:
                bh = sp_3m.get("bh_significant")
                sig_marker = " ✓" if bh else " ✗" if bh is not None else ""
                print(f"  {regime_8} ({n}mo): S&P 500 3M avg {sp_3m['mean']:+.1f}%, win rate {sp_3m['win_rate']:.0f}%{sig_marker}")

    if liquidity_va:
        print("\n=== Key Findings (Liquidity Value-Added, 3M) ===")
        for regime, assets in liquidity_va.items():
            for col, va in assets.items():
                if "SandP" in col or "500" in col or "S&P" in col:
                    verdict = "YES ✓" if va["liquidity_matters"] else "no ✗"
                    print(f"  {regime}: loose {va['loose_mean']:+.1f}% vs tight {va['tight_mean']:+.1f}% "
                          f"(spread {va['spread']:.1f}pp, IR {va['information_ratio']:.2f}) → {verdict}")

    # OOS summary
    if oos_results and "error" not in oos_results:
        print(f"\n=== Out-of-Sample Validation (split: {args.oos}) ===")
        stab = oos_results.get("stability", {})
        for regime in ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]:
            rs = stab.get(regime, {})
            for col, s in rs.items():
                if "_3M" not in col or s.get("status") == "missing_in_half":
                    continue
                if ("SandP" in col or "S_P" in col or "500" in col):
                    label = "STABLE" if s.get("stable") else ("SIGN FLIP" if not s.get("same_sign") else "DRIFT")
                    print(f"  {regime}: IS {s['is_mean']:+.1f}% → OOS {s['oos_mean']:+.1f}% ({label})")

    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
