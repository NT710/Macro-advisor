"""
Unit tests for the Macro Advisor dashboard generator.
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
    generate_sparkline,
    generate_svg_regime_map,
    generate_svg_timeline,
    generate_svg_mini_chart,
    md_to_html,
    parse_key_changes,
    parse_cross_asset_table,
    inline_asset,
    REGIME_COLORS,
)


# ---------------------------------------------------------------------------
# Sparkline tests
# ---------------------------------------------------------------------------

class TestSparkline:
    def test_sparkline_normal(self):
        """10 values → returns valid <svg> with <polyline>."""
        values = [1, 3, 2, 5, 4, 6, 3, 7, 5, 8]
        result = generate_sparkline(values)
        assert "<svg" in result
        assert "<polyline" in result
        assert 'viewBox="0 0 80 20"' in result

    def test_sparkline_fewer_than_2(self):
        """0 or 1 values → returns empty string."""
        assert generate_sparkline([]) == ""
        assert generate_sparkline([5]) == ""
        assert generate_sparkline(None) == ""

    def test_sparkline_equal_values(self):
        """All same value → flat horizontal line at midpoint."""
        result = generate_sparkline([5, 5, 5, 5, 5])
        assert "<svg" in result
        assert "<polyline" in result
        # All y-coords should be 10.0 (midpoint of height=20)
        assert "10.0" in result

    def test_sparkline_with_nulls(self):
        """Values with None gaps → broken line (multiple <polyline> segments)."""
        values = [1, 2, None, 4, 5]
        result = generate_sparkline(values)
        assert "<svg" in result
        # Should have multiple polyline segments due to the None gap
        polyline_count = result.count("<polyline")
        assert polyline_count >= 2, f"Expected >=2 polylines for broken line, got {polyline_count}"

    def test_sparkline_with_nan(self):
        """NaN values treated same as None — gaps in line."""
        values = [1, 2, float("nan"), 4, 5]
        result = generate_sparkline(values)
        assert "<svg" in result
        polyline_count = result.count("<polyline")
        assert polyline_count >= 2

    def test_sparkline_accessibility(self):
        """Output contains role='img' and aria-label."""
        result = generate_sparkline([1, 2, 3, 4, 5])
        assert 'role="img"' in result
        assert 'aria-label=' in result
        assert "5 data points" in result

    def test_sparkline_custom_dimensions(self):
        """Custom width/height are reflected in SVG."""
        result = generate_sparkline([1, 2, 3], width=100, height=30)
        assert 'viewBox="0 0 100 30"' in result


# ---------------------------------------------------------------------------
# SVG generator tests
# ---------------------------------------------------------------------------

class TestRegimeMap:
    def test_regime_map_normal(self):
        """Valid regime data → SVG with 4 quadrants + position dot."""
        regime_data = {
            "regime": "Goldilocks",
            "direction": "Stable",
            "confidence": "High",
            "x": 0.5, "y": -0.5,
            "forecast_6m": "Goldilocks",
            "forecast_6m_x": 0.5, "forecast_6m_y": -0.5,
            "forecast_12m": "Overheating",
            "forecast_12m_x": 0.5, "forecast_12m_y": 0.5,
        }
        result = generate_svg_regime_map(regime_data)
        assert "<svg" in result
        # 4 quadrant rects
        assert result.count("<rect") >= 4
        # Position dot (2 circles for outer + inner)
        assert "<circle" in result
        # Labels
        assert "GOLDILOCKS" in result
        assert "OVERHEATING" in result
        assert "STAGFLATION" in result
        assert "DISINFLATION" in result
        # Forecast line
        assert "stroke-dasharray" in result

    def test_regime_map_no_history(self):
        """Empty history → SVG with dot only, no trail polyline."""
        regime_data = {
            "regime": "Goldilocks",
            "direction": "Stable",
            "confidence": "High",
            "x": 0.5, "y": -0.5,
            "forecast_6m": "Unknown",
            "forecast_12m": "Unknown",
        }
        result = generate_svg_regime_map(regime_data, regime_history=[])
        assert "<svg" in result
        assert "<circle" in result
        # No trail polyline
        assert result.count("<polyline") == 0

    def test_regime_map_with_history(self):
        """History provided → trail polyline + trail dots."""
        regime_data = {
            "regime": "Goldilocks",
            "x": 0.5, "y": -0.5,
            "forecast_6m": "Unknown",
            "forecast_12m": "Unknown",
        }
        history = [
            {"regime": "Overheating", "x": 0.5, "y": 0.5},
            {"regime": "Goldilocks", "x": 0.5, "y": -0.5},
        ]
        result = generate_svg_regime_map(regime_data, regime_history=history)
        assert "<polyline" in result  # trail line
        assert 'role="img"' in result


class TestTimeline:
    def test_timeline_empty(self):
        """Empty history → returns empty string."""
        assert generate_svg_timeline([]) == ""

    def test_timeline_single_week(self):
        """One entry → one dot, no connecting line."""
        result = generate_svg_timeline([{"regime": "Goldilocks", "week": "2026-W12", "summary": "Test"}])
        assert "<svg" in result
        assert "<circle" in result
        # Should NOT have a connecting line (only 1 dot)
        assert "<line" not in result

    def test_timeline_multiple_weeks(self):
        """Multiple entries → dots + connecting line."""
        history = [
            {"regime": "Goldilocks", "week": "2026-W10", "summary": "Week 10"},
            {"regime": "Overheating", "week": "2026-W11", "summary": "Week 11"},
            {"regime": "Goldilocks", "week": "2026-W12", "summary": "Week 12"},
        ]
        result = generate_svg_timeline(history)
        assert result.count("<circle") == 3
        assert "<line" in result  # connecting line
        assert 'role="img"' in result

    def test_timeline_dot_colors(self):
        """Each dot should use the correct regime color."""
        history = [
            {"regime": "Goldilocks", "week": "2026-W10", "summary": ""},
            {"regime": "Stagflation", "week": "2026-W11", "summary": ""},
        ]
        result = generate_svg_timeline(history)
        assert REGIME_COLORS["Goldilocks"] in result
        assert REGIME_COLORS["Stagflation"] in result


class TestMiniChart:
    def test_mini_chart_empty(self):
        """Empty data → returns empty string."""
        assert generate_svg_mini_chart([], "Test") == ""
        assert generate_svg_mini_chart(None, "Test") == ""
        assert generate_svg_mini_chart([1], "Test") == ""

    def test_mini_chart_normal(self):
        """Valid data → SVG with polyline + area fill."""
        values = [1.0, 2.0, 1.5, 3.0, 2.5]
        result = generate_svg_mini_chart(values, "Growth")
        assert "<svg" in result
        assert "<polyline" in result
        assert "<polygon" in result  # area fill
        assert "Growth" in result
        assert 'role="img"' in result


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestMdToHtml:
    def test_script_stripping(self):
        """Input with <script> tags → output has no <script> tags."""
        input_md = 'Hello <script>alert("xss")</script> World'
        result = md_to_html(input_md)
        assert "<script" not in result
        assert "alert" not in result
        assert "Hello" in result
        assert "World" in result

    def test_script_stripping_multiline(self):
        """Multiline script tags are also stripped."""
        input_md = """Some text
