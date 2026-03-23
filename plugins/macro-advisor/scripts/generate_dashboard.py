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
import base64
import json
import os
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
    # Strip YAML meta blocks (---\nmeta:\n...\n--- or front matter at top of file)
    # These are internal quality metadata and should never render in the dashboard.
    md_text = re.sub(r'(?m)^---\s*\nmeta:.*?^---\s*$', '', md_text, flags=re.DOTALL | re.MULTILINE)
    # Also strip YAML front matter at very start of file (e.g. skill descriptions)
    if md_text.lstrip().startswith('---'):
        md_text = re.sub(r'\A\s*---.*?^---\s*$', '', md_text, count=1, flags=re.DOTALL | re.MULTILINE)
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
        # Raw HTML pass-through (lines starting with < are already HTML)
        elif line.strip().startswith("<"):
            html_lines.append(line)
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


def _status_html(status):
    """Color-code a thesis assumption status string."""
    if not status:
        return ''
    s_upper = status.upper()
    if s_upper == 'INTACT':
        return f'<span style="color: var(--green);">{status}</span>'
    elif s_upper == 'UNDER PRESSURE':
        return f'<span style="color: var(--amber);">{status}</span>'
    elif s_upper == 'BROKEN':
        return f'<span style="color: var(--red);">{status}</span>'
    return status


def _extract_status(text):
    """Extract and remove status marker (INTACT/UNDER PRESSURE/BROKEN) from text.
    Returns (cleaned_text, status_string)."""
    for s in ['UNDER PRESSURE', 'INTACT', 'BROKEN']:
        if s in text.upper():
            cleaned = re.sub(r'\s*—?\s*' + re.escape(s), '', text, flags=re.IGNORECASE).strip()
            return cleaned, s
    return text, ''


def _is_section_boundary(line_text):
    """Check if a line marks the start of a new thesis section."""
    l = line_text.strip()
    if l.startswith('## ') or l.startswith('# '):
        return True
    if l.startswith('**') and ':' in l and l.endswith('**'):
        return True
    if l.startswith('**') and ':**' in l:
        return True
    return False


def _peek_past_blanks(lines, start):
    """From start, skip blank lines and return index of next non-empty line."""
    idx = start
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    return idx


def _emit_h2(text):
    """Emit a section header as ## for consistent amber styling.
    Extracts just the section name, stripping bold markers and content after the colon."""
    # Strip existing markdown header markers
    clean = re.sub(r'^#+\s*', '', text.strip())
    # Match **Section Name:** (possibly followed by content) — extract just the name
    bold_match = re.match(r'\*\*(.+?):\*\*', clean)
    if bold_match:
        clean = bold_match.group(1).strip()
    else:
        # Match **Section Name** (no colon)
        bold_match2 = re.match(r'\*\*(.+?)\*\*', clean)
        if bold_match2:
            clean = bold_match2.group(1).strip()
    clean = clean.rstrip(':').strip()
    return f'## {clean}'


def format_thesis_html(md_text):
    """Section-aware thesis rendering for both tactical and structural theses.

    Converts thesis markdown into optimised display format:
    - Section headers → h2 (renders in amber/uppercase Bloomberg style via CSS)
    - Assumptions → table (#, Assumption, Status) — Status column hidden when all empty
    - What We Have To Believe → table (#, Assumption, Testable By, Status)
    - Structural Foundation → table (Constraint, Quantified, Source)
    - Quantified Causal Chain → table (#, Link, Quantified)
    - ETF Expression → table (Order, ETF, Size, Rationale)
    - Kill Switch → highlighted card
    - Conviction → keep result line, collapse scoring rubric
    - Mechanism / Claim / Consensus / Contrarian Stress-Test → prose with h2 headers
    - Plain English Summary → prose with h2 header
    """
    lines = md_text.split('\n')
    output_lines = []
    i = 0

    def _match_section(lower_line, *keywords):
        """Check if a lowered line starts with any of the keyword patterns as bold or h2."""
        for kw in keywords:
            if lower_line.startswith(f'**{kw}') or lower_line.startswith(f'## {kw}'):
                return True
        return False

    while i < len(lines):
        line = lines[i]
        lower = line.lower().strip()

        # --- Strip thesis title lines (### THESIS CANDIDATE / ### STRUCTURAL THESIS CANDIDATE) ---
        # These are redundant since the detail header shows the title
        if lower.startswith('### thesis candidate') or lower.startswith('### structural thesis candidate'):
            i += 1
            continue

        # --- Strip metadata lines already shown in header/index or source viewer ---
        # Status, Generated, Updated, Source, Classification, Provenance, Research Brief
        if re.match(r'^\*\*(?:Status|Generated|Updated|Classification|Provenance|Source|Research Brief):\*\*', line.strip()):
            i += 1
            continue

        # --- Assumptions: numbered list → table ---
        if _match_section(lower, 'assumptions:' , 'assumptions'):
            output_lines.append(_emit_h2(line))
            output_lines.append('')
            i += 1
            # Collect all numbered items first to check if any have status
            items = []
            while i < len(lines):
                l = lines[i].strip()
                if not l:
                    peek = _peek_past_blanks(lines, i + 1)
                    if peek < len(lines) and _is_section_boundary(lines[peek]):
                        break
                    i += 1
                    continue
                if _is_section_boundary(l):
                    break
                m = re.match(r'^\d+\.\s*(.+)', l)
                if m:
                    text, status = _extract_status(m.group(1))
                    items.append((text, status))
                    i += 1
                else:
                    break
            # Decide whether to show status column
            has_any_status = any(s for _, s in items)
            if has_any_status:
                output_lines.append('| # | Assumption | Status |')
                output_lines.append('|---|-----------|--------|')
                for n, (text, status) in enumerate(items, 1):
                    output_lines.append(f'| {n} | {text} | {_status_html(status)} |')
            else:
                output_lines.append('| # | Assumption |')
                output_lines.append('|---|-----------|')
                for n, (text, _) in enumerate(items, 1):
                    output_lines.append(f'| {n} | {text} |')
            output_lines.append('')
            continue

        # --- What We Have To Believe: numbered list → table ---
        if _match_section(lower, 'what we have to believe'):
            output_lines.append(_emit_h2(line))
            output_lines.append('')
            i += 1
            items = []
            while i < len(lines):
                l = lines[i].strip()
                if not l:
                    peek = _peek_past_blanks(lines, i + 1)
                    if peek < len(lines) and _is_section_boundary(lines[peek]):
                        break
                    i += 1
                    continue
                if _is_section_boundary(l):
                    break
                m = re.match(r'^\d+\.\s*(.+)', l)
                if m:
                    text = m.group(1)
                    testable = ''
                    # Split on "Testable by:" or "— Testable by:"
                    tb_match = re.split(r'\s*—?\s*[Tt]estable\s+by:\s*', text, maxsplit=1)
                    if len(tb_match) == 2:
                        text = tb_match[0].strip()
                        testable = tb_match[1].strip()
                    # Extract status from either field
                    text, status = _extract_status(text)
                    if not status:
                        testable, status = _extract_status(testable)
                    items.append((text, testable, status))
                    i += 1
                else:
                    break
            has_any_status = any(s for _, _, s in items)
            if has_any_status:
                output_lines.append('| # | Assumption | Testable By | Status |')
                output_lines.append('|---|-----------|-------------|--------|')
                for n, (text, testable, status) in enumerate(items, 1):
                    output_lines.append(f'| {n} | {text} | {testable} | {_status_html(status)} |')
            else:
                output_lines.append('| # | Assumption | Testable By |')
                output_lines.append('|---|-----------|-------------|')
                for n, (text, testable, _) in enumerate(items, 1):
                    output_lines.append(f'| {n} | {text} | {testable} |')
            output_lines.append('')
            continue

        # --- Structural Foundation: prose + bullet list → table ---
        if _match_section(lower, 'structural foundation'):
            output_lines.append(_emit_h2(line))
            output_lines.append('')
            i += 1
            # Collect description prose (before bullets)
            desc_lines = []
            while i < len(lines):
                l = lines[i].strip()
                if not l:
                    i += 1
                    continue
                if l.startswith('- '):
                    break
                if _is_section_boundary(l):
                    break
                desc_lines.append(lines[i])
                i += 1
            if desc_lines:
                output_lines.extend(desc_lines)
                output_lines.append('')
            # Convert bullets to table
            if i < len(lines) and lines[i].strip().startswith('- '):
                output_lines.append('| Binding Constraint | Quantified | Source |')
                output_lines.append('|-------------------|-----------|--------|')
                while i < len(lines) and lines[i].strip().startswith('- '):
                    text = lines[i].strip()[2:].strip()
                    parts = [p.strip() for p in text.split(' — ')]
                    if len(parts) >= 3:
                        output_lines.append(f'| {parts[0]} | {parts[1]} | {parts[2]} |')
                    elif len(parts) == 2:
                        output_lines.append(f'| {parts[0]} | {parts[1]} | |')
                    else:
                        output_lines.append(f'| {text} | | |')
                    i += 1
                output_lines.append('')
            continue

        # --- Quantified Causal Chain: numbered list → table ---
        if _match_section(lower, 'quantified causal chain'):
            output_lines.append(_emit_h2(line))
            output_lines.append('')
            i += 1
            # Skip description prose before the numbered list
            desc_lines = []
            while i < len(lines):
                l = lines[i].strip()
                if not l:
                    i += 1
                    continue
                if re.match(r'^\d+\.', l):
                    break
                if _is_section_boundary(l):
                    break
                desc_lines.append(lines[i])
                i += 1
            if desc_lines:
                output_lines.extend(desc_lines)
                output_lines.append('')
            # Collect numbered items
            items = []
            while i < len(lines):
                l = lines[i].strip()
                if not l:
                    peek = _peek_past_blanks(lines, i + 1)
                    if peek < len(lines) and _is_section_boundary(lines[peek]):
                        break
                    i += 1
                    continue
                if _is_section_boundary(l):
                    break
                m = re.match(r'^\d+\.\s*(.+)', l)
                if m:
                    text = m.group(1)
                    # Try to split: "Link text — quantified detail"
                    parts = text.split(' — ', 1)
                    if len(parts) == 2:
                        items.append((parts[0].strip(), parts[1].strip()))
                    else:
                        items.append((text.strip(), ''))
                    i += 1
                else:
                    break
            if items:
                output_lines.append('| # | Link | Quantified |')
                output_lines.append('|---|------|-----------|')
                for n, (link, quant) in enumerate(items, 1):
                    output_lines.append(f'| {n} | {link} | {quant} |')
                output_lines.append('')
            continue

        # --- ETF Expression: bullet list with order labels → table ---
        # Matches: **ETF Expression:**, ## ETF Expression, *Expression:*
        if (_match_section(lower, 'etf expression') or lower == '*expression:*'
                or lower.startswith('## etf expression')):
            output_lines.append(_emit_h2('ETF Expression'))
            output_lines.append('')
            i += 1
            # Collect prose lines before the bullet list
            # (structural format has *Thesis conviction:* and *Expression:* before bullets)
            prose_lines = []
            while i < len(lines):
                l = lines[i].strip()
                if not l:
                    i += 1
                    continue
                if l.startswith('- '):
                    break
                if _is_section_boundary(l):
                    break
                # Keep conviction and expression label lines as prose
                prose_lines.append(lines[i])
                i += 1
            if prose_lines:
                output_lines.extend(prose_lines)
                output_lines.append('')
            # Convert order bullets to table
            if i < len(lines) and lines[i].strip().startswith('- '):
                output_lines.append('| Order | ETF | Size | Rationale |')
                output_lines.append('|-------|-----|------|-----------|')
                while i < len(lines) and lines[i].strip().startswith('- '):
                    text = lines[i].strip()[2:].strip()
                    # Parse: **First-order** (desc): ETF — size — rationale
                    order_match = re.match(r'\*\*(.+?)\*\*\s*(?:\([^)]*\))?\s*:?\s*(.*)', text)
                    if order_match:
                        order = order_match.group(1).strip()
                        rest = order_match.group(2).strip()
                        parts = [p.strip() for p in rest.split(' — ')]
                        etf = parts[0] if len(parts) >= 1 else ''
                        # Reduce/Avoid has format: ETF — reason (2 parts, no size)
                        is_reduce = 'reduce' in order.lower() or 'avoid' in order.lower()
                        if is_reduce and len(parts) == 2:
                            size = '—'
                            rationale = parts[1]
                        elif len(parts) >= 3:
                            size = parts[1]
                            rationale = parts[2]
                        elif len(parts) == 2:
                            size = parts[1]
                            rationale = ''
                        else:
                            size = ''
                            rationale = ''
                        output_lines.append(f'| {order} | {etf} | {size} | {rationale} |')
                    else:
                        output_lines.append(f'| — | {text} | | |')
                    i += 1
                output_lines.append('')
            continue

        # --- Kill Switch: render as highlighted card ---
        if _match_section(lower, 'kill switch'):
            text = line.strip()
            kill_text = re.sub(r'^#+\s*', '', text)
            kill_text = re.sub(r'\*\*[Kk]ill [Ss]witch:\*\*\s*', '', kill_text)
            kill_text = re.sub(r'^[Kk]ill [Ss]witch:?\s*', '', kill_text).strip()
            i += 1
            while i < len(lines) and lines[i].strip() and not _is_section_boundary(lines[i]):
                kill_text += ' ' + lines[i].strip()
                i += 1
            output_lines.append(f'<div class="kill-switch-card">')
            output_lines.append(f'<strong>KILL SWITCH:</strong> {apply_inline(kill_text)}')
            output_lines.append(f'</div>')
            output_lines.append('')
            continue

        # --- Conviction: keep result, collapse scoring rubric ---
        if (lower.startswith('**conviction:**') and not lower.startswith('**conviction &')):
            output_lines.append(_emit_h2('Conviction'))
            output_lines.append('')
            # Extract just the conviction level from this line
            conv_match = re.search(r'\*\*[Cc]onviction:\*\*\s*(.+)', line.strip())
            if conv_match:
                output_lines.append(conv_match.group(1).strip())
            output_lines.append('')
            i += 1
            # Skip the scoring rubric — everything until the next MAJOR thesis section
            # Rubric lines include **Primary dimensions:**, **Veto gate:**, **Scoring:**
            # which look like section boundaries but are actually rubric content
            major_sections = [
                'etf expression', 'trigger to add', 'kill switch', 'time horizon',
                'consensus view', 'entry timing', 'monitoring cadence',
                'analyst cross-references', 'mechanism', 'claim',
                'plain english summary', 'structural foundation',
                'quantified causal chain', 'what we have to believe',
                'contrarian stress-test', 'assumptions',
            ]
            while i < len(lines):
                l = lines[i].strip().lower()
                # Stop at ## headers
                if l.startswith('## '):
                    break
                # Stop at known major bold sections
                is_major = False
                for ms in major_sections:
                    if l.startswith(f'**{ms}'):
                        is_major = True
                        break
                if is_major:
                    break
                # Stop at structural conviction/expression markers
                if l.startswith('*thesis conviction:*') or l.startswith('*expression:*'):
                    break
                i += 1
            continue

        # --- Prose sections: emit h2 header, content stays as prose ---
        # Mechanism, Claim, Plain English Summary, Consensus view,
        # Contrarian Stress-Test, Trigger to add, Time horizon, Entry timing,
        # Monitoring cadence
        prose_sections = [
            'mechanism:', 'mechanism',
            'claim:', 'claim',
            'plain english summary:', 'plain english summary',
            'consensus view:', 'consensus view',
            'contrarian stress-test:', 'contrarian stress-test',
            'trigger to add:', 'trigger to add',
            'time horizon:', 'time horizon',
            'entry timing:', 'entry timing',
            'monitoring cadence:', 'monitoring cadence',
            'analyst cross-references', 'analyst cross-references:',
        ]
        matched_prose = False
        for kw in prose_sections:
            if _match_section(lower, kw):
                output_lines.append(_emit_h2(line))
                output_lines.append('')
                i += 1
                # For inline bold format like **Claim:** the rest of the line is the content
                inline_match = re.match(r'\*\*[^*]+:\*\*\s*(.+)', line.strip())
                if inline_match:
                    output_lines.append(inline_match.group(1).strip())
                    output_lines.append('')
                matched_prose = True
                break
        if matched_prose:
            continue

        # --- Default: pass through ---
        output_lines.append(line)
        i += 1

    return '\n'.join(output_lines)


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

        # Current regime — only match "Current Quadrant" line or the first "Regime:" line
        if regime == "Unknown" and ("current quadrant" in lower or ("regime:" in lower and "forecast" not in lower and "most likely" not in lower)):
            if "goldilocks" in lower:
                regime = "Goldilocks"
            elif "overheating" in lower:
                regime = "Overheating"
            elif "stagflation" in lower:
                regime = "Stagflation"
            elif "disinflation" in lower or "slowdown" in lower:
                regime = "Disinflationary Slowdown"

        if "direction:" in lower and "forecast" not in lower and direction == "Stable":
            # Extract the raw text after "Direction:"
            match = re.search(r'\*{0,2}[Dd]irection:?\*{0,2}\s*(.+)', line)
            if match:
                direction = match.group(1).strip()

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
            # Track which forecast horizon we're currently under
            if "6 month" in lower or "6-month" in lower:
                current_forecast = "6m"
            elif "12 month" in lower or "12-month" in lower:
                current_forecast = "12m"

            # Match "most likely regime:" on its own line
            if "most likely" in lower and "regime" in lower:
                target = current_forecast if 'current_forecast' in dir() else None
                if target == "6m" and forecast_6m == "Unknown":
                    if "goldilocks" in lower:
                        forecast_6m = "Goldilocks"
                    elif "overheating" in lower:
                        forecast_6m = "Overheating"
                    elif "stagflation" in lower:
                        forecast_6m = "Stagflation"
                    elif "disinflation" in lower or "slowdown" in lower:
                        forecast_6m = "Disinflationary Slowdown"
                elif target == "12m" and forecast_12m == "Unknown":
                    if "goldilocks" in lower:
                        forecast_12m = "Goldilocks"
                    elif "overheating" in lower:
                        forecast_12m = "Overheating"
                    elif "stagflation" in lower:
                        forecast_12m = "Stagflation"
                    elif "disinflation" in lower or "slowdown" in lower:
                        forecast_12m = "Disinflationary Slowdown"

    # --- Extract text sections for the regime tab ---
    weeks_held = ""
    regime_narrative = ""
    forecast_section_md = ""
    what_changed_md = ""

    # Extract weeks held
    for line in lines:
        lower = line.lower()
        if "weeks in current regime" in lower:
            match = re.search(r'\*{0,2}Weeks in current regime:?\*{0,2}\s*(.+)', line, re.IGNORECASE)
            if match:
                weeks_held = match.group(1).strip()
            break

    # Extract regime narrative (paragraph after Regime Assessment header, after the metadata lines)
    # Matches both ## and ### headers
    in_regime_section = False
    metadata_lines_seen = 0
    narrative_lines = []
    for line in lines:
        lower = line.lower().strip()
        if lower.startswith("#") and "regime assessment" in lower:
            in_regime_section = True
            continue
        if in_regime_section:
            # Skip metadata lines (bold key-value pairs)
            if lower.startswith("**") and ":" in lower:
                metadata_lines_seen += 1
                continue
            # Skip blank lines between metadata and narrative
            if metadata_lines_seen > 0 and not lower:
                continue
            # Stop at next section header or horizontal rule
            if lower.startswith("#") or lower == "---":
                break
            if lower:
                narrative_lines.append(line)
                metadata_lines_seen = 99  # prevent re-entering skip mode

    regime_narrative = " ".join(narrative_lines).strip()

    # Extract full Regime Forecast section as markdown
    in_forecast_text = False
    forecast_lines = []
    for line in lines:
        lower = line.lower().strip()
        if lower.startswith("#") and "regime forecast" in lower:
            in_forecast_text = True
            continue
        if in_forecast_text:
            if (lower.startswith("## ") and not lower.startswith("### ")) or lower == "---":
                break
            forecast_lines.append(line)
    forecast_section_md = "\n".join(forecast_lines).strip()

    # Extract What Changed This Week section
    in_what_changed = False
    what_changed_lines = []
    for line in lines:
        lower = line.lower().strip()
        if lower.startswith("#") and "what changed this week" in lower:
            in_what_changed = True
            continue
        if in_what_changed:
            if (lower.startswith("## ") and not lower.startswith("### ")) or lower == "---":
                break
            what_changed_lines.append(line)
    what_changed_md = "\n".join(what_changed_lines).strip()

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
        "weeks_held": weeks_held,
        "regime_narrative": regime_narrative,
        "forecast_section_md": forecast_section_md,
        "what_changed_md": what_changed_md,
    }


