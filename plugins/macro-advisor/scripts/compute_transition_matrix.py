#!/usr/bin/env python3
"""
Compute empirical Markov transition probability matrices for the 4-regime
and 8-regime macro models.

For each current regime X, computes the historical probability of transitioning
to each regime Y at 6-month and 12-month horizons. Outputs a JSON file consumed
by Skill 6 to anchor regime forecasts in empirical base rates.

Uses Bayesian shrinkage: 8-regime probabilities are smoothed toward the 4-regime
prior when sample sizes are small, avoiding cliff-edge fallbacks.

Usage:
    python compute_transition_matrix.py --fred-key YOUR_KEY --output-dir ./outputs/data/
    python compute_transition_matrix.py --output-dir ./outputs/data/  # uses FRED_API_KEY env var
    python compute_transition_matrix.py --fred-key YOUR_KEY --output-dir ./outputs/data/ --years 15
"""

import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# Import classification logic from regime_backtest (no duplication)
sys.path.insert(0, str(Path(__file__).parent))
from regime_backtest import fetch_fred_series, classify_regimes, FRED_REGIME_SERIES

HORIZONS = [6, 12]  # months
SHRINKAGE_WEIGHT = 10  # Bayesian shrinkage toward 4-regime prior
POST_COVID_START = "2022-01-01"  # post-COVID window start

# All possible regime labels (for consistent matrix keys)
FOUR_REGIMES = [
    "Goldilocks",
    "Overheating",
    "Disinflationary Slowdown",
    "Stagflation",
]
EIGHT_REGIMES = [
    f"{family} — {liq} Liquidity"
    for family in FOUR_REGIMES
    for liq in ["Ample", "Tight"]
]


def compute_transition_matrix(regime_series, horizon_months, regime_col, all_labels):
    """
    Compute empirical transition probabilities at a given horizon.

    For each month t where regime_col is X, look at month t + horizon_months.
    Record the transition X -> Y.

    Returns:
        matrix: dict[source -> dict[target -> probability]]
        counts: dict[source -> dict[target -> count]]
        total_per_source: dict[source -> total_count]
        low_n_regimes: list of source regimes with N < 10
    """
    series = regime_series[regime_col].dropna()

    # Build transition pairs: (source at t, target at t + horizon)
    # Exclude the last `horizon_months` of data (no forward target)
    shifted = series.shift(-horizon_months)
    valid = series.index[shifted.notna()]

    pairs = pd.DataFrame({
        "source": series.loc[valid].values,
        "target": shifted.loc[valid].values,
    })

    counts = {}
    total_per_source = {}

    for label in all_labels:
        counts[label] = {}
        source_rows = pairs[pairs["source"] == label]
        total_per_source[label] = len(source_rows)

        for target_label in all_labels:
            n = len(source_rows[source_rows["target"] == target_label])
            counts[label][target_label] = n

    # Compute probabilities (handle zero-count sources)
    matrix = {}
    low_n_regimes = []

    for label in all_labels:
        total = total_per_source[label]
        if total == 0:
            # Regime never observed as source: null probabilities
            matrix[label] = {t: None for t in all_labels}
            low_n_regimes.append(label)
            continue

        if total < 10:
            low_n_regimes.append(label)

        matrix[label] = {}
        for target_label in all_labels:
            matrix[label][target_label] = round(
                counts[label][target_label] / total, 4
            )

    return matrix, counts, total_per_source, low_n_regimes


def apply_bayesian_shrinkage(
    eight_matrix, eight_counts, eight_totals,
    four_matrix, regime_family_map,
    all_eight_labels, all_four_labels,
    shrinkage_weight=SHRINKAGE_WEIGHT,
):
    """
    Shrink 8-regime probabilities toward 4-regime prior.

    For each 8-regime cell:
      shrunk = alpha * eight_prob + (1 - alpha) * four_prior
      alpha = N_eight / (N_eight + shrinkage_weight)

    When N_eight is large, alpha -> 1.0 (trust 8-regime data).
    When N_eight is small, alpha -> 0 (fall back to 4-regime).

    Args:
        regime_family_map: dict mapping 8-regime label -> 4-regime family
    """
    # Precompute how many 8-regime variants each 4-regime family has
    # (currently 2: Ample + Tight, but derived from data to be future-proof)
    family_variant_count = {}
    for label_8, family_4 in regime_family_map.items():
        family_variant_count[family_4] = family_variant_count.get(family_4, 0) + 1

    shrunk_matrix = {}

    for source_8 in all_eight_labels:
        n_source = eight_totals.get(source_8, 0)
        if n_source == 0:
            shrunk_matrix[source_8] = {t: None for t in all_eight_labels}
            continue

        alpha = n_source / (n_source + shrinkage_weight)
        source_4 = regime_family_map[source_8]

        shrunk_matrix[source_8] = {}
        for target_8 in all_eight_labels:
            eight_prob = eight_matrix[source_8].get(target_8)
            if eight_prob is None:
                shrunk_matrix[source_8][target_8] = None
                continue

            target_4 = regime_family_map[target_8]
            four_prior = four_matrix.get(source_4, {}).get(target_4)

            if four_prior is None:
                # No 4-regime prior available, use raw 8-regime
                shrunk_matrix[source_8][target_8] = eight_prob
            else:
                # Distribute 4-regime prior equally across all variants of the same family
                n_variants = family_variant_count.get(target_4, 2)
                four_prior_split = four_prior / n_variants
                shrunk = alpha * eight_prob + (1 - alpha) * four_prior_split
                shrunk_matrix[source_8][target_8] = round(shrunk, 4)

        # Renormalize to sum to 1.0
        vals = [v for v in shrunk_matrix[source_8].values() if v is not None]
        total = sum(vals)
        if total > 0:
            for t in all_eight_labels:
                if shrunk_matrix[source_8][t] is not None:
                    shrunk_matrix[source_8][t] = round(
                        shrunk_matrix[source_8][t] / total, 4
                    )

    return shrunk_matrix


