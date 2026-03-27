# Macro Investment Advisor — Methodology & System Reference

**Version:** 2.6
**Last Updated:** 2026-03-22
**Framework:** Alpine Macro methodology

---

## What This System Produces

The system makes three types of claims each week: regime calls (which macroeconomic quadrant are we in — Goldilocks, Overheating, Disinflationary Slowdown, or Stagflation), asset tilts (what to favor and avoid, expressed as specific ETFs), and thesis predictions (specific investment bets with explicit mechanisms, testable assumptions, and kill switches). Theses come in two depths: tactical (generated from weekly data patterns, weeks-to-quarters horizon) and structural (grounded in first-principles research on physical/economic constraints, quarters-to-years horizon). Everything runs on a Sunday, and the Monday briefing is the user-facing output.

---

## Core Methodology

### What We Believe (Alpine Macro Framework)

1. **Liquidity drives markets.** Changes in money supply, credit conditions, and central bank balance sheets are the primary transmission mechanism to asset prices. This is our analytical lens — we commit to it consistently. When the data contradicts it, we report the contradiction as an observation worth investigating, not as evidence the framework is wrong.

2. **Central banks are the key actors.** Their policy shifts (rate changes, balance sheet operations, forward guidance) are the most important signals to track.

3. **Positioning reveals vulnerability.** When consensus positioning is extreme, the risk/reward skews against it. Crowded trades unwind violently when the macro picture shifts.

4. **Regime identification over point forecasting.** The goal is to identify which regime we're in and which way it's turning. Asset allocation follows regime — but each instance is unique. The framework tells us how to think; the data tells us what to conclude. Regimes are structural conditions that persist for quarters or longer. A regime change requires confirmation across multiple data prints and a visible shift in the 6-month trend — not a single anomalous month.

5. **Contrarian framing is structural.** The question is always: what does the market believe, and what would have to be true for the market to be wrong?

### Four-Quadrant Regime Model

|                    | Inflation Falling | Inflation Rising |
|--------------------|-------------------|------------------|
| **Growth Rising**  | Goldilocks        | Overheating      |
| **Growth Falling** | Disinflationary Slowdown | Stagflation |

The regime label is the starting point. Asset implications are derived from each specific instance's data — credit conditions, positioning, policy stance, valuations — not read from a template. Two different Overheating regimes can look different.

---

## System Architecture

### Execution Chain (Single Sunday Run)

```
Skill 0:  Data Collection (FRED + Yahoo + CFTC + ECB + Eurostat + EIA + BIS → structured JSON)
Skill 1:  Central Bank Watch (Fed, ECB, SNB, BoJ, PBoC)
Skill 2:  Liquidity & Credit Monitor (M2, credit spreads, NFCI, Fed balance sheet)
Skill 3:  Macro Data Tracker (PMIs, employment, inflation, GDP, surprises)
Skill 4:  Geopolitical & Policy Scanner (trade, fiscal, regulatory, energy)
Skill 5:  Market Positioning & Sentiment (COT, flows, VIX, AAII, Fear & Greed)
Skill 10: External Analyst Monitor (8 analysts: Steno, Gromen, Peccatiello, MacroVoices, Marks, Alden, Gavekal, Alpine Macro)
Skill 14: Decade Horizon Strategic Map (quarterly: 3-5 mega-forces, causal chain mapping, thesis book blind spot analysis)
Skill 13: Structural Scanner (bi-weekly: 7 signal detectors including technology displacement — data-first with subagent deep research)
Skill 6:  Weekly Macro Synthesis (reads Skills 1-5 + Skill 10 — NOT Skills 13/14; structural findings enter via thesis pipeline → regime assessment + sector view + 6/12M forecast)
Skill 6b: Regime Evaluator (independent blind regime check — reads Skills 1-5 raw, not regime history — produces PASS/REVIEW/CHALLENGE verdict for Skill 8)
Skill 7:  Thesis Generator & Monitor (3 sources: data-pattern + analyst-sourced + scanner candidates; combined 5-investigation cap for Skill 11)
Skill 11: Structural Research (first-principles research — 5 trigger paths: data-pattern, analyst, scanner, decade-horizon blind spots, manual)
Skill 8:  Self-Improvement Loop (observe → inspect → amend → evaluate + accuracy scoring + Skill 13 health: kill rate, emptiness, provenance ratio + Skill 14 health: force stability, blind spot conversion)
Skill 12: Thesis Presentation (renders theses into visual reports + briefing cards + chart specs)
Skill 9:  Monday Morning Briefing (reads synthesis + theses + presentation cards + improvement → HTML dashboard)
```

Order: 0→1→2→3→4→5→10→14(quarterly)→13(bi-weekly)→streak→6→6b→7→11(if triggered)→8→12→9. Single scheduled task, Sundays at 16:00 CET.

### Data Foundation

**Skill 0 (data_collector.py)** runs before every analysis cycle, pulling 90+ series from seven free institutional-quality sources. Every subsequent skill reads this structured data first. Web search is used only for qualitative context not available in structured form.

