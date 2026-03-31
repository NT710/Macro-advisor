# Skill T4: Order Executor

## Objective

Take the trade plan from T3 and submit the orders to Alpaca. This skill is mechanical — it does not second-guess the trade reasoner. It translates the plan into API calls and records the results.

## Inputs

1. **Trade plan** — `outputs/portfolio/latest-trade-plan.json` (from T3)
2. **Config** — `config/user-config.json`

## Execution

### Pre-Flight Checks

Before submitting any orders:

1. **Market hours check:** Alpaca paper trading accepts orders outside market hours but they queue. Log whether market is open or closed. If closed, orders will execute at next open.

2. **Account status check:** Run a quick snapshot to verify account is active and not trading-blocked.

3. **Buying power check:** For buy orders, verify total cost doesn't exceed available buying power. If it does, scale down all buy orders proportionally and log the adjustment.

4. **Duplicate order check:** Read recent orders from Alpaca. If an identical order (same symbol, side, qty) was submitted in the last 24 hours and is still pending, skip the duplicate.

5. **Structural new-position limit price check (AT-2026W14-001):** For any buy order where `layer` is `thesis_structural` AND the symbol has no current holding (new position entry, not an add to existing), verify the stored limit price is within 5% of the current live ask price. Fetch the live quote using the bash command below, then compare against the stored limit.

   - If deviation ≤ 5%: proceed with stored limit. Log the check result.
   - If deviation > 5%: recalculate limit as `current_ask × 1.003`. Replace the stored limit. Log with note: `"Limit reset: prior $X → current $Y (N% deviation)."` This reset is automatic — not discretionary.
   - If the live quote fetch fails: log the failure, proceed with stored limit. Do not block the order.
   - This check does NOT apply to: existing positions being adjusted (fill price anchors the limit), regime or tactical thesis layers, or sell orders.

   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/trade_executor.py \
     --action quote \
     --config config/user-config.json \
     --symbol GDX
   ```

### Order Submission

Process orders in priority order from the trade plan:
1. URGENT (kill switch exits) — submit immediately as market orders
2. NORMAL — submit in sequence
3. LOW — submit last

For each order:

```bash
# Write order spec to temp file
echo '{"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "side": "buy", "qty": 10, "type": "limit", "limit_price": 525.50, "time_in_force": "day"}' > /tmp/order.json

# Submit via trade executor
python ${CLAUDE_PLUGIN_ROOT}/scripts/trade_executor.py \
  --action submit_order \
  --config config/user-config.json \
  --order-file /tmp/order.json
```

Or for batch submission:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/trade_executor.py \
  --action submit_batch \
  --config config/user-config.json \
  --order-file outputs/portfolio/latest-trade-plan-orders.json \
  --output outputs/trades/
```

### Post-Submission Verification

After all orders are submitted, take a new snapshot to verify:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/trade_executor.py \
  --action snapshot \
  --config config/user-config.json \
  --output outputs/portfolio/
```

Compare pre and post snapshots. Log:
- Orders submitted: [N]
- Orders filled: [N]
- Orders pending: [N]
- Orders rejected: [N]
- Rejection reasons: [list]

### Handling Failures

- **Rejected order:** Log the rejection reason. Do NOT retry automatically. The trade log should record the failure.
- **Partial fill:** Log the partial fill. The remaining quantity will be picked up in the next reconciliation cycle.
- **API error:** Log the error. If the error is transient (timeout, 5xx), retry once after 30 seconds. If it fails again, skip and log.
- **Insufficient buying power:** If a buy order fails for insufficient funds, log it and skip. Do not cancel other orders to free up funds.

## Output

Save execution results to `outputs/trades/YYYY-MM-DD-HHMM-execution.json`:

```json
{
  "executed_at": "ISO timestamp",
  "orders_submitted": 5,
  "orders_filled": 4,
  "orders_pending": 1,
  "orders_rejected": 0,
  "results": [
    {
      "symbol": "SPY",
      "name": "SPDR S&P 500 ETF Trust",
      "side": "buy",
      "qty_requested": 10,
      "qty_filled": 10,
      "fill_price": 525.30,
      "order_id": "...",
      "status": "filled",
      "reason": "from trade plan",
      "thesis": "",
      "layer": "regime",
      "slippage_pct": 0.04
    }
  ],
  "pre_execution_snapshot": "reference to snapshot file",
  "post_execution_snapshot": "reference to snapshot file"
}
```

## Quality Standards

- Every order submission attempt must be logged, successful or not
- Slippage (difference between planned price and fill price) must be computed for every filled order
- Kill switch exits must be verified as filled. If a kill switch exit is rejected or fails, this is a critical alert — log at highest severity
- The executor never modifies the trade plan. If something doesn't work, it logs the failure for T7 to analyze
- Every structural new-position limit check (Pre-Flight #5) must be logged — whether the limit was kept, reset, or the check was skipped due to a quote failure

## Meta Block

```yaml
---
meta:
  skill: order-executor
  skill_version: "1.1"
  run_date: "[ISO date]"
  orders_submitted: [number]
  orders_filled: [number]
  orders_pending: [number]
  orders_rejected: [number]
  kill_switch_exits_verified: [number]
  structural_limit_checks: [number]
  structural_limit_resets: [number]
  avg_slippage_pct: [number]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```
