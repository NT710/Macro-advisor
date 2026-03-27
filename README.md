# Macro Advisor Marketplace

A Claude Cowork plugin marketplace for autonomous macro research and paper trading. Two plugins that work independently but chain together: the Macro Advisor generates weekly macro regime assessments and investment theses, the Trading Engine translates those into portfolio positions on Alpaca paper trading.

## The Model

Both plugins are built on a **three-force framework**: **Growth** (expanding or contracting?), **Inflation** (rising or falling?), and **Liquidity** (loosening or tightening?). Where these three forces sit determines the macro regime — Goldilocks, Overheating, Disinflationary Slowdown, or Stagflation. Each regime has a different playbook for what to own and what to avoid. The system reads the underlying data, identifies which regime you're in, and forecasts where the forces are heading at 6 and 12-month horizons.

## Plugins

### Macro Advisor `v0.7.6`

Autonomous macro research system. Pulls 90+ economic data series from FRED, Yahoo Finance, CFTC COT, ECB, Eurostat, EIA, and BIS, identifies the current macro regime using the Alpine Macro liquidity-first framework, produces 6 and 12-month regime forecasts with probability distributions and conditional triggers, generates investment theses with specific ETF implementation and kill switches, scores its own accuracy, and delivers a weekly HTML dashboard.

The 16-skill analysis chain runs in sequence: data collection across all sources, central bank and liquidity monitoring, macro and geopolitical analysis, market positioning and sentiment, external analyst cross-referencing (8 analysts), decade horizon mapping (quarterly), structural scanning for multi-year imbalances (bi-weekly, 7 signal detectors including technology displacement), weekly synthesis with regime classification and forecasts, independent regime evaluation (generator-evaluator pattern for anti-anchoring), thesis generation and monitoring from three sources (data patterns, analyst insights, structural scans), self-improvement scoring, and delivery.

**Commands:**

- `/macro-advisor:setup` — First-run setup. Explains the three-force model, then walks you through FRED API key, currency preference, ETF mapping, and scheduling.
- `/macro-advisor:run-weekly` — Run the full 16-skill weekly analysis cycle manually. Collects data, analyzes all macro pillars, identifies regime, generates forecasts, generates/monitors theses, scores accuracy, and produces the HTML dashboard.
- `/macro-advisor:structural-scan` — Run the structural scanner manually (7 signal detectors including technology displacement, capex underinvestment, demographic shifts).
- `/macro-advisor:investigate-theme` — Investigate a macro theme you find interesting. Runs structural research and thesis evaluation against the latest data. Use this anytime between weekly runs when you spot something worth exploring.
- `/macro-advisor:activate-thesis` — List draft theses with numbered selection and activate the ones you want monitored. Activated theses get weekly kill switch and assumption checks.
- `/macro-advisor:update-etfs` — Refresh the dynamic ETF mapping. Searches for current liquid ETFs matching your currency and thematic preferences.
- `/macro-advisor:implement-improvements` — Review and apply self-improvement amendments proposed by the system. The improvement loop proposes changes but nothing takes effect without your explicit approval.

[Full documentation →](plugins/macro-advisor/README.md)

### Trading Engine `v0.2.0-beta`

Autonomous paper trading system. Reads the Macro Advisor's regime assessments, theses, and regime forecasts (including the underlying Growth, Inflation, and Liquidity driver readings and trajectories), reconciles current Alpaca positions against target allocation, reasons through trades with mandatory devil's advocate for every new position, executes on Alpaca, and tracks performance with P&L attribution. Includes forecast-aware trade reasoning (durability assessment based on driver sensitivity, not just regime label), structural thesis turnover reservation (prevents structural theses from being indefinitely deferred by the regime scaling queue), and a self-improvement loop that proposes amendments to its own execution logic — with human approval required before any change takes effect.

> **Beta:** Active development. Expect changes to skill logic, dashboard format, and improvement loop behavior between versions.

**Commands:**

- `/trading-engine:setup` — First-run setup. Walks you through Alpaca API keys, macro advisor path detection, and scheduling.
- `/trading-engine:run-trading` — Run the full trading engine cycle manually. Reads macro advisor outputs (including regime forecasts and driver readings), reconciles positions, reasons through trades, executes on Alpaca, and generates the P&L dashboard.
- `/trading-engine:implement-improvements` — Review and apply self-improvement amendments proposed by the trading engine.
- `/trading-engine:update-external-positions` — Add, remove, or update your real-world holdings for the T8 external portfolio overlay.

