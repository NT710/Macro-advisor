#!/usr/bin/env python3
"""
One-time migration: generate horizon JSON sidecar from legacy markdown.

Skill 14's first run (2026-03-23) predated the JSON sidecar spec, producing
only the markdown horizon map and last-horizon.json tracker. This script
backfills the missing latest-horizon-data.json so that refresh_blind_spots.py
can operate weekly instead of waiting for the next quarterly Skill 14 run.

Usage:
    python migrate_horizon_sidecar.py --output-dir outputs/
    python migrate_horizon_sidecar.py --output-dir outputs/ --dry-run
"""

import argparse
import json
import sys
from pathlib import Path

# Import the existing markdown parser from the dashboard generator
from generate_dashboard import parse_horizon_map


def reshape_causal_chains(force: dict) -> dict:
    """Reshape parse_horizon_map() causal chain format to sidecar contract format.

    parse_horizon_map() returns:
        causal_chains = {"first_order": {chain, direction, consensus, timeline}, ...}

    Sidecar contract (and refresh_blind_spots.py) expects:
        causal_chains = {"first_order": [{impact, direction, consensus}], ...}

    The key rename is: "chain" -> "impact".
    Each order becomes a single-element array.
    """
    raw_chains = force.get("causal_chains", {})
    if not raw_chains:
        return {"first_order": [], "second_order": [], "third_order": []}

    reshaped = {}
    for order in ("first_order", "second_order", "third_order"):
        entry = raw_chains.get(order)
        if entry and isinstance(entry, dict):
            reshaped[order] = [{
                "impact": entry.get("chain", ""),
                "direction": entry.get("direction", ""),
                "consensus": entry.get("consensus", ""),
                "timeline": entry.get("timeline", ""),
            }]
        elif entry and isinstance(entry, list):
            # Already in array format
            reshaped[order] = entry
        else:
            reshaped[order] = []

    return reshaped


def migrate(output_dir: Path, dry_run: bool = False):
    strategic_dir = output_dir / "strategic"

    # Check if sidecar already exists
    latest_path = strategic_dir / "latest-horizon-data.json"
    if latest_path.exists():
        print(f"Sidecar already exists: {latest_path}", file=sys.stderr)
        print("Nothing to migrate.", file=sys.stderr)
        return

    # Find the markdown horizon map
    md_path = strategic_dir / "latest-horizon-map.md"
    if not md_path.exists():
        # Try dated files
        candidates = sorted(strategic_dir.glob("*-horizon-map.md"), reverse=True)
        for c in candidates:
            if c.name != "latest-horizon-map.md":
                md_path = c
                break

    if not md_path.exists():
        print("ERROR: No horizon markdown map found.", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing: {md_path.name} ({md_path.stat().st_size:,} bytes)", file=sys.stderr)

    # Parse markdown using existing dashboard parser
    md_text = md_path.read_text(encoding="utf-8")
    parsed = parse_horizon_map(md_text)

    if not parsed or not parsed.get("forces"):
        print("ERROR: parse_horizon_map returned no forces.", file=sys.stderr)
        sys.exit(1)

    # Reshape causal chains from flat dicts to arrays of impact objects
    for force in parsed["forces"]:
        force["causal_chains"] = reshape_causal_chains(force)

    # Enrich meta from last-horizon.json (has richer data than markdown meta block)
    tracker_path = strategic_dir / "last-horizon.json"
    if tracker_path.exists():
        tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
        meta = parsed.setdefault("meta", {})

        # Merge tracker fields that aren't in the markdown meta
        meta.setdefault("last_run_date", tracker.get("last_run_date", ""))
        meta.setdefault("last_run_quarter", tracker.get("last_run_quarter", ""))
        meta.setdefault("run_type", tracker.get("run_type", ""))
        meta["mega_forces_mapped"] = tracker.get("mega_forces_count", len(parsed["forces"]))
        meta["mega_forces_changed"] = tracker.get("mega_forces_changed", [])
        meta["blind_spots_identified"] = tracker.get("blind_spots_identified", len(parsed["blind_spots"]))
        meta["blind_spots_actionable"] = tracker.get("blind_spots_actionable", 0)
        meta["blind_spots_flagged_for_scanner"] = tracker.get("blind_spots_flagged_scanner", 0)
        meta["blind_spots_flagged_for_research"] = tracker.get("blind_spots_flagged_research", 0)

        # Preserve quality and bias checks
        if "confirmation_bias_checks" in tracker:
            meta["confirmation_bias_checks"] = tracker["confirmation_bias_checks"]
        if "blind_spots_by_priority" in tracker:
            meta["blind_spots_by_priority"] = tracker["blind_spots_by_priority"]

        # Use mega-force names from tracker if available (list vs count)
        if isinstance(tracker.get("mega_forces_mapped"), list):
            meta["mega_forces_names"] = tracker["mega_forces_mapped"]

        quarter = tracker.get("last_run_quarter", "")
    else:
        quarter = ""
        print("Warning: last-horizon.json not found, meta will be sparse.", file=sys.stderr)

    # Count impacts for summary
    total_impacts = 0
    for force in parsed["forces"]:
        chains = force.get("causal_chains", {})
        for order in ("first_order", "second_order", "third_order"):
            total_impacts += len(chains.get(order, []))

    # Summary
    print(f"\nMigration summary:", file=sys.stderr)
    print(f"  Forces:      {len(parsed['forces'])}", file=sys.stderr)
    print(f"  Blind spots: {len(parsed['blind_spots'])}", file=sys.stderr)
    print(f"  Impacts:     {total_impacts} (across all causal chain orders)", file=sys.stderr)
    print(f"  Quarter:     {quarter or 'unknown'}", file=sys.stderr)

    if dry_run:
        print(f"\n--- DRY RUN: would write to ---", file=sys.stderr)
        if quarter:
            print(f"  {strategic_dir / f'{quarter}-horizon-data.json'}", file=sys.stderr)
        print(f"  {latest_path}", file=sys.stderr)
        print(f"\n--- JSON preview (first 200 lines) ---")
        preview = json.dumps(parsed, indent=2, ensure_ascii=False)
        lines = preview.split("\n")
        print("\n".join(lines[:200]))
        if len(lines) > 200:
            print(f"\n... ({len(lines) - 200} more lines)")
        return

    # Write dated copy
    if quarter:
        dated_path = strategic_dir / f"{quarter}-horizon-data.json"
        dated_path.write_text(
            json.dumps(parsed, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote: {dated_path}", file=sys.stderr)

    # Write latest
    latest_path.write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote: {latest_path}", file=sys.stderr)
    print(f"\nMigration complete. Blind spot refresh should now work.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Migrate horizon markdown to JSON sidecar")
    parser.add_argument("--output-dir", required=True, help="Workspace outputs directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    args = parser.parse_args()

    migrate(Path(args.output_dir), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
