#!/usr/bin/env python3
"""
Macro Advisor — Weekly Dashboard Generator (Alpine Report Edition)
Reads all output files and produces a single HTML dashboard with:
- Hero section with SVG regime map + metrics strip with sparklines
- What Changed This Week section
- Economic Dashboard 2x2 mini-chart grid
- Regime evolution timeline (26-week, clickable popovers)
- Active positions (research-report style, expandable)
- Cross-asset heatmap
- System health

Uses Jinja2 template at scripts/dashboard-template.html.

Usage:
    python generate_dashboard.py --week 2026-W12 --output-dir outputs/ --out dashboard.html
"""

import argparse
import base64
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def read_file(path):
    """Read a file, return empty string if not found."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def inline_asset(path):
    """Read a local asset file and return content for embedding.

    .woff2 files → base64 data URI
    .js files → raw content
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Asset not found: {path}")
    if p.suffix == ".woff2":
        data = p.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:font/woff2;base64,{b64}"
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Markdown → HTML conversion
# ---------------------------------------------------------------------------

def md_to_html(md_text):
    """Simple markdown to HTML conversion — handles headers, bold, tables, lists, code blocks.
    Strips <script> tags for XSS defense-in-depth."""
    # Strip <script> tags before processing
    md_text = re.sub(r'<script\b[^>]*>.*?</script>', '', md_text, flags=re.DOTALL | re.IGNORECASE)

    lines = md_text.split("\n")
    html_lines = []
    in_table = False
    in_code = False
    in_ul = False

    for line in lines:
        # Code blocks
        if line.strip().startswith("```"):
            if in_code:
                html_lines.append("</pre></div>")
                in_code = False
            else:
                html_lines.append('<div class="code-block"><pre>')
                in_code = True
            continue
        if in_code:
            html_lines.append(line)
            continue

        # Close list if needed
        if in_ul and not line.strip().startswith("- ") and not line.strip().startswith("* "):
            html_lines.append("</ul>")
            in_ul = False

        # Tables
        if "|" in line and not line.strip().startswith("```"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if all(set(c) <= set("- :") for c in cells):
                continue  # skip separator row
            if not in_table:
                html_lines.append('<div class="table-wrapper"><table>')
                in_table = True
                html_lines.append("<thead><tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr></thead><tbody>")
            else:
                html_lines.append("<tr>" + "".join(f"<td>{apply_inline(c)}</td>" for c in cells) + "</tr>")
            continue
        elif in_table:
            html_lines.append("</tbody></table></div>")
            in_table = False

        # Headers
        if line.startswith("# "):
            html_lines.append(f'<h1>{apply_inline(line[2:])}</h1>')
        elif line.startswith("## "):
            html_lines.append(f'<h2>{apply_inline(line[3:])}</h2>')
        elif line.startswith("### "):
            html_lines.append(f'<h3>{apply_inline(line[4:])}</h3>')
        elif line.startswith("#### "):
            html_lines.append(f'<h4>{apply_inline(line[5:])}</h4>')
        # Lists
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            content = line.strip()[2:]
            html_lines.append(f"<li>{apply_inline(content)}</li>")
        # Horizontal rule
        elif line.strip() == "---":
            html_lines.append("<hr>")
        # Empty line
        elif line.strip() == "":
            html_lines.append("")
        # Regular paragraph
        else:
            html_lines.append(f"<p>{apply_inline(line)}</p>")

    if in_table:
        html_lines.append("</tbody></table></div>")
    if in_ul:
        html_lines.append("</ul>")
    if in_code:
        html_lines.append("</pre></div>")

    return "\n".join(html_lines)


def apply_inline(text):
    """Apply inline markdown formatting."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    def _safe_link(m):
        label, href = m.group(1), m.group(2)
        if href.lower().startswith("javascript:"):
            return label  # strip javascript: URIs
        return f'<a href="{href}">{label}</a>'
    text = re.sub(r'\[(.+?)\]\((.+?)\)', _safe_link, text)
    return text


# ---------------------------------------------------------------------------
# Regime parsing
# ---------------------------------------------------------------------------

def parse_regime_from_synthesis(synthesis_text):
    """Extract regime data including forecasts from synthesis for the visualization."""
    regime = "Unknown"
    direction = "Stable"
    confidence = "Medium"
    forecast_6m = "Unknown"
    forecast_12m = "Unknown"

    lines = synthesis_text.split("\n")
    in_forecast_section = False

    for line in lines:
        lower = line.lower()

        if "current quadrant" in lower or ("regime:" in lower and "forecast" not in lower):
            if "goldilocks" in lower:
                regime = "Goldilocks"
            elif "overheating" in lower:
                regime = "Overheating"
            elif "stagflation" in lower:
                regime = "Stagflation"
            elif "disinflation" in lower or "slowdown" in lower:
                regime = "Disinflationary Slowdown"

        if "direction:" in lower and "forecast" not in lower:
            if "stable" in lower:
                direction = "Stable"
            elif "stagflation" in lower:
                direction = "Toward Stagflation"
            elif "goldilocks" in lower:
                direction = "Toward Goldilocks"
            elif "overheating" in lower:
                direction = "Toward Overheating"
            elif "disinflation" in lower or "slowdown" in lower:
                direction = "Toward Disinflation"

        if "confidence:" in lower and not in_forecast_section:
            if "high" in lower:
                confidence = "High"
            elif "low" in lower:
                confidence = "Low"
            else:
                confidence = "Medium"

        if "regime forecast" in lower or "6 and 12 month" in lower:
            in_forecast_section = True

        if in_forecast_section:
            if ("6 month" in lower or "6-month" in lower) and "most likely" in lower:
                for r in ["Goldilocks", "Overheating", "Stagflation"]:
                    if r.lower() in lower:
                        forecast_6m = r
                        break
                if "disinflation" in lower or "slowdown" in lower:
                    forecast_6m = "Disinflationary Slowdown"

            if ("12 month" in lower or "12-month" in lower) and "most likely" in lower:
                for r in ["Goldilocks", "Overheating", "Stagflation"]:
                    if r.lower() in lower:
                        forecast_12m = r
                        break
                if "disinflation" in lower or "slowdown" in lower:
                    forecast_12m = "Disinflationary Slowdown"

    coords = {
        "Goldilocks": (0.5, -0.5),
        "Overheating": (0.5, 0.5),
        "Disinflationary Slowdown": (-0.5, -0.5),
        "Stagflation": (-0.5, 0.5),
        "Unknown": (0, 0),
    }

    x, y = coords.get(regime, (0, 0))
    f6x, f6y = coords.get(forecast_6m, (0, 0))
    f12x, f12y = coords.get(forecast_12m, (0, 0))

    return {
        "regime": regime,
        "direction": direction,
        "confidence": confidence,
        "x": x, "y": y,
        "forecast_6m": forecast_6m,
        "forecast_6m_x": f6x, "forecast_6m_y": f6y,
        "forecast_12m": forecast_12m,
        "forecast_12m_x": f12x, "forecast_12m_y": f12y,
    }


# ---------------------------------------------------------------------------
# SVG generation engine
# ---------------------------------------------------------------------------

REGIME_COLORS = {
    "Goldilocks": "#34d399",
    "Overheating": "#fbbf24",
    "Stagflation": "#f87171",
    "Disinflationary Slowdown": "#60a5fa",
    "Unknown": "#8b8fa3",
}

REGIME_COLORS_BG = {
    "Goldilocks": "#34d39915",
    "Overheating": "#fbbf2415",
    "Stagflation": "#f8717115",
    "Disinflationary Slowdown": "#60a5fa15",
    "Unknown": "#8b8fa315",
}


def generate_sparkline(values, width=80, height=20, color="currentColor", stroke_width=1.5):
    """Generate an inline SVG sparkline.

    Returns empty string for <2 non-None values.
    Handles None/NaN values by drawing broken line segments with gaps.
    All-equal values render as a flat horizontal line at midpoint.
    """
    # Filter out None/NaN but track positions
    points = []
    for i, v in enumerate(values or []):
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            points.append((i, float(v)))

    if len(points) < 2:
        return ""

    n = len(values)
    y_vals = [p[1] for p in points]
    min_v = min(y_vals)
    max_v = max(y_vals)

    # Prevent division by zero for equal values
    v_range = max_v - min_v if max_v != min_v else 1.0
    mid_y = height / 2

    def scale_x(idx):
        return (idx / max(n - 1, 1)) * width

    def scale_y(v):
        if max_v == min_v:
            return mid_y
        return height - ((v - min_v) / v_range) * (height - 2) - 1

    # Build segments (break at None gaps)
    segments = []
    current_segment = []
    for i in range(n):
        v = values[i]
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            current_segment.append((scale_x(i), scale_y(float(v))))
        else:
            if len(current_segment) >= 2:
                segments.append(current_segment)
            current_segment = []
    if len(current_segment) >= 2:
        segments.append(current_segment)
    elif len(current_segment) == 1 and segments:
        # Single trailing point — attach to last segment
        segments[-1].append(current_segment[0])

    if not segments:
        return ""

    # Build SVG polylines
    polylines = []
    for seg in segments:
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in seg)
        polylines.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    label_text = f"Sparkline showing {len(points)} data points"
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="{label_text}" style="vertical-align:middle">'
        + "".join(polylines)
        + "</svg>"
    )


def generate_svg_regime_map(regime_data, regime_history=None, size=300):
    """Generate an SVG regime map with four colored quadrants, position dot,
    trailing path, and forecast dots."""
    regime_history = regime_history or []
    half = size / 2
    pad = 30  # padding for labels

    def to_svg(x, y):
        """Convert regime coords (-1..1, -1..1) to SVG coords."""
        sx = pad + (x + 1) / 2 * (size - 2 * pad)
        sy = pad + (1 - (y + 1) / 2) * (size - 2 * pad)  # y inverted
        return sx, sy

    parts = [f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
             f'role="img" aria-label="Regime map showing current position in {regime_data["regime"]} quadrant">']

    # Quadrant backgrounds
    qw = (size - 2 * pad) / 2
    # Quadrant layout: X=growth (left=falling, right=rising), Y=inflation (top=rising, bottom=falling)
    # Top-left: Stagflation (growth falling, inflation rising)
    # Top-right: Overheating (growth rising, inflation rising)
    # Bottom-left: Disinflationary Slowdown (growth falling, inflation falling)
    # Bottom-right: Goldilocks (growth rising, inflation falling)
    quadrants = [
        (pad, pad, "Stagflation"),
        (pad + qw, pad, "Overheating"),
        (pad, pad + qw, "Disinflationary Slowdown"),
        (pad + qw, pad + qw, "Goldilocks"),
    ]
    for qx, qy, qname in quadrants:
        parts.append(f'<rect x="{qx}" y="{qy}" width="{qw}" height="{qw}" '
                     f'fill="{REGIME_COLORS_BG[qname]}" />')

    # Crosshairs
    parts.append(f'<line x1="{pad}" y1="{half}" x2="{size-pad}" y2="{half}" '
                 f'stroke="#ffffff15" stroke-width="1" stroke-dasharray="4,4"/>')
    parts.append(f'<line x1="{half}" y1="{pad}" x2="{half}" y2="{size-pad}" '
                 f'stroke="#ffffff15" stroke-width="1" stroke-dasharray="4,4"/>')

    # Quadrant labels
    label_positions = [
        (pad + qw * 0.5, pad + qw * 0.5, "STAGFLATION", REGIME_COLORS["Stagflation"]),
        (pad + qw * 1.5, pad + qw * 0.5, "OVERHEATING", REGIME_COLORS["Overheating"]),
        (pad + qw * 0.5, pad + qw * 1.5, "DISINFLATION", REGIME_COLORS["Disinflationary Slowdown"]),
        (pad + qw * 1.5, pad + qw * 1.5, "GOLDILOCKS", REGIME_COLORS["Goldilocks"]),
    ]
    for lx, ly, label, lcolor in label_positions:
        parts.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" dominant-baseline="middle" '
                     f'fill="{lcolor}" opacity="0.3" font-size="11" font-weight="600">{label}</text>')

    # Axis labels
    parts.append(f'<text x="{half}" y="{size - 5}" text-anchor="middle" fill="#8b8fa3" font-size="10">Growth →</text>')
    parts.append(f'<text x="10" y="{half}" text-anchor="middle" fill="#8b8fa3" font-size="10" '
                 f'transform="rotate(-90,10,{half})">Inflation ↑</text>')

    # Historical trail
    if len(regime_history) > 1:
        trail_points = []
        for r in regime_history:
            sx, sy = to_svg(r["x"], r["y"])
            trail_points.append(f"{sx:.1f},{sy:.1f}")
        pts = " ".join(trail_points)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="#60a5fa" '
                     f'stroke-width="1.5" stroke-opacity="0.3" stroke-dasharray="3,3"/>')
        # Trail dots (fading)
        for i, r in enumerate(regime_history[:-1]):
            sx, sy = to_svg(r["x"], r["y"])
            opacity = 0.1 + (i / len(regime_history)) * 0.3
            parts.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="3" '
                         f'fill="#60a5fa" opacity="{opacity:.2f}"/>')

    # Forecast dots
    if regime_data.get("forecast_6m", "Unknown") != "Unknown":
        fx, fy = to_svg(regime_data["forecast_6m_x"], regime_data["forecast_6m_y"])
        cx, cy = to_svg(regime_data["x"], regime_data["y"])
        parts.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{fx:.1f}" y2="{fy:.1f}" '
                     f'stroke="#fbbf24" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.6"/>')
        parts.append(f'<polygon points="{fx:.1f},{fy-6:.1f} {fx-5:.1f},{fy+4:.1f} {fx+5:.1f},{fy+4:.1f}" '
                     f'fill="#fbbf24" opacity="0.7"/>')

    if regime_data.get("forecast_12m", "Unknown") != "Unknown":
        f12x, f12y = to_svg(regime_data["forecast_12m_x"], regime_data["forecast_12m_y"])
        # Connect from 6m forecast if available, else from current
        if regime_data.get("forecast_6m", "Unknown") != "Unknown":
            sx, sy = to_svg(regime_data["forecast_6m_x"], regime_data["forecast_6m_y"])
        else:
            sx, sy = to_svg(regime_data["x"], regime_data["y"])
        parts.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{f12x:.1f}" y2="{f12y:.1f}" '
                     f'stroke="#f87171" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.5"/>')
        parts.append(f'<rect x="{f12x-5:.1f}" y="{f12y-5:.1f}" width="10" height="10" '
                     f'fill="#f87171" opacity="0.6"/>')

    # Current position dot (on top)
    cx, cy = to_svg(regime_data["x"], regime_data["y"])
    dot_color = REGIME_COLORS.get(regime_data["regime"], "#60a5fa")
    parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="8" fill="{dot_color}" opacity="0.9"/>')
    parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#fff" opacity="0.9"/>')

    parts.append("</svg>")
    return "\n".join(parts)


def generate_svg_timeline(regime_history, max_weeks=26):
    """Generate a horizontal SVG timeline showing regime history.
    Each week = colored dot. Returns empty string for empty history."""
    if not regime_history:
        return ""

    history = regime_history[-max_weeks:]  # cap at max_weeks
    n = len(history)
    dot_r = 8
    gap = 36
    width = max((n - 1) * gap + dot_r * 4, 100)
    height = 60

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
             f'preserveAspectRatio="xMinYMid meet" '
             f'role="img" aria-label="Regime timeline showing {n} weeks of history">']

    y_center = 25

    # Connecting line
    if n > 1:
        x1 = dot_r * 2
        x2 = (n - 1) * gap + dot_r * 2
        parts.append(f'<line x1="{x1}" y1="{y_center}" x2="{x2}" y2="{y_center}" '
                     f'stroke="#2e3345" stroke-width="2"/>')

    # Dots
    for i, r in enumerate(history):
        cx = i * gap + dot_r * 2
        color = REGIME_COLORS.get(r.get("regime", "Unknown"), "#8b8fa3")
        week = r.get("week", "")
        # Synthesis snippet for popover (first 150 chars)
        summary = r.get("summary", "")[:150]
        # Escape quotes in data attributes to prevent attribute injection
        safe_summary = summary.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
        safe_week = week.replace('"', "&quot;")

        parts.append(
            f'<circle cx="{cx}" cy="{y_center}" r="{dot_r}" fill="{color}" '
            f'class="timeline-dot" tabindex="0" '
            f'data-week="{safe_week}" data-summary="{safe_summary}" '
            f'style="cursor:pointer" />'
        )
        # Week label below
        parts.append(
            f'<text x="{cx}" y="{y_center + 22}" text-anchor="middle" '
            f'fill="#8b8fa3" font-size="9">{week[-3:]}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def generate_svg_mini_chart(values, label, color="#60a5fa", width=280, height=120):
    """Generate a mini SVG chart for the economic dashboard grid.
    Returns empty string for empty/insufficient data."""
    if not values or len(values) < 2:
        return ""

    # Filter None values
    clean = [(i, float(v)) for i, v in enumerate(values) if v is not None]
    if len(clean) < 2:
        return ""

    n = len(values)
    y_vals = [v for _, v in clean]
    min_v = min(y_vals)
    max_v = max(y_vals)
    v_range = max_v - min_v if max_v != min_v else 1.0

    pad_x = 5
    pad_y = 20
    chart_w = width - 2 * pad_x
    chart_h = height - 2 * pad_y

    def sx(i):
        return pad_x + (i / max(n - 1, 1)) * chart_w

    def sy(v):
        if max_v == min_v:
            return pad_y + chart_h / 2
        return pad_y + chart_h - ((v - min_v) / v_range) * chart_h

    pts = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in clean)

    # Area fill
    area_pts = pts + f" {sx(clean[-1][0]):.1f},{pad_y + chart_h} {sx(clean[0][0]):.1f},{pad_y + chart_h}"

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'role="img" aria-label="{label} trend chart">'
        f'<text x="{pad_x}" y="14" fill="#e4e4e7" font-size="12" font-weight="600">{label}</text>'
        f'<polygon points="{area_pts}" fill="{color}" opacity="0.08"/>'
        f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        # Min/max labels
        f'<text x="{width - pad_x}" y="{sy(max_v) - 4:.1f}" text-anchor="end" fill="#8b8fa3" font-size="9">{max_v:.1f}</text>'
        f'<text x="{width - pad_x}" y="{sy(min_v) + 12:.1f}" text-anchor="end" fill="#8b8fa3" font-size="9">{min_v:.1f}</text>'
        f'</svg>'
    )


# ---------------------------------------------------------------------------
# Briefing & cross-asset parsers
# ---------------------------------------------------------------------------

def parse_key_changes(briefing_text):
    """Parse the 'Key Changes' or 'What Changed' section from the briefing.
    Returns list of dicts with headline, explanation, impact (bullish/bearish/neutral).
    Falls back to Big Picture first paragraph if Key Changes not found."""
    if not briefing_text:
        return []

    lines = briefing_text.split("\n")
    changes = []

    # Find Key Changes section
    in_section = False
    for line in lines:
        lower = line.lower().strip()
        if any(h in lower for h in ["## key changes", "## what changed", "### key changes", "### what changed"]):
            in_section = True
            continue
        if in_section:
            if line.startswith("## ") or line.startswith("### "):
                break  # next section
            if line.strip().startswith("- ") or line.strip().startswith("* "):
                bullet = line.strip()[2:].strip()
                if not bullet:
                    continue
                # Split into headline (first sentence) and explanation (rest)
                parts = bullet.split(". ", 1)
                headline = parts[0].strip()
                explanation = parts[1].strip() if len(parts) > 1 else ""

                # Infer impact from keywords
                lower_bullet = bullet.lower()
                if any(w in lower_bullet for w in ["risk-on", "easing", "bullish", "recovery", "improving", "strong"]):
                    impact = "bullish"
                elif any(w in lower_bullet for w in ["risk-off", "tightening", "bearish", "deteriorat", "weak", "concern"]):
                    impact = "bearish"
                else:
                    impact = "neutral"

                changes.append({
                    "headline": headline,
                    "explanation": explanation,
                    "impact": impact,
                })

    if changes:
        return changes

    # Fallback: Big Picture first paragraph
    in_big_picture = False
    for line in lines:
        lower = line.lower().strip()
        if "## big picture" in lower or "### big picture" in lower:
            in_big_picture = True
            continue
        if in_big_picture:
            if line.startswith("## ") or line.startswith("### "):
                break
            if line.strip():
                changes.append({
                    "headline": line.strip(),
                    "explanation": "",
                    "impact": "neutral",
                })
                break  # just first paragraph

    return changes


def parse_cross_asset_table(briefing_text):
    """Parse the cross-asset view table from briefing markdown.
    Returns list of dicts with asset, direction, conviction, change.
    Returns empty list if table not found or unparseable."""
    if not briefing_text:
        return []

    lines = briefing_text.split("\n")
    rows = []

    in_section = False
    in_table = False
    headers = []

    for line in lines:
        lower = line.lower().strip()
        if "cross-asset" in lower or "asset allocation" in lower:
            in_section = True
            continue

        if in_section and "|" in line:
            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c]  # remove empty from leading/trailing |

            if not cells:
                continue

            # Skip separator rows
            if all(set(c) <= set("- :") for c in cells):
                continue

            if not in_table:
                headers = [c.lower() for c in cells]
                in_table = True
                continue

            if len(cells) >= 2:
                row = {"asset": cells[0]}
                for j, cell in enumerate(cells[1:], 1):
                    if j < len(headers):
                        row[headers[j]] = cell
                    elif j == 1:
                        row["direction"] = cell
                    elif j == 2:
                        row["conviction"] = cell
                    elif j == 3:
                        row["change"] = cell
                rows.append(row)

        elif in_table and not line.strip().startswith("|"):
            break  # end of table

    return rows


# ---------------------------------------------------------------------------
# Thesis processing
# ---------------------------------------------------------------------------

def process_theses(theses, output_dir):
    """Deduplicate and enrich thesis data for template rendering."""
    # Deduplicate: ACTIVE supersedes DRAFT
    thesis_names = {}
    for name, content in theses:
        base = name.replace("ACTIVE-", "").replace("DRAFT-", "")
        status = "ACTIVE" if "ACTIVE-" in name else "DRAFT"
        if base not in thesis_names:
            thesis_names[base] = (name, content, status)
        elif status == "ACTIVE":
            thesis_names[base] = (name, content, status)

    deduped = sorted(thesis_names.values(), key=lambda x: (0 if x[2] == "ACTIVE" else 1, x[0]))

    # Load chart specs and presentation reports
    thesis_chart_specs = {}
    thesis_presentations = {}
    if output_dir is not None:
        presentations_dir = output_dir / "theses" / "presentations"
        if presentations_dir is not None and presentations_dir.exists():
            for f in presentations_dir.glob("*-charts.json"):
                try:
                    thesis_chart_specs[f.stem.replace("-charts", "")] = json.loads(f.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            for f in presentations_dir.glob("*-report.md"):
                thesis_presentations[f.stem.replace("-report", "")] = f.read_text(encoding="utf-8")

    # Build enriched thesis list
    enriched = []
    for i, (name, content, status) in enumerate(deduped):
        content_lower = content.lower()
        is_structural = (
            "classification:** structural" in content_lower
            or "structural thesis candidate" in content_lower
            or "structural foundation" in content_lower
        )
        thesis_type = "STRUCTURAL" if is_structural else "TACTICAL"
        thesis_key = name.replace("ACTIVE-", "").replace("DRAFT-", "").replace(".md", "")
        clean_name = thesis_key.replace("-", " ").title()

        # Extract conviction from content
        conviction = 50
        conv_match = re.search(r'conviction[:\s]*(\d+)', content_lower)
        if conv_match:
            conviction = min(int(conv_match.group(1)), 100)

        # Count weeks active (look for "week" mentions or dates)
        weeks_active = ""
        weeks_match = re.search(r'(\d+)\s*weeks?\s*(?:active|old|running)', content_lower)
        if weeks_match:
            weeks_active = f"W{weeks_match.group(1)}"

        # Count assumptions
        assumptions_total = 0
        assumptions_intact = 0
        for line in content.split("\n"):
            ll = line.lower().strip()
            if ll.startswith("- ") and ("assumption" in ll or "intact" in ll or "under pressure" in ll or "broken" in ll):
                assumptions_total += 1
                if "intact" in ll or "holds" in ll:
                    assumptions_intact += 1

        # Get presentation report if available
        render_content = thesis_presentations.get(thesis_key, content)
        chart_spec = thesis_chart_specs.get(thesis_key)

        enriched.append({
            "name": clean_name,
            "raw_name": name,
            "thesis_key": thesis_key,
            "status": status,
            "thesis_type": thesis_type,
            "conviction": conviction,
            "weeks_active": weeks_active,
            "assumptions_total": assumptions_total,
            "assumptions_intact": assumptions_intact,
            "content_html": md_to_html(render_content),
            "has_chart": chart_spec is not None,
            "chart_index": i,
        })

    return enriched, thesis_chart_specs


# ---------------------------------------------------------------------------
# Data extraction for metrics strip and mini-charts
# ---------------------------------------------------------------------------

def extract_metrics(snapshot_data):
    """Extract key metrics from snapshot for the hero metrics strip."""
    snap = {}
    if snapshot_data:
        try:
            snap = json.loads(snapshot_data)
        except json.JSONDecodeError:
            return []

    markets = snap.get("markets", snap.get("snapshot", {}).get("markets", {}))
    rates = snap.get("rates", snap.get("snapshot", {}).get("rates", {}))

    metrics = []

    def _num(v):
        """Coerce to float, return None if not numeric."""
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v.replace(",", ""))
            except ValueError:
                return None
        return None

    # S&P 500
    sp = markets.get("SP500", markets.get("^GSPC", {}))
    if isinstance(sp, dict):
        val = _num(sp.get("value", sp.get("close", sp.get("price"))))
        change = sp.get("change_pct", sp.get("pct_change"))
        history = sp.get("history", [])
        if val is not None:
            metrics.append({"label": "S&P 500", "value": f"{val:,.0f}" if val > 100 else f"{val:.2f}",
                            "change": change, "history": history})
    elif isinstance(sp, (int, float)):
        metrics.append({"label": "S&P 500", "value": f"{sp:,.0f}", "change": None, "history": []})

    # VIX
    vix = markets.get("VIX", markets.get("^VIX", {}))
    if isinstance(vix, dict):
        val = _num(vix.get("value", vix.get("close", vix.get("price"))))
        change = vix.get("change_pct", vix.get("pct_change"))
        history = vix.get("history", [])
        if val is not None:
            metrics.append({"label": "VIX", "value": f"{val:.1f}", "change": change, "history": history})
    elif isinstance(vix, (int, float)):
        metrics.append({"label": "VIX", "value": f"{vix:.1f}", "change": None, "history": []})

    # 10Y yield
    for key in ["US10Y", "^TNX", "DGS10"]:
        ty = rates.get(key, markets.get(key, {}))
        if isinstance(ty, dict):
            val = _num(ty.get("value", ty.get("close", ty.get("price"))))
            change = ty.get("change_pct", ty.get("pct_change"))
            history = ty.get("history", [])
            if val is not None:
                metrics.append({"label": "10Y", "value": f"{val:.2f}%", "change": change, "history": history})
                break
        elif isinstance(ty, (int, float)):
            metrics.append({"label": "10Y", "value": f"{ty:.2f}%", "change": None, "history": []})
            break

    # HY OAS
    for key in ["HY_OAS", "BAMLH0A0HYM2", "ICE_HY_OAS"]:
        hy = rates.get(key, snap.get("credit", {}).get(key, {}))
        if isinstance(hy, dict):
            val = _num(hy.get("value", hy.get("close")))
            change = hy.get("change_pct")
            history = hy.get("history", [])
            if val is not None:
                metrics.append({"label": "HY OAS", "value": f"{val:.0f}bp", "change": change, "history": history})
                break
        elif isinstance(hy, (int, float)):
            metrics.append({"label": "HY OAS", "value": f"{hy:.0f}bp", "change": None, "history": []})
            break

    # DXY
    dxy = markets.get("DXY", markets.get("DX-Y.NYB", {}))
    if isinstance(dxy, dict):
        val = _num(dxy.get("value", dxy.get("close", dxy.get("price"))))
        change = dxy.get("change_pct", dxy.get("pct_change"))
        history = dxy.get("history", [])
        if val is not None:
            metrics.append({"label": "DXY", "value": f"{val:.1f}", "change": change, "history": history})
    elif isinstance(dxy, (int, float)):
        metrics.append({"label": "DXY", "value": f"{dxy:.1f}", "change": None, "history": []})

    # Gold
    gold = markets.get("GOLD", markets.get("GC=F", {}))
    if isinstance(gold, dict):
        val = _num(gold.get("value", gold.get("close", gold.get("price"))))
        change = gold.get("change_pct", gold.get("pct_change"))
        history = gold.get("history", [])
        if val is not None:
            metrics.append({"label": "Gold", "value": f"${val:,.0f}", "change": change, "history": history})
    elif isinstance(gold, (int, float)):
        metrics.append({"label": "Gold", "value": f"${gold:,.0f}", "change": None, "history": []})

    return metrics


def extract_mini_chart_data(full_data_text):
    """Extract data series for 2x2 economic dashboard mini-charts from latest-data-full.json."""
    charts = []
    if not full_data_text:
        return charts

    try:
        data = json.loads(full_data_text)
    except json.JSONDecodeError:
        return charts

    # Navigate data structure — could be nested in various ways
    series = data if isinstance(data, dict) else {}

    chart_defs = [
        ("Growth", ["GDP", "GDPC1", "industrial_production", "INDPRO"], "#34d399"),
        ("Inflation", ["CPI", "CPIAUCSL", "PCE", "PCEPI"], "#fbbf24"),
        ("Liquidity", ["M2SL", "M2", "NFCI", "financial_conditions"], "#60a5fa"),
        ("Credit", ["HY_OAS", "BAMLH0A0HYM2", "IG_OAS", "BAMLC0A0CM"], "#f87171"),
    ]

    for label, keys, color in chart_defs:
        values = None
        for key in keys:
            # Try direct lookup
            entry = series.get(key, {})
            if isinstance(entry, dict):
                hist = entry.get("history", entry.get("values", []))
                if hist and isinstance(hist, list):
                    values = hist[-26:]  # last 26 entries
                    break
            # Try nested paths
            for section in ["macro", "rates", "credit", "liquidity", "growth"]:
                nested = series.get(section, {}).get(key, {})
                if isinstance(nested, dict):
                    hist = nested.get("history", nested.get("values", []))
                    if hist and isinstance(hist, list):
                        values = hist[-26:]
                        break
            if values:
                break

        charts.append({"label": label, "values": values or [], "color": color})

    return charts


# ---------------------------------------------------------------------------
# Week browsing (reused from original)
# ---------------------------------------------------------------------------

def discover_weeks(output_dir):
    """Find all available weeks by scanning briefing files."""
    briefings_dir = output_dir / "briefings"
    weeks = []
    if briefings_dir.exists():
        for f in sorted(briefings_dir.glob("*-briefing.md"), reverse=True):
            week = f.name.replace("-briefing.md", "")
            weeks.append(week)
    return weeks


def load_week_data(output_dir, week):
    """Load all data for a given week."""
    briefing = read_file(output_dir / "briefings" / f"{week}-briefing.md")
    improvement = read_file(output_dir / "improvement" / f"{week}-improvement.md")
    synthesis = read_file(output_dir / "synthesis" / f"{week}-synthesis.md")
    return briefing, improvement, synthesis


# ---------------------------------------------------------------------------
# Main dashboard generation
# ---------------------------------------------------------------------------

def generate_html(week, briefing, theses, improvement, synthesis, snapshot_data,
                  all_weeks=None, all_weeks_data=None, regime_history=None,
                  skill_files=None, methodology=None, output_dir=None,
                  full_data_text=None):
    """Generate the full HTML dashboard using Jinja2 template."""

    all_weeks = all_weeks or [week]
    all_weeks_data = all_weeks_data or {}
    regime_history = regime_history or []
    skill_files = skill_files or []
    methodology = methodology or ""

    # Parse regime data
    regime_data = parse_regime_from_synthesis(synthesis)

    # Count consecutive weeks unchanged
    weeks_unchanged = 0
    if regime_history:
        current = regime_data["regime"]
        for r in reversed(regime_history):
            if r.get("regime") == current:
                weeks_unchanged += 1
            else:
                break

    # Generate SVGs
    regime_map_svg = generate_svg_regime_map(regime_data, regime_history)
    timeline_svg = generate_svg_timeline(regime_history)

    # Metrics
    metrics = extract_metrics(snapshot_data)
    for m in metrics:
        m["sparkline"] = generate_sparkline(m.get("history", []), width=60, height=16)

    # Mini charts
    mini_charts_data = extract_mini_chart_data(full_data_text)
    mini_charts = []
    for mc in mini_charts_data:
        svg = generate_svg_mini_chart(mc["values"], mc["label"], mc["color"])
        mini_charts.append({"label": mc["label"], "svg": svg})

    # What Changed
    key_changes = parse_key_changes(briefing)

    # Cross-asset heatmap
    cross_asset = parse_cross_asset_table(briefing)

    # Theses
    enriched_theses, thesis_chart_specs = process_theses(theses, output_dir)

    # Briefing HTML
    briefing_html = md_to_html(briefing) if briefing else ""

    # Improvement HTML
    improvement_html = md_to_html(improvement) if improvement else ""

    # Skills accordion data
    skills_data = []
    for name, content in skill_files:
        clean_name = name.replace(".md", "").replace("-", " ").title()
        first_line = ""
        for line in content.split("\n"):
            if line.strip().startswith("##") and "Objective" not in line:
                continue
            if line.strip() and not line.startswith("#") and not line.startswith("---"):
                first_line = line.strip()[:120]
                break
        skills_data.append({"name": clean_name, "description": first_line, "content_html": md_to_html(content)})

    # Methodology HTML
    methodology_html = md_to_html(methodology) if methodology else ""

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Load Jinja2 template
    script_dir = Path(__file__).parent
    template_path = script_dir / "dashboard-template.html"
    if not template_path.exists():
        print(f"ERROR: Template not found at {template_path}", file=sys.stderr)
        print("Expected: scripts/dashboard-template.html", file=sys.stderr)
        sys.exit(1)

    # Load assets from local assets/ directory
    assets_dir = script_dir / "assets"
    try:
        chart_js = inline_asset(assets_dir / "chart.min.js")
    except FileNotFoundError:
        print("WARNING: Chart.js not found at scripts/assets/chart.min.js — thesis charts will not render", file=sys.stderr)
        chart_js = "/* Chart.js not available */"

    try:
        font_data_uri = inline_asset(assets_dir / "inter-latin.woff2")
    except FileNotFoundError:
        print("WARNING: Inter font not found — using system fonts", file=sys.stderr)
        font_data_uri = ""

    env = Environment(
        loader=FileSystemLoader(str(script_dir)),
        autoescape=select_autoescape([]),
    )
    template = env.get_template("dashboard-template.html")

    # Regime CSS class helper
    def regime_css_class(regime_name):
        return regime_name.lower().replace(" ", "-").replace("disinflationary-slowdown", "disinflation")

    html = template.render(
        week=week,
        generated=generated,
        regime_data=regime_data,
        regime_css_class=regime_css_class(regime_data["regime"]),
        regime_color=REGIME_COLORS.get(regime_data["regime"], "#8b8fa3"),
        weeks_unchanged=weeks_unchanged,
        regime_map_svg=regime_map_svg,
        metrics=metrics,
        key_changes=key_changes,
        mini_charts=mini_charts,
        timeline_svg=timeline_svg,
        regime_history=regime_history,
        theses=enriched_theses,
        thesis_chart_specs_json=json.dumps(thesis_chart_specs) if thesis_chart_specs else "{}",
        cross_asset=cross_asset,
        briefing_html=briefing_html,
        improvement_html=improvement_html,
        skills=skills_data,
        methodology_html=methodology_html,
        chart_js=chart_js,
        font_data_uri=font_data_uri,
        all_weeks=all_weeks,
    )

    return html


def main():
    parser = argparse.ArgumentParser(description="Generate Macro Advisor HTML Dashboard")
    parser.add_argument("--week", required=True, help="Week identifier (e.g., 2026-W12)")
    parser.add_argument("--output-dir", required=True, help="Macro Advisor outputs directory")
    parser.add_argument("--out", required=True, help="Output HTML file path")
    parser.add_argument("--plugin-root", default=None, help="Plugin root directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    # Discover all available weeks
    all_weeks = discover_weeks(output_dir)
    if not all_weeks:
        all_weeks = [args.week]
    if args.week not in all_weeks:
        all_weeks.insert(0, args.week)

    # Read current week data
    briefing = read_file(output_dir / "briefings" / f"{args.week}-briefing.md")
    theses = []
    for subdir in ["active", "closed"]:
        theses_dir = output_dir / "theses" / subdir
        if theses_dir.exists():
            for f in sorted(theses_dir.glob("*.md")):
                theses.append((f.name, f.read_text(encoding="utf-8")))

    improvement = read_file(output_dir / "improvement" / f"{args.week}-improvement.md")
    synthesis = read_file(output_dir / "synthesis" / f"{args.week}-synthesis.md")
    snapshot = read_file(output_dir / "data" / "latest-snapshot.json")
    full_data = read_file(output_dir / "data" / "latest-data-full.json")

    # Build historical regime data
    regime_history = []
    for w in reversed(all_weeks):
        syn = read_file(output_dir / "synthesis" / f"{w}-synthesis.md")
        if syn:
            rd = parse_regime_from_synthesis(syn)
            rd["week"] = w
            # Get synthesis summary for timeline popovers
            for line in syn.split("\n"):
                if line.strip() and not line.startswith("#") and not line.startswith("---"):
                    rd["summary"] = line.strip()[:150]
                    break
            regime_history.append(rd)

    # Load all weeks data
    all_weeks_data = {}
    for w in all_weeks:
        b, imp, syn = load_week_data(output_dir, w)
        all_weeks_data[w] = {"briefing": b, "improvement": imp, "synthesis": syn}

    # Read skill files
    skills_dir = output_dir.parent / "skills"
    skill_files = []
    if skills_dir.exists():
        for f in sorted(skills_dir.glob("*.md")):
            skill_files.append((f.name, f.read_text(encoding="utf-8")))

    # Read methodology
    methodology = ""
    if args.plugin_root:
        methodology = read_file(Path(args.plugin_root) / "skills" / "macro-advisor" / "references" / "methodology.md")

    # Generate HTML
    html = generate_html(
        args.week, briefing, theses, improvement, synthesis, snapshot,
        all_weeks=all_weeks,
        all_weeks_data=all_weeks_data,
        regime_history=regime_history,
        skill_files=skill_files,
        methodology=methodology,
        output_dir=output_dir,
        full_data_text=full_data,
    )

    # Write output
    out_path = Path(args.out)
    out_path.write_text(html, encoding="utf-8")
    print(f"Dashboard generated: {out_path} ({len(html):,} bytes)")
    print(f"Weeks available: {len(all_weeks)} ({', '.join(all_weeks)})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
