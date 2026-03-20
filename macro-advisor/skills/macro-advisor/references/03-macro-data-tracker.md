# Skill 3: Macro Data Tracker

## Objective

Track real economy indicators that feed into regime identification. The key insight: the direction of data surprises matters more than the absolute numbers. Systematically beating or missing expectations shifts the growth/inflation picture and drives asset allocation.

## Core Principle

Regime identification over point forecasting. The goal is not to predict GDP to one decimal place. It's to identify which regime we're in (expansion, slowdown, recession, recovery) and which direction the regime is turning. The surprise direction — whether data is systematically beating or missing consensus — is the leading signal.

## Data Targets

### Growth Indicators
- **PMIs:** US ISM Manufacturing, US ISM Services, Eurozone Composite PMI, China Caixin Manufacturing & Services
- **GDP:** Latest prints and revisions for US, EU, China
- **Leading Indicators:** Conference Board Leading Economic Index (LEI), OECD Composite Leading Indicators (CLI)

### Employment
- **US:** Nonfarm payrolls (NFP), weekly initial claims, continuing claims, ADP private payrolls
- **Eurozone:** Unemployment rate
- **Job openings:** JOLTS (US) — quits rate, openings/unemployed ratio

### Inflation
- **US:** CPI (headline and core), PCE (headline and core), sticky vs. flexible CPI
- **Eurozone:** HICP (headline and core)
- **China:** CPI, PPI
- **Inflation expectations:** University of Michigan survey, 5Y5Y breakevens, TIPS spreads

### Consumer & Housing
- **US Consumer:** Retail sales, Michigan Consumer Sentiment, Conference Board Consumer Confidence
- **US Housing:** Housing starts, building permits, existing home sales, Case-Shiller home prices
- **European consumer:** GfK Consumer Climate (Germany), Eurozone retail sales

### Surprise Indices
- **Citi Economic Surprise Index:** US, Eurozone, EM
- Direction and trend of surprises more important than level

## Execution Steps

1. Search for major economic data releases from the past 7 days (NFP, CPI, PMIs, GDP, retail sales, etc.)
2. For each release found, capture: actual number, consensus estimate, prior reading, surprise direction
3. Search for Citi Economic Surprise Index current readings
4. Search for leading indicator updates (LEI, CLI)
5. Search for inflation expectations data
6. Compile into the output format with regime assessment

## Search Strategy

- "US economic data releases this week [YEAR]"
- "ISM manufacturing PMI [month] [YEAR]"
- "ISM services PMI [month] [YEAR]"
- "eurozone PMI [month] [YEAR]"
- "China Caixin PMI [month] [YEAR]"
- "US nonfarm payrolls [month] [YEAR]"
- "US CPI [month] [YEAR]"
- "US PCE inflation [month] [YEAR]"
- "eurozone HICP inflation [month] [YEAR]"
- "US retail sales [month] [YEAR]"
- "economic surprise index [YEAR]"
- "Conference Board leading economic index [YEAR]"
- "JOLTS job openings [YEAR]"
- "US housing starts building permits [month] [YEAR]"
- "University of Michigan consumer sentiment [month] [YEAR]"

Focus on: Bureau of Labor Statistics, Bureau of Economic Analysis, ISM, Eurostat, NBS China, financial news with actual numbers (not just commentary).

## Output Format

```markdown
## Macro Data Tracker — Week of [Date]

### Growth Regime: [Accelerating / Stable / Decelerating / Contraction Risk]
[One sentence justification]

### This Week's Key Releases

| Indicator | Actual | Consensus | Prior | Surprise |
|-----------|--------|-----------|-------|----------|
| [name]    | [val]  | [val]     | [val] | [+/-]   |

[If no major releases this week, state that explicitly and reference next week's calendar.]

### Surprise Trend
[Are data releases systematically beating or missing? Direction of the surprise index. Is the trend accelerating, stable, or reversing?]

### Inflation Picture
[Sticky vs. flexible components. Services vs. goods. Headline vs. core. Direction of change. Are inflation expectations anchored or drifting?]

### Labor Market
[Tight, loosening, or deteriorating? Lead indicators (claims, JOLTS) vs. lagging (unemployment rate). What's the signal for future wage/inflation pressure?]

### Leading Indicators
[LEI direction, PMI new orders vs. inventories, yield curve signal. What are the forward-looking indicators saying about growth 3-6 months out?]

### Bottom Line
[2-3 sentences: What does the real economy data say about the growth/inflation mix? Which direction is the regime moving? Take a position.]
```

## Quality Standards

- The data table must include actual numbers, not descriptions — "176K" not "below expectations"
- Every surprise direction must be calculated from actual vs. consensus, not inferred from commentary
- If a major release happened this week but data couldn't be found, flag it in the gaps
- The growth regime classification must follow from the data presented
- Distinguish between data that is newly released this week vs. data being referenced from prior weeks

## Meta Block

Distinguish between actual retrieval failures ("gaps") and data that hasn't been released yet ("scheduled_releases"). This distinction matters for the improvement loop — gaps indicate search strategy problems, scheduled releases are expected and acceptable.

```yaml
---
meta:
  skill: macro-data-tracker
  skill_version: "1.1"
  run_date: "[ISO date]"
  execution:
    searches_attempted: [number]
    searches_with_useful_results: [number]
    data_points_extracted: [number]
    data_points_expected: 15
  gaps:
    - "[ONLY actual retrieval failures — data exists but couldn't be found]"
  scheduled_releases:
    - "[data that hasn't been released yet — include expected release date]"
    - "example: ISM Manufacturing March 2026 (releases April 1)"
    - "example: Conference Board LEI February 2026 (expected late March)"
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
    freshest_source_date: "[date]"
    oldest_source_used: "[date]"
  notes: "[any issues]"
---
```

### Amendment log
- v1.1 (2026-W12, A-2026W12-004): Split meta block into "gaps" (retrieval failures) and "scheduled_releases" (future-dated data). Root cause: first run conflated ISM/LEI calendar releases with search failures, inflating gap count. Expected impact: clearer inspection accuracy for improvement loop, no change to self_score.
