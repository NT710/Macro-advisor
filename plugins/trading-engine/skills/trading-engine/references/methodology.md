# Trading Engine — Methodology & System Reference

**Version:** 1.0
**Last Updated:** 2026-03-31
**Platform:** Alpaca Paper Trading via alpaca-py
**Dependency:** Macro Advisor (read-only)

---

## What This System Does

The trading engine translates macro research into actual portfolio positions. It reads the Macro Advisor's weekly outputs (regime assessments, asset tilts, investment theses), computes a target portfolio, reasons through which trades to execute, submits orders to Alpaca paper trading, and tracks performance. It runs autonomously on a schedule, with a self-improvement loop that monitors execution quality and trading performance.

The macro advisor is the research analyst. The trading engine is the portfolio manager. They don't share state. The trading engine reads research outputs and makes independent execution decisions.

---

## Core Design Principles

### 1. Complete Separation from Macro Advisor
The trading engine reads macro advisor outputs from a fixed directory path. It never writes back, modifies, or provides feedback to the macro advisor. If the macro advisor changes its file format, the signal parser (T1) adapts. The two systems evolve independently.

### 2. Anti-Confirmation Bias Architecture
Three structural safeguards prevent the system from fooling itself:
- **T3 is P&L blind.** The trade reasoner sees positions and sizes but not unrealized gains/losses. Decisions are based on macro signals and thesis logic.
- **T1 is stateless.** The signal parser reads fresh every run. No memory of prior signals, no anchoring.
- **T7 tracks by mechanism, not by asset class.** The improvement loop measures which thesis types (divergence, regime shift, positioning extreme) work — not which sectors or ETFs recently performed well.

### 3. Mandatory Devil's Advocate
Every new position requires an articulated bear case before entry. The improvement loop tracks whether realized losses matched the bear case (anticipated risk) or came from unarticulated risks (blind spots). This is the system's primary tool for improving its own reasoning quality.

### 4. Hardcoded Risk Constraints
Risk limits are not adjustable by the improvement loop: max position 15%, max sector 30%, max drawdown 10% trigger, min cash 5%, max thesis overlay 25%, no leverage, long-only. These exist to prevent the system from optimizing itself into a concentrated blow-up.

---

## System Architecture

### Skill Chain

```
Skill T0: Portfolio Snapshot     (Alpaca account state → JSON)
Skill T1: Signal Parser          (macro advisor outputs → normalized trade signals)
Skill T2: Position Reconciler    (current positions vs target → gap analysis)
Skill T3: Trade Reasoner         (gap analysis → trade plan with reasoning)
Skill T4: Order Executor         (trade plan → Alpaca API orders)
Skill T5: Trade Logger           (execution results → permanent audit trail)
Skill T6: Performance Tracker    (P&L, attribution, drawdown, win rates)
Skill T7: Self-Improvement Loop  (observe → inspect → amend → evaluate)
Skill T8: External Portfolio     (user's real holdings → exposure overlay, optional)
```

**Sunday full run:** T0→T1→T2→T3→T4→T5→T6→T7→T8
**Wednesday defense check:** T0→T1→T2→T3(defense only)→T4→T5

### Data Flow

```
Macro Advisor outputs (read-only)
    ↓
T1: Signal Parser → latest-signals.json
    ↓
T0: Portfolio Snapshot → latest-snapshot.json
    ↓
T2: Position Reconciler → latest-reconciliation.json
    ↓
T3: Trade Reasoner → latest-trade-plan.json + reasoning.md
    ↓
T4: Order Executor → execution.json
    ↓
T5: Trade Logger → trade-log.json + weekly-summaries.md
    ↓
T6: Performance Tracker → weekly performance report
    ↓
T7: Self-Improvement Loop → improvement report + amendment proposals
    ↓
T8: External Portfolio Overlay → exposure comparison + thesis alignment + kill switch alerts (optional, Sunday only)
    ↓
Dashboard Generator → HTML dashboard (P&L + Trades + Improvements + External Portfolio tabs)
```

---

## Interface Contract with Macro Advisor

The trading engine reads three categories of output:

1. **Weekly synthesis** — regime assessment, asset tilts, sector view, regime forecasts. Tells the trading engine the strategic allocation.
2. **Active theses** — specific ETF expressions with sizing ranges, kill switches, assumption status. Tells the trading engine the tactical/structural overlays.
3. **Data snapshot** — latest FRED/Yahoo data for kill switch evaluation.

Source paths (relative to Trading/):
- `{macro_advisor_outputs}/synthesis/`
- `{macro_advisor_outputs}/theses/active/`
- `{macro_advisor_outputs}/theses/closed/`
- `{macro_advisor_outputs}/data/`
- `{macro_advisor_outputs}/briefings/`
- `{macro_advisor_skills}/references/etf-reference.md`

---

## Allocation Framework

