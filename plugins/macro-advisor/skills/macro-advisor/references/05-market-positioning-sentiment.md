# Skill 5: Market Positioning & Sentiment

## Objective

Track where money is positioned and where sentiment sits. Positioning is not a signal alone — but positioning extremes combined with macro shifts create the most violent price moves. This skill identifies the vulnerability points.

## Core Principle

Crowded trades unwind violently when the macro picture shifts. The question is always: where is everyone positioned, and what would cause them to reverse? Positioning data tells you about vulnerability, not direction. Combine with the macro regime assessment to identify where the risk/reward is most asymmetric.

## Data Targets

### CFTC Commitments of Traders (COT) — **available in snapshot** (`snapshot.positioning.*`)
Net speculative positions with 52-week percentile rankings for 9 key contracts. Pulled automatically from CFTC SODA API (free, no API key). Read from snapshot first — no web search needed for these:
- **Equity index futures:** S&P 500 (`snapshot.positioning.sp500`), Nasdaq 100 (`snapshot.positioning.nasdaq100`)
- **Treasury futures:** 10Y Note (`snapshot.positioning.10y_treasury`), 2Y Note (`snapshot.positioning.2y_treasury`)
- **FX:** EUR/USD (`snapshot.positioning.eur_usd`), JPY/USD (`snapshot.positioning.jpy_usd`)
- **Commodities:** Gold (`snapshot.positioning.gold`), Crude Oil WTI (`snapshot.positioning.crude_oil_wti`), Copper (`snapshot.positioning.copper`)
- Each contract includes: `net_speculative`, `weekly_change`, `percentile_52w`, `extreme` (null / "extreme long" / "extreme short" / "crowded long" / "crowded short"), `direction` (building/unwinding long/short)
- Focus on: extreme readings (percentile ≥90 or ≤10), direction of change, rate of change
- Web search only for: contracts not in snapshot (Russell 2000, 5Y/30Y Treasury, GBP, CHF, AUD) and for narrative context around extreme readings

### Fund Flows
- **ETF flows:** major equity ETFs (SPY, QQQ, IWM), bond ETFs (TLT, HYG, LQD), international (EEM, EFA)
- **ICI mutual fund flows** — weekly (equity, bond, money market)
- **EPFR global flows** — if available via search (regional allocation shifts)
- **Money market fund balances** — **available in snapshot** (`snapshot.liquidity.money_market_funds`). Retail money market funds (billions USD), direction (cash on sidelines? rising = risk-off, falling = deployment into risk assets). Read from snapshot first.

### Volatility & Options
- **VIX:** level, term structure (contango = complacent, backwardation = fear) — **available in snapshot** (`snapshot.markets.vix`)
- **VVIX:** volatility of volatility (cheap options protection = complacency)
- **Put/call ratios:** CBOE Equity Put/Call Ratio — **no longer in snapshot** (^CPCE delisted on Yahoo). Web search for current put/call ratio if needed for sentiment context. VIX and CBOE Skew are the primary structured sentiment indicators.
- **Skew:** CBOE Skew Index — **available in snapshot** (`snapshot.markets.cboe_skew`). Readings above 150 = high tail risk demand, below 120 = low. Read from snapshot first.

### Sentiment Surveys
- **AAII Investor Sentiment Survey:** bullish/bearish/neutral percentages, bull-bear spread
- **CNN Fear & Greed Index:** composite reading
- **Bank of America Global Fund Manager Survey** (monthly) — cash levels, biggest tail risks, most crowded trade
- **Investors Intelligence** — bull/bear ratio

### Short Interest
- Major index constituents with unusually high short interest
- Sector-level short interest trends
- Short interest as % of float for key macro ETFs

### Credit Stress Cluster (Private Credit Proxy) — **available in snapshot** (`snapshot.credit.private_credit_proxy`)
Private credit ($1.7T+ market) has no public mark-to-market. These are **adjacent-market proxies** that share borrower profiles with private credit. Convergence across proxies strengthens the signal in either direction (stress or benign). Divergence is itself informative — it reveals where the stress narrative breaks down or where benign assumptions may be premature.

- **Senior Loan Officer Survey** (`sloos_tightening_pct`): % of banks tightening C&I loan standards. Quarterly (often stale). Positive = tightening. Above 40 = severe. This is the strongest leading indicator — when banks tighten, private credit borrowers face the same or worse conditions.
- **C&I Loans Outstanding** (`ci_loans_level_B`, `ci_loans_yoy_pct`): Total bank commercial & industrial lending. Contraction or stagnation = credit withdrawal. YoY growth below 0 = serious.
- **Leveraged Loan ETF — BKLN** (`leveraged_loan_etf`, `leveraged_loan_month_chg`): Price-based proxy. Leveraged loans share the same borrower universe as private credit (sub-IG corporates, sponsor-backed). Price declines > 2% in a month = stress. Also in `snapshot.markets.bkln_leveraged_loans`.
- **BDC Income ETF — BIZD** (`bdc_etf`, `bdc_month_chg`): Direct proxy for private credit. BDCs (Business Development Companies) hold private credit loans and are publicly traded, making this the closest observable proxy. Wider thresholds than BKLN (±3% stress/risk-on) because BDCs are equity-like with higher volatility. Also in `snapshot.markets.bizd_bdc_income`.
- **HY OAS** (`hy_oas_cross_ref`): Cross-reference only — already reported in Credit Spreads. Included here for convergence check.
- **Composite signal** (`composite_signal`): Convergence-based composite of 5 proxies. Raw vote breakdown: `stress_count`, `easing_count`, `neutral_count`, `total_proxies`. Requires ≥2 agreeing proxies for directional call. When `neutral_count` is high relative to `total_proxies`, most proxies are abstaining — do not describe this as "converging." Mixed signals = "inconclusive." This is deliberate — do NOT resolve ambiguity by favoring the stress narrative.
- **Analyst override** (`private_credit_override`): Present only when Skill 2 identifies a qualitative-quantitative contradiction — e.g., the composite reads "benign" but major fund gating events are occurring. The override cites specific named events and does NOT change the composite. If present, report both the composite and the override, and let the contradiction stand.

