#!/usr/bin/env python3
"""
Macro Advisor — Weekly Dashboard Generator
Reads all output files and produces a single HTML dashboard with:
- Regime visualization (four-quadrant scatter with current position + history)
- Monday briefing (formatted)
- Active theses (formatted)
- Improvement report (formatted)

Usage:
    python generate_dashboard.py --week 2026-W12 --output-dir outputs/ --out dashboard.html
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def read_file(path):
    """Read a file, return empty string if not found."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def md_to_html(md_text):
    """Simple markdown to HTML conversion — handles headers, bold, tables, lists, code blocks."""
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
                lang = line.strip().replace("```", "")
                html_lines.append(f'<div class="code-block"><pre>')
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
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Inline code
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # Links
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text


def parse_regime_from_synthesis(synthesis_text):
    """Extract regime data including forecasts from synthesis for the visualization."""
    regime = "Unknown"
    direction = "Stable"
    confidence = "Medium"
    forecast_6m = "Unknown"
    forecast_12m = "Unknown"
    forecast_6m_confidence = "Low"
    forecast_12m_confidence = "Low"

    lines = synthesis_text.split("\n")
    in_forecast_section = False

    for i, line in enumerate(lines):
        lower = line.lower()

        # Current regime
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

        # Forecast section detection
        if "regime forecast" in lower or "6 and 12 month" in lower:
            in_forecast_section = True

        if in_forecast_section:
            # Look for 6-month forecast regime
            if ("6 month" in lower or "6-month" in lower) and "most likely" in lower:
                if "goldilocks" in lower:
                    forecast_6m = "Goldilocks"
                elif "overheating" in lower:
                    forecast_6m = "Overheating"
                elif "stagflation" in lower:
                    forecast_6m = "Stagflation"
                elif "disinflation" in lower or "slowdown" in lower:
                    forecast_6m = "Disinflationary Slowdown"

            # Look for 12-month forecast regime
            if ("12 month" in lower or "12-month" in lower) and "most likely" in lower:
                if "goldilocks" in lower:
                    forecast_12m = "Goldilocks"
                elif "overheating" in lower:
                    forecast_12m = "Overheating"
                elif "stagflation" in lower:
                    forecast_12m = "Stagflation"
                elif "disinflation" in lower or "slowdown" in lower:
                    forecast_12m = "Disinflationary Slowdown"

    # Map regime to coordinates
    # X = growth direction (-1 to 1), Y = inflation direction (-1 to 1)
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
        "x": x,
        "y": y,
        "forecast_6m": forecast_6m,
        "forecast_6m_x": f6x,
        "forecast_6m_y": f6y,
        "forecast_12m": forecast_12m,
        "forecast_12m_x": f12x,
        "forecast_12m_y": f12y,
    }


