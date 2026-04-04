#!/usr/bin/env python3
"""
Regime Core — Shared classification functions for the 8-regime macro model.

Used by:
  - regime_backtest.py (historical validation)
  - regime_classifier.py (weekly deterministic classification)

Growth × Inflation × Liquidity → 8 regimes.
All functions are pure pandas logic with no I/O.
"""

import numpy as np
import pandas as pd


# Direction window for growth/inflation classification.
# 6-month window identifies structural direction, not monthly noise.
DIRECTION_WINDOW = 6

# Confirmation filter: new regime must persist this many consecutive months.
CONFIRMATION_MONTHS = 2

# Rolling window for liquidity median (months).
LIQUIDITY_ROLLING_WINDOW = 36
LIQUIDITY_MIN_PERIODS = 12


def build_monthly_df(fred_data):
    """
    Build a monthly-aligned DataFrame from FRED series data.

    Args:
        fred_data: dict of {series_id: pd.Series} with DatetimeIndex.
            Expected keys: INDPRO, UNRATE, RSAFS, PAYEMS, CPIAUCSL, CPILFESL,
                           M2SL, NFCI, WALCL (all optional).

    Returns:
        pd.DataFrame with monthly frequency, columns for YoY changes and levels.
    """
    monthly = pd.DataFrame()

    # Growth axis — YoY % change for level series, raw level for rate series
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

    # Inflation axis
    if "CPIAUCSL" in fred_data:
        s = fred_data["CPIAUCSL"].resample("ME").last().dropna()
        monthly["cpi_yoy"] = s.pct_change(12) * 100

    if "CPILFESL" in fred_data:
        s = fred_data["CPILFESL"].resample("ME").last().dropna()
        monthly["core_cpi_yoy"] = s.pct_change(12) * 100

    # Liquidity axis
    if "M2SL" in fred_data:
        s = fred_data["M2SL"].resample("ME").last().dropna()
        monthly["m2_yoy"] = s.pct_change(12) * 100

    if "NFCI" in fred_data:
        s = fred_data["NFCI"].resample("ME").last().dropna()
        monthly["nfci"] = s

    if "WALCL" in fred_data:
        s = fred_data["WALCL"].resample("ME").last().dropna()
        monthly["fed_assets_yoy"] = s.pct_change(12) * 100

    monthly = monthly.dropna(subset=["cpi_yoy"], how="all")
    return monthly


def _direction_signal(series, window=DIRECTION_WINDOW, invert=False):
    """Convert a series to directional signals (+1, -1, 0) over a diff window."""
    diff = series.diff(window)
    if invert:
        return diff.apply(lambda x: -1 if x > 0 else (1 if x < 0 else 0) if pd.notna(x) else np.nan)
    return diff.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0) if pd.notna(x) else np.nan)


def compute_growth_score(monthly):
    """
    Compute growth score from majority vote of directional signals.

    Returns (score_series, signals_df) where score is the mean of available
    signals (NaN indicators excluded, not counted as 0).
    """
    signals = pd.DataFrame(index=monthly.index)

    if "indpro_yoy" in monthly.columns:
        signals["indpro"] = _direction_signal(monthly["indpro_yoy"])

    if "unrate" in monthly.columns:
        signals["unrate"] = _direction_signal(monthly["unrate"], invert=True)

    if "retail_yoy" in monthly.columns:
        signals["retail"] = _direction_signal(monthly["retail_yoy"])

    if "payrolls_yoy" in monthly.columns:
        signals["payrolls"] = _direction_signal(monthly["payrolls_yoy"])

    # mean with skipna=True: NaN indicators excluded from vote
    score = signals.mean(axis=1)
    return score, signals


def compute_growth_direction(score):
    """Classify growth direction from score. Zero maps to 'falling' (documented bias)."""
    return score.apply(lambda x: "rising" if x > 0 else "falling" if pd.notna(x) else None)


def compute_inflation_score(monthly):
    """
    Compute inflation score from blended CPI/Core CPI 6-month change.

    Returns score_series (positive = rising inflation).
    """
    if "cpi_yoy" not in monthly.columns:
        return pd.Series(np.nan, index=monthly.index)

    cpi_dir = monthly["cpi_yoy"].diff(DIRECTION_WINDOW)
    core_dir = (monthly["core_cpi_yoy"].diff(DIRECTION_WINDOW)
                if "core_cpi_yoy" in monthly.columns else cpi_dir)

    return (cpi_dir.fillna(0) + core_dir.fillna(0)) / 2


def compute_inflation_direction(score):
    """Classify inflation direction. Zero maps to 'falling' (documented bias)."""
    return score.apply(lambda x: "rising" if x > 0 else "falling" if pd.notna(x) else None)


