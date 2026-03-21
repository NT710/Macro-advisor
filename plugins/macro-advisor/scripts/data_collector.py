#!/usr/bin/env python3
"""
Macro Advisor — Skill 0: Data Collection Script
Pulls structured data from FRED, Yahoo Finance, CFTC COT (via CFTC SODA API),
ECB Statistical Data Warehouse, and Eurostat.
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
import time
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

    # Manufacturing Employment (BLS, not ISM — ISM diffusion sub-indices are not on FRED)
    "MANEMP": ("All Employees: Manufacturing (thousands)", "employment", "monthly"),

    # Regional Fed Manufacturing Surveys (PMI proxies — diffusion indices, free on FRED)
    # These release mid-month BEFORE ISM, making them leading indicators for regime detection
    "GACDISA066MSFRBNY": ("NY Empire State Mfg Survey (Current General Business Conditions)", "regional_fed_mfg", "monthly"),
    "GACDFSA066MSFRBPHI": ("Philadelphia Fed Mfg Survey (Current Business Outlook)", "regional_fed_mfg", "monthly"),
    "BACTSAMFRBDAL": ("Dallas Fed Mfg Survey (Current General Business Activity)", "regional_fed_mfg", "monthly"),

    # Broad Activity Index
    "CFNAIMA3": ("Chicago Fed National Activity Index (3-month MA)", "activity_index", "monthly"),

    # Housing
    "HOUST": ("Housing Starts", "housing", "monthly"),
    "PERMIT": ("Building Permits", "housing", "monthly"),
    "EXHOSLUSM495S": ("Existing Home Sales", "housing", "monthly"),
    "CSUSHPISA": ("Case-Shiller Home Price Index", "housing", "monthly"),

    # Leading Indicators
    # NOTE: Conference Board LEI (USSLIND) removed — FRED series discontinued 2020, always returns empty.
    # Skill 3 falls back to web search for current TCB LEI release. CFNAI partially fills the role.

    # Money Markets
    "WRMFNS": ("Retail Money Market Funds (weekly, billions USD)", "money_markets", "weekly"),

    # Credit Conditions (private credit proxies)
    "DRTSCILM": ("Senior Loan Officer Survey - Tightening C&I Loans (Large/Mid)", "credit_conditions", "quarterly"),
    "BUSLOANS": ("Commercial & Industrial Loans Outstanding", "credit_conditions", "monthly"),
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

    # Volatility & Sentiment
    "^VIX": ("VIX", "volatility"),
    "^SKEW": ("CBOE Skew Index", "volatility"),
    # NOTE: ^CPCE (CBOE Equity Put/Call Ratio) removed — delisted on Yahoo, no alternative found.
    # VIX and CBOE Skew cover sentiment. Skill 5 uses these for sentiment assessment.

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

    # Leveraged Loan / Private Credit Proxy
    "BKLN": ("Invesco Senior Loan ETF", "leveraged_loans"),
}

# ---------------------------------------------------------------------------
# CFTC COT CONTRACTS (via CFTC SODA API — free, no API key)
# ---------------------------------------------------------------------------
# Two datasets on publicreporting.cftc.gov:
#   TFF (Traders in Financial Futures): gpe5-46if — equities, rates, FX
#   Disaggregated Futures Only: 72hh-3qpy — commodities
#
# TFF trader categories: asset_mgr (Asset Manager), lev_money (Leveraged Money)
# Disaggregated trader category: m_money (Money Manager)
# Net speculative = Long positions - Short positions
#
# Format: (name, category, dataset_id, contract_market_code, long_col, short_col)
COT_CONTRACTS = {
    # Equities — Asset Manager positions (TFF)
    "sp500": ("S&P 500 E-mini", "equities", "gpe5-46if", "13874A",
              "asset_mgr_positions_long", "asset_mgr_positions_short"),
    "nasdaq100": ("Nasdaq-100", "equities", "gpe5-46if", "20974+",
                  "asset_mgr_positions_long", "asset_mgr_positions_short"),
    # Rates — Leveraged Money positions (TFF)
    "10y_treasury": ("10-Year Treasury Note", "rates", "gpe5-46if", "043602",
                     "lev_money_positions_long", "lev_money_positions_short"),
    "2y_treasury": ("2-Year Treasury Note", "rates", "gpe5-46if", "042601",
                    "lev_money_positions_long", "lev_money_positions_short"),
    # FX — Leveraged Money positions (TFF)
    "eur_usd": ("EUR/USD", "fx", "gpe5-46if", "099741",
                "lev_money_positions_long", "lev_money_positions_short"),
    "jpy_usd": ("JPY/USD", "fx", "gpe5-46if", "097741",
                "lev_money_positions_long", "lev_money_positions_short"),
    # Commodities — Money Manager positions (Disaggregated)
    "gold": ("Gold", "commodities", "72hh-3qpy", "088691",
             "m_money_positions_long_all", "m_money_positions_short_all"),
    "crude_oil_wti": ("Crude Oil WTI", "commodities", "72hh-3qpy", "067651",
                      "m_money_positions_long_all", "m_money_positions_short_all"),
    "copper": ("Copper", "commodities", "72hh-3qpy", "085692",
               "m_money_positions_long_all", "m_money_positions_short_all"),
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
            # Retry with backoff on rate limit (FRED: 120 req/min)
            data = None
            for attempt in range(3):
                try:
                    data = fred.get_series(series_id, observation_start=fetch_start, observation_end=end_date)
                    break
                except Exception as e:
                    if "429" in str(e) or "rate" in str(e).lower() or "limit" in str(e).lower():
                        wait = 2 ** attempt  # 1s, 2s, 4s
                        print(f"    Rate limited on {series_id}, retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        raise
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


def fetch_cot_data(lookback_weeks=52):
    """Fetch CFTC Commitments of Traders data via CFTC SODA API (free, no key).

    Two datasets:
      - TFF (Traders in Financial Futures) for equities, rates, FX
      - Disaggregated Futures Only for commodities
    Extracts net speculative positions and computes historical percentiles.
    """
    import urllib.request
    import urllib.parse
    import urllib.error

    cftc_base = "https://publicreporting.cftc.gov/resource"
    results = {}
    errors = []

    for key, (name, category, dataset_id, contract_code, long_col, short_col) in COT_CONTRACTS.items():
        url_base = f"{cftc_base}/{dataset_id}.json"
        params = urllib.parse.urlencode({
            "$limit": lookback_weeks,
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$where": f"cftc_contract_market_code='{contract_code}'"
        })
        url = f"{url_base}?{params}"

        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "MacroAdvisor/1.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data_rows = json.loads(resp.read().decode("utf-8"))

                if not data_rows:
                    errors.append(f"{name} ({contract_code}): no data returned")
                    break

                # Compute net speculative for each week (data is newest-first)
                net_positions = []
                history = []
                for row in data_rows:
                    try:
                        long_val = float(row.get(long_col, 0))
                        short_val = float(row.get(short_col, 0))
                        net = long_val - short_val
                        date_str = row.get("report_date_as_yyyy_mm_dd", "")[:10]
                        net_positions.append(net)
                        history.append({
                            "date": date_str,
                            "net_speculative": round(net, 0),
                            "long": round(long_val, 0),
                            "short": round(short_val, 0),
                        })
                    except (TypeError, ValueError):
                        continue

                if not net_positions:
                    errors.append(f"{name} ({contract_code}): could not parse position data")
                    break

                latest_net = net_positions[0]
                latest_date = history[0]["date"]

                # Prior week
                prior_net = net_positions[1] if len(net_positions) > 1 else None
                weekly_change = round(latest_net - prior_net, 0) if prior_net is not None else None

                # Historical percentile
                percentile = None
                if len(net_positions) >= 10:
                    below = sum(1 for n in net_positions if n < latest_net)
                    percentile = round(below / len(net_positions) * 100, 1)

                # Extreme detection
                extreme = None
                if percentile is not None:
                    if percentile >= 90:
                        extreme = "extreme long"
                    elif percentile <= 10:
                        extreme = "extreme short"
                    elif percentile >= 80:
                        extreme = "crowded long"
                    elif percentile <= 20:
                        extreme = "crowded short"

                # Direction of change
                direction = None
                if weekly_change is not None:
                    if latest_net > 0 and weekly_change > 0:
                        direction = "building long"
                    elif latest_net > 0 and weekly_change < 0:
                        direction = "unwinding long"
                    elif latest_net < 0 and weekly_change < 0:
                        direction = "building short"
                    elif latest_net < 0 and weekly_change > 0:
                        direction = "unwinding short"
                    else:
                        direction = "flat"

                # Determine trader type label from column name
                if "asset_mgr" in long_col:
                    trader_type = "Asset Manager"
                elif "lev_money" in long_col:
                    trader_type = "Leveraged Money"
                else:
                    trader_type = "Money Manager"

                results[key] = {
                    "name": name,
                    "category": category,
                    "trader_type": trader_type,
                    "latest_date": latest_date,
                    "net_speculative": round(latest_net, 0),
                    "prior_net": round(prior_net, 0) if prior_net is not None else None,
                    "weekly_change": weekly_change,
                    "percentile_52w": percentile,
                    "extreme": extreme,
                    "direction": direction,
                    "weeks_of_data": len(net_positions),
                    "history": history[:52],
                }
                break  # success

            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 2:
                    wait = 2 ** attempt
                    print(f"    Rate limited on {name}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    errors.append(f"{name} ({contract_code}): HTTP {e.code} — {str(e)[:80]}")
                    break
            except Exception as e:
                if attempt < 2:
                    wait = 2 ** attempt
                    print(f"    Error on {name}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    errors.append(f"{name} ({contract_code}): {str(e)[:100]}")
                    break

    return {"data": results, "errors": errors}


# ---------------------------------------------------------------------------
# ECB STATISTICAL DATA WAREHOUSE (SDW) — Free, no API key
# ---------------------------------------------------------------------------

ECB_SERIES = {
    # Eurozone M3 outstanding amounts (EUR millions, monthly)
    "m3_outstanding": {
        "key": "BSI/M.U2.Y.V.M30.X.1.U2.2300.Z01.E",
        "name": "Eurozone M3 Outstanding Amounts",
        "frequency": "monthly",
        "observations": 13,  # 13 months for YoY
    },
    # ECB Total Assets (weekly, EUR millions)
    "ecb_total_assets": {
        "key": "ILM/W.U2.C.T000000.Z5.Z01",
        "name": "ECB Consolidated Balance Sheet — Total Assets",
        "frequency": "weekly",
        "observations": 26,  # ~6 months
    },
}


def fetch_ecb_data():
    """Fetch data from ECB Statistical Data Warehouse (free, no key)."""
    import requests

    results = {}
    errors = []
    base_url = "https://data-api.ecb.europa.eu/service/data"

    for series_id, config in ECB_SERIES.items():
        try:
            url = f"{base_url}/{config['key']}"
            r = requests.get(
                url,
                headers={"Accept": "application/json"},
                params={"lastNObservations": config["observations"]},
                timeout=15,
            )

            if r.status_code != 200:
                errors.append(f"{series_id}: HTTP {r.status_code}")
                continue

            data = r.json()
            datasets = data.get("dataSets", [])
            if not datasets or not datasets[0].get("series"):
                errors.append(f"{series_id}: no data in response")
                continue

            # Extract time dimension
            dims = data.get("structure", {}).get("dimensions", {}).get("observation", [])
            time_dim = None
            for d in dims:
                if d.get("id") == "TIME_PERIOD":
                    time_dim = d.get("values", [])

            # Extract observations
            series_data = list(datasets[0]["series"].values())[0]
            obs = series_data.get("observations", {})

            history = []
            for obs_key, obs_val in sorted(obs.items(), key=lambda x: int(x[0])):
                idx = int(obs_key)
                period = time_dim[idx]["id"] if time_dim and idx < len(time_dim) else obs_key
                value = obs_val[0]
                if value is not None:
                    history.append({"date": period, "value": round(float(value), 2)})

            if not history:
                errors.append(f"{series_id}: all observations null")
                continue

            latest = history[-1]

            # Compute YoY for monthly series
            yoy = None
            if config["frequency"] == "monthly" and len(history) >= 13:
                current = latest["value"]
                year_ago = history[-13]["value"]
                if year_ago and year_ago != 0:
                    yoy = round(((current - year_ago) / year_ago) * 100, 2)

            # Compute WoW change for weekly series
            wow_change = None
            if config["frequency"] == "weekly" and len(history) >= 2:
                wow_change = round(history[-1]["value"] - history[-2]["value"], 2)

            results[series_id] = {
                "name": config["name"],
                "frequency": config["frequency"],
                "latest_value": latest["value"],
                "latest_date": latest["date"],
                "yoy_pct": yoy,
                "wow_change": wow_change,
                "observation_count": len(history),
                "history": history,
            }

        except Exception as e:
            errors.append(f"{series_id}: {str(e)[:100]}")

    return {"data": results, "errors": errors}


# ---------------------------------------------------------------------------
# EUROSTAT — Free, no API key
# ---------------------------------------------------------------------------

EUROSTAT_SERIES = {
    # HICP headline (annual rate of change, Euro Area, all items)
    "hicp_headline": {
        "dataset": "prc_hicp_manr",
        "params": {"geo": "EA", "coicop": "CP00", "freq": "M"},
        "name": "Eurozone HICP — All Items (YoY %)",
        "last_periods": 6,
    },
    # HICP core (ex energy, food, alcohol, tobacco)
    "hicp_core": {
        "dataset": "prc_hicp_manr",
        "params": {"geo": "EA", "coicop": "TOT_X_NRG_FOOD", "freq": "M"},
        "name": "Eurozone HICP — Core ex Energy & Food (YoY %)",
        "last_periods": 6,
    },
}


def fetch_eurostat_data():
    """Fetch data from Eurostat API (free, no key)."""
    import requests

    results = {}
    errors = []
    base_url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

    for series_id, config in EUROSTAT_SERIES.items():
        try:
            url = f"{base_url}/{config['dataset']}"
            params = dict(config["params"])
            params["lastTimePeriod"] = config["last_periods"]

            r = requests.get(url, params=params, timeout=15)

            if r.status_code != 200:
                errors.append(f"{series_id}: HTTP {r.status_code}")
                continue

            data = r.json()
            vals = data.get("value", {})
            dims = data.get("dimension", {})
            time_dim = dims.get("time", {}).get("category", {}).get("index", {})

            # Build time-sorted history
            history = []
            for period, idx in sorted(time_dim.items(), key=lambda x: x[1]):
                val = vals.get(str(idx))
                if val is not None:
                    history.append({"date": period, "value": round(float(val), 2)})

            if not history:
                errors.append(f"{series_id}: no data points")
                continue

            latest = history[-1]

            # Compute direction (is inflation rising or falling?)
            direction = None
            if len(history) >= 2:
                prev = history[-2]["value"]
                curr = latest["value"]
                if curr > prev:
                    direction = "rising"
                elif curr < prev:
                    direction = "falling"
                else:
                    direction = "stable"

            results[series_id] = {
                "name": config["name"],
                "latest_value": latest["value"],
                "latest_date": latest["date"],
                "direction": direction,
                "prior_value": history[-2]["value"] if len(history) >= 2 else None,
                "observation_count": len(history),
                "history": history,
            }

        except Exception as e:
            errors.append(f"{series_id}: {str(e)[:100]}")

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

    # Private credit stress proxy cluster
    # These are PROXIES — they observe adjacent markets, not private credit directly.
    # The $1.7T private credit market has no public mark-to-market. These series
    # capture credit conditions that overlap with private credit borrower profiles.
    # Interpretation must always acknowledge the proxy gap.
    pc_proxy = {}
    if "DRTSCILM" in fd:
        # Senior Loan Officer Survey: % of banks tightening C&I loan standards
        # Positive = tightening, Negative = easing. Quarterly, so often stale.
        sloos_val = fd["DRTSCILM"]["latest_value"]
        pc_proxy["sloos_tightening_pct"] = sloos_val
        pc_proxy["sloos_date"] = fd["DRTSCILM"]["latest_date"]
        pc_proxy["sloos_signal"] = (
            "severe tightening" if sloos_val > 40 else
            "tightening" if sloos_val > 10 else
            "neutral" if sloos_val > -10 else
            "easing" if sloos_val > -30 else
            "strong easing"
        )
    if "BUSLOANS" in fd:
        # C&I loans outstanding — growth/contraction indicates bank lending appetite
        ci_yoy = fd["BUSLOANS"].get("yoy_change_percent")
        pc_proxy["ci_loans_level_B"] = round(fd["BUSLOANS"]["latest_value"] / 1000, 1) if fd["BUSLOANS"]["latest_value"] else None
        pc_proxy["ci_loans_yoy_pct"] = ci_yoy
        pc_proxy["ci_loans_date"] = fd["BUSLOANS"]["latest_date"]
        if ci_yoy is not None:
            # Thresholds calibrated symmetrically around nominal GDP growth (~4-5%).
            # Contraction is unambiguous stress. Low growth may be normal in a slow economy.
            pc_proxy["ci_loans_signal"] = (
                "contracting" if ci_yoy < -0.5 else
                "flat" if ci_yoy < 1.5 else
                "moderate growth" if ci_yoy < 5 else
                "rapid growth"
            )
    if "BKLN" in yd:
        # Leveraged loan ETF — price declines signal stress in the leveraged loan market,
        # which shares the same borrower universe as private credit
        bkln = yd["BKLN"]
        pc_proxy["leveraged_loan_etf"] = bkln["latest_value"]
        pc_proxy["leveraged_loan_week_chg"] = bkln.get("week_change_pct")
        pc_proxy["leveraged_loan_month_chg"] = bkln.get("month_change_pct")
        pc_proxy["leveraged_loan_date"] = bkln["latest_date"]
        month_chg = bkln.get("month_change_pct") or 0
        # Symmetric thresholds: same sensitivity for stress and easing
        pc_proxy["leveraged_loan_signal"] = (
            "stress" if month_chg < -1.5 else
            "softening" if month_chg < -0.5 else
            "stable" if abs(month_chg) <= 0.5 else
            "firming" if month_chg < 1.5 else
            "risk-on"
        )
    # HY OAS from the existing credit spreads (cross-reference, not double count)
    if "BAMLH0A0HYM2" in fd:
        pc_proxy["hy_oas_cross_ref"] = fd["BAMLH0A0HYM2"]["latest_value"]

    if pc_proxy:
        # Composite assessment — require convergence, not any single indicator
        stress_signals = 0
        easing_signals = 0
        total_signals = 0
        if "sloos_signal" in pc_proxy:
            total_signals += 1
            if pc_proxy["sloos_signal"] in ("tightening", "severe tightening"):
                stress_signals += 1
            elif pc_proxy["sloos_signal"] in ("easing", "strong easing"):
                easing_signals += 1
        if "ci_loans_signal" in pc_proxy:
            total_signals += 1
            if pc_proxy["ci_loans_signal"] == "contracting":
                stress_signals += 1
            elif pc_proxy["ci_loans_signal"] in ("moderate growth", "rapid growth"):
                easing_signals += 1
            # "flat" is neutral — contributes to total but doesn't vote either way
        if "leveraged_loan_signal" in pc_proxy:
            total_signals += 1
            if pc_proxy["leveraged_loan_signal"] == "stress":
                stress_signals += 1
            elif pc_proxy["leveraged_loan_signal"] in ("firming", "risk-on"):
                easing_signals += 1
            # "stable" and "softening" are neutral — contribute to total but don't vote
        if "hy_oas_cross_ref" in pc_proxy:
            total_signals += 1
            hy = pc_proxy["hy_oas_cross_ref"]
            if hy > 5.0:
                stress_signals += 1
            elif hy < 3.5:
                easing_signals += 1

        # Require at least 2 agreeing proxies AND no opposing majority.
        # "Inconclusive" means proxies actively disagree, not that some are silent.
        # If 2+ proxies agree and 0 disagree, that's a valid directional call.
        if stress_signals >= 2 and stress_signals > easing_signals:
            composite = "stress — majority of proxies converging"
        elif easing_signals >= 2 and easing_signals > stress_signals:
            composite = "benign — majority of proxies converging"
        elif total_signals <= 1:
            composite = "insufficient data — need at least 2 proxies for directional call"
        elif stress_signals > 0 and easing_signals > 0 and stress_signals == easing_signals:
            composite = "inconclusive — proxies actively diverging (stress and easing signals present)"
        else:
            composite = "inconclusive — no clear signal"

        pc_proxy["composite_signal"] = composite
        pc_proxy["stress_count"] = stress_signals
        pc_proxy["easing_count"] = easing_signals
        pc_proxy["total_proxies"] = total_signals
        pc_proxy["_disclaimer"] = (
            "These are PROXIES for private credit conditions, not direct observations. "
            "Private credit has no public mark-to-market. Bank lending surveys, C&I loan "
            "volumes, and leveraged loan ETF prices capture adjacent markets that share "
            "borrower profiles with private credit — but they can diverge. Treat convergence "
            "as informative and divergence as genuinely uncertain, not as a sign one proxy is 'right'."
        )
        derived["credit_stress_private_proxy"] = pc_proxy

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


def build_summary_snapshot(fred_data, yahoo_data, derived, cot_data=None, ecb_data=None, eurostat_data=None):
    """Build a concise summary for skill consumption."""
    fd = fred_data.get("data", {}) if fred_data else {}
    yd = yahoo_data.get("data", {}) if yahoo_data else {}
    cd = cot_data.get("data", {}) if cot_data else {}

    ed = ecb_data.get("data", {}) if ecb_data else {}
    esd = eurostat_data.get("data", {}) if eurostat_data else {}

    snapshot = {
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "rates": {},
        "credit": {},
        "liquidity": {},
        "growth": {},
        "inflation": {},
        "markets": {},
        "positioning": {},
        "regional_fed_mfg": {},
        "eurozone": {},
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
    if "credit_stress_private_proxy" in derived:
        snapshot["credit"]["private_credit_proxy"] = derived["credit_stress_private_proxy"]

    # Liquidity
    for key in ["m2_growth", "liquidity_plumbing", "financial_conditions"]:
        if key in derived:
            snapshot["liquidity"][key] = derived[key]
    if "WALCL" in fd:
        snapshot["liquidity"]["fed_total_assets_T"] = round(fd["WALCL"]["latest_value"] / 1e6, 2)
        snapshot["liquidity"]["fed_assets_change"] = fd["WALCL"].get("change_absolute")

    # Growth
    for sid, key in [("UNRATE", "unemployment"), ("ICSA", "initial_claims"), ("CCSA", "continuing_claims"),
                     ("UMCSENT", "consumer_sentiment"), ("PAYEMS", "nonfarm_payrolls"),
                     ("MANEMP", "manufacturing_employment"),
                     ("INDPRO", "industrial_production"), ("RSAFS", "retail_sales")]:
        if sid in fd:
            snapshot["growth"][key] = {
                "value": fd[sid]["latest_value"], "date": fd[sid]["latest_date"],
                "change": fd[sid].get("change_absolute"), "yoy": fd[sid].get("yoy_change_percent"),
                "mom": fd[sid].get("mom_change_percent"), "percentile": fd[sid].get("percentile_rank")
            }

    # Regional Fed Manufacturing Surveys (PMI proxies)
    # Diffusion indices: >0 = expansion, <0 = contraction, 0 = neutral (analogous to ISM >50 / <50)
    for sid, key in [("GACDISA066MSFRBNY", "empire_state"), ("GACDFSA066MSFRBPHI", "philly_fed"),
                     ("BACTSAMFRBDAL", "dallas_fed")]:
        if sid in fd:
            val = fd[sid]["latest_value"]
            signal = "expansion" if val > 0 else ("contraction" if val < 0 else "neutral")
            snapshot["regional_fed_mfg"][key] = {
                "value": val, "date": fd[sid]["latest_date"],
                "change": fd[sid].get("change_absolute"), "mom": fd[sid].get("mom_change_percent"),
                "signal": signal,
            }

    # Composite: count + average for magnitude awareness
    fed_surveys = {k: v for k, v in snapshot["regional_fed_mfg"].items() if k != "composite"}
    if fed_surveys:
        values = [v["value"] for v in fed_surveys.values()]
        expanding = sum(1 for v in values if v > 0)
        contracting = sum(1 for v in values if v < 0)
        total = len(fed_surveys)
        avg = round(sum(values) / total, 2)

        # Consensus from vote count
        if expanding > contracting:
            consensus = "expansion"
        elif contracting > expanding:
            consensus = "contraction"
        else:
            consensus = "mixed"

        # Conviction: is the average far from zero, or marginal?
        # Thresholds based on historical regional Fed ranges (~-30 to +40)
        if abs(avg) < 2:
            conviction = "marginal"
        elif abs(avg) < 10:
            conviction = "moderate"
        else:
            conviction = "strong"

        snapshot["regional_fed_mfg"]["composite"] = {
            "expanding_count": expanding,
            "contracting_count": contracting,
            "total_count": total,
            "average": avg,
            "consensus": consensus,
            "conviction": conviction,
        }

    # Chicago Fed National Activity Index
    if "CFNAIMA3" in fd:
        cfnai_val = fd["CFNAIMA3"]["latest_value"]
        cfnai_signal = "above_trend" if cfnai_val > 0 else ("below_trend" if cfnai_val < 0 else "at_trend")
        snapshot["growth"]["cfnai_3mo"] = {
            "value": cfnai_val, "date": fd["CFNAIMA3"]["latest_date"],
            "signal": cfnai_signal,
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
                         ("JPY=X", "usdjpy"), ("CHF=X", "usdchf"), ("CNY=X", "usdcny"),
                         ("BKLN", "bkln_leveraged_loans")]:
        if ticker in yd:
            snapshot["markets"][key] = {
                "value": yd[ticker]["latest_value"],
                "date": yd[ticker]["latest_date"],
                "day_chg": yd[ticker].get("day_change_pct"),
                "week_chg": yd[ticker].get("week_change_pct"),
                "month_chg": yd[ticker].get("month_change_pct"),
                "three_month_chg": yd[ticker].get("three_month_change_pct"),
            }

    # COT Positioning (from CFTC SODA API)
    if cd:
        for key, contract in cd.items():
            snapshot["positioning"][key] = {
                "name": contract["name"],
                "category": contract["category"],
                "trader_type": contract["trader_type"],
                "net_speculative": contract["net_speculative"],
                "prior_net": contract.get("prior_net"),
                "weekly_change": contract.get("weekly_change"),
                "percentile_52w": contract.get("percentile_52w"),
                "extreme": contract.get("extreme"),
                "direction": contract.get("direction"),
                "date": contract["latest_date"],
            }

    # Eurozone data (ECB SDW + Eurostat — no API key required)
    if "m3_outstanding" in ed:
        m3 = ed["m3_outstanding"]
        snapshot["eurozone"]["m3"] = {
            "value_eur_millions": m3["latest_value"],
            "date": m3["latest_date"],
            "yoy_pct": m3.get("yoy_pct"),
        }
        if m3.get("yoy_pct") is not None:
            snapshot["eurozone"]["m3_yoy"] = m3["yoy_pct"]

    if "ecb_total_assets" in ed:
        ecb = ed["ecb_total_assets"]
        snapshot["eurozone"]["ecb_balance_sheet"] = {
            "total_assets_eur_millions": ecb["latest_value"],
            "date": ecb["latest_date"],
            "wow_change_eur_millions": ecb.get("wow_change"),
        }

    if "hicp_headline" in esd:
        hicp = esd["hicp_headline"]
        snapshot["eurozone"]["hicp_headline"] = {
            "value": hicp["latest_value"],
            "date": hicp["latest_date"],
            "direction": hicp.get("direction"),
            "prior_value": hicp.get("prior_value"),
        }

    if "hicp_core" in esd:
        core = esd["hicp_core"]
        snapshot["eurozone"]["hicp_core"] = {
            "value": core["latest_value"],
            "date": core["latest_date"],
            "direction": core.get("direction"),
            "prior_value": core.get("prior_value"),
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
    parser.add_argument("--series", default=None,
                       help="Comma-separated FRED series IDs for targeted pull (e.g., 'FYFSD,FGEXPND,A091RC1Q027SBEA'). "
                            "When specified, only these series are fetched (no Yahoo, no derived metrics). "
                            "Used by Skill 11 for on-demand research data.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lookback = 182 if args.mode == "weekly" else 1825  # 26 weeks or 5 years
    today = datetime.now().strftime("%Y-%m-%d")
    week = datetime.now().strftime("%Y-W%V")

    # Targeted series pull (used by Skill 11 for on-demand research)
    if args.series:
        series_ids = [s.strip() for s in args.series.split(",") if s.strip()]
        print(f"=== Targeted FRED Pull — {today} ({len(series_ids)} series, lookback: {lookback} days) ===\n")

        try:
            from fredapi import Fred
        except ImportError:
            print("ERROR: fredapi not installed. Run: pip install fredapi")
            return 1

        fred = Fred(args.fred_key)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback)

        results = {}
        errors = []
        for sid in series_ids:
            for attempt in range(3):
                try:
                    data = fred.get_series(sid, observation_start=start_date, observation_end=end_date)
                    if data is not None and len(data.dropna()) > 0:
                        data = data.dropna()
                        history = [{"date": ts.strftime("%Y-%m-%d"), "value": round(float(val), 4)}
                                   for ts, val in data.items()]
                        results[sid] = {
                            "series_id": sid,
                            "latest_value": round(float(data.iloc[-1]), 4),
                            "latest_date": data.index[-1].strftime("%Y-%m-%d"),
                            "observation_count": len(data),
                            "history": history,
                        }
                    else:
                        errors.append(f"{sid}: empty or no data")
                    break
                except Exception as e:
                    if ("429" in str(e) or "rate" in str(e).lower() or "limit" in str(e).lower()) and attempt < 2:
                        wait = 2 ** attempt
                        print(f"  Rate limited on {sid}, retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        errors.append(f"{sid}: {str(e)[:100]}")
                        break

        output = {
            "collection_date": today,
            "mode": "targeted",
            "series_requested": series_ids,
            "lookback_days": lookback,
            "data": results,
            "errors": errors,
        }

        out_path = output_dir / f"research-{today}-targeted.json"
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2, default=str)

        print(f"Fetched: {len(results)}/{len(series_ids)} series")
        if errors:
            for err in errors:
                print(f"  Error: {err}")
        print(f"Saved to: {out_path.name}")
        return 0 if results else 1

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

    # 3. CFTC COT (via CFTC SODA API — free, no key needed)
    cot_weeks = 52 if args.mode == "weekly" else 260  # 1 year or 5 years
    print("Fetching CFTC COT data (publicreporting.cftc.gov)...")
    cot_data = fetch_cot_data(cot_weeks)
    if cot_data:
        n = len(cot_data["data"])
        e = len(cot_data["errors"])
        print(f"  COT: {n} contracts fetched, {e} errors")
        if cot_data["errors"]:
            for err in cot_data["errors"][:5]:
                print(f"    - {err}")

    # 4. ECB Statistical Data Warehouse (free, no key)
    print("Fetching ECB data (data-api.ecb.europa.eu)...")
    ecb_data = fetch_ecb_data()
    if ecb_data:
        n = len(ecb_data["data"])
        e = len(ecb_data["errors"])
        print(f"  ECB: {n} series fetched, {e} errors")
        if ecb_data["errors"]:
            for err in ecb_data["errors"]:
                print(f"    - {err}")

    # 5. Eurostat (free, no key)
    print("Fetching Eurostat data (ec.europa.eu/eurostat)...")
    eurostat_data = fetch_eurostat_data()
    if eurostat_data:
        n = len(eurostat_data["data"])
        e = len(eurostat_data["errors"])
        print(f"  Eurostat: {n} series fetched, {e} errors")
        if eurostat_data["errors"]:
            for err in eurostat_data["errors"]:
                print(f"    - {err}")

    # 6. Derived metrics
    print("Computing derived metrics...")
    derived = compute_derived_metrics(fred_data, yahoo_data)
    print(f"  Derived: {len(derived)} metrics computed")

    # 7. Snapshot
    print("Building summary snapshot...")
    snapshot = build_summary_snapshot(fred_data, yahoo_data, derived, cot_data, ecb_data, eurostat_data)

    # 6. Save
    full_output = {
        "collection_date": today,
        "collection_week": week,
        "mode": args.mode,
        "lookback_days": lookback,
        "fred": fred_data,
        "yahoo": yahoo_data,
        "cot": cot_data,
        "ecb": ecb_data,
        "eurostat": eurostat_data,
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
    total_fred = len(fred_data["data"]) if fred_data else 0
    total_yahoo = len(yahoo_data["data"]) if yahoo_data else 0
    total_cot = len(cot_data["data"]) if cot_data else 0
    total_ecb = len(ecb_data["data"]) if ecb_data else 0
    total_eurostat = len(eurostat_data["data"]) if eurostat_data else 0
    total = total_fred + total_yahoo + total_cot + total_ecb + total_eurostat
    total_err = sum(len(d.get("errors", [])) for d in [fred_data, yahoo_data, cot_data, ecb_data, eurostat_data] if d)

    print(f"\n=== Collection Complete ===")
    print(f"Series fetched: {total} (FRED: {total_fred}, Yahoo: {total_yahoo}, COT: {total_cot}, ECB: {total_ecb}, Eurostat: {total_eurostat})")
    print(f"Errors: {total_err}")
    print(f"Derived metrics: {len(derived)}")
    print(f"Success rate: {total / max(total + total_err, 1) * 100:.1f}%")
    print(f"Files: {full_path.name}, {snapshot_path.name}")

    return 0 if total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
