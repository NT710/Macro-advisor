---
description: Run the full trading engine cycle manually
allowed-tools: Read, Write, Edit, Bash, WebSearch, WebFetch
---

Execute the full trading engine skill chain manually.

## Pre-Flight

1. Read `config/user-config.json` to load the user's Alpaca API keys and configuration.
2. If config is missing or `setup_completed` is false, tell the user to run `/setup` first and stop.
3. Read `skills/trading-engine/references/RULES.md` — the universal rules apply to every skill.
4. Read `CLAUDE.md` for project context.
5. Verify Alpaca connectivity:
   ```bash
   python scripts/trade_executor.py --action snapshot --config config/user-config.json --output outputs/portfolio/
   ```
   If this fails, stop and report the error.

## Execution Chain

Execute skills in order. Each skill reads the output of the previous skill. Do not skip skills. Do not parallelize — the chain is sequential by design.

For each skill, read its reference file from `skills/trading-engine/references/` and follow its instructions exactly.

### T0: Portfolio Snapshot
Read `skills/trading-engine/references/T0-portfolio-snapshot.md` and execute. Produces `outputs/portfolio/latest-snapshot.json`.

### T1: Signal Parser
Read `skills/trading-engine/references/T1-signal-parser.md` and execute. Reads macro advisor outputs and produces `outputs/portfolio/latest-signals.json`.

**Stop if T1 reports STALE SIGNALS.** If the macro advisor hasn't run in 7+ days, skip new trades entirely. Only process kill switch exits from the signals that are available.

### T2: Position Reconciler
Read `skills/trading-engine/references/T2-position-reconciler.md` and execute. Produces `outputs/portfolio/latest-reconciliation.json`.

### T3: Trade Reasoner
Read `skills/trading-engine/references/T3-trade-reasoner.md` and execute. Produces `outputs/portfolio/latest-trade-plan.json` and `outputs/trades/YYYY-MM-DD-reasoning.md`.

### T4: Order Executor
Read `skills/trading-engine/references/T4-order-executor.md` and execute. Submits orders to Alpaca and produces `outputs/trades/YYYY-MM-DD-HHMM-execution.json`.

### T5: Trade Logger
Read `skills/trading-engine/references/T5-trade-logger.md` and execute. Updates `outputs/trades/trade-log.json` and `outputs/trades/weekly-summaries.md`.

### T6: Performance Tracker
Read `skills/trading-engine/references/T6-performance-tracker.md` and execute. Produces weekly performance report in `outputs/performance/`.

### T7: Self-Improvement Loop
Read `skills/trading-engine/references/T7-self-improvement-loop.md` and execute. Produces improvement report in `outputs/improvement/`.

## Post-Run

Take a final snapshot:
```bash
python scripts/trade_executor.py --action snapshot --config config/user-config.json --output outputs/portfolio/
```

### Generate Dashboard

After the full chain completes, generate the HTML trading dashboard:
```bash
python scripts/generate_dashboard.py \
  --portfolio outputs/portfolio/ \
  --trades outputs/trades/ \
  --performance outputs/performance/ \
  --improvement outputs/improvement/ \
  --output outputs/dashboard/
```

This produces `outputs/dashboard/latest-dashboard.html` — a self-contained HTML file with three tabs: P&L, Trades, and Improvements.

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
