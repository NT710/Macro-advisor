#!/usr/bin/env python3
"""Compute the regime week streak from regime-history.json.

This script is the authoritative source for "weeks in current regime family."
It reads the regime history file, counts consecutive trailing weeks
with the same regime family (4-quadrant), and prints the result.

The streak counts on `regime_family`, NOT the full 8-regime label.
A liquidity condition change within the same family does NOT reset the streak.

The LLM MUST NOT compute this count itself — it reads this script's output.

Usage:
    python regime_week_count.py --history outputs/regime-history.json

Output (stdout):
    JSON object: {"regime": "Stagflation", "regime_family": "Stagflation", "streak": 3, "note": "..."}

    streak = number of consecutive weeks ending at the most recent entry
             that share the same regime family.

    If the file doesn't exist or is empty, returns streak=0 with a note
    that the LLM should estimate from data trends.
"""

import argparse
import json
import sys
from pathlib import Path


def compute_streak(history_path: str) -> dict:
    path = Path(history_path)

    if not path.exists():
        return {
            "regime": "Unknown",
            "streak": 0,
            "note": "No regime-history.json found. This appears to be the first run. "
                    "Estimate weeks in current regime from the 6-month data trends — "
                    "do NOT default to 1."
        }

    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {
            "regime": "Unknown",
            "streak": 0,
            "note": f"Failed to read regime-history.json: {e}. Estimate from data trends."
        }

    if not entries or not isinstance(entries, list):
        return {
            "regime": "Unknown",
            "streak": 0,
            "note": "regime-history.json is empty. First run — estimate from data trends."
        }

    # Deduplicate by week (keep last entry per week, in case of reruns)
    by_week = {}
    for entry in entries:
        week = entry.get("week", "")
        if week:
            by_week[week] = entry

    # Sort by week string (ISO week strings sort chronologically)
    sorted_weeks = sorted(by_week.keys())
    if not sorted_weeks:
        return {
            "regime": "Unknown",
            "streak": 0,
            "note": "No valid week entries found. Estimate from data trends."
        }

    # Count trailing streak of same regime family
    # Use regime_family if available (8-regime model), fall back to regime (4-regime legacy)
    latest = by_week[sorted_weeks[-1]]
    current_family = latest.get("regime_family", latest.get("regime", "Unknown"))
    current_regime = latest.get("regime", current_family)
    streak = 0

    for week_key in reversed(sorted_weeks):
        entry = by_week[week_key]
        entry_family = entry.get("regime_family", entry.get("regime", ""))
        if entry_family == current_family:
            streak += 1
        else:
            break

    return {
        "regime": current_regime,
        "regime_family": current_family,
        "streak": streak,
        "weeks_covered": sorted_weeks[-streak:] if streak > 0 else [],
        "note": f"The prior {streak} week(s) were {current_family} (family). "
                f"If this week is also {current_family}, weeks_in_regime = {streak + 1}. "
                f"If the regime family changed, weeks_in_regime = 1. "
                f"Liquidity condition changes within the same family do NOT reset the streak."
    }


def main():
    parser = argparse.ArgumentParser(description="Compute regime week streak")
    parser.add_argument("--history", required=True, help="Path to regime-history.json")
    args = parser.parse_args()

    result = compute_streak(args.history)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
