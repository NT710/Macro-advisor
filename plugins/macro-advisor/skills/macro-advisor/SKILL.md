---
name: macro-advisor
description: >
  Autonomous macro research system using the Alpine Macro framework. This skill
  should be used when the user asks to "run the macro analysis", "generate a
  weekly briefing", "check the macro regime", "update theses", "run the Sunday
  cycle", "what does the macro data say", or any request related to macro
  economic analysis, regime identification, ETF allocation, or investment
  thesis generation and monitoring.
version: 0.1.0
---

# Macro Advisor

An autonomous macro research system that collects economic data, identifies macro regimes, generates investment theses with ETF implementation, and delivers weekly HTML dashboards.

## Core Belief System

Alpine Macro framework: liquidity drives markets, central banks are the key actors, positioning reveals vulnerability, regime identification over point forecasting, contrarian framing is structural.

Read `references/methodology.md` for the full methodology, eight-regime model (Growth × Inflation × Liquidity), and system architecture.

## Universal Rules

Before executing ANY skill, read `references/RULES.md`. These are non-negotiable policies on data integrity, sizing, language, and analytical discipline.

## Execution Chain

The system runs as a single sequential chain. Each skill reads the output of prior skills.

```
Order: 0 → 1 → 2 → 3 → 4 → 5 → 10 → 14(quarterly) → 13(bi-weekly) → streak → 6 → 6b → 6c → 7 → 11(if candidates flagged) → blind-spot-refresh → 8 → 12 → 9
```

| Step | Skill | Reference File | Purpose |
|------|-------|---------------|---------|
| 0 | Data Collection | `references/00-data-collection.md` | FRED + Yahoo + CFTC + ECB + Eurostat + EIA + BIS → structured JSON |
| 1 | Central Bank Watch | `references/01-central-bank-watch.md` | Fed, ECB, SNB, BoJ, PBoC |
| 2 | Liquidity & Credit | `references/02-liquidity-credit-monitor.md` | M2, credit spreads, NFCI, Fed balance sheet |
| 3 | Macro Data Tracker | `references/03-macro-data-tracker.md` | PMIs, employment, inflation, GDP |
| 4 | Geopolitical Scanner | `references/04-geopolitical-policy-scanner.md` | Trade, fiscal, regulatory, energy |
| 5 | Positioning & Sentiment | `references/05-market-positioning-sentiment.md` | COT, flows, VIX, AAII |
| 10 | Analyst Monitor | `references/10-analyst-monitor.md` | External analyst feeds via ~~browser |
| 14 | Decade Horizon | `references/14-decade-horizon.md` | Quarterly: 3-5 mega-forces, causal chain mapping, thesis book blind spot analysis |
| 13 | Structural Scanner | `references/13-structural-scanner.md` | Bi-weekly: 7 signal detectors including technology displacement |
| 6 | Weekly Synthesis | `references/06-weekly-macro-synthesis.md` | 8-regime assessment (Growth × Inflation × Liquidity) + sector view + 3-axis forecast (cyclical only — does NOT read Skill 13) |
| 6b | Regime Evaluator | `references/06b-regime-evaluator.md` | Independent blind 3-axis regime check + reasoning audit → PASS/REVIEW/CHALLENGE |
| 6c | Empirical Sentiment | `references/06c-empirical-sentiment.md` | Analog matching: finds similar historical macro periods, computes per-asset risk/reward ratios |
| 7 | Thesis Generator | `references/07-thesis-generator-monitor.md` | Generate and monitor theses (three sources: data patterns, analyst-sourced, structural scanner) |
| 11 | Structural Research | `references/11-structural-research.md` | First-principles research (5 trigger paths: data patterns, analyst, scanner, decade-horizon blind spots, manual) |
| — | Blind Spot Refresh | `scripts/refresh_blind_spots.py` | Weekly: re-evaluates Skill 14 blind spot coverage against current thesis book |
| 8 | Self-Improvement | `references/08-self-improvement-loop.md` | Observe → inspect �� amend → evaluate (includes scanner + horizon health monitoring) |
| 12 | Thesis Presentation | `references/12-thesis-presentation.md` | Chart JSON specs + briefing cards (dashboard renders raw thesis files directly) |
| 9 | Monday Briefing | `references/09-monday-briefing.md` | HTML dashboard delivery |

## ETF Reference

ETF selection uses three layers:

1. **Reference table** (`references/etf-reference.md`) — primary ETFs in the user's preferred currency, built during `/macro-advisor:setup` and refreshable with `/update-etfs`
2. **USD fallback** — where no ETF exists in the preferred currency, the reference table includes a USD-denominated alternative (flagged)
3. **Dynamic discovery** (`etf_lookup.py`) — searches ~100 liquid ETFs on Yahoo Finance for thematic/niche exposures not in the reference table, verifies real price data before recommending

## Scripts

All Python scripts are in the `scripts/` directory at the plugin root:

- `data_collector.py` — FRED + Yahoo + CFTC + ECB + Eurostat + EIA + BIS data pull (requires FRED API key; all others are keyless)
- `etf_lookup.py` — Dynamic ETF discovery and verification
- `generate_dashboard.py` — HTML dashboard renderer
- `regime_backtest.py` — Historical regime model validation (8-regime + backfill)
- `evaluation_streak.py` — Deterministic divergence streak computation for Skill 6b
- `analog_matcher.py` — Empirical pattern recognition: finds historical analog periods, computes risk/reward ratios per asset (Skill 6c)
- `refresh_blind_spots.py` — Weekly blind spot coverage refresh: gathers context from horizon data + active theses, applies LLM-evaluated coverage updates

## Output Structure

Outputs are generated at runtime in the working directory:

```
outputs/
├── data/              (JSON snapshots — weekly + latest)
├── collection/        (per-skill weekly outputs)
├── synthesis/         (weekly regime assessments + regime evaluations + evaluation history)
├── strategic/         (quarterly decade horizon maps + last-horizon.json)
├── strategic/blind-spots/ (BLINDSPOT- files for Skill 13/7/11 consumption)
├── strategic/blind-spot-refreshes/ (weekly refresh logs)
├── structural/        (bi-weekly scanner output + last-scan.json)
├── structural/candidates/ (CANDIDATE- files for Skill 7/11 consumption)
├── research/          (structural research briefs)
├── theses/active/     (ACTIVE- and DRAFT- thesis files)
├── theses/closed/     (closed thesis files with outcomes)
├── theses/presentations/ (chart specs JSON — no report files)
├── briefings/         (weekly briefing MD + HTML dashboard)
├── improvement/       (improvement reports + trackers)
└── backtest/          (regime backtest results)
```

## Configuration

The system reads `config/user-config.json` for user preferences set during `/macro-advisor:setup`:

- `fred_api_key` — FRED API key (required; only key needed — EIA, CFTC, BIS are all keyless)
- `preferred_currency` — CHF, EUR, USD, or GBP
- `browser_access` — whether Chrome extension is available (for analyst monitoring)
- `schedule` — day and time for the weekly run