def _inline_chartjs():
    """Read chart.min.js from the local assets folder and return its contents.

    Falls back to an empty string with a console warning if the file is missing.
    """
    assets_dir = Path(__file__).resolve().parent / "assets"
    chart_path = assets_dir / "chart.min.js"
    if chart_path.exists():
        return chart_path.read_text(encoding="utf-8")
    return 'console.warn("chart.min.js not found — charts will not render");'


def _normalize_header(h):
    """Normalize a markdown table header to a simple key.
    'Why (plain language)' -> 'why', 'Sector' -> 'sector', etc."""
    return h.lower().split('(')[0].strip()


def _parse_table_section(lines):
    """Parse a markdown table from a list of lines. Returns list of dicts."""
    rows = []
    header_cols = []
    for line in lines:
        if '|' not in line:
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if all(set(c) <= set('- :') for c in cells):
            continue  # separator row
        if not header_cols:
            header_cols = [_normalize_header(c) for c in cells]
            continue
        row = dict(zip(header_cols, cells))
        if any(row.values()):
            rows.append(row)
    return rows


def extract_cross_asset_tables(briefing_text):
    """Extract cross-asset table AND sector view table from briefing markdown.

    Returns (cross_assets, sector_view) — both are lists of dicts.
    """
    cross_asset_lines = []
    sector_lines = []
    in_cross_asset = False
    in_sector = False

    for line in briefing_text.split('\n'):
        lower = line.lower().strip()

        # Detect cross-asset section start
        if lower.startswith('## cross-asset view'):
            in_cross_asset = True
            in_sector = False
            continue

        # Detect sector view sub-section
        if in_cross_asset and ('sector view' in lower) and lower.startswith('###'):
            in_cross_asset = False
            in_sector = True
            continue

        # Stop at next ## section (but not ### which we handle above)
        if (in_cross_asset or in_sector) and line.startswith('## ') and not line.startswith('### '):
            break

        if in_cross_asset:
            cross_asset_lines.append(line)
        elif in_sector:
            sector_lines.append(line)

    return _parse_table_section(cross_asset_lines), _parse_table_section(sector_lines)


def parse_improvement_report(improvement_text):
    """Extract structured data from the self-improvement loop markdown.

    Returns dict with:
      health_score: str (e.g. "0.84")
      health_trend: str (e.g. "stable", "improving", "degrading")
      skills_at_risk: str
      observation_rows: list of dicts (skill table)
      amendments: list of dicts (id, skill/proposed, description, priority/target, status, verdict)
      gaps: list of dicts (skill, gap, weeks, severity)
    """
    result = {
        "health_score": "",
        "health_trend": "",
        "skills_at_risk": "",
        "observation_rows": [],
        "amendments": [],
        "gaps": [],
    }
    if not improvement_text:
        return result

    # Health score: "Overall system score: 0.84" or "system_health_score: 0.84"
    m = re.search(r'(?:Overall system score|system_health_score)[:\s]*([0-9.]+)', improvement_text)
    if m:
        result["health_score"] = m.group(1)

    # Trend — handle markdown bold: "**Trend:** Stable" or "system_health_trend: stable"
    m = re.search(r'\*{0,2}Trend\*{0,2}:\*{0,2}\s+(\w+)', improvement_text, re.IGNORECASE)
    if not m:
        m = re.search(r'system_health_trend[:\s]+(\w+)', improvement_text, re.IGNORECASE)
    if m:
        result["health_trend"] = m.group(1).strip().lower()

    # Skills at risk
    m = re.search(r'Skills at risk:\*?\*?\s*(.+)', improvement_text)
    if m:
        result["skills_at_risk"] = m.group(1).strip()

    # Parse observation summary table
    lines = improvement_text.split('\n')
    in_obs = False
    obs_lines = []
    for line in lines:
        lower = line.lower().strip()
        if 'observation summary' in lower and lower.startswith('#'):
            in_obs = True
            continue
        if in_obs:
            if line.strip().startswith('#') or line.strip() == '---':
                break
            if '|' in line:
                obs_lines.append(line)
    if obs_lines:
        result["observation_rows"] = _parse_table_section(obs_lines)

    # Parse amendment evaluation table
    in_amend = False
    amend_lines = []
    for line in lines:
        lower = line.lower().strip()
        if ('amendment evaluation' in lower or 'amendment tracker' in lower) and lower.startswith('#'):
            in_amend = True
            continue
        if in_amend:
            if line.strip().startswith('#') or line.strip() == '---':
                break
            if '|' in line:
                amend_lines.append(line)
    if amend_lines:
        result["amendments"] = _parse_table_section(amend_lines)

    # Parse data gaps table
    in_gaps = False
    gap_lines = []
    for line in lines:
        lower = line.lower().strip()
        if 'data gaps' in lower and lower.startswith('#'):
            in_gaps = True
            continue
        if in_gaps:
            if line.strip().startswith('#') or line.strip() == '---':
                break
            if '|' in line:
                gap_lines.append(line)
    if gap_lines:
        result["gaps"] = _parse_table_section(gap_lines)

    return result


