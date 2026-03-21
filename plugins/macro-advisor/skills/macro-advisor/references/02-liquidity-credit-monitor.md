# Skill 2: Liquidity & Credit Monitor

## Objective

Track the core variables of the Alpine Macro methodology — money supply, credit conditions, and financial conditions. This is the engine of the system. Changes in liquidity are the primary transmission mechanism to asset prices.

## Core Principle

We believe liquidity is the primary transmission mechanism to asset prices. Changes in money supply, credit availability, and financial conditions drive risk asset performance more reliably than earnings, GDP, or sentiment. This is our analytical framework, inherited from Alpine Macro. Track these variables as the foundation of the regime assessment. Direction and rate of change matter more than absolute levels. When the data shows a contradiction — liquidity loose but risk assets falling, or liquidity tightening but equities rising — report it as an observation worth investigating, not as a framework failure. The contradiction itself is often the most useful signal in the data.

## Data Targets

### Money Supply
- **US M2** — monthly official, but track weekly proxies via commercial bank deposits (H.8 report). Available in snapshot: `snapshot.liquidity.*` (M2 level and growth regime)
- **Eurozone M3** — **available in snapshot:** `snapshot.eurozone.m3` (outstanding amounts in EUR millions, date) and `snapshot.eurozone.m3_yoy` (YoY growth %). Pulled from ECB SDW API (free, no key). Read from snapshot first — no web search needed.
- **China Total Social Financing** — PBoC monthly release, the broadest credit measure. Web search only (no free API).
- **China Aggregate Credit** — new yuan loans, shadow banking flows. Web search only.

### Credit Conditions
- **US high-yield credit spreads** — ICE BofA HY OAS (current level + direction)
- **US investment-grade spreads** — ICE BofA IG OAS
- **European credit spreads** — iTraxx Crossover, iTraxx Main
- **Bank lending surveys** — Fed SLOOS (quarterly), ECB Bank Lending Survey (quarterly). Between releases, track commentary and analyst summaries. SLOOS tightening data available in snapshot: `snapshot.credit.private_credit_proxy.sloos_tightening_pct`.
- **C&I loan volumes** — Commercial & Industrial Loans Outstanding (weekly). Available in snapshot: `snapshot.credit.private_credit_proxy.ci_loans_yoy_pct`. YoY contraction = credit withdrawal.
- **Leveraged loan market** — BKLN ETF price as proxy for leveraged loan conditions. Available in snapshot: `snapshot.markets.bkln_leveraged_loans` and `snapshot.credit.private_credit_proxy.leveraged_loan_etf`.
- **Private credit proxy composite** — Available at `snapshot.credit.private_credit_proxy.composite_signal`. This is a convergence-based composite. When it reads "inconclusive," report the divergence rather than picking the most alarming proxy.

### Financial Conditions Indices
- **Chicago Fed National Financial Conditions Index (NFCI)** — weekly release
- **Goldman Sachs Financial Conditions Index (GS FCI)** — reported in GS research and financial media
- **Bloomberg Financial Conditions Index** — alternative cross-check

### Central Bank Balance Sheets & Plumbing
- **Fed balance sheet** — weekly H.4.1 release (total assets, reserve balances). Available in snapshot: `snapshot.liquidity.fed_total_assets_T`, `snapshot.liquidity.fed_assets_change`
- **QT pace** — actual vs. scheduled reduction
- **TGA balance** — Treasury General Account at the Fed (affects reserve levels). Available in snapshot via FRED WTREGEN.
- **Reverse repo facility (RRP)** — usage level and trend (draining = liquidity injection). Available in snapshot via FRED RRPONTSYD.
- **ECB balance sheet** — **available in snapshot:** `snapshot.eurozone.ecb_balance_sheet` (total assets in EUR millions, date, WoW change). Pulled from ECB SDW API (free, no key). Read from snapshot first — no web search needed.

## Execution Steps

1. **Read the data snapshot first.** Extract all structured data from `outputs/data/latest-snapshot.json`. If any snapshot section is empty or its date is >2 months old, treat that data point as missing and fall back to web search for the latest reading.
   - **US M2:** `snapshot.liquidity.*` (level, growth regime, M2 growth metrics)
   - **Eurozone M3:** `snapshot.eurozone.m3` (EUR millions, date), `snapshot.eurozone.m3_yoy` (YoY %)
   - **Credit spreads:** `snapshot.credit.*` (HY OAS, IG OAS — from FRED)
   - **Financial conditions:** `snapshot.liquidity.financial_conditions` (NFCI — from FRED)
   - **Fed balance sheet:** `snapshot.liquidity.fed_total_assets_T`, `snapshot.liquidity.fed_assets_change`
   - **TGA / RRP:** via FRED data in snapshot
   - **ECB balance sheet:** `snapshot.eurozone.ecb_balance_sheet` (total assets, WoW change)
   - **Private credit proxy:** `snapshot.credit.private_credit_proxy` (composite + components)
2. **Web search only for data NOT in snapshot:**
   - China Total Social Financing (PBoC monthly — no free API)
   - Goldman Sachs FCI (proprietary, headlines only)
   - QT pace commentary (qualitative)
   - Any qualitative credit conditions commentary
3. Synthesize into regime assessment

## Search Strategy

Only search for data NOT available in the snapshot. The snapshot covers: US M2, NFCI, Fed balance sheet, TGA, RRP, HY/IG OAS, SLOOS, C&I loans, BKLN, Eurozone M3, ECB balance sheet.

**Search for these (not in snapshot):**
- "China total social financing [month] [YEAR]"
- "Goldman Sachs financial conditions index [YEAR]"
- "commercial bank deposits H.8 [YEAR]" (weekly proxy for M2, if more granularity needed)

**Do NOT search for (available in snapshot — unless section is empty or date is >2 months stale):**
- US M2 → `snapshot.liquidity.*`
- HY/IG credit spreads → `snapshot.credit.*`
- NFCI → `snapshot.liquidity.financial_conditions`
- Fed balance sheet, TGA, RRP → `snapshot.liquidity.*`
- Eurozone M3 → `snapshot.eurozone.m3`
- ECB balance sheet → `snapshot.eurozone.ecb_balance_sheet`

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
