#!/usr/bin/env python3
"""Post-run output contract check for the weekly macro run.

Verifies that every skill produced the files it was contracted to produce.
Also checks thesis-specific requirements: every active thesis must have a
companion JSON sidecar, and every thesis Updated field must match today's date.

Usage:
    python postrun_check.py --week 2026-W13 --output-dir outputs/
    python postrun_check.py --week 2026-W13 --output-dir outputs/ --skill skill_6b_regime_evaluation

Exit codes:
    0 = all checks passed
    1 = one or more FAIL items found (missing required files or thesis violations)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path


from run_log_utils import log_event as _log_event


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

def _detect_classification(sidecar: dict, md_content: str) -> str:
    """Determine thesis classification from sidecar or markdown.

    Returns "structural" or "tactical".  Falls back to "tactical" (the less
    restrictive field set) when classification cannot be determined.
    """
    # 1. Prefer the sidecar's own field
    cls = sidecar.get("classification", "").strip().lower()
    if cls.startswith("structural"):
        return "structural"
    if cls == "tactical":
        return "tactical"

    # 2. Fall back to markdown **Classification:** field
    match = re.search(r'\*\*Classification:\*\*\s*(.+)', md_content)
    if match:
        val = match.group(1).strip().lower()
        if val.startswith("structural"):
            return "structural"
        return "tactical"

    # 3. Default — tactical has fewer required fields, safer default
    return "tactical"


# Valid status values per Skill 7 schema
_VALID_ASSUMPTION_STATUSES = {
    "INTACT", "DEVELOPING", "UNDER PRESSURE", "WEAKENING",
    "STRENGTHENING", "WATCH", "BROKEN", "INVALIDATED", "FAILED",
}


def _validate_sidecar_content(
    sidecar: dict,
    classification: str,
    thesis_name: str,
) -> list[str]:
    """Validate sidecar JSON content against the Skill 7 schema.

    Returns a list of FAIL strings (empty if valid).
    """
    fails: list[str] = []
    prefix = f"FAIL [Thesis Sidecar Content]: {thesis_name}"

    # --- Fields required for ALL theses (tactical + structural) ---
    required_all = {
        "name": str,
        "status": str,
        "classification": str,
        "updated": str,
        "conviction": str,
        "summary": str,
        "the_bet": str,
    }
    for field, expected_type in required_all.items():
        val = sidecar.get(field)
        if val is None:
            fails.append(f"{prefix} — missing required field '{field}'")
        elif not isinstance(val, expected_type):
            fails.append(
                f"{prefix} — '{field}' must be {expected_type.__name__}, "
                f"got {type(val).__name__}"
            )

    # --- mechanism: must be a list ---
    mechanism = sidecar.get("mechanism")
    if mechanism is None:
        fails.append(f"{prefix} — missing required field 'mechanism'")
    elif not isinstance(mechanism, list):
        fails.append(
            f"{prefix} — 'mechanism' must be an array, "
            f"got {type(mechanism).__name__}"
        )

    # --- what_has_to_stay_true: must be a list of objects with text + status ---
    whst = sidecar.get("what_has_to_stay_true")
    if whst is None:
        fails.append(f"{prefix} — missing required field 'what_has_to_stay_true'")
    elif not isinstance(whst, list):
        fails.append(
            f"{prefix} — 'what_has_to_stay_true' must be an array, "
            f"got {type(whst).__name__} "
            "(this is the most common sidecar failure — "
            "do not flatten assumptions into a summary string)"
        )
    elif len(whst) == 0:
        fails.append(f"{prefix} — 'what_has_to_stay_true' array is empty")
    else:
        for i, item in enumerate(whst):
            if not isinstance(item, dict):
                fails.append(
                    f"{prefix} — what_has_to_stay_true[{i}] must be an object, "
                    f"got {type(item).__name__}"
                )
                continue
            if "text" not in item:
                fails.append(
                    f"{prefix} — what_has_to_stay_true[{i}] missing 'text'"
                )
            if "status" not in item:
                fails.append(
                    f"{prefix} — what_has_to_stay_true[{i}] missing 'status'"
                )
            elif item["status"] not in _VALID_ASSUMPTION_STATUSES:
                fails.append(
                    f"{prefix} — what_has_to_stay_true[{i}].status "
                    f"'{item['status']}' is not a valid status value"
                )

    # --- the_trade: must be an object with key sub-fields ---
    the_trade = sidecar.get("the_trade")
    if the_trade is None:
        fails.append(f"{prefix} — missing required field 'the_trade'")
    elif not isinstance(the_trade, dict):
        fails.append(
            f"{prefix} — 'the_trade' must be an object, "
            f"got {type(the_trade).__name__}"
        )
    else:
        for sub in ("when_to_get_out", "how_long"):
            if sub not in the_trade:
                fails.append(f"{prefix} — the_trade.{sub} is missing")

    # --- Fields required ONLY for structural theses ---
    if classification == "structural":
        # what_cant_change: must be a list (not null)
        wcc = sidecar.get("what_cant_change")
        if wcc is None:
            fails.append(
                f"{prefix} — structural thesis missing 'what_cant_change' "
                "(set to null only for tactical theses)"
            )
        elif not isinstance(wcc, list):
            fails.append(
                f"{prefix} — 'what_cant_change' must be an array for "
                f"structural theses, got {type(wcc).__name__}"
            )

        # what_could_break_it: must be an object (not null)
        wcbi = sidecar.get("what_could_break_it")
        if wcbi is None:
            fails.append(
                f"{prefix} — structural thesis missing 'what_could_break_it' "
                "(set to null only for tactical theses)"
            )
        elif not isinstance(wcbi, dict):
            fails.append(
                f"{prefix} — 'what_could_break_it' must be an object for "
                f"structural theses, got {type(wcbi).__name__}"
            )

        # the_trade.when_to_buy: required for structural
        if isinstance(the_trade, dict) and the_trade.get("when_to_buy") is None:
            fails.append(
                f"{prefix} — structural thesis missing the_trade.when_to_buy"
            )

    # --- Stub content detection ---
    # Sidecars that pass structural validation but contain placeholder text
    # instead of real data. These cause the dashboard to render empty sections
    # because it prefers sidecar JSON over markdown parsing.
    stub_prefix = f"FAIL [Thesis Sidecar Stub]: {thesis_name}"
    _STUB_PHRASES = ("see thesis document", "see thesis doc", "see document")

    def _is_stub_text(text: str) -> bool:
        return any(p in text.lower() for p in _STUB_PHRASES)

    # what_has_to_stay_true: single-item stub
    if isinstance(whst, list) and len(whst) == 1 and isinstance(whst[0], dict):
        if _is_stub_text(whst[0].get("text", "")):
            fails.append(
                f"{stub_prefix} — 'what_has_to_stay_true' contains placeholder "
                "text instead of individual assumptions. Skill 7 must populate "
                "each assumption as a separate object with text, testable_by, "
                "and status fields."
            )

    # mechanism: single-item stub
    if isinstance(mechanism, list) and len(mechanism) == 1 and isinstance(mechanism[0], dict):
        if _is_stub_text(mechanism[0].get("link", "")):
            fails.append(
                f"{stub_prefix} — 'mechanism' contains placeholder text instead "
                "of the causal chain steps. Skill 7 must populate each step."
            )

    # what_cant_change: single-item stub (structural only)
    if classification == "structural" and isinstance(wcc, list) and len(wcc) == 1 and isinstance(wcc[0], dict):
        if _is_stub_text(wcc[0].get("constraint", "")):
            fails.append(
                f"{stub_prefix} — 'what_cant_change' contains placeholder text "
                "instead of binding constraints. Skill 7 must populate each "
                "constraint with quantified data and source."
            )

    # what_could_break_it: stub object (structural only)
    if classification == "structural" and isinstance(wcbi, dict):
        if _is_stub_text(wcbi.get("primary_risk", "")):
            fails.append(
                f"{stub_prefix} — 'what_could_break_it' contains placeholder "
                "text. Skill 7 must populate strongest_counter, key_risks, "
                "and post_test_conviction."
            )
        elif not wcbi.get("strongest_counter") and not wcbi.get("key_risks"):
            fails.append(
                f"{stub_prefix} — 'what_could_break_it' is missing both "
                "'strongest_counter' and 'key_risks'. Structural theses "
                "require a full contrarian stress test."
            )

    # conviction: must not be empty
    conv = sidecar.get("conviction", "")
    if isinstance(conv, str) and not conv.strip():
        fails.append(
            f"{stub_prefix} — 'conviction' is empty. Every thesis must have "
            "a conviction level (High, Medium, Low, or qualified variant)."
        )

    # testable_by: warn if no assumption has it (not a hard fail yet)
    if isinstance(whst, list) and len(whst) > 1:
        has_testable = any(
            isinstance(a, dict) and a.get("testable_by")
            for a in whst
        )
        if not has_testable:
            # Emit as a warning (printed to stderr, not added to failures)
            print(
                f"WARN [Thesis Sidecar]: {thesis_name} — no assumption has "
                "'testable_by' populated. Dashboard will show an incomplete "
                "assumptions table.",
                file=sys.stderr,
            )

    return fails


def _verify_sidecar_fidelity(
    md_content: str,
    sidecar: dict,
    thesis_name: str,
) -> list[str]:
    """Verify sidecar fields are 1:1 with the markdown content.

    Checks:
    1. String containment — sidecar text fields appear in markdown sections
    2. Count matching — assumption and mechanism counts match
    3. No truncation — no fields end with '...'
    4. Section presence — if markdown has a section, sidecar has the field
    """
    fails: list[str] = []
    warns: list[str] = []
    prefix = f"FAIL [Sidecar Fidelity]: {thesis_name}"
    warn_prefix = f"WARN [Sidecar Fidelity]: {thesis_name}"

    def _normalize(text: str) -> str:
        """Normalize whitespace for substring comparison."""
        return " ".join(text.split()).strip()

    # --- Count matching ---

    # Count numbered items under "## What Has To Stay True" in markdown
    md_assumption_count = 0
    in_section = False
    for line in md_content.split("\n"):
        if line.strip().startswith("## What Has To Stay True"):
            in_section = True
            continue
        if in_section and line.strip().startswith("## "):
            break
        if in_section and re.match(r'^\d+\.', line.strip()):
            md_assumption_count += 1

    json_assumption_count = len(sidecar.get("what_has_to_stay_true", []))
    if md_assumption_count > 0 and json_assumption_count != md_assumption_count:
        fails.append(
            f"{prefix} — assumption count mismatch: "
            f"markdown has {md_assumption_count}, sidecar has {json_assumption_count}"
        )

    # Count mechanism steps in markdown
    md_mechanism_count = 0
    in_section = False
    for line in md_content.split("\n"):
        if line.strip().startswith("### Mechanism"):
            in_section = True
            continue
        if in_section and re.match(r'^#{2,3}\s+', line.strip()):
            break
        if in_section and re.match(r'^\d+\.', line.strip()):
            md_mechanism_count += 1

    json_mechanism_count = len(sidecar.get("mechanism", []))
    if md_mechanism_count > 0 and json_mechanism_count != md_mechanism_count:
        fails.append(
            f"{prefix} — mechanism count mismatch: "
            f"markdown has {md_mechanism_count}, sidecar has {json_mechanism_count}"
        )

    # --- Section presence ---
    md_lower = md_content.lower()
    if "## where the market stands" in md_lower:
        wms = sidecar.get("where_the_market_stands")
        if not wms:
            print(
                f"{warn_prefix} — markdown has 'Where The Market Stands' section "
                "but sidecar field is missing or null",
                file=sys.stderr,
            )

    # --- No truncation ---
    for field in ("summary", "the_bet", "where_the_market_stands"):
        val = sidecar.get(field)
        if isinstance(val, str) and val.rstrip().endswith("..."):
            fails.append(
                f"{prefix} — '{field}' appears truncated (ends with '...'). "
                "Sidecar must contain the full text from the markdown section."
            )

    # Check trade fields for truncation
    trade = sidecar.get("the_trade", {})
    if isinstance(trade, dict):
        for sub in ("what_to_buy", "when_to_get_out", "when_to_buy_more", "how_long"):
            val = trade.get(sub, "")
            if isinstance(val, str) and val.rstrip().endswith("..."):
                fails.append(
                    f"{prefix} — 'the_trade.{sub}' appears truncated (ends with '...')"
                )

    # Check mechanism links for truncation
    for i, step in enumerate(sidecar.get("mechanism", [])):
        if isinstance(step, dict):
            link = step.get("link", "")
            if isinstance(link, str) and link.rstrip().endswith("..."):
                fails.append(
                    f"{prefix} — mechanism[{i}].link appears truncated"
                )

    # --- change_log presence ---
    change_log = sidecar.get("change_log")
    if not change_log or not isinstance(change_log, list) or len(change_log) == 0:
        print(
            f"{warn_prefix} — 'change_log' is missing or empty. "
            "Run compile_sidecars.py to generate change_log from diffs.",
            file=sys.stderr,
        )

    return fails


def check_thesis_contracts(contract: dict, output_dir: Path, today: str) -> list[str]:
    """
    For every .md file in outputs/theses/active/:
    1. A companion -data.json sidecar must exist.
    2. The sidecar must contain valid structured content per the Skill 7 schema.
    3. The **Updated:** field in the markdown must equal today's date.
    """
    failures = []
    thesis_cfg = contract.get("skills", {}).get("skill_7_thesis_monitor", {}).get("thesis_checks", {})
    if not thesis_cfg:
        return failures

    active_dir_pattern = thesis_cfg.get("active_dir", "theses/active/")
    require_sidecar = thesis_cfg.get("require_sidecar", True)
    require_updated_today = thesis_cfg.get("require_updated_today", True)

    active_dir = output_dir / active_dir_pattern
    if not active_dir.exists():
        failures.append(f"FAIL [Thesis Contracts]: {active_dir} directory not found")
        return failures

    thesis_files = sorted(active_dir.glob("*.md"))
    if not thesis_files:
        # No thesis files — nothing to check
        return failures

    for thesis_path in thesis_files:
        stem = thesis_path.stem  # e.g. ACTIVE-structural-grid-bottleneck

        # Read markdown content (needed for Updated check and classification fallback)
        try:
            md_content = thesis_path.read_text(encoding="utf-8")
        except OSError as e:
            failures.append(f"FAIL [Thesis]: cannot read {thesis_path.name}: {e}")
            continue

        # --- Sidecar existence + content check ---
        if require_sidecar:
            sidecar_path = active_dir / f"{stem}-data.json"
            if not sidecar_path.exists():
                failures.append(
                    f"FAIL [Thesis Sidecar]: {thesis_path.name} has no companion "
                    f"{stem}-data.json — Skill 7 must create the JSON sidecar"
                )
            else:
                # Parse and validate sidecar content
                try:
                    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as e:
                    failures.append(
                        f"FAIL [Thesis Sidecar]: {sidecar_path.name} is not valid JSON: {e}"
                    )
                    sidecar = None

                if sidecar is not None:
                    classification = _detect_classification(sidecar, md_content)
                    failures += _validate_sidecar_content(
                        sidecar, classification, thesis_path.name
                    )
                    # Fidelity check: verify sidecar matches markdown content
                    failures += _verify_sidecar_fidelity(
                        md_content, sidecar, thesis_path.name
                    )

        # --- Updated date check ---
        if require_updated_today:
            updated_match = re.search(r'\*\*Updated:\*\*\s*(\S+)', md_content)
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

def check_single_skill(contract: dict, output_dir: Path, week: str, today: str, skill_id: str) -> list[str]:
    """Check outputs for a single skill only (used with --skill flag).

    Supports both core skills (skills.*) and conditional skills (conditional_skills.*).
    For skill_7_thesis_monitor, also runs thesis sidecar + Updated date checks.
    """
    failures = []

    # Check in core skills
    skill = contract.get("skills", {}).get(skill_id)
    if skill:
        label = skill.get("description", skill_id)
        for pattern in skill.get("outputs", []):
            resolved = resolve_pattern(pattern, week, today)
            result = check_file_exists(output_dir / resolved, label)
            if result:
                failures.append(result)

        # Skill 7 also requires thesis sidecar checks
        if skill_id == "skill_7_thesis_monitor":
            failures += check_thesis_contracts(contract, output_dir, today)

        return failures

    # Check in conditional skills
    cond_skill = contract.get("conditional_skills", {}).get(skill_id)
    if cond_skill:
        label = cond_skill.get("description", skill_id)
        for pattern in cond_skill.get("outputs_if_ran", cond_skill.get("outputs_if_triggered", [])):
            resolved = resolve_pattern(pattern, week, today)
            # For wildcard patterns (e.g. research/STRUCTURAL-*-{date}.md), skip existence check
            if "*" in resolved:
                continue
            result = check_file_exists(output_dir / resolved, label)
            if result:
                failures.append(result)
        return failures

    # Check in optional skills
    opt_skill = contract.get("optional_skills", {}).get(skill_id)
    if opt_skill:
        label = opt_skill.get("description", skill_id)
        for pattern in opt_skill.get("outputs", []):
            resolved = resolve_pattern(pattern, week, today)
            result = check_file_exists(output_dir / resolved, label)
            if result:
                failures.append(result)
        return failures

    failures.append(f"FAIL: Unknown skill '{skill_id}' — not found in output contract")
    return failures


def main():
    parser = argparse.ArgumentParser(description="Post-run output contract check")
    parser.add_argument("--week", required=True, help="ISO week string, e.g. 2026-W13")
    parser.add_argument("--output-dir", required=True, help="Path to outputs/ directory")
    parser.add_argument(
        "--contract",
        default=None,
        help="Path to output-contract.json (default: {plugin_root}/config/output-contract.json)"
    )
    parser.add_argument(
        "--skill",
        default=None,
        help="Check only this skill's outputs (e.g. skill_6b_regime_evaluation). "
             "When omitted, all skills are checked."
    )
    parser.add_argument("--run-log", default=None, help="Path to JSONL run log (optional)")
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

    if args.skill:
        # Single-skill mode: check only the specified skill
        all_failures += check_single_skill(contract, output_dir, args.week, today, args.skill)
        label = args.skill
    else:
        # Full mode: check everything
        # 1. Core skill outputs
        all_failures += check_skill_outputs(contract, output_dir, args.week, today)

        # 2. Conditional skill outputs (scanner, decade horizon)
        all_failures += check_conditional_skills(contract, output_dir, args.week, today)

        # 3. Thesis sidecar + Updated date checks
        all_failures += check_thesis_contracts(contract, output_dir, today)
        label = args.week

    run_log = Path(args.run_log) if args.run_log else None
    phase = f"postrun-{args.skill}" if args.skill else "postrun-full"

    # Report
    if not all_failures:
        print(f"POST-RUN CHECK: All output contracts satisfied for {label}.")
        _log_event(run_log, "INFO", phase, f"All output contracts satisfied for {label}")
        sys.exit(0)
    else:
        print(f"\nPOST-RUN CHECK FAILED — {len(all_failures)} issue(s) found for {label}:\n")
        for f in all_failures:
            print(f"  {f}")
        for failure in all_failures:
            _log_event(run_log, "ERROR", phase, failure)
        print(
            "\nDo not share the dashboard with the user until these are resolved. "
            "Re-run the failing skill(s) to produce the missing outputs."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