Two modes: `weekly` (26-week trailing history) for regular Sunday runs, `historical` (5 years) for regime comparison and first-ever run. A third mode — targeted pulls via `--series` flag — fetches specific FRED series on demand for Skill 11 research investigations. All API fetches (FRED, CFTC) use retry with exponential backoff on rate limit (429) errors.

#### Source 1: FRED (Federal Reserve Economic Data)
Free API (key required). 52+ series covering:

**Money Supply:**
- US M2 Money Stock (weekly: WM2NS, monthly: M2SL)

**Fed Balance Sheet & Plumbing:**
- Fed Total Assets (WALCL) — tracks QT pace
- Treasury General Account / TGA (WTREGEN) — TGA draining = liquidity injection
- Reverse Repo Facility / ON RRP (RRPONTSYD) — RRP falling = liquidity injection
- Reserve Balances at Fed (WRESBAL)

**Interest Rates:**
- Fed Funds Effective Rate (DFF)
- Treasury Yields: 2Y (DGS2), 5Y (DGS5), 10Y (DGS10), 30Y (DGS30)
- Yield Curve Spreads: 10Y-2Y (T10Y2Y), 10Y-3M (T10Y3M)

**Credit Spreads:**
- ICE BofA US High Yield OAS (BAMLH0A0HYM2) — the primary credit stress indicator
- ICE BofA US Investment Grade OAS (BAMLC0A0CM)
- ICE BofA US HY Effective Yield (BAMLH0A0HYM2EY)

**Financial Conditions:**
- Chicago Fed NFCI (NFCI) — negative = loose, positive = tight
- Adjusted NFCI (ANFCI)
- St. Louis Fed Financial Stress Index (STLFSI4)

**Inflation:**
- CPI All Urban Consumers (CPIAUCSL)
- Core CPI ex Food & Energy (CPILFESL)
- PCE Price Index (PCEPI)
- Core PCE (PCEPILFE)
- 5-Year Breakeven Inflation (T5YIE)
- 10-Year Breakeven Inflation (T10YIE)
- U of Michigan Inflation Expectations (MICH)

**Employment:**
- Total Nonfarm Payrolls (PAYEMS)
- Unemployment Rate (UNRATE)
- Initial Jobless Claims (ICSA)
- Continuing Jobless Claims (CCSA)
- JOLTS Job Openings (JTSJOL)
- JOLTS Quits Rate (JTSQUR)

**Growth & Activity:**
- Real GDP (GDP, GDPC1)
- Industrial Production Index (INDPRO)
- Retail Sales (RSAFS)
- U of Michigan Consumer Sentiment (UMCSENT)

**Housing:**
- Housing Starts (HOUST), Building Permits (PERMIT)
- Existing Home Sales (EXHOSLUSM495S)
- Case-Shiller Home Price Index (CSUSHPISA)

**Regional Fed Manufacturing Surveys (PMI Proxies):**
- NY Empire State Mfg Survey (GACDISA066MSFRBNY) — monthly, diffusion index, >0 = expansion. Releases mid-month before ISM.
- Philadelphia Fed Mfg Survey (GACDFSA066MSFRBPHI) — monthly, diffusion index, >0 = expansion. Releases mid-month before ISM.
- Dallas Fed Mfg Survey (BACTSAMFRBDAL) — monthly, diffusion index, >0 = expansion.

*These three together provide a structured composite PMI proxy for regime identification. ISM headline is proprietary and not on FRED — web search is still used for the market-moving ISM number and surprise direction, but the regional Feds ensure regime detection doesn't depend on web search succeeding.*

**Broad Activity Index:**
- Chicago Fed National Activity Index, 3-month MA (CFNAIMA3) — monthly. Weighted average of 85 indicators. >0 = above-trend, <0 = below-trend.

**Leading Indicators:**
- Conference Board LEI — removed from FRED config (USSLIND discontinued 2020). Skill 3 falls back to web search for the current TCB LEI release.

**Money Markets:**
- Retail Money Market Funds (WRMFNS) — weekly, billions USD, cash on sidelines indicator

**Credit Conditions (Private Credit Proxies):**
- Senior Loan Officer Survey — Tightening C&I Loans, Large/Mid firms (DRTSCILM) — quarterly. The strongest leading indicator for bank lending appetite. When banks tighten, private credit borrowers face equivalent or worse conditions.
- Commercial & Industrial Loans Outstanding (BUSLOANS) — weekly. Total bank C&I lending volume. YoY contraction signals credit withdrawal.

*These are proxies for private credit conditions, not direct observations. Private credit has no public mark-to-market. See Skill 5 for interpretation guardrails.*

**Inventory-to-Sales Ratios (supply chain tightness for Skill 13):**
- Retail Inventories/Sales Ratio (RETAILIRSA) — monthly
- Manufacturing Inventories/Sales Ratio (MNFCTRIRSA) — monthly
- Wholesale Inventories/Sales Ratio (WHLSLRIRSA) — monthly

