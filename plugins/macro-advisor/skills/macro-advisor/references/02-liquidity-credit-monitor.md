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
- **BDC market** — BIZD (VanEck BDC Income ETF) as direct proxy for private credit conditions. BDCs hold private credit loans and are publicly traded, making this the closest observable proxy to actual private credit market health. Available in snapshot: `snapshot.markets.bizd_bdc_income` and `snapshot.credit.private_credit_proxy.bdc_etf`. Wider thresholds than BKLN (±3% stress/risk-on vs ±1.5%) because BDCs are equity-like instruments with higher volatility.
- **Private credit proxy composite** — Available at `snapshot.credit.private_credit_proxy.composite_signal`. This is a convergence-based composite of 5 proxies (SLOOS, C&I loans, BKLN, BIZD, HY OAS). Raw vote breakdown available at `stress_count`, `easing_count`, `neutral_count`, `total_proxies`. When it reads "inconclusive," report the divergence rather than picking the most alarming proxy. When neutral_count is high relative to total_proxies, state explicitly that most proxies are abstaining — do not describe this as "converging."

### Financial Conditions Indices
- **Chicago Fed National Financial Conditions Index (NFCI)** — weekly release. Available in snapshot: `snapshot.liquidity.financial_conditions`. This is the primary financial conditions indicator.
- **Goldman Sachs Financial Conditions Index (GS FCI)** — proprietary, not available via web search. Do not search for it. Use NFCI as the primary indicator. If GS FCI appears in news headlines during the credit market scan (Search 2), note the headline value, but do not spend a dedicated search on it.
- **Bloomberg Financial Conditions Index** — alternative cross-check (headlines only)

### Central Bank Balance Sheets & Plumbing
- **Fed balance sheet** — weekly H.4.1 release (total assets, reserve balances). Available in snapshot: `snapshot.liquidity.fed_total_assets_T`, `snapshot.liquidity.fed_assets_change`. **Rolling trend:** `snapshot.liquidity.trends.fed_total_assets` provides 4-week and 8-week direction bias (`expansion_bias`, `contraction_bias`, `mixed_positive`, `mixed_negative`, or `neutral`), week counts, and cumulative change with percentage. Use the trend to resolve single-week ambiguity — a +$9B week means nothing alone but `expansion_bias` over 4 and 8 weeks confirms a direction.
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
   - **Fed balance sheet:** `snapshot.liquidity.fed_total_assets_T`, `snapshot.liquidity.fed_assets_change`, **plus rolling trends:** `snapshot.liquidity.trends.fed_total_assets` (4w and 8w direction, cumulative change %). Also available: `snapshot.liquidity.trends.tga`, `snapshot.liquidity.trends.reserves`, `snapshot.liquidity.trends.m2_weekly`
   - **TGA / RRP:** via FRED data in snapshot
   - **ECB balance sheet:** `snapshot.eurozone.ecb_balance_sheet` (total assets, WoW change)
   - **Private credit proxy:** `snapshot.credit.private_credit_proxy` (composite + components)
2. **Check for qualitative-quantitative contradiction in private credit.** After reading the snapshot composite and writing your credit conditions prose, ask: does my qualitative assessment (from web search, news, or market events) contradict the quantitative composite? If yes, populate the `private_credit_override` field. **Override rules:**
   - The override must cite **specific named events** — e.g., "Cliffwater $33B fund gated redemptions on March 18" or "Ares Capital suspended NAV reporting." Vague statements like "I sense stress building" or "conditions feel tight" are NOT valid overrides.
   - The override does NOT change the composite_signal. It sits alongside it as a separate field for downstream consumers to evaluate.
   - Format: `**Private Credit Override:** [CONTRADICTS COMPOSITE] — [specific event 1], [specific event 2]. Composite reads [X] but [qualitative observation].`
   - If no contradiction exists, omit the override field entirely. Do not write "no override needed."
3. **Web search for data NOT in snapshot (3 search budget):**
   - **Search 1: China Total Social Financing** — PBoC monthly, no free API. Will return nothing 2-3 weeks per month (publication lag). When unavailable, note the lag and move on — do not retry.
   - **Search 2: Credit and liquidity market developments** — Search for notable events in credit markets, leveraged lending, private credit, or central bank operations this week. This is a neutral scan — report what you find, whether it's stress, stability, or easing. Do not search with stress-biased terms like "credit crisis" or "default wave." Financial news has a negativity bias — stress events are reported more than stability. Absence of stress headlines is itself a data point. Do not interpret a quiet week as "no data" — interpret it as "no notable disruption."
   - **Search 3: Discretionary** — Use for whatever gap matters most this week. Examples: QT pace commentary if Fed communicated, European credit conditions if ECB acted, commercial bank deposits (H.8) if M2 trend is ambiguous. If nothing warrants a third search, skip it.
