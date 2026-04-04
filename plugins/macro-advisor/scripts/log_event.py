#!/usr/bin/env python3
"""Append a single event to the weekly run log (JSONL format).

Usage:
    python log_event.py --log-file outputs/run-logs/2026-W14-run-log.jsonl \
        --severity INFO --phase skill-1 --message "Central Bank Watch completed"

    python log_event.py --log-file outputs/run-logs/2026-W14-run-log.jsonl \
        --severity INFO --phase run-start --message "Weekly run started" --status IN_PROGRESS

Severity levels:
    INFO  — skill completed, skip reason, timing note
    WARN  — non-fatal issue: data gap, web search failure, script failed but non-blocking
    ERROR — checkpoint failure requiring re-run
    FATAL — preflight halt (run stops here)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Append event to run log")
    parser.add_argument("--log-file", required=True, help="Path to JSONL log file")
    parser.add_argument("--severity", required=True, choices=["INFO", "WARN", "ERROR", "FATAL"])
    parser.add_argument("--phase", required=True, help="Phase name (e.g. skill-1, preflight, run-start)")
    parser.add_argument("--message", required=True, help="Human-readable event description")
    parser.add_argument("--status", choices=["IN_PROGRESS", "COMPLETE"], help="Run status marker: IN_PROGRESS or COMPLETE")
    args = parser.parse_args()

    entry: dict = {
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "severity": args.severity,
        "phase": args.phase,
        "message": args.message,
    }
    if args.status:
        entry["status"] = args.status

    log_path = Path(args.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
