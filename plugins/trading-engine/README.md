# Trading Engine (Beta)

An autonomous paper trading system for Claude Cowork. Reads macro research from the Macro Advisor plugin — including regime assessments, investment theses, and regime forecasts with underlying Growth, Inflation, and Liquidity driver readings — translates it into portfolio positions on Alpaca paper trading, and tracks performance with attribution analysis.

> **Beta:** This plugin is in active development. Expect changes to skill logic, dashboard format, and improvement loop behavior between versions.

## What It Does

After each macro advisor weekly run, the trading engine:

1. Snapshots the current Alpaca paper trading portfolio
2. Parses macro advisor outputs — regime assessment, active theses, kill switches, and regime forecasts (6/12-month probability distributions, conditional triggers, current driver readings, driver trajectories)
3. Reconciles current positions against target allocation
4. Reasons through which trades to execute (with mandatory devil's advocate for every new position), using regime forecasts as reasoning context for durability assessment and driver-sensitive sizing
5. Reserves turnover budget for structural thesis first entries that have been deferred 2+ runs, preventing the regime scaling queue from indefinitely blocking structural positions
6. Submits orders to Alpaca
7. Logs every decision and non-decision
8. Tracks performance — P&L attribution by layer (regime vs thesis), drawdown, Sharpe, win rates
9. Self-improves execution quality through structured observation
10. Delivers an HTML dashboard with Overview, Positions, Trades & Reasoning, Performance, External, Improvements, and Rules tabs

## Key Design Decisions

- **Three-force integration:** Trade reasoning considers the underlying Growth, Inflation, and Liquidity drivers — not just the regime label. Position durability is assessed by sensitivity to specific forces.
- **P&L blindness:** The trade reasoner never sees unrealized gains/losses. Decisions are based on macro signals only.
- **Kill switch = immediate exit:** No exceptions, no delays, no "one more day."
- **Devil's advocate mandatory:** Every new position requires an articulated bear case before entry.
- **Forecast as context, not override:** 6/12-month regime forecasts inform reasoning (durability assessment, devil's advocate enrichment, turnover budget tiebreakers) but do not mechanically change allocations or skip positions.
- **Structural thesis reservation:** When a structural thesis has been active for 2+ runs with zero position, the reasoner reserves its first-entry amount (33% of target) from the turnover budget before regime scaling fills the rest. Prevents indefinite deferral.
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

## Trading Pipeline

The engine runs a 9-step pipeline (T0–T8):

```
T0  Portfolio Snapshot      — Alpaca account state (no P&L visible to reasoner)
T1  Signal Parser           — Extracts regime, theses, kill switches, and regime
                              forecasts (including driver readings and trajectories)
                              from macro advisor outputs
T2  Position Reconciler     — Current vs target gap analysis (current regime only)
T3  Trade Reasoner          — Portfolio manager brain: priority-ordered decisions
                              with devil's advocate, forecast-aware durability
                              assessment, and structural thesis reservation
T4  Order Executor          — Converts trade plan to Alpaca API orders
T5  Trade Logger            — Permanent audit trail
T6  Performance Tracker     — P&L, attribution, drawdown, Sharpe, win rates
T7  Self-Improvement Loop   — Observe → inspect → amend → evaluate
T8  External Portfolio      — User's real holdings exposure comparison (optional)
```

## Schedule

| Task | Day | Time | Chain |
|------|-----|------|-------|
| Sunday full run | Sunday | 19:00 CET | T0→T1→T2→T3→T4→T5→T6→T7→T8 + Dashboard |
| Wednesday check | Wednesday | 18:00 CET | T0→T1→T2→T3(defense)→T4→T5 |

## License

MIT
