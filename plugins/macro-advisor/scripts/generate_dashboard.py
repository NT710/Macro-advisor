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


def _table_col_widths(header_names):
    """Return a list of CSS width strings for known thesis table layouts.
    header_names should be lowercased. Returns None for unknown layouts."""
    n = len(header_names)
    h = tuple(header_names)

    # (#, Assumption) — 2 cols
    if n == 2 and '#' in h:
        return ['5%', '95%']
    # (#, Assumption, Status) — 3 cols
    if n == 3 and '#' in h and 'status' in h:
        return ['5%', '75%', '20%']
    # (#, Assumption, Testable By) — 3 cols
    if n == 3 and '#' in h and 'testable by' in h:
        return ['5%', '60%', '35%']
    # (#, Assumption, Testable By, Status) — 4 cols
    if n == 4 and '#' in h and 'testable by' in h:
        return ['5%', '50%', '30%', '15%']
    # (#, Link, Quantified) — causal chain
    if n == 3 and '#' in h and 'link' in h:
        return ['5%', '55%', '40%']
    # (Binding Constraint, Quantified, Source) — structural foundation
    if n == 3 and 'binding constraint' in h:
        return ['35%', '35%', '30%']
    # (Order, ETF, Size, Rationale) — ETF expression
    if n == 4 and 'order' in h and 'etf' in h:
        return ['12%', '28%', '20%', '40%']
    # (What, Direction, ETFs, Why) — cross-asset without timing
    if n == 4 and 'what' in h and 'direction' in h:
        return ['18%', '12%', '18%', '52%']
    # (What, Direction, ETFs, Why, Timing) — cross-asset with timing
    if n == 5 and 'what' in h and 'timing' in h:
        return ['16%', '10%', '16%', '38%', '20%']
    return None


def md_to_html(md_text):
    """Simple markdown to HTML conversion — handles headers, bold, tables, lists, code blocks."""
    # Strip YAML meta blocks (---\nmeta:\n...\n--- or front matter at top of file)
    # These are internal quality metadata and should never render in the dashboard.
    md_text = re.sub(r'(?m)^---\s*\nmeta:.*?^---\s*$', '', md_text, flags=re.DOTALL | re.MULTILINE)
    # Also strip YAML front matter at very start of file (e.g. skill descriptions)
    if md_text.lstrip().startswith('---'):
        md_text = re.sub(r'\A\s*---.*?^---\s*$', '', md_text, count=1, flags=re.DOTALL | re.MULTILINE)
    # Also strip meta blocks wrapped in code fences (```yaml\nmeta:\n...\n```)
    md_text = re.sub(r'(?m)^```(?:yaml|yml)?\s*\nmeta:.*?^```\s*$', '', md_text, flags=re.DOTALL | re.MULTILINE)
    # Strip standalone meta: blocks not wrapped in any delimiter (bare meta blocks at end of file)
    md_text = re.sub(r'(?m)^meta:\n(?:  .+\n)+', '', md_text)
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
                # Assign column widths based on header names
                col_widths = _table_col_widths([c.lower() for c in cells])
                if col_widths:
                    html_lines.append("<thead><tr>" + "".join(
                        f'<th style="width:{w}">{c}</th>' for c, w in zip(cells, col_widths)
                    ) + "</tr></thead><tbody>")
                else:
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
    # Green statuses
    if s_upper == 'INTACT':
        return f'<span style="color: var(--green);">{status}</span>'
    # Amber statuses
    elif s_upper in ('UNDER PRESSURE', 'DEVELOPING', 'WATCH', 'WEAKENING', 'MONITORING'):
        return f'<span style="color: var(--amber);">{status}</span>'
    # Red statuses
    elif s_upper in ('BROKEN', 'INVALIDATED', 'FAILED'):
        return f'<span style="color: var(--red);">{status}</span>'
    # Blue/accent for strengthening
    elif s_upper == 'STRENGTHENING':
        return f'<span style="color: var(--accent);">{status}</span>'
    return status


def _extract_status(text):
    """Extract and remove status marker from text.
    Returns (cleaned_text, status_string).
    Searches longest-first to avoid partial matches (e.g. 'UNDER PRESSURE' before 'INTACT')."""
    for s in ['UNDER PRESSURE', 'STRENGTHENING', 'INVALIDATED', 'DEVELOPING', 'MONITORING',
              'WEAKENING', 'INTACT', 'BROKEN', 'FAILED', 'WATCH']:
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