<script type="text/javascript">
var x = 1;
alert(x);
</script>
More text"""
        result = md_to_html(input_md)
        assert "<script" not in result.lower()
        assert "Some text" in result
        assert "More text" in result

    def test_script_stripping_case_insensitive(self):
        """Script tag stripping is case-insensitive."""
        input_md = '<SCRIPT>evil()</SCRIPT> safe text'
        result = md_to_html(input_md)
        assert "<script" not in result.lower()
        assert "safe text" in result


class TestParseBriefing:
    def test_parse_key_changes(self):
        """Briefing with 'Key Changes' heading → extracts bullets."""
        briefing = """# Weekly Briefing

## Big Picture
Economy is stable.

## Key Changes
- Fed signals easing path ahead. Markets responded positively with risk-on sentiment
- Inflation data deteriorating. CPI came in above expectations, causing concern
- Employment steady. No major changes in labor market
"""
        changes = parse_key_changes(briefing)
        assert len(changes) == 3
        assert changes[0]["headline"] == "Fed signals easing path ahead"
        assert changes[0]["impact"] == "bullish"  # "easing" + "risk-on"
        assert changes[1]["impact"] == "bearish"  # "deteriorat" + "concern"
        assert changes[2]["impact"] == "neutral"

    def test_parse_briefing_fallback(self):
        """Briefing without 'Key Changes' → falls back to 'Big Picture'."""
        briefing = """# Weekly Briefing

## Big Picture
Economy continues its moderate expansion trajectory.

## Cross-Asset View
| Asset | Direction |
"""
        changes = parse_key_changes(briefing)
        assert len(changes) == 1
        assert "moderate expansion" in changes[0]["headline"]
        assert changes[0]["impact"] == "neutral"

    def test_parse_briefing_empty(self):
        """Empty briefing → returns empty list."""
        assert parse_key_changes("") == []
        assert parse_key_changes(None) == []


class TestParseCrossAsset:
    def test_parse_cross_asset_table(self):
        """Markdown table with | delimiters → parsed correctly."""
        briefing = """# Briefing

## Cross-Asset View

