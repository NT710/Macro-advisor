#!/usr/bin/env python3
"""
Trading Dashboard Generator

Produces a self-contained HTML file with three tabs:
  1. P&L — portfolio value chart, return metrics, attribution, drawdown, risk state
  2. Trades — trade log table, closed trades, devil's advocate log
  3. Improvements — system health, pending amendment proposals, evaluated amendments

Reads from:
  - outputs/portfolio/ (snapshots)
  - outputs/trades/ (trade-log.json, closed-trades.json, reasoning logs)
  - outputs/performance/ (latest-performance-report.json)
  - outputs/improvement/ (amendment-tracker.md, latest improvement report)

Usage:
    python generate_dashboard.py \
        --portfolio outputs/portfolio/ \
        --trades outputs/trades/ \
        --performance outputs/performance/ \
        --improvement outputs/improvement/ \
        --output outputs/dashboard/
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
import html as html_lib


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
    """Generate the HTML dashboard."""

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
    improvement_report = {"health_score": None, "health_trend": None, "proposals": [], "recommendations": [], "execution_quality": {}, "reasoning_quality": {}, "performance_quality": {}, "risk_discipline": {}, "skills_at_risk": None}
    if improvement_dir:
        amendments = parse_amendment_tracker(improvement_dir)
        improvement_report = parse_latest_improvement_report(improvement_dir)

    # Extract performance metrics
    returns = perf_report.get("returns", {})
    risk = perf_report.get("risk", {})
    win_rate = perf_report.get("win_rate", {})
    attribution = perf_report.get("attribution", {})
    sharpe = perf_report.get("sharpe_ratio", 0)

    portfolio_value = returns.get("ending_value", 0) or 0
    starting_value = returns.get("starting_value", 0) or 0
    total_return = returns.get("total_return_pct", 0) or 0
    hwm = risk.get("high_water_mark", 0) or 0
    max_dd = risk.get("max_drawdown_pct", 0) or 0
    current_dd = risk.get("current_drawdown_pct", 0) or 0

    # Build chart data from snapshots
    chart_labels = []
    chart_values = []
    for snap in snapshots:
        ts = snap.get("timestamp", "")
        val = snap.get("account", {}).get("portfolio_value", 0)
        # Extract date portion
        date_str = ts[:10] if len(ts) >= 10 else ts
        chart_labels.append(date_str)
        chart_values.append(round(val, 2))

    # If no snapshots, use performance report data
    if not chart_labels and returns.get("daily_returns"):
        for dr in returns["daily_returns"]:
            chart_labels.append(dr.get("date", "")[:10])
            chart_values.append(round(dr.get("portfolio_value", 0), 2))

    # Build trade rows
    trade_rows_html = ""
    for t in trade_log:
        trade_rows_html += f"""<tr>
            <td>{esc(t.get('date', ''))[:10]}</td>
            <td>{esc(t.get('run_type', ''))}</td>
            <td><strong>{esc(t.get('symbol', ''))}</strong></td>
            <td class="{'buy-cell' if t.get('side') == 'buy' else 'sell-cell'}">{esc(t.get('side', '').upper())}</td>
            <td>{t.get('qty', '')}</td>
            <td>{fmt_money(t.get('fill_price'))}</td>
            <td>{esc(t.get('order_type', ''))}</td>
            <td>{esc(t.get('layer', ''))}</td>
            <td>{esc(t.get('thesis', '') or '—')}</td>
            <td>{esc(t.get('status', ''))}</td>
            <td class="reason-cell">{esc(t.get('reason', '')[:80])}</td>
        </tr>"""

    if not trade_rows_html:
        trade_rows_html = '<tr><td colspan="11" class="empty-state">No trades recorded yet. Run the trading engine to see trades here.</td></tr>'

    # Build closed trade rows
    closed_rows_html = ""
    for ct in closed_trades:
        pl = ct.get("realized_pl", 0) or 0
        pl_pct = ct.get("realized_pl_pct", 0) or 0
        pl_class = "positive" if pl > 0 else "negative" if pl < 0 else ""
        bear_hit = ct.get("bear_case_realized")
        bear_icon = "&#10004;" if bear_hit else "&#10008;" if bear_hit is False else "—"

        closed_rows_html += f"""<tr>
            <td><strong>{esc(ct.get('symbol', ''))}</strong></td>
            <td>{esc(ct.get('entry_date', ''))}</td>
            <td>{esc(ct.get('exit_date', ''))}</td>
            <td>{ct.get('holding_days', '—')}</td>
            <td>{fmt_money(ct.get('entry_price'))}</td>
            <td>{fmt_money(ct.get('exit_price'))}</td>
            <td class="{pl_class}">{fmt_money(pl)}</td>
            <td class="{pl_class}">{fmt_pct(pl_pct)}</td>
            <td>{esc(ct.get('layer', ''))}</td>
            <td>{esc(ct.get('close_reason', ''))}</td>
            <td>{bear_icon}</td>
        </tr>"""

    if not closed_rows_html:
        closed_rows_html = '<tr><td colspan="11" class="empty-state">No closed trades yet.</td></tr>'

    # Attribution summary
    layer_counts = attribution.get("trade_count_by_layer", {})
    mechanism_counts = attribution.get("trade_count_by_mechanism", {})

    attr_layer_html = ""
    for layer, count in layer_counts.items():
        attr_layer_html += f"<tr><td>{esc(layer)}</td><td>{count}</td></tr>"
    if not attr_layer_html:
        attr_layer_html = '<tr><td colspan="2">No data yet</td></tr>'

    attr_mechanism_html = ""
    for mech, count in mechanism_counts.items():
        attr_mechanism_html += f"<tr><td>{esc(mech)}</td><td>{count}</td></tr>"
    if not attr_mechanism_html:
        attr_mechanism_html = '<tr><td colspan="2">No data yet</td></tr>'

    # Win rate summary
    wr_total = win_rate.get("total_closed", 0)
    wr_wins = win_rate.get("wins", 0)
    wr_losses = win_rate.get("losses", 0)
    wr_rate = win_rate.get("win_rate")
    wr_avg_win = win_rate.get("avg_win")
    wr_avg_loss = win_rate.get("avg_loss")
    wr_pf = win_rate.get("profit_factor")

    # Drawdown alert
    drawdown_alert = ""
    if current_dd and current_dd >= 7.0:
        drawdown_alert = f"""
        <div class="alert alert-danger">
            &#9888; DRAWDOWN ALERT: Portfolio is {current_dd:.1f}% below high water mark.
            Circuit breaker triggers at 10%.
        </div>"""

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    dashboard_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trading Engine Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
    :root {{
        --bg: #0f1117;
        --surface: #1a1d27;
        --surface2: #252836;
        --border: #2e3246;
        --text: #e4e6f0;
        --text-dim: #8b8fa3;
        --accent: #6c8cff;
        --accent-hover: #5a7aee;
        --positive: #34d399;
        --negative: #f87171;
        --warning: #fbbf24;
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
        background: var(--bg);
        color: var(--text);
        line-height: 1.6;
    }}

    .container {{
        max-width: 1280px;
        margin: 0 auto;
        padding: 24px;
    }}

    header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--border);
    }}

    header h1 {{
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text);
    }}

    header .timestamp {{
        font-size: 0.85rem;
        color: var(--text-dim);
    }}

    .tabs {{
        display: flex;
        gap: 4px;
        margin-bottom: 24px;
        background: var(--surface);
        border-radius: 8px;
        padding: 4px;
        width: fit-content;
    }}

    .tab {{
        padding: 10px 24px;
        border: none;
        background: transparent;
        color: var(--text-dim);
        cursor: pointer;
        border-radius: 6px;
        font-size: 0.9rem;
        font-weight: 500;
        transition: all 0.2s;
    }}

    .tab:hover {{
        color: var(--text);
        background: var(--surface2);
    }}

    .tab.active {{
        background: var(--accent);
        color: white;
    }}

    .tab-content {{
        display: none;
    }}

    .tab-content.active {{
        display: block;
    }}

    .metric-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }}

    .metric-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 16px;
    }}

    .metric-card .label {{
        font-size: 0.75rem;
        color: var(--text-dim);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }}

    .metric-card .value {{
        font-size: 1.5rem;
        font-weight: 600;
    }}

    .metric-card .value.positive {{ color: var(--positive); }}
    .metric-card .value.negative {{ color: var(--negative); }}

    .chart-container {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 24px;
    }}

    .chart-container h3 {{
        font-size: 0.9rem;
        color: var(--text-dim);
        margin-bottom: 12px;
        font-weight: 500;
    }}

    .section {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 24px;
    }}

    .section h3 {{
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 16px;
        color: var(--text);
    }}

    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
    }}

    th {{
        text-align: left;
        padding: 8px 12px;
        color: var(--text-dim);
        font-weight: 500;
        border-bottom: 1px solid var(--border);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    td {{
        padding: 8px 12px;
        border-bottom: 1px solid var(--border);
        color: var(--text);
    }}

    tr:hover {{
        background: var(--surface2);
    }}

    .buy-cell {{ color: var(--positive); font-weight: 600; }}
    .sell-cell {{ color: var(--negative); font-weight: 600; }}
    .positive {{ color: var(--positive); }}
    .negative {{ color: var(--negative); }}
    .reason-cell {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .empty-state {{ text-align: center; color: var(--text-dim); padding: 32px !important; }}

    .two-col {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
    }}

    .alert {{
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 24px;
        font-weight: 500;
    }}

    .alert-danger {{
        background: rgba(248, 113, 113, 0.15);
        border: 1px solid var(--negative);
        color: var(--negative);
    }}

    .badge {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: var(--warning);
        color: var(--bg);
        font-size: 0.7rem;
        font-weight: 700;
        border-radius: 10px;
        min-width: 18px;
        height: 18px;
        padding: 0 5px;
        margin-left: 6px;
    }}

    .proposal-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
    }}

    .proposal-card.pending {{
        border-left: 3px solid var(--warning);
    }}

    .proposal-card.implemented {{
        border-left: 3px solid var(--positive);
    }}

    .proposal-card.reverted {{
        border-left: 3px solid var(--negative);
    }}

    .proposal-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;
    }}

    .proposal-header h4 {{
        font-size: 0.95rem;
        font-weight: 600;
    }}

    .proposal-status {{
        font-size: 0.75rem;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    .status-pending {{
        background: rgba(251, 191, 36, 0.15);
        color: var(--warning);
    }}

    .status-implemented {{
        background: rgba(52, 211, 153, 0.15);
        color: var(--positive);
    }}

    .status-effective {{
        background: rgba(52, 211, 153, 0.15);
        color: var(--positive);
    }}

    .status-ineffective {{
        background: rgba(248, 113, 113, 0.15);
        color: var(--negative);
    }}

    .status-inconclusive {{
        background: rgba(139, 143, 163, 0.15);
        color: var(--text-dim);
    }}

    .proposal-detail {{
        font-size: 0.85rem;
        color: var(--text-dim);
        margin-bottom: 6px;
    }}

    .proposal-detail strong {{
        color: var(--text);
    }}

    .proposal-diff {{
        margin: 12px 0;
        padding: 12px;
        background: var(--bg);
        border-radius: 6px;
        font-size: 0.8rem;
        font-family: 'SF Mono', 'Fira Code', monospace;
    }}

    .diff-remove {{
        color: var(--negative);
        text-decoration: line-through;
        opacity: 0.7;
    }}

    .diff-add {{
        color: var(--positive);
    }}

    .recommendation-card {{
        background: var(--surface2);
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 8px;
        font-size: 0.85rem;
        border-left: 3px solid var(--accent);
    }}

    .health-indicator {{
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }}

    .health-improving {{ background: var(--positive); }}
    .health-stable {{ background: var(--accent); }}
    .health-degrading {{ background: var(--negative); }}

    .action-hint {{
        margin-top: 16px;
        padding: 12px 16px;
        background: rgba(108, 140, 255, 0.1);
        border: 1px solid rgba(108, 140, 255, 0.3);
        border-radius: 8px;
        font-size: 0.85rem;
        color: var(--accent);
    }}

    @media (max-width: 768px) {{
        .two-col {{ grid-template-columns: 1fr; }}
        .metric-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1>Trading Engine Dashboard</h1>
        <span class="timestamp">Generated: {now}</span>
    </header>

    {drawdown_alert}

    <div class="tabs">
        <button class="tab active" onclick="switchTab('pnl')">P&L</button>
        <button class="tab" onclick="switchTab('trades')">Trades</button>
        <button class="tab" onclick="switchTab('improvements')">Improvements{' <span class="badge">' + str(len(improvement_report["proposals"])) + '</span>' if improvement_report["proposals"] else ''}</button>
    </div>

    <!-- P&L TAB -->
    <div id="tab-pnl" class="tab-content active">
        <div class="metric-grid">
            <div class="metric-card">
                <div class="label">Portfolio Value</div>
                <div class="value">{fmt_money(portfolio_value)}</div>
            </div>
            <div class="metric-card">
                <div class="label">Total Return</div>
                <div class="value {'positive' if total_return > 0 else 'negative' if total_return < 0 else ''}">{fmt_pct(total_return)}</div>
            </div>
            <div class="metric-card">
                <div class="label">Sharpe Ratio</div>
                <div class="value">{sharpe:.2f}</div>
            </div>
            <div class="metric-card">
                <div class="label">High Water Mark</div>
                <div class="value">{fmt_money(hwm)}</div>
            </div>
            <div class="metric-card">
                <div class="label">Max Drawdown</div>
                <div class="value negative">{fmt_pct(-max_dd) if max_dd else '—'}</div>
            </div>
            <div class="metric-card">
                <div class="label">Current Drawdown</div>
                <div class="value {'negative' if current_dd > 3 else ''}">{fmt_pct(-current_dd) if current_dd else '—'}</div>
            </div>
        </div>

        <div class="chart-container">
            <h3>Portfolio Value Over Time</h3>
            <canvas id="valueChart" height="80"></canvas>
        </div>

        <div class="two-col">
            <div class="section">
                <h3>Attribution by Layer</h3>
                <table>
                    <thead><tr><th>Layer</th><th>Trades</th></tr></thead>
                    <tbody>{attr_layer_html}</tbody>
                </table>
            </div>
            <div class="section">
                <h3>Attribution by Mechanism</h3>
                <table>
                    <thead><tr><th>Mechanism</th><th>Trades</th></tr></thead>
                    <tbody>{attr_mechanism_html}</tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <h3>Win Rate Summary</h3>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="label">Closed Trades</div>
                    <div class="value">{wr_total}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Win Rate</div>
                    <div class="value {'positive' if wr_rate and wr_rate > 50 else ''}">{f'{wr_rate:.1f}%' if wr_rate is not None else '—'}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Avg Win</div>
                    <div class="value positive">{fmt_money(wr_avg_win)}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Avg Loss</div>
                    <div class="value negative">{fmt_money(wr_avg_loss)}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Profit Factor</div>
                    <div class="value">{f'{wr_pf:.2f}' if wr_pf is not None else '—'}</div>
                </div>
            </div>
        </div>
    </div>

    <!-- TRADES TAB -->
    <div id="tab-trades" class="tab-content">
        <div class="section">
            <h3>Trade Log</h3>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Run</th>
                        <th>Symbol</th>
                        <th>Side</th>
                        <th>Qty</th>
                        <th>Price</th>
                        <th>Type</th>
                        <th>Layer</th>
                        <th>Thesis</th>
                        <th>Status</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody>
                    {trade_rows_html}
                </tbody>
            </table>
            </div>
        </div>

        <div class="section">
            <h3>Closed Trades</h3>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Days</th>
                        <th>Entry Price</th>
                        <th>Exit Price</th>
                        <th>P&L</th>
                        <th>P&L %</th>
                        <th>Layer</th>
                        <th>Close Reason</th>
                        <th>Bear Case Hit</th>
                    </tr>
                </thead>
                <tbody>
                    {closed_rows_html}
                </tbody>
            </table>
            </div>
        </div>
    </div>

    <!-- IMPROVEMENTS TAB -->
    <div id="tab-improvements" class="tab-content">
        {_build_improvements_tab(improvement_report, amendments)}
    </div>
</div>

<script>
function switchTab(tab) {{
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');
    event.target.classList.add('active');
}}

// Portfolio value chart
const ctx = document.getElementById('valueChart');
if (ctx) {{
    const labels = {json.dumps(chart_labels)};
    const values = {json.dumps(chart_values)};

    if (labels.length > 0) {{
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Portfolio Value',
                    data: values,
                    borderColor: '#6c8cff',
                    backgroundColor: 'rgba(108, 140, 255, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: labels.length > 20 ? 0 : 3,
                    borderWidth: 2,
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return '$' + context.parsed.y.toLocaleString(undefined, {{minimumFractionDigits: 2}});
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#8b8fa3', maxTicksLimit: 10 }},
                        grid: {{ color: 'rgba(46, 50, 70, 0.5)' }}
                    }},
                    y: {{
                        ticks: {{
                            color: '#8b8fa3',
                            callback: function(value) {{ return '$' + value.toLocaleString(); }}
                        }},
                        grid: {{ color: 'rgba(46, 50, 70, 0.5)' }}
                    }}
                }}
            }}
        }});
    }} else {{
        ctx.parentElement.innerHTML += '<p style="color: #8b8fa3; text-align: center; padding: 40px 0;">No snapshot data available yet. Portfolio value chart will appear after the first trading run.</p>';
    }}
}}
</script>
</body>
</html>"""

    # Save
    os.makedirs(output_dir, exist_ok=True)
    dated_name = f"{datetime.now().strftime('%Y-%m-%d')}-trading-dashboard.html"
    dated_path = os.path.join(output_dir, dated_name)
    latest_path = os.path.join(output_dir, "latest-dashboard.html")

    with open(dated_path, "w") as f:
        f.write(dashboard_html)
    with open(latest_path, "w") as f:
        f.write(dashboard_html)

    print(f"Dashboard saved to {dated_path}")
    return dated_path


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
