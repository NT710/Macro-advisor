---
description: Run the full weekly macro analysis cycle manually
allowed-tools: Read, Write, Edit, Bash, Grep, WebSearch, WebFetch
---

Run the full Macro Advisor weekly analysis cycle. This executes the same sequence as the scheduled Sunday run.

## Pre-flight

1. Read `config/user-config.json` to load the user's FRED API key, currency preference, and configuration.
2. If config is missing or `setup_completed` is false, tell the user to run `/setup` first and stop.
3. Read the macro-advisor skill (`skills/macro-advisor/SKILL.md`) and the universal rules (`skills/macro-advisor/references/RULES.md`).

## Execution

Execute the full skill chain in order. For each skill, read its reference file from `skills/macro-advisor/references/` and follow its instructions exactly.

```
0 → 1 → 2 → 3 → 4 → 5 → 10 → 6 → 7 → 11(if triggered) → 8 → 12 → 9
```

The FRED API key from the config is passed to data_collector.py and regime_backtest.py via the `--fred-key` argument. Never hardcode the key in any output file.

## Post-run

After the Monday Briefing (Skill 9) generates the HTML dashboard, report to the user:

- Which regime was identified
- How many active theses
- Any new theses generated or existing theses invalidated
- The dashboard file location