### Layer 1: Strategic (Regime-Driven)
Baseline allocations per regime are defined in `${CLAUDE_PLUGIN_ROOT}/config/regime-templates.json`. Four family-level templates exist (Goldilocks, Overheating, Disinflationary Slowdown, Stagflation), each specifying target weights for ~12-14 asset class buckets. A `_liquidity_modifiers` section adjusts these weights based on whether liquidity is ample or tight. The macro advisor outputs both a full 8-regime label (e.g., "Goldilocks — Ample Liquidity") and a `regime_family` (e.g., "Goldilocks"). T1 passes both. T2 uses the family template as the base, then applies the liquidity modifier overlay. The synthesis cross-asset table can further modify these weights (Bull = 1.2x template, Neutral = 1.0x, Bear = 0.5x or 0).

### Layer 2: Tactical/Structural (Thesis-Driven)
Active theses add overlays on top of the strategic layer. The trade reasoner (T3) decides sizing for every ETF expression — first, second, or third-order — based on the thesis logic, conviction, and macro context. There is no mechanical formula mapping expression order to position size. A compelling third-order expression can be sized larger than a weak first-order one.

Sizing guidance:
- The thesis itself defines a sizing range (e.g., "medium 3-5%"). T3 decides where within that range to allocate, and how to distribute across the thesis's ETF expressions.
- STRENGTHENING theses: T3 should lean toward the top of the sizing range
- WEAKENING theses: T3 should lean toward the bottom or exit
- Total thesis overlay capped at 25% of portfolio
- T3 must articulate its sizing reasoning for each expression — why this size, for this expression, in this macro context

### Position Sizing Logic
- New tactical thesis: scale in over 2 runs (50% → 100%)
- New structural thesis: scale in over 3-4 runs (33% → 66% → 100%)
- STRENGTHENING thesis: 75% on first entry
- Regime change rotation: 2 runs normally, 1-2 runs for Stagflation shift

---

## Risk Management

### Static Limits (Not Adjustable by T7)
| Parameter | Limit | Rationale |
|-----------|-------|-----------|
| Max single position | 15% | Prevent concentration risk |
| Max sector | 30% | Sector diversification |
| Max drawdown trigger | 10% | Circuit breaker |
| Min cash | 5% | Liquidity buffer |
| Max thesis overlay | 25% | Research quality is unproven |
| Leverage | None (1x) | Paper trading learning phase |
| Short selling | Not allowed | Long-only |

### Dynamic Risk Responses
- **10% drawdown:** Raise cash to 25% by closing weakest-conviction positions
- **Kill switch fired:** Immediate market-order exit, no discretion
- **Regime change to Stagflation:** Accelerated rotation (1-2 runs vs normal 2-3)

---

## Self-Improvement Loop

Same OBSERVE → INSPECT → AMEND → EVALUATE framework as the macro advisor. Tracks:

**Execution quality:** Fill rates, slippage, rejection rates, kill switch response time.
**Reasoning quality:** Devil's advocate rigor, expression sizing differentiation, skip quality.
**Performance quality:** Attribution by layer (regime vs thesis), win rate by mechanism type, bear case accuracy.

The improvement loop CAN adjust: limit order buffers, scaling pace, reconciliation thresholds, signal parsing logic.
The improvement loop CANNOT adjust: risk constraints, anti-bias rules, kill switch discipline, devil's advocate requirement.

Persistent state files:
- `outputs/improvement/amendment-tracker.md`
- `outputs/improvement/performance-tracker.md`

---

## Scheduling

| Task | Day | Time (CET) | Chain | Purpose |
|------|-----|------------|-------|---------|
| Sunday full run | Sunday | 19:00 | T0→T1→T2→T3→T4→T5→T6→T7→T8 | Full analysis + trading + external portfolio |
| Wednesday check | Wednesday | 18:00 | T0→T1→T2→T3(defense)→T4→T5 | Kill switches + drawdown only |

The Sunday run starts 3 hours after the macro advisor (16:00 CET) to ensure fresh macro outputs are available.

---

## File Structure

