#!/usr/bin/env python3
"""Shared run-log helper used by all scripts that append to the JSONL run log."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def log_event(
    log_path,
    severity: str,
    phase: str,
    message: str,
    details: dict = None,
) -> None:
    """Append a JSONL entry to the run log.

    Args:
        log_path: Path to the JSONL log file, or None (no-op).
        severity: INFO, WARN, ERROR, or FATAL.
        phase: Phase name (e.g. skill-1, preflight, data-collector).
        message: Human-readable event description.
        details: Optional structured data dict appended to the entry.
    """
    if log_path is None:
        return
    entry = {
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "severity": severity,
        "phase": phase,
        "message": message,
    }
    if details:
        entry["details"] = details
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
