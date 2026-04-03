#!/usr/bin/env python3
"""compile_sidecars.py — Deterministic thesis markdown → JSON sidecar compiler.

Replaces LLM-generated sidecars with mechanically extracted JSON.
Reads thesis markdown files, extracts structured data by heading,
and writes JSON sidecars that are 1:1 with the markdown content.

Usage:
    python compile_sidecars.py                           # compile all theses
    python compile_sidecars.py --dry-run                  # show what would change
    python compile_sidecars.py --thesis ACTIVE-credit-equity-disconnect
    python compile_sidecars.py --theses-dir /path/to/theses/active
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import date
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Markdown section splitter
# ---------------------------------------------------------------------------

def split_sections(text: str) -> dict[str, str]:
    """Split markdown into sections keyed by heading text.

    Returns a dict like:
        {"Summary": "paragraph...", "The Bet": "paragraph...", ...}

    Handles ## and ### headings. For ### headings nested under ## headings,
    the key is just the ### text (e.g., "Mechanism", not "Why It Works > Mechanism").

    Special case: some files have the heading and content on the same line
    (e.g., "## Where The Market Stands The market is..."). We detect this
    and separate heading from content.
    """
    sections: dict[str, str] = {}
    # Also capture the preamble (everything before the first ## heading)
    sections["_preamble"] = ""

    current_key = "_preamble"
    lines = text.split("\n")

    for line in lines:
        # Skip # and ### title headings (go into preamble)
        if re.match(r'^#{1}\s+', line) and not re.match(r'^#{2}', line):
            sections["_preamble"] += line + "\n"
            continue
        # Some files use ### for the title heading (e.g., ### STRUCTURAL THESIS CANDIDATE:)
        if re.match(r'^#{3}\s+(?:STRUCTURAL\s+THESIS|THESIS|ACTIVE\s+THESIS)', line, re.IGNORECASE):
            sections["_preamble"] += line + "\n"
            continue

        # Match headings: ## or ###
        m = re.match(r'^(#{2,3})\s+(.+)$', line)
        if m:
            heading_text = m.group(2).strip()

            # Known heading names — used to detect inline content
            known_headings = [
                "Summary", "The Bet", "Why It Works", "Mechanism",
                "What Can't Change", "What Has To Stay True",
                "Where The Market Stands", "What Could Break It",
                "The Trade", "What to buy", "When to buy more",
                "When to buy", "When to get out", "How long",
                "External Views", "Relationship to Existing Theses",
                "ADDITIONAL POSITIONING NOTES FOR SIX USER",
            ]

            # First check for exact match (no inline content)
            if heading_text in known_headings:
                current_key = heading_text
                sections[current_key] = ""
                continue

            # Check if content is on the same line as the heading
            # Sort by length descending to match longer headings first
            # (prevents "When to buy" matching "When to buy more")
            matched_heading = None
            for kh in sorted(known_headings, key=len, reverse=True):
                if heading_text.startswith(kh) and len(heading_text) > len(kh) + 1:
                    matched_heading = kh
                    break

            if matched_heading:
                current_key = matched_heading
                # Content after the heading name
                inline_content = heading_text[len(matched_heading):].strip()
                sections[current_key] = inline_content + "\n"
            else:
                current_key = heading_text
                sections[current_key] = ""
        else:
            sections[current_key] = sections.get(current_key, "") + line + "\n"

    # Strip trailing whitespace from all sections
    return {k: v.strip() for k, v in sections.items()}


# ---------------------------------------------------------------------------
# Metadata extractors (from preamble **Key:** Value lines)
# ---------------------------------------------------------------------------

def extract_meta(preamble: str, key: str) -> str | None:
    """Extract a **Key:** Value metadata field from the preamble."""
    # Match **Key:** Value or *Key:* Value
    pattern = rf'\*\*{re.escape(key)}:\*\*\s*(.+)'
    m = re.search(pattern, preamble)
    if m:
        return m.group(1).strip()
    # Also try *Key:* format
    pattern2 = rf'\*{re.escape(key)}:\*\s*(.+)'
    m2 = re.search(pattern2, preamble)
    if m2:
        return m2.group(1).strip()
    return None


def extract_status(preamble: str, filename: str = "") -> str:
    """Extract thesis status (ACTIVE or DRAFT) from preamble or filename."""
    raw = extract_meta(preamble, "Status") or ""
    if "ACTIVE" in raw.upper():
        return "ACTIVE"
    if "DRAFT" in raw.upper():
        return "DRAFT"
    # Fallback to filename
    if filename.upper().startswith("ACTIVE"):
        return "ACTIVE"
    if filename.upper().startswith("DRAFT"):
        return "DRAFT"
    return "DRAFT"


def extract_conviction(preamble: str, sections: dict[str, str]) -> str:
    """Extract clean conviction level, stripping parenthetical qualifiers.

    Looks in preamble metadata first, then in trade section (*Thesis conviction:*),
    then falls back to section content.
    """
    raw = extract_meta(preamble, "Conviction") or ""

    # Also check for *Thesis conviction:* in The Trade section or nearby
    if not raw:
        trade_text = sections.get("The Trade", "")
        m = re.search(r'\*Thesis conviction:\*\s*(\w[\w\-]*)', trade_text)
        if m:
            raw = m.group(1)

    if not raw:
        # Check all sections for **Conviction:** pattern
        for text in sections.values():
            m = re.search(r'\*\*Conviction:\*\*\s*(\w[\w\-]*)', text)
            if m:
                raw = m.group(1)
                break

    # Clean: strip parenthetical qualifiers like "High (tactical)"
    cleaned = re.sub(r'\s*\(.*?\)', '', raw).strip()

    # Normalize to title case
    if cleaned.lower() in ("high", "medium-high", "medium", "low-medium", "low"):
        return cleaned.title()

    return cleaned or "Unknown"


def infer_classification(filename: str, preamble: str) -> str:
    """Infer thesis classification from filename or preamble."""
    raw = extract_meta(preamble, "Classification") or ""
    if raw.lower() in ("structural", "tactical"):
        return raw.lower()
    # Infer from title line
    if "STRUCTURAL" in preamble.upper():
        return "structural"
    if "structural" in filename.lower() and "ACTIVE-structural" in filename:
        return "structural"
    return "tactical"


# ---------------------------------------------------------------------------
# Content parsers
# ---------------------------------------------------------------------------

_VALID_STATUSES = {
    "INTACT", "DEVELOPING", "UNDER PRESSURE", "WEAKENING",
    "STRENGTHENING", "WATCH", "BROKEN", "INVALIDATED", "FAILED",
}


def parse_numbered_items(text: str) -> list[str]:
    """Parse a numbered list into individual item strings.

    Handles multi-line items where continuation lines are not numbered.
    Sub-items (indented bullets like `   - **Test:**`) are folded into
    their parent numbered item.
    """
    if not text.strip():
        return []

    items: list[str] = []
    current_item = ""

    for line in text.split("\n"):
        # Match top-level numbered item: 1. or 1) (NOT indented sub-bullets)
        if re.match(r'^\d+[\.\)]\s+', line):
            if current_item:
                items.append(current_item.strip())
            # Strip the number prefix
            current_item = re.sub(r'^\d+[\.\)]\s+', '', line)
        elif re.match(r'^[-*]\s+\*\*[A-Z]', line) and not current_item:
            # Top-level bullet with bold start (alternate list format, no numbers)
            if current_item:
                items.append(current_item.strip())
            current_item = re.sub(r'^[-*]\s+', '', line)
        elif line.strip() and current_item:
            # Continuation line or sub-bullet — fold into current item
            current_item += " " + line.strip()

    if current_item:
        items.append(current_item.strip())

    return items


def parse_mechanism(text: str) -> list[dict]:
    """Parse mechanism section into array of {step, link, quantified, source}."""
    items = parse_numbered_items(text)
    result = []
    for i, item in enumerate(items, 1):
        # Try to extract bold title: **Title.** Rest of text
        m = re.match(r'\*\*(.+?)\*\*\s*[—–\-]?\s*(.*)', item, re.DOTALL)
        if m:
            link = m.group(1).strip().rstrip('.') + ". " + m.group(2).strip()
        else:
            link = item

        # Try to extract quantified data (numbers, percentages, dollar amounts)
        quant_parts = re.findall(
            r'(?:[\$€£][\d,.]+[BMTKbmtk]?|[\d,.]+%|[\d,.]+\s*(?:bp|bps|tonnes?|GW|TWh|MW|B/d|b/d))',
            link
        )
        quantified = "; ".join(quant_parts[:5]) if quant_parts else ""

        # Try to extract source references (— Source, Year)
        source_match = re.search(r'—\s*([^—]+?)(?:\.|$)', link)
        source = source_match.group(1).strip() if source_match else ""

        result.append({
            "step": i,
            "link": link,
            "quantified": quantified,
            "source": source,
        })
    return result


def parse_assumptions(text: str) -> list[dict]:
    """Parse 'What Has To Stay True' into array of assumption objects.

    Each item gets: text, testable_by, status, current_status_detail.
    """
    items = parse_numbered_items(text)
    result = []
    for item in items:
        # Extract testable_by if present (after "Testable by:" or "— Testable by:")
        testable_by = ""
        tb_match = re.search(r'[—–\-]\s*[Tt]estable\s+by:\s*(.+?)(?:\.\s*[A-Z]|$)', item)
        if tb_match:
            testable_by = tb_match.group(1).strip().rstrip('.')

        # Extract status keywords (usually at end: "Current status: INTACT")
        status = "INTACT"  # default
        for s in _VALID_STATUSES:
            if s in item.upper():
                status = s
                break

        # Also check for "Current status: X" or "status: X"
        status_match = re.search(
            r'(?:[Cc]urrent\s+)?[Ss]tatus:\s*(\w[\w\s]*?)(?:\s*[\(\.]|$)',
            item
        )
        if status_match:
            raw_status = status_match.group(1).strip().upper()
            for s in _VALID_STATUSES:
                if s in raw_status:
                    status = s
                    break

        # Extract the core assumption text (before testable_by or status annotations)
        core_text = item
        # Remove testable_by portion
        core_text = re.sub(r'\s*[—–\-]\s*[Tt]estable\s+by:.*', '', core_text)
        # Remove "Current status: ..." portion
        core_text = re.sub(r'\s*[—–\-]?\s*[Cc]urrent\s+status:.*', '', core_text)
        core_text = core_text.strip().rstrip('.')

        result.append({
            "text": core_text,
            "testable_by": testable_by,
            "status": status,
        })

    return result


def parse_what_cant_change(text: str) -> list[dict]:
    """Parse structural 'What Can't Change' into constraint objects."""
    items = parse_numbered_items(text)
    result = []
    for item in items:
        # Extract source (after — or --)
        source = ""
        source_match = re.search(r'[—–]\s*([^—–]+?)(?:\.|$)', item)
        if source_match:
            source = source_match.group(1).strip().rstrip('.')

        # Extract quantified data
        quant_parts = re.findall(
            r'(?:[\$€£][\d,.]+[BMTKbmtk]?|[\d,.]+%|[\d,.]+\s*(?:bp|bps|tonnes?|GW|TWh|MW))',
            item
        )
        quantified = "; ".join(quant_parts[:5]) if quant_parts else ""

        # Core constraint text (first sentence or before source citation)
        constraint = re.sub(r'\s*[—–]\s*[A-Z].*', '', item).strip()

        result.append({
            "constraint": constraint,
            "quantified": quantified,
            "source": source,
        })

    return result


