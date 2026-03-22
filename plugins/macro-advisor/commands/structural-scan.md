---
description: Run the structural scanner to find multi-year macro imbalances
allowed-tools: Read, Write, Edit, Bash, Grep, WebSearch, WebFetch
---

Run the Structural Scanner (Skill 13) to proactively find multi-year supply-demand gaps, capex underinvestment cycles, and structural macro imbalances.

## FIRST: READ THE RULES

Before doing anything else, read `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/RULES.md`.

## Pre-flight

1. Read `config/user-config.json`. If missing or `setup_completed` is false, tell the user to run `/macro-advisor:setup` first.
2. Read `workspace_path` from config. If the current working directory does not match, `cd` to `workspace_path`.
3. Ensure data snapshot exists. If `outputs/data/latest-snapshot.json` does not exist, tell the user: "No data snapshot found. Run `/macro-advisor:run-weekly` first to collect data, or run data collection standalone." The scanner needs the snapshot as a starting input.

## Cadence Check

Read `outputs/structural/last-scan.json`. If `last_run_date` exists and is fewer than 12 days ago, tell the user:

"Structural scanner last ran on [date] ([N] days ago). The bi-weekly cadence suggests waiting until [date + 14 days]. Run anyway?"

If the user confirms, proceed. If running as part of the scheduled Sunday chain (not manual), skip silently.

If `last-scan.json` doesn't exist, this is the first run — proceed.

## Execute Skill 13

Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/13-structural-scanner.md`
Read: `outputs/data/latest-snapshot.json` + `outputs/data/latest-data-full.json`
Read: `config/user-config.json` for FRED API key (needed for on-demand FRED pulls)

If the data snapshot is more than 7 days old, refresh it first:
```bash
pip install -r ${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt --break-system-packages -q 2>/dev/null
python ${CLAUDE_PLUGIN_ROOT}/scripts/data_collector.py --fred-key "FRED_KEY_FROM_CONFIG" --output-dir outputs/data/ --mode weekly
```

If prior scan exists, read: `outputs/structural/last-scan.json` for recurring domain tracking and historical kill rate.

The scanner uses a data-first approach: it exhausts quantitative data from the snapshot (commodity momentum, inventory-to-sales, EIA energy, BIS credit gaps) before resorting to web search. This prevents media narrative substitution.

Execute Phases 1 → 2 → 3 → 4 as described in the skill reference.

## Output

Create output directories if they don't exist:
```bash
mkdir -p outputs/structural/candidates
```

Save results:
- `outputs/structural/YYYY-Www-structural-scan.md` — full scan output
- `outputs/structural/candidates/CANDIDATE-[domain-slug]-[date].md` — one per advancing domain
- Update `outputs/structural/last-scan.json`

## Report to User

Present results:

```
Structural Scanner — [date]

Signal detection: [X]/6 detectors found tension
Domains flagged: [list]
After screening: [N] advanced, [N] deferred, [N] dismissed

[For each advancing candidate:]
→ [Domain]: [one-sentence summary of the imbalance]
  Gap: [quantified]
  Consensus: [niche/emerging/mainstream]
  Recommended: [full Skill 11 brief / focused brief / quick check]

[If any domains deferred:]
Deferred (re-check next cycle): [list with reasons]

These candidates are saved in outputs/structural/candidates/. Skill 7 will pick them up in the next /run-weekly cycle, or you can run /macro-advisor:investigate-theme on any candidate now.
```
