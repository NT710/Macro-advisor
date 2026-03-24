#!/usr/bin/env python3
"""Pre-flight check for the weekly macro run.

Validates that all prerequisites are met before skills execute.
Returns non-zero exit code if any check fails, forcing the orchestration
to address issues before proceeding with stale or missing data.

Checks:
1. Snapshot freshness — latest-snapshot.json must be from today's date
2. Snapshot completeness — key market data fields must be present
3. Config — user-config.json must exist with required fields

Usage:
    python preflight_check.py --output-dir outputs/data/ --config config/user-config.json

Exit codes:
    0 = all checks pass
    1 = snapshot missing or stale (data collector must run first)
    2 = snapshot incomplete (data collector may have partially failed)
    3 = config missing or invalid
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def check_snapshot_freshness(output_dir: Path) -> list[str]:
    """Check that the snapshot exists and was generated today."""
    errors = []
    snapshot_path = output_dir / "latest-snapshot.json"

    if not snapshot_path.exists():
        errors.append(
            f"FAIL: No snapshot found at {snapshot_path}. "
            f"Run the data collector (Skill 0) first."
        )
        return errors

    try:
        snap = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        errors.append(f"FAIL: Cannot read snapshot: {e}")
        return errors

    generated = snap.get("generated", "")
    if not generated:
        errors.append("FAIL: Snapshot has no 'generated' timestamp. Re-run data collector.")
        return errors

    # Parse the generated timestamp
    try:
        gen_dt = datetime.fromisoformat(generated.replace("Z", "+00:00"))
    except ValueError:
        try:
            gen_dt = datetime.strptime(generated[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            errors.append(f"FAIL: Cannot parse snapshot timestamp: {generated}")
            return errors

    now = datetime.now()
    age_hours = (now - gen_dt).total_seconds() / 3600

    # Snapshot must be from today (or at most 18 hours old to handle timezone edge cases)
    if age_hours > 18:
        errors.append(
            f"FAIL: Snapshot is {age_hours:.1f} hours old "
            f"(generated: {generated}). "
            f"Data is STALE. Re-run the data collector before proceeding."
        )

    return errors


def check_snapshot_completeness(output_dir: Path) -> list[str]:
    """Check that key market data fields are present in the snapshot."""
    errors = []
    snapshot_path = output_dir / "latest-snapshot.json"

    if not snapshot_path.exists():
        return []  # already caught by freshness check

    try:
        snap = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []  # already caught by freshness check

    markets = snap.get("markets", {})
    required_markets = ["oil_wti", "sp500", "gold", "vix"]
    missing = [m for m in required_markets if m not in markets or markets[m].get("value") is None]

    if missing:
        errors.append(
            f"WARNING: Snapshot missing key market data: {', '.join(missing)}. "
            f"Data collector may have partially failed. Check Yahoo Finance connectivity."
        )

    # Check that market data dates are recent (within 5 trading days)
    now = datetime.now()
    for key in ["oil_wti", "sp500"]:
        entry = markets.get(key, {})
        date_str = entry.get("date", "")
        if date_str:
            try:
                data_date = datetime.strptime(date_str, "%Y-%m-%d")
                days_old = (now - data_date).days
                if days_old > 5:
                    errors.append(
                        f"WARNING: {key} data is {days_old} days old "
                        f"(date: {date_str}). May be stale."
                    )
            except ValueError:
                pass

    return errors


def check_config(config_path: Path) -> list[str]:
    """Check that user config exists and has required fields."""
    errors = []

    if not config_path.exists():
        errors.append(f"FAIL: Config not found at {config_path}. Run /setup first.")
        return errors

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        errors.append(f"FAIL: Cannot read config: {e}")
        return errors

    if not config.get("fred_api_key"):
        errors.append("FAIL: No FRED API key in config. Run /setup first.")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Pre-flight checks for weekly macro run")
    parser.add_argument("--output-dir", required=True, help="Path to outputs/data/")
    parser.add_argument("--config", required=True, help="Path to config/user-config.json")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    config_path = Path(args.config)

    all_errors = []
    all_warnings = []

    # Run checks
    freshness = check_snapshot_freshness(output_dir)
    completeness = check_snapshot_completeness(output_dir)
    config = check_config(config_path)

    for msg in freshness + completeness + config:
        if msg.startswith("FAIL"):
            all_errors.append(msg)
        else:
            all_warnings.append(msg)

    # Report
    if not all_errors and not all_warnings:
        print("PRE-FLIGHT: All checks passed.")
        try:
            snap = json.loads((output_dir / "latest-snapshot.json").read_text(encoding="utf-8"))
            print(f"  Snapshot generated: {snap.get('generated', 'unknown')}")
            markets = snap.get("markets", {})
            oil = markets.get("oil_wti", {})
            sp = markets.get("sp500", {})
            print(f"  Oil WTI: ${oil.get('value', 'N/A')} (as of {oil.get('date', 'N/A')})")
            print(f"  S&P 500: {sp.get('value', 'N/A')} (as of {sp.get('date', 'N/A')})")
        except Exception:
            pass
        sys.exit(0)

    if all_warnings:
        for w in all_warnings:
            print(w, file=sys.stderr)

    if all_errors:
        for e in all_errors:
            print(e, file=sys.stderr)
        print(
            "\nPRE-FLIGHT FAILED. Fix the issues above before running skills. "
            "Do NOT proceed with stale or missing data.",
            file=sys.stderr
        )
        sys.exit(1)
    else:
        print("PRE-FLIGHT: Passed with warnings (see above).")
        sys.exit(0)


if __name__ == "__main__":
    main()
