#!/usr/bin/env python3
"""Post-run output contract check for the weekly macro run.

Verifies that every skill produced the files it was contracted to produce.
Also checks thesis-specific requirements: every active thesis must have a
companion JSON sidecar, and every thesis Updated field must match today's date.

Usage:
    python postrun_check.py --week 2026-W13 --output-dir outputs/

Exit codes:
    0 = all checks passed
    1 = one or more FAIL items found (missing required files or thesis violations)
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_pattern(pattern: str, week: str, today: str) -> str:
    """Replace {week} and {date} placeholders in a path pattern."""
    return pattern.replace("{week}", week).replace("{date}", today)


def check_file_exists(path: Path, label: str) -> str | None:
    """Return a FAIL string if path does not exist, else None."""
    if not path.exists():
        return f"FAIL [{label}]: missing {path}"
    return None


# ---------------------------------------------------------------------------
# Core skill output checks
# ---------------------------------------------------------------------------

def check_skill_outputs(contract: dict, output_dir: Path, week: str, today: str) -> list[str]:
    """Check all mandatory skill outputs declared in the contract."""
    failures = []
    for skill_id, skill in contract.get("skills", {}).items():
        label = skill.get("description", skill_id)
        for pattern in skill.get("outputs", []):
            resolved = resolve_pattern(pattern, week, today)
            result = check_file_exists(output_dir / resolved, label)
            if result:
                failures.append(result)
    return failures


# ---------------------------------------------------------------------------
# Conditional skill checks
# ---------------------------------------------------------------------------

def check_conditional_skills(contract: dict, output_dir: Path, week: str, today: str) -> list[str]:
    """Check conditional skills — only verify outputs if the skill ran this cycle."""
    failures = []
    for skill_id, skill in contract.get("conditional_skills", {}).items():
        label = skill.get("description", skill_id)
        condition_file = skill.get("condition_file")
        condition_field = skill.get("condition_field")
        max_age_days = skill.get("condition_max_age_days")

        if not condition_file or not condition_field or not max_age_days:
            continue

        tracker_path = output_dir / condition_file
        if not tracker_path.exists():
            # No tracker means it's never run — that's fine, not a failure
            continue

        try:
            tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
            last_run = tracker.get(condition_field, "")
        except Exception:
            continue

        if not last_run:
            continue

        try:
            last_run_date = date.fromisoformat(last_run[:10])
            age_days = (date.today() - last_run_date).days
        except ValueError:
            continue

        # If the skill ran today (age == 0), verify its outputs
        if age_days == 0:
            for pattern in skill.get("outputs_if_ran", []):
                resolved = resolve_pattern(pattern, week, today)
                result = check_file_exists(output_dir / resolved, label)
                if result:
                    failures.append(result)

    return failures


# ---------------------------------------------------------------------------
# Thesis-specific checks
# ---------------------------------------------------------------------------

def check_thesis_contracts(contract: dict, output_dir: Path, today: str) -> list[str]:
    """
    For every .md file in outputs/theses/active/:
    1. A companion -data.json sidecar must exist.
    2. The **Updated:** field in the markdown must equal today's date.
    """
    failures = []
    thesis_cfg = contract.get("skills", {}).get("skill_7_thesis_monitor", {}).get("thesis_checks", {})
    if not thesis_cfg:
        return failures

    active_dir_pattern = thesis_cfg.get("active_dir", "outputs/theses/active/")
    require_sidecar = thesis_cfg.get("require_sidecar", True)
    require_updated_today = thesis_cfg.get("require_updated_today", True)

    active_dir = output_dir / active_dir_pattern
    if not active_dir.exists():
        failures.append("FAIL [Thesis Contracts]: outputs/theses/active/ directory not found")
        return failures

    thesis_files = sorted(active_dir.glob("*.md"))
    if not thesis_files:
        # No thesis files — nothing to check
        return failures

    for thesis_path in thesis_files:
        stem = thesis_path.stem  # e.g. ACTIVE-structural-grid-bottleneck

        # --- Sidecar check ---
        if require_sidecar:
            sidecar_path = active_dir / f"{stem}-data.json"
            if not sidecar_path.exists():
                failures.append(
                    f"FAIL [Thesis Sidecar]: {thesis_path.name} has no companion "
                    f"{stem}-data.json — Skill 7 must create the JSON sidecar"
                )

        # --- Updated date check ---
        if require_updated_today:
            try:
                content = thesis_path.read_text(encoding="utf-8")
            except OSError as e:
                failures.append(f"FAIL [Thesis Updated]: cannot read {thesis_path.name}: {e}")
                continue

            updated_match = re.search(r'\*\*Updated:\*\*\s*(\S+)', content)
            if not updated_match:
                failures.append(
                    f"FAIL [Thesis Updated]: {thesis_path.name} has no **Updated:** field"
                )
            else:
                updated_val = updated_match.group(1).strip()
                if updated_val != today:
                    failures.append(
                        f"FAIL [Thesis Updated]: {thesis_path.name} — "
                        f"Updated: {updated_val}, expected: {today} "
                        f"(Skill 7 write-back did not run for this thesis)"
                    )

    return failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Post-run output contract check")
    parser.add_argument("--week", required=True, help="ISO week string, e.g. 2026-W13")
    parser.add_argument("--output-dir", required=True, help="Path to outputs/ directory")
    parser.add_argument(
        "--contract",
        default=None,
        help="Path to output-contract.json (default: {plugin_root}/config/output-contract.json)"
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    today = date.today().isoformat()

    # Locate contract file
    if args.contract:
        contract_path = Path(args.contract)
    else:
        # Default: two levels up from scripts/ → plugin root → config/
        contract_path = Path(__file__).parent.parent / "config" / "output-contract.json"

    if not contract_path.exists():
        print(f"FAIL: output-contract.json not found at {contract_path}", file=sys.stderr)
        sys.exit(1)

    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL: Cannot parse output-contract.json: {e}", file=sys.stderr)
        sys.exit(1)

    all_failures = []

    # 1. Core skill outputs
    all_failures += check_skill_outputs(contract, output_dir, args.week, today)

    # 2. Conditional skill outputs (scanner, decade horizon)
    all_failures += check_conditional_skills(contract, output_dir, args.week, today)

    # 3. Thesis sidecar + Updated date checks
    all_failures += check_thesis_contracts(contract, output_dir, today)

    # Report
    if not all_failures:
        print(f"POST-RUN CHECK: All output contracts satisfied for {args.week}.")
        sys.exit(0)
    else:
        print(f"\nPOST-RUN CHECK FAILED — {len(all_failures)} issue(s) found for {args.week}:\n")
        for f in all_failures:
            print(f"  {f}")
        print(
            "\nDo not share the dashboard with the user until these are resolved. "
            "Re-run the failing skill(s) to produce the missing outputs."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
