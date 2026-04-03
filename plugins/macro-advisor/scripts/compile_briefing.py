#!/usr/bin/env python3
"""compile_briefing.py — Deterministic synthesis/thesis → briefing JSON compiler.

Reads the synthesis markdown (cross-asset table, sector view, regime data)
and compiled thesis sidecars to produce briefing-data.json deterministically.

Usage:
    python compile_briefing.py                           # compile latest week
    python compile_briefing.py --dry-run                  # show output without writing
    python compile_briefing.py --week 2026-W14
    python compile_briefing.py --outputs-dir /path/to/outputs
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import date, datetime


# ---------------------------------------------------------------------------
# Cross-Asset table parser (markdown table format)
# ---------------------------------------------------------------------------

def parse_cross_asset_table(text: str) -> list[dict]:
    """Parse the Cross-Asset Implications markdown table.

    Expected columns: Asset Class | Stance | ETF Expression | Rationale | Timing
    Maps to canonical JSON keys: what, direction, etfs, recommendation, timing
    """
    rows = []
    in_table = False
    headers = []

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                break  # End of table
            continue

        cells = [c.strip() for c in stripped.split("|")]
        # Remove empty first/last cells from leading/trailing |
        cells = [c for c in cells if c or cells.index(c) not in (0, len(cells) - 1)]
        if not cells:
            continue

        # Skip separator rows (|---|---|...)
        if all(re.match(r'^[-:]+$', c) for c in cells):
            in_table = True
            continue

        if not in_table:
            # This is the header row
            headers = [c.lower().strip() for c in cells]
            continue

        # Data row
        row = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                row[headers[i]] = cell

        # Map to canonical keys (dashboard reads 'why' not 'recommendation')
        canonical = {
            "what": row.get("asset class", row.get("asset", "")),
            "direction": row.get("stance", row.get("direction", row.get("signal", ""))),
            "etfs": _extract_etfs(row.get("etf expression", row.get("etfs", row.get("etf", "")))),
            "conviction": _infer_conviction(row.get("stance", "")),
            "why": row.get("rationale", ""),
            "timing": row.get("timing", ""),
        }
        if canonical["what"]:
            rows.append(canonical)

    return rows


def _extract_etfs(text: str) -> str:
    """Extract ETF tickers from text like 'CSSPX.SW (iShares Core S&P 500) / CSNDX.SW'."""
    tickers = re.findall(r'[A-Z]{2,10}\.SW|[A-Z]{2,5}', text)
    # Filter out common non-ticker words
    noise = {"ETF", "USD", "CHF", "EUR", "GBP", "SW", "SIX", "IMI"}
    return ", ".join(t for t in tickers if t not in noise and len(t) >= 2)


def _infer_conviction(stance: str) -> str:
    """Infer conviction from stance text."""
    lower = stance.lower()
    if "overweight" in lower or "long" in lower:
        return "high" if "strong" in lower else "medium"
    if "underweight" in lower or "short" in lower or "avoid" in lower:
        return "medium"
    if "neutral" in lower or "cautious" in lower:
        return "low"
    return "medium"


# ---------------------------------------------------------------------------
# Sector View parser (prose format with bold sector names)
# ---------------------------------------------------------------------------

def parse_sector_view(text: str) -> list[dict]:
    """Parse sector view from prose format.

    Format: **Sector (Direction):** Description. **Stance:** ... **Reassessment trigger:** ...
    """
    sectors = []

    # Split on bold sector names: **Sector Name (Direction):**
    blocks = re.split(r'(?=\*\*[A-Z][A-Za-z &/]+\s*\()', text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Extract sector name and direction from **Sector (Direction):**
        header_match = re.match(
            r'\*\*([A-Za-z &/]+?)\s*\(([^)]+)\)(?:\s*:)?\*\*[:\s]*(.+)',
            block, re.DOTALL
        )
        if not header_match:
            # Try simpler format: **Sector:** Description
            header_match2 = re.match(
                r'\*\*([A-Za-z &/]+?)\s*:\*\*\s*(.+)',
                block, re.DOTALL
            )
            if header_match2:
                sector_name = header_match2.group(1).strip()
                body = header_match2.group(2).strip()
                direction = ""
            else:
                continue
        else:
            sector_name = header_match.group(1).strip()
            direction = header_match.group(2).strip()
            body = header_match.group(3).strip()

        # Extract stance if present
        stance_match = re.search(r'\*\*Stance:\*\*\s*(.+?)(?:\.\s*\*\*|$)', body)
        if stance_match:
            direction = stance_match.group(1).strip().rstrip(".")

        # Extract rationale (everything before **Stance:**)
        why = re.sub(r'\*\*Stance:\*\*.*', '', body).strip()
        why = re.sub(r'\*\*Reassessment trigger:\*\*.*', '', why).strip()

        # Extract reassessment trigger
        timing = ""
        trigger_match = re.search(r'\*\*Reassessment trigger:\*\*\s*(.+?)(?:\.|$)', body)
        if trigger_match:
            timing = trigger_match.group(1).strip()

        # Extract ETFs from body
        etfs = _extract_etfs(body)

        # Infer conviction from direction keywords
        conviction = "Medium"
        if "overweight" in direction.lower():
            conviction = "High"
        elif "underweight" in direction.lower():
            conviction = "High"
        elif "neutral" in direction.lower():
            conviction = "Low"

        sectors.append({
            "sector": sector_name,
            "direction": direction,
            "conviction": conviction,
            "why": why[:500],  # Truncate long rationales for dashboard display
            "etfs": etfs,
            "timing": timing,
        })

    return sectors


# ---------------------------------------------------------------------------
# Regime parser (from synthesis markdown)
# ---------------------------------------------------------------------------

def parse_regime_from_synthesis(text: str) -> dict:
    """Extract regime data from synthesis markdown."""
    regime = {
        "regime": "Unknown",
        "regime_family": "Unknown",
        "liquidity_condition": "unknown",
        "direction": "Stable",
        "confidence": "Medium",
        "weeks_in_regime": 0,
        "growth_score": 0.0,
        "inflation_score": 0.0,
        "liquidity_score": 0.0,
    }

    # Try to find regime line: **Regime:** Stagflation — Ample Liquidity
    regime_match = re.search(
        r'(?:\*\*)?[Rr]egime(?:\*\*)?[:\s]+([A-Za-z]+(?:\s*[—–]\s*[A-Za-z]+\s*[A-Za-z]*))',
        text
    )
    if regime_match:
        full_label = regime_match.group(1).strip()
        regime["regime"] = full_label
        # Split on em-dash for family + liquidity
        parts = re.split(r'\s*[—–]\s*', full_label)
        regime["regime_family"] = parts[0].strip()
        if len(parts) > 1:
            liq = parts[1].strip().lower()
            regime["liquidity_condition"] = "ample" if "ample" in liq else "tight"

    # Extract scores
    for key, pattern in [
        ("growth_score", r'[Gg]rowth\s+(?:score|axis)[:\s]+([+-]?[\d.]+)'),
        ("inflation_score", r'[Ii]nflation\s+(?:score|axis)[:\s]+([+-]?[\d.]+)'),
        ("liquidity_score", r'[Ll]iquidity\s+(?:score|axis|condition)[:\s]+([+-]?[\d.]+)'),
    ]:
        m = re.search(pattern, text)
        if m:
            try:
                regime[key] = max(-1.0, min(1.0, float(m.group(1))))
            except ValueError:
                pass

    # Weeks in regime
    weeks_match = re.search(r'(\d+)\s+(?:consecutive\s+)?weeks?\s+(?:in\s+|of\s+)?(?:Stagflation|Goldilocks|Overheating|Disinflationary)', text, re.IGNORECASE)
    if weeks_match:
        regime["weeks_in_regime"] = int(weeks_match.group(1))

    # Confidence
    conf_match = re.search(r'[Cc]onfidence[:\s]+(High|Medium|Low)', text)
    if conf_match:
        regime["confidence"] = conf_match.group(1)

    return regime


# ---------------------------------------------------------------------------
# Thesis index builder (from compiled sidecars)
# ---------------------------------------------------------------------------

def build_theses_index(theses_dir: Path) -> dict:
    """Build theses index from compiled JSON sidecars."""
    theses = {}

    for json_path in sorted(theses_dir.glob("*-data.json")):
        try:
            sidecar = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        # Derive slug from filename
        stem = json_path.stem.replace("-data", "")
        slug = stem.replace("ACTIVE-", "").replace("DRAFT-", "")

        trade = sidecar.get("the_trade", {})
        summary = sidecar.get("summary", "")

        theses[slug] = {
            "name": sidecar.get("name", slug.replace("-", " ").title()),
            "status": sidecar.get("status", "DRAFT"),
            "conviction": sidecar.get("conviction", "Unknown"),
            "classification": sidecar.get("classification", "tactical"),
            "direction": _infer_direction(trade, summary),
            "what": summary[:500] if summary else "",
            "recommendation": _first_sentence(trade.get("what_to_buy", "")),
            "kill_switch": _first_sentence(trade.get("when_to_get_out", "")),
            "etfs": _extract_etfs(trade.get("what_to_buy", "")),
            "next_watch": "",  # Would need analyst/watch data
        }

    return theses


def _infer_direction(trade: dict, summary: str) -> str:
    """Infer trade direction from trade details."""
    buy_text = (trade.get("what_to_buy", "") + " " + summary).lower()
    if "reduce" in buy_text or "exit" in buy_text or "avoid" in buy_text or "underweight" in buy_text:
        return "cautious"
    if "overweight" in buy_text or "long" in buy_text or "buy" in buy_text:
        return "long"
    return "neutral"


def _first_sentence(text: str) -> str:
    """Extract first sentence from text."""
    if not text:
        return ""
    # Split on period followed by space and capital letter
    m = re.match(r'(.+?\.)\s+[A-Z]', text)
    if m:
        return m.group(1)
    return text[:200]


# ---------------------------------------------------------------------------
# Main compiler
# ---------------------------------------------------------------------------

def compile_briefing(
    outputs_dir: Path,
    week: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Compile briefing-data.json from synthesis markdown + compiled sidecars."""

    # Find latest synthesis file
    synthesis_dir = outputs_dir / "synthesis"
    if week:
        synthesis_path = synthesis_dir / f"{week}-synthesis.md"
    else:
        # Find latest
        candidates = sorted(synthesis_dir.glob("*-synthesis.md"), reverse=True)
        synthesis_path = candidates[0] if candidates else None

    if not synthesis_path or not synthesis_path.exists():
        print(f"ERROR: Synthesis file not found: {synthesis_path}", file=sys.stderr)
        sys.exit(1)

    # Detect week from filename
    if not week:
        week_match = re.search(r'(\d{4}-W\d{2})', synthesis_path.name)
        week = week_match.group(1) if week_match else "Unknown"

    synthesis_text = synthesis_path.read_text(encoding="utf-8")

    # Also try to load synthesis-data.json for regime scores
    synthesis_json_path = synthesis_dir / f"{week}-synthesis-data.json"
    synthesis_json = None
    if synthesis_json_path.exists():
        try:
            synthesis_json = json.loads(synthesis_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Parse regime data
    regime = parse_regime_from_synthesis(synthesis_text)

    # Override with synthesis JSON if available (more precise scores)
    if synthesis_json and "regime" in synthesis_json:
        rj = synthesis_json["regime"]
        regime["regime"] = rj.get("regime", regime["regime"])
        regime["regime_family"] = rj.get("regime_family", rj.get("quadrant", regime["regime_family"]))
        regime["liquidity_condition"] = rj.get("liquidity_condition", regime["liquidity_condition"])
        for key in ("growth_score", "inflation_score", "liquidity_score"):
            if rj.get(key) is not None:
                regime[key] = rj[key]
        if rj.get("weeks_held"):
            regime["weeks_in_regime"] = rj["weeks_held"]
        if rj.get("direction"):
            regime["direction"] = rj["direction"]
        if rj.get("confidence"):
            regime["confidence"] = rj["confidence"]

    # Parse cross-asset table
    cross_asset = parse_cross_asset_table(synthesis_text)

    # Parse sector view
    # Find the sector view section
    sector_match = re.search(r'## Sector View\s*\n(.*?)(?=\n## |\Z)', synthesis_text, re.DOTALL)
    sector_text = sector_match.group(1) if sector_match else ""
    sector_view = parse_sector_view(sector_text)

    # Build theses index from compiled sidecars
    theses_dir = outputs_dir / "theses" / "active"
    theses = build_theses_index(theses_dir)

    # Assemble briefing data
    briefing = {
        "meta": {
            "skill": "monday-morning-briefing",
            "skill_version": "9.3-compiled",
            "run_date": str(date.today()),
            "week": week,
            "briefing_type": "dashboard_data",
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "regime": regime["regime"],
            "regime_family": regime["regime_family"],
            "liquidity_condition": regime["liquidity_condition"],
            "regime_weeks": regime["weeks_in_regime"],
            "regime_confidence": regime["confidence"],
            "growth_score": regime["growth_score"],
            "inflation_score": regime["inflation_score"],
            "liquidity_score": regime["liquidity_score"],
        },
        "regime": regime,
        "cross_asset": cross_asset,
        "sector_view": sector_view,
        "theses": theses,
    }

    # Write output
    briefings_dir = outputs_dir / "briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)
    output_path = briefings_dir / f"{week}-briefing-data.json"

    if dry_run:
        print(json.dumps(briefing, indent=2, ensure_ascii=False)[:3000])
        print(f"\n... [truncated for display]")
        print(f"\nWould write to: {output_path}")
        print(f"  cross_asset: {len(cross_asset)} items")
        print(f"  sector_view: {len(sector_view)} items")
        print(f"  theses: {len(theses)} entries ({sum(1 for t in theses.values() if t['status'] == 'ACTIVE')} ACTIVE, {sum(1 for t in theses.values() if t['status'] == 'DRAFT')} DRAFT)")
    else:
        output_path.write_text(
            json.dumps(briefing, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Compiled briefing: {output_path}")
        print(f"  cross_asset: {len(cross_asset)} items")
        print(f"  sector_view: {len(sector_view)} items")
        print(f"  theses: {len(theses)} entries ({sum(1 for t in theses.values() if t['status'] == 'ACTIVE')} ACTIVE, {sum(1 for t in theses.values() if t['status'] == 'DRAFT')} DRAFT)")

    return briefing


def main():
    parser = argparse.ArgumentParser(
        description="Compile briefing-data.json from synthesis + thesis sidecars"
    )
    parser.add_argument("--outputs-dir", type=Path, default=None)
    parser.add_argument("--week", type=str, default=None, help="Week label (e.g., 2026-W14)")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    outputs_dir = args.outputs_dir
    if outputs_dir is None:
        candidates = [
            Path.home() / "Macro investment" / "outputs",
            Path(__file__).parent.parent / "outputs",
        ]
        for c in candidates:
            if c.exists():
                outputs_dir = c
                break
        if outputs_dir is None:
            print("ERROR: Cannot find outputs directory. Use --outputs-dir.", file=sys.stderr)
            sys.exit(1)

    compile_briefing(outputs_dir, week=args.week, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
