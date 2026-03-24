# Skill T3: Trade Reasoner

## Objective

This is the portfolio manager brain. It receives the reconciliation output (what we hold vs what we should hold) and decides which trades to actually execute this run. Not every delta gets traded immediately. The reasoner applies judgment about sequencing, timing, conviction, and the anti-confirmation-bias safeguards.

T3 receives position sizes but NOT unrealized P&L. It cannot see whether a position is winning or losing. This is deliberate. Decisions must be driven by the macro picture and thesis logic, not by anchoring to gains or losses.

## Inputs

1. **Reconciliation** — `outputs/portfolio/latest-reconciliation.json` (from T2)
2. **Signals** — `outputs/portfolio/latest-signals.json` (from T1). This includes the `regime_forecast` block containing the macro advisor's 6-month and 12-month regime probability distributions, key assumptions, confidence levels, and conditional triggers.
3. **Risk limits** — `${CLAUDE_PLUGIN_ROOT}/config/risk-limits.json`
4. **Trade log** — most recent entries from `outputs/trades/` (to check scaling state — how much of a target position we've already built)

## Regime Forecast Context

T3 has access to the macro advisor's 6-month and 12-month regime forecasts via `signals.regime_forecast`. This data is **informational context for reasoning, not a mechanical input to allocation.** T2 builds the target allocation from the current regime template. T3 uses the forecast to make better judgment calls about the trades T2 proposes.

The macro advisor's regime model is built on three underlying forces: **Growth** (rising or falling), **Inflation** (rising or falling), and **Liquidity** (loosening or tightening). The regime quadrant is the output of where these forces sit. The forecast block includes both the current state of each driver (score, direction, key data) and their projected trajectories at each horizon. When reasoning about individual positions, think in terms of these underlying drivers — not just the regime label. A position's sensitivity to growth, inflation, or liquidity tells you more about its durability than whether the regime name changes.

The forecast should inform T3's reasoning in three specific ways:

**1. Durability-aware sizing.** When deciding how aggressively to scale a regime-driven position, consider the expected shelf life of the current regime — and specifically, which underlying driver is expected to shift. A position that only works in the current regime should be sized more conservatively if the forecast gives that regime low persistence probability. A position that works across both the current regime and the most likely future regime can be sized at full conviction.

Use the driver trajectories to assess position-level durability. A position sensitive to inflation (like GSG) has a short shelf life if the inflation driver is forecast to normalize (oil returning to $70-80). A position sensitive to growth deceleration (like defensive equities) retains value even if the regime shifts from Stagflation to Disinflationary Slowdown, because the growth driver continues in the same direction. A position sensitive to liquidity (like short-duration bonds) depends on the Fed path — if liquidity is forecast to shift from tightening to easing, the position's rationale weakens on the 6-month horizon even if it's correct today.

Example: If the current regime is Stagflation and the 6-month forecast gives 50% probability to Disinflationary Slowdown, gold (which holds up in both regimes because it responds to both inflation fear AND growth fear) deserves full conviction sizing. But a commodities position like GSG (which works in Stagflation because inflation is rising, but suffers in Disinflationary Slowdown because the inflation driver normalizes) might warrant a more cautious scaling pace — not a skip, but slower steps.

**2. Devil's advocate enrichment.** The forecast's conditional triggers should appear in the devil's advocate reasoning for relevant positions. If the forecast says "Hormuz resolution within 6-8 weeks shifts regime to Disinflationary Slowdown," that is a concrete, testable bear case for every position that depends on the current Stagflation regime persisting.

**3. Cross-regime position awareness.** When choosing between multiple positions competing for turnover budget, prefer positions that carry value across the current regime AND the forecast's most likely next regime. This is a tiebreaker, not an override — a high-conviction current-regime-only position still beats a low-conviction cross-regime one.

**What this is NOT:**
- It is NOT a reason to build positions for a future regime that hasn't arrived. The target allocation comes from T2, which uses the current regime template. T3 does not second-guess T2's target.
- It is NOT a probability-weighted blending formula. There is no mechanical rule like "reduce position by (1 - persistence probability)."
- It is NOT a reason to skip positions. If the reconciliation says the portfolio needs GSG, the forecast doesn't override that. It may affect *pace* (scale slower if the regime looks short-lived) but not *direction* (skip entirely).
- It does NOT change the priority stack. Kill switches, drawdown, regime change rotation — all still come first. Forecast awareness is a lens on how to execute, not what to execute.

**In the reasoning log:** When the forecast materially influences a sizing or scaling decision, note it explicitly. Example: "GSG scaled at 40% of target instead of 50% — 6-month forecast gives Stagflation only 35% persistence, GSG has minimal value in Disinflationary Slowdown base case." This makes the judgment auditable and lets the improvement loop (T7) track whether forecast-informed sizing decisions outperform or underperform purely current-regime sizing.

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

**Structural thesis turnover reservation:**

When a structural thesis has been ACTIVE for 2+ runs with zero position, the reasoner must reserve its first-entry amount (33% of target allocation) from the turnover budget before allocating the remainder to regime scaling or other position adjustments. This prevents structural theses from being indefinitely deferred by the regime scaling queue.

The reservation is small by design — typically 1-2% of portfolio per structural thesis. It fits within the existing 25% turnover cap. The purpose is sequencing, not pace: structural theses with time-bound entry windows (e.g., "scale in over 8-12 weeks") should not miss their entry timing because regime positions consumed the entire budget for multiple consecutive runs.

If the total structural reservation exceeds 5% of portfolio in a single run, the reasoner should prioritize by thesis conviction and entry-window urgency, not by activation date.

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
- Total turnover (buys + sells as % of portfolio) should not exceed 25% in a single run under normal conditions. Structural thesis reservations (see Priority 4) come out of this budget — they do not increase it

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