def parse_what_could_break_it(text: str) -> dict | None:
    """Parse 'What Could Break It' into stress test object."""
    if not text.strip():
        return None

    lines = text.strip()

    # Extract strongest counter-argument (first paragraph or **Strongest counter-argument:**)
    strongest = ""
    sc_match = re.search(
        r'\*\*[Ss]trongest\s+counter[\s-]*argument:\*\*\s*(.+?)(?=\n\s*[-*]\s+\*\*[Kk]ey\s+risk|\n\s*[-*]\s+\*\*Assessment|\Z)',
        lines, re.DOTALL
    )
    if sc_match:
        strongest = sc_match.group(1).strip()
    else:
        # First paragraph
        paras = lines.split("\n\n")
        if paras:
            strongest = paras[0].strip()

    # Extract key risks
    risks = []
    for m in re.finditer(
        r'[-*]\s+\*\*[Kk]ey\s+risk\s*\d*:\*\*\s*(.+?)(?=\n\s*[-*]\s+\*\*|$)',
        lines, re.DOTALL
    ):
        risk_text = m.group(1).strip()
        prob_match = re.search(r'[Pp]robability:\s*(.+?)(?:\.|$)', risk_text)
        probability = prob_match.group(1).strip() if prob_match else "Unknown"
        risks.append({
            "risk": risk_text,
            "probability": probability,
        })

    # Extract post-test conviction
    post_conviction = ""
    pc_match = re.search(
        r'\*\*[Aa]ssessment\s+after\s+(?:considering\s+)?contrarian\s+case:\*\*\s*(.+)',
        lines
    )
    if pc_match:
        post_conviction = pc_match.group(1).strip()

    return {
        "strongest_counter": strongest,
        "key_risks": risks,
        "post_test_conviction": post_conviction,
    }


