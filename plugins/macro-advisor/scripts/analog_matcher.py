#!/usr/bin/env python3
"""
Macro Advisor — Analog Matcher (Empirical Sentiment)

Finds historical periods most similar to the current macro state and computes
forward risk/reward ratios per asset class. Inspired by NowcastIQ's pattern
recognition approach.

Method:
    1. Build historical state vectors: (growth_score, inflation_score, liquidity_score)
    2. Compute cosine similarity between current state and all historical states
    3. Select top-N most similar periods (analogs)
    4. Compute forward 1/4/12-week returns per asset in those analog periods
    5. Express as upside/downside risk/reward ratios

Output:
    empirical-sentiment.json — per-asset risk/reward ratios, analog count,
    confidence level, and list of analog periods (for transparency).

Usage:
    python analog_matcher.py --fred-key YOUR_KEY --output-dir ./outputs/synthesis/ \\
        --growth-score 0.3 --inflation-score -0.2 --liquidity-score 0.5

    python analog_matcher.py --fred-key YOUR_KEY --output-dir ./outputs/synthesis/ \\
        --state-file outputs/synthesis/2026-W14-synthesis-data.json

    python analog_matcher.py --fred-key YOUR_KEY --output-dir ./outputs/synthesis/ \\
        --backtest --train-end 2019-12-31
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

# FRED series for state vector computation (same as regime_backtest.py)
FRED_SERIES = {
    # Growth axis
    "INDPRO": "Industrial Production Index",
    "UNRATE": "Unemployment Rate",
    "RSAFS": "Retail Sales",
    "PAYEMS": "Nonfarm Payrolls",
    # Inflation axis
    "CPIAUCSL": "CPI All Urban Consumers",
    "CPILFESL": "Core CPI ex Food & Energy",
    # Liquidity axis
    "M2SL": "M2 Money Stock",
    "NFCI": "Chicago Fed NFCI",
    "WALCL": "Fed Total Assets",
}

# Yahoo tickers for forward return measurement — core ETF universe
YAHOO_ASSETS = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "TLT": "US 20Y+ Treasuries",
    "GLD": "Gold",
    "GSG": "Commodities",
    "EFA": "Int'l Developed",
    "EEM": "Emerging Markets",
    "HYG": "High Yield Credit",
    "DX-Y.NYB": "US Dollar (DXY)",
    "XLE": "Energy Sector",
    "XLU": "Utilities Sector",
    "XLK": "Technology Sector",
    "IWM": "Russell 2000",
    "VNQ": "Real Estate",
    "TIP": "TIPS",
    "SHV": "Short Treasury",
}

# Forward windows in weeks
FORWARD_WINDOWS_WEEKS = [4, 12, 26]  # ~1 month, ~3 months, ~6 months

# Minimum analogs for a valid signal
MIN_ANALOGS = 10

# Default number of top analogs to use
DEFAULT_TOP_N = 20

# Direction window for score computation (months)
DIRECTION_WINDOW = 6


# ---------------------------------------------------------------------------
# DATA FETCHING
# ---------------------------------------------------------------------------

def fetch_fred_series(api_key, years=15):
    """Fetch all FRED series needed for state vector computation."""
    from fredapi import Fred
    fred = Fred(api_key=api_key)

    end = datetime.now()
    start = end - timedelta(days=years * 365 + 400)

    data = {}
    for series_id, name in FRED_SERIES.items():
        try:
            s = fred.get_series(series_id, observation_start=start, observation_end=end)
            if s is not None and len(s) > 0:
                data[series_id] = s
        except Exception as e:
            print(f"Warning: Failed to fetch {series_id} ({name}): {e}", file=sys.stderr)

    return data


def fetch_yahoo_weekly(tickers, years=15):
    """Fetch weekly price data for asset return computation."""
    import yfinance as yf

    end = datetime.now()
    start = end - timedelta(days=years * 365 + 60)

    data = {}
    for ticker, name in tickers.items():
        try:
            df = yf.download(ticker, start=start, end=end, interval="1wk",
                             progress=False, auto_adjust=True)
            if df is not None and len(df) > 10:
                close = df["Close"]
                # Handle multi-level columns from yfinance
                if hasattr(close, 'columns'):
                    close = close.iloc[:, 0]
                data[ticker] = close.dropna()
        except Exception as e:
            print(f"Warning: Failed to fetch {ticker} ({name}): {e}", file=sys.stderr)

    return data


# ---------------------------------------------------------------------------
# STATE VECTOR COMPUTATION
# ---------------------------------------------------------------------------

def _expanding_rank_pct(series):
    """Compute expanding-window rank percentile for each value.

    At each point t, the rank is computed only using values from index 0..t
    (no future data). This avoids look-ahead bias in backtests.

    Returns Series with values in [0, 1].
    """
    result = pd.Series(index=series.index, dtype=float)
    values = []
    for i, (idx, val) in enumerate(series.items()):
        if pd.isna(val):
            result.iloc[i] = np.nan
            continue
        values.append(val)
        # Rank of current value within all values seen so far
        rank = sum(1 for v in values if v <= val)
        n = len(values)
        result.iloc[i] = (rank - 1) / (n - 1) if n > 1 else 0.5
    return result


# Approximate FRED publication lags in months.
# E.g., INDPRO for January is released in mid-March (~2 month lag).
# We shift data forward by this many months so that at month t,
# the state vector only uses data that was actually published by month t.
FRED_PUB_LAG = {
    "INDPRO": 2,    # ~6-7 weeks after reference month
    "UNRATE": 1,    # ~4 weeks (first Friday of following month)
    "RSAFS": 2,     # ~6 weeks
    "PAYEMS": 1,    # ~4 weeks (first Friday)
    "CPIAUCSL": 1,  # ~2-3 weeks
    "CPILFESL": 1,  # same release as CPI
    "M2SL": 2,      # ~6 weeks
    "NFCI": 0,      # weekly, near real-time
    "WALCL": 0,     # weekly, near real-time
}


def compute_state_vectors(fred_data, apply_pub_lag=True):
    """Compute monthly state vectors: (growth_score, inflation_score, liquidity_score).

    Uses the same methodology as regime_backtest.py for consistency:
    - Growth: 6-month direction of INDPRO YoY, UNRATE (inv), Retail YoY, Payrolls YoY
    - Inflation: 6-month direction of CPI YoY + Core CPI YoY blend
    - Liquidity: majority vote of M2 YoY vs median, NFCI vs median, Fed BS YoY vs median

    Key anti-bias measures:
    - Expanding-window rank normalization (no future data in percentile computation)
    - Optional FRED publication lag shift (data dated to when it was available, not reference month)

    Returns DataFrame with growth_score, inflation_score, liquidity_score columns.
    """
    monthly = pd.DataFrame()

    # Build monthly indicators (same as regime_backtest.py)
    if "INDPRO" in fred_data:
        s = fred_data["INDPRO"].resample("ME").last().dropna()
        monthly["indpro_yoy"] = s.pct_change(12) * 100

    if "UNRATE" in fred_data:
        s = fred_data["UNRATE"].resample("ME").last().dropna()
        monthly["unrate"] = s

    if "RSAFS" in fred_data:
        s = fred_data["RSAFS"].resample("ME").last().dropna()
        monthly["retail_yoy"] = s.pct_change(12) * 100

    if "PAYEMS" in fred_data:
        s = fred_data["PAYEMS"].resample("ME").last().dropna()
        monthly["payrolls_yoy"] = s.pct_change(12) * 100

    if "CPIAUCSL" in fred_data:
        s = fred_data["CPIAUCSL"].resample("ME").last().dropna()
        monthly["cpi_yoy"] = s.pct_change(12) * 100

    if "CPILFESL" in fred_data:
        s = fred_data["CPILFESL"].resample("ME").last().dropna()
        monthly["core_cpi_yoy"] = s.pct_change(12) * 100

    if "M2SL" in fred_data:
        s = fred_data["M2SL"].resample("ME").last().dropna()
        monthly["m2_yoy"] = s.pct_change(12) * 100

    if "NFCI" in fred_data:
        s = fred_data["NFCI"].resample("ME").last().dropna()
        monthly["nfci"] = s

    if "WALCL" in fred_data:
        s = fred_data["WALCL"].resample("ME").last().dropna()
        monthly["fed_assets_yoy"] = s.pct_change(12) * 100

    monthly = monthly.dropna(how="all")

    # Apply FRED publication lag: shift each indicator forward so that
    # the value at month t reflects what was actually available at month t.
    if apply_pub_lag:
        col_to_series = {
            "indpro_yoy": "INDPRO", "unrate": "UNRATE", "retail_yoy": "RSAFS",
            "payrolls_yoy": "PAYEMS", "cpi_yoy": "CPIAUCSL", "core_cpi_yoy": "CPILFESL",
            "m2_yoy": "M2SL", "nfci": "NFCI", "fed_assets_yoy": "WALCL",
        }
        for col, series_id in col_to_series.items():
            lag = FRED_PUB_LAG.get(series_id, 0)
            if lag > 0 and col in monthly.columns:
                monthly[col] = monthly[col].shift(lag)

    # --- Growth score: continuous [-1, 1] ---
    growth_signals = pd.DataFrame(index=monthly.index)

    if "indpro_yoy" in monthly.columns:
        growth_signals["indpro"] = monthly["indpro_yoy"].diff(DIRECTION_WINDOW)
    if "unrate" in monthly.columns:
        growth_signals["unrate"] = -monthly["unrate"].diff(DIRECTION_WINDOW)
    if "retail_yoy" in monthly.columns:
        growth_signals["retail"] = monthly["retail_yoy"].diff(DIRECTION_WINDOW)
    if "payrolls_yoy" in monthly.columns:
        growth_signals["payrolls"] = monthly["payrolls_yoy"].diff(DIRECTION_WINDOW)

    # Normalize each signal to [-1, 1] using EXPANDING-WINDOW rank percentile.
    # At each month t, the rank uses only data from the start through month t.
    # This prevents future data from leaking into historical state vectors.
    for col in growth_signals.columns:
        ranked = _expanding_rank_pct(growth_signals[col])
        growth_signals[col] = (ranked - 0.5) * 2  # maps [0,1] to [-1,1]

    monthly["growth_score"] = growth_signals.mean(axis=1)

    # --- Inflation score: continuous [-1, 1] ---
    inflation_signals = pd.DataFrame(index=monthly.index)

    if "cpi_yoy" in monthly.columns:
        inflation_signals["cpi"] = monthly["cpi_yoy"].diff(DIRECTION_WINDOW)
    if "core_cpi_yoy" in monthly.columns:
        inflation_signals["core_cpi"] = monthly["core_cpi_yoy"].diff(DIRECTION_WINDOW)

    for col in inflation_signals.columns:
        ranked = _expanding_rank_pct(inflation_signals[col])
        inflation_signals[col] = (ranked - 0.5) * 2

    monthly["inflation_score"] = inflation_signals.mean(axis=1)

    # --- Liquidity score: continuous [-1, 1] ---
    # Uses 36-month rolling median comparison (matching regime_backtest.py methodology)
    liquidity_signals = pd.DataFrame(index=monthly.index)
    MEDIAN_WINDOW = 36

    if "m2_yoy" in monthly.columns:
        med = monthly["m2_yoy"].rolling(MEDIAN_WINDOW, min_periods=12).median()
        liquidity_signals["m2"] = monthly["m2_yoy"] - med

    if "nfci" in monthly.columns:
        med = monthly["nfci"].rolling(MEDIAN_WINDOW, min_periods=12).median()
        # NFCI: lower = looser, so invert
        liquidity_signals["nfci"] = -(monthly["nfci"] - med)

    if "fed_assets_yoy" in monthly.columns:
        med = monthly["fed_assets_yoy"].rolling(MEDIAN_WINDOW, min_periods=12).median()
        liquidity_signals["fed_bs"] = monthly["fed_assets_yoy"] - med

    for col in liquidity_signals.columns:
        ranked = _expanding_rank_pct(liquidity_signals[col])
        liquidity_signals[col] = (ranked - 0.5) * 2

    monthly["liquidity_score"] = liquidity_signals.mean(axis=1)

    # Drop rows where any score is NaN
    monthly = monthly.dropna(subset=["growth_score", "inflation_score", "liquidity_score"])

    return monthly[["growth_score", "inflation_score", "liquidity_score"]]


# ---------------------------------------------------------------------------
# ANALOG MATCHING
# ---------------------------------------------------------------------------

def cosine_similarity(v1, v2):
    """Compute cosine similarity between two vectors."""
    dot = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def find_analogs(state_vectors, current_state, top_n=DEFAULT_TOP_N, exclude_recent_months=12):
    """Find top-N most similar historical periods to the current state.

    Args:
        state_vectors: DataFrame with growth_score, inflation_score, liquidity_score
        current_state: dict with growth_score, inflation_score, liquidity_score
        top_n: number of analogs to return
        exclude_recent_months: exclude the most recent N months (12 default —
            macro regimes persist 12-18 months, so shorter exclusions risk
            selecting analogs from the same regime episode)

    Returns:
        List of (date, similarity_score) tuples, sorted by similarity descending.
    """
    current_vec = np.array([
        current_state["growth_score"],
        current_state["inflation_score"],
        current_state["liquidity_score"],
    ])

    # Exclude recent months
    if exclude_recent_months > 0:
        cutoff = state_vectors.index[-1] - pd.DateOffset(months=exclude_recent_months)
        candidates = state_vectors.loc[state_vectors.index <= cutoff]
    else:
        candidates = state_vectors

    similarities = []
    for date, row in candidates.iterrows():
        hist_vec = np.array([row["growth_score"], row["inflation_score"], row["liquidity_score"]])
        sim = cosine_similarity(current_vec, hist_vec)
        similarities.append((date, sim))

    # Sort by similarity descending
    similarities.sort(key=lambda x: x[1], reverse=True)

    return similarities[:top_n]


# ---------------------------------------------------------------------------
# FORWARD RETURN COMPUTATION
# ---------------------------------------------------------------------------

def compute_forward_returns_weekly(weekly_prices, analog_dates, forward_weeks):
    """Compute forward returns for each asset at each analog date.

    Args:
        weekly_prices: dict of {ticker: Series of weekly prices}
        analog_dates: list of (date, similarity) tuples from find_analogs
        forward_weeks: list of forward periods in weeks

    Returns:
        dict of {ticker: {window: list of returns}}
    """
    results = {}

    for ticker, prices in weekly_prices.items():
        results[ticker] = {}
        for fw in forward_weeks:
            returns = []
            for analog_date, sim in analog_dates:
                # Find the closest weekly price date to the analog date
                idx = prices.index.get_indexer([analog_date], method="nearest")[0]
                if idx < 0 or idx + fw >= len(prices):
                    continue
                # Skip if nearest match is more than 14 days from the analog date
                matched_date = prices.index[idx]
                if abs((matched_date - analog_date).days) > 14:
                    continue
                entry_price = float(prices.iloc[idx])
                exit_price = float(prices.iloc[idx + fw])
                if entry_price > 0:
                    ret = (exit_price / entry_price - 1) * 100
                    returns.append(ret)
            results[ticker][fw] = returns

    return results


# ---------------------------------------------------------------------------
# RISK/REWARD RATIO COMPUTATION
# ---------------------------------------------------------------------------

def compute_risk_reward(returns):
    """Compute risk/reward ratio from a list of returns.

    Risk/reward = trimmed_mean positive return / abs(trimmed_mean negative return).
    Uses 10th/90th percentile winsorization to reduce outlier sensitivity.
    A ratio of 10x means upside is ~10x the downside.
    A ratio of 1x means symmetric risk/reward.
    A ratio of 0.1x means downside is ~10x the upside.

    Returns:
        dict with ratio, mean_upside, mean_downside, hit_rate, n, mean, median, std
    """
    if not returns or len(returns) < 3:
        return {
            "ratio": None,
            "mean_upside": None,
            "mean_downside": None,
            "hit_rate": None,
            "n": len(returns) if returns else 0,
            "mean": None,
            "median": None,
            "std": None,
            "confidence": "insufficient_data",
        }

    arr = np.array(returns)

    # Winsorize at 10th/90th percentiles to reduce outlier sensitivity.
    # With 20 analogs, a single extreme return can swing the ratio dramatically.
    p10, p90 = np.percentile(arr, [10, 90])
    winsorized = np.clip(arr, p10, p90)

    positives = winsorized[winsorized > 0]
    negatives = winsorized[winsorized < 0]

    mean_up = float(np.mean(positives)) if len(positives) > 0 else 0.0
    mean_down = float(np.mean(negatives)) if len(negatives) > 0 else 0.0

    # When one side is near-zero, cap the ratio rather than hardcoding.
    # Use a floor of 0.1% to avoid division by zero.
    if abs(mean_down) < 0.1 and mean_up < 0.1:
        ratio = 1.0  # both sides near zero = truly neutral
    elif abs(mean_down) < 0.1:
        ratio = min(10.0, mean_up / 0.1)  # cap at 10x
    elif mean_up < 0.1:
        ratio = max(0.1, 0.1 / abs(mean_down))  # floor at 0.1x
    else:
        ratio = round(min(10.0, max(0.1, mean_up / abs(mean_down))), 2)

    # Confidence based on sample size
    n = len(returns)
    if n >= 20:
        confidence = "high"
    elif n >= MIN_ANALOGS:
        confidence = "medium"
    elif n >= 5:
        confidence = "low"
    else:
        confidence = "insufficient_data"

    return {
        "ratio": ratio,
        "mean_upside": round(mean_up, 2),
        "mean_downside": round(mean_down, 2),
        "hit_rate": round(float(len(arr[arr > 0]) / n * 100), 1),  # use original, not winsorized
        "n": n,
        "mean": round(float(np.mean(arr)), 2),
        "median": round(float(np.median(arr)), 2),
        "std": round(float(np.std(arr)), 2),
        "confidence": confidence,
    }


def interpret_ratio(ratio):
    """Convert ratio to human-readable signal."""
    if ratio is None:
        return "insufficient_data"
    if ratio >= 5.0:
        return "strong_bullish"
    elif ratio >= 2.0:
        return "bullish"
    elif ratio >= 1.2:
        return "slightly_bullish"
    elif ratio >= 0.8:
        return "neutral"
    elif ratio >= 0.5:
        return "slightly_bearish"
    elif ratio >= 0.2:
        return "bearish"
    else:
        return "strong_bearish"


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------

def run_analog_matching(fred_data, yahoo_weekly, current_state, top_n=DEFAULT_TOP_N,
                        train_end=None):
    """Run the full analog matching pipeline.

    Args:
        fred_data: dict of FRED series
        yahoo_weekly: dict of weekly price Series
        current_state: dict with growth_score, inflation_score, liquidity_score
        top_n: number of analogs
        train_end: if set, only use data up to this date for training (out-of-sample test)

    Returns:
        dict with per-asset risk/reward ratios and analog metadata
    """
    # Step 1: Compute historical state vectors
    state_vectors = compute_state_vectors(fred_data)

    if train_end:
        state_vectors = state_vectors.loc[state_vectors.index <= pd.Timestamp(train_end)]

    if len(state_vectors) < MIN_ANALOGS * 2:
        return {"error": f"Insufficient historical data: {len(state_vectors)} months (need ≥{MIN_ANALOGS * 2})"}

    # Step 2: Find analogs
    analogs = find_analogs(state_vectors, current_state, top_n=top_n,
                           exclude_recent_months=0 if train_end else 12)

    if len(analogs) < MIN_ANALOGS:
        return {"error": f"Only {len(analogs)} analogs found (need ≥{MIN_ANALOGS})"}

    # Step 3: Compute forward returns
    forward_returns = compute_forward_returns_weekly(yahoo_weekly, analogs, FORWARD_WINDOWS_WEEKS)

    # Step 4: Compute risk/reward ratios
    signals = {}
    for ticker, name in YAHOO_ASSETS.items():
        ticker_signals = {}
        for fw in FORWARD_WINDOWS_WEEKS:
            returns = forward_returns.get(ticker, {}).get(fw, [])
            rr = compute_risk_reward(returns)
            rr["signal"] = interpret_ratio(rr["ratio"])
            rr["forward_weeks"] = fw
            ticker_signals[f"{fw}w"] = rr
        signals[ticker] = {
            "name": name,
            "windows": ticker_signals,
        }

    # Step 5: Build output
    analog_periods = [
        {
            "date": d.strftime("%Y-%m"),
            "similarity": round(sim, 3),
        }
        for d, sim in analogs
    ]

    # Identify surprising findings (textbook-contradicting signals)
    surprises = []
    growth_dir = "rising" if current_state["growth_score"] > 0 else "falling"
    inflation_dir = "rising" if current_state["inflation_score"] > 0 else "falling"

    for ticker, data in signals.items():
        for window_key, rr in data["windows"].items():
            signal = rr.get("signal", "neutral")
            # Flag counter-intuitive signals
            if growth_dir == "falling" and ticker in ("SPY", "QQQ", "IWM") and "bullish" in signal:
                surprises.append(f"{data['name']} ({ticker}) shows {signal} at {window_key} despite falling growth")
            elif growth_dir == "rising" and ticker in ("TLT", "GLD") and "bullish" in signal:
                surprises.append(f"{data['name']} ({ticker}) shows {signal} at {window_key} despite rising growth")
            elif inflation_dir == "falling" and ticker == "GSG" and "bullish" in signal:
                surprises.append(f"Commodities ({ticker}) show {signal} at {window_key} despite falling inflation")

    return {
        "current_state": {
            "growth_score": round(current_state["growth_score"], 3),
            "inflation_score": round(current_state["inflation_score"], 3),
            "liquidity_score": round(current_state["liquidity_score"], 3),
        },
        "analog_count": len(analogs),
        "analog_periods": analog_periods,
        "mean_similarity": round(np.mean([s for _, s in analogs]), 3),
        "signals": signals,
        "surprises": surprises,
        "forward_windows_weeks": FORWARD_WINDOWS_WEEKS,
        "methodology": {
            "method": "cosine_similarity",
            "dimensions": ["growth_score", "inflation_score", "liquidity_score"],
            "top_n": top_n,
            "min_analogs": MIN_ANALOGS,
            "history_months": len(state_vectors),
            "exclude_recent_months": 0 if train_end else 12,
        },
    }


# ---------------------------------------------------------------------------
# OUT-OF-SAMPLE BACKTEST
# ---------------------------------------------------------------------------

def run_backtest(fred_data, yahoo_weekly, state_vectors, train_end, test_start=None,
                 top_n=DEFAULT_TOP_N):
    """Run out-of-sample backtest.

    For each month after train_end, use only data up to that month to find
    analogs, compute risk/reward ratios, then check actual forward returns.

    Anti-bias measures:
    - 12-month exclusion window (prevents same-episode contamination)
    - Expanding-window state vectors (no future data in ranks)
    - Per-ticker naive baseline comparison
    - Bootstrap confidence intervals on hit rates
    - Neutral predictions tracked separately (not excluded from accuracy)
    - Materiality threshold (±0.5% dead zone for direction calls)

    Returns summary statistics on signal accuracy.
    """
    if test_start is None:
        test_start = pd.Timestamp(train_end) + pd.DateOffset(months=1)
    else:
        test_start = pd.Timestamp(test_start)

    test_months = state_vectors.loc[state_vectors.index >= test_start]
    if len(test_months) < 6:
        return {"error": f"Only {len(test_months)} test months available"}

    results = []
    for date, row in test_months.iterrows():
        current = {
            "growth_score": row["growth_score"],
            "inflation_score": row["inflation_score"],
            "liquidity_score": row["liquidity_score"],
        }

        # Only use history up to this date
        train_vectors = state_vectors.loc[state_vectors.index < date]
        if len(train_vectors) < MIN_ANALOGS * 2:
            continue

        # Use 12-month exclusion even in backtest mode to prevent
        # same-episode contamination (macro regimes persist 12-18 months)
        analogs = find_analogs(train_vectors, current, top_n=top_n,
                               exclude_recent_months=12)
        if len(analogs) < MIN_ANALOGS:
            continue

        forward_returns = compute_forward_returns_weekly(yahoo_weekly, analogs, FORWARD_WINDOWS_WEEKS)

        for ticker in YAHOO_ASSETS:
            for fw in FORWARD_WINDOWS_WEEKS:
                returns = forward_returns.get(ticker, {}).get(fw, [])
                rr = compute_risk_reward(returns)
                signal = interpret_ratio(rr["ratio"])

                # Compute actual forward return for this test date
                if ticker in yahoo_weekly:
                    prices = yahoo_weekly[ticker]
                    idx = prices.index.get_indexer([date], method="nearest")[0]
                    if 0 <= idx < len(prices) - fw:
                        matched_date = prices.index[idx]
                        if abs((matched_date - date).days) > 14:
                            actual = None
                        else:
                            actual = (float(prices.iloc[idx + fw]) / float(prices.iloc[idx]) - 1) * 100
                    else:
                        actual = None
                else:
                    actual = None

                results.append({
                    "date": date.strftime("%Y-%m"),
                    "ticker": ticker,
                    "forward_weeks": fw,
                    "predicted_signal": signal,
                    "predicted_ratio": rr["ratio"],
                    "predicted_mean": rr["mean"],
                    "actual_return": round(float(actual), 2) if actual is not None else None,
                    "n_analogs": rr["n"],
                })

    if not results:
        return {"error": "No valid backtest results"}

    df = pd.DataFrame(results)
    df = df.dropna(subset=["actual_return"])

    # --- Directional accuracy with materiality threshold ---
    # A return within ±0.5% is treated as "flat" — neither side gets credit.
    MATERIALITY_THRESHOLD = 0.5

    correct = 0
    total = 0
    neutral_count = 0
    neutral_correct = 0
    for _, row in df.iterrows():
        sig = row["predicted_signal"]
        actual = row["actual_return"]
        is_flat = abs(actual) < MATERIALITY_THRESHOLD

        if sig == "neutral":
            neutral_count += 1
            if is_flat:
                neutral_correct += 1
            continue  # neutral tracked separately

        if "bullish" in sig:
            total += 1
            if not is_flat and actual > 0:
                correct += 1
        elif "bearish" in sig:
            total += 1
            if not is_flat and actual < 0:
                correct += 1

    hit_rate = round(correct / total * 100, 1) if total > 0 else 0

    # --- Per-ticker, per-window naive baseline ---
    # The naive baseline for each ticker/window is the unconditional frequency
    # of positive returns. If SPY goes up 60% of the time, a model that always
    # predicts "bullish" gets 60% for free. We need to beat this.
    baseline_stats = {}
    for ticker in YAHOO_ASSETS:
        for fw in FORWARD_WINDOWS_WEEKS:
            mask = (df["ticker"] == ticker) & (df["forward_weeks"] == fw)
            subset = df[mask]
            if len(subset) < 5:
                continue

            # Naive baseline: fraction of periods with positive returns
            actual_positive_rate = float((subset["actual_return"] > MATERIALITY_THRESHOLD).mean()) * 100

            # Model accuracy for this ticker/window
            ticker_correct = 0
            ticker_total = 0
            for _, row in subset.iterrows():
                sig = row["predicted_signal"]
                actual = row["actual_return"]
                is_flat = abs(actual) < MATERIALITY_THRESHOLD
                if sig == "neutral":
                    continue
                if "bullish" in sig:
                    ticker_total += 1
                    if not is_flat and actual > 0:
                        ticker_correct += 1
                elif "bearish" in sig:
                    ticker_total += 1
                    if not is_flat and actual < 0:
                        ticker_correct += 1

            ticker_hit = round(ticker_correct / ticker_total * 100, 1) if ticker_total > 0 else None

            # Naive baseline: always predict the majority direction
            naive_hit = max(actual_positive_rate, 100 - actual_positive_rate)

            # Fraction of predictions that are bullish (detects asymmetric prediction bias)
            bullish_pct = float((subset["predicted_signal"].str.contains("bullish")).mean()) * 100

            baseline_stats[f"{ticker}_{fw}w"] = {
                "ticker": ticker,
                "forward_weeks": fw,
                "n_predictions": ticker_total,
                "model_hit_rate": ticker_hit,
                "naive_baseline": round(naive_hit, 1),
                "excess_accuracy": round(ticker_hit - naive_hit, 1) if ticker_hit is not None else None,
                "actual_positive_rate": round(actual_positive_rate, 1),
                "bullish_prediction_pct": round(bullish_pct, 1),
            }

    # --- Bootstrap confidence interval on overall hit rate ---
    n_bootstrap = 1000
    if total > 0:
        # Build array of 0/1 for correct/incorrect directional predictions
        direction_results = []
        for _, row in df.iterrows():
            sig = row["predicted_signal"]
            actual = row["actual_return"]
            if sig == "neutral":
                continue
            is_flat = abs(actual) < MATERIALITY_THRESHOLD
            if "bullish" in sig:
                direction_results.append(1 if (not is_flat and actual > 0) else 0)
            elif "bearish" in sig:
                direction_results.append(1 if (not is_flat and actual < 0) else 0)

        direction_arr = np.array(direction_results)
        rng = np.random.default_rng(42)
        boot_hits = []
        for _ in range(n_bootstrap):
            sample = rng.choice(direction_arr, size=len(direction_arr), replace=True)
            boot_hits.append(float(sample.mean()) * 100)
        ci_lower = round(float(np.percentile(boot_hits, 2.5)), 1)
        ci_upper = round(float(np.percentile(boot_hits, 97.5)), 1)
    else:
        ci_lower = ci_upper = 0

    # Compute overall naive baseline (weighted avg across tickers)
    naive_baselines = [v["naive_baseline"] for v in baseline_stats.values() if v["naive_baseline"] is not None]
    overall_naive = round(float(np.mean(naive_baselines)), 1) if naive_baselines else None

    return {
        "test_period": f"{test_months.index[0].strftime('%Y-%m')} to {test_months.index[-1].strftime('%Y-%m')}",
        "test_months": len(test_months),
        "total_directional_predictions": total,
        "correct_directional_predictions": correct,
        "directional_hit_rate": hit_rate,
        "hit_rate_95ci": [ci_lower, ci_upper],
        "neutral_predictions": neutral_count,
        "neutral_predictions_pct": round(neutral_count / (total + neutral_count) * 100, 1) if (total + neutral_count) > 0 else 0,
        "materiality_threshold_pct": MATERIALITY_THRESHOLD,
        "naive_baseline_hit_rate": overall_naive,
        "excess_accuracy_vs_naive": round(hit_rate - overall_naive, 1) if overall_naive else None,
        "per_ticker_baselines": baseline_stats,
        "results_sample": results[:50],  # first 50 for inspection
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Macro Advisor — Analog Matcher")
    parser.add_argument("--fred-key", required=True, help="FRED API key")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--years", type=int, default=15, help="Years of history (default: 15)")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N,
                        help=f"Number of analogs (default: {DEFAULT_TOP_N})")

    # Current state — either explicit scores or from a synthesis JSON
    parser.add_argument("--growth-score", type=float, help="Current growth score (-1 to 1)")
    parser.add_argument("--inflation-score", type=float, help="Current inflation score (-1 to 1)")
    parser.add_argument("--liquidity-score", type=float, help="Current liquidity score (-1 to 1)")
    parser.add_argument("--state-file", help="Path to synthesis-data.json (reads scores from regime block)")

    # Backtest mode
    parser.add_argument("--backtest", action="store_true", help="Run out-of-sample backtest")
    parser.add_argument("--train-end", help="Training cutoff date (YYYY-MM-DD) for backtest")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve current state
    current_state = None
    if args.state_file:
        state_path = Path(args.state_file)
        if state_path.exists():
            sdata = json.loads(state_path.read_text(encoding="utf-8"))
            regime = sdata.get("regime", {})
            current_state = {
                "growth_score": float(regime.get("growth_score", 0)),
                "inflation_score": float(regime.get("inflation_score", 0)),
                "liquidity_score": float(regime.get("liquidity_score", 0)),
            }
            print(f"State from {args.state_file}: {current_state}", file=sys.stderr)
        else:
            print(f"Error: state file not found: {args.state_file}", file=sys.stderr)
            sys.exit(1)
    elif args.growth_score is not None and args.inflation_score is not None and args.liquidity_score is not None:
        current_state = {
            "growth_score": args.growth_score,
            "inflation_score": args.inflation_score,
            "liquidity_score": args.liquidity_score,
        }
    elif not args.backtest:
        print("Error: Provide --state-file or all three score flags, or use --backtest mode",
              file=sys.stderr)
        sys.exit(1)

    # Fetch data
    print("Fetching FRED data...", file=sys.stderr)
    fred_data = fetch_fred_series(args.fred_key, years=args.years)
    print(f"  Fetched {len(fred_data)} FRED series", file=sys.stderr)

    print("Fetching Yahoo weekly prices...", file=sys.stderr)
    yahoo_weekly = fetch_yahoo_weekly(YAHOO_ASSETS, years=args.years)
    print(f"  Fetched {len(yahoo_weekly)} tickers", file=sys.stderr)

    if args.backtest:
        # Backtest mode
        train_end = args.train_end or "2019-12-31"
        print(f"Running out-of-sample backtest (train end: {train_end})...", file=sys.stderr)

        state_vectors = compute_state_vectors(fred_data)
        result = run_backtest(fred_data, yahoo_weekly, state_vectors,
                              train_end=train_end, top_n=args.top_n)

        out_path = output_dir / "analog-backtest-results.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nBacktest results saved to {out_path}", file=sys.stderr)

        if "directional_hit_rate" in result:
            print(f"Directional hit rate: {result['directional_hit_rate']}% "
                  f"({result['correct_directional_predictions']}/{result['total_directional_predictions']})",
                  file=sys.stderr)
            print(f"  95% CI: [{result['hit_rate_95ci'][0]}%, {result['hit_rate_95ci'][1]}%]",
                  file=sys.stderr)
            print(f"  Naive baseline: {result['naive_baseline_hit_rate']}%",
                  file=sys.stderr)
            print(f"  Excess vs naive: {result['excess_accuracy_vs_naive']}pp",
                  file=sys.stderr)
            print(f"  Neutral predictions: {result['neutral_predictions']} "
                  f"({result['neutral_predictions_pct']}% of all predictions)",
                  file=sys.stderr)
        elif "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)

        # Print summary to stdout
        print(json.dumps(result, indent=2))

    else:
        # Normal analog matching mode
        print(f"Finding top {args.top_n} analogs...", file=sys.stderr)
        result = run_analog_matching(fred_data, yahoo_weekly, current_state,
                                     top_n=args.top_n)

        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

        out_path = output_dir / "empirical-sentiment.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nEmpirical sentiment saved to {out_path}", file=sys.stderr)
        print(f"Analogs found: {result['analog_count']}, "
              f"mean similarity: {result['mean_similarity']}", file=sys.stderr)

        if result.get("surprises"):
            print(f"\nSurprising findings:", file=sys.stderr)
            for s in result["surprises"]:
                print(f"  ⚠ {s}", file=sys.stderr)

        # Print summary to stdout
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
