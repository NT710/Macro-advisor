#!/usr/bin/env python3
"""
Trading Dashboard Generator (Alpine Report Edition)

Produces a self-contained HTML file with three tabs:
  1. P&L — portfolio value chart, return metrics with sparklines, attribution
  2. Trades — trade log with sort/filter, closed trades
  3. Improvements — system health, pending amendment proposals, evaluated amendments

Uses Jinja2 template at scripts/trading-dashboard-template.html.
Design tokens are in scripts/design_tokens.py (local copy, duplicated in macro-advisor).

Usage:
    python generate_dashboard.py \
        --portfolio outputs/portfolio/ \
        --trades outputs/trades/ \
        --performance outputs/performance/ \
        --improvement outputs/improvement/ \
        --output outputs/dashboard/
"""

import argparse
import base64
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path
import html as html_lib

from jinja2 import Environment, FileSystemLoader, select_autoescape

# ---------------------------------------------------------------------------
# Import local design tokens
# ---------------------------------------------------------------------------

from design_tokens import CSS_VARIABLES, FONT_FACE_CSS


def load_json(path):
    """Load a JSON file, return empty dict/list on failure."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_all_json(directory, pattern):
    """Load all JSON files matching a glob pattern."""
    results = []
    for f in sorted(Path(directory).glob(pattern)):
        try:
            with open(f, "r") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return results


def load_snapshots(portfolio_dir):
    """Load portfolio snapshots for the value chart."""
    snapshots = []
    for f in sorted(Path(portfolio_dir).glob("*-snapshot.json")):
        if f.name == "latest-snapshot.json":
            continue
        try:
            with open(f, "r") as fh:
                snap = json.load(fh)
                snapshots.append(snap)
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return snapshots


def esc(text):
    """Escape text for safe HTML embedding."""
    if text is None:
        return ""
    return html_lib.escape(str(text))


def fmt_money(val):
    """Format a number as currency."""
    if val is None:
        return "—"
    try:
        return f"${val:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def fmt_pct(val):
    """Format a number as percentage."""
    if val is None:
        return "—"
    try:
        return f"{val:+.2f}%"
    except (ValueError, TypeError):
        return str(val)


def _num(val, default=0):
    """Coerce a value to float, returning default for None/non-numeric."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


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


def generate_sparkline(values, width=80, height=20, color="currentColor", stroke_width=1.5):
    """Generate an inline SVG sparkline.

    Returns empty string for <2 non-None values.
    Handles None/NaN values by drawing broken line segments with gaps.
    All-equal values render as a flat horizontal line at midpoint.
    """
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

    v_range = max_v - min_v if max_v != min_v else 1.0
    mid_y = height / 2

    def scale_x(idx):
        return (idx / max(n - 1, 1)) * width

    def scale_y(v):
        if max_v == min_v:
            return mid_y
        return height - ((v - min_v) / v_range) * (height - 2) - 1

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
        segments[-1].append(current_segment[0])

    if not segments:
        return ""

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


def parse_amendment_tracker(improvement_dir):
    """Parse amendment-tracker.md for active and reverted amendments."""
    tracker_path = os.path.join(improvement_dir, "amendment-tracker.md")
    amendments = []
    try:
        with open(tracker_path, "r") as f:
            content = f.read()

        # Parse the Active Amendments table
        in_active = False
        for line in content.split("\n"):
            if "## Active Amendments" in line:
                in_active = True
                continue
            if in_active and line.startswith("## "):
                break
            if in_active and line.startswith("|") and not line.startswith("| ID") and not line.startswith("|----") and "(append" not in line:
                cols = [c.strip() for c in line.split("|")[1:-1]]
                if len(cols) >= 9:
                    amendments.append({
                        "id": cols[0],
                        "skill": cols[1],
                        "proposed": cols[2],
                        "implemented": cols[3],
                        "status": cols[4],
                        "target_metric": cols[5],
                        "before": cols[6],
                        "after": cols[7],
                        "verdict": cols[8],
                    })
    except FileNotFoundError:
        pass
    return amendments


