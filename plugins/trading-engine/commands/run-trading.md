---
description: Run the full trading engine cycle manually
allowed-tools: Read, Write, Edit, Bash, WebSearch, WebFetch
---

Execute the full trading engine skill chain manually.

## Pre-Flight

1. Read `config/user-config.json` to load the user's Alpaca API keys and configuration. If not found at the relative path, the working directory may not be the workspace — stop and tell the user to select their workspace folder in Cowork.
2. If config is missing or `setup_completed` is false, tell the user to run `/trading-engine:setup` first and stop.
3. Read `workspace_path` from config. If the current working directory does not match `workspace_path`, `cd` to `workspace_path` so all relative output paths resolve correctly.
4. Read `${CLAUDE_PLUGIN_ROOT}/skills/trading-engine/references/RULES.md` — the universal rules apply to every skill.
5. Read `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` for project context.
6. Verify Alpaca connectivity:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/trade_executor.py --action snapshot --config config/user-config.json --output outputs/portfolio/
   ```
   If this fails, stop and report the error.

## Execution Chain

Execute skills in order. Each skill reads the output of the previous skill. Do not skip skills. Do not parallelize — the chain is sequential by design.

For each skill, read its reference file from `${CLAUDE_PLUGIN_ROOT}/skills/trading-engine/references/` and follow its instructions exactly.

### T0: Portfolio Snapshot
Read `${CLAUDE_PLUGIN_ROOT}/skills/trading-engine/references/T0-portfolio-snapshot.md` and execute. Produces `outputs/portfolio/latest-snapshot.json`.

### T1: Signal Parser
Read `${CLAUDE_PLUGIN_ROOT}/skills/trading-engine/references/T1-signal-parser.md` and execute. Reads macro advisor outputs and produces `outputs/portfolio/latest-signals.json`.

**Stop if T1 reports STALE SIGNALS.** If the macro advisor hasn't run in 7+ days, skip new trades entirely. Only process kill switch exits from the signals that are available.

### T2: Position Reconciler
Read `${CLAUDE_PLUGIN_ROOT}/skills/trading-engine/references/T2-position-reconciler.md` and execute. Produces `outputs/portfolio/latest-reconciliation.json`.

### T3: Trade Reasoner
Read `${CLAUDE_PLUGIN_ROOT}/skills/trading-engine/references/T3-trade-reasoner.md` and execute. Produces `outputs/portfolio/latest-trade-plan.json` and `outputs/trades/YYYY-MM-DD-reasoning.md`.

### T4: Order Executor
Read `${CLAUDE_PLUGIN_ROOT}/skills/trading-engine/references/T4-order-executor.md` and execute. Submits orders to Alpaca and produces `outputs/trades/YYYY-MM-DD-HHMM-execution.json`.

### T5: Trade Logger
Read `${CLAUDE_PLUGIN_ROOT}/skills/trading-engine/references/T5-trade-logger.md` and execute. Updates `outputs/trades/trade-log.json` and `outputs/trades/weekly-summaries.md`.

### T6: Performance Tracker
Read `${CLAUDE_PLUGIN_ROOT}/skills/trading-engine/references/T6-performance-tracker.md` and execute. Produces weekly performance report in `outputs/performance/`.

### T7: Self-Improvement Loop
Read `${CLAUDE_PLUGIN_ROOT}/skills/trading-engine/references/T7-self-improvement-loop.md` and execute. Produces improvement report in `outputs/improvement/`.

### T8: External Portfolio Overlay (Optional, Sunday Only)
Check `config/user-config.json` for `external_portfolio_enabled`:

- If `true` AND this is a Sunday full run (not a Wednesday defense check): Read `${CLAUDE_PLUGIN_ROOT}/skills/trading-engine/references/T8-external-portfolio-overlay.md` and execute. Produces external portfolio snapshot, exposure comparison, thesis alignment, and kill switch alerts in `outputs/external/`.
- If `false`: skip T8.
- If the field is **missing** (existing user who updated the plugin): skip T8 silently. Do NOT prompt during a run — the run should complete without interruption. Instead, include a one-time note in the post-run summary: "New in this version: external portfolio tracking is available. Run `/update-external-positions` to set it up." Only show this note once — after showing it, write `external_portfolio_enabled: false` to the config so future runs skip silently without the note.

## Post-Run

Take a final snapshot:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/trade_executor.py --action snapshot --config config/user-config.json --output outputs/portfolio/
```

### Generate Dashboard

After the full chain completes, generate the HTML trading dashboard:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/generate_dashboard.py \
  --portfolio outputs/portfolio/ \
  --trades outputs/trades/ \
  --performance outputs/performance/ \
  --improvement outputs/improvement/ \
  --external outputs/external/ \
  --output outputs/dashboard/
```

This produces `outputs/dashboard/latest-dashboard.html` — a self-contained HTML file with tabs: P&L, Trades, Improvements, and (if external portfolio is enabled) External Portfolio.

The `--external` flag is optional. If the directory doesn't exist or is empty, the dashboard renders without the External Portfolio tab.

Present the dashboard file to the user as the primary output of the run.

Report summary to user:
- Regime: [current]
- Trades executed: [N]
- Portfolio value: $[X]
- Week return: [X]%
- Key decisions: [1-2 sentence summary]
- Any alerts: [kill switches, drawdown warnings, stale signals]
- Dashboard: link to `outputs/dashboard/latest-dashboard.html`
- If T7 proposed any amendments: "X skill amendments proposed this week. Run `/implement-improvements` to review and apply them."
