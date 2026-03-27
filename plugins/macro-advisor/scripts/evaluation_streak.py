#!/usr/bin/env python3
"""Compute the regime evaluation divergence streak from evaluation history.

This script is the authoritative source for "consecutive weeks the blind
classification diverged from Skill 6." The LLM must NOT compute this
count itself — it reads this script's output.

Mirrors the pattern of regime_week_count.py.

Usage:
    python evaluation_streak.py --history outputs/synthesis/regime-evaluation-history.json

Output (stdout):
    JSON object with consecutive_divergence_weeks and context.
"""

import argparse
import json
import sys
from pathlib import Path


def compute_streak(history_path: str) -> dict:
    path = Path(history_path)

    if not path.exists():
        return {
            "consecutive_divergence_weeks": 0,
            "last_blind_regime": "Unknown",
            "last_skill6_regime": "Unknown",
            "note": "No evaluation history found. First run of Skill 6b."
        }

    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {
            "consecutive_divergence_weeks": 0,
            "last_blind_regime": "Unknown",
            "last_skill6_regime": "Unknown",
            "note": f"Failed to read evaluation history: {e}."
        }

    if not entries or not isinstance(entries, list):
        return {
            "consecutive_divergence_weeks": 0,
            "last_blind_regime": "Unknown",
            "last_skill6_regime": "Unknown",
            "note": "Evaluation history is empty. First run of Skill 6b."
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
            "consecutive_divergence_weeks": 0,
            "last_blind_regime": "Unknown",
            "last_skill6_regime": "Unknown",
            "note": "No valid week entries found."
        }

    # Count trailing streak of divergence
    streak = 0
    for week_key in reversed(sorted_weeks):
        entry = by_week[week_key]
        if entry.get("diverged", False):
            streak += 1
        else:
            break

    latest = by_week[sorted_weeks[-1]]

    return {
        "consecutive_divergence_weeks": streak,
        "last_blind_regime": latest.get("blind_regime", "Unknown"),
        "last_skill6_regime": latest.get("skill6_regime", "Unknown"),
        "last_verdict": latest.get("verdict", "Unknown"),
        "weeks_in_history": len(sorted_weeks),
        "note": f"Prior {streak} consecutive week(s) of divergence. "
                f"Last blind call: {latest.get('blind_regime', '?')}, "
                f"last Skill 6 call: {latest.get('skill6_regime', '?')}."
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compute regime evaluation divergence streak"
    )
    parser.add_argument(
        "--history", required=True,
        help="Path to regime-evaluation-history.json"
    )
    args = parser.parse_args()

    result = compute_streak(args.history)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
