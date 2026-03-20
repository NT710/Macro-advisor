# Skill T6: Performance Tracker

## Objective

Measure how the trading engine is actually performing. This is the only skill that sees unrealized P&L. It produces weekly performance reports with attribution, drawdown analysis, and win rates — the numbers that tell you whether the system is adding value or destroying it.

## Inputs

1. **Performance snapshot** — run the trade executor in performance mode:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/trade_executor.py \
     --action performance_snapshot \
     --config ${CLAUDE_PLUGIN_ROOT}/config/user-config.json \
     --output ${CLAUDE_PLUGIN_ROOT}/outputs/portfolio/
   ```
2. **Historical snapshots** — all files in `${CLAUDE_PLUGIN_ROOT}/outputs/portfolio/`
3. **Trade log** — `${CLAUDE_PLUGIN_ROOT}/outputs/trades/trade-log.json`
4. **Closed trades** — `${CLAUDE_PLUGIN_ROOT}/outputs/trades/closed-trades.json`
5. **Performance calculator** — run the script:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/performance_calculator.py \
     --snapshots ${CLAUDE_PLUGIN_ROOT}/outputs/portfolio/ \
     --trades ${CLAUDE_PLUGIN_ROOT}/outputs/trades/ \
     --output ${CLAUDE_PLUGIN_ROOT}/outputs/performance/
   ```

## Weekly Performance Report

Produce `${CLAUDE_PLUGIN_ROOT}/outputs/performance/YYYY-Www-performance.md`:

```markdown
## Trading Engine Performance — Week of [Date]

### Portfolio Summary
- Starting value (week): $[X]
- Ending value (week): $[X]
- Week return: [X]%
- Cumulative return (since inception): [X]%
- High water mark: $[X]
- Current drawdown from HWM: [X]%
- Max drawdown (all-time): [X]%
- Sharpe ratio (annualized): [X]

### Attribution — Where Did Returns Come From?

| Layer | Positions | Allocation % | Week Return | Contribution |
|-------|-----------|-------------|-------------|--------------|
| Regime tilts | [N] | [X]% | [X]% | [X]% |
| Tactical theses | [N] | [X]% | [X]% | [X]% |
| Structural theses | [N] | [X]% | [X]% | [X]% |
| Cash | 1 | [X]% | ~0% | — |

This tells us whether the value is coming from the regime model (strategic) or from
the thesis overlays (tactical/structural). If regime tilts consistently outperform
thesis overlays, the macro advisor's regime calls are the real edge. If thesis overlays
consistently outperform, the thesis generation is the edge.

### Thesis Performance

| Thesis | Type | Status | Weeks Active | Unrealized P&L | Mechanism |
|--------|------|--------|-------------|----------------|-----------|
| [name] | tactical | ACTIVE | [N] | [X]% | [type] |

### Closed Trades This Week

| Symbol | Entry | Exit | P&L | P&L % | Days Held | Close Reason | Bear Case Hit? |
|--------|-------|------|-----|-------|-----------|-------------|----------------|
| [sym] | $[X] | $[X] | $[X] | [X]% | [N] | [reason] | [yes/no] |

### Cumulative Win Rate

| Category | Wins | Losses | Win Rate | Avg Win | Avg Loss | Profit Factor |
|----------|------|--------|----------|---------|----------|---------------|
| All trades | [N] | [N] | [X]% | $[X] | $[X] | [X] |
| Regime trades | [N] | [N] | [X]% | $[X] | $[X] | [X] |
| Tactical thesis | [N] | [N] | [X]% | $[X] | $[X] | [X] |
| Structural thesis | [N] | [N] | [X]% | $[X] | $[X] | [X] |

### Win Rate by Mechanism Type

| Mechanism | Trades | Win Rate | Avg P&L % |
|-----------|--------|----------|-----------|
| Divergence | [N] | [X]% | [X]% |
| Regime shift | [N] | [X]% | [X]% |
| Positioning extreme | [N] | [X]% | [X]% |
| Policy shift | [N] | [X]% | [X]% |
| Structural constraint | [N] | [X]% | [X]% |

This table answers: which types of thesis mechanisms actually make money? After 8+ weeks,
this data tells you which pattern categories the macro advisor is good at spotting
and which it isn't.

### Devil's Advocate Accuracy

| Total Entries | Bear Cases Realized | Bear Cases Not Realized | Unarticulated Losses |
|--------------|--------------------|-----------------------|---------------------|
| [N] | [N] ([X]%) | [N] ([X]%) | [N] ([X]%) |

"Unarticulated losses" are the most important number. These are losses where the
devil's advocate at entry did NOT identify the risk that actually materialized.
A high unarticulated loss rate means the bear case step is not rigorous enough.

### Risk Metrics
- VaR (95%, 1-week, historical): $[X] ([X]% of portfolio)
- Current concentration: largest position [symbol] at [X]%
- Sector concentration: [sector] at [X]%
- Thesis overlay: [X]% (limit: 25%)
- Drawdown breach events: [N] (all-time)

### Benchmark Comparison (if available)
- SPY total return over same period: [X]%
- 60/40 (SPY/TLT) return: [X]%
- Engine return: [X]%
- Alpha vs SPY: [X]%
- Alpha vs 60/40: [X]%
```

## Drawdown Alert

If current drawdown exceeds 7% (approaching the 10% circuit breaker), produce a prominent alert at the top of the report:

```markdown
⚠️ DRAWDOWN ALERT: Portfolio is [X]% below high water mark.
Circuit breaker triggers at 10%. Current trajectory: [improving/worsening].
Largest contributors to drawdown: [top 3 losing positions with P&L].
```

## Quality Standards

- All P&L figures must come from Alpaca API data, not estimated
- Attribution requires accurate tagging of each position's layer (regime vs thesis) — this comes from the trade log
- Win rate calculations must only include fully closed trades, not unrealized positions
- The devil's advocate accuracy tracking requires matching closed-trade bear case text against actual outcomes — this is a judgment call by this skill, not a mechanical check
- Benchmark comparison is informational. The system should not optimize to beat the benchmark — that would introduce a bias. It's context, not a target.

## Meta Block

```yaml
---
meta:
  skill: performance-tracker
  skill_version: "1.0"
  run_date: "[ISO date]"
  portfolio_value: [number]
  week_return_pct: [number]
  cumulative_return_pct: [number]
  max_drawdown_pct: [number]
  sharpe_ratio: [number]
  trades_closed_this_week: [number]
  overall_win_rate: [number or null]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```
