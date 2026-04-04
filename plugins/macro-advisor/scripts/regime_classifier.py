#!/usr/bin/env python3
"""
Regime Classifier — Deterministic weekly regime classification.

Reads latest-data-full.json (with regime_history fields from data_collector.py),
computes growth/inflation/liquidity scores using the shared regime_core module,
applies the 2-month confirmation filter, and writes regime-classifier-output.json.

This output serves as the deterministic reference for Skill 6b (Regime Evaluator).
Skill 6 does NOT see this output — it classifies independently to preserve
evaluator independence.

Usage:
    python regime_classifier.py --data-dir outputs/data/
"""

import argparse
import json
import sys
import warnings
from datetime import datetime
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


def parse_regime_history(data_full):
    """
    Parse regime_history fields from latest-data-full.json into pandas Series
    suitable for build_monthly_df.

    Returns dict of {series_id: pd.Series} with DatetimeIndex.
    """
    fred = data_full.get("fred", {}).get("data", {})
    series = {}

    for sid in ["INDPRO", "UNRATE", "RSAFS", "PAYEMS", "CPIAUCSL", "CPILFESL",
                "M2SL", "NFCI", "WALCL"]:
        entry = fred.get(sid, {})
        history = entry.get("regime_history")
        if not history:
            print(f"  WARNING: {sid} has no regime_history — skipping")
            continue

        dates = [pd.Timestamp(h["date"]) for h in history]
        values = [h["value"] for h in history]
        s = pd.Series(values, index=dates, dtype=float, name=sid)
        s = s.sort_index()
        series[sid] = s

    return series


def load_confirmation_state(data_dir):
    """
    Load the prior confirmed regime from regime-history.json
    for the confirmation filter's initial state.

    Returns the most recent regime_family string, or None if unavailable.
    """
    history_path = data_dir / "regime-history.json"
    if not history_path.exists():
        return None

    try:
        with open(history_path) as f:
            history = json.load(f)
        if isinstance(history, list) and len(history) > 0:
            # Most recent entry
            last = history[-1]
            return last.get("regime_family") or last.get("regime")
        return None
    except Exception as e:
        print(f"  WARNING: Could not read regime-history.json: {e}")
        return None