def parse_latest_improvement_report(improvement_dir):
    """Parse the latest T7 improvement report for system health and proposals."""
    report = {
        "health_score": None,
        "health_trend": None,
        "skills_at_risk": None,
        "execution_quality": {},
        "reasoning_quality": {},
        "performance_quality": {},
        "risk_discipline": {},
        "proposals": [],
        "evaluations": [],
        "recommendations": [],
        "raw_markdown": None,
    }

    # Find the latest improvement report
    reports = sorted(Path(improvement_dir).glob("*-trading-improvement.md"), reverse=True)
    if not reports:
        return report

    try:
        with open(reports[0], "r") as f:
            content = f.read()
        report["raw_markdown"] = content

        # Extract system health summary
        health_match = re.search(r"\*\*Overall score:\*\*\s*(.+)", content)
        if health_match:
            report["health_score"] = health_match.group(1).strip()

        trend_match = re.search(r"\*\*Trend:\*\*\s*(.+)", content)
        if trend_match:
            report["health_trend"] = trend_match.group(1).strip()

        risk_match = re.search(r"\*\*Skills at risk:\*\*\s*(.+)", content)
        if risk_match:
            report["skills_at_risk"] = risk_match.group(1).strip()

        # Extract execution quality metrics
        fill_match = re.search(r"Fill rate:\s*(.+?)%", content)
        if fill_match:
            report["execution_quality"]["fill_rate"] = fill_match.group(1).strip() + "%"

        slip_match = re.search(r"Avg slippage:\s*(.+?)%", content)
        if slip_match:
            report["execution_quality"]["slippage"] = slip_match.group(1).strip() + "%"

        ks_match = re.search(r"Kill switch response:\s*(\w+)", content)
        if ks_match:
            report["execution_quality"]["kill_switch"] = ks_match.group(1).strip()

        # Extract amendment proposals (look for AMENDMENT PROPOSAL blocks)
        proposal_blocks = re.findall(
            r"### AMENDMENT PROPOSAL:\s*(.+?)(?=### AMENDMENT|### Amendment Evaluation|### Recommendations|$)",
            content, re.DOTALL
        )
        for block in proposal_blocks:
            proposal = {"id": "", "skill": "", "issue": "", "current": "", "proposed": "", "rationale": "", "impact": "", "risk": ""}
            id_line = block.split("\n")[0].strip()
            proposal["id"] = id_line

            skill_m = re.search(r"\*\*Skill:\*\*\s*(.+)", block)
            if skill_m:
                proposal["skill"] = skill_m.group(1).strip()
            issue_m = re.search(r"\*\*Issue:\*\*\s*(.+)", block)
            if issue_m:
                proposal["issue"] = issue_m.group(1).strip()
            root_m = re.search(r"\*\*Root Cause:\*\*\s*(.+)", block)
            if root_m:
                proposal["root_cause"] = root_m.group(1).strip()

            current_m = re.search(r"\*\*Current Instruction:\*\*\s*\n>\s*(.+?)(?=\n\*\*)", block, re.DOTALL)
            if current_m:
                proposal["current"] = current_m.group(1).strip()
            proposed_m = re.search(r"\*\*Proposed Instruction:\*\*\s*\n>\s*(.+?)(?=\n\*\*)", block, re.DOTALL)
            if proposed_m:
                proposal["proposed"] = proposed_m.group(1).strip()

            rationale_m = re.search(r"\*\*Rationale:\*\*\s*(.+)", block)
            if rationale_m:
                proposal["rationale"] = rationale_m.group(1).strip()
            impact_m = re.search(r"\*\*Expected Impact:\*\*\s*(.+)", block)
            if impact_m:
                proposal["impact"] = impact_m.group(1).strip()
            risk_m = re.search(r"\*\*Risk:\*\*\s*(.+)", block)
            if risk_m:
                proposal["risk"] = risk_m.group(1).strip()

            report["proposals"].append(proposal)

        # Extract recommendations
        rec_match = re.search(r"### Recommendations for Human Review\s*\n(.+?)(?=\n##|\n```|$)", content, re.DOTALL)
        if rec_match:
            recs = [r.strip().lstrip("- ") for r in rec_match.group(1).strip().split("\n") if r.strip() and not r.strip().startswith("#")]
            report["recommendations"] = recs

    except (FileNotFoundError, Exception):
        pass

    return report


