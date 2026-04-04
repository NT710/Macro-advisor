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


from run_log_utils import log_event as _log_event

# ---------------------------------------------------------------------------
# REGIME CLASSIFICATION SERIES — extended history for regime_classifier.py
# These 9 series get 5 years of monthly regime_history in the output JSON,
# regardless of the lookback_days parameter. This feeds the deterministic
# regime classifier (36-month rolling medians need 3+ years of data).
# ---------------------------------------------------------------------------
REGIME_SERIES = {
    "INDPRO", "UNRATE", "RSAFS", "PAYEMS",  # growth axis
    "CPIAUCSL", "CPILFESL",                  # inflation axis
    "M2SL", "NFCI", "WALCL",                 # liquidity axis
}

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

    # Inventory-to-Sales Ratios (supply chain tightness for Skill 13)
    "RETAILIRSA": ("Retail Inventories/Sales Ratio", "inventories", "monthly"),
    "MNFCTRIRSA": ("Manufacturing Inventories/Sales Ratio", "inventories", "monthly"),
    "WHLSLRIRSA": ("Wholesale Inventories/Sales Ratio", "inventories", "monthly"),
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

    # Commodities — Front Month
    "GC=F": ("Gold Futures", "commodities"),
    "CL=F": ("Crude Oil WTI Futures", "commodities"),
    "HG=F": ("Copper Futures", "commodities"),
    "SI=F": ("Silver Futures", "commodities"),
    "NG=F": ("Natural Gas Futures", "commodities"),
    "BZ=F": ("Brent Crude Futures", "commodities"),

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
    "BIZD": ("VanEck BDC Income ETF", "private_credit_bdc"),
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


# ---------------------------------------------------------------------------
# PLAUSIBLE RANGE VALIDATION
# ---------------------------------------------------------------------------
# Guards against garbage data propagating through the system. If a source
# returns a value outside these bounds, it's flagged as anomalous — not
# silently dropped, not silently accepted. Downstream skills see the flag
# and can decide how to handle it.
#
# Ranges are deliberately wide: they catch glitches (VIX = 500, S&P = 0,
# negative unemployment) without filtering legitimate extremes. Every bound
# is set wider than any historically observed value for that series.
#
# Format: "series_key": (min, max, description)
#   - min/max are inclusive. None means unbounded on that side.
#   - description is for the anomaly report — human-readable context.
#
# These ranges should be reviewed annually or after major market dislocations.
# ---------------------------------------------------------------------------

PLAUSIBLE_RANGES = {
    # --- FRED: Rates (percentages) ---
    # Fed funds has been 0-20% historically (Volcker peak ~20%, ZIRP floor 0)
    "DFF":    (-0.5, 25.0, "Fed funds rate"),
    "DGS2":   (-1.0, 20.0, "2Y Treasury yield"),
    "DGS5":   (-1.0, 20.0, "5Y Treasury yield"),
    "DGS10":  (-1.0, 20.0, "10Y Treasury yield"),
    "DGS30":  (-1.0, 20.0, "30Y Treasury yield"),
    "T10Y2Y": (-5.0, 5.0,  "10Y-2Y spread"),
    "T10Y3M": (-5.0, 5.0,  "10Y-3M spread"),

    # --- FRED: Credit spreads (percentage points, not bps) ---
    # HY OAS peaked ~20% in 2008. IG peaked ~6%.
    "BAMLH0A0HYM2":   (0.0, 25.0, "HY OAS"),
    "BAMLC0A0CM":      (0.0, 10.0, "IG OAS"),
    "BAMLH0A0HYM2EY":  (0.0, 30.0, "HY effective yield"),

    # --- FRED: Financial conditions (index values) ---
    # NFCI centered at 0, historically -1 to +4 (GFC peak)
    "NFCI":     (-2.0, 6.0,  "Chicago Fed NFCI"),
    "ANFCI":    (-2.0, 6.0,  "Adjusted NFCI"),
    "STLFSI4":  (-3.0, 10.0, "St. Louis financial stress"),

    # --- FRED: Inflation (index levels or percentages) ---
    "T5YIE":   (-3.0, 8.0,  "5Y breakeven inflation"),
    "T10YIE":  (-2.0, 6.0,  "10Y breakeven inflation"),
    "MICH":    (0.0, 20.0,  "Michigan inflation expectations"),

    # --- FRED: Employment ---
    "UNRATE":  (0.0, 30.0,  "Unemployment rate"),         # US peak ~25% in Depression, ~15% COVID
    "ICSA":    (0.0, 7000.0, "Initial claims (thousands)"),  # COVID peak ~6.9M
    "CCSA":    (0.0, 25000.0, "Continuing claims (thousands)"),  # COVID peak ~23M

    # --- FRED: Growth indicators ---
    "UMCSENT": (0.0, 120.0, "Michigan consumer sentiment"),  # historical range ~50-112
    "RSAFS":   (100000.0, 1000000.0, "Retail sales (millions)"),  # ~$500B-700B/mo range

    # --- FRED: Fed balance sheet (millions USD) ---
    "WALCL":    (500000.0, 15000000.0, "Fed total assets"),     # $0.5T to $15T
    "WTREGEN":  (0.0, 2000000.0, "Treasury General Account"),  # max ~$1.8T
    "RRPONTSYD": (0.0, 3000000.0, "Reverse repo facility"),    # max ~$2.5T
    "WRESBAL":  (0.0, 5000000.0, "Reserve balances"),

    # --- FRED: Money supply (billions USD) ---
    "M2SL":    (1000.0, 30000.0, "M2 money stock (monthly, billions)"),
    "WM2NS":   (1000.0, 30000.0, "M2 money stock (weekly, billions)"),

    # --- FRED: Regional Fed manufacturing surveys (diffusion indices) ---
    # These are diffusion indices, historically about -50 to +50
    "GACDISA066MSFRBNY":  (-80.0, 80.0, "Empire State mfg survey"),
    "GACDFSA066MSFRBPHI": (-80.0, 80.0, "Philly Fed mfg survey"),
    "BACTSAMFRBDAL":      (-80.0, 80.0, "Dallas Fed mfg survey"),

    # --- FRED: Activity index ---
    "CFNAIMA3": (-5.0, 3.0, "Chicago Fed national activity 3mo MA"),

    # --- Yahoo: Equity indices ---
    "^GSPC":    (500.0, 15000.0,  "S&P 500"),      # currently ~5000-6000, wide bounds
    "^NDX":     (1000.0, 40000.0, "Nasdaq 100"),
    "^RUT":     (300.0, 5000.0,   "Russell 2000"),
    "^STOXX50E": (500.0, 8000.0,  "Euro Stoxx 50"),

    # --- Yahoo: Volatility ---
    "^VIX":     (5.0, 100.0, "VIX"),               # VIX peaked ~82 in March 2020
    "^SKEW":    (90.0, 175.0, "CBOE Skew Index"),   # historical range ~100-160

    # --- Yahoo: Commodities ---
    "GC=F":     (500.0, 5000.0,  "Gold futures"),    # currently ~$2000-3000
    "CL=F":     (-10.0, 200.0,   "Crude WTI"),       # went negative briefly in 2020
    "HG=F":     (1.0, 10.0,      "Copper futures"),
    "SI=F":     (5.0, 60.0,      "Silver futures"),
    "NG=F":     (0.5, 15.0,      "Natural gas"),
    "BZ=F":     (5.0, 200.0,     "Brent crude"),

    # --- Yahoo: Currencies ---
    "EURUSD=X":  (0.7, 1.7,   "EUR/USD"),
    "JPY=X":     (70.0, 200.0, "USD/JPY"),
    "CHF=X":     (0.5, 1.5,    "USD/CHF"),
    "GBPUSD=X":  (0.8, 2.2,   "GBP/USD"),
    "CNY=X":     (5.0, 10.0,   "USD/CNY"),
    "DX-Y.NYB":  (60.0, 140.0, "DXY"),

    # --- Yahoo: Bond/Credit ETFs (price, not yield) ---
    "TLT":  (50.0, 200.0, "TLT 20Y Treasury ETF"),
    "HYG":  (50.0, 110.0, "HYG High Yield ETF"),
    "LQD":  (70.0, 150.0, "LQD IG Corporate ETF"),
    "BKLN": (10.0, 30.0,  "BKLN Leveraged Loan ETF"),
    "BIZD": (8.0, 25.0,   "BIZD BDC Income ETF"),
    "SHV":  (90.0, 120.0, "SHV Short Treasury ETF"),

    # --- Yahoo: Regional/EM ETFs ---
    "EEM": (15.0, 70.0,  "EEM Emerging Markets ETF"),
    "EFA": (30.0, 100.0, "EFA EAFE ETF"),
}


def validate_data_ranges(fred_data, yahoo_data):
    """Check all fetched values against plausible ranges.

    Returns a list of anomaly dicts. Empty list = all values in range.
    Each anomaly includes enough context for downstream skills to decide
    whether to trust the number or flag it.
    """
    anomalies = []
    fd = fred_data.get("data", {}) if fred_data else {}
    yd = yahoo_data.get("data", {}) if yahoo_data else {}

    for series_key, (lo, hi, desc) in PLAUSIBLE_RANGES.items():
        # Check FRED data
        if series_key in fd:
            val = fd[series_key].get("latest_value")
            date = fd[series_key].get("latest_date", "unknown")
            if val is not None:
                if (lo is not None and val < lo) or (hi is not None and val > hi):
                    anomalies.append({
                        "source": "FRED",
                        "series": series_key,
                        "description": desc,
                        "value": val,
                        "date": date,
                        "expected_range": [lo, hi],
                        "severity": "high" if (
                            (lo is not None and val < lo * 0.5) or
                            (hi is not None and val > hi * 2)
                        ) else "medium",
                    })

        # Check Yahoo data
        if series_key in yd:
            val = yd[series_key].get("latest_value")
            date = yd[series_key].get("latest_date", "unknown")
            if val is not None:
                if (lo is not None and val < lo) or (hi is not None and val > hi):
                    anomalies.append({
                        "source": "Yahoo",
                        "series": series_key,
                        "description": desc,
                        "value": val,
                        "date": date,
                        "expected_range": [lo, hi],
                        "severity": "high" if (
                            (lo is not None and val < lo * 0.5) or
                            (hi is not None and val > hi * 2)
                        ) else "medium",
                    })

    return anomalies


