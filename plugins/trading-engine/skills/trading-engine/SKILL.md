---
name: trading-engine
description: >
  Autonomous paper trading system that reads macro advisor outputs and executes
  trades on Alpaca. Use when the user asks to "run the trading engine", "execute
  trades", "check portfolio", "run the Sunday trading cycle", "what did we trade",
  or any request related to trade execution, portfolio management, P&L tracking,
  or trading self-improvement. Also triggers on "trading dashboard", "show P&L",
  "show trades", "implement trading improvements", "trading engine status",
  "update external positions", "add external holdings", or "track my real portfolio".
version: 0.2.5-beta
---

# Trading Engine

An autonomous paper trading system that translates macro research into portfolio positions on Alpaca paper trading, with anti-confirmation-bias architecture, mandatory devil's advocate reasoning, and a self-improvement loop.

## Core Design Principles

1. **Anti-confirmation bias:** T3 never sees P&L, T1 is stateless, T7 tracks by mechanism not asset class.
2. **Devil's advocate mandatory:** Every new position requires an articulated bear case before entry.
3. **Kill switch = immediate exit:** No exceptions, no delays.
4. **Sizing follows reasoning:** Expression order doesn't determine size — conviction and thesis logic do.
5. **Hardcoded risk limits:** Not adjustable by the improvement loop.

Read `references/methodology.md` for the full methodology and system architecture. The system uses an 8-regime model (Growth × Inflation × Liquidity) with family-level templates and liquidity modifier overlays.

## Universal Rules

Before executing ANY skill, read `references/RULES.md`. These are non-negotiable policies on risk, execution, anti-bias, and data integrity.

## Execution Chain

The system runs as a single sequential chain. Each skill reads the output of prior skills.

**Sunday full run:** T0→T1→T2→T3→T4→T5→T6→T7→T8 + Dashboard
**Wednesday defense check:** T0→T1→T2→T3(defense only)→T4→T5

| Step | Skill | Reference File | Purpose |
|------|-------|---------------|---------|
| T0 | Portfolio Snapshot | `references/T0-portfolio-snapshot.md` | Alpaca account state → JSON (no P&L) |
| T1 | Signal Parser | `references/T1-signal-parser.md` | Macro advisor outputs → normalized signals (incl. empirical sentiment) |
| T2 | Position Reconciler | `references/T2-position-reconciler.md` | Current vs target → gap analysis |
| T3 | Trade Reasoner | `references/T3-trade-reasoner.md` | Gap analysis → trade plan with reasoning |
| T4 | Order Executor | `references/T4-order-executor.md` | Trade plan → Alpaca API orders |
| T5 | Trade Logger | `references/T5-trade-logger.md` | Execution results → permanent audit trail |
| T6 | Performance Tracker | `references/T6-performance-tracker.md` | P&L, attribution, drawdown, win rates |
| T7 | Self-Improvement Loop | `references/T7-self-improvement-loop.md` | Observe → inspect → amend → evaluate |
| T8 | External Portfolio Overlay | `references/T8-external-portfolio-overlay.md` | User's real holdings → exposure comparison (optional, Sunday only) |

## Scripts

All Python scripts are in the `scripts/` directory at the plugin root:

- `trade_executor.py` — Alpaca API wrapper (snapshot, orders, positions)
- `performance_calculator.py` — P&L attribution, Sharpe, drawdown
- `generate_dashboard.py` — HTML dashboard with P&L, trades, improvements, and external portfolio tabs
- `external_portfolio.py` — yfinance wrapper for external position pricing, classification, and exposure aggregation

## Macro Advisor Dependency

This plugin reads macro advisor outputs. The macro advisor must run its weekly cycle before the trading engine runs. Source paths are configured during `/trading-engine:setup` based on where the macro advisor plugin stores its outputs.

If macro advisor outputs are stale (>7 days), the trading engine skips new trades and only processes kill switch exits.

## Output Structure

Outputs are generated at runtime in the working directory:

```
outputs/
├── portfolio/          (snapshots, signals, reconciliation, trade plans)
├── trades/             (trade log, execution records, reasoning logs)
├── performance/        (weekly performance reports)
├── improvement/        (amendment tracker, performance tracker)
├── external/           (external portfolio snapshots, exposure, value history)
└── dashboard/          (HTML trading dashboard)
```

## Configuration

The system reads `config/user-config.json` for user preferences set during `/trading-engine:setup`:

- `alpaca_api_key` — Alpaca API key (paper trading)
- `alpaca_secret_key` — Alpaca secret key
- `paper` — always true (paper trading only)
- `macro_advisor_outputs` — path to macro advisor outputs directory
- `schedule_day` — day for the full run
- `schedule_time` — time for the full run
- `setup_completed` — whether setup has been run
- `external_portfolio_enabled` — whether external portfolio tracking is active
- `base_currency` — user's preferred currency for external portfolio valuation