def compute_duration_stats(regime_series, regime_col):
    """
    Compute duration statistics for each regime: mean, median, max months,
    episode count, and current duration.
    """
    series = regime_series[regime_col].dropna()
    if len(series) == 0:
        return {}

    # Identify consecutive runs
    runs = []
    current_regime = None
    current_start = None
    current_length = 0

    for date, regime in series.items():
        if regime != current_regime:
            if current_regime is not None:
                runs.append({
                    "regime": current_regime,
                    "start": current_start,
                    "length": current_length,
                })
            current_regime = regime
            current_start = date
            current_length = 1
        else:
            current_length += 1

    # Add the last run (still in progress)
    if current_regime is not None:
        runs.append({
            "regime": current_regime,
            "start": current_start,
            "length": current_length,
            "is_current": True,
        })

    stats = {}
    all_regimes = series.unique()

    for regime in all_regimes:
        regime_runs = [r for r in runs if r["regime"] == regime]
        lengths = [r["length"] for r in regime_runs]

        if not lengths:
            continue

        current_run = [r for r in regime_runs if r.get("is_current")]
        current_duration = current_run[0]["length"] if current_run else None

        stats[regime] = {
            "mean_months": round(float(np.mean(lengths)), 1),
            "median_months": int(np.median(lengths)),
            "max_months": int(np.max(lengths)),
            "n_episodes": len(regime_runs),
            "current_duration_months": current_duration,
        }

    return stats


def compute_frequency_distribution(regime_series, regime_col):
    """Compute frequency distribution for each regime."""
    series = regime_series[regime_col].dropna()
    total = len(series)
    if total == 0:
        return {}

    counts = series.value_counts()
    result = {}
    for regime, count in counts.items():
        result[regime] = {
            "count": int(count),
            "percentage": round(float(count / total * 100), 1),
        }
    return result


def has_valid_liquidity(regime_df):
    """
    Check whether regime_8 values actually contain liquidity suffixes.
    If classify_regimes() couldn't compute liquidity (all 3 FRED series failed),
    it silently copies regime into regime_8 without the suffix.
    """
    if "regime_8" not in regime_df.columns:
        return False

    sample = regime_df["regime_8"].dropna().head(20)
    if len(sample) == 0:
        return False

    has_suffix = sample.str.contains("Ample|Tight", na=False)
    return bool(has_suffix.any())


def build_regime_family_map():
    """Map 8-regime labels to their 4-regime family."""
    mapping = {}
    for label in EIGHT_REGIMES:
        for family in FOUR_REGIMES:
            if label.startswith(family):
                mapping[label] = family
                break
    return mapping