def build_signal_details(monthly, growth_signals, liq_signals, liq_medians):
    """Build the detailed signal breakdown for the output JSON."""
    # Growth signals
    growth_detail = {}
    for col in growth_signals.columns:
        val = growth_signals[col].iloc[-1]
        if col == "indpro" and "indpro_yoy" in monthly.columns:
            yoy_cur = monthly["indpro_yoy"].iloc[-1]
            yoy_6m = monthly["indpro_yoy"].iloc[-7] if len(monthly) > 6 else None
            growth_detail["indpro"] = {
                "value": int(val) if pd.notna(val) else None,
                "yoy_current": round(yoy_cur, 2) if pd.notna(yoy_cur) else None,
                "yoy_6m_ago": round(yoy_6m, 2) if yoy_6m is not None and pd.notna(yoy_6m) else None,
                "direction": "rising" if val > 0 else "falling" if val < 0 else "flat",
            }
        elif col == "unrate" and "unrate" in monthly.columns:
            lvl_cur = monthly["unrate"].iloc[-1]
            lvl_6m = monthly["unrate"].iloc[-7] if len(monthly) > 6 else None
            growth_detail["unrate"] = {
                "value": int(val) if pd.notna(val) else None,
                "level_current": round(lvl_cur, 2) if pd.notna(lvl_cur) else None,
                "level_6m_ago": round(lvl_6m, 2) if lvl_6m is not None and pd.notna(lvl_6m) else None,
                "direction": "falling_good" if val > 0 else "rising_bad" if val < 0 else "flat",
            }
        elif col == "retail" and "retail_yoy" in monthly.columns:
            yoy_cur = monthly["retail_yoy"].iloc[-1]
            yoy_6m = monthly["retail_yoy"].iloc[-7] if len(monthly) > 6 else None
            growth_detail["retail"] = {
                "value": int(val) if pd.notna(val) else None,
                "yoy_current": round(yoy_cur, 2) if pd.notna(yoy_cur) else None,
                "yoy_6m_ago": round(yoy_6m, 2) if yoy_6m is not None and pd.notna(yoy_6m) else None,
                "direction": "rising" if val > 0 else "falling" if val < 0 else "flat",
            }
        elif col == "payrolls" and "payrolls_yoy" in monthly.columns:
            yoy_cur = monthly["payrolls_yoy"].iloc[-1]
            yoy_6m = monthly["payrolls_yoy"].iloc[-7] if len(monthly) > 6 else None
            growth_detail["payrolls"] = {
                "value": int(val) if pd.notna(val) else None,
                "yoy_current": round(yoy_cur, 2) if pd.notna(yoy_cur) else None,
                "yoy_6m_ago": round(yoy_6m, 2) if yoy_6m is not None and pd.notna(yoy_6m) else None,
                "direction": "rising" if val > 0 else "falling" if val < 0 else "flat",
            }

    # Inflation signals
    inflation_detail = {}
    if "cpi_yoy" in monthly.columns:
        cpi_6m = monthly["cpi_yoy"].diff(6).iloc[-1]
        inflation_detail["cpi_yoy_6m_change"] = round(cpi_6m, 4) if pd.notna(cpi_6m) else None
    if "core_cpi_yoy" in monthly.columns:
        core_6m = monthly["core_cpi_yoy"].diff(6).iloc[-1]
        inflation_detail["core_cpi_yoy_6m_change"] = round(core_6m, 4) if pd.notna(core_6m) else None
    inflation_detail["blended"] = round(monthly["inflation_score"].iloc[-1], 4) if "inflation_score" in monthly.columns else None

    # Liquidity signals
    liq_detail = {}
    for col in liq_signals.columns:
        val = liq_signals[col].iloc[-1] if len(liq_signals) > 0 else None
        med = liq_medians.get(col)
        med_val = med.iloc[-1] if med is not None and len(med) > 0 else None

        if col == "m2" and "m2_yoy" in monthly.columns:
            liq_detail["m2"] = {
                "value": int(val) if pd.notna(val) else None,
                "current_yoy": round(monthly["m2_yoy"].iloc[-1], 2),
                "median_36m": round(med_val, 2) if med_val is not None and pd.notna(med_val) else None,
                "vs_median": "above" if val == 1 else "below" if val == 0 else "unknown",
            }
        elif col == "nfci" and "nfci" in monthly.columns:
            liq_detail["nfci"] = {
                "value": int(val) if pd.notna(val) else None,
                "current": round(monthly["nfci"].iloc[-1], 4),
                "median_36m": round(med_val, 4) if med_val is not None and pd.notna(med_val) else None,
                "vs_median": "below_loose" if val == 1 else "above_tight" if val == 0 else "unknown",
            }
        elif col == "fed_bs" and "fed_assets_yoy" in monthly.columns:
            liq_detail["fed_bs"] = {
                "value": int(val) if pd.notna(val) else None,
                "current_yoy": round(monthly["fed_assets_yoy"].iloc[-1], 2),
                "median_36m": round(med_val, 2) if med_val is not None and pd.notna(med_val) else None,
                "vs_median": "above" if val == 1 else "below" if val == 0 else "unknown",
            }

    return growth_detail, inflation_detail, liq_detail