def parse_external_views(text: str) -> list[dict]:
    """Parse External Views section into structured entries."""
    if not text.strip():
        return []

    entries = []
    # Split on ### subheadings or **Analyst Name:** patterns
    blocks = re.split(r'(?=^###\s+|\*\*[A-Z])', text, flags=re.MULTILINE)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Extract analyst name
        name_match = re.match(r'(?:###\s+)?(?:\d{4}-\d{2}-\d{2}\s*[—–]\s*)?(.+?)(?:\n|$)', block)
        if not name_match:
            continue

        name = name_match.group(1).strip().strip('*')

        # Extract quote
        quote = ""
        quote_match = re.search(r'[-*]\s*[Qq]uote:\s*(.+?)(?=\n\s*[-*]\s*[A-Z]|\Z)', block, re.DOTALL)
        if quote_match:
            quote = quote_match.group(1).strip()

        # Extract alignment
        alignment = ""
        align_match = re.search(r'[Tt]hesis\s+alignment:\s*(.+?)(?:\n|$)', block)
        if align_match:
            alignment = align_match.group(1).strip()

        if name and len(name) > 3:
            entries.append({
                "analyst": name,
                "quote_summary": quote[:200] if quote else "",
                "alignment": alignment,
            })

    return entries


# ---------------------------------------------------------------------------
# Change log generation (diff-based)
# ---------------------------------------------------------------------------