def compute_all(regime_df, label, post_covid_start=None):
    """
    Compute transition matrices, duration stats, and frequency for a given
    time window of the regime DataFrame.

    Args:
        regime_df: Full monthly regime DataFrame from classify_regimes()
        label: "full_sample" or "post_covid"
        post_covid_start: Optional date string to filter post-COVID window
    """
    if post_covid_start:
        df = regime_df.loc[post_covid_start:]
    else:
        df = regime_df

    valid_8 = has_valid_liquidity(df)
    family_map = build_regime_family_map()

    result = {
        "label": label,
        "months": len(df),
        "date_range": {
            "start": df.index.min().strftime("%Y-%m") if len(df) > 0 else None,
            "end": df.index.max().strftime("%Y-%m") if len(df) > 0 else None,
        },
        "horizons": {},
        "duration_stats": {
            "four_regime": compute_duration_stats(df, "regime"),
        },
        "frequency": {
            "four_regime": compute_frequency_distribution(df, "regime"),
        },
    }

    if valid_8:
        result["duration_stats"]["eight_regime"] = compute_duration_stats(df, "regime_8")
        result["frequency"]["eight_regime"] = compute_frequency_distribution(df, "regime_8")

    for horizon in HORIZONS:
        horizon_key = f"{horizon}_month"

        # 4-regime matrix
        four_matrix, four_counts, four_totals, four_low_n = compute_transition_matrix(
            df, horizon, "regime", FOUR_REGIMES
        )

        result["horizons"][horizon_key] = {
            "four_regime": {
                "matrix": four_matrix,
                "counts": four_counts,
                "total_per_source": four_totals,
                "low_n_regimes": four_low_n,
            }
        }

        # 8-regime matrix (only if liquidity data is valid)
        if valid_8:
            eight_matrix, eight_counts, eight_totals, eight_low_n = compute_transition_matrix(
                df, horizon, "regime_8", EIGHT_REGIMES
            )

            # Apply Bayesian shrinkage
            shrunk_matrix = apply_bayesian_shrinkage(
                eight_matrix, eight_counts, eight_totals,
                four_matrix, family_map,
                EIGHT_REGIMES, FOUR_REGIMES,
            )

            result["horizons"][horizon_key]["eight_regime"] = {
                "matrix": shrunk_matrix,
                "raw_matrix": eight_matrix,
                "counts": eight_counts,
                "total_per_source": eight_totals,
                "low_n_regimes": eight_low_n,
                "shrinkage_weight": SHRINKAGE_WEIGHT,
            }

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Compute regime transition probability matrices"
    )
    parser.add_argument(
        "--fred-key",
        default=os.environ.get("FRED_API_KEY"),
        help="FRED API key (defaults to FRED_API_KEY env var)",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for regime-transitions.json",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Years of history to analyze (default: 10)",
    )
    args = parser.parse_args()

    if not args.fred_key:
        print("ERROR: FRED API key required. Use --fred-key or set FRED_API_KEY env var.")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "regime-transitions.json"

    # Suppress stdout noise from fetch_fred_series
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        fred_data, errors = fetch_fred_series(args.fred_key, years=args.years)
    finally:
        sys.stdout = old_stdout

    if errors:
        print(f"FRED fetch warnings: {len(errors)} series had issues")
        for e in errors:
            print(f"  {e}")

    if not fred_data:
        print("ERROR: No FRED data retrieved. Cannot compute transition matrix.")
        return 1

    print(f"Classifying regimes from {args.years} years of FRED data...")
    regime_df = classify_regimes(fred_data)
    print(f"  {len(regime_df)} monthly observations classified")

    valid_8 = has_valid_liquidity(regime_df)
    if not valid_8:
        print("WARNING: Liquidity data unavailable. 8-regime matrix will be omitted.")

    # Current regime (from most recent month)
    last_row = regime_df.iloc[-1]
    current_regime = {
        "four_regime": last_row.get("regime"),
        "eight_regime": last_row.get("regime_8") if valid_8 else None,
    }

    print(f"  Current regime: {current_regime['four_regime']}")
    if valid_8:
        print(f"  Current 8-regime: {current_regime['eight_regime']}")

    # Compute for full sample
    print("\nComputing full-sample transition matrices...")
    full_sample = compute_all(regime_df, "full_sample")

    # Compute for post-COVID window
    post_covid_df = regime_df.loc[POST_COVID_START:]
    post_covid = None
    if len(post_covid_df) >= 12:
        print(f"Computing post-COVID transition matrices ({len(post_covid_df)} months)...")
        post_covid = compute_all(regime_df, "post_covid", post_covid_start=POST_COVID_START)
    else:
        print(f"Post-COVID window too short ({len(post_covid_df)} months), skipping.")

    # Build output
    output = {
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "years": args.years,
        "total_months": len(regime_df),
        "current_regime": current_regime,
        "windows": {
            "full_sample": full_sample,
        },
        "metadata": {
            "classification_method": "6-month direction window, 2-month confirmation filter",
            "liquidity_method": "relative thresholds (rolling 36-month median), majority vote",
            "shrinkage_method": f"Bayesian shrinkage toward 4-regime prior, weight={SHRINKAGE_WEIGHT}",
            "post_covid_start": POST_COVID_START,
            "eight_regime_available": valid_8,
            "note": "8-regime probabilities are Bayesian-shrunk toward 4-regime prior. Raw (unshrunk) probabilities in raw_matrix.",
        },
    }

    if post_covid:
        output["windows"]["post_covid"] = post_covid

    # Write output
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nWritten to {output_path}")

    # Summary
    for window_name, window_data in output["windows"].items():
        print(f"\n--- {window_name} ({window_data['months']} months) ---")
        for horizon_key, horizon_data in window_data["horizons"].items():
            four_low = horizon_data["four_regime"]["low_n_regimes"]
            print(f"  {horizon_key}: 4-regime OK, low-N: {four_low or 'none'}")
            if "eight_regime" in horizon_data:
                eight_low = horizon_data["eight_regime"]["low_n_regimes"]
                print(f"  {horizon_key}: 8-regime (shrunk), low-N: {eight_low or 'none'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