# ---------------------------------------------------------------------------
# Z-SCORE TENSION DETECTION
# ---------------------------------------------------------------------------
# The structural scanner (Skill 13) has 7 prompt-defined detector categories.
# In practice, the LLM finds what those 7 descriptions tell it to look for.
# This pass lets the DATA decide which domains deserve attention: for every
# macro-relevant series, compute z-scores on level and 8-observation rate of
# change. Anything >2σ gets flagged and fed to Skill 13 as Phase 0 input.
# ---------------------------------------------------------------------------

# Categories relevant for structural macro analysis.
# Excludes: equities, volatility, ETF prices (positioning/sentiment, not macro).
MACRO_CATEGORIES = {
    "rates", "credit", "financial_conditions", "inflation", "employment",
    "growth", "inventories", "money_supply", "fed_balance_sheet",
    "activity_index", "housing", "regional_fed_mfg", "credit_conditions",
    "commodities", "fx", "money_markets",
}


def _category_for_series(series_key):
    """Look up the category for a FRED or Yahoo series key."""
    if series_key in FRED_SERIES:
        return FRED_SERIES[series_key][1]
    if series_key in YAHOO_TICKERS:
        return YAHOO_TICKERS[series_key][1]
    return None


def load_zscore_baseline(output_dir):
    """Load the running z-score baseline from disk.

    The baseline accumulates mean/variance/count across weekly runs using
    Welford's online algorithm. This gives a long-term reference that grows
    with each run, catching slow drifts that a 26-week window normalizes away.

    Returns dict: {series_id: {"mean": float, "m2": float, "count": int}}
    m2 is the running sum of squared deviations (variance = m2 / count).
    """
    baseline_path = Path(output_dir) / "zscore-baseline.json"
    if baseline_path.exists():
        try:
            with open(baseline_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def update_zscore_baseline(baseline, series_values):
    """Update baseline with new observations using Welford's online algorithm.

    series_values: dict of {series_id: latest_value}
    Returns updated baseline dict.
    """
    for sid, val in series_values.items():
        if val is None:
            continue
        if sid not in baseline:
            baseline[sid] = {"mean": val, "m2": 0.0, "count": 1}
        else:
            entry = baseline[sid]
            entry["count"] += 1
            delta = val - entry["mean"]
            entry["mean"] += delta / entry["count"]
            delta2 = val - entry["mean"]
            entry["m2"] += delta * delta2
    return baseline


def save_zscore_baseline(baseline, output_dir):
    """Persist the running baseline to disk."""
    baseline_path = Path(output_dir) / "zscore-baseline.json"
    with open(baseline_path, "w") as f:
        json.dump(baseline, f, indent=2)


def compute_zscore_tensions(fred_data, yahoo_data, data_anomalies=None,
                            baseline=None, threshold=2.0):
    """Flag macro series whose current level or 8-observation rate of change
    is >threshold standard deviations from historical norm.

    Two baselines:
    - Short-term: z-scores against the current history window (~26 weeks).
      Catches sudden deviations.
    - Long-term: z-scores against the running baseline that accumulates across
      weekly runs (Welford's algorithm). Catches slow drifts that a 26-week
      window normalizes away. Only active after 20+ accumulated observations.

    Returns (tensions_list, series_values_dict).
    series_values_dict is {series_id: latest_value} for baseline update.
    """
    tensions = []
    series_values = {}  # for baseline update
    anomaly_series = set()
    if data_anomalies:
        anomaly_series = {a["series"] for a in data_anomalies}
    if baseline is None:
        baseline = {}

    # Merge FRED and Yahoo data into a single iteration
    all_series = {}
    for source_label, source_data in [("FRED", fred_data), ("Yahoo", yahoo_data)]:
        if not source_data:
            continue
        for sid, sdata in source_data.get("data", {}).items():
            cat = _category_for_series(sid)
            if cat not in MACRO_CATEGORIES:
                continue
            if sid in anomaly_series:
                continue
            desc = sdata.get("name", FRED_SERIES.get(sid, YAHOO_TICKERS.get(sid, ("", "")))[0])
            all_series[sid] = (source_label, sdata, cat, desc)

    for sid, (source_label, sdata, cat, desc) in all_series.items():
        history = sdata.get("history", [])
        # Minimum 10 observations for level z-score. Monthly macro series
        # (CPI, unemployment, payrolls) get ~13 observations in weekly mode
        # due to the yoy_start extension. We want to include them.
        if len(history) < 10:
            # Still record value for baseline accumulation even if too few
            # observations for short-term z-score
            if history:
                series_values[sid] = history[-1]["value"]
            continue

        values = [h["value"] for h in history]
        latest = values[-1]
        series_values[sid] = latest

        # --- Short-term level z-score (current window) ---
        mean_val = sum(values) / len(values)
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        std_val = variance ** 0.5
        if std_val < 1e-6:
            continue

        level_z = (latest - mean_val) / std_val

        # --- Long-term level z-score (accumulated baseline) ---
        lt_z = None
        lt_mean = None
        lt_std = None
        if sid in baseline and baseline[sid]["count"] >= 20:
            b = baseline[sid]
            lt_mean = b["mean"]
            lt_var = b["m2"] / b["count"]
            lt_std = lt_var ** 0.5
            if lt_std > 1e-6:
                lt_z = (latest - lt_mean) / lt_std

        # --- Rate-of-change z-score (8-observation window) ---
        # For monthly series with ~13 observations, this gives 5 rolling windows
        # (13 - 8 = 5). Tight but usable. For weekly series with 26+, plenty.
        roc_z = None
        roc_direction = None
        roc_window = 8
        if len(values) >= roc_window + 3:  # need at least 3 rolling windows
            changes = []
            for i in range(roc_window, len(values)):
                changes.append(values[i] - values[i - roc_window])
            if len(changes) >= 3:
                latest_change = changes[-1]
                roc_mean = sum(changes) / len(changes)
                roc_var = sum((c - roc_mean) ** 2 for c in changes) / len(changes)
                roc_std = roc_var ** 0.5
                if roc_std > 1e-6:
                    roc_z = (latest_change - roc_mean) / roc_std
                    roc_direction = "accelerating" if latest_change > roc_mean else "decelerating"

        # --- Flag if any z-score exceeds threshold ---
        level_flagged = abs(level_z) >= threshold
        lt_flagged = lt_z is not None and abs(lt_z) >= threshold
        roc_flagged = roc_z is not None and abs(roc_z) >= threshold

        if level_flagged or lt_flagged or roc_flagged:
            # Determine flag reason
            reasons = []
            if level_flagged:
                reasons.append("level")
            if lt_flagged:
                reasons.append("long_term")
            if roc_flagged:
                reasons.append("rate_of_change")
            reason = "+".join(reasons) if len(reasons) > 1 else reasons[0]

            tensions.append({
                "source": source_label,
                "series": sid,
                "description": desc,
                "category": cat,
                "latest_value": round(latest, 4),
                "level_zscore": round(level_z, 2),
                "long_term_zscore": round(lt_z, 2) if lt_z is not None else None,
                "long_term_baseline_n": baseline[sid]["count"] if sid in baseline else 0,
                "roc_zscore": round(roc_z, 2) if roc_z is not None else None,
                "roc_window": roc_window,
                "flag_reason": reason,
                "direction": "above_mean" if latest > mean_val else "below_mean",
                "roc_direction": roc_direction,
                "historical_mean": round(mean_val, 4),
                "historical_std": round(std_val, 4),
                "long_term_mean": round(lt_mean, 4) if lt_mean is not None else None,
                "long_term_std": round(lt_std, 4) if lt_std is not None else None,
            })

    # Sort by max absolute z-score descending (strongest signals first)
    def _max_z(t):
        zs = [abs(t["level_zscore"])]
        if t["roc_zscore"] is not None:
            zs.append(abs(t["roc_zscore"]))
        if t["long_term_zscore"] is not None:
            zs.append(abs(t["long_term_zscore"]))
        return max(zs)
    tensions.sort(key=_max_z, reverse=True)
    return tensions, series_values


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

    # For YoY calculations, we need at least 13 months of data.
    # For regime series, we need 5 years for the 36-month rolling median.
    yoy_start = end_date - timedelta(days=max(lookback_days, 400))
    regime_start = end_date - timedelta(days=1825)  # 5 years for regime_history

    results = {}
    errors = []

    for series_id, (name, category, freq) in FRED_SERIES.items():
        try:
            # Use extended start for YoY calculation.
            # Regime series get 5-year history for regime_classifier.py.
            if series_id in REGIME_SERIES:
                fetch_start = regime_start
            elif freq in ("monthly", "quarterly"):
                fetch_start = yoy_start
            else:
                fetch_start = start_date
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

                    # Regime series: add 5-year monthly history for regime_classifier.py
                    if series_id in REGIME_SERIES:
                        regime_data = data[data.index >= regime_start]
                        regime_monthly = regime_data.resample("ME").last().dropna()
                        results[series_id]["regime_history"] = [
                            {"date": ts.strftime("%Y-%m-%d"), "value": round(float(val), 4)}
                            for ts, val in regime_monthly.items()
                        ]
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
                if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                    wait = 2 ** (attempt + 1)  # 2s, 4s — give CFTC servers time to recover
                    label = "Rate limited" if e.code == 429 else f"Server error {e.code}"
                    print(f"    {label} on {name}, retrying in {wait}s...")
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


# ---------------------------------------------------------------------------
# EIA PETROLEUM DATA (free, no key — via bulk download from eia.gov)
# ---------------------------------------------------------------------------
EIA_SERIES = {
    "WCESTUS1": {
        "name": "US Commercial Crude Oil Inventories (excl. SPR)",
        "bulk_id": "PET.WCESTUS1.W",
    },
    "WCSSTUS1": {
        "name": "US Strategic Petroleum Reserve",
        "bulk_id": "PET.WCSSTUS1.W",
    },
    "WPULEUS3": {
        "name": "US Refinery Utilization",
        "bulk_id": "PET.WPULEUS3.W",
    },
    "WRPUPUS2": {
        "name": "US Total Petroleum Products Supplied (demand proxy)",
        "bulk_id": "PET.WRPUPUS2.W",
    },
}


def fetch_eia_data(lookback_weeks=52):
    """Fetch EIA petroleum data via bulk download (free, no API key required).

    Downloads PET.zip (~61MB) from eia.gov/opendata/bulk/, extracts 4 target
    weekly petroleum series, and discards the rest. Updated twice daily by EIA.
    Takes ~30-60 seconds depending on connection speed.

    Returns dict with {"data": {...}, "errors": [...]} or None on total failure.
    """
    import urllib.request
    import zipfile
    import io

    bulk_url = "https://www.eia.gov/opendata/bulk/PET.zip"
    target_ids = {cfg["bulk_id"]: sid for sid, cfg in EIA_SERIES.items()}

    results = {}
    errors = []

    try:
        print("    Downloading EIA bulk file (PET.zip, ~61MB, no key needed)...")
        req = urllib.request.Request(bulk_url, headers={"User-Agent": "MacroAdvisor/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            zip_bytes = resp.read()

        print(f"    Downloaded {len(zip_bytes) / 1024 / 1024:.1f} MB, extracting target series...")

        # Extract PET.txt from zip in memory
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            # Find the text file (usually PET.txt)
            txt_name = [n for n in zf.namelist() if n.endswith('.txt')][0]
            with zf.open(txt_name) as f:
                for line in f:
                    line = line.decode('utf-8', errors='replace').strip()
                    if not line:
                        continue
                    # Quick check before parsing JSON (performance: skip 99.99% of lines)
                    match = False
                    for bulk_id in target_ids:
                        if bulk_id in line:
                            match = True
                            break
                    if not match:
                        continue

                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    series_bulk_id = obj.get("series_id", "")
                    if series_bulk_id not in target_ids:
                        continue

                    series_id = target_ids[series_bulk_id]
                    config = EIA_SERIES[series_id]
                    raw_data = obj.get("data", [])

                    if not raw_data:
                        errors.append(f"{series_id}: no data in bulk file")
                        continue

                    # raw_data is list of [date_str, value] in desc order
                    # date format: YYYYMMDD → convert to YYYY-MM-DD
                    history = []
                    for entry in reversed(raw_data):
                        if len(entry) < 2 or entry[1] is None:
                            continue
                        try:
                            date_str = str(entry[0])
                            val = float(entry[1])
                            # Convert YYYYMMDD to YYYY-MM-DD
                            if len(date_str) == 8 and date_str.isdigit():
                                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                            else:
                                formatted_date = date_str
                            history.append({"date": formatted_date, "value": round(val, 2)})
                        except (ValueError, TypeError, IndexError):
                            continue

                    # Trim to lookback window
                    if lookback_weeks < len(history):
                        history = history[-lookback_weeks:]

                    if not history:
                        errors.append(f"{series_id}: all values null in bulk data")
                        continue

                    latest = history[-1]
                    prior = history[-2] if len(history) >= 2 else None

                    results[series_id] = {
                        "name": config["name"],
                        "series_id": series_id,
                        "latest_value": latest["value"],
                        "latest_date": latest["date"],
                        "prior_value": prior["value"] if prior else None,
                        "prior_date": prior["date"] if prior else None,
                        "observation_count": len(history),
                        "history": history,
                    }

        # Check for missing series
        for bulk_id, sid in target_ids.items():
            if sid not in results:
                errors.append(f"{sid}: not found in bulk file (expected {bulk_id})")

    except urllib.error.URLError as e:
        errors.append(f"Bulk download failed: {str(e)[:200]}")
    except Exception as e:
        errors.append(f"Bulk extraction failed: {str(e)[:200]}")

    return {"data": results, "errors": errors} if results or errors else None


# ---------------------------------------------------------------------------
# BIS CREDIT-TO-GDP DATA (free, no key — CSV download from bis.org)
# ---------------------------------------------------------------------------
BIS_COUNTRIES = {
    "US": "United States",
    "XM": "Euro area",  # BIS uses XM for Euro area aggregate
    "CN": "China",
    "JP": "Japan",
    "GB": "United Kingdom",
}


def fetch_bis_credit_data():
    """Fetch BIS credit-to-GDP gap data (free CSV, no key required).

    The BIS publishes credit-to-GDP ratios (actual) and HP-filter trends quarterly.
    The credit gap = actual ratio - trend. We fetch both and compute the gap.

    Data URL: https://data.bis.org/topics/CREDIT_GAPS/BIS,WS_CREDIT_GAP,1.0/Q.[CC].P.A.[A|B]
    where A = actual ratio, B = HP-filter trend

    Returns:
        dict with country-level credit-to-GDP gap data, or None on total failure
    """
    import urllib.request

    results = {}
    errors = []

    base_url = "https://data.bis.org/topics/CREDIT_GAPS/BIS,WS_CREDIT_GAP,1.0/"

    def _fetch_bis_series(country_code, suffix):
        """Fetch a BIS CSV series, return list of {date, value} or None."""
        url = f"{base_url}Q.{country_code}.P.A.{suffix}?file_format=csv&format=long&include=code%2Clabel"
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "MacroAdvisor/1.0"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw = resp.read().decode("utf-8")
                # Parse the BIS portal CSV — data rows start with "BIS,WS_CREDIT_GAP
                # Format: ...,date,availability,,obs_status,value
                data_lines = [l for l in raw.split("\n") if l.startswith('"BIS')]
                history = []
                for line in data_lines:
                    parts = line.split(",")
                    # Find date (YYYY-MM-DD) and last float value
                    date = None
                    value = None
                    for p in parts:
                        p = p.strip().strip('"')
                        if len(p) == 10 and p[4:5] == "-" and p[7:8] == "-":
                            date = p
                        try:
                            value = float(p)
                        except (ValueError, TypeError):
                            pass
                    if date and value is not None:
                        history.append({"date": date, "value": round(value, 2)})
                return history if history else None
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                else:
                    return None
            except Exception:
                if attempt < 2:
                    time.sleep(1)
                else:
                    return None
        return None

    for country_code, country_name in BIS_COUNTRIES.items():
        try:
            # Fetch actual credit-to-GDP ratio and HP-filter trend
            actual = _fetch_bis_series(country_code, "A")
            trend = _fetch_bis_series(country_code, "B")

            if not actual:
                errors.append(f"BIS {country_code}: could not fetch actual ratio")
                continue
            if not trend:
                errors.append(f"BIS {country_code}: could not fetch trend — using actual only")
                # Can't compute gap without trend, skip
                continue

            # Align by date and compute gap = actual - trend
            trend_by_date = {h["date"]: h["value"] for h in trend}
            gap_history = []
            for point in actual:
                if point["date"] in trend_by_date:
                    gap = round(point["value"] - trend_by_date[point["date"]], 2)
                    gap_history.append({"date": point["date"], "value": gap})

            if not gap_history:
                errors.append(f"BIS {country_code}: no overlapping dates for gap computation")
                continue

            # Take last 8 quarters (2 years)
            gap_history = gap_history[-8:]
            latest = gap_history[-1]
            prior = gap_history[-2] if len(gap_history) >= 2 else None

            # Credit gap interpretation
            gap = latest["value"]
            signal = (
                "overheating" if gap > 10 else
                "above_trend" if gap > 2 else
                "near_trend" if gap > -2 else
                "below_trend" if gap > -10 else
                "depressed"
            )

            results[country_code] = {
                "country": country_name,
                "credit_gap_pp": gap,
                "signal": signal,
                "latest_date": latest["date"],
                "prior_gap": prior["value"] if prior else None,
                "prior_date": prior["date"] if prior else None,
                "direction": "widening" if prior and gap > prior["value"] else "narrowing" if prior and gap < prior["value"] else "stable",
                "observation_count": len(gap_history),
                "history": gap_history,  # Last 2 years quarterly (already trimmed to 8)
            }

        except Exception as e:
            errors.append(f"BIS {country_code}: {str(e)[:100]}")

    return {"data": results, "errors": errors} if results or errors else None


# ---------------------------------------------------------------------------
# OECD CLI CONFIGURATION
# ---------------------------------------------------------------------------
# OECD publishes CLI at country level only (no Euro Area aggregate).
# DEU (Germany) serves as Euro proxy — standard practice in macro analysis.
OECD_CLI_COUNTRIES = {
    "USA": "United States",
    "DEU": "Germany",  # Euro Area proxy (OECD has no EA aggregate for CLI)
    "CHN": "China",
    "JPN": "Japan",
    "GBR": "United Kingdom",
}


def fetch_oecd_cli_data():
    """Fetch OECD Composite Leading Indicators (CLI) for major economies.

    Uses the OECD SDMX REST API (sdmx.oecd.org). Free, no auth required.
    CLI is amplitude-adjusted, centred around 100. Values above 100 indicate
    above-trend growth; below 100 indicates below-trend.

    The key signal is DIRECTION, not level:
      > 100 + rising  → "expanding"   (growth accelerating)
      > 100 + falling → "decelerating" (early warning)
      < 100 + falling → "contracting"  (growth deteriorating)
      < 100 + rising  → "recovering"   (trough forming)

    Returns:
        dict with country-level CLI data + global divergence assessment, or None on total failure
    """
    import urllib.request
    import json as _json

    errors = []
    results = {}

    # Single multi-country query — avoids rate limiting
    country_keys = "+".join(OECD_CLI_COUNTRIES.keys())
    # Dataflow: OECD.SDD.STES, DSD_STES@DF_CLI
    # Dimensions (9): REF_AREA.FREQ.MEASURE.UNIT_MEASURE.ACTIVITY.ADJUSTMENT.TRANSFORMATION.TIME_HORIZ.METHODOLOGY
    # LI = Composite Leading Indicator, IX = Index, AA = Amplitude adjusted, H = OECD harmonised
    url = (
        f"https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI,/"
        f"{country_keys}.M.LI.IX._Z.AA.IX._Z.H+N"
        f"?startPeriod={(datetime.now() - timedelta(days=1095)).strftime('%Y-%m')}"  # 3 years back
        f"&detail=dataonly"
    )

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "MacroAdvisor/1.0",
                "Accept": "application/vnd.sdmx.data+json;charset=utf-8;version=1.0",
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
            data = _json.loads(raw)

            # Parse SDMX-JSON structure
            structure = data.get("data", {}).get("structure", {})
            dims = structure.get("dimensions", {})

            # Map dimension indices to values
            series_dims = dims.get("series", [])
            ref_areas = [v.get("id") for v in next((d for d in series_dims if d["id"] == "REF_AREA"), {}).get("values", [])]
            obs_dims = dims.get("observation", [])
            time_periods = sorted([v.get("id") for v in next((d for d in obs_dims if d["id"] == "TIME_PERIOD"), {}).get("values", [])])

            if not time_periods:
                errors.append("OECD CLI: response had no time periods")
                break

            datasets = data.get("data", {}).get("dataSets", [{}])
            if not datasets:
                errors.append("OECD CLI: response had no datasets")
                break

            series = datasets[0].get("series", {})

            for sk, sv in series.items():
                parts = sk.split(":")
                country_idx = int(parts[0])
                country = ref_areas[country_idx] if country_idx < len(ref_areas) else None
                if not country or country not in OECD_CLI_COUNTRIES:
                    continue

                obs = sv.get("observations", {})
                if not obs:
                    errors.append(f"OECD CLI {country}: no observations")
                    continue

                # Build sorted history
                history = []
                for ok, ov in obs.items():
                    t_idx = int(ok)
                    if t_idx < len(time_periods):
                        history.append({"date": time_periods[t_idx], "value": round(ov[0], 4)})
                history.sort(key=lambda x: x["date"])

                if len(history) < 2:
                    errors.append(f"OECD CLI {country}: insufficient data ({len(history)} points)")
                    continue

                latest = history[-1]
                prior = history[-2]
                mom_change = round(latest["value"] - prior["value"], 4)

                # Signal classification
                above_100 = latest["value"] >= 100
                rising = mom_change > 0
                if above_100 and rising:
                    direction = "expanding"
                elif above_100 and not rising:
                    direction = "decelerating"
                elif not above_100 and not rising:
                    direction = "contracting"
                else:
                    direction = "recovering"

                # Revision detection: OECD revises prior 2-3 months when new data arrives.
                # Full implementation would read prior snapshot and compare values.
                # Deferred: requires persistent state across runs (TODO in plan).
                revised = False

                results[country] = {
                    "country": OECD_CLI_COUNTRIES[country],
                    "value": latest["value"],
                    "date": latest["date"],
                    "mom_change": mom_change,
                    "direction": direction,
                    "revised": revised,
                    "observation_count": len(history),
                    "history": history[-24:],  # Last 2 years monthly
                }

            break  # Success, no need to retry

        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                errors.append(f"OECD CLI: HTTP {e.code}, retrying...")
            else:
                errors.append(f"OECD CLI: HTTP {e.code} — {str(e)[:100]}")
                break
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                errors.append(f"OECD CLI: {str(e)[:150]}")
                break

    if not results:
        return {"data": {}, "errors": errors} if errors else None

    # Compute global divergence assessment
    directions = {k: v["direction"] for k, v in results.items()}
    decelerating_count = sum(1 for d in directions.values() if d in ("decelerating", "contracting"))
    us_dir = directions.get("USA")
    non_us_dirs = {k: v for k, v in directions.items() if k != "USA"}

    # US vs world divergence
    us_expanding = us_dir in ("expanding", "recovering")
    world_contracting = sum(1 for d in non_us_dirs.values() if d in ("decelerating", "contracting")) >= len(non_us_dirs) / 2
    if us_expanding and world_contracting:
        us_vs_world = "diverging_up"
    elif not us_expanding and not world_contracting:
        us_vs_world = "diverging_down"
    else:
        us_vs_world = "aligned"

    divergence = {
        "us_vs_world": us_vs_world,
        "simultaneous_deceleration": decelerating_count >= 3,
        "economies_decelerating": decelerating_count,
        "directions": directions,
    }

    return {"data": results, "divergence": divergence, "errors": errors}


# ---------------------------------------------------------------------------
# IMF WEO FORECAST CONFIGURATION
# ---------------------------------------------------------------------------
IMF_WEO_COUNTRIES = {
    "USA": "United States",
    "EURO": "Euro area",
    "CHN": "China",
    "JPN": "Japan",
    "GBR": "United Kingdom",
}

IMF_WEO_INDICATORS = {
    "NGDP_RPCH": "Real GDP growth (%)",
    "PCPIPCH": "CPI inflation (%)",
}


def fetch_imf_weo_data():
    """Fetch IMF World Economic Outlook forecasts for major economies.

    Uses the IMF DataMapper API (free, no auth). WEO updates twice yearly
    (April + October). Fetches GDP growth and CPI inflation forecasts for
    current year, next year, and year after.

    Important: The DataMapper API blocks requests with country codes in the URL path.
    Must use the indicator-only endpoint and filter client-side.

    Returns:
        dict with country-level GDP and CPI forecasts + vintage info, or None on total failure
    """
    import urllib.request
    import json as _json

    errors = []
    results = {}

    current_year = datetime.now().year
    periods = f"{current_year},{current_year + 1},{current_year + 2}"

    for indicator, desc in IMF_WEO_INDICATORS.items():
        # IMF blocks country-filtered URLs but allows indicator-only + periods
        url = f"https://www.imf.org/external/datamapper/api/v1/{indicator}?periods={periods}"

        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://www.imf.org/external/datamapper/",
                    "Accept-Language": "en-US,en;q=0.9",
                })
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read().decode("utf-8")
                data = _json.loads(raw)

                values = data.get("values", {}).get(indicator, {})
                if not values:
                    errors.append(f"IMF WEO {indicator}: no values in response")
                    break

                for country_code, country_name in IMF_WEO_COUNTRIES.items():
                    if country_code not in values:
                        # IMF may not have data for all countries
                        continue

                    country_data = values[country_code]
                    if country_code not in results:
                        results[country_code] = {"country": country_name}

                    # Map year values
                    for year_str, val in country_data.items():
                        year = int(year_str)
                        if year == current_year:
                            key = f"{indicator.lower()}_current"
                        elif year == current_year + 1:
                            key = f"{indicator.lower()}_next"
                        elif year == current_year + 2:
                            key = f"{indicator.lower()}_next2"
                        else:
                            continue
                        results[country_code][key] = round(val, 2) if isinstance(val, (int, float)) else val

                break  # Success

            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                else:
                    errors.append(f"IMF WEO {indicator}: HTTP {e.code}")
                    break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    errors.append(f"IMF WEO {indicator}: {str(e)[:150]}")
                    break

    if not results:
        return {"data": {}, "errors": errors} if errors else None

    # Determine WEO vintage — IMF updates April and October
    # We can't detect vintage from the API directly, so infer from current date
    now = datetime.now()
    if now.month >= 10:
        vintage = f"Oct {now.year}"
    elif now.month >= 4:
        vintage = f"Apr {now.year}"
    else:
        vintage = f"Oct {now.year - 1}"

    # Staleness check: flag if vintage is > 4 months old
    vintage_month = 10 if "Oct" in vintage else 4
    vintage_year = int(vintage.split()[-1])
    months_since = (now.year - vintage_year) * 12 + (now.month - vintage_month)
    stale = months_since > 4

    return {
        "data": results,
        "vintage": vintage,
        "stale": stale,
        "months_since_vintage": months_since,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# BIS GLOBAL LIQUIDITY INDICATORS (GLI)
# ---------------------------------------------------------------------------

# BIS aggregate codes for GLI
BIS_GLI_AGGREGATES = {
    "4T": "All reporting countries",
    "3P": "Emerging market economies",
    "3C": "Advanced economies",
}


def fetch_bis_gli_data():
    """Fetch BIS Global Liquidity Indicators — USD credit to non-bank borrowers.

    Uses the BIS SDMX REST API (stats.bis.org). Free, no auth required.
    Tracks cross-border USD-denominated credit via bank loans + debt securities.
    This is the dominant global liquidity transmission channel.

    Key series: CURR_DENOM=USD, L_INSTR=B (loans+bonds), UNIT_MEASURE=771 (YoY growth %),
    BORROWERS_SECTOR=N (non-bank), aggregates 4T (total), 3P (EM), 3C (AE).

    Returns:
        dict with aggregate-level GLI data, or None on total failure
    """
    import urllib.request
    import csv as _csv
    import io as _io

    errors = []
    results = {}

    start_period = (datetime.now() - timedelta(days=1095)).strftime("%Y-Q1")  # 3 years
    url = f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_GLI/1.0/?format=csv&startPeriod={start_period}"

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MacroAdvisor/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")

            reader = _csv.DictReader(_io.StringIO(raw))
            # Collect relevant rows: USD, loans+bonds (B), YoY growth (771), non-bank (N)
            for row in reader:
                if (row.get("CURR_DENOM") == "USD"
                        and row.get("L_INSTR") == "B"
                        and row.get("UNIT_MEASURE") == "771"
                        and row.get("BORROWERS_SECTOR") == "N"):
                    cty = row.get("BORROWERS_CTY", "")
                    if cty not in BIS_GLI_AGGREGATES:
                        continue
                    period = row.get("TIME_PERIOD", "")
                    try:
                        val = float(row.get("OBS_VALUE", ""))
                    except (ValueError, TypeError):
                        continue
                    results.setdefault(cty, []).append({"date": period, "value": round(val, 3)})

            break  # Success

        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** (attempt + 1))
            else:
                errors.append(f"BIS GLI: HTTP {e.code}")
                break
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                errors.append(f"BIS GLI: {str(e)[:150]}")
                break

    if not results:
        return {"data": {}, "errors": errors} if errors else None

    # Process each aggregate: compute latest, prior, direction
    processed = {}
    for agg_code, agg_name in BIS_GLI_AGGREGATES.items():
        history = results.get(agg_code, [])
        if not history:
            continue
        history.sort(key=lambda x: x["date"])
        if len(history) < 2:
            continue

        latest = history[-1]
        prior = history[-2]
        yoy = latest["value"]

        signal = (
            "rapid_expansion" if yoy > 8 else
            "moderate_expansion" if yoy > 3 else
            "stagnant" if yoy > 0 else
            "contracting"
        )

        processed[agg_code] = {
            "aggregate": agg_name,
            "yoy_growth_pct": yoy,
            "signal": signal,
            "date": latest["date"],
            "prior_yoy": prior["value"],
            "prior_date": prior["date"],
            "direction": "accelerating" if yoy > prior["value"] else "decelerating",
            "observation_count": len(history),
            "history": history[-12:],  # Last 3 years quarterly
        }

    if not processed:
        return {"data": {}, "errors": errors} if errors else None

    # AE vs EMDE divergence
    ae_yoy = processed.get("3C", {}).get("yoy_growth_pct")
    emde_yoy = processed.get("3P", {}).get("yoy_growth_pct")
    ae_emde_divergence = (ae_yoy is not None and emde_yoy is not None
                          and abs(ae_yoy - emde_yoy) > 3)

    return {
        "data": processed,
        "ae_emde_divergence": ae_emde_divergence,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# BIS RESIDENTIAL PROPERTY PRICES
# ---------------------------------------------------------------------------

BIS_PROPERTY_COUNTRIES = {
    "US": "United States",
    "DE": "Germany",
    "CN": "China",
    "JP": "Japan",
    "GB": "United Kingdom",
    "IN": "India",
    "BR": "Brazil",
    "KR": "Korea",
    "MX": "Mexico",
    "ID": "Indonesia",
}


def fetch_bis_property_data():
    """Fetch BIS residential property prices (real, YoY growth) for 10 economies.

    Uses the BIS SDMX REST API (stats.bis.org). Free, no auth required.
    Fetches real (CPI-deflated) residential property price YoY growth rates.
    Uses percentile-based signal classification vs each country's own 10-year history.

    Returns:
        dict with country-level property price data, or None on total failure
    """
    import urllib.request
    import csv as _csv
    import io as _io

    errors = []
    results = {}

    # Fetch 10+ years for percentile calculation
    start_period = (datetime.now() - timedelta(days=4380)).strftime("%Y-Q1")  # 12 years
    url = f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_SPP/1.0/?format=csv&startPeriod={start_period}"

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MacroAdvisor/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")

            reader = _csv.DictReader(_io.StringIO(raw))
            # Filter: VALUE=R (real/deflated), UNIT_MEASURE=771 (YoY growth %)
            for row in reader:
                if row.get("VALUE") == "R" and row.get("UNIT_MEASURE") == "771":
                    area = row.get("REF_AREA", "")
                    if area not in BIS_PROPERTY_COUNTRIES:
                        continue
                    period = row.get("TIME_PERIOD", "")
                    try:
                        val = float(row.get("OBS_VALUE", ""))
                    except (ValueError, TypeError):
                        continue
                    results.setdefault(area, []).append({"date": period, "value": round(val, 4)})

            break  # Success

        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** (attempt + 1))
            else:
                errors.append(f"BIS Property: HTTP {e.code}")
                break
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                errors.append(f"BIS Property: {str(e)[:150]}")
                break

    if not results:
        return {"data": {}, "errors": errors} if errors else None

    # Process each country: percentile-based signal classification
    processed = {}
    for country_code, country_name in BIS_PROPERTY_COUNTRIES.items():
        history = results.get(country_code, [])
        if not history:
            continue
        history.sort(key=lambda x: x["date"])
        if len(history) < 4:
            errors.append(f"BIS Property {country_code}: insufficient data ({len(history)} points)")
            continue

        latest = history[-1]
        yoy = latest["value"]

        # Percentile-based classification vs own history
        all_values = sorted([h["value"] for h in history])
        rank = sum(1 for v in all_values if v <= yoy) / len(all_values) * 100

        signal = (
            "overheating" if rank > 90 else
            "hot" if rank > 70 else
            "moderate" if rank > 30 else
            "cooling" if rank > 10 else
            "declining"
        )

        processed[country_code] = {
            "country": country_name,
            "yoy_pct": yoy,
            "percentile": round(rank, 1),
            "signal": signal,
            "date": latest["date"],
            "observation_count": len(history),
            "history": history[-12:],  # Last 3 years quarterly
        }

    if not processed:
        return {"data": {}, "errors": errors} if errors else None

    # Systemic risk: count overheating economies
    overheating_count = sum(1 for v in processed.values() if v["signal"] == "overheating")

    return {
        "data": processed,
        "systemic_overheating": overheating_count >= 3,
        "overheating_count": overheating_count,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# WORLD BANK STRUCTURAL INDICATORS
# ---------------------------------------------------------------------------

WB_COUNTRIES = {
    "US": "United States", "DE": "Germany", "CN": "China",
    "JP": "Japan", "GB": "United Kingdom",
    "IN": "India", "BR": "Brazil", "KR": "Korea, Rep.",
    "MX": "Mexico", "ID": "Indonesia",
}

WB_INDICATORS = {
    "SP.POP.65UP.TO.ZS": "pop_65plus_pct",
    "SL.TLF.ACTI.ZS": "labor_participation_pct",
    "FS.AST.PRVT.GD.ZS": "credit_private_pct_gdp",
    "BN.CAB.XOKA.GD.ZS": "current_account_pct_gdp",
    "NE.TRD.GNFS.ZS": "trade_openness_pct_gdp",
    "NY.GDP.PCAP.PP.KD": "gdp_per_capita_ppp",
    "SI.POV.GINI": "gini",
    "DT.DOD.DECT.GN.ZS": "external_debt_pct_gni",
}


def fetch_worldbank_structural_data():
    """Fetch World Bank structural indicators for 10 economies.

    Uses the World Bank Indicators API v2 (api.worldbank.org). Free, no auth, no rate limits.
    Annual data with 1-2 year lag. Designed for Skill 13 (structural scanner) and
    Skill 14 (decade horizon), NOT for weekly regime assessment.

    Returns:
        dict with country-level structural data, or None on total failure
    """
    import urllib.request
    import json as _json

    errors = []
    results = {}

    country_str = ";".join(WB_COUNTRIES.keys())
    current_year = datetime.now().year

    for wb_code, field_name in WB_INDICATORS.items():
        url = (
            f"https://api.worldbank.org/v2/country/{country_str}/indicator/{wb_code}"
            f"?date={current_year - 7}:{current_year}&format=json&per_page=500"
        )

        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "MacroAdvisor/1.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read().decode("utf-8")
                data = _json.loads(raw)

                if not isinstance(data, list) or len(data) < 2:
                    errors.append(f"WB {wb_code}: unexpected response format")
                    break

                meta = data[0]
                records = data[1] or []

                # Pagination check
                if meta.get("pages", 1) > 1:
                    errors.append(f"WB {wb_code}: truncated ({meta['pages']} pages, only fetched page 1)")

                # For each country, take the most recent non-null value
                for record in records:
                    country_id = record.get("country", {}).get("id", "")
                    val = record.get("value")
                    year = record.get("date", "")

                    if country_id not in WB_COUNTRIES or val is None:
                        continue

                    if country_id not in results:
                        results[country_id] = {"country": WB_COUNTRIES[country_id]}

                    # Only store if this is the most recent value for this field
                    existing_year = results[country_id].get(f"{field_name}_year", "0")
                    if year > existing_year:
                        results[country_id][field_name] = round(val, 2) if isinstance(val, (int, float)) else val
                        results[country_id][f"{field_name}_year"] = year

                break  # Success

            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                else:
                    errors.append(f"WB {wb_code}: HTTP {e.code}")
                    break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    errors.append(f"WB {wb_code}: {str(e)[:150]}")
                    break

    if not results:
        return {"data": {}, "errors": errors} if errors else None

    return {"data": results, "errors": errors}


def compute_rolling_trend(history, windows=(4, 8)):
    """Compute rolling direction bias from periodic history (any frequency).

    For each window size, counts how many period-over-period changes were
    positive vs negative, computes cumulative change, and classifies direction.
    Works with any data frequency (daily, weekly, monthly) — the window size
    refers to number of observations, not calendar weeks.

    Args:
        history: list of {"date": str, "value": float} sorted ascending
        windows: tuple of window sizes in observation periods (default: 4 and 8)

    Returns:
        dict with trend data per window, or None if insufficient history
    """
    if not history or len(history) < max(windows) + 1:
        return None

    result = {}
    for w in windows:
        # Take the last (w+1) entries to get w period-over-period changes
        recent = history[-(w + 1):]
        changes = []
        for i in range(1, len(recent)):
            changes.append(recent[i]["value"] - recent[i - 1]["value"])

        periods_positive = sum(1 for c in changes if c > 0)
        periods_negative = sum(1 for c in changes if c < 0)
        periods_flat = sum(1 for c in changes if c == 0)
        cumulative = round(sum(changes), 2)

        # Magnitude check: if cumulative change is <0.1% of the base value,
        # the direction is noise regardless of period counts
        base_value = recent[0]["value"]
        cumulative_pct = abs(cumulative / base_value * 100) if base_value != 0 else 0

        # Direction classification: require clear majority AND meaningful magnitude
        if cumulative_pct < 0.05:
            # Less than 0.05% change over the window — statistically flat
            direction = "neutral"
        elif periods_positive >= (w * 0.75):
            direction = "expansion_bias"
        elif periods_negative >= (w * 0.75):
            direction = "contraction_bias"
        elif periods_positive > periods_negative:
            direction = "mixed_positive"
        elif periods_negative > periods_positive:
            direction = "mixed_negative"
        else:
            direction = "neutral"

        result[f"{w}w"] = {
            "direction": direction,
            "periods_positive": periods_positive,
            "periods_negative": periods_negative,
            "periods_flat": periods_flat,
            "cumulative_change": cumulative,
            "cumulative_change_pct": round(cumulative_pct, 3),
            "start_date": recent[0]["date"],
            "end_date": recent[-1]["date"],
        }

    return result


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

    # Rolling trends for key liquidity series
    # These resolve single-week ambiguity (e.g., +$9.6B — noise or trend?)
    # by looking at 4-week and 8-week windows
    liquidity_trends = {}
    for sid, label, scale in [
        ("WALCL", "fed_total_assets", 1),      # Fed balance sheet (millions)
        ("WTREGEN", "tga", 1),                  # Treasury General Account (millions)
        ("WRESBAL", "reserves", 1),             # Reserve balances (millions)
    ]:
        if sid in fd:
            trend = compute_rolling_trend(fd[sid].get("history", []))
            if trend:
                liquidity_trends[label] = trend
    # M2 weekly (separate series from monthly M2SL)
    if "WM2NS" in fd:
        trend = compute_rolling_trend(fd["WM2NS"].get("history", []))
        if trend:
            liquidity_trends["m2_weekly"] = trend
    if liquidity_trends:
        derived["liquidity_trends"] = liquidity_trends

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
    if "BIZD" in yd:
        # BDC Income ETF — direct proxy for private credit market health.
        # BDCs hold private credit loans and are publicly traded, making BIZD
        # the closest observable proxy to actual private credit conditions.
        # Wider thresholds than BKLN: BDCs are more volatile and less liquid.
        bizd = yd["BIZD"]
        pc_proxy["bdc_etf"] = bizd["latest_value"]
        pc_proxy["bdc_week_chg"] = bizd.get("week_change_pct")
        pc_proxy["bdc_month_chg"] = bizd.get("month_change_pct")
        pc_proxy["bdc_date"] = bizd["latest_date"]
        month_chg = bizd.get("month_change_pct") or 0
        # Wider thresholds than BKLN: BDCs are more volatile (equity-like vs loan-like)
        pc_proxy["bdc_signal"] = (
            "stress" if month_chg < -3.0 else
            "softening" if month_chg < -1.0 else
            "stable" if abs(month_chg) <= 1.0 else
            "firming" if month_chg < 3.0 else
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
        if "bdc_signal" in pc_proxy:
            total_signals += 1
            if pc_proxy["bdc_signal"] == "stress":
                stress_signals += 1
            elif pc_proxy["bdc_signal"] in ("firming", "risk-on"):
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
        pc_proxy["neutral_count"] = total_signals - stress_signals - easing_signals
        pc_proxy["total_proxies"] = total_signals
        pc_proxy["_disclaimer"] = (
            "These are PROXIES for private credit conditions, not direct observations. "
            "Private credit has no public mark-to-market. Bank lending surveys, C&I loan "
            "volumes, leveraged loan ETF prices, and BDC ETF prices capture adjacent or "
            "overlapping markets that share borrower profiles with private credit — but they "
            "can diverge. Treat convergence as informative and divergence as genuinely "
            "uncertain, not as a sign one proxy is 'right'."
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

    # -----------------------------------------------------------------------
    # Commodity structural signals (for Skill 13: Structural Scanner)
    # -----------------------------------------------------------------------
    # 1. WTI-Brent spread as crude oil curve shape proxy
    #    When WTI > Brent: acute US near-term tightness (unusual, signals domestic supply stress)
    #    When Brent > WTI: normal structure, international demand premium
    #    Spread widening/narrowing over time signals shifting tightness
    if "CL=F" in yd and "BZ=F" in yd:
        wti = yd["CL=F"]["latest_value"]
        brent = yd["BZ=F"]["latest_value"]
        spread = round(wti - brent, 2)
        # Compute spread trend from history if available
        spread_trend = None
        wti_hist = yd["CL=F"].get("history", [])
        brent_hist = yd["BZ=F"].get("history", [])
        if len(wti_hist) >= 20 and len(brent_hist) >= 20:
            # Align by date (use last 20 common data points)
            wti_dates = {h["date"]: h["value"] for h in wti_hist}
            recent_spreads = []
            for h in brent_hist[-30:]:
                if h["date"] in wti_dates:
                    recent_spreads.append(wti_dates[h["date"]] - h["value"])
            if len(recent_spreads) >= 10:
                early_avg = sum(recent_spreads[:5]) / 5
                late_avg = sum(recent_spreads[-5:]) / 5
                if late_avg > early_avg + 0.5:
                    spread_trend = "narrowing_to_wti_premium"
                elif late_avg < early_avg - 0.5:
                    spread_trend = "widening_brent_premium"
                else:
                    spread_trend = "stable"

        derived["crude_term_structure"] = {
            "wti_brent_spread": spread,
            "signal": "us_tightness" if spread > 0 else "normal_brent_premium" if spread > -5 else "wide_brent_premium",
            "spread_trend": spread_trend,
            "wti_price": wti,
            "brent_price": brent,
            "date": yd["CL=F"]["latest_date"],
        }

    # 2. Commodity momentum signals (price vs 13-week and 26-week moving averages)
    #    Sustained above-MA = supply tightness being priced
    #    Sustained below-MA = demand weakness or supply relief
    commodity_momentum = {}
    for ticker, key in [("GC=F", "gold"), ("CL=F", "crude_wti"), ("HG=F", "copper"),
                        ("SI=F", "silver"), ("NG=F", "natgas")]:
        if ticker in yd and yd[ticker].get("history"):
            hist = yd[ticker]["history"]
            price = yd[ticker]["latest_value"]
            if len(hist) >= 26:
                ma13 = sum(h["value"] for h in hist[-13:]) / 13
                ma26 = sum(h["value"] for h in hist[-26:]) / 26
                above_13 = price > ma13
                above_26 = price > ma26
                if above_13 and above_26:
                    momentum = "strong_uptrend"
                elif above_26 and not above_13:
                    momentum = "weakening"
                elif not above_26 and above_13:
                    momentum = "recovering"
                else:
                    momentum = "downtrend"
                commodity_momentum[key] = {
                    "price": price,
                    "ma_13w": round(ma13, 2),
                    "ma_26w": round(ma26, 2),
                    "above_13w_ma": above_13,
                    "above_26w_ma": above_26,
                    "momentum": momentum,
                    "pct_above_26w_ma": round((price - ma26) / ma26 * 100, 2),
                }
    if commodity_momentum:
        derived["commodity_momentum"] = commodity_momentum

    # 3. Inventory-to-sales ratios (already in weekly FRED, compute trend here)
    #    Rising I/S = demand weakening or overproduction (bearish for supply-tightness thesis)
    #    Falling I/S = inventory drawdown (bullish for supply-tightness thesis)
    inv_sales = {}
    for sid, label in [("RETAILIRSA", "retail"), ("MNFCTRIRSA", "manufacturing"),
                       ("WHLSLRIRSA", "wholesale")]:
        if sid in fd:
            val = fd[sid]["latest_value"]
            trend = compute_rolling_trend(fd[sid].get("history", []), windows=(4, 8))
            inv_sales[label] = {
                "ratio": val,
                "date": fd[sid]["latest_date"],
                "trend": trend,
                "signal": "drawing" if trend and trend.get("8w", {}).get("direction") == "contraction_bias"
                         else "building" if trend and trend.get("8w", {}).get("direction") == "expansion_bias"
                         else "stable"
            }
    if inv_sales:
        derived["inventory_to_sales"] = inv_sales

    return derived


def build_summary_snapshot(fred_data, yahoo_data, derived, cot_data=None, ecb_data=None, eurostat_data=None,
                           eia_data=None, bis_data=None, oecd_data=None, weo_data=None,
                           gli_data=None, property_data=None, wb_data=None):
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
        "commodities": {},
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
    if "liquidity_trends" in derived:
        snapshot["liquidity"]["trends"] = derived["liquidity_trends"]

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
                         ("BKLN", "bkln_leveraged_loans"),
                         ("BIZD", "bizd_bdc_income")]:
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

    # Commodity structural signals (for Skill 13)
    if "crude_term_structure" in derived:
        snapshot["commodities"]["term_structure"] = derived["crude_term_structure"]
    if "commodity_momentum" in derived:
        snapshot["commodities"]["momentum"] = derived["commodity_momentum"]
    if "inventory_to_sales" in derived:
        snapshot["commodities"]["inventory_to_sales"] = derived["inventory_to_sales"]

    # EIA Petroleum Data (for Skill 13 — energy structural signals)
    eia = eia_data.get("data", {}) if eia_data else {}
    if eia:
        energy = {}
        if "WCESTUS1" in eia:
            energy["crude_inventory_mbbls"] = {
                "value": eia["WCESTUS1"]["latest_value"],
                "date": eia["WCESTUS1"]["latest_date"],
                "prior": eia["WCESTUS1"].get("prior_value"),
            }
        if "WCSSTUS1" in eia:
            spr = eia["WCSSTUS1"]["latest_value"]
            # SPR thresholds calibrated 2025-03 (pre-2022 baseline ~600M; post-drawdown ~350-400M)
            energy["spr_inventory_mbbls"] = {
                "value": spr,
                "date": eia["WCSSTUS1"]["latest_date"],
                "signal": "depleted" if spr < 350 else "low" if spr < 450 else "adequate" if spr < 600 else "full",
            }
        if "WPULEUS3" in eia:
            util = eia["WPULEUS3"]["latest_value"]
            # Refinery utilization thresholds calibrated 2025-03 (nameplate max ~97%; sustained >95% unusual)
            energy["refinery_utilization_pct"] = {
                "value": util,
                "date": eia["WPULEUS3"]["latest_date"],
                "signal": "at_ceiling" if util > 95 else "tight" if util > 92 else "normal" if util > 85 else "weak",
            }
        if "WCESTUS1" in eia and "WRPUPUS2" in eia:
            inv = eia["WCESTUS1"]["latest_value"]
            demand = eia["WRPUPUS2"]["latest_value"]
            if demand and demand > 0:
                # Days of supply = inventory (thousands of barrels) / daily demand
                # WRPUPUS2 is in thousands of barrels per day
                days = round(inv / demand, 1)
                # Days-of-supply thresholds calibrated 2025-03 (DOE typical: 20-30 days; sub-20 historically rare)
                energy["days_of_supply"] = {
                    "value": days,
                    "signal": "critically_low" if days < 20 else "tight" if days < 25 else "adequate" if days < 30 else "comfortable",
                }
        if energy:
            snapshot["energy"] = energy

    # BIS Credit Data (for Skill 13 — international structural context)
    bis = bis_data.get("data", {}) if bis_data else {}
    if bis:
        intl = {}
        for country_code, data in bis.items():
            intl[f"credit_gap_{country_code.lower()}"] = {
                "country": data["country"],
                "credit_gap_pp": data["credit_gap_pp"],
                "signal": data["signal"],
                "direction": data["direction"],
                "date": data["latest_date"],
            }
        if intl:
            snapshot["international_structural"] = intl

    # OECD Composite Leading Indicators — global cycle assessment
    if oecd_data and oecd_data.get("data"):
        oecd = oecd_data["data"]
        li = {}
        for country_code, cdata in oecd.items():
            li[f"oecd_cli_{country_code.lower()}"] = {
                "country": cdata["country"],
                "value": cdata["value"],
                "direction": cdata["direction"],
                "date": cdata["date"],
                "mom_change": cdata["mom_change"],
                "revised": cdata.get("revised", False),
            }
        # Add global divergence assessment
        divergence = oecd_data.get("divergence", {})
        if divergence:
            li["global_divergence"] = divergence
        if li:
            snapshot["leading_indicators"] = li

    # IMF WEO consensus forecasts — sanity check for Skill 6 forecasts
    if weo_data and weo_data.get("data"):
        weo = weo_data["data"]
        cf = {
            "imf_weo_vintage": weo_data.get("vintage", "unknown"),
            "stale": weo_data.get("stale", False),
            "months_since_vintage": weo_data.get("months_since_vintage", 0),
        }
        for country_code, cdata in weo.items():
            cf[country_code.lower()] = cdata
        snapshot["consensus_forecasts"] = cf

    # BIS Global Liquidity Indicators — global dollar liquidity channel
    try:
        if gli_data and gli_data.get("data"):
            gli = gli_data["data"]
            gli_section = {}
            for agg_code, adata in gli.items():
                gli_section[agg_code.lower()] = {
                    "aggregate": adata["aggregate"],
                    "yoy_growth_pct": adata["yoy_growth_pct"],
                    "signal": adata["signal"],
                    "direction": adata["direction"],
                    "date": adata["date"],
                }
            gli_section["ae_emde_divergence"] = gli_data.get("ae_emde_divergence", False)
            snapshot.setdefault("international_structural", {})["global_liquidity"] = gli_section
    except Exception as e:
        pass  # GLI failure must not corrupt international_structural

    # BIS Residential Property Prices — financial stability monitoring
    try:
        if property_data and property_data.get("data"):
            prop = property_data["data"]
            for country_code, cdata in prop.items():
                snapshot.setdefault("international_structural", {})[f"property_{country_code.lower()}"] = {
                    "country": cdata["country"],
                    "yoy_pct": cdata["yoy_pct"],
                    "percentile": cdata["percentile"],
                    "signal": cdata["signal"],
                    "date": cdata["date"],
                }
            snapshot.setdefault("international_structural", {})["property_systemic"] = {
                "overheating_count": property_data.get("overheating_count", 0),
                "systemic_overheating": property_data.get("systemic_overheating", False),
            }
    except Exception as e:
        pass  # Property failure must not corrupt international_structural

    # World Bank structural indicators — demographics + external balances
    try:
        if wb_data and wb_data.get("data"):
            wb = wb_data["data"]
            demographics = {}
            external = {}
            aging_hotspots = []
            twin_deficit = []

            for country_code, cdata in wb.items():
                cc = country_code.lower()
                demo = {"country": cdata.get("country", country_code)}
                ext = {"country": cdata.get("country", country_code)}

                for field in ["pop_65plus_pct", "labor_participation_pct"]:
                    if field in cdata:
                        demo[field] = cdata[field]
                        demo[f"{field}_year"] = cdata.get(f"{field}_year", "")
                for field in ["credit_private_pct_gdp", "current_account_pct_gdp",
                              "trade_openness_pct_gdp", "gdp_per_capita_ppp",
                              "gini", "external_debt_pct_gni"]:
                    if field in cdata:
                        ext[field] = cdata[field]
                        ext[f"{field}_year"] = cdata.get(f"{field}_year", "")

                if len(demo) > 1:
                    demographics[cc] = demo
                if len(ext) > 1:
                    external[cc] = ext

                # Flag aging hotspots (65+ > 25%)
                if cdata.get("pop_65plus_pct", 0) > 25:
                    aging_hotspots.append(country_code)
                # Flag current account deficit (< -2% GDP). Note: true "twin deficit"
                # also requires fiscal deficit, which isn't in WB indicators yet.
                if (cdata.get("current_account_pct_gdp") is not None
                        and cdata["current_account_pct_gdp"] < -2):
                    twin_deficit.append(country_code)

            if demographics:
                demographics["aging_hotspots"] = aging_hotspots
                snapshot["structural_demographics"] = demographics
            if external:
                external["twin_deficit_warning"] = twin_deficit
                snapshot["structural_external"] = external
    except Exception as e:
        pass  # WB failure must not corrupt snapshot

    # Derived signals (the most useful section for skills)
    snapshot["derived_signals"] = derived

    return snapshot


def main():
    parser = argparse.ArgumentParser(description="Macro Advisor Data Collector")
    parser.add_argument("--fred-key", required=True, help="FRED API key")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--mode", choices=["weekly", "historical"], default="weekly",
                       help="weekly = 26-week lookback (default), historical = 5-year lookback")
    parser.add_argument("--skip-eia", action="store_true",
                       help="Skip EIA petroleum data download (saves ~30-60s if not needed)")
    parser.add_argument("--series", default=None,
                       help="Comma-separated FRED series IDs for targeted pull (e.g., 'FYFSD,FGEXPND,A091RC1Q027SBEA'). "
                            "When specified, only these series are fetched (no Yahoo, no derived metrics). "
                            "Used by Skill 11 for on-demand research data.")
    parser.add_argument("--run-log", default=None, help="Path to JSONL run log (optional)")
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

    # 6. EIA Petroleum Data (free, no key — via bulk download)
    eia_data = None
    if not args.skip_eia:
        eia_weeks = 52 if args.mode == "weekly" else 260
        print("Fetching EIA petroleum data (eia.gov bulk download)...")
        eia_data = fetch_eia_data(eia_weeks)
        if eia_data:
            n = len(eia_data["data"])
            e = len(eia_data["errors"])
            print(f"  EIA: {n} series fetched, {e} errors")
            if eia_data["errors"]:
                for err in eia_data["errors"]:
                    print(f"    - {err}")
        else:
            print("  EIA: no data returned (bulk download may have failed)")
    else:
        print("EIA: skipped (--skip-eia flag)")

    # 7. BIS Credit Data (free, no key — CSV download)
    print("Fetching BIS credit-to-GDP data (bis.org)...")
    bis_data = fetch_bis_credit_data()
    if bis_data:
        n = len(bis_data["data"])
        e = len(bis_data["errors"])
        print(f"  BIS: {n} country series fetched, {e} errors")
        if bis_data["errors"]:
            for err in bis_data["errors"]:
                print(f"    - {err}")

    # 8. OECD Composite Leading Indicators (free, no key — SDMX REST API)
    print("Fetching OECD CLI data (sdmx.oecd.org)...")
    oecd_data = fetch_oecd_cli_data()
    if oecd_data:
        n = len(oecd_data["data"])
        e = len(oecd_data["errors"])
        print(f"  OECD CLI: {n} country series fetched, {e} errors")
        if oecd_data.get("divergence"):
            div = oecd_data["divergence"]
            print(f"  Global cycle: US vs world = {div['us_vs_world']}, "
                  f"{div['economies_decelerating']} decelerating")
        if oecd_data["errors"]:
            for err in oecd_data["errors"]:
                print(f"    - {err}")
    else:
        print("  OECD CLI: no data returned (API may be unavailable)")

    # 9. IMF WEO Forecasts (free, no key — DataMapper API)
    print("Fetching IMF WEO data (imf.org DataMapper)...")
    weo_data = fetch_imf_weo_data()
    if weo_data:
        n = len(weo_data["data"])
        e = len(weo_data["errors"])
        stale_tag = " [STALE]" if weo_data.get("stale") else ""
        print(f"  WEO: {n} country forecasts fetched, vintage: {weo_data.get('vintage', '?')}{stale_tag}, {e} errors")
        if weo_data["errors"]:
            for err in weo_data["errors"]:
                print(f"    - {err}")
    else:
        print("  WEO: no data returned (API may be unavailable)")

    # 10. BIS Global Liquidity Indicators (free, no key — SDMX REST API)
    print("Fetching BIS GLI data (stats.bis.org)...")
    gli_data = fetch_bis_gli_data()
    if gli_data and gli_data.get("data"):
        n = len(gli_data["data"])
        e = len(gli_data["errors"])
        total = gli_data["data"].get("4T", {})
        if total:
            print(f"  BIS GLI: {n} aggregates fetched, USD credit YoY: {total.get('yoy_growth_pct', '?')}% ({total.get('signal', '?')}), {e} errors")
        else:
            print(f"  BIS GLI: {n} aggregates fetched, {e} errors")
        if gli_data.get("ae_emde_divergence"):
            print(f"  AE/EMDE divergence detected (>3pp gap)")
        if gli_data["errors"]:
            for err in gli_data["errors"]:
                print(f"    - {err}")
    else:
        gli_data = None
        print("  BIS GLI: no data returned (API may be unavailable)")

    # 11. BIS Residential Property Prices (free, no key — SDMX REST API)
    print("Fetching BIS property price data (stats.bis.org)...")
    property_data = fetch_bis_property_data()
    if property_data and property_data.get("data"):
        n = len(property_data["data"])
        e = len(property_data["errors"])
        oh = property_data.get("overheating_count", 0)
        print(f"  BIS Property: {n} countries fetched, {oh} overheating, {e} errors")
        if property_data.get("systemic_overheating"):
            print(f"  WARNING: Systemic overheating ({oh} economies above 90th percentile)")
        if property_data["errors"]:
            for err in property_data["errors"]:
                print(f"    - {err}")
    else:
        property_data = None
        print("  BIS Property: no data returned (API may be unavailable)")

    # 12. World Bank Structural Indicators (free, no key — REST API)
    print("Fetching World Bank structural data (api.worldbank.org)...")
    wb_data = fetch_worldbank_structural_data()
    if wb_data and wb_data.get("data"):
        n = len(wb_data["data"])
        e = len(wb_data["errors"])
        print(f"  World Bank: {n} countries fetched, {e} errors")
        if wb_data["errors"]:
            for err in wb_data["errors"][:5]:
                print(f"    - {err}")
            if e > 5:
                print(f"    ... and {e - 5} more")
    else:
        wb_data = None
        print("  World Bank: no data returned (API may be unavailable)")

    # 13. Derived metrics
    print("Computing derived metrics...")
    derived = compute_derived_metrics(fred_data, yahoo_data)
    print(f"  Derived: {len(derived)} metrics computed")

    # 13b. Range validation — catch garbage data before it propagates
    print("Validating data ranges...")
    data_anomalies = validate_data_ranges(fred_data, yahoo_data)
    if data_anomalies:
        print(f"  WARNING: {len(data_anomalies)} value(s) outside plausible range:")
        for a in data_anomalies:
            print(f"    - {a['source']} {a['series']} ({a['description']}): "
                  f"{a['value']} (expected {a['expected_range'][0]}–{a['expected_range'][1]}) "
                  f"[{a['severity']}]")
    else:
        print("  All values within plausible ranges")

    # 13c. Z-score tension detection — flag statistically unusual macro readings
    # Lets the DATA decide which domains deserve structural scanner attention,
    # rather than relying solely on Skill 13's 7 prompt-defined detector categories.
    # Uses dual baseline: short-term (current window) + long-term (accumulated across runs).
    print("Computing z-score tensions...")
    zscore_baseline = load_zscore_baseline(output_dir)
    if zscore_baseline:
        baseline_counts = [e["count"] for e in zscore_baseline.values()]
        baseline_active = sum(1 for c in baseline_counts if c >= 20)
        print(f"  Loaded running baseline ({len(baseline_counts)} series tracked, "
              f"{baseline_active} active (20+ obs), max {max(baseline_counts)} obs)")
    else:
        print("  No running baseline yet (first run, long-term z-scores disabled)")

    zscore_tensions, series_values = compute_zscore_tensions(
        fred_data, yahoo_data, data_anomalies, baseline=zscore_baseline)

    # Update and save baseline with this run's values
    zscore_baseline = update_zscore_baseline(zscore_baseline, series_values)
    save_zscore_baseline(zscore_baseline, output_dir)
    print(f"  Baseline updated: {len(series_values)} series, {len(zscore_baseline)} total tracked")

    if zscore_tensions:
        print(f"  Tensions flagged: {len(zscore_tensions)} series above 2σ threshold")
        for t in zscore_tensions[:5]:  # Show top 5
            parts = [f"level={t['level_zscore']:+.1f}σ"]
            if t.get("long_term_zscore") is not None:
                parts.append(f"lt={t['long_term_zscore']:+.1f}σ({t['long_term_baseline_n']}obs)")
            if t["roc_zscore"] is not None:
                parts.append(f"roc={t['roc_zscore']:+.1f}σ")
            print(f"    - {t['series']} ({t['description']}): {', '.join(parts)} [{t['flag_reason']}]")
        if len(zscore_tensions) > 5:
            print(f"    ... and {len(zscore_tensions) - 5} more")
    else:
        print("  No macro series outside 2σ threshold")

    # 14. Snapshot
    print("Building summary snapshot...")
    snapshot = build_summary_snapshot(fred_data, yahoo_data, derived, cot_data, ecb_data, eurostat_data,
                                     eia_data=eia_data, bis_data=bis_data,
                                     oecd_data=oecd_data, weo_data=weo_data,
                                     gli_data=gli_data, property_data=property_data, wb_data=wb_data)

    # 15. Save
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
        "eia": eia_data,
        "bis": bis_data,
        "oecd": oecd_data,
        "weo": weo_data,
        "gli": gli_data,
        "property": property_data,
        "wb": wb_data,
        "derived": derived,
        "data_anomalies": data_anomalies,
        "zscore_tensions": zscore_tensions,
        "snapshot": snapshot,
    }

    # Embed anomalies and z-score tensions in snapshot — this is what skills read first
    if data_anomalies:
        snapshot["data_anomalies"] = data_anomalies
    if zscore_tensions:
        snapshot["zscore_tensions"] = zscore_tensions

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
    total_eia = len(eia_data["data"]) if eia_data else 0
    total_bis = len(bis_data["data"]) if bis_data else 0
    total = total_fred + total_yahoo + total_cot + total_ecb + total_eurostat + total_eia + total_bis
    total_err = sum(len(d.get("errors", [])) for d in [fred_data, yahoo_data, cot_data, ecb_data, eurostat_data, eia_data, bis_data] if d)

    print(f"\n=== Collection Complete ===")
    print(f"Series fetched: {total} (FRED: {total_fred}, Yahoo: {total_yahoo}, COT: {total_cot}, ECB: {total_ecb}, Eurostat: {total_eurostat}, EIA: {total_eia}, BIS: {total_bis})")
    print(f"Errors: {total_err}")
    print(f"Derived metrics: {len(derived)}")
    print(f"Range anomalies: {len(data_anomalies)}" + (" ⚠" if data_anomalies else ""))
    print(f"Z-score tensions: {len(zscore_tensions)}" + (f" (top: {zscore_tensions[0]['series']})" if zscore_tensions else ""))
    print(f"Success rate: {total / max(total + total_err, 1) * 100:.1f}%")
    print(f"Files: {full_path.name}, {snapshot_path.name}")

    # Log to run log if provided
    run_log = Path(args.run_log) if args.run_log else None
    all_errors_list = []
    for src_name, src_data in [("FRED", fred_data), ("Yahoo", yahoo_data), ("COT", cot_data),
                                ("ECB", ecb_data), ("Eurostat", eurostat_data), ("EIA", eia_data),
                                ("BIS", bis_data), ("OECD", oecd_data), ("WEO", weo_data)]:
        if src_data and src_data.get("errors"):
            all_errors_list.extend(f"{src_name}: {e}" for e in src_data["errors"][:3])

    msg = (f"Collection complete: {total} series fetched, {total_err} errors, "
           f"{len(data_anomalies)} anomalies, {len(zscore_tensions)} tensions")
    _log_event(run_log, "INFO", "data-collector", msg,
               details={"series": total, "errors": total_err,
                        "anomalies": len(data_anomalies),
                        "tensions": len(zscore_tensions)})
    if total_err > 0:
        _log_event(run_log, "WARN", "data-collector",
                   f"{total_err} collection error(s)",
                   details={"error_samples": all_errors_list[:10]})
    if data_anomalies:
        _log_event(run_log, "WARN", "data-collector",
                   f"{len(data_anomalies)} data range anomaly(ies) detected",
                   details={"anomalies": [a["series"] for a in data_anomalies[:5]]})

    return 0 if total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