def generate_changelog_entry(
    old_sidecar: dict | None,
    new_sidecar: dict,
    today: str,
) -> dict:
    """Generate a changelog entry by diffing old and new sidecars."""
    if old_sidecar is None:
        return {"date": today, "changes": "Initial compilation from markdown"}

    changes = []

    # Check assumption status changes
    old_assumptions = {a.get("text", "")[:60]: a.get("status", "") for a in old_sidecar.get("what_has_to_stay_true", [])}
    new_assumptions = {a.get("text", "")[:60]: a.get("status", "") for a in new_sidecar.get("what_has_to_stay_true", [])}

    for key, new_status in new_assumptions.items():
        old_status = old_assumptions.get(key, "")
        if old_status and old_status != new_status:
            short_key = key[:40] + "..." if len(key) > 40 else key
            changes.append(f'Assumption "{short_key}" status: {old_status} → {new_status}')

    # Count changes
    old_count = len(old_sidecar.get("what_has_to_stay_true", []))
    new_count = len(new_sidecar.get("what_has_to_stay_true", []))
    if old_count != new_count:
        changes.append(f"Assumption count: {old_count} → {new_count}")

    # Conviction change
    old_conv = old_sidecar.get("conviction", "")
    new_conv = new_sidecar.get("conviction", "")
    if old_conv and old_conv != new_conv:
        changes.append(f"Conviction: {old_conv} → {new_conv}")

    # Status change
    old_status = old_sidecar.get("status", "")
    new_status = new_sidecar.get("status", "")
    if old_status and old_status != new_status:
        changes.append(f"Status: {old_status} → {new_status}")

    if not changes:
        changes.append("Recompiled from markdown (no content changes)")

    return {"date": today, "changes": "; ".join(changes)}


