# Macro Advisor

An autonomous macro research system for Claude Cowork. Collects economic data from FRED and Yahoo Finance, identifies macro regimes using the Alpine Macro framework (liquidity-first, four-quadrant regime model), generates investment theses with specific ETF implementation, and delivers weekly HTML dashboards.

## What It Does

Every week, the system:

1. Pulls 74+ economic data series from FRED, Yahoo Finance, and CFTC COT (via CFTC SODA API — free, no key needed)
2. Analyzes central bank policy, liquidity conditions, macro data, geopolitical risks, and market positioning
3. Reads external analyst feeds for cross-referencing
4. Identifies the current macro regime (Goldilocks, Overheating, Disinflationary Slowdown, or Stagflation)
5. Generates and monitors investment theses with testable assumptions and kill switches
6. Scores its own accuracy and self-improves
7. Delivers an HTML dashboard with briefing, regime map, thesis reports, and system health

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

Run `/macro-advisor:setup` after installation. It will walk you through:

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
| `/macro-advisor:setup` | First-run configuration |
| `/macro-advisor:run-weekly` | Run the full 13-skill analysis cycle manually |
| `/macro-advisor:investigate-theme` | Investigate a macro theme idea — runs deep research (Skill 11) and thesis evaluation (Skill 7) against the latest data |
| `/macro-advisor:activate-thesis` | List draft theses with numbered selection, activate the ones you want to monitor |
| `/macro-advisor:update-etfs` | Refresh ETF mapping with current market offerings |
| `/macro-advisor:implement-improvements` | Review and apply self-improvement amendments proposed by the system |

## Requirements

- Claude Cowork (desktop app)
- Python 3.8+
- Free FRED API key
- Chrome extension (optional, for X and LinkedIn analyst feeds — 3 of 8 analysts)

## How It Works

The system runs 13 skills in sequence, each building on the previous:

```
Data Collection → Central Bank Watch → Liquidity Monitor → Macro Tracker →
Geopolitical Scanner → Positioning & Sentiment → Analyst Monitor →
Weekly Synthesis → Thesis Generator → Self-Improvement → Thesis Presentation →
Monday Briefing
```

Full methodology is documented in `skills/macro-advisor/references/methodology.md`.

## Configuration

All user preferences are stored in `config/user-config.json` (created during setup, not tracked in git). Add this to your `.gitignore` if you fork the repo.

## License

MIT
