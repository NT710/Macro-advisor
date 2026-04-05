# Skill 3: Macro Data Tracker

## Objective

Track real economy indicators that feed into regime identification. The key insight: the direction of data surprises matters more than the absolute numbers. Systematically beating or missing expectations shifts the growth/inflation picture and drives asset allocation.

## Core Principle

Regime identification over point forecasting. The goal is not to predict GDP to one decimal place. It's to identify which regime we're in (expansion, slowdown, recession, recovery) and which direction the regime is turning. The surprise direction — whether data is systematically beating or missing consensus — is the leading signal.

## Data Targets

### Structured Data — available in snapshot (`outputs/data/latest-snapshot.json`)

Read these from the snapshot first. No web search needed.

**Employment (snapshot.growth.*):**
- Nonfarm payrolls (`snapshot.growth.nonfarm_payrolls`) — value, date, YoY, MoM
- Unemployment rate (`snapshot.growth.unemployment`)
- Initial claims (`snapshot.growth.initial_claims`)
- Continuing claims (`snapshot.growth.continuing_claims`)
- JOLTS Job Openings (`snapshot.growth.jolts_openings`) — monthly, value + date + YoY
- JOLTS Quits (`snapshot.growth.jolts_quits`) — monthly, value + date + YoY

**Inflation (snapshot.inflation.*):**
- CPI headline (`snapshot.inflation.cpi`) — value, date, YoY, MoM
- Core CPI (`snapshot.inflation.core_cpi`)
- PCE (`snapshot.inflation.pce`)
- Core PCE (`snapshot.inflation.core_pce`)
- Michigan Inflation Expectations (`snapshot.inflation.michigan_expectations`) — value, date
- Inflation expectations assessment (`snapshot.inflation.expectations`) — anchored/drifting, 5Y/10Y breakevens

**Consumer & Activity (snapshot.growth.*):**
- Consumer Sentiment (`snapshot.growth.consumer_sentiment`) — U of Michigan, value + date + YoY
- Retail Sales (`snapshot.growth.retail_sales`)
- Industrial Production (`snapshot.growth.industrial_production`)

**Regional Fed Manufacturing Surveys (snapshot.regional_fed_mfg.*):**
- NY Empire State (`snapshot.regional_fed_mfg.empire_state`) — diffusion index, >0 = expansion, <0 = contraction. Releases mid-month, BEFORE ISM.
- Philadelphia Fed (`snapshot.regional_fed_mfg.philly_fed`) — same interpretation. Releases mid-month, BEFORE ISM.
- Dallas Fed (`snapshot.regional_fed_mfg.dallas_fed`) — same interpretation.
- Composite signal (`snapshot.regional_fed_mfg.composite`) — `expanding_count`, `contracting_count`, `total_count`, `average` (mean of diffusion indices), `consensus` (expansion/contraction/mixed), `conviction` (strong/moderate/marginal). The conviction field matters: "expansion with marginal conviction" means surveys are near zero and the signal is weak — do not treat it as a confident PMI proxy. Use this as a structured PMI proxy for regime identification when ISM headline is not yet available or web search fails.

**GDP & Growth Nowcasts (snapshot.growth.*):**
- Real GDP (`snapshot.growth.real_gdp`) — quarterly, value + date + YoY. May be stale between releases.
- Real GDP Chained (`snapshot.growth.real_gdp_chained`) — quarterly, value + date + YoY.
- Atlanta Fed GDPNow (`snapshot.growth.gdpnow`) — real-time nowcast, daily updates. Signal: contracting/stalling/moderate/strong. This is the best real-time growth signal between GDP releases.
- St. Louis Economic News Index (`snapshot.growth.stleni`) — weekly, value + date.
- Recession Probability (`snapshot.growth.recession_probability`) — Smoothed US Recession Probability (Chauvet). Signal: elevated (>30%), moderate (>10%), low (≤10%).

**Leading Indicators (snapshot.growth.*):**
- Conference Board LEI — **NOT in snapshot** (FRED series USSLIND discontinued 2020, removed from data collector). Always use web search: "Conference Board leading economic index [month] [YEAR]".
- Chicago Fed National Activity Index (`snapshot.growth.cfnai_3mo`) — 3-month moving average. >0 = above-trend growth, <0 = below-trend. Broad composite of 85 indicators.

**Housing (snapshot.growth.*):**
- Housing Starts (`snapshot.growth.housing_starts`) — monthly, value + date + YoY + MoM
- Building Permits (`snapshot.growth.building_permits`) — monthly, value + date + YoY + MoM
- Existing Home Sales (`snapshot.growth.existing_home_sales`) — monthly, value + date + YoY + MoM
- Case-Shiller Home Price Index (`snapshot.growth.case_shiller_hpi`) — monthly, value + date + YoY

**Eurozone (snapshot.eurozone.* — if present):**
- HICP headline (`snapshot.eurozone.hicp_headline`) — from Eurostat API, annual rate of change
- HICP core (`snapshot.eurozone.hicp_core`) — ex energy, food, alcohol, tobacco
- ECB M3 YoY growth can be cross-referenced from `snapshot.eurozone.m3_yoy` if available

### Web Search Only — not available in structured APIs