# ---------------------------------------------------------------------------
# Main compiler
# ---------------------------------------------------------------------------

def compile_thesis(md_path: Path, output_dir: Path | None = None) -> dict:
    """Compile a single thesis markdown file into a JSON sidecar dict."""
    text = md_path.read_text(encoding="utf-8")
    sections = split_sections(text)
    preamble = sections.get("_preamble", "")

    # Infer name from filename
    stem = md_path.stem  # e.g., "ACTIVE-credit-equity-disconnect"
    slug = stem.replace("ACTIVE-", "").replace("DRAFT-", "")
    clean_name = slug.replace("-", " ").title()

    status = extract_status(preamble, stem)
    classification = infer_classification(stem, preamble)

    # Build the sidecar
    sidecar: dict = {
        "name": clean_name,
        "status": status,
        "classification": classification,
        "generated": extract_meta(preamble, "Generated") or extract_meta(preamble, "Activated") or "",
        "updated": extract_meta(preamble, "Updated") or str(date.today()),
        "provenance": extract_meta(preamble, "Provenance") or "",
        "conviction": extract_conviction(preamble, sections),
        "summary": sections.get("Summary", ""),
        "the_bet": sections.get("The Bet", ""),
        "mechanism": parse_mechanism(sections.get("Mechanism", "")),
        "what_has_to_stay_true": parse_assumptions(sections.get("What Has To Stay True", "")),
        "where_the_market_stands": sections.get("Where The Market Stands") or None,
        "the_trade": {
            "what_to_buy": sections.get("What to buy", ""),
            "when_to_buy_more": sections.get("When to buy more", ""),
            "when_to_buy": sections.get("When to buy", ""),
            "when_to_get_out": sections.get("When to get out", ""),
            "how_long": sections.get("How long", ""),
        },
    }

    # Structural-only fields
    if classification == "structural":
        sidecar["what_cant_change"] = parse_what_cant_change(
            sections.get("What Can't Change", "")
        )
        sidecar["what_could_break_it"] = parse_what_could_break_it(
            sections.get("What Could Break It", "")
        )
    else:
        sidecar["what_cant_change"] = None
        sidecar["what_could_break_it"] = None

    # External views (not rendered from sidecar in dashboard, but useful for completeness)
    ext_views = sections.get("External Views", "")
    if ext_views and ext_views != "(Not yet populated - new thesis)":
        sidecar["external_views_present"] = True
    else:
        sidecar["external_views_present"] = False

    # Load previous sidecar for change_log continuity and conviction fallback
    sidecar_path = (output_dir or md_path.parent) / f"{stem}-data.json"
    old_sidecar = None
    old_changelog: list[dict] = []
    if sidecar_path.exists():
        try:
            old_sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            old_changelog = old_sidecar.get("change_log", [])
        except (json.JSONDecodeError, OSError):
            pass

    # Conviction fallback: if markdown has no conviction, use existing sidecar's value
    if sidecar.get("conviction") == "Unknown" and old_sidecar:
        old_conv = old_sidecar.get("conviction", "")
        if old_conv:
            # Clean it
            sidecar["conviction"] = re.sub(r'\s*\(.*?\)', '', old_conv).strip() or "Unknown"

    # Generate change_log
    today = sidecar.get("updated") or str(date.today())
    new_entry = generate_changelog_entry(old_sidecar, sidecar, today)

    # Dedupe: don't add entry if same date already exists with same content
    if old_changelog and old_changelog[-1].get("date") == today:
        # Replace today's entry (recompilation)
        sidecar["change_log"] = old_changelog[:-1] + [new_entry]
    else:
        sidecar["change_log"] = old_changelog + [new_entry]

    return sidecar