def format_thesis_from_json(sidecar):
    """Render thesis HTML directly from a JSON sidecar — no markdown parsing needed.

    Produces the same visual output as format_thesis_html() but reads structured data
    from the sidecar dict instead of parsing markdown prose. This eliminates the class
    of parsing bugs (em-dash splits, missing status keywords, bold marker confusion)
    that affect the markdown parser.

    Supports both old and new key names with fallback to old keys for backward compatibility.

    Returns markdown-like text that md_to_html() can render (same as format_thesis_html).
    """
    lines = []

    # Plain English Summary
    summary = sidecar.get("summary", sidecar.get("plain_english_summary"))
    if summary:
        lines.append('## Summary')
        lines.append('')
        lines.append(summary)
        lines.append('')

    # The Bet (formerly Claim)
    bet = sidecar.get("the_bet", sidecar.get("claim"))
    if bet:
        lines.append('## The Bet')
        lines.append('')
        lines.append(bet)
        lines.append('')

    # What Has To Stay True (formerly Assumptions)
    assumptions = sidecar.get("what_has_to_stay_true", sidecar.get("assumptions", []))
    if assumptions:
        has_testable = any(a.get("testable_by") for a in assumptions)
        has_status = any(a.get("status") for a in assumptions)

        if has_testable:
            lines.append('## What Has To Stay True')
            lines.append('')
            if has_status:
                lines.append('| # | Assumption | Testable By | Status |')
                lines.append('|---|-----------|-------------|--------|')
                for n, a in enumerate(assumptions, 1):
                    status_html = _status_html(a.get("status", ""))
                    lines.append(f'| {n} | {a.get("text", "")} | {a.get("testable_by", "")} | {status_html} |')
            else:
                lines.append('| # | Assumption | Testable By |')
                lines.append('|---|-----------|-------------|')
                for n, a in enumerate(assumptions, 1):
                    lines.append(f'| {n} | {a.get("text", "")} | {a.get("testable_by", "")} |')
        else:
            lines.append('## What Has To Stay True')
            lines.append('')
            if has_status:
                lines.append('| # | Assumption | Status |')
                lines.append('|---|-----------|--------|')
                for n, a in enumerate(assumptions, 1):
                    status_html = _status_html(a.get("status", ""))
                    lines.append(f'| {n} | {a.get("text", "")} | {status_html} |')
            else:
                lines.append('| # | Assumption |')
                lines.append('|---|-----------|')
                for n, a in enumerate(assumptions, 1):
                    lines.append(f'| {n} | {a.get("text", "")} |')
        lines.append('')

    # Mechanism (formerly Causal Chain)
    chain = sidecar.get("mechanism", sidecar.get("causal_chain", []))
    if chain:
        lines.append('## Mechanism')
        lines.append('')
        lines.append('| # | Link | Quantified |')
        lines.append('|---|------|-----------|')
        for step in chain:
            n = step.get("step", "")
            link = step.get("link", "")
            quant = step.get("quantified", "")
            source = step.get("source", "")
            if source:
                quant = f'{quant} ({source})' if quant else source
            lines.append(f'| {n} | **{link}** | {quant} |')
        lines.append('')

    # What Can't Change (formerly Structural Foundation)
    foundation = sidecar.get("what_cant_change", sidecar.get("structural_foundation"))
    if foundation:
        lines.append('## What Can\'t Change')
        lines.append('')
        lines.append('| Binding Constraint | Quantified | Source |')
        lines.append('|-------------------|-----------|--------|')
        for f in foundation:
            lines.append(f'| {f.get("constraint", "")} | {f.get("quantified", "")} | {f.get("source", "")} |')
        lines.append('')

    # Where The Market Stands (formerly Consensus View)
    market_view = sidecar.get("where_the_market_stands", sidecar.get("consensus_view"))
    if market_view:
        lines.append('## Where The Market Stands')
        lines.append('')
        lines.append(market_view)
        lines.append('')

    # The Trade (contains what_to_buy, when_to_buy_more, when_to_get_out, how_long)
    trade = sidecar.get("the_trade", {})

    # What to buy (formerly ETF Expression)
    etf = trade.get("what_to_buy", sidecar.get("etf_expression"))
    if etf and isinstance(etf, dict):
        lines.append('## What to buy')
        lines.append('')
        lines.append('| Order | ETF | Size | Rationale |')
        lines.append('|-------|-----|------|-----------|')
        for order_key, order_label in [("first_order", "First-order"), ("second_order", "Second-order"),
                                        ("third_order", "Third-order"), ("reduce_avoid", "Reduce/Avoid")]:
            for item in etf.get(order_key, []):
                ticker = item.get("ticker", item.get("etf", ""))
                size = item.get("size", "—") if order_key != "reduce_avoid" else "—"
                rationale = item.get("rationale", "")
                lines.append(f'| {order_label} | {ticker} | {size} | {rationale} |')
        lines.append('')

    # Conviction
    if sidecar.get("conviction"):
        lines.append('## Conviction')
        lines.append('')
        lines.append(sidecar["conviction"])
        lines.append('')

    # When to get out (formerly Kill Switch)
    kill_switch = trade.get("when_to_get_out", sidecar.get("kill_switch"))
    if kill_switch:
        lines.append(f'<div class="kill-switch-card">')
        lines.append(f'<strong>KILL SWITCH:</strong> {kill_switch}')
        lines.append(f'</div>')
        lines.append('')

    # When to buy more (formerly Trigger to Add)
    trigger = trade.get("when_to_buy_more", sidecar.get("trigger_to_add"))
    if trigger:
        lines.append('## When to buy more')
        lines.append('')
        lines.append(trigger)
        lines.append('')

    # What Could Break It (formerly Contrarian Stress Test)
    stress = sidecar.get("what_could_break_it", sidecar.get("contrarian_stress_test"))
    if stress and isinstance(stress, dict):
        lines.append('## What Could Break It')
        lines.append('')
        if stress.get("strongest_counter"):
            lines.append(f'**Strongest counter-argument:** {stress["strongest_counter"]}')
            lines.append('')
        for risk in stress.get("key_risks", []):
            lines.append(f'- {risk.get("risk", "")} (Probability: {risk.get("probability", "?")})')
        if stress.get("post_test_conviction"):
            lines.append('')
            lines.append(f'**Conviction after stress test:** {stress["post_test_conviction"]}')
        lines.append('')

    return '\n'.join(lines)


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

        # --- What Has To Stay True (formerly What We Have To Believe): numbered list → table ---
        if _match_section(lower, 'what has to stay true') or _match_section(lower, 'what we have to believe'):
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

        # --- What Can't Change (formerly Structural Foundation): prose + bullet list → table ---
        if _match_section(lower, 'what can\'t change') or _match_section(lower, 'structural foundation'):
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
            # Convert bullets to table (skip blank lines between bullets)
            if i < len(lines) and lines[i].strip().startswith('- '):
                output_lines.append('| Binding Constraint | Quantified | Source |')
                output_lines.append('|-------------------|-----------|--------|')
                while i < len(lines):
                    l = lines[i].strip()
                    if not l:
                        # Blank line — peek ahead for more bullets or section boundary
                        peek = _peek_past_blanks(lines, i + 1)
                        if peek < len(lines) and lines[peek].strip().startswith('- '):
                            i += 1
                            continue
                        break
                    if not l.startswith('- '):
                        break
                    text = l[2:].strip()
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

        # --- Mechanism (formerly Quantified Causal Chain): numbered list → table ---
        if _match_section(lower, 'mechanism') or _match_section(lower, 'quantified causal chain'):
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
                    # Split on bold markers: **Bold claim.** Rest is quantified
                    bold_match = re.match(r'\*\*(.+?)\*\*\s*(.*)', text, re.DOTALL)
                    if bold_match:
                        link = bold_match.group(1).strip()
                        quant = bold_match.group(2).strip()
                        # Strip leading dash/emdash from quantified if present
                        quant = re.sub(r'^[—–\-]\s*', '', quant)
                        items.append((f'**{link}**', quant))
                    else:
                        # Fallback: no bold markers, keep full text as link
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

        # --- ETF Expression / What to buy: bullet list with order labels → table ---
        # Matches: ### What to buy (current), **ETF Expression:**, ## ETF Expression, *Expression:*
        if (_match_section(lower, 'what to buy') or _match_section(lower, 'etf expression')
                or lower == '*expression:*' or lower.startswith('## etf expression')):
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
            # Convert order bullets to table (skip blank lines between bullets)
            if i < len(lines) and lines[i].strip().startswith('- '):
                output_lines.append('| Order | ETF | Size | Rationale |')
                output_lines.append('|-------|-----|------|-----------|')
                while i < len(lines):
                    l = lines[i].strip()
                    if not l:
                        peek = _peek_past_blanks(lines, i + 1)
                        if peek < len(lines) and lines[peek].strip().startswith('- '):
                            i += 1
                            continue
                        break
                    if not l.startswith('- '):
                        break
                    text = l[2:].strip()
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
                'what to buy', 'etf expression',
                'when to buy more', 'trigger to add',
                'when to get out', 'kill switch',
                'how long', 'time horizon',
                'when to buy', 'entry timing',
                'where the market stands', 'consensus view',
                'what could break it', 'contrarian stress-test',
                'what has to stay true', 'what we have to believe', 'assumptions',
                'external views', 'analyst cross-references',
                'summary', 'plain english summary',
                'the bet', 'claim',
                'mechanism', 'structural foundation',
                'quantified causal chain', 'monitoring cadence',
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
        # Current names + old names for migration compatibility
        prose_sections = [
            'summary:', 'summary',
            'plain english summary:', 'plain english summary',
            'the bet:', 'the bet',
            'claim:', 'claim',
            'where the market stands:', 'where the market stands',
            'consensus view:', 'consensus view',
            'what could break it:', 'what could break it',
            'contrarian stress-test:', 'contrarian stress-test',
            'when to buy more:', 'when to buy more',
            'trigger to add:', 'trigger to add',
            'how long:', 'how long',
            'time horizon:', 'time horizon',
            'when to buy:', 'when to buy',
            'entry timing:', 'entry timing',
            'when to get out:', 'when to get out',
            'kill switch:', 'kill switch',
            'etf expression:', 'etf expression',
            'monitoring cadence:', 'monitoring cadence',
            'external views', 'external views:',
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


def _regime_name_from_string(text):
    """Normalize a regime name from various formats to the canonical dashboard name."""
    lower = text.lower().strip()
    if "goldilocks" in lower:
        return "Goldilocks"
    elif "overheating" in lower:
        return "Overheating"
    elif "stagflation" in lower and "dis" not in lower:
        return "Stagflation"
    elif "disinflation" in lower or "slowdown" in lower:
        return "Disinflationary Slowdown"
    return "Unknown"


def _regime_coords(regime_name):
    """Map regime name to (x, y) chart coordinates."""
    coords = {
        "Goldilocks": (0.5, -0.5),
        "Overheating": (0.5, 0.5),
        "Disinflationary Slowdown": (-0.5, -0.5),
        "Stagflation": (-0.5, 0.5),
        "Unknown": (0, 0),
    }
    return coords.get(regime_name, (0, 0))


def _build_forecast_table_md(forecast_table):
    """Convert a forecast_table JSON array into a markdown table string."""
    if not forecast_table:
        return ""
    headers = ["Time Horizon", "Regime", "Growth Score", "Inflation Score", "Key Driver", "Confidence"]
    rows = []
    for row in forecast_table:
        rows.append(f'| **{row.get("time_horizon", "")}** | {row.get("regime", "")} | {row.get("growth_score", "")} | {row.get("inflation_score", "")} | {row.get("key_driver", "")} | {row.get("confidence", "")} |')
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "|" + "|".join(["---"] * len(headers)) + "|"
    return "\n".join([header_line, sep_line] + rows)


def parse_regime_from_json(json_data):
    """Extract regime data from the synthesis-data.json sidecar.

    Returns the same dict shape as parse_regime_from_synthesis for drop-in compatibility.
    """
    regime_block = json_data.get("regime", {})
    narrative_block = json_data.get("narrative", {})
    forecasts = json_data.get("forecasts", [])
    forecast_table = json_data.get("forecast_table", [])

    regime = _regime_name_from_string(regime_block.get("quadrant", "Unknown"))
    direction = regime_block.get("direction", "Stable")
    confidence = regime_block.get("confidence", "Medium")
    weeks_held = str(regime_block.get("weeks_held", "")) if regime_block.get("weeks_held") else ""

    # Use actual growth/inflation scores for chart coordinates when available
    gs = regime_block.get("growth_score")
    inf = regime_block.get("inflation_score")
    if gs is not None and inf is not None:
        x = max(-1.0, min(1.0, float(gs)))
        y = max(-1.0, min(1.0, float(inf)))
    else:
        x, y = _regime_coords(regime)

    # Extract 6-month and 12-month forecast regimes
    forecast_6m = "Unknown"
    forecast_12m = "Unknown"
    forecast_6m_x, forecast_6m_y = 0, 0
    forecast_12m_x, forecast_12m_y = 0, 0

    for fc in forecasts:
        horizon = fc.get("horizon", "").lower()
        fc_regime = _regime_name_from_string(fc.get("regime", "Unknown"))
        # Use midpoint of score ranges for chart positioning when available
        gs_range = fc.get("growth_score_range")
        inf_range = fc.get("inflation_score_range")
        if gs_range and inf_range and len(gs_range) == 2 and len(inf_range) == 2:
            fc_x = max(-1.0, min(1.0, (float(gs_range[0]) + float(gs_range[1])) / 2))
            fc_y = max(-1.0, min(1.0, (float(inf_range[0]) + float(inf_range[1])) / 2))
        else:
            fc_x, fc_y = _regime_coords(fc_regime)

        if "6" in horizon and forecast_6m == "Unknown":
            forecast_6m = fc_regime
            forecast_6m_x, forecast_6m_y = fc_x, fc_y
        elif "12" in horizon and forecast_12m == "Unknown":
            forecast_12m = fc_regime
            forecast_12m_x, forecast_12m_y = fc_x, fc_y

    # Build narrative text from JSON narrative block
    regime_narrative = narrative_block.get("regime_assessment", "") or ""

    # Build forecast section as markdown from the forecast_table array
    forecast_section_md = _build_forecast_table_md(forecast_table)

    # What changed
    what_changed_md = narrative_block.get("what_changed", "") or ""

    # Build the full narrative sections for the regime tab (liquidity, growth, policy, positioning)
    # These are rendered below the main narrative in the regime panel
    extra_narratives = []
    for key, label in [("liquidity_picture", "Liquidity"), ("growth_picture", "Growth"),
                       ("policy_picture", "Policy"), ("positioning_picture", "Positioning")]:
        text = narrative_block.get(key, "")
        if text:
            extra_narratives.append(f"**{label}:** {text}")
    if extra_narratives:
        regime_narrative = regime_narrative + "\n\n" + "\n\n".join(extra_narratives) if regime_narrative else "\n\n".join(extra_narratives)

    return {
        "regime": regime,
        "direction": direction,
        "confidence": confidence,
        "x": x,
        "y": y,
        "forecast_6m": forecast_6m,
        "forecast_6m_x": forecast_6m_x,
        "forecast_6m_y": forecast_6m_y,
        "forecast_12m": forecast_12m,
        "forecast_12m_x": forecast_12m_x,
        "forecast_12m_y": forecast_12m_y,
        "weeks_held": weeks_held,
        "regime_narrative": regime_narrative,
        "forecast_section_md": forecast_section_md,
        "what_changed_md": what_changed_md,
    }


def parse_regime_from_synthesis(synthesis_text):
    """Extract regime data including forecasts from synthesis markdown (legacy fallback).

    NOTE: This is the markdown-parsing fallback used when synthesis-data.json is not available.
    New weekly runs should produce synthesis-data.json which is read by parse_regime_from_json().
    """
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

        # Current regime — match "Current Quadrant" line, YAML front matter, or "Regime:" metadata
        if regime == "Unknown":
            if "current quadrant" in lower:
                regime = _regime_name_from_string(line)
            elif lower.strip().startswith("regime:") and "forecast" not in lower and "most likely" not in lower:
                regime = _regime_name_from_string(line)

        if "direction:" in lower and "forecast" not in lower and direction == "Stable":
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
            if "6 month" in lower or "6-month" in lower:
                current_forecast = "6m"
            elif "12 month" in lower or "12-month" in lower:
                current_forecast = "12m"

            if "most likely" in lower and "regime" in lower:
                target = current_forecast if 'current_forecast' in dir() else None
                if target == "6m" and forecast_6m == "Unknown":
                    forecast_6m = _regime_name_from_string(line)
                elif target == "12m" and forecast_12m == "Unknown":
                    forecast_12m = _regime_name_from_string(line)

    # --- Extract text sections for the regime tab ---
    weeks_held = ""
    regime_narrative = ""
    forecast_section_md = ""
    what_changed_md = ""

    # Extract weeks held — try multiple patterns
    for line in lines:
        lower = line.lower()
        if "weeks in current regime" in lower:
            match = re.search(r'\*{0,2}Weeks in current regime:?\*{0,2}\s*(.+)', line, re.IGNORECASE)
            if match:
                weeks_held = match.group(1).strip()
            break
        elif "regime duration" in lower:
            match = re.search(r'(\d+)\s*weeks?', lower)
            if match:
                weeks_held = match.group(1)
            break

    # Extract regime narrative from the Regime Assessment section
    # Look for "Regime Assessment" or "Regime Quadrant Assessment" headers
    in_regime_section = False
    metadata_lines_seen = 0
    narrative_lines = []
    for line in lines:
        lower = line.lower().strip()
        if lower.startswith("#") and ("regime assessment" in lower or "regime quadrant assessment" in lower):
            # Only match the TOP-LEVEL regime header (## level), not sub-sections like "Liquidity Regime Assessment"
            if "liquidity" in lower or "policy" in lower or "growth" in lower or "inflation" in lower:
                continue
            in_regime_section = True
            continue
        if in_regime_section:
            if lower.startswith("**") and ":" in lower:
                metadata_lines_seen += 1
                continue
            if metadata_lines_seen > 0 and not lower:
                continue
            # Stop at next ## header, ### sub-header, or horizontal rule
            if lower.startswith("#") or lower == "---":
                break
            if lower:
                narrative_lines.append(line)
                metadata_lines_seen = 99

    regime_narrative = " ".join(narrative_lines).strip()

    # If narrative is still empty, try the "Regime Edge Assessment" or "Quadrant Stability Analysis" block
    if not regime_narrative:
        in_stability = False
        stability_lines = []
        for line in lines:
            lower = line.lower().strip()
            if lower.startswith("#") and ("regime edge" in lower or "quadrant stability" in lower or "stability analysis" in lower):
                in_stability = True
                continue
            if in_stability:
                if lower.startswith("#") or lower == "---":
                    break
                if lower and not lower.startswith("**") and not lower.startswith("- "):
                    stability_lines.append(line.strip())
        if stability_lines:
            regime_narrative = " ".join(stability_lines).strip()

    # Last resort: try paragraph after "Regime Edge Assessment" bold block
    if not regime_narrative:
        in_coords = False
        blank_count = 0
        for line in lines:
            lower = line.lower().strip()
            if "coordinate-label consistency" in lower or "regime coordinates" in lower:
                in_coords = True
                blank_count = 0
                continue
            if in_coords:
                # Stop at section boundaries
                if lower.startswith("#") or lower == "---":
                    break
                # Skip metadata, list items, and table rows
                if lower and not lower.startswith("**") and not lower.startswith("-") and not lower.startswith("|") and not lower.startswith("✓") and not lower.startswith("✗"):
                    regime_narrative = line.strip()
                    break

    # Extract full Regime Forecast section as markdown
    in_forecast_text = False
    forecast_lines = []
    for line in lines:
        lower = line.lower().strip()
        if lower.startswith("#") and ("regime forecast" in lower or "6 and 12" in lower or "6-month and 12-month" in lower or "6 & 12" in lower):
            in_forecast_text = True
            continue
        if in_forecast_text:
            if lower.startswith("## ") and not lower.startswith("### "):
                if '12-month' in lower or '12 month' in lower or '6-month' in lower or '6 month' in lower or 'forecast' in lower:
                    forecast_lines.append(line)
                    continue
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

    # Use actual scores from YAML front matter if available
    x, y = _regime_coords(regime)
    yaml_match_gs = re.search(r'^growth_score:\s*([-\d.]+)', synthesis_text, re.MULTILINE)
    yaml_match_inf = re.search(r'^inflation_score:\s*([-\d.]+)', synthesis_text, re.MULTILINE)
    if yaml_match_gs and yaml_match_inf:
        x = max(-1.0, min(1.0, float(yaml_match_gs.group(1))))
        y = max(-1.0, min(1.0, float(yaml_match_inf.group(1))))

    f6x, f6y = _regime_coords(forecast_6m)
    f12x, f12y = _regime_coords(forecast_12m)

    # Try to extract weeks_held from YAML front matter if not found in markdown body
    if not weeks_held:
        yaml_weeks = re.search(r'^regime_weeks:\s*(\d+)', synthesis_text, re.MULTILINE)
        if yaml_weeks:
            weeks_held = yaml_weeks.group(1)

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

        # Detect cross-asset section start (flexible: ##, ###, or bold header)
        if ('cross-asset' in lower or 'cross asset' in lower) and lower.startswith('#'):
            in_cross_asset = True
            in_sector = False
            continue

        # Detect sector view sub-section (###, ##, or bold header within cross-asset)
        if (in_cross_asset or not in_sector) and 'sector view' in lower and (lower.startswith('#') or lower.startswith('**')):
            in_cross_asset = False
            in_sector = True
            continue

        # Stop at next major section (but not sub-headers about cross-asset/sector)
        if (in_cross_asset or in_sector) and line.strip().startswith('## ') and 'cross' not in lower and 'sector' not in lower:
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

    # Parse amendment evaluation table — try multiple header patterns
    # (different weeks use different headers: "Amendment Evaluation", "Amendment Tracker",
    #  "Summary of Amendment Decisions", "Amendment Proposals")
    amend_headers = ['amendment evaluation', 'amendment tracker',
                     'summary of amendment', 'amendment proposals',
                     'proposed amendments', 'proposed new amendments']
    in_amend = False
    amend_lines = []
    best_amend_lines = []  # keep the longest table found
    for line in lines:
        lower = line.lower().strip()
        if any(ah in lower for ah in amend_headers) and lower.startswith('#'):
            # If we were already collecting, save what we had
            if amend_lines and len(amend_lines) > len(best_amend_lines):
                best_amend_lines = amend_lines[:]
            in_amend = True
            amend_lines = []
            continue
        if in_amend:
            if line.strip().startswith('#') or line.strip() == '---':
                if amend_lines and len(amend_lines) > len(best_amend_lines):
                    best_amend_lines = amend_lines[:]
                in_amend = False
                continue
            if '|' in line:
                amend_lines.append(line)
    # Final check in case file ended while in_amend
    if amend_lines and len(amend_lines) > len(best_amend_lines):
        best_amend_lines = amend_lines
    if best_amend_lines:
        result["amendments"] = _parse_table_section(best_amend_lines)

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


def parse_horizon_map(md_text):
    """Parse Skill 14 Decade Horizon Strategic Map markdown into structured data.

    Returns dict with:
      - meta: run_date, run_type, mega_forces_mapped, blind_spots_identified, etc.
      - forces: list of dicts (name, direction, confidence, timeline, data_anchor,
                mechanism, cross_sector, last_quarter_change, causal_chains, stress_test)
      - blind_spots: list of dicts (name, priority, coverage_gap, investability, timeline,
                     recommendation, coverage_status)
      - summary_table: list of dicts (force, direction, confidence, timeline, consensus, mispricing)
    """
    if not md_text or not md_text.strip():
        return None

    result = {
        "meta": {},
        "forces": [],
        "blind_spots": [],
        "summary_table": [],
    }

    # ── Extract meta block (YAML in code fence at end) ──
    meta_match = re.search(r'```(?:yaml|yml)?\s*\n---\s*\nmeta:\s*\n(.*?)```', md_text, re.DOTALL)
    if meta_match:
        meta_text = meta_match.group(1)
        for line in meta_text.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('#'):
                key, _, val = line.partition(':')
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key in ('run_date', 'run_type', 'skill_version'):
                    result["meta"][key] = val
        # nested execution block
        exec_match = re.search(r'execution:\s*\n((?:\s{4,}.+\n)+)', meta_text)
        if exec_match:
            for line in exec_match.group(1).split('\n'):
                line = line.strip()
                if ':' in line:
                    k, _, v = line.partition(':')
                    k, v = k.strip(), v.strip()
                    try:
                        result["meta"][k] = int(v)
                    except ValueError:
                        result["meta"][k] = v
        # quality block
        qual_match = re.search(r'quality:\s*\n((?:\s{4,}.+\n)+)', meta_text)
        if qual_match:
            for line in qual_match.group(1).split('\n'):
                line = line.strip()
                if ':' in line:
                    k, _, v = line.partition(':')
                    result["meta"][k.strip()] = v.strip()

    # ── Extract run date/type from header if meta block missing ──
    if not result["meta"].get("run_date"):
        date_m = re.search(r'\*\*Run Date:\*\*\s*(.+)', md_text)
        if date_m:
            result["meta"]["run_date"] = date_m.group(1).strip()
    if not result["meta"].get("run_type"):
        type_m = re.search(r'\*\*Run Type:\*\*\s*(.+)', md_text)
        if type_m:
            result["meta"]["run_type"] = type_m.group(1).strip()

    # ── Extract mega-force summary table ──
    table_match = re.search(r'MEGA-FORCE SUMMARY TABLE.*?\n+\|.*?\n\|[-| :]+\n((?:\|.*\n?)+)', md_text, re.IGNORECASE)
    if table_match:
        for row in table_match.group(1).strip().split('\n'):
            cells = [c.strip() for c in row.split('|')[1:-1]]
            if len(cells) >= 6:
                result["summary_table"].append({
                    "force": re.sub(r'^\d+\.\s*', '', cells[0]),
                    "direction": cells[1],
                    "confidence": cells[2],
                    "timeline": cells[3],
                    "consensus": cells[4],
                    "mispricing": cells[5],
                })

    # ── Extract individual mega-forces (Phase 1 sections) ──
    # Split on "## Mega-Force N:" headers in Phase 1 area
    phase1_match = re.search(r'## PHASE 1.*?(?=## PHASE 2|$)', md_text, re.DOTALL | re.IGNORECASE)
    if phase1_match:
        phase1_text = phase1_match.group(0)
        force_sections = re.split(r'(?=## Mega-Force \d+:)', phase1_text)
        for section in force_sections:
            name_m = re.match(r'## Mega-Force \d+:\s*(.+)', section.strip())
            if not name_m:
                continue
            force = {"name": name_m.group(1).strip()}

            # Extract key fields
            dir_m = re.search(r'\*\*Direction:\*\*\s*(.+)', section)
            force["direction"] = dir_m.group(1).strip() if dir_m else ""

            conf_m = re.search(r'\*\*Confidence in persistence:\*\*\s*(.+)', section)
            force["confidence"] = conf_m.group(1).strip() if conf_m else ""

            time_m = re.search(r'\*\*Time horizon:\*\*\s*(.+)', section)
            force["timeline"] = time_m.group(1).strip() if time_m else ""

            # Data anchor — capture as block of text
            anchor_m = re.search(r'\*\*Data anchor:\*\*\s*\n((?:[-*].*\n?)+)', section)
            if anchor_m:
                anchors = []
                for line in anchor_m.group(1).strip().split('\n'):
                    line = re.sub(r'^[-*]\s*', '', line.strip())
                    if line:
                        anchors.append(line)
                force["data_anchor"] = anchors
            else:
                force["data_anchor"] = []

            # Mechanism paragraph
            mech_m = re.search(r'\*\*Mechanism:\*\*\s*\n(.+?)(?=\n\*\*|\n---|\n##|$)', section, re.DOTALL)
            force["mechanism"] = mech_m.group(1).strip() if mech_m else ""

            # Cross-sector impact
            cross_m = re.search(r'\*\*Cross-sector impact:\*\*\s*\n((?:[-*].*\n?)+)', section)
            if cross_m:
                impacts = []
                for line in cross_m.group(1).strip().split('\n'):
                    line = re.sub(r'^[-*]\s*', '', line.strip())
                    if line:
                        impacts.append(line)
                force["cross_sector"] = impacts
            else:
                force["cross_sector"] = []

            # Last quarter change
            lqc_m = re.search(r'\*\*Last quarter change:\*\*\s*(.+)', section)
            force["last_quarter_change"] = lqc_m.group(1).strip() if lqc_m else ""

            result["forces"].append(force)

    # ── Extract causal chains (Phase 2) and attach to forces ──
    phase2_match = re.search(r'## PHASE 2.*?(?=## PHASE 3|$)', md_text, re.DOTALL | re.IGNORECASE)
    if phase2_match:
        phase2_text = phase2_match.group(0)
        # Split by mega-force headers within Phase 2
        force_chains = re.split(r'(?=## Mega-Force \d+:)', phase2_text)
        for section in force_chains:
            name_m = re.match(r'## Mega-Force \d+:\s*(.+)', section.strip())
            if not name_m:
                continue
            force_name = name_m.group(1).strip()

            chains = {}
            for order_label, order_key in [("FIRST-ORDER", "first_order"), ("SECOND-ORDER", "second_order"), ("THIRD-ORDER", "third_order")]:
                order_m = re.search(rf'### {order_label} IMPACTS.*?\n(.*?)(?=### [A-Z]|---\s*\n## |$)', section, re.DOTALL)
                if order_m:
                    block = order_m.group(1).strip()
                    chain_info = {}
                    # Extract chain arrow
                    chain_m = re.search(r'\*\*Chain:\*\*\s*(.+)', block)
                    chain_info["chain"] = chain_m.group(1).strip() if chain_m else ""
                    # Direction
                    dir_m = re.search(r'Direction:\s*(.+)', block)
                    chain_info["direction"] = dir_m.group(1).strip() if dir_m else ""
                    # Consensus
                    cons_m = re.search(r'Consensus awareness:\s*(.+)', block)
                    chain_info["consensus"] = cons_m.group(1).strip() if cons_m else ""
                    # Timeline to materiality
                    tl_m = re.search(r'\*\*Timeline to (?:materiality|irreversibility):\*\*\s*(.+)', block)
                    chain_info["timeline"] = tl_m.group(1).strip() if tl_m else ""
                    chains[order_key] = chain_info

            # Attach chains to matching force (fuzzy: Phase 2 may use shorter names)
            for f in result["forces"]:
                if f["name"] == force_name or force_name in f["name"] or f["name"] in force_name:
                    f["causal_chains"] = chains
                    break

    # ── Extract contrarian stress tests (Phase 4) and attach to forces ──
    phase4_match = re.search(r'## PHASE 4.*?(?=## MEGA-FORCE SUMMARY|## Summary|## Meta|$)', md_text, re.DOTALL | re.IGNORECASE)
    if phase4_match:
        phase4_text = phase4_match.group(0)
        stress_sections = re.split(r'(?=### Mega-Force \d+:)', phase4_text)
        for section in stress_sections:
            name_m = re.match(r'### Mega-Force \d+:\s*(.+)', section.strip())
            if not name_m:
                continue
            force_name = name_m.group(1).strip()

            stress = {}
            # Consensus saturation
            sat_m = re.search(r'Consensus status:\s*(.+?)(?:\n|$)', section)
            stress["consensus_status"] = sat_m.group(1).strip() if sat_m else ""
            # Assessment
            assess_m = re.search(r'\*\*Assessment:\*\*\s*(.+?)(?:\n|$)', section)
            stress["assessment"] = assess_m.group(1).strip() if assess_m else ""
            # Conviction after stress test
            conv_m = re.search(r'\*\*Conviction after stress test:\*\*\s*(.+)', section)
            stress["conviction_post_test"] = conv_m.group(1).strip() if conv_m else ""

            for f in result["forces"]:
                if f["name"] == force_name or force_name in f["name"] or f["name"] in force_name:
                    f["stress_test"] = stress
                    break

    # ── Extract blind spots (Phase 3) ──
    phase3_match = re.search(r'## PHASE 3.*?(?=## PHASE 4|$)', md_text, re.DOTALL | re.IGNORECASE)
    if phase3_match:
        phase3_text = phase3_match.group(0)

        # Coverage assessment per mega-force
        coverage_sections = re.split(r'(?=\*\*Mega-Force \d+)', phase3_text)
        coverage_map = {}
        for section in coverage_sections:
            cov_name_m = re.match(r'\*\*Mega-Force \d+\s*\(([^)]+)\)\s*—\s*Coverage Status:\s*(.+?)\*\*', section)
            if cov_name_m:
                coverage_map[cov_name_m.group(1).strip()] = cov_name_m.group(2).strip()

        # Prioritized blind spots
        blind_sections = re.split(r'(?=\*\*(?:HIGH|MEDIUM|LOW) PRIORITY BLIND SPOT)', phase3_text)
        for section in blind_sections:
            bs_m = re.match(r'\*\*(HIGH|MEDIUM|LOW) PRIORITY BLIND SPOT #\d+:\s*(.+?)\*\*', section.strip())
            if not bs_m:
                continue
            bs = {
                "priority": bs_m.group(1),
                "name": bs_m.group(2).strip(),
            }
            gap_m = re.search(r'\*\*Coverage gap:\*\*\s*(.+?)(?:\n\n|\n\*\*)', section, re.DOTALL)
            bs["coverage_gap"] = gap_m.group(1).strip() if gap_m else ""

            inv_m = re.search(r'\*\*Investability:\*\*\s*(\S+(?:\s+\S+)?)', section)
            inv_raw = inv_m.group(1).strip() if inv_m else ""
            # Capture two-word levels like "VERY HIGH" or "MEDIUM-HIGH" but stop before long descriptions
            if inv_raw and '—' in inv_raw:
                inv_raw = inv_raw.split('—')[0].strip()
            bs["investability"] = inv_raw

            tl_m = re.search(r'\*\*Timeline to materiality:\*\*\s*(.+?)(?:\n|$)', section)
            bs["timeline"] = tl_m.group(1).strip() if tl_m else ""

            rec_m = re.search(r'\*\*Recommendation:\*\*\s*(.+?)(?:\n\n|\n---|\n\*\*|$)', section, re.DOTALL)
            bs["recommendation"] = rec_m.group(1).strip() if rec_m else ""

            result["blind_spots"].append(bs)

        # Attach coverage status to forces
        for f in result["forces"]:
            for cov_key, cov_val in coverage_map.items():
                if cov_key.lower() in f["name"].lower() or f["name"].lower() in cov_key.lower():
                    f["coverage_status"] = cov_val
                    break

    return result


def generate_html(week, briefing, theses, improvement, synthesis, snapshot_data,
                   all_weeks=None, all_weeks_data=None, regime_history=None,
                   skill_files=None, methodology=None, output_dir=None,
                   closed_theses=None, horizon_map=None, horizon_json_data=None,
                   thesis_json_sidecars=None, accuracy_tracker=None,
                   improvement_json=None):
    """Generate the full HTML dashboard with multi-week history support."""

    all_weeks = all_weeks or [week]
    all_weeks_data = all_weeks_data or {}
    regime_history = regime_history or []
    skill_files = skill_files or []
    methodology = methodology or ""
    thesis_json_sidecars = thesis_json_sidecars or {}
    accuracy_tracker = accuracy_tracker or ""
    improvement_json = improvement_json or None

    # --- Parse accuracy and system health data ---
    # Priority 1: improvement-data.json sidecar (stable contract)
    # Priority 2: accuracy-tracker.md (persistent cross-week file, markdown parsing)
    accuracy_pct = None
    accuracy_cumulative_html = ""
    accuracy_scorecard_html = ""

    if improvement_json and "accuracy" in improvement_json:
        acc = improvement_json["accuracy"]
        accuracy_pct = acc.get("cumulative_pct")

        # Build cumulative table from JSON
        by_cat = acc.get("by_category", [])
        if by_cat:
            rows = ['| Category | Correct | Partial | Wrong | Total | Accuracy | Confidence |',
                    '|----------|---------|---------|-------|-------|----------|------------|']
            for cat in by_cat:
                rows.append(f'| {cat.get("category", "")} | {cat.get("correct", "")} | {cat.get("partial", "")} | {cat.get("wrong", "")} | {cat.get("total", "")} | **{cat.get("accuracy_pct", "")}%** | {cat.get("confidence", "")} |')
            # Add cumulative row
            rows.append(f'| **CUMULATIVE** | **{acc.get("correct", "")}** | **{acc.get("partial", "")}** | **{acc.get("wrong", "")}** | **{acc.get("total_calls", "")}** | **{accuracy_pct}%** | |')
            accuracy_cumulative_html = md_to_html('\n'.join(rows))

        # Build scorecard detail from JSON
        scorecard = acc.get("scorecard", [])
        if scorecard:
            sc_rows = ['| Call | Outcome | Verdict | Reasoning |',
                       '|------|---------|---------|-----------|']
            for sc in scorecard:
                verdict = sc.get("verdict", "")
                verdict_icon = {"CORRECT": "✓", "PARTIALLY CORRECT": "~", "WRONG": "✗", "TOO EARLY": "⏳"}.get(verdict.upper(), "")
                sc_rows.append(f'| {sc.get("call", "")} | {sc.get("outcome", "")} | {verdict_icon} {verdict} | {sc.get("reasoning", "")} |')
            accuracy_scorecard_html = md_to_html('\n'.join(sc_rows))

    # Fallback: parse accuracy-tracker.md if JSON not available
    if accuracy_pct is None and accuracy_tracker:
        cum_match = re.search(r'\*\*CUMULATIVE\*\*.*?\*\*(\d+)%\*\*', accuracy_tracker)
        if cum_match:
            accuracy_pct = int(cum_match.group(1))

        if not accuracy_cumulative_html:
            in_cumulative = False
            cum_lines = []
            for line in accuracy_tracker.split('\n'):
                if 'Cumulative Accuracy' in line and line.strip().startswith('#'):
                    in_cumulative = True
                    continue
                if in_cumulative:
                    if line.strip().startswith('|'):
                        cum_lines.append(line)
                    elif line.strip().startswith('#') or (line.strip() and not line.strip().startswith('|') and cum_lines):
                        break
            if cum_lines:
                accuracy_cumulative_html = md_to_html('\n'.join(cum_lines))

        if not accuracy_scorecard_html:
            in_detail = False
            detail_lines = []
            for line in accuracy_tracker.split('\n'):
                if 'Scorecard Detail' in line:
                    in_detail = True
                    continue
                if in_detail:
                    if line.strip().startswith('#') and 'Scorecard Detail' not in line:
                        break
                    if line.strip():
                        detail_lines.append(line)
            if detail_lines:
                accuracy_scorecard_html = md_to_html('\n'.join(detail_lines))

    # Regime: Try synthesis-data.json sidecar first (stable contract),
    # fall back to markdown parsing (legacy) if not available.
    regime_data = None
    if output_dir:
        sidecar_path = output_dir / "synthesis" / f"{week}-synthesis-data.json"
        if sidecar_path.exists():
            try:
                sidecar_json = json.loads(sidecar_path.read_text(encoding="utf-8"))
                regime_data = parse_regime_from_json(sidecar_json)
            except Exception as e:
                import sys
                print(f"Warning: failed to parse {sidecar_path}: {e}", file=sys.stderr)
    if regime_data is None:
        regime_data = parse_regime_from_synthesis(synthesis)  # legacy fallback

    # NOTE: Regime JSON override from briefing-data.json happens below (further enrichment)

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

    # Try briefing-data.json: week-prefixed first, then legacy
    # We do NOT fall back to an un-prefixed "briefing-data.json" because it could be stale
    # data from a prior week with no way to verify which week it belongs to.
    json_path = None
    if output_dir:
        candidates = [
            output_dir / "briefings" / f"{week}-briefing-data.json",   # canonical: 2026-W13-briefing-data.json
            output_dir / "briefings" / f"{week}-thesis-status.json",   # legacy format
        ]
        for candidate in candidates:
            if candidate.exists():
                json_path = candidate
                break

    briefing_json_raw = None  # keep full JSON for regime/meta extraction later

    if json_path:
        try:
            raw = json.loads(json_path.read_text(encoding="utf-8"))
            briefing_json_raw = raw  # store for regime/meta/thesis use below

            # briefing-data.json nests under "theses"; legacy is flat
            thesis_data = raw.get("theses", raw) if isinstance(raw, dict) else {}
            for slug, data in thesis_data.items():
                if isinstance(data, dict):
                    if data.get("recommendation"):
                        thesis_recommendations[slug] = data["recommendation"].lower()
                    if data.get("conviction"):
                        thesis_convictions_from_briefing[slug] = data["conviction"]

            # Normalize cross_asset keys: JSON uses asset/signal/etf,
            # renderer expects what/direction/etfs
            cross_assets_from_json = []
            for item in raw.get("cross_asset", []):
                normalized = dict(item)  # copy all fields (why, timing, etc.)
                if "asset" in normalized and "what" not in normalized:
                    normalized["what"] = normalized.pop("asset")
                if "signal" in normalized and "direction" not in normalized:
                    normalized["direction"] = normalized.pop("signal")
                if "etf" in normalized and "etfs" not in normalized:
                    normalized["etfs"] = normalized.pop("etf")
                cross_assets_from_json.append(normalized)

            # Normalize sector_view keys: JSON uses etf, renderer expects etfs
            sector_view_from_json = []
            for item in raw.get("sector_view", []):
                normalized = dict(item)
                if "etf" in normalized and "etfs" not in normalized:
                    normalized["etfs"] = normalized.pop("etf")
                sector_view_from_json.append(normalized)
        except Exception as e:
            import sys
            print(f"Warning: failed to parse {json_path}: {e}", file=sys.stderr)
            briefing_json_raw = None  # reset so downstream code doesn't use partial data

    # Regime JSON override — now that briefing_json_raw is loaded
    if briefing_json_raw and "regime" in briefing_json_raw:
        rj = briefing_json_raw["regime"]
        regime_data["regime"] = rj.get("quadrant", regime_data["regime"])
        regime_data["direction"] = rj.get("direction", regime_data["direction"])
        regime_data["confidence"] = rj.get("confidence", regime_data["confidence"])
        if rj.get("weeks_in_regime"):
            regime_data["weeks_held"] = str(rj["weeks_in_regime"])
        gs = rj.get("growth_score")
        inf = rj.get("inflation_score")
        if gs is not None and inf is not None:
            regime_data["x"] = max(-1.0, min(1.0, float(gs)))
            regime_data["y"] = max(-1.0, min(1.0, float(inf)))

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

    # Helper: generate conviction label HTML
    def _conviction_bar_html(conviction_str):
        """Generate a colored text label for conviction level.
        Preserves the exact wording (e.g. 'Low-Medium', 'Medium-High',
        'High (strengthening)') and maps color by the dominant level."""
        raw = conviction_str.strip().lower() if conviction_str else ""
        # Determine dominant level for color mapping
        level = raw.split("(")[0].split(",")[0].strip()
        if "-" in level:
            parts = [p.strip() for p in level.split("-")]
            rank = {"high": 3, "medium": 2, "med": 2, "low": 1}
            level = max(parts, key=lambda p: rank.get(p, 0))
        if level in ("high", "h"):
            color = "var(--green)"
        elif level in ("medium", "med", "m"):
            color = "var(--amber)"
        elif level in ("low", "l"):
            color = "var(--red)"
        else:
            color = "var(--text-muted)"
        display = conviction_str.strip() if conviction_str else "—"
        return f'<span class="conviction-label" style="color: {color}; font-size: 10px; font-weight: 600; white-space: nowrap;">{display}</span>'

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
        thesis_stem = name.replace(".md", "")  # e.g. "ACTIVE-structural-grid-bottleneck"

        # --- THESIS SIDECAR: structured data from thesis-name-data.json ---
        thesis_sidecar = thesis_json_sidecars.get(thesis_stem)

        # --- JSON-PRIMARY: conviction and recommendation from briefing-data.json ---
        conviction = ""
        recommendation = ""

        # Priority 1: thesis sidecar (most authoritative — from the thesis file itself)
        if thesis_sidecar:
            conviction = thesis_sidecar.get("conviction", "")
            # Sidecar doesn't carry recommendation (that's a briefing concept)

        json_thesis_entry = None
        if briefing_json_raw and "theses" in briefing_json_raw:
            json_theses = briefing_json_raw["theses"]
            # Try exact slug match first
            if thesis_key in json_theses:
                json_thesis_entry = json_theses[thesis_key]
            else:
                # Fuzzy match: word overlap between thesis_key and JSON slugs
                # Only accept if there's a single best match (no ties — ambiguity means skip)
                tk_words = set(thesis_key.lower().replace('-', ' ').split()) - {'the', 'a', 'an', 'of', 'for', 'and', 'in', 'on'}
                best_score = 0
                best_match = None
                tie = False
                for jk, jv in json_theses.items():
                    jk_words = set(jk.lower().replace('-', ' ').split()) - {'the', 'a', 'an', 'of', 'for', 'and', 'in', 'on'}
                    overlap = len(tk_words & jk_words)
                    if overlap >= 2 and overlap > best_score:
                        best_score = overlap
                        best_match = jv
                        tie = False
                    elif overlap >= 2 and overlap == best_score:
                        tie = True  # ambiguous — two JSON entries score equally
                if best_match and not tie:
                    json_thesis_entry = best_match

            if json_thesis_entry:
                conviction = json_thesis_entry.get("conviction", "")
                recommendation = json_thesis_entry.get("recommendation", "")

        # --- LEGACY FALLBACK: parse conviction from thesis markdown file ---
        if not conviction:
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
            # Match prose patterns
            if not conviction:
                conviction_match = re.search(
                    r'(?:conviction|conv\.?)\s*(?:level|holds at|after stress-test)?[:\s]+\*{0,2}(High|Medium|Low)(?:-\w+)?\*{0,2}',
                    content, re.IGNORECASE
                )
                if conviction_match:
                    conviction = conviction_match.group(1).strip().capitalize()
            # Last resort: briefing table lookup (fuzzy)
            if not conviction:
                thesis_lookup_conv = thesis_key.lower()
                conv_words = set(thesis_lookup_conv.replace('-', ' ').split()) - {'the', 'a', 'an', 'of', 'for', 'and', 'in', 'on'}
                best_conv_score = 0
                for ckey, cval in thesis_convictions_from_briefing.items():
                    if ckey in thesis_lookup_conv or thesis_lookup_conv in ckey:
                        conviction = cval
                        break
                    ckey_words = set(ckey.replace('-', ' ').split()) - {'the', 'a', 'an', 'of', 'for', 'and', 'in', 'on'}
                    overlap = len(conv_words & ckey_words)
                    if overlap >= 2 and overlap > best_conv_score:
                        best_conv_score = overlap
                        conviction = cval

        # Metadata: prefer thesis sidecar, fall back to markdown parsing
        if thesis_sidecar:
            provenance = thesis_sidecar.get("provenance", "")
            generated = thesis_sidecar.get("generated", "")
            updated = thesis_sidecar.get("updated", "")
            # time_horizon can be nested under the_trade or at top level
            trade = thesis_sidecar.get("the_trade", {})
            horizon = trade.get("how_long", thesis_sidecar.get("time_horizon", ""))
        else:
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

            # Extract time horizon (first line after ### How long or ## Time Horizon)
            horizon = ""
            horizon_match = re.search(r'###?\s*How long\s*\n+(.+)', content)
            if not horizon_match:
                horizon_match = re.search(r'## Time Horizon\s*\n+(.+)', content)
            if horizon_match:
                # Grab just the short duration label (e.g. "1-3 months", "2-5 years")
                h_match = re.match(r'([\d]+-[\d]+\s*(?:months?|years?|weeks?))', horizon_match.group(1).strip(), re.IGNORECASE)
                if h_match:
                    horizon = h_match.group(1)
                else:
                    # Fallback: take first phrase before period or parenthesis
                    horizon = horizon_match.group(1).strip().split('.')[0].split('(')[0].strip()

        # Legacy fallback: look up recommendation from briefing table (only if JSON didn't provide one)
        if not recommendation:
            thesis_lookup = thesis_key.lower()
            thesis_words = set(thesis_lookup.replace('-', ' ').split()) - {'the', 'a', 'an', 'of', 'for', 'and', 'in', 'on'}
            best_match_score = 0
            for rkey, rval in thesis_recommendations.items():
                if rkey in thesis_lookup or thesis_lookup in rkey:
                    recommendation = rval.capitalize()
                    break
                rkey_words = set(rkey.replace('-', ' ').split()) - {'the', 'a', 'an', 'of', 'for', 'and', 'in', 'on'}
                overlap = len(thesis_words & rkey_words)
                if overlap >= 2 and overlap > best_match_score:
                    best_match_score = overlap
                    recommendation = rval.capitalize()

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
                r'(## (?:Summary|Plain English Summary))',
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

        # Render thesis body: prefer JSON sidecar (no parsing needed), fall back to markdown
        if thesis_sidecar:
            thesis_body_html = md_to_html(format_thesis_from_json(thesis_sidecar))
        else:
            thesis_body_html = md_to_html(format_thesis_html(render_content))

        display = "block" if i == 0 else "none"
        thesis_contents += (
            f'<div class="thesis-detail" id="thesis-{i}" style="display:{display}">'
            f'{chart_html}'
            f'{thesis_body_html}'
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
        # Match ### How long (current), ## Time Horizon (legacy), **Time horizon:** (bold inline)
        horizon_text = ""
        horizon_match = re.search(r'###?\s*How long\s*\n+(.+)', content)
        if not horizon_match:
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
    # Priority 1: improvement-data.json sidecar; Priority 2: markdown parsing
    imp = improvement_parsed
    if improvement_json:
        ij_health = improvement_json.get("health", {})
        if ij_health.get("score") is not None:
            imp["health_score"] = str(ij_health["score"])
        if ij_health.get("trend"):
            imp["health_trend"] = ij_health["trend"]
        if ij_health.get("skills_at_risk"):
            imp["skills_at_risk"] = ij_health["skills_at_risk"]
        ij_skills = improvement_json.get("skill_scores", [])
        if ij_skills:
            imp["observation_rows"] = ij_skills
        ij_amend = improvement_json.get("amendments", [])
        if ij_amend:
            imp["amendments"] = ij_amend
        ij_gaps = improvement_json.get("data_gaps", [])
        if ij_gaps:
            imp["gaps"] = ij_gaps

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
        proposed = (row.get("proposed", "") or row.get("skill", ""))
        status = (row.get("status", ""))
        target = (row.get("target metric", "") or row.get("target", "")
                  or row.get("amendment", "") or row.get("type", ""))
        before = row.get("before", "")
        after = (row.get("after", "") or row.get("after (run 3)", ""))
        verdict = (row.get("verdict", "") or row.get("recommendation", ""))
        impact = row.get("impact", "")

        # Badge for status
        s_lower = status.lower().strip()
        if s_lower in ("approved", "implemented"):
            badge_cls = "badge-active"
        elif s_lower in ("proposed", "new"):
            badge_cls = "badge-draft"
        elif s_lower in ("rejected", "reverted"):
            badge_cls = "badge-invalidated"
        elif s_lower == "pending":
            badge_cls = "badge-draft"
        else:
            badge_cls = "badge-draft"

        # Verdict coloring
        v_lower = verdict.lower() if verdict else ""
        v_style = ""
        if "effective" in v_lower or "approve" in v_lower:
            v_style = 'color: var(--green);'
        elif "reverted" in v_lower or "ineffective" in v_lower or "reject" in v_lower:
            v_style = 'color: var(--red);'
        elif "inconclusive" in v_lower or "defer" in v_lower:
            v_style = 'color: var(--accent);'

        # Build expanded detail content
        description = row.get("description", "")
        detail_parts = []
        if description:
            detail_parts.append(f'<strong>Description:</strong> {description}')
        if impact:
            detail_parts.append(f'<strong>Impact:</strong> {impact}')
        if before:
            detail_parts.append(f'<strong>Before:</strong> {before}')
        if after:
            detail_parts.append(f'<strong>After:</strong> {after}')
        if not detail_parts and verdict:
            detail_parts.append(verdict)
        detail_html = ' &nbsp;·&nbsp; '.join(detail_parts) if detail_parts else 'No detail available.'

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
        weeks_missing = row.get("consecutive weeks", row.get("consecutive weeks missing",
                        row.get("weeks", "")))
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

    # --- Build Mega Forces tab HTML from Skill 14 horizon map ---
    # Prefer pre-parsed JSON sidecar (horizon-data.json) over markdown parsing
    if horizon_json_data:
        # JSON sidecar matches parse_horizon_map() output shape — use directly
        horizon_data = horizon_json_data
        # Ensure expected top-level keys exist
        horizon_data.setdefault("meta", {})
        horizon_data.setdefault("forces", [])
        horizon_data.setdefault("blind_spots", [])
        horizon_data.setdefault("summary_table", [])
        # Build summary_table from forces if not provided explicitly in JSON
        if not horizon_data["summary_table"] and horizon_data["forces"]:
            for f in horizon_data["forces"]:
                horizon_data["summary_table"].append({
                    "force": f.get("name", ""),
                    "direction": f.get("direction", ""),
                    "confidence": f.get("confidence", ""),
                    "timeline": f.get("timeline", ""),
                    "consensus": f.get("consensus", ""),
                    "mispricing": f.get("mispricing", ""),
                })
    else:
        horizon_data = parse_horizon_map(horizon_map) if horizon_map else None
    mega_forces_html = ""
    if horizon_data and horizon_data.get("forces"):
        hd = horizon_data
        hm = hd["meta"]
        run_date = hm.get("run_date") or hm.get("last_run_date", "—")
        run_type = hm.get("run_type", "—")
        forces_mapped = hm.get("mega_forces_mapped", len(hd["forces"]))
        blind_count = hm.get("blind_spots_identified", len(hd["blind_spots"]))
        actionable_count = hm.get("blind_spots_actionable", 0)

        # Derive quarter from run_date (e.g. "2026-03-23" -> "2026 Q1")
        report_quarter = "—"
        try:
            rd_parsed = datetime.strptime(run_date.strip(), "%Y-%m-%d")
            q = (rd_parsed.month - 1) // 3 + 1
            report_quarter = f"{rd_parsed.year} Q{q}"
        except (ValueError, AttributeError):
            # Try extracting from filename pattern like "2026-Q1"
            q_match = re.search(r'(\d{4})-Q(\d)', horizon_map or "")
            if q_match:
                report_quarter = f"{q_match.group(1)} Q{q_match.group(2)}"

        # Direction color helper
        def _dir_color(d):
            dl = d.lower() if d else ""
            if "accelerat" in dl:
                return "var(--green)"
            elif "deceler" in dl:
                return "var(--red)"
            return "var(--amber)"

        # Confidence color helper
        def _conf_color(c):
            cl = c.lower() if c else ""
            if "very high" in cl:
                return "var(--green)"
            elif "high" in cl:
                return "var(--accent)"
            elif "medium" in cl:
                return "var(--amber)"
            return "var(--text-muted)"

        # Priority color helper
        def _prio_color(p):
            pl = p.upper() if p else ""
            if pl == "HIGH":
                return "var(--red)"
            elif pl == "MEDIUM":
                return "var(--amber)"
            return "var(--text-muted)"

        # KPI strip
        mega_forces_html += f'''
        <div class="kpi-grid" style="margin-bottom: 12px;">
            <div class="kpi-card">
                <div class="kpi-label">MEGA FORCES</div>
                <div class="kpi-number">{forces_mapped}</div>
                <div class="kpi-sub">Structural shifts mapped</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">BLIND SPOTS</div>
                <div class="kpi-number" style="color: {"var(--red)" if blind_count > 0 else "var(--green)"};">{blind_count}</div>
                <div class="kpi-sub">{actionable_count} actionable</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">LAST RUN</div>
                <div style="font-size: 14px; font-weight: 600; color: var(--text); font-variant-numeric: tabular-nums; line-height: 1.1;">{run_date}</div>
                <div class="kpi-sub">{run_type}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">REPORT</div>
                <div class="kpi-number">{report_quarter}</div>
                <div class="kpi-sub">Quarterly horizon map</div>
            </div>
        </div>
        '''

        # Summary table
        if hd["summary_table"]:
            sum_rows = ""
            for st in hd["summary_table"]:
                dc = _dir_color(st["direction"])
                cc = _conf_color(st["confidence"])
                sum_rows += (
                    f'<tr>'
                    f'<td style="color: var(--white); font-weight: 500;">{st["force"]}</td>'
                    f'<td><span style="color: {dc}; font-weight: 600;">{st["direction"]}</span></td>'
                    f'<td style="color: {cc};">{st["confidence"]}</td>'
                    f'<td style="color: var(--text-muted);">{st["timeline"]}</td>'
                    f'<td style="color: var(--text);">{st["consensus"]}</td>'
                    f'<td style="color: var(--accent);">{st["mispricing"]}</td>'
                    f'</tr>'
                )
            mega_forces_html += f'''
            <div class="panel" style="margin-bottom: 12px;">
                <div class="panel-header"><span class="panel-title">LANDSCAPE</span><span class="panel-meta">Decade horizon</span></div>
                <div class="panel-body-dense">
                    <div class="cross-asset-container">
                        <table>
                            <thead><tr>
                                <th>Force</th><th>Direction</th><th>Confidence</th>
                                <th>Timeline</th><th>Consensus</th><th>Mispricing</th>
                            </tr></thead>
                            <tbody>{sum_rows}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            '''

        # Force cards — each expandable
        for idx, force in enumerate(hd["forces"]):
            dc = _dir_color(force.get("direction", ""))
            cc = _conf_color(force.get("confidence", ""))
            dir_short = force.get("direction", "").split("(")[0].strip()
            conf_short = force.get("confidence", "").split("(")[0].strip()
            cov = force.get("coverage_status", "")
            cov_color = "var(--green)" if "WELL" in cov.upper() else ("var(--amber)" if "PARTIAL" in cov.upper() else "var(--red)" if cov else "var(--text-muted)")

            # Stress test info
            stress = force.get("stress_test", {})
            conviction_post = stress.get("conviction_post_test", "")
            assessment = stress.get("assessment", "")

            # Data anchor bullets
            anchor_html = ""
            for a in force.get("data_anchor", [])[:4]:
                anchor_html += f'<li style="margin: 2px 0; color: var(--text); font-size: 11px;">{apply_inline(a)}</li>'

            # Causal chains
            chains = force.get("causal_chains", {})
            chains_html = ""
            for order_key, order_label in [("first_order", "1ST ORDER"), ("second_order", "2ND ORDER"), ("third_order", "3RD ORDER")]:
                chain = chains.get(order_key, {})
                if not chain:
                    continue
                chain_dir = chain.get("direction", "")
                chain_cons = chain.get("consensus", "")
                chain_tl = chain.get("timeline", "")
                chain_arrow = chain.get("chain", "")
                cons_color = "var(--red)" if "VERY LOW" in chain_cons.upper() else ("var(--amber)" if "LOW" in chain_cons.upper() else "var(--text-muted)")
                chains_html += f'''
                <div style="margin-bottom: 8px; padding: 8px 10px; background: var(--surface); border-left: 2px solid var(--border-bright);">
                    <div style="font-family: var(--mono); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--accent); margin-bottom: 4px;">{order_label}</div>
                    <div style="font-size: 11px; color: var(--text); margin-bottom: 4px; line-height: 1.5;">{apply_inline(chain_arrow)}</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px 16px; font-family: var(--mono); font-size: 10px;">
                        <span style="color: var(--text-muted);">Direction: <span style="color: var(--text);">{chain_dir}</span></span>
                        <span style="color: var(--text-muted);">Consensus: <span style="color: {cons_color};">{chain_cons}</span></span>
                        {"<span style='color: var(--text-muted);'>Timeline: <span style=color:var(--text);>" + chain_tl + "</span></span>" if chain_tl else ""}
                    </div>
                </div>'''

            # Mechanism first sentence for collapsed view
            mechanism = force.get("mechanism", "")
            mech_short = mechanism[:200] + "..." if len(mechanism) > 200 else mechanism

            force_id = f"mega-force-{idx}"
            short_id = f"mf-short-{idx}"
            mega_forces_html += f'''
            <div class="panel mf-card" style="margin-bottom: 8px;">
                <div class="panel-header" style="cursor: pointer;" onclick="var body = document.getElementById('{force_id}'); var short = document.getElementById('{short_id}'); var arrow = this.querySelector('.mf-arrow'); if(body.style.display === 'none') {{ body.style.display = 'block'; short.style.display = 'none'; arrow.style.transform = 'rotate(180deg)'; }} else {{ body.style.display = 'none'; short.style.display = 'block'; arrow.style.transform = 'rotate(0deg)'; }}">
                    <span class="panel-title" style="display: flex; align-items: center; gap: 10px;">
                        {force["name"]}
                        <span style="font-size: 9px; padding: 2px 6px; background: {dc}22; color: {dc}; border: 1px solid {dc}44; font-weight: 500; letter-spacing: 0.04em;">{dir_short}</span>
                        <span style="font-size: 9px; padding: 2px 6px; background: {cc}22; color: {cc}; border: 1px solid {cc}44; font-weight: 500;">{conf_short}</span>
                        {"<span style='font-size: 9px; padding: 2px 6px; background:" + cov_color + "22; color:" + cov_color + "; border: 1px solid " + cov_color + "44; font-weight: 500;'>" + cov + "</span>" if cov else ""}
                    </span>
                    <span style="display: flex; align-items: center; gap: 12px;">
                        <span style="color: var(--text-muted); font-size: 10px; font-weight: 400; text-transform: none; letter-spacing: 0;">{force.get("timeline", "")}</span>
                        <span class="mf-arrow" style="color: var(--text-muted); font-size: 10px; transition: transform 0.15s;">&#9660;</span>
                    </span>
                </div>
                <div id="{short_id}" class="panel-body" style="padding: 8px 12px;">
                    <div style="display: flex; gap: 16px; margin-bottom: 8px;">
                        <div style="flex: 1;">
                            <div style="font-family: var(--mono); font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px;">Key Data</div>
                            <ul style="margin: 0 0 0 14px; padding: 0;">{anchor_html}</ul>
                        </div>
                    </div>
                    <div style="font-size: 12px; color: var(--text); line-height: 1.6; margin-bottom: 6px;">{apply_inline(mech_short)}</div>
                </div>
                <div id="{force_id}" style="display: none;">
                    <div style="padding: 8px 12px 10px 12px;">
                        <div style="display: flex; gap: 16px; margin-bottom: 8px;">
                            <div style="flex: 1;">
                                <div style="font-family: var(--mono); font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px;">Key Data</div>
                                <ul style="margin: 0 0 0 14px; padding: 0;">{anchor_html}</ul>
                            </div>
                        </div>
                        <div style="font-family: var(--mono); font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px;">Mechanism</div>
                        <div style="font-size: 12px; color: var(--text); line-height: 1.6; margin-bottom: 12px;">{apply_inline(mechanism)}</div>
                        {"<div style='margin-bottom: 12px;'><div style=" + repr("font-family: var(--mono); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--accent); margin-bottom: 6px;") + ">Causal Chains</div>" + chains_html + "</div>" if chains_html else ""}
                        {"<div style='padding: 8px 10px; background: var(--surface2); border: 1px solid var(--border); margin-bottom: 8px;'><div style=" + repr("font-family: var(--mono); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--accent); margin-bottom: 4px;") + ">Stress Test</div><div style=" + repr("font-size: 11px; color: var(--text); line-height: 1.5;") + ">" + apply_inline(assessment) + "</div><div style=" + repr("font-family: var(--mono); font-size: 10px; color: var(--text-muted); margin-top: 4px;") + ">Post-test conviction: <span style=" + repr("color: var(--accent); font-weight: 600;") + ">" + conviction_post + "</span></div></div>" if assessment else ""}
                    </div>
                </div>
            </div>
            '''

        # Blind spots section
        if hd["blind_spots"]:
            bs_rows = ""
            for bs in hd["blind_spots"]:
                pc = _prio_color(bs["priority"])
                bs_rows += (
                    f'<tr>'
                    f'<td><span style="color: {pc}; font-weight: 600;">{bs["priority"]}</span></td>'
                    f'<td style="color: var(--white); font-weight: 500;">{bs["name"]}</td>'
                    f'<td style="color: var(--text);">{bs.get("coverage_gap", "")}</td>'
                    f'<td style="color: var(--text-muted);">{bs.get("investability", "")}</td>'
                    f'<td style="color: var(--text-muted);">{bs.get("timeline", "")}</td>'
                    f'<td style="color: var(--text); font-size: 10px;">{bs.get("recommendation", "")}</td>'
                    f'</tr>'
                )
            mega_forces_html += f'''
            <div class="panel" style="margin-top: 12px;">
                <div class="panel-header"><span class="panel-title">BLIND SPOTS</span><span class="panel-meta">{blind_count} identified · {actionable_count} actionable</span></div>
                <div class="panel-body-dense">
                    <div class="cross-asset-container">
                        <table>
                            <thead><tr>
                                <th>Priority</th><th>Blind Spot</th><th>Coverage Gap</th>
                                <th>Investability</th><th>Timeline</th><th>Action</th>
                            </tr></thead>
                            <tbody>{bs_rows}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            '''
    else:
        mega_forces_html = "<p style='color: var(--text-muted); text-align: center; padding: 40px 0;'>No horizon map data available. Run Skill 14 (Decade Horizon) to generate mega-force analysis.</p>"

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

    # Extract run date from briefing JSON for cross-asset/sector headers
    briefing_data_date = ""
    if briefing_json_raw and isinstance(briefing_json_raw, dict):
        meta = briefing_json_raw.get("meta", {})
        if isinstance(meta, dict):
            briefing_data_date = meta.get("run_date", "") or meta.get("week", "")

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

    # Track record — from accuracy tracker (authoritative), with briefing/improvement fallback
    track_record = "Collecting data..."
    track_record_color = "var(--text-muted)"
    if accuracy_pct is not None:
        track_record = f"{accuracy_pct}%"
        track_record_color = '#22c55e' if accuracy_pct >= 70 else ('#f59e0b' if accuracy_pct >= 50 else '#ef4444')
    else:
        # Fallback: regex search in briefing or improvement text
        briefing_lower = briefing.lower() if briefing else ""
        for text in [briefing_lower, improvement_lower]:
            accuracy_fallback = re.search(r'(\d+)%\s*(?:cumulative\s*)?accuracy', text)
            if not accuracy_fallback:
                accuracy_fallback = re.search(r'accuracy[:\s]+(\d+)%', text)
            if accuracy_fallback:
                pct = int(accuracy_fallback.group(1))
                track_record = f"{pct}%"
                track_record_color = '#22c55e' if pct >= 70 else ('#f59e0b' if pct >= 50 else '#ef4444')
                break
        else:
            if 'too early' in (briefing_lower or '') or 'collecting data' in improvement_lower:
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
    table-layout: fixed;
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
    font-family: 'Inter', sans-serif;
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
/* Conviction label — colored text */
.conviction-label {{
    font-size: 10px;
    font-weight: 600;
    white-space: nowrap;
    letter-spacing: 0.02em;
}}
.thesis-horizon {{
    font-size: 10px;
    color: var(--text-muted);
    white-space: nowrap;
}}
/* Thesis detail panel */
.thesis-detail-panel {{
    background: var(--surface);
    border: 1px solid var(--border);
    overflow-x: auto;
    max-width: 100%;
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
    overflow-wrap: break-word;
    word-break: break-word;
}}
.thesis-detail table {{
    table-layout: fixed;
    width: 100%;
}}
.thesis-detail td, .thesis-detail th {{
    overflow-wrap: break-word;
    word-break: break-word;
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
    <button onclick="showTab('megaforces')">MEGA FORCES</button>
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
                <div class="panel-body thesis-book" id="thesis-book-scroll" style="max-height: 360px; overflow-y: auto; position: relative;">
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
                <div id="thesis-book-fade" style="pointer-events: none; position: relative; height: 28px; margin-top: -28px; background: linear-gradient(transparent, var(--surface)); display: flex; align-items: flex-end; justify-content: center;">
                    <span style="font-size: 9px; color: var(--text-dim); letter-spacing: 0.1em; text-transform: uppercase; opacity: 0.7; pointer-events: none;">&#x25BC; scroll</span>
                </div>
            </div>
        </div>

        {'<div class="panel overview-grid-full"><div class="panel-header"><span class="panel-title">Cross-Asset View</span><span class="panel-meta">' + briefing_data_date + '</span></div><div class="panel-body">' + cross_asset_html + '</div></div>' if cross_asset_html else ''}

        {'<div class="panel overview-grid-full"><div class="panel-header"><span class="panel-title">Stocks — Sector View</span><span class="panel-meta">' + briefing_data_date + '</span></div><div class="panel-body">' + sector_view_html + '</div></div>' if sector_view_html else ''}
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
                    {'<div style="border-top: 1px solid var(--border); padding-top: 12px;"><h4 style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); margin-bottom: 8px;">6 &amp; 12-Month Forecast</h4>' + regime_forecast_html + '</div>' if regime_forecast_html else ''}
                    {'<div style="border-top: 1px solid var(--border); padding-top: 12px; margin-top: 12px;"><h4 style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); margin-bottom: 8px;">What Changed This Week</h4>' + regime_what_changed_html + '</div>' if regime_what_changed_html else ''}
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

    <!-- Mega Forces Tab -->
    <div class="tab-content" id="tab-megaforces">
        {mega_forces_html}
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

        {'<div class="panel" style="margin-bottom: 8px;"><div class="panel-header"><span class="panel-title">ACCURACY SCORECARD</span><span class="panel-meta">' + (f'{accuracy_pct}% cumulative' if accuracy_pct is not None else 'Collecting data') + '</span></div><div class="panel-body-dense">' + ('<div style="margin-bottom: 12px;">' + accuracy_cumulative_html + '</div>' if accuracy_cumulative_html else '') + ('<div><h4 style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); margin: 12px 0 8px 0;">Scorecard Detail</h4>' + accuracy_scorecard_html + '</div>' if accuracy_scorecard_html else '') + '</div></div>' if (accuracy_cumulative_html or accuracy_scorecard_html) else ''}

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

    // Chart.js cannot measure canvas dimensions inside display:none containers.
    // When a tab becomes visible, force-resize any Chart.js instances it contains.
    requestAnimationFrame(() => {{
        if (tabId === 'regime' && regimeChartInstances['regimeChart']) {{
            regimeChartInstances['regimeChart'].resize();
        }}
        if (tabId === 'overview' && regimeChartInstances['regimeChartOverview']) {{
            regimeChartInstances['regimeChartOverview'].resize();
        }}
        // Also resize any thesis charts that may be in the visible tab
        Object.values(Chart.instances || {{}}).forEach(c => c.resize());
    }});
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
// Store chart instances so we can resize them when hidden tabs become visible
const regimeChartInstances = {{}};

function renderRegimeChart(canvasId) {{
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const chartInstance = new Chart(canvas.getContext('2d'), {{
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
    regimeChartInstances[canvasId] = chartInstance;
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
    // Extra height per row to accommodate wrapped labels (multi-line names need more space)
    const rowHeight = 52;
    const chartHeight = Math.max(200, data.length * rowHeight + 100);
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
                            // Wrap at ~28 chars per line for better readability
                            const maxWidth = 28;
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

// Thesis book scroll fade — hide indicator when scrolled to bottom
(function() {{
    var el = document.getElementById('thesis-book-scroll');
    var fade = document.getElementById('thesis-book-fade');
    if (el && fade) {{
        function checkScroll() {{
            var atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 8;
            var noScroll = el.scrollHeight <= el.clientHeight;
            fade.style.opacity = (atBottom || noScroll) ? '0' : '1';
            fade.style.transition = 'opacity 0.2s';
        }}
        el.addEventListener('scroll', checkScroll);
        checkScroll();
    }}
}})();
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
    # Also load JSON sidecar files when available (thesis-name-data.json)
    theses = []
    thesis_json_sidecars = {}  # keyed by thesis filename stem (without .md)
    closed_theses = []
    theses_dir = output_dir / "theses" / "active"
    if theses_dir.exists():
        for f in sorted(theses_dir.glob("*.md")):
            theses.append((f.name, f.read_text(encoding="utf-8")))
            # Check for companion JSON sidecar: ACTIVE-foo.md → ACTIVE-foo-data.json
            json_sidecar = f.with_name(f.stem + "-data.json")
            if json_sidecar.exists():
                try:
                    thesis_json_sidecars[f.stem] = json.loads(json_sidecar.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Warning: failed to parse thesis sidecar {json_sidecar}: {e}", file=sys.stderr)
    closed_dir = output_dir / "theses" / "closed"
    if closed_dir.exists():
        for f in sorted(closed_dir.glob("*.md")):
            closed_theses.append((f.name, f.read_text(encoding="utf-8")))

    # Read improvement
    improvement = read_file(output_dir / "improvement" / f"{args.week}-improvement.md")

    # Read accuracy tracker (persistent cross-week file)
    accuracy_tracker = read_file(output_dir / "improvement" / "accuracy-tracker.md")

    # Read improvement JSON sidecar (structured data for System Health tab)
    improvement_json = None
    improvement_json_path = output_dir / "improvement" / f"{args.week}-improvement-data.json"
    if improvement_json_path.exists():
        try:
            improvement_json = json.loads(improvement_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: failed to parse {improvement_json_path}: {e}", file=sys.stderr)

    # Read synthesis (for regime data)
    synthesis = read_file(output_dir / "synthesis" / f"{args.week}-synthesis.md")

    # Build historical regime data for all weeks (for the regime trail)
    regime_history = []
    for w in reversed(all_weeks):  # oldest first
        # Try JSON sidecar first, fall back to markdown parsing
        sidecar_path = output_dir / "synthesis" / f"{w}-synthesis-data.json"
        if sidecar_path.exists():
            try:
                sidecar_json = json.loads(sidecar_path.read_text(encoding="utf-8"))
                rd = parse_regime_from_json(sidecar_json)
                rd["week"] = w
                regime_history.append(rd)
                continue
            except Exception:
                pass
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

    # Read Skill 14 Decade Horizon map — prefer JSON sidecar, fall back to markdown
    horizon_map = ""
    horizon_json_data = None
    strategic_dir = output_dir / "strategic"

    # Try JSON sidecar first (stable contract, no parsing needed)
    if strategic_dir.exists():
        json_candidates = [
            strategic_dir / "latest-horizon-data.json",
        ] + sorted(strategic_dir.glob("*-horizon-data.json"), reverse=True)
        for jc in json_candidates:
            if jc.exists() and jc.name != "latest-horizon-data.json" or (jc.name == "latest-horizon-data.json" and jc.exists()):
                try:
                    horizon_json_data = json.loads(jc.read_text(encoding="utf-8"))
                    print(f"Horizon: using JSON sidecar {jc.name}", file=sys.stderr)
                    break
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Warning: failed to parse {jc}: {e}", file=sys.stderr)

    # Fall back to markdown if no JSON sidecar
    if not horizon_json_data:
        horizon_map = read_file(strategic_dir / "latest-horizon-map.md") if strategic_dir.exists() else ""
        if not horizon_map and strategic_dir.exists():
            horizon_files = sorted(strategic_dir.glob("*-horizon-map.md"), reverse=True)
            for hf in horizon_files:
                if hf.name != "latest-horizon-map.md":
                    horizon_map = read_file(hf)
                    if horizon_map:
                        break

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
        horizon_map=horizon_map,
        horizon_json_data=horizon_json_data,
        thesis_json_sidecars=thesis_json_sidecars,
        accuracy_tracker=accuracy_tracker,
        improvement_json=improvement_json,
    )

    # Write output
    out_path = Path(args.out)
    out_path.write_text(html, encoding="utf-8")
    print(f"Dashboard generated: {out_path} ({len(html):,} bytes)")
    print(f"Weeks available: {len(all_weeks)} ({', '.join(all_weeks)})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
