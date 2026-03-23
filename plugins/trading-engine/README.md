# Trading Engine (Beta)

An autonomous paper trading system for Claude Cowork. Reads macro research from the Macro Advisor plugin, translates it into portfolio positions on Alpaca paper trading, and tracks performance with attribution analysis.

> **Beta:** This plugin is in active development. Expect changes to skill logic, dashboard format, and improvement loop behavior between versions.

## What It Does

After each macro advisor weekly run, the trading engine:

1. Snapshots the current Alpaca paper trading portfolio
2. Parses macro advisor outputs — regime assessment, active theses, kill switches
3. Reconciles current positions against target allocation
4. Reasons through which trades to execute (with mandatory devil's advocate for every new position)
5. Submits orders to Alpaca
6. Logs every decision and non-decision
7. Tracks performance — P&L attribution by layer (regime vs thesis), drawdown, Sharpe, win rates
8. Self-improves execution quality through structured observation
9. Delivers an HTML dashboard with P&L, trades, and improvement tabs

## Key Design Decisions

- **P&L blindness:** The trade reasoner never sees unrealized gains/losses. Decisions are based on macro signals only.
- **Kill switch = immediate exit:** No exceptions, no delays, no "one more day."
- **Devil's advocate mandatory:** Every new position requires an articulated bear case before entry.
- **Sizing follows reasoning:** ETF expression sizing is driven by conviction and thesis logic, not by expression order.
- **Risk limits are hardcoded:** Max position 15%, max sector 30%, max drawdown 10% trigger, min cash 5%, max thesis overlay 25%. The self-improvement loop cannot change these.

## Prerequisites

- **Macro Advisor plugin** — must be installed and running its weekly cycle
- **Alpaca paper trading account** — free at [alpaca.markets](https://alpaca.markets)
- Python 3.8+
- Claude Cowork (desktop app)

## Installation

This plugin is part of the Macro Advisor marketplace. After adding the marketplace:

1. Install the trading-engine plugin
2. Run `/trading-engine:setup` to configure your Alpaca API keys and schedule

## Commands

| Command | Description |
|---------|-------------|
| `/trading-engine:setup` | First-run: install alpaca-py, configure API keys, schedule runs |
| `/trading-engine:run-trading` | Run the full trading chain manually |
| `/trading-engine:implement-improvements` | Review and approve/defer T7 amendment proposals |
| `/trading-engine:update-external-positions` | Add, remove, or update your real-world holdings for T8 overlay |

## Schedule

| Task | Day | Time | Chain |
|------|-----|------|-------|
| Sunday full run | Sunday | 19:00 CET | T0→T1→T2→T3→T4→T5→T6→T7→T8 + Dashboard |
| Wednesday check | Wednesday | 18:00 CET | T0→T1→T2→T3(defense)→T4→T5 |

## License

MIT