*Falling I/S = inventory drawdown (supply tightness). Rising I/S = demand weakening or overproduction. The collector computes 4w/8w rolling trend for each.*

#### Source 2: Yahoo Finance
Free, no API key required. 25 tickers covering:

**Equity Indices:** S&P 500 (^GSPC), Nasdaq 100 (^NDX), Russell 2000 (^RUT), Euro Stoxx 50 (^STOXX50E)
**Volatility & Sentiment:** VIX (^VIX), CBOE Skew Index (^SKEW)
**Bond ETFs:** TLT (20+ Year Treasury), HYG (High Yield), LQD (Investment Grade)
**Commodities:** Gold (GC=F), Crude Oil WTI (CL=F), Copper (HG=F), Silver (SI=F), Natural Gas (NG=F), Brent Crude (BZ=F)
**Currencies:** EUR/USD, USD/JPY, USD/CHF, GBP/USD, USD/CNY, DXY (DX-Y.NYB)
**Regional ETFs:** EEM (Emerging Markets), EFA (EAFE)
**Money Markets:** SHV (Short Treasury)
**Leveraged Loans:** BKLN (Invesco Senior Loan ETF) — price proxy for leveraged loan market, which shares borrower universe with private credit

#### Source 3: CFTC SODA API (COT Positioning Data)
Free, no API key required. Pulls directly from `publicreporting.cftc.gov`. Two datasets, 9 contracts:

**TFF (Traders in Financial Futures) — dataset `gpe5-46if`:**
- **Equities (Asset Manager positions):** S&P 500 E-mini (13874A), Nasdaq-100 (20974+)
- **Rates (Leveraged Money positions):** 10-Year Treasury Note (043602), 2-Year Treasury Note (042601)
- **FX (Leveraged Money positions):** EUR/USD (099741), JPY/USD (097741)

**Disaggregated Futures Only — dataset `72hh-3qpy`:**
- **Commodities (Money Manager positions):** Gold (088691), Crude Oil WTI (067651), Copper (085692)

For each contract, the collector computes: net speculative position (long minus short), weekly change, 52-week historical percentile, extreme detection (≥90th or ≤10th percentile), and direction of change (building/unwinding long/short). Data is released weekly (Friday, for Tuesday positions). The snapshot stores all COT data under `snapshot.positioning.*`, directly consumable by Skill 5.

Asset Manager and Money Manager positions reflect speculative positioning in equities and commodities. Leveraged Money positions reflect speculative positioning in rates and FX. These are the trader categories whose crowded trades create the violent unwinds that the positioning analysis is designed to detect.

Zero configuration required — the CFTC publishes this data as a public Socrata dataset with no authentication.

#### Source 4: ECB Statistical Data Warehouse (SDW)
Free REST API, no authentication required. 2 series:

**Monetary Aggregates:**
- Eurozone M3 Outstanding Amounts (monthly, EUR millions) — 13-month history for YoY computation

**Balance Sheet:**
- ECB Consolidated Total Assets (weekly, EUR millions) — 26-week history with WoW change

Available in snapshot under `snapshot.eurozone.m3`, `snapshot.eurozone.m3_yoy`, and `snapshot.eurozone.ecb_balance_sheet`. These replace web searches that were previously used by Skill 2 (Liquidity & Credit Monitor) for Eurozone M3 and ECB balance sheet data.

#### Source 5: Eurostat
Free JSON API, no authentication required. 2 series:

**Inflation:**
- HICP All Items — Euro Area (monthly, annual rate of change %) — headline Eurozone inflation
- HICP Core ex Energy & Food — Euro Area (monthly, annual rate of change %) — core Eurozone inflation

Available in snapshot under `snapshot.eurozone.hicp_headline` and `snapshot.eurozone.hicp_core`. These replace web searches that were previously used by Skill 3 (Macro Data Tracker) for Eurozone HICP data.

#### Source 6: EIA (US Energy Information Administration)
Free, no API key required. Downloads the EIA bulk file (PET.zip, ~61MB) and extracts 4 weekly series:

**US Petroleum:**
- Commercial Crude Oil Inventories excl. SPR (WCESTUS1) — weekly, thousands of barrels
- Strategic Petroleum Reserve (WCSSTUS1) — weekly, thousands of barrels
- Refinery Utilization (WPULEUS3) — weekly, percent
- Total Petroleum Products Supplied / demand proxy (WRPUPUS2) — weekly, thousands of barrels/day

The collector computes days of supply (inventory / demand rate). Available at `snapshot.energy`. Note: EIA covers US petroleum only — European and Chinese energy data requires web search.

#### Source 7: BIS (Bank for International Settlements)
Free, no API key required. Fetches from the BIS data portal (data.bis.org). 5 economies:

**Credit-to-GDP Gap:**
- Actual credit-to-GDP ratio (suffix A) and HP-filter trend (suffix B) for US, Euro area, China, Japan, UK
- Gap = actual − trend. Positive gap = credit growing faster than trend (overheating risk), negative = below trend (deleveraging)
- Signal classification: `overheating` (>+10pp), `above_trend`, `near_trend`, `below_trend`, `depressed` (<−10pp)

Available at `snapshot.international_structural`. Quarterly frequency — the most recent observation may lag by 1-2 quarters. Used by Skill 13 Signal 5 as a quantitative anchor for sovereign/credit structural analysis.

#### Derived Signals (computed automatically)
The data collector computes higher-level signals from raw data:

- **Yield Curve State:** steepening (expansion), flat (transition), or inverted (recession warning) — with consecutive weeks in current state
- **Real 10Y Rate:** nominal 10Y minus breakeven — restrictive / neutral / accommodative
- **Credit Stress:** HY OAS level + direction + percentile rank vs. history
- **VIX Regime:** panic / fear / elevated / normal / complacent
- **Liquidity Plumbing:** TGA + RRP direction → double injection / net injection / net drain / double drain
- **Rolling Liquidity Trends:** 4-week and 8-week direction bias for Fed total assets (WALCL), TGA, reserve balances, and M2 weekly. Each window reports direction (`expansion_bias`, `contraction_bias`, `mixed_positive`, `mixed_negative`, `neutral`), week counts, cumulative change, and cumulative change %. A magnitude floor (0.05% of base value) prevents noise from registering as a trend. Resolves single-week ambiguity — e.g., a +$9B weekly change is meaningless alone, but `expansion_bias` over 4 and 8 weeks confirms the Fed is expanding.
- **M2 Growth Regime:** expanding / moderate / stagnant / contracting
- **Financial Conditions:** NFCI with consecutive weeks in loose/tight state
- **USD Trend:** DXY direction over week/month
- **Private Credit Stress Proxy:** Composite of SLOOS tightening, C&I loan growth, leveraged loan ETF price, and HY OAS cross-reference. Requires majority convergence to signal stress or benign — mixed signals produce "inconclusive," which is an honest finding, not a failure. See `snapshot.credit.private_credit_proxy`.
- **Equity Regime:** S&P 500 trend over week/month/3-month
- **Inflation Expectations:** 5Y and 10Y breakevens, anchored vs. drifting assessment
- **Crude Term Structure:** WTI-Brent spread as curve shape proxy — `us_tightness` / `normal_brent_premium` / `wide_brent_premium` with spread trend direction
- **Commodity Momentum:** Price vs. 13-week and 26-week moving averages for gold, crude, copper, silver, natural gas — `strong_uptrend` / `weakening` / `recovering` / `downtrend`
- **Inventory-to-Sales Ratios:** Retail, manufacturing, and wholesale I/S ratios with 4w/8w trend — `drawing` (contraction bias) / `building` (expansion bias) / `stable`
- **EIA Energy Data** (free, no key): US commercial crude inventories, SPR level, refinery utilization, days of supply. Available at `snapshot.energy`.
- **BIS Credit-to-GDP Gap** (free, no key): Credit-to-GDP gap deviation from trend for US, Euro area, China, Japan, UK — `overheating` (>+10pp) / `above_trend` / `near_trend` / `below_trend` / `depressed` (<-10pp). Available at `snapshot.international_structural`.

Every series includes a **percentile rank** vs. the full history fetched — "where is the current value relative to the range?" This enables statements like "HY OAS is at the 97th percentile of tightness" without needing external benchmarking.

#### What Structured Data Does NOT Cover (web search fills these gaps)
- Central bank policy statements, forward guidance, press conferences (qualitative)
- Sentiment surveys: AAII, CNN Fear & Greed, BofA Fund Manager Survey (no free API — BofA is proprietary, web search for headlines only)
- Geopolitical and policy developments (inherently qualitative)
- PMI releases: ISM headline (proprietary), Eurozone Composite PMI, China Caixin PMI. NOTE: Regional Fed surveys (Empire State, Philly Fed, Dallas Fed) now provide a structured PMI proxy in the snapshot for regime identification. ISM web search is still used for the market-moving headline number and surprise direction.
- China Total Social Financing (PBoC, no free API)
- Analyst views and research (Chrome-based browsing + WebFetch via Skill 10)
- COT data for contracts not in the 9-contract coverage (Russell 2000, 5Y/30Y Treasury, GBP, CHF, AUD — web search fallback)

Note: VIX, CBOE Skew, Put/Call ratio, money market fund assets, and CFTC COT positioning (9 key contracts) are now in the structured data snapshot. These were previously web-search-only gaps.

#### Dynamic ETF Discovery
`etf_lookup.py` uses two-layer search: (1) keyword match against a curated universe of ~160 liquid ETFs covering equities, fixed income, FX/currency, volatility, commodities, and alternatives, (2) live Yahoo Finance search API as fallback for themes not in the curated list. All results are verified with real price data, liquidity checks (>10K avg daily volume), and freshness checks (<7 days old). Never recommends unverified tickers. Skill 7 runs a counter-thesis search (opposing direction) alongside the thesis search to force engagement with the other side of the trade, and checks entry timing against recent price momentum.

