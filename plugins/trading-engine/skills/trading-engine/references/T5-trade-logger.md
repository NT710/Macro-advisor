# Skill T5: Trade Logger

## Objective

Consolidate all trade activity from the current run into a permanent, auditable log. Every trade, every skip, every reasoning decision, every devil's advocate argument gets recorded. This is the institutional memory of the trading engine.

## Inputs

1. **Execution results** — `outputs/trades/YYYY-MM-DD-HHMM-execution.json` (from T4)
2. **Trade plan** — `outputs/portfolio/latest-trade-plan.json` (from T3)
3. **Reasoning log** — `outputs/trades/YYYY-MM-DD-reasoning.md` (from T3)
4. **Post-execution snapshot** — latest from `outputs/portfolio/`

## Log Entry Format

For each trade executed, append to `outputs/trades/trade-log.json` (cumulative file):

```json
{
  "trade_id": "T-YYYYMMDD-NNN",
  "date": "ISO date",
  "run_type": "sunday_full|wednesday_check",
  "symbol": "SPY",
  "name": "SPDR S&P 500 ETF Trust",
  "side": "buy|sell",
  "qty": 10,
  "fill_price": 525.30,
  "order_type": "market|limit",
  "slippage_pct": 0.04,
  "status": "filled|partial|rejected|cancelled",
  "layer": "regime|thesis_tactical|thesis_structural",
  "thesis": "thesis name or empty",
  "mechanism_type": "divergence|regime_shift|positioning_extreme|...",
  "reason": "full reasoning from T3",
  "devil_advocate": "bear case text from T3",
  "scaling_state": "1_of_2|2_of_2|full",
  "portfolio_pct_after": 15.2,
  "regime_at_entry": "Goldilocks",
  "realized_pl": null,
  "closed_date": null,
  "close_reason": null
}
```

When a position is closed (sell trade), find the matching open trade(s) and update:
- `realized_pl`: compute from entry price to exit price
- `closed_date`: date of the close
- `close_reason`: "kill_switch|regime_change|time_expired|rebalance|manual"

## Summary Log

Also produce a human-readable weekly summary appended to `outputs/trades/weekly-summaries.md`:

```markdown
## Trading Summary — [Date] ([Run Type])

### Portfolio State
- Portfolio value: $[X]
- Cash: [X]%
- Positions: [N]
- Regime: [quadrant] (week [N])

### Trades Executed
| Symbol | Name | Side | Qty | Price | Layer | Thesis | Reason |
|--------|------|------|-----|-------|-------|--------|--------|
| SPY | SPDR S&P 500 ETF Trust | BUY | 10 | $525.30 | regime | — | Goldilocks tilt |

### Trades Skipped
| Symbol | Name | Reason |
|--------|------|--------|
| OIH | VanEck Oil Services ETF | Third-order: no concrete edge |

### Kill Switch Activity
[None this run / details]

### Devil's Advocate Log
[Thesis: bear case summary. Proceed: Yes/No]

### Risk State
- Max position: [symbol] ([full name]) at [X]%
- Thesis overlay: [X]%
- Drawdown: [X]% from HWM
- Risk violations: [none / list]
```

## Closed Trade Tracking

When a position is fully closed, create a closed-trade entry in `outputs/trades/closed-trades.json`:

```json
{
  "symbol": "XLE",
  "name": "Energy Select Sector SPDR",
  "entry_date": "2026-03-20",
  "exit_date": "2026-04-15",
  "entry_price": 85.30,
  "exit_price": 82.10,
  "qty": 20,
  "realized_pl": -64.00,
  "realized_pl_pct": -3.75,
  "holding_days": 26,
  "layer": "thesis_tactical",
  "thesis": "ACTIVE-oil-thesis",
  "mechanism_type": "divergence",
  "close_reason": "kill_switch",
  "devil_advocate_at_entry": "Bear case was oil supply recovery faster than expected. That's what happened.",
  "bear_case_realized": true
}
```

The `bear_case_realized` field is critical for the improvement loop. It tracks whether the loss came from a risk we articulated at entry or from something we didn't see coming.

## Quality Standards

- Every filled order from T4 must appear in the trade log. No missing entries.
- The trade log is append-only. Never delete or modify historical entries (except to add realized_pl when closing).
- The weekly summary must be written even if zero trades occurred — a "no trades this week" summary is useful information.
- Closed trade entries must accurately link entry and exit trades.

## Meta Block

```yaml
---
meta:
  skill: trade-logger
  skill_version: "1.0"
  run_date: "[ISO date]"
  trades_logged: [number]
  trades_closed: [number]
  devil_advocates_logged: [number]
  bear_cases_realized: [number]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```
