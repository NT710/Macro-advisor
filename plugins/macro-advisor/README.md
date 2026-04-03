# Macro Advisor

An autonomous macro research system for Claude Cowork. Built on a three-force model — **Growth**, **Inflation**, and **Liquidity** — that determines the macro regime and drives all downstream analysis. Collects economic data from FRED, Yahoo Finance, CFTC COT, ECB, Eurostat, EIA, and BIS, identifies macro regimes using the Alpine Macro eight-regime model (Growth × Inflation × Liquidity), produces 6 and 12-month regime forecasts with 3-axis probability distributions, runs empirical pattern matching against historical analog periods, generates investment theses with specific ETF implementation, and delivers weekly HTML dashboards.

## What It Does

Every week, the system:

1. Pulls 90+ economic data series from FRED, Yahoo Finance, CFTC COT, ECB, Eurostat, EIA, and BIS
2. Analyzes central bank policy, liquidity conditions, macro data, geopolitical risks, and market positioning
3. Reads external analyst feeds (8 analysts) for cross-referencing
4. Scans for structural imbalances — supply-demand gaps, capex underinvestment, demographic shifts, technology displacement (bi-weekly, 7 signal detectors)
5. Identifies the current macro regime using the 8-regime model: four families (Goldilocks, Overheating, Disinflationary Slowdown, Stagflation) × two liquidity conditions (Ample, Tight)
6. Produces 6 and 12-month regime forecasts with 3-axis probability distributions (Growth, Inflation, Liquidity trajectories), key assumptions, and conditional triggers
7. Runs empirical pattern matching — finds historical analog periods via cosine similarity and computes per-asset risk/reward ratios (informational context, not directional signal)
8. Generates and monitors investment theses from three sources: data patterns, analyst insights, and structural scans
9. Scores its own accuracy and self-improves
10. Delivers an HTML dashboard with briefing, regime map, thesis reports, and system health

## Installation

### As a Cowork Plugin

1. In Claude Cowork, go to **Settings → Plugins → Add marketplace**
2. Enter the GitHub repo URL
3. Click **Sync**
4. Run `/macro-advisor:setup` in a new session

### From GitHub

1. Clone this repo
2. Open Claude Cowork and point it at the cloned folder
3. Run `/macro-advisor:setup`

## Setup

Run `/macro-advisor:setup` after installation. It starts by explaining the three-force model (Growth, Inflation, Liquidity → eight regimes), then walks you through:

1. **Python dependencies** — installs fredapi, yfinance, pandas, numpy
2. **FRED API key** — free from [fred.stlouisfed.org](https://fred.stlouisfed.org) (My Account → API Keys)
3. **Browser access** — optional, for reading analyst feeds on X and LinkedIn (Steno, Gromen, Alpine Macro). Other analysts use WebFetch.
4. **Currency preference** — CHF, EUR, USD, or GBP
5. **ETF mapping** — builds your ETF reference table for your preferred currency (USD fallback where needed, plus dynamic discovery for niche ETFs)
6. **Schedule** — when to run the weekly analysis

CFTC COT positioning data (9 key futures contracts) is pulled automatically from the CFTC SODA API — no API key needed.

## Commands

| Command | Description |
|---------|-------------|
| `/macro-advisor:setup` | First-run configuration — explains the model, then sets up dependencies, API keys, currency, ETFs, and schedule |
| `/macro-advisor:run-weekly` | Run the full 17-skill analysis cycle manually |
| `/macro-advisor:investigate-theme` | Investigate a macro theme idea — runs deep research (Skill 11) and thesis evaluation (Skill 7) against the latest data |
| `/macro-advisor:structural-scan` | Run the structural scanner manually (bi-weekly, 7 signal detectors) |
| `/macro-advisor:activate-thesis` | List draft theses with numbered selection, activate the ones you want to monitor |
| `/macro-advisor:update-etfs` | Refresh ETF mapping with current market offerings |
| `/macro-advisor:implement-improvements` | Review and apply self-improvement amendments proposed by the system |

## Requirements

- Claude Cowork (desktop app)
- Python 3.8+
- Free FRED API key
- Chrome extension (optional, for X and LinkedIn analyst feeds — 3 of 8 analysts)

## How It Works

The system runs 17 skills in a specific sequence, each building on the previous. Some skills run on special cadences (quarterly, bi-weekly) while the rest run every week:

```
Data Collection → Central Bank Watch → Liquidity Monitor → Macro Tracker →
Geopolitical Scanner → Positioning & Sentiment → Analyst Monitor →
Decade Horizon (quarterly) → Structural Scanner (bi-weekly) →
Weekly Synthesis (8-regime + 3-axis forecasts) → Regime Evaluator →
Empirical Sentiment (analog matching) →
Thesis Generator → Structural Research (if triggered) → Self-Improvement →
Thesis Presentation → Monday Briefing
```

The synthesis skill is where the three forces converge: it reads all upstream analysis, classifies the current regime using the 8-regime model (Growth × Inflation × Liquidity), and produces probability-weighted forecasts at 6 and 12-month horizons with 3-axis driver trajectories and conditional triggers. The empirical sentiment skill then finds historical analog periods and computes per-asset risk/reward ratios as informational context (not directional signal — out-of-sample testing showed it does not beat naive baselines). These outputs, along with the underlying driver trajectories, are consumed by the Trading Engine for forward-looking position reasoning.

The thesis generator draws from three sources: data patterns from the weekly synthesis, analyst-sourced candidates from the analyst monitor, and structural scanner candidates from the bi-weekly structural scan. The decade horizon map (quarterly) provides strategic context by mapping mega-forces across the next decade and identifying blind spots in the thesis book. Structural candidates are routed through first-principles research (Skill 11) before becoming theses.

Full methodology is documented in `skills/macro-advisor/references/methodology.md`.

## Configuration

All user preferences are stored in `config/user-config.json` (created during setup, not tracked in git). Add this to your `.gitignore` if you fork the repo.

## License

MIT