### External Analyst Monitoring

**Skill 10** monitors 8 external analysts across two groups. Group A (frequent: Steno on X, Gromen on X, Peccatiello on Substack, MacroVoices podcast transcripts) and Group B (less frequent: Howard Marks memos, Lyn Alden monthly newsletter, Evergreen Gavekal blog, Alpine Macro on LinkedIn). It reads with fresh eyes — no pre-loaded expectations about what to find. For browser-accessed sources (X, LinkedIn), it follows links to full articles, not just feed headlines. The reasoning behind analyst conclusions is what makes this useful for thesis cross-referencing and as a source of analyst-originated thesis candidates.

### Thesis System

Theses are specific, falsifiable investment bets classified into two types:

**Tactical theses** are generated from weekly data patterns (divergences, regime shifts, positioning extremes). They use a standard template with mechanism, assumptions, kill switches, and ETF expressions. Time horizon: weeks to quarters. Generated directly from Skill 6 synthesis output.

**Structural theses** are grounded in first-principles research on physical, economic, or structural constraints that take years to resolve. They require a Skill 11 Structural Research Brief before generation — quantified binding constraints, supply-demand analysis, capital flow data, and a steelmanned contrarian stress-test. The expanded structural template separates thesis conviction from expression selection from entry timing, requires independently testable assumptions ("What Has To Stay True"), and monitors through weekly kill switch checks with full structural reviews triggered by data changes (assumption pressure, binding constraint updates, regime shifts) rather than fixed calendar intervals.