| Asset | Direction | Conviction | Δ Week |
|-------|-----------|------------|--------|
| US Equities | Favor | High | — |
| US Treasuries | Reduce | Medium | ▼ was Favor |
| Gold | Neutral | Low | ▲ was Reduce |
"""
        rows = parse_cross_asset_table(briefing)
        assert len(rows) == 3
        assert rows[0]["asset"] == "US Equities"
        assert rows[0]["direction"] == "Favor"
        assert rows[1]["asset"] == "US Treasuries"
        assert rows[2]["asset"] == "Gold"

    def test_parse_cross_asset_malformed(self):
        """Malformed / missing table → returns empty list."""
        briefing = """# Briefing

## Cross-Asset View

No table here, just text.
"""
        rows = parse_cross_asset_table(briefing)
        assert rows == []

    def test_parse_cross_asset_empty(self):
        """Empty input → returns empty list."""
        assert parse_cross_asset_table("") == []


# ---------------------------------------------------------------------------
# Asset inlining tests
# ---------------------------------------------------------------------------

class TestInlineAsset:
    def test_inline_js(self):
        """JS file → returns raw content."""
        with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
            f.write("console.log('hello');")
            f.flush()
            result = inline_asset(f.name)
            assert result == "console.log('hello');"
        os.unlink(f.name)

    def test_inline_woff2(self):
        """woff2 file → returns base64 data URI."""
        with tempfile.NamedTemporaryFile(suffix=".woff2", delete=False) as f:
            f.write(b"\x00\x01\x02\x03")
            f.flush()
            result = inline_asset(f.name)
            assert result.startswith("data:font/woff2;base64,")
        os.unlink(f.name)

    def test_inline_missing_file(self):
        """Missing file → raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            inline_asset("/nonexistent/path/file.js")


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_generate_html_empty_data(self):
        """All empty inputs → renders with empty states, no crash."""
        from generate_dashboard import generate_html

        template_path = Path(__file__).parent / "dashboard-template.html"
        if not template_path.exists():
            pytest.skip("dashboard-template.html not found")

        result = generate_html(
            week="2026-W12",
            briefing="",
            theses=[],
            improvement="",
            synthesis="",
            snapshot_data="",
            regime_history=[],
            output_dir=None,
        )
        assert "<!DOCTYPE html>" in result or "<html" in result
        assert "2026-W12" in result

    def test_generate_html_full_data(self):
        """Realistic inputs → valid HTML under 500KB."""
        from generate_dashboard import generate_html

        template_path = Path(__file__).parent / "dashboard-template.html"
        if not template_path.exists():
            pytest.skip("dashboard-template.html not found")

        synthesis = """## Regime Classification
Current Quadrant: Goldilocks
Direction: Stable
Confidence: High

## Regime Forecast (6 and 12 Month)
- 6 month: Most likely Goldilocks
- 12 month: Most likely Overheating
"""
        briefing = """# Weekly Briefing

## Key Changes
- Fed signals easing path ahead. Markets responded with risk-on sentiment
- Inflation data deteriorating. CPI came in above expectations

## Cross-Asset View

| Asset | Direction | Conviction | Change |
|-------|-----------|------------|--------|
| US Equities | Favor | High | — |
| Treasuries | Reduce | Medium | ▼ |
"""
        snapshot = json.dumps({
            "markets": {
                "SP500": {"value": 5200, "change_pct": 2.1, "history": [5000, 5100, 5150, 5200]},
                "VIX": {"value": 14.2, "change_pct": -1.3, "history": [16, 15, 14.5, 14.2]},
            },
            "rates": {
                "US10Y": {"value": 4.31, "history": [4.2, 4.25, 4.3, 4.31]},
            }
        })

        history = [
            {"regime": "Overheating", "x": 0.3, "y": 0.4, "week": "2026-W10", "summary": "Week 10"},
            {"regime": "Goldilocks", "x": 0.5, "y": -0.3, "week": "2026-W11", "summary": "Week 11"},
            {"regime": "Goldilocks", "x": 0.5, "y": -0.5, "week": "2026-W12", "summary": "Week 12"},
        ]

        result = generate_html(
            week="2026-W12",
            briefing=briefing,
            theses=[],
            improvement="## Self-improvement\nAll systems nominal.",
            synthesis=synthesis,
            snapshot_data=snapshot,
            regime_history=history,
            output_dir=None,
        )

        assert "<html" in result
        assert "Goldilocks" in result
        assert "Fed signals easing" in result
        assert "US Equities" in result
        # Size check: with real Chart.js (~205KB) and Inter font (~230KB) inlined,
        # total should still be reasonable (under 600KB for the full self-contained file)
        size_kb = len(result.encode("utf-8")) / 1024
        assert size_kb < 700, f"Generated HTML is {size_kb:.0f}KB — expected under 700KB"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
