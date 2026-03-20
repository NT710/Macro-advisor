# Skill 5: Market Positioning & Sentiment

## Objective

Track where money is positioned and where sentiment sits. Positioning is not a signal alone — but positioning extremes combined with macro shifts create the most violent price moves. This skill identifies the vulnerability points.

## Core Principle

Crowded trades unwind violently when the macro picture shifts. The question is always: where is everyone positioned, and what would cause them to reverse? Positioning data tells you about vulnerability, not direction. Combine with the macro regime assessment to identify where the risk/reward is most asymmetric.

## Data Targets

### CFTC Commitments of Traders (COT)
- **Equity index futures:** S&P 500, Nasdaq, Russell 2000 — net speculative positioning
- **Treasury futures:** 2Y, 5Y, 10Y, 30Y — net speculative positioning
- **FX:** EUR/USD, JPY/USD, GBP/USD, CHF/USD, AUD/USD — net speculative
- **Commodities:** Crude oil, gold, copper — net speculative
- Focus on: extreme readings (historical percentile), direction of change, rate of change

### Fund Flows
- **ETF flows:** major equity ETFs (SPY, QQQ, IWM), bond ETFs (TLT, HYG, LQD), international (EEM, EFA)
- **ICI mutual fund flows** — weekly (equity, bond, money market)
- **EPFR global flows** — if available via search (regional allocation shifts)
- **Money market fund balances** — total assets, direction (cash on sidelines?)

### Volatility & Options
- **VIX:** level, term structure (contango = complacent, backwardation = fear)
- **VVIX:** volatility of volatility (cheap options protection = complacency)
- **Put/call ratios:** equity index, total equity
- **Skew:** CBOE Skew Index — tail risk pricing

### Sentiment Surveys
- **AAII Investor Sentiment Survey:** bullish/bearish/neutral percentages, bull-bear spread
- **CNN Fear & Greed Index:** composite reading
- **Bank of America Global Fund Manager Survey** (monthly) — cash levels, biggest tail risks, most crowded trade
- **Investors Intelligence** — bull/bear ratio

### Short Interest
- Major index constituents with unusually high short interest
- Sector-level short interest trends
- Short interest as % of float for key macro ETFs

## Execution Steps

1. Search for latest CFTC Commitments of Traders data (released Friday for prior Tuesday)
2. Search for ETF flow data for the past week
3. Search for VIX level, term structure, put/call ratios
4. Search for AAII sentiment survey latest results
5. Search for CNN Fear & Greed Index current reading
6. Search for BofA Fund Manager Survey (if monthly release occurred)
7. Search for notable short interest data
8. Identify positioning extremes and synthesize

## Search Strategy

- "CFTC commitments of traders [YEAR]"
- "COT report net speculative positions [YEAR]"
- "ETF fund flows weekly [YEAR]"
- "SPY QQQ ETF flows [month] [YEAR]"
- "VIX level term structure [YEAR]"
- "put call ratio equity [YEAR]"
- "AAII investor sentiment survey latest [YEAR]"
- "CNN fear greed index [YEAR]"
- "Bank of America fund manager survey [month] [YEAR]"
- "money market fund assets [YEAR]"
- "short interest data [YEAR]"
- "CBOE skew index [YEAR]"
- "ICI mutual fund flows weekly [YEAR]"

Prioritize: CFTC.gov, ETF.com, Bloomberg, BarChart (for COT), AAII.com references, financial news with actual data.

## Output Format

```markdown
## Market Positioning & Sentiment — Week of [Date]

### Positioning Summary
[Where is the crowd? What are the largest speculative positions in absolute terms and relative to history? 3-5 sentences.]

### Positioning Extremes
[Any positions at historical extremes — long or short. These are the vulnerability points. Include the historical percentile if available.]

| Asset | Net Position | Historical Context | Direction of Change |
|-------|-------------|-------------------|-------------------|
| [name] | [contracts/$ amount] | [e.g., "90th percentile long"] | [increasing/decreasing] |

[If no extremes: "No positioning at historical extremes this period."]

### Sentiment Indicators
**AAII Bull-Bear Spread:** [number, interpretation]
**Fear & Greed:** [reading, direction]
**VIX:** [level], term structure: [contango/backwardation/flat]
**Put/Call Ratio:** [reading, what it implies]

[Overall sentiment assessment: bullish extreme / bullish / neutral / bearish / bearish extreme]

### Flow Data
[Where is money moving? Into/out of which asset classes, regions, sectors? Specific numbers for major ETF flows.]

### Contrarian Signal
[If positioning is extreme, what would cause the unwind? What's the specific macro trigger that would force a reversal? Connect back to the macro data from other skills.]

[If no extreme positioning: "No contrarian setups identified this period."]
```

## Quality Standards

- COT data must include net speculative positions with actual numbers, not just "bullish" or "bearish"
- Historical percentile context is critical — a large long position means nothing without knowing if it's at the 50th or 95th percentile
- Sentiment indicators must include the actual readings, not just directional descriptions
- The contrarian signal section is the most valuable — it must connect positioning to a specific macro catalyst, not just say "positioning is extreme"
- VIX term structure shape matters as much as the level

## Meta Block

```yaml
---
meta:
  skill: market-positioning-sentiment
  skill_version: "1.0"
  run_date: "[ISO date]"
  execution:
    searches_attempted: [number]
    searches_with_useful_results: [number]
    data_points_extracted: [number]
    data_points_expected: 15
  gaps:
    - "[list data points not found — e.g., 'COT historical percentile not available']"
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
    freshest_source_date: "[date]"
    oldest_source_used: "[date]"
  notes: "[any issues]"
---
```