def _build_improvements_tab(report, amendments):
    """Build the HTML for the Improvements tab."""

    # System health summary
    health_trend = report.get("health_trend", "unknown") or "unknown"
    health_class = "health-improving" if "improv" in health_trend.lower() else "health-degrading" if "degrad" in health_trend.lower() else "health-stable"
    health_score = report.get("health_score") or "—"
    skills_at_risk = report.get("skills_at_risk") or "None"

    health_html = f"""
        <div class="section">
            <h3>System Health</h3>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="label">Overall Score</div>
                    <div class="value">{esc(str(health_score))}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Trend</div>
                    <div class="value"><span class="health-indicator {health_class}"></span>{esc(health_trend)}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Skills at Risk</div>
                    <div class="value" style="font-size: 1rem;">{esc(skills_at_risk)}</div>
                </div>
            </div>
    """

    # Execution quality summary
    eq = report.get("execution_quality", {})
    if eq:
        health_html += """
            <div class="two-col" style="margin-top: 16px;">
                <div>
                    <h4 style="font-size: 0.85rem; color: #8b8fa3; margin-bottom: 8px;">Execution Quality</h4>
                    <table>"""
        for k, v in eq.items():
            health_html += f"<tr><td>{esc(k.replace('_', ' ').title())}</td><td>{esc(str(v))}</td></tr>"
        health_html += """
                    </table>
                </div>
                <div>
                    <h4 style="font-size: 0.85rem; color: #8b8fa3; margin-bottom: 8px;">Reasoning Quality</h4>
                    <table>"""
        rq = report.get("reasoning_quality", {})
        for k, v in rq.items():
            health_html += f"<tr><td>{esc(k.replace('_', ' ').title())}</td><td>{esc(str(v))}</td></tr>"
        if not rq:
            health_html += '<tr><td colspan="2" style="color: #8b8fa3;">Available after first run</td></tr>'
        health_html += """
                    </table>
                </div>
            </div>"""

    health_html += "</div>"

    # Pending proposals
    proposals = report.get("proposals", [])
    pending_amendments = [a for a in amendments if a.get("status", "").upper() in ("PROPOSED", "")]

    proposals_html = '<div class="section"><h3>Pending Amendment Proposals</h3>'

    if proposals:
        for p in proposals:
            proposals_html += f"""
            <div class="proposal-card pending">
                <div class="proposal-header">
                    <h4>{esc(p.get('id', 'New Proposal'))}</h4>
                    <span class="proposal-status status-pending">Pending Review</span>
                </div>
                <div class="proposal-detail"><strong>Skill:</strong> {esc(p.get('skill', ''))}</div>
                <div class="proposal-detail"><strong>Issue:</strong> {esc(p.get('issue', ''))}</div>
                <div class="proposal-detail"><strong>Root Cause:</strong> {esc(p.get('root_cause', ''))}</div>
                <div class="proposal-diff">
                    <div class="diff-remove">{esc(p.get('current', ''))}</div>
                    <div class="diff-add">{esc(p.get('proposed', ''))}</div>
                </div>
                <div class="proposal-detail"><strong>Rationale:</strong> {esc(p.get('rationale', ''))}</div>
                <div class="proposal-detail"><strong>Expected Impact:</strong> {esc(p.get('impact', ''))}</div>
                <div class="proposal-detail"><strong>Risk:</strong> {esc(p.get('risk', ''))}</div>
            </div>"""
        proposals_html += """
            <div class="action-hint">
                To approve or defer these proposals, run the <strong>implement-improvements</strong> command.
                The system will walk you through each amendment for your approval.
            </div>"""
    elif pending_amendments:
        for a in pending_amendments:
            proposals_html += f"""
            <div class="proposal-card pending">
                <div class="proposal-header">
                    <h4>{esc(a.get('id', ''))}</h4>
                    <span class="proposal-status status-pending">Pending</span>
                </div>
                <div class="proposal-detail"><strong>Skill:</strong> {esc(a.get('skill', ''))}</div>
                <div class="proposal-detail"><strong>Target Metric:</strong> {esc(a.get('target_metric', ''))}</div>
            </div>"""
        proposals_html += """
            <div class="action-hint">
                To approve or defer these proposals, run the <strong>implement-improvements</strong> command.
            </div>"""
    else:
        proposals_html += '<p class="empty-state">No pending proposals. The system will propose improvements after the next full run.</p>'

    proposals_html += "</div>"

    # Evaluated amendments (from tracker)
    evaluated = [a for a in amendments if a.get("verdict", "").strip() and a.get("verdict", "").strip() not in ("", "-")]
    eval_html = '<div class="section"><h3>Amendment History</h3>'

    if evaluated:
        eval_html += """
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Skill</th>
                        <th>Proposed</th>
                        <th>Implemented</th>
                        <th>Target Metric</th>
                        <th>Before</th>
                        <th>After</th>
                        <th>Verdict</th>
                    </tr>
                </thead>
                <tbody>"""
        for a in evaluated:
            verdict = a.get("verdict", "").strip().upper()
            v_class = "status-effective" if "EFFECTIVE" in verdict and "IN" not in verdict else "status-ineffective" if "INEFFECTIVE" in verdict else "status-inconclusive"
            eval_html += f"""<tr>
                <td>{esc(a.get('id', ''))}</td>
                <td>{esc(a.get('skill', ''))}</td>
                <td>{esc(a.get('proposed', ''))}</td>
                <td>{esc(a.get('implemented', ''))}</td>
                <td>{esc(a.get('target_metric', ''))}</td>
                <td>{esc(a.get('before', ''))}</td>
                <td>{esc(a.get('after', ''))}</td>
                <td><span class="proposal-status {v_class}">{esc(verdict)}</span></td>
            </tr>"""
        eval_html += "</tbody></table></div>"
    else:
        implemented = [a for a in amendments if a.get("implemented", "").strip() and a.get("implemented", "").strip() != "-"]
        if implemented:
            eval_html += """
                <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr><th>ID</th><th>Skill</th><th>Proposed</th><th>Implemented</th><th>Status</th><th>Target Metric</th></tr>
                    </thead>
                    <tbody>"""
            for a in implemented:
                status = a.get("status", "").strip().upper()
                s_class = "status-implemented" if status in ("IMPLEMENTED", "EVALUATED") else "status-pending"
                eval_html += f"""<tr>
                    <td>{esc(a.get('id', ''))}</td>
                    <td>{esc(a.get('skill', ''))}</td>
                    <td>{esc(a.get('proposed', ''))}</td>
                    <td>{esc(a.get('implemented', ''))}</td>
                    <td><span class="proposal-status {s_class}">{esc(status)}</span></td>
                    <td>{esc(a.get('target_metric', ''))}</td>
                </tr>"""
            eval_html += "</tbody></table></div>"
        else:
            eval_html += '<p class="empty-state">No amendments evaluated yet. History will appear after amendments are implemented and evaluated.</p>'

    eval_html += "</div>"

    # Recommendations for human review
    recs = report.get("recommendations", [])
    recs_html = ""
    if recs:
        recs_html = '<div class="section"><h3>Recommendations for Your Review</h3>'
        for r in recs:
            recs_html += f'<div class="recommendation-card">{esc(r)}</div>'
        recs_html += "</div>"

    return health_html + proposals_html + eval_html + recs_html