def generate_html(week, briefing, theses, improvement, synthesis, snapshot_data,
                   all_weeks=None, all_weeks_data=None, regime_history=None,
                   skill_files=None, methodology=None, output_dir=None,
                   closed_theses=None):
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

    # Load structured dashboard data from JSON (primary) or markdown parsing (legacy)
    thesis_recommendations = {}
    thesis_convictions_from_briefing = {}
    cross_assets_from_json = []
    sector_view_from_json = []

    # Try briefing-data.json first, then legacy thesis-status.json
    briefing_data_path = output_dir / "briefings" / f"{week}-briefing-data.json" if output_dir else None
    legacy_path = output_dir / "briefings" / f"{week}-thesis-status.json" if output_dir else None
    json_path = None
    if briefing_data_path and briefing_data_path.exists():
        json_path = briefing_data_path
    elif legacy_path and legacy_path.exists():
        json_path = legacy_path

    if json_path:
        try:
            raw = json.loads(json_path.read_text(encoding="utf-8"))
            # briefing-data.json nests under "theses"; legacy is flat
            thesis_data = raw.get("theses", raw) if isinstance(raw, dict) else {}
            for slug, data in thesis_data.items():
                if isinstance(data, dict):
                    if data.get("recommendation"):
                        thesis_recommendations[slug] = data["recommendation"].lower()
                    if data.get("conviction"):
                        thesis_convictions_from_briefing[slug] = data["conviction"]
            cross_assets_from_json = raw.get("cross_asset", [])
            sector_view_from_json = raw.get("sector_view", [])
        except (json.JSONDecodeError, AttributeError):
            pass  # fall through to markdown fallback

    # Fallback: parse briefing markdown tables for weeks that pre-date the JSON output
    if not thesis_recommendations and briefing:
        in_table = False
        header_cols = []
        for line in briefing.split('\n'):
            lower = line.lower()
            if ('draft candidates' in lower or 'awaiting your decision' in lower
                    or 'active positions' in lower or 'active theses' in lower):
                in_table = True
                header_cols = []
                continue
            if in_table and '|' in line:
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if all(set(c) <= set('- :') for c in cells):
                    continue
                if not header_cols:
                    header_cols = [c.lower() for c in cells]
                    continue
                row = dict(zip(header_cols, cells))
                thesis_name = re.sub(r'[^a-z0-9\-]', '', row.get('thesis', '').strip().lower().replace(' ', '-'))
                rec_raw = (row.get('recommendation', '') or row.get('what to do', '')).strip()
                rec = rec_raw.split('.')[0].split(',')[0].split(' ')[0].strip().lower()
                if thesis_name and rec:
                    thesis_recommendations[thesis_name] = rec
                conv = row.get('conviction', '').strip()
                if thesis_name and conv:
                    thesis_convictions_from_briefing[thesis_name] = conv
            elif in_table and line.strip() and '|' not in line and not line.strip().startswith('|'):
                in_table = False
                header_cols = []

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

    # Count active, draft, tactical, structural for Overview KPI
    active_count = sum(1 for _, _, s in deduped if s == "ACTIVE")
    draft_count = sum(1 for _, _, s in deduped if s == "DRAFT")

    tactical_count = 0
    structural_count = 0
    for _, content, _ in deduped:
        content_lower = content.lower()
        is_structural = (
            "classification:** structural" in content_lower
            or "structural thesis candidate" in content_lower
            or "structural foundation" in content_lower
        )
        if is_structural:
            structural_count += 1
        else:
            tactical_count += 1

    # Load thesis chart specs from presentations directory
    thesis_chart_specs = {}
    thesis_presentations = {}
    if output_dir is not None:
        presentations_dir = output_dir / "theses" / "presentations"
    else:
        presentations_dir = None
    if presentations_dir is not None and presentations_dir.exists():
        for f in presentations_dir.glob("*-charts.json"):
            try:
                thesis_chart_specs[f.stem.replace("-charts", "")] = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

    # Load thesis presentation reports (Skill 12 output) for enriched rendering
    if presentations_dir is not None and presentations_dir.exists():
        for f in presentations_dir.glob("*-report.md"):
            thesis_presentations[f.stem.replace("-report", "")] = f.read_text(encoding="utf-8")

    # Helper: generate conviction bar HTML
    def _conviction_bar_html(conviction_str):
        """Generate 4-block conviction bar. High=3 filled, Medium=2, Low=1, empty=0."""
        level = conviction_str.strip().lower() if conviction_str else ""
        if level in ("high", "h"):
            filled, css_class = 3, ""
        elif level in ("medium", "med", "m"):
            filled, css_class = 2, " medium"
        elif level in ("low", "l"):
            filled, css_class = 1, " low"
        else:
            filled, css_class = 0, ""
        blocks = ''.join(
            f'<div class="block{" filled" if j < filled else ""}"></div>'
            for j in range(4)
        )
        return f'<div class="conviction-bar{css_class}" title="Conviction: {conviction_str or "Unknown"}">{blocks}</div>'

    # Build thesis index table + detail panels
    thesis_table_rows = ""
    thesis_contents = ""
    thesis_book_rows = ""  # for Overview tab compact table

    for i, (name, content, status) in enumerate(deduped):
        clean_name = name.replace("ACTIVE-", "").replace("DRAFT-", "").replace(".md", "").replace("-", " ").title()

        # Detect thesis type: structural vs tactical
        content_lower = content.lower()
        is_structural = (
            "classification:** structural" in content_lower
            or "structural thesis candidate" in content_lower
            or "structural foundation" in content_lower
        )
        thesis_type = "STRUCTURAL" if is_structural else "TACTICAL"

        # Extract metadata from content
        thesis_key = name.replace("ACTIVE-", "").replace("DRAFT-", "").replace(".md", "")

        conviction = ""
        # Match structural format: *Thesis conviction:* High
        conviction_match = re.search(r'\*Thesis conviction:\*\s*(\w+)', content)
        if conviction_match:
            conviction = conviction_match.group(1).strip()
        # Also match tactical format: **Conviction:** High
        if not conviction:
            conviction_match = re.search(r'\*\*Conviction:\*\*\s*(\w+)', content)
            if conviction_match:
                conviction = conviction_match.group(1).strip()
        # Also match h2 format: ## Conviction\nHigh (on next line)
        if not conviction:
            conviction_match = re.search(r'##\s*Conviction\s*\n+\s*(High|Medium|Low)', content, re.IGNORECASE)
            if conviction_match:
                conviction = conviction_match.group(1).strip().capitalize()
        # Also match YAML meta block: confidence: high/medium/low
        if not conviction:
            conviction_match = re.search(r'confidence:\s*(\w+)', content)
            if conviction_match:
                conviction = conviction_match.group(1).strip().capitalize()
        # Fallback: look up conviction from briefing table
        if not conviction:
            thesis_lookup_conv = thesis_key.lower()
            for ckey, cval in thesis_convictions_from_briefing.items():
                if ckey in thesis_lookup_conv or thesis_lookup_conv in ckey:
                    conviction = cval
                    break

        provenance = ""
        prov_match = re.search(r'\*\*Provenance:\*\*\s*(.+)', content)
        if prov_match:
            provenance = prov_match.group(1).strip()

        generated = ""
        gen_match = re.search(r'\*\*Generated:\*\*\s*(.+)', content)
        if gen_match:
            generated = gen_match.group(1).strip()

        updated = ""
        upd_match = re.search(r'\*\*Updated:\*\*\s*(.+)', content)
        if upd_match:
            updated = upd_match.group(1).strip()

        # Extract time horizon (first line after ## Time Horizon)
        horizon = ""
        horizon_match = re.search(r'## Time Horizon\s*\n+(.+)', content)
        if horizon_match:
            # Grab just the short duration label (e.g. "1-3 months", "2-5 years")
            h_match = re.match(r'([\d]+-[\d]+\s*(?:months?|years?|weeks?))', horizon_match.group(1).strip(), re.IGNORECASE)
            if h_match:
                horizon = h_match.group(1)
            else:
                # Fallback: take first phrase before period or parenthesis
                horizon = horizon_match.group(1).strip().split('.')[0].split('(')[0].strip()

        # Look up recommendation from briefing
        recommendation = ""
        thesis_lookup = thesis_key.lower()
        for rkey, rval in thesis_recommendations.items():
            if rkey in thesis_lookup or thesis_lookup in rkey:
                recommendation = rval.capitalize()
                break

        # Build table row — compact 5-column format with badge pills + conviction bars
        selected_class = "selected" if i == 0 else ""
        status_lower = status.lower()
        type_lower = thesis_type.lower()
        status_badge = "A" if status == "ACTIVE" else "D"
        badge_status_cls = "badge-active" if status == "ACTIVE" else "badge-draft"
        type_badge = "S" if is_structural else "T"
        badge_type_cls = "badge-structural" if is_structural else "badge-tactical"
        conv_bar = _conviction_bar_html(conviction)
        horizon_short = (horizon or "—").replace("months", "mo").replace("month", "mo").replace("years", "yr").replace("year", "yr").replace("weeks", "wk").replace("week", "wk")

        thesis_table_rows += (
            f'<tr class="thesis-row {selected_class}" onclick="showThesis({i})" data-idx="{i}" data-status="{status_lower}" data-type="{type_lower}"'
            f' data-clean-name="{clean_name}" data-thesis-status="{status}" data-thesis-type="{thesis_type}"'
            f' data-conviction="{conviction or ""}" data-horizon="{horizon_short}"'
            f' data-generated="{generated or ""}" data-updated="{updated or ""}">'
            f'<td class="thesis-name-cell">{clean_name}</td>'
            f'<td><span class="badge {badge_status_cls}" title="{status}">{status_badge}</span></td>'
            f'<td><span class="badge {badge_type_cls}" title="{thesis_type}">{type_badge}</span></td>'
            f'<td>{conv_bar}</td>'
            f'<td class="thesis-horizon">{horizon_short}</td>'
            f'</tr>\n'
        )

        # Build thesis book row for Overview (compact — same format)
        rec_class = f"rec-{recommendation.lower()}" if recommendation else ""
        thesis_book_rows += (
            f'<tr>'
            f'<td class="thesis-name-cell">{clean_name}</td>'
            f'<td><span class="badge {badge_status_cls}" title="{status}">{status_badge}</span></td>'
            f'<td><span class="badge {badge_type_cls}" title="{thesis_type}">{type_badge}</span></td>'
            f'<td>{conv_bar}</td>'
            f'<td><span class="thesis-rec {rec_class}">{recommendation or "—"}</span></td>'
            f'</tr>\n'
        )

        # Build detail content
        render_content = content

        # Inject conviction into the markdown before rendering
        if conviction:
            render_content = re.sub(
                r'(## Plain English Summary)',
                f'**Conviction:** {conviction}\n\n\\1',
                render_content, count=1
            )

        if is_structural:
            # Strip Source and Research Brief (shown in source viewer at bottom)
            render_content = re.sub(
                r'^\*\*(?:Source|Research Brief):\*\*.*\n?',
                '', render_content, flags=re.MULTILINE
            )

        # Build chart HTML if chart spec exists
        chart_html = ""
        chart_spec = thesis_chart_specs.get(thesis_key)
        if chart_spec:
            chart_id = f"thesis-chart-{i}"
            chart_html = f'<div class="chart-container"><h3>{chart_spec.get("title", "Thesis Chart")}</h3><canvas id="{chart_id}" data-thesis-key="{thesis_key}"></canvas></div>'

        # Structural theses get a source viewer
        source_viewer = ""
        if is_structural:
            source_lines = []
            for line in content.split('\n'):
                for field in ('Source:', 'Provenance:', 'Research Brief:'):
                    if line.strip().startswith(f'**{field}'):
                        source_lines.append(line.strip())

            research_brief_content = ""
            brief_match = re.search(r'`outputs/research/(.+?)`', content)
            if brief_match and output_dir is not None:
                brief_path = output_dir / "research" / brief_match.group(1)
                if brief_path.exists():
                    research_brief_content = brief_path.read_text(encoding="utf-8")

            source_inner = '<div style="margin-top: 12px;">'
            for line in source_lines:
                source_inner += f'<p style="margin: 4px 0; font-size: 13px; color: var(--text);">{md_to_html(line)}</p>'
            if research_brief_content:
                source_inner += (
                    f'<details style="margin-top: 16px;">'
                    f'<summary style="cursor: pointer; color: var(--accent); font-size: 13px;">Research Brief</summary>'
                    f'<div style="margin-top: 12px; padding: 16px; background: var(--bg); border-radius: 6px; '
                    f'max-height: 600px; overflow-y: auto; font-size: 14px; line-height: 1.7;">'
                    f'{md_to_html(research_brief_content)}'
                    f'</div>'
                    f'</details>'
                )
            source_inner += '</div>'

            source_viewer = (
                f'<div style="margin-top: 24px; padding: 12px 16px; background: var(--surface2); border-radius: 8px; border-left: 3px solid var(--accent);">'
                f'<a href="#" onclick="event.preventDefault(); var el = document.getElementById(\'source-raw-{i}\'); el.style.display = el.style.display === \'none\' ? \'block\' : \'none\';" '
                f'style="color: var(--accent); font-size: 13px; text-decoration: none;">View sources &rarr;</a>'
                f'<div id="source-raw-{i}" style="display:none;">{source_inner}</div>'
                f'</div>'
            )

        display = "block" if i == 0 else "none"
        thesis_contents += (
            f'<div class="thesis-detail" id="thesis-{i}" style="display:{display}">'
            f'{chart_html}'
            f'{md_to_html(format_thesis_html(render_content))}'
            f'{source_viewer}'
            f'</div>\n'
        )

    # --- Build archive table from closed theses ---
    closed_theses = closed_theses or []
    archive_table_rows = ""
    for name, content in closed_theses:
        clean_name = name.replace(".md", "").replace("-", " ").title()
        # Remove common prefixes
        for prefix in ("Closed ", "Invalidated "):
            if clean_name.startswith(prefix):
                clean_name = clean_name[len(prefix):]

        content_lower = content.lower()
        is_structural = (
            "classification:** structural" in content_lower
            or "structural thesis candidate" in content_lower
            or "structural foundation" in content_lower
        )
        thesis_type = "STRUCTURAL" if is_structural else "TACTICAL"

        # Outcome: look for **Outcome:** or **Status:** or **Close reason:**
        outcome = ""
        for pattern in [r'\*\*Outcome:\*\*\s*(.+)', r'\*\*Close reason:\*\*\s*(.+)', r'\*\*Status:\*\*\s*(.+)']:
            m = re.search(pattern, content)
            if m:
                outcome = m.group(1).strip()
                break
        # Fallback: check filename prefix
        if not outcome:
            if "INVALIDATED" in name.upper():
                outcome = "Invalidated"
            elif "CLOSED" in name.upper():
                outcome = "Closed"

        generated_date = ""
        m = re.search(r'\*\*Generated:\*\*\s*(.+)', content)
        if m:
            generated_date = m.group(1).strip()

        closed_date = ""
        for pattern in [r'\*\*Closed:\*\*\s*(.+)', r'\*\*Invalidated:\*\*\s*(.+)', r'\*\*Close date:\*\*\s*(.+)']:
            m = re.search(pattern, content)
            if m:
                closed_date = m.group(1).strip()
                break

        conviction = ""
        m = re.search(r'\*Thesis conviction:\*\s*(\w+)', content) or re.search(r'\*\*Conviction:\*\*\s*(\w+)', content)
        if m:
            conviction = m.group(1).strip()

        # Duration
        duration = ""
        if generated_date and closed_date:
            try:
                from datetime import datetime as dt
                g = dt.strptime(generated_date.split()[0], "%Y-%m-%d")
                c = dt.strptime(closed_date.split()[0], "%Y-%m-%d")
                days = (c - g).days
                if days >= 0:
                    duration = f"{days}d"
            except (ValueError, IndexError):
                pass

        type_class = "type-structural" if is_structural else "type-tactical"
        outcome_lower = outcome.lower()
        outcome_class = "archive-invalidated" if "invalidat" in outcome_lower else ("archive-closed" if outcome_lower else "")

        archive_table_rows += (
            f'<tr>'
            f'<td class="thesis-name-cell">{clean_name}</td>'
            f'<td><span class="thesis-type {type_class}">{thesis_type}</span></td>'
            f'<td class="thesis-conviction">{conviction or "—"}</td>'
            f'<td><span class="{outcome_class}">{outcome or "—"}</span></td>'
            f'<td class="thesis-date">{generated_date or "—"}</td>'
            f'<td class="thesis-date">{closed_date or "—"}</td>'
            f'<td class="thesis-date">{duration or "—"}</td>'
            f'</tr>\n'
        )

    # --- Build timeline data for active/draft theses ---
    # Each thesis becomes a horizontal bar: start = generated date, end = generated + horizon
    timeline_data_items = []
    for i, (name, content, status) in enumerate(deduped):
        clean_name = name.replace("ACTIVE-", "").replace("DRAFT-", "").replace(".md", "").replace("-", " ").title()

        generated_date = ""
        m = re.search(r'\*\*Generated:\*\*\s*(.+)', content)
        if m:
            generated_date = m.group(1).strip().split()[0]  # just the date part

        # Parse horizon to estimate end date
        # Match both ## Time Horizon (h2) and **Time horizon:** (bold inline)
        horizon_text = ""
        horizon_match = re.search(r'## Time [Hh]orizon\s*\n+(.+)', content)
        if not horizon_match:
            horizon_match = re.search(r'\*\*Time [Hh]orizon:\*\*\s*(.+)', content)
        if not horizon_match:
            # Also try **Time horizon:** on its own line followed by content on next line
            horizon_match = re.search(r'\*\*Time [Hh]orizon:\*\*\s*\n+(.+)', content)
        if horizon_match:
            horizon_text = horizon_match.group(1).strip()

        # Extract numeric range from horizon (e.g., "2-8 weeks", "6-18 months", "1-3 months")
        horizon_weeks = 0
        # Try range format: "6-18 months"
        h_match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*(weeks?|months?|years?)', horizon_text, re.IGNORECASE)
        if h_match:
            low, high = int(h_match.group(1)), int(h_match.group(2))
            unit = h_match.group(3).lower()
            mid = (low + high) / 2
            if 'week' in unit:
                horizon_weeks = mid
            elif 'month' in unit:
                horizon_weeks = mid * 4.33
            elif 'year' in unit:
                horizon_weeks = mid * 52
        else:
            # Try single number: "6 months", "18 months", "2 years"
            h_match_single = re.search(r'(\d+)\s*(weeks?|months?|years?)', horizon_text, re.IGNORECASE)
            if h_match_single:
                val = int(h_match_single.group(1))
                unit = h_match_single.group(2).lower()
                if 'week' in unit:
                    horizon_weeks = val
                elif 'month' in unit:
                    horizon_weeks = val * 4.33
                elif 'year' in unit:
                    horizon_weeks = val * 52
        # Default: if still 0, give a default of 13 weeks (~3 months) so bar is visible
        if horizon_weeks == 0:
            horizon_weeks = 13

        color = "#22c55e" if status == "ACTIVE" else "#f59e0b"
        timeline_data_items.append({
            "idx": i,
            "name": clean_name,
            "status": status,
            "start": generated_date,
            "horizonWeeks": round(horizon_weeks, 1),
            "color": color,
        })

    timeline_data_json = json.dumps(timeline_data_items)

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
    improvement_parsed = {}  # parsed struct per week
    for w in all_weeks:
        display = "block" if w == week else "none"
        wd = all_weeks_data.get(w, {})
        content = wd.get("improvement", "")
        if not content and w == week:
            content = improvement
        if not content:
            content = f"No improvement report available for {w}."
        improvement_weeks_html += f'<div class="week-content" data-week="{w}" style="display:{display}">{md_to_html(content)}</div>\n'
        if w == week:
            improvement_parsed = parse_improvement_report(content)

    # Build structured system health components
    imp = improvement_parsed
    health_score = imp.get("health_score", "")
    health_trend = imp.get("health_trend", "")
    skills_at_risk = imp.get("skills_at_risk", "")
    obs_rows = imp.get("observation_rows", [])
    amendments = imp.get("amendments", [])
    gaps = imp.get("gaps", [])

    # Count non-resolved amendments (PROPOSED or verdict INCONCLUSIVE)
    pending_count = sum(1 for a in amendments if (
        a.get("status", "").lower() in ("proposed", "pending") or
        "inconclusive" in a.get("verdict", "").lower()
    ))

    # Health score color
    try:
        hs_val = float(health_score) if health_score else 0
    except ValueError:
        hs_val = 0
    if hs_val >= 0.8:
        hs_color = "var(--green)"
    elif hs_val >= 0.6:
        hs_color = "var(--accent)"
    else:
        hs_color = "var(--red)"

    # Trend arrow
    trend_arrow = ""
    if "improv" in health_trend or "up" in health_trend:
        trend_arrow = "↑"
    elif "degrad" in health_trend or "down" in health_trend or "declin" in health_trend:
        trend_arrow = "↓"
    elif health_trend:
        trend_arrow = "→"

    # Build observation summary table rows
    obs_table_rows = ""
    for row in obs_rows:
        skill = row.get("skill", "")
        # Try multiple column name patterns
        score = (row.get("run 3 score", "") or row.get("score", "") or
                 row.get("self score", "") or row.get("run 2 score", ""))
        delta = row.get("δ", row.get("delta", ""))
        data_pts = row.get("data points", row.get("data_points", ""))
        gaps_col = row.get("gaps", "")
        freshest = row.get("freshest", "")

        # Color delta
        delta_style = ""
        if delta:
            d_str = delta.strip().lstrip('+')
            try:
                d_val = float(d_str) if d_str not in ("NEW", "—", "0") else 0
                if d_val > 0:
                    delta_style = 'color: var(--green);'
                elif d_val < 0:
                    delta_style = 'color: var(--red);'
            except ValueError:
                if delta.strip() == "NEW":
                    delta_style = 'color: var(--blue);'

        obs_table_rows += (
            f'<tr>'
            f'<td>{skill}</td>'
            f'<td style="text-align:center;">{score}</td>'
            f'<td style="text-align:center; {delta_style}">{delta}</td>'
            f'<td style="text-align:center;">{data_pts}</td>'
            f'<td>{gaps_col}</td>'
            f'<td style="text-align:center;">{freshest}</td>'
            f'</tr>'
        )

    # Build amendment log table rows
    amendment_table_rows = ""
    for row in amendments:
        a_id = (row.get("amendment id", "") or row.get("id", ""))
        proposed = row.get("proposed", "")
        status = (row.get("status", ""))
        target = (row.get("target metric", "") or row.get("amendment", ""))
        before = row.get("before", "")
        after = (row.get("after", "") or row.get("after (run 3)", ""))
        verdict = row.get("verdict", "")

        # Badge for status
        s_lower = status.lower().strip()
        if s_lower == "approved":
            badge_cls = "badge-active"
        elif s_lower == "proposed":
            badge_cls = "badge-draft"
        elif s_lower == "rejected" or s_lower == "reverted":
            badge_cls = "badge-invalidated"
        else:
            badge_cls = "badge-draft"

        # Verdict coloring
        v_lower = verdict.lower() if verdict else ""
        v_style = ""
        if "effective" in v_lower:
            v_style = 'color: var(--green);'
        elif "reverted" in v_lower or "ineffective" in v_lower:
            v_style = 'color: var(--red);'
        elif "inconclusive" in v_lower:
            v_style = 'color: var(--accent);'

        # Build expanded detail content
        detail_parts = []
        if before:
            detail_parts.append(f'<strong>Before:</strong> {before}')
        if after:
            detail_parts.append(f'<strong>After:</strong> {after}')
        detail_html = ' → '.join(detail_parts) if detail_parts else 'No detail available.'

        amendment_table_rows += (
            f'<tr class="amendment-row" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === \'none\' ? \'table-row\' : \'none\';" style="cursor: pointer;">'
            f'<td style="color: var(--amber); white-space: nowrap;">{a_id}</td>'
            f'<td style="white-space: nowrap;">{proposed}</td>'
            f'<td>{target}</td>'
            f'<td><span class="badge {badge_cls}">{status.upper()}</span></td>'
            f'<td style="{v_style}">{verdict or "—"}</td>'
            f'</tr>'
            f'<tr class="amendment-detail" style="display: none;">'
            f'<td colspan="5" style="background: var(--surface2); padding: 8px 12px; font-size: 11px; color: var(--text-muted); border-left: 3px solid var(--amber);">'
            f'{detail_html}'
            f'</td>'
            f'</tr>'
        )

    # Build gaps table rows
    gaps_table_rows = ""
    for row in gaps:
        skill = row.get("skill", "")
        gap = row.get("gap description", row.get("gap", ""))
        weeks_missing = row.get("consecutive weeks", row.get("consecutive weeks missing", ""))
        severity = row.get("severity", "")

        sev_style = ""
        sev_lower = severity.lower() if severity else ""
        if sev_lower == "high":
            sev_style = 'color: var(--red);'
        elif sev_lower == "medium":
            sev_style = 'color: var(--accent);'
        elif sev_lower == "low":
            sev_style = 'color: var(--text-muted);'

        gaps_table_rows += (
            f'<tr>'
            f'<td>{skill}</td>'
            f'<td>{gap}</td>'
            f'<td style="text-align:center;">{weeks_missing}</td>'
            f'<td style="{sev_style}">{severity}</td>'
            f'</tr>'
        )

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

    # Build regime forecast text HTML from synthesis sections
    regime_forecast_html = md_to_html(regime_data.get("forecast_section_md", "")) if regime_data.get("forecast_section_md") else ""
    regime_what_changed_html = md_to_html(regime_data.get("what_changed_md", "")) if regime_data.get("what_changed_md") else ""

    # Build methodology (About) HTML — parse into h2 sections for accordion display
    methodology_html = ""
    methodology_meta = {"version": "", "framework": "", "updated": ""}
    if methodology:
        # Extract version, framework, last updated from header
        m = re.search(r'\*\*Version:\*\*\s*(.+)', methodology)
        if m:
            methodology_meta["version"] = m.group(1).strip()
        m = re.search(r'\*\*(?:Last Updated|Updated):\*\*\s*(.+)', methodology)
        if m:
            methodology_meta["updated"] = m.group(1).strip()
        m = re.search(r'\*\*Framework:\*\*\s*(.+)', methodology)
        if m:
            methodology_meta["framework"] = m.group(1).strip()

    # Override version from plugin.json if available
    plugin_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.claude-plugin', 'plugin.json')
    try:
        with open(plugin_json_path, "r") as f:
            plugin_data = json.load(f)
        methodology_meta["version"] = plugin_data.get("version", methodology_meta["version"])
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    if methodology:
        # Split into h2 sections
        sections = []
        current_title = ""
        current_lines = []
        for line in methodology.split('\n'):
            if line.startswith('## ') and not line.startswith('### '):
                if current_title:
                    sections.append((current_title, '\n'.join(current_lines)))
                current_title = line[3:].strip()
                current_lines = []
            elif line.startswith('# ') and not line.startswith('## '):
                # Top-level title — skip (it's the page header)
                continue
            else:
                current_lines.append(line)
        if current_title:
            sections.append((current_title, '\n'.join(current_lines)))

        # Build accordion HTML reusing the skill-accordion pattern
        for title, body in sections:
            # Skip metadata lines from section body (Version, Updated, Framework at top)
            body_stripped = body.strip()
            if not body_stripped or (len(body_stripped) < 20 and '**' in body_stripped):
                continue
            methodology_html += f'''<div class="skill-accordion">
                <button class="skill-header" onclick="this.classList.toggle('open'); this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'block' ? 'none' : 'block';">
                    <span class="skill-name">{title}</span>
                    <span class="skill-arrow">&#9660;</span>
                </button>
                <div class="skill-body" style="display:none">{md_to_html(body)}</div>
            </div>\n'''

    if not methodology_html:
        methodology_html = "<p style='color: var(--text-muted); text-align: center; padding: 40px 0;'>No methodology document found.</p>"

    # --- Build cross-asset and sector view tables ---
    def _direction_class(d):
        dl = d.lower()
        if any(x in dl for x in ['buy', 'favor', 'strong favor', 'overweight']):
            return 'direction-buy'
        elif any(x in dl for x in ['reduce', 'underweight', 'avoid']):
            return 'direction-sell'
        return 'direction-hold'

    def _has_timing(items):
        """Check if any item in the list has a non-empty timing value."""
        return any(item.get('timing', '').strip() for item in items)

    def _build_asset_table(items, name_key='what', show_timing=True):
        """Build HTML table rows from a list of asset dicts."""
        rows = ''
        for item in items:
            what = item.get(name_key, '')
            direction = item.get('direction', '')
            etfs = item.get('etfs', '')
            why = item.get('why', '')
            dc = _direction_class(direction)
            rows += (
                f'<tr>'
                f'<td class="cross-asset-what">{what}</td>'
                f'<td><span class="cross-asset-direction {dc}">{direction}</span></td>'
                f'<td class="cross-asset-etfs">{etfs}</td>'
                f'<td class="cross-asset-why">{why}</td>'
            )
            if show_timing:
                rows += f'<td class="cross-asset-timing">{item.get("timing", "")}</td>'
            rows += '</tr>'
        return rows

    def _build_asset_section(items, name_key, label):
        """Build a full cross-asset or sector table HTML block."""
        if not items:
            return ""
        show_timing = _has_timing(items)
        html = '<div class="cross-asset-container"><table>'
        if show_timing:
            html += f'<thead><tr><th style="width:18%">{label}</th><th style="width:12%">Direction</th><th style="width:16%">ETFs</th><th style="width:34%">Why</th><th style="width:20%">Timing</th></tr></thead><tbody>'
        else:
            html += f'<thead><tr><th style="width:20%">{label}</th><th style="width:13%">Direction</th><th style="width:20%">ETFs</th><th style="width:47%">Why</th></tr></thead><tbody>'
        html += _build_asset_table(items, name_key, show_timing)
        html += '</tbody></table></div>'
        return html

    # Use JSON data if available, otherwise fall back to markdown extraction
    if cross_assets_from_json:
        cross_assets = cross_assets_from_json
        sector_view = sector_view_from_json
    else:
        cross_assets, sector_view = extract_cross_asset_tables(briefing) if briefing else ([], [])

    cross_asset_html = _build_asset_section(cross_assets, 'what', 'What')
    sector_view_html = _build_asset_section(sector_view, 'sector', 'Sector')

    # Extract system health score from improvement text
    health_score = "—"
    amendments_pending = "—"
    data_freshness = "100%"

    improvement_lower = improvement.lower()
    score_match = re.search(r'(?:overall.*?score|system score)[:\s]+(\d+\.?\d*)', improvement_lower)
    if score_match:
        health_score = score_match.group(1)

    amend_match = re.search(r'(\d+)\s*(?:carry-forward|pending|amendments pending)', improvement_lower)
    if amend_match:
        amendments_pending = amend_match.group(1)

    # Track record — extract from improvement or briefing
    track_record = "Collecting data..."
    track_record_color = "var(--text-muted)"
    # Try briefing first (system health section usually has accuracy)
    briefing_lower = briefing.lower() if briefing else ""
    regime_accuracy_match = re.search(r'regime\s*(?:call)?\s*accuracy[:\s]+(\d+)%', briefing_lower)
    if regime_accuracy_match:
        pct = int(regime_accuracy_match.group(1))
        track_record = f"{pct}%"
        track_record_color = '#22c55e' if pct >= 70 else ('#f59e0b' if pct >= 50 else '#ef4444')
    elif 'too early' in briefing_lower or 'collecting data' in improvement_lower:
        track_record = "Collecting..."
        track_record_color = "var(--text-muted)"

    # Health score color
    try:
        score_val = float(health_score) if health_score != "—" else 0
        health_color = '#22c55e' if score_val > 80 else ('#f59e0b' if score_val > 60 else '#ef4444')
    except ValueError:
        health_color = '#8b8fa3'

    # Build thesis chart specs JSON for frontend rendering
    # NOTE: This is injected via string concatenation after the f-string,
    # because JSON contains braces that conflict with f-string interpolation.
    thesis_chart_specs_raw = json.dumps(thesis_chart_specs) if thesis_chart_specs else '{}'

    # Build regime history trail data points (cap at 26 weeks = 6-month horizon)
    trail_entries = regime_history[:-1]  # all except current (current is its own dataset)
    trail_entries = trail_entries[-26:]  # keep most recent 26 weeks
    history_points = ', '.join(
        f'{{ x: {r["x"]}, y: {r["y"]} }}'
        for r in trail_entries
    )
    # Week labels for tooltips on trail dots
    trail_week_labels = json.dumps([r.get("week", "") for r in trail_entries])

    # Render regime narrative as markdown
    regime_narrative_html = md_to_html(regime_data.get('regime_narrative', '')) if regime_data.get('regime_narrative') else '<p style="color: var(--text-muted);">Narrative not available — run the weekly cycle to populate.</p>'

    # Map regime to color for topbar
    regime_color_map = {
        "Goldilocks": "#22c55e",
        "Overheating": "#f59e0b",
        "Stagflation": "#ef4444",
        "Disinflationary Slowdown": "#3b82f6",
        "Disinflationary": "#3b82f6",
    }
    regime_color = regime_color_map.get(regime_data['regime'], "#a855f7")

    # Briefing word count for reading time estimate
    briefing_word_count = len(briefing.split()) if briefing else 0
    reading_time = max(1, briefing_word_count // 250)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Macro Advisor — {week}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script>{_inline_chartjs()}</script>
<style>
:root {{
    --bg: #0a0a0a;
    --surface: #111111;
    --surface2: #1a1a1a;
    --surface3: #222222;
    --border: #2a2a2a;
    --border-bright: #3a3a3a;
    --text: #d4d4d4;
    --text-muted: #737373;
    --text-dim: #525252;
    --accent: #f59e0b;
    --amber: #f59e0b;
    --amber-dim: #92400e;
    --green: #22c55e;
    --green-dim: #166534;
    --red: #ef4444;
    --red-dim: #991b1b;
    --blue: #3b82f6;
    --blue-dim: #1e3a5f;
    --cyan: #06b6d4;
    --orange: #f97316;
    --purple: #a855f7;
    --white: #fafafa;
    --mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', 'Consolas', monospace;
    --sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: var(--mono);
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    padding: 0;
    font-size: 12px;
}}
.topbar {{
    background: #000;
    border-bottom: 1px solid var(--border);
    padding: 6px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 100;
}}
.topbar-left {{
    display: flex;
    align-items: center;
    gap: 16px;
}}
.topbar-logo {{
    color: var(--accent);
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.1em;
    font-family: var(--mono);
}}
.topbar-regime {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
}}
.regime-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: {regime_color};
    animation: pulse 2s infinite;
}}
@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.7; }}
}}
.regime-name {{
    color: {regime_color};
    font-weight: 600;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
.regime-conf {{
    color: var(--text-muted);
    font-size: 11px;
}}
.topbar-right {{
    display: flex;
    align-items: center;
    gap: 20px;
    color: var(--text-muted);
    font-size: 11px;
}}
.week-select {{
    background: var(--surface2);
    color: var(--accent);
    border: 1px solid var(--border);
    padding: 3px 8px;
    font-family: var(--mono);
    font-size: 11px;
    cursor: pointer;
}}
.topbar-clock {{
    color: var(--text-dim);
    font-variant-numeric: tabular-nums;
}}
.nav {{
    display: flex;
    gap: 0;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0 16px;
}}
.nav button {{
    background: none;
    border: none;
    color: var(--text-muted);
    padding: 8px 16px;
    cursor: pointer;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-bottom: 2px solid transparent;
    transition: all 0.15s;
}}
.nav button:hover {{
    color: var(--text);
    background: var(--surface2);
}}
.nav button.active {{
    color: var(--accent);
    border-bottom-color: var(--accent);
}}
.main {{
    padding: 12px 16px;
}}
.tab-content {{
    display: none;
}}
.tab-content.active {{
    display: block;
}}
/* KPI Grid */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 8px;
    margin-bottom: 16px;
}}
.kpi-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 10px 12px;
}}
.kpi {{
    padding: 10px 12px;
}}
.kpi-label {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-dim);
    margin-bottom: 4px;
}}
.kpi-value {{
    font-size: 22px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    line-height: 1.1;
}}
.kpi-number {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 22px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--accent);
    line-height: 1.1;
}}
.kpi-sub {{
    font-size: 10px;
    color: var(--text-muted);
    margin-top: 4px;
}}
/* Grid layouts */
.grid-3 {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
}}
/* 2-column grid for overview */
.overview-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 8px;
}}
.overview-grid-full {{
    grid-column: 1 / -1;
}}
/* Panel styling */
.panel {{
    background: var(--surface);
    border: 1px solid var(--border);
    overflow: hidden;
}}
.panel-header {{
    background: var(--surface2);
    border-bottom: 1px solid var(--border);
    padding: 6px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
}}
.panel-body {{
    padding: 10px 12px;
}}
.panel-body-dense {{
    padding: 0;
}}
.scroll-y {{
    overflow-y: auto;
}}
.regime-forecast-chart {{
    position: relative;
}}
.thesis-book {{
    overflow-x: auto;
}}
.thesis-book table {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    width: 100%;
    border-collapse: collapse;
}}
.thesis-book th {{
    background: var(--surface2);
    padding: 4px 10px;
    text-align: left;
    font-weight: 500;
    font-size: 10px;
    border-bottom: 1px solid var(--border);
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
.thesis-book td {{
    padding: 5px 10px;
    border-bottom: 1px solid #1a1a1a;
}}
.thesis-book tr:hover td {{
    background: var(--surface2);
}}
.cross-asset-container {{
    overflow-x: auto;
}}
.cross-asset-container table {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    width: 100%;
    border-collapse: collapse;
    font-feature-settings: "tnum";
}}
.cross-asset-container th {{
    background: var(--surface2);
    padding: 4px 10px;
    text-align: left;
    font-weight: 500;
    font-size: 10px;
    border-bottom: 1px solid var(--border);
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
.cross-asset-container td {{
    padding: 5px 10px;
    border-bottom: 1px solid #1a1a1a;
}}
.cross-asset-container tr:hover td {{
    background: var(--surface2);
}}
.cross-asset-what {{
    color: var(--white);
    white-space: nowrap;
}}
.cross-asset-etfs {{
    font-family: var(--mono);
    white-space: nowrap;
    color: var(--text-muted);
}}
.cross-asset-why {{
    color: var(--text);
    font-family: 'Inter', sans-serif;
    font-size: 11px;
}}
.cross-asset-timing {{
    color: var(--text-muted);
    font-size: 10px;
    white-space: nowrap;
}}
.cross-asset-direction {{
    font-weight: 600;
}}
.direction-buy {{
    color: var(--green);
}}
.direction-sell {{
    color: var(--red);
}}
.direction-hold {{
    color: var(--text-muted);
}}
/* Chart container */
.chart-container {{
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 10px 12px;
    margin-bottom: 8px;
    position: relative;
}}
.chart-container h3 {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    margin-bottom: 12px;
}}
canvas {{
    max-height: 400px;
}}
/* Content styling */
.briefing-content {{
    font-family: var(--sans);
    font-size: 13px;
    line-height: 1.7;
}}
.briefing-content h2 {{
    color: var(--accent);
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 20px 0 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--border);
}}
.briefing-content h3 {{
    color: var(--text);
    font-size: 12px;
    font-weight: 600;
    margin: 14px 0 6px;
}}
.briefing-content p {{
    margin: 6px 0;
}}
.briefing-content table {{
    font-family: var(--mono);
    margin: 8px 0;
}}
h1 {{ font-size: 16px; font-weight: 700; margin: 20px 0 12px; letter-spacing: -0.02em; }}
h2 {{ color: var(--accent); font-family: var(--mono); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; margin: 20px 0 8px; padding-bottom: 4px; border-bottom: 1px solid var(--border); }}
h3 {{ color: var(--text); font-size: 12px; font-weight: 600; margin: 14px 0 6px; }}
h4 {{ font-size: 11px; font-weight: 600; margin: 8px 0 6px; }}
p {{ margin: 6px 0; color: var(--text); }}
ul {{ margin: 6px 0 6px 20px; }}
li {{ margin: 3px 0; }}
hr {{ border: none; border-top: 1px solid var(--border); margin: 12px 0; }}
strong {{ color: var(--white); }}
code {{ background: var(--surface2); padding: 2px 4px; border-radius: 0; font-family: 'JetBrains Mono', monospace; font-size: 11px; }}
a {{ color: var(--accent); text-decoration: none; }}
.table-wrapper {{ overflow-x: auto; margin: 8px 0; }}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    font-family: var(--mono);
}}
th {{
    text-align: left;
    padding: 4px 10px;
    font-weight: 500;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-dim);
    border-bottom: 1px solid var(--border);
    background: var(--surface2);
    position: sticky;
    top: 0;
}}
td {{
    padding: 5px 10px;
    border-bottom: 1px solid #1a1a1a;
    font-variant-numeric: tabular-nums;
}}
tr:hover td {{
    background: var(--surface2);
}}
.code-block {{
    background: var(--surface2);
    border: 1px solid var(--border);
    padding: 8px 12px;
    margin: 8px 0;
    overflow-x: auto;
}}
.code-block pre {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    line-height: 1.4;
}}
/* Thesis index table */
/* Thesis sidebar layout: index left, detail right */
.grid-sidebar {{
    display: grid;
    grid-template-columns: 380px 1fr;
    gap: 8px;
    transition: grid-template-columns 0.3s ease;
}}
.thesis-index {{
    background: var(--surface);
    border: 1px solid var(--border);
}}
.thesis-index table {{
    margin: 0;
}}
.thesis-index th {{
    position: sticky;
    top: 0;
    z-index: 1;
}}
.thesis-row {{
    cursor: pointer;
    transition: background 0.1s;
}}
.thesis-row:hover td {{
    background: var(--surface2);
}}
.thesis-row.selected td {{
    background: var(--amber-dim);
    border-left: 2px solid var(--accent);
}}
.thesis-row.selected td:first-child {{
    padding-left: 6px;
}}
.thesis-name-cell {{
    font-weight: 500;
    color: var(--white);
    min-width: 100px;
    max-width: 200px;
    word-wrap: break-word;
    overflow-wrap: break-word;
}}
/* Badge system — compact pills */
.badge {{
    font-size: 10px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 2px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-family: var(--mono);
    cursor: help;
}}
.badge-active {{ background: var(--green-dim); color: var(--green); }}
.badge-draft {{ background: var(--amber-dim); color: var(--accent); }}
.badge-invalidated {{ background: var(--red-dim); color: var(--red); }}
.badge-closed {{ background: var(--surface3); color: var(--text-muted); }}
.badge-tactical {{ background: var(--blue-dim); color: var(--blue); }}
.badge-structural {{ background: #3b1f6e; color: var(--purple); }}
/* Amendment row interactions */
.amendment-row:hover {{ background: var(--surface2); }}
.amendment-detail td {{ font-family: var(--mono); }}
/* Conviction bar — 4 blocks visual indicator */
.conviction-bar {{
    display: flex;
    gap: 2px;
    align-items: center;
}}
.conviction-bar .block {{
    width: 12px;
    height: 6px;
    background: var(--surface3);
    border-radius: 1px;
}}
.conviction-bar .block.filled {{ background: var(--green); }}
.conviction-bar.medium .block.filled {{ background: var(--accent); }}
.conviction-bar.low .block.filled {{ background: var(--red); }}
.thesis-horizon {{
    font-size: 10px;
    color: var(--text-muted);
    white-space: nowrap;
}}
/* Thesis detail panel */
.thesis-detail-panel {{
    background: var(--surface);
    border: 1px solid var(--border);
}}
.thesis-detail-header {{
    background: var(--surface2);
    border-bottom: 1px solid var(--border);
    padding: 6px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 2;
}}
.thesis-detail-title {{
    font-size: 11px;
    font-weight: 600;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}
.thesis-detail-dates {{
    font-size: 10px;
    color: var(--text-dim);
    font-family: var(--mono);
    margin-top: 2px;
    letter-spacing: 0.02em;
}}
.thesis-detail-meta {{
    font-size: 10px;
    color: var(--text-dim);
    display: flex;
    gap: 6px;
    align-items: center;
    flex-shrink: 0;
}}
.thesis-detail {{
    font-family: var(--sans);
    font-size: 13px;
    line-height: 1.7;
    color: var(--text);
    padding: 10px 12px;
}}
.thesis-detail h1 {{
    color: var(--accent);
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 16px 0 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--border);
}}
.thesis-detail h2 {{
    color: var(--accent);
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 16px 0 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--border);
}}
.thesis-detail h3 {{
    color: var(--text);
    font-size: 12px;
    font-weight: 600;
    margin: 12px 0 6px;
}}
.thesis-detail p {{
    margin: 4px 0;
    color: var(--text);
}}
.thesis-detail strong {{
    color: var(--white);
}}
.kill-switch-card {{
    background: var(--red-dim);
    border-left: 3px solid var(--red);
    padding: 8px 12px;
    margin: 8px 0;
    font-size: 11px;
}}
.kill-switch-card strong {{
    color: var(--red);
}}
/* Thesis filters */
.thesis-filters {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}}
.thesis-filters select {{
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 3px 8px;
    font-family: var(--mono);
    font-size: 10px;
    cursor: pointer;
}}
.thesis-filters select:hover {{
    border-color: var(--accent);
}}
.thesis-count {{
    color: var(--text-dim);
    font-size: 10px;
    margin-left: auto;
}}
/* Sub-tabs for theses (Active/Draft | Archive) */
.thesis-subtabs {{
    display: flex;
    gap: 0;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--border);
}}
.thesis-subtabs button {{
    background: none;
    border: none;
    color: var(--text-muted);
    padding: 6px 14px;
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-bottom: 2px solid transparent;
}}
.thesis-subtabs button:hover {{
    color: var(--text);
}}
.thesis-subtabs button.active {{
    color: var(--accent);
    border-bottom-color: var(--accent);
}}
.thesis-subtab-content {{
    display: none;
}}
.thesis-subtab-content.active {{
    display: block;
}}
/* Archive table */
.archive-invalidated {{
    background: var(--red-dim);
    color: var(--red);
    font-size: 10px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 2px;
}}
.archive-closed {{
    background: var(--surface3);
    color: var(--text-muted);
    font-size: 10px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 2px;
}}
/* View toggle (table/timeline) */
.view-toggle {{
    display: inline-flex;
    border: 1px solid var(--border);
    overflow: hidden;
    margin-left: 8px;
}}
.view-toggle button {{
    background: var(--surface);
    border: none;
    color: var(--text-muted);
    padding: 3px 10px;
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10px;
    border-right: 1px solid var(--border);
}}
.view-toggle button:last-child {{
    border-right: none;
}}
.view-toggle button:hover {{
    color: var(--text);
}}
.view-toggle button.active {{
    background: var(--amber-dim);
    color: var(--accent);
}}
/* Timeline container */
.thesis-timeline {{
    display: none;
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 10px 12px;
    margin-bottom: 8px;
}}
.thesis-timeline.active {{
    display: block;
}}
.thesis-timeline canvas {{
    width: 100% !important;
}}
/* Skill accordion */
.skill-accordion {{
    border: 1px solid var(--border);
    margin-bottom: 6px;
    overflow: hidden;
}}
.skill-header {{
    width: 100%;
    background: var(--surface2);
    border: none;
    padding: 8px 12px;
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    text-align: left;
    color: var(--text);
    transition: background 0.2s;
    font-size: 12px;
}}
.skill-header:hover {{
    background: var(--surface3);
}}
.skill-header.open {{
    background: var(--surface3);
    border-bottom: 1px solid var(--border);
}}
.skill-name {{
    font-weight: 600;
    font-size: 12px;
    min-width: 160px;
}}
.skill-desc {{
    color: var(--text-muted);
    font-size: 11px;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.skill-arrow {{
    color: var(--text-muted);
    font-size: 9px;
    transition: transform 0.2s;
}}
.skill-header.open .skill-arrow {{
    transform: rotate(180deg);
}}
.skill-body {{
    padding: 10px 12px;
    background: var(--bg);
    font-size: 12px;
    max-height: 600px;
    overflow-y: auto;
}}
/* Responsive: stack grids on narrow screens */
@media (max-width: 900px) {{
    .grid-sidebar, .grid-3 {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<div class="topbar">
    <div class="topbar-left">
        <span class="topbar-logo">MACRO ADVISOR</span>
        <div class="topbar-regime">
            <span class="regime-dot"></span>
            <span class="regime-name">{regime_data['regime']}</span>
            <span class="regime-conf">W{regime_data.get('weeks_held', '—')} · {regime_data['confidence'].upper()} CONF</span>
        </div>
    </div>
    <div class="topbar-right">
        <select class="week-select" id="weekSelector" onchange="switchWeek(this.value)">
            {week_options_html}
        </select>
        <span id="clock"></span>
    </div>
</div>

<div class="nav">
    <button class="active" onclick="showTab('overview')">OVERVIEW</button>
    <button onclick="showTab('briefing')">BRIEFING</button>
    <button onclick="showTab('regime')">REGIME</button>
    <button onclick="showTab('theses')">THESES</button>
    <button onclick="showTab('improvement')">SYSTEM</button>
    <button onclick="showTab('about')">ABOUT</button>
</div>

<div class="main">

    <!-- Overview Tab -->
    <div class="tab-content active" id="tab-overview">
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">REGIME</div>
                <div class="kpi-number" style="color: {regime_color};">{regime_data['regime']}</div>
                <div class="kpi-sub">W{regime_data.get('weeks_held', '—')} · {regime_data['confidence'].upper()}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">ACTIVE THESES</div>
                <div class="kpi-number">{active_count}</div>
                <div class="kpi-sub">{tactical_count} tactical · {structural_count} structural</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">DRAFT THESES</div>
                <div class="kpi-number" style="color: var(--accent);">{draft_count}</div>
                <div class="kpi-sub">Awaiting decision</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">SYSTEM HEALTH</div>
                <div class="kpi-number" style="color: {health_color};">{health_score}</div>
                <div class="kpi-sub">{amendments_pending} pending</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">TRACK RECORD</div>
                <div class="kpi-number" style="color: {track_record_color};">{track_record}</div>
                <div class="kpi-sub">Regime call accuracy</div>
            </div>
        </div>

        <div class="overview-grid">
            <div class="panel">
                <div class="panel-header">Regime Forecast</div>
                <div class="panel-body regime-forecast-chart">
                    <canvas id="regimeChartOverview" style="max-height: 280px;"></canvas>
                </div>
            </div>
            <div class="panel">
                <div class="panel-header">Thesis Book</div>
                <div class="panel-body thesis-book">
                    <table>
                        <thead>
                            <tr>
                                <th>Thesis</th>
                                <th>St</th>
                                <th>Ty</th>
                                <th>Conv</th>
                                <th>Rec</th>
                            </tr>
                        </thead>
                        <tbody>
                            {thesis_book_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        {'<div class="panel overview-grid-full"><div class="panel-header">Cross-Asset View</div><div class="panel-body">' + cross_asset_html + '</div></div>' if cross_asset_html else ''}

        {'<div class="panel overview-grid-full"><div class="panel-header">Stocks — Sector View</div><div class="panel-body">' + sector_view_html + '</div></div>' if sector_view_html else ''}
    </div>

    <!-- Briefing Tab -->
    <div class="tab-content" id="tab-briefing">
        <div class="panel">
            <div class="panel-header">Monday Briefing · ~{reading_time} min read</div>
            <div class="panel-body briefing-content">
                {briefing_weeks_html}
            </div>
        </div>
    </div>

    <!-- Regime Tab -->
    <div class="tab-content" id="tab-regime">
        <div class="overview-grid">
            <div class="panel">
                <div class="panel-header">Regime Forecast</div>
                <div class="panel-body regime-forecast-chart">
                    <canvas id="regimeChart" style="max-height: 320px;"></canvas>
                </div>
            </div>
            <div class="panel">
                <div class="panel-header">Regime Narrative</div>
                <div class="panel-body" style="font-size: 12px; line-height: 1.6; font-family: var(--sans);">
                    <div style="margin-bottom: 16px;">
                        <div style="font-size: 14px; font-weight: 600; color: {regime_color}; margin-bottom: 4px;">{regime_data['regime']}</div>
                        <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">W{regime_data.get('weeks_held', '—')} · {regime_data['confidence'].upper()} CONFIDENCE</div>
                        {regime_narrative_html}
                    </div>
                    {'<div style="border-top: 1px solid var(--border); padding-top: 12px;"><h4 style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">6 &amp; 12-Month Forecast</h4>' + regime_forecast_html + '</div>' if regime_forecast_html else ''}
                    {'<div style="border-top: 1px solid var(--border); padding-top: 12px; margin-top: 12px;"><h4 style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">What Changed This Week</h4>' + regime_what_changed_html + '</div>' if regime_what_changed_html else ''}
                </div>
            </div>
        </div>
    </div>

    <!-- Theses Tab -->
    <div class="tab-content" id="tab-theses">
        <div class="thesis-subtabs">
            <button class="active" onclick="showThesisSubtab('current')">ACTIVE &amp; DRAFT</button>
            <button onclick="showThesisSubtab('archive')">ARCHIVE {'  (' + str(len(closed_theses)) + ')' if closed_theses else ''}</button>
        </div>

        <!-- Active/Draft sub-tab -->
        <div class="thesis-subtab-content active" id="thesis-sub-current">
            <div class="thesis-filters">
                <select id="filter-status" onchange="filterTheses()">
                    <option value="all">All Status</option>
                    <option value="active">Active</option>
                    <option value="draft">Draft</option>
                </select>
                <select id="filter-type" onchange="filterTheses()">
                    <option value="all">All Types</option>
                    <option value="tactical">Tactical</option>
                    <option value="structural">Structural</option>
                </select>
                <div class="view-toggle">
                    <button class="active" onclick="toggleThesisView('table')">TABLE</button>
                    <button onclick="toggleThesisView('timeline')">TIMELINE</button>
                </div>
                <span class="thesis-count" id="thesis-count">{len(deduped)} theses</span>
            </div>

            <div class="grid-sidebar" id="thesis-grid-view">
                <!-- Left: index table (sticky) -->
                <div style="position: sticky; top: 8px; align-self: start;">
                    <div class="thesis-index" id="thesis-table-view">
                        <div class="panel-body-dense scroll-y" style="max-height: calc(100vh - 260px);">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Thesis</th>
                                        <th>St</th>
                                        <th>Ty</th>
                                        <th>Conv</th>
                                        <th>Horizon</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {thesis_table_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="thesis-timeline" id="thesis-timeline-view" onclick="toggleTimelineExpand()" style="cursor: pointer;">
                        <canvas id="timelineChart"></canvas>
                        <div class="expand-hint" style="text-align: center; font-size: 10px; color: var(--text-muted); margin-top: 6px; font-family: var(--mono); letter-spacing: 0.05em;">⤢ Click to expand</div>
                    </div>
                </div>

                <!-- Right: detail panel -->
                <div class="thesis-detail-panel" id="thesis-detail-panel">
                    <div class="thesis-detail-header" id="thesis-detail-header">
                        <div>
                            <span class="thesis-detail-title" id="detail-title"></span>
                            <div class="thesis-detail-dates" id="detail-dates"></div>
                        </div>
                        <span class="thesis-detail-meta" id="detail-meta"></span>
                    </div>
                    <div>
                        {thesis_contents}
                    </div>
                </div>
            </div>
        </div>

        <!-- Archive sub-tab -->
        <div class="thesis-subtab-content" id="thesis-sub-archive">
            {'<div class="thesis-index"><table><thead><tr><th>Thesis</th><th>Type</th><th>Conv</th><th>Outcome</th><th>Created</th><th>Closed</th><th>Duration</th></tr></thead><tbody>' + archive_table_rows + '</tbody></table></div>' if archive_table_rows else '<p style="color: var(--text-muted); padding: 40px 0; text-align: center;">No closed theses yet. Theses move here when invalidated or closed at target.</p>'}
        </div>
    </div>

    <!-- System Health Tab -->
    <div class="tab-content" id="tab-improvement">
        {'<div class="grid-3" style="margin-bottom: 8px;">' +
            '<div class="panel"><div class="kpi">' +
                '<div class="kpi-label">HEALTH SCORE</div>' +
                '<div class="kpi-value" style="color: ' + hs_color + ';">' + (health_score or '—') + '</div>' +
                '<div class="kpi-sub">' + trend_arrow + ' ' + health_trend + '</div>' +
            '</div></div>' +
            '<div class="panel"><div class="kpi">' +
                '<div class="kpi-label">AMENDMENTS PENDING</div>' +
                '<div class="kpi-value" style="color: ' + ('var(--accent)' if pending_count > 0 else 'var(--green)') + ';">' + str(pending_count) + '</div>' +
                '<div class="kpi-sub">Run /implement-improvements</div>' +
            '</div></div>' +
            '<div class="panel"><div class="kpi">' +
                '<div class="kpi-label">SKILLS AT RISK</div>' +
                '<div class="kpi-value" style="color: ' + ('var(--red)' if skills_at_risk and 'none' not in skills_at_risk.lower() else 'var(--green)') + ';">' + ('None' if not skills_at_risk or 'none' in skills_at_risk.lower() else skills_at_risk[:20]) + '</div>' +
                '<div class="kpi-sub">All self_scores monitored</div>' +
            '</div></div>' +
        '</div>' if health_score else ''}

        {'<div class="panel"><div class="panel-header"><span class="panel-title">SKILL SCORES</span><span class="panel-meta">' + week + '</span></div><div class="panel-body-dense"><table><thead><tr><th>Skill</th><th>Score</th><th>Δ</th><th>Data Points</th><th>Gaps</th><th>Freshest</th></tr></thead><tbody>' + obs_table_rows + '</tbody></table></div></div>' if obs_table_rows else ''}

        {'<div class="panel" style="margin-top: 8px;"><div class="panel-header"><span class="panel-title">AMENDMENT LOG</span><span class="panel-meta">' + week + '</span></div><div class="panel-body-dense"><table><thead><tr><th>ID</th><th>Proposed</th><th>Target / Description</th><th>Status</th><th>Verdict</th></tr></thead><tbody>' + amendment_table_rows + '</tbody></table></div></div>' if amendment_table_rows else ''}

        {'<div class="panel" style="margin-top: 8px;"><div class="panel-header"><span class="panel-title">DATA GAPS</span><span class="panel-meta">' + str(len(gaps)) + ' tracked</span></div><div class="panel-body-dense"><table><thead><tr><th>Skill</th><th>Gap</th><th>Weeks</th><th>Severity</th></tr></thead><tbody>' + gaps_table_rows + '</tbody></table></div></div>' if gaps_table_rows else ''}

        <div class="panel" style="margin-top: 8px;">
            <div class="panel-header">
                <span class="panel-title">FULL REPORT</span>
                <a href="#" onclick="event.preventDefault(); var el = document.getElementById('improvement-full-report'); el.style.display = el.style.display === 'none' ? 'block' : 'none'; this.textContent = el.style.display === 'none' ? 'expand' : 'collapse';" style="color: var(--accent); font-size: 10px; text-decoration: none; font-family: var(--mono);">expand</a>
            </div>
            <div class="panel-body briefing-content" id="improvement-full-report" style="display: none;">
                {improvement_weeks_html}
            </div>
        </div>
    </div>

    <!-- About Tab -->
    <div class="tab-content" id="tab-about">
        {'<div class="grid-3" style="margin-bottom: 8px;">' +
            '<div class="panel"><div class="kpi">' +
                '<div class="kpi-label">FRAMEWORK</div>' +
                '<div style="font-size: 14px; font-weight: 600; color: var(--accent); line-height: 1.3;">' + (methodology_meta["framework"] or 'Alpine Macro') + '</div>' +
            '</div></div>' +
            '<div class="panel"><div class="kpi">' +
                '<div class="kpi-label">VERSION</div>' +
                '<div style="font-size: 18px; font-weight: 700; color: var(--white); font-variant-numeric: tabular-nums;">' + (methodology_meta["version"] or '—') + '</div>' +
            '</div></div>' +
            '<div class="panel"><div class="kpi">' +
                '<div class="kpi-label">LAST UPDATED</div>' +
                '<div style="font-size: 14px; font-weight: 600; color: var(--text); font-variant-numeric: tabular-nums;">' + (methodology_meta["updated"] or '—') + '</div>' +
            '</div></div>' +
        '</div>' if methodology_meta["version"] or methodology_meta["framework"] else ''}

        {methodology_html}
    </div>

</div>

<script>
// Clock update
function updateClock() {{
    const now = new Date();
    document.getElementById('clock').textContent = now.toLocaleTimeString('en-US', {{ hour: '2-digit', minute: '2-digit' }});
}}
updateClock();
setInterval(updateClock, 1000);

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

// Thesis filters
function filterTheses() {{
    const status = document.getElementById('filter-status').value;
    const type = document.getElementById('filter-type').value;
    let visible = 0;
    document.querySelectorAll('.thesis-row').forEach(row => {{
        const matchStatus = status === 'all' || row.dataset.status === status;
        const matchType = type === 'all' || row.dataset.type === type;
        row.style.display = (matchStatus && matchType) ? '' : 'none';
        if (matchStatus && matchType) visible++;
    }});
    document.getElementById('thesis-count').textContent = visible + ' thes' + (visible === 1 ? 'is' : 'es');
}}

// Thesis index table navigation
function showThesis(idx) {{
    document.querySelectorAll('.thesis-row').forEach(r => r.classList.remove('selected'));
    const row = document.querySelector('.thesis-row[data-idx="' + idx + '"]');
    if (row) row.classList.add('selected');
    document.querySelectorAll('.thesis-detail').forEach(t => t.style.display = 'none');
    document.getElementById('thesis-' + idx).style.display = 'block';

    // Populate detail panel header from row data attributes
    if (row) {{
        const name = row.dataset.cleanName || '';
        const status = row.dataset.thesisStatus || '';
        const ttype = row.dataset.thesisType || '';
        const conviction = row.dataset.conviction || '';
        const horizon = row.dataset.horizon || '';
        const generated = row.dataset.generated || '';
        const updated = row.dataset.updated || '';
        const titleEl = document.getElementById('detail-title');
        const metaEl = document.getElementById('detail-meta');
        const datesEl = document.getElementById('detail-dates');
        if (titleEl) titleEl.textContent = name.toUpperCase();
        if (datesEl) {{
            let dateStr = '';
            if (generated) dateStr += 'Created ' + generated;
            if (updated && updated !== generated) dateStr += (dateStr ? '  ·  ' : '') + 'Updated ' + updated;
            datesEl.textContent = dateStr;
        }}
        if (metaEl) {{
            const sBadge = status === 'ACTIVE'
                ? '<span class="badge badge-active" title="' + status + '">ACTIVE</span>'
                : '<span class="badge badge-draft" title="' + status + '">DRAFT</span>';
            const tBadge = ttype === 'STRUCTURAL'
                ? '<span class="badge badge-structural" title="' + ttype + '">STRUCTURAL</span>'
                : '<span class="badge badge-tactical" title="' + ttype + '">TACTICAL</span>';
            const convColor = conviction === 'High' ? 'var(--green)' : conviction === 'Medium' ? 'var(--amber)' : conviction === 'Low' ? 'var(--red)' : 'var(--text-muted)';
            const convSpan = conviction ? ' <span style="color: ' + convColor + '; font-size: 10px; font-weight: 500; margin-left: 6px;">' + conviction + ' conviction</span>' : '';
            const horizonSpan = horizon && horizon !== '—' ? ' <span style="color: var(--text-muted); font-size: 10px; margin-left: 6px;">· ' + horizon + '</span>' : '';
            metaEl.innerHTML = sBadge + ' ' + tBadge + convSpan + horizonSpan;
        }}
    }}
}}

// Regime Charts (Overview and main)
function renderRegimeChart(canvasId) {{
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    new Chart(canvas.getContext('2d'), {{
        type: 'scatter',
        data: {{
            datasets: [
                {{
                    label: 'This Week',
                    data: [{{ x: {regime_data['x']}, y: {regime_data['y']} }}],
                    backgroundColor: '#3b82f6',
                    borderColor: '#3b82f6',
                    pointRadius: 12,
                    pointHoverRadius: 14,
                    pointStyle: 'circle',
                }},
                {{
                    label: '6-Month Forecast ({regime_data["forecast_6m"]})',
                    data: {regime_data["forecast_6m"] != "Unknown" and f'[{{ x: {regime_data["forecast_6m_x"]}, y: {regime_data["forecast_6m_y"]} }}]' or '[]'},
                    backgroundColor: 'rgba(251, 191, 36, 0.6)',
                    borderColor: '#f59e0b',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 10,
                    pointHoverRadius: 12,
                    pointStyle: 'triangle',
                }},
                {{
                    label: 'Historical Trail',
                    data: [{history_points}],
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    borderColor: 'rgba(59, 130, 246, 0.3)',
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
                    backgroundColor: 'rgba(239, 68, 68, 0.4)',
                    borderColor: '#ef4444',
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
                        color: '#a0a0a0',
                        font: {{ size: 11, weight: '600' }}
                    }},
                    grid: {{
                        color: 'rgba(255,255,255,0.05)',
                        drawTicks: false,
                    }},
                    ticks: {{
                        callback: function(v) {{
                            if (v === -1) return 'Falling';
                            if (v === 0) return '';
                            if (v === 1) return 'Rising';
                            return '';
                        }},
                        color: '#a0a0a0',
                        font: {{ size: 10 }}
                    }},
                    border: {{ color: 'rgba(255,255,255,0.08)' }}
                }},
                y: {{
                    min: -1.2,
                    max: 1.2,
                    title: {{
                        display: true,
                        text: '↑ Inflation Direction',
                        color: '#a0a0a0',
                        font: {{ size: 11, weight: '600' }}
                    }},
                    grid: {{
                        color: 'rgba(255,255,255,0.05)',
                        drawTicks: false,
                    }},
                    ticks: {{
                        callback: function(v) {{
                            if (v === -1) return 'Falling';
                            if (v === 0) return '';
                            if (v === 1) return 'Rising';
                            return '';
                        }},
                        color: '#a0a0a0',
                        font: {{ size: 10 }}
                    }},
                    border: {{ color: 'rgba(255,255,255,0.08)' }}
                }}
            }},
            plugins: {{
                legend: {{ display: true, labels: {{ color: '#a0a0a0', font: {{ size: 11 }} }} }},
                tooltip: {{
                    callbacks: {{
                        label: function(ctx) {{
                            const trailWeeks = {trail_week_labels};
                            if (ctx.dataset.label === 'Historical Trail' && trailWeeks[ctx.dataIndex]) {{
                                return trailWeeks[ctx.dataIndex] + ' (' + ctx.parsed.x.toFixed(2) + ', ' + ctx.parsed.y.toFixed(2) + ')';
                            }}
                            return ctx.dataset.label + ' (' + ctx.parsed.x.toFixed(2) + ', ' + ctx.parsed.y.toFixed(2) + ')';
                        }}
                    }}
                }}
            }}
        }},
        plugins: [{{
            id: 'quadrantLabels',
            afterDraw: function(chart) {{
                const {{ ctx, chartArea }} = chart;
                const midX = (chartArea.left + chartArea.right) / 2;
                const midY = (chartArea.top + chartArea.bottom) / 2;

                ctx.save();
                ctx.font = '600 12px "JetBrains Mono", monospace';
                ctx.textAlign = 'center';
                ctx.globalAlpha = 0.15;

                ctx.fillStyle = '#22c55e';
                ctx.fillText('GOLDILOCKS', (midX + chartArea.right) / 2, (midY + chartArea.bottom) / 2);

                ctx.fillStyle = '#f59e0b';
                ctx.fillText('OVERHEATING', (midX + chartArea.right) / 2, (chartArea.top + midY) / 2);

                ctx.fillStyle = '#3b82f6';
                ctx.fillText('DISINFLATION', (chartArea.left + midX) / 2, (midY + chartArea.bottom) / 2);

                ctx.fillStyle = '#ef4444';
                ctx.fillText('STAGFLATION', (chartArea.left + midX) / 2, (chartArea.top + midY) / 2);

                ctx.globalAlpha = 0.1;
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
}}

// Render both regime charts
renderRegimeChart('regimeChart');
renderRegimeChart('regimeChartOverview');

// Thesis-specific charts
const thesisChartSpecs = __THESIS_CHART_SPECS_PLACEHOLDER__;
Object.entries(thesisChartSpecs).forEach(([key, spec]) => {{
    const canvas = document.querySelector(`canvas[data-thesis-key="${{key}}"]`);
    if (!canvas || canvas._chartRendered) return;

    if (spec.data && spec.data.datasets) {{
        const chartConfig = {{
            type: spec.type || 'line',
            data: spec.data,
            options: spec.options || {{
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2.5,
                scales: {{
                    x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#a0a0a0', maxTicksLimit: 10 }} }},
                    y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#a0a0a0' }} }},
                }},
                plugins: {{ legend: {{ labels: {{ color: '#a0a0a0' }} }} }},
            }},
        }};
        if (spec.options) {{
            const s = chartConfig.options.scales = chartConfig.options.scales || {{}};
            ['x','y','y1'].forEach(axis => {{
                if (s[axis]) {{
                    s[axis].grid = s[axis].grid || {{}};
                    s[axis].grid.color = s[axis].grid.color || 'rgba(255,255,255,0.05)';
                    s[axis].ticks = s[axis].ticks || {{}};
                    s[axis].ticks.color = s[axis].ticks.color || '#a0a0a0';
                }}
            }});
            const p = chartConfig.options.plugins = chartConfig.options.plugins || {{}};
            p.legend = p.legend || {{}};
            p.legend.labels = p.legend.labels || {{}};
            p.legend.labels.color = p.legend.labels.color || '#a0a0a0';
        }}
        new Chart(canvas.getContext('2d'), chartConfig);
        canvas._chartRendered = true;
    }} else if (spec.datasets) {{
        const datasets = spec.datasets.map((ds, idx) => ({{
            label: ds.label || 'Series',
            data: ds.data || [],
            borderColor: ds.color || ['#3b82f6', '#22c55e', '#ef4444', '#f59e0b'][idx % 4],
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
                        x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#a0a0a0', maxTicksLimit: 10 }} }},
                        y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#a0a0a0' }} }},
                    }},
                    plugins: {{ legend: {{ labels: {{ color: '#a0a0a0' }} }} }},
                }},
            }});
            canvas._chartRendered = true;
        }}
    }}
}});

// Hide raw Chart.js spec code blocks
document.querySelectorAll('.thesis-detail .code-block').forEach(block => {{
    const text = block.textContent || '';
    if (text.includes('"type"') && text.includes('"datasets"') && (text.includes('"borderColor"') || text.includes('"chart_type"'))) {{
        block.style.display = 'none';
    }}
}});
document.querySelectorAll('.thesis-detail h3, .thesis-detail h4').forEach(header => {{
    const text = (header.textContent || '').toLowerCase();
    if (text.includes('chart specification') || text.includes('chart spec')) {{
        const next = header.nextElementSibling;
        if (next && next.style.display === 'none') {{
            header.style.display = 'none';
        }}
    }}
}});

// Thesis sub-tabs
function showThesisSubtab(subtab) {{
    document.querySelectorAll('.thesis-subtab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.thesis-subtabs button').forEach(b => b.classList.remove('active'));
    document.getElementById('thesis-sub-' + subtab).classList.add('active');
    event.target.classList.add('active');
}}

// View toggle (Table vs Timeline)
let timelineExpanded = false;
function toggleThesisView(view) {{
    document.querySelectorAll('.view-toggle button').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    const tableView = document.getElementById('thesis-table-view');
    const timelineView = document.getElementById('thesis-timeline-view');
    const gridView = document.getElementById('thesis-grid-view');
    const detailPanel = document.getElementById('thesis-detail-panel');
    if (view === 'timeline') {{
        tableView.style.display = 'none';
        timelineView.classList.add('active');
        renderTimeline();
    }} else {{
        tableView.style.display = '';
        timelineView.classList.remove('active');
        // Collapse back when switching to table
        timelineExpanded = false;
        gridView.style.gridTemplateColumns = '';
        gridView.style.transition = '';
        if (detailPanel) detailPanel.style.display = '';
    }}
}}

function toggleTimelineExpand() {{
    const gridView = document.getElementById('thesis-grid-view');
    const detailPanel = document.getElementById('thesis-detail-panel');
    const timelineView = document.getElementById('thesis-timeline-view');
    timelineExpanded = !timelineExpanded;
    gridView.style.transition = 'grid-template-columns 0.3s ease';
    if (timelineExpanded) {{
        gridView.style.gridTemplateColumns = '1fr';
        if (detailPanel) {{
            detailPanel.style.opacity = '0';
            detailPanel.style.transition = 'opacity 0.2s ease';
            setTimeout(() => {{ detailPanel.style.display = 'none'; }}, 200);
        }}
        timelineView.querySelector('.expand-hint').textContent = '⤡ Click to collapse';
    }} else {{
        gridView.style.gridTemplateColumns = '';
        if (detailPanel) {{
            detailPanel.style.display = '';
            detailPanel.style.opacity = '0';
            setTimeout(() => {{
                detailPanel.style.transition = 'opacity 0.2s ease';
                detailPanel.style.opacity = '1';
            }}, 50);
        }}
        timelineView.querySelector('.expand-hint').textContent = '⤢ Click to expand';
    }}
    // Re-render chart at new size
    timelineRendered = false;
    const canvas = document.getElementById('timelineChart');
    const parent = canvas.parentNode;
    parent.removeChild(canvas);
    const newCanvas = document.createElement('canvas');
    newCanvas.id = 'timelineChart';
    parent.insertBefore(newCanvas, parent.querySelector('.expand-hint'));
    renderTimeline();
}}

// Timeline
let timelineRendered = false;
function renderTimeline() {{
    if (timelineRendered) return;
    timelineRendered = true;
    const data = __TIMELINE_DATA_PLACEHOLDER__;
    if (!data.length) return;

    const canvas = document.getElementById('timelineChart');
    if (!canvas) return;

    // Set canvas height dynamically based on thesis count
    // Extra height per row to accommodate wrapped labels
    const rowHeight = 44;
    const chartHeight = Math.max(200, data.length * rowHeight + 80);
    canvas.style.height = chartHeight + 'px';

    const today = new Date();
    const labels = [];
    const barData = [];
    const bgColors = [];
    const borderColors = [];

    data.sort((a, b) => (a.start || '').localeCompare(b.start || ''));

    data.forEach(item => {{
        labels.push(item.name);
        let startDate = item.start ? new Date(item.start) : today;
        let endMs = startDate.getTime() + (item.horizonWeeks * 7 * 24 * 60 * 60 * 1000);
        let endDate = new Date(endMs);

        barData.push([startDate.getTime(), endDate.getTime()]);
        bgColors.push(item.color + '33');
        borderColors.push(item.color);
    }});

    const allTimes = barData.flat();
    const minTime = Math.min(...allTimes, today.getTime());
    const maxTime = Math.max(...allTimes, today.getTime());
    const range = maxTime - minTime;
    // Add some padding before the earliest bar so labels aren't clipped
    const padLeft = range * 0.02;
    const padRight = range * 0.05;

    // Build quarter tick positions: Q1 starts Jan 1, Q2 Apr 1, Q3 Jul 1, Q4 Oct 1
    // Cap at ~8 quarters to avoid label overcrowding
    const maxQuarters = 8;
    const quarterTicks = [];
    const qStart = new Date(new Date(minTime - padLeft).getFullYear(), Math.floor(new Date(minTime - padLeft).getMonth() / 3) * 3, 1);
    const qEnd = new Date(maxTime + padRight);
    let qDate = new Date(qStart);
    while (qDate <= qEnd) {{
        quarterTicks.push(qDate.getTime());
        qDate = new Date(qDate.getFullYear(), qDate.getMonth() + 3, 1);
    }}
    // Add one more quarter past the end for breathing room
    quarterTicks.push(qDate.getTime());

    // If too many quarters, thin out to show every Nth quarter
    let displayTicks = quarterTicks;
    if (quarterTicks.length > maxQuarters) {{
        const step = Math.ceil(quarterTicks.length / maxQuarters);
        displayTicks = quarterTicks.filter((_, i) => i % step === 0);
        // Always include the last tick
        if (displayTicks[displayTicks.length - 1] !== quarterTicks[quarterTicks.length - 1]) {{
            displayTicks.push(quarterTicks[quarterTicks.length - 1]);
        }}
    }}

    function quarterLabel(ts) {{
        const d = new Date(ts);
        const q = Math.floor(d.getMonth() / 3) + 1;
        const yr = String(d.getFullYear()).slice(-2);
        return 'Q' + q + '-' + yr;
    }}

    new Chart(canvas.getContext('2d'), {{
        type: 'bar',
        data: {{
            labels: labels,
            datasets: [{{
                label: 'Thesis Period',
                data: barData,
                backgroundColor: bgColors,
                borderColor: borderColors,
                borderWidth: 1,
                borderSkipped: false,
                barPercentage: 0.7,
            }}]
        }},
        options: {{
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            layout: {{
                padding: {{ top: 20 }}
            }},
            scales: {{
                x: {{
                    type: 'linear',
                    min: minTime - padLeft,
                    max: Math.max(maxTime + padRight, displayTicks[displayTicks.length - 1]),
                    afterBuildTicks: function(scale) {{
                        scale.ticks = displayTicks.map(t => ({{ value: t }}));
                    }},
                    ticks: {{
                        callback: function(v) {{
                            return quarterLabel(v);
                        }},
                        color: '#a0a0a0',
                        font: {{ size: 10, family: '"JetBrains Mono", monospace' }},
                        autoSkip: false,
                        maxRotation: 0,
                        minRotation: 0,
                    }},
                    grid: {{ color: 'rgba(255,255,255,0.05)' }},
                }},
                y: {{
                    ticks: {{
                        color: '#e4e4e7',
                        font: {{ size: 11 }},
                        // Wrap long thesis names by splitting into multiple lines
                        callback: function(value, index) {{
                            const label = this.getLabelForValue(value);
                            if (!label) return label;
                            // Wrap at ~20 chars per line
                            const maxWidth = 22;
                            if (label.length <= maxWidth) return label;
                            const words = label.split(' ');
                            const lines = [];
                            let current = '';
                            words.forEach(w => {{
                                if ((current + ' ' + w).trim().length > maxWidth && current) {{
                                    lines.push(current.trim());
                                    current = w;
                                }} else {{
                                    current = current ? current + ' ' + w : w;
                                }}
                            }});
                            if (current) lines.push(current.trim());
                            return lines;
                        }},
                    }},
                    grid: {{ display: false }},
                }}
            }},
            plugins: {{
                legend: {{ display: false }},
                tooltip: {{
                    callbacks: {{
                        label: function(ctx) {{
                            const [start, end] = ctx.raw;
                            const s = new Date(start).toLocaleDateString('en-US', {{ month: 'short', day: 'numeric', year: 'numeric' }});
                            const e = new Date(end).toLocaleDateString('en-US', {{ month: 'short', day: 'numeric', year: 'numeric' }});
                            return s + ' → ' + e;
                        }}
                    }}
                }}
            }},
        }},
        plugins: [{{
            id: 'todayLine',
            afterDraw: function(chart) {{
                const {{ ctx, chartArea, scales }} = chart;
                const xPos = scales.x.getPixelForValue(today.getTime());
                if (xPos >= chartArea.left && xPos <= chartArea.right) {{
                    ctx.save();
                    ctx.strokeStyle = '#ef4444';
                    ctx.lineWidth = 2;
                    ctx.setLineDash([4, 4]);
                    ctx.beginPath();
                    ctx.moveTo(xPos, chartArea.top);
                    ctx.lineTo(xPos, chartArea.bottom);
                    ctx.stroke();
                    ctx.fillStyle = '#ef4444';
                    ctx.font = '10px "JetBrains Mono", monospace';
                    ctx.textAlign = 'center';
                    ctx.fillText('Today', xPos, chartArea.top - 6);
                    ctx.restore();
                }}
            }}
        }}]
    }});
}}

// Initialize first thesis detail header on load
if (document.querySelector('.thesis-row[data-idx="0"]')) {{
    showThesis(0);
}}
</script>

</body>
</html>"""

    # Replace placeholders with actual JSON
    html = html.replace('__THESIS_CHART_SPECS_PLACEHOLDER__', thesis_chart_specs_raw)
    html = html.replace('__TIMELINE_DATA_PLACEHOLDER__', timeline_data_json)

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
    parser.add_argument("--plugin-root", default=None, help="Plugin root directory (for locating methodology.md and skill files)")
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

    # Read thesis files — active/draft and closed separately
    theses = []
    closed_theses = []
    theses_dir = output_dir / "theses" / "active"
    if theses_dir.exists():
        for f in sorted(theses_dir.glob("*.md")):
            theses.append((f.name, f.read_text(encoding="utf-8")))
    closed_dir = output_dir / "theses" / "closed"
    if closed_dir.exists():
        for f in sorted(closed_dir.glob("*.md")):
            closed_theses.append((f.name, f.read_text(encoding="utf-8")))

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

    # Read methodology for the About tab from plugin root (read-only cache is fine)
    methodology = ""
    if args.plugin_root:
        methodology = read_file(Path(args.plugin_root) / "skills" / "macro-advisor" / "references" / "methodology.md")

    # Generate HTML — pass all weeks data, regime history, skills, methodology
    html = generate_html(
        args.week, briefing, theses, improvement, synthesis, snapshot,
        all_weeks=all_weeks,
        all_weeks_data=all_weeks_data,
        regime_history=regime_history,
        skill_files=skill_files,
        methodology=methodology,
        output_dir=output_dir,
        closed_theses=closed_theses,
    )

    # Write output
    out_path = Path(args.out)
    out_path.write_text(html, encoding="utf-8")
    print(f"Dashboard generated: {out_path} ({len(html):,} bytes)")
    print(f"Weeks available: {len(all_weeks)} ({', '.join(all_weeks)})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
