# Skill T2: Position Reconciler

## Objective

Compare what we currently hold (from T0 snapshot) against what we should hold (from T1 signals). Produce a gap analysis — the difference between current state and target state. No trading decisions here. Just the math.

## Inputs

1. **Portfolio snapshot** — `outputs/portfolio/latest-snapshot.json` (from T0)
2. **Trade signals** — `outputs/portfolio/latest-signals.json` (from T1)
3. **Risk limits** — `config/risk-limits.json`
4. **Regime templates** — `config/regime-templates.json`

## Reconciliation Process

### Step 1: Compute Target Allocation

Start from the regime template for the current regime (from T1 signals). The template provides baseline weights for each asset class.

Apply thesis overlays:
- For each tradeable thesis signal, include ALL ETF expressions (first, second, and third-order) in the target allocation using the thesis midpoint sizing as a starting point
- T2 does not differentiate sizing by expression order — that judgment belongs to T3. T2 includes every expression at the thesis midpoint so T3 has the full picture to reason about.
- STRENGTHENING theses: use top of sizing range as starting point
- WEAKENING theses: use bottom of sizing range as starting point
- Respect the 25% max thesis overlay cap from RULES.md

For the "Reduce/Avoid" entries: if the target allocation from the regime template includes an ETF that a thesis says to avoid, reduce that allocation by half and note the conflict.

### Step 2: Validate Against Risk Limits

Check the computed target against risk limits:

- No single position > 15% of portfolio
- No sector > 30% of equity allocation
- Cash >= 5%
- Total thesis overlay <= 25%

If any limit would be breached, scale down the offending positions proportionally until the limit is respected. Log which positions were scaled and why.

### Step 3: Compute Deltas

For each symbol in the target allocation or current portfolio:

```json
{
  "symbol": "SPY",
  "current_pct": 12.5,
  "current_shares": 50,
  "current_value": 25000,
  "target_pct": 15.0,
  "target_value": 30000,
  "delta_pct": 2.5,
  "delta_value": 5000,
  "delta_shares_approx": 10,
  "action": "BUY_MORE|SELL_SOME|HOLD|NEW_POSITION|CLOSE|EXIT_KILL_SWITCH",
  "layer": "regime|thesis_tactical|thesis_structural",
  "thesis": "thesis name if applicable",
  "priority": "URGENT|NORMAL|LOW",
  "reason": "why this delta exists"
}
```

Priority logic:
- **URGENT:** Kill switch exits (action = EXIT_KILL_SWITCH), drawdown circuit breaker
- **NORMAL:** Regime changes, new thesis entries, thesis sizing adjustments
- **LOW:** Small rebalances (<1% delta), regime refinements

### Step 4: Handle Kill Switch Exits

If T1 reported any kill switches as TRIGGERED:
- Set the corresponding positions to target 0%
- Mark action as EXIT_KILL_SWITCH
- Set priority to URGENT
- These override all other computations for that symbol

### Step 5: Handle Positions Not in Target

If the current portfolio holds a symbol that does not appear in the target allocation:
- Check if it's from a thesis that has been closed/invalidated → EXIT
- Check if it's from a prior regime that no longer applies → SELL_SOME (gradual)
- If unknown origin, flag for manual review

## Output Format

Save to `outputs/portfolio/latest-reconciliation.json`:

```json
{
  "reconciled_at": "ISO timestamp",
  "regime": "current regime from T1",
  "portfolio_value": 100000,
  "target_allocation": {
    "SPY": {"pct": 15.0, "layer": "regime", "source": "regime template"},
    "XLE": {"pct": 4.0, "layer": "thesis_tactical", "source": "ACTIVE-oil-thesis"}
  },
  "current_allocation": {
    "SPY": {"pct": 12.5, "shares": 50, "value": 25000},
    "cash": {"pct": 45.0, "value": 45000}
  },
  "deltas": [ ... ],
  "risk_check": {
    "max_single_position_ok": true,
    "max_sector_ok": true,
    "min_cash_ok": true,
    "max_thesis_overlay_ok": true,
    "drawdown_breach": false,
    "violations_corrected": []
  },
  "urgent_exits": [
    {"symbol": "...", "reason": "kill switch triggered for [thesis]"}
  ],
  "orphaned_positions": [
    {"symbol": "...", "reason": "no matching target — from closed thesis?"}
  ]
}
```

## Quality Standards

- Every target allocation must trace back to either a regime template entry or a specific thesis signal
- Delta computations must be arithmetically correct — verify that target percentages sum to approximately 100%
- Risk limit violations must be corrected before output, not left as warnings
- Kill switch exits are always included in deltas even if other computations would suggest holding

## Meta Block

```yaml
---
meta:
  skill: position-reconciler
  skill_version: "1.0"
  run_date: "[ISO date]"
  positions_current: [number]
  positions_target: [number]
  deltas_count: [number]
  urgent_exits: [number]
  risk_violations_corrected: [number]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```