def compute_liquidity_score(monthly):
    """
    Compute liquidity score from majority vote vs 36-month rolling medians.

    Uses RELATIVE thresholds (rolling median), not absolute levels.
    Reason: NFCI is negative post-GFC, M2 was >2% for most of history.
    Absolute thresholds produce 95%+ 'loose' — useless for conditioning.

    Returns (score_series, signals_df, medians_dict).
    """
    signals = pd.DataFrame(index=monthly.index)
    medians = {}

    if "m2_yoy" in monthly.columns:
        med = monthly["m2_yoy"].rolling(LIQUIDITY_ROLLING_WINDOW,
                                         min_periods=LIQUIDITY_MIN_PERIODS).median()
        signals["m2"] = (monthly["m2_yoy"] > med).astype(float)
        signals.loc[med.isna(), "m2"] = np.nan
        medians["m2"] = med

    if "nfci" in monthly.columns:
        med = monthly["nfci"].rolling(LIQUIDITY_ROLLING_WINDOW,
                                       min_periods=LIQUIDITY_MIN_PERIODS).median()
        # NFCI inverted: lower = looser
        signals["nfci"] = (monthly["nfci"] < med).astype(float)
        signals.loc[med.isna(), "nfci"] = np.nan
        medians["nfci"] = med

    if "fed_assets_yoy" in monthly.columns:
        med = monthly["fed_assets_yoy"].rolling(LIQUIDITY_ROLLING_WINDOW,
                                                  min_periods=LIQUIDITY_MIN_PERIODS).median()
        signals["fed_bs"] = (monthly["fed_assets_yoy"] > med).astype(float)
        signals.loc[med.isna(), "fed_bs"] = np.nan
        medians["fed_bs"] = med

    if len(signals.columns) == 0:
        return pd.Series(np.nan, index=monthly.index), signals, medians

    score = signals.mean(axis=1)  # skipna=True by default
    return score, signals, medians


def classify_liquidity(score):
    """Classify liquidity condition from score."""
    return score.apply(
        lambda x: "loose" if x > 0.5 else "tight" if pd.notna(x) else None
    )


def assign_regime_family(growth_direction, inflation_direction):
    """
    Assign 4-quadrant regime family from growth and inflation directions.

    Returns a Series of regime family labels.
    """
    def _assign(g, i):
        if g == "rising" and i == "falling":
            return "Goldilocks"
        elif g == "rising" and i == "rising":
            return "Overheating"
        elif g == "falling" and i == "falling":
            return "Disinflationary Slowdown"
        elif g == "falling" and i == "rising":
            return "Stagflation"
        return None

    return pd.Series(
        [_assign(g, i) for g, i in zip(growth_direction, inflation_direction)],
        index=growth_direction.index
    )


def assign_regime_8(regime_family, liquidity_binary):
    """
    Assign full 8-regime label from family + liquidity condition.

    Returns a Series of 8-regime labels like 'Goldilocks — Ample Liquidity'.
    """
    def _label(fam, liq):
        if pd.isna(fam) or fam is None:
            return None
        if pd.isna(liq) or liq is None:
            return fam  # fall back to 4-quadrant label
        liq_label = "Ample" if liq == "loose" else "Tight"
        return f"{fam} — {liq_label} Liquidity"

    return pd.Series(
        [_label(f, l) for f, l in zip(regime_family, liquidity_binary)],
        index=regime_family.index
    )


def apply_confirmation_filter(raw_regimes, confirmation_months=CONFIRMATION_MONTHS,
                              initial_confirmed=None):
    """
    Apply the 2-month confirmation filter to a sequence of raw regime labels.

    A regime change only registers after `confirmation_months` consecutive months
    of the new classification. Eliminates single-month noise flips.

    Args:
        raw_regimes: iterable of raw regime labels (strings or None).
        confirmation_months: number of consecutive months required to confirm.
        initial_confirmed: starting confirmed regime (for classifier continuity).

    Returns:
        list of confirmed regime labels, same length as raw_regimes.
    """
    confirmed = []
    current_confirmed = initial_confirmed
    pending_regime = None
    pending_count = 0

    for raw in raw_regimes:
        if current_confirmed is None:
            current_confirmed = raw
            pending_regime = None
            pending_count = 0
        elif raw == current_confirmed:
            pending_regime = None
            pending_count = 0
        elif raw == pending_regime:
            pending_count += 1
            if pending_count >= confirmation_months:
                current_confirmed = raw
                pending_regime = None
                pending_count = 0
        else:
            pending_regime = raw
            pending_count = 1

        confirmed.append(current_confirmed)

    return confirmed