4. Synthesize into regime assessment

## Search Strategy

Only search for data NOT available in the snapshot. The snapshot covers: US M2, NFCI, Fed balance sheet, TGA, RRP, HY/IG OAS, SLOOS, C&I loans, BKLN, BIZD, Eurozone M3, ECB balance sheet.

**3 search budget — use all 3 or fewer, never more:**

1. **China TSF** (when available)
   - Primary: "PBOC Total Social Financing [month] [YEAR] release"
   - Fallback: "China credit data [month] [YEAR] Reuters OR Bloomberg"
   - If unavailable: Note "TSF: Monthly release pending. Last known: [value, date]. Publication lag 2-4 weeks." Do not retry — accept the lag for monthly aggregates.

2. **Credit and liquidity market developments** (weekly)
   - "credit market [week] [YEAR] leveraged loans private credit"
   - This is a neutral scan. Report whatever you find: fund launches, gating events, spread commentary, issuance volumes, regulatory actions, or nothing notable. Do not search with stress-biased terms like "credit crisis" or "default wave."
   - If the search surfaces specific named events that contradict the private credit composite, those events feed the override field (Step 2). If it surfaces events that confirm the composite, note that too.

3. **Discretionary** (use when a specific gap matters this week)
   - QT pace commentary (when Fed communicates)
   - European credit conditions (when ECB acts)
   - Commercial bank deposits H.8 (when M2 trend is ambiguous)
   - If nothing warrants a third search, skip it and note "Search 3: not needed this week" in meta.

**Retired searches (do not use):**
- **Goldman Sachs FCI** — proprietary, not available via web search. NFCI from FRED serves the same function and is already in snapshot. Note in output: "GS FCI: proprietary index; using NFCI as alternative."
- **iTraxx Crossover** — requires Bloomberg terminal. Using HY/IG OAS from FRED instead.

**Do NOT search for (available in snapshot — unless section is empty or date is >2 months stale):**
- US M2 → `snapshot.liquidity.*`
- HY/IG credit spreads → `snapshot.credit.*`
- NFCI → `snapshot.liquidity.financial_conditions`
- Fed balance sheet, TGA, RRP → `snapshot.liquidity.*`
- Eurozone M3 → `snapshot.eurozone.m3`
- ECB balance sheet → `snapshot.eurozone.ecb_balance_sheet`
- BKLN, BIZD → `snapshot.markets.*` and `snapshot.credit.private_credit_proxy`

### General rules
Prioritize: FRED data references (already in snapshot), Federal Reserve publications, ECB Statistical Data Warehouse, Reuters, Bloomberg. The data snapshot provides the quantitative foundation. Web search fills two gaps: (1) data not available via API (China TSF), and (2) qualitative market developments that quantitative proxies can't capture (events, commentary, policy actions).

### Amendment log
- v1.3 (2026-W13, A-2026W13-001): Replaced search strategy. Retired GS FCI search (proprietary — use NFCI from snapshot). Formalized "credit and liquidity market developments" as Search 2 — neutral framing, captures both stress and stability events. Added discretionary Search 3 with skip option. Root cause: 2 of 3 searches targeted inherently unavailable data (GS FCI proprietary, China TSF publication lag), producing a structural 0.33 effectiveness ratio. The one useful search (credit market events) happened despite the instructions, not because of them. Confirmation bias check: Search 2 uses neutral framing ("market developments" not "stress signals"), explicitly warns about financial news negativity bias, and instructs analyst to report confirming evidence alongside contradicting evidence.
- v1.2 (2026-W13): Added BIZD (VanEck BDC Income ETF) as 5th private credit proxy. Added neutral_count to raw vote breakdown. Added private_credit_override field for analyst to flag qualitative-quantitative contradictions (must cite specific named events, not subjective assessments). Root cause: composite reported "benign" with 2/4 proxies voting while analyst's prose correctly identified fund gating events — qualitative insight didn't propagate through JSON to downstream skills. Confirmation bias check passed: BIZD is structurally justified (direct proxy vs adjacent-market proxies), override constrained to named events only.
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
**Private Credit Proxies:** [Composite signal] (stress: [N], easing: [N], neutral: [N] of [total] proxies). BKLN: [signal], BIZD: [signal], SLOOS: [signal], C&I: [signal], HY OAS cross-ref: [signal].
**Private Credit Override:** [Only if qualitative events contradict composite — cite specific named events. Omit entirely if no contradiction.]
[2-3 sentence interpretation: Are credit conditions tightening or loosening? Pace of change matters more than level.]

### Financial Conditions Indices
**NFCI:** [Latest reading, change, what it implies]
**GS FCI:** [If headline value appeared in credit market scan, note it. Otherwise: "Proprietary — using NFCI as primary indicator."]
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
  skill_version: "1.3"
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
