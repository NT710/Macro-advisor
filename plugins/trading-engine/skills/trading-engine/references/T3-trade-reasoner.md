# Skill T3: Trade Reasoner

## Objective

This is the portfolio manager brain. It receives the reconciliation output (what we hold vs what we should hold) and decides which trades to actually execute this run. Not every delta gets traded immediately. The reasoner applies judgment about sequencing, timing, conviction, and the anti-confirmation-bias safeguards.

T3 receives position sizes but NOT unrealized P&L. It cannot see whether a position is winning or losing. This is deliberate. Decisions must be driven by the macro picture and thesis logic, not by anchoring to gains or losses.

## Inputs

1. **Reconciliation** — `outputs/portfolio/latest-reconciliation.json` (from T2)
2. **Signals** — `outputs/portfolio/latest-signals.json` (from T1)
3. **Risk limits** — `${CLAUDE_PLUGIN_ROOT}/config/risk-limits.json`
4. **Trade log** — most recent entries from `outputs/trades/` (to check scaling state — how much of a target position we've already built)

## Decision Framework

### Priority 1: Kill Switch Exits

If the reconciliation contains any `urgent_exits`, process these first. No reasoning required — kill switches are absolute.

For each urgent exit:
```json
{
  "symbol": "XLE",
  "name": "Energy Select Sector SPDR",
  "action": "SELL",
  "qty": "all",
  "type": "market",
  "time_in_force": "day",
  "reason": "Kill switch triggered: [condition]. Thesis INVALIDATED.",
  "thesis": "ACTIVE-oil-thesis",
  "layer": "thesis_tactical",
  "devil_advocate": "N/A — mandatory exit",
  "priority": "URGENT"
}
```

### Priority 2: Drawdown Circuit Breaker

If the reconciliation risk_check shows `drawdown_breach: true`:
- Compute which positions to close to raise cash to 25%
- Close lowest-conviction positions first (WEAKENING theses > oldest tactical theses > smallest regime tilts)
- Use market orders

### Priority 3: Regime Change Rotation

If the signal parser reports a regime change:
- This is a significant event. The entire strategic allocation shifts.
- **Week 1 of new regime:** Execute 50% of the rotation (sell half of positions to close, buy half of new positions)
- **Week 2:** Complete the rotation to full target
- **Exception:** If shifting TO Stagflation, execute 75% in week 1 (Stagflation is the value-destroying regime — urgency is warranted)

### Priority 4: New Thesis Entries

For each new thesis signal that doesn't have a current position:

**Before creating any order, the devil's advocate step is mandatory — per position, not per thesis:**

Every position gets its own DA entry in the trade plan. This is non-negotiable because T7 matches bear cases against individual position outcomes. A regime-level DA cannot be attributed to a specific loss.

For positions sharing a macro thesis (e.g., multiple regime-driven entries), use a shared base bear case plus a mandatory position-specific addendum:

```
DEVIL'S ADVOCATE — [Thesis Name] — [Symbol] ([Full ETF Name])
Base bear case: [1 paragraph articulating the shared macro scenario where the thesis is wrong.
What specific, plausible development would invalidate the regime call or thesis logic?]
Position-specific risk: [1-2 sentences on what could go wrong for THIS specific ETF beyond
the shared macro thesis. E.g., sector-specific headwinds, concentration risk, liquidity,
regulatory exposure. Every ETF has at least one idiosyncratic risk — name it.]
Bear case probability: [Low / Medium / High — honest assessment for this position]
Proceed: [Yes — bear case acknowledged but conviction holds / No — bear case is too strong, skip this trade]
```

The base bear case text may be identical across positions sharing a thesis. The position-specific risk must be unique to the ETF. "Same as above" is not acceptable — if you cannot articulate a position-specific risk, that is itself a signal worth examining.

If "Proceed: No" — skip the trade and log the decision. The improvement loop will track whether skipped trades would have been profitable or not.

**Scaling logic for new entries:**
- Tactical thesis: Enter at 50% of target on first run, 100% on next run if thesis still ACTIVE
- Structural thesis: Enter at 33% of target on first run, 66% on run 2, 100% on run 3-4. Structural theses are patient by nature.
- STRENGTHENING thesis: Can enter at 75% on first run

**Order type for new entries:**
- Limit order at last close price + 0.3% buffer (for buys) or - 0.3% (for sells)
- If the position is driven by a kill-switch exit from the reconciler, use market order instead

**Expression sizing — reasoning over formula:**

The reasoner decides sizing for every ETF expression in a thesis — first, second, or third-order — based on conviction, thesis logic, and macro context. There is no mechanical rule mapping expression order to position size. A third-order expression can be a better trade than a first-order one if the reasoning supports it.

For each expression the reasoner includes, articulate:
```
EXPRESSION SIZING — [Thesis Name] — [ETF] — [Order: 1st/2nd/3rd]
Conviction reasoning: [why this expression deserves this size in current context]
Sizing: [X% of portfolio]
Decision: [INCLUDE / SKIP]
```

Skipping an expression is fine — but the reason should be "the reasoning doesn't support it," not "it's third-order so we skip by default."

### Priority 5: Position Adjustments

For existing positions that need resizing (delta from reconciliation):
- If delta < 1% of portfolio: SKIP (not worth the transaction)
- If delta is 1-3%: adjust with limit order
- If delta > 3%: split into two orders across two runs

### Priority 6: Orphaned Position Cleanup

Positions flagged as "orphaned" by T2 (no matching target):
- If from a thesis that was closed more than 2 weeks ago: close immediately
- If recently orphaned: hold for one more run, then close
- Log the reason clearly

## Output Format

Produce two files:

### 1. Trade Plan: `outputs/portfolio/latest-trade-plan.json`

```json
{
  "planned_at": "ISO timestamp",
  "regime": "current regime",
  "run_type": "sunday_full|wednesday_check",
  "orders": [
    {
      "symbol": "SPY",
      "name": "SPDR S&P 500 ETF Trust",
      "action": "buy|sell",
      "qty": 10,
      "type": "market|limit",
      "limit_price": null,
      "time_in_force": "day",
      "reason": "Regime tilt: Goldilocks favors US equities. Scaling to 50% of target.",
      "thesis": "",
      "layer": "regime",
      "mechanism_type": "",
      "priority": "NORMAL",
      "devil_advocate": "Base bear case: if tariff escalation continues, Goldilocks assessment may be premature. Growth could decelerate Q2. Position-specific risk: SPY has elevated mega-cap tech concentration — a sector rotation away from growth would hit SPY harder than equal-weight alternatives. Probability: Medium. Proceed: Yes — liquidity picture still supportive.",
      "scaling_state": "1_of_2"
    }
  ],
  "skipped": [
    {
      "symbol": "OIH",
      "name": "VanEck Oil Services ETF",
      "reason": "Third-order expression for oil thesis — no concrete edge articulated. SKIP.",
      "delta_pct": 0.75
    }
  ],
  "summary": {
    "total_orders": 5,
    "buys": 3,
    "sells": 2,
    "urgent_exits": 0,
    "new_positions": 2,
    "adjustments": 1,
    "skipped": 3,
    "estimated_turnover_pct": 8.5
  }
}
```

### 2. Reasoning Log: `outputs/trades/YYYY-MM-DD-reasoning.md`

A readable markdown document explaining every decision:

```markdown
## Trade Reasoning — [Date]

### Regime Context
[Current regime, weeks in regime, direction. 2-3 sentences.]

### Kill Switch Exits
[None / list with explanation]

### New Positions
#### [Symbol] ([Full ETF Name]) — [Layer] — [Thesis if applicable]
- Target: [X]% of portfolio
- This run: [Y]% (scaling [N of M])
- Reason: [from reconciliation]
- Devil's advocate (base): [shared macro bear case]
- Devil's advocate (position-specific): [risk unique to this ETF]
- Bear case probability: [Low/Medium/High]
- Order: [type] [qty] shares at [price/market]

### Adjustments
[existing positions being resized]

### Skipped
[what we decided NOT to do, and why]

### Risk State After Execution
- Estimated cash: [X]%
- Largest position: [symbol] ([full name]) at [X]%
- Thesis overlay: [X]%
- Drawdown from HWM: [X]%
```

## Wednesday Mid-Week Check

On Wednesday runs, T3 operates in defensive mode only:
- Process kill switch exits (Priority 1)
- Process drawdown circuit breaker (Priority 2)
- Do NOT enter new positions
- Do NOT adjust existing positions for regime changes
- Do NOT act on new theses

The Wednesday check is defense only. Offense happens on Sunday.

## Quality Standards

- Every order must have a non-empty `reason` field
- Every new position must have a `devil_advocate` entry with both a base bear case and a position-specific risk. The position-specific risk must be unique to the ETF — not a copy of the base.
- Kill switch exits must be processed before any other orders
- The reasoning log must be human-readable — it's the primary audit trail
- Skipped trades are as important as executed trades in the log
- Total turnover (buys + sells as % of portfolio) should not exceed 25% in a single run under normal conditions

## Meta Block

```yaml
---
meta:
  skill: trade-reasoner
  skill_version: "1.0"
  run_date: "[ISO date]"
  run_type: "sunday_full|wednesday_check"
  orders_planned: [number]
  orders_urgent: [number]
  orders_new_positions: [number]
  orders_skipped: [number]
  devil_advocates_written: [number]
  devil_advocates_blocked: [number]
  estimated_turnover_pct: [number]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```