def compile_all(
    theses_dir: Path,
    output_dir: Path | None = None,
    dry_run: bool = False,
    single_thesis: str | None = None,
) -> list[tuple[str, dict, bool]]:
    """Compile all thesis markdown files in the directory.

    Returns list of (filename, sidecar_dict, changed) tuples.
    """
    results = []
    md_files = sorted(theses_dir.glob("*.md"))

    if single_thesis:
        # Filter to single thesis
        md_files = [f for f in md_files if single_thesis in f.stem]

    for md_path in md_files:
        stem = md_path.stem
        sidecar_path = (output_dir or theses_dir) / f"{stem}-data.json"

        sidecar = compile_thesis(md_path, output_dir)

        # Check if changed
        changed = True
        if sidecar_path.exists():
            try:
                existing = json.loads(sidecar_path.read_text(encoding="utf-8"))
                # Compare without change_log (it's expected to differ)
                existing_cmp = {k: v for k, v in existing.items() if k != "change_log"}
                new_cmp = {k: v for k, v in sidecar.items() if k != "change_log"}
                changed = json.dumps(existing_cmp, sort_keys=True) != json.dumps(new_cmp, sort_keys=True)
            except (json.JSONDecodeError, OSError):
                changed = True

        if not dry_run and changed:
            sidecar_path.write_text(
                json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        results.append((stem, sidecar, changed))

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compile thesis markdown files into JSON sidecars"
    )
    parser.add_argument(
        "--theses-dir",
        type=Path,
        default=None,
        help="Directory containing thesis .md files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files",
    )
    parser.add_argument(
        "--thesis",
        type=str,
        default=None,
        help="Compile a single thesis by stem name (e.g., ACTIVE-credit-equity-disconnect)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed field-by-field output",
    )

    args = parser.parse_args()

    # Default theses directory — try common locations
    theses_dir = args.theses_dir
    if theses_dir is None:
        candidates = [
            Path.home() / "Macro investment" / "outputs" / "theses" / "active",
            Path(__file__).parent.parent / "outputs" / "theses" / "active",
        ]
        for c in candidates:
            if c.exists():
                theses_dir = c
                break
        if theses_dir is None:
            print("ERROR: Cannot find theses directory. Use --theses-dir.", file=sys.stderr)
            sys.exit(1)

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Compiling sidecars from: {theses_dir}")
    print()

    results = compile_all(
        theses_dir=theses_dir,
        dry_run=args.dry_run,
        single_thesis=args.thesis,
    )

    # Report
    compiled = 0
    unchanged = 0
    for stem, sidecar, changed in results:
        status_icon = "+" if changed else "="
        print(f"  {status_icon} {stem}")

        if args.verbose and changed:
            print(f"      status={sidecar['status']}  conviction={sidecar['conviction']}  classification={sidecar['classification']}")
            print(f"      summary={len(sidecar.get('summary', ''))} chars")
            print(f"      the_bet={len(sidecar.get('the_bet', ''))} chars")
            print(f"      mechanism={len(sidecar.get('mechanism', []))} steps")
            print(f"      assumptions={len(sidecar.get('what_has_to_stay_true', []))} items")
            print(f"      where_the_market_stands={'present' if sidecar.get('where_the_market_stands') else 'missing'}")
            trade = sidecar.get("the_trade", {})
            print(f"      the_trade: what_to_buy={len(trade.get('what_to_buy', ''))} chars, "
                  f"when_to_get_out={len(trade.get('when_to_get_out', ''))} chars")
            print(f"      change_log={len(sidecar.get('change_log', []))} entries")
            print()

        if changed:
            compiled += 1
        else:
            unchanged += 1

    print()
    action = "Would compile" if args.dry_run else "Compiled"
    print(f"{action}: {compiled} files  |  Unchanged: {unchanged} files  |  Total: {len(results)}")

    if args.dry_run and compiled > 0:
        print("\nRun without --dry-run to write files.")


if __name__ == "__main__":
    main()
