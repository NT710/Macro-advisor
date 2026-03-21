# Macro Advisor Marketplace

A Claude Cowork plugin marketplace for autonomous macro research and paper trading. Two plugins that work independently but chain together: the Macro Advisor generates weekly macro regime assessments and investment theses, the Trading Engine translates those into portfolio positions on Alpaca paper trading.

## Plugins

### Macro Advisor `v0.4.0`

Autonomous macro research system. Pulls 62+ economic data series from FRED and Yahoo Finance, identifies the current macro regime (Goldilocks, Overheating, Disinflationary Slowdown, or Stagflation) using the Alpine Macro liquidity-first framework, generates investment theses with specific ETF implementation and kill switches, scores its own accuracy, and delivers a weekly HTML dashboard.

**Commands:**

- `/macro-advisor:setup` — First-run setup. Walks you through FRED API key, currency preference, ETF mapping, and scheduling.
- `/macro-advisor:run-weekly` — Run the full 13-skill weekly analysis cycle manually. Collects data, analyzes all macro pillars, identifies regime, generates/monitors theses, scores accuracy, and produces the HTML dashboard.
- `/macro-advisor:investigate-theme` — Investigate a macro theme you find interesting. Runs Skill 11 structural research and Skill 7 thesis evaluation against the latest data. Use this anytime between weekly runs when you spot something worth exploring.
- `/macro-advisor:activate-thesis` — List draft theses with numbered selection and activate the ones you want monitored. Activated theses get weekly kill switch and assumption checks.
- `/macro-advisor:update-etfs` — Refresh the dynamic ETF mapping. Searches for current liquid ETFs matching your currency and thematic preferences.
- `/macro-advisor:implement-improvements` — Review and apply self-improvement amendments proposed by the system. The improvement loop proposes changes but nothing takes effect without your explicit approval.

[Full documentation →](plugins/macro-advisor/README.md)

### Trading Engine `v0.1.1-beta`

Autonomous paper trading system. Reads the Macro Advisor's regime assessments and theses, reconciles current Alpaca positions against target allocation, reasons through trades with mandatory devil's advocate for every new position, executes on Alpaca, and tracks performance with P&L attribution. Includes a self-improvement loop that proposes amendments to its own execution logic — with human approval required before any change takes effect.

> **Beta:** Active development. Expect changes to skill logic, dashboard format, and improvement loop behavior between versions.

**Commands:**

- `/trading-engine:setup` — First-run setup. Walks you through Alpaca API keys, macro advisor path detection, and scheduling.
- `/trading-engine:run-trading` — Run the full trading engine cycle manually. Reads macro advisor outputs, reconciles positions, reasons through trades, executes on Alpaca, and generates the P&L dashboard.
- `/trading-engine:implement-improvements` — Review and apply self-improvement amendments proposed by the trading engine.

[Full documentation →](plugins/trading-engine/README.md)

## How They Chain Together

```
Macro Advisor (Sunday 17:00 CET)          Trading Engine (Sunday 19:00 CET)
─────────────────────────────────          ─────────────────────────────────
FRED / Yahoo Finance / Analysts            Reads macro advisor outputs
        ↓                                          ↓
Regime identification                      Portfolio snapshot (Alpaca)
        ↓                                          ↓
Thesis generation + kill switches          Position reconciliation
        ↓                                          ↓
Self-improvement scoring                   Trade reasoning + devil's advocate
        ↓                                          ↓
HTML dashboard                             Order execution (Alpaca)
                                                   ↓
                                           P&L attribution + self-improvement
                                                   ↓
                                           HTML dashboard (P&L, Trades, Improvements)
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

- **Stateless reasoning** — each run starts fresh from data, not from prior conclusions
- **Kill switches are immediate** — no exceptions, no delays, no "one more day"
- **P&L blindness** — the trading reasoner never sees unrealized gains/losses when deciding positions
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
    commands/               # /macro-advisor:setup, :run-weekly, :investigate-theme, :activate-thesis, :update-etfs, :implement-improvements
    hooks/                  # Session start hook (reads user config)
    skills/                 # 13-skill research chain + references
    scripts/                # Data collection, dashboard generation, ETF lookup, backtest, tests
      assets/               # Bundled Chart.js + Inter font for offline dashboards
    config/                 # User config (created during setup, gitignored)
  trading-engine/           # Paper trading plugin (beta)
    .claude-plugin/
    commands/               # /trading-engine:setup, :run-trading, :implement-improvements
    hooks/                  # Session start hook (reads user config)
    skills/                 # 8-skill trading chain (T0–T7) + references
    scripts/                # Trade execution, performance calc, dashboard, design tokens, tests
      assets/               # Bundled Chart.js + Inter font for offline dashboards
    config/                 # Risk limits, regime templates, user config
```

## License

MIT
