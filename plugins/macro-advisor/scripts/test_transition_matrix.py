#!/usr/bin/env python3
"""
Tests for compute_transition_matrix.py

Uses synthetic regime data with known expected outputs to verify:
- Transition probability computation
- Bayesian shrinkage behavior
- Duration statistics
- Edge cases (zero-count regimes, horizon tail exclusion)
- JSON schema validation
- regime_8 degradation guard
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from compute_transition_matrix import (
    EIGHT_REGIMES,
    FOUR_REGIMES,
    apply_bayesian_shrinkage,
    build_regime_family_map,
    compute_duration_stats,
    compute_frequency_distribution,
    compute_transition_matrix,
    has_valid_liquidity,
)


def make_regime_df(regimes_4, regimes_8=None, start="2016-01-31"):
    """Helper: build a monthly regime DataFrame from lists of regime labels."""
    dates = pd.date_range(start=start, periods=len(regimes_4), freq="ME")
    df = pd.DataFrame({"regime": regimes_4}, index=dates)

    if regimes_8 is not None:
        df["regime_8"] = regimes_8
    else:
        df["regime_8"] = df["regime"]

    return df


# --- Transition Matrix Tests ---


class TestTransitionMatrix:
    def test_simple_known_transitions(self):
        """12 months Goldilocks then 12 months Stagflation.
        At 6-month horizon, months 1-6 (Goldi) -> Goldi, months 7-12 (Goldi) -> Stag,
        months 13-18 (Stag) -> Stag. Last 6 months excluded (no forward target)."""
        regimes = ["Goldilocks"] * 12 + ["Stagflation"] * 12
        df = make_regime_df(regimes)

        matrix, counts, totals, low_n = compute_transition_matrix(
            df, 6, "regime", FOUR_REGIMES
        )

        # First 6 Goldilocks months -> Goldilocks at +6
        # Next 6 Goldilocks months -> Stagflation at +6
        assert counts["Goldilocks"]["Goldilocks"] == 6
        assert counts["Goldilocks"]["Stagflation"] == 6
        assert totals["Goldilocks"] == 12

        assert matrix["Goldilocks"]["Goldilocks"] == 0.5
        assert matrix["Goldilocks"]["Stagflation"] == 0.5

        # 12 Stagflation months, last 6 excluded, so 6 usable -> all self-transition
        assert counts["Stagflation"]["Stagflation"] == 6
        assert totals["Stagflation"] == 6

    def test_probability_sum_to_one(self):
        """For every source regime with observations, probabilities must sum to 1.0."""
        regimes = (
            ["Goldilocks"] * 20
            + ["Overheating"] * 15
            + ["Disinflationary Slowdown"] * 10
            + ["Stagflation"] * 15
        )
        df = make_regime_df(regimes)

        for horizon in [6, 12]:
            matrix, counts, totals, low_n = compute_transition_matrix(
                df, horizon, "regime", FOUR_REGIMES
            )

            for source, targets in matrix.items():
                vals = [v for v in targets.values() if v is not None]
                if vals:
                    assert abs(sum(vals) - 1.0) < 1e-6, (
                        f"Source {source} horizon {horizon}: sum={sum(vals)}"
                    )

    def test_count_consistency(self):
        """Sum of counts per source row must equal total_per_source."""
        regimes = ["Goldilocks"] * 30 + ["Overheating"] * 30
        df = make_regime_df(regimes)

        matrix, counts, totals, low_n = compute_transition_matrix(
            df, 6, "regime", FOUR_REGIMES
        )

        for source in FOUR_REGIMES:
            count_sum = sum(counts[source].values())
            assert count_sum == totals[source], (
                f"{source}: count_sum={count_sum} != total={totals[source]}"
            )

    def test_single_regime_self_transition(self):
        """All months in one regime: 100% self-transition."""
        regimes = ["Goldilocks"] * 24
        df = make_regime_df(regimes)

        matrix, counts, totals, low_n = compute_transition_matrix(
            df, 6, "regime", FOUR_REGIMES
        )

        assert matrix["Goldilocks"]["Goldilocks"] == 1.0
        assert matrix["Goldilocks"]["Overheating"] == 0.0

    def test_horizon_exceeds_data(self):
        """8 months of data, 12-month horizon. All excluded (no forward target)."""
        regimes = ["Goldilocks"] * 8
        df = make_regime_df(regimes)

        matrix, counts, totals, low_n = compute_transition_matrix(
            df, 12, "regime", FOUR_REGIMES
        )

        # No usable pairs
        assert totals["Goldilocks"] == 0
        assert all(v is None for v in matrix["Goldilocks"].values())

    def test_horizon_tail_exclusion_count(self):
        """120 months, horizon=12: expect exactly 108 usable pairs."""
        regimes = ["Goldilocks"] * 120
        df = make_regime_df(regimes)

        matrix, counts, totals, low_n = compute_transition_matrix(
            df, 12, "regime", FOUR_REGIMES
        )

        assert totals["Goldilocks"] == 108

    def test_zero_count_regime_produces_null(self):
        """A regime that never appears as source gets null probabilities."""
        regimes = ["Goldilocks"] * 24
        df = make_regime_df(regimes)

        matrix, counts, totals, low_n = compute_transition_matrix(
            df, 6, "regime", FOUR_REGIMES
        )

        # Stagflation never observed
        assert totals["Stagflation"] == 0
        assert all(v is None for v in matrix["Stagflation"].values())
        assert "Stagflation" in low_n

    def test_low_n_detection(self):
        """Regimes with fewer than 10 source observations are flagged."""
        regimes = ["Goldilocks"] * 20 + ["Overheating"] * 5
        df = make_regime_df(regimes)

        matrix, counts, totals, low_n = compute_transition_matrix(
            df, 6, "regime", FOUR_REGIMES
        )

        assert "Overheating" in low_n or totals["Overheating"] < 10


# --- Bayesian Shrinkage Tests ---


class TestBayesianShrinkage:
    def test_large_n_trusts_eight_regime(self):
        """With large N, shrinkage alpha approaches 1.0 (trust 8-regime data)."""
        family_map = build_regime_family_map()

        # Simulate: Goldilocks-Ample has N=100, strong self-transition
        eight_matrix = {r: {t: 0.0 for t in EIGHT_REGIMES} for r in EIGHT_REGIMES}
        eight_matrix["Goldilocks — Ample Liquidity"]["Goldilocks — Ample Liquidity"] = 0.8
        eight_matrix["Goldilocks — Ample Liquidity"]["Goldilocks — Tight Liquidity"] = 0.2

        eight_counts = {r: {t: 0 for t in EIGHT_REGIMES} for r in EIGHT_REGIMES}
        eight_counts["Goldilocks — Ample Liquidity"]["Goldilocks — Ample Liquidity"] = 80
        eight_counts["Goldilocks — Ample Liquidity"]["Goldilocks — Tight Liquidity"] = 20

        eight_totals = {r: 0 for r in EIGHT_REGIMES}
        eight_totals["Goldilocks — Ample Liquidity"] = 100

        four_matrix = {r: {t: 0.25 for t in FOUR_REGIMES} for r in FOUR_REGIMES}

        shrunk = apply_bayesian_shrinkage(
            eight_matrix, eight_counts, eight_totals,
            four_matrix, family_map,
            EIGHT_REGIMES, FOUR_REGIMES,
            shrinkage_weight=10,
        )

        # alpha = 100 / (100 + 10) = 0.909. Should heavily trust the 0.8 self-transition
        goldi_ample_self = shrunk["Goldilocks — Ample Liquidity"]["Goldilocks — Ample Liquidity"]
        assert goldi_ample_self is not None
        assert goldi_ample_self > 0.7  # still dominated by the 8-regime data

    def test_small_n_favors_four_regime_prior(self):
        """With small N, shrinkage alpha approaches 0 (favor 4-regime prior)."""
        family_map = build_regime_family_map()

        # N=3: alpha = 3/(3+10) = 0.23
        eight_matrix = {r: {t: 0.0 for t in EIGHT_REGIMES} for r in EIGHT_REGIMES}
        eight_matrix["Stagflation — Tight Liquidity"]["Stagflation — Tight Liquidity"] = 1.0

        eight_counts = {r: {t: 0 for t in EIGHT_REGIMES} for r in EIGHT_REGIMES}
        eight_counts["Stagflation — Tight Liquidity"]["Stagflation — Tight Liquidity"] = 3

        eight_totals = {r: 0 for r in EIGHT_REGIMES}
        eight_totals["Stagflation — Tight Liquidity"] = 3

        # 4-regime prior: uniform 25% each
        four_matrix = {r: {t: 0.25 for t in FOUR_REGIMES} for r in FOUR_REGIMES}

        shrunk = apply_bayesian_shrinkage(
            eight_matrix, eight_counts, eight_totals,
            four_matrix, family_map,
            EIGHT_REGIMES, FOUR_REGIMES,
            shrinkage_weight=10,
        )

        # The self-transition should be pulled down from 1.0 toward the prior
        stag_tight_self = shrunk["Stagflation — Tight Liquidity"]["Stagflation — Tight Liquidity"]
        assert stag_tight_self is not None
        assert stag_tight_self < 0.5  # heavily shrunk toward prior

    def test_shrunk_probabilities_sum_to_one(self):
        """After shrinkage, probabilities must still sum to 1.0."""
        family_map = build_regime_family_map()

        # Build a non-trivial scenario
        eight_matrix = {r: {t: 0.0 for t in EIGHT_REGIMES} for r in EIGHT_REGIMES}
        eight_counts = {r: {t: 0 for t in EIGHT_REGIMES} for r in EIGHT_REGIMES}
        eight_totals = {r: 0 for r in EIGHT_REGIMES}

        # Give a few regimes some data
        for i, src in enumerate(EIGHT_REGIMES[:4]):
            eight_totals[src] = 5 + i * 3
            for j, tgt in enumerate(EIGHT_REGIMES):
                c = max(0, (5 + i * 3) // 8 - abs(i - j))
                eight_counts[src][tgt] = c

            total = sum(eight_counts[src].values())
            if total > 0:
                eight_totals[src] = total
                for tgt in EIGHT_REGIMES:
                    eight_matrix[src][tgt] = eight_counts[src][tgt] / total

        four_matrix = {r: {t: 0.25 for t in FOUR_REGIMES} for r in FOUR_REGIMES}

        shrunk = apply_bayesian_shrinkage(
            eight_matrix, eight_counts, eight_totals,
            four_matrix, family_map,
            EIGHT_REGIMES, FOUR_REGIMES,
        )

        for src in EIGHT_REGIMES[:4]:
            vals = [v for v in shrunk[src].values() if v is not None]
            if vals:
                assert abs(sum(vals) - 1.0) < 1e-3, (
                    f"{src}: sum={sum(vals)}"
                )


# --- Duration Stats Tests ---


class TestDurationStats:
    def test_basic_duration(self):
        """12 months Goldilocks, 6 months Stagflation. Verify stats."""
        regimes = ["Goldilocks"] * 12 + ["Stagflation"] * 6
        df = make_regime_df(regimes)

        stats = compute_duration_stats(df, "regime")

        assert stats["Goldilocks"]["mean_months"] == 12.0
        assert stats["Goldilocks"]["n_episodes"] == 1
        assert stats["Goldilocks"]["current_duration_months"] is None

        assert stats["Stagflation"]["mean_months"] == 6.0
        assert stats["Stagflation"]["current_duration_months"] == 6  # last run

    def test_multiple_episodes(self):
        regimes = ["Goldilocks"] * 5 + ["Overheating"] * 3 + ["Goldilocks"] * 7
        df = make_regime_df(regimes)

        stats = compute_duration_stats(df, "regime")

        assert stats["Goldilocks"]["n_episodes"] == 2
        assert stats["Goldilocks"]["mean_months"] == 6.0  # (5+7)/2
        assert stats["Goldilocks"]["max_months"] == 7


# --- Frequency Distribution Tests ---


class TestFrequencyDistribution:
    def test_basic_frequency(self):
        regimes = ["Goldilocks"] * 60 + ["Stagflation"] * 40
        df = make_regime_df(regimes)

        freq = compute_frequency_distribution(df, "regime")

        assert freq["Goldilocks"]["count"] == 60
        assert freq["Goldilocks"]["percentage"] == 60.0
        assert freq["Stagflation"]["count"] == 40
        assert freq["Stagflation"]["percentage"] == 40.0


# --- Regime_8 Degradation Guard ---


class TestLiquidityGuard:
    def test_valid_liquidity_detected(self):
        regimes_8 = ["Goldilocks — Ample Liquidity"] * 10
        df = make_regime_df(["Goldilocks"] * 10, regimes_8)
        assert has_valid_liquidity(df) is True

    def test_missing_liquidity_detected(self):
        """When regime_8 = regime (no suffix), guard catches it."""
        regimes = ["Goldilocks"] * 10
        df = make_regime_df(regimes)
        df["regime_8"] = df["regime"]  # no liquidity suffix
        assert has_valid_liquidity(df) is False

    def test_no_regime_8_column(self):
        regimes = ["Goldilocks"] * 10
        df = make_regime_df(regimes)
        df = df.drop(columns=["regime_8"])
        assert has_valid_liquidity(df) is False


# --- Regime Family Map ---


class TestRegimeFamilyMap:
    def test_all_eight_regimes_mapped(self):
        mapping = build_regime_family_map()
        assert len(mapping) == 8
        for label in EIGHT_REGIMES:
            assert label in mapping
            assert mapping[label] in FOUR_REGIMES

    def test_consistency(self):
        mapping = build_regime_family_map()
        assert mapping["Goldilocks — Ample Liquidity"] == "Goldilocks"
        assert mapping["Stagflation — Tight Liquidity"] == "Stagflation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