def generate_dashboard(portfolio_dir, trades_dir, performance_dir, output_dir, improvement_dir=None):
    """Generate the HTML dashboard using Jinja2 template."""

    # Load data
    perf_report = load_json(os.path.join(performance_dir, "latest-performance-report.json"))
    trade_log = load_json(os.path.join(trades_dir, "trade-log.json"))
    if not isinstance(trade_log, list):
        trade_log = []
    closed_trades = load_json(os.path.join(trades_dir, "closed-trades.json"))
    if not isinstance(closed_trades, list):
        closed_trades = []
    snapshots = load_snapshots(portfolio_dir)

    # Load improvement data
    amendments = []
    improvement_report = {
        "health_score": None, "health_trend": None, "proposals": [],
        "recommendations": [], "execution_quality": {}, "reasoning_quality": {},
        "performance_quality": {}, "risk_discipline": {}, "skills_at_risk": None,
    }
    if improvement_dir:
        amendments = parse_amendment_tracker(improvement_dir)
        improvement_report = parse_latest_improvement_report(improvement_dir)

    # Extract performance metrics
    returns = perf_report.get("returns", {})
    risk = perf_report.get("risk", {})
    win_rate_data = perf_report.get("win_rate", {})
    attribution = perf_report.get("attribution", {})

    portfolio_value_raw = _num(returns.get("ending_value"))
    total_return_raw = _num(returns.get("total_return_pct"))
    starting_value = _num(returns.get("starting_value"))
    total_pl_raw = portfolio_value_raw - starting_value if starting_value else 0
    sharpe_raw = _num(perf_report.get("sharpe_ratio"))
    max_dd_raw = _num(risk.get("max_drawdown_pct"))
    current_dd_raw = _num(risk.get("current_drawdown_pct"))
    wr_rate_raw = win_rate_data.get("win_rate")
    wr_total = _num(win_rate_data.get("total_closed"), 0)

    # Build chart data from snapshots
    chart_labels = []
    chart_values = []
    for snap in snapshots:
        ts = snap.get("timestamp", "")
        val = _num(snap.get("account", {}).get("portfolio_value"))
        date_str = ts[:10] if len(ts) >= 10 else ts
        chart_labels.append(date_str)
        chart_values.append(round(val, 2))

    if not chart_labels and returns.get("daily_returns"):
        for dr in returns["daily_returns"]:
            chart_labels.append(dr.get("date", "")[:10])
            chart_values.append(round(_num(dr.get("portfolio_value")), 2))

    # Build sparklines (last 26 data points)
    equity_curve = chart_values[-26:] if chart_values else []
    sparkline_portfolio = generate_sparkline(equity_curve, color="#60a5fa") if len(equity_curve) >= 2 else ""
    sparkline_pl = generate_sparkline(
        [v - starting_value for v in equity_curve] if starting_value and equity_curve else [],
        color="#34d399",
    )

    # Win rate sparkline from rolling 20-trade window
    winrate_history = []
    if closed_trades and len(closed_trades) >= 2:
        window = 20
        for i in range(len(closed_trades)):
            start = max(0, i - window + 1)
            chunk = closed_trades[start:i + 1]
            wins = sum(1 for c in chunk if _num(c.get("realized_pl")) > 0)
            winrate_history.append(wins / len(chunk) * 100 if chunk else 0)
    sparkline_winrate = generate_sparkline(winrate_history[-26:], color="#34d399") if len(winrate_history) >= 2 else ""

    # Load Jinja2 template
    script_dir = Path(__file__).parent
    template_path = script_dir / "trading-dashboard-template.html"
    if not template_path.exists():
        print(f"ERROR: Template not found at {template_path}", file=sys.stderr)
        print("Expected: plugins/trading-engine/scripts/trading-dashboard-template.html", file=sys.stderr)
        sys.exit(1)

    # Load assets from local assets/ directory
    assets_dir = script_dir / "assets"
    try:
        chart_js = inline_asset(assets_dir / "chart.min.js")
    except FileNotFoundError:
        print("WARNING: Chart.js not found — equity curve chart will not render", file=sys.stderr)
        chart_js = "/* Chart.js not available */"

    try:
        font_data_uri = inline_asset(assets_dir / "inter-latin.woff2")
    except FileNotFoundError:
        print("WARNING: Inter font not found — using system fonts", file=sys.stderr)
        font_data_uri = ""

    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(script_dir)),
        autoescape=select_autoescape([]),
    )
    env.filters["fmt_money"] = lambda v: fmt_money(v)
    env.filters["fmt_pct"] = lambda v: fmt_pct(v)

    template = env.get_template("trading-dashboard-template.html")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Render improvements tab HTML (reuse existing builder)
    improvements_html = _build_improvements_tab(improvement_report, amendments)

    html = template.render(
        generated=now,
        css_variables=CSS_VARIABLES,
        font_data_uri=font_data_uri,
        chart_js=chart_js,
        # Drawdown alert
        drawdown_alert=current_dd_raw >= 7.0,
        current_drawdown=f"{current_dd_raw:.1f}",
        # Metrics strip
        portfolio_value=fmt_money(portfolio_value_raw),
        total_pl=fmt_money(total_pl_raw),
        total_pl_raw=total_pl_raw,
        total_return=fmt_pct(total_return_raw),
        total_return_raw=total_return_raw,
        sharpe=f"{sharpe_raw:.2f}" if sharpe_raw else "—",
        win_rate=f"{wr_rate_raw:.1f}%" if wr_rate_raw is not None else "—",
        win_rate_raw=wr_rate_raw,
        max_drawdown=fmt_pct(-max_dd_raw) if max_dd_raw else "—",
        # Sparklines (pre-rendered SVG)
        sparkline_portfolio=sparkline_portfolio,
        sparkline_pl=sparkline_pl,
        sparkline_winrate=sparkline_winrate,
        # Chart data
        chart_labels=bool(chart_labels),
        chart_labels_json=json.dumps(chart_labels),
        chart_values_json=json.dumps(chart_values),
        # Attribution
        attr_layer=attribution.get("trade_count_by_layer", {}),
        # Win rate summary
        wr_total=int(wr_total),
        avg_win=fmt_money(win_rate_data.get("avg_win")),
        avg_loss=fmt_money(win_rate_data.get("avg_loss")),
        profit_factor=f"{win_rate_data['profit_factor']:.2f}" if win_rate_data.get("profit_factor") is not None else "—",
        # Trade tables
        trade_log=trade_log,
        closed_trades=closed_trades,
        # Improvements
        improvements_html=improvements_html,
        proposal_count=len(improvement_report.get("proposals", [])),
    )

    # Inject Chart.js inline (replace CDN reference pattern — template uses inline script)
    # The template's <script> block references Chart directly; we inject it before </head>
    if chart_js and chart_js != "/* Chart.js not available */":
        html = html.replace("</style>\n</head>",
                           f"</style>\n<script>{chart_js}</script>\n</head>")

    # Save
    os.makedirs(output_dir, exist_ok=True)
    dated_name = f"{datetime.now().strftime('%Y-%m-%d')}-trading-dashboard.html"
    dated_path = os.path.join(output_dir, dated_name)
    latest_path = os.path.join(output_dir, "latest-dashboard.html")

    with open(dated_path, "w") as f:
        f.write(html)
    with open(latest_path, "w") as f:
        f.write(html)

    print(f"Dashboard saved to {dated_path}")
    return html


def main():
    parser = argparse.ArgumentParser(description="Trading Dashboard Generator")
    parser.add_argument("--portfolio", required=True, help="Portfolio snapshots directory")
    parser.add_argument("--trades", required=True, help="Trade logs directory")
    parser.add_argument("--performance", required=True, help="Performance reports directory")
    parser.add_argument("--improvement", default=None, help="Improvement reports directory")
    parser.add_argument("--output", required=True, help="Output directory for dashboard HTML")

    args = parser.parse_args()
    generate_dashboard(args.portfolio, args.trades, args.performance, args.output, args.improvement)


if __name__ == "__main__":
    main()
