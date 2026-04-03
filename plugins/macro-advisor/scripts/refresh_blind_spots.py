#!/usr/bin/env python3
"""
Blind Spot Coverage Refresh

Lightweight weekly check that re-evaluates whether the active thesis book
covers the causal chain impacts identified in the quarterly Decade Horizon
(Skill 14). Updates latest-horizon-data.json blind_spots array and meta counts.

This script handles the STRUCTURAL part: reading files, writing updates,
logging. The SEMANTIC coverage comparison is done by the LLM skill step
that invokes this script's output as input.

Usage:
    python refresh_blind_spots.py --output-dir outputs/

Outputs:
    - Reads: outputs/strategic/latest-horizon-data.json
    - Reads: outputs/theses/active/*.md
    - Writes: outputs/strategic/blind-spot-refresh-context.json
      (context file for the LLM skill step to read and evaluate)
    - After LLM evaluation, call with --apply to write back:
      python refresh_blind_spots.py --output-dir outputs/ --apply refresh-result.json
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path


def gather_context(output_dir: Path) -> dict:
    """Gather horizon data + active theses into a context file for LLM evaluation."""

    strategic_dir = output_dir / "strategic"
    theses_dir = output_dir / "theses" / "active"

    # Read horizon data
    horizon_path = strategic_dir / "latest-horizon-data.json"
    if not horizon_path.exists():
        print("No horizon data found. Skill 14 has not run yet. Skipping.", file=sys.stderr)
        return {}

    horizon_data = json.loads(horizon_path.read_text(encoding="utf-8"))

    forces = horizon_data.get("forces", [])
    if not forces:
        print("No mega-forces in horizon data. Nothing to refresh.", file=sys.stderr)
        return {}

    # Extract second and third-order impacts from causal chains
    impacts_to_check = []
    for force in forces:
        chains = force.get("causal_chains", {})
        for order in ["second_order", "third_order"]:
            for impact in chains.get(order, []):
                impacts_to_check.append({
                    "force_name": force["name"],
                    "order": order,
                    "impact": impact.get("impact", ""),
                    "direction": impact.get("direction", ""),
                    "consensus": impact.get("consensus", ""),
                })

    if not impacts_to_check:
        print("No second/third-order impacts to check. Blind spot refresh not needed.", file=sys.stderr)
        return {}

    # Read active theses (names + summaries for LLM matching)
    theses = []
    if theses_dir.exists():
        for f in sorted(theses_dir.glob("*.md")):
            # Read first ~50 lines for summary context
            content = f.read_text(encoding="utf-8")
            lines = content.split("\n")[:50]
            summary = "\n".join(lines)

            # Also try reading the JSON sidecar for structured data
            sidecar_path = f.with_suffix("").with_name(f.stem + "-data.json")
            sidecar = {}
            if sidecar_path.exists():
                try:
                    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass

            theses.append({
                "filename": f.name,
                "summary": summary,
                "thesis_name": sidecar.get("thesis_name", f.stem),
                "direction": sidecar.get("direction", ""),
                "mechanism": sidecar.get("mechanism", ""),
            })

    # Current blind spots for reference
    current_blind_spots = horizon_data.get("blind_spots", [])

    context = {
        "refresh_date": date.today().isoformat(),
        "horizon_run_date": horizon_data.get("meta", {}).get("last_run_date", "unknown"),
        "impacts_to_check": impacts_to_check,
        "active_theses": theses,
        "current_blind_spots": current_blind_spots,
        "force_coverage_status": [
            {"name": f["name"], "coverage_status": f.get("coverage_status", "UNKNOWN")}
            for f in forces
        ],
    }

    return context


def apply_refresh(output_dir: Path, refresh_result_path: Path):
    """Apply LLM-evaluated blind spot refresh back to horizon data."""

    strategic_dir = output_dir / "strategic"
    horizon_path = strategic_dir / "latest-horizon-data.json"

    if not horizon_path.exists():
        print("ERROR: No horizon data to update.", file=sys.stderr)
        sys.exit(1)

    horizon_data = json.loads(horizon_path.read_text(encoding="utf-8"))
    refresh = json.loads(refresh_result_path.read_text(encoding="utf-8"))

    # Update blind spots
    if "blind_spots" in refresh:
        horizon_data["blind_spots"] = refresh["blind_spots"]

    # Update force coverage statuses if provided
    if "force_coverage" in refresh:
        for fc in refresh["force_coverage"]:
            for force in horizon_data.get("forces", []):
                if force["name"] == fc["name"]:
                    force["coverage_status"] = fc["coverage_status"]

    # Update meta counts
    meta = horizon_data.setdefault("meta", {})
    blind_spots = horizon_data.get("blind_spots", [])
    meta["blind_spots_identified"] = len(blind_spots)
    meta["blind_spots_actionable"] = sum(
        1 for bs in blind_spots
        if bs.get("investability", "").upper() in ("HIGH", "MEDIUM")
        and "monitor" not in bs.get("recommendation", "").lower()
    )
    meta["blind_spots_flagged_for_scanner"] = sum(
        1 for bs in blind_spots
        if "SKILL 13" in bs.get("recommendation", "").upper()
        or "SCANNER" in bs.get("recommendation", "").upper()
    )
    meta["blind_spots_flagged_for_research"] = sum(
        1 for bs in blind_spots
        if "SKILL 11" in bs.get("recommendation", "").upper()
        or "RESEARCH" in bs.get("recommendation", "").upper()
    )

    # Add refresh tracking
    meta["last_blind_spot_refresh"] = date.today().isoformat()
    refreshes = meta.get("blind_spot_refreshes", [])
    refreshes.append({
        "date": date.today().isoformat(),
        "prior_count": refresh.get("prior_blind_spot_count", 0),
        "new_count": len(blind_spots),
        "changes": refresh.get("changes_summary", ""),
    })
    meta["blind_spot_refreshes"] = refreshes

    # Write updated horizon data
    horizon_path.write_text(
        json.dumps(horizon_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Also update the dated copy if it exists
    quarter = meta.get("last_run_quarter", "")
    if quarter:
        dated_path = strategic_dir / f"{quarter}-horizon-data.json"
        if dated_path.exists():
            dated_path.write_text(
                json.dumps(horizon_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    # Write refresh log
    log_dir = strategic_dir / "blind-spot-refreshes"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"refresh-{date.today().isoformat()}.json"
    log_path.write_text(
        json.dumps({
            "date": date.today().isoformat(),
            "horizon_run_date": meta.get("last_run_date", "unknown"),
            "prior_blind_spots": refresh.get("prior_blind_spot_count", 0),
            "updated_blind_spots": len(blind_spots),
            "changes": refresh.get("changes_summary", ""),
            "blind_spots": blind_spots,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Blind spot refresh applied. {len(blind_spots)} blind spots "
          f"(was {refresh.get('prior_blind_spot_count', '?')}). "
          f"Log: {log_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Blind Spot Coverage Refresh")
    parser.add_argument("--output-dir", required=True, help="Workspace outputs directory")
    parser.add_argument("--apply", type=str, default=None,
                        help="Path to LLM refresh result JSON to apply")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    if args.apply:
        apply_refresh(output_dir, Path(args.apply))
    else:
        context = gather_context(output_dir)
        if not context:
            sys.exit(0)

        # Write context for LLM evaluation
        context_path = output_dir / "strategic" / "blind-spot-refresh-context.json"
        context_path.write_text(
            json.dumps(context, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "status": "context_ready",
            "context_path": str(context_path),
            "impacts_to_check": len(context["impacts_to_check"]),
            "active_theses": len(context["active_theses"]),
            "current_blind_spots": len(context["current_blind_spots"]),
        }, indent=2))


if __name__ == "__main__":
    main()