- **PMIs:** US ISM Manufacturing, US ISM Services, Eurozone Composite PMI, China Caixin Manufacturing & Services. ISM PMIs are NOT on FRED (proprietary data). Web search is the only source for the headline numbers. NOTE: Regional Fed surveys (Empire State, Philly Fed, Dallas Fed) are available in snapshot as structured PMI proxies. Use those for regime identification; use ISM web search for the market-moving headline number and surprise direction.
- **GDP:** EU, China latest prints (US GDP now in snapshot: `snapshot.growth.real_gdp`)
- **ADP private payrolls**
- **Eurozone unemployment rate**
- **China CPI, PPI**
- **Sticky vs. flexible CPI** (BLS breakdown, not a FRED series)
- **Conference Board Consumer Confidence** (proprietary, headlines only)
- **GfK Consumer Climate (Germany)**
- **Eurozone retail sales** (Eurostat publishes but not in snapshot yet)

### Surprise Indices
- **Citi Economic Surprise Index:** US, Eurozone, EM — no free API, web search only
- Direction and trend of surprises more important than level

## Execution Steps

1. **Read the data snapshot first.** Extract all structured data from `outputs/data/latest-snapshot.json`:
   - Employment: unemployment, claims, payrolls, JOLTS (openings, quits) — from `snapshot.growth.*`
   - Inflation: CPI, Core CPI, PCE, Core PCE, Michigan expectations — from `snapshot.inflation.*`
   - Consumer: Michigan Sentiment, retail sales — from `snapshot.growth.*`
   - GDP & Nowcasts: `snapshot.growth.real_gdp`, `snapshot.growth.gdpnow` (real-time), `snapshot.growth.recession_probability`
   - Housing: starts, permits, existing sales, Case-Shiller HPI — from `snapshot.growth.*`
   - Leading: CFNAI 3mo (`snapshot.growth.cfnai_3mo`), industrial production — from `snapshot.growth.*`
   - Regional Fed Mfg: Empire State, Philly Fed, Dallas Fed, composite — from `snapshot.regional_fed_mfg.*`. Use the composite consensus as the structured PMI proxy for regime identification.
   - Eurozone: HICP headline + core — from `snapshot.eurozone.*` if present
   - Housing: starts, permits, existing sales — from `snapshot.growth.*` if present
   - For each snapshot value, note the date — if it's the same as last week, the data hasn't updated yet. That's not a gap, it's a release schedule issue.
2. **Web search for data NOT in snapshot:** PMIs (ISM, Eurozone, China Caixin), GDP, ADP, Conference Board LEI, surprise indices, China inflation, GfK, Conference Board Consumer Confidence
3. For each release found (snapshot or search), capture: actual number, consensus estimate (search-only), prior reading, surprise direction
4. Search for Citi Economic Surprise Index current readings
5. Compile into the output format with regime assessment

## Search Strategy

Only search for data NOT available in the snapshot. The snapshot covers: NFP, unemployment, claims, JOLTS (openings, quits), CPI, Core CPI, PCE, Core PCE, Michigan Sentiment, Michigan Inflation Expectations, retail sales, industrial production, regional Fed mfg surveys, CFNAI, housing (starts, permits, existing sales, Case-Shiller), GDP, GDPNow, recession probability, and (if Eurostat integration is active) HICP.

**Search for these (not in snapshot):**
- "ISM manufacturing PMI [month] [YEAR]"
- "ISM services PMI [month] [YEAR]"
- "eurozone PMI [month] [YEAR]"
- "China Caixin PMI [month] [YEAR]"
- "EU GDP [quarter] [YEAR]" (US GDP now in snapshot)
- "ADP private payrolls [month] [YEAR]"
- "Conference Board leading economic index [month] [YEAR]" (no longer in snapshot — FRED series discontinued)
- "economic surprise index [YEAR]"
- "Conference Board consumer confidence [month] [YEAR]"
- "China CPI PPI [month] [YEAR]"

**Search only if snapshot data is stale (>2 months old):**
- "eurozone HICP inflation [month] [YEAR]" (only if Eurostat not yet in snapshot)

**Do NOT search for (available in snapshot — unless section is empty or date is >2 months stale):**
- US nonfarm payrolls, unemployment, claims, JOLTS → `snapshot.growth.*`
- US CPI, PCE, inflation expectations → `snapshot.inflation.*`
- Michigan Consumer Sentiment → `snapshot.growth.consumer_sentiment`
- Retail sales, industrial production → `snapshot.growth.*`
- Housing starts, building permits, existing home sales, Case-Shiller → `snapshot.growth.*`
- US GDP, GDPNow, recession probability → `snapshot.growth.*`
- JOLTS openings, quits → `snapshot.growth.*`
- Regional Fed mfg surveys (Empire State, Philly, Dallas) → `snapshot.regional_fed_mfg.*`
- Chicago Fed National Activity Index → `snapshot.growth.cfnai_3mo`

Focus on: ISM headline (for market-moving number + surprise direction), Eurozone PMI, China Caixin PMI, NBS China, financial news with actual numbers (not just commentary).

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
[LEI direction, regional Fed mfg composite (expansion/contraction/mixed), CFNAI (above/below trend), ISM PMI new orders vs. inventories, yield curve signal. What are the forward-looking indicators saying about growth 3-6 months out?]

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
