# Skill 2: Liquidity & Credit Monitor

## Objective

Track the core variables of the Alpine Macro methodology — money supply, credit conditions, and financial conditions. This is the engine of the system. Changes in liquidity are the primary transmission mechanism to asset prices.

## Core Principle

We believe liquidity is the primary transmission mechanism to asset prices. Changes in money supply, credit availability, and financial conditions drive risk asset performance more reliably than earnings, GDP, or sentiment. This is our analytical framework, inherited from Alpine Macro. Track these variables as the foundation of the regime assessment. Direction and rate of change matter more than absolute levels. When the data shows a contradiction — liquidity loose but risk assets falling, or liquidity tightening but equities rising — report it as an observation worth investigating, not as a framework failure. The contradiction itself is often the most useful signal in the data.

## Data Targets

### Money Supply
- **US M2** — monthly official, but track weekly proxies via commercial bank deposits (H.8 report)
- **Eurozone M3** — ECB monthly release
- **China Total Social Financing** — PBoC monthly release, the broadest credit measure
- **China Aggregate Credit** — new yuan loans, shadow banking flows

### Credit Conditions
- **US high-yield credit spreads** — ICE BofA HY OAS (current level + direction)
- **US investment-grade spreads** — ICE BofA IG OAS
- **European credit spreads** — iTraxx Crossover, iTraxx Main
- **Bank lending surveys** — Fed SLOOS (quarterly), ECB Bank Lending Survey (quarterly). Between releases, track commentary and analyst summaries.

### Financial Conditions Indices
- **Chicago Fed National Financial Conditions Index (NFCI)** — weekly release
- **Goldman Sachs Financial Conditions Index (GS FCI)** — reported in GS research and financial media
- **Bloomberg Financial Conditions Index** — alternative cross-check

### Central Bank Balance Sheets & Plumbing
- **Fed balance sheet** — weekly H.4.1 release (total assets, reserve balances)
- **QT pace** — actual vs. scheduled reduction
- **TGA balance** — Treasury General Account at the Fed (affects reserve levels)
- **Reverse repo facility (RRP)** — usage level and trend (draining = liquidity injection)
- **ECB balance sheet** — weekly release

## Execution Steps

1. Search for latest M2/M3 data for US, Eurozone, China
2. Search for credit spread levels — HY OAS, IG OAS, iTraxx
3. Search for NFCI and financial conditions index readings
4. Search for Fed balance sheet weekly data (H.4.1)
5. Search for TGA balance and RRP facility usage
6. Search for ECB balance sheet data
7. Search for China Total Social Financing latest release
8. Synthesize into regime assessment

## Search Strategy

- "US M2 money supply [month] [YEAR]"
- "commercial bank deposits H.8 [YEAR]"
- "eurozone M3 money supply [month] [YEAR]"
- "China total social financing [month] [YEAR]"
- "high yield credit spread OAS [month] [YEAR]"
- "investment grade credit spread [YEAR]"
- "NFCI financial conditions index latest [YEAR]"
- "Goldman Sachs financial conditions index [YEAR]"
- "Federal Reserve balance sheet H.4.1 [YEAR]"
- "Treasury general account TGA balance [YEAR]"
- "reverse repo facility RRP usage [YEAR]"
- "ECB balance sheet [month] [YEAR]"

### Rate-limit prone — use fallback strategy

**China Total Social Financing (TSF):**
1. Primary: Search "PBOC Total Social Financing [month] [YEAR] release"
2. Fallback: Search "China credit data [month] [YEAR] Reuters OR Bloomberg"
3. If rate-limited: Note "TSF: Monthly release pending or unavailable. Last known: [value, date]. Publication lag is 2-4 weeks after month-end." Do not retry — accept the lag for monthly aggregates.

**iTraxx Crossover:**
- Skip web search entirely. iTraxx requires Bloomberg real-time access not available via web search.
- Instead: Use HY/IG OAS from data snapshot as primary credit spread indicators (already captured via FRED).
- Document: "[iTraxx Crossover: real-time pricing unavailable via web search. Using ICE BofA HY OAS and IG OAS from FRED as primary credit spread indicators. Manual Bloomberg check recommended for European credit spread confirmation.]"

### General rules
Prioritize: FRED data references (already in snapshot), Federal Reserve publications, ECB Statistical Data Warehouse, Reuters, Bloomberg. The data snapshot provides M2, NFCI, Fed balance sheet, TGA, RRP, HY OAS, IG OAS — use these as the quantitative foundation. Web search fills qualitative gaps only.

### Amendment log
- v1.1 (2026-W12, A-2026W12-002): Added fallback strategy for China TSF (accept monthly publication lag) and removed iTraxx web search (use FRED HY/IG OAS instead). Root cause: rate-limiting blocked 5/7 searches. Expected impact: eliminate 3 wasted search attempts, improve metadata clarity.

## Output Format

```markdown
## Liquidity & Credit Monitor — Week of [Date]

### Liquidity Regime: [Expanding / Stable / Contracting / Turning]
[One sentence justification for the classification]

### Money Supply
**US M2:** [Latest reading, YoY change, direction vs. prior period]
**Eurozone M3:** [Latest reading, YoY change, direction]
**China TSF:** [Latest reading, YoY change, direction]
[2-3 sentence interpretation: Is money supply growth accelerating, decelerating, or stable?]

### Credit Conditions
**HY Spreads:** [Level in bps, change over past week/month, direction]
**IG Spreads:** [Level in bps, change, direction]
**European Credit:** [iTraxx levels if available]
[2-3 sentence interpretation: Are credit conditions tightening or loosening? Pace of change matters more than level.]

### Financial Conditions Indices
**NFCI:** [Latest reading, change, what it implies]
**GS FCI:** [Latest reading if available]
[Interpretation: Are overall financial conditions loosening or tightening?]

### Central Bank Balance Sheets & Plumbing
**Fed balance sheet:** [Total assets, weekly change, QT pace vs. plan]
**TGA:** [Balance, direction — draining TGA = liquidity injection]
**RRP:** [Usage level, trend — declining RRP = liquidity injection]
**ECB balance sheet:** [Total assets, change]
[Net effect on system liquidity]

### Bottom Line
[2-3 sentences: What is the liquidity regime doing and what does it imply for risk assets? Take a clear position.]
```

## Quality Standards

- Every data point must include the date of the reading — stale data labelled as current is worse than admitting the gap
- Credit spreads must include both level AND direction of change
- The regime classification must be justified by the data presented, not assumed
- If a data point is unavailable, state "Not available this period" rather than omitting silently
- The Bottom Line must take a position — "liquidity is [expanding/contracting] and this is [supportive/headwind] for risk assets"

## Meta Block

```yaml
---
meta:
  skill: liquidity-credit-monitor
  skill_version: "1.1"
  run_date: "[ISO date]"
  execution:
    searches_attempted: [number]
    searches_with_useful_results: [number]
    data_points_extracted: [number]
    data_points_expected: 20
  gaps:
    - "[list each data point looked for but not found]"
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
    freshest_source_date: "[date]"
    oldest_source_used: "[date]"
  notes: "[issues encountered]"
---
```
