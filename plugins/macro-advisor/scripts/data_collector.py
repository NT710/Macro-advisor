#!/usr/bin/env python3
"""
Macro Advisor — Skill 0: Data Collection Script
Pulls structured data from FRED and Yahoo Finance.
Saves current readings + trailing history as JSON.

Modes:
    --mode weekly     (default) 26-week lookback for regular Sunday runs
    --mode historical 5-year lookback for deep analysis and regime comparison

Usage:
    python data_collector.py --fred-key YOUR_KEY --output-dir ./outputs/data/
    python data_collector.py --fred-key YOUR_KEY --output-dir ./outputs/data/ --mode historical
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# FRED SERIES CONFIGURATION
# ---------------------------------------------------------------------------
FRED_SERIES = {
    # Money Supply
    "WM2NS": ("US M2 Money Stock (weekly)", "money_supply", "weekly"),
    "M2SL": ("US M2 Money Stock (monthly SA)", "money_supply", "monthly"),

    # Fed Balance Sheet & Plumbing
    "WALCL": ("Fed Total Assets", "fed_balance_sheet", "weekly"),
    "WTREGEN": ("Treasury General Account (TGA)", "fed_balance_sheet", "weekly"),
    "RRPONTSYD": ("Reverse Repo Facility (ON RRP)", "fed_balance_sheet", "daily"),
    "WRESBAL": ("Reserve Balances at Fed", "fed_balance_sheet", "weekly"),

    # Interest Rates
    "DFF": ("Fed Funds Effective Rate", "rates", "daily"),
    "DGS2": ("2-Year Treasury Yield", "rates", "daily"),
    "DGS5": ("5-Year Treasury Yield", "rates", "daily"),
    "DGS10": ("10-Year Treasury Yield", "rates", "daily"),
    "DGS30": ("30-Year Treasury Yield", "rates", "daily"),
    "T10Y2Y": ("10Y-2Y Treasury Spread", "rates", "daily"),
    "T10Y3M": ("10Y-3M Treasury Spread", "rates", "daily"),

    # Credit Spreads
    "BAMLH0A0HYM2": ("ICE BofA US HY OAS", "credit", "daily"),
    "BAMLC0A0CM": ("ICE BofA US IG OAS", "credit", "daily"),
    "BAMLH0A0HYM2EY": ("ICE BofA US HY Effective Yield", "credit", "daily"),

    # Financial Conditions
    "NFCI": ("Chicago Fed NFCI", "financial_conditions", "weekly"),
    "ANFCI": ("Adjusted NFCI", "financial_conditions", "weekly"),
    "STLFSI4": ("St. Louis Fed Financial Stress Index", "financial_conditions", "weekly"),

    # Inflation
    "CPIAUCSL": ("CPI All Urban Consumers", "inflation", "monthly"),
    "CPILFESL": ("Core CPI (ex Food & Energy)", "inflation", "monthly"),
    "PCEPI": ("PCE Price Index", "inflation", "monthly"),
    "PCEPILFE": ("Core PCE Price Index", "inflation", "monthly"),
    "T5YIE": ("5-Year Breakeven Inflation", "inflation", "daily"),
    "T10YIE": ("10-Year Breakeven Inflation", "inflation", "daily"),
    "MICH": ("U of Michigan Inflation Expectations", "inflation", "monthly"),

    # Employment
    "PAYEMS": ("Total Nonfarm Payrolls", "employment", "monthly"),
    "UNRATE": ("Unemployment Rate", "employment", "monthly"),
    "ICSA": ("Initial Jobless Claims", "employment", "weekly"),
    "CCSA": ("Continuing Jobless Claims", "employment", "weekly"),
    "JTSJOL": ("JOLTS Job Openings", "employment", "monthly"),
    "JTSQUR": ("JOLTS Quits Rate", "employment", "monthly"),

    # Growth & Activity
    "GDP": ("Real GDP", "growth", "quarterly"),
    "GDPC1": ("Real GDP (chained)", "growth", "quarterly"),
    "INDPRO": ("Industrial Production Index", "growth", "monthly"),
    "RSAFS": ("Retail Sales", "growth", "monthly"),
    "UMCSENT": ("U of Michigan Consumer Sentiment", "growth", "monthly"),

    # PMIs (ISM)
    "MANEMP": ("ISM Manufacturing Employment", "pmi", "monthly"),
    "NAPMNOI": ("ISM Manufacturing New Orders", "pmi", "monthly"),
    "NAPMPI": ("ISM Manufacturing Prices", "pmi", "monthly"),

    # Housing
    "HOUST": ("Housing Starts", "housing", "monthly"),
    "PERMIT": ("Building Permits", "housing", "monthly"),
    "EXHOSLUSM495S": ("Existing Home Sales", "housing", "monthly"),
    "CSUSHPISA": ("Case-Shiller Home Price Index", "housing", "monthly"),

    # Leading Indicators
    "USSLIND": ("Conference Board LEI", "leading", "monthly"),
}

# ---------------------------------------------------------------------------
# YAHOO FINANCE TICKERS
# ---------------------------------------------------------------------------
YAHOO_TICKERS = {
    # Equity Indices
    "^GSPC": ("S&P 500", "equities"),
    "^NDX": ("Nasdaq 100", "equities"),
    "^RUT": ("Russell 2000", "equities"),
    "^STOXX50E": ("Euro Stoxx 50", "equities"),

    # Volatility
    "^VIX": ("VIX", "volatility"),

    # Bond ETFs
    "TLT": ("iShares 20+ Year Treasury", "bonds"),
    "HYG": ("iShares High Yield Corporate", "credit_etf"),
    "LQD": ("iShares Investment Grade Corporate", "credit_etf"),

    # Commodities
    "GC=F": ("Gold Futures", "commodities"),
    "CL=F": ("Crude Oil WTI Futures", "commodities"),
    "HG=F": ("Copper Futures", "commodities"),

    # Currencies
    "EURUSD=X": ("EUR/USD", "fx"),
    "JPY=X": ("USD/JPY", "fx"),
    "CHF=X": ("USD/CHF", "fx"),
    "GBPUSD=X": ("GBP/USD", "fx"),
    "CNY=X": ("USD/CNY", "fx"),
    "DX-Y.NYB": ("US Dollar Index (DXY)", "fx"),

    # Regional ETFs
    "EEM": ("iShares MSCI EM ETF", "em"),
    "EFA": ("iShares MSCI EAFE ETF", "dm_intl"),

    # Money Markets
    "SHV": ("iShares Short Treasury", "money_market"),
}


def safe_float(val):
    """Safely convert pandas values to float, handling Series and scalar."""
    try:
        if hasattr(val, 'iloc'):
            return float(val.iloc[0])
        return float(val)
    except (TypeError, ValueError, IndexError):
        return None


def fetch_fred_data(api_key, lookback_days=182):
    """Fetch all FRED series with trailing history."""
    try:
        from fredapi import Fred
    except ImportError:
        print("ERROR: fredapi not installed. Run: pip install fredapi")
        return None

    fred = Fred(api_key=api_key)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    # For YoY calculations, we need at least 13 months of data
    yoy_start = end_date - timedelta(days=max(lookback_days, 400))

    results = {}
    errors = []

    for series_id, (name, category, freq) in FRED_SERIES.items():
        try:
            # Use extended start for YoY calculation
            fetch_start = yoy_start if freq in ("monthly", "quarterly") else start_date
            data = fred.get_series(series_id, observation_start=fetch_start, observation_end=end_date)
            if data is not None and len(data) > 0:
                data = data.dropna()
                if len(data) > 0:
                    latest = float(data.iloc[-1])
                    prior = float(data.iloc[-2]) if len(data) > 1 else None

                    change_abs = round(latest - prior, 4) if prior is not None else None
                    change_pct = round((latest - prior) / abs(prior) * 100, 4) if prior is not None and prior != 0 else None

                    # YoY change
                    yoy_change = None
                    if freq in ("monthly", "quarterly"):
                        year_ago_target = data.index[-1] - timedelta(days=365)
                        year_ago_candidates = data[data.index <= year_ago_target]
                        if len(year_ago_candidates) > 0:
                            year_ago_val = float(year_ago_candidates.iloc[-1])
                            if year_ago_val != 0:
                                yoy_change = round((latest - year_ago_val) / abs(year_ago_val) * 100, 2)

                    # MoM change for monthly data
                    mom_change = None
                    if freq == "monthly" and prior is not None and prior != 0:
                        mom_change = round((latest - prior) / abs(prior) * 100, 4)

                    # Trim history to requested lookback for output
                    history_data = data[data.index >= start_date]
                    history = []
                    for ts, val in history_data.tail(52).items():
                        history.append({
                            "date": ts.strftime("%Y-%m-%d"),
                            "value": round(float(val), 4)
                        })

                    # Percentile rank (where is current value vs. history?)
                    percentile = None
                    if len(data) >= 10:
                        below = (data < latest).sum()
                        percentile = round(below / len(data) * 100, 1)

                    results[series_id] = {
                        "name": name,
                        "category": category,
                        "frequency": freq,
                        "latest_value": round(latest, 4),
                        "latest_date": data.index[-1].strftime("%Y-%m-%d"),
                        "prior_value": round(prior, 4) if prior is not None else None,
                        "prior_date": data.index[-2].strftime("%Y-%m-%d") if len(data) > 1 else None,
                        "change_absolute": change_abs,
                        "change_percent": change_pct,
                        "mom_change_percent": mom_change,
                        "yoy_change_percent": yoy_change,
                        "percentile_rank": percentile,
                        "history": history,
                        "observation_count": len(history_data),
                    }
                else:
                    errors.append(f"{series_id}: no data after dropping NaN")
            else:
                errors.append(f"{series_id}: empty response")
        except Exception as e:
            errors.append(f"{series_id}: {str(e)[:100]}")

    return {"data": results, "errors": errors}


def fetch_yahoo_data(lookback_days=182):
    """Fetch Yahoo Finance tickers with trailing history."""
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip install yfinance")
        return None

    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    results = {}
    errors = []

    # Batch download for efficiency
    all_tickers = list(YAHOO_TICKERS.keys())
    try:
        batch = yf.download(all_tickers, start=start_date.strftime("%Y-%m-%d"),
                           end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=True,
                           group_by="ticker")
    except Exception as e:
        print(f"  Batch download failed: {e}. Falling back to individual downloads.")
        batch = None

    for ticker, (name, category) in YAHOO_TICKERS.items():
        try:
            if batch is not None and len(all_tickers) > 1:
                try:
                    close = batch[ticker]["Close"].dropna()
                except (KeyError, TypeError):
                    close = None
            else:
                close = None

            # Fallback to individual download
            if close is None or len(close) == 0:
                data = yf.download(ticker, start=start_date.strftime("%Y-%m-%d"),
                                 end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
                if data is not None and len(data) > 0:
                    close = data["Close"].dropna()
                    # Flatten if multi-level columns
                    if hasattr(close, 'columns'):
                        close = close.iloc[:, 0]

            if close is not None and len(close) > 0:
                latest = safe_float(close.iloc[-1])
                prior = safe_float(close.iloc[-2]) if len(close) > 1 else None

                if latest is None:
                    errors.append(f"{ticker}: could not parse latest value")
                    continue

                # Week change
                week_ago_idx = max(0, len(close) - 6)
                week_ago = safe_float(close.iloc[week_ago_idx])
                week_change_pct = round((latest - week_ago) / abs(week_ago) * 100, 2) if week_ago and week_ago != 0 else None

                # Month change
                month_ago_idx = max(0, len(close) - 22)
                month_ago = safe_float(close.iloc[month_ago_idx])
                month_change_pct = round((latest - month_ago) / abs(month_ago) * 100, 2) if month_ago and month_ago != 0 else None

                # 3-month change
                three_month_idx = max(0, len(close) - 66)
                three_month_ago = safe_float(close.iloc[three_month_idx])
                three_month_change_pct = round((latest - three_month_ago) / abs(three_month_ago) * 100, 2) if three_month_ago and three_month_ago != 0 else None

                # Build weekly history
                weekly = close.resample("W-FRI").last().dropna()
                history = []
                for ts in weekly.tail(52).index:
                    v = safe_float(weekly.loc[ts])
                    if v is not None:
                        history.append({
                            "date": ts.strftime("%Y-%m-%d"),
                            "value": round(v, 4)
                        })

                results[ticker] = {
                    "name": name,
                    "category": category,
                    "latest_value": round(latest, 4),
                    "latest_date": close.index[-1].strftime("%Y-%m-%d"),
                    "prior_close": round(prior, 4) if prior is not None else None,
                    "day_change_pct": round((latest - prior) / abs(prior) * 100, 2) if prior and prior != 0 else None,
                    "week_change_pct": week_change_pct,
                    "month_change_pct": month_change_pct,
                    "three_month_change_pct": three_month_change_pct,
                    "history": history,
                }
            else:
                errors.append(f"{ticker}: no data returned")
        except Exception as e:
            errors.append(f"{ticker}: {str(e)[:100]}")

    return {"data": results, "errors": errors}


def compute_derived_metrics(fred_data, yahoo_data):
    """Compute higher-level derived metrics from raw data."""
    derived = {}
    fd = fred_data.get("data", {}) if fred_data else {}
    yd = yahoo_data.get("data", {}) if yahoo_data else {}

    # Yield curve signal
    if "T10Y2Y" in fd:
        val = fd["T10Y2Y"]["latest_value"]
        hist = fd["T10Y2Y"].get("history", [])
        # Count consecutive weeks in current state
        consecutive = 0
        current_sign = val >= 0
        for h in reversed(hist):
            if (h["value"] >= 0) == current_sign:
                consecutive += 1
            else:
                break
        derived["yield_curve_10y2y"] = {
            "value": val,
            "signal": "inverted (recession warning)" if val < 0 else "steepening (expansion)" if val > 0.5 else "flat (transition)",
            "date": fd["T10Y2Y"]["latest_date"],
            "consecutive_weeks_in_state": consecutive,
            "percentile": fd["T10Y2Y"].get("percentile_rank")
        }

    # Real rates
    if "DGS10" in fd and "T10YIE" in fd:
        real_rate = round(fd["DGS10"]["latest_value"] - fd["T10YIE"]["latest_value"], 4)
        derived["real_10y_rate"] = {
            "value": real_rate,
            "signal": "restrictive" if real_rate > 2.0 else "neutral" if real_rate > 0.5 else "accommodative",
            "date": fd["DGS10"]["latest_date"]
        }

    # Credit stress
    if "BAMLH0A0HYM2" in fd and "BAMLC0A0CM" in fd:
        hy = fd["BAMLH0A0HYM2"]["latest_value"]
        ig = fd["BAMLC0A0CM"]["latest_value"]
        derived["credit_spreads"] = {
            "hy_oas_bps": round(hy * 100, 0),
            "ig_oas_bps": round(ig * 100, 0),
            "hy_ig_diff_bps": round((hy - ig) * 100, 0),
            "hy_signal": "distress" if hy > 6.0 else "stress" if hy > 5.0 else "elevated" if hy > 4.0 else "normal" if hy > 3.0 else "compressed",
            "hy_direction": "widening" if (fd["BAMLH0A0HYM2"].get("change_absolute") or 0) > 0 else "tightening",
            "hy_percentile": fd["BAMLH0A0HYM2"].get("percentile_rank"),
            "date": fd["BAMLH0A0HYM2"]["latest_date"]
        }

    # VIX regime
    if "^VIX" in yd:
        vix = yd["^VIX"]["latest_value"]
        derived["vix_regime"] = {
            "value": vix,
            "signal": "panic" if vix > 35 else "fear" if vix > 25 else "elevated" if vix > 20 else "complacent" if vix < 13 else "normal",
            "week_change": yd["^VIX"].get("week_change_pct"),
            "date": yd["^VIX"]["latest_date"]
        }

    # Liquidity plumbing
    if "WTREGEN" in fd and "RRPONTSYD" in fd:
        tga_change = fd["WTREGEN"].get("change_absolute")
        rrp_change = fd["RRPONTSYD"].get("change_absolute")
        liquidity_signal = "neutral"
        if tga_change is not None and rrp_change is not None:
            if tga_change < 0 and rrp_change < 0:
                liquidity_signal = "double injection"
            elif tga_change < 0 or rrp_change < 0:
                liquidity_signal = "net injection"
            elif tga_change > 0 and rrp_change > 0:
                liquidity_signal = "double drain"
            else:
                liquidity_signal = "net drain"
        derived["liquidity_plumbing"] = {
            "tga_balance_B": round(fd["WTREGEN"]["latest_value"] / 1000, 1),
            "tga_change": tga_change,
            "rrp_usage_B": round(fd["RRPONTSYD"]["latest_value"], 1),
            "rrp_change": rrp_change,
            "signal": liquidity_signal
        }

    # M2 growth regime
    if "M2SL" in fd and fd["M2SL"].get("yoy_change_percent") is not None:
        m2_yoy = fd["M2SL"]["yoy_change_percent"]
        derived["m2_growth"] = {
            "yoy_percent": m2_yoy,
            "signal": "expanding" if m2_yoy > 5 else "moderate" if m2_yoy > 2 else "stagnant" if m2_yoy > 0 else "contracting",
            "date": fd["M2SL"]["latest_date"]
        }

    # NFCI regime
    if "NFCI" in fd:
        nfci = fd["NFCI"]["latest_value"]
        nfci_hist = fd["NFCI"].get("history", [])
        consecutive_loose = 0
        for h in reversed(nfci_hist):
            if h["value"] < 0:
                consecutive_loose += 1
            else:
                break
        derived["financial_conditions"] = {
            "nfci": nfci,
            "signal": "tight" if nfci > 0 else "loose",
            "consecutive_weeks_loose": consecutive_loose if nfci < 0 else 0,
            "percentile": fd["NFCI"].get("percentile_rank"),
            "date": fd["NFCI"]["latest_date"]
        }

    # USD trend
    if "DX-Y.NYB" in yd:
        dxy = yd["DX-Y.NYB"]
        derived["usd_trend"] = {
            "value": dxy["latest_value"],
            "week_change_pct": dxy.get("week_change_pct"),
            "month_change_pct": dxy.get("month_change_pct"),
            "signal": "strengthening" if (dxy.get("month_change_pct") or 0) > 1 else "weakening" if (dxy.get("month_change_pct") or 0) < -1 else "range-bound"
        }

    # Equity market regime
    if "^GSPC" in yd:
        sp = yd["^GSPC"]
        derived["equity_regime"] = {
            "sp500": sp["latest_value"],
            "week_pct": sp.get("week_change_pct"),
            "month_pct": sp.get("month_change_pct"),
            "three_month_pct": sp.get("three_month_change_pct"),
            "trend": "strong uptrend" if (sp.get("three_month_change_pct") or 0) > 5 else "uptrend" if (sp.get("three_month_change_pct") or 0) > 0 else "downtrend" if (sp.get("three_month_change_pct") or 0) > -10 else "correction"
        }

    # Inflation expectations
    if "T5YIE" in fd and "T10YIE" in fd:
        be5 = fd["T5YIE"]["latest_value"]
        be10 = fd["T10YIE"]["latest_value"]
        derived["inflation_expectations"] = {
            "breakeven_5y": be5,
            "breakeven_10y": be10,
            "anchored": abs(be10 - 2.0) < 0.5,
            "signal": "elevated" if be5 > 2.8 else "anchored" if be5 < 2.5 else "drifting higher",
            "date": fd["T5YIE"]["latest_date"]
        }

    return derived


def build_summary_snapshot(fred_data, yahoo_data, derived):
    """Build a concise summary for skill consumption."""
    fd = fred_data.get("data", {}) if fred_data else {}
    yd = yahoo_data.get("data", {}) if yahoo_data else {}

    snapshot = {
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "rates": {},
        "credit": {},
        "liquidity": {},
        "growth": {},
        "inflation": {},
        "markets": {},
        "derived_signals": {},
    }

    # Rates
    for sid, key in [("DFF", "fed_funds"), ("DGS2", "us_2y"), ("DGS5", "us_5y"), ("DGS10", "us_10y"), ("DGS30", "us_30y")]:
        if sid in fd:
            snapshot["rates"][key] = {"value": fd[sid]["latest_value"], "date": fd[sid]["latest_date"],
                                       "change": fd[sid].get("change_absolute"), "percentile": fd[sid].get("percentile_rank")}

    # Credit
    for key in ["credit_spreads"]:
        if key in derived:
            snapshot["credit"] = derived[key]

    # Liquidity
    for key in ["m2_growth", "liquidity_plumbing", "financial_conditions"]:
        if key in derived:
            snapshot["liquidity"][key] = derived[key]
    if "WALCL" in fd:
        snapshot["liquidity"]["fed_total_assets_T"] = round(fd["WALCL"]["latest_value"] / 1e6, 2)
        snapshot["liquidity"]["fed_assets_change"] = fd["WALCL"].get("change_absolute")

    # Growth
    for sid, key in [("UNRATE", "unemployment"), ("ICSA", "initial_claims"), ("CCSA", "continuing_claims"),
                     ("UMCSENT", "consumer_sentiment"), ("USSLIND", "lei"), ("PAYEMS", "nonfarm_payrolls"),
                     ("INDPRO", "industrial_production"), ("RSAFS", "retail_sales")]:
        if sid in fd:
            snapshot["growth"][key] = {
                "value": fd[sid]["latest_value"], "date": fd[sid]["latest_date"],
                "change": fd[sid].get("change_absolute"), "yoy": fd[sid].get("yoy_change_percent"),
                "mom": fd[sid].get("mom_change_percent"), "percentile": fd[sid].get("percentile_rank")
            }

    # Inflation
    for sid, key in [("CPIAUCSL", "cpi"), ("CPILFESL", "core_cpi"), ("PCEPI", "pce"), ("PCEPILFE", "core_pce"), ("MICH", "michigan_expectations")]:
        if sid in fd:
            snapshot["inflation"][key] = {
                "value": fd[sid]["latest_value"], "date": fd[sid]["latest_date"],
                "yoy": fd[sid].get("yoy_change_percent"), "mom": fd[sid].get("mom_change_percent")
            }
    if "inflation_expectations" in derived:
        snapshot["inflation"]["expectations"] = derived["inflation_expectations"]

    # Markets
    for ticker, key in [("^GSPC", "sp500"), ("^NDX", "nasdaq100"), ("^RUT", "russell2000"),
                         ("^VIX", "vix"), ("GC=F", "gold"), ("CL=F", "oil_wti"), ("HG=F", "copper"),
                         ("EURUSD=X", "eurusd"), ("DX-Y.NYB", "dxy"), ("TLT", "tlt_20y_treasury"),
                         ("HYG", "hyg"), ("LQD", "lqd"), ("EEM", "eem"), ("EFA", "efa"),
                         ("JPY=X", "usdjpy"), ("CHF=X", "usdchf"), ("CNY=X", "usdcny")]:
        if ticker in yd:
            snapshot["markets"][key] = {
                "value": yd[ticker]["latest_value"],
                "date": yd[ticker]["latest_date"],
                "day_chg": yd[ticker].get("day_change_pct"),
                "week_chg": yd[ticker].get("week_change_pct"),
                "month_chg": yd[ticker].get("month_change_pct"),
                "three_month_chg": yd[ticker].get("three_month_change_pct"),
            }

    # Derived signals (the most useful section for skills)
    snapshot["derived_signals"] = derived

    return snapshot


def main():
    parser = argparse.ArgumentParser(description="Macro Advisor Data Collector")
    parser.add_argument("--fred-key", required=True, help="FRED API key")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--mode", choices=["weekly", "historical"], default="weekly",
                       help="weekly = 26-week lookback (default), historical = 5-year lookback")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lookback = 182 if args.mode == "weekly" else 1825  # 26 weeks or 5 years
    today = datetime.now().strftime("%Y-%m-%d")
    week = datetime.now().strftime("%Y-W%V")

    print(f"=== Macro Advisor Data Collection — {today} (mode: {args.mode}, lookback: {lookback} days) ===\n")

    # 1. FRED
    print("Fetching FRED data...")
    fred_data = fetch_fred_data(args.fred_key, lookback)
    if fred_data:
        n = len(fred_data["data"])
        e = len(fred_data["errors"])
        print(f"  FRED: {n} series fetched, {e} errors")
        if fred_data["errors"]:
            for err in fred_data["errors"][:5]:
                print(f"    - {err}")
            if e > 5:
                print(f"    ... and {e - 5} more")

    # 2. Yahoo Finance
    print("Fetching Yahoo Finance data...")
    yahoo_data = fetch_yahoo_data(lookback)
    if yahoo_data:
        n = len(yahoo_data["data"])
        e = len(yahoo_data["errors"])
        print(f"  Yahoo: {n} tickers fetched, {e} errors")
        if yahoo_data["errors"]:
            for err in yahoo_data["errors"][:5]:
                print(f"    - {err}")

    # 3. Derived metrics
    print("Computing derived metrics...")
    derived = compute_derived_metrics(fred_data, yahoo_data)
    print(f"  Derived: {len(derived)} metrics computed")

    # 4. Snapshot
    print("Building summary snapshot...")
    snapshot = build_summary_snapshot(fred_data, yahoo_data, derived)

    # 5. Save
    full_output = {
        "collection_date": today,
        "collection_week": week,
        "mode": args.mode,
        "lookback_days": lookback,
        "fred": fred_data,
        "yahoo": yahoo_data,
        "derived": derived,
        "snapshot": snapshot,
    }

    full_path = output_dir / f"{week}-data-full.json"
    snapshot_path = output_dir / f"{week}-snapshot.json"
    latest_full = output_dir / "latest-data-full.json"
    latest_snap = output_dir / "latest-snapshot.json"

    for path, data in [(full_path, full_output), (snapshot_path, snapshot),
                       (latest_full, full_output), (latest_snap, snapshot)]:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    # Stats
    total = (len(fred_data["data"]) if fred_data else 0) + (len(yahoo_data["data"]) if yahoo_data else 0)
    total_err = (len(fred_data["errors"]) if fred_data else 0) + (len(yahoo_data["errors"]) if yahoo_data else 0)

    print(f"\n=== Collection Complete ===")
    print(f"Series fetched: {total}")
    print(f"Errors: {total_err}")
    print(f"Derived metrics: {len(derived)}")
    print(f"Success rate: {total / max(total + total_err, 1) * 100:.1f}%")
    print(f"Files: {full_path.name}, {snapshot_path.name}")

    return 0 if total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
