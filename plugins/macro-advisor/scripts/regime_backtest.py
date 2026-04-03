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
    Classify each month into one of four regimes based on growth and inflation direction.

    Growth axis: 3-month direction of Industrial Production YoY, Unemployment Rate (inverted),
                 Retail Sales YoY. Majority vote.
    Inflation axis: 3-month direction of CPI YoY. Core CPI as confirmation.

    Returns DataFrame with columns: growth_direction, inflation_direction, regime, plus components.
    """

    # Build monthly aligned DataFrame
    # For level series (INDPRO, RSAFS, PAYEMS, M2SL, WALCL): compute YoY % change
    # For rate series (UNRATE, CPIAUCSL, CPILFESL): use level or YoY as appropriate

    monthly = pd.DataFrame()

    # Industrial Production - YoY growth
    if "INDPRO" in fred_data:
        s = fred_data["INDPRO"].resample("ME").last().dropna()
        monthly["indpro_yoy"] = s.pct_change(12) * 100

    # Unemployment Rate - level (lower = better growth, so we invert for direction)
    if "UNRATE" in fred_data:
        s = fred_data["UNRATE"].resample("ME").last().dropna()
        monthly["unrate"] = s

    # Retail Sales - YoY growth
    if "RSAFS" in fred_data:
        s = fred_data["RSAFS"].resample("ME").last().dropna()
        monthly["retail_yoy"] = s.pct_change(12) * 100

    # Nonfarm Payrolls - YoY growth
    if "PAYEMS" in fred_data:
        s = fred_data["PAYEMS"].resample("ME").last().dropna()
        monthly["payrolls_yoy"] = s.pct_change(12) * 100

    # CPI - YoY inflation
    if "CPIAUCSL" in fred_data:
        s = fred_data["CPIAUCSL"].resample("ME").last().dropna()
        monthly["cpi_yoy"] = s.pct_change(12) * 100

    # Core CPI - YoY
    if "CPILFESL" in fred_data:
        s = fred_data["CPILFESL"].resample("ME").last().dropna()
        monthly["core_cpi_yoy"] = s.pct_change(12) * 100

    # M2 - YoY growth (for liquidity overlay)
    if "M2SL" in fred_data:
        s = fred_data["M2SL"].resample("ME").last().dropna()
        monthly["m2_yoy"] = s.pct_change(12) * 100

    # NFCI (for liquidity overlay) - weekly, take month-end
    if "NFCI" in fred_data:
        s = fred_data["NFCI"].resample("ME").last().dropna()
        monthly["nfci"] = s

    # Fed Total Assets - YoY growth (for liquidity overlay)
    if "WALCL" in fred_data:
        s = fred_data["WALCL"].resample("ME").last().dropna()
        monthly["fed_assets_yoy"] = s.pct_change(12) * 100

    monthly = monthly.dropna(subset=["cpi_yoy"], how="all")

    # --- Growth direction: 6-month change in each growth indicator ---
    # Using 6-month window (not 3) to identify structural direction, not noise.
    # This matches the Skill 6 regime stability principle: regimes are structural
    # conditions that persist for quarters, not monthly fluctuations.
    DIRECTION_WINDOW = 6

    growth_signals = pd.DataFrame(index=monthly.index)

    # INDPRO YoY: rising = growth improving
    if "indpro_yoy" in monthly.columns:
        growth_signals["indpro"] = monthly["indpro_yoy"].diff(DIRECTION_WINDOW).apply(
            lambda x: 1 if x > 0 else (-1 if x < 0 else 0))

    # UNRATE: falling = growth improving (inverted)
    if "unrate" in monthly.columns:
        growth_signals["unrate"] = monthly["unrate"].diff(DIRECTION_WINDOW).apply(
            lambda x: -1 if x > 0 else (1 if x < 0 else 0))

    # Retail Sales YoY: rising = growth improving
    if "retail_yoy" in monthly.columns:
        growth_signals["retail"] = monthly["retail_yoy"].diff(DIRECTION_WINDOW).apply(
            lambda x: 1 if x > 0 else (-1 if x < 0 else 0))

    # Payrolls YoY: rising = growth improving
    if "payrolls_yoy" in monthly.columns:
        growth_signals["payrolls"] = monthly["payrolls_yoy"].diff(DIRECTION_WINDOW).apply(
            lambda x: 1 if x > 0 else (-1 if x < 0 else 0))

    # Majority vote
    monthly["growth_score"] = growth_signals.mean(axis=1)
    monthly["growth_direction"] = monthly["growth_score"].apply(
        lambda x: "rising" if x > 0 else "falling")

    # --- Inflation direction: 6-month change in CPI YoY ---
    if "cpi_yoy" in monthly.columns:
        cpi_dir_chg = monthly["cpi_yoy"].diff(DIRECTION_WINDOW)
        # Core CPI as confirmation / tiebreaker
        core_dir_chg = monthly["core_cpi_yoy"].diff(DIRECTION_WINDOW) if "core_cpi_yoy" in monthly.columns else cpi_dir_chg

        # Blend: if both agree, strong signal. If they disagree, use headline.
        monthly["inflation_score"] = (cpi_dir_chg.fillna(0) + core_dir_chg.fillna(0)) / 2
        monthly["inflation_direction"] = monthly["inflation_score"].apply(
            lambda x: "rising" if x > 0 else "falling")

    # --- Raw regime assignment (before confirmation filter) ---
    def assign_regime(row):
        g = row.get("growth_direction", None)
        i = row.get("inflation_direction", None)
        if g == "rising" and i == "falling":
            return "Goldilocks"
        elif g == "rising" and i == "rising":
            return "Overheating"
        elif g == "falling" and i == "falling":
            return "Disinflationary Slowdown"
        elif g == "falling" and i == "rising":
            return "Stagflation"
        return None

    monthly["regime_raw"] = monthly.apply(assign_regime, axis=1)

    # --- Confirmation filter: require 2 consecutive months in new regime ---
    # A regime change only registers after 2 months of the new classification.
    # This eliminates single-month noise flips while preserving real transitions.
    CONFIRMATION_MONTHS = 2
    confirmed = []
    current_confirmed = None
    pending_regime = None
    pending_count = 0

    for idx, row in monthly.iterrows():
        raw = row["regime_raw"]
        if current_confirmed is None:
            # First observation — accept it
            current_confirmed = raw
            pending_regime = None
            pending_count = 0
        elif raw == current_confirmed:
            # Still in confirmed regime — reset any pending change
            pending_regime = None
            pending_count = 0
        elif raw == pending_regime:
            # Same new regime as last month — increment counter
            pending_count += 1
            if pending_count >= CONFIRMATION_MONTHS:
                current_confirmed = raw
                pending_regime = None
                pending_count = 0
        else:
            # Different regime than both confirmed and pending — start new pending
            pending_regime = raw
            pending_count = 1

        confirmed.append(current_confirmed)

    monthly["regime"] = confirmed
    # NOTE: The confirmed regime is the authoritative classification.
    # The 2-month confirmation filter prevents single-month noise flips.
    # Do NOT overwrite with raw regime assignment.

    # --- Liquidity overlay ---
    # Use RELATIVE thresholds (rolling 36-month median) not absolute levels.
    # Reason: NFCI has been negative for almost the entire post-GFC era,
    # and M2 was >2% for most of the sample. Absolute thresholds produce
    # a 95%+ "loose" classification that is useless for conditioning.
    # Relative thresholds ask: "is liquidity looser or tighter than recent history?"

    liquidity_scores = pd.DataFrame(index=monthly.index)

    # M2 YoY growth: above rolling median = loosening, below = tightening
    if "m2_yoy" in monthly.columns:
        m2_median = monthly["m2_yoy"].rolling(36, min_periods=12).median()
        monthly["m2_condition"] = (monthly["m2_yoy"] > m2_median).map(
            {True: "above_trend", False: "below_trend"})
        liquidity_scores["m2"] = (monthly["m2_yoy"] > m2_median).astype(int)

    # NFCI: below rolling median = looser than usual, above = tighter
    # (NFCI is inverted: more negative = looser)
    if "nfci" in monthly.columns:
        nfci_median = monthly["nfci"].rolling(36, min_periods=12).median()
        monthly["nfci_condition"] = (monthly["nfci"] < nfci_median).map(
            {True: "looser_than_trend", False: "tighter_than_trend"})
        liquidity_scores["nfci"] = (monthly["nfci"] < nfci_median).astype(int)

    # Fed balance sheet: above rolling median growth = loosening
    if "fed_assets_yoy" in monthly.columns:
        fed_median = monthly["fed_assets_yoy"].rolling(36, min_periods=12).median()
        liquidity_scores["fed_bs"] = (monthly["fed_assets_yoy"] > fed_median).astype(int)

    # Combined: majority vote across available signals
    if len(liquidity_scores.columns) > 0:
        monthly["liquidity_score"] = liquidity_scores.mean(axis=1)
        monthly["liquidity_binary"] = monthly["liquidity_score"].apply(
            lambda x: "loose" if x > 0.5 else "tight")
        monthly["liquidity_condition"] = monthly["liquidity_score"].apply(
            lambda x: "strong_loose" if x >= 0.8 else "loose" if x > 0.5
            else "tight" if x > 0.2 else "strong_tight")

    # --- Eight-regime classification ---
    # Combine regime family (4-quadrant) with liquidity condition (ample/tight)
    # to create the full 8-regime label.
    # regime_family preserves the 4-quadrant label for backward compatibility
    # (kill switches, streak counting, template lookup all use regime_family).
    monthly["regime_family"] = monthly["regime"]

    if "liquidity_binary" in monthly.columns:
        monthly["regime_8"] = monthly.apply(
            lambda row: f"{row['regime']} — {'Ample' if row['liquidity_binary'] == 'loose' else 'Tight'} Liquidity"
            if pd.notna(row.get("regime")) and pd.notna(row.get("liquidity_binary"))
            else row.get("regime"),
            axis=1
        )
    else:
        monthly["regime_8"] = monthly["regime"]

    # Drop rows where regime couldn't be assigned
    monthly = monthly.dropna(subset=["regime"])

    return monthly


# ---------------------------------------------------------------------------
# FORWARD RETURN COMPUTATION
# ---------------------------------------------------------------------------

def compute_forward_returns(asset_prices, regime_df):
    """
    For each month in regime_df, compute forward 1/3/6M returns for each asset.
    Returns a DataFrame aligned to regime_df index.
    """
    returns = pd.DataFrame(index=regime_df.index)

    for ticker, name in YAHOO_ASSETS.items():
        if ticker not in asset_prices:
            continue
        prices = asset_prices[ticker]
        safe_name = name.replace(" ", "_").replace("+", "").replace("&", "and")

        for window in FORWARD_WINDOWS:
            col = f"{safe_name}_{window}M"
            fwd = prices.pct_change(window).shift(-window) * 100
            # Align to regime_df index
            aligned = fwd.reindex(regime_df.index, method="nearest", tolerance=pd.Timedelta("5D"))
            returns[col] = aligned

    return returns


# ---------------------------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------------------------

def analyze_regime_returns(regime_df, returns_df):
    """
    Layer 1: Average/median/win-rate of forward returns by regime.
    """
    combined = regime_df.join(returns_df, how="inner")
    results = {}

    for regime in ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]:
        mask = combined["regime"] == regime
        subset = combined[mask]
        n_months = int(mask.sum())

        regime_stats = {"n_months": n_months, "assets": {}}

        for col in returns_df.columns:
            vals = subset[col].dropna()
            if len(vals) < 10:
                continue
            regime_stats["assets"][col] = {
                "mean": round(float(vals.mean()), 2),
                "median": round(float(vals.median()), 2),
                "std": round(float(vals.std()), 2),
                "win_rate": round(float((vals > 0).mean()) * 100, 1),
                "p25": round(float(vals.quantile(0.25)), 2),
                "p75": round(float(vals.quantile(0.75)), 2),
                "n": int(len(vals)),
                "low_n_warning": len(vals) < 20,
            }

        results[regime] = regime_stats

    return results


def analyze_eight_regimes(regime_df, returns_df):
    """
    Layer 2: Eight-regime model (Growth × Inflation × Liquidity).
    Returns stats keyed by the full 8-regime label.
    """
    if "regime_8" not in regime_df.columns:
        return None

    combined = regime_df.join(returns_df, how="inner")
    results = {}

    # All 8 regime labels
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
        results[regime_8] = stats

    return results


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
                         regime_df, returns_df, years, layer2_eight=None):
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
                    bg = "#dcfce7" if mean > 0 else "#fee2e2" if mean < 0 else "#f3f4f6"
                    row += f'<td style="background:{bg}; text-align:center;">{mean:+.1f}%<br><small style="color:#6b7280;">{win}% win</small></td>'
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
    print("\n[4/6] Computing forward returns...")
    returns_df = compute_forward_returns(yahoo_data, regime_df)
    print(f"  Return columns: {len(returns_df.columns)}")

    # 4. Analyze
    print("\n[5/6] Analyzing...")
    layer1 = analyze_regime_returns(regime_df, returns_df)
    layer2_eight = analyze_eight_regimes(regime_df, returns_df)
    layer2_legacy = analyze_liquidity_overlay(regime_df, returns_df)
    transitions = analyze_transitions(regime_df, returns_df)
    timeline = compute_regime_timeline(regime_df)
    liquidity_va = compute_liquidity_value_added(layer1, layer2_legacy)

    # 5. Save results
    print("\n[6/6] Generating report...")
    regime_8_dist = regime_df["regime_8"].value_counts().to_dict() if "regime_8" in regime_df.columns else {}
    results = {
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "years": args.years,
        "total_months": len(regime_df),
        "regime_distribution": regime_df["regime"].value_counts().to_dict(),
        "regime_8_distribution": regime_8_dist,
        "layer1_regime_family_returns": layer1,
        "layer2_eight_regime_returns": layer2_eight,
        "layer2_liquidity_overlay_legacy": layer2_legacy,
        "transitions": transitions,
        "timeline": timeline,
        "liquidity_value_added": liquidity_va,
    }

    json_path = output_dir / "regime-backtest-results.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Results JSON: {json_path}")

    html = generate_html_report(layer1, layer2_legacy, transitions, timeline, liquidity_va,
                                regime_df, returns_df, args.years, layer2_eight=layer2_eight)
    html_path = output_dir / "regime-backtest-report.html"
    with open(html_path, "w") as f:
        f.write(html)
    print(f"  HTML report: {html_path}")

    # Print key findings
    print("\n=== Key Findings (Layer 1: Regime Only) ===")
    for regime in ["Goldilocks", "Overheating", "Disinflationary Slowdown", "Stagflation"]:
        rd = layer1.get(regime, {})
        n = rd.get("n_months", 0)
        sp = rd.get("assets", {})
        # Find S&P 500 3M (column name uses SandP or similar)
        sp_3m = None
        for col, vals in sp.items():
            if ("SandP" in col or "S_P" in col or "S&P" in col or "500" in col) and "3M" in col:
                sp_3m = vals
                break
        if sp_3m:
            print(f"  {regime} ({n}mo): S&P 500 3M avg {sp_3m['mean']:+.1f}%, win rate {sp_3m['win_rate']:.0f}%")
        else:
            # Fallback: show first 3M asset
            for col, vals in sp.items():
                if "3M" in col:
                    print(f"  {regime} ({n}mo): {col} avg {vals['mean']:+.1f}%, win rate {vals['win_rate']:.0f}%")
                    break

    if layer2_eight:
        print("\n=== Key Findings (Layer 2: Eight-Regime Model, 3M) ===")
        for regime_8, rd in sorted(layer2_eight.items()):
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
                print(f"  {regime_8} ({n}mo): S&P 500 3M avg {sp_3m['mean']:+.1f}%, win rate {sp_3m['win_rate']:.0f}%")

    if liquidity_va:
        print("\n=== Key Findings (Liquidity Value-Added, 3M) ===")
        for regime, assets in liquidity_va.items():
            for col, va in assets.items():
                if "SandP" in col or "500" in col or "S&P" in col:
                    verdict = "YES ✓" if va["liquidity_matters"] else "no ✗"
                    print(f"  {regime}: loose {va['loose_mean']:+.1f}% vs tight {va['tight_mean']:+.1f}% "
                          f"(spread {va['spread']:.1f}pp, IR {va['information_ratio']:.2f}) → {verdict}")

    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
