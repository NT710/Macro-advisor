"""
Unit tests for the Trading Engine dashboard generator.
Run with: python -m pytest scripts/test_dashboard.py -v
"""
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts dir to path so we can import generate_dashboard
sys.path.insert(0, str(Path(__file__).parent))

from generate_dashboard import (
    esc,
    fmt_money,
    fmt_pct,
    generate_sparkline,
    inline_asset,
    load_json,
    load_snapshots,
    _build_improvements_tab,
    _num,
)


# ---------------------------------------------------------------------------
# _num coercion tests
# ---------------------------------------------------------------------------

class TestNum:
    def test_num_normal(self):
        assert _num(42) == 42.0
        assert _num(3.14) == 3.14

    def test_num_string(self):
        assert _num("123") == 123.0
        assert _num("not a number") == 0

    def test_num_none(self):
        assert _num(None) == 0
        assert _num(None, -1) == -1

    def test_num_bool(self):
        assert _num(True) == 1.0
        assert _num(False) == 0.0


# ---------------------------------------------------------------------------
# Formatting tests
# ---------------------------------------------------------------------------

class TestFormatting:
    def test_esc_none(self):
        assert esc(None) == ""

    def test_esc_html(self):
        assert "&lt;" in esc("<script>")

    def test_fmt_money_normal(self):
        assert fmt_money(1234.56) == "$1,234.56"

    def test_fmt_money_none(self):
        assert fmt_money(None) == "—"

    def test_fmt_pct_normal(self):
        result = fmt_pct(2.5)
        assert "2.50%" in result

    def test_fmt_pct_none(self):
        assert fmt_pct(None) == "—"

    def test_fmt_pct_negative(self):
        result = fmt_pct(-3.2)
        assert "-3.20%" in result


# ---------------------------------------------------------------------------
# Sparkline tests
# ---------------------------------------------------------------------------

class TestSparkline:
    def test_sparkline_normal(self):
        values = [1, 3, 2, 5, 4, 6, 3, 7, 5, 8]
        result = generate_sparkline(values)
        assert "<svg" in result
        assert "<polyline" in result
        assert 'viewBox="0 0 80 20"' in result

    def test_sparkline_fewer_than_2(self):
        assert generate_sparkline([]) == ""
        assert generate_sparkline([5]) == ""
        assert generate_sparkline(None) == ""

    def test_sparkline_equal_values(self):
        result = generate_sparkline([5, 5, 5, 5, 5])
        assert "<svg" in result
        assert "<polyline" in result
        assert "10.0" in result

    def test_sparkline_with_nulls(self):
        values = [1, 2, None, 4, 5]
        result = generate_sparkline(values)
        assert "<svg" in result
        polyline_count = result.count("<polyline")
        assert polyline_count >= 2, f"Expected >=2 polylines for broken line, got {polyline_count}"

    def test_sparkline_with_nan(self):
        values = [1, 2, float("nan"), 4, 5]
        result = generate_sparkline(values)
        assert "<svg" in result
        polyline_count = result.count("<polyline")
        assert polyline_count >= 2

    def test_sparkline_accessibility(self):
        result = generate_sparkline([1, 2, 3, 4, 5])
        assert 'role="img"' in result
        assert 'aria-label=' in result
        assert "5 data points" in result

    def test_sparkline_custom_dimensions(self):
        result = generate_sparkline([1, 2, 3], width=100, height=30)
        assert 'viewBox="0 0 100 30"' in result


# ---------------------------------------------------------------------------
# Asset inlining tests
# ---------------------------------------------------------------------------

class TestInlineAsset:
    def test_inline_js(self):
        with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
            f.write("console.log('hello');")
            f.flush()
            result = inline_asset(f.name)
            assert result == "console.log('hello');"
        os.unlink(f.name)

    def test_inline_woff2(self):
        with tempfile.NamedTemporaryFile(suffix=".woff2", delete=False) as f:
            f.write(b"\x00\x01\x02\x03")
            f.flush()
            result = inline_asset(f.name)
            assert result.startswith("data:font/woff2;base64,")
        os.unlink(f.name)

    def test_inline_missing_file(self):
        with pytest.raises(FileNotFoundError):
            inline_asset("/nonexistent/path/file.js")


# ---------------------------------------------------------------------------
# Data loading tests
# ---------------------------------------------------------------------------

class TestDataLoading:
    def test_load_json_missing(self):
        result = load_json("/nonexistent/file.json")
        assert result == {}

    def test_load_json_valid(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"key": "value"}, f)
            f.flush()
            result = load_json(f.name)
            assert result == {"key": "value"}
        os.unlink(f.name)

    def test_load_snapshots_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_snapshots(tmpdir)
            assert result == []

    def test_load_snapshots_with_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap = {"timestamp": "2026-03-21T10:00:00", "account": {"portfolio_value": 100000}}
            with open(os.path.join(tmpdir, "2026-03-21-snapshot.json"), "w") as f:
                json.dump(snap, f)
            result = load_snapshots(tmpdir)
            assert len(result) == 1
            assert result[0]["account"]["portfolio_value"] == 100000


# ---------------------------------------------------------------------------
# Improvements tab tests
# ---------------------------------------------------------------------------

