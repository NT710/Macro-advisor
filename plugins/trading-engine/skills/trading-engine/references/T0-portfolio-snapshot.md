# Skill T0: Portfolio Snapshot

## Objective

Capture the current state of the Alpaca paper trading account. This is the factual foundation — every other skill reads from this snapshot. No interpretation, no judgment. Just the numbers.

## Execution

Run the trade executor in snapshot mode:

```bash
python scripts/trade_executor.py \
  --action snapshot \
  --config config/user-config.json \
  --output outputs/portfolio/
```

## Output

The script produces `outputs/portfolio/latest-snapshot.json` containing:

- **Account state:** cash, equity, portfolio_value, buying_power
- **Positions:** symbol, qty, side, market_value, current_price, avg_entry_price (NO unrealized P&L — that's deliberately excluded from T0)
- **Allocations:** each position as percentage of portfolio value, plus cash percentage
- **Recent orders:** last 20 orders with status, fill info

## What T0 Does NOT Include

Unrealized P&L per position. This is intentional. The trade reasoner (T3) must make decisions based on macro signals and position sizes, not based on whether it's winning or losing on a position. P&L is tracked separately in T6 for performance measurement.

## Validation Checks

After taking the snapshot, verify:

1. **Account is active:** `account.status` should be "ACTIVE". If not, log the issue and halt the run.
2. **Portfolio value is non-zero:** If portfolio_value is 0 or negative, something is wrong. Log and halt.
3. **Cash percentage computed:** Verify cash allocation percentage is calculated correctly.
4. **No stale data:** Timestamp should be within the last few minutes.

## When This Runs

- Every Sunday at 19:00 CET (after macro advisor completes)
- Every Wednesday at 18:00 CET (mid-week check)
- On-demand when manually triggered

## Meta Block

```yaml
---
meta:
  skill: portfolio-snapshot
  skill_version: "1.0"
  run_date: "[ISO date]"
  portfolio_value: [number]
  positions_count: [number]
  cash_pct: [number]
  account_status: "[ACTIVE/other]"
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```
