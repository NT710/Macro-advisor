# Trading Engine — Project Instructions

This is an autonomous trading system that executes trades on Alpaca paper trading based on signals from the Macro Advisor.

## Architecture Documentation

The system's methodology, architecture, and design decisions are documented in `skills/trading-engine/references/methodology.md`. This is the source of truth for how the system works.

**When you change any architectural decision — execution order, skill additions, risk parameters, allocation logic — update `methodology.md` to reflect the change.**

## Key Files

- `skills/trading-engine/references/RULES.md` — universal policy (risk constraints, execution discipline, anti-bias rules). Read before executing any skill.
- `config/risk-limits.json` — hardcoded risk parameters. NOT adjustable by T7 improvement loop.
- `config/regime-templates.json` — baseline allocations per regime. Starting points, not gospel.
- `config/user-config.json` — API keys and user preferences (created during setup, git-ignored).
- `skills/trading-engine/references/methodology.md` — full system documentation. Keep in sync with changes.
- `outputs/improvement/amendment-tracker.md` — persistent record of skill amendments.
- `outputs/improvement/performance-tracker.md` — persistent record of execution quality.

## Scheduled Tasks

- `trading-engine-sunday` runs Sundays at 19:00 CET. Full chain: T0→T1→T2→T3→T4→T5→T6→T7 + Dashboard.
- `trading-engine-wednesday` runs Wednesdays at 18:00 CET. Defense only: T0→T1→T2→T3(defense)→T4→T5.

## Principles

1. Never fabricate portfolio data. Every number comes from Alpaca's API.
2. Kill switch exits are absolute. No exceptions, no delays.
3. The trading engine reads from the macro advisor but never writes to it.
4. T3 (trade reasoner) never sees unrealized P&L. Decisions are based on macro signals.
5. The devil's advocate step is mandatory for every new position.
6. The self-improvement loop cannot modify risk constraints or anti-bias rules.
7. ETF expression sizing follows reasoning, not expression order — T3 decides sizing for first, second, and third-order expressions based on conviction and thesis logic.

## Macro Advisor Interface

This plugin depends on the Macro Advisor plugin. It reads macro advisor outputs from the macro advisor's output directory. It depends on the macro advisor running its Sunday cycle before the trading engine runs. If macro data is stale (>7 days), the trading engine skips new trades and only processes kill switch exits.