def main():
    parser = argparse.ArgumentParser(description="Deterministic regime classifier")
    parser.add_argument("--data-dir", required=True, help="Directory with latest-data-full.json")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    data_file = data_dir / "latest-data-full.json"

    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        return 1

    print("=== Regime Classifier ===")
    print(f"  Reading {data_file}")

    with open(data_file) as f:
        data_full = json.load(f)

    # Parse regime_history into pandas Series
    fred_series = parse_regime_history(data_full)
    if len(fred_series) < 3:
        print(f"ERROR: Only {len(fred_series)} regime series available (need at least 3)")
        return 1

    print(f"  Parsed {len(fred_series)} regime series")

    # Build monthly DataFrame using shared core
    monthly = build_monthly_df(fred_series)
    if len(monthly) < 7:
        print(f"ERROR: Only {len(monthly)} months of data (need at least 7 for 6-month window)")
        return 1

    print(f"  Monthly DataFrame: {len(monthly)} months ({monthly.index[0].strftime('%Y-%m')} to {monthly.index[-1].strftime('%Y-%m')})")

    # Compute scores
    growth_score, growth_signals = compute_growth_score(monthly)
    monthly["growth_score"] = growth_score
    monthly["growth_direction"] = compute_growth_direction(growth_score)

    monthly["inflation_score"] = compute_inflation_score(monthly)
    monthly["inflation_direction"] = compute_inflation_direction(monthly["inflation_score"])

    liq_score, liq_signals, liq_medians = compute_liquidity_score(monthly)
    monthly["liquidity_score"] = liq_score
    monthly["liquidity_binary"] = classify_liquidity(liq_score)

    # Raw regime assignment
    monthly["regime_raw"] = assign_regime_family(
        monthly["growth_direction"], monthly["inflation_direction"]
    )

    # Apply confirmation filter with prior state
    prior_confirmed = load_confirmation_state(data_dir)
    if prior_confirmed:
        print(f"  Prior confirmed regime: {prior_confirmed}")

    confirmed = apply_confirmation_filter(
        monthly["regime_raw"].tolist(),
        initial_confirmed=prior_confirmed
    )
    monthly["regime_confirmed"] = confirmed

    # Current month values
    cur = monthly.iloc[-1]
    cur_growth = round(float(cur["growth_score"]), 4) if pd.notna(cur["growth_score"]) else None
    cur_inflation = round(float(cur["inflation_score"]), 4) if pd.notna(cur["inflation_score"]) else None
    cur_liquidity = round(float(cur["liquidity_score"]), 4) if pd.notna(cur["liquidity_score"]) else None

    regime_family = cur["regime_confirmed"]
    liq_condition = cur["liquidity_binary"] if pd.notna(cur.get("liquidity_binary")) else None

    if regime_family and liq_condition:
        regime_8 = f"{regime_family} — {'Ample' if liq_condition == 'loose' else 'Tight'} Liquidity"
    else:
        regime_8 = regime_family

    # Build signal details
    growth_detail, inflation_detail, liq_detail = build_signal_details(
        monthly, growth_signals, liq_signals, liq_medians
    )

    # Confirmation filter state
    raw_this_month = cur["regime_raw"]
    filter_state = {
        "current_confirmed_regime": regime_family,
        "raw_regime_this_month": raw_this_month,
        "agrees": raw_this_month == regime_family,
    }

    # Build output
    now = datetime.now()
    output = {
        "run_date": now.strftime("%Y-%m-%d"),
        "week": now.strftime("%Y-W%V"),
        "data_through": monthly.index[-1].strftime("%Y-%m-%d"),
        "growth": {
            "score": cur_growth,
            "direction": cur["growth_direction"],
            "signals": growth_detail,
        },
        "inflation": {
            "score": cur_inflation,
            "direction": cur["inflation_direction"],
            "signals": inflation_detail,
        },
        "liquidity": {
            "score": cur_liquidity,
            "condition": liq_condition,
            "signals": liq_detail,
        },
        "regime_family": regime_family,
        "regime_8": regime_8,
        "confirmation_filter": filter_state,
        "methodology": (
            "regime_core.py: 6-month direction window, majority vote growth, "
            "blended CPI/Core inflation, 36-month rolling median liquidity, "
            "2-month confirmation filter"
        ),
    }

    # Write output
    output_file = data_dir / "regime-classifier-output.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Regime: {regime_8}")
    print(f"  Growth: {cur_growth} ({cur['growth_direction']})")
    print(f"  Inflation: {cur_inflation} ({cur['inflation_direction']})")
    print(f"  Liquidity: {cur_liquidity} ({liq_condition})")
    print(f"  Confirmation: raw={raw_this_month}, confirmed={regime_family}")
    print(f"\n  Written to {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
