#!/usr/bin/env python3
"""Summarize a weekly run log (JSONL format).

Reads the JSONL log file, counts events by severity, extracts categories
(data gaps, source failures, retries), and checks for incomplete runs.

Usage:
    python run_log_summary.py --log-file outputs/run-logs/2026-W14-run-log.jsonl

Exit codes:
    0 = summary produced (even if warnings/errors exist)
    1 = log file not found or unreadable
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_log(log_path: Path) -> tuple[list[dict], int]:
    """Parse JSONL log file, skipping malformed lines.

    Returns (entries, skipped_count).
    """
    entries = []
    skipped = 0
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            skipped += 1
    return entries, skipped


def summarize(entries: list[dict], skipped: int = 0) -> None:
    """Print a human-readable summary of the run log."""
    if not entries:
        print("RUN LOG: Empty — no events recorded.")
        return

    # Count by severity
    counts: dict[str, int] = {}
    for e in entries:
        sev = e.get("severity", "UNKNOWN")
        counts[sev] = counts.get(sev, 0) + 1

    # Check run status
    has_start = any(e.get("status") == "IN_PROGRESS" for e in entries)
    has_complete = any(e.get("status") == "COMPLETE" for e in entries)
    run_status = "COMPLETE" if has_complete else ("INCOMPLETE" if has_start else "UNKNOWN")

    # Extract timing
    start_ts = None
    end_ts = None
    for e in entries:
        if e.get("phase") == "run-start":
            start_ts = e.get("ts")
        if e.get("phase") == "run-end":
            end_ts = e.get("ts")

    # Collect warnings and errors
    issues = [e for e in entries if e.get("severity") in ("WARN", "ERROR", "FATAL")]

    # Categorize issues (use specific phrases to avoid false positives)
    data_gaps = [e for e in issues if any(k in e.get("message", "").lower() for k in ("data gap", "missing key market", "data is stale", "collection error", "snapshot missing"))]
    source_failures = [e for e in issues if any(k in e.get("message", "").lower() for k in ("403", "404", "timeout", "unavailable", "failed to fetch", "connectivity"))]
    retries = [e for e in issues if any(k in e.get("message", "").lower() for k in ("re-run", "retry", "re-running", "passed on retry"))]
    script_failures = [e for e in issues if any(k in e.get("message", "").lower() for k in ("script failed", "exit code", "non-zero"))]

    # Print summary
    print(f"RUN LOG SUMMARY")
    print(f"  Status: {run_status}")
    if start_ts:
        print(f"  Started: {start_ts}")
    if end_ts:
        print(f"  Completed: {end_ts}")
    print(f"  Total events: {len(entries)}")
    print(f"  INFO: {counts.get('INFO', 0)}  |  WARN: {counts.get('WARN', 0)}  |  ERROR: {counts.get('ERROR', 0)}  |  FATAL: {counts.get('FATAL', 0)}")

    if skipped:
        print(f"  Skipped {skipped} malformed line(s)")
    if run_status == "INCOMPLETE":
        last_phase = entries[-1].get("phase", "unknown") if entries else "unknown"
        print(f"  *** INCOMPLETE RUN — last recorded phase: {last_phase} ***")

    if not issues:
        print("  No warnings or errors — clean run.")
        return

    print(f"\n  Issues ({len(issues)}):")
    for e in issues:
        print(f"    [{e.get('severity')}] {e.get('phase')}: {e.get('message')}")
        details = e.get("details")
        if details and isinstance(details, dict):
            for dk, dv in details.items():
                print(f"      {dk}: {dv}")

    if data_gaps:
        print(f"\n  Data gaps: {len(data_gaps)}")
    if source_failures:
        print(f"  Source failures: {len(source_failures)}")
    if retries:
        print(f"  Skills re-run: {len(retries)}")
    if script_failures:
        print(f"  Script failures: {len(script_failures)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize weekly run log")
    parser.add_argument("--log-file", required=True, help="Path to JSONL log file")
    args = parser.parse_args()

    log_path = Path(args.log_file)
    if not log_path.exists():
        print(f"RUN LOG: File not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    entries, skipped = parse_log(log_path)
    summarize(entries, skipped)


if __name__ == "__main__":
    main()