def generate_html(week, briefing, theses, improvement, synthesis, snapshot_data,
                   all_weeks=None, all_weeks_data=None, regime_history=None,
                   skill_files=None, methodology=None):
    """Generate the full HTML dashboard with multi-week history support."""

    all_weeks = all_weeks or [week]
    all_weeks_data = all_weeks_data or {}
    regime_history = regime_history or []
    skill_files = skill_files or []
    methodology = methodology or ""

    regime_data = parse_regime_from_synthesis(synthesis)

    # Parse snapshot for key numbers
    snap = {}
    if snapshot_data:
        try:
            snap = json.loads(snapshot_data)
        except json.JSONDecodeError:
            snap = {}

    # Deduplicate theses: if both ACTIVE- and DRAFT- versions exist for the same
    # thesis name, keep only the ACTIVE version (DRAFT is superseded).
    thesis_names = {}
    for name, content in theses:
        base = name.replace("ACTIVE-", "").replace("DRAFT-", "")
        status = "ACTIVE" if "ACTIVE-" in name else "DRAFT"
        if base not in thesis_names:
            thesis_names[base] = (name, content, status)
        elif status == "ACTIVE":
            # ACTIVE supersedes DRAFT
            thesis_names[base] = (name, content, status)
        # else: DRAFT doesn't overwrite ACTIVE

    # Sort: ACTIVE first, then DRAFT
    deduped = sorted(thesis_names.values(), key=lambda x: (0 if x[2] == "ACTIVE" else 1, x[0]))

    # Load thesis chart specs from presentations directory
    presentations_dir = output_dir / "theses" / "presentations"
    thesis_chart_specs = {}
    if presentations_dir.exists():
        for f in presentations_dir.glob("*-charts.json"):
            try:
                thesis_chart_specs[f.stem.replace("-charts", "")] = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

    # Load thesis presentation reports (Skill 12 output) for enriched rendering
    thesis_presentations = {}
    if presentations_dir.exists():
        for f in presentations_dir.glob("*-report.md"):
            thesis_presentations[f.stem.replace("-report", "")] = f.read_text(encoding="utf-8")

    # Build thesis tabs HTML
    thesis_tabs = ""
    thesis_contents = ""
    for i, (name, content, status) in enumerate(deduped):
        active_class = "active" if i == 0 else ""
        display = "block" if i == 0 else "none"
        clean_name = name.replace("ACTIVE-", "").replace("DRAFT-", "").replace(".md", "").replace("-", " ").title()

        # Detect thesis type: structural vs tactical
        content_lower = content.lower()
        is_structural = (
            "classification:** structural" in content_lower
            or "structural thesis candidate" in content_lower
            or "structural foundation" in content_lower
        )
        thesis_type = "STRUCTURAL" if is_structural else "TACTICAL"
        type_badge_class = "badge-structural" if is_structural else "badge-tactical"

        badge_class = "badge-active" if status == "ACTIVE" else "badge-draft"

        # Use presentation report if available, otherwise raw thesis
        thesis_key = name.replace("ACTIVE-", "").replace("DRAFT-", "").replace(".md", "")
        render_content = thesis_presentations.get(thesis_key, content)

        # Build chart HTML if chart spec exists
        chart_html = ""
        chart_spec = thesis_chart_specs.get(thesis_key)
        if chart_spec:
            chart_id = f"thesis-chart-{i}"
            chart_html = f'<div class="chart-container"><h3>{chart_spec.get("title", "Thesis Chart")}</h3><canvas id="{chart_id}"></canvas></div>'

        thesis_tabs += (
            f'<button class="thesis-tab {active_class}" onclick="showThesis({i})">'
            f'{clean_name} '
            f'<span class="badge {type_badge_class}">{thesis_type}</span>'
            f'<span class="badge {badge_class}">{status}</span>'
            f'</button>\n'
        )
        thesis_contents += (
            f'<div class="thesis-content" id="thesis-{i}" style="display:{display}">'
            f'{chart_html}'
            f'{md_to_html(render_content)}'
            f'</div>\n'
        )

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Pre-build week-switchable content outside the f-string to avoid brace conflicts
    week_options_html = ''.join(
        f'<option value="{w}" {"selected" if w == week else ""}>{w}</option>'
        for w in all_weeks
    )

    briefing_weeks_html = ""
    for w in all_weeks:
        display = "block" if w == week else "none"
        wd = all_weeks_data.get(w, {})
        content = wd.get("briefing", "")
        if not content and w == week:
            content = briefing
        if not content:
            content = f"No briefing available for {w}."
        briefing_weeks_html += f'<div class="week-content" data-week="{w}" style="display:{display}">{md_to_html(content)}</div>\n'

    improvement_weeks_html = ""
    for w in all_weeks:
        display = "block" if w == week else "none"
        wd = all_weeks_data.get(w, {})
        content = wd.get("improvement", "")
        if not content and w == week:
            content = improvement
        if not content:
            content = f"No improvement report available for {w}."
        improvement_weeks_html += f'<div class="week-content" data-week="{w}" style="display:{display}">{md_to_html(content)}</div>\n'

    # Build skills accordion HTML
    skills_html = ""
    for name, content in skill_files:
        clean_name = name.replace(".md", "").replace("-", " ").title()
        # Extract first line as description
        first_line = ""
        for line in content.split("\n"):
            if line.strip().startswith("##") and "Objective" not in line:
                continue
            if line.strip() and not line.startswith("#") and not line.startswith("---"):
                first_line = line.strip()[:120]
                break
        skills_html += f'''<div class="skill-accordion">
            <button class="skill-header" onclick="this.classList.toggle('open'); this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'block' ? 'none' : 'block';">
                <span class="skill-name">{clean_name}</span>
                <span class="skill-desc">{first_line}...</span>
                <span class="skill-arrow">&#9660;</span>
            </button>
            <div class="skill-body" style="display:none">{md_to_html(content)}</div>
        </div>\n'''

    # Build methodology (About) HTML
    methodology_html = md_to_html(methodology) if methodology else "<p>No methodology document found.</p>"

    # Build thesis chart specs JSON for frontend rendering
    # NOTE: This is injected via string concatenation after the f-string,
    # because JSON contains braces that conflict with f-string interpolation.
    thesis_chart_specs_raw = json.dumps(thesis_chart_specs) if thesis_chart_specs else '{}'

    # Build regime history trail data points
    history_points = ', '.join(
        f'{{ x: {r["x"]}, y: {r["y"]} }}'
        for r in regime_history[:-1]  # all except current (current is its own dataset)
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Macro Advisor — {week}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {{
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #242836;
    --border: #2e3345;
    --text: #e4e4e7;
    --text-muted: #8b8fa3;
    --accent: #60a5fa;
    --green: #34d399;
    --red: #f87171;
    --yellow: #fbbf24;
    --orange: #fb923c;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 0;
}}
.header {{
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 24px 40px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.header h1 {{
    font-size: 20px;
    font-weight: 600;
    letter-spacing: -0.02em;
}}
.header .meta {{
    color: var(--text-muted);
    font-size: 13px;
}}
.regime-banner {{
    background: var(--surface2);
    border-bottom: 1px solid var(--border);
    padding: 20px 40px;
    display: flex;
    gap: 40px;
    align-items: center;
}}
.regime-label {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.03em;
}}
.regime-detail {{
    color: var(--text-muted);
    font-size: 14px;
}}
.regime-detail strong {{
    color: var(--text);
}}
.nav {{
    display: flex;
    gap: 0;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0 40px;
}}
.nav button {{
    background: none;
    border: none;
    color: var(--text-muted);
    padding: 14px 20px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
}}
.nav button:hover {{
    color: var(--text);
}}
.nav button.active {{
    color: var(--accent);
    border-bottom-color: var(--accent);
}}
.main {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 32px 40px;
}}
.tab-content {{
    display: none;
}}
.tab-content.active {{
    display: block;
}}
.chart-container {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 32px;
    position: relative;
}}
.chart-container h3 {{
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 16px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
canvas {{
    max-height: 400px;
}}
/* Content styling */
h1 {{ font-size: 24px; font-weight: 700; margin: 32px 0 16px; letter-spacing: -0.02em; }}
h2 {{ font-size: 20px; font-weight: 600; margin: 28px 0 12px; letter-spacing: -0.01em; color: var(--accent); }}
h3 {{ font-size: 16px; font-weight: 600; margin: 24px 0 10px; }}
h4 {{ font-size: 14px; font-weight: 600; margin: 20px 0 8px; }}
p {{ margin: 8px 0; color: var(--text); }}
ul {{ margin: 8px 0 8px 24px; }}
li {{ margin: 4px 0; }}
hr {{ border: none; border-top: 1px solid var(--border); margin: 24px 0; }}
strong {{ color: #fff; }}
code {{ background: var(--surface2); padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
a {{ color: var(--accent); text-decoration: none; }}
.table-wrapper {{ overflow-x: auto; margin: 16px 0; }}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}}
th {{
    background: var(--surface2);
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
}}
td {{
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
}}
tr:hover td {{
    background: var(--surface2);
}}
.code-block {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    margin: 12px 0;
    overflow-x: auto;
}}
.code-block pre {{
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 13px;
    line-height: 1.5;
}}
/* Thesis tabs */
.thesis-tabs {{
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}}
.thesis-tab {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 16px;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
}}
.thesis-tab:hover {{
    border-color: var(--accent);
    color: var(--text);
}}
.thesis-tab.active {{
    background: var(--surface2);
    border-color: var(--accent);
    color: var(--text);
}}
.badge {{
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-left: 6px;
}}
.badge-active {{
    background: rgba(52, 211, 153, 0.15);
    color: var(--green);
}}
.badge-draft {{
    background: rgba(251, 191, 36, 0.15);
    color: var(--yellow);
}}
.badge-structural {{
    background: rgba(168, 85, 247, 0.15);
    color: #a855f7;
}}
.badge-tactical {{
    background: rgba(96, 165, 250, 0.12);
    color: var(--accent);
}}
/* Briefing sections */
.briefing-hero {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 28px;
    margin-bottom: 24px;
}}
.briefing-hero .regime-tag {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 12px;
}}
.briefing-section {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
}}
.briefing-section h2 {{
    margin-top: 0;
    font-size: 16px;
}}
/* Regime colors */
.regime-goldilocks {{ color: var(--green); }}
.regime-overheating {{ color: var(--orange); }}
.regime-stagflation {{ color: var(--red); }}
.regime-disinflation {{ color: var(--accent); }}
/* Skill accordion */
.skill-accordion {{
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 8px;
    overflow: hidden;
}}
.skill-header {{
    width: 100%;
    background: var(--surface);
    border: none;
    padding: 14px 18px;
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    text-align: left;
    color: var(--text);
    transition: background 0.2s;
}}
.skill-header:hover {{
    background: var(--surface2);
}}
.skill-header.open {{
    background: var(--surface2);
    border-bottom: 1px solid var(--border);
}}
.skill-name {{
    font-weight: 600;
    font-size: 14px;
    min-width: 200px;
}}
.skill-desc {{
    color: var(--text-muted);
    font-size: 12px;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.skill-arrow {{
    color: var(--text-muted);
    font-size: 10px;
    transition: transform 0.2s;
}}
.skill-header.open .skill-arrow {{
    transform: rotate(180deg);
}}
.skill-body {{
    padding: 20px;
    background: var(--bg);
    font-size: 14px;
    max-height: 600px;
    overflow-y: auto;
}}
</style>
</head>
<body>

<div class="header">
    <h1>Macro Advisor</h1>
    <div style="display:flex; align-items:center; gap:16px;">
        <select id="weekSelector" onchange="switchWeek(this.value)" style="background:var(--surface2); color:var(--text); border:1px solid var(--border); padding:8px 12px; border-radius:6px; font-size:13px; cursor:pointer;">
            {week_options_html}
        </select>
        <div class="meta">Generated {generated}</div>
    </div>
</div>

<div class="regime-banner">
    <div>
        <div class="regime-label regime-{regime_data['regime'].lower().replace(' ', '-').replace('disinflationary-slowdown', 'disinflation')}">{regime_data['regime']}</div>
        <div class="regime-detail">Direction: <strong>{regime_data['direction']}</strong> &middot; Confidence: <strong>{regime_data['confidence']}</strong></div>
    </div>
</div>

<div class="nav">
    <button class="active" onclick="showTab('briefing')">Briefing</button>
    <button onclick="showTab('regime')">Regime Map</button>
    <button onclick="showTab('theses')">Theses</button>
    <button onclick="showTab('improvement')">System Health</button>
    <button onclick="showTab('skills')">Skills</button>
    <button onclick="showTab('about')">About</button>
</div>

<div class="main">
    <!-- Briefing Tab -->
    <div class="tab-content active" id="tab-briefing">
        {briefing_weeks_html}
    </div>

    <!-- Regime Map Tab -->
    <div class="tab-content" id="tab-regime">
        <div class="chart-container">
            <h3>Regime Map — Current Position</h3>
            <canvas id="regimeChart"></canvas>
        </div>
        <p style="color: var(--text-muted); font-size: 13px;">
            <strong>Blue circle:</strong> This week's regime assessment based on current data.
            <strong>Yellow triangle:</strong> 6-month forecast — where the analysis says we're heading, based on policy trajectory, credit cycle, and growth/inflation trends. Not a linear extrapolation.
            <strong>Red square:</strong> 12-month forecast — longer-term projection with lower confidence. Both forecasts are derived from the synthesis reasoning, with stated assumptions that could change the trajectory.
            As weekly runs accumulate, prior weeks will appear as a fading trail showing how the regime has evolved.
        </p>
    </div>

    <!-- Theses Tab -->
    <div class="tab-content" id="tab-theses">
        <h2>Investment Theses</h2>
        <div class="thesis-tabs">
            {thesis_tabs}
        </div>
        {thesis_contents}
    </div>

    <!-- Improvement Tab -->
    <div class="tab-content" id="tab-improvement">
        {improvement_weeks_html}
    </div>

    <!-- Skills Tab -->
    <div class="tab-content" id="tab-skills">
        <h2>System Skills</h2>
        <p style="color: var(--text-muted); margin-bottom: 20px;">Click any skill to expand and read its full definition.</p>
        {skills_html}
    </div>

    <!-- About Tab -->
    <div class="tab-content" id="tab-about">
        {methodology_html}
    </div>
</div>

<script>
// Week switching
function switchWeek(selectedWeek) {{
    document.querySelectorAll('.week-content').forEach(el => {{
        el.style.display = el.dataset.week === selectedWeek ? 'block' : 'none';
    }});
}}

// Tab navigation
function showTab(tabId) {{
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + tabId).classList.add('active');
    event.target.classList.add('active');
}}

// Thesis tabs
function showThesis(idx) {{
    document.querySelectorAll('.thesis-content').forEach(t => t.style.display = 'none');
    document.querySelectorAll('.thesis-tab').forEach(t => t.classList.remove('active'));
    document.getElementById('thesis-' + idx).style.display = 'block';
    document.querySelectorAll('.thesis-tab')[idx].classList.add('active');
}}

// Regime Chart
const ctx = document.getElementById('regimeChart').getContext('2d');
new Chart(ctx, {{
    type: 'scatter',
    data: {{
        datasets: [
            {{
                label: 'This Week',
                data: [{{ x: {regime_data['x']}, y: {regime_data['y']} }}],
                backgroundColor: '#60a5fa',
                borderColor: '#60a5fa',
                pointRadius: 12,
                pointHoverRadius: 14,
                pointStyle: 'circle',
            }},
            {{
                label: '6-Month Forecast ({regime_data["forecast_6m"]})',
                data: {regime_data["forecast_6m"] != "Unknown" and f'[{{ x: {regime_data["forecast_6m_x"]}, y: {regime_data["forecast_6m_y"]} }}]' or '[]'},
                backgroundColor: 'rgba(251, 191, 36, 0.6)',
                borderColor: '#fbbf24',
                borderWidth: 2,
                borderDash: [5, 5],
                pointRadius: 10,
                pointHoverRadius: 12,
                pointStyle: 'triangle',
            }},
            {{
                label: 'Historical Trail',
                data: [{history_points}],
                backgroundColor: 'rgba(96, 165, 250, 0.2)',
                borderColor: 'rgba(96, 165, 250, 0.3)',
                pointRadius: 5,
                pointHoverRadius: 7,
                pointStyle: 'circle',
                showLine: true,
                borderWidth: 1,
                borderDash: [2, 2],
            }},
            {{
                label: '12-Month Forecast ({regime_data["forecast_12m"]})',
                data: {regime_data["forecast_12m"] != "Unknown" and f'[{{ x: {regime_data["forecast_12m_x"]}, y: {regime_data["forecast_12m_y"]} }}]' or '[]'},
                backgroundColor: 'rgba(248, 113, 113, 0.4)',
                borderColor: '#f87171',
                borderWidth: 2,
                borderDash: [3, 3],
                pointRadius: 8,
                pointHoverRadius: 10,
                pointStyle: 'rect',
            }}
        ]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 1.6,
        scales: {{
            x: {{
                min: -1.2,
                max: 1.2,
                title: {{
                    display: true,
                    text: 'Growth Direction →',
                    color: '#8b8fa3',
                    font: {{ size: 13, weight: '600' }}
                }},
                grid: {{
                    color: 'rgba(255,255,255,0.06)',
                    drawTicks: false,
                }},
                ticks: {{
                    callback: function(v) {{
                        if (v === -1) return 'Falling';
                        if (v === 0) return '';
                        if (v === 1) return 'Rising';
                        return '';
                    }},
                    color: '#8b8fa3',
                    font: {{ size: 11 }}
                }},
                border: {{ color: 'rgba(255,255,255,0.1)' }}
            }},
            y: {{
                min: -1.2,
                max: 1.2,
                title: {{
                    display: true,
                    text: '↑ Inflation Direction',
                    color: '#8b8fa3',
                    font: {{ size: 13, weight: '600' }}
                }},
                grid: {{
                    color: 'rgba(255,255,255,0.06)',
                    drawTicks: false,
                }},
                ticks: {{
                    callback: function(v) {{
                        if (v === -1) return 'Falling';
                        if (v === 0) return '';
                        if (v === 1) return 'Rising';
                        return '';
                    }},
                    color: '#8b8fa3',
                    font: {{ size: 11 }}
                }},
                border: {{ color: 'rgba(255,255,255,0.1)' }}
            }}
        }},
        plugins: {{
            legend: {{ display: true, labels: {{ color: '#8b8fa3', font: {{ size: 12 }} }} }},
            annotation: {{}}
        }}
    }},
    plugins: [{{
        id: 'quadrantLabels',
        afterDraw: function(chart) {{
            const {{ ctx, chartArea }} = chart;
            const midX = (chartArea.left + chartArea.right) / 2;
            const midY = (chartArea.top + chartArea.bottom) / 2;

            ctx.save();
            ctx.font = '600 14px -apple-system, sans-serif';
            ctx.textAlign = 'center';
            ctx.globalAlpha = 0.25;

            // Goldilocks (top-right → growth rising, inflation falling → bottom-right)
            ctx.fillStyle = '#34d399';
            ctx.fillText('GOLDILOCKS', (midX + chartArea.right) / 2, (midY + chartArea.bottom) / 2);

            // Overheating (growth rising, inflation rising → top-right)
            ctx.fillStyle = '#fb923c';
            ctx.fillText('OVERHEATING', (midX + chartArea.right) / 2, (chartArea.top + midY) / 2);

            // Disinflationary Slowdown (growth falling, inflation falling → bottom-left)
            ctx.fillStyle = '#60a5fa';
            ctx.fillText('DISINFLATION', (chartArea.left + midX) / 2, (midY + chartArea.bottom) / 2);

            // Stagflation (growth falling, inflation rising → top-left)
            ctx.fillStyle = '#f87171';
            ctx.fillText('STAGFLATION', (chartArea.left + midX) / 2, (chartArea.top + midY) / 2);

            // Draw crosshairs
            ctx.globalAlpha = 0.15;
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(midX, chartArea.top);
            ctx.lineTo(midX, chartArea.bottom);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(chartArea.left, midY);
            ctx.lineTo(chartArea.right, midY);
            ctx.stroke();

            ctx.restore();
        }}
    }}]
}});

// Thesis-specific charts (rendered from Skill 12 chart specs)
const thesisChartSpecs = __THESIS_CHART_SPECS_PLACEHOLDER__;
Object.entries(thesisChartSpecs).forEach(([key, spec]) => {{
    // Find the canvas by looking for thesis-chart-N pattern
    const canvases = document.querySelectorAll('canvas[id^="thesis-chart-"]');
    canvases.forEach(canvas => {{
        if (canvas.closest('.thesis-content') && !canvas._chartRendered) {{
            const datasets = (spec.datasets || []).map((ds, idx) => ({{
                label: ds.label || 'Series',
                data: ds.data || [],
                borderColor: ds.color || ['#60a5fa', '#34d399', '#f87171', '#fbbf24'][idx % 4],
                backgroundColor: 'transparent',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.3,
            }}));
            if (datasets.length > 0 && datasets[0].data.length > 0) {{
                new Chart(canvas.getContext('2d'), {{
                    type: spec.chart_type || 'line',
                    data: {{
                        labels: datasets[0].data.map(d => d.x || d.date || ''),
                        datasets: datasets.map(ds => ({{
                            ...ds,
                            data: ds.data.map(d => d.y || d.value || d),
                        }})),
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: true,
                        aspectRatio: 2.5,
                        scales: {{
                            x: {{ grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#8b8fa3', maxTicksLimit: 10 }} }},
                            y: {{ grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#8b8fa3' }} }},
                        }},
                        plugins: {{ legend: {{ labels: {{ color: '#8b8fa3' }} }} }},
                    }},
                }});
                canvas._chartRendered = true;
            }}
        }}
    }});
}});
</script>

</body>
</html>"""

    # Replace the chart specs placeholder with actual JSON (avoids f-string brace conflicts)
    html = html.replace('__THESIS_CHART_SPECS_PLACEHOLDER__', thesis_chart_specs_raw)

    return html


def discover_weeks(output_dir):
    """Find all available weeks by scanning briefing files."""
    briefings_dir = output_dir / "briefings"
    weeks = []
    if briefings_dir.exists():
        for f in sorted(briefings_dir.glob("*-briefing.md"), reverse=True):
            # Extract week from filename like 2026-W12-briefing.md
            week = f.name.replace("-briefing.md", "")
            weeks.append(week)
    return weeks


def load_week_data(output_dir, week):
    """Load all data for a given week."""
    briefing = read_file(output_dir / "briefings" / f"{week}-briefing.md")
    improvement = read_file(output_dir / "improvement" / f"{week}-improvement.md")
    synthesis = read_file(output_dir / "synthesis" / f"{week}-synthesis.md")
    return briefing, improvement, synthesis


def main():
    parser = argparse.ArgumentParser(description="Generate Macro Advisor HTML Dashboard")
    parser.add_argument("--week", required=True, help="Week identifier (e.g., 2026-W12)")
    parser.add_argument("--output-dir", required=True, help="Macro Advisor outputs directory")
    parser.add_argument("--out", required=True, help="Output HTML file path")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    # Discover all available weeks
    all_weeks = discover_weeks(output_dir)
    if not all_weeks:
        all_weeks = [args.week]
    if args.week not in all_weeks:
        all_weeks.insert(0, args.week)

    # Read current week briefing
    briefing = read_file(output_dir / "briefings" / f"{args.week}-briefing.md")

    # Read all thesis files (active + closed)
    theses = []
    for subdir in ["active", "closed"]:
        theses_dir = output_dir / "theses" / subdir
        if theses_dir.exists():
            for f in sorted(theses_dir.glob("*.md")):
                theses.append((f.name, f.read_text(encoding="utf-8")))

    # Read improvement
    improvement = read_file(output_dir / "improvement" / f"{args.week}-improvement.md")

    # Read synthesis (for regime data)
    synthesis = read_file(output_dir / "synthesis" / f"{args.week}-synthesis.md")

    # Build historical regime data for all weeks (for the regime trail)
    regime_history = []
    for w in reversed(all_weeks):  # oldest first
        syn = read_file(output_dir / "synthesis" / f"{w}-synthesis.md")
        if syn:
            rd = parse_regime_from_synthesis(syn)
            rd["week"] = w
            regime_history.append(rd)

    # Load all weeks' briefings and improvements for the history selector
    all_weeks_data = {}
    for w in all_weeks:
        b, imp, syn = load_week_data(output_dir, w)
        all_weeks_data[w] = {"briefing": b, "improvement": imp, "synthesis": syn}

    # Read snapshot
    snapshot = read_file(output_dir / "data" / "latest-snapshot.json")

    # Read skill files for the Skills tab
    skills_dir = output_dir.parent / "skills"
    skill_files = []
    if skills_dir.exists():
        for f in sorted(skills_dir.glob("*.md")):
            skill_files.append((f.name, f.read_text(encoding="utf-8")))

    # Read methodology for the About tab
    methodology = read_file(output_dir.parent / "methodology.md")

    # Generate HTML — pass all weeks data, regime history, skills, methodology
    html = generate_html(
        args.week, briefing, theses, improvement, synthesis, snapshot,
        all_weeks=all_weeks,
        all_weeks_data=all_weeks_data,
        regime_history=regime_history,
        skill_files=skill_files,
        methodology=methodology,
    )

    # Write output
    out_path = Path(args.out)
    out_path.write_text(html, encoding="utf-8")
    print(f"Dashboard generated: {out_path} ({len(html):,} bytes)")
    print(f"Weeks available: {len(all_weeks)} ({', '.join(all_weeks)})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