class TestImprovementsTab:
    def test_empty_improvements(self):
        report = {
            "health_score": None, "health_trend": None, "proposals": [],
            "recommendations": [], "execution_quality": {}, "reasoning_quality": {},
            "skills_at_risk": None,
        }
        result = _build_improvements_tab(report, [])
        assert "No pending proposals" in result
        assert "System Health" in result

    def test_with_health_score(self):
        report = {
            "health_score": "7.2/10", "health_trend": "improving", "proposals": [],
            "recommendations": [], "execution_quality": {"fill_rate": "95%"},
            "reasoning_quality": {}, "skills_at_risk": "T3-risk-sizing",
        }
        result = _build_improvements_tab(report, [])
        assert "7.2/10" in result
        assert "improving" in result
        assert "T3-risk-sizing" in result
        assert "Fill Rate" in result

    def test_with_proposals(self):
        report = {
            "health_score": "6/10", "health_trend": "stable", "proposals": [
                {"id": "AMD-007", "skill": "T3", "issue": "test issue", "rationale": "test rationale",
                 "current": "old", "proposed": "new", "impact": "high", "risk": "low"},
            ],
            "recommendations": ["Review risk limits"], "execution_quality": {},
            "reasoning_quality": {}, "skills_at_risk": None,
        }
        result = _build_improvements_tab(report, [])
        assert "AMD-007" in result
        assert "test issue" in result
        assert "Review risk limits" in result

    def test_with_evaluated_amendments(self):
        amendments = [
            {"id": "AMD-001", "skill": "T3", "proposed": "2026-01-01",
             "implemented": "2026-01-05", "status": "EVALUATED",
             "target_metric": "win_rate", "before": "55%", "after": "62%",
             "verdict": "EFFECTIVE"},
        ]
        report = {
            "health_score": None, "health_trend": None, "proposals": [],
            "recommendations": [], "execution_quality": {}, "reasoning_quality": {},
            "skills_at_risk": None,
        }
        result = _build_improvements_tab(report, amendments)
        assert "AMD-001" in result
        assert "EFFECTIVE" in result


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_generate_dashboard_empty_data(self):
        """All empty inputs → renders with empty states, no crash."""
        from generate_dashboard import generate_dashboard

        template_path = Path(__file__).parent / "trading-dashboard-template.html"
        if not template_path.exists():
            pytest.skip("trading-dashboard-template.html not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            portfolio_dir = os.path.join(tmpdir, "portfolio")
            trades_dir = os.path.join(tmpdir, "trades")
            perf_dir = os.path.join(tmpdir, "performance")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(portfolio_dir)
            os.makedirs(trades_dir)
            os.makedirs(perf_dir)

            # Create empty performance report
            with open(os.path.join(perf_dir, "latest-performance-report.json"), "w") as f:
                json.dump({}, f)
            # Create empty trade log
            with open(os.path.join(trades_dir, "trade-log.json"), "w") as f:
                json.dump([], f)
            with open(os.path.join(trades_dir, "closed-trades.json"), "w") as f:
                json.dump([], f)

            result = generate_dashboard(portfolio_dir, trades_dir, perf_dir, output_dir)
            assert "<!DOCTYPE html>" in result or "<html" in result
            assert "TRADING ENGINE" in result
            assert "No trades recorded" in result
            assert "No portfolio snapshots" in result

    def test_generate_dashboard_with_data(self):
        """Realistic inputs → valid HTML."""
        from generate_dashboard import generate_dashboard

        template_path = Path(__file__).parent / "trading-dashboard-template.html"
        if not template_path.exists():
            pytest.skip("trading-dashboard-template.html not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            portfolio_dir = os.path.join(tmpdir, "portfolio")
            trades_dir = os.path.join(tmpdir, "trades")
            perf_dir = os.path.join(tmpdir, "performance")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(portfolio_dir)
            os.makedirs(trades_dir)
            os.makedirs(perf_dir)

            # Create snapshots
            for i, val in enumerate([100000, 100500, 101000, 101200, 102000]):
                snap = {"timestamp": f"2026-03-{15+i:02d}T10:00:00", "account": {"portfolio_value": val}}
                with open(os.path.join(portfolio_dir, f"2026-03-{15+i:02d}-snapshot.json"), "w") as f:
                    json.dump(snap, f)

            # Create performance report
            perf = {
                "returns": {"ending_value": 102000, "starting_value": 100000, "total_return_pct": 2.0},
                "risk": {"max_drawdown_pct": 1.5, "current_drawdown_pct": 0.5, "high_water_mark": 102000},
                "win_rate": {"total_closed": 10, "wins": 6, "losses": 4, "win_rate": 60.0,
                             "avg_win": 500, "avg_loss": -300, "profit_factor": 2.5},
                "sharpe_ratio": 1.45,
                "attribution": {"trade_count_by_layer": {"core": 5, "satellite": 3, "tactical": 2}},
            }
            with open(os.path.join(perf_dir, "latest-performance-report.json"), "w") as f:
                json.dump(perf, f)

            # Create trade log
            trades = [
                {"date": "2026-03-20T10:00:00", "run_type": "LIVE", "symbol": "AAPL",
                 "side": "buy", "qty": 10, "fill_price": 178.50, "order_type": "market",
                 "layer": "core", "thesis": "Long US Tech", "status": "filled", "reason": "Macro bullish"},
            ]
            with open(os.path.join(trades_dir, "trade-log.json"), "w") as f:
                json.dump(trades, f)

            closed = [
                {"symbol": "MSFT", "entry_date": "2026-03-10", "exit_date": "2026-03-18",
                 "holding_days": 8, "entry_price": 410, "exit_price": 420,
                 "realized_pl": 100, "realized_pl_pct": 2.44, "layer": "core",
                 "close_reason": "take-profit", "bear_case_realized": False},
            ]
            with open(os.path.join(trades_dir, "closed-trades.json"), "w") as f:
                json.dump(closed, f)

            result = generate_dashboard(portfolio_dir, trades_dir, perf_dir, output_dir)
            assert "<html" in result
            assert "AAPL" in result
            assert "$102,000.00" in result
            assert "60.0%" in result

            # Size check
            size_kb = len(result.encode("utf-8")) / 1024
            assert size_kb < 700, f"Generated HTML is {size_kb:.0f}KB — expected under 700KB"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