**Anti-confirmation-bias rules for this cluster:**
1. **Never call "private credit stress" from a single proxy.** One indicator moving while others are stable is noise, not signal.
2. **When proxies diverge, say so explicitly.** "SLOOS shows tightening but leveraged loan prices are stable — the signal is inconclusive" is a valid and valuable finding.
3. **Always state the proxy gap.** Every mention of private credit stress must acknowledge we are observing adjacent markets, not private credit directly. Private credit NAVs lag, are smoothed, and can mask deterioration for quarters.
4. **Don't anchor on the narrative that private credit is "the next shoe to drop."** That framing has been recycled since 2022. The data may show genuine stress or genuine stability — report what the proxies show, not what makes the most compelling story.
5. **SLOOS staleness matters.** If the latest SLOOS is 3+ months old, note this explicitly. A Q1 survey reading applied to Q3 conditions is misleading.
6. **Benign convergence is equally newsworthy.** Don't treat "all proxies stable" as "nothing to report." Active benign conditions mean credit channels are functioning — that's useful context for the regime assessment and thesis generation.
7. **Don't anchor on normalization either.** The mirror of the stress bias is assuming everything is fine because leveraged loan ETFs are stable. Private credit NAVs lag and are smoothed — stability in adjacent markets doesn't guarantee stability in private credit.

## Execution Steps

1. **Read the data snapshot first.** Extract all structured data from `outputs/data/latest-snapshot.json`:
   - **COT positioning** (`snapshot.positioning.*`): net speculative positions, percentiles, extremes for all 9 contracts. This is the primary positioning data source. Build the Positioning Extremes table directly from this.
   - **Credit stress cluster** (`snapshot.credit.private_credit_proxy`): SLOOS, C&I loans, BKLN, BIZD, HY OAS — 5 proxies. Check `composite_signal` first, then raw votes (`stress_count`, `easing_count`, `neutral_count`). If "inconclusive," report the divergence honestly. If `private_credit_override` is present (from Skill 2), report both the composite and the override.
   - **VIX** (`snapshot.markets.vix`): level + changes
   - **CBOE Skew** (`snapshot.markets.cboe_skew`): tail risk demand. Readings above 150 = high tail risk demand, below 120 = low.
   - **Put/Call ratio**: no longer in snapshot (^CPCE delisted). Web search if needed for sentiment context.
   - **Money market fund assets** (`snapshot.liquidity.money_market_funds`): cash on sidelines (value_B in billions, with change and percentile)
2. If `snapshot.positioning` is empty (CFTC API unreachable), fall back to web search for COT data: "CFTC commitments of traders [YEAR]"
3. Search for ETF flow data for the past week
4. Use snapshot VIX for level; search for VIX term structure context (contango/backwardation)
5. Search for AAII sentiment survey latest results
6. Search for CNN Fear & Greed Index current reading
7. Search for BofA Fund Manager Survey (if monthly release occurred — this is web-search-only, proprietary data)
8. Search for notable short interest data
9. Search for COT contracts not in snapshot (Russell 2000, 5Y/30Y Treasury, GBP, CHF, AUD) if needed for complete picture
10. Identify positioning extremes and synthesize

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

### Credit Conditions (Private Credit Proxy)
**Composite:** [composite_signal from snapshot]
**SLOOS:** [reading] ([date — note if stale]) — [signal]
**C&I Loans:** [level]B, [yoy]% YoY — [signal]
**Leveraged Loans (BKLN):** [price], [month change]% month — [signal]
**HY OAS cross-ref:** [level] — [consistent/divergent with above]

[If composite = "benign": State which proxies are converging and what would need to change for this to deteriorate. A benign reading is equally significant as a stress reading — do not treat it as "nothing to report." Active benign conditions are useful context for other skills.]
[If composite = "inconclusive": Explicitly state which proxies diverge and why the signal is ambiguous. Do not default to a stress narrative. Divergence is a valid finding — it means the adjacent markets are telling different stories.]
[If composite = "stress": State which proxies are converging and what would need to change for the signal to reverse. Note the proxy gap — this is not direct observation of private credit. Do not anchor on stress as the "real" signal just because the feature was designed to detect it.]

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
- Credit stress cluster must never call "private credit stress" from a single proxy — require convergence
- When credit proxies diverge, the correct output is "inconclusive," not "mixed signals suggest growing stress"

## Meta Block

```yaml
---
meta:
  skill: market-positioning-sentiment
  skill_version: "1.3"
  run_date: "[ISO date]"
  execution:
    searches_attempted: [number]
    searches_with_useful_results: [number]
    data_points_extracted: [number]
    data_points_expected: 19
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
