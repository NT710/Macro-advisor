#!/usr/bin/env python3
"""
Trading Dashboard Generator (Alpine Report Edition)

Produces a self-contained HTML file with multiple tabs:
  1. Overview — portfolio metrics, sparklines, attribution
  2. Positions — current holdings with layers, thesis, scaling state
  3. Trades & Reasoning — trade log, closed trades, weekly reasoning
  4. Performance — attribution, win rates, risk metrics, benchmarking
  5. External — external portfolio comparison, exposure deltas, kill switch propagation
  6. Improvements — system health, pending amendments, history
  7. Rules — risk constraints, execution discipline, rule documentation

Uses Jinja2 template at scripts/trading-dashboard-template.html.
CSS variables are inlined; Chart.js is injected before </head>.

Usage:
    python generate_dashboard.py \
        --portfolio outputs/portfolio/ \
        --trades outputs/trades/ \
        --performance outputs/performance/ \
        --improvement outputs/improvement/ \
        --external outputs/external/ \
        --config outputs/config/ \
        --rules RULES.md \
        --reasoning outputs/trades/reasoning/ \
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


def parse_reasoning_files(reasoning_dir):
    """Parse weekly reasoning markdown files from trades/reasoning directory."""
    reasoning_entries = []
    if not reasoning_dir or not os.path.exists(reasoning_dir):
        return reasoning_entries

    try:
        for f in sorted(Path(reasoning_dir).glob("*-reasoning.md"), reverse=True):
            try:
                with open(f, "r") as fh:
                    content = fh.read()

                entry = {
                    "week_date": None,
                    "regime_context": "",
                    "kill_switch_exits": [],
                    "new_positions": [],
                    "adjustments": [],
                    "skipped": [],
                    "risk_state_after": {},
                }

                # Extract week date from header — handle multiple formats
                week_match = re.search(r"#{1,2}\s*(?:Trading Engine Reasoning|Trade Reasoning)\s*(?:—|–|-)\s*(?:Week of\s*)?(.+?)(?:\n|$)", content)
                if week_match:
                    entry["week_date"] = week_match.group(1).strip()
                else:
                    # Fall back to filename date
                    fname_date = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
                    if fname_date:
                        entry["week_date"] = fname_date.group(1)

                # Extract regime context — handle ## or ### level
                regime_match = re.search(r"#{2,3}\s*Regime Context\s*\n(.+?)(?=\n#{2,3}\s|\Z)", content, re.DOTALL)
                if regime_match:
                    entry["regime_context"] = regime_match.group(1).strip()

                # Extract kill switch exits
                ks_match = re.search(r"#{2,3}\s*Kill Switch Exits\s*\n(.+?)(?=\n#{2,3}\s|\Z)", content, re.DOTALL)
                if ks_match:
                    ks_block = ks_match.group(1)
                    for line in ks_block.split("\n"):
                        if line.strip().startswith("- "):
                            line = line.strip()[2:]
                            if line.lower() != "none this week":
                                parts = line.split(":", 1)
                                if len(parts) == 2:
                                    entry["kill_switch_exits"].append({
                                        "symbol": parts[0].strip(),
                                        "reason": parts[1].strip()
                                    })

                # Extract new positions
                new_pos_match = re.search(r"#{2,3}\s*(?:New Positions|Scaling Existing Positions)\s*(?:\([^)]*\))?\s*\n(.+?)(?=\n#{2,3}\s(?!#)|\Z)", content, re.DOTALL)
                if new_pos_match:
                    new_pos_block = new_pos_match.group(1)
                    # Find each position block — handle both formats:
                    # Format 1: **SYMBOL — Name**
                    # Format 2: ### SYMBOL (Name) — Layer
                    pos_blocks = re.findall(r"\*\*([A-Z0-9]+)\s*—\s*(.+?)\*\*\n(.+?)(?=\n\*\*|\n#{2,3}\s|\Z)", new_pos_block, re.DOTALL)
                    if not pos_blocks:
                        # Try ### heading format: ### SYMBOL (Name) — Layer
                        pos_blocks = re.findall(r"###\s+([A-Z0-9,\s]+?)\s*\((.+?)\)\s*(?:—|–|-)\s*.+?\n(.+?)(?=\n###|\Z)", new_pos_block, re.DOTALL)
                    if not pos_blocks:
                        # Simplest: ### SYMBOL — anything
                        pos_blocks = re.findall(r"###\s+([A-Z0-9]+)\s*(?:—|–|-)\s*(.+?)\n(.+?)(?=\n###|\Z)", new_pos_block, re.DOTALL)
                    for symbol, name, pos_content in pos_blocks:
                        pos_dict = {
                            "symbol": symbol.strip(),
                            "name": name.strip(),
                            "target_pct": None,
                            "this_run_pct": None,
                            "reason": "",
                            "devil_advocate_base": "",
                            "devil_advocate_specific": "",
                            "bear_case_probability": None,
                            "order_type": "",
                            "expression_sizing": []
                        }

                        # Parse position details
                        target_m = re.search(r"- Target:\s*(.+?)%", pos_content)
                        if target_m:
                            pos_dict["target_pct"] = _num(target_m.group(1).strip())

                        this_m = re.search(r"- This Run:\s*(.+?)%", pos_content)
                        if this_m:
                            pos_dict["this_run_pct"] = _num(this_m.group(1).strip())

                        reason_m = re.search(r"- Reason:\s*(.+?)(?=\n-|\Z)", pos_content, re.DOTALL)
                        if reason_m:
                            pos_dict["reason"] = reason_m.group(1).strip()

                        da_base_m = re.search(r"- Devil's Advocate \(Base\):\s*(.+?)(?=\n-|\Z)", pos_content, re.DOTALL)
                        if da_base_m:
                            pos_dict["devil_advocate_base"] = da_base_m.group(1).strip()

                        da_spec_m = re.search(r"- Devil's Advocate \(Specific\):\s*(.+?)(?=\n-|\Z)", pos_content, re.DOTALL)
                        if da_spec_m:
                            pos_dict["devil_advocate_specific"] = da_spec_m.group(1).strip()

                        bear_m = re.search(r"- Bear Case Probability:\s*(.+?)%", pos_content)
                        if bear_m:
                            pos_dict["bear_case_probability"] = _num(bear_m.group(1).strip())

                        order_m = re.search(r"- Order:\s*(.+?)(?=\n|\Z)", pos_content)
                        if order_m:
                            pos_dict["order_type"] = order_m.group(1).strip()

                        # Parse expression sizing table if present
                        sizing_match = re.search(r"#### Expression Sizing\s*\n\|.+?\|.+?\|\n\|[-:\|]+\|(.+?)(?=\n###|\n\*\*|\Z)", pos_content, re.DOTALL)
                        if sizing_match:
                            sizing_block = sizing_match.group(1)
                            for sizing_line in sizing_block.split("\n"):
                                if sizing_line.strip().startswith("|"):
                                    cols = [c.strip() for c in sizing_line.split("|")[1:-1]]
                                    if len(cols) >= 5:
                                        pos_dict["expression_sizing"].append({
                                            "etf": cols[0],
                                            "conviction": cols[1],
                                            "size": _num(cols[2]),
                                            "decision": cols[3],
                                            "reasoning": cols[4]
                                        })

                        entry["new_positions"].append(pos_dict)

                # Extract adjustments
                adj_match = re.search(r"#{2,3}\s*Adjustments\s*\n(.+?)(?=\n#{2,3}\s|\Z)", content, re.DOTALL)
                if adj_match:
                    adj_block = adj_match.group(1)
                    for line in adj_block.split("\n"):
                        if line.strip().startswith("- "):
                            entry["adjustments"].append(line.strip()[2:])

                # Extract skipped
                skip_match = re.search(r"#{2,3}\s*Skipped\s*\n(.+?)(?=\n#{2,3}\s|\Z)", content, re.DOTALL)
                if skip_match:
                    skip_block = skip_match.group(1)
                    for line in skip_block.split("\n"):
                        if line.strip().startswith("- "):
                            line = line.strip()[2:]
                            if line.lower() != "none this week":
                                parts = line.split(":", 1)
                                if len(parts) == 2:
                                    entry["skipped"].append({
                                        "symbol": parts[0].strip(),
                                        "reason": parts[1].strip()
                                    })

                # Extract risk state after execution
                risk_match = re.search(r"#{2,3}\s*Risk State After\s*(?:Execution)?\s*\n(.+?)(?=\n#{2,3}\s|\Z)", content, re.DOTALL)
                if risk_match:
                    risk_block = risk_match.group(1)
                    cash_m = re.search(r"- Cash:\s*(.+?)%", risk_block)
                    if cash_m:
                        entry["risk_state_after"]["cash_pct"] = _num(cash_m.group(1).strip())

                    largest_m = re.search(r"- Largest Position:\s*(.+?)(?=\n|\Z)", risk_block)
                    if largest_m:
                        entry["risk_state_after"]["largest_position"] = largest_m.group(1).strip()

                    thesis_m = re.search(r"- Thesis Overlay:\s*(.+?)%", risk_block)
                    if thesis_m:
                        entry["risk_state_after"]["thesis_overlay_pct"] = _num(thesis_m.group(1).strip())

                    dd_m = re.search(r"- Current Drawdown:\s*(.+?)%", risk_block)
                    if dd_m:
                        entry["risk_state_after"]["drawdown_pct"] = _num(dd_m.group(1).strip())

                reasoning_entries.append(entry)

            except (json.JSONDecodeError, FileNotFoundError):
                continue

    except Exception:
        pass

    return reasoning_entries


def _parse_numbered_rules(block, extract_limit=False):
    """Parse numbered markdown rules into list of dicts with name+description (and optional limit_value)."""
    items = []
    # Split on numbered list items: "1. **Bold name.** Description..."
    parts = re.split(r'\n\d+\.\s+', '\n' + block)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Try to extract bold name: **Name** or **Name:**
        bold_match = re.match(r'\*\*(.+?)\*\*[:\.]?\s*(.*)', part, re.DOTALL)
        if bold_match:
            name = bold_match.group(1).strip().rstrip('.')
            desc = bold_match.group(2).strip()
            # Clean up multi-line descriptions
            desc = re.sub(r'\s+', ' ', desc)
        else:
            # No bold — use first sentence as name
            sentences = part.split('. ', 1)
            name = sentences[0].strip()
            desc = sentences[1].strip() if len(sentences) > 1 else ""
            desc = re.sub(r'\s+', ' ', desc)

        item = {"name": name, "description": desc}

        if extract_limit:
            # Try to extract a limit value like "15%", "10%", "25%", "5%"
            limit_match = re.search(r'(\d+(?:\.\d+)?%)', name + ' ' + desc)
            item["limit_value"] = limit_match.group(1) if limit_match else "—"
            # Also check for boolean limits
            if not limit_match:
                if 'no leverage' in (name + ' ' + desc).lower():
                    item["limit_value"] = "None (1x only)"
                elif 'no short' in (name + ' ' + desc).lower():
                    item["limit_value"] = "Long only"

        items.append(item)
    return items


def parse_rules_md(rules_path):
    """Parse RULES.md for risk constraints, execution discipline, anti-bias rules, external rules."""
    rules = {
        "risk_constraints": [],
        "execution": [],
        "anti_bias": [],
        "external": [],
    }

    if not rules_path or not os.path.exists(rules_path):
        return rules

    try:
        with open(rules_path, "r") as f:
            content = f.read()

        # Extract sections by ## headers. Handle parenthetical suffixes in header.
        def extract_section(header_pattern):
            match = re.search(header_pattern + r'\s*\n(.+?)(?=\n## |\Z)', content, re.DOTALL)
            return match.group(1).strip() if match else ""

        risk_block = extract_section(r'## Risk Constraints[^\n]*')
        exec_block = extract_section(r'## Execution Discipline[^\n]*')
        bias_block = extract_section(r'## Anti-Confirmation-Bias Rules[^\n]*')
        ext_block = extract_section(r'## External Portfolio Rules[^\n]*')

        rules["risk_constraints"] = _parse_numbered_rules(risk_block, extract_limit=True)
        rules["execution"] = _parse_numbered_rules(exec_block)
        rules["anti_bias"] = _parse_numbered_rules(bias_block)
        rules["external"] = _parse_numbered_rules(ext_block)

    except Exception:
        pass

    return rules


def _parse_md_table(text):
    """Parse a markdown table into a list of dicts keyed by header names."""
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return []
    header_line = lines[0]
    cells = [c.strip() for c in header_line.split("|")[1:-1]]
    if not cells:
        return []
    rows = []
    for line in lines[2:]:  # skip header + separator
        if not line.startswith("|"):
            break
        vals = [c.strip() for c in line.split("|")[1:-1]]
        if len(vals) == len(cells):
            rows.append(dict(zip(cells, vals)))
    return rows


def parse_external_overlay(external_dir):
    """Parse the latest external overlay markdown for exposure, thesis alignment, and gap analysis."""
    result = {
        "exposure_by_asset_class": [],
        "exposure_by_geography": [],
        "exposure_by_sector": [],
        "thesis_alignments": [],
        "gap_analysis": [],
        "non_investable_summary": "",
        "kill_switch_status": "",
        "summary": "",
    }

    if not external_dir or not os.path.exists(external_dir):
        return result

    # Find latest overlay file
    overlay_files = sorted(Path(external_dir).glob("*-external-overlay.md"), reverse=True)
    if not overlay_files:
        return result

    try:
        with open(overlay_files[0], "r") as f:
            content = f.read()

        # Parse exposure by asset class
        ac_match = re.search(r"\*\*By Asset Class:\*\*\s*\n(\|.+?\n(?:\|.+?\n)*)", content, re.DOTALL)
        if ac_match:
            result["exposure_by_asset_class"] = _parse_md_table(ac_match.group(1))

        # Parse exposure by geography
        geo_match = re.search(r"\*\*By Geography:\*\*\s*\n(\|.+?\n(?:\|.+?\n)*)", content, re.DOTALL)
        if geo_match:
            result["exposure_by_geography"] = _parse_md_table(geo_match.group(1))

        # Parse exposure by sector
        sec_match = re.search(r"\*\*By Sector[^*]*:\*\*\s*\n(\|.+?\n(?:\|.+?\n)*)", content, re.DOTALL)
        if sec_match:
            result["exposure_by_sector"] = _parse_md_table(sec_match.group(1))

        # Parse thesis alignment scan
        thesis_blocks = re.findall(
            r"\*\*Thesis:\s*(.+?)\s*\(([^)]+)\)\*\*\s*\n(.*?)(?=\n\*\*Thesis:|\n###|\Z)",
            content, re.DOTALL
        )
        for name, status, body in thesis_blocks:
            alignment = {
                "thesis_name": name.strip(),
                "status": status.strip(),
                "direction": "",
                "overlapping": "",
                "opposing": "",
                "kill_switch": "",
            }
            dir_m = re.search(r"- Direction:\s*(.+)", body)
            if dir_m:
                alignment["direction"] = dir_m.group(1).strip()
            over_m = re.search(r"- External positions with overlapping exposure:\s*(.+?)(?=\n-|\Z)", body, re.DOTALL)
            if over_m:
                alignment["overlapping"] = over_m.group(1).strip()
            opp_m = re.search(r"- External positions with opposing exposure:\s*(.+?)(?=\n-|\Z)", body, re.DOTALL)
            if opp_m:
                alignment["opposing"] = opp_m.group(1).strip()
            ks_m = re.search(r"- Kill switch status:\s*(.+)", body)
            if ks_m:
                alignment["kill_switch"] = ks_m.group(1).strip()
            result["thesis_alignments"].append(alignment)

        # Parse gap analysis
        gap_blocks = re.findall(
            r"\d+\.\s+\*\*(.+?)\*\*\s*(.+?)(?=\n\d+\.|\n\*\*Non-investable|\n###|\Z)",
            content, re.DOTALL
        )
        for title, body in gap_blocks:
            result["gap_analysis"].append({
                "title": title.strip(),
                "description": body.strip().replace("\n", " "),
            })

        # Parse non-investable summary
        ni_match = re.search(r"\*\*Non-investable exposure[^*]*:\*\*\s*\n(.+?)(?=\n###|\Z)", content, re.DOTALL)
        if ni_match:
            result["non_investable_summary"] = ni_match.group(1).strip().replace("\n", " ")

        # Kill switch propagation section
        ks_match = re.search(r"### Kill Switch Propagation\s*\n(.+?)(?=\n###|\Z)", content, re.DOTALL)
        if ks_match:
            result["kill_switch_status"] = ks_match.group(1).strip()

        # Summary
        sum_match = re.search(r"### Summary\s*\n(.+?)(?=\n---|\Z)", content, re.DOTALL)
        if sum_match:
            result["summary"] = sum_match.group(1).strip()

    except Exception:
        pass

    return result


def parse_regime_templates(regime_path):
    """Load and transform regime templates from JSON."""
    regimes = {}
    data = load_json(regime_path)

    if isinstance(data, dict):
        for regime_name, regime_data in data.items():
            if isinstance(regime_data, dict):
                weights = {}
                for asset_key, asset_info in regime_data.items():
                    if asset_key.endswith("_description") or asset_key.endswith("_total") or asset_key in ("etf", "rationale"):
                        continue
                    if isinstance(asset_info, dict):
                        weight = asset_info.get("weight", asset_info.get("pct"))
                        if weight is not None:
                            label = asset_key.replace("_", " ").title()
                            weights[label] = _num(weight)
                    else:
                        label = asset_key.replace("_", " ").title()
                        weights[label] = _num(asset_info, 0)
                if weights:
                    regimes[regime_name] = weights

    return regimes


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


def generate_dashboard(portfolio_dir, trades_dir, performance_dir, output_dir, improvement_dir=None,
                       external_dir=None, config_dir=None, rules_path=None, reasoning_dir=None):
    """Generate the HTML dashboard using Jinja2 template."""

    # Determine reasoning directory
    if reasoning_dir is None and trades_dir:
        reasoning_dir = os.path.join(trades_dir, "reasoning")

    # Load data
    perf_report = load_json(os.path.join(performance_dir, "latest-performance-report.json"))
    trade_log = load_json(os.path.join(trades_dir, "trade-log.json"))
    if not isinstance(trade_log, list):
        trade_log = []
    closed_trades = load_json(os.path.join(trades_dir, "closed-trades.json"))
    if not isinstance(closed_trades, list):
        closed_trades = []
    snapshots = load_snapshots(portfolio_dir)

    # Load latest snapshot
    latest_snapshot = load_json(os.path.join(portfolio_dir, "latest-snapshot.json"))

    # Load latest performance snapshot (has unrealized P&L per position from Alpaca)
    latest_perf_snapshot = load_json(os.path.join(portfolio_dir, "latest-performance.json"))
    # Build a lookup: symbol -> unrealized_pl, unrealized_plpc, change_today
    _perf_pnl_map = {}
    if isinstance(latest_perf_snapshot, dict):
        for pos in latest_perf_snapshot.get("positions", []):
            sym = pos.get("symbol", "")
            if sym:
                _perf_pnl_map[sym] = {
                    "unrealized_pl": _num(pos.get("unrealized_pl")),
                    "unrealized_plpc": _num(pos.get("unrealized_plpc")),
                    "change_today": _num(pos.get("change_today")),
                }

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

    # Load reasoning files — try dedicated reasoning dir first, fall back to trades dir
    weekly_reasoning = parse_reasoning_files(reasoning_dir)
    if not weekly_reasoning:
        weekly_reasoning = parse_reasoning_files(trades_dir)

    # Load rules — auto-discover RULES.md if not explicitly provided
    rules_data = {}
    risk_limits_json = {}
    regime_templates = {}
    if not rules_path:
        # Auto-discover: script is at scripts/generate_dashboard.py,
        # RULES.md is at skills/trading-engine/references/RULES.md
        # (both under the same plugin root)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        plugin_root = os.path.dirname(script_dir)  # up from scripts/ to plugin root
        candidates = [
            os.path.join(plugin_root, "skills", "trading-engine", "references", "RULES.md"),
            os.path.join(plugin_root, "references", "RULES.md"),
            os.path.join(plugin_root, "RULES.md"),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                rules_path = candidate
                break
    if rules_path:
        rules_data = parse_rules_md(rules_path)
    if not config_dir:
        # Auto-discover config directory relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        plugin_root = os.path.dirname(script_dir)
        candidate_config = os.path.join(plugin_root, "config")
        if os.path.isdir(candidate_config):
            config_dir = candidate_config
    if config_dir:
        risk_limits_path = os.path.join(config_dir, "risk-limits.json")
        risk_limits_json = load_json(risk_limits_path)
        regime_path = os.path.join(config_dir, "regime-templates.json")
        regime_templates = parse_regime_templates(regime_path)

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

    # Extract latest snapshot metrics
    account = latest_snapshot.get("account", {})
    cash_pct = 0
    thesis_overlay_pct = 0
    largest_position = None
    largest_position_name = ""
    largest_position_pct = 0
    positions = []

    if account:
        portfolio_value = _num(account.get("portfolio_value"))
        cash = _num(account.get("cash"))
        if portfolio_value and cash:
            cash_pct = (cash / portfolio_value) * 100

    # Build lookup from trade log: symbol → {name, layer, thesis} from most recent filled trade
    _trade_meta = {}
    for t in reversed(trade_log):
        sym = t.get("symbol", "")
        if sym and sym not in _trade_meta:
            _trade_meta[sym] = {
                "name": t.get("name", ""),
                "layer": t.get("layer", ""),
                "thesis": t.get("thesis", ""),
            }

    # Top-level allocation percentages from snapshot
    alloc_map = latest_snapshot.get("allocations_pct", {})

    # Process positions
    if isinstance(latest_snapshot.get("positions"), list):
        for pos in latest_snapshot.get("positions", []):
            symbol = pos.get("symbol", "")
            # Name: prefer snapshot, fall back to trade log lookup
            name = pos.get("name", "") or _trade_meta.get(symbol, {}).get("name", "")
            qty = _num(pos.get("qty"))
            avg_entry = _num(pos.get("avg_entry_price"))
            current_price = _num(pos.get("current_price"))
            market_value = _num(pos.get("market_value"))
            # Allocation: prefer per-position field, fall back to top-level allocations_pct
            alloc_pct = _num(pos.get("allocation_pct")) or _num(alloc_map.get(symbol))

            # Layer/thesis: prefer snapshot fields, fall back to trade log
            layer = pos.get("layer", "") or _trade_meta.get(symbol, {}).get("layer", "")
            thesis = pos.get("thesis", "") or _trade_meta.get(symbol, {}).get("thesis", "")

            # Compute unrealized return for this position
            pos_return_pct = 0
            if avg_entry and avg_entry > 0 and current_price:
                pos_return_pct = ((current_price - avg_entry) / avg_entry) * 100

            # Enrich with unrealized P&L from performance snapshot
            pnl_data = _perf_pnl_map.get(symbol, {})
            unrealized_pl = pnl_data.get("unrealized_pl", 0) or 0
            unrealized_plpc = pnl_data.get("unrealized_plpc", 0) or 0
            change_today = pnl_data.get("change_today", 0) or 0

            positions.append({
                "symbol": symbol,
                "name": name,
                "qty": qty,
                "avg_entry": fmt_money(avg_entry),
                "current_price": fmt_money(current_price),
                "market_value": fmt_money(market_value),
                "allocation_pct": f"{alloc_pct:.1f}%" if alloc_pct else "0%",
                "allocation_pct_raw": alloc_pct,
                "return_pct": pos_return_pct,
                "unrealized_pl": unrealized_pl,
                "unrealized_plpc": unrealized_plpc * 100 if abs(unrealized_plpc) < 10 else unrealized_plpc,
                "change_today": change_today,
                "layer": layer,
                "thesis": thesis,
                "scaling_state": pos.get("scaling_state", "")
            })

            # Track thesis overlay (positions with a non-empty thesis)
            if thesis:
                thesis_overlay_pct += alloc_pct

            if largest_position is None or alloc_pct > largest_position_pct:
                largest_position = symbol
                largest_position_name = name
                largest_position_pct = alloc_pct

    # Build positions P&L list sorted by unrealized_pl descending
    positions_pnl = sorted(
        [p for p in positions if p.get("unrealized_pl") is not None],
        key=lambda p: p.get("unrealized_pl", 0),
        reverse=True
    )

    # Compute portfolio-level P&L totals for the footer
    pnl_total_dollar = sum(p.get("unrealized_pl", 0) or 0 for p in positions_pnl)
    pnl_total_today = sum(p.get("change_today", 0) or 0 for p in positions_pnl)
    # Weighted-average % return: weight each position's % by its allocation_pct_raw
    _wt_num = sum((p.get("unrealized_plpc", 0) or 0) * (p.get("allocation_pct_raw", 0) or 0) for p in positions_pnl)
    _wt_den = sum(p.get("allocation_pct_raw", 0) or 0 for p in positions_pnl)
    pnl_total_pct = (_wt_num / _wt_den) if _wt_den else 0

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

    # Parse attribution from performance report or fall back to trade_count_by_layer
    attr_layer = {}
    if "by_layer" in attribution:
        for layer_name, layer_data in attribution.get("by_layer", {}).items():
            attr_layer[layer_name] = {
                "layer": layer_name,
                "positions": layer_data.get("positions", 0),
                "allocation_pct": layer_data.get("allocation_pct", 0),
                "week_return": layer_data.get("week_return", 0),
                "contribution": layer_data.get("contribution", 0),
            }
    else:
        # Fall back to trade_count_by_layer — compute allocation, return, contribution from positions
        _layer_alloc = {}
        _layer_return_weighted = {}  # sum of (alloc * return) per layer
        _layer_positions_count = {}  # count of current held positions per layer
        for p in positions:
            pl = p.get("layer", "")
            if pl:
                alloc_raw = p.get("allocation_pct_raw", 0) or 0
                ret_raw = p.get("return_pct", 0) or 0
                _layer_alloc[pl] = _layer_alloc.get(pl, 0) + alloc_raw
                _layer_return_weighted[pl] = _layer_return_weighted.get(pl, 0) + (alloc_raw * ret_raw / 100)
                _layer_positions_count[pl] = _layer_positions_count.get(pl, 0) + 1

        for layer_name, count in attribution.get("trade_count_by_layer", {}).items():
            layer_alloc = _layer_alloc.get(layer_name, 0)
            # Weighted average return for the layer
            layer_return = 0
            if layer_alloc > 0:
                layer_return = (_layer_return_weighted.get(layer_name, 0) / layer_alloc) * 100
            # Contribution = allocation × return (contribution to total portfolio return)
            layer_contribution = _layer_return_weighted.get(layer_name, 0)
            attr_layer[layer_name] = {
                "layer": layer_name,
                "positions": _layer_positions_count.get(layer_name, count),
                "allocation_pct": layer_alloc,
                "week_return": round(layer_return, 2),
                "contribution": round(layer_contribution, 2),
            }

    # Load external portfolio data
    ext_has_data = False
    ext_positions = []
    ext_total_value = 0
    ext_base_currency = "USD"
    ext_position_count = 0
    ext_stale_count = 0
    ext_value_history = []
    ext_exposure = {}
    paper_exposure = {}
    ext_thesis_overlap = []
    ext_allocation_deltas = []
    ext_non_investable_deltas = []
    ext_non_investable_summary = ""
    ext_kill_switch_propagation = []
    ext_approaching_kill_switches = []
    ext_staleness_warnings = []
    ext_overlay = {"exposure_by_asset_class": [], "exposure_by_geography": [], "exposure_by_sector": [],
                   "thesis_alignments": [], "gap_analysis": [], "non_investable_summary": "",
                   "kill_switch_status": "", "summary": ""}

    if external_dir and os.path.exists(external_dir):
        ext_has_data = True
        # Load latest prices — try latest-prices.json first, fall back to *-external-snapshot.json
        latest_prices = load_json(os.path.join(external_dir, "latest-prices.json"))
        if not latest_prices or "positions" not in latest_prices:
            # Fall back to the most recent external snapshot
            _ext_snaps = sorted(Path(external_dir).glob("*-external-snapshot.json"), reverse=True)
            if _ext_snaps:
                latest_prices = load_json(str(_ext_snaps[0]))
        if latest_prices and "positions" in latest_prices:
            ext_positions = latest_prices["positions"]
            ext_position_count = len(ext_positions)
            ext_total_value = _num(latest_prices.get("total_value_base") or latest_prices.get("total_value"))
            ext_base_currency = latest_prices.get("base_currency", "USD")
            ext_stale_count = sum(1 for p in ext_positions if p.get("price_stale") or p.get("manual_valuation"))

        # Load value history
        value_history_data = load_json(os.path.join(external_dir, "external-value-history.json"))
        if value_history_data:
            ext_value_history = value_history_data

        # Load exposure
        ext_exposure_data = load_json(os.path.join(external_dir, "latest-exposure.json"))
        if ext_exposure_data:
            ext_exposure = ext_exposure_data

        # Load thesis overlap
        thesis_overlap = load_json(os.path.join(external_dir, "latest-thesis-overlap.json"))
        if thesis_overlap and "overlaps" in thesis_overlap:
            ext_thesis_overlap = thesis_overlap["overlaps"]

        # Load kill switches
        kill_switches = load_json(os.path.join(external_dir, "latest-kill-switches.json"))
        if kill_switches:
            if "propagations" in kill_switches:
                ext_kill_switch_propagation = kill_switches["propagations"]
            if "approaching" in kill_switches:
                ext_approaching_kill_switches = kill_switches["approaching"]

        # Parse external overlay markdown for rich content
        ext_overlay = parse_external_overlay(external_dir)

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
    env.filters["tojson"] = json.dumps

    template = env.get_template("trading-dashboard-template.html")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Read version from plugin.json
    plugin_version = ""
    plugin_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.claude-plugin', 'plugin.json')
    try:
        with open(plugin_json_path, "r") as f:
            plugin_data = json.load(f)
        plugin_version = plugin_data.get("version", "")
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Sort trade log by date descending (latest first)
    trade_log.sort(key=lambda t: t.get("date", ""), reverse=True)

    # Render improvements tab HTML (reuse existing builder)
    improvements_html = _build_improvements_tab(improvement_report, amendments)

    html = template.render(
        generated=now,
        version=plugin_version,
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
        attr_layer=attr_layer,
        # Win rate summary
        wr_total=int(wr_total),
        avg_win=fmt_money(win_rate_data.get("avg_win")),
        avg_loss=fmt_money(win_rate_data.get("avg_loss")),
        profit_factor=f"{win_rate_data['profit_factor']:.2f}" if win_rate_data.get("profit_factor") is not None else "—",
        # Positions
        positions=positions,
        positions_pnl=positions_pnl,
        pnl_total_dollar=pnl_total_dollar,
        pnl_total_pct=pnl_total_pct,
        pnl_total_today=pnl_total_today,
        position_count=len(positions),
        cash_pct=f"{cash_pct:.1f}%",
        thesis_overlay_pct=f"{thesis_overlay_pct:.1f}%",
        largest_position_name=f"{largest_position} ({largest_position_name})" if largest_position and largest_position_name else (largest_position or "—"),
        largest_position_pct=f"{largest_position_pct:.1f}%",
        # Trade tables
        trade_log=trade_log,
        closed_trades=closed_trades,
        # Weekly reasoning
        weekly_reasoning=weekly_reasoning,
        # Performance metrics
        perf_attribution=list(attr_layer.values()),
        perf_thesis=[],
        perf_winrate_by_category={},
        perf_winrate_by_mechanism={},
        perf_da_accuracy={},
        perf_risk_metrics={},
        perf_benchmark={},
        # External portfolio
        ext_has_data=ext_has_data,
        ext_positions=ext_positions,
        ext_total_value=fmt_money(ext_total_value),
        ext_base_currency=ext_base_currency,
        ext_position_count=ext_position_count,
        ext_stale_count=ext_stale_count,
        ext_value_history=ext_value_history,
        ext_exposure=ext_exposure,
        paper_exposure=paper_exposure,
        ext_thesis_overlap=ext_thesis_overlap,
        ext_allocation_deltas=ext_allocation_deltas,
        ext_non_investable_deltas=ext_non_investable_deltas,
        ext_non_investable_summary=ext_non_investable_summary,
        ext_kill_switch_propagation=ext_kill_switch_propagation,
        ext_approaching_kill_switches=ext_approaching_kill_switches,
        ext_staleness_warnings=ext_staleness_warnings,
        ext_overlay=ext_overlay,
        # Rules
        rules_risk_constraints=rules_data.get("risk_constraints", []),
        rules_execution=rules_data.get("execution", ""),
        rules_anti_bias=rules_data.get("anti_bias", ""),
        rules_external=rules_data.get("external", ""),
        risk_limits_json=risk_limits_json,
        regime_templates=regime_templates,
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
    parser.add_argument("--external", default=None, help="External portfolio data directory")
    parser.add_argument("--config", default=None, help="Config files directory (risk-limits.json, regime-templates.json)")
    parser.add_argument("--rules", default=None, help="Path to RULES.md file")
    parser.add_argument("--reasoning", default=None, help="Weekly reasoning markdown files directory")
    parser.add_argument("--output", required=True, help="Output directory for dashboard HTML")

    args = parser.parse_args()
    generate_dashboard(
        args.portfolio,
        args.trades,
        args.performance,
        args.output,
        improvement_dir=args.improvement,
        external_dir=args.external,
        config_dir=args.config,
        rules_path=args.rules,
        reasoning_dir=args.reasoning,
    )


if __name__ == "__main__":
    main()