Both types share:
- Summary (readable by a non-specialist)
- Testable assumptions (each checked weekly)
- First/second/third-order ETF expressions (verified via etf_lookup.py, listed in user's preferred currency where available)
- Kill switches (specific, measurable — if met, thesis is INVALIDATED, no negotiation)
- Parameter review (when analyst insights challenge thesis parameters, flagged for review)
- Time horizon derived from the mechanism, not from a default

**Thesis provenance:** Every thesis is tagged as `data-pattern` (generated from Skill 6 synthesis divergences, regime shifts, positioning extremes), `analyst-sourced` (flagged by Skill 7 from analyst monitor output, researched by Skill 11), or `structural-scanner` (originated from Skill 13 scanner candidates, researched by Skill 11). Analyst-sourced theses must produce independent evidence — if the evidence base relies primarily on the originating analyst's own data and claims, conviction is reduced. Skill 8 monitors the ratio across all three provenance categories and flags drift if any single category dominates (>60% of active theses).

**Three thesis candidate pipelines (Skill 7 Function A):**
1. **Data-pattern path:** Skill 6 synthesis → Skill 7 identifies divergences/regime shifts → generates tactical or flags for Skill 11 if structural.
2. **Analyst-sourced path:** Skill 10 monitors analysts → Skill 7 flags candidates (max 2 per week) that meet three criteria: not captured by existing thesis, not already pursued as data-pattern candidate, contains testable mechanism → Skill 11 runs structural research with evidence independence requirement → Skill 7 generates thesis if evidence holds → enters as DRAFT.
3. **Scanner-sourced path:** Skill 13 detects quantitative tension → screens through equilibrium/base-rate/consensus checks → writes candidate to `outputs/structural/candidates/` → Skill 7 reads and routes ALL scanner candidates to Skill 11 (no bypass) → Skill 7 generates thesis if Skill 11 validates → enters as DRAFT with `provenance: structural-scanner`.

**Combined investigation cap:** No more than 5 total investigation candidates are sent to Skill 11 in a single weekly run (across all three pipelines). If the combined count exceeds 5, prioritize by gap size, novelty, and distance from consensus. Defer the rest.

No fixed limit on thesis count. Quality over quantity. The thesis monitor reads the analyst monitor output to cross-reference assumptions. Parameter Reviews from analyst cross-referencing are written directly to the thesis file under an `## External Views` section so findings travel with the thesis.

Lifecycle: DRAFT → ACTIVE → STRENGTHENING / WEAKENING → INVALIDATED / TIME EXPIRED → CLOSED

### Thesis Presentation (Three-Layer Architecture)

Theses exist in three layers, each serving a different consumption mode:

**Layer 1: Structured file** (the thesis markdown in `outputs/theses/active/`). Machine-readable, for monitoring. This is what Skill 7 writes and maintains.

**Layer 2: Full thesis report** (rendered by Skill 12 into `outputs/theses/presentations/`). The deep-read version with charts, evidence tables, steelmanned bear case, and status history. This is what a human opens when they want to understand a thesis in full. Structural theses get expanded treatment: What Can't Change section, "What Has To Stay True" table, quantified bear claims, and supply-demand trajectory charts.

**Layer 3: Briefing card** (generated by Skill 12, consumed by Skill 9). A compressed summary for the Monday Briefing — status, one-line bet, what changed this week, key risk. Includes a tactical/structural badge so the reader knows the thesis depth at a glance.

The dashboard (`generate_dashboard.py`) renders all three: briefing cards in the Briefing tab, full thesis reports in the Theses tab (with thesis-specific charts from Skill 12's chart specs), and raw thesis files accessible via the Skills tab.

### Self-Improvement Loop (Cognee Framework)

Every weekly run ends with a self-improvement cycle:

1. **Observe:** Each skill writes structured meta blocks with quality metrics
2. **Inspect:** Detects patterns — data gaps, quality trends, search effectiveness, reasoning quality, analytical accuracy
3. **Amend:** Proposes specific, targeted changes to skill instructions (never re-proposes already-implemented amendments)
4. **Evaluate:** Checks whether prior amendments improved metrics. Updates the amendment tracker.

Three layers of quality:
- **Data quality** (2a-2e): Are skills collecting data reliably?
- **Reasoning quality** (2g): Is information flowing between skills? Are cross-references being made?
- **Analytical accuracy** (2h): Were our calls right? Regime, asset tilts, event predictions, thesis performance — scored weekly, cumulative rates tracked in accuracy-tracker.md.

Persistent state files:
- `amendment-tracker.md` — all amendments from proposal through evaluation
- `accuracy-tracker.md` — cumulative scorecard of analytical call accuracy

### Weekly Delivery

One HTML dashboard file containing:
1. **Briefing tab** — 5-minute read, plain language, ETF-focused, with last week's scorecard. Thesis section uses Skill 12 briefing cards with tactical/structural badges.
2. **Regime Map tab** — four-quadrant scatter with current position, 6/12M forecast dots, historical trail
3. **Theses tab** — tabbed view of all active and draft theses. Renders Skill 12 presentation reports (with thesis-specific charts) when available, falls back to raw thesis markdown. Structural and tactical theses are badge-distinguished.
4. **System Health tab** — improvement report, amendment proposals, accuracy tracking
5. **Skills tab** — expandable view of all skill definitions
6. **About tab** — this methodology document

Historical week selector allows browsing past briefings and improvement reports.

---

## Investment Context

### ETF-Focused

All recommendations use specific ETF tickers. Equivalents in the user's preferred currency are primary (verified via Yahoo Finance). USD tickers shown in parentheses when no local-currency version exists. The user's preferred currency is set in `config/user-config.json`.

Reference tables: `skills/references/etf-reference.md` (broad allocation, thematic/sector, currency-specific equivalents).
Dynamic discovery: `scripts/etf_lookup.py` — two-layer search (~160 curated + Yahoo Finance fallback) with verification and liquidity guardrails. Counter-thesis search and entry timing checks live in Skill 7.

### Sizing

- **Monday Briefing:** Directional tilts only ("favor CSSPX.SW over CSNDX.SW"). No percentage allocations.
- **Theses:** Sizing ranges ("small 1-3%", "medium 3-5%"). The user decides exact amounts.

### Sector View

All 11 GICS sectors covered weekly. Timing derived from catalysts (not pre-set categories): what drives the view, when does it resolve, what's the exit signal. Thematic sub-sectors added when active theses or events make them relevant.

---

## Analytical Discipline

### Data Integrity (Non-Negotiable)
- Never invent numbers. Every data point sourced.
- Date-stamp every number. Source-tag ambiguous claims.
- Four-tier data quality: Tier 1 (FRED, official) → Tier 2 (market prices) → Tier 3 (surveys) → Tier 4 (commentary).
- When data conflicts, both values reported.

### Avoiding Confirmation Bias
- No pre-loaded causal chains or expected outcomes. Derive from current data.
- The regime model is our belief system — we commit to it. But asset implications are derived per-instance, not from a template.
- Analyst feeds read with fresh eyes. Extraction fields lead with "whatever they're actually saying" — known topics provide context, not filters.
- Analyst view map is framed analyst-view-first: "Their current view → Challenges our model? → What they see that we might not" — not "Aligns with regime?"
- Thesis patterns are open-ended — the "What to Look For" list is a starting point, not a closed set.
- The improvement loop checks reasoning quality: did skills connect information across outputs?
- Analyst-sourced investigations require evidence independence — cannot rely primarily on the originating analyst's own data.
- Sampling bias warning: 3 of 8 analysts (Gromen, Alden, Gavekal) share views on fiscal dominance/hard assets. Convergence among them is weighted accordingly.
- Analyst views persist until superseded by new content from the same analyst (no calendar cutoff), with age tags for transparency.
- Skill 8 monitors provenance ratio — flags drift if analyst-sourced theses dominate over data-sourced.

### Accountability
- Monday briefing opens with a scorecard: what we said last week, what happened, were we right.
- Improvement loop tracks cumulative accuracy across all weeks.
- After 4+ weeks, the track record reveals where the system adds value and where it doesn't.

---

## Historical Validation of the Regime Model

A quantitative backtest (`scripts/regime_backtest.py`) tests the core claim: does the four-quadrant regime model carry predictive information about forward asset class returns? The backtest also tests whether a liquidity overlay improves the signal.

### What Was Tested

**Layer 1 — Regime only.** Mechanical regime classification (growth × inflation direction over a 6-month window, with a 2-month confirmation filter before regime changes register) applied to 15 years of monthly data (180 months). Forward 1/3/6-month returns computed for 9 asset classes across all four regimes. The 6-month window and confirmation filter align the backtest with the Skill 6 regime stability principle — regimes are structural, not monthly fluctuations.

**Layer 2 — Regime × liquidity.** Same as Layer 1 but conditioned on liquidity (M2 YoY growth, NFCI, Fed balance sheet growth — each measured relative to its own rolling 36-month median, not absolute thresholds).

### Key Findings (as of March 2026)

**The regime model carries information.** Return spreads across regimes are consistent and directionally match the framework's logic across asset classes. The regime classification has predictive power for forward returns.

**Liquidity adds value in the regime that matters most.** The liquidity overlay (M2, NFCI, Fed balance sheet) meaningfully improves signal quality during Disinflationary Slowdown — the most common regime in the dataset. In the other three regimes, the liquidity signal did not cross the significance threshold with this sample size.

**Regime stability improved signal quality.** The 6-month direction window and 2-month confirmation filter reduced noise significantly, raising average regime duration and making return patterns cleaner without losing real transitions.

Full numbers and detailed breakdowns are in `outputs/backtest/`.

### What This Does NOT Validate

**6-12 month regime forecasting.** The backtest validates the classification → return link (if you're in the right regime, the asset implications are real). It does not validate the system's ability to predict which regime will be active 6 or 12 months from now. That forecasting involves judgment, policy interpretation, and analyst cross-referencing that cannot be mechanically replayed on historical data. Forward forecasting accuracy can only be measured through the weekly accuracy tracker over time.

**The judgment layer.** Thesis generation, analyst interpretation, kill switch calibration, and contrarian positioning calls are not tested. These are inherently forward-looking and are scored by the self-improvement loop (Skill 8).

### Critical Warning: Historical Bias

These backtest results are base rates, not predictions. The most dangerous thing this system can do is treat historical averages as templates for current decisions. Two Stagflation periods can produce completely different asset returns depending on credit conditions, positioning, policy response, and starting valuations.

The weekly system must derive its conclusions from current-instance data. The backtest tells us which regimes historically favored which assets. It does not tell us that the current instance will behave the same way. Every weekly synthesis should reason from the data forward, not from historical averages backward.

If the backtest numbers start appearing in skill outputs as justification for positioning ("historically, Goldilocks produces +4.7% equity returns, therefore..."), that is a failure mode. The regime label is a starting point. The data fills in the detail. The backtest provides context, not conclusions.

### Running the Backtest

```bash
python scripts/regime_backtest.py \
  --fred-key "YOUR_KEY" \
  --output-dir outputs/backtest/ \
  --years 15
```

Outputs: `regime-backtest-results.json` (raw data) and `regime-backtest-report.html` (visual report).

---

## File Structure

```
Macro Advisor/
├── CLAUDE.md                       (project instructions)
├── CONNECTORS.md                   (MCP connector requirements — browser access for 3/8 analysts)
├── README.md
├── skills/
│   └── macro-advisor/
│       ├── SKILL.md                (skill definition — triggers, config, ETF reference layers)
│       └── references/
│           ├── RULES.md            (universal policy — data integrity, sizing, language, discipline)
│           ├── etf-reference.md    (ETF lookup tables — broad, thematic, currency-specific)
│           ├── methodology.md      (this file)
│           ├── 00-data-collection.md
│           ├── 01-central-bank-watch.md    (v1.1)
│           ├── 02-liquidity-credit-monitor.md (v1.1)
│           ├── 03-macro-data-tracker.md    (v1.1)
│           ├── 04-geopolitical-policy-scanner.md (v1.1)
│           ├── 05-market-positioning-sentiment.md (v1.2 — COT from snapshot, graceful degradation)
│           ├── 06-weekly-macro-synthesis.md
│           ├── 07-thesis-generator-monitor.md (v1.7 — 3 input sources: data-pattern + analyst + scanner candidates, combined 5-investigation cap)
│           ├── 08-self-improvement-loop.md
│           ├── 09-monday-briefing.md
│           ├── 10-analyst-monitor.md       (v2.0 — 8 analysts, analyst-sourced thesis candidates)
│           ├── 11-structural-research.md   (v1.3 — 5 trigger paths including scanner candidates + decade-horizon blind spots, on-demand FRED, evidence independence)
│           ├── 12-thesis-presentation.md   (v1.1 — visual reports + briefing cards, resolved chart data)
│           ├── 13-structural-scanner.md   (v1.1 — bi-weekly, 7 signal detectors including technology displacement, data-first with subagent research)
│           └── 14-decade-horizon.md       (v1.0 — quarterly mega-force mapping, causal chains, thesis book blind spot analysis)
├── hooks/
│   └── hooks.json                  (session start hook — reads user config)
├── scripts/
│   ├── assets/
│   │   ├── chart.min.js            (bundled Chart.js for offline dashboards)
│   │   └── inter-latin.woff2       (bundled Inter font for offline dashboards)
│   ├── dashboard-template.html     (Jinja2 HTML template for dashboard rendering)
│   ├── data_collector.py           (FRED + Yahoo + CFTC + ECB + Eurostat + EIA + BIS data pull, --series for targeted FRED pulls)
│   ├── etf_lookup.py               (dynamic ETF discovery + verification)
│   ├── generate_dashboard.py       (HTML dashboard generator — reads template + assets)
│   ├── regime_backtest.py          (historical regime backtest — Layer 1 + Layer 2 liquidity)
│   ├── test_dashboard.py           (unit tests for dashboard generator)
│   └── requirements.txt
├── outputs/
│   ├── data/                       (JSON snapshots — weekly + latest)
│   ├── collection/                 (per-skill weekly outputs)
│   ├── synthesis/                  (weekly regime assessments)
│   ├── research/                   (Skill 11 structural research briefs)
│   ├── theses/active/              (ACTIVE- and DRAFT- thesis files)
│   ├── theses/closed/              (closed thesis files with outcomes)
│   ├── theses/presentations/       (Skill 12 rendered reports + chart specs)
│   ├── briefings/                  (weekly briefing MD + HTML dashboard)
│   ├── strategic/                  (Skill 14 quarterly horizon maps + last-horizon.json)
│   ├── strategic/blind-spots/      (BLINDSPOT- files for Skill 13/7/11 consumption)
│   ├── structural/                 (Skill 13 scan results + last-scan.json)
│   ├── structural/candidates/      (advancing scanner candidates for Skill 7 → Skill 11)
│   ├── improvement/                (improvement reports + amendment-tracker.md + accuracy-tracker.md)
│   └── backtest/                   (regime backtest results JSON + HTML report)
├── commands/
│   ├── setup.md                    (first-run configuration with workspace folder check)
│   ├── run-weekly.md               (manual execution trigger for full 14-skill chain)
│   ├── investigate-theme.md        (on-demand theme research)
│   ├── activate-thesis.md          (draft thesis activation)
│   ├── structural-scan.md          (manual structural scanner run)
│   ├── update-etfs.md              (refresh ETF mapping)
│   └── implement-improvements.md   (review self-improvement amendments)
└── config/
    ├── config-schema.json          (expected config fields — drives upgrade notices in pre-flight)
    └── user-config.json            (API keys, preferences — created during setup, gitignored)
```

### Naming Conventions
- Weekly outputs: `YYYY-Www-[skill-name].md` (e.g., `2026-W12-central-bank-watch.md`)
- Theses: `[STATUS]-[thesis-name].md` (e.g., `ACTIVE-labor-recession-credit-stress.md`)
- Dashboard: `YYYY-Www-dashboard.html`

---

## Honest Limitations

### What this system does well
- Structured data collection from institutional-quality free APIs (90+ series across FRED/Yahoo/CFTC/ECB/Eurostat/EIA/BIS, 95%+ success rate) with four-tier quality classification and date-stamped sourcing
- Interprets policy — reads central bank decisions, analyst views, and geopolitical developments and takes positions ("Fed is dovish despite inflation revision"). The user can override any interpretation; the thesis review process is the governance mechanism.
- Forces weekly regime identification with explicit reasoning
- Thesis accountability through testable assumptions and absolute kill switches
- Self-corrects through the improvement loop (data quality + reasoning quality + analytical accuracy)
- Builds cumulative institutional memory and track record over time
- Monitors 8 external analysts across X, Substack, LinkedIn, podcasts, newsletters, and blogs — reads with fresh eyes, follows links to full articles, cross-references against thesis parameters, and surfaces analyst-originated thesis candidates through an evidence-independent research pipeline

### What this system does not do
- Provide real-time monitoring — weekly cadence only, not a Bloomberg terminal
- Give specific trade execution — it tells you the regime, thesis, and instruments, you decide when and how much
- Predict future regimes mechanically — the completed backtest (`scripts/regime_backtest.py`, results in `outputs/backtest/`) confirmed that regime classifications predict forward asset returns and validated the regime + liquidity model. But the system's 6-12 month regime *forecasts* involve judgment calls (policy interpretation, analyst cross-referencing) that cannot be mechanically replayed. Forecast accuracy is tracked weekly by the accuracy tracker, not by the backtest.

### The meta-risk
The system produces structured output every week. There's a danger of treating "system says Stagflation" as a substitute for thinking. The regime model is our framework — we believe in it — but we also check each instance against the data rather than reading off a template. The accountability scorecard exists precisely to catch when the framework stops working.