[Full documentation →](plugins/trading-engine/README.md)

## How They Chain Together

```
Macro Advisor (Sunday 17:00 CET)          Trading Engine (Sunday 19:00 CET)
─────────────────────────────────          ─────────────────────────────────
FRED / Yahoo Finance / Analysts            Reads macro advisor outputs
        ↓                                          ↓
Three-force analysis                       Portfolio snapshot (Alpaca)
(Growth, Inflation, Liquidity)                     ↓
        ↓                                  Signal parsing (regime + forecasts
Regime identification                       + driver readings + theses)
        ↓                                          ↓
6/12-month regime forecasts                Position reconciliation
with driver trajectories                           ↓
        ↓                                  Trade reasoning + devil's advocate
Thesis generation + kill switches          (forecast-aware, driver-sensitive)
        ↓                                          ↓
Self-improvement scoring                   Order execution (Alpaca)
        ↓                                          ↓
HTML dashboard                             P&L attribution + self-improvement
                                                   ↓
                                           External portfolio overlay (optional)
                                                   ↓
                                           HTML dashboard (P&L, Trades, Improvements, External Portfolio)
```

The Trading Engine runs two hours after the Macro Advisor to ensure fresh macro data is available. On Wednesdays, a lighter defense-only check runs kill switches and drawdown monitoring without generating new positions.

Each plugin works independently. The Macro Advisor is useful on its own as a research tool. The Trading Engine requires the Macro Advisor's outputs but handles graceful degradation — if macro data is stale, it processes only kill switch exits and skips new positions.

## Installation

### As a Cowork Marketplace

1. In Claude Cowork, go to **Settings → Plugins → Add marketplace**
2. Enter: `https://github.com/NT710/Macro-advisor`
3. Click **Sync** — both plugins appear in your plugin list
4. **Select a workspace folder** in Cowork (the folder icon) before running setup. All outputs, config, and data are saved here and persist between sessions.
5. Run `/macro-advisor:setup` first, then `/trading-engine:setup`

### From GitHub

```bash
git clone https://github.com/NT710/Macro-advisor.git
```

Open Claude Cowork and point it at the cloned folder. Run the setup commands above.

## Key Design Principles

Both plugins share a philosophy of epistemic humility and anti-confirmation bias:

- **Three-force foundation** — all regime calls and trade decisions trace back to Growth, Inflation, and Liquidity readings
- **Stateless reasoning** — each run starts fresh from data, not from prior conclusions
- **Kill switches are immediate** — no exceptions, no delays, no "one more day"
- **P&L blindness** — the trading reasoner never sees unrealized gains/losses when deciding positions
- **Forecast as context, not override** — 6/12-month regime forecasts inform trade reasoning but do not mechanically change allocations
- **Self-improvement with human gate** — both systems propose amendments to their own logic, but nothing changes without explicit user approval
- **Risk limits are hardcoded** — the self-improvement loop cannot modify position limits, drawdown triggers, or cash minimums

## Requirements

- Claude Cowork (desktop app)
- Python 3.8+
- Free FRED API key ([fred.stlouisfed.org](https://fred.stlouisfed.org))
- Free Alpaca paper trading account ([alpaca.markets](https://alpaca.markets)) — Trading Engine only
- Chrome extension — optional, for browsing analyst feeds on X and LinkedIn (3 of 8 analysts require it, the rest use WebFetch)

## Repository Structure

```
.claude-plugin/
  marketplace.json          # Marketplace manifest listing both plugins
plugins/
  macro-advisor/            # Macro research plugin
    .claude-plugin/
    commands/               # /macro-advisor:setup, :run-weekly, :investigate-theme, :structural-scan, :activate-thesis, :update-etfs, :implement-improvements
    hooks/                  # Session start hook (reads user config)
    skills/                 # 16-skill research chain + references
    scripts/                # Data collection, dashboard generation, ETF lookup, backtest, tests
      assets/               # Bundled Chart.js + Inter font for offline dashboards
    config/                 # User config (created during setup, gitignored)
  trading-engine/           # Paper trading plugin (beta)
    .claude-plugin/
    commands/               # /trading-engine:setup, :run-trading, :implement-improvements, :update-external-positions
    hooks/                  # Session start hook (reads user config)
    skills/                 # 9-step trading chain (T0–T8) + references
    scripts/                # Trade execution, performance calc, dashboard, design tokens, tests
      assets/               # Bundled Chart.js + Inter font for offline dashboards
    config/                 # Risk limits, regime templates, user config
```

## License

MIT