```
Trading/
├── CLAUDE.md                        (project instructions)
├── CONNECTORS.md                    (MCP connector requirements)
├── README.md
├── hooks/
│   └── hooks.json                   (session start hook — reads user config)
├── skills/
│   ├── RULES.md                     (risk constraints, execution discipline, anti-bias)
│   ├── references/
│   │   ├── methodology.md           (this file)
│   │   ├── T0-portfolio-snapshot.md
│   │   ├── T1-signal-parser.md
│   │   ├── T2-position-reconciler.md
│   │   ├── T3-trade-reasoner.md
│   │   ├── T4-order-executor.md
│   │   ├── T5-trade-logger.md
│   │   ├── T6-performance-tracker.md
│   │   ├── T7-self-improvement-loop.md
│   │   └── T8-external-portfolio-overlay.md
├── scripts/
│   ├── assets/
│   │   └── chart.min.js             (bundled Chart.js for offline dashboards)
│   ├── generate_dashboard.py        (HTML dashboard with Overview, Positions, Trades & Reasoning, Performance, External, Improvements, and Rules tabs)
│   ├── performance_calculator.py    (P&L, attribution, Sharpe)
│   ├── trade_executor.py            (alpaca-py API wrapper)
│   ├── external_portfolio.py        (yfinance wrapper for external positions)
│   ├── trading-dashboard-template.html (Jinja2 HTML template for dashboard)
│   ├── test_dashboard.py            (unit tests for dashboard generator)
│   └── requirements.txt             (alpaca-py, yfinance, jinja2, pytest)
├── config/
│   ├── risk-limits.json             (hardcoded — not adjustable by T7)
│   ├── regime-templates.json        (baseline allocations per regime)
│   └── user-config.json             (API keys, created during setup)
├── commands/
│   ├── setup.md                     (first-run configuration)
│   ├── run-trading.md               (manual execution trigger)
│   └── implement-improvements.md    (review T7 amendment proposals)
├── outputs/
│   ├── portfolio/                   (snapshots, signals, reconciliation, trade plans)
│   ├── trades/                      (trade log, execution records, reasoning logs)
│   ├── performance/                 (weekly performance reports)
│   ├── improvement/                 (amendment tracker, performance tracker)
│   ├── external/                    (external portfolio snapshots, exposure, value history)
│   └── dashboard/                   (HTML trading dashboard — generated after each run)
```

---

## External Portfolio Overlay (T8)

An optional module that tracks the user's real-world holdings and maps them against the paper portfolio and active theses. Configured during setup — if the user opts out, T8 is skipped entirely.

### Design Principle: Information, Not Influence

T8 is strictly read-only with respect to T1-T7. External positions never affect signal parsing, reconciliation, trade reasoning, performance tracking, or self-improvement. The paper portfolio is a clean sandbox that expresses macro research without contamination from the user's existing holdings. T8 produces a separate informational overlay — it shows the map between model and reality, but the model doesn't know about reality.

### What T8 Produces

1. **Portfolio valuation** — live pricing via yfinance, FX conversion to base currency, P&L tracking (when entry price was provided).
2. **Exposure aggregation** — sector, geography, asset class, and currency breakdowns. For ETFs with sector weightings data, distributes allocation proportionally (e.g., QQQ at 20% of portfolio contributes 10% to tech if QQQ is 50% tech). For individual stocks, uses yfinance sector/industry directly.
3. **Paper portfolio comparison** — side-by-side exposure across all four dimensions with delta computation.
4. **Thesis alignment scan** — maps external holdings to active theses by exposure characteristics (sector, geography, macro factor), not by ticker or asset class. This means a gold miner equity matches a "long gold" thesis even if the paper portfolio expresses it via a commodity ETF. Identifies positions with overlapping and opposing exposure.
5. **Kill switch propagation** — when a thesis is invalidated, notifies the user about external positions with overlapping exposure to the invalidated thesis.
6. **Allocation delta analysis** — largest exposure differences between paper and external, filtered to the user's investable asset classes only. Paper exposure in non-investable asset classes is reported as a single structural summary line, not as gaps to close. Framed as descriptive comparison, not as recommendations.

### Data Sources

- User input at setup: ticker, quantity, entry price (optional), entry date (optional), account label (optional)
- yfinance: current prices, FX rates, sector weightings, asset class splits, top holdings, classification metadata
- Paper portfolio state from T0/T6
- Active theses from macro advisor outputs (same source T1 reads)

### Asset Classification

Automatic via yfinance. For individual stocks: sector, industry, country, currency are reliable and require no user input. For ETFs: category, sector weightings, asset class split (stock/bond/other), and top holdings are pulled from fund data. The system only asks the user for classification when yfinance returns insufficient data — typically obscure local funds or recently listed securities.

### Limitations

- No dividends, splits, or corporate actions tracking. Valuation is price × quantity.
- No risk metrics (VaR, Sharpe) for the external portfolio. This is an exposure tool, not a risk management tool.
- No trade recommendations. It shows gaps and alignment. The user acts.
- Classification of exotic assets (private equity, real estate, options) is manual and approximate.

---

## Honest Limitations

### What this system does well
- Translates macro research into executable positions with clear reasoning
- Enforces risk discipline mechanically (kill switches, drawdown limits, position limits)
- Forces articulation of bear cases before every entry (devil's advocate)
- Tracks performance attribution to identify where value comes from
- Self-corrects execution parameters through the improvement loop
- Maintains complete audit trail of every decision and non-decision

### What this system does not do
- Real-time monitoring — weekly/mid-week cadence only
- Intraday trading or timing — orders are end-of-day oriented
- Trade non-US-listed ETFs — Alpaca supports US markets only; CHF equivalents from the macro advisor are mapped to USD tickers
- Guarantee profits — this is a paper trading system for learning and validation
- Override the macro advisor — if the macro research is wrong, the trades will be wrong

### The meta-risk
The system produces structured trade plans and performance metrics every week. There's a danger of treating "system says buy SPY" as a substitute for thinking. The regime templates are starting points, not algorithms. The devil's advocate exists precisely to slow down automatic execution and force reasoning. If the bear cases become boilerplate, the system has lost its most important safeguard.
